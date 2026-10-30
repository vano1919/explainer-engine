"""The signal pieces of the sound director (Blueprint P4, docs/AUDIO_SYSTEM.md SD-): pan, stereo width, room impulse responses,
shelves, the presence-band dip, room tone, the beat grid and the band share a check measures. numpy only (no scipy: it is not in
requirements.txt), deterministic (the same seed gives the same samples), mono float32 in and out unless a stereo pair is named.
``assemble.build_audio_v2`` renders with these and ``sound_director.check`` measures with the same ``band_share``, so the filter and
its check never disagree about what a band is.

* ``pan(x, p)``: constant-power law, L = cos(theta), R = sin(theta), theta = (p + 1) * pi / 4 (BP-121): the centre is -3 dB per side.
* ``widen(x, seed)``: two fixed, different chains of first-order all-pass sections make a mono file a decorrelated pair (BP-121:
  "music is wide" from mono library files); the magnitude of each side equals the source's.
* ``impulse(kind, seed, sr)``: a scene's room (BP-122): exponentially decaying noise with a fixed RT60 per kind; outdoors a pair of
  early reflections inside 60 ms; ``neutral`` is a bare delta. Energy 1, so a wet share keeps the level.
* ``convolve``: FFT overlap-add, output as long as the input. ``shelf`` / ``highpass``: zero-phase FIRs from a magnitude curve.
* ``band_dip``: a short-time FFT gain at a centre, Q and depth, opened by a 0..1 envelope (BP-118): the music and beds leave the
  voice's presence band while the narrator speaks and come back in the pauses.
* ``room_tone``: pink-ish noise high-passed at BP-116's ``hpf_hz``; it is synthesised in the frequency domain, so it is circular and
  a loop of it has no seam.
* ``beat_grid``: tempo (60-180 BPM) and first-beat offset from the autocorrelation of the onset envelope.
"""

from __future__ import annotations

import hashlib

import numpy as np

from explainer_engine.audio import foley as F
from explainer_engine.standards import sourced_rules as RULES

SR = F.SR
CENTRE_GAIN = float(np.sqrt(2.0))  # undoes the pan law's -3 dB per side at p = 0 where a mono level is meant to stay put
RT60 = {"room": 0.35, "hall": 1.4, "cave": 2.8}  # seconds; outdoor and neutral have no tail
PREDELAY = {"room": 0.010, "hall": 0.022, "cave": 0.035}
ROOM_TILT = {"neutral": 1.0, "room": 1.0, "hall": 1.2, "cave": 1.5, "outdoor": 0.8}  # power ~ 1/f^tilt: the colour of the tone
ROOM_LOWPASS = {"neutral": 6000.0, "room": 5000.0, "hall": 3500.0, "cave": 2200.0, "outdoor": 9000.0}
KINDS = ("outdoor", "room", "hall", "cave", "neutral")


def seed_of(text: str) -> int:
    """A stable non-negative seed below 2**31 from a name (a scene id, a library item): sha256, never ``hash()``."""
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16) % (2 ** 31)


def rms_db(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)) if x.size else -120.0


# --- pan and width --------------------------------------------------------------------------------------------------------

def pan(x: np.ndarray, p: float) -> np.ndarray:
    """(n, 2) from a mono signal: constant power, p in [-1, 1] (-1 left, 0 centre, +1 right)."""
    theta = (float(np.clip(p, -1.0, 1.0)) + 1.0) * np.pi / 4.0
    x = np.asarray(x)
    return np.stack([x * float(np.cos(theta)), x * float(np.sin(theta))], axis=1)


