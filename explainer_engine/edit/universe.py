# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/edit/universe.py`
# Target Module : explainer_engine/edit/universe.py
# Target Classes/Symbols : def thread(), def assert_thread(), def sprite_prompt()
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

"""The universe thread for generated art (UR-22, the primary visual rule).

Every image prompt (pod pictures and Gemini cast sprites) carries the same drawing rules from the episode look, so characters,
props and places look drawn by one artist for one scene, in every era and every place. ``sprite_prompt`` builds the Gemini
prompt of a cast sprite from the look; ``assert_thread`` is the guard the generators call before any paid image.
"""

from __future__ import annotations

KEY = ("Full body, one figure only, feet visible, no text, no letters, no logo. Flat solid pure green #00FF00 background, no "
       "shadow on the background, no green on the figure.")


def thread(look: dict) -> str:
    t = str(look.get("universe_thread", "")).strip(" ,.")
    if not t:
        raise ValueError("the look has no universe_thread (UR-22)")
    return t


def assert_thread(prompt: str, look: dict) -> None:
    if thread(look).lower() not in prompt.lower():
        raise ValueError("the image prompt lacks the universe thread (UR-22): refusing to spend on it")


def sprite_prompt(who: str, look_of_person: str, pose: str, look: dict) -> str:
    """A cast sprite in the episode's universe: the person (from historical portraits), the emotional pose, the thread."""
    text = (f"A friendly CARICATURE of the historical figure {who}: {look_of_person}. Pose and expression: {pose}. "
            f"Adult, dignified-comic. Drawn in {thread(look)}. {KEY}")
    assert_thread(text, look)
    return text
