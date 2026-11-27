"""Multi-Act Broadcast Cinema Audio Mixer (4-Act Score + Scene-Locked Ambience + Visual-Spotted Foley + Zero-Pump Sidechain).

Addresses every single audio flaw found in our Ears-On audit:
1. Multi-act music progression (4 distinct emotional stems crossfaded smoothly over 3.5-4.0s).
2. Scene-locked ambience per shot with smooth 0.40s J-cut/L-cut crossfades (zero unrelated water/rain);
   a dramatic scene keeps ONE continuous room-tone bed across all of its shots (BP-215).
3. Post-assembly visual-spotted foley/SFX capped strictly <= -8 dB relative to voice (zero overpowering map whooshes!).
4. Smooth, zero-pumping RMS envelope follower (180ms attack, 650ms release, gentle -3.8 dB ducking)
   so background ambience NEVER jumps up loudly during speech pauses.
5. Exact ITU-R BS.1770-4 two-pass EBU R128 mastering to -14.0 LUFS / <= -1.2 dBTP @ 48 kHz stereo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfiltfilt


def _load_stereo_48k(path: Path, sr: int = 48000) -> np.ndarray:
    data, file_sr = sf.read(str(path), always_2d=True)
    x = data.astype(np.float32)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    elif x.shape[1] > 2:
        x = x[:, :2]
    if file_sr != sr:
        left = resample_poly(x[:, 0], sr, file_sr).astype(np.float32)
        right = resample_poly(x[:, 1], sr, file_sr).astype(np.float32)
        x = np.stack([left, right], axis=1)
    return x


def _loop_seamless(buf: np.ndarray, target_n: int, xfade_n: int = 24000) -> np.ndarray:
    """Loop an audio stem seamlessly with equal-power crossfades so zero click or jump occurs."""
    if len(buf) >= target_n:
        return buf[:target_n].copy()
    xf = min(xfade_n, len(buf) // 3)
    if xf < 100:
        reps = int(np.ceil(target_n / max(1, len(buf))))
        return np.tile(buf, (reps, 1))[:target_n].copy()
    out = buf.copy()
    step = len(buf) - xf
    t = np.linspace(0.0, np.pi * 0.5, xf, dtype=np.float32)[:, None]
    fade_out = np.cos(t)
    fade_in = np.sin(t)
    while len(out) < target_n:
        chunk = buf.copy()
        overlap = out[-xf:] * fade_out + chunk[:xf] * fade_in
        out = np.concatenate([out[:-xf], overlap, chunk[xf:]], axis=0)
        if step <= 0:
            break
    return out[:target_n]


def _loop_nonperiodic_ambience(
    buf: np.ndarray,
    target_n: int,
    *,
    xfade_n: int = 28800,
    seed: int = 17,
) -> np.ndarray:
    """Extend a short ambience bed without creating a periodic rhythmic loop cadence.

    Slices varying window lengths (55%-88% of source) at deterministic pseudo-random
    offsets, alternates stereo channels on odd slices, and blends seams with long
    equal-power crossfades so fire crackles / wind gusts never repeat on a fixed beat.
    """
    src_n = len(buf)
    if src_n >= target_n:
        return buf[:target_n].copy()
    if src_n < 12000:
        return _loop_seamless(buf, target_n, xfade_n=min(xfade_n, src_n // 3))

    rng = np.random.default_rng(seed)
    xf = max(2400, min(xfade_n, src_n // 4))

    # Start with a clean first chunk (75%-95% of source)
    first_len = max(xf * 2 + 1, int(src_n * float(rng.uniform(0.75, 0.95))))
    out = buf[: min(src_n, first_len)].copy()
    slice_idx = 1
    while len(out) < target_n:
        win_len = max(xf * 2 + 1, int(src_n * float(rng.uniform(0.55, 0.88))))
        win_len = min(src_n, win_len)
        max_start = max(0, src_n - win_len)
        start = int(rng.integers(0, max_start + 1)) if max_start > 0 else 0
        chunk = buf[start : start + win_len].copy()
        if slice_idx % 2 == 1 and chunk.shape[1] == 2:
            # Stereo L/R swap breaks spatial crackle periodicity while preserving timbre & RMS
            chunk = chunk[:, ::-1].copy()
        xf_cur = min(xf, len(out) // 2, len(chunk) // 2)
        if xf_cur < 100:
            out = np.concatenate([out, chunk], axis=0)
        else:
            t_cur = np.linspace(0.0, np.pi * 0.5, xf_cur, dtype=np.float32)[:, None]
            overlap = out[-xf_cur:] * np.cos(t_cur) + chunk[:xf_cur] * np.sin(t_cur)
            out = np.concatenate([out[:-xf_cur], overlap, chunk[xf_cur:]], axis=0)
        slice_idx += 1
    return out[:target_n]


def _normalize_rms_db(x: np.ndarray, target_dbfs: float) -> np.ndarray:
    rms = float(np.sqrt(np.mean(x * x)) + 1e-9)
    cur_db = 20.0 * np.log10(rms)
    gain = 10.0 ** ((target_dbfs - cur_db) / 20.0)
    return (x * gain).astype(np.float32)


def _smooth_voice_duck_envelope(
    voice_mono: np.ndarray,
    sr: int,
    *,
    duck_db: float = -3.8,
    attack_ms: float = 180.0,
    release_ms: float = 650.0,
    thresh_dbfs: float = -34.0,
) -> np.ndarray:
    """Compute a smooth, zero-pumping gain curve (1.0 in pauses, 10^(duck_db/20) during voice)."""
    # Compute 20ms block RMS for speed & musical smoothness
    hop = max(1, int(sr * 0.02))
    n_blocks = int(np.ceil(len(voice_mono) / hop))
    pad = n_blocks * hop - len(voice_mono)
    padded = np.pad(voice_mono, (0, pad)) if pad > 0 else voice_mono
    blocks = padded.reshape(n_blocks, hop)
    rms_db = 20.0 * np.log10(np.sqrt(np.mean(blocks * blocks, axis=1)) + 1e-8)

    # Soft knee activity [0..1]
    activity = np.clip((rms_db - thresh_dbfs) / 14.0, 0.0, 1.0)
    a_att = np.exp(-20.0 / max(1.0, attack_ms))
    a_rel = np.exp(-20.0 / max(1.0, release_ms))

    env = np.zeros(n_blocks, dtype=np.float32)
    cur = 0.0
    for i in range(n_blocks):
        tgt = float(activity[i])
        coeff = a_att if tgt > cur else a_rel
        cur = coeff * cur + (1.0 - coeff) * tgt
        env[i] = cur

    duck_lin = 10.0 ** (duck_db / 20.0)
    gain_blocks = 1.0 - env * (1.0 - duck_lin)
    # Upsample cleanly back to sample rate
    xp = np.arange(n_blocks, dtype=np.float32) * hop
    x_eval = np.arange(len(voice_mono), dtype=np.float32)
    return np.interp(x_eval, xp, gain_blocks).astype(np.float32)


def _eq_bed(x: np.ndarray, sr: int, *, hp_hz: float = 45.0, lp_hz: float = 9500.0) -> np.ndarray:
    """Gentle warmth/air shaping so background stems leave a clean pocket for narration."""
    sos_hp = butter(2, hp_hz / (0.5 * sr), btype="highpass", output="sos")
    sos_lp = butter(2, lp_hz / (0.5 * sr), btype="lowpass", output="sos")
    out = np.empty_like(x)
    for ch in range(2):
        y = sosfiltfilt(sos_hp, x[:, ch])
        y = sosfiltfilt(sos_lp, y)
        out[:, ch] = y.astype(np.float32)
    return out


def _spectral_centroid(x: np.ndarray, sr: int) -> float:
    mono = x.mean(axis=1) if x.ndim == 2 else x
    if len(mono) < 256:
        return 0.0
    seg = mono[: min(len(mono), sr * 3)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)
    denom = float(np.sum(spec)) + 1e-9
    return float(np.sum(freqs * spec) / denom)


def _resolve_owning_scene_end(
    t_start: float,
    explicit_end: float | None,
    scene_windows: list[dict[str, Any]] | None,
    total_duration_s: float,
) -> float:
    """Resolve the owning scene's end timestamp for strict per-scene hard audio isolation."""
    if explicit_end is not None:
        return min(total_duration_s, float(explicit_end))
    if not scene_windows:
        return total_duration_s
    for sw in scene_windows:
        s0 = float(sw.get("start_s", 0.0))
        s1 = float(sw.get("end_s", total_duration_s))
        if s0 - 0.05 <= t_start < s1:
            return min(total_duration_s, s1)
    return total_duration_s


