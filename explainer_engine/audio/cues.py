"""Beat cues (VB-08, docs/STORY_ENGINE.md; the creator, 2026-10-19): a very short, light sound on a visual beat, so the
change on screen is noticed for an instant without the ear tiring. Built here from tones and noise (numpy only, free,
deterministic: the same name gives the same samples), so a cue never needs a library file.

Why short, quiet and few kinds (evidence in docs/STORY_ENGINE.md, VB section): a 60 ms tone in sync with a visual change
pulls attention to it ("pip and pop", Van der Burg et al. 2008), the benefit falls when every event carries a tone, and
interface sounds should be "as brief as possible", "in moderation" and "just a few sounds that are easily distinguishable"
(Google, conversation design: earcons). So: ten cues of 25-200 ms, at most -20 dB, never doubling a sound effect.
"""

from __future__ import annotations

import numpy as np

from explainer_engine.audio import foley as F

SR = F.SR
MIN_MS, MAX_MS = 20, 250  # VB-08 duration bounds
MAX_GAIN_DB, MIN_GAIN_DB, DEFAULT_GAIN_DB = -20.0, -36.0, -26.0
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
_CACHE: dict = {}


def render(name: str) -> np.ndarray:
    """Mono float32 at 48 kHz, peak 1, faded at both ends (no click)."""
    if name not in _CACHE:
        x = BUILD[name][0]()
        _CACHE[name] = _fade(x / (np.abs(x).max() + 1e-9))
    return _CACHE[name]


def length_ms(name: str, max_ms: float | None = None) -> float:
    if name == NONE:
        return 0.0
    ms = len(render(name)) / SR * 1000
    return min(ms, max_ms) if max_ms else ms
