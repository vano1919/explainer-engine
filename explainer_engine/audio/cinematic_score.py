"""True Continuous Multi-Minute Cinematic Musical Score Engine + 0.4s Cinema Silence Drops.

Eliminates short (<15s) looped SFX drones and synthetic sine pads forever:
1. Enforces a hard fail-closed gate rejecting ANY music track shorter than ``MIN_RAW_MUSIC_DURATION_S = 45.0s``
   or containing synthetic/placeholder markers.
2. Assembles real multi-minute CC0 / Public Domain orchestral, cello, string, and piano recordings across
   story acts with smooth 3.5-4.5s equal-power crossfades, subtle warmth & vocal-pocket shaping, and
   zero jarring loop seams.
3. Supports surgical **0.4s Cinema Silence Drops** (smooth 35ms dip to -36 dB right before major climax
   moments like the first flint spark or alpha wolf snarl, followed by clean emotional swell).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import butter, filtfilt, iirpeak, resample_poly, sosfiltfilt

MIN_RAW_MUSIC_DURATION_S: float = 45.0
FORBIDDEN_MUSIC_TOKENS = ("synth", "sine", "beep", "placeholder", "sfx_loop", "rumble_loop")


def validate_music_stem(
    wav_path: Path,
    *,
    min_duration_s: float = MIN_RAW_MUSIC_DURATION_S,
) -> dict[str, Any]:
    """Fail-closed gate rejecting synthetic music placeholders or any raw track shorter than 45.0 seconds."""
    p = Path(wav_path)
    if not p.is_file():
        raise FileNotFoundError(f"Music score stem not found: {p}")
    low = p.name.lower()
    for bad in FORBIDDEN_MUSIC_TOKENS:
        if bad in low:
            raise ValueError(f"Forbidden synthetic/loop music stem rejected: {p.name}")
    info = sf.info(str(p))
    dur_s = float(info.frames) / float(max(1, info.samplerate))
    if dur_s < min_duration_s:
        raise ValueError(
            f"Music stem {p.name!r} raw duration {dur_s:.2f}s < required {min_duration_s:.1f}s minimum "
            "(short SFX loops are strictly prohibited as musical score)"
        )
    return {
        "status": "PASS",
        "path": str(p),
        "duration_s": round(dur_s, 3),
        "sample_rate": int(info.samplerate),
        "channels": int(info.channels),
    }


def apply_cinema_silence_drops(
    buf: np.ndarray,
    sr: int,
    silence_drops: list[dict[str, Any]],
) -> np.ndarray:
    """Carve crisp 0.4s cinema silence drops (smooth 35ms ramp down, hold, 180ms recovery) before climaxes."""
    if not silence_drops:
        return buf
    out = buf.copy()
    n_total = len(out)
    for drop in silence_drops:
        t_s = float(drop["time_s"])
        dur_s = float(drop.get("duration_s", 0.40))
        depth_db = float(drop.get("depth_db", -36.0))
        ramp_in_s = float(drop.get("ramp_in_s", 0.035))
        ramp_out_s = float(drop.get("ramp_out_s", 0.16))

        i0 = max(0, int(round((t_s - ramp_in_s) * sr)))
        i1 = min(n_total, int(round(t_s * sr)))
        i2 = min(n_total, int(round((t_s + dur_s) * sr)))
        i3 = min(n_total, int(round((t_s + dur_s + ramp_out_s) * sr)))
        floor_lin = float(10.0 ** (depth_db / 20.0))

        if i1 > i0:
            env_in = np.linspace(1.0, floor_lin, i1 - i0, dtype=np.float32)[:, None]
            out[i0:i1] *= env_in
        if i2 > i1:
            out[i1:i2] *= floor_lin
        if i3 > i2:
            t_r = np.linspace(0.0, np.pi * 0.5, i3 - i2, dtype=np.float32)[:, None]
            env_out = floor_lin + (1.0 - floor_lin) * np.sin(t_r)
            out[i2:i3] *= env_out
    return out


def _shape_documentary_score_eq(x: np.ndarray, sr: int) -> np.ndarray:
    """Warm filmic underscore shaping: 42Hz HPF, 6800Hz gentle air rolloff, soft -2.5dB vocal pocket at 1.9kHz."""
    sos_hp = butter(2, 42.0 / (0.5 * sr), btype="highpass", output="sos")
    sos_lp = butter(2, 6800.0 / (0.5 * sr), btype="lowpass", output="sos")
    # Gentle notch attenuation in narrator vocal presence band (~1.9 kHz)
    b_pk, a_pk = iirpeak(1900.0 / (0.5 * sr), Q=1.4)
    out = np.empty_like(x)
    for ch in range(x.shape[1]):
        y = sosfiltfilt(sos_hp, x[:, ch])
        y = sosfiltfilt(sos_lp, y)
        # Subtract 25% of narrow vocal-band peak (~-2.5 dB pocket)
        band = filtfilt(b_pk, a_pk, y)
        y = y - 0.25 * band
        out[:, ch] = y.astype(np.float32)
    return out


def _load_48k_stereo(wav_path: Path, sr: int = 48000) -> np.ndarray:
    data, file_sr = sf.read(str(wav_path), always_2d=True)
    x = data.astype(np.float32)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    elif x.shape[1] > 2:
        x = x[:, :2]
    if file_sr != sr:
        x = np.stack(
            [resample_poly(x[:, 0], sr, file_sr).astype(np.float32), resample_poly(x[:, 1], sr, file_sr).astype(np.float32)],
            axis=1,
        )
    return x


def build_continuous_musical_score(
    score_cues: list[dict[str, Any]],
    *,
    total_duration_s: float,
    out_wav: Path,
    silence_drops: list[dict[str, Any]] | None = None,
    sr: int = 48000,
    min_raw_duration_s: float = MIN_RAW_MUSIC_DURATION_S,
) -> dict[str, Any]:
    """Assemble a continuous, loop-free multi-act musical score stem from verified >=45s real recordings."""
    n_total = max(1, int(round(total_duration_s * sr)))
    score_buf = np.zeros((n_total, 2), dtype=np.float32)
    validated_cues: list[dict[str, Any]] = []

    for cue in score_cues:
        p = Path(str(cue["wav_path"]))
        v = validate_music_stem(p, min_duration_s=min_raw_duration_s)
        st = max(0.0, float(cue["start_s"]))
        en = min(total_duration_s, float(cue["end_s"]))
        if en <= st:
            continue
        seg_n = int(round((en - st) * sr))
        raw = _load_48k_stereo(p, sr=sr)
        offset_s = max(0.0, float(cue.get("source_offset_s", 0.0)))
        s0 = int(round(offset_s * sr))
        if s0 + seg_n > len(raw):
            s0 = max(0, len(raw) - seg_n)
        seg = raw[s0 : s0 + seg_n].copy()
        if len(seg) < seg_n:
            # Pad smoothly only if a cue exceeds a multi-minute piece (never short-loop!)
            pad = np.zeros((seg_n - len(seg), 2), dtype=np.float32)
            seg = np.concatenate([seg, pad], axis=0)

        seg = _shape_documentary_score_eq(seg, sr)
        rms = float(np.sqrt(np.mean(seg * seg)) + 1e-9)
        cur_db = 20.0 * np.log10(rms)
        tgt_db = float(cue.get("level_dbfs", -28.0))
        seg *= float(10.0 ** ((tgt_db - cur_db) / 20.0))

        # Equal-power sine/cosine act crossfades (default 3.5s)
        fade_in_s = float(cue.get("fade_in_s", cue.get("fade_s", 3.5)))
        fade_out_s = float(cue.get("fade_out_s", cue.get("fade_s", 3.5)))
        fn_in = min(seg_n // 3, int(round(fade_in_s * sr)))
        fn_out = min(seg_n // 3, int(round(fade_out_s * sr)))
        if fn_in > 8:
            t_r = np.linspace(0.0, np.pi * 0.5, fn_in, dtype=np.float32)[:, None]
            seg[:fn_in] *= np.sin(t_r)
        if fn_out > 8:
            t_r = np.linspace(0.0, np.pi * 0.5, fn_out, dtype=np.float32)[:, None]
            seg[-fn_out:] *= np.cos(t_r)

        dst_s0 = int(round(st * sr))
        dst_s1 = min(n_total, dst_s0 + seg_n)
        score_buf[dst_s0:dst_s1] += seg[: dst_s1 - dst_s0]
        validated_cues.append(
            {
                "cue_id": cue.get("cue_id", p.stem),
                "wav_path": str(p),
                "raw_duration_s": v["duration_s"],
                "start_s": round(st, 3),
                "end_s": round(en, 3),
                "source_offset_s": round(offset_s, 3),
                "level_dbfs": tgt_db,
            }
        )

    if silence_drops:
        score_buf = apply_cinema_silence_drops(score_buf, sr, silence_drops)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), np.clip(score_buf, -0.98, 0.98), sr, subtype="PCM_24")
    report = {
        "schema": "cinematic_score/1",
        "path": str(out_wav),
        "duration_s": round(total_duration_s, 3),
        "min_raw_duration_enforced_s": min_raw_duration_s,
        "cues": validated_cues,
        "silence_drops": list(silence_drops or []),
    }
    out_wav.with_suffix(".score_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
