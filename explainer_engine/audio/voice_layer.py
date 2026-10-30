"""RETIRED by D-39 (2026-10-16, ElevenLabs is the narrator): Kokoro-era voice blend; kept as history, never run. The narrator's voice: a Kokoro style blend, a duration-preserving alteration, and the checks that prove the timings
the edit depends on survive it (docs/AUDIO_SYSTEM.md, "Voice alteration layer", D-38). numpy + stdlib; ffmpeg for the
pitch step (the `rubberband` filter).

``words.json`` is measured on the BASE render (the blended voice, before `alter`). Every step after it must keep the
length (|delta| <= 1 frame) and the word onsets (|envelope lag| <= 20 ms): `timing_preserved` decides, and `alter`
refuses to return audio that fails it.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/voice_style.py (build_style blend) and
# tmr_engine/render/mix.py (shape_voice: brightness / warmth shelves, _deess, _moving_average)
# changed: the blend takes any number of voices; shaping keeps only warmth, brightness and de-essing

from __future__ import annotations

import json
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "voice_spec.schema.json"
FRAME = 1 / 30  # P-14: the video frame; a length change above this moves a cut
MAX_LAG_MS = 20.0
MAX_PITCH_LAG_SEARCH_MS = 150.0


# -- spec -------------------------------------------------------------------------------------------------------

def validate_voice_spec(spec: dict) -> list[str]:
    """Schema errors plus the semantic rules; an empty list means valid."""
    from jsonschema import Draft202012Validator

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '-'}: {e.message}" for e in
              sorted(Draft202012Validator(schema).iter_errors(spec), key=lambda e: list(map(str, e.absolute_path)))]
    if not errors:
        blend = spec["blend"]
        if sum(b["weight"] for b in blend) > 0.5 + 1e-9:
            errors.append("blend: the other voices together may weigh at most 0.5 (the base keeps the larger share)")
        names = [spec["base"]] + [b["voice"] for b in blend]
        if len(set(names)) != len(names):
            errors.append("blend: a voice appears twice")
    return errors


def load_voice_spec(path: Path | str) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_voice_spec(spec)
    if errors:
        raise ValueError(f"voice spec {path}: " + "; ".join(errors))
    return spec


# -- blend ------------------------------------------------------------------------------------------------------

def blend_style(styles: list[np.ndarray], weights: list[float]) -> np.ndarray:
    """The weighted mean of Kokoro style arrays (510 x 1 x 256); weights are normalised to sum to 1."""
    if not styles or len(styles) != len(weights):
        raise ValueError("blend_style needs one weight per style")
    if any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("blend weights must be non-negative and not all zero")
    total = float(sum(weights))
    out = np.zeros_like(np.asarray(styles[0], dtype=np.float32))
    for s, w in zip(styles, weights):
        s = np.asarray(s, dtype=np.float32)
        if s.shape != out.shape:
            raise ValueError("style arrays differ in shape")
        out += (w / total) * s
    return out.astype(np.float32)


def narrator_style(get_voice, spec: dict) -> np.ndarray:
    """The style array for ``spec``: the base voice carries the weight the blend leaves."""
    blend = spec["blend"]
    names = [spec["base"]] + [b["voice"] for b in blend]
    weights = [1.0 - sum(b["weight"] for b in blend)] + [b["weight"] for b in blend]
    return blend_style([get_voice(n) for n in names], weights)


# -- audio io ---------------------------------------------------------------------------------------------------

def read_wav(path: Path | str) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = ((b[:, 0].astype(np.int32) << 8 | b[:, 1].astype(np.int32) << 16 | b[:, 2].astype(np.int32) << 24) >> 8)
        x = x.astype(np.float32) / 8388608.0
    else:
        raise ValueError(f"unsupported sample width {width}")
    return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr


def write_wav(path: Path | str, x: np.ndarray, sr: int) -> None:
    y = np.clip(np.asarray(x, dtype=np.float32), -1.0, 1.0)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes((y * 32767.0).astype("<i2").tobytes())


# -- shaping (copied from TMR mix.shape_voice, reduced) ----------------------------------------------------------

def _moving_average(x: np.ndarray, width: int) -> np.ndarray:
    width = max(1, int(width))
    if width == 1 or len(x) == 0:
        return x.astype(np.float64)
    c = np.cumsum(np.concatenate([[0.0], x.astype(np.float64)]))
    full = (c[width:] - c[:-width]) / width
    left = (width - 1) // 2
    return np.concatenate([np.full(left, full[0]), full, np.full(len(x) - len(full) - left, full[-1])])


def _deess(x: np.ndarray, sr: int, amount: float) -> np.ndarray:
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    lo = np.clip((freqs - 4500.0) / 1000.0, 0.0, 1.0)
    hi = np.clip((9500.0 - freqs) / 1000.0, 0.0, 1.0)
    band = np.fft.irfft(np.fft.rfft(x.astype(np.float64)) * (lo * hi), len(x))
    env = np.sqrt(_moving_average(band * band, int(0.01 * sr)))
    active = env[env > env.max() * 0.05] if env.max() > 0 else env[:0]
    if len(active) < 10:
        return x
    threshold = float(np.percentile(active, 70))
    ratio = 1.0 + 3.0 * float(np.clip(amount, 0.0, 1.0))
    gain = np.ones_like(env)
    over = env > threshold
    gain[over] = (env[over] / threshold) ** (1.0 / ratio - 1.0)
    gain = _moving_average(gain, int(0.005 * sr))
    return (x + band * (gain - 1.0)).astype(np.float32)


def shape_voice(x: np.ndarray, sr: int, warmth_db: float = 0.0, brightness_db: float = 0.0, deess: float = 0.0) -> np.ndarray:
    """De-ess, then one zero-phase FFT EQ: a low shelf below ~250 Hz (warmth) and a high shelf above ~4 kHz
    (brightness). Same length in and out."""
    if len(x) == 0:
        return x
    y = np.asarray(x, dtype=np.float32)
    if deess > 0:
        y = _deess(y, sr, deess)
    if warmth_db or brightness_db:
        freqs = np.fft.rfftfreq(len(y), 1.0 / sr)
        db = np.zeros_like(freqs)
        if brightness_db:
            t = np.clip((freqs - 3000.0) / 2500.0, 0.0, 1.0)
            db += float(brightness_db) * (0.5 - 0.5 * np.cos(np.pi * t))
        if warmth_db:
            t = np.clip((freqs - 150.0) / 250.0, 0.0, 1.0)
            db += float(warmth_db) * (0.5 + 0.5 * np.cos(np.pi * t))
        y = np.fft.irfft(np.fft.rfft(y.astype(np.float64)) * 10.0 ** (db / 20.0), len(y)).astype(np.float32)
    return y


# -- pitch (ffmpeg rubberband, tempo fixed at 1.0) --------------------------------------------------------------

def pitch_shift(x: np.ndarray, sr: int, semitones: float, formant: str = "preserved") -> np.ndarray:
    """Pitch by ``semitones`` at tempo 1.0 through ffmpeg's rubberband; the output is trimmed or padded to the input
    length (rubberband can add a few milliseconds of latency; `timing_preserved` measures what is left)."""
    if abs(semitones) < 1e-9:
        return np.asarray(x, dtype=np.float32)
    scale = 2.0 ** (float(semitones) / 12.0)
    with tempfile.TemporaryDirectory() as tmp:
        a, b = Path(tmp) / "in.wav", Path(tmp) / "out.wav"
        write_wav(a, x, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-af",
                        f"rubberband=pitch={scale:.6f}:tempo=1:formant={formant}:pitchq=quality", str(b)],
                       check=True, capture_output=True)
        y, sr2 = read_wav(b)
    if sr2 != sr:
        raise RuntimeError(f"rubberband returned {sr2} Hz, expected {sr}")
    n = len(x)
    return np.pad(y, (0, max(0, n - len(y))))[:n].astype(np.float32)


# -- timing checks ----------------------------------------------------------------------------------------------

def _envelope(x: np.ndarray, sr: int, win_ms: float = 10.0) -> np.ndarray:
    """RMS envelope at 1 kHz (1 ms hop)."""
    hop = max(1, int(sr / 1000))
    win = max(hop, int(sr * win_ms / 1000))
    sq = np.square(np.asarray(x, dtype=np.float64))
    return np.sqrt(_moving_average(sq, win))[::hop]


def envelope_lag_ms(before: np.ndarray, after: np.ndarray, sr: int, search_ms: float = MAX_PITCH_LAG_SEARCH_MS) -> float:
    """How many ms ``after`` lags ``before`` (positive = later), from the cross-correlation of the loudness envelopes."""
    n = min(len(before), len(after))
    a, b = _envelope(before[:n], sr), _envelope(after[:n], sr)
    a, b = a - a.mean(), b - b.mean()
    size = 1 << int(np.ceil(np.log2(2 * len(a))))
    corr = np.fft.irfft(np.fft.rfft(b, size) * np.conj(np.fft.rfft(a, size)), size)
    k = int(search_ms)
    window = np.concatenate([corr[-k:], corr[:k + 1]])  # lags -k..+k ms
    return float(int(np.argmax(window)) - k)


def timing_preserved(before: np.ndarray, after: np.ndarray, sr: int) -> dict:
    """The contract: |length delta| <= one frame and |envelope lag| <= 20 ms."""
    delta = (len(after) - len(before)) / sr
    lag = envelope_lag_ms(before, after, sr)
    return {"length_delta_s": round(delta, 4), "lag_ms": round(lag, 1),
            "ok": abs(delta) <= FRAME + 1e-9 and abs(lag) <= MAX_LAG_MS}


def alter(x: np.ndarray, sr: int, spec: dict, *, strict: bool = True) -> tuple[np.ndarray, dict]:
    """The alteration layer: pitch (formant preserved or shifted) then tone, both duration-preserving. Returns the
    audio and a report. If the result breaks the timing contract the base audio is returned (strict) or the error
    raised (``strict=False``); the report says which."""
    pitch, tone = spec["pitch"], spec["tone"]
    y = pitch_shift(x, sr, pitch["semitones"], pitch["formant"])
    y = shape_voice(y, sr, tone["warmth_db"], tone["brightness_db"], tone["deess"])
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    if peak > 0.97:
        y = (y * (0.97 / peak)).astype(np.float32)
    check = timing_preserved(x, y, sr)
    report = {"voice": spec["id"], "pitch_semitones": pitch["semitones"], "formant": pitch["formant"], "timing": check,
              "used": "altered" if check["ok"] else "base"}
    if not check["ok"]:
        if not strict:
            raise ValueError(f"alteration breaks the timing contract: {check}")
        return np.asarray(x, dtype=np.float32), report
    return y.astype(np.float32), report


# -- measurements -----------------------------------------------------------------------------------------------

def f0_track(x: np.ndarray, sr: int, fmin: float = 60.0, fmax: float = 300.0) -> np.ndarray:
    """Pitch (Hz) of voiced 40 ms frames (10 ms hop) by normalised autocorrelation; unvoiced frames are dropped."""
    frame, hop = int(0.04 * sr), int(0.01 * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    out = []
    x = np.asarray(x, dtype=np.float64)
    gate = 0.1 * float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0
    for i in range(0, len(x) - frame - hi, hop):
        seg = x[i:i + frame + hi]
        a = seg[:frame] - seg[:frame].mean()
        if np.sqrt(np.mean(a * a)) < gate:
            continue
        e0 = float(np.dot(a, a))
        best, best_lag = 0.0, 0
        for lag in range(lo, hi + 1):
            b = seg[lag:lag + frame] - seg[lag:lag + frame].mean()
            den = np.sqrt(e0 * float(np.dot(b, b)))
            r = float(np.dot(a, b)) / den if den > 0 else 0.0
            if r > best:
                best, best_lag = r, lag
        if best > 0.6 and best_lag:
            out.append(sr / best_lag)
    return np.asarray(out)


def measure(x: np.ndarray, sr: int, words: int | None = None) -> dict:
    """Median pitch (Hz), pitch spread (semitone standard deviation), duration, pace and RMS level."""
    f0 = f0_track(x, sr)
    seconds = len(x) / sr
    out = {"seconds": round(seconds, 2), "rms_dbfs": round(20 * np.log10(max(1e-9, float(np.sqrt(np.mean(np.square(x)))))), 1)}
    if len(f0) >= 5:
        med = float(np.median(f0))
        out.update(f0_median_hz=round(med, 1), f0_spread_st=round(float(np.std(12 * np.log2(f0 / med))), 2))
    if words:
        out["wpm"] = round(words / seconds * 60.0, 1)
    return out
