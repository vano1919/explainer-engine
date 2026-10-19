"""Voice consistency check (creator 2026-10-16: "from 3:17 almost to the end another voice comes in").

One ElevenLabs v4 generation of the whole Day 1 read (2,917 characters, 223 s) drifted: from about 190 s of the read the
timbre went darker and duller (spectral tilt -25 dB against a median of -21.3 dB, centroid 1,080 Hz against ~1,250 Hz),
which a listener hears as a different actor. Long single generations drift; the fix is chunked reads
(``script.tts_chunks``), and this check finds drift in any read before it is used: windows whose timbre is far from the
read's own median are REVIEW (listen there). numpy only.
"""
from __future__ import annotations

import numpy as np

TILT_DB = 3.5      # spectral tilt (2-5 kHz vs < 500 Hz) further than this from the read's median
CENTROID_REL = 0.22  # or a spectral centroid more than 22 % off


def _timbre(seg: np.ndarray, sr: int) -> tuple[float, float] | None:
    """(median spectral centroid, median tilt in dB) of the voiced 40 ms frames; None under 20 voiced frames."""
    n = int(0.04 * sr)
    cents, tilts = [], []
    for i in range(0, len(seg) - n, n):
        fr = seg[i:i + n] * np.hanning(n)
        if np.sqrt((fr ** 2).mean()) < 0.01:
            continue
        sp = np.abs(np.fft.rfft(fr))
        fq = np.fft.rfftfreq(n, 1 / sr)
        cents.append(float((sp * fq).sum() / (sp.sum() + 1e-12)))
        lo, hi = sp[fq < 500].sum(), sp[(fq > 2000) & (fq < 5000)].sum()
        tilts.append(float(20 * np.log10(hi / (lo + 1e-12) + 1e-12)))
    if len(cents) < 20:
        return None
    return float(np.median(cents)), float(np.median(tilts))


def window_features(x: np.ndarray, sr: int, win_s: float = 15.0) -> list[dict]:
    out = []
    for a in range(0, max(1, int(len(x) / sr - win_s / 3)), int(win_s)):
        f = _timbre(x[int(a * sr):int((a + win_s) * sr)], sr)
        if f:
            out.append({"start": float(a), "end": float(min(a + win_s, len(x) / sr)), "centroid": f[0], "tilt_db": f[1]})
    return out


def _outliers(w: list[dict], label: str) -> list[dict]:
    if len(w) < 3:
        return []
    mt = float(np.median([r["tilt_db"] for r in w]))
    mc = float(np.median([r["centroid"] for r in w]))
    found = []
    for r in w:
        dt, dc = r["tilt_db"] - mt, r["centroid"] / mc - 1
        if abs(dt) > TILT_DB or abs(dc) > CENTROID_REL:
            found.append({"rule": "VOICE-1", "severity": "REVIEW", "where": f"{r['start']:.0f}-{r['end']:.0f} s",
                          "detail": f"timbre off {label} median (tilt {dt:+.1f} dB, centroid {dc:+.0%}): listen; "
                                    "a different-sounding voice means re-read this chunk"})
    return found


def check(x: np.ndarray, sr: int, win_s: float = 15.0) -> tuple[list[dict], list[dict]]:
    """(windows, findings). A finding is REVIEW: emotion moves timbre too, so a person listens before a re-read."""
    w = window_features(x, sr, win_s)
    return w, _outliers(w, "the read's")


def check_speakers(x: np.ndarray, sr: int, turns: list[tuple[str, float, float]]) -> tuple[list[dict], list[dict]]:
    """Voiced dialogue (D-45): several voices in one read are not drift. Each speaker's turns ``(speaker, start, end)``
    are compared with that speaker's own median, so a hero whose turn sounds unlike their other turns is found and the
    other voice is not."""
    windows, found = [], []
    for who in dict.fromkeys(t[0] for t in turns):
        w = []
        for _, a, b in (t for t in turns if t[0] == who):
            f = _timbre(x[int(a * sr):int(b * sr)], sr)
            if f:
                w.append({"speaker": who, "start": float(a), "end": float(b), "centroid": f[0], "tilt_db": f[1]})
        windows += w
        found += [dict(r, detail=f"{who}: " + r["detail"]) for r in _outliers(w, f"{who}'s")]
    return windows, found