def _allpass_ir(coefs: list[float], length: int = 2048, nfft: int = 1 << 13) -> np.ndarray:
    """Impulse response of cascaded first-order all-pass sections H(w) = (a + e^-jw) / (1 + a e^-jw), |H| = 1."""
    z = np.exp(-1j * np.pi * np.arange(nfft // 2 + 1) / (nfft // 2))
    h = np.ones_like(z)
    for a in coefs:
        h = h * (a + z) / (1.0 + a * z)
    return np.fft.irfft(h, nfft)[:length].astype(np.float32)


def widen(x: np.ndarray, seed: int) -> np.ndarray:
    """(n, 2) decorrelated pair from a mono signal. The left and right chains differ (fixed bases, a seeded jitter), so the same
    seed gives the same pair and two seeds give two slightly different images."""
    rng = np.random.default_rng(seed)
    base_l, base_r = np.array([-0.96, 0.62, -0.43, 0.31]), np.array([0.55, -0.9, 0.47, -0.35])
    left = _allpass_ir(list(base_l + rng.uniform(-0.04, 0.04, 4)))
    right = _allpass_ir(list(base_r + rng.uniform(-0.04, 0.04, 4)))
    x = np.asarray(x, dtype=np.float32)
    return np.stack([convolve(x, left), convolve(x, right)], axis=1)


# --- convolution, room and tone shaping -----------------------------------------------------------------------------------

def convolve(x: np.ndarray, ir: np.ndarray, *, tail: bool = False) -> np.ndarray:
    """FFT overlap-add convolution. The result has the input's length (the tail is dropped); ``tail=True`` keeps all
    ``len(x) + len(ir) - 1`` samples."""
    x, ir = np.asarray(x, dtype=np.float32), np.asarray(ir, dtype=np.float32)
    n, m = len(x), len(ir)
    out = np.zeros(n + m - 1 if tail else n, dtype=np.float32)
    if n == 0 or m == 0:
        return out
    nfft = 1 << max(12, int(np.ceil(np.log2(2 * m))))
    block = nfft - m + 1
    h = np.fft.rfft(ir, nfft)
    for i in range(0, n, block):
        y = np.fft.irfft(np.fft.rfft(x[i:i + block], nfft) * h, nfft)
        j = min(len(out), i + nfft)
        out[i:j] += y[:j - i]
    return out


def impulse(kind: str, seed: int, sr: int = SR) -> np.ndarray:
    """A scene's impulse response (wet path only, energy 1). ``outdoor``: two early reflections inside 60 ms; ``neutral``: a delta;
    room, hall, cave: noise decaying 60 dB over the kind's RT60 after a pre-delay, softened above 7 kHz."""
    if kind not in KINDS:
        raise ValueError(f"unknown acoustic {kind!r}; known: {KINDS}")
    rng = np.random.default_rng(seed)
    if kind == "neutral":
        return np.ones(1, dtype=np.float32)
    if kind == "outdoor":
        ir = np.zeros(int(0.060 * sr), dtype=np.float32)
        for t, g in ((0.023, 0.6), (0.047, 0.4)):
            ir[int((t + rng.uniform(-0.003, 0.003)) * sr)] = g
    else:
        n = int(RT60[kind] * sr)
        t = np.arange(n) / sr
        ir = (rng.standard_normal(n) * np.exp(-6.9078 * t / RT60[kind])).astype(np.float32)
        ir = F._band(ir, 0, 7000)  # air takes the top off a tail
        ir = np.concatenate([np.zeros(int(PREDELAY[kind] * sr), dtype=np.float32), ir])
    return (ir / np.sqrt(np.sum(ir.astype(np.float64) ** 2) + 1e-12)).astype(np.float32)


def _zero_phase_fir(gain_of_f, sr: int, taps: int) -> np.ndarray:
    nfft = 1 << 15
    f = np.fft.rfftfreq(nfft, 1.0 / sr)
    ir = np.roll(np.fft.irfft(gain_of_f(f), nfft), taps // 2)[:taps] * np.hanning(taps)
    return ir.astype(np.float32)


def _apply_zero_phase(x: np.ndarray, ir: np.ndarray) -> np.ndarray:
    d = len(ir) // 2
    return convolve(x, ir, tail=True)[d:d + len(x)]


def shelf(x: np.ndarray, sr: int, hz: float, db: float, high: bool) -> np.ndarray:
    """A shelf of ``db`` above (``high``) or below ``hz``: half the gain at ``hz``, the full gain a decade away. Zero phase."""
    if abs(db) < 1e-9:
        return np.asarray(x, dtype=np.float32)
    if high:
        shape = lambda f: f ** 2 / (f ** 2 + hz ** 2)  # noqa: E731
    else:
        shape = lambda f: hz ** 2 / (f ** 2 + hz ** 2)  # noqa: E731
    fir = _zero_phase_fir(lambda f: 10 ** (db * shape(np.maximum(f, 1e-3)) / 20.0), sr, 4097)
    return _apply_zero_phase(x, fir)


def highpass(x: np.ndarray, sr: int, hz: float, order: int = 4) -> np.ndarray:
    """High-pass at ``hz`` (Butterworth magnitude, ``6 * order`` dB per octave, zero phase): BP-118's narration chain, BP-116's tone."""
    fir = _zero_phase_fir(lambda f: np.where(f > 0, 1.0 / np.sqrt(1.0 + (hz / np.maximum(f, 1e-3)) ** (2 * order)), 0.0), sr, 8193)
    return _apply_zero_phase(x, fir)


def key_from_gain(gain: np.ndarray, depth_db: float) -> np.ndarray:
    """A duck curve (linear gain, ``duck.duck_gain``) as a 0..1 key: 1 at full duck depth. The dip then follows the voice with
    the duck's own attack, hold and release (BP-53)."""
    return np.clip(-20 * np.log10(np.maximum(gain, 1e-9)) / max(depth_db, 1e-9), 0.0, 1.0).astype(np.float32)


def band_dip(x: np.ndarray, sr: int, key_env: np.ndarray, hz: float, q: float, depth_db: float) -> np.ndarray:
    """Dip ``x`` by up to ``depth_db`` around ``hz`` (bell of quality ``q``) wherever ``key_env`` (0..1, one value per sample) is up.
    A short-time FFT gain: 2048-sample Hann frames, 50 % overlap-add, one gain per frame at its centre. ``x`` is mono (n,) or
    stereo (n, 2); every channel gets the same gain."""
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        return np.stack([band_dip(x[:, c], sr, key_env, hz, q, depth_db) for c in range(x.shape[1])], axis=1)
    n, size = len(x), 2048
    hop = size // 2
    if n == 0:
        return x
    frames = (n + hop - 1) // hop + 1
    padded = np.zeros((frames + 1) * hop, dtype=np.float32)
    padded[hop:hop + n] = x
    window = (0.5 - 0.5 * np.cos(2 * np.pi * np.arange(size) / size)).astype(np.float32)  # periodic Hann: 50 % overlap sums to 1
    f = np.fft.rfftfreq(size, 1.0 / sr)
    fr = np.maximum(f, 1e-3)
    bell = np.where(f > 0, 1.0 / (1.0 + q ** 2 * (fr / hz - hz / fr) ** 2), 0.0).astype(np.float32)
    centre = np.clip(np.arange(frames) * hop, 0, n - 1)  # frame j is centred on original sample j * hop
    depth = depth_db * np.asarray(key_env, dtype=np.float32)[centre]
    out = np.zeros((frames + 1, hop), dtype=np.float32)
    for a in range(0, frames, 512):
        b = min(frames, a + 512)
        idx = (np.arange(a, b) * hop)[:, None] + np.arange(size)[None, :]
        spec = np.fft.rfft(padded[idx] * window, axis=1)
        y = np.fft.irfft(spec * (10 ** (-(depth[a:b, None] * bell[None, :]) / 20.0)).astype(np.float32), size, axis=1)
        out[a:b] += y[:, :hop]
        out[a + 1:b + 1] += y[:, hop:]
    return out.reshape(-1)[hop:hop + n]


def dip_centre_for_gap(gap_db: float, hz: float, q: float, lo: float, hi: float) -> float:
    """The depth at the bell's centre (dB) that moves a pink background's share of ``[lo, hi)`` Hz down by ``gap_db``. A bell of Q 1.2
    dips its centre by far more than it dips the 1-4 kHz band as a whole (3.5 dB at 2.2 kHz moves that band's energy share by only
    1.4 dB), so the gap a check measures is the target and the centre depth follows from it (bisection on the share)."""
    f = np.geomspace(50.0, 12000.0, 4000)
    power = 1.0 / f
    bell = 1.0 / (1.0 + q ** 2 * (f / hz - hz / f) ** 2)
    band = (f >= lo) & (f < hi)

    def moved(depth: float) -> float:
        p = power * 10 ** (-depth * bell / 10.0)
        return 10 * np.log10((p[band].sum() / p.sum()) / (power[band].sum() / power.sum()))

    a, b = 0.0, 40.0
    for _ in range(40):
        mid = (a + b) / 2
        a, b = (mid, b) if moved(mid) > -gap_db else (a, mid)
    return round((a + b) / 2, 3)


def room_tone(kind: str, seed: int, seconds: float, sr: int = SR) -> np.ndarray:
    """Mono float32 room tone of ``seconds`` at RMS 0.05: noise shaped in the frequency domain to a 1/f^tilt power, high-passed at
    BP-116's ``hpf_hz`` and low-passed per kind. Circular by construction (a loop of it has no seam)."""
    if kind not in KINDS:
        raise ValueError(f"unknown acoustic {kind!r}; known: {KINDS}")
    n = int(round(seconds * sr))
    spec = np.fft.rfft(np.random.default_rng(seed).standard_normal(n).astype(np.float32))
    f = np.fft.rfftfreq(n, 1.0 / sr)
    fr = np.maximum(f, 1.0)
    hpf = float(RULES.T("BP-116", "hpf_hz"))
    gain = fr ** (-ROOM_TILT[kind] / 2.0)
    gain = gain / np.sqrt(1.0 + (hpf / fr) ** 8) / np.sqrt(1.0 + (fr / ROOM_LOWPASS[kind]) ** 4)
    gain[0] = 0.0
    y = np.fft.irfft(spec * gain.astype(np.float32), n).astype(np.float32)
    return y * np.float32(0.05 / (np.sqrt(np.mean(y.astype(np.float64) ** 2)) + 1e-12))


# --- measuring ------------------------------------------------------------------------------------------------------------

def band_share(x: np.ndarray, sr: int, lo: float, hi: float, mask: np.ndarray | None = None) -> float | None:
    """The share (0..1) of the signal's energy that lies in ``[lo, hi)`` Hz, from Hann-windowed 16384-sample blocks. With a boolean
    per-sample ``mask`` only the blocks that are at least 90 % inside it count (speech or pause). ``None`` when no block counts or
    there is no energy. Stereo is read as its mid channel."""
    x = np.asarray(x)
    if x.ndim == 2:
        x = x.mean(axis=1)
    size = 16384
    nb = len(x) // size
    if nb == 0:
        return None
    use = np.ones(nb, dtype=bool)
    if mask is not None:
        use = np.asarray(mask[:nb * size], dtype=np.float32).reshape(nb, size).mean(axis=1) >= 0.9
    rows = np.flatnonzero(use)
    if not len(rows):
        return None
    win = np.hanning(size).astype(np.float32)
    f = np.fft.rfftfreq(size, 1.0 / sr)
    band = (f >= lo) & (f < hi)
    total = inside = 0.0
    blocks = np.asarray(x[:nb * size], dtype=np.float32).reshape(nb, size)
    for a in range(0, len(rows), 256):
        p = np.abs(np.fft.rfft(blocks[rows[a:a + 256]] * win, axis=1)) ** 2
        total += float(p.sum())
        inside += float(p[:, band].sum())
    return inside / total if total > 0 else None


def beat_grid(x: np.ndarray, sr: int = SR) -> dict | None:
    """``{"bpm", "offset_s"}`` of a rhythmic signal, or ``None`` when no tempo in 60-180 BPM stands out (under ~2 s, or no pulse).
    The onset envelope is the rectified rise of the 5 ms RMS; the tempo is the strongest lag of its autocorrelation (a faster tempo
    wins a near tie, so a click track at 120 reads 120, not 60); the offset is where the beats fall best on the envelope."""
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 2:
        x = x.mean(axis=1)
    hop = max(1, int(sr * 0.005))
    n = len(x) // hop
    if n < 400:
        return None
    env = np.sqrt(np.mean(x[:n * hop].astype(np.float64).reshape(n, hop) ** 2, axis=1))
    onset = np.maximum(np.diff(env, prepend=env[0]), 0.0)
    if onset.max() <= 1e-9:
        return None
    dev = onset - onset.mean()
    spec = np.fft.rfft(dev, 2 * n)
    ac = np.fft.irfft(np.abs(spec) ** 2)[:n]
    ac = np.convolve(ac, np.array([0.25, 0.5, 0.25]), mode="same") / (ac[0] + 1e-12)
    bpms = np.arange(60.0, 180.25, 0.25)
    lags = 60.0 / bpms / (hop / sr)
    score = np.interp(lags, np.arange(n), ac)
    best = int(np.argmax(score))
    if score[best] < 0.1:
        return None
    for k in np.argsort(-score)[:40]:  # near ties go to the faster tempo
        if bpms[k] > bpms[best] and score[k] >= 0.97 * score[best]:
            best = int(k)
    # refine tempo and phase together: the comb of onsets at period P and phase p, over a fine grid around the autocorrelation's pick
    best_comb, pick = -1.0, (bpms[best], 0.0)
    for bpm in np.arange(bpms[best] - 1.0, bpms[best] + 1.0001, 0.05):
        period = 60.0 / bpm / (hop / sr)
        for p in np.arange(0.0, period, 0.5):
            pos = np.round(p + np.arange(0, n - p, period)).astype(int).clip(0, n - 1)
            c = float(onset[pos].sum())
            if c > best_comb + 1e-12:
                best_comb, pick = c, (bpm, p)
    return {"bpm": round(float(pick[0]), 2), "offset_s": round(float(pick[1] * hop / sr), 3)}
