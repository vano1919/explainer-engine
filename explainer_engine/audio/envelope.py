# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/envelope.py`
# Target Module : explainer_engine/audio/envelope.py
# Target Classes/Symbols : def envelope(), def mouth_states(), def _speaking()
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

"""A fallback mouth driven by loudness, for clips without phoneme timings. stdlib + numpy.

- ``envelope``: the loudness of a WAV in 1/12 s steps, streamed in 1-second blocks.
- ``mouth_states``: closed / half / open per step, only while someone speaks, each state held for at least two
  steps so the mouth never flutters.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/character.py
# changed: renamed beak -> mouth; logic unchanged

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

STEP = 1.0 / 12.0


def envelope(wav_path: Path, start: float = 0.0, seconds: float | None = None) -> list[float]:
    """RMS (linear) of the mid channel per 1/12 s step, streamed in 1-second blocks."""
    out: list[float] = []
    with wave.open(str(wav_path), "rb") as w:
        rate, channels = w.getframerate(), w.getnchannels()
        w.setpos(min(w.getnframes(), int(start * rate)))
        left = w.getnframes() - w.tell() if seconds is None else min(int(seconds * rate), w.getnframes() - w.tell())
        step = max(1, int(round(rate * STEP)))
        carry = np.zeros(0, dtype=np.float32)
        while left > 0:
            n = min(rate, left)
            raw = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
            left -= n
            mid = raw.reshape(-1, channels).mean(axis=1) if channels > 1 else raw
            data = np.concatenate([carry, mid])
            whole = len(data) // step * step
            if whole:
                out.extend(np.sqrt(np.mean(data[:whole].reshape(-1, step) ** 2, axis=1)).tolist())
            carry = data[whole:]
    return out


def mouth_states(levels: list[float], speaking: list[bool]) -> list[int]:
    """0 closed, 1 half, 2 open per step; only while someone speaks; every state held >= 2 steps."""
    voiced = [lv for lv, s in zip(levels, speaking) if s and lv > 0]
    ref = float(np.percentile(voiced, 75)) if voiced else 1.0
    states = []
    for lv, s in zip(levels, speaking):
        x = lv / ref if s and ref > 0 else 0.0
        states.append(2 if x > 0.75 else 1 if x > 0.3 else 0)
    held = states[:1]
    for k in range(1, len(states)):  # never flutter: a state lasts at least two steps
        held.append(states[k] if (k + 1 >= len(states) or states[k] == states[k + 1] or held[-1] != states[k - 1]) else held[-1])
    return held


def _speaking(levels: list[float], speech: list[tuple[float, float]], offset: float) -> list[bool]:
    flags = [False] * len(levels)
    for s, e in speech:
        for k in range(max(0, int((s - offset) / STEP)), min(len(levels), int(math.ceil((e - offset) / STEP)))):
            flags[k] = True
    return flags
