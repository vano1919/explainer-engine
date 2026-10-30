"""The drawing kit of the maps and the compensator: palette colours, supersampled canvas, easing, the markers. PIL + numpy.

Colours come only from ``design/palette.json`` (tokens, blends of tokens); sizes are shares of the frame height, so a frame drawn at
320x180 and at 1920x1080 has the same look. A frame is a pure function of its spec and its number (CMP-09): no clock, no random
state that is not seeded from the spec, no file reads other than the declared fonts and plates.
"""

from __future__ import annotations

import hashlib
import io
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from explainer_engine.design import palette as PAL

ROOT = Path(__file__).resolve().parents[2]
FONT_FILES = [ROOT / "assets" / "fonts" / "ComicNeue-Bold.ttf", ROOT / "assets" / "fonts" / "Bangers-Regular.ttf"]
SS = 2  # supersampling of a drawn frame: edges are smooth and the downsample is deterministic


@lru_cache(maxsize=1)
def tokens() -> dict[str, tuple[int, int, int]]:
    return {name: tuple(int(t["hex"][i:i + 2], 16) for i in (1, 3, 5)) for name, t in PAL.load()["tokens"].items()}


def rgb(token: str) -> tuple[int, int, int]:
    return tokens()[token]


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """``a`` moved ``t`` of the way to ``b``."""
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))  # type: ignore[return-value]


def faction(side: str) -> tuple[int, int, int]:
    return rgb({"a": "faction_a", "b": "faction_b"}[side])


