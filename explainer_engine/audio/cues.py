# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/cues.py`
# Target Module : explainer_engine/audio/cues.py
# Target Classes/Symbols : def _fade(), def _sweep(), def _tick(), def _tap(), def _whiff(), def _thud(), def render(), def length_ms()
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

"""Beat cues (VB-08, docs/STORY_ENGINE.md; the creator, 2026-10-19): a very short, light sound on a visual beat, so the
change on screen is noticed for an instant without the ear tiring. Built here from tones and noise (numpy only, free,
deterministic: the same name gives the same samples), so a cue never needs a library file.

Why short, quiet and few kinds (evidence in docs/STORY_ENGINE.md, VB section): a 60 ms tone in sync with a visual change
pulls attention to it ("pip and pop", Van der Burg et al. 2008), the benefit falls when every event carries a tone, and
interface sounds should be "as brief as possible", "in moderation" and "just a few sounds that are easily distinguishable"
(Google, conversation design: earcons). So: ten cues inside BP-64's length and level (an earcon, not a one-shot: BP-58's
0.1 s floor is for stings and impacts), never doubling a sound effect; a repeated cue rotates BP-57's pitch jitter.
"""

from __future__ import annotations

import numpy as np

from explainer_engine.audio import foley as F
from explainer_engine.standards import sourced_rules as RULES  # SR is the sample rate here

SR = F.SR
MIN_MS, MAX_MS = RULES.T("BP-64", "cue_ms")  # VB-08 duration bounds (house, D-58)
MIN_GAIN_DB, MAX_GAIN_DB = (float(x) for x in RULES.T("BP-64", "gain_db"))
DEFAULT_GAIN_DB = float(RULES.T("BP-64", "default_gain_db"))
NONE = "none"


def _fade(x: np.ndarray, ms_in: float = 2.0, ms_out: float = 8.0) -> np.ndarray:
    x = x.astype(np.float32).copy()
    a, b = min(len(x), int(ms_in * SR / 1000)), min(len(x), int(ms_out * SR / 1000))
    if a:
        x[:a] *= np.linspace(0, 1, a, dtype=np.float32)
    if b:
        x[-b:] *= np.linspace(1, 0, b, dtype=np.float32)
    return x


def _sweep(f0: float, f1: float, seconds: float, decay: float) -> np.ndarray:
    t = F._t(seconds)
    f = f0 + (f1 - f0) * t / seconds
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / decay)).astype(np.float32)


def _tick() -> np.ndarray:
    return F._band(F._noise(0.025, np.random.default_rng(11)), 2500, 9000) * F._env(int(0.025 * SR), 0.0005, 0.004)


def _tap() -> np.ndarray:
    return F._ping(620, 0.045, 0.012) + 0.4 * F._band(F._noise(0.045, np.random.default_rng(12)), 800, 3000) * F._env(
        int(0.045 * SR), 0.0005, 0.006)


def _whiff() -> np.ndarray:
    n = int(0.12 * SR)
    shape = np.sin(np.pi * np.arange(n) / n) ** 2
    return F._band(F._noise(0.12, np.random.default_rng(13)), 1500, 6000) * shape.astype(np.float32) * 0.8


def _thud() -> np.ndarray:
    return _sweep(150, 70, 0.09, 0.03)


BUILD = {  # name -> (generator, what it suits)
    "tick": (_tick, "a word or label appears"),
    "tap": (_tap, "a label is pinned to a spot"),
    "pop": (lambda: F.pop_in(1)[: int(0.06 * SR)], "an object or sticker pops in"),
    "blip": (lambda: F._ping(880, 0.07, 0.02), "a number, a chart, a sign"),
    "pluck": (lambda: F._ping(523.25, 0.12, 0.035) + F._ping(1046.5, 0.12, 0.02, 0.3), "a ring is drawn round a thing"),
    "chime": (lambda: F._ping(1568, 0.18, 0.05, 0.7) + F._ping(3136, 0.18, 0.03, 0.2), "a reveal, a check, a joyful take"),
    "whiff": (_whiff, "an arrow or a quick move"),
    "thud": (_thud, "a cross, a heavy fact, an angry take"),
    "rise": (lambda: _sweep(500, 1100, 0.15, 0.06), "up: more, growth, arrow up"),
    "fall": (lambda: _sweep(900, 400, 0.15, 0.06), "down: less, loss, arrow down, a sad take"),
}
NAMES = tuple(BUILD) + (NONE,)
_J = float(RULES.T("BP-57", "pitch_jitter"))
VARIANTS = (1.0, round(1.0 - _J, 6), round(1.0 + _J, 6))  # BP-57 / VB-10: a reused sound takes the next pitch, never identical
_CACHE: dict = {}


def render(name: str, variant: int = 0) -> np.ndarray:
    """Mono float32 at 48 kHz, peak 1, faded at both ends (no click). ``variant`` picks one of three deterministic
    pitch shifts (plain resampling): the mixer rotates them per sound (VB-10), so a cue heard again reads as another
    press of the same kind, never the identical waveform (the creator's "one press plays many times", 2026-10-19)."""
    v = variant % len(VARIANTS)
    if (name, v) not in _CACHE:
        x = BUILD[name][0]()
        x = _fade(x / (np.abs(x).max() + 1e-9))
        r = VARIANTS[v]
        if r != 1.0:
            idx = np.arange(0.0, len(x) - 1, r)
            x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
        _CACHE[(name, v)] = x
    return _CACHE[(name, v)]


def length_ms(name: str, max_ms: float | None = None) -> float:
    if name == NONE:
        return 0.0
    ms = len(render(name)) / SR * 1000
    return min(ms, max_ms) if max_ms else ms
