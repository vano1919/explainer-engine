"""Faces of the J5 dialogue test: blinks, brows and a mouth that follows the words (free, no model, CPU).

The sheets have no mouth, eyelid or brow variants, so every state is drawn on the card's own pixels at render time:

- a **blink** is a skin-coloured lid that slides down over the eye (the colour is sampled from the graded card just below the eye, so the
  fire's light and the face shadow carry over) with a dark lash line at its edge;
- a **brow** is a small vertical displacement (a Gaussian bump) around the brow, up for a listener, down and in for a speaker who is stern;
- a **mouth** follows the cues of Rhubarb Lip Sync (MIT, github.com/DanielSWolf/rhubarb-lip-sync, shapes A-H and X from the audio): the jaw
  drops (the part of the face below the mouth line is displaced, the beard goes with it) and a dark opening is drawn between the lips.

Everything is a function of the clip time ``T`` only, like the rest of ``j5_background``. Features are measured once on the sheets (pixels of
the 1280-px ``*.cut.png``); ``setup`` maps them into the layer through the card's alpha box. Not a lip-sync model: the shapes are the nine
classic mouth positions, which is what hand-drawn 2D animation uses; it reads as speech, it is not a performance.
"""
from __future__ import annotations

import json
import math
import zlib
from pathlib import Path

import numpy as np

# feature boxes in sheet pixels: eyes (cx, cy, w, h of the eye opening), brows (cx, cy, sigma_x, sigma_y), mouth (cx, cy, width, lip band
# height, jaw drop at full opening). Measured on zoomed crops of the cut-outs (2026-11-06).
FEATURES = {
    "B_H2_right34": {"eyes": [(644.0, 122.5, 23, 19), (685.5, 121.0, 20, 17)], "brows": [(641, 103, 15, 6), (688, 101, 12, 6)],
                     "mouth": (672.0, 161.0, 26, 3.0, 4.5), "chin_y": 172, "teeth": True, "skin_dy": 12},
    "B_H1_left34": {"eyes": [(523.5, 157.0, 25, 12), (581.0, 156.0, 34, 13)], "brows": [(525, 141, 18, 6), (576, 139, 24, 6)],
                    "mouth": (548.0, 225.5, 40, 4.5, 5.5), "chin_y": 285, "teeth": False, "skin_dy": 10},
}
# Rhubarb's shapes -> (opening 0..1, width factor): A closed (M, B, P), B teeth, C open, D wide, E round, F pucker, G F/V, H L, X rest
SHAPES = {"A": (0.0, 1.0), "B": (0.18, 1.0), "C": (0.50, 0.95), "D": (0.90, 1.05), "E": (0.55, 0.72), "F": (0.35, 0.55),
          "G": (0.14, 1.0), "H": (0.42, 0.90), "X": (0.0, 1.0)}
INTERIOR = np.array([0.34, 0.10, 0.10], np.float32)      # the mouth's inside (the roof of it) at the card's normal brightness
TONGUE = np.array([0.62, 0.25, 0.23], np.float32)        # the lower part of the opening, lighter
TEETH = np.array([0.88, 0.84, 0.76], np.float32)
LASH = np.array([0.09, 0.05, 0.05], np.float32)
BLINK_S = 0.20                                           # a blink lasts about 0.2 s


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def blink_times(seed: str, start: float, duration: float) -> list[float]:
    """Start times of the blinks of one figure in one shot: the first 0.8-1.6 s in, then every 1.5-2.6 s (deterministic per seed)."""
    rng = np.random.default_rng(zlib.crc32(seed.encode()))
    t, out = start + rng.uniform(0.8, 1.6), []
    while t < start + duration:
        out.append(float(t))
        t += rng.uniform(1.5, 2.6)
    return out


def closure(T: float, blinks: list[float]) -> float:
    """0 = open, 1 = shut: down fast (35 % of the blink), up slower."""
    for b in blinks:
        u = (T - b) / BLINK_S
        if 0 <= u <= 1:
            return float(smooth(u / 0.35) if u < 0.35 else 1 - smooth((u - 0.35) / 0.65))
    return 0.0


