# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_sheet.py`
# Target Module : explainer_engine/training/pods/xworld_v2_sheet.py
# Target Classes/Symbols : def rows_of(), def build()
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

"""Contact sheets of one xworld_v2 round test: one sheet per scene, a row per seed and prompt form, shot 0 first in every
row, the round's VL score of each form written beside it. PIL only, so it runs on the pod and locally.

    python xworld_v2_sheet.py <scene dir> <round out dir> <label> [round]   ->  <round dir>/sheet_<scene>.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import FORMS, MODES, ROUND_TESTS, SEEDS, load
else:
    from xworld_v2_scenes import FORMS, MODES, ROUND_TESTS, SEEDS, load

W, H, PAD, TOP = 384, 216, 6, 34


def rows_of(scene, tests=None):
    """[(seed, form)] a scene's sheet shows: every seed x form, or what a training round drew (ROUND_TESTS)."""
    if tests is None:
        return [(seed, form) for seed in SEEDS for form in FORMS]
    return [(seed, f) for f, only, sds in tests if only is None or scene in only for seed in sds]


def build(scene_dir, outd, label, tests=None):
    from PIL import Image, ImageDraw
    outd = Path(outd)
    summ = json.loads((outd / "summary.json").read_text()) if (outd / "summary.json").exists() else {}
    made = []
    for sc in load(scene_dir):
        ids = [s["id"] for s in sc["shots"]]
        rows = rows_of(sc["name"], tests)
        sheet = Image.new("RGB", (PAD + len(ids) * (W + PAD), TOP + len(rows) * (H + 20 + PAD)), "white")
        d = ImageDraw.Draw(sheet)
        d.text((PAD, 8), f"{label} - {sc['name']} ({sc['world']}); per row: did the camera move? same place? anatomy correct? background correct? anyone duplicated?", fill="black")
        for r, (seed, form) in enumerate(rows):
            y = TOP + r * (H + 20 + PAD)
            score = summ.get(f"{form}/{sc['name']}")
            d.text((PAD, y), f"seed {seed} {form}" + (f"  VL {score:.2f}" if score is not None else ""), fill="black")
            for c, sid in enumerate(ids):
                p = outd / (f"{sc['name']}_{seed}_s0.png" if sid == "s0" else f"{sc['name']}_{seed}_{form}_{sid}.png")
                if p.exists():
                    with Image.open(p) as im:
                        sheet.paste(im.convert("RGB").resize((W, H)), (PAD + c * (W + PAD), y + 16))
        dst = outd / f"sheet_{sc['name']}.jpg"
        sheet.save(dst, quality=85)
        made.append(dst)
    return made


if __name__ == "__main__":
    print(build(*sys.argv[1:4], tests=MODES.get(sys.argv[4]) if len(sys.argv) > 4 else None))
