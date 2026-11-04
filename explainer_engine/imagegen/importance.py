# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/importance.py`
# Target Module : explainer_engine/imagegen/importance.py
# Target Classes/Symbols : def classify()
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

"""Which pictures are filler (D-53, PV-43). stdlib only.

Importance is computed from what the script already says, never declared by the script: a writer cannot mark a picture
"filler" to get it past a gate. A picture is NOT filler when any of these holds:

* a shot that uses it is type B (named heroes acting) or the picture itself names heroes or shows people;
* it is used more than once (the viewer meets it again, so it carries the story);
* it is a premium picture (reused identity assets or a reveal);
* a segment that uses it has a beat job outside FILLER_JOBS (hook, question, evidence, complication, reveal, payoff) or no job at all.

What stays is the establishing plate (type A) or the insert (type C) with no person in it, used once, inside an explanation,
emotional pause, humour or transition beat. Shot length is not known at script stage; the 4-second limit the creator chose is
checked after timing (docs/PRODUCTION_SCRIPT.md PV-43).
"""

from __future__ import annotations

from explainer_engine.production import script as S

FILLER_JOBS = {"explanation", "emotional_pause", "humor", "transition"}
FILLER_SHARE_MAX = 0.30        # at most this share of an episode's painted pictures may come from Canva (D-53)
CANVA_FREE_AI_USES = 20        # the creator's free plan (V-39); a count above it is reviewed


def classify(doc: dict) -> dict[str, dict]:
    """picture id -> {"filler": bool, "why_not": [reasons]} for every used picture."""
    pics, _ = S.pictures(doc)
    seg_job = {seg["id"]: seg.get("job") for seg in doc["segments"]}
    shots_of: dict[str, list[dict]] = {}
    for sh in S.shots(doc):
        shots_of.setdefault(sh["picture_id"], []).append(sh)
    out = {}
    for pid, pic in pics.items():
        shots = shots_of.get(pid, [])
        if not shots:
            continue
        why = []
        if any(sh["shot"].get("type") == "B" for sh in shots):
            why.append("used in a B shot (named heroes acting)")
        if pic.get("heroes") or pic.get("people"):
            why.append("shows heroes or people")
        if len(shots) > 1:
            why.append("used more than once")
        if pic.get("tier") == "premium":
            why.append("premium picture")
        for sh in shots:
            job = seg_job.get(sh["segment"])
            if job not in FILLER_JOBS:
                why.append(f"beat {sh['segment']} has job {job!r}" if job else f"beat {sh['segment']} has no job")
        out[pid] = {"filler": not why, "why_not": sorted(set(why))}
    return out
