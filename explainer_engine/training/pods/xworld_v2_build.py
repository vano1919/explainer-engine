# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v2_build.py`
# Target Module : explainer_engine/training/pods/xworld_v2_build.py
# Target Classes/Symbols : def cut_caption(), def new_place(), def pairs(), def samples(), def build()
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

"""Builds the xworld_v2 training folders and config on the pod (D-80; ვანო 2026-10-26 13:26 Tbilisi, the round plan):
* ``new/``: the 210 new-world pictures (xworld_v2_data.py), captions ``xworld style, ...``, repeated NEW_REPEATS times;
* ``pairs/target`` + ``pairs/control``: the cross-shot pairs (357, less those that move to another place) of xworld_v1 (shot -> next shot; the 234 within-shot ones are dropped)
  with their reviewed captions written as cuts (cut_caption), under ``rm style``: they keep the base model's sense of cutting and moving a scene
  (regularization) while the show's look stays on its own trigger. The show's single frames are left out.
Sample prompts: five held-out new-world pictures, the tent scene's first shot, and one held-out person again without a
trigger and with ``rm style`` (does the look stay apart?).

    python xworld_v2_build.py <v1 dataset> <v1 captions.jsonl> <v2 dataset> <scene dir> <out ds> <cfg template> <cfg out>
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

if __package__:
    from .xworld_v1_build import load_captions, plan
    from .xworld_v1_test import KEEP, MASTER
    from .xworld_v2_data import RM_TRIGGER, TRIGGER
else:
    from xworld_v1_build import load_captions, plan
    from xworld_v1_test import KEEP, MASTER
    from xworld_v2_data import RM_TRIGGER, TRIGGER

NEW_REPEATS = 3
SAMPLE_HELD = ["c007", "c062", "p012", "p065", "o009"]
SIZES = {"c": (768, 1024), "p": (1024, 576), "o": (1024, 1024)}


CHANGE_V1 = "Change from the previous shot:"
CUT = "Cut to the next shot:"


def cut_caption(text):
    """A v1 pair caption `xworld style, <description>. Change from the previous shot: <change>` in the form the round test
    asks with (P2F: the master sentence, the description, the cut, the keep line), under rm style (ვანო 2026-10-26 12:33:
    the 357 cut pairs are the only ones that can teach a cut, so they are written like the prompt that uses them)."""
    assert text.startswith(TRIGGER + ", ") and CHANGE_V1 in text, text[:80]
    desc, change = text[len(TRIGGER) + 2:].split(CHANGE_V1, 1)
    return f"{RM_TRIGGER}, {MASTER} {desc.strip()} {CUT} {change.strip()} {KEEP}"


NEW_PLACE = re.compile(
    r"(scene (shifts|changes|transitions)|shifts? to (a|an|the) (new|different|doorway|room|hallway|kitchen|outdoor|street|forest"
    r"|house|garage|lab|yard)|(new|different) (room|location|place|setting|environment|scene|background)"
    r"|background (changes|is now|has changed|shifts)|(room|setting|location|environment|scene|background) "
    r"(is now|has changed|changes|shifts)|(moves?|goes|cuts?|transitions?) to (a|an|the) (different|new|another)"
    r"|now (in|inside|outdoors|outside|at) (a|an|the))", re.I)


def new_place(text):
    """A change sentence that moves to another place: it contradicts the master sentence (keep its landmarks)."""
    return bool(NEW_PLACE.search(text.split(CUT, 1)[1]))


def pairs(v1_manifest, caps):
    """The 357 cross-shot v1 pair items (the 234 within-shot pairs teach a still camera: review 2026-10-26), written as cuts."""
    cut = len(v1_manifest["train"]["scene_pairs"])
    out = []
    for kind, name, img, ctrl, text in plan(v1_manifest, caps):
        if kind == "pair" and int(name[1:]) < cut:  # plan() numbers scene_pairs first, then inshot_pairs
            cap = cut_caption(text)
            if not new_place(cap):  # ~15 pairs, ვანო 2026-10-26 12:42
                out.append((name, img, ctrl, cap))
    return out


def samples(v2_manifest, tent):
    held = v2_manifest["hold_out"]
    out = []
    for i in SAMPLE_HELD:
        w, h = SIZES[i[0]]
        out.append({"prompt": held[i], "width": w, "height": h})
    s0 = tent["shots"][0]
    out.append({"prompt": f"{TRIGGER}, {s0['desc']} {s0['layout']}", "width": 1024, "height": 576})
    plain = held["c007"][len(TRIGGER) + 2:]
    out.append({"prompt": plain, "width": 768, "height": 1024})
    out.append({"prompt": f"{RM_TRIGGER}, {plain}", "width": 768, "height": 1024})
    return out


def build(v1, v1_caps, v2, scene_dir, out, template, cfg_out):
    v1, v2, out = Path(v1), Path(v2), Path(out)
    v1m = json.loads((v1 / "manifest.json").read_text(encoding="utf-8"))
    v2m = json.loads((v2 / "manifest.json").read_text(encoding="utf-8"))
    for sub in ("new", "pairs/target", "pairs/control"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    for i in v2m["train"]:
        shutil.copy(v2 / "new" / f"{i}.png", out / "new" / f"{i}.png")
        shutil.copy(v2 / "new" / f"{i}.txt", out / "new" / f"{i}.txt")
    pr = pairs(v1m, load_captions(v1_caps))
    for name, img, ctrl, text in pr:
        shutil.copy(v1 / img, out / "pairs/target" / f"{name}.png")
        (out / "pairs/target" / f"{name}.txt").write_text(text, encoding="utf-8")
        shutil.copy(v1 / ctrl, out / "pairs/control" / f"{name}.png")
    tent = json.loads((Path(scene_dir) / "tent.json").read_text(encoding="utf-8"))
    smp = samples(v2m, tent)
    cfg = Path(template).read_text(encoding="utf-8").replace("\"@SAMPLES@\"", json.dumps(smp, ensure_ascii=False))
    assert f"num_repeats: {NEW_REPEATS} " in cfg, "the template's repeats differ from NEW_REPEATS"
    Path(cfg_out).write_text(cfg, encoding="utf-8")
    n = {"new": len(v2m["train"]), "pairs": len(pr)}
    print("built", n, flush=True)
    return n


if __name__ == "__main__":
    build(*sys.argv[1:8])
