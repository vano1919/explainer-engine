"""Factor cells of the strategy matrix (Opus plan section 10, 2026-10-26): every picture row of round 3 and 4 is a COMBINATION of four factors, not a
hand-written strategy. Pure logic, no model: the names, the L16 design and the text builders; the pod side is in xworld_v2_loop_run.py.

  A canvas     g = 2x2 grid (four shots at 2560x1408)          p = 1x2 pair (master | target shot, 2560x704)
  B reference  n = none (text only)   e = edit, the master is Image 1   c = in-context: Image 1 is the canvas with the master in its first panel
               s = model sheets of the people as the images
  C layout     0 = none            1 = the set's 3D ray cast in words (camera + landmarks left to right, per panel)
  D prompt     0 = the behind line first in each panel   1 = the same plus exact prop counts from the set ("exactly one table")
  E extras     (round 3a, optional ``+dir`` / ``+sk`` / ``+dsk``) the direction-view picture of the empty place, the line sketch of the panels, both

A row name is ``X_<A>_<B>_<C>_<D>``, for example ``X_g_e_1_0``. 2 x 4 x 2 x 2 = 32 cells; the design takes 16 of them (a half fraction of 2^5 with B
coded by two bits: every main effect and every two-factor interaction is estimable, and any two factors meet in equal numbers).
"""
from __future__ import annotations

import itertools
import re

LEVELS = {"A": ("g", "p"), "B": ("n", "e", "c", "s"), "C": ("0", "1"), "D": ("0", "1")}
NAME = re.compile(r"^X_([gp])_([necs])_([01])_([01])(?:\+(dir|sk|dsk|dpl))?$")
EXTRAS = ("", "dir", "sk", "dsk", "dpl")  # E: extra pictures given to the cell (round 3a): none, the direction views, the line sketch, both; ``dpl`` = the direction views cut into one empty backdrop per panel
COVERED = ("X_g_n_0_0",)  # round 2's S2Tp is exactly this cell (grid, text only, no layout, behind-first)


def name(a, b, c, d):
    return f"X_{a}_{b}_{c}_{d}"


def parse(row):
    """{A, B, C, D} of a cell name, or None when the row is not a cell."""
    m = NAME.match(row)
    return dict(zip("ABCDE", [g or "" for g in m.groups()])) if m else None


def spec(row):
    """The registry entry of a cell row (same keys as loop.ROWS): per-shot pictures for a pair, one grid per scene and seed for a grid."""
    c = parse(row)
    if not c:
        return None
    return {"kind": "cell", "control": False, "grid": c["A"] == "g", "cell": c,
            "note": f"cell: canvas {c['A']}, reference {c['B']}, layout {c['C']}, prompt {c['D']}" + (f", extra {c['E']}" if c["E"] else "")}


def l16():
    """The 16 cells of the design. Bits (a, c, d, b1) are free and b2 = parity, so a + c + d + b1 + b2 is even; B = 2*b1 + b2."""
    out = []
    for a, c, d, b1 in itertools.product((0, 1), repeat=4):
        b2 = (a + c + d + b1) % 2
        out.append(name(LEVELS["A"][a], LEVELS["B"][2 * b1 + b2], LEVELS["C"][c], LEVELS["D"][d]))
    return out


def design(covered=COVERED):
    """The cells still to draw: the L16 minus what an earlier round already holds."""
    return [c for c in l16() if c not in covered]


def balance(cells):
    """{(factor, factor): {(level, level): count}} for every pair of factors: orthogonal when each pair of factors has all its level pairs equally often."""
    out = {}
    for f, g in itertools.combinations("ABCD", 2):
        cnt = {}
        for row in cells:
            c = parse(row)
            cnt[(c[f], c[g])] = cnt.get((c[f], c[g]), 0) + 1
        out[(f, g)] = cnt
    return out


def is_orthogonal(cells):
    return all(len(set(v.values())) == 1 and len(v) == len(LEVELS[f]) * len(LEVELS[g]) for (f, g), v in balance(cells).items())


def draws(cells, scenes=2, seeds=2, shots=2):
    """(grids, pairs): how many 2560x1408 grids and 2560x704 pairs a set of cells draws (a pair cell draws 2 target shots, s2 and s4)."""
    g = sum(parse(c)["A"] == "g" for c in cells) * scenes * seeds
    p = sum(parse(c)["A"] == "p" for c in cells) * scenes * seeds * shots
    return g, p


def prop_counts(object_ids):
    """The D1 text: one 'exactly one X' per object the camera sees (every object of the set is a single piece)."""
    return ("Props in this panel, each exactly once: " + ", ".join(f"exactly one {o.replace('_', ' ')}" for o in object_ids) + ".") if object_ids else ""
