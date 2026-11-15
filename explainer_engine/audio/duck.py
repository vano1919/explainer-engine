
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


PRESENCE_BAND_HZ = tuple(float(v) for v in SR.T("BP-204", "presence_band_hz"))
PRESENCE_CUT_DB = float(SR.T("BP-204", "presence_cut_db"))
OUTER_CUT_DB = float(SR.T("BP-204", "outer_cut_db"))


def duck_presence_band(
    bed_or_bus: np.ndarray,
    voice_sidechain: np.ndarray,
    sr: int = 48000,
    *,
    presence_hz: tuple[float, float] = PRESENCE_BAND_HZ,
    presence_cut_db: float = PRESENCE_CUT_DB,
    outer_cut_db: float = OUTER_CUT_DB,
    threshold_db: float = -37.0,
) -> np.ndarray:
    """Step 5 Fix (BP-204): dynamic presence-band (280-3600 Hz) ducking instead of -9 dB broadband crushing.
    Supports 1D (N,), channel-first (2, N), and sample-first (N, 2) stereo arrays.
    """
    from scipy import signal

    arr = np.asarray(bed_or_bus, dtype=np.float32)
    sc = np.asarray(voice_sidechain, dtype=np.float32)
    if sc.ndim > 1:
        sc = sc.mean(axis=-1 if sc.shape[-1] <= 2 and sc.shape[0] > 2 else 0)
    is_1d = arr.ndim == 1
    channels_last = (not is_1d) and arr.shape[-1] in (1, 2) and arr.shape[0] > 2
    if is_1d:
        stereo = arr[None, :]
    elif channels_last:
        stereo = arr.T
    else:
        stereo = arr
    n = stereo.shape[-1]
    sc = sc[:n] if len(sc) >= n else np.pad(sc, (0, n - len(sc)))

    win = max(1, int(0.12 * sr))
    env = np.convolve(np.abs(sc), np.ones(win, dtype=np.float32) / win, mode="same")
    gate = (env > (10.0 ** (threshold_db / 20.0))).astype(np.float32)
    smooth_w = max(1, int(0.32 * sr))
    gate = np.clip(np.convolve(gate, np.ones(smooth_w, dtype=np.float32) / smooth_w, mode="same"), 0.0, 1.0)

    sos_bp = signal.butter(2, [presence_hz[0], presence_hz[1]], btype="bandpass", fs=sr, output="sos")
    presence = signal.sosfilt(sos_bp, stereo, axis=-1).astype(np.float32)
    outer = stereo - presence

    g_pres = (10.0 ** (-abs(presence_cut_db) * gate / 20.0)).astype(np.float32)
    g_outer = (10.0 ** (-abs(outer_cut_db) * gate / 20.0)).astype(np.float32)
    out = presence * g_pres + outer * g_outer
    if is_1d:
        return out[0]
    return out.T if channels_last else out


def stage_spatial_sound(
    audio: np.ndarray,
    *,
    source_x: float = 0.5,
    distance: str = "medium",
    camera_op: str = "hold",
    progress: float = 0.0,
    sr: int = 48000,
) -> np.ndarray:
    """Step 5 & Creator C1: stage sound inside the picture space so level, pan, and distance follow the source and camera.

    - ``source_x`` in ``[0, 1]`` maps to stereo pan ``[-0.75, +0.75]`` via equal-power panning.
    - ``distance`` (``distant`` | ``medium`` | ``close``) applies air-absorption low-pass filtering and distance gain.
    - ``camera_op`` (``push`` / ``push_in`` / ``fly_to``) adds up to +2.5 dB proximity gain as ``progress`` goes 0 -> 1.
    """
    from scipy import signal

    x = np.asarray(audio, dtype=np.float32)
    if x.ndim > 1:
        x = x.mean(axis=0)
    lp_hz = {"distant": 2800.0, "medium": 6800.0, "close": None}.get(str(distance), 6800.0)
    if lp_hz and len(x) > 16:
        sos = signal.butter(2, lp_hz, btype="low", fs=sr, output="sos")
        x = signal.sosfilt(sos, x).astype(np.float32)
    dist_db = {"distant": -5.0, "medium": -1.5, "close": 0.0}.get(str(distance), -1.5)
    cam_db = 2.5 * float(np.clip(progress, 0.0, 1.0)) if str(camera_op) in ("push", "push_in", "fly_to", "zoom") else (
        -2.0 * float(np.clip(progress, 0.0, 1.0)) if str(camera_op) in ("pull", "pull_back") else 0.0
    )
    gain = 10.0 ** ((dist_db + cam_db) / 20.0)
    pan = float(np.clip(2.0 * float(source_x) - 1.0, -0.75, 0.75))
    angle = (pan + 1.0) * np.pi / 4.0
    left = x * gain * np.cos(angle)
    right = x * gain * np.sin(angle)
    return np.stack([left.astype(np.float32), right.astype(np.float32)], axis=0)


def place_spatial_event(
    buf: np.ndarray,
    x: np.ndarray,
    t0_s: float,
    gain_db: float = 0.0,
    *,
    source_x: float = 0.5,
    distance: str = "medium",
    camera_op: str = "hold",
    progress: float = 0.0,
    sr: int = 48000,
) -> None:
    """Shared spatial event placement into a (N, 2) stereo buffer used by both tools/render_tools/mix.py and audio/stems.py."""
    i0 = max(0, int(round(float(t0_s) * sr)))
    if i0 >= len(buf) or len(x) == 0:
        return
    n = min(len(x), len(buf) - i0)
    if n <= 0:
        return
    lin_gain = float(10.0 ** (float(gain_db) / 20.0))
    staged = stage_spatial_sound(
        np.asarray(x[:n], dtype=np.float32) * lin_gain,
        source_x=source_x,
        distance=distance,
        camera_op=camera_op,
        progress=progress,
        sr=sr,
    )
    buf[i0:i0 + n] += staged.T


def duck_stems_under_voice(
    ambience: np.ndarray,
    music: np.ndarray,
    voice_sidechain: np.ndarray,
    *,
    sr: int = 48000,
    bed_presence_cut_db: float = 5.5,
    bed_outer_cut_db: float = 1.8,
    music_presence_cut_db: float = 6.5,
    music_outer_cut_db: float = 2.2,
) -> tuple[np.ndarray, np.ndarray]:
    """Shared presence-band ducking for ambience bed and music stems under voice, used by both mix.py and stems.py."""
    v_sc = np.asarray(voice_sidechain, dtype=np.float32)
    if v_sc.ndim > 1:
        v_sc = v_sc.mean(axis=-1 if v_sc.shape[-1] <= 2 and v_sc.shape[0] > 2 else 0)
    bed_ducked = duck_presence_band(
        ambience, v_sc, sr=sr, presence_cut_db=bed_presence_cut_db, outer_cut_db=bed_outer_cut_db
    )
    mus_ducked = duck_presence_band(
        music, v_sc, sr=sr, presence_cut_db=music_presence_cut_db, outer_cut_db=music_outer_cut_db
    )
    return bed_ducked, mus_ducked

