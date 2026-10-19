"""Motion accents (MO rules, docs/STORY_ENGINE.md; D-48): drawn motion on top of a shot's camera move, so a still
picture does not read as a slideshow. Episode 1 had 217 shots, every one a push or pan of at most 8 % zoom, no
transition but the cut, and 8 bubbles in 18 minutes (measured 2026-10-19); the creator saw it as slow and not animated.

Every accent is a pure function of the frame number, so a frame renders the same twice:

* camera accents change the crop: ``punch`` (a snap zoom-in on the word, held), ``shake`` (a decaying jolt),
  ``wobble`` (a slow breathing scale over the whole shot, the cheapest "alive" motion);
* picture accents are drawn on the finished frame: ``whip_in`` (the shot enters with a blurred slide over the last
  frame of the shot before), ``flash_in`` (a smash cut: three frames of white), ``pop_text`` (up to four words pop in
  with an overshoot and fade out), ``slam_text`` (large words slam down from twice their size with a jolt).

``timing`` resolves each accent's phrase to frames (``resolve``); ``assemble`` asks ``camera`` for the crop and
``draw`` for the overlay.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CAMERA = {"punch", "shake", "wobble"}
ENTRY = {"whip_in", "flash_in"}  # they belong to the start of their shot
TEXT = {"pop_text", "slam_text"}
PUNCH_IN, PUNCH_ZOOM = 0.12, 0.18  # seconds to reach the punch, extra zoom at strength 1
SHAKE_S, SHAKE_AMP = 0.45, 0.018  # length, amplitude as a share of the frame at strength 1
WOBBLE_PERIOD, WOBBLE_AMP = 2.4, 0.015
WHIP_S, FLASH_FRAMES = 0.22, 3
POP_S, TEXT_FADE = 0.25, 0.15
TEXT_HOLD_BASE, TEXT_HOLD_PER_WORD = 1.5, 0.3  # P-71: a label holds 1.5 s + 0.3 s a word (D-49)
SLAM_S = 0.12


def resolve(accents: list[dict], shot_start: float, shot_end: float, word_start, fps: int) -> list[dict]:
    """Timed accents of one shot. ``word_start(phrase)`` returns the start time of the phrase in this shot or None
    (the accent then lands on the shot's first frame); entry accents always start the shot."""
    out = []
    for a in accents:
        t = shot_start
        if a.get("at") and a["kind"] not in ENTRY:
            w = word_start(a["at"])
            t = shot_start if w is None else min(max(shot_start, w), shot_end)
        out.append({"kind": a["kind"], "start": round(t, 3), "start_frame": int(round(t * fps)),
                    "strength": float(a.get("strength", 0.6)), "text": a.get("text", ""), "pos": a.get("pos", [0.5, 0.2])})
    return out


def text_hold(text: str, kind: str = "pop_text") -> float:
    """Seconds a popped or slammed word stays readable (P-71); a slam holds a little longer."""
    return TEXT_HOLD_BASE + TEXT_HOLD_PER_WORD * max(1, len(text.split())) + (0.6 if kind == "slam_text" else 0.0)


def _ease_out(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def camera(accents: list[dict], f: int, fps: int, f0: int) -> tuple[float, float, float]:
    """(zoom factor >= 1, dx, dy as shares of the frame) the crop gets at frame ``f`` of a shot starting at ``f0``."""
    z, dx, dy = 1.0, 0.0, 0.0
    for a in accents:
        k, s = a["kind"], a["strength"]
        t = (f - a["start_frame"]) / fps
        if k == "punch" and t >= 0:
            z *= 1 + PUNCH_ZOOM * s * _ease_out(t / PUNCH_IN)
        elif k == "shake" and 0 <= t < SHAKE_S:
            decay = (1 - t / SHAKE_S) ** 2
            dx += SHAKE_AMP * s * decay * math.sin(2 * math.pi * 13 * t)
            dy += SHAKE_AMP * s * decay * math.sin(2 * math.pi * 17 * t + 1.3)
        elif k == "wobble":
            u = (f - f0) / fps
            z *= 1 + WOBBLE_AMP * s * (0.5 - 0.5 * math.cos(2 * math.pi * u / WOBBLE_PERIOD))
        elif k == "slam_text" and 0 <= t - SLAM_S < SHAKE_S * 0.6:  # the slam lands with a small jolt
            tt = t - SLAM_S
            dy += SHAKE_AMP * 0.6 * s * (1 - tt / (SHAKE_S * 0.6)) * math.sin(2 * math.pi * 15 * tt)
    return z, dx, dy


def apply_camera(box: tuple[float, float, float, float], W: int, H: int, z: float, dx: float, dy: float):
    """The crop box zoomed by ``z`` about its centre and moved by (dx, dy) shares, kept inside the picture."""
    x0, y0, x1, y1 = box
    cw, ch = (x1 - x0) / z, (y1 - y0) / z
    cx = (x0 + x1) / 2 + dx * (x1 - x0)
    cy = (y0 + y1) / 2 + dy * (y1 - y0)
    cx = min(max(cx, cw / 2), W - cw / 2)
    cy = min(max(cy, ch / 2), H - ch / 2)
    return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


def _font(size: int, path) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), max(8, size))


