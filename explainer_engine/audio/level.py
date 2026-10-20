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
