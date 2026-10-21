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

from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf"
SHOUT_FONT = ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"
FILL = (244, 236, 216, 255)
INK = (30, 26, 22, 255)
POP_S, OUT_S = 0.18, 0.15
MARGIN = 0.035  # of the frame, a bubble never touches the edge
MAX_CHARS = int(SR.T("BP-84", "bubble_chars_per_line"))  # per line
MAX_WORDS = int(SR.T("BP-38", "max_words"))  # BP-84: a bubble is an accent of BP-38's words, never a line (RX-01)


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


def head_box(mouth: tuple[float, float], frame: tuple[int, int]) -> tuple[float, float, float, float]:
    """The face around a mouth point (frame pixels): what a bubble or an effect must never cover."""
    (sx, sy), (FW, FH) = mouth, frame
    return (sx - 0.075 * FW, sy - 0.24 * FH, sx + 0.075 * FW, sy + 0.04 * FH)


def overlaps(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def layout(speaker: tuple[float, float], size: tuple[int, int], frame: tuple[int, int], side: str | None = None,
           lift: float = 0.16, avoid: list[tuple[int, int, int, int]] = (),
           faces: list[tuple[float, float, float, float]] = ()) -> tuple[int, int]:
    """Top-left corner of a bubble for a speaker point (frame pixels): above the speaker, toward the frame centre (or
    ``side``), inside the margins, clear of every face (the speaker's and ``faces``, the other heroes' head boxes) and of
    the ``avoid`` boxes (bubbles already on screen). Faces come first: a bubble may touch another bubble before a face
    (the creator, 2026-10-20: a bubble never sits on a face)."""
    (sx, sy), (w, h), (FW, FH) = speaker, size, frame
    toward = side or ("right" if sx < FW / 2 else "left")
    sign = 1 if toward == "right" else -1
    m = MARGIN * FH

    def place(dx: float, dy: float) -> tuple[int, int]:
        cx, cy = sx + sign * dx * FW, sy - dy * FH - h / 2
        return int(min(max(cx - w / 2, m), FW - m - w)), int(min(max(cy - h / 2, m), FH - m - h))

    head = head_box(speaker, frame)  # the speaker's face stays visible

    def hits(x: int, y: int, boxes) -> bool:
        return any(x < b[2] + m and b[0] < x + w + m and y < b[3] + m / 2 and b[1] < y + h + m / 2 for b in boxes)

    cands = [place(0.10, lift), place(0.22, lift), place(-0.10, lift), place(0.30, lift - 0.10), place(0.30, 0.0),
             place(-0.30, 0.0), place(0.10, lift + 0.12), place(0.30, lift + 0.12), place(0.42, lift + 0.20),
             place(-0.42, lift + 0.20), place(0.0, lift + 0.30), place(0.45, -0.25), place(-0.45, -0.25)]
    cands += [place(dx / 100, dy) for dy in (lift, lift - 0.10, 0.0, -0.15, -0.25) for dx in range(-45, 46, 3)]  # a finer sweep, last
    others = [((f[0] + f[2]) / 2, (f[1] + f[3]) / 2) for f in faces if not overlaps(f, head)]

    def nearer_other(c) -> bool:  # a bubble closer to another face than to its speaker reads as his (the creator 2026-10-21)
        cx, cy = c[0] + w / 2, c[1] + h / 2
        return any(math.dist((cx, cy), o) < math.dist((cx, cy), (sx, sy - 0.1 * FH)) for o in others)

    cands = sorted(cands, key=nearer_other)  # stable: the old order among the bubbles that read as the speaker's
    for boxes in ([head, *faces, *avoid], [head, *faces], list(avoid)):  # faces and bubbles; else faces; else bubbles
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
                 kind: str = "speech", side: str | None = None, avoid: list[tuple[int, int, int, int]] = (),
                 faces: list[tuple[float, float, float, float]] = ()):
        self.start, self.end, self.text = start, end, text
        body, (w, h) = draw_bubble(text, frame[1], kind)
        x, y = layout(speaker_px, (w, h), frame, side, avoid=avoid, faces=faces)
        self.box = (x, y, x + w, y + h)
        self.covers_face = any(overlaps(self.box, f) for f in [head_box(speaker_px, frame), *faces])  # BUBBLE-4
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
    """Findings for bubble specs: a line at most MAX_WORDS words (BP-84), on screen long enough to read: BP-27's hold,
    max(hold_min_s, s_per_word x words), which superseded the old max(1.4, 0.3 n). Each takes its rule's severity."""
    out = []
    hold_min, per_word = SR.T("BP-27", "hold_min_s"), SR.T("BP-27", "s_per_word")
    for r in rows:
        n = len(r["text"].split())
        if n > MAX_WORDS:
            out.append({"rule": "BUBBLE-1", "severity": SR.rule("BP-84").get("severity", "REVIEW"),
                        "detail": f"{r['text'][:40]!r}: {n} words > {MAX_WORDS} (BP-84)"})
        need = max(hold_min, per_word * n)
        if r["end"] - r["start"] < need - 1e-6:
            out.append({"rule": "BUBBLE-2", "severity": SR.rule("BP-27").get("severity", "REVIEW"),
                        "detail": f"{r['text'][:40]!r}: on screen {r['end'] - r['start']:.2f} s < {need:.2f} s (BP-27)"})
    return out