def load_cues(path: Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["mouthCues"]


def mouth_state(T: float, line: dict | None) -> tuple[float, float]:
    """(opening, width factor) at clip time T for a line = {"start": s, "cues": [...]}; eased over the first 55 ms of each cue."""
    if not line:
        return 0.0, 1.0
    t = T - line["start"]
    cues = line["cues"]
    if t < -0.05 or t > cues[-1]["end"] + 0.1:
        return 0.0, 1.0
    prev, cur = (0.0, 1.0), (0.0, 1.0)
    for i, c in enumerate(cues):
        if c["start"] <= t < c["end"]:
            cur = SHAPES[c["value"]]
            prev = SHAPES[cues[i - 1]["value"]] if i else (0.0, 1.0)
            u = float(smooth((t - c["start"]) / 0.055))
            return prev[0] + (cur[0] - prev[0]) * u, prev[1] + (cur[1] - prev[1]) * u
    return 0.0, 1.0


def setup(pm: np.ndarray, sheet: str, mapper) -> dict | None:
    """Map the sheet's features into this layer with ``mapper(x, y) -> (X, Y)`` (the card's real projection: sheet pixel -> frame pixel,
    from the Blender job's geometry), and sample the card's own colours near the eyes and mouth (they are graded already)."""
    feat = FEATURES.get(sheet)
    if not feat:
        return None
    mp = mapper
    k = float(mp(1.0, 0.0)[0] - mp(0.0, 0.0)[0])                     # layer pixels per sheet pixel
    rgb = pm[..., :3] / np.maximum(pm[..., 3:4], 1e-3)

    def skin(x, y, w=7, h=4):
        px, py = int(x), int(y)
        patch = rgb[py - h:py + h, px - w:px + w].reshape(-1, 3)
        return np.median(patch, axis=0).astype(np.float32)

    eyes = []
    for cx, cy, w, h in feat["eyes"]:
        x, y = mp(cx, cy)
        eyes.append({"x": x, "y": y, "w": w * k, "h": h * k, "skin": skin(x, y + (h / 2 + feat["skin_dy"] * 0.55) * k)})
    mx, my = mp(feat["mouth"][0], feat["mouth"][1])
    skin_mouth = skin(mx, my - 9 * k, 12, 3)
    luma = float(skin_mouth @ np.array([0.3, 0.59, 0.11], np.float32))
    for e in eyes:
        e["lash"] = LASH * min(1.2, max(0.5, luma / 0.62))
    return {"k": k, "eyes": eyes, "brows": [(*mp(bx, by), sx * k, sy * k) for bx, by, sx, sy in feat["brows"]],
            "mouth": {"x": mx, "y": my, "w": feat["mouth"][2] * k, "line": feat["mouth"][3] * k, "jaw": feat["mouth"][4] * k,
                      "interior": INTERIOR * min(1.3, max(0.55, luma / 0.62)), "tongue": TONGUE * min(1.3, max(0.55, luma / 0.62)),
                      "teeth_c": TEETH * min(1.2, max(0.6, luma / 0.62)), "teeth": feat["teeth"], "chin": mp(0.0, feat["chin_y"])[1], "lash": LASH * min(1.2, max(0.5, luma / 0.62))},
            "skin_luma": luma}


def displacement(face: dict, gx: np.ndarray, gy: np.ndarray, T: float, op: float, brow: float) -> tuple[np.ndarray, np.ndarray]:
    """Extra displacement fields (px, content moves by +d) on the crop grid: the jaw below the mouth line and the brows.
    ``op`` is the mouth opening 0..1, ``brow`` the brow lift (+ up, - down) in sheet-scale units of the card."""
    k = face["k"]
    dx = np.zeros_like(gx)
    dy = np.zeros_like(gx)
    m = face["mouth"]
    if op > 0.01:
        # only the jaw moves: the weight rises below the lips, is full over the chin and is gone a chin's height below it (neck, collar,
        # armour stay), and it fades sideways within about one mouth width
        span = max(8 * k, m["chin"] - m["y"])
        below = smooth((gy - (m["y"] + m["line"] * 0.8)) / (3.5 * k)) * (1 - smooth((gy - m["chin"]) / (0.5 * span)))
        side = np.exp(-(((gx - m["x"]) / (m["w"] * 1.25)) ** 2))
        dy += m["jaw"] * op * below * side
    if abs(brow) > 1e-3:
        for bx, by, sx, sy in face["brows"]:
            dy -= brow * 2.2 * k * np.exp(-(((gx - bx) / sx) ** 2 + ((gy - by) / sy) ** 2))
    return dx, dy


def _soft_ellipse(shape, cx, cy, ax, ay, feather):
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - cx) / max(ax, 0.3)) ** 2 + ((yy - cy) / max(ay, 0.3)) ** 2)
    return np.clip((1.0 - r) * max(ax, ay) / feather + 0.5, 0, 1).astype(np.float32)


