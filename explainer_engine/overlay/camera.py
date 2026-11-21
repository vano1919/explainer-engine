"""The photo camera of a 30 % shot (a slow, eased-linear push) and the map plate's push, as pure functions of the frame number.

The same function draws the background (``demo_bg``), places the overlay in a calm zone and checks the protected zones on every frame
(``rules`` OV-34), so the three can never disagree.
"""
from __future__ import annotations

W, H = 2560, 1440


def cam(push: tuple[float, float, float, float], f: int, n: int) -> tuple[float, float, float]:
    """(scale, centre x, centre y) of frame f of n; the centre is clamped so the crop stays inside the picture."""
    s0, s1, cx, cy = push
    u = f / max(1, n)
    s = s0 + (s1 - s0) * u
    half = 0.5 / s
    return s, min(max(cx, half), 1 - half), min(max(cy, half), 1 - half)


def to_frame(box: tuple[float, float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float, float]:
    """A normalised picture box (x0, y0, x1, y1) -> frame pixels (x0, y0, x1, y1) under camera ``c``."""
    s, cx, cy = c
    x0, y0, x1, y1 = box
    k = lambda v, m, size: ((v - (m - 0.5 / s)) * s) * size
    return (k(x0, cx, W), k(y0, cy, H), k(x1, cx, W), k(y1, cy, H))


def affine(c: tuple[float, float, float], sw: int, sh: int) -> tuple[float, float, float, float, float, float]:
    """PIL Image.transform AFFINE coefficients (output pixel -> source pixel) of camera ``c`` for an sw x sh source."""
    s, cx, cy = c
    cw, ch = sw / s, sh / s
    x0, y0 = cx * sw - cw / 2, cy * sh - ch / 2
    return (cw / W, 0.0, x0, 0.0, ch / H, y0)


def plate_affine(k: float, f: int, n: int, w: int, h: int) -> tuple[float, float, float, float, float, float]:
    """The map plate's push about the frame centre: scale 1 + k f / n (the overlay's world group scales by the same function)."""
    s = 1.0 + k * f / n
    cw, ch = w / s, h / s
    return (cw / W, 0.0, (w - cw) / 2, 0.0, ch / H, (h - ch) / 2)
