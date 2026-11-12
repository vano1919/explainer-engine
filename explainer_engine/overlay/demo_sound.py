"""Procedural sounds of the demo (OV-56: the library files are absent in this container, so every class is made with numpy; this is
allowed in the demo only). One family for the whole episode (OV-52): soft, organic (paper, pencil, wood, a soft bell); no beeps.

``render_class(cls, frames, rng)`` returns a mono float32 array at SR; ``mix`` places the events of the specs, the narration lines and
the ambience bed into stems.
"""
from __future__ import annotations

import numpy as np

SR = 48000
FPS = 24


def _env(n: int, a: float, d: float, kind: str = "exp") -> np.ndarray:
    t = np.arange(n) / SR
    att = np.minimum(1.0, t / max(a, 1e-4))
    return att * np.exp(-t / d) if kind == "exp" else att


def _noise(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n).astype(np.float32)


def lp(x: np.ndarray, fc: float) -> np.ndarray:
    """One-pole low-pass, vectorised by blocks through lfilter-free FFT (fast enough for short clips)."""
    n = len(x)
    f = np.fft.rfft(x, 2 * n)
    freqs = np.fft.rfftfreq(2 * n, 1 / SR)
    h = 1.0 / np.sqrt(1 + (freqs / fc) ** 2)
    return np.fft.irfft(f * h)[:n].astype(np.float32)


def hp(x: np.ndarray, fc: float) -> np.ndarray:
    return (x - lp(x, fc)).astype(np.float32)


def bp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    return lp(hp(x, lo), hi)


def sine(n: int, f0: float, f1: float | None = None) -> np.ndarray:
    t = np.arange(n) / SR
    f = np.linspace(f0, f1 if f1 is not None else f0, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32)


def render_class(cls: str, frames: int, rng) -> np.ndarray:
    n = max(int(frames / FPS * SR), int(0.04 * SR))
    j = 1.0 + (rng.random() - 0.5) * 0.10            # BP-57: a pitch jitter of +-5 % per variant
    if cls == "pop_in":                                # a soft wooden pop: a short falling sine with a breath of noise
        n = int(0.16 * SR)
        x = sine(n, 520 * j, 260 * j) * _env(n, 0.004, 0.035) + 0.25 * lp(_noise(n, rng), 1800) * _env(n, 0.002, 0.012)
    elif cls == "glow_ping":                           # a soft bell: three inharmonic partials, a long gentle decay
        n = int(0.9 * SR)
        x = sum(a * sine(n, f * j) * _env(n, 0.006, d) for a, f, d in ((1.0, 660, 0.30), (0.45, 1346, 0.20), (0.22, 2040, 0.12)))
    elif cls == "pencil_scribble":                     # a pencil line: band-passed noise strokes whose rate follows the draw
        x = bp(_noise(n, rng), 1500, 5200)
        t = np.arange(n) / SR
        stroke = 0.55 + 0.45 * np.sin(2 * np.pi * (9.0 + 4 * rng.random()) * t + rng.random() * 6.28) ** 2
        fade = np.minimum(1, t / 0.04) * np.minimum(1, (n / SR - t) / 0.06)
        x = x * stroke * fade
    elif cls == "tick":                                # a small wooden tick
        n = int(0.09 * SR)
        x = sine(n, 1750 * j) * _env(n, 0.001, 0.012) * 0.8 + 0.4 * hp(_noise(n, rng), 2500) * _env(n, 0.0005, 0.004)
    elif cls == "tock":                                # the lower wooden tick
        n = int(0.11 * SR)
        x = sine(n, 1050 * j) * _env(n, 0.001, 0.018) * 0.85 + 0.3 * hp(_noise(n, rng), 1800) * _env(n, 0.0005, 0.005)
    elif cls == "landing_thud":                        # a soft landing: a low sine and a muffled knock
        n = int(0.42 * SR)
        x = sine(n, 95 * j, 55 * j) * _env(n, 0.003, 0.09) + 0.5 * lp(_noise(n, rng), 420) * _env(n, 0.002, 0.03)
    elif cls == "slide_grow":                          # a rising paper slide, as long as the bar's growth
        t = np.arange(n) / SR
        x = bp(_noise(n, rng), 300, 3200) * (0.25 + 0.75 * (t / (n / SR)) ** 1.5) * np.minimum(1, t / 0.03) * np.minimum(1, (n / SR - t) / 0.05)
    elif cls == "air_swell":                           # a low airy swell, as long as the motion
        t = np.arange(n) / SR
        u = t / (n / SR)
        x = lp(_noise(n, rng), 700) * np.sin(np.pi * np.clip(u, 0, 1)) ** 1.5
        x += 0.5 * lp(_noise(n, rng), 220) * np.sin(np.pi * np.clip(u, 0, 1)) ** 2
    elif cls == "swish":                               # the quiet rustle of the glass panel
        n = int(0.30 * SR)
        t = np.arange(n) / SR
        x = bp(_noise(n, rng), 1200, 6500) * np.sin(np.pi * t / (n / SR)) ** 2
    else:
        raise KeyError(cls)
    x = np.asarray(x, np.float32)
    return x / (np.max(np.abs(x)) + 1e-9)


CLASSES = ["pop_in", "glow_ping", "pencil_scribble", "tick", "tock", "landing_thud", "slide_grow", "air_swell", "swish"]


def ambience(seconds: float, rng, crackle_spans: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """A continuous wind bed over the whole video (never silent: OV-55) and a fire crackle layer for the 30 % shots' spans. Returns (wind, fire)."""
    n = int(seconds * SR)
    wind = lp(_noise(n, rng), 600) + 0.6 * lp(_noise(n, rng), 180)
    t = np.arange(n) / SR
    wind *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.11 * t + 1.3) + 0.1 * np.sin(2 * np.pi * 0.31 * t)
    fire = np.zeros(n, np.float32)
    for a, b in crackle_spans:
        k = int((b - a) * 11)                              # about eleven crackles a second
        for _ in range(k):
            pos = int((a + rng.random() * (b - a)) * SR)
            m = int((0.01 + 0.03 * rng.random()) * SR)
            c = hp(_noise(m, rng), 900) * _env(m, 0.0004, 0.006) * (0.2 + 0.8 * rng.random() ** 2)
            fire[pos:pos + m] += c[:max(0, min(m, n - pos))] if pos < n else 0
        ramp = np.ones(n, np.float32)
        i0, i1 = int(a * SR), int(b * SR)
        r = int(0.4 * SR)
        ramp[:] = 0
        ramp[i0:i1] = 1
        ramp = lp(ramp, 3.0)
        fire = fire * np.where((np.arange(n) >= i0 - r) & (np.arange(n) <= i1 + r), 1.0, 1.0)
    return wind.astype(np.float32), fire


def place(buf: np.ndarray, x: np.ndarray, t_s: float, gain: float) -> None:
    i = int(round(t_s * SR))
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += gain * x[:m]
