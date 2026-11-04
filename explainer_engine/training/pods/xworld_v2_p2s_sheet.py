# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_p2s_sheet.py`
# Target Module : explainer_engine/training/pods/xworld_v2_p2s_sheet.py
# Target Classes/Symbols : def rows_of(), def sheet(), def main()
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

"""Collage of the P2S test (xworld_v2_p2s.py): one sheet per scene. Row 0 = the master and the model sheets; then one row per
cell (refs, cfg, LoRA weight) with shots 1..4. Questions per row: did the camera move? is it the same place? is it the same
face and clothes as the sheet?

    python xworld_v2_p2s_sheet.py <out dir of xworld_v2_p2s.py> ["title"]     writes <out>/p2s_<scene>.jpg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W, H = 384, 216


def rows_of(todo, scene):
    """[(label, [picture names])] of one scene: the references row first, then the cells in drawing order."""
    mine = [j for j in todo if j["scene"] == scene]
    head = [j["name"] for j in mine if j["kind"] in ("master", "sheet")]
    rows, seen = [("master and model sheets", head)], {}
    for j in mine:
        if j["kind"] in ("master", "sheet"):
            continue
        key = (j["kind"], j["cfg"], j["weight"])
        seen.setdefault(key, []).append(j["name"])
    for (kind, cfg, weight), names in seen.items():
        rows.append((f"{kind}  cfg {cfg}  weight {weight}", names))
    return rows


def sheet(outd, scene, title=""):
    outd = Path(outd)
    todo = json.loads((outd / "jobs.json").read_text(encoding="utf-8"))
    rows = rows_of(todo, scene)
    cols = max(len(r[1]) for r in rows)
    img = Image.new("RGB", (cols * (W + 4), 24 + len(rows) * (H + 28)), "white")
    d = ImageDraw.Draw(img)
    d.text((4, 4), f"{title} {scene}: per row did the camera move? same place? same face and clothes as the sheet? anatomy correct? background correct? anyone duplicated?", fill="black")
    for i, (label, names) in enumerate(rows):
        y = 24 + i * (H + 28)
        d.text((4, y + 2), label, fill="black")
        for k, n in enumerate(names):
            p = outd / f"{n}.png"
            if p.exists():
                img.paste(Image.open(p).convert("RGB").resize((W, H)), (k * (W + 4), y + 18))
    path = outd / f"p2s_{scene}.jpg"
    img.save(path, quality=88)
    return path


def main(argv):
    outd, title = argv[0], (argv[1] if len(argv) > 1 else "")
    for scene in sorted({j["scene"] for j in json.loads((Path(outd) / "jobs.json").read_text(encoding="utf-8"))}):
        print(sheet(outd, scene, title))


if __name__ == "__main__":
    main(sys.argv[1:])
