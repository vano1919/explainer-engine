"""Speech bubbles over a held picture (creator 2026-10-16): one picture carries a short exchange, a bubble pops in on the
speaker with the line they say, then the other answers, instead of a new picture for every sentence.

A bubble is drawn once (cream fill, the look's thick dark ink outline, a tail to the speaker's mouth, Comic Neue Bold, OFL)
and animated per frame: it pops in over POP_S (scale 0.6 -> 1.06 -> 1, ease-out-back) and fades out over OUT_S.
Positions are in picture coordinates (0..1) and are mapped through the shot's crop box at the bubble's start, so a bubble
stays still on screen while the camera drifts slowly underneath. PIL + numpy only.
"""
from __future__ import annotations

import math
import textwrap
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf"
SHOUT_FONT = ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"
FILL = (244, 236, 216, 255)
INK = (30, 26, 22, 255)
POP_S, OUT_S = 0.18, 0.15
MARGIN = 0.035  # of the frame, a bubble never touches the edge
MAX_CHARS = 26  # per line
MAX_WORDS = 14  # a bubble is a line, not a paragraph (check_bubbles)


@lru_cache(maxsize=16)
def font(size: int, shout: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(SHOUT_FONT if shout else FONT), size)


def wrap(text: str, width: int = MAX_CHARS) -> list[str]:
    """Even lines: a sentence break is a line break when both parts fit; otherwise the narrowest width that keeps the
    line count wins (no one-word last line)."""
    parts = [p.strip() for p in text.replace(". ", ".|").replace("? ", "?|").replace("! ", "!|").split("|") if p.strip()]
    if 1 < len(parts) <= 3 and all(len(p) <= width for p in parts):
        return parts
    best = textwrap.wrap(text, width) or [""]
    for w in range(width, 9, -1):
        cand = textwrap.wrap(text, w)
        if len(cand) > len(best):
            break
        best = cand
    return best


def draw_bubble(text: str, frame_h: int, kind: str = "speech") -> tuple[Image.Image, tuple[float, float]]:
    """The bubble body (no tail) as RGBA and its size. Text size scales with the frame height (44 px at 1080p)."""
    shout = kind == "shout"
    size = round(frame_h * (0.046 if shout else 0.041))
    f = font(size, shout)
    lines = wrap(text.upper() if shout else text)
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    widths = [d0.textlength(line, font=f) for line in lines]
    lh = round(size * 1.18)
    tw, th = max(widths), lh * len(lines)
    pad_x, pad_y = size * 0.95, size * 0.62
    ow = max(4, round(frame_h * 0.0055))
    W, H = int(tw + 2 * pad_x + 2 * ow), int(th + 2 * pad_y + 2 * ow)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = min(H / 2, size * 1.6)
    d.rounded_rectangle([ow, ow, W - ow - 1, H - ow - 1], radius=r, fill=FILL, outline=INK, width=ow)
    y = pad_y + ow
    for line, w in zip(lines, widths):
        d.text(((W - w) / 2, y), line, font=f, fill=INK)
        y += lh
    return im, (W, H)


def layout(speaker: tuple[float, float], size: tuple[int, int], frame: tuple[int, int], side: str | None = None,
           lift: float = 0.16, avoid: list[tuple[int, int, int, int]] = ()) -> tuple[int, int]:
    """Top-left corner of a bubble for a speaker point (frame pixels): above the speaker, toward the frame centre (or
    ``side``), inside the margins, and clear of the ``avoid`` boxes (bubbles already on screen) when any candidate is."""
    (sx, sy), (w, h), (FW, FH) = speaker, size, frame
    toward = side or ("right" if sx < FW / 2 else "left")
    sign = 1 if toward == "right" else -1
    m = MARGIN * FH

    def place(dx: float, dy: float) -> tuple[int, int]:
        cx, cy = sx + sign * dx * FW, sy - dy * FH - h / 2
        return int(min(max(cx - w / 2, m), FW - m - w)), int(min(max(cy - h / 2, m), FH - m - h))

    head = (sx - 0.075 * FW, sy - 0.24 * FH, sx + 0.075 * FW, sy + 0.04 * FH)  # the speaker's face stays visible

    def hits(x: int, y: int, boxes) -> bool:
        return any(x < b[2] + m and b[0] < x + w + m and y < b[3] + m / 2 and b[1] < y + h + m / 2 for b in boxes)

    cands = [place(0.10, lift), place(0.22, lift), place(-0.10, lift), place(0.30, lift - 0.10), place(0.30, 0.0),
             place(-0.30, 0.0), place(0.10, lift + 0.12), place(0.30, lift + 0.12)]
    for boxes in ([head, *avoid], list(avoid)):  # clear of the face and other bubbles; else at least of the bubbles
        free = next((c for c in cands if not hits(*c, boxes)), None)
        if free:
            return free
    return cands[0]


