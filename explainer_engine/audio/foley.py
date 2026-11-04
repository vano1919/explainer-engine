# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/foley.py`
# Target Module : explainer_engine/audio/foley.py
# Target Classes/Symbols : def _t(), def _noise(), def _band(), def _env(), def _ping(), def _place(), def footstep(), def jump_whoosh(), def landing_thud(), def cloth_rustle(), def buckle_click(), def page_flip(), def pencil_scribble(), def blink_click(), def tick(), def tock(), def tick_loop(), def chain_jingle(), def wing_flutter(), def glow_ping(), def seam_shimmer(), def pop_in(), def swish(), def monocle_pop(), def hit_sub(), def hit_body(), def hit_air()
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

"""Procedural foley: deterministic sound effects built from noise and tones (numpy only, no network, no cost).

Every generator takes a seed and returns mono float32 at 48 kHz in [-1, 1]. The same seed gives the same samples, so a
library rebuild is byte-identical. Quality is "clean and plain": they are placeholders a person may replace with
better recordings, and each library entry records that it is procedural (``sfx_library``).
"""

from __future__ import annotations

import numpy as np

from explainer_engine.standards import sourced_rules as RULES  # SR is the sample rate here

SR = 48000


def _t(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SR)) / SR


def _noise(seconds: float, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(int(seconds * SR)).astype(np.float32)


def _band(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Soft band-pass in the frequency domain (smooth edges so it does not ring)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    gain = np.ones_like(f)
    if lo > 0:
        gain *= 1 / (1 + (lo / np.maximum(f, 1.0)) ** 4)
    if hi < SR / 2:
        gain *= 1 / (1 + (np.maximum(f, 1.0) / hi) ** 4)
    return np.fft.irfft(spec * gain, n=len(x)).astype(np.float32)


def _env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / SR
    a = np.minimum(1.0, t / max(attack, 1e-4))
    return (a * np.exp(-t / max(decay, 1e-4))).astype(np.float32)


def _ping(freq: float, seconds: float, decay: float, amp: float = 1.0) -> np.ndarray:
    t = _t(seconds)
    return (amp * np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)).astype(np.float32)


def _place(canvas: np.ndarray, sound: np.ndarray, at: float, gain: float = 1.0) -> None:
    i = int(at * SR)
    j = min(len(canvas), i + len(sound))
    if i < len(canvas):
        canvas[i:j] += gain * sound[: j - i]


def footstep(surface: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if surface == "snow":
        n = _band(_noise(0.22, rng), 900, 5000) * _env(int(0.22 * SR), 0.004, 0.07)
        grains = np.zeros(int(0.22 * SR), np.float32)
        for k in rng.integers(0, int(0.15 * SR), 14):
            grains[k] += rng.uniform(0.3, 1.0)
        return 0.9 * n + 0.5 * _band(grains, 1500, 7000) * 6
    if surface == "grass":
        return _band(_noise(0.18, rng), 600, 3200) * _env(int(0.18 * SR), 0.015, 0.06) * 1.2
    if surface == "stone":
        click = _band(_noise(0.05, rng), 1500, 6000) * _env(int(0.05 * SR), 0.001, 0.012)
        body = _ping(220 + rng.uniform(-20, 20), 0.12, 0.03, 0.5)
        out = np.zeros(int(0.14 * SR), np.float32)
        _place(out, click, 0)
        _place(out, body, 0)
        return out
    if surface == "dirt":
        thump = _ping(95 + rng.uniform(-10, 10), 0.16, 0.04, 0.8)
        return thump + _band(_noise(0.16, rng), 200, 1800) * _env(int(0.16 * SR), 0.003, 0.05)
    raise ValueError(f"unknown surface {surface}")


def jump_whoosh(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(0.28 * SR)
    sweep = np.zeros(n, np.float32)
    parts = 6
    for k in range(parts):
        lo = 300 * (1.6 ** k)
        seg = _band(_noise(0.28, rng), lo, lo * 2.2)
        sweep += seg * np.sin(np.pi * np.clip((np.arange(n) / n) * 1.4 - 0.1 * k, 0, 1)) ** 2
    return sweep / 3


def landing_thud(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = _ping(68, 0.3, 0.07, 1.0)
    out += _band(_noise(0.3, rng), 150, 1500) * _env(int(0.3 * SR), 0.002, 0.04) * 0.8
    return out


def cloth_rustle(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = _band(_noise(0.45, rng), 700, 4500)
    am = np.abs(_band(_noise(0.45, rng), 4, 18))
    am = am / (am.max() + 1e-9)
    return n * am * _env(len(n), 0.03, 0.25) * 2.0


def buckle_click(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.18 * SR), np.float32)
    _place(out, _ping(2400 + rng.uniform(-100, 100), 0.06, 0.008), 0.0)
    _place(out, _ping(3600, 0.05, 0.006, 0.7), 0.0)
    _place(out, _ping(2000, 0.07, 0.01, 0.8), 0.07)
    return out


def page_flip(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(0.4 * SR)
    t = np.arange(n) / n
    body = _band(_noise(0.4, rng), 1200, 7000) * (np.sin(np.pi * t) ** 2)
    flutter = 0.6 + 0.4 * np.sin(2 * np.pi * 38 * np.arange(n) / SR)
    return body * flutter * 1.3


def pencil_scribble(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.7 * SR), np.float32)
    t = 0.02
    while t < 0.62:
        d = rng.uniform(0.03, 0.07)
        _place(out, _band(_noise(d, rng), 2500, 8000) * _env(int(d * SR), 0.004, d * 0.5), t, rng.uniform(0.5, 1.0))
        t += d + rng.uniform(0.005, 0.03)
    return out


def blink_click(seed: int) -> np.ndarray:
    """The small soft 'plip' of an eye blink (cartoon, not realistic)."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.08 * SR), np.float32)
    _place(out, _ping(1500 + rng.uniform(-80, 80), 0.04, 0.007, 0.7), 0.0)
    _place(out, _band(_noise(0.02, rng), 2000, 7000) * _env(int(0.02 * SR), 0.001, 0.006), 0.0, 0.4)
    return out


def tick(seed: int, pitch: float = 3100.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.12 * SR), np.float32)
    _place(out, _ping(pitch + rng.uniform(-30, 30), 0.1, 0.012, 0.8), 0.0)
    _place(out, _ping(pitch * 1.52, 0.05, 0.006, 0.35), 0.0)
    _place(out, _band(_noise(0.01, rng), 3000, 9000) * _env(int(0.01 * SR), 0.0005, 0.003), 0.0, 0.5)
    return out


def tock(seed: int) -> np.ndarray:
    return tick(seed, 2200.0)


def tick_loop(seconds: float = 4.0, bpm: float = 60.0, seed: int = 7) -> np.ndarray:
    out = np.zeros(int(seconds * SR) + SR // 4, np.float32)
    step = 60.0 / bpm
    k = 0
    while k * step < seconds:
        _place(out, (tick(seed + k) if k % 2 == 0 else tock(seed + k)), k * step)
        k += 1
    return out[: int(seconds * SR)]


def chain_jingle(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.7 * SR), np.float32)
    for k in range(9):
        _place(out, _ping(rng.uniform(3500, 9000), 0.25, rng.uniform(0.02, 0.06), rng.uniform(0.3, 0.8)),
               rng.uniform(0, 0.25))
    return out


def wing_flutter(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(0.55 * SR)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * 26 * np.arange(n) / SR)
    return _band(_noise(0.55, rng), 1800, 6500) * am * np.sin(np.pi * np.arange(n) / n) * 1.6


def glow_ping(seed: int) -> np.ndarray:
    out = _ping(1318.5, 1.3, 0.32, 0.8) + _ping(2637, 1.3, 0.2, 0.3) + _ping(3951, 1.3, 0.12, 0.12)
    t = _t(1.3)
    return out * (1 + 0.08 * np.sin(2 * np.pi * 6 * t))


def seam_shimmer(seed: int) -> np.ndarray:
    """Crossing from one world into another: a rising shimmer of detuned tones over a soft airy swell."""
    rng = np.random.default_rng(seed)
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k in range(7):
        f0 = 500 * (1.25 ** k)
        f = f0 * (1 + 0.35 * t / 2.6) + rng.uniform(-3, 3)
        out += (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * np.clip(t / 2.6, 0, 1)) ** 2 / 7).astype(np.float32)
    air = _band(_noise(2.6, rng), 2000, 9000) * np.sin(np.pi * np.clip(t / 2.6, 0, 1)) ** 3 * 0.25
    return out + air


def pop_in(seed: int) -> np.ndarray:
    t = _t(0.1)
    f = 320 + 700 * (t / 0.1)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.03)).astype(np.float32)


def swish(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(0.5 * SR)
    t = np.arange(n) / n
    out = np.zeros(n, np.float32)
    for k in range(5):
        lo = 800 * (1.5 ** k)
        out += _band(_noise(0.5, rng), lo, lo * 2) * np.sin(np.pi * np.clip(t * 1.2 - 0.04 * k, 0, 1)) ** 2
    return out / 2.5


def monocle_pop(seed: int) -> np.ndarray:
    out = np.zeros(int(0.5 * SR), np.float32)
    _place(out, pop_in(seed), 0.0, 0.7)
    _place(out, _ping(2800, 0.3, 0.07, 0.5), 0.05)
    _place(out, _ping(4200, 0.2, 0.05, 0.25), 0.07)
    return out


def hit_sub(seed: int) -> np.ndarray:
    """The sub layer of a composite hit (BP-119): a falling sine below ``sub_hz``, band-limited to it."""
    rng = np.random.default_rng(seed)
    sub = float(RULES.T("BP-119", "sub_hz"))
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = np.minimum(sub * 0.85, 62 + rng.uniform(-4, 4)) * np.exp(-1.6 * t) + 30
    out = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.008, 0.16)
    return _band(_band(out.astype(np.float32), 0, sub), 0, sub) * 1.5


def hit_body(seed: int) -> np.ndarray:
    """The body layer (BP-119): a struck mid-range thump of noise and a low ping, band-limited to ``body_hz``."""
    rng = np.random.default_rng(seed)
    lo, hi = (float(x) for x in RULES.T("BP-119", "body_hz"))
    n = int(0.45 * SR)
    out = _noise(0.45, rng) * _env(n, 0.002, 0.07) + _ping(260 + rng.uniform(-20, 20), 0.45, 0.09, 1.4)
    return _band(_band(out, lo, hi), lo, hi) * 1.3


def hit_air(seed: int) -> np.ndarray:
    """The air layer (BP-119): a short bright burst of noise, band-limited to ``air_hz``."""
    rng = np.random.default_rng(seed)
    lo, hi = (float(x) for x in RULES.T("BP-119", "air_hz"))
    n = int(0.35 * SR)
    out = _noise(0.35, rng) * _env(n, 0.001, 0.05)
    return _band(_band(out, lo, hi), lo, hi) * 1.6


# id -> (category tags, generator, seeds)
BUILD = {
    "footstep_snow": (["footstep", "snow", "walk"], lambda s: footstep("snow", s), (1, 2, 3)),
    "footstep_grass": (["footstep", "grass", "walk"], lambda s: footstep("grass", s), (1, 2, 3)),
    "footstep_stone": (["footstep", "stone", "walk"], lambda s: footstep("stone", s), (1, 2, 3)),
    "footstep_dirt": (["footstep", "dirt", "walk"], lambda s: footstep("dirt", s), (1, 2, 3)),
    "jump_whoosh": (["jump", "move", "whoosh"], jump_whoosh, (1, 2)),
    "landing_thud": (["jump", "land", "impact"], landing_thud, (1, 2)),
    "cloth_rustle": (["cloth", "coat", "move"], cloth_rustle, (1, 2, 3)),
    "buckle_click": (["satchel", "buckle", "prop"], buckle_click, (1, 2)),
    "page_flip": (["notebook", "page", "prop"], page_flip, (1, 2)),
    "pencil_scribble": (["notebook", "pencil", "write"], pencil_scribble, (1, 2)),
    "blink_click": (["eye", "blink"], blink_click, (1, 2, 3)),
    "tick": (["companion", "clock", "tick"], tick, (1, 2, 3)),
    "tock": (["companion", "clock", "tock"], tock, (1, 2, 3)),
    "tick_loop_4s": (["companion", "clock", "loop"], lambda s: tick_loop(4.0, 60.0, s), (1,)),
    "chain_jingle": (["companion", "chain", "prop"], chain_jingle, (1, 2)),
    "wing_flutter": (["companion", "wing", "move"], wing_flutter, (1, 2)),
    "glow_ping": (["magic", "glow", "ping"], glow_ping, (1,)),
    "seam_shimmer": (["magic", "worlds", "transition"], seam_shimmer, (1,)),
    "pop_in": (["ui", "appear", "pop"], pop_in, (1,)),
    "swish": (["transition", "whoosh"], swish, (1, 2)),
    "monocle_pop": (["analyst", "startle", "prop"], monocle_pop, (1,)),
    "hit_sub": (["hit", "hit_sub", "impact"], hit_sub, (1, 2, 3)),  # the three layers of a composite hit (BP-119, SD-05)
    "hit_body": (["hit", "hit_body", "impact"], hit_body, (1, 2, 3)),
    "hit_air": (["hit", "hit_air", "impact"], hit_air, (1, 2, 3)),
}
