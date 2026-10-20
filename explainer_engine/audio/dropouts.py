"""Dropout scan (ED-12): finds digital-silence runs in a narration and reports those that cut into sound (speech level on one
side). A pause inserted in the middle of a word shows up here; on the Episode 1 read it found 67 of 131 before the fix.
numpy only: ``scan(audio, sr)``."""
from __future__ import annotations

import numpy as np


def _db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)) if len(x) else -120.0


def scan(audio: np.ndarray, sr: int, min_run: float = 0.05, loud_db: float = -42.0) -> dict:
    z = np.abs(audio) < 1e-7
    edges = np.flatnonzero(np.diff(np.concatenate([[0], z.astype(np.int8), [0]])))
    runs = [(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_run * sr]
    k = int(0.02 * sr)
    bad = []
    for a, b in runs:
        before, after = _db(audio[max(0, a - k):a]), _db(audio[b:b + k])
        if before > loud_db or after > loud_db:
            bad.append({"at": round(a / sr, 2), "seconds": round((b - a) / sr, 2), "before_db": round(before), "after_db": round(after)})
    return {"silence_runs": len(runs), "cut_into_sound": bad}