def tail_polygon(box: tuple[int, int, int, int], tip: tuple[float, float]) -> list[tuple[float, float]]:
    """A tapered tail from the bubble edge nearest the speaker to ``tip`` (frame pixels)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx = min(max(tip[0], x0 + (x1 - x0) * 0.25), x0 + (x1 - x0) * 0.75)
    by = y1 if tip[1] > cy else y0
    half = max(10.0, (y1 - y0) * 0.16)
    return [(bx - half, by - (4 if by == y1 else -4)), (bx + half, by - (4 if by == y1 else -4)), tip]


def ease_out_back(u: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (u - 1) ** 3 + c1 * (u - 1) ** 2


class Bubble:
    """One bubble: text, speaker point (frame pixels), on-screen interval."""

    def __init__(self, text: str, speaker_px: tuple[float, float], start: float, end: float, frame: tuple[int, int],
                 kind: str = "speech", side: str | None = None, avoid: list[tuple[int, int, int, int]] = ()):
        self.start, self.end = start, end
        body, (w, h) = draw_bubble(text, frame[1], kind)
        x, y = layout(speaker_px, (w, h), frame, side, avoid=avoid)
        self.box = (x, y, x + w, y + h)
        ow = max(4, round(frame[1] * 0.0055))
        dist = math.dist((x + w / 2, y + h / 2), speaker_px)
        stop = min(0.10 * frame[1], dist * 0.25)  # the tail stops short of the mouth
        vx, vy = speaker_px[0] - (x + w / 2), speaker_px[1] - (y + h / 2)
        n = math.hypot(vx, vy) or 1.0
        tip = (speaker_px[0] - vx / n * stop, speaker_px[1] - vy / n * stop)
        lx0, ly0 = min(x, tip[0]) - ow * 2, min(y, tip[1]) - ow * 2
        lx1, ly1 = max(x + w, tip[0]) + ow * 2, max(y + h, tip[1]) + ow * 2
        layer = Image.new("RGBA", (int(lx1 - lx0), int(ly1 - ly0)), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        poly = [(px - lx0, py - ly0) for px, py in tail_polygon((x, y, x + w, y + h), tip)]
        d.polygon(poly, fill=INK)  # the tail's ink: a filled outline, then the fill inset by the outline width
        cx, cy = sum(p[0] for p in poly) / 3, sum(p[1] for p in poly) / 3
        k = max(0.0, 1.0 - 2.2 * ow / max(1.0, math.dist(poly[2], ((poly[0][0] + poly[1][0]) / 2, poly[0][1]))))
        d.polygon([(cx + (px - cx) * k, cy + (py - cy) * k) for px, py in poly], fill=FILL)
        layer.alpha_composite(body, (int(x - lx0), int(y - ly0)))
        by = poly[0][1] + (ow * 0.6 if tip[1] > y + h / 2 else -ow * 0.6)  # open the body's outline where the tail joins
        d.line([(poly[0][0] + ow * 1.6, by), (poly[1][0] - ow * 1.6, by)], fill=FILL, width=ow + 2)
        self.layer, self.origin = layer, (int(lx0), int(ly0))
        self.anchor = (tip[0] - lx0, tip[1] - ly0)  # scaling pivots on the tail tip

    def frame_layer(self, t: float):
        """(image, top-left) for time ``t``, or None when the bubble is not on screen."""
        if t < self.start or t >= self.end:
            return None
        u = (t - self.start) / POP_S
        scale = 0.6 + 0.4 * ease_out_back(min(1.0, u)) if u < 1 else 1.0
        alpha = min(1.0, (t - self.start) / (POP_S * 0.6), (self.end - t) / OUT_S)
        im = self.layer
        if abs(scale - 1.0) > 1e-3:
            W, H = im.size
            im = im.resize((max(1, round(W * scale)), max(1, round(H * scale))), Image.BICUBIC)
        if alpha < 0.999:
            a = im.getchannel("A").point(lambda v: int(v * max(alpha, 0.0)))
            im = im.copy()
            im.putalpha(a)
        ax, ay = self.anchor
        return im, (round(self.origin[0] + ax - ax * scale), round(self.origin[1] + ay - ay * scale))


def composite(frame: Image.Image, bubbles: list[Bubble], t: float) -> Image.Image:
    out = None
    for b in bubbles:
        got = b.frame_layer(t)
        if got is None:
            continue
        if out is None:
            out = frame.convert("RGBA")
        im, (x, y) = got
        out.alpha_composite(im, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    return frame if out is None else out.convert("RGB")


def check_bubbles(rows: list[dict]) -> list[dict]:
    """Findings for bubble specs: a line at most MAX_WORDS words, on screen long enough to read (0.3 s per word, >= 1.4 s)."""
    out = []
    for r in rows:
        n = len(r["text"].split())
        if n > MAX_WORDS:
            out.append({"rule": "BUBBLE-1", "severity": "FAIL", "detail": f"{r['text'][:40]!r}: {n} words > {MAX_WORDS}"})
        need = max(1.4, 0.3 * n)
        if r["end"] - r["start"] < need:
            out.append({"rule": "BUBBLE-2", "severity": "FAIL",
                        "detail": f"{r['text'][:40]!r}: on screen {r['end'] - r['start']:.1f} s < {need:.1f} s"})
    return out
