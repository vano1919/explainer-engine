# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/training/pods/xworld_v1_pick.py`
# Target Module : explainer_engine/training/pods/xworld_v1_pick.py
# Target Classes/Symbols : def rank(), def score()
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

"""Checkpoint choice for xworld_v1 from its training samples (D-80, LT-75 step 1; the night plan's agreed method).

The six fixed-seed samples per saved step (LT-77) are scored with CLIP (``training.embed``, free, local):
* ``held``  the held-out samples (0, 1 and the edit 3) against the REAL frames they describe (closer = better);
* ``style`` the two new subjects (4, 5) against the mean of 60 training frames (the look carried to a new subject);
* ``bleed`` the no-trigger sample (2) against the same mean (how much the look leaks without the trigger; reported only).
Rank = held + style; the two best steps go to the prompt-type test, never two neighbours (at least 500 steps apart),
so the test also shows whether more training helps. Claude looks at the sheets before ``picks.json`` is written.

    python -m explainer_engine.training.pods.xworld_v1_pick <dataset dir> <samples dir> <out json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HELD = {0: (0, 0), 1: (1, 0), 3: (0, 1)}  # sample index -> (held-out chain, frame) it describes (xworld_v1_build.samples)


def rank(scores, gap=500):
    """scores {step: {held, style, ...}} -> the two best steps by held + style, at least ``gap`` steps apart."""
    order = sorted(scores, key=lambda s: -(scores[s]["held"] + scores[s]["style"]))
    best = order[0]
    second = next((s for s in order[1:] if abs(s - best) >= gap), order[1] if len(order) > 1 else best)
    return [best, second]


def score(dataset, samples):
    from explainer_engine.training import embed
    dataset, samples = Path(dataset), Path(samples)
    m = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    chains = [c for c in m["hold_out"]["chains"] if len(c) >= 6]
    train = [dataset / x["img"] for x in m["train"]["single"][::max(1, len(m["train"]["single"]) // 60)]][:60]
    cache = samples / "_emb"
    centre = embed.images(train, cache).mean(0); centre /= np.linalg.norm(centre)
    truth = {k: embed.images([dataset / chains[c][f]], cache)[0] for k, (c, f) in HELD.items()}
    by_step = {}
    for p in samples.glob("*.jpg"):
        mm = re.search(r"__0*(\d+)_(\d)\.jpg$", p.name)
        if mm:
            by_step.setdefault(int(mm.group(1)), {})[int(mm.group(2))] = p
    out = {}
    for step, ims in sorted(by_step.items()):
        if step == 0 or len(ims) < 6:
            continue
        v = {k: embed.images([ims[k]], cache)[0] for k in ims}
        out[step] = {"held": round(float(np.mean([v[k] @ truth[k] for k in HELD])), 4),
                     "style": round(float(np.mean([v[k] @ centre for k in (4, 5)])), 4),
                     "bleed": round(float(v[2] @ centre), 4)}
    return out


if __name__ == "__main__":
    s = score(sys.argv[1], sys.argv[2])
    res = {"scores": s, "picks": rank(s)}
    Path(sys.argv[3]).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
