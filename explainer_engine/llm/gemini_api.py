# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/llm/gemini_api.py`
# Target Module : explainer_engine/llm/gemini_api.py
# Target Classes/Symbols : class GeminiRefused (methods: ), def monthly_ceiling(), def reserve(), def complete()
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

"""The Gemini API (the Argon reviewer): its monthly ceiling and nothing else yet.

The creator's line is ``gemini_api`` in ``config/spend_caps.json`` (max_usd per calendar month, 2026-10-30). No client exists, so
``complete`` always refuses; ``reserve`` is the check the client will call before a paid request (the 80 % stop of the ledger,
invariant 2). The picture calls of ``imagegen/gemini.py`` keep their own per-episode line and are not touched.
"""

from __future__ import annotations

from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import STOP_FRACTION


# TODO [CLAUDE-CLASS-SYNC: GeminiRefused] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `GeminiRefused` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class GeminiRefused(RuntimeError):
    """A Gemini API call was asked for that this repository does not allow yet."""


def monthly_ceiling() -> float:
    return float(spend_caps.gemini_api()["max_usd"])


def reserve(estimate_usd: float, spent_month_usd: float) -> float:
    """The month's spend after this request, or GeminiRefused when it would pass 80 % of the ceiling (stop and ask)."""
    if estimate_usd < 0 or spent_month_usd < 0:
        raise GeminiRefused("a Gemini request cannot cost or have cost less than nothing")
    after = spent_month_usd + estimate_usd
    limit = monthly_ceiling() * STOP_FRACTION
    if after > limit + 1e-9:
        raise GeminiRefused(f"Gemini API: ${after:.2f} this month would pass {STOP_FRACTION:.0%} of the ${monthly_ceiling():g} ceiling "
                            "(config/spend_caps.json gemini_api); stop and ask the creator")
    return after


def complete(*_args, **_kwargs):
    raise GeminiRefused("the Gemini API client is not built yet: nothing may call it (docs/PROGRESS.md, D9 2026-10-30)")
