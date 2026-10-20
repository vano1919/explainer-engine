"""Period cards (ED-09) and data visuals (ED-10), drawn by our own code as overlays on the finished frame: free, hand-drawn
look (the bubbles' fonts), no stock chart template. Every number a visual shows is written in the script and traces to a claim.

card:   {"title": "WEEK 1", "line": "Can knowledge replace calluses?"}  - drawn over the first seconds of a period
visual: {"id", "segment", "at": "phrase", "kind": "calc"|"bars"|"timeline", "hold": 3..7, "claim": "C-08", ...}
All functions take the frame (PIL RGB) and return it drawn on; time-dependent parts take ``t`` seconds since the start."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from explainer_engine.finish import bubbles as BUB

CREAM, INK, ACCENT, ACCENT2 = (244, 232, 204), (38, 30, 24), (232, 156, 62), (110, 190, 170)
CARD_IN, CARD_HOLD, CARD_OUT = 0.5, 2.6, 0.9
BUILD = 0.8
MIN_HOLD, MAX_HOLD = 3.0, 7.0
MAX_MARKS = 6
TITLES = {"day1": "DAY 1", "week1": "WEEK 1", "month1": "MONTH 1", "year1": "YEAR 1", "year10": "YEAR 10", "year100": "YEAR 100",
          "compare": "THE REAL RECORD"}


def font(size: int, shout: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(BUB.SHOUT_FONT if shout else BUB.FONT), max(8, int(size)))


def ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def _text_w(d: ImageDraw.ImageDraw, s: str, f) -> int:
    return int(d.textlength(s, font=f))


def _shadow_text(d, xy, s, f, fill, h, anchor="la"):
    off = max(2, h // 300)
    d.text((xy[0] + off, xy[1] + off), s, font=f, fill=(0, 0, 0), anchor=anchor)
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


# --- period card -----------------------------------------------------------------------------------------------------

def card_length() -> float:
    return CARD_IN + CARD_HOLD + CARD_OUT


def card(frame: Image.Image, spec: dict, t: float, dots: int, lit: int) -> Image.Image:
    """The picture dims, the title rises, the line under it, a row of dots shows where the period sits in the story."""
    W, H = frame.size
    a = min(ease(t / CARD_IN), ease((card_length() - t) / CARD_OUT)) if 0 <= t <= card_length() else 0.0
    if a <= 0:
        return frame
    out = ImageEnhance.Brightness(frame).enhance(1 - 0.58 * a)
    d = ImageDraw.Draw(out, "RGBA")
    rise = int(H * 0.03 * (1 - ease(t / CARD_IN)))
    ft, fl = font(H * 0.15, True), font(H * 0.05)
    title = spec["title"]
    tw = _text_w(d, title, ft)
    col = tuple(int(c) for c in CREAM)
    _shadow_text(d, ((W - tw) // 2, int(H * 0.30) + rise), title, ft, col + (int(255 * a),), H)
    line = spec.get("line") or ""
    if line:
        lw = _text_w(d, line, fl)
        _shadow_text(d, ((W - lw) // 2, int(H * 0.52) + rise), line, fl, ACCENT + (int(255 * a),), H)
    gap, r = int(H * 0.045), int(H * 0.011)
    x0 = W // 2 - (dots - 1) * gap // 2
    y = int(H * 0.68)
    d.line([(x0, y), (x0 + (dots - 1) * gap, y)], fill=CREAM + (int(110 * a),), width=max(2, H // 400))
    for i in range(dots):
        on = i <= lit
        rr = r * (1.5 if i == lit else 1.0)
        d.ellipse([x0 + i * gap - rr, y - rr, x0 + i * gap + rr, y + rr],
                  fill=(ACCENT if on else (90, 80, 70)) + (int(255 * a),), outline=CREAM + (int(200 * a),), width=max(1, H // 500))
    return out


# --- data visuals ----------------------------------------------------------------------------------------------------

def _panel(frame: Image.Image, g: dict, a: float):
    """A dark parchment panel on one side of the frame; returns (image, draw, box)."""
    W, H = frame.size
    side = g.get("side", "right")
    pw, ph = int(W * 0.46), int(H * (0.50 if g["kind"] != "timeline" else 0.34))
    x0 = int(W * 0.52) if side == "right" else int(W * 0.02) if side == "left" else (W - pw) // 2
    y0 = (H - ph) // 2 - int(H * 0.03) + int(H * 0.04 * (1 - a))
    lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rad = H // 40
    d.rounded_rectangle([x0, y0, x0 + pw, y0 + ph], rad, fill=(34, 27, 22, int(215 * a)), outline=CREAM + (int(230 * a),),
                        width=max(2, H // 280))
    return lay, d, (x0, y0, pw, ph)


def _fit(d, s: str, size: float, maxw: int, shout=False):
    f = font(size, shout)
    while _text_w(d, s, f) > maxw and size > 10:
        size *= 0.93
        f = font(size, shout)
    return f


def visual(frame: Image.Image, g: dict, t: float, hold: float) -> Image.Image:
    """Draw one visual at ``t`` seconds after it starts; it builds in BUILD seconds and leaves in the last 0.4 s."""
    W, H = frame.size
    a = min(ease(t / 0.35), ease((hold - t) / 0.4))
    if a <= 0:
        return frame
    lay, d, (x0, y0, pw, ph) = _panel(frame, g, a)
    pad = int(pw * 0.06)
    inner = pw - 2 * pad
    k = ease((t - 0.15) / BUILD)
    ink = CREAM + (int(255 * a),)
    title = g.get("title")
    ty = y0 + int(ph * 0.07)
    if title:
        f = _fit(d, title, H * 0.052, inner)
        d.text((x0 + pad, ty), title, font=f, fill=ACCENT + (int(255 * a),))
        ty += int(H * 0.07)
    if g["kind"] == "calc":
        lines = g["lines"]
        step = (ph - (ty - y0) - int(ph * 0.08)) / max(1, len(lines))
        for i, s in enumerate(lines):
            last = i == len(lines) - 1
            appear = ease((t - 0.2 - i * 0.55) / 0.35)
            if appear <= 0:
                continue
            f = _fit(d, s, H * (0.085 if last else 0.062), inner, shout=last)
            col = (ACCENT2 if last else CREAM) + (int(255 * a * appear),)
            d.text((x0 + pad, ty + i * step + int((1 - appear) * H * 0.015)), s, font=f, fill=col)
    elif g["kind"] == "bars":
        bars = g["bars"][:MAX_MARKS]
        top = max(b["value"] for b in bars)
        area_h = ph - (ty - y0) - int(ph * 0.06)
        row = area_h / len(bars)
        for i, b in enumerate(bars):
            y = ty + i * row
            lab = _fit(d, b["label"], H * 0.04, inner)
            d.text((x0 + pad, y), b["label"], font=lab, fill=ink)
            bx, by, bh = x0 + pad, y + int(H * 0.05), int(row * 0.34)
            full = inner * 0.72 * b["value"] / top
            w = max(4, int(full * k))
            d.rounded_rectangle([bx, by, bx + w, by + bh], bh // 3, fill=(ACCENT if i % 2 == 0 else ACCENT2) + (int(255 * a),))
            if k > 0.55:
                tf = font(H * 0.044)
                d.text((bx + int(full) + int(H * 0.012), by + bh // 2), b["text"], font=tf, fill=ink, anchor="lm")
    else:  # timeline
        span = g["span"]
        yb = y0 + int(ph * 0.62)
        xa, xb = x0 + pad, x0 + pw - pad
        d.line([(xa, yb), (xa + int((xb - xa) * k), yb)], fill=CREAM + (int(255 * a),), width=max(3, H // 220))
        for m in g["marks"][:MAX_MARKS]:
            x = xa + int((xb - xa) * m["at"])
            if m["at"] <= k + 1e-6:
                d.ellipse([x - H // 90, yb - H // 90, x + H // 90, yb + H // 90], fill=ACCENT + (int(255 * a),))
                f = _fit(d, m["label"], H * 0.04, int(inner * 0.42))
                al = "ra" if m["at"] > 0.6 else "la"
                d.text((x, yb - int(H * 0.085)), m["label"], font=f, fill=ink, anchor=al)
        sf = _fit(d, span, H * 0.07, inner, shout=True)
        d.text(((xa + xb) // 2, y0 + int(ph * 0.82)), span, font=sf, fill=ACCENT2 + (int(255 * a * ease((t - 0.5) / 0.4)),), anchor="mm")
    return Image.alpha_composite(frame.convert("RGBA"), lay).convert("RGB")


def check_visual(g: dict) -> list[str]:
    """Problems of one visual spec (PV-31): the numbers must be there and traceable."""
    out = []
    if not g.get("claim"):
        out.append("no claim id: every number on screen must trace to the claim map")
    hold = float(g.get("hold", 4.0))
    if not MIN_HOLD <= hold <= MAX_HOLD:
        out.append(f"hold {hold} s; must be {MIN_HOLD}-{MAX_HOLD} s")
    kind = g.get("kind")
    if kind == "calc" and not (2 <= len(g.get("lines", [])) <= 4):
        out.append("a calculation has 2-4 lines")
    elif kind == "bars" and not (2 <= len(g.get("bars", [])) <= 4 and all(isinstance(b.get("value"), (int, float)) and b["value"] > 0 for b in g["bars"])):
        out.append("bars need 2-4 bars with positive values")
    elif kind == "timeline" and not (g.get("span") and 2 <= len(g.get("marks", [])) <= MAX_MARKS):
        out.append("a timeline needs a span text and 2-6 marks")
    elif kind not in ("calc", "bars", "timeline"):
        out.append(f"unknown kind {kind!r}")
    return out
