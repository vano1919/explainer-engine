"""Assembler Audio Mixer (Upgraded for P0-1 & P1-4):
1. ONE authoritative film clock (episode_timing/2 with timing_id & render_epoch) and ONE trim contract (rec['clip_path']).
2. Map draw SFX emitted dynamically from explainer_engine.maps.tactile_renderer.AudioEventEmitter (no hardcoded MAP_DRAW_SPANS_S).
3. Calls shared explainer_engine.audio.duck.duck_presence_band and stage_spatial_sound (no duplicate inline DSP).
4. Music cues derived from segment mood and scene boundaries (BP-62), with default beds and music silenced during intentional_silence.
5. Final-file integrated LUFS (-14 LUFS target, BP-50), 4x oversampled True Peak (<= -1.0 dBTP, limiter at -1.5 dBTP), and per-shot/per-stem loudness report.
"""
from __future__ import annotations

import json
import os
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy import signal

from explainer_engine.audio import duck as DUCK
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
import hashlib

from explainer_engine.episode import timing as ET
from explainer_engine.maps import actions as MA
from explainer_engine.maps import tactile_renderer as TR
from explainer_engine.standards import sourced_rules as SR_RULES
from explainer_engine.videolane import plan as VP

RENDERER_SCRIPT_REL = VP.RENDERER_SCRIPT_REL

SR = 48000
FPS = 24
TARGET_LUFS = float(SR_RULES.T("BP-50", "lufs"))
PASS_BAND_LUFS = tuple(float(v) for v in SR_RULES.T("BP-50", "pass_band"))
TRUE_PEAK_MAX_DBTP = float(SR_RULES.T("BP-50", "true_peak_max"))
LIMITER_TP_DBTP = float(SR_RULES.T("BP-50", "limiter_tp"))
MUSIC_UNDER_MIN_LU = float(SR_RULES.T("BP-52", "music_under_lu"))
BED_UNDER_MIN_LU = float(SR_RULES.T("BP-52", "bed_under_lu"))
COMBINED_UNDER_MIN_LU = float(SR_RULES.T("BP-52", "combined_under_lu"))


def _default_paths() -> tuple[Path, Path, Path, Path]:
    r = Path(os.environ.get("TRUCE_EPISODE_DIR", "/Users/vano_tatulashvili/Documents/explainer-engine-truce/episodes/ep_truce_1914"))
    dl = Path(os.environ.get("TRUCE_DL_DIR", "/Users/vano_tatulashvili/Documents/hf_truce/dl/explainer-engine/demo_truce_1914/full_film_2026-11-15/inputs"))
    w = Path(os.environ.get("TRUCE_WORK_DIR", "/Users/vano_tatulashvili/Documents/hf_truce/work"))
    t_path = Path(os.environ.get("TRUCE_TIMING_JSON", str(dl / "clock" / "timing.json")))
    return r, dl, w, t_path


def load_mono(p: Path) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def db(g: float) -> float:
    return float(10.0 ** (float(g) / 20.0))


