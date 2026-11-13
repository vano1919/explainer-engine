"""The style bridge for HELPER renderers (roadmap 9.1 and section 11, ICW-05; bible ``motion.default``: "HELPER graphics from the
Python renderers through the style bridge"). Maps, HUD cards, tableaux and other drawn-by-code frames sit between Blender shots, so
they take the same tokens the Blender style engine uses (``blender/style.py``): the ink and paper colours of the palette, the Line
Art weight of BP-173 scaled to the frame, and the same paper grain at the same opacity.

    BridgeTokens.from_style(StyleTokens)       # one set of tokens for both sides
    line_px(height)                            # the ink weight at this frame height (1.5-3 px at 1440, scaled)
    finish(image, tokens, paper=texture)       # the paper overlay of the Blender compositor, in numpy

Deterministic (CMP-09): a pure function of the image, the tokens and the paper texture's bytes; no clock, no random state. The
overlay is the compositor's: grey of the paper texture, stretched to 0..1 (Normalize), Overlay-blended at ``paper_opacity``; the
texture is cropped to the frame's aspect and resized with a fixed filter, so the grain lands where the Blender pass puts it.
Without a paper texture ``finish`` returns the image unchanged (never a fake grain).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.blender import style as S

REF_H = S.MASTER_H


def _rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


@dataclass(frozen=True)
class BridgeTokens:
    ink: tuple[int, int, int]
    paper: tuple[int, int, int]
    line_px_1440: float
    paper_opacity: float
    accents: dict

    @classmethod
    def from_style(cls, tokens: S.StyleTokens | None = None) -> "BridgeTokens":
        t = tokens or S.StyleTokens.from_bible()
        pal = S.palette()
        accents = {k: _rgb(v) for k, v in pal.items() if k not in (t.ink, t.paper, "chroma_key")}
        return cls(ink=_rgb(pal[t.ink]), paper=_rgb(pal[t.paper]), line_px_1440=t.line_px, paper_opacity=t.paper_opacity,
                   accents=accents)

    def line_px(self, height: int) -> float:
        """The ink weight at ``height``: the 1440p weight scaled with the frame (a 1080p HUD draws 0.75 x)."""
        return round(self.line_px_1440 * height / REF_H, 4)

    def colour(self, token: str) -> tuple[int, int, int]:
        if token == "ink":
            return self.ink
        if token == "paper":
            return self.paper
        if token not in self.accents:
            raise KeyError(f"{token!r} is not a palette token the bridge offers (the chroma key never reaches the screen)")
        return self.accents[token]


def grain(paper: Path | str | Image.Image, width: int, height: int) -> np.ndarray:
    """The paper's grain as float32 0..1 at ``width`` x ``height``: grey, centre-cropped to the aspect, resized (Lanczos), stretched
    to its own min..max like the compositor's Normalize node."""
    im = paper if isinstance(paper, Image.Image) else Image.open(paper)
    g = im.convert("L")
    w, h = g.size
    want = width / height
    if w / h > want:
        cw = round(h * want)
        g = g.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    else:
        ch = round(w / want)
        g = g.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    a = np.asarray(g.resize((width, height), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
    lo, hi = float(a.min()), float(a.max())
    return np.zeros_like(a) + 0.5 if hi - lo < 1e-6 else (a - lo) / (hi - lo)


def overlay(base: np.ndarray, top: np.ndarray, factor: float) -> np.ndarray:
    """Blender's Mix node in Overlay mode: base < 0.5 -> 2·base·top, else 1 - 2(1-base)(1-top), mixed by ``factor``."""
    t = top[..., None] if top.ndim == base.ndim - 1 else top
    ov = np.where(base < 0.5, 2 * base * t, 1 - 2 * (1 - base) * (1 - t))
    return base * (1 - factor) + ov * factor


def finish(image: Image.Image, tokens: BridgeTokens | None = None, *, paper: Path | str | Image.Image | None = None) -> Image.Image:
    """The paper pass on a HELPER frame (RGB or RGBA; alpha is kept). Same inputs, same bytes."""
    if paper is None:
        return image.copy()
    t = tokens or BridgeTokens.from_style()
    mode = image.mode
    rgb = image.convert("RGB")
    a = np.asarray(rgb, dtype=np.float32) / 255.0
    out = overlay(a, grain(paper, rgb.width, rgb.height), t.paper_opacity)
    res = Image.fromarray(np.clip(np.rint(out * 255.0), 0, 255).astype(np.uint8), "RGB")
    if mode == "RGBA":
        res.putalpha(image.getchannel("A"))
    return res


def off_palette_share(image: Image.Image, tokens: BridgeTokens | None = None, *, tolerance: int = 24) -> float:
    """Share of pixels farther than ``tolerance`` (max channel distance) from every palette token and every ink/paper blend
    step: a REVIEW signal for a HELPER frame that drew colours the palette does not hold (before the paper pass)."""
    t = tokens or BridgeTokens.from_style()
    cols = [t.ink, t.paper, *t.accents.values()]
    steps = [tuple(round(x + (y - x) * k / 8) for x, y in zip(a, b)) for a in cols for b in (t.ink, t.paper) for k in range(9)]
    ref = np.array(sorted(set(steps)), dtype=np.int16)
    px = np.asarray(image.convert("RGB").resize((max(1, image.width // 4), max(1, image.height // 4)), Image.Resampling.NEAREST),
                    dtype=np.int16).reshape(-1, 1, 3)
    near = (np.abs(px - ref[None]).max(axis=2) <= tolerance).any(axis=1)
    return round(float(1 - near.mean()), 4)
