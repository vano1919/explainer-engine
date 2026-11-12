"""Measurements of the rendered demo that the validator reads (all free, from the files): text contrast, background texture, the longest
frozen run, the glass panel's rendered alpha and a pixel check of when each element first appears.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

W, H, FPS = 2560, 1440, 24


def lum(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float64) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def hexrgb(h: str) -> np.ndarray:
    n = int(h[1:], 16)
    return np.array([(n >> 16) & 255, (n >> 8) & 255, n & 255], np.float64)


def frame(video: Path, f: int, pix: str = "rgb24") -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select=eq(n\\,{f})", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", pix, "-"],
                       capture_output=True, check=True)
    ch = {"rgb24": 3, "gray": 1, "rgba": 4}[pix]
    return np.frombuffer(r.stdout, np.uint8).reshape(H, W, ch) if ch > 1 else np.frombuffer(r.stdout, np.uint8).reshape(H, W)


def contrast(comp: Path, spec: dict, texts: dict[str, list], ink: str, pad: int = 3) -> dict[str, float]:
    """WCAG contrast of the ink text against the pixels around it, measured on the composite (before the final grade) at a settled frame:
    the background = pixels of the padded text box that are not near the ink colour (anti-aliased edges excluded), the 10th percentile."""
    ink_rgb, out = hexrgb(ink), {}
    l_ink = float(lum(ink_rgb))
    panels = {p["id"]: p for p in spec["panels"]}
    for it in spec["items"]:
        boxes = texts.get(it["id"])
        if not boxes:
            continue
        p = panels[it["pid"]]
        f = min(max(it["motion_end"] + 8, p["start"] + 10), (it["end"] or spec["frames"]) - 8)
        img = frame(comp, f)
        worst = 99.0
        for x, y, w, h in boxes:
            x0, y0, x1, y1 = int(max(0, x - pad)), int(max(0, y - pad)), int(min(W, x + w + pad)), int(min(H, y + h + pad))
            reg = img[y0:y1, x0:x1].reshape(-1, 3).astype(np.float64)
            d = np.linalg.norm(reg - ink_rgb, axis=1)
            bg = reg[d > 90]
            if len(bg) < 50:
                continue
            l_bg = float(np.percentile(lum(bg), 10))
            worst = min(worst, (max(l_bg, l_ink) + 0.05) / (min(l_bg, l_ink) + 0.05))
        if worst < 99:
            out[it["id"]] = round(worst, 2)
    return out


def bg_std(bg: Path, n: int) -> float:
    g = frame(bg, n // 2, "gray").astype(np.float64)
    return float(g.std())


def gray_stream(video: Path, w: int = 640, h: int = 360) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h}:flags=area,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w)


def frozen_run(video: Path, tau: float = 0.02) -> tuple[int, float]:
    """The longest run of frames in a row whose mean absolute difference (0-255, 640x360 gray) is below tau, and the smallest per-frame difference."""
    g = gray_stream(video).astype(np.float32)
    d = np.abs(np.diff(g, axis=0)).mean(axis=(1, 2))
    run = best = 0
    for v in d:
        run = run + 1 if v < tau else 0
        best = max(best, run)
    return best, float(d.min())


def alpha_frames(webm: Path, w: int = 1280, h: int = 720) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(webm), "-vf", f"alphaextract,scale={w}:{h}:flags=area", "-pix_fmt", "gray",
                        "-f", "rawvideo", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w)


def glass_alpha(webm: Path, spec: dict, a: np.ndarray | None = None) -> dict[str, float]:
    """The overlay's rendered alpha (0-255) of each glass panel: the median over its interior, at a settled frame."""
    a = alpha_frames(webm) if a is None else a
    out = {}
    for p in spec["panels"]:
        if p["surface"] != "glass":
            continue
        f = min(len(a) - 1, p["start"] + 24)
        x, y, w, h = (v / 2 for v in p["box"])
        reg = a[f, int(y + h * 0.1):int(y + h * 0.9), int(x + w * 0.1):int(x + w * 0.9)]
        out[p["id"]] = float(np.median(reg))
    return out


def pixel_first_change(webm: Path, spec: dict, boxes: dict[str, list], a: np.ndarray | None = None) -> dict[str, int | None]:
    """An independent check of the item timing from the rendered pixels: the first frame at which the overlay's alpha inside an item's own
    box differs from the frame two before the planned start (only meaningful where nothing else changes inside that box)."""
    a = alpha_frames(webm).astype(np.int16) if a is None else a.astype(np.int16)
    out = {}
    for it in spec["items"]:
        b = boxes.get(it["id"])
        if not b or it["kind"] in ("scale_bar", "chart_title", "chart_axis", "chart_zero"):
            continue
        x, y, w, h = (v / 2 for v in b)
        box = (slice(int(max(0, y)), int(min(a.shape[1], y + h + 1))), slice(int(max(0, x)), int(min(a.shape[2], x + w + 1))))
        f0 = max(0, it["start"] - 3)
        base = a[f0][box]
        first = None
        for f in range(f0 + 1, min(len(a), it["start"] + 12)):
            if np.abs(a[f][box] - base).sum() > 255 * 2:
                first = f
                break
        out[it["id"]] = first
    return out
