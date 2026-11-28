"""Unified realistic cinema film-grade post-pass for maps, 2.5D scenes, stills, and visual bridges."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CinemaGradeSpec:
    """Deterministic unified cinema film-look parameters."""

    name: str = "historical_docudrama_35mm"
    contrast: float = 1.07
    saturation: float = 0.90
    shadow_tint_rgb: tuple[float, float, float] = (0.96, 0.99, 1.05)
    highlight_tint_rgb: tuple[float, float, float] = (1.03, 1.00, 0.94)
    vignette_strength: float = 0.24
    grain_sigma: float = 2.6
    lift: float = 0.012


DEFAULT_CINEMA_GRADE = CinemaGradeSpec()


@lru_cache(maxsize=16)
def _vignette_mask(height: int, width: int, strength: float) -> np.ndarray:
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    nx = (xx / max(1.0, width - 1.0) - 0.5) * 2.0
    ny = (yy / max(1.0, height - 1.0) - 0.5) * 2.0
    r2 = nx * nx * 0.85 + ny * ny * 1.05
    mask = 1.0 - strength * np.clip((r2 - 0.32) / 1.15, 0.0, 1.0) ** 1.45
    return mask[..., None].astype(np.float32)


def apply_unified_film_grade(
    frame_rgb: np.ndarray,
    *,
    frame_idx: int = 0,
    spec: CinemaGradeSpec = DEFAULT_CINEMA_GRADE,
) -> np.ndarray:
    """Apply unified realistic film look to an ``(H, W, 3)`` uint8 RGB frame."""
    x = frame_rgb.astype(np.float32) / 255.0
    h, w = x.shape[:2]

    luma = 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
    x = luma[..., None] + spec.saturation * (x - luma[..., None])

    hi_w = np.clip((luma - 0.35) / 0.55, 0.0, 1.0)[..., None]
    lo_w = 1.0 - hi_w
    s_tint = np.asarray(spec.shadow_tint_rgb, dtype=np.float32)[None, None, :]
    h_tint = np.asarray(spec.highlight_tint_rgb, dtype=np.float32)[None, None, :]
    x = x * (lo_w * s_tint + hi_w * h_tint)

    x = np.clip((x - 0.5) * spec.contrast + 0.5, 0.0, 1.0)
    x = np.where(x > 0.85, 0.85 + (x - 0.85) * 0.68, x)
    x = spec.lift + (1.0 - spec.lift) * x

    if spec.vignette_strength > 0:
        x = x * _vignette_mask(h, w, spec.vignette_strength)

    if spec.grain_sigma > 0:
        rng = np.random.default_rng(104729 + frame_idx * 7919)
        gh, gw = max(1, h // 2), max(1, w // 2)
        g_small = rng.normal(0.0, spec.grain_sigma / 255.0, (gh, gw, 1)).astype(np.float32)
        g = np.repeat(np.repeat(g_small, 2, axis=0), 2, axis=1)[:h, :w, :]
        mid_weight = (4.0 * luma * (1.0 - luma))[..., None]
        x = x + g * (0.35 + 0.65 * mid_weight)

    return np.clip(x * 255.0 + 0.5, 0.0, 255.0).astype(np.uint8)


DEFAULT_LUT_PATH = "assets/luts/historical_docudrama_35mm.cube"


def grade_and_upscale_video_2k(
    src_mp4: Path,
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    lut_path: Path | None = None,
    grain_strength: int = 4,
    vignette_angle: str = "PI/5",
    cas_strength: float = 0.35,
) -> dict[str, object]:
    """Conform any LTX/2.5D/Map clip to 2K 2560x1440 @ 24fps under the exact unified 35mm cinema LUT, grain, and vignette."""
    import hashlib
    import subprocess

    src = Path(src_mp4)
    dst = Path(out_mp4)
    dst.parent.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[2]
    lut = Path(lut_path) if lut_path is not None else (repo_root / DEFAULT_LUT_PATH)

    # Probe source aspect to perform exact centered 16:9 crop without stretching (e.g. 1280x704 -> 1252x704)
    wh = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(src),
        ],
        text=True,
    ).strip()
    sw, sh = (int(v) for v in wh.split("x")[:2])
    if sw * height > sh * width:
        cw, ch = (round(sh * width / height) // 2) * 2, sh
    elif sw * height < sh * width:
        cw, ch = sw, (round(sw * height / width) // 2) * 2
    else:
        cw, ch = sw, sh

    vf_parts = [f"crop={cw}:{ch}:(in_w-out_w)/2:(in_h-out_h)/2", f"scale={width}:{height}:flags=lanczos"]
    if cas_strength > 0:
        vf_parts.append(f"cas={cas_strength:.2f}")
    if lut.is_file():
        # Escape colons/backslashes for ffmpeg filtergraph
        lut_esc = str(lut.resolve()).replace("\\", "/").replace(":", "\\:")
        vf_parts.append(f"lut3d=file='{lut_esc}'")
    if vignette_angle:
        vf_parts.append(f"vignette=angle={vignette_angle}")
    if grain_strength > 0:
        vf_parts.append(f"noise=alls={int(grain_strength)}:allf=t")
    vf_parts.extend([f"fps={fps}", "format=yuv420p"])

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(src),
            "-vf",
            ",".join(vf_parts),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "256k",
            str(dst),
        ],
        check=True,
    )
    h = hashlib.sha256()
    with dst.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {
        "input_path": str(src),
        "output_path": str(dst),
        "width": width,
        "height": height,
        "fps": fps,
        "lut_used": str(lut) if lut.is_file() else None,
        "sha256": h.hexdigest(),
    }
