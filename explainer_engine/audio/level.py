# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/level.py`
# Target Module : explainer_engine/audio/level.py
# Target Classes/Symbols : def _mean(), def level_gain(), def level_voice()
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

"""Voice leveler (creator 2026-10-16: the ElevenLabs read sounded "unstable"): per-sentence loudness on the Day 1 read swung
from -35.5 to -22.6 dB (std 2.5 dB). A slow gain rider pulls every spoken stretch toward the same level, within a limit, so
emphasis stays but a whispered "Wise." is not 13 dB under a shouted "Two!". numpy only, O(n).
"""
from __future__ import annotations

import numpy as np


def _mean(x: np.ndarray, k: int) -> np.ndarray:
    k = max(1, int(k))
    c = np.concatenate([[0.0], np.cumsum(x)])
    lo = np.clip(np.arange(len(x)) - k // 2, 0, len(x))
    hi = np.clip(lo + k, 0, len(x))
    return (c[hi] - c[lo]) / k


def level_gain(voice: np.ndarray, sr: int, target_db: float = -27.0, max_boost_db: float = 4.0, max_cut_db: float = 5.0,
               window_s: float = 0.35, strength: float = 0.7, floor_db: float = -48.0, release_s: float = 0.2) -> np.ndarray:
    """Linear gain per sample. ``strength`` 0..1 is how much of the distance to ``target_db`` is closed; stretches below
    ``floor_db`` (pauses, breath) keep the gain of the speech before them so noise is not lifted."""
    lvl = 10 * np.log10(np.maximum(_mean(voice ** 2, sr * window_s), 1e-12))
    want = np.clip((target_db - lvl) * strength, -max_cut_db, max_boost_db)
    speech = lvl > floor_db
    g = np.where(speech, want, np.nan)
    idx = np.arange(len(g))
    ok = ~np.isnan(g)
    if not ok.any():
        return np.ones(len(voice))
    g = np.interp(idx, idx[ok], g[ok])  # hold across pauses
    out = _mean(g, sr * release_s * 2)  # centred smoothing of an already smooth curve: no step, no pumping
    return 10 ** (out / 20)


def level_voice(voice: np.ndarray, sr: int, **kw) -> np.ndarray:
    return voice * level_gain(voice, sr, **kw)
