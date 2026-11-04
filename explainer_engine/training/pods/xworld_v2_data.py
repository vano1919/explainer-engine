# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_data.py`
# Target Module : explainer_engine/training/pods/xworld_v2_data.py
# Target Classes/Symbols : def as_drawn(), def caption(), def build()
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

"""The new-world part of the xworld_v2 dataset (D-80; ვანო 2026-10-26 13:17 Tbilisi: "99 % is good, train the world"): the
220 BFL pictures of `training/cast` with captions made from the text each was drawn from, without the style words, so the
look binds to the trigger. Ten are held out for the checkpoint choice (HOLD_OUT). Where Claude's look found a woman drawn
as a man (FIXED_MALE) or unclear (FIXED_PERSON) the caption says what is drawn, never what was asked.

    python -m explainer_engine.training.pods.xworld_v2_data <world dir> <out dir>
writes <out>/new/<id>.png + .txt and <out>/manifest.json (train ids, hold-out ids with their captions).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

TRIGGER = "xworld style"
RM_TRIGGER = "rm style"  # the training show's sequence pairs keep their own trigger, so its look stays out of ours
HOLD_OUT = ["c007", "c033", "c062", "c085", "p012", "p041", "p065", "p078", "o009", "o024"]
# Claude's look 2026-10-26 (rating page notes): asked for a woman, drawn as a man / unclear
FIXED_MALE = ["c006", "c010", "c014", "c018", "c022", "c030", "c041", "c046", "c050", "c054", "c057", "c058", "c074",
              "c078", "c081", "c089", "c090", "c093", "c097", "c098"]
FIXED_PERSON = ["c029", "c045", "c053", "c086"]
FRAME = {"person": "one person, full body, on a plain off-white background: ",
         "place": "an empty place with no people, wide view: ",
         "object": "one object on a plain off-white background: "}


def as_drawn(cid, desc):
    """The description with the sex of the drawn picture (FIXED_MALE, FIXED_PERSON)."""
    if cid in FIXED_MALE:
        desc = desc.replace(", a woman,", ", a man,")
        desc = re.sub(r"\bShe\b", "He", desc); desc = re.sub(r"\bher\b", "his", desc); desc = re.sub(r"\bHer\b", "His", desc)
    elif cid in FIXED_PERSON:
        desc = desc.replace(", a woman,", ", a person,")
        desc = re.sub(r"\bShe has\b", "The person has", desc); desc = re.sub(r"\b[Hh]er\b", "the", desc)
    return desc


def caption(item_id, kind, desc):
    return f"{TRIGGER}, {FRAME[kind]}{as_drawn(item_id, desc)}"


def build(world, out):
    from explainer_engine.training.cast.rate_page import kept
    from explainer_engine.training.cast.sheet import items
    world, out = Path(world), Path(out)
    (out / "new").mkdir(parents=True, exist_ok=True)
    its, best = items(), kept(world)
    missing = sorted(set(its) - set(best))
    if missing:
        raise ValueError(f"no kept picture for {missing}")
    man = {"train": [], "hold_out": {}}
    for i in sorted(its):
        text = caption(i, its[i]["kind"], its[i]["desc"])
        if i in HOLD_OUT:
            man["hold_out"][i] = text
            continue
        shutil.copy(world / f"{best[i]['name']}.png", out / "new" / f"{i}.png")
        (out / "new" / f"{i}.txt").write_text(text, encoding="utf-8")
        man["train"].append(i)
    (out / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(man["train"]), "train,", len(man["hold_out"]), "held out ->", out)
    return man


if __name__ == "__main__":
    build(*sys.argv[1:3])
