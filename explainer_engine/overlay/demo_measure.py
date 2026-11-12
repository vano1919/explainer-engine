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


TEXT_TOKEN: dict[str, str] = {}      # the kinds whose text is not drawn in the ink token (template2.html)


def contrast(comp: Path, spec: dict, texts: dict[str, list], ink: str, pad: int = 10, dim: str | None = None) -> dict[str, float]:
    """WCAG contrast of the text against the ground right behind it, measured on the composite (before the final grade) at a settled frame.
    OV-15: the pixels really under the text (after the glass or the halo). The text pixels are those near the item's own text colour
    (ink, or the dim token for the zero label); the ground is the ring 3-5 px outside the glyphs (the halo or the panel; the anti-aliased
    edge is excluded), the 10th percentile of its luminance (the darkest part of the ground is the one that limits legibility)."""
    from scipy import ndimage as ndi
    panels = {p["id"]: p for p in spec["panels"]}
    out = {}
    for it in spec["items"]:
        boxes = texts.get(it["id"])
        if not boxes:
            continue
        col = dim if (TEXT_TOKEN.get(it["kind"]) == "dim" and dim) else ink
        rgb, l_txt = hexrgb(col), float(lum(hexrgb(col)))
        p = panels[it["pid"]]
        f = min(max(it["motion_end"] + 8, p["start"] + 10), (it["end"] or spec["frames"]) - 8)
        img = frame(comp, f)
        worst = 99.0
        for x, y, w, h in boxes:
            x0, y0, x1, y1 = int(max(0, x - pad)), int(max(0, y - pad)), int(min(W, x + w + pad)), int(min(H, y + h + pad))
            reg = img[y0:y1, x0:x1].astype(np.float64)
            t = np.linalg.norm(reg - rgb, axis=2) <= 60
            if t.sum() < 30:
                continue
            ring = ndi.binary_dilation(t, iterations=5) & ~ndi.binary_dilation(t, iterations=3)
            bg = reg[ring]
            if len(bg) < 50:
                continue
            l_bg = float(np.percentile(lum(bg), 10))
            worst = min(worst, (max(l_bg, l_txt) + 0.05) / (min(l_bg, l_txt) + 0.05))
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


# ------------------------------------------------------------------------------------------------ the checks added after the first demo (OV-63..66)
def n_frames(video: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return int(r.stdout.strip().split(",")[0])


def audio_seconds(video: Path) -> float | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    s = r.stdout.strip().split(",")[0]
    return float(s) if s and s != "N/A" else None


def sync_from_signals(s_ov: np.ndarray, s_c: np.ndarray, lags: int = 3) -> dict:
    """``s_ov[f]`` = how much the overlay changed at frame f (its own file), ``s_c[f]`` = how much the picture changed on top of its background at
    frame f (the composite). ``lag`` = the shift of the composite against the overlay that fits best (0 = in step; >0 = the composite is late).
    ``stalls`` = frames where the overlay clearly moved and the composite did not (a repeated overlay frame)."""
    n = min(len(s_ov), len(s_c))
    a, b = s_ov[:n].astype(np.float64), s_c[:n].astype(np.float64)
    if a.max() <= 0:
        return {"lag": 0, "stalls": 0, "moving_frames": 0}
    best, lag = -1.0, 0
    for k in range(-lags, lags + 1):
        x, y = (a[: n - k], b[k:]) if k >= 0 else (a[-k:], b[: n + k])
        if x.std() == 0 or y.std() == 0:
            continue
        cc = float(np.corrcoef(x, y)[0, 1])
        if cc > best + 1e-9 or (abs(cc - best) <= 1e-9 and abs(k) < abs(lag)):
            best, lag = cc, k
    mov = a > 0.25 * np.percentile(a[a > 0], 75)
    base = float(np.median(b[~mov])) if (~mov).any() else 0.0        # what the composite changes with no overlay motion (codec noise, the push)
    top = a >= np.percentile(a[mov], 50)                               # the gain from the clear half of the moving frames
    gain = float(np.percentile((b[top] - base) / a[top], 75)) if top.any() else 0.0
    if gain <= 0:
        return {"lag": lag, "stalls": int(mov.sum()), "moving_frames": int(mov.sum()), "corr": round(best, 3)}
    clear = mov & (gain * a > 1.5 * max(base, 1e-6))                  # only motion that must rise above the composite's own noise can be judged
    stalls = int(np.sum(clear & ((b - base) < 0.2 * gain * a)))
    return {"lag": lag, "stalls": stalls, "moving_frames": int(clear.sum()), "corr": round(best, 3)}


def sync_check(comp: Path, bg: Path, alpha: np.ndarray) -> dict:
    """OV-64: is the overlay in step with the picture IN THE COMPOSITE (the file the viewer gets), not only in its own file. Measured inside
    the box the overlay ever covers, so a small label is not lost in the noise of the whole frame."""
    c, g = gray_stream(comp).astype(np.float32), gray_stream(bg).astype(np.float32)
    n = min(len(c), len(g), len(alpha))
    a = alpha[:n, ::2, ::2].astype(np.float32)
    ys, xs = np.where(a.max(axis=0) > 8)
    if not len(ys):
        return {"lag": 0, "stalls": 0, "moving_frames": 0}
    box = (slice(None), slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    a, d = a[box], (c[:n] - g[:n])[box]
    s_ov = np.concatenate([[0.0], np.abs(a[1:] - a[:-1]).mean(axis=(1, 2))])
    s_c = np.concatenate([[0.0], np.abs(d[1:] - d[:-1]).mean(axis=(1, 2))])
    return sync_from_signals(s_ov, s_c)
