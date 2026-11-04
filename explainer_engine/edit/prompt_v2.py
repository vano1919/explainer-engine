# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/edit/prompt_v2.py`
# Target Module : explainer_engine/edit/prompt_v2.py
# Target Classes/Symbols : def compose(), def lint()
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

"""Prompt v2 (D-41, UR-22..UR-26): fixed slots, one light key, costume, the look v2 thread. stdlib only.

Order: shot type, subject (with its action and one emotion), world (costume, materials), ONE light key from the beat,
atmosphere, the look thread, the suffix. ``compose`` builds it; ``lint`` is ``world.resolver.check_text``.
"""

from __future__ import annotations

from explainer_engine.world.resolver import check_text, clause_for_beat, load_look, not_yet

SHOT_WORDS = {"A": "wide cinematic establishing shot", "B": "medium cinematic shot", "C": "tight cinematic insert"}


def compose(shot_type: str, subject: str, world: dict, beat: int, *, people: bool = False, plate: bool = False,
            costume_hint: str = "", look: dict | None = None) -> str:
    look = look or load_look()
    parts = [SHOT_WORDS[shot_type], subject.strip(" ,.")]
    if people and not plate:
        parts.append(look["figure"])
        parts.append(costume_hint or "dressed in " + ", ".join(world["host"]["costume"][:2]))
    # no flat list of materials: "hides, flint, bone" got painted as tents, daggers and bones on the ground (Day 1 v5)
    parts.append(clause_for_beat(world, beat))
    early = not_yet(world, beat)
    atmosphere = [a for a in world["host"]["atmosphere"][:3] if not (early and a in ("woodsmoke", "smoke"))][:2]
    parts.append(", ".join(atmosphere))
    if early:  # UR-27 story state: what the story has not made yet must not be in the frame
        parts.append("everything cold, dark and unlit, nothing burning or glowing anywhere in the frame")  # positive: naming it paints it
    return ", ".join(parts) + ", " + look["thread"] + look["suffix"]


def lint(prompt: str, world: dict, *, plate: bool = False, people: bool = False, visitors_named: list[str] | None = None,
         look: dict | None = None, beat: int | None = None) -> list[dict]:
    return check_text(prompt, world, look, plate=plate, people=people, visitors_named=visitors_named, beat=beat)
