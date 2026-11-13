"""House-style graphic cards (AS-12, docs/SCENE_REUSE_RULES.md): the phone screen and the number cards of a cut, drawn in the channel's
drawn world (paper ground, ink outlines that wobble like a hand line, the hand font ComicNeue, palette tokens only), never a flat UI
mock-up. The Gemini review of the minute-1 test (2026-11-07) named the flat "14% No service" and "8,000,000 people / fire: 0" cards as
breaking the style; the creator chose the free in-code fix (answer 6a, 22:23 UTC).

    card(spec, (1280, 704)) -> PIL.Image      spec: {"kind": "phone", "battery": 14, "status": "No service"}
                                                     {"kind": "stat", "lines": ["8,000,000 people", "fire: 0"]}
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf"
PALETTE = json.loads((ROOT / "explainer_engine" / "design" / "palette.json").read_text(encoding="utf-8"))["tokens"]
KINDS = ("phone", "stat")


def _rgb(token: str) -> tuple[int, int, int]:
    h = PALETTE[token]["hex"].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _paper(size, seed: int) -> Image.Image:
    """Paper ground: the palette's paper with a soft grain and a gentle darker edge, so the card sits in the drawn world."""
    random.seed(seed)
    base = Image.new("RGB", size, _rgb("paper"))
    ink = Image.new("RGB", size, _rgb("ink"))
    grain = Image.effect_noise(size, 18).convert("L").filter(ImageFilter.GaussianBlur(0.8))
    base = Image.composite(ink, base, grain.point(lambda v: int(max(0, v - 128) * 0.12)))
    edge = Image.radial_gradient("L").resize(size).point(lambda v: int(max(0, v - 120) * 0.45))
    return Image.composite(ink, base, edge)


def _wobble(d: ImageDraw.ImageDraw, box, radius: int, seed: int, width: int = 7, colour: str = "ink") -> None:
    """A rounded rectangle outlined by a hand-drawn line: the path wobbles a few pixels, drawn twice slightly apart."""
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    pts = []
    for side in range(4):
        for i in range(24):
            t = i / 24
            x, y = [(x0 + (x1 - x0) * t, y0), (x1, y0 + (y1 - y0) * t), (x1 - (x1 - x0) * t, y1), (x0, y1 - (y1 - y0) * t)][side]
            pts.append((x + rnd.uniform(-2.5, 2.5), y + rnd.uniform(-2.5, 2.5)))
    for off in (0, 2):
        d.line([(x + off, y + off * 0.5) for x, y in pts + pts[:1]], fill=_rgb(colour), width=width - off * 2, joint="curve")


def card(spec: dict, size=(1280, 704), seed: int = 7) -> Image.Image:
    if spec.get("kind") not in KINDS:
        raise ValueError(f"card kind must be one of {KINDS}")
    w, h = size
    img = _paper(size, seed)
    d = ImageDraw.Draw(img)
    big = ImageFont.truetype(str(FONT), int(h * 0.12))
    mid = ImageFont.truetype(str(FONT), int(h * 0.065))
    if spec["kind"] == "phone":
        pw, ph = int(h * 0.48), int(h * 0.84)
        box = ((w - pw) // 2, (h - ph) // 2, (w + pw) // 2, (h + ph) // 2)
        d.rounded_rectangle(box, 36, fill=_rgb("ink"))
        _wobble(d, box, 36, seed)
        cx = w // 2
        bw, bh = int(pw * 0.5), int(ph * 0.12)
        by = box[1] + int(ph * 0.28)
        bat = (cx - bw // 2, by, cx + bw // 2, by + bh)
        _wobble(d, bat, 10, seed + 1, width=6, colour="paper")
        d.rectangle((bat[2] + 4, by + bh // 3, bat[2] + 14, by + 2 * bh // 3), fill=_rgb("paper"))
        lvl = max(0.04, min(1.0, float(spec.get("battery", 14)) / 100))
        d.rectangle((bat[0] + 9, bat[1] + 9, bat[0] + 9 + int((bw - 18) * lvl), bat[3] - 9), fill=_rgb("answer_coral"))
        d.text((cx, by + bh + int(ph * 0.13)), f"{int(spec.get('battery', 14))}%", font=big, fill=_rgb("paper"), anchor="mm")
        d.text((cx, by + bh + int(ph * 0.30)), str(spec.get("status", "No service")), font=mid, fill=_rgb("paper"), anchor="mm")
    else:
        lines = spec.get("lines", [])
        y = h // 2 - (len(lines) - 1) * int(h * 0.09)
        for k, line in enumerate(lines):
            col = _rgb("answer_coral") if k == len(lines) - 1 else _rgb("ink")
            d.text((w // 2 + int(6 * math.sin(k)), y), line, font=big, fill=col, anchor="mm")
            y += int(h * 0.18)
    return img


def write(spec: dict, path, size=(1280, 704)) -> Path:
    path = Path(path)
    card(spec, size).save(path)
    return path
