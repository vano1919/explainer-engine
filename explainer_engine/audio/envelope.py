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
