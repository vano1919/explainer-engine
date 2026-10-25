"""Drawn props from the text (the creator 2026-10-21: "visual things that follow logically from the text", not new pictures).

A prop beat (``visual_beats[].kind == "prop"``) pops a cut-out PNG onto the frame. This module makes those cut-outs from line
icons, free and offline: the Tabler outline set (MIT, ``assets/icons/tabler/LICENSE``), vendored as SVG, drawn here by a
small SVG path reader (M L H V C S Q T A Z, absolute and relative: all the set uses) onto a paper sticker in the channel's
ink, so a prop sits in the drawn world like the labels and bubbles do (one ink outline, palette colours, D-55). No cairo, no
network at render time: a frame renders the same twice.

    python -m explainer_engine.design.icons build [names...]   # assets/icons/png/<name>.png (all vendored icons by default)
    python -m explainer_engine.design.icons sheet <out.png>     # every sticker on one contact sheet, to look at
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SVG_DIR = ROOT / "assets" / "icons" / "tabler"
PNG_DIR = ROOT / "assets" / "icons" / "png"
_PALETTE = Path(__file__).resolve().parent / "palette.json"
SIZE = 512  # sticker side in pixels; beats.draw scales it to the frame
ICON_SHARE = 0.62  # the icon's box inside the sticker
STROKE = 2.2  # stroke width in icon units (Tabler draws 2 on a 24 grid; a touch heavier reads at video size)
ACCENTS = {"cash-off": "false_red", "credit-card-off": "false_red", "phone-off": "false_red", "user-off": "false_red",
           "ban": "false_red", "x": "false_red", "flame": "answer_coral", "check": "true_green"}


def _rgb(name: str) -> tuple[int, int, int]:
    h = json.loads(_PALETTE.read_text(encoding="utf-8"))["tokens"][name]["hex"].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


_TOKEN = re.compile(r"[A-Za-z]|-?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def _arc(p0, rx, ry, phi, large, sweep, p1, n=16):
    """Points of an SVG endpoint arc (SVG 1.1 F.6.5), p0 excluded."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    rx, ry = abs(rx), abs(ry)
    c, s = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = c * dx + s * dy, -s * dx + c * dy
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(0.0, num / den)) * (-1 if large == sweep else 1)
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx, cy = c * cx1 - s * cy1 + (p0[0] + p1[0]) / 2, s * cx1 + c * cy1 + (p0[1] + p1[1]) / 2
    a0 = math.atan2((y1 - cy1) / ry, (x1 - cx1) / rx)
    a1 = math.atan2((-y1 - cy1) / ry, (-x1 - cx1) / rx)
    da = a1 - a0
    if sweep and da < 0:
        da += 2 * math.pi
    elif not sweep and da > 0:
        da -= 2 * math.pi
    n = max(4, int(abs(da) / (math.pi / 2) * n))
    out = []
    for i in range(1, n + 1):
        a = a0 + da * i / n
        ex, ey = rx * math.cos(a), ry * math.sin(a)
        out.append((c * ex - s * ey + cx, s * ex + c * ey + cy))
    return out


def _bez(pts, n=12):
    out = []
    for i in range(1, n + 1):
        t = i / n
        if len(pts) == 3:
            (a, b, c) = pts
            out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * b[0] + t * t * c[0],
                        (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * b[1] + t * t * c[1]))
        else:
            (a, b, c, d) = pts
            u = 1 - t
            out.append((u ** 3 * a[0] + 3 * u * u * t * b[0] + 3 * u * t * t * c[0] + t ** 3 * d[0],
                        u ** 3 * a[1] + 3 * u * u * t * b[1] + 3 * u * t * t * c[1] + t ** 3 * d[1]))
    return out


def path_polylines(d: str) -> list[list[tuple[float, float]]]:
    """An SVG path's ``d`` as polylines (closed ones end on their first point)."""
    toks = _TOKEN.findall(d)
    lines, cur, start = [], None, (0.0, 0.0)
    pos, cmd, i = (0.0, 0.0), None, 0
    last_ctrl = None

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "zZ":
                if cur:
                    cur.append(start)
                pos, last_ctrl = start, None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if C == "M":
            pos = (ox + num(), oy + num())
            cur = [pos]
            lines.append(cur)
            start = pos
            cmd = "l" if rel else "L"  # extra pairs after M are line-tos
            last_ctrl = None
            continue
        if cur is None:
            cur = [pos]
            lines.append(cur)
        if C == "L":
            pos = (ox + num(), oy + num())
            cur.append(pos)
            last_ctrl = None
        elif C == "H":
            pos = ((pos[0] if rel else 0.0) + num(), pos[1])
            cur.append(pos)
            last_ctrl = None
        elif C == "V":
            pos = (pos[0], (pos[1] if rel else 0.0) + num())
            cur.append(pos)
            last_ctrl = None
        elif C in "CS":
            if C == "C":
                c1 = (ox + num(), oy + num())
            else:
                c1 = (2 * pos[0] - last_ctrl[0], 2 * pos[1] - last_ctrl[1]) if last_ctrl else pos
            c2 = (ox + num(), oy + num())
            end = (ox + num(), oy + num())
            cur += _bez([pos, c1, c2, end])
            pos, last_ctrl = end, c2
        elif C in "QT":
            if C == "Q":
                c1 = (ox + num(), oy + num())
            else:
                c1 = (2 * pos[0] - last_ctrl[0], 2 * pos[1] - last_ctrl[1]) if last_ctrl else pos
            end = (ox + num(), oy + num())
            cur += _bez([pos, c1, end])
            pos, last_ctrl = end, c1
        elif C == "A":
            rx, ry, phi, large, sweep = num(), num(), num(), int(num()), int(num())
            end = (ox + num(), oy + num())
            cur += _arc(pos, rx, ry, phi, large, sweep, end)
            pos, last_ctrl = end, None
        else:
            raise ValueError(f"svg command {cmd!r} not supported")
    return [ln for ln in lines if len(ln) > 1]


