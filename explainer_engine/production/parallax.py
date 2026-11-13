"""2.5D parallax (D-70 stage F, bible.json motion default "stills + 2.5D parallax"): near parts of a picture slide a little
more than far parts while the shot runs. numpy only.

A shot opts in with ``motion.parallax`` (the near-far shift at the shot's ends, a share of the frame width, at most
MAX_AMP). The depth map is ``<picture>.depth.png`` (``production/depth.py``); a picture without one stays flat and the render
report lists it. ``shift`` is a pure function of the frame (the shot's progress u), so a chunked render draws the same pixels.

Extended in v4.2/v4.3 with ``estimate_synthetic_depth_and_face_safe_mask`` and multi-axis ``(dx, dy)`` parallax support
so existing generated images can receive both horizontal and vertical 2.5D depth parallax while protecting character faces.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

MAX_AMP = 0.02    # 2 % of the width end to end: a camera drift, never a wobble (schema maximum too)
DEFAULT_AMP = 0.012


def amount(motion: dict) -> float:
    return min(float(motion.get("parallax") or 0.0), MAX_AMP)


def load(picture: Path | None) -> np.ndarray | None:
    """The picture's depth map as float32 0..1 (1 = nearest), or None."""
    if picture is None:
        return None
    p = Path(picture).with_name(Path(picture).stem + ".depth.png")
    if not p.exists():
        return None
    return np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0


def estimate_synthetic_depth_and_face_safe_mask(
    image: Image.Image,
    protect_center_character: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a smooth multi-plane depth map (0..1, 1=nearest) and a face-safe warp suppression mask (0..1, 1=rigid)."""
    w, h = image.size
    gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]

    center_weight = np.exp(-((xx / 0.55) ** 2 + ((yy - 0.48) / 0.42) ** 2)).astype(np.float32)
    depth = np.clip(0.45 * yy + 0.35 * gray * center_weight + 0.20 * (1.0 - np.abs(xx)), 0.0, 1.0)

    if protect_center_character:
        face_mask = np.exp(-((xx / 0.28) ** 2 + ((yy - 0.36) / 0.22) ** 2)).astype(np.float32)
        face_mask = np.clip(face_mask, 0.0, 1.0)
        mean_face_depth = float((depth * face_mask).sum() / max(face_mask.sum(), 1e-6))
        depth = depth * (1.0 - 0.85 * face_mask) + mean_face_depth * (0.85 * face_mask)
    else:
        face_mask = np.zeros((h, w), dtype=np.float32)

    return depth.astype(np.float32), face_mask.astype(np.float32)


def direction(motion: dict) -> float:
    """Near parts move with the camera's side move; a push or a hold drifts left to right."""
    if "x0" in motion:
        d = float(motion["x1"]) - float(motion["x0"])
    else:
        d = float(motion.get("dx", 0.0))
    return -1.0 if d < 0 else 1.0


def direction_2d(motion: dict) -> tuple[float, float]:
    """Return `(sign_x, sign_y)` for multi-axis 2.5D parallax shifts."""
    sx = direction(motion)
    if "y0" in motion and "y1" in motion:
        dy = float(motion["y1"]) - float(motion["y0"])
    else:
        dy = float(motion.get("dy", 0.0))
    sy = -1.0 if dy < 0 else (1.0 if dy > 0 else 0.0)
    return sx, sy


def shift(
    frame: Image.Image,
    depth: np.ndarray,
    box,
    src_size: tuple[int, int],
    u: float,
    amp: float,
    sign: float = 1.0,
    dy_amp: float = 0.0,
    sign_y: float = 1.0,
) -> Image.Image:
    """``frame`` (the crop ``box`` of a picture of ``src_size``, already resized) with its near parts moved by
    amp * width * (2u - 1) * (depth - mean depth) horizontally and optionally dy_amp * height * (2u - 1) * (depth - mean depth)
    vertically. Inverse mapping with clamped edges: no holes, no tears."""
    if amp <= 0 and dy_amp <= 0:
        return frame
    OW, OH = frame.size
    W, H = src_size
    dh, dw = depth.shape
    sx0, sy0, sx1, sy1 = box[0] * dw / W, box[1] * dh / H, box[2] * dw / W, box[3] * dh / H
    d = np.asarray(Image.fromarray(depth).resize((OW, OH), Image.BILINEAR, box=(sx0, sy0, sx1, sy1)), dtype=np.float32)
    centered_d = d - float(d.mean())
    off_x = sign * min(float(amp), MAX_AMP) * OW * (2.0 * u - 1.0) * centered_d if amp > 0 else np.zeros_like(centered_d)
    off_y = sign_y * min(float(dy_amp), MAX_AMP) * OH * (2.0 * u - 1.0) * centered_d if dy_amp > 0 else np.zeros_like(centered_d)

    if not (np.any(np.abs(off_x) >= 0.5) or np.any(np.abs(off_y) >= 0.5)):
        return frame

    xs = np.clip(np.rint(np.arange(OW, dtype=np.float32)[None, :] - off_x), 0, OW - 1).astype(np.intp)
    ys = np.clip(np.rint(np.arange(OH, dtype=np.float32)[:, None] - off_y), 0, OH - 1).astype(np.intp)
    src = np.asarray(frame)
    out = src[ys, xs]
    return Image.fromarray(out)