def fade(x: np.ndarray, fi_s: float = 0.04, fo_s: float = 0.06) -> np.ndarray:
    x = x.copy()
    fi, fo = min(int(fi_s * SR), len(x) // 2), min(int(fo_s * SR), len(x) // 2)
    if fi > 0:
        x[:fi] *= np.linspace(0.0, 1.0, fi, dtype=np.float32)
    if fo > 0:
        x[-fo:] *= np.linspace(1.0, 0.0, fo, dtype=np.float32)
    return x


def place_spatial(
    buf: np.ndarray,
    x: np.ndarray,
    t0_s: float,
    gain_db: float = 0.0,
    *,
    source_x: float = 0.5,
    distance: str = "medium",
    camera_op: str = "hold",
    progress: float = 0.0,
) -> None:
    """Place a mono sound into ``buf`` (shape (N, 2)) using shared ``duck.place_spatial_event`` (P1-4 / B4)."""
    DUCK.place_spatial_event(
        buf,
        x,
        t0_s,
        gain_db,
        source_x=source_x,
        distance=distance,
        camera_op=camera_op,
        progress=progress,
        sr=SR,
    )


def loop_fill_spatial(
    buf: np.ndarray,
    src: np.ndarray,
    t0_s: float,
    t1_s: float,
    gain_db: float,
    *,
    source_x: float = 0.5,
    distance: str = "medium",
    camera_op: str = "hold",
    progress: float = 0.0,
    xf_s: float = 0.35,
) -> None:
    i0, i1 = max(0, int(round(t0_s * SR))), min(len(buf), int(round(t1_s * SR)))
    need = i1 - i0
    if need <= 0 or len(src) < 1000:
        return
    out = np.zeros(need, dtype=np.float32)
    pos = 0
    step = max(1000, len(src) - int(0.4 * SR))
    while pos < need:
        take = min(len(src), need - pos)
        chunk = fade(src[:take], 0.12, 0.12)
        out[pos:pos + take] += chunk
        pos += step
    out = fade(out, xf_s, xf_s)
    place_spatial(buf, out, t0_s, gain_db, source_x=source_x, distance=distance, camera_op=camera_op, progress=progress)


def emit_map_audio_events_for_shot(
    shot: dict,
    t_shot: dict,
    *,
    fps: int = FPS,
) -> list[dict]:
    """P1-4 Single Map Audio Path: derive map draw and counter audio events from ``tactile_renderer.AudioEventEmitter``
    and ``maps.actions.emit_frame_locked_audio_events`` on the retimed clock — never from a hardcoded shot dict."""
    n_frames = int(t_shot.get("frames", fps))
    shot_start_s = float(t_shot.get("start_frame", 0)) / float(fps)
    draw_spans = shot.get("draw_spans_frames") or (shot.get("map_spec") or {}).get("draw_spans_frames")
    plan_doc = dict(shot.get("map_spec") or shot)
    plan_doc.setdefault("total_frames", n_frames)
    plan_doc.setdefault("fps", fps)
    if isinstance(draw_spans, list) and draw_spans and not plan_doc.get("frame_locked_audio_events"):
        fl_evs = []
        for idx, sp in enumerate(draw_spans):
            if isinstance(sp, (list, tuple)) and len(sp) >= 2:
                f0, f1 = max(0, int(sp[0])), min(n_frames, int(sp[1]))
                style = str(sp[2]) if len(sp) >= 3 else "chalk"
                sfx_id = "chalk_line__v1" if "chalk" in style else "pencil_line__v1"
                fl_evs.append({
                    "event_id": f"{shot.get('shot_id', 'map')}_{idx}:draw",
                    "action_kind": "front_line" if "chalk" in style else "route_arrow",
                    "class": "map_route_draw",
                    "sfx_id": sfx_id,
                    "sound_token": f"L:{sfx_id}",
                    "sync": "span",
                    "start_frame": f0,
                    "end_frame": f1,
                    "start_s": round(f0 / float(fps), 4),
                    "end_s": round(f1 / float(fps), 4),
                    "dur_s": round((f1 - f0) / float(fps), 4),
                })
        plan_doc["frame_locked_audio_events"] = fl_evs
    emitter = TR.AudioEventEmitter(plan_doc)
    out_events: list[dict] = []
    for ev in emitter.events:
        ev_copy = dict(ev)
        tok = str(ev_copy.get("sound_token") or "")
        if "sfx_id" not in ev_copy and tok.startswith("L:"):
            ev_copy["sfx_id"] = tok[2:]
        sf = int(ev_copy.get("start_frame", 0))
        ef = int(ev_copy.get("end_frame", sf + 1))
        ev_copy["timeline_start_s"] = round(shot_start_s + sf / float(fps), 4)
        ev_copy["timeline_end_s"] = round(shot_start_s + ef / float(fps), 4)
        out_events.append(ev_copy)
    return out_events


def is_intentional_silence_shot(shot: dict) -> bool:
    """Return True when a shot or its sound plan explicitly requests intentional silence (BP-204 / C1)."""
    if bool(shot.get("intentional_silence") or shot.get("silent_by_design")):
        return True
    sp = shot.get("sound_plan") or {}
    if isinstance(sp, dict) and bool(sp.get("intentional_silence") or sp.get("silent_by_design")):
        return True
    if str(shot.get("speaker_type") or "").lower() == "silent_beat" and bool(shot.get("mute_beds", False)):
        return True
    return False


_MOOD_TO_MUSIC_CUE = {
    "somber": ("somber_strings", -22.0),
    "tense": ("tense_pulse", -23.0),
    "escalation": ("tense_pulse", -23.0),
    "quiet": ("quiet_resolve", -22.5),
    "sacred": ("quiet_resolve", -22.0),
    "warmth": ("warm_cello", -21.5),
    "brotherhood": ("warm_cello", -21.5),
    "elegy": ("somber_strings", -21.0),
    "aftermath": ("somber_strings", -21.0),
}


def build_music_cues_from_script(script_doc: dict, timing_doc: dict) -> list[dict]:
    """P1-4 Scene/Mood-Driven Music Spotting (BP-62): derive music cues from segment mood and retimed scene boundaries,
    never from hardcoded second literals, and preserve at least one >= 10 s planned no-music stretch."""
    fps = int(timing_doc.get("fps") or FPS)
    fade_in_s = float(SR_RULES.T("BP-62", "fade_in_s"))
    fade_out_s = float(SR_RULES.T("BP-62", "fade_out_s"))
    no_music_min_s = float(SR_RULES.T("BP-62", "no_music_stretch_min_s"))

    shots_by_seg: dict[str, list[dict]] = {}
    for s in script_doc.get("shots", []) or []:
        if isinstance(s, dict) and s.get("shot_id") in (timing_doc.get("shots") or {}):
            seg_id = str(s.get("segment_id") or timing_doc["shots"][s["shot_id"]].get("segment_id") or s["shot_id"].split("_")[0])
            shots_by_seg.setdefault(seg_id, []).append(s)

    seg_meta: dict[str, dict] = {}
    for seg in script_doc.get("segments", []) or []:
        if isinstance(seg, dict):
            sid = str(seg.get("id") or seg.get("segment_id") or "")
            if sid:
                seg_meta[sid] = seg

    seg_ids = sorted(shots_by_seg.keys())
    if not seg_ids:
        return []

    # Designate a planned no-music stretch (BP-62: at least one >= 10s stretch without music, e.g. middle transition segment)
    no_music_seg = None
    for sid in seg_ids:
        seg_shots = shots_by_seg[sid]
        if any(is_intentional_silence_shot(sh) for sh in seg_shots):
            no_music_seg = sid
            break
    if no_music_seg is None and len(seg_ids) >= 3:
        mid_idx = len(seg_ids) // 2
        no_music_seg = seg_ids[mid_idx]

    cues: list[dict] = []
    for idx, seg_id in enumerate(seg_ids):
        if seg_id == no_music_seg:
            continue
        seg_shots = shots_by_seg[seg_id]
        active_shots = [sh for sh in seg_shots if not is_intentional_silence_shot(sh)]
        if not active_shots:
            continue
        first_sid = active_shots[0]["shot_id"]
        last_sid = active_shots[-1]["shot_id"]
        t0 = float(timing_doc["shots"][first_sid]["start_frame"]) / float(fps)
        t1 = float(timing_doc["shots"][last_sid].get("end_frame", timing_doc["shots"][last_sid]["start_frame"] + timing_doc["shots"][last_sid]["frames"])) / float(fps)
        if t1 - t0 < 2.0:
            continue
        meta = seg_meta.get(seg_id) or {}
        mood_str = " ".join([
            str(meta.get("mood") or ""),
            str(meta.get("tone") or ""),
            str(meta.get("title") or ""),
            str(active_shots[0].get("mood") or active_shots[0].get("narrative_purpose") or ""),
        ]).lower()
        chosen_cue, gain_db = ("somber_strings", -22.0) if idx in (0, len(seg_ids) - 1) else (
            ("tense_pulse", -23.0) if idx % 3 == 1 else (
                ("quiet_resolve", -22.5) if idx % 3 == 2 else ("warm_cello", -21.5)
            )
        )
        for kw, (cue_name, cue_gain) in _MOOD_TO_MUSIC_CUE.items():
            if kw in mood_str:
                chosen_cue, gain_db = cue_name, cue_gain
                break
        cues.append({
            "segment_id": seg_id,
            "cue": chosen_cue,
            "start_s": round(t0, 4),
            "end_s": round(t1, 4),
            "gain_db": gain_db,
            "fade_in_s": fade_in_s,
            "fade_out_s": fade_out_s,
            "no_music_min_s": no_music_min_s,
        })
    return cues


def _bs1770_k_weight_biquads(sr: int = SR) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return exact ITU-R BS.1770-4 Stage 1 (pre-filter) and Stage 2 (RLB high-pass) biquad coefficients."""
    if int(sr) == 48000:
        b_pre = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285], dtype=np.float64)
        a_pre = np.array([1.0, -1.69065929318241, 0.73248077421585], dtype=np.float64)
        b_rlb = np.array([1.0, -2.0, 1.0], dtype=np.float64)
        a_rlb = np.array([1.0, -1.99004745483398, 0.99007225036621], dtype=np.float64)
        return b_pre, a_pre, b_rlb, a_rlb

    # Bilinear transform from ITU-R BS.1770-4 analog filter specifications for non-48kHz sample rates
    f0_pre = 1681.974450955533
    g_pre = 3.999843853973347
    q_pre = 0.7071752369554196
    k_pre = np.tan(np.pi * f0_pre / float(sr))
    vh = 10.0 ** (g_pre / 20.0)
    vb = vh ** 0.4996667741545416
    a0_p = 1.0 + k_pre / q_pre + k_pre * k_pre
    b_pre = np.array([
        (vh + vb * k_pre / q_pre + k_pre * k_pre) / a0_p,
        2.0 * (k_pre * k_pre - vh) / a0_p,
        (vh - vb * k_pre / q_pre + k_pre * k_pre) / a0_p,
    ], dtype=np.float64)
    a_pre = np.array([
        1.0,
        2.0 * (k_pre * k_pre - 1.0) / a0_p,
        (1.0 - k_pre / q_pre + k_pre * k_pre) / a0_p,
    ], dtype=np.float64)

    f0_rlb = 38.13547087602444
    q_rlb = 0.5003270373238773
    k_rlb = np.tan(np.pi * f0_rlb / float(sr))
    a0_r = 1.0 + k_rlb / q_rlb + k_rlb * k_rlb
    b_rlb = np.array([1.0 / a0_r, -2.0 / a0_r, 1.0 / a0_r], dtype=np.float64)
    a_rlb = np.array([
        1.0,
        2.0 * (k_rlb * k_rlb - 1.0) / a0_r,
        (1.0 - k_rlb / q_rlb + k_rlb * k_rlb) / a0_r,
    ], dtype=np.float64)
    return b_pre, a_pre, b_rlb, a_rlb


def compute_integrated_lufs(audio: np.ndarray, sr: int = SR) -> float:
    """Measure ITU-R BS.1770-4 / EBU R128 gated integrated loudness in LUFS using exact K-weighting biquads
    and channel-weighted energy summation (G_i = 1.0 for L/R/C, summed across channels)."""
    arr = np.asarray(audio, dtype=np.float64)
    if arr.size == 0:
        return -70.0
    if arr.ndim == 1:
        ch_data = arr[:, None]
    elif arr.shape[0] <= 5 and arr.shape[-1] > 5:
        ch_data = arr.T
    else:
        ch_data = arr

    n_samples, n_ch = ch_data.shape
    if n_samples == 0:
        return -70.0

    b_pre, a_pre, b_rlb, a_rlb = _bs1770_k_weight_biquads(sr)
    y = signal.lfilter(b_pre, a_pre, ch_data, axis=0)
    y = signal.lfilter(b_rlb, a_rlb, y, axis=0)
    sq = y * y

    ch_weights = np.ones(n_ch, dtype=np.float64)
    if n_ch >= 5:
        ch_weights[3:5] = 1.41

    win = max(1, int(round(0.400 * sr)))
    hop = max(1, int(round(0.100 * sr)))
    if n_samples < win:
        mean_sq_per_ch = np.mean(sq, axis=0)
        e = float(np.sum(mean_sq_per_ch * ch_weights))
        return float(-0.691 + 10.0 * np.log10(max(1e-12, e)))

    n_blocks = 1 + (n_samples - win) // hop
    cs = np.vstack([np.zeros((1, n_ch), dtype=np.float64), np.cumsum(sq, axis=0)])
    idx0 = np.arange(n_blocks) * hop
    idx1 = idx0 + win
    mean_sq_blocks = (cs[idx1] - cs[idx0]) / float(win)
    blocks = np.sum(mean_sq_blocks * ch_weights[None, :], axis=1)

    l_blocks = -0.691 + 10.0 * np.log10(np.maximum(1e-12, blocks))
    abs_mask = l_blocks > -70.0
    if not np.any(abs_mask):
        return -70.0
    rel_thr = -0.691 + 10.0 * np.log10(max(1e-12, float(np.mean(blocks[abs_mask])))) - 10.0
    rel_mask = abs_mask & (l_blocks > rel_thr)
    gated = blocks[rel_mask] if np.any(rel_mask) else blocks[abs_mask]
    return float(-0.691 + 10.0 * np.log10(max(1e-12, float(np.mean(gated)))))


def read_stereo_wav(wav_path: Path | str) -> tuple[np.ndarray, int]:
    """Reopen a written 16-bit PCM WAV file from disk and return float32 samples (N, C) and sample rate."""
    p = Path(wav_path)
    if not p.is_file():
        raise ContractError(f"Mix WAV file does not exist on disk: {p}")
    with wave.open(str(p), "rb") as wf:
        ch = wf.getnchannels()
        sr = wf.getframerate()
        sw = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
    if sw != 2:
        raise ContractError(f"{p}: expected 16-bit PCM WAV (sampwidth=2), got {sw}")
    arr = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    arr = arr.reshape(-1, ch) if ch > 1 else arr[:, None]
    return arr, sr


def compute_true_peak_dbtp(audio: np.ndarray, oversample: int = 4) -> float:
    """Measure 4x oversampled True Peak in dBTP (BP-50)."""
    arr = np.asarray(audio, dtype=np.float32)
    if arr.size == 0:
        return -120.0
    if arr.ndim == 1:
        arr = arr[:, None]
    elif arr.shape[0] <= 2 and arr.shape[-1] > 2:
        arr = arr.T
    up = signal.resample_poly(arr, oversample, 1, axis=0)
    pk = float(np.max(np.abs(up)))
    return float(20.0 * np.log10(max(1e-9, pk)))


def normalize_to_target_lufs_and_true_peak(
    mix: np.ndarray,
    *,
    target_lufs: float = TARGET_LUFS,
    limiter_dbtp: float = LIMITER_TP_DBTP,
    sr: int = SR,
) -> tuple[np.ndarray, dict]:
    """Scale ``mix`` to ``target_lufs`` (-14.0 LUFS) and apply a soft true-peak ceiling at ``limiter_dbtp`` (-1.5 dBTP)."""
    arr = np.asarray(mix, dtype=np.float32).copy()
    cur_lufs = compute_integrated_lufs(arr, sr=sr)
    if cur_lufs > -65.0:
        gain_db = float(np.clip(target_lufs - cur_lufs, -24.0, 24.0))
        arr *= db(gain_db)
    ceiling_lin = db(limiter_dbtp)
    tp_before = compute_true_peak_dbtp(arr)
    if tp_before > limiter_dbtp:
        # Soft-knee limiter + oversampled ceiling trim so true peak stays strictly <= -1.0 dBTP
        arr = (ceiling_lin * np.tanh(arr / max(1e-6, ceiling_lin))).astype(np.float32)
        tp_mid = compute_true_peak_dbtp(arr)
        if tp_mid > limiter_dbtp:
            arr *= db(limiter_dbtp - tp_mid - 0.08)
    final_lufs = compute_integrated_lufs(arr, sr=sr)
    final_tp = compute_true_peak_dbtp(arr)
    return arr, {
        "target_lufs": target_lufs,
        "integrated_lufs": round(final_lufs, 2),
        "true_peak_dbtp": round(final_tp, 2),
        "pass_lufs": PASS_BAND_LUFS[0] <= final_lufs <= PASS_BAND_LUFS[1],
        "pass_true_peak": final_tp <= TRUE_PEAK_MAX_DBTP,
    }


def measure_mix_loudness_report(
    mix: np.ndarray | Path | str,
    *,
    wav_path: Path | str | None = None,
    voice_stem: np.ndarray | None = None,
    bed_stem: np.ndarray | None = None,
    sfx_stem: np.ndarray | None = None,
    music_stem: np.ndarray | None = None,
    timing_doc: dict | None = None,
    extra_findings: list[dict] | None = None,
    shot_beds: dict[str, dict] | None = None,
    sr: int = SR,
) -> dict:
    """P1-4 & B4 Final-File & Stem Loudness Report: reopen the written WAV from disk when provided,
    measure ITU-R BS.1770-4 integrated LUFS, 4x True Peak dBTP, stem LU gaps under speech (BP-52), and per-shot loudness."""
    measured_from_disk = False
    measured_file_str: str | None = None
    measured_file_sha: str | None = None
    if isinstance(mix, (Path, str)):
        disk_p = Path(mix)
        mix_arr, sr = read_stereo_wav(disk_p)
        measured_from_disk = True
        measured_file_str = str(disk_p)
        measured_file_sha = hashlib.sha256(disk_p.read_bytes()).hexdigest()
    elif wav_path is not None and Path(wav_path).is_file():
        disk_p = Path(wav_path)
        mix_arr, sr = read_stereo_wav(disk_p)
        measured_from_disk = True
        measured_file_str = str(disk_p)
        measured_file_sha = hashlib.sha256(disk_p.read_bytes()).hexdigest()
    else:
        mix_arr = np.asarray(mix, dtype=np.float32)

    mix = mix_arr
    int_lufs = compute_integrated_lufs(mix, sr=sr)
    tp_dbtp = compute_true_peak_dbtp(mix)
    v_lufs = compute_integrated_lufs(voice_stem, sr=sr) if voice_stem is not None else None
    b_lufs = compute_integrated_lufs(bed_stem, sr=sr) if bed_stem is not None else None
    s_lufs = compute_integrated_lufs(sfx_stem, sr=sr) if sfx_stem is not None else None
    m_lufs = compute_integrated_lufs(music_stem, sr=sr) if music_stem is not None else None

    bed_gap = round(v_lufs - b_lufs, 2) if (v_lufs is not None and b_lufs is not None and b_lufs > -65.0) else None
    mus_gap = round(v_lufs - m_lufs, 2) if (v_lufs is not None and m_lufs is not None and m_lufs > -65.0) else None

    per_shot: dict[str, dict] = {}
    if timing_doc and isinstance(timing_doc.get("shots"), dict):
        fps = int(timing_doc.get("fps") or FPS)
        for sid, sh in timing_doc["shots"].items():
            i0 = max(0, int(round(float(sh.get("start_frame", 0)) / fps * sr)))
            i1 = min(len(mix), int(round(float(sh.get("end_frame", int(sh.get("start_frame", 0)) + int(sh.get("frames", 0)))) / fps * sr)))
            if i1 > i0:
                seg_slice = mix[i0:i1]
                per_shot[sid] = {
                    "lufs": round(compute_integrated_lufs(seg_slice, sr=sr), 2),
                    "true_peak_dbtp": round(compute_true_peak_dbtp(seg_slice), 2),
                }

    findings: list[dict] = []
    if not (PASS_BAND_LUFS[0] <= int_lufs <= PASS_BAND_LUFS[1]):
        findings.append({
            "rule": "BP-50",
            "status": "FAIL" if (int_lufs < -16.0 or int_lufs > -13.0) else "REVIEW",
            "detail": f"integrated_lufs={int_lufs:.2f} outside pass band {PASS_BAND_LUFS}",
        })
    if tp_dbtp > TRUE_PEAK_MAX_DBTP:
        findings.append({
            "rule": "BP-50",
            "status": "FAIL",
            "detail": f"true_peak_dbtp={tp_dbtp:.2f} exceeds ceiling {TRUE_PEAK_MAX_DBTP:.1f} dBTP",
        })
    if bed_gap is not None and bed_gap < BED_UNDER_MIN_LU:
        findings.append({
            "rule": "BP-52",
            "status": "FAIL",
            "detail": f"bed_under_voice_lu={bed_gap:.2f} < {BED_UNDER_MIN_LU:.1f} LU",
        })
    if mus_gap is not None and mus_gap < MUSIC_UNDER_MIN_LU:
        findings.append({
            "rule": "BP-52",
            "status": "FAIL",
            "detail": f"music_under_voice_lu={mus_gap:.2f} < {MUSIC_UNDER_MIN_LU:.1f} LU",
        })

    if extra_findings:
        findings.extend(extra_findings)
    status = "FAIL" if any(f["status"] == "FAIL" for f in findings) else ("REVIEW" if findings else "PASS")
    out_rep = {
        "schema": "mix_loudness_report/1",
        "status": status,
        "timing_id": (timing_doc or {}).get("timing_id"),
        "render_epoch": (timing_doc or {}).get("render_epoch"),
        "measured_from_disk": measured_from_disk,
        "measured_file": measured_file_str,
        "measured_file_sha256": measured_file_sha,
        "integrated_lufs": round(int_lufs, 2),
        "true_peak_dbtp": round(tp_dbtp, 2),
        "stems": {
            "voice_lufs": round(v_lufs, 2) if v_lufs is not None else None,
            "bed_lufs": round(b_lufs, 2) if b_lufs is not None else None,
            "sfx_lufs": round(s_lufs, 2) if s_lufs is not None else None,
            "music_lufs": round(m_lufs, 2) if m_lufs is not None else None,
            "bed_under_voice_lu": bed_gap,
            "music_under_voice_lu": mus_gap,
        },
        "per_shot": per_shot,
        "findings": findings,
    }
    if shot_beds is not None:
        out_rep["shot_beds"] = shot_beds
    return out_rep


def synth_sfx(kind: str, dur_s: float = 1.0, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = max(1, int(round(dur_s * SR)))
    t = np.linspace(0.0, dur_s, n, dtype=np.float32)
    if kind in ("chalk", "pencil", "pencil_line__v1", "chalk_line__v1"):
        w = rng.standard_normal(n).astype(np.float32)
        sos = signal.butter(2, [900, 4200], btype="bandpass", fs=SR, output="sos")
        y = signal.sosfilt(sos, w).astype(np.float32)
        mod = 0.55 + 0.45 * np.sin(2 * np.pi * 13.0 * t + 1.8 * np.sin(2 * np.pi * 2.7 * t))
        return fade((y * mod / (np.max(np.abs(y)) + 1e-6) * 0.35).astype(np.float32), 0.03, 0.05)
    if kind in ("tick", "counter_tick"):
        n_tk = min(n, int(0.028 * SR))
        tt = np.linspace(0, 0.028, n_tk, dtype=np.float32)
        clk = (np.sin(2 * np.pi * 1450 * tt) * np.exp(-tt * 140) + 0.4 * rng.standard_normal(n_tk) * np.exp(-tt * 220)).astype(np.float32)
        out = np.zeros(n, dtype=np.float32)
        out[:n_tk] = clk * 0.45
        return out
    w = rng.standard_normal(n).astype(np.float32)
    sos = signal.butter(2, [200, 2400], btype="bandpass", fs=SR, output="sos")
    y = signal.sosfilt(sos, w).astype(np.float32)
    return fade((y / (np.max(np.abs(y)) + 1e-6) * 0.25).astype(np.float32), 0.02, 0.04)


def synth_music_cue(kind: str, dur_s: float, fade_in_s: float = 1.0, fade_out_s: float = 2.0) -> np.ndarray:
    n = max(1, int(round(dur_s * SR)))
    t = np.linspace(0.0, dur_s, n, dtype=np.float32)
    if kind == "somber_strings":
        freqs = [146.83, 220.0, 261.63, 329.63]
        sig = sum(
            (0.28 / (i + 1)) * np.sin(2 * np.pi * f * t + 0.2 * np.sin(2 * np.pi * 0.18 * t))
            for i, f in enumerate(freqs)
        )
        sos = signal.butter(2, 950, btype="low", fs=SR, output="sos")
        sig = signal.sosfilt(sos, sig.astype(np.float32)).astype(np.float32)
    elif kind == "tense_pulse":
        base = 0.35 * np.sin(2 * np.pi * 73.42 * t) + 0.20 * np.sin(2 * np.pi * 110.0 * t)
        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * 0.75 * t)
        sig = (base * pulse).astype(np.float32)
    elif kind == "quiet_resolve":
        freqs = [196.0, 246.94, 293.66, 392.0]
        sig = sum(
            (0.24 / (i + 1)) * np.sin(2 * np.pi * f * t) * np.exp(-0.04 * (t % 4.0))
            for i, f in enumerate(freqs)
        ).astype(np.float32)
    else:
        freqs = [130.81, 196.0, 246.94, 329.63]
        sig = sum(
            (0.26 / (i + 1)) * np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.22 * t))
            for i, f in enumerate(freqs)
        ).astype(np.float32)
    sig = sig / (np.max(np.abs(sig)) + 1e-6) * 0.45
    return fade(sig.astype(np.float32), fade_in_s, fade_out_s)


def run_mix(
    *,
    episode_dir: Path | None = None,
    dl_dir: Path | None = None,
    work_dir: Path | None = None,
    timing_doc: dict | None = None,
    timing_path: Path | None = None,
    script_doc: dict | None = None,
    edit_points: dict | None = None,
) -> dict:
    r_dir, d_dir, w_dir, t_p = _default_paths()
    R = Path(episode_dir) if episode_dir is not None else r_dir
    DL = Path(dl_dir) if dl_dir is not None else d_dir
    W = Path(work_dir) if work_dir is not None else w_dir
    W.mkdir(parents=True, exist_ok=True)
    T_PATH = Path(timing_path) if timing_path is not None else t_p

    if script_doc is None:
        script_doc = json.loads((R / RENDERER_SCRIPT_REL).read_text(encoding="utf-8"))
    if edit_points is None:
        ep_file = R / "planning" / "full_film_2026-11-15" / "edit_points.json"
        edit_points = json.loads(ep_file.read_text(encoding="utf-8")).get("clips", {}) if ep_file.is_file() else {}
    if timing_doc is None:
        raw_t = json.loads(T_PATH.read_text(encoding="utf-8"))
        timing_doc = ET.retime_with_edit_points(raw_t, script_doc, edit_points, episode_dir=R)
        ET.persist_authoritative_clock(timing_doc, T_PATH)

    auth_clock_p = T_PATH if T_PATH.is_file() else (R / "audio" / "timing.json" if (R / "audio" / "timing.json").is_file() else None)
    auth_clock = json.loads(auth_clock_p.read_text(encoding="utf-8")) if auth_clock_p is not None else timing_doc
    align_findings = ET.verify_clock_alignment(auth_clock, timing_doc)
    if align_findings:
        raise ContractError(f"Clock alignment check failed in mix: {align_findings[0]['detail']}")

    sc_by_id = {s["shot_id"]: s for s in script_doc.get("shots", [])}
    sound_plan_shots: dict[str, dict] = {}
    sp_p = R / "audio" / "sound_plan.json"
    if sp_p.is_file():
        try:
            sp_doc = json.loads(sp_p.read_text(encoding="utf-8"))
            for sp_sh in sp_doc.get("shots", []) or []:
                if isinstance(sp_sh, dict) and sp_sh.get("shot_id"):
                    sound_plan_shots[str(sp_sh["shot_id"])] = sp_sh
        except Exception:
            pass

    total_frames = int(timing_doc["total_frames"])
    total_s = total_frames / float(FPS)
    N = int(round(total_s * SR)) + SR

    VOICE = np.zeros((N, 2), dtype=np.float32)
    BEDS = np.zeros((N, 2), dtype=np.float32)
    SFX = np.zeros((N, 2), dtype=np.float32)
    MUS = np.zeros((N, 2), dtype=np.float32)
    mix_findings: list[dict] = []
    shot_beds: dict[str, dict] = {}

    # 1. Place narrator read and single-trimmed spoken inserts using authoritative timing_doc
    read_p = ET.resolve_narration_path(R, dl_dir=DL)
    read_x = load_mono(read_p)
    for row in timing_doc.get("narrator_offsets", []):
        sid = row["shot_id"]
        if row.get("paused_for_insert"):
            dp = (timing_doc.get("dialogue_positions") or {}).get(sid) or {}
            rec_p = R / "production" / "video" / f"{sid}.json"
            rec = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.is_file() else dp
            clip_rel = rec.get("clip_path") or dp.get("clip_path") or f"production/video/cut/{sid}.mp4"
            clip_p = R / clip_rel
            if not clip_p.is_file():
                raise ContractError(f"{sid}: single trim contract requires trimmed clip_path {clip_rel!r} for audio mix")
            seg_x = fade(load_mono(clip_p), 0.04, 0.08)
            e = edit_points.get(sid, {}) if isinstance(edit_points.get(sid), dict) else {}
            if "mute_tail_from_s" in e:
                in_s = float(rec.get("in_s", dp.get("in_s", 0.0)))
                rel_mute = max(0.0, float(e["mute_tail_from_s"]) - in_s)
                m_idx = int(round(rel_mute * SR))
                if 0 <= m_idx < len(seg_x):
                    fl = min(int(0.08 * SR), len(seg_x) - m_idx)
                    if fl > 0:
                        seg_x[m_idx:m_idx + fl] *= np.linspace(1.0, 0.0, fl, dtype=np.float32)
                    seg_x[m_idx + fl:] = 0.0
            rms = float(np.sqrt(np.mean(seg_x ** 2) + 1e-9))
            g = np.clip(0.095 / rms, 0.5, 2.8)
            t0 = float(row["timeline_start_frame"]) / float(FPS)
            place_spatial(VOICE, (seg_x * g).astype(np.float32), t0, 0.0, source_x=0.5, distance="close")
        else:
            r0 = int(round(float(row["read_start_frame"]) / float(FPS) * SR))
            r1 = min(len(read_x), int(round(float(row["read_end_frame"]) / float(FPS) * SR)))
            if r1 > r0:
                seg_x = fade(read_x[r0:r1], 0.02, 0.03)
                t0 = float(row["timeline_start_frame"]) / float(FPS)
                place_spatial(VOICE, seg_x, t0, 0.0, source_x=0.5, distance="close")

    # 1b. Populate ambience beds from sound plan / shot bed spec via loop_fill_spatial, or record intentional absence (B4)
    for sid, t_sh in timing_doc.get("shots", {}).items():
        sh = sc_by_id.get(sid) or {}
        sp_entry = sound_plan_shots.get(sid) or {}
        sh_sp = sh.get("sound_plan") if isinstance(sh.get("sound_plan"), dict) else {}
        t0_bed = float(t_sh.get("start_frame", 0)) / float(FPS)
        t1_bed = float(t_sh.get("end_frame", int(t_sh.get("start_frame", 0)) + int(t_sh.get("frames", 0)))) / float(FPS)
        if is_intentional_silence_shot(sh) or bool(sh_sp.get("bed_intentionally_absent")) or str(sh_sp.get("bed") or "").lower() == "none":
            shot_beds[sid] = {
                "shot_id": sid,
                "bed_populated": False,
                "bed_intentionally_absent": True,
                "reason": "intentional_silence or explicit bed absence in sound plan",
            }
            continue
        bed_kind = str(
            sh_sp.get("bed")
            or (sh.get("audio") or {}).get("bed")
            or (sp_entry.get("bed") or {}).get("class")
            or sp_entry.get("room")
            or "wind_room_tone"
        )
        bed_gain_db = float(sh_sp.get("gain_db", (sp_entry.get("bed") or {}).get("gain_db", -24.0)))
        bed_src_x = float(sh_sp.get("source_x", (sp_entry.get("bed") or {}).get("source_x", 0.5)))
        bed_dist = str(sh_sp.get("distance", (sp_entry.get("bed") or {}).get("distance", "medium")))
        cam_op = str((sh.get("camera_spec") or {}).get("camera_move") or "hold")
        bed_dur = max(1.5, t1_bed - t0_bed)
        bed_src = synth_sfx(bed_kind, dur_s=min(4.0, bed_dur + 0.5), seed=abs(hash((sid, bed_kind))) % 10000)
        loop_fill_spatial(
            BEDS,
            bed_src,
            t0_bed,
            t1_bed,
            bed_gain_db,
            source_x=bed_src_x,
            distance=bed_dist,
            camera_op=cam_op,
        )
        shot_beds[sid] = {
            "shot_id": sid,
            "bed_populated": True,
            "bed_intentionally_absent": False,
            "bed_kind": bed_kind,
            "gain_db": bed_gain_db,
            "source_x": bed_src_x,
            "distance": bed_dist,
            "camera_op": cam_op,
            "start_s": round(t0_bed, 4),
            "end_s": round(t1_bed, 4),
        }

    # 2. Emit map audio events dynamically via tactile_renderer.AudioEventEmitter (P1-4 / B4: no 0.25s/0.35s fallback)
    for sid, t_sh in timing_doc.get("shots", {}).items():
        sh = sc_by_id.get(sid) or {}
        if is_intentional_silence_shot(sh):
            continue
        if sh.get("route") == "map" or sh.get("map_spec") is not None:
            map_evs = emit_map_audio_events_for_shot(sh, t_sh, fps=FPS)
            if not map_evs:
                mix_findings.append({
                    "rule": "BP-203",
                    "shot_id": sid,
                    "status": "REVIEW",
                    "detail": f"{sid}: map shot has no planned frame-locked audio events in AudioEventEmitter (refusing 0.25s/0.35s fallback)",
                })
                continue
            for ev in map_evs:
                if ev.get("timeline_start_s") is None or ev.get("timeline_end_s") is None:
                    mix_findings.append({
                        "rule": "BP-203",
                        "shot_id": sid,
                        "status": "REVIEW",
                        "detail": f"{sid}: map audio event {ev.get('event_id')!r} missing explicit timeline_start_s/timeline_end_s",
                    })
                    continue
                t0 = float(ev["timeline_start_s"])
                t1 = float(ev["timeline_end_s"])
                if t1 <= t0:
                    mix_findings.append({
                        "rule": "BP-203",
                        "shot_id": sid,
                        "status": "REVIEW",
                        "detail": f"{sid}: map audio event {ev.get('event_id')!r} has non-positive duration ({t0}..{t1})",
                    })
                    continue
                kind = str(ev.get("sfx_id") or ev.get("kind") or "chalk")
                dur_ev = t1 - t0
                place_spatial(
                    SFX,
                    synth_sfx(kind, dur_ev, seed=abs(hash((sid, t0))) % 10000),
                    t0,
                    float(ev.get("gain_db", -12.5)),
                    source_x=float(ev.get("screen_x", 0.5)),
                    distance="close",
                )

    # 3. Build scene/mood-driven music cues (BP-62), respecting intentional_silence
    for cue in build_music_cues_from_script(script_doc, timing_doc):
        dur_cue = float(cue["end_s"]) - float(cue["start_s"])
        if dur_cue > 1.0:
            place_spatial(
                MUS,
                synth_music_cue(cue["cue"], dur_cue, cue["fade_in_s"], cue["fade_out_s"]),
                float(cue["start_s"]),
                float(cue["gain_db"]),
                source_x=0.5,
                distance="medium",
            )

    # Zero out BEDS and MUS inside any intentional_silence shot window (BP-204 / C1)
    for sid, t_sh in timing_doc.get("shots", {}).items():
        sh = sc_by_id.get(sid) or {}
        if is_intentional_silence_shot(sh):
            i0 = max(0, int(round(float(t_sh.get("start_frame", 0)) / float(FPS) * SR)))
            i1 = min(N, int(round(float(t_sh.get("end_frame", int(t_sh.get("start_frame", 0)) + int(t_sh.get("frames", 0)))) / float(FPS) * SR)))
            BEDS[i0:i1] = 0.0
            MUS[i0:i1] = 0.0

    # 4. Dynamic presence-band ducking via shared duck.duck_stems_under_voice (BP-204 / B4)
    v_mono = np.mean(VOICE, axis=-1)
    BEDS_DUCKED, MUS_DUCKED = DUCK.duck_stems_under_voice(
        BEDS, MUS, v_mono, sr=SR, bed_presence_cut_db=5.5, bed_outer_cut_db=1.8, music_presence_cut_db=6.5, music_outer_cut_db=2.2
    )

    raw_mix = VOICE + BEDS_DUCKED + SFX + MUS_DUCKED
    final_mix, norm_meta = normalize_to_target_lufs_and_true_peak(raw_mix, target_lufs=TARGET_LUFS, limiter_dbtp=LIMITER_TP_DBTP, sr=SR)

    out_wav = W / "full_mix.wav"
    pcm = np.clip(np.rint(final_mix * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())

    # Reopen the written WAV file from disk to measure the actual delivered file (B4)
    report = measure_mix_loudness_report(
        out_wav,
        wav_path=out_wav,
        voice_stem=VOICE,
        bed_stem=BEDS_DUCKED,
        sfx_stem=SFX,
        music_stem=MUS_DUCKED,
        timing_doc=timing_doc,
        extra_findings=mix_findings,
        shot_beds=shot_beds,
        sr=SR,
    )
    report["normalization"] = norm_meta
    write_json_atomic(out_wav.with_suffix(".loudness.json"), report)
    return report


if __name__ == "__main__":
    rep = run_mix()
    print("WROTE full_mix.wav", json.dumps({"status": rep["status"], "lufs": rep["integrated_lufs"], "dbtp": rep["true_peak_dbtp"]}))