def _text_layer(frame: Image.Image, text: str, pos, scale: float, alpha: float, font_path, big: bool) -> Image.Image:
    W, H = frame.size
    size = int(H * (0.13 if big else 0.075) * scale)
    if size < 6 or alpha <= 0:
        return frame
    font = _font(size, font_path)
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    l, t, r, b = d.textbbox((0, 0), text, font=font, stroke_width=max(2, size // 12))
    x = pos[0] * W - (r - l) / 2
    y = pos[1] * H - (b - t) / 2
    a = int(255 * alpha)
    d.text((x, y), text, font=font, fill=(255, 248, 232, a), stroke_width=max(2, size // 12), stroke_fill=(24, 20, 26, a))
    return Image.alpha_composite(frame.convert("RGBA"), layer).convert("RGB")


def draw(frame: Image.Image, accents: list[dict], f: int, fps: int, f0: int, f1: int, previous: Image.Image | None,
         font_path) -> Image.Image:
    """Picture accents on a finished frame of a shot spanning frames f0..f1 (``previous`` = the last frame before)."""
    W, H = frame.size
    for a in accents:
        k, s = a["kind"], a["strength"]
        t = (f - a["start_frame"]) / fps
        if k == "whip_in" and previous is not None and 0 <= t < WHIP_S:
            u = _ease_out(t / WHIP_S)
            blur = max(1, int(W * 0.03 * (1 - u) * (0.5 + s)))
            off = int(W * (1 - u))
            canvas = Image.new("RGB", frame.size)
            canvas.paste(previous.filter(ImageFilter.BoxBlur(blur)), (off - W, 0))  # the old shot leaves to the left
            canvas.paste(frame.filter(ImageFilter.BoxBlur(blur)), (off, 0))  # the new one arrives from the right
            frame = canvas
        elif k == "flash_in" and 0 <= f - f0 < FLASH_FRAMES:
            white = Image.new("RGB", frame.size, (255, 252, 244))
            frame = Image.blend(white, frame, (f - f0 + 1) / (FLASH_FRAMES + 1))
        elif k in TEXT and a["text"]:
            end = min((f1 - a["start_frame"]) / fps, text_hold(a["text"], k))
            if not 0 <= t < end:
                continue
            fade = min(1.0, (end - t) / TEXT_FADE)
            if k == "pop_text":
                u = t / POP_S
                scale = 0.6 + 0.52 * _ease_out(u) if u < 1 else 1.12 - 0.12 * min(1.0, (t - POP_S) / 0.1)
                frame = _text_layer(frame, a["text"], a["pos"], scale, fade, font_path, big=False)
            else:
                scale = 2.0 - 1.0 * _ease_out(t / SLAM_S)
                frame = _text_layer(frame, a["text"], a["pos"], scale, fade * min(1.0, t / SLAM_S + 0.3), font_path, big=True)
    return frame


def counts(shots: list[dict]) -> dict:
    """How many shots carry each accent kind (for the motion report)."""
    c: dict = {}
    for s in shots:
        for a in s.get("accents", []):
            c[a["kind"]] = c.get(a["kind"], 0) + 1
    return c
