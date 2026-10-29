"""2.5D parallax (D-70 stage F, bible.json motion default "stills + 2.5D parallax"): near parts of a picture slide a little
more than far parts while the shot runs. numpy only.

A shot opts in with ``motion.parallax`` (the near-far shift at the shot's ends, a share of the frame width, at most
MAX_AMP). The depth map is ``<picture>.depth.png`` (``production/depth.py``); a picture without one stays flat and the render
report lists it. ``shift`` is a pure function of the frame (the shot's progress u), so a chunked render draws the same pixels.
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


def direction(motion: dict) -> float:
    """Near parts move with the camera's side move; a push or a hold drifts left to right."""
    if "x0" in motion:
        d = float(motion["x1"]) - float(motion["x0"])
    else:
        d = float(motion.get("dx", 0.0))
    return -1.0 if d < 0 else 1.0


def shift(frame: Image.Image, depth: np.ndarray, box, src_size: tuple[int, int], u: float, amp: float,
          sign: float = 1.0) -> Image.Image:
    """``frame`` (the crop ``box`` of a picture of ``src_size``, already resized) with its near parts moved by
    amp * width * (2u - 1) * (depth - mean depth). Inverse mapping with clamped edges: no holes, no tears."""
    if amp <= 0:
        return frame
    OW, OH = frame.size
    W, H = src_size
    dh, dw = depth.shape
    sx0, sy0, sx1, sy1 = box[0] * dw / W, box[1] * dh / H, box[2] * dw / W, box[3] * dh / H
    d = np.asarray(Image.fromarray(depth).resize((OW, OH), Image.BILINEAR, box=(sx0, sy0, sx1, sy1)), dtype=np.float32)
    off = sign * amp * OW * (2.0 * u - 1.0) * (d - float(d.mean()))
    if not np.any(np.abs(off) >= 0.5):
        return frame
    xs = np.clip(np.rint(np.arange(OW, dtype=np.float32)[None, :] - off), 0, OW - 1).astype(np.intp)
    src = np.asarray(frame)
    out = src[np.arange(OH)[:, None], xs]
    return Image.fromarray(out)
