"""Effect audibility against the bed, and a click detector: two measurements of a rendered mix (numpy only, free).

Method idea from earshot's ``real-sound`` QA (Leonxlnx/earshot, MIT, ``skills/real-sound/scripts/qa.py``: "audibility" and
"clicks"). Re-implemented here from the description alone: no code is copied, the filters differ (a brick-wall FFT band
split instead of Butterworth), so there is no provenance row.

What is measured (always, with no judgement):
  * ``audibility``: the effect's level over the bed's, per 1/3-octave band (IEC 61260 base-ten centres, 25 Hz..20 kHz), over
    the effect's loudest ``window_s`` stretch; and at the band where the effect is strongest;
  * ``clicks``: samples of the content above ``hf_hz`` that stand out from their neighbourhood and how much of that burst's
    energy sits inside ``burst_s`` (a click is concentrated, a designed attack is not).

What is judged (D-59, rule one): NOTHING without a sourced number. The registry has no rule for an effect-over-bed margin or a
click detector; earshot's own values (6 / 3 / 0 dB margins, 14 kHz, 9x, 6x, 0.8) are one author's measured norms of seven
launch films: one source type, so not binding. ``Limits`` therefore holds ``None`` for every judging number and ``check``
returns one ``NOT_RUN`` finding per measurement that was given, carrying the measured values. When a number gets two source
types (and a BP row), the caller passes it in ``Limits`` and the same call returns FAIL/REVIEW findings.

Requirement IDs: OR-A03, OR-A15, OR-A24 (a sound that cannot be heard is not "per-shot sound design"; a click is a defect).
Findings: AUD-01 effect under the bed's margin, AUD-02 effect silent, CLK-01 click in the mix; ``NOT_RUN`` otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

WINDOW_S = 0.06  # the stretch the effect is judged over (a measurement window, not a threshold)
CAP_DB = 60.0  # margins are capped to +-this so empty bands do not give infinities
_EPS = 1e-30

# IEC 61260 base-ten nominal band centres, 25 Hz .. 20 kHz
BAND_CENTRES = tuple(1000.0 * 10 ** (0.1 * n) for n in range(-16, 14))


@dataclass(frozen=True)
class Limits:
    """Judging numbers. ``None`` = no sourced value exists: the check reports the measurement as ``NOT_RUN``."""

    masked_below_db: float | None = None  # AUD-01: dominant-band margin under this = the bed hides the effect
    silent_peak_dbfs: float | None = None  # AUD-02: effect peak under this = nothing there (a missed trim)
    hf_hz: float | None = None  # clicks: the high-pass corner
    local_ratio: float | None = None  # clicks: |hf| over the RMS of the +-local_s neighbourhood
    near_ratio: float | None = None  # clicks: |hf| over the RMS of the +-near_s neighbourhood
    concentration_min: float | None = None  # clicks: share of the burst energy inside +-burst_s
    local_s: float = 0.010
    near_s: float = 0.002
    burst_s: float = 0.0005
    wide_s: float = 0.005
    severity: str = "REVIEW"


def _as_signal(x, name: str) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 1 or a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be a non-empty 1-D finite array")
    return a


def _db(power: float) -> float:
    return 10.0 * math.log10(max(float(power), _EPS))


def loudest_window(x: np.ndarray, sr: int, window_s: float = WINDOW_S) -> int:
    """Start sample of the ``window_s`` stretch with the most energy (1 ms hop)."""
    n = max(1, int(round(window_s * sr)))
    if x.size <= n:
        return 0
    c = np.concatenate([[0.0], np.cumsum(x * x)])
    starts = np.arange(0, x.size - n + 1, max(1, sr // 1000))
    return int(starts[int(np.argmax(c[starts + n] - c[starts]))])


def band_powers(seg: np.ndarray, sr: int) -> np.ndarray:
    """Power per 1/3-octave band of one windowed segment (Hann, rfft; bins summed between the band edges)."""
    w = np.hanning(seg.size)
    spec = np.abs(np.fft.rfft(seg * w)) ** 2 / max(float((w * w).sum()), _EPS)
    freqs = np.fft.rfftfreq(seg.size, 1.0 / sr)
    out = np.zeros(len(BAND_CENTRES))
    for i, fc in enumerate(BAND_CENTRES):
        lo, hi = fc * 10 ** -0.05, fc * 10 ** 0.05
        out[i] = spec[(freqs >= lo) & (freqs < hi)].sum()
    return out


def audibility(effect, bed, sr: int, window_s: float = WINDOW_S) -> dict:
    """Effect over bed, per band, over the effect's loudest window. ``effect`` and ``bed`` are mono, the same length and
    rate, as the rendered stems (``bed`` = music + ambience). Returns the measured numbers; no verdict."""
    e, b = _as_signal(effect, "effect"), _as_signal(bed, "bed")
    if e.size != b.size:
        raise ValueError("effect and bed must be the same length")
    if sr <= 0:
        raise ValueError("sr must be positive")
    peak = float(np.max(np.abs(e)))
    peak_dbfs = 20.0 * math.log10(peak) if peak > 0 else -math.inf
    if peak == 0:
        return {"peak_dbfs": peak_dbfs, "silent": True, "window_start_s": 0.0, "dominant_hz": None, "margin_db": None,
                "bands": []}
    n = min(e.size, max(8, int(round(window_s * sr))))
    s = loudest_window(e, sr, window_s)
    pe, pb = band_powers(e[s:s + n], sr), band_powers(b[s:s + n], sr)
    k = int(np.argmax(pe))
    margins = np.clip(10 * np.log10(np.maximum(pe, _EPS) / np.maximum(pb, _EPS)), -CAP_DB, CAP_DB)
    return {"peak_dbfs": round(peak_dbfs, 2), "silent": False, "window_start_s": round(s / sr, 4),
            "dominant_hz": round(BAND_CENTRES[k], 1), "margin_db": round(float(margins[k]), 2),
            "bands": [{"hz": round(fc, 1), "effect_db": round(_db(p), 1), "margin_db": round(float(m), 1)}
                      for fc, p, m in zip(BAND_CENTRES, pe, margins) if p > pe.max() * 1e-6]}


def _highpass(x: np.ndarray, sr: int, hz: float) -> np.ndarray:
    spec = np.fft.rfft(x)
    spec[np.fft.rfftfreq(x.size, 1.0 / sr) < hz] = 0.0
    return np.fft.irfft(spec, n=x.size)


def _box_rms(sq: np.ndarray, half: int) -> np.ndarray:
    c = np.concatenate([[0.0], np.cumsum(sq)])
    idx = np.arange(sq.size)
    lo, hi = np.clip(idx - half, 0, sq.size), np.clip(idx + half + 1, 0, sq.size)
    return np.sqrt(np.maximum((c[hi] - c[lo]) / np.maximum(hi - lo, 1), 0.0))


def click_candidates(x, sr: int, limits: Limits, top: int = 20) -> list[dict]:
    """The strongest high-frequency bursts of ``x``: time, local ratio, near ratio, concentration. Needs ``limits.hf_hz``;
    ratios and concentration are measured, nothing is judged here."""
    if limits.hf_hz is None:
        raise ValueError("limits.hf_hz is required to measure clicks")
    sig = _as_signal(x, "x")
    hp = _highpass(sig, sr, float(limits.hf_hz))
    sq, mag = hp * hp, np.abs(hp)
    loc = _box_rms(sq, int(limits.local_s * sr)) + 1e-9
    near = _box_rms(sq, max(1, int(limits.near_s * sr))) + 1e-9
    ratio = mag / loc
    out = []
    for i in np.argsort(-ratio)[: top * 40]:
        edge = int(limits.wide_s * sr)  # the FFT split wraps around: the first and last wide_s are not judged
        if i < edge or i >= sig.size - edge or any(abs(int(i) - o["_i"]) < int(0.010 * sr) for o in out):
            continue
        b, w = int(limits.burst_s * sr), int(limits.wide_s * sr)
        conc = float(sq[max(0, i - b):i + b].sum() / (sq[max(0, i - w):i + w].sum() + _EPS))
        out.append({"t": round(int(i) / sr, 4), "_i": int(i), "local_ratio": round(float(ratio[i]), 2),
                    "near_ratio": round(float(mag[i] / near[i]), 2), "concentration": round(conc, 3)})
        if len(out) >= top:
            break
    for o in out:
        o.pop("_i")
    return sorted(out, key=lambda o: o["t"])


def check(effects: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Findings for a list of ``{"id", "effect", "bed", "sr"}`` (mono arrays) and/or ``{"id", "mix", "sr"}`` (a stem or the
    master for the click detector). Each measurement without its sourced limits yields a ``NOT_RUN`` finding that carries
    the measured values (never a PASS)."""
    if not isinstance(effects, list):
        raise ValueError("effects must be a list of dicts")
    out: list[dict] = []
    for i, item in enumerate(effects):
        if not isinstance(item, dict) or "id" not in item or "sr" not in item:
            raise ValueError(f"effects[{i}] needs 'id' and 'sr'")
        where, sr = str(item["id"]), int(item["sr"])
        if "effect" in item:
            m = audibility(item["effect"], item["bed"], sr)
            if limits.silent_peak_dbfs is None and limits.masked_below_db is None:
                out.append({"rule": "AUD-01", "severity": "NOT_RUN", "where": where,
                            "detail": f"no sourced margin in the registry; measured {_summ(m)}"})
            else:
                if limits.silent_peak_dbfs is not None and m["peak_dbfs"] < limits.silent_peak_dbfs:
                    out.append({"rule": "AUD-02", "severity": limits.severity, "where": where,
                                "detail": f"peak {m['peak_dbfs']} dBFS is under {limits.silent_peak_dbfs}: nothing audible"})
                elif limits.masked_below_db is not None and m["margin_db"] is not None \
                        and m["margin_db"] < limits.masked_below_db:
                    out.append({"rule": "AUD-01", "severity": limits.severity, "where": where,
                                "detail": f"{m['margin_db']} dB over the bed at {m['dominant_hz']} Hz, under "
                                          f"{limits.masked_below_db}"})
        if "mix" in item:
            need = (limits.hf_hz, limits.local_ratio, limits.near_ratio, limits.concentration_min)
            if limits.hf_hz is None:
                out.append({"rule": "CLK-01", "severity": "NOT_RUN", "where": where,
                            "detail": "no sourced high-pass corner or ratios in the registry; click detector not run"})
            else:
                cands = click_candidates(item["mix"], sr, limits)
                if any(v is None for v in need):
                    out.append({"rule": "CLK-01", "severity": "NOT_RUN", "where": where,
                                "detail": f"ratios or concentration not sourced; strongest bursts: {cands[:5]}"})
                else:
                    for c in cands:
                        if (c["local_ratio"] > limits.local_ratio and c["near_ratio"] > limits.near_ratio
                                and c["concentration"] >= limits.concentration_min):
                            out.append({"rule": "CLK-01", "severity": limits.severity, "where": f"{where}@{c['t']}s",
                                        "detail": f"click: {c}"})
    return sorted(out, key=lambda f: (f["rule"], f["where"]))


def _summ(m: dict) -> str:
    return (f"peak {m['peak_dbfs']} dBFS, dominant band {m['dominant_hz']} Hz, margin {m['margin_db']} dB "
            f"(window at {m['window_start_s']} s)")