def icon_polylines(name: str) -> list[list[tuple[float, float]]]:
    """The icon's strokes in its 24-unit grid (Tabler's invisible bounding path, stroke="none", is skipped)."""
    svg = (SVG_DIR / f"{name}.svg").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<path([^>]*)/?>", svg):
        attrs = m.group(1)
        if 'stroke="none"' in attrs:
            continue
        d = re.search(r'\sd="([^"]+)"', attrs)
        if d:
            out += path_polylines(d.group(1))
    return out


def available() -> list[str]:
    return sorted(p.stem for p in SVG_DIR.glob("*.svg"))


def _cut(lines, share: float):
    """The first ``share`` of the strokes' total length: the icon as a hand draws it (the strokes in their own order)."""
    if share >= 1:
        return lines
    lens = [sum(math.dist(a, b) for a, b in zip(ln, ln[1:])) for ln in lines]
    left, out = share * sum(lens), []
    for ln, n in zip(lines, lens):
        if left <= 0:
            break
        if n <= left:
            out.append(ln)
            left -= n
            continue
        part = [ln[0]]
        for a, b in zip(ln, ln[1:]):
            seg = math.dist(a, b)
            if seg >= left:
                u = left / seg if seg else 1.0
                part.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
                break
            part.append(b)
            left -= seg
        out.append(part)
        break
    return out


DRAW_S, STAGGER_S, DISC_S = 0.45, 0.4, 0.12  # engineering: strokes drawn on in DRAW_S; a row names a thing about every 0.4 s


def sticker(name: str, size: int = SIZE, accent: str | None = None, share: float = 1.0) -> Image.Image:
    """The icon in ink on a round paper sticker with one ink outline (RGBA, transparent outside); ``share`` < 1 draws only
    that part of its strokes (the draw-on)."""
    ss = 3  # supersample, then shrink: smooth strokes without an anti-aliasing library
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ink, paper = _rgb("ink"), _rgb("paper")
    col = _rgb(accent or ACCENTS.get(name, "ink"))
    rim = S * 0.035
    d.ellipse([rim, rim, S - rim, S - rim], fill=paper + (255,), outline=ink + (255,), width=int(S * 0.03))
    box = S * ICON_SHARE
    k, o = box / 24.0, (S - box) / 2
    w = max(2, int(STROKE * k))
    for ln in _cut(icon_polylines(name), share):
        pts = [(o + x * k, o + y * k) for x, y in ln]
        d.line(pts, fill=col + (255,), width=w, joint="curve")
        for x, y in (pts[0], pts[-1]):  # round caps
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=col + (255,))
    return im.resize((size, size), Image.LANCZOS)


_CACHE: dict = {}


def strip(spec: str, size: int, t: float) -> Image.Image | None:
    """A prop asset ``icon:a+b+c`` at ``t`` seconds after it appears: the stickers in a row, each drawn on in turn (its disc
    first, then its strokes), so a line that lists things shows them as the narrator names them. None before anything shows."""
    names = [n for n in spec.split("+") if n]
    for n in names:
        if not (SVG_DIR / f"{n}.svg").exists():
            raise FileNotFoundError(f"icon {n!r} is not in {SVG_DIR}")
    done = len(names) * STAGGER_S + DRAW_S
    q = min(round(t * 15) / 15, round(done, 3))  # 15 drawing steps a second; drawn once it is complete
    key = (spec, size, q)
    if key in _CACHE:
        return _CACHE[key]
    gap = int(size * 0.08)
    out = Image.new("RGBA", (len(names) * size + (len(names) - 1) * gap, size), (0, 0, 0, 0))
    for k, n in enumerate(names):
        u = q - k * STAGGER_S
        if u <= 0:
            continue
        piece = sticker(n, size, share=min(1.0, max(0.0, (u - DISC_S) / DRAW_S)))
        if u < DISC_S:  # the disc pops in first
            piece = piece.resize((max(1, int(size * (0.5 + 0.5 * u / DISC_S))),) * 2, Image.BICUBIC)
            off = (size - piece.width) // 2
            out.alpha_composite(piece, (k * (size + gap) + off, off))
        else:
            out.alpha_composite(piece, (k * (size + gap), 0))
    if len(_CACHE) > 256:
        _CACHE.clear()
    _CACHE[key] = out
    return out


def build(names: list[str] | None = None, out: Path = PNG_DIR) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for n in names or available():
        p = out / f"{n}.png"
        sticker(n).save(p)
        done.append(p)
    return done


def sheet(path: Path, names: list[str] | None = None, cell: int = 160) -> Path:
    names = names or available()
    cols = 10
    rows = math.ceil(len(names) / cols)
    im = Image.new("RGB", (cols * cell, rows * (cell + 24)), (60, 60, 64))
    d = ImageDraw.Draw(im)
    for k, n in enumerate(names):
        x, y = (k % cols) * cell, (k // cols) * (cell + 24)
        im.paste(sticker(n, cell - 10), (x + 5, y + 5), sticker(n, cell - 10))
        d.text((x + 6, y + cell - 2), n[:22], fill=(235, 235, 235))
    im.save(path)
    return path


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if a and a[0] == "build":
        print(f"{len(build(a[1:] or None))} stickers in {PNG_DIR}")
        return 0
    if a and a[0] == "sheet" and len(a) > 1:
        print(sheet(Path(a[1])))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
