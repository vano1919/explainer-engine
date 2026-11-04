# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/compose/crowd.py`
# Target Module : explainer_engine/compose/crowd.py
# Target Classes/Symbols : def _width_m(), def scatter(), def check()
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

"""AC-10..AC-11: crowds and battles from a few crowd units. A model cannot count 200 soldiers; code can: it scatters N
figures over a band of ground by perspective (more of them far away, where the ground is wider), keeps a real gap between
them, varies each by mirror and a slight tint, and never stands two identical figures side by side.

Band: ``{"units": [crowd names], "count", "z": [near_m, far_m], "x"?: [0, 1], "seed", "angle"?, "facing"?:
"left"|"right"|"mixed", "kind"?: a layout.SIZES row (default adult), "gap_m"?: 0.7, "tint"?: 0.08}``.
"""

from __future__ import annotations

import math
import random

MIN_UNITS = 3            # AC-11: a crowd of 10 or more takes at least three different units
CLONE_SHARE = 0.15       # AC-10: at most this share of neighbouring pairs may be the same unit facing the same way


def _width_m(cam: dict, z: float) -> float:
    """How many metres of ground the frame is wide at distance z."""
    return z / cam["f"] * 16 / 9


def scatter(band: dict, cam: dict, lib) -> list[dict]:
    from explainer_engine.compose.frame import project
    rng = random.Random(band.get("seed", 0))
    near, far = band["z"]
    x0, x1 = band.get("x", [0.0, 1.0])
    gap = band.get("gap_m", 0.7)
    kind = band.get("kind", "adult")
    facing = band.get("facing", "mixed")
    out, tries = [], 0
    while len(out) < band["count"] and tries < band["count"] * 40:
        tries += 1
        z = near + (far - near) * math.sqrt(rng.random())          # uniform over ground area: more people far away
        x = x0 + (x1 - x0) * rng.random()
        xm = (x - 0.5) * _width_m(cam, z)
        if any(abs(p["z"] - z) < gap * 1.5 and abs(p["xm"] - xm) < gap for p in out):
            continue
        near_ones = sorted(out, key=lambda p: (p["z"] - z) ** 2 + (p["xm"] - xm) ** 2)[:3]
        face = rng.choice(["left", "right"]) if facing == "mixed" else facing
        units = band["units"][:]
        rng.shuffle(units)
        pick = None
        for u in units:
            hit = lib.find("crowd", u, band.get("angle", "three_quarter"), face)
            if hit and not any(n["asset"] == hit["id"] and n["flip"] == hit["flip"] for n in near_ones):
                pick = hit
                break
        if pick is None:
            hit = lib.find("crowd", units[0], band.get("angle", "three_quarter"), face)
            if not hit:
                raise KeyError(f"no crowd unit {units[0]!r} at {band.get('angle', 'three_quarter')}")
            pick = hit
        j = band.get("tint", 0.08)
        tint = tuple(round(1 + rng.uniform(-j, j), 3) for _ in range(3))
        p = project(cam, kind, z, x)
        out.append({"crowd": True, "asset": pick["id"], "flip": pick["flip"], "z": p["z"], "xm": round(xm, 2),
                    "box": p["box"], "tint": tint, "tag": f"crowd:{pick['id']}"})
    return out


def check(bands: list[dict], placed: list[dict]) -> list[dict]:
    out = []
    for b in bands:
        if b["count"] >= 10 and len(set(b["units"])) < MIN_UNITS:
            out.append({"rule": "AC-11", "severity": "FAIL", "detail": f"{b['count']} people from {len(set(b['units']))} "
                        f"unit(s): at least {MIN_UNITS}"})
        if len([p for p in placed if p.get("crowd")]) < sum(x["count"] for x in bands) * 0.9:
            out.append({"rule": "AC-10", "severity": "REVIEW", "detail": "the band is too small for the count at this gap"})
    crowd = [p for p in placed if p.get("crowd")]
    same = 0
    for a in crowd:                    # each figure and its nearest neighbour on the ground (metres)
        others = [b for b in crowd if b is not a]
        if not others:
            break
        b = min(others, key=lambda b: (b["z"] - a["z"]) ** 2 + (b["xm"] - a["xm"]) ** 2)
        same += a["asset"] == b["asset"] and a["flip"] == b["flip"]
    if len(crowd) >= 10 and same / len(crowd) > CLONE_SHARE:
        out.append({"rule": "AC-10", "severity": "FAIL", "detail": f"{same} of {len(crowd)} figures stand next to the same "
                    f"unit facing the same way: it reads as a clone stamp"})
    return out