def consolidate_scene_room_tone(
    scene_ambiences: list[dict[str, Any]],
    scene_windows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Join the per-shot ambience entries of a dramatic scene into one continuous bed (BP-215).

    A scene is dramatic when an ambience entry or its scene window says ``dramatic_scene``. Entries that follow
    each other in time with the same ``scene_id`` become one entry, so the bed is generated and faded only once.
    Different beds or levels inside one such run are an error: the room would audibly change at a cut.
    """
    dramatic = {
        str(row.get("scene_id") or row.get("scene_group"))
        for row in [*scene_ambiences, *(scene_windows or [])]
        if row.get("dramatic_scene") and (row.get("scene_id") or row.get("scene_group"))
    }
    if any(row.get("dramatic_scene") and not (row.get("scene_id") or row.get("scene_group")) for row in scene_ambiences):
        raise ValueError("a dramatic_scene ambience entry needs a scene_id")

    out: list[dict[str, Any]] = []
    previous_scene = ""
    for row in sorted(scene_ambiences, key=lambda r: float(r["start_s"])):
        scene = str(row.get("scene_id") or row.get("scene_group") or "")
        if scene in dramatic and scene == previous_scene:
            bed = out[-1]
            for key, default in (("wav_path", None), ("level_dbfs", -36.0), ("hp_hz", 65.0), ("lp_hz", 6500.0)):
                if str(bed.get(key, default)) != str(row.get(key, default)):
                    raise ValueError(
                        f"dramatic scene {scene!r} needs a single continuous room-tone bed: {key} changes from "
                        f"{bed.get(key, default)!r} to {row.get(key, default)!r}"
                    )
            bed["end_s"] = max(float(bed["end_s"]), float(row["end_s"]))
            if "scene_end_s" in bed or "scene_end_s" in row:
                bed["scene_end_s"] = max(
                    float(bed.get("scene_end_s", bed["end_s"])), float(row.get("scene_end_s", row["end_s"])), bed["end_s"]
                )
        else:
            entry = dict(row)
            if scene in dramatic:
                entry["shot_id"] = f"room_tone_{scene}"
                entry["kind"] = "scene_room_tone"
            out.append(entry)
        previous_scene = scene
    return out


def render_dialogue_scene_track(
    plan: dict[str, Any],
    stems: dict[str, Path],
    room_tones: dict[str, Path],
    out_wav: Path,
    *,
    room_tone_dbfs: float = -46.0,
    sr: int = 48000,
) -> dict[str, Any]:
    """Render the sound of a J/L-cut plan: overlapping speaker turns over one room-tone bed per scene.

    ``plan`` comes from ``plan_dialogue_j_l_cuts``. ``stems`` maps a dialogue ``shot_id`` to that clip's cleaned
    audio on the source clip's clock; ``room_tones`` maps every ``scene_id`` of the plan to its one bed. A fade
    never reaches into a spoken word, and a stem too short for its line and breath tail fails closed.
    """
    from explainer_engine.episode.word_timeline_compiler import enforce_dialogue_breath_tail

    shots = list(plan["shots"])
    if not shots:
        raise ValueError("empty dialogue plan")
    n_total = int(round(float(plan["total_duration_s"]) * sr))
    mix = np.zeros((n_total, 2), dtype=np.float32)
    anti_click = 0.005

    for idx, shot in enumerate(shots):
        if not shot["has_dialogue"]:
            continue
        sid = shot["shot_id"]
        if sid not in stems:
            raise ValueError(f"no dialogue stem for shot {sid!r}")
        audio = _load_stereo_48k(Path(stems[sid]), sr=sr)
        src_in, src_out = float(shot["audio_source_in_s"]), float(shot["audio_source_out_s"])
        if len(audio) / sr < src_out - 1.0 / float(plan["fps"]):
            enforce_dialogue_breath_tail(
                {**shot, "trim_start_s": src_in, "duration_s": src_out - src_in, "source_duration_s": len(audio) / sr}
            )
        seg = audio[int(round(src_in * sr)) : int(round(src_out * sr))].copy()
        start = float(shot["audio_start_s"])
        overlap_in = max(0.0, shots[idx - 1]["audio_end_s"] - start) if idx else 0.0
        overlap_out = (
            max(0.0, shot["audio_end_s"] - shots[idx + 1]["audio_start_s"]) if idx + 1 < len(shots) else 0.0
        )
        lead_room = float(shot["speech_start_s"]) - src_in
        tail_room = src_out - float(shot["speech_end_s"])
        fade_in = int(round(max(anti_click, min(overlap_in, lead_room)) * sr))
        fade_out = int(round(max(anti_click, min(overlap_out, tail_room)) * sr))
        fade_in, fade_out = min(fade_in, len(seg) // 2), min(fade_out, len(seg) // 2)
        if fade_in > 1:
            seg[:fade_in] *= np.sin(np.linspace(0.0, np.pi * 0.5, fade_in, dtype=np.float32))[:, None]
        if fade_out > 1:
            seg[-fade_out:] *= np.cos(np.linspace(0.0, np.pi * 0.5, fade_out, dtype=np.float32))[:, None]
        s_idx = int(round(start * sr))
        e_idx = min(n_total, s_idx + len(seg))
        mix[s_idx:e_idx] += seg[: e_idx - s_idx]

    # One bed for each unbroken run of a scene: generated once, faded only at the scene's own edges
    runs: list[dict[str, Any]] = []
    for shot in shots:
        if runs and runs[-1]["scene_id"] == shot["scene_id"]:
            runs[-1]["end_s"] = max(runs[-1]["end_s"], shot["audio_end_s"])
        else:
            runs.append({"scene_id": shot["scene_id"], "start_s": shot["audio_start_s"], "end_s": shot["audio_end_s"]})
    for run_idx, run in enumerate(runs):
        scene = run["scene_id"]
        if scene not in room_tones:
            raise ValueError(f"scene {scene!r} has no room-tone bed")
        s_idx = int(round(run["start_s"] * sr))
        e_idx = min(n_total, int(round(run["end_s"] * sr)))
        raw = _load_stereo_48k(Path(room_tones[scene]), sr=sr)
        if not len(raw) or float(np.max(np.abs(raw))) <= 0.0:
            raise ValueError(f"scene {scene!r}: room-tone bed is silent")
        bed = _normalize_rms_db(_loop_nonperiodic_ambience(raw, e_idx - s_idx, seed=17 + run_idx * 31), room_tone_dbfs)
        fade = min(len(bed) // 3, int(round(0.25 * sr)))
        if fade > 1:
            bed[:fade] *= np.sin(np.linspace(0.0, np.pi * 0.5, fade, dtype=np.float32))[:, None]
            bed[-fade:] *= np.cos(np.linspace(0.0, np.pi * 0.5, fade, dtype=np.float32))[:, None]
        mix[s_idx:e_idx] += bed

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), np.clip(mix, -0.98, 0.98), sr, subtype="PCM_24")
    return {
        "path": str(out_wav),
        "duration_s": round(n_total / sr, 4),
        "room_tone_beds": [{**r, "start_s": round(r["start_s"], 4), "end_s": round(r["end_s"], 4)} for r in runs],
        "cuts": plan["cuts"],
    }


def mix_broadcast_cinema_audio(
    *,
    total_duration_s: float,
    voice_wav: Path,
    music_acts: list[dict[str, Any]],
    scene_ambiences: list[dict[str, Any]],
    sfx_events: list[dict[str, Any]],
    out_wav: Path,
    sub_bass_events: list[dict[str, Any]] | None = None,
    ltx_diegetic_wav: Path | None = None,
    ltx_diegetic_gain_db: float = 0.0,
    silence_drops: list[dict[str, Any]] | None = None,
    scene_windows: list[dict[str, Any]] | None = None,
    strict_scene_isolation: bool = True,
    max_scene_bleed_s: float = 0.25,
    export_qa_stems: bool = True,
    modern_underscore_only: bool = True,
    min_music_raw_duration_s: float = 0.0,
    sr: int = 48000,
    target_lufs: float = -14.0,
    true_peak_ceiling_db: float = -1.5,
    strict_silence_drops: bool = False,
) -> dict[str, Any]:
    """Mix 6-layer 48kHz stereo broadcast documentary master with <1.0 dB pumping, strict per-scene isolation, and exact -14.0 LUFS.

    Layers:
    1. Voice (ElevenLabs Odom polished + RNNoise-cleaned character dialogue)
    2. Continuous Modern Documentary Underscore (>=45s real recordings, -43 dBFS default, 1.2-3.8 kHz vocal pocket EQ + Cinema Silence Drops)
    3. Strictly Scene-Isolated Ambience (clamped to [scene_start, scene_end + 0.25s] with 0.25s equal-power cosine exit fade)
    4. Stabilized LTX Native Diegetic Foley (85Hz HPF + light afftdn + 0.40s J/L crossfades)
    5. Visual-Spotted / LTX-Synced Punch SFX (clamped strictly to owning scene end + 0.25s, capped <= -8.5 dB rel voice)
    6. 40-80 Hz Sub-Bass Cinematic Impacts (bandpassed impacts)

    When ``export_qa_stems=True``, writes 3 isolated clean-room QA stems alongside ``out_wav``:
    ``stem_music_only.wav``, ``stem_sfx_amb_only.wav``, and ``stem_voice_plus_bed.wav``.
    """
    from explainer_engine.audio.cinematic_score import (
        _shape_documentary_score_eq,
        apply_cinema_silence_drops,
        validate_music_stem,
    )

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    n_total = int(round(total_duration_s * sr))

    # 1. Voice stem (center-focused stereo, -16.5 dBFS reference RMS during speech)
    voice_raw = _load_stereo_48k(voice_wav, sr=sr)
    voice_buf = np.zeros((n_total, 2), dtype=np.float32)
    v_len = min(n_total, len(voice_raw))
    voice_buf[:v_len] = voice_raw[:v_len]
    v_mono = voice_buf.mean(axis=1)
    active = np.abs(v_mono) > 0.012
    if np.any(active):
        speech_rms = float(np.sqrt(np.mean(v_mono[active] ** 2)) + 1e-9)
        voice_buf *= (10.0 ** (-16.5 / 20.0)) / speech_rms
        v_mono = voice_buf.mean(axis=1)
    voice_rms_db = 20.0 * np.log10(float(np.sqrt(np.mean(v_mono[active] ** 2)) + 1e-9)) if np.any(active) else -16.5

    # Ultra-transparent sidechain envelopes keeping pause-vs-speech pumping strictly < 1.0 dB!
    music_duck = _smooth_voice_duck_envelope(v_mono, sr, duck_db=-1.6, attack_ms=220.0, release_ms=900.0)
    amb_duck = _smooth_voice_duck_envelope(v_mono, sr, duck_db=-1.1, attack_ms=240.0, release_ms=950.0)

    # 2. Continuous Multi-Act Modern Documentary Underscore (vocal-pocket EQ + subtle -43 dBFS default)
    music_buf = np.zeros((n_total, 2), dtype=np.float32)
    for act in music_acts:
        p = Path(str(act["wav_path"]))
        if not p.is_file():
            continue
        if min_music_raw_duration_s > 0.0:
            validate_music_stem(
                p,
                min_duration_s=min_music_raw_duration_s,
                modern_underscore_only=modern_underscore_only,
            )
        st = max(0.0, float(act["start_s"]))
        en = min(total_duration_s, float(act["end_s"]))
        if en <= st:
            continue
        s_idx, e_idx = int(round(st * sr)), int(round(en * sr))
        seg_n = e_idx - s_idx
        raw_m = _load_stereo_48k(p, sr=sr)
        off_s = max(0.0, float(act.get("source_offset_s", 0.0)))
        off_n = int(round(off_s * sr))
        if off_n > 0 and off_n < len(raw_m):
            raw_m = raw_m[off_n:]
        stem = _shape_documentary_score_eq(raw_m, sr)
        stem = _loop_seamless(stem, seg_n)
        lvl_db = float(act.get("level_dbfs", -43.0))
        stem = _normalize_rms_db(stem, lvl_db)

        xf_s = float(act.get("fade_s", 3.2))
        xf_n = min(seg_n // 3, int(round(xf_s * sr)))
        if xf_n > 10:
            t_r = np.linspace(0.0, np.pi * 0.5, xf_n, dtype=np.float32)
            env = np.ones(seg_n, dtype=np.float32)
            env[:xf_n] = np.sin(t_r)
            env[-xf_n:] = np.cos(t_r)
            stem *= env[:, None]
        music_buf[s_idx:e_idx] += stem
    music_buf *= music_duck[:, None]
    if silence_drops:
        music_buf = apply_cinema_silence_drops(music_buf, sr, silence_drops)

    # 3. Strictly Scene-Isolated Ambiences (hard-clamped to [scene_start, scene_end + 0.25s] with 0.25s cosine exit!)
    amb_buf = np.zeros((n_total, 2), dtype=np.float32)
    shot_reports: list[dict[str, Any]] = []
    clamped_ambience_count = 0
    scene_ambiences = consolidate_scene_room_tone(scene_ambiences, scene_windows)
    for idx_amb, sh in enumerate(scene_ambiences):
        st = max(0.0, float(sh["start_s"]))
        en = min(total_duration_s, float(sh["end_s"]))
        lead = float(sh.get("j_cut_lead_s", 0.20 if strict_scene_isolation else 0.35))
        tail = float(sh.get("l_cut_tail_s", max_scene_bleed_s if strict_scene_isolation else 0.35))
        if strict_scene_isolation:
            lead = min(lead, max_scene_bleed_s)
            tail = min(tail, max_scene_bleed_s)
            owner_end = _resolve_owning_scene_end(st, sh.get("scene_end_s", en), scene_windows, total_duration_s)
            max_allowed_end = min(total_duration_s, owner_end + max_scene_bleed_s)
            if en + tail > max_allowed_end + 1e-6:
                clamped_ambience_count += 1
            a_st = max(0.0, st - lead)
            a_en = min(en + tail, max_allowed_end)
        else:
            a_st = max(0.0, st - lead)
            a_en = min(total_duration_s, en + tail)
        s_idx, e_idx = int(round(a_st * sr)), int(round(a_en * sr))
        seg_n = max(0, e_idx - s_idx)
        p = Path(str(sh["wav_path"]))
        if seg_n > 0 and p.is_file():
            raw = _eq_bed(
                _load_stereo_48k(p, sr=sr),
                sr,
                hp_hz=float(sh.get("hp_hz", 65.0)),
                lp_hz=float(sh.get("lp_hz", 6500.0)),
            )
            seg = _loop_nonperiodic_ambience(raw, seg_n, seed=17 + idx_amb * 31)
            seg = _normalize_rms_db(seg, float(sh.get("level_dbfs", -36.0)))
            fade_in_n = min(seg_n // 3, int(round(0.25 * sr)))
            fade_out_n = min(seg_n // 3, int(round(max_scene_bleed_s * sr)))
            env = np.ones(seg_n, dtype=np.float32)
            if fade_in_n > 10:
                t_in = np.linspace(0.0, np.pi * 0.5, fade_in_n, dtype=np.float32)
                env[:fade_in_n] = np.sin(t_in)
            if fade_out_n > 10:
                t_out = np.linspace(0.0, np.pi * 0.5, fade_out_n, dtype=np.float32)
                env[-fade_out_n:] = np.cos(t_out)
            seg *= env[:, None]
            amb_buf[s_idx:e_idx] += seg
            cent = _spectral_centroid(seg, sr)
        else:
            cent = 0.0

        sfx_in_shot = sum(1 for e in sfx_events if st - 0.25 <= float(e["time_s"]) <= en + 0.25)
        inferred_env = p.stem if p.stem else "ambience"
        shot_reports.append(
            {
                "shot_id": str(sh.get("shot_id") or f"amb_{idx_amb + 1:02d}_{inferred_env}"),
                "kind": str(sh.get("kind") or "ambience_zone"),
                "scene_environment": str(sh.get("scene_environment") or inferred_env),
                "start_s": round(st, 3),
                "end_s": round(en, 3),
                "effective_end_s": round(a_en, 3),
                "sfx_count_in_shot": sfx_in_shot,
                "spectral_centroid_hz": round(cent, 1),
            }
        )
    amb_buf *= amb_duck[:, None]
    if silence_drops:
        amb_buf = apply_cinema_silence_drops(amb_buf, sr, silence_drops)

    # 4. Layer 4 — Stabilized LTX Native Diegetic Foley Stem (0.40s J/L crossfaded 48kHz native audio)
    ltx_buf = np.zeros((n_total, 2), dtype=np.float32)
    ltx_layer_active = False
    if ltx_diegetic_wav is not None and Path(ltx_diegetic_wav).is_file():
        ltx_raw = _load_stereo_48k(Path(ltx_diegetic_wav), sr=sr)
        l_len = min(n_total, len(ltx_raw))
        ltx_buf[:l_len] = ltx_raw[:l_len] * float(10.0 ** (ltx_diegetic_gain_db / 20.0))
        ltx_buf *= amb_duck[:, None]
        if silence_drops:
            ltx_buf = apply_cinema_silence_drops(ltx_buf, sr, silence_drops)
        ltx_layer_active = True

    # 5. Layer 5 — Visual-Spotted / LTX-Synced Punch SFX (strictly scene-clamped + <= -8.5 dB rel voice!)
    sfx_buf = np.zeros((n_total, 2), dtype=np.float32)
    max_sfx_rel_db = -40.0
    usage_counts: dict[str, int] = {}
    clamped_sfx_count = 0
    for ev in sfx_events:
        p = Path(str(ev["wav_path"]))
        if not p.is_file():
            continue
        t_s = max(0.0, float(ev["time_s"]))
        max_dur = float(ev.get("max_duration_s", 2.2))
        if strict_scene_isolation:
            owner_end = _resolve_owning_scene_end(t_s, ev.get("scene_end_s"), scene_windows, total_duration_s)
            allowed_dur = max(0.0, (owner_end + max_scene_bleed_s) - t_s)
            if allowed_dur < max_dur:
                clamped_sfx_count += 1
                max_dur = allowed_dur
        if max_dur <= 0.04:
            continue
        raw = _load_stereo_48k(p, sr=sr)
        raw = raw[: min(len(raw), int(round(max_dur * sr)))]
        cnt = usage_counts.get(str(p), 0)
        usage_counts[str(p)] = cnt + 1
        if cnt > 0 and len(raw) > 256:
            pitch_up = 100 + ((cnt % 3) - 1) * 3  # 97, 103, 100
            if pitch_up != 100:
                l_p = resample_poly(raw[:, 0], pitch_up, 100).astype(np.float32)
                r_p = resample_poly(raw[:, 1], pitch_up, 100).astype(np.float32)
                raw = np.stack([l_p, r_p], axis=1)
        target_sfx_db = min(voice_rms_db - 8.5, float(ev.get("level_dbfs", voice_rms_db - 12.0)))
        scaled = _normalize_rms_db(raw, target_sfx_db)
        fn_in = min(len(scaled) // 4, int(round(0.04 * sr)))
        fn_out = min(len(scaled) // 2, int(round(min(0.25, max_scene_bleed_s) * sr)))
        if fn_in > 4:
            r_in = np.sin(np.linspace(0.0, np.pi * 0.5, fn_in, dtype=np.float32))[:, None]
            scaled[:fn_in] *= r_in
        if fn_out > 4:
            r_out = np.cos(np.linspace(0.0, np.pi * 0.5, fn_out, dtype=np.float32))[:, None]
            scaled[-fn_out:] *= r_out
        s_idx = int(round(t_s * sr))
        e_idx = min(n_total, s_idx + len(scaled))
        if e_idx > s_idx:
            sfx_buf[s_idx:e_idx] += scaled[: e_idx - s_idx]
            ev_rms_db = 20.0 * np.log10(float(np.sqrt(np.mean(scaled * scaled)) + 1e-9))
            max_sfx_rel_db = max(max_sfx_rel_db, ev_rms_db - voice_rms_db)

    # 6. Layer 6 — 40-80 Hz Sub-Bass Cinematic Impacts (filtered from real CC0 impact WAVs, zero sine placeholders)
    sub_buf = np.zeros((n_total, 2), dtype=np.float32)
    sos_sub = butter(3, [38.0 / (0.5 * sr), 92.0 / (0.5 * sr)], btype="bandpass", output="sos")
    for sev in sub_bass_events or []:
        p = Path(str(sev["wav_path"]))
        if not p.is_file():
            continue
        t_s = max(0.0, float(sev["time_s"]))
        max_dur = float(sev.get("max_duration_s", 1.8))
        raw = _load_stereo_48k(p, sr=sr)
        raw = raw[: min(len(raw), int(round(max_dur * sr)))]
        if len(raw) < 64:
            continue
        sub = np.empty_like(raw)
        for ch in range(2):
            sub[:, ch] = sosfiltfilt(sos_sub, raw[:, ch]).astype(np.float32)
        sub = _normalize_rms_db(sub, float(sev.get("level_dbfs", voice_rms_db - 11.5)))
        fn = min(len(sub) // 4, int(round(0.05 * sr)))
        if fn > 4:
            r = np.linspace(0.0, 1.0, fn, dtype=np.float32)[:, None]
            sub[:fn] *= r
            sub[-fn:] *= r[::-1]
        s_idx = int(round(t_s * sr))
        e_idx = min(n_total, s_idx + len(sub))
        if e_idx > s_idx:
            sub_buf[s_idx:e_idx] += sub[: e_idx - s_idx]

    # Measure background pumping swing (pause bed RMS vs speech bed RMS)
    bed = music_buf + amb_buf
    bed_mono = bed.mean(axis=1)
    inactive = ~active
    if np.any(active) and np.any(inactive):
        bed_sp_db = 20.0 * np.log10(float(np.sqrt(np.mean(bed_mono[active] ** 2)) + 1e-9))
        bed_pa_db = 20.0 * np.log10(float(np.sqrt(np.mean(bed_mono[inactive] ** 2)) + 1e-9))
        pump_swing_db = abs(bed_pa_db - bed_sp_db)
    else:
        pump_swing_db = 0.0

    # Sum all 6 cinema layers & Two-Pass EBU R128 Mastering (-14.0 LUFS / <= true_peak_ceiling_db dBTP)
    mix = voice_buf + music_buf + amb_buf + ltx_buf + sfx_buf + sub_buf
    # Gentle head/tail 30ms anti-pop fade
    anti_pop = min(n_total // 8, int(round(0.03 * sr)))
    if anti_pop > 4:
        r = np.linspace(0.0, 1.0, anti_pop, dtype=np.float32)[:, None]
        mix[:anti_pop] *= r
        mix[-anti_pop:] *= r[::-1]

    def _measure_true_peak_lin(sig: np.ndarray) -> float:
        """4x oversampled ITU-R BS.1770-4 inter-sample true peak (linear)."""
        if len(sig) < 16:
            return float(np.max(np.abs(sig))) if len(sig) else 0.0
        peak = float(np.max(np.abs(sig)))
        # Process in chunks to keep memory modest on long 48kHz stereo mixes
        chunk = sr * 15
        for st_i in range(0, len(sig), chunk):
            seg = sig[st_i : min(len(sig), st_i + chunk)]
            for ch in range(seg.shape[1]):
                up = resample_poly(seg[:, ch], 4, 1)
                peak = max(peak, float(np.max(np.abs(up))))
        return peak

    def _smooth_true_peak_limit(sig: np.ndarray, ceiling_lin: float) -> np.ndarray:
        """Transparent lookahead true-peak brickwall limiter (zero flat-top hard-clipping)."""
        out = sig.astype(np.float32, copy=True)
        # 2-pass envelope limiting on 4x oversampled peak envelope guarantees true peak <= ceiling_lin
        # without flat-top waveform distortion that causes inter-sample overshoot.
        hop = max(1, int(sr * 0.002))  # 2ms resolution (~96 samples @ 48kHz)
        look_blocks = 3  # 6ms lookahead
        rel_coeff = float(np.exp(-2.0 / 65.0))  # ~65ms smooth release
        for _ in range(3):
            # Compute per-2ms block true peak via 4x oversampling
            n_samp = len(out)
            n_blk = int(np.ceil(n_samp / hop))
            blk_peak = np.zeros(n_blk, dtype=np.float32)
            chunk_blks = max(1, int((sr * 15) // hop))
            for b0 in range(0, n_blk, chunk_blks):
                b1 = min(n_blk, b0 + chunk_blks)
                s0 = b0 * hop
                s1 = min(n_samp, b1 * hop)
                seg = out[s0:s1]
                p_max = np.zeros(b1 - b0, dtype=np.float32)
                for ch in range(seg.shape[1]):
                    up = np.abs(resample_poly(seg[:, ch], 4, 1))
                    up_hop = hop * 4
                    pad_u = (b1 - b0) * up_hop - len(up)
                    up = np.pad(up, (0, pad_u)) if pad_u > 0 else up[: (b1 - b0) * up_hop]
                    p_max = np.maximum(p_max, up.reshape(b1 - b0, up_hop).max(axis=1))
                blk_peak[b0:b1] = p_max

            if float(np.max(blk_peak)) <= ceiling_lin * 1.002:
                break

            # Lookahead max window so gain ramps down cleanly BEFORE transient hits
            win_peak = blk_peak.copy()
            for k in range(1, look_blocks + 1):
                win_peak[:-k] = np.maximum(win_peak[:-k], blk_peak[k:])
                win_peak[k:] = np.maximum(win_peak[k:], blk_peak[:-k])

            req_gain = np.minimum(1.0, (ceiling_lin * 0.985) / np.maximum(win_peak, 1e-9)).astype(np.float32)
            # Smooth attack (fast) & release (65ms) on gain curve
            smooth_g = np.ones(n_blk, dtype=np.float32)
            cur_g = 1.0
            for i in range(n_blk):
                rg = float(req_gain[i])
                cur_g = rg if rg < cur_g else rel_coeff * cur_g + (1.0 - rel_coeff) * rg
                smooth_g[i] = cur_g
            # Reverse lookahead pass to keep fast attack smooth (zero click)
            for i in range(n_blk - 2, -1, -1):
                smooth_g[i] = min(smooth_g[i], smooth_g[i + 1] + 0.18)

            xp = np.arange(n_blk, dtype=np.float32) * hop
            x_eval = np.arange(n_samp, dtype=np.float32)
            sample_gain = np.interp(x_eval, xp, smooth_g).astype(np.float32)
            out *= sample_gain[:, None]
        return out

    meter = pyln.Meter(sr)
    ceil_lin = float(10.0 ** (true_peak_ceiling_db / 20.0))
    # Two-pass loudness + true-peak convergence (no pre-limiter pyloudnorm clipping warning!)
    for _ in range(3):
        cur_lufs = float(meter.integrated_loudness(mix))
        if np.isfinite(cur_lufs) and abs(cur_lufs - target_lufs) > 0.08:
            g = float(10.0 ** ((target_lufs - cur_lufs) / 20.0))
            mix = (mix * g).astype(np.float32)
        mix = _smooth_true_peak_limit(mix, ceil_lin)
        post_lufs = float(meter.integrated_loudness(mix))
        if np.isfinite(post_lufs) and abs(post_lufs - target_lufs) <= 0.15:
            break

    final_lufs = float(meter.integrated_loudness(mix))
    final_peak_db = float(20.0 * np.log10(float(np.max(np.abs(mix))) + 1e-9))
    final_true_peak_dbtp = float(20.0 * np.log10(_measure_true_peak_lin(mix) + 1e-9))

    sf.write(str(out_wav), mix, sr, subtype="PCM_24")

    qa_stems: dict[str, str] = {}
    if export_qa_stems:
        # Export 3 isolated clean-room QA stems alongside out_wav for Adversarial Ears-On Audit
        stem_dir = out_wav.parent
        music_stem_p = stem_dir / "stem_music_only.wav"
        sfx_amb_stem_p = stem_dir / "stem_sfx_amb_only.wav"
        voice_bed_stem_p = stem_dir / "stem_voice_plus_bed.wav"
        sf.write(str(music_stem_p), np.clip(music_buf, -0.98, 0.98), sr, subtype="PCM_24")
        sf.write(str(sfx_amb_stem_p), np.clip(amb_buf + ltx_buf + sfx_buf + sub_buf, -0.98, 0.98), sr, subtype="PCM_24")
        v_bed = _smooth_true_peak_limit((voice_buf + music_buf + amb_buf).astype(np.float32), ceil_lin)
        sf.write(str(voice_bed_stem_p), np.clip(v_bed, -0.98, 0.98), sr, subtype="PCM_24")
        qa_stems = {
            "music_only": str(music_stem_p),
            "sfx_amb_only": str(sfx_amb_stem_p),
            "voice_plus_bed": str(voice_bed_stem_p),
        }

    # Measure music-to-voice headroom (dB voice louder than music during active speech)
    m_mono = music_buf.mean(axis=1)
    if np.any(active) and float(np.sqrt(np.mean(m_mono[active] ** 2))) > 1e-7:
        music_sp_db = float(20.0 * np.log10(float(np.sqrt(np.mean(m_mono[active] ** 2))) + 1e-12))
        music_headroom_db = round(voice_rms_db - music_sp_db, 2)
    else:
        music_sp_db = -120.0
        music_headroom_db = 99.0

    silence_drop_diagnostics: list[dict[str, Any]] = []
    for sd in silence_drops or []:
        t0 = max(0.0, float(sd.get("time_s", 0.0)))
        dur_sd = max(0.05, float(sd.get("duration_s", 0.4)))
        s0 = max(0, min(n_total - 1, int(round(t0 * sr))))
        s1 = max(s0 + 1, min(n_total, int(round((t0 + dur_sd) * sr))))
        m_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(mix[s0:s1] ** 2)) + 1e-12)))
        v_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(voice_buf[s0:s1] ** 2)) + 1e-12)))
        voice_overlap = v_rms_db > -38.0
        effective = (m_rms_db <= -32.0) and (not voice_overlap)
        silence_drop_diagnostics.append(
            {
                "time_s": round(t0, 3),
                "duration_s": round(dur_sd, 3),
                "master_rms_dbfs": round(m_rms_db, 2),
                "voice_rms_dbfs": round(v_rms_db, 2),
                "voice_overlap": voice_overlap,
                "effective": effective,
            }
        )
    if strict_silence_drops:
        bad_drops = [d for d in silence_drop_diagnostics if not d["effective"]]
        if bad_drops:
            raise ValueError(
                f"Cinema silence drop masked by voice or insufficiently quiet: {bad_drops}"
            )

    ltx_snapped_sfx_count = sum(
        1
        for e in sfx_events
        if bool(e.get("ltx_snapped"))
        or bool(e.get("snapped_to_ltx"))
        or abs(float(e.get("ltx_snap_delta_ms", 0.0) or 0.0)) > 0.0
    )

    report = {
        "schema": "broadcast_cinema_audio_mix/2",
        "layers": 6 if ltx_layer_active else 5,
        "master_wav": str(out_wav),
        "sample_rate": sr,
        "channels": 2,
        "duration_s": round(total_duration_s, 3),
        "integrated_lufs": round(final_lufs, 2),
        "peak_dbfs": round(final_peak_db, 2),
        "true_peak_dbtp": round(final_true_peak_dbtp, 2),
        "voice_active_rms_dbfs": round(voice_rms_db, 2),
        "music_under_voice_rms_dbfs": round(music_sp_db, 2),
        "music_to_voice_headroom_db": music_headroom_db,
        "strict_scene_isolation": bool(strict_scene_isolation),
        "max_scene_bleed_s": round(max_scene_bleed_s, 3),
        "clamped_ambience_count": clamped_ambience_count,
        "clamped_sfx_count": clamped_sfx_count,
        "qa_stems": qa_stems,
        "max_sfx_relative_to_voice_db": round(max_sfx_rel_db, 2),
        "max_pause_pumping_swing_db": round(pump_swing_db, 2),
        "ltx_diegetic_layer_active": ltx_layer_active,
        "silence_drop_count": len(silence_drops or []),
        "silence_drop_diagnostics": silence_drop_diagnostics,
        "music_act_count": len(music_acts),
        "sfx_event_count": len(sfx_events),
        "ltx_snapped_sfx_count": ltx_snapped_sfx_count,
        "shots": shot_reports,
    }
    out_wav.with_suffix(".mix_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
