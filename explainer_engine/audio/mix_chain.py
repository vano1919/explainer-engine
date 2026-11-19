"""The one mix chain (final plan S13, W6; docs/MIX_CHAIN.md): the function ``audio/stems.render`` (G8) calls to turn the four
background-and-voice buses into the delivered stems.

Order, after the vendored ``v-design-sound`` mix practice (references/mix.md) and our registry:

1. voice bus: the read, never touched (centre);
2. music: sidechain duck under the voice (``ATTACK_MS`` / ``RELEASE_MS``), then a 1-4 kHz carve while the voice speaks, then a
   static trim until the voice is at least BP-208's ``voice_over_music_min_lu`` over the music *while it speaks* (measured, not
   assumed: the dip alone never guarantees it);
3. bed and effects: the bed ducks as before (BP-53's floor), effects are not ducked; the background bus dips only where it would
   push the sum over the ceiling (``stems.bus_limit`` semantics, here inside the master limiter);
4. master: one static gain to BP-50's target (ITU-R BS.1770-4 gating, own implementation checked against ffmpeg
   ebur128 in the tests) and one true-peak limiter (4x oversampled) with a ceiling a little under BP-50's ``true_peak_max`` so the
   AAC encode stays under it (``verify`` re-measures after an AAC round trip). Both act on every stem alike, so the stems still sum
   to the mix.

Numbers: loudness, peak and the voice-over-music gap are read from ``qa/targets`` and ``standards/sourced_rules`` (BP-50, BP-208),
never copied (there is no second loudness table). The chain's own settings (attack, release, the carve, the limiter margin and the
gap margin) are read from BP-214, a hypothesis row (REVIEW only, one source of one type: the vendored skill's mix.md), and listed in
every ``mix_chain/1`` record.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from explainer_engine.audio import duck
from explainer_engine.qa import gates as G
from explainer_engine.qa import targets as T
from explainer_engine.validators import _common as C
from explainer_engine.validators import mix as VM

SR = 48000
SCHEMA = "mix_chain/1"

# BP-214 (hypothesis, REVIEW only): the chain's engineering settings, read from the registry
ATTACK_MS = float(C.T("BP-214", "attack_ms"))
RELEASE_MS = float(C.T("BP-214", "release_ms"))
CARVE_DB = float(C.T("BP-214", "carve_db"))
CARVE_BAND_HZ = tuple(float(v) for v in C.T("BP-214", "carve_band_hz"))
TP_MARGIN_DB = float(C.T("BP-214", "tp_margin_db"))      # the limiter's ceiling sits this far under BP-50's true_peak_max (AAC overshoot)
MASTER_GAIN_MAX_DB = float(C.T("BP-214", "master_gain_max_db"))   # the master gain never moves the mix by more than this
AAC_KBPS = int(C.T("BP-63", "aac_kbps"))                 # the delivery bitrate, as production/assemble reads it
GAP_MARGIN_LU = float(C.T("BP-214", "gap_margin_lu"))    # the music is trimmed to the gap plus this, so the measured gap is not on the edge
SPEECH_THRESHOLD = 0.02       # the voice's control level where a window counts as speech (stems / mix_check)

# one home each: BP-50 through qa/targets (the one set of loudness numbers), BP-208 through validators/_common (what VAL-MIX reads)
LUFS_TARGET = float(T.PROFILES["long"]["lufs"])
TP_MAX = float(T.PROFILES["long"]["true_peak_max"])
GAP_MIN_LU = float(C.T("BP-208", "voice_over_music_min_lu"))
TIGHT_BAND = float(C.T("BP-208", "lufs_tight_band"))


# ---------------------------------------------------------------- measurement (ITU-R BS.1770-4)
_SHELF = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
          np.array([1.0, -1.69065929318241, 0.73248077421585]))
_HPF = (np.array([1.0, -2.0, 1.0]), np.array([1.0, -1.99004745483398, 0.99007225036621]))


def _k_weight(x: np.ndarray) -> np.ndarray:
    """K-weighting (48 kHz coefficients of BS.1770-4); ``x`` is (n,) or (n, ch)."""
    y = signal.lfilter(*_SHELF, x, axis=0)
    return signal.lfilter(*_HPF, y, axis=0)


def integrated_lufs(x: np.ndarray, sr: int = SR) -> float:
    """Integrated loudness (LUFS): 400 ms blocks at 75 % overlap, -70 LUFS absolute gate, -10 LU relative gate, channels
    weighted 1 (stereo or mono). ``-inf`` when nothing passes the gate."""
    if sr != SR:
        raise ValueError("integrated_lufs: the K-weighting coefficients are for 48 kHz")
    x = np.asarray(x, np.float64)
    x = x[:, None] if x.ndim == 1 else x
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(x) < blk:
        return float("-inf")
    z = _k_weight(x) ** 2
    c = np.concatenate([np.zeros((1, z.shape[1])), np.cumsum(z, axis=0)])
    starts = np.arange(0, len(x) - blk + 1, hop)
    ms = ((c[starts + blk] - c[starts]) / blk).sum(axis=1)
    lk = -0.691 + 10 * np.log10(np.maximum(ms, 1e-20))
    keep = lk > -70.0
    if not keep.any():
        return float("-inf")
    rel = -0.691 + 10 * np.log10(ms[keep].mean()) - 10.0
    keep &= lk > rel
    return float(-0.691 + 10 * np.log10(ms[keep].mean())) if keep.any() else float("-inf")


def true_peak_dbtp(x: np.ndarray, sr: int = SR) -> float:
    """True peak (dBTP): the largest sample of the 4x oversampled signal."""
    x = np.asarray(x, np.float32)
    if not len(x):
        return float("-inf")
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(max(1e-9, float(np.abs(up).max()))))


def speech_mask(voice: np.ndarray, sr: int = SR) -> np.ndarray:
    lvl = duck.control_level(voice, sr)
    m = np.repeat(lvl > SPEECH_THRESHOLD, int(sr / duck.CTRL_HZ))
    return np.pad(m, (0, max(0, len(voice) - len(m))))[: len(voice)]


def lufs_where(x: np.ndarray, mask: np.ndarray) -> float | None:
    """Loudness of the stretches of ``x`` where ``mask`` is true, joined (the way ``audio/mix_check`` measures a stem under
    speech); None under one second."""
    seg = np.asarray(x)[: len(mask)][mask[: len(x)]]
    if len(seg) < SR:
        return None
    v = integrated_lufs(seg)
    return None if v == float("-inf") else v


# ---------------------------------------------------------------- the chain
def carve(music: np.ndarray, voice: np.ndarray, *, depth_db: float = CARVE_DB, band_hz: tuple = CARVE_BAND_HZ) -> np.ndarray:
    """Dip the music's band (1-4 kHz) by ``depth_db`` while the voice speaks, with the sidechain's attack and release; the rest
    of the spectrum is untouched (zero-phase band split, so the dip leaves no phase smear)."""
    if depth_db <= 0 or not len(music):
        return music
    sos = signal.butter(2, band_hz, btype="bandpass", fs=SR, output="sos")
    band = signal.sosfiltfilt(sos, music, axis=0).astype(np.float32)
    g = duck.duck_gain(voice, SR, len(music), depth_db=depth_db, threshold=SPEECH_THRESHOLD,
                       attack_ms=ATTACK_MS, release_ms=RELEASE_MS).astype(np.float32)
    return (music - band + band * g[:, None]).astype(np.float32)


def limit_env(need: np.ndarray, attack_s: float = 0.005, release_s: float = 0.12) -> np.ndarray:
    """A smooth gain envelope from the per-sample gain a signal ``need``s: minimum over a short look-ahead block, one block of
    look-ahead, then a release back to 1 (the shape of ``stems.bus_limit``, 5 ms blocks)."""
    h = max(1, int(attack_s * SR))
    k = len(need) // h + 1
    blk = np.pad(need, (0, k * h - len(need)), constant_values=1.0).reshape(k, h).min(axis=1)
    blk = np.minimum(blk, np.concatenate([blk[1:], [1.0]]))
    rel = np.exp(-h / (release_s * SR))
    env = np.empty_like(blk)
    cur = 1.0
    for i, v in enumerate(blk):
        cur = v if v < cur else v + (cur - v) * rel
        env[i] = cur
    return np.repeat(env, h)[: len(need)].astype(np.float32)


def tp_limit_env(mix: np.ndarray, ceiling_db: float) -> np.ndarray:
    """Per-sample gain that keeps the 4x oversampled peak of ``mix`` (n, 2) under ``ceiling_db`` dBTP."""
    ceil = 10 ** (ceiling_db / 20)
    up = np.abs(signal.resample_poly(mix.astype(np.float32), 4, 1, axis=0)).max(axis=1)
    pk = up.reshape(-1, 4).max(axis=1) if len(up) % 4 == 0 else np.pad(up, (0, 4 - len(up) % 4)).reshape(-1, 4).max(axis=1)
    pk = pk[: len(mix)]
    need = np.where(pk > ceil, ceil / np.maximum(pk, 1e-9), 1.0).astype(np.float32)
    return limit_env(need)


def mix_stems(nar: np.ndarray, amb: np.ndarray, sfx: np.ndarray, mus: np.ndarray, voice: np.ndarray, *,
              bed_duck_db: float, music_duck_db: float, master: bool = True, lufs_target: float = LUFS_TARGET) -> tuple[dict, dict]:
    """The chain. ``nar`` / ``amb`` / ``sfx`` / ``mus`` are (n, 2) float32 buses before any ducking; ``voice`` is the mono read
    that drives the sidechains. Returns ``({narration, music, ambience, sfx, mix}, record)``; the record is ``mix_chain/1``."""
    n = len(voice)
    g_mus = duck.duck_gain(voice, SR, n, depth_db=music_duck_db, threshold=SPEECH_THRESHOLD,
                           attack_ms=ATTACK_MS, release_ms=RELEASE_MS).astype(np.float32)
    g_bed = duck.duck_gain(voice, SR, n, depth_db=bed_duck_db, threshold=SPEECH_THRESHOLD,
                           attack_ms=ATTACK_MS, release_ms=RELEASE_MS).astype(np.float32)
    step = duck.step_finding(g_mus, SR)
    mus = carve(mus * g_mus[:, None], voice)
    amb = amb * g_bed[:, None]
    sfx = sfx.copy()
    mask = speech_mask(voice)
    rec: dict = {"schema": SCHEMA, "sidechain": {"attack_ms": ATTACK_MS, "release_ms": RELEASE_MS, "music_depth_db": music_duck_db,
                                                  "bed_depth_db": bed_duck_db, "step_finding": step},
                 "carve": {"band_hz": list(CARVE_BAND_HZ), "depth_db": CARVE_DB},
                 "settings_rule": "BP-214 (hypothesis, REVIEW only)", "tp_margin_db": TP_MARGIN_DB, "gap_margin_lu": GAP_MARGIN_LU}
    # music at least GAP_MIN_LU under the voice while it speaks
    v_l, m_l = lufs_where(nar, mask), lufs_where(mus, mask)
    trim = 0.0
    if v_l is not None and m_l is not None and (v_l - m_l) < GAP_MIN_LU + GAP_MARGIN_LU:
        trim = GAP_MIN_LU + GAP_MARGIN_LU - (v_l - m_l)
        mus = mus * np.float32(10 ** (-trim / 20))
        m_l -= trim
    rec["music_trim_db"] = round(trim, 2)
    rec["voice_lufs_in_speech"] = None if v_l is None else round(v_l, 2)
    rec["music_lufs_in_speech"] = None if m_l is None else round(m_l, 2)
    stems = {"narration": nar, "music": mus, "ambience": amb, "sfx": sfx}
    total = nar + amb + sfx + mus
    if master and len(total) and np.abs(total).max() > 1e-6:
        ceiling = TP_MAX - TP_MARGIN_DB
        gain_db, env = 0.0, np.ones(n, np.float32)
        for _ in range(4):                       # gain to the target, limit, re-measure: the limiter costs a little loudness
            cur = integrated_lufs(total * np.float32(10 ** (gain_db / 20)) * env[:, None])
            if cur == float("-inf") or abs(cur - lufs_target) < 0.05:
                break
            gain_db = float(np.clip(gain_db + lufs_target - cur, -MASTER_GAIN_MAX_DB, MASTER_GAIN_MAX_DB))
            env = tp_limit_env(total * np.float32(10 ** (gain_db / 20)), ceiling)
        g = np.float32(10 ** (gain_db / 20))
        stems = {k: (v * g * env[:, None]).astype(np.float32) for k, v in stems.items()}
        final = integrated_lufs(total * g * env[:, None])
        capped = abs(gain_db) >= MASTER_GAIN_MAX_DB - 1e-6 and not abs(final - lufs_target) <= TIGHT_BAND
        rec["rows"] = [G.row("master_gain_cap", False,
                             f"the master gain reached its cap of {MASTER_GAIN_MAX_DB:g} dB (BP-214) and the mix is at {final:.1f} LUFS, "
                             f"off BP-50's target: the input is too quiet or too loud to fix by gain", round(gain_db, 2),
                             level=G.REVIEW)] if capped else []
        rec["master"] = {"gain_db": round(gain_db, 2), "gain_capped": bool(capped), "limiter_ceiling_dbtp": ceiling,
                         "max_gain_reduction_db": round(float(-20 * np.log10(max(1e-9, float(env.min())))), 2)}
    else:
        rec["master"] = {"gain_db": 0.0, "skipped": "master off or silent mix"}
        rec["rows"] = []
    stems["mix"] = stems["narration"] + stems["ambience"] + stems["sfx"] + stems["music"]
    rec["measured"] = measure(stems, voice_mask=mask)
    return stems, rec


def measure(stems: dict, voice_mask: np.ndarray | None = None) -> dict:
    """Own BS.1770 numbers of the finished stems: the mix's integrated loudness and true peak, and the voice-over-music gap
    while the voice speaks."""
    mix = stems["mix"]
    out = {"lufs": None, "true_peak": None}
    il = integrated_lufs(mix)
    out["lufs"] = None if il == float("-inf") else round(il, 2)
    out["true_peak"] = round(true_peak_dbtp(mix), 2) if len(mix) else None
    if voice_mask is not None:
        v_l, m_l = lufs_where(stems["narration"], voice_mask), lufs_where(stems["music"], voice_mask)
        if v_l is not None:
            out["voice_lufs"] = round(v_l, 2)
        if m_l is not None:
            out["music_lufs"] = round(m_l, 2)
    return out


# ---------------------------------------------------------------- scenes: effects and the bed
BED_CROSSFADE_S = 1.0     # cue rows of one bed that abut or overlap by at most this are one continuous bed (a place's crossfade)


def _runs(iv: list[dict]) -> list[dict]:
    """Bed rows that follow each other (abutting, or a crossfade overlap up to ``BED_CROSSFADE_S``) are one bed layer; a hole
    or a longer overlap (two beds at once) stays a separate layer, so the validator still counts both."""
    out: list[dict] = []
    for b in sorted(iv, key=lambda r: (r["start"], r["end"])):
        if out and out[-1]["end"] - BED_CROSSFADE_S <= b["start"] <= out[-1]["end"] + 1e-6:
            out[-1] = {"start": out[-1]["start"], "end": max(out[-1]["end"], b["end"])}
        else:
            out.append(dict(b))
    return out


def scenes_of(plan: dict, placed: list[dict], sheet_rows: list[dict]) -> tuple[list[dict], list[tuple], dict]:
    """``(scenes, bed_sets, windows)``: per scene (a plan segment) its effects (the events placed on its shots) and the bed
    intervals the cue sheet plays inside its window."""
    seg_shots: dict = {}
    for s in plan.get("shots", []):
        seg_shots.setdefault(s.get("segment_id"), []).append(s)
    windows = {sid: (min(s["start_s"] for s in ss), max(s["start_s"] + s["dur_s"] for s in ss)) for sid, ss in seg_shots.items()}
    shot_seg = {s["shot_id"]: s.get("segment_id") for s in plan.get("shots", [])}
    scenes = [{"scene_id": sid, "effects": [e for e in placed if shot_seg.get(e.get("shot_id")) == sid
                                            and e.get("layer") in ("foley", "spot", "transition")]} for sid in windows]
    beds = [r for r in sheet_rows if r.get("layer") == "ambience" and not str(r.get("cue_id", "")).startswith("EV_")]
    bed_sets = []
    for sid, (a, b) in windows.items():
        iv = [{"start": max(a, float(r["start_s"])), "end": min(b, float(r["end_s"]))} for r in beds
              if float(r["end_s"]) > a and float(r["start_s"]) < b]
        bed_sets.append((sid, _runs(iv), b - a, a))
    return scenes, bed_sets, windows


def scene_rows(plan: dict, placed: list[dict], sheet_rows: list[dict]) -> list[dict]:
    """VAL-MIX-04 (effects per scene) and VAL-MIX-05 (one bed, no gap) for every scene of a rendered plan."""
    scenes, bed_sets, _ = scenes_of(plan, placed, sheet_rows)
    rows = list(VM.effects_per_scene(scenes))
    for sid, iv, dur, a in bed_sets:
        r = VM.one_continuous_bed([{"start": b["start"] - a, "end": b["end"] - a} for b in iv], dur)
        rows.append({**r, "gate": f"VAL-MIX-05:{sid}"})
    return rows


# ---------------------------------------------------------------- verification after the codec
def aac_roundtrip(wav: Path, bitrate: str | None = None) -> dict:
    """Encode the mix to AAC (the delivery codec) and measure the decoded result with ffmpeg's ebur128: the true peak after the
    codec is what BP-50 means by 'codec-safe'. ``{}`` and a reason when ffmpeg is absent."""
    if shutil.which("ffmpeg") is None:
        return {"not_run": "ffmpeg is not installed"}
    bitrate = bitrate or f"{AAC_KBPS}k"
    with tempfile.TemporaryDirectory() as d:
        m4a = Path(d) / "x.m4a"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", "-b:a", bitrate, str(m4a)], check=True)
        meas = T.measure_file(m4a)
    return {"codec": f"aac {bitrate}", **meas}


def verify(stems_dir: Path, plan: dict | None = None, placed: list[dict] | None = None, sheet_rows: list[dict] | None = None,
           duration_s: float | None = None) -> dict:
    """Measure a rendered stem set and judge it with ``validators/mix`` (every row measures or says NOT_RUN): loudness and true
    peak of the file (ffmpeg ebur128, an independent measurement from the chain's own), true peak after AAC, the voice over the
    music, effects per scene and the bed per scene."""
    stems_dir = Path(stems_dir)

    def read(name):
        with wave.open(str(stems_dir / f"{name}.wav")) as w:
            raw, ch = w.readframes(w.getnframes()), w.getnchannels()
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
        return x.reshape(-1, ch)
    nar, mus = read("narration"), read("music")
    mask = speech_mask(nar.mean(axis=1))
    meas = {}
    if shutil.which("ffmpeg"):
        meas = T.measure_file(stems_dir / "mix.wav")
    else:
        mix = read("mix")
        meas = {"lufs": integrated_lufs(mix), "true_peak": true_peak_dbtp(mix)}
    v_l, m_l = lufs_where(nar, mask), lufs_where(mus, mask)
    if v_l is not None:
        meas["voice_lufs"] = v_l
    if m_l is not None:
        meas["music_lufs"] = m_l
    rows = [VM.loudness(meas), VM.true_peak(meas), VM.voice_over_music(meas)]
    codec = aac_roundtrip(stems_dir / "mix.wav")
    if "true_peak" in codec:
        r = VM.true_peak(codec)
        rows.append({**r, "gate": "VAL-MIX-02:after_aac", "detail": "after AAC: " + r["detail"]})
    else:
        rows.append(G.row("VAL-MIX-02:after_aac", None, "NOT_RUN: " + codec.get("not_run", "no true peak after the codec")))
    if plan is not None and placed is not None and sheet_rows is not None:
        rows += scene_rows(plan, placed, sheet_rows)
    else:
        rows += [G.row("VAL-MIX-04", None, "NOT_RUN: no plan, placed events and cue sheet given"),
                 G.row("VAL-MIX-05", None, "NOT_RUN: no plan, placed events and cue sheet given")]
    return {"schema": "mix_verify/1", "measured": {k: (round(v, 2) if isinstance(v, float) else v) for k, v in meas.items()},
            "after_aac": codec, "rows": rows, "verdict": G.verdict(rows)}
