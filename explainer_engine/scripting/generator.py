# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2: ScriptGenerator Default Upgrade to `production_script/4` & Retry Feedback Loop
# Target Module : explainer_engine/scripting/generator.py
# Target Classes/Symbols : ScriptGenerationConfig, ScriptGenerator
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    1. In `ScriptGenerationConfig` / `ScriptGenerator.__init__`:
#       - Add `target_schema_version: str = "production_script/4"` (allowing explicit override to `"production_script/2"` or `"production_script/3"` for backward-compatible unit tests).
#    2. In `ScriptGenerator._build_system_prompt()` and `_build_user_prompt()`:
#       - Inject the complete `production_script/4` contract requirements: top-level `cast[]` (`living: false` for historical figures under `CD-06`), `cold_open_type`, per-segment `tension_zone`, `scene_type`, `character_id`, `on_screen_text` (`<=4` words), `music_cue`, `sfx_tags` (`<=2`), `silence_duration_sec`, `tier_change_reason`, and `payoff_thread_id`.
#       - Enforce `BP-170` duration constraints directly in the generation prompt (`<=1.5s` in `cold_open`/`climax`, `<=2.0s` in `escalation`, `<=2.5s` in `grounding`/`coda` for Tier 1 `parallax_25d` and Tier 2 `qwen_nextpose`).
#    3. In `ScriptGenerator.generate()` validation-retry loop:
#       - Run `ScriptValidator.validate(candidate_script)` and feed itemized `MoldContractViolation` messages back into the repair prompt on retry.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/scripting/generator.py` still defaults to generating v2/v3 scripts (`"schema_version": "production_script/2"` or `"production_script/3"`) and does not instruct the LLM to emit `cast[]`, `tension_zone`, `scene_type`, `music_cue`, or `BP-170` duration caps, nor does it validate `/4` Mold rules during retries.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Upgrading `ScriptGenerator` to emit and self-validate `production_script/4` ensures newly generated scripts natively satisfy `MASTER_MOLD.md` v2.1.0 on the first pass or deterministic retry.
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
"""Stub specification module for explainer_engine/scripting/generator.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
