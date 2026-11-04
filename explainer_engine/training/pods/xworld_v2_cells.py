# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_cells.py`
# Target Module : explainer_engine/training/pods/xworld_v2_cells.py
# Target Classes/Symbols : def name(), def parse(), def spec(), def l16(), def design(), def balance(), def is_orthogonal(), def draws(), def prop_counts()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
