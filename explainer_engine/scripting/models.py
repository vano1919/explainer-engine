# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2: Typed Dataclasses / Models for `production_script/4` Entities
# Target Module : explainer_engine/scripting/models.py
# Target Classes/Symbols : MusicCueSpec, SegmentSpec, CastMemberSpec, ProductionScriptV4
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Update `explainer_engine/scripting/models.py` so the in-memory script models represent all `production_script/4` fields without losing unknown/legacy keys:
#    - Add `CastMemberSpec` (`character_id`, `name`, `role`, `living`, `elevenlabs_voice_id`, `reference_sheet_path`, `lora_id`, `lora_scale=0.7`).
#    - Add `MusicCueSpec` (`track_id`, `mood`, `duck_db=-14.0`, `fade_in_sec`, `fade_out_sec`, `crossfade_sec`).
#    - Extend `SegmentSpec` with optional `/4` fields (`tension_zone`, `scene_type`, `character_id`, `on_screen_text`, `music_cue`, `sfx_tags`, `silence_duration_sec`, `tier_change_reason`, `payoff_thread_id`), plus a property alias `payoff_Thread_id` that reads/writes `payoff_thread_id` so both casings work seamlessly.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/scripting/models.py` only models v2/v3 segment fields and strips or ignores `/4` keys when converting between dicts and typed objects, plus `schemas/production_script_v4.schema.json:255` uses `payoff_Thread_id` (capital `T`) while `MASTER_MOLD.md` uses `payoff_thread_id`.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Provides full round-trip fidelity (`from_dict` / `to_dict`) for `production_script/4` while transparently bridging the `payoff_Thread_id` / `payoff_thread_id` casing discrepancy.
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
"""Stub specification module for explainer_engine/scripting/models.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
