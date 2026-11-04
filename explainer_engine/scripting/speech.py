# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/speech.py`
# Target Module : explainer_engine/scripting/speech.py
# Target Classes/Symbols : def speakers(), def check()
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

"""How each speaking hero talks (PV-46, DW-11; creator 2026-10-19). stdlib only.

Every hero who speaks has ``cast.<id>.speech``: the manner and the vocabulary of their speech. A real person or a known
character talks the way they are generally known to talk (``basis: public``, with the sources that describe it); an invented
hero talks from their personality (``basis: personality``). The words are always our own: the manner is borrowed, never a
quote, a catchphrase of a film or series, or an imitation of an actor's voice (VC-02 stays the rule for voices).
"""

from __future__ import annotations

import re

LEGACY = "production_script/1"
BASES = ("public", "personality")
MIN_WORDS = 3  # signature words or turns of phrase a hero's lines draw on


def speakers(doc: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for seg in doc["segments"]:
        for ln in seg["lines"]:
            if ln.get("speaker"):
                out.setdefault(ln["speaker"], []).append(ln["text"])
    for sh in doc.get("shorts", []):
        for ln in sh.get("lines", []):
            if ln.get("speaker"):
                out.setdefault(ln["speaker"], []).append(ln["text"])
    return out


def check(doc: dict) -> list[dict]:
    sev = "REVIEW" if doc.get("schema") == LEGACY else "FAIL"
    out = []

    def f(where, detail, s=sev):
        out.append({"rule": "PV-46", "severity": s, "where": where, "detail": detail})

    for who, lines in speakers(doc).items():
        sp = doc.get("cast", {}).get(who, {}).get("speech")
        if not sp:
            f(who, f"{who} speaks but has no cast.{who}.speech: write the manner and vocabulary of their speech, from how they "
                   "are generally known to talk or, for an invented hero, from their personality (DW-11)")
            continue
        if sp.get("basis") not in BASES:
            f(who, f"speech.basis is one of {BASES}")
        if len(sp.get("style", "").split()) < 4:
            f(who, "speech.style says in a sentence how they talk (pace, register, sentence length, habits)")
        if len(sp.get("words", [])) < MIN_WORDS:
            f(who, f"speech.words lists at least {MIN_WORDS} words or turns of phrase typical of them")
        if sp.get("basis") == "public" and not sp.get("sources"):
            f(who, "a publicly known manner needs its sources (claim ids or URLs): how they are described, never a film "
                   "or actor portrayal copied")
        text = " ".join(lines).lower()
        for bad in sp.get("avoid", []):
            if re.search(r"\b" + re.escape(bad.lower()) + r"\b", text):
                f(who, f"{who} says {bad!r}, which their speech avoids", "REVIEW")
        # the fields existing is not the manner being used (the 2026-10-19 audit): on /3, a hero none of whose
        # signature words or phrases ever appears in their lines probably talks like everyone else
        words = sp.get("words", [])
        if doc.get("schema") == "production_script/3" and len(lines) >= 3 and words and not any(
                re.search(r"\b" + re.escape(w.lower()) + r"\b", text) for w in words):
            f(who, f"none of {who}'s signature words ({', '.join(words[:4])}...) appears in their {len(lines)} lines: "
                   "the written voice ignores the declared manner (DW-11)", "REVIEW")
    return out
