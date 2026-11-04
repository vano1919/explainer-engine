# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M2 (Research Brief & Counterfactual/Historical Source Dossier Synchronization): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/research/__init__.py`
# Target Module : explainer_engine/research/__init__.py
# Target Classes/Symbols : (module-level definitions)
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this research subsystem module with `production_script/4` (`MASTER_MOLD.md` v2.1.0):
#    - Populate structured cast candidates (`character_id`, `name`, `living: bool`, `historical_era`, primary historical quote sources) so `CastRegistry` and `verify_voice_clearance` (`CD-06`) know deterministically whether a figure is a deceased historical character (`living=False`, eligible for `D-90` voicing) or a living person (`living=True`, banned under `D-62`/`PV-55`).
#    - Tag geographic entities with ISO-A3 country codes for `MapRenderer` (`ne_50m_admin_0_countries.geojson`, `D-96`) and tag tension-zone beat candidates (`cold_open` hook facts, `grounding` citations, `escalation` causal chains, `climax` turning point, `coda` payoff).
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this research module outputs v2/v3 research briefs without `living: bool` cast metadata (`CD-06`), ISO-A3 map territory codes (`D-96`), or tension-zone beat classifications (`D-84`).
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Feeds `ScriptGenerator`, `CastRegistry`, and `MapRenderer` with structured, citation-backed inputs so `/4` scripts require zero manual patching.
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
