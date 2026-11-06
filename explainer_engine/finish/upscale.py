
"""WP-5b: an LTX clip (1920x1088, the sizes the video model takes: width and height divisible by 64, edit/clay_video.py)
becomes a delivery-frame clip (BP-167, 2560x1440 at 24 fps): the 4 px strips the model's size adds are cropped off the top
and bottom to a true 16:9 frame, then a Lanczos scale. ffmpeg only, free, deterministic. A latent upscaler on the pod is a
different, paid step and is not this one. Shorts are not made here: ``production/shorts.py`` owns them (BP-167, 1440x2560).

Guide step 3 (gap G8, D-116) adds two optional steps after the Lanczos scale, off by default so the WP-5b chain stays as it was:
``sharpen`` (``cas`` = contrast-adaptive sharpening 0.4, or ``unsharp`` 5:5:0.6) and ``grain`` (temporal noise, so a flat ink fill
does not band). The route-test pod runs ``ROUTE_TEST`` (cas + grain 6) and keeps both files; ``compare`` measures what the chain
did to the drawing (ink share, palette, sharpness: ``training/video_qa.shot_identity``) on the first, middle and last frame and the
mean-colour CIE76 dE to the Qwen first frame (``blender/grade.delta_e``). No threshold is set here (none is sourced yet, D-59).

    python -m explainer_engine.finish.upscale <clip.mp4> <out.mp4> [--sharpen cas|unsharp|none] [--grain 6] [--first-frame F.png]"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from explainer_engine.core import delivery
from explainer_engine.core.errors import ConfigError

CRF = 17  # the same crf as production/shorts.FINAL_VIDEO: the clip is re-encoded once more in assembly
CAS = 0.4
UNSHARP = "5:5:0.6"
ROUTE_TEST = {"sharpen": "cas", "grain": 6}   # the guide's chain lanczos -> cas -> grain (step 3, G8)


def video_filter(src_w: int, src_h: int, size: tuple[int, int] | None = None, *, sharpen: str = "none", grain: int = 0) -> str:
    """The -vf chain: crop to the delivery aspect (centred, never stretch), Lanczos to the delivery size, then the optional
    sharpen and grain, at the delivery fps."""
    if sharpen not in ("cas", "unsharp", "none"):
        raise ConfigError(f"sharpen is cas, unsharp or none, not {sharpen!r}")
    w, h = size or delivery.size()
    if src_w <= 0 or src_h <= 0:
        raise ConfigError(f"source size {src_w}x{src_h} is not a picture")
    if src_w * h >= src_h * w:  # wider than the delivery aspect (or equal): trim the sides
        crop_w, crop_h = round(src_h * w / h) // 2 * 2, src_h
    else:  # taller (the model's 1088): trim the top and bottom
        crop_w, crop_h = src_w, round(src_w * h / w) // 2 * 2
    if crop_w < src_w * 0.9 or crop_h < src_h * 0.9:
        raise ConfigError(f"{src_w}x{src_h} is not close to {w}:{h}: cropping would cut more than 10 %, re-render the clip")
    extra = {"cas": f",cas={CAS}", "unsharp": f",unsharp={UNSHARP}", "none": ""}[sharpen] + (f",noise=alls={int(grain)}:allf=t"
                                                                                            if grain else "")
    return f"crop={crop_w}:{crop_h}:(in_w-out_w)/2:(in_h-out_h)/2,scale={w}:{h}:flags=lanczos{extra},fps={delivery.fps()}"


def probe_size(path: Path | str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True)
    if out.returncode != 0 or "x" not in out.stdout:
        raise ConfigError(f"ffprobe could not read {path}: {out.stderr.strip()[:200]}")
    w, h = out.stdout.strip().split("x")[:2]
    return int(w), int(h)


def upscale(src: Path | str, dst: Path | str, size: tuple[int, int] | None = None, *, sharpen: str = "none", grain: int = 0) -> Path:
    """``src`` to ``dst`` at the delivery frame. The sound track is dropped (a native-audio LTX clip keeps its own through the
    sound stems); a temp file is renamed so a half-written clip never lies under the final name."""
    w, h = probe_size(src)
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", video_filter(w, h, size, sharpen=sharpen, grain=grain), "-an", "-c:v", "libx264",
           "-crf", str(CRF), "-preset", "medium", "-pix_fmt", "yuv420p", str(part)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        part.unlink(missing_ok=True)
        raise ConfigError(f"upscale failed: {done.stderr.strip()[:300]}")
    os.replace(part, dst)
    return dst


def _mean_rgb(frame) -> list[float]:
    import numpy as np
    return [float(v) / 255 for v in np.asarray(frame, dtype=float).reshape(-1, 3).mean(axis=0)]


def compare(before: Path | str, after: Path | str, first_frame: Path | str | None = None, *, width: int = 960) -> dict:
    """What the upscale changed: per sampled frame (first, middle, last) the ink ratio, palette distance and sharpness after vs
    before (on the source's grid), and the mean-colour dE of each version to the first frame image."""
    import numpy as np
    from PIL import Image

    from explainer_engine.blender import grade
    from explainer_engine.training import video_qa as VQ
    a, _ = VQ.read_video(before, width=width)
    b, _ = VQ.read_video(after, width=width)
    if b.shape[1:3] != a.shape[1:3]:   # the source's 1088 rows were cropped to 16:9: compare on the source's grid
        b = np.stack([np.asarray(Image.fromarray(f).resize((a.shape[2], a.shape[1]), Image.LANCZOS)) for f in b])
    n = min(len(a), len(b))
    if n == 0:
        raise ConfigError("no frames to compare")
    ref = None
    if first_frame is not None:
        ref = np.asarray(Image.open(first_frame).convert("RGB").resize((a.shape[2], a.shape[1]), Image.LANCZOS))
    rows = []
    for i in sorted({0, n // 2, n - 1}):
        m = VQ.shot_identity(a[i], b[i])
        row = {"frame": i, "ink_ratio": m["ink_ratio"], "palette_dist": m["palette_dist"], "sharp_ratio": m["sharp_ratio"]}
        if ref is not None:
            row["delta_e_before"] = round(grade.delta_e(_mean_rgb(a[i]), _mean_rgb(ref)), 3)
            row["delta_e_after"] = round(grade.delta_e(_mean_rgb(b[i]), _mean_rgb(ref)), 3)
        rows.append(row)
    return {"schema": "upscale_compare/1", "before": str(before), "after": str(after), "frames": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="an LTX clip to the delivery frame, optionally sharpened and grained, then compared")
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--sharpen", default=ROUTE_TEST["sharpen"], choices=["cas", "unsharp", "none"])
    ap.add_argument("--grain", type=int, default=ROUTE_TEST["grain"])
    ap.add_argument("--first-frame", type=Path)
    a = ap.parse_args(argv)
    upscale(a.src, a.dst, sharpen=a.sharpen, grain=a.grain)
    print(json.dumps(compare(a.src, a.dst, a.first_frame), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
