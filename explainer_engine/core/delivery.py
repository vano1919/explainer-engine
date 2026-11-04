# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/delivery.py`
# Target Module : explainer_engine/core/delivery.py
# Target Classes/Symbols : def long_minutes(), def size(), def fps(), def shorts(), def frame_ms(), def shorts_frame(), def defaults()
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

"""Delivery defaults of an animated episode (BP-167, the creator's word of 2026-10-30 16:13 UTC, D-59 house).

The one reader of the registry row: the long video's target minutes, its frame size, its frame rate and the number of Shorts.
A job or script that names its own fps or size keeps it; the still-picture route (D-43) does not read this module.
"""

from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR


def long_minutes() -> int:
    return SR.T("BP-167", "long_minutes")


def size() -> tuple[int, int]:
    return SR.T("BP-167", "width"), SR.T("BP-167", "height")


def fps() -> int:
    return SR.T("BP-167", "fps")


def shorts() -> int:
    return SR.T("BP-167", "shorts")


def frame_ms(frame_rate: float | None = None) -> float:
    """One frame in ms at the job's fps (BP-54 ``frames`` x 1000 / fps); no fps given = the delivery default (BP-167)."""
    rate = fps() if frame_rate is None else frame_rate
    if rate <= 0:
        raise ValueError(f"fps must be positive, got {rate}")
    return SR.T("BP-54", "frames") * 1000.0 / rate


def shorts_frame() -> tuple[int, int]:
    """A Short's (width, height): the master frame rotated 90 degrees (BP-167), 1440 x 2560."""
    w, h = size()
    return h, w


def defaults() -> dict:
    w, h = size()
    return {"long_minutes": long_minutes(), "width": w, "height": h, "fps": fps(), "shorts": shorts()}
