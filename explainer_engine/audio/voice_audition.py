"""Voice audition (P4b, VC-06/VC-07): the one place a voice is measured. Free, numpy only, deterministic.

A candidate voice is listened to for free (the library preview the connector's ``creative_list_voices`` returns, or a test
read the creator already holds) and gets one profile of eight measures: pitch (median and range), pitch variation,
emphasis, pace, spectral centroid, pause rhythm, sibilance and the consistency of several takes. ``distinct`` makes VC-04
measurable with BP-138's margins; ``record`` is the ``voice_audition/1`` document the casting card shows the creator, who
still picks by ear (VC-03). P8 and P12b import this module; nothing else measures a voice.

    x, sr = load_audio("preview.mp3")
    rec = record("NOpBlnGInO9m6vDvFkFC", "Grandpa Spuds Oxley", x, sr, source={"kind": "library_preview", "ref": url})

    python -m explainer_engine.audio.voice_audition measure <audio file> [--text <file>]
    python -m explainer_engine.audio.voice_audition compare <audio file> <audio file> ...

Numbers that decide anything (the three margins) come from BP-138 in the registry (hypothesis, REVIEW). The profile itself is
descriptive: it is measured, never judged good or bad. Speaker consistency uses a numpy MFCC embedding (``numpy_mfcc13``);
the identity scorer the pipeline uses later is chosen by the P12b measurement, and ``consistency`` takes any embedder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Callable

import numpy as np

from ..standards import sourced_rules as SR
from . import voice_check, voice_layer

SR_AUDIT = 24000
FRAME_S, HOP_S = 0.025, 0.010
ACTIVE_BELOW_PEAK_DB = 30.0  # a frame is speech when within this of the read's 95th-percentile level
PAUSE_MIN_S = 0.25  # an inside-speech gap shorter than this is articulation, not a pause
MIN_SPEECH_S = 5.0  # under this the profile is marked unreliable (a preview is ~10 s: enough to compare, not to cast alone)
SIBILANT_BAND = (5000.0, 9000.0)
BODY_BAND = (300.0, 3000.0)
N_MEL, N_MFCC = 40, 13
SMOOTH, PEAK_SPAN = 9, 5  # syllable peaks: envelope smoothed over 90 ms, a peak beats its neighbours 50 ms either side


# -- audio in -------------------------------------------------------------------------------------------------------

def load_audio(path: Path | str, sr: int = SR_AUDIT) -> tuple[np.ndarray, int]:
    """Mono float32 at ``sr`` (ffmpeg decodes mp3/wav/anything; a plain 24 kHz wav is read directly)."""
    path = Path(path)
    if path.suffix.lower() == ".wav":
        x, rate = voice_layer.read_wav(path)
        if rate == sr:
            return x.astype(np.float32), sr
    proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                          capture_output=True, check=False)
    if proc.returncode or not proc.stdout:
        raise RuntimeError(f"ffmpeg could not decode {path}: {proc.stderr.decode(errors='replace')[:200]}")
    return np.frombuffer(proc.stdout, dtype="<f4").copy(), sr


def sha256_of(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# -- the eight measures ---------------------------------------------------------------------------------------------

def _frames(x: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """(frame matrix, level in dB per frame) for 25 ms frames at a 10 ms hop."""
    n, hop = int(FRAME_S * sr), int(HOP_S * sr)
    if len(x) < n:
        return np.zeros((0, n)), np.zeros(0)
    idx = np.arange(0, len(x) - n + 1, hop)
    fr = np.stack([x[i:i + n] for i in idx]).astype(np.float64)
    rms = np.sqrt((fr ** 2).mean(axis=1))
    return fr, 20 * np.log10(np.maximum(rms, 1e-9))


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Start and end (exclusive) of each run of True."""
    if not mask.any():
        return []
    d = np.diff(np.concatenate([[0], mask.astype(np.int8), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def _band(power: np.ndarray, freqs: np.ndarray, lo: float, hi: float) -> float:
    return float(power[(freqs >= lo) & (freqs < hi)].sum())


def f0_track(x: np.ndarray, sr: int, fmin: float = 60.0, fmax: float = 300.0) -> np.ndarray:
    """Pitch (Hz) of the voiced 40 ms frames at a 10 ms hop, all frames at once by FFT autocorrelation. The same method and
    gate as ``voice_layer.f0_track`` (the loop version, ~100x slower; a test pins their agreement); the first correlation peak within
    10 % of the best wins, so a pitch is not read an octave low."""
    x = np.asarray(x, dtype=np.float64)
    n, hop = int(0.04 * sr), int(0.01 * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    if len(x) < n + hop:
        return np.zeros(0)
    idx = np.arange(0, len(x) - n + 1, hop)
    fr = np.stack([x[i:i + n] for i in idx])
    fr = fr - fr.mean(axis=1, keepdims=True)
    energy = np.sqrt((fr ** 2).mean(axis=1))
    gate = 0.1 * float(np.sqrt(np.mean(np.square(x))))
    spec = np.fft.rfft(fr, 2 * n, axis=1)
    ac = np.fft.irfft(spec * np.conj(spec), axis=1)[:, :hi + 1]
    ac = ac / np.maximum(ac[:, :1], 1e-12) * (n / (n - np.arange(hi + 1)))[None, :]  # bias-corrected normalised r(lag)
    r = ac[:, lo:hi + 1]
    best = r.max(axis=1)
    peak = np.zeros_like(r, dtype=bool)
    peak[:, 1:-1] = (r[:, 1:-1] >= r[:, :-2]) & (r[:, 1:-1] >= r[:, 2:])
    first = np.argmax(peak & (r >= 0.9 * best[:, None]), axis=1)
    keep = (energy >= gate) & (best > 0.6)
    return sr / (lo + first[keep])


def measure(x: np.ndarray, sr: int, text: str | None = None) -> dict:
    """The profile of one read. ``text`` (the words spoken) adds ``wpm``; without it the pace is the syllable rate."""
    x = np.asarray(x, dtype=np.float32)
    fr, db = _frames(x, sr)
    out: dict = {"duration_s": round(len(x) / sr, 2), "sample_rate": sr}
    if not len(db):
        return {**out, "reliable": False, "note": "audio shorter than one frame"}
    peak = float(np.percentile(db, 95))
    active = db > peak - ACTIVE_BELOW_PEAK_DB
    runs = _runs(active)
    if not runs:
        return {**out, "reliable": False, "note": "no speech found"}
    first, last = runs[0][0], runs[-1][1]
    span = active[first:last]
    hop = HOP_S
    # pauses: silent runs inside the speech span of at least PAUSE_MIN_S
    pauses = [(b - a) * hop for a, b in _runs(~span) if (b - a) * hop >= PAUSE_MIN_S]
    speech_s = float(span.sum() * hop)
    span_s = len(span) * hop
    out["speech_s"] = round(speech_s, 2)
    out["reliable"] = speech_s >= MIN_SPEECH_S
    if not out["reliable"]:
        out["note"] = f"under {MIN_SPEECH_S:g} s of speech: compare previews with each other, do not cast on this alone"

    # pitch (voice_layer.f0_track works on the audio; cut to the speech span)
    a, b = int(first * HOP_S * sr), int(last * HOP_S * sr)
    f0 = f0_track(x[a:b], sr)
    if len(f0) >= 5:
        st = 12 * np.log2(f0 / np.median(f0))
        out["f0_median_hz"] = round(float(np.median(f0)), 1)
        out["f0_range_st"] = round(float(np.percentile(st, 90) - np.percentile(st, 10)), 2)
        out["pitch_variation_st"] = round(float(np.std(st)), 2)

    # emphasis: how far the loud words rise above the typical speaking level
    lv = db[first:last][span]
    out["emphasis_db"] = round(float(np.percentile(lv, 90) - np.percentile(lv, 50)), 2)

    # pace: words per speaking minute when the text is known, else syllable peaks per speaking second
    env = np.convolve(10 ** (db[first:last] / 20), np.ones(SMOOTH) / SMOOTH, mode="same")
    e = 20 * np.log10(np.maximum(env, 1e-9))
    k = PEAK_SPAN
    c = e[k:-k]
    around = np.max(np.stack([e[k + s:len(e) - k + s] for s in range(-k, k + 1)]), axis=0)
    pk = (c >= around) & (c > peak - ACTIVE_BELOW_PEAK_DB + 6.0)
    out["syllable_rate"] = round(float(pk.sum()) / max(speech_s, 1e-6), 2)
    if text:
        words = len(text.split())
        out["wpm_speaking"] = round(words / max(speech_s, 1e-6) * 60.0, 1)
        out["wpm_overall"] = round(words / max(span_s, 1e-6) * 60.0, 1)

    # timbre: centroid and tilt (voice_check's measure) and sibilance over the speech frames
    tim = voice_check._timbre(x[a:b], sr)
    if tim:
        out["centroid_hz"], out["tilt_db"] = round(tim[0], 1), round(tim[1], 2)
    sp = (np.abs(np.fft.rfft(fr[first:last][span] * np.hanning(fr.shape[1]), axis=1)) ** 2).mean(axis=0)
    freqs = np.fft.rfftfreq(fr.shape[1], 1 / sr)
    if sr / 2 > SIBILANT_BAND[0]:
        out["sibilance_db"] = round(10 * np.log10((_band(sp, freqs, *SIBILANT_BAND) + 1e-12)
                                                  / (_band(sp, freqs, *BODY_BAND) + 1e-12)), 2)

    # pause rhythm
    out["pauses"] = {"count": len(pauses), "per_min": round(len(pauses) / max(span_s, 1e-6) * 60.0, 1),
                     "median_s": round(float(np.median(pauses)), 2) if pauses else 0.0,
                     "ratio": round(float(sum(pauses)) / max(span_s, 1e-6), 3)}
    return out


# -- consistency of takes -------------------------------------------------------------------------------------------

def _mel_filters(sr: int, n_fft: int) -> np.ndarray:
    def mel(f):
        return 2595 * np.log10(1 + f / 700)

    pts = 700 * (10 ** (np.linspace(mel(60), mel(sr / 2 - 100), N_MEL + 2) / 2595) - 1)
    bins = np.floor((n_fft + 1) * pts / sr).astype(int)
    fb = np.zeros((N_MEL, n_fft // 2 + 1))
    for m in range(1, N_MEL + 1):
        l, c, r = bins[m - 1], bins[m], bins[m + 1]
        for k in range(l, c):
            fb[m - 1, k] = (k - l) / max(c - l, 1)
        for k in range(c, r):
            fb[m - 1, k] = (r - k) / max(r - c, 1)
    return fb


def mfcc_embedding(x: np.ndarray, sr: int) -> np.ndarray:
    """``numpy_mfcc13``: mean and standard deviation of MFCC 1..12 over the speech frames (no neural net, no download)."""
    fr, db = _frames(np.asarray(x, dtype=np.float32), sr)
    if not len(db):
        return np.zeros(2 * (N_MFCC - 1))
    fr = fr[db > np.percentile(db, 95) - ACTIVE_BELOW_PEAK_DB]
    power = np.abs(np.fft.rfft(fr * np.hanning(fr.shape[1]), axis=1)) ** 2
    logmel = np.log(power @ _mel_filters(sr, fr.shape[1]).T + 1e-10)
    n = np.arange(N_MEL)
    dct = np.cos(np.pi / N_MEL * (n[None, :] + 0.5) * np.arange(N_MFCC)[:, None])
    c = (logmel @ dct.T)[:, 1:]
    return np.concatenate([c.mean(axis=0), c.std(axis=0)])


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    d = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / d) if d else 0.0


def consistency(takes: list[np.ndarray], sr: int, embedder: Callable[[np.ndarray, int], np.ndarray] = mfcc_embedding,
                name: str = "numpy_mfcc13") -> dict:
    """How alike several takes of one voice sound: the cosine of their embeddings, pairwise. Reported, not judged (the
    threshold waits for a measurement on real takes, P12b)."""
    if len(takes) < 2:
        return {"embedder": name, "takes": len(takes), "min_cosine": None, "mean_cosine": None}
    emb = [embedder(t, sr) for t in takes]
    cs = [_cos(a, b) for a, b in combinations(emb, 2)]
    return {"embedder": name, "takes": len(takes), "min_cosine": round(min(cs), 4), "mean_cosine": round(float(np.mean(cs)), 4)}


# -- VC-04, measurable ----------------------------------------------------------------------------------------------

def _margins() -> dict:
    return {"f0_margin_st": SR.T("BP-138", "f0_margin_st"), "rate_margin": SR.T("BP-138", "rate_margin"),
            "centroid_margin": SR.T("BP-138", "centroid_margin")}


def difference(a: dict, b: dict) -> dict:
    """Per measure: the distance between two profiles, and whether it reaches BP-138's margin (None = not measurable)."""
    m = _margins()
    out: dict = {}
    if a.get("f0_median_hz") and b.get("f0_median_hz"):
        d = abs(12 * np.log2(a["f0_median_hz"] / b["f0_median_hz"]))
        out["f0_st"] = {"value": round(float(d), 2), "margin": m["f0_margin_st"], "met": bool(d >= m["f0_margin_st"])}
    for key in ("wpm_speaking", "syllable_rate"):
        if a.get(key) and b.get(key):
            d = abs(a[key] - b[key]) / max(a[key], b[key])
            out["rate"] = {"value": round(float(d), 3), "margin": m["rate_margin"], "met": bool(d >= m["rate_margin"]),
                           "measure": key}
            break
    if a.get("centroid_hz") and b.get("centroid_hz"):
        d = abs(a["centroid_hz"] - b["centroid_hz"]) / max(a["centroid_hz"], b["centroid_hz"])
        out["centroid"] = {"value": round(float(d), 3), "margin": m["centroid_margin"], "met": bool(d >= m["centroid_margin"])}
    return out


def distinct(profiles: dict[str, dict]) -> list[dict]:
    """Pairs of cast voices that reach none of BP-138's three margins: the ear may not tell them apart (VC-04, REVIEW).
    A pair with no measurable margin at all is reported too, as unmeasured."""
    found = []
    for (ka, pa), (kb, pb) in combinations(profiles.items(), 2):
        diff = difference(pa, pb)
        if not diff:
            found.append({"rule": "VC-04", "severity": SR.level("BP-138"), "where": f"{ka} / {kb}",
                          "detail": "no measure to compare (profiles lack pitch, pace and centroid): listen"})
        elif not any(d["met"] for d in diff.values()):
            found.append({"rule": "VC-04", "severity": SR.level("BP-138"), "where": f"{ka} / {kb}",
                          "detail": "differ by less than every margin " + ", ".join(
                              f"{k} {d['value']} < {d['margin']}" for k, d in diff.items()) + ": the ear may confuse them"})
    return found


# -- the record -----------------------------------------------------------------------------------------------------

def record(voice_id: str, name: str, x: np.ndarray, sr: int, source: dict, text: str | None = None,
           takes: list[np.ndarray] | None = None, fit: dict | None = None) -> dict:
    """The ``voice_audition/1`` document of one voice: where the audio came from, its profile, its takes' consistency."""
    doc = {"schema": "voice_audition/1", "voice_id": voice_id, "name": name, "source": source,
           "profile": measure(x, sr, text),
           "consistency": consistency(takes, sr) if takes else None,
           "fit": fit}
    return doc


def baseline_of(profile: dict, kind: str, ref: str, sha256: str | None = None) -> dict:
    """The ``channel_voices/1`` baseline of a voice from its profile: where it was heard (a library ``preview`` until the
    first approved ``read`` of the episode replaces it), and the timbre numbers EL-13 compares takes with."""
    if not profile.get("reliable") or "centroid_hz" not in profile:
        raise ValueError("a baseline needs a reliable profile with a centroid")
    out = {"kind": kind, "ref": ref, "centroid_hz": profile["centroid_hz"], "tilt_db": profile["tilt_db"]}
    if sha256:
        out["sha256"] = sha256
    if "f0_median_hz" in profile:
        out["f0_median_hz"] = profile["f0_median_hz"]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="measure a voice (free)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("audio")
    m.add_argument("--text", help="file holding the words spoken (adds wpm)")
    c = sub.add_parser("compare")
    c.add_argument("audio", nargs="+")
    bl = sub.add_parser("baseline", help="print the registry baseline of an audio file")
    bl.add_argument("audio")
    bl.add_argument("--kind", choices=["preview", "read"], required=True)
    bl.add_argument("--ref", required=True, help="where the audio came from (URL or path)")
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        x, sr = load_audio(a.audio)
        text = Path(a.text).read_text(encoding="utf-8") if a.text else None
        print(json.dumps(measure(x, sr, text), indent=1))
        return 0
    if a.cmd == "baseline":
        x, sr = load_audio(a.audio)
        print(json.dumps(baseline_of(measure(x, sr), a.kind, a.ref, sha256_of(a.audio)), indent=1))
        return 0
    profiles = {Path(p).stem: measure(*load_audio(p)) for p in a.audio}
    print(json.dumps({"profiles": profiles, "distinct_findings": distinct(profiles)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
