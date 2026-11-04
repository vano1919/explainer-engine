# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/imagegen/routing.py`
# Target Module : explainer_engine/imagegen/routing.py
# Target Classes/Symbols : def tier_of(), def route(), def batch_cost()
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

"""Picture routing (D-52): every picture is painted by Gemini on the batch tier, on one of three tiers. stdlib only.

Scope (N-06, 2026-10-30): the D-43 still-picture route. An animated episode's keyframes (D-77, D-80) are made on a pod with
Qwen-Image-2.1 and the xworld_v2 LoRA and are not routed here; its route is docs/SHOT_CONTINUITY.md and docs/SHOT_PROMPTS.md.

The tier is chosen by what the picture has to do, never by habit (docs/VISUAL_WORLD_ARCHITECTURE.md section 6):

* ``draft``    - Nano Banana 2.1 at 1K: composition and story tests, replaceable pictures. Same model as the final, so a
                 draft predicts the final (Flash-Lite at the same price ignored the world's palette and came back 1376x768,
                 Episode 1 test, 2026-10-17).
* ``standard`` - Nano Banana 2.1 at 2K: every scene picture. Episode 1's 74 pictures were made with it and accepted.
* ``premium``  - Gemini 3 Pro Image at 2K: only where the picture is reused across videos (cast references, thumbnail
                 elements) or a reveal shot that must hold several references at once; each one carries a reason, and at
                 most a tenth of an episode's pictures may be premium (PV-40).

4K is not routed: the video is 1080p/1440p and pictures are graded to 1.2 x the frame, which 2K covers.
Batch prices (USD per picture, ai.google.dev/gemini-api/docs/pricing, checked 2026-10-17) live in ``gemini.BATCH_PRICES``.
"""

from __future__ import annotations

from explainer_engine.imagegen.gemini import BATCH_PRICES, REFERENCE_USD

TIERS = {
    "draft": ("gemini-nano-banana-2.1", "1K"),
    "standard": ("gemini-nano-banana-2.1", "2K"),
    "premium": ("gemini-3-pro-image", "2K"),
}
DEFAULT_TIER = "standard"
PREMIUM_SHARE_MAX = 0.10


def tier_of(pic: dict) -> str:
    return pic.get("tier") or DEFAULT_TIER


def route(tier: str) -> tuple[str, str]:
    """(model, size) of a tier; an unknown tier is an error, never a silent default."""
    if tier not in TIERS:
        raise ValueError(f"unknown picture tier {tier!r}; one of {sorted(TIERS)}")
    return TIERS[tier]


def batch_cost(tier: str, references: int = 0) -> float:
    model, size = route(tier)
    return round(BATCH_PRICES[model][size] + references * REFERENCE_USD, 4)