def paint(out: np.ndarray, face: dict, box: tuple[int, int, int, int], T: float, close: float, op: float, wf: float,
          off: tuple[float, float] = (0.0, 0.0)) -> None:
    """Draw the blink lids and the mouth opening into the (already warped) crop ``out`` in place. ``off`` = the idle displacement at the face."""
    x0, y0 = box[0], box[1]
    h, w = out.shape[:2]
    k = face["k"]
    ox, oy = off
    if close > 0.02:
        for e in face["eyes"]:
            cx, cy = e["x"] - x0 + ox, e["y"] - y0 + oy
            ax, ay = e["w"] / 2 * 1.28, e["h"] / 2 * 1.35
            top = cy - ay
            lid_y = top + close * 2 * ay                                               # the lid's edge, from the top to the bottom of the eye
            m = _soft_ellipse((h, w), cx, cy, ax, ay, 1.2 * k)
            yy = np.arange(h, dtype=np.float32)[:, None]
            cover = m * np.clip((lid_y - yy) / (1.2 * k) + 0.5, 0, 1)
            a = out[..., 3:4]
            skin = e["skin"] * a
            out[..., :3] = out[..., :3] * (1 - cover[..., None]) + skin * cover[..., None]
            # the lash line along the lid's edge: a shallow arc, dark, 2 px at 2560
            xx = np.arange(w, dtype=np.float32)[None, :]
            arc = lid_y + 0.22 * ay * (1 - ((xx - cx) / ax) ** 2) * (0.4 + 0.6 * close)
            line = np.exp(-(((yy - arc) / (1.1 * k)) ** 2)) * np.clip(1 - np.abs((xx - cx) / ax), 0, 1) ** 0.5 * (np.abs(xx - cx) < ax)
            line = (line * (0.35 + 0.65 * close))[..., None]
            out[..., :3] = out[..., :3] * (1 - line) + e["lash"] * a * line
    if op > 0.02:
        m = face["mouth"]
        cx, cy = m["x"] - x0 + ox, m["y"] - y0 + oy
        gap = m["jaw"] * op
        ax, ay = m["w"] / 2 * wf, gap / 2 + m["line"] * 0.45
        ey = cy + gap / 2
        ring = _soft_ellipse((h, w), cx, ey, ax + 1.3 * k, ay + 1.3 * k, 1.0 * k)
        inner = _soft_ellipse((h, w), cx, ey, ax, ay, 0.9 * k)
        a = out[..., 3:4]
        yy = np.arange(h, dtype=np.float32)[:, None]
        v = np.clip((yy - (ey - ay)) / max(1e-3, 2 * ay), 0, 1)                              # 0 at the top of the opening, 1 at the bottom
        inside = m["interior"][None, None, :] * (1 - v[..., None]) + m["tongue"][None, None, :] * v[..., None] * 0.9
        out[..., :3] = out[..., :3] * (1 - ring[..., None]) + m["lash"] * a * ring[..., None]
        out[..., :3] = out[..., :3] * (1 - inner[..., None]) + inside * a * inner[..., None]
        if m["teeth"] and op > 0.28 and wf > 0.8:                                           # a strip of upper teeth along the top of a wide opening
            band = inner * np.clip(1 - (yy - (ey - ay)) / max(1e-3, 0.62 * ay), 0, 1)
            band = band * np.clip((op - 0.28) / 0.25, 0, 1)
            out[..., :3] = out[..., :3] * (1 - band[..., None] * 0.9) + m["teeth_c"] * a * band[..., None] * 0.9
