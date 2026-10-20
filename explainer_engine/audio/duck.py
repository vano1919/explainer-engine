"""Sidechain ducking without audible cuts (creator 2026-10-16): when a world sound hits (a strike, friction, a snap) the music
dips for its length and comes back, so the two never pile up into noise, and the dip must never sound like a cut.

The gain is computed on a 1 ms control grid: the sidechain's peak level per millisecond -> a target dip (0 dB below the
threshold, `depth_db` at full level) -> a hold -> one-pole smoothing in dB with separate attack and release times -> linear
interpolation back to samples. Every change is spread over at least `attack_ms`, so no step is ever larger than
depth / attack per millisecond. numpy only.
"""
from __future__ import annotations

import numpy as np

from explainer_engine.standards import sourced_rules as SR

CTRL_HZ = 1000  # one control value per millisecond
# BP-53: ducking is a dip, not a cut. The house numbers come from the registry (house_depth_db 9, attack 20 ms, release
# 280 ms, hold 80 ms) and sit inside its sourced ranges (depth 6-12 dB, attack 20-80 ms, release 250-700 ms, hold >= 50 ms);
# no gain step may exceed max_step_db_per_ms (the level JND). Change the registry, never these lines.
_T = SR.rule("BP-53")["thresholds"]
DEPTH_DB = float(_T["house_depth_db"])
ATTACK_MS = float(min(max(_T["house_attack_ms"], _T["attack_ms"][0]), _T["attack_ms"][1]))
RELEASE_MS = float(min(max(_T["house_release_ms"], _T["release_ms"][0]), _T["release_ms"][1]))
HOLD_MS = float(max(_T["house_hold_ms"], _T["hold_ms_min"]))
MAX_STEP_DB_PER_MS = float(_T["max_step_db_per_ms"])


def control_level(side: np.ndarray, sr: int) -> np.ndarray:
    """Peak |x| of every millisecond of the sidechain."""
    hop = max(1, sr // CTRL_HZ)
    n = int(np.ceil(len(side) / hop))
    pad = np.zeros(n * hop)
    pad[: len(side)] = np.abs(side)
    return pad.reshape(n, hop).max(axis=1)


def duck_gain(side: np.ndarray, sr: int, n: int | None = None, *, depth_db: float = DEPTH_DB, threshold: float = 0.02,
              knee: float = 4.0, attack_ms: float = ATTACK_MS, release_ms: float = RELEASE_MS, hold_ms: float = HOLD_MS) -> np.ndarray:
    """Gain curve (linear, length `n` or len(side)) that lowers another track while `side` sounds.

    `threshold` is the sidechain level (linear peak) where the dip starts; at `knee` x threshold it is full depth."""
    n = len(side) if n is None else n
    lvl = control_level(side, sr)
    x = np.clip((np.log(lvl + 1e-12) - np.log(threshold)) / np.log(knee), 0.0, 1.0)
    target = -depth_db * x
    h = int(hold_ms)
    if h > 0:  # hold: keep the deepest value of the last `hold_ms` (a sound's gaps do not pump the music)
        from numpy.lib.stride_tricks import sliding_window_view
        padded = np.concatenate([np.zeros(h), target])
        target = sliding_window_view(padded, h + 1).min(axis=1)
    a_att = np.exp(-1.0 / max(attack_ms, 1e-3))
    a_rel = np.exp(-1.0 / max(release_ms, 1e-3))
    g = np.empty_like(target)
    cur = 0.0
    for i, t in enumerate(target):  # ~1000 steps per second: a 10-minute mix is 600k steps
        a = a_att if t < cur else a_rel
        cur = a * cur + (1.0 - a) * t
        g[i] = cur
    hop = sr / CTRL_HZ
    xs = (np.arange(len(g)) + 0.5) * hop
    gain_db = np.interp(np.arange(n), xs, g, left=g[0] if len(g) else 0.0, right=g[-1] if len(g) else 0.0)
    return 10 ** (gain_db / 20.0)


def max_step_db_per_ms(gain: np.ndarray, sr: int) -> float:
    """Largest gain change in dB over any millisecond (the 'no cut' check: a step heard as a cut is several dB in < 1 ms)."""
    db = 20 * np.log10(np.maximum(gain, 1e-9))
    hop = max(1, sr // CTRL_HZ)
    return float(np.abs(db[hop:] - db[:-hop]).max()) if len(db) > hop else 0.0


def step_finding(gain: np.ndarray, sr: int) -> dict | None:
    """BP-53: the finding when a duck curve steps faster than the ear's level JND (None when it is a dip, not a cut)."""
    step = max_step_db_per_ms(gain, sr)
    if step <= MAX_STEP_DB_PER_MS:
        return None
    return {"rule": "BP-53", "severity": "REVIEW", "where": "music duck",
            "detail": f"gain steps {step:.2f} dB in a millisecond (at most {MAX_STEP_DB_PER_MS:g}): a dip heard as a cut"}