@lru_cache(maxsize=64)
def font(px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_FILES:
        if path.exists():
            return ImageFont.truetype(str(path), max(8, int(px)))
    return ImageFont.load_default(size=max(8, int(px)))


def ease_in_out(u: float) -> float:
    """Cubic ease in and out (BP-23: every move is eased)."""
    u = min(max(u, 0.0), 1.0)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def march(u: float, lead: float = 0.15, tail: float = 0.15) -> float:
    """Progress of a march: a slow start, a cruise at constant speed, a halt at the line (law 2). The speed ramps up over
    ``lead``, holds, and ramps down over ``tail`` (a trapezoid), so the position is continuous and never jumps."""
    u = min(max(u, 0.0), 1.0)
    v = 1.0 / (1.0 - (lead + tail) / 2.0)  # the cruise speed that makes the whole path take one unit
    if u < lead:
        return v * u * u / (2 * lead)
    if u > 1.0 - tail:
        r = 1.0 - u
        return 1.0 - v * r * r / (2 * tail)
    return v * lead / 2 + v * (u - lead)


def smoothstep(e0: float, e1: float, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def seeded(*parts) -> np.random.Generator:
    """A generator seeded from the spec, never from time (CMP-09)."""
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


class Canvas:
    """A supersampled RGBA canvas; every coordinate is in output pixels. ``text`` is the only call that draws letters: a plate never
    calls it (CMP-01)."""

    def __init__(self, width: int, height: int, background=None, ss: int = SS):
        self.w, self.h, self.ss = width, height, ss
        base = (0, 0, 0, 0) if background is None else (*background, 255)
        self.im = Image.new("RGBA", (width * ss, height * ss), base)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def replace(self, im: Image.Image) -> None:
        """Swap the pixels (a dimmed or painted base) and keep drawing on the new ones."""
        self.im = im.convert("RGBA")
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def px(self, v: float) -> int:
        return int(round(v * self.ss))

    def _pts(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def polygon(self, pts, fill=None, outline=None, width: float = 0):
        pts = self._pts(pts)
        if len(pts) >= 3:
            self.d.polygon(pts, fill=fill, outline=outline if not width else None)
            if outline and width:
                self.d.line(pts + [pts[0]], fill=outline, width=max(1, self.px(width)), joint="curve")

    def line(self, pts, fill, width: float = 2, dash: tuple[float, float] | None = None):
        pts = self._pts(pts)
        if len(pts) < 2:
            return
        if dash is None:
            self.d.line(pts, fill=fill, width=max(1, self.px(width)), joint="curve")
            return
        on, off = dash[0] * self.ss, dash[1] * self.ss
        phase, width_px = 0.0, max(1, self.px(width))        # the dash pattern runs on along the whole line, across its segments
        for a, b in zip(pts, pts[1:]):
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            pos = 0.0
            while pos < length:
                step = max((on - phase) if phase < on else (on + off - phase), 1e-6)       # always moves on, whatever the float noise
                end = min(length, pos + step)
                if phase < on:
                    p0 = (a[0] + (b[0] - a[0]) * pos / length, a[1] + (b[1] - a[1]) * pos / length)
                    p1 = (a[0] + (b[0] - a[0]) * end / length, a[1] + (b[1] - a[1]) * end / length)
                    self.d.line([p0, p1], fill=fill, width=width_px)
                phase = (phase + end - pos) % (on + off)
                pos = end

    def circle(self, cx, cy, r, fill=None, outline=None, width: float = 2):
        box = [(cx - r) * self.ss, (cy - r) * self.ss, (cx + r) * self.ss, (cy + r) * self.ss]
        self.d.ellipse(box, fill=fill, outline=outline, width=max(1, self.px(width)) if outline else 0)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width: float = 2, radius: float = 0):
        box = [x0 * self.ss, y0 * self.ss, x1 * self.ss, y1 * self.ss]
        if radius:
            self.d.rounded_rectangle(box, radius=radius * self.ss, fill=fill, outline=outline, width=max(1, self.px(width)) if outline else 0)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=max(1, self.px(width)) if outline else 0)

    def text(self, xy, s: str, size: float, fill, anchor: str = "la", stroke: float = 0, stroke_fill=None):
        f = font(self.px(size))
        self.d.text((xy[0] * self.ss, xy[1] * self.ss), s, font=f, fill=fill, anchor=anchor,
                    stroke_width=self.px(stroke) if stroke else 0, stroke_fill=stroke_fill)

    def text_width(self, s: str, size: float) -> float:
        return self.d.textlength(s, font=font(self.px(size))) / self.ss

    def paste(self, layer: Image.Image, xy=(0, 0)):
        """Paste an RGBA layer given at output size (it is scaled to the supersampled canvas)."""
        big = layer.convert("RGBA").resize((layer.width * self.ss, layer.height * self.ss), Image.BICUBIC)
        self.im.alpha_composite(big, (int(xy[0] * self.ss), int(xy[1] * self.ss)))

    def image(self) -> Image.Image:
        if self.ss == 1:
            return self.im.copy()
        return self.im.resize((self.w, self.h), Image.LANCZOS)


def marker(c: Canvas, side: str, cx: float, cy: float, r: float) -> None:
    """A unit counter. The two sides differ by colour AND shape (a square, a triangle): meaning is never colour alone (CMP-06)."""
    ink = rgb("ink")
    col = (*faction(side), 255)
    width = max(2.0, r * 0.22)
    if side == "a":
        c.rect(cx - r, cy - r, cx + r, cy + r, fill=col, outline=ink, width=width, radius=r * 0.2)
    else:
        c.polygon([(cx, cy - r * 1.15), (cx + r * 1.1, cy + r * 0.85), (cx - r * 1.1, cy + r * 0.85)], fill=col, outline=ink, width=width)


def arrow_head(c: Canvas, tip, back, size: float, fill, ink=None) -> None:
    """A triangle at ``tip`` pointing away from ``back``."""
    dx, dy = tip[0] - back[0], tip[1] - back[1]
    n = math.hypot(dx, dy) or 1.0
    ux, uy = dx / n, dy / n
    left = (tip[0] - ux * size - uy * size * 0.55, tip[1] - uy * size + ux * size * 0.55)
    right = (tip[0] - ux * size + uy * size * 0.55, tip[1] - uy * size - ux * size * 0.55)
    c.polygon([tip, left, right], fill=fill, outline=ink, width=max(1.0, size * 0.12) if ink else 0)


def polyline_prefix(pts: list[tuple[float, float]], share: float) -> list[tuple[float, float]]:
    """The first ``share`` of a polyline by length (the arrow that draws itself: trim_end 0 -> 1)."""
    if share >= 1.0:
        return list(pts)
    lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    goal = sum(lens) * max(share, 0.0)
    out = [pts[0]]
    run = 0.0
    for (a, b), n in zip(zip(pts, pts[1:]), lens):
        if run + n >= goal:
            t = (goal - run) / n if n else 0.0
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            return out
        out.append(b)
        run += n
    return out


def polyline_point(pts: list[tuple[float, float]], share: float) -> tuple[float, float]:
    return polyline_prefix(pts, share)[-1]


def png_bytes(im: Image.Image) -> bytes:
    """One fixed encoder setting, no metadata: the same image is the same bytes (CMP-09)."""
    buf = io.BytesIO()
    im.save(buf, format="PNG", compress_level=6, optimize=False)
    return buf.getvalue()


def write_bytes_atomic(path, data: bytes):
    """A file written through a temp name and ``store.replace_file`` (retries on Windows while a reader holds the target)."""
    from pathlib import Path
    from explainer_engine.core import store
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    store.replace_file(tmp, path)
    return path


def frame_hash(im: Image.Image) -> str:
    return hashlib.sha256(png_bytes(im)).hexdigest()
