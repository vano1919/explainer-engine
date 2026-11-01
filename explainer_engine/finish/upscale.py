"""WP-5b: an LTX clip (1920x1088, the sizes the video model takes: width and height divisible by 64, edit/clay_video.py)
becomes a delivery-frame clip (BP-167, 2560x1440 at 24 fps): the 4 px strips the model's size adds are cropped off the top
and bottom to a true 16:9 frame, then a Lanczos scale. ffmpeg only, free, deterministic. A latent upscaler on the pod is a
different, paid step and is not this one. Shorts are not made here: ``production/shorts.py`` owns them (BP-167, 1440x2560)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from explainer_engine.core import delivery
from explainer_engine.core.errors import ConfigError

CRF = 17  # the same crf as production/shorts.FINAL_VIDEO: the clip is re-encoded once more in assembly


def video_filter(src_w: int, src_h: int, size: tuple[int, int] | None = None) -> str:
    """The -vf chain: crop to the delivery aspect (centred, never stretch), then Lanczos to the delivery size at its fps."""
    w, h = size or delivery.size()
    if src_w <= 0 or src_h <= 0:
        raise ConfigError(f"source size {src_w}x{src_h} is not a picture")
    if src_w * h >= src_h * w:  # wider than the delivery aspect (or equal): trim the sides
        crop_w, crop_h = round(src_h * w / h) // 2 * 2, src_h
    else:  # taller (the model's 1088): trim the top and bottom
        crop_w, crop_h = src_w, round(src_w * h / w) // 2 * 2
    if crop_w < src_w * 0.9 or crop_h < src_h * 0.9:
        raise ConfigError(f"{src_w}x{src_h} is not close to {w}:{h}: cropping would cut more than 10 %, re-render the clip")
    return f"crop={crop_w}:{crop_h}:(in_w-out_w)/2:(in_h-out_h)/2,scale={w}:{h}:flags=lanczos,fps={delivery.fps()}"


def probe_size(path: Path | str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True)
    if out.returncode != 0 or "x" not in out.stdout:
        raise ConfigError(f"ffprobe could not read {path}: {out.stderr.strip()[:200]}")
    w, h = out.stdout.strip().split("x")[:2]
    return int(w), int(h)


def upscale(src: Path | str, dst: Path | str, size: tuple[int, int] | None = None) -> Path:
    """``src`` to ``dst`` at the delivery frame. The sound track is dropped (a native-audio LTX clip keeps its own through the
    sound stems); a temp file is renamed so a half-written clip never lies under the final name."""
    w, h = probe_size(src)
    dst = Path(dst)
    part = dst.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", video_filter(w, h, size), "-an", "-c:v", "libx264",
           "-crf", str(CRF), "-preset", "medium", "-pix_fmt", "yuv420p", str(part)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        part.unlink(missing_ok=True)
        raise ConfigError(f"upscale failed: {done.stderr.strip()[:300]}")
    os.replace(part, dst)
    return dst
