"""Clean cut-out edges before a dialogue figure goes into the render (DL-03, the creator 2026-11-07 22:23 UTC; the Gemini review saw a
1-2 px white line along the top edge of the v1 cut-outs at 00:39, 00:44 and 01:01: BiRefNet leaves a light fringe and the figure's
image border, and the texture's repeat wrap draws it). Free, PIL only.

    trim_edge(img, px=2) -> RGBA: alpha eroded by ``px``, the image border cleared, edge colour pulled from the opaque inside.
    python -m explainer_engine.production.cutout_prep <in.png> <out.png> [px]
"""
from __future__ import annotations

import sys

from PIL import Image, ImageChops, ImageFilter


def trim_edge(img: Image.Image, px: int = 2) -> Image.Image:
    if px < 1:
        raise ValueError("px must be >= 1 (DL-03)")
    im = img.convert("RGBA")
    r, g, b, a = im.split()
    a = a.filter(ImageFilter.MinFilter(2 * px + 1))              # erode the matte: the light fringe goes
    w, h = im.size
    border = Image.new("L", im.size, 0)
    border.paste(255, (px, px, w - px, h - px))                  # nothing on the image's own border (the repeat-wrap line)
    a = ImageChops.multiply(a, border)
    # decontaminate: the edge's colour comes from the opaque inside, not from the old background
    solid = Image.merge("RGB", (r, g, b))
    inside = solid.filter(ImageFilter.MaxFilter(3))
    edge = ImageChops.subtract(img.convert("RGBA").split()[3], a)
    rgb = Image.composite(inside, solid, edge)
    out = rgb.convert("RGBA")
    out.putalpha(a)
    return out


def main(argv: list[str]) -> int:
    src, dst = argv[0], argv[1]
    px = int(argv[2]) if len(argv) > 2 else 2
    trim_edge(Image.open(src), px).save(dst)
    print("wrote", dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
