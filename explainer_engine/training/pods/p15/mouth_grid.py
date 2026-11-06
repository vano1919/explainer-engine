"""The J5 mouth-variant SHEET layout, ONE constant read by both sides (ვანო 2026-11-06 19:41 UTC: one Qwen picture per hero holding all
variants, not 16 HD pictures). The pod (``p15_mouth``) asks Qwen for this grid at its native 1280x720; the free cut-and-align step of the
J5 thread (``cut``) reads the same numbers. Pure Python + PIL, no torch.

Layout: 4 columns x 2 rows of equal cells on a 1280x720 canvas, row-major, ``MARGIN`` px of the canvas edge kept out of every cell:
    row 1:  A closed | B slight, teeth | C open | D wide
    row 2:  E round  | F pucker        | blink1 (half) | blink2 (shut)
Files (under ``<out>/mouth_variants/``): ``<hero>__sheet_s<seed>.png`` (the picture as drawn) + ``.json`` sidecar; the cut cells are
``<hero>__<cell>.png`` (cell names = ORDER), written by ``cut_files``.
"""
from __future__ import annotations

from pathlib import Path

CANVAS = (1280, 720)
COLS, ROWS = 4, 2
MARGIN = 8
ORDER = ("A", "B", "C", "D", "E", "F", "blink1", "blink2")
WORDS = {"A": "closed", "B": "slightly open showing teeth", "C": "open", "D": "wide open", "E": "small and round",
         "F": "puckered", "blink1": "eyes half closed", "blink2": "eyes shut"}


def cell_box(name: str, size=CANVAS) -> tuple[int, int, int, int]:
    """(x0, y0, x1, y1) of one cell on a canvas of ``size`` (the layout scales with the picture)."""
    i = ORDER.index(name)
    w, h = size
    cw, ch = (w - 2 * MARGIN) / COLS, (h - 2 * MARGIN) / ROWS
    c, r = i % COLS, i // COLS
    return round(MARGIN + c * cw), round(MARGIN + r * ch), round(MARGIN + (c + 1) * cw), round(MARGIN + (r + 1) * ch)


def cut(im) -> dict:
    """{cell name: PIL image} of a drawn sheet."""
    return {n: im.crop(cell_box(n, im.size)) for n in ORDER}


def cut_files(sheet_path: Path, hero: str, out_dir: Path) -> list[Path]:
    from PIL import Image
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, c in cut(Image.open(sheet_path).convert("RGB")).items():
        p = out_dir / f"{hero}__{n}.png"
        c.save(p)
        paths.append(p)
    return paths
