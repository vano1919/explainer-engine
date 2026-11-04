# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/errors.py`
# Target Module : explainer_engine/core/errors.py
# Target Classes/Symbols : class EngineError (methods: ), class ContractError (methods: ), class ConfigError (methods: ), class RetryableError (methods: ), class NeedsReview (methods: ), class ValidationError (methods: __init__), class PipelineFailure (methods: __str__)
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

"""Deterministic error types. The pipeline fails loudly and specifically, and says which kind of failure it is:
retryable (transient), permanent (configuration/contract) or a human-review stop."""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/errors.py
# changed: cue/schedule errors removed; RetryableError, NeedsReview added

from __future__ import annotations

from dataclasses import dataclass, field


# TODO [CLAUDE-CLASS-SYNC: EngineError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `EngineError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class EngineError(Exception):
    """Base class for all engine failures."""


# TODO [CLAUDE-CLASS-SYNC: ContractError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `ContractError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class ContractError(EngineError):
    """A document did not satisfy its versioned schema or a referential rule (permanent: fix the input)."""


# TODO [CLAUDE-CLASS-SYNC: ConfigError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `ConfigError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class ConfigError(EngineError):
    """Invalid or missing configuration (permanent: fix the config before the job starts)."""


# TODO [CLAUDE-CLASS-SYNC: RetryableError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `RetryableError` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class RetryableError(EngineError):
    """A transient failure (network, a renderer crash) that may succeed on a bounded retry."""


# TODO [CLAUDE-CLASS-SYNC: NeedsReview] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `NeedsReview` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class NeedsReview(EngineError):
    """A gate needs a human decision; the job stops with NEEDS_REVIEW after saving everything."""


# TODO [CLAUDE-CLASS-SYNC: ValidationError] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `ValidationError` (methods: __init__) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class ValidationError(EngineError):
    """Deterministic validation failed; ``findings`` lists each failed check."""

    def __init__(self, findings: list[dict]) -> None:
        self.findings = findings
        super().__init__("; ".join(f"{f['check']}: {f['detail']}" for f in findings))


# TODO [CLAUDE-CLASS-SYNC: PipelineFailure] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `PipelineFailure` (methods: __str__) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
@dataclass
class PipelineFailure(EngineError):
    """A job stopped at a known stage, with a readable report."""

    stage: str
    message: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.stage}] {self.message}"
