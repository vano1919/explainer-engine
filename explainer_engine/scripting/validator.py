# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2: Script Validator Synchronization with `schema_version` & `mold_contract`
# Target Module : explainer_engine/scripting/validator.py
# Target Classes/Symbols : ValidationIssue, ValidationResult, ScriptValidator, validate_script
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    1. In `ScriptValidator.validate(script: dict[str, Any]) -> ValidationResult`:
#       - Call `detect_schema_version(script)` from `explainer_engine.scripting.schema_version`.
#       - Run JSON Schema validation via `explainer_engine.validate.validate_production_script(script)`.
#       - When `detect_schema_version(script) == "production_script/4"`, invoke `validate_mold_contract(script)` from `explainer_engine.scripting.mold_contract`, `validate_zone_pacing(script)` from `explainer_engine.pacing.tension_zones`, and `validate_shot_variety(script)` from `explainer_engine.pacing.shot_variety`.
#       - Normalize the casing alias `payoff_Thread_id` -> `payoff_thread_id` (while accepting both during input validation so neither schema nor callers break on `MASTER_MOLD.md` vs `production_script_v4.schema.json` casing).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/scripting/validator.py` currently validates legacy v2/v3 script rules (word counts, basic segment fields, beat durations) without checking `/4` fields (`cast[]`, `tension_zone`, `scene_type`, `cold_open_type`, `music_cue`, `on_screen_text`, `BP-170` Tier 1/Tier 2 static caps, or `D-62`/`D-90` voice clearance).
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Unifies v2/v3 legacy validation and `/4` Master Mold validation behind a single `ScriptValidator` entry point so `ScriptGenerator` and `pipeline.py` catch every Master Mold violation before spending TTS or GPU budget.
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
"""Stub specification module for explainer_engine/scripting/validator.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
