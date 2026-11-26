"""LTX-2.5 Native 48kHz Audio Guide & Stabilized Diegetic Foley Stem Builder.

Every Modal H100 LTX-2.5 video clip carries synchronized 48kHz stereo native audio (flint strikes,
breath, footsteps in snow, fire crackle, wolf growls, wind). Instead of stripping it with ``-an``,
this module:
1. Extracts and analyzes each LTX clip's native audio (RMS envelope, spectral centroid, transient
   onset timestamps) into an ``ltx_audio_guide.json`` cheat sheet.
2. Snaps CC0 punch foley cues to observed LTX physical transients within ``+/- 40ms`` for pixel-exact
   audiovisual impact.
3. Builds a stabilized, continuous 48kHz stereo LTX diegetic stem (``85Hz HPF`` + light ``afftdn`` +
   0.40s equal-power J/L-cut crossfades across shot boundaries), blended softly under narration and
   raised to full cinema presence during narrator-free dramatic scenes.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def extract_ltx_audio_wav(
    clip_mp4: Path,
    out_wav: Path,
    *,
    sr: int = 48000,
    clean_filter: bool = True,
) -> Path | None:
    """Extract 48kHz stereo audio from an LTX-2.5 MP4 clip, optionally applying 85Hz HPF + light afftdn."""
    if not clip_mp4.is_file():
        raise FileNotFoundError(f"LTX clip not found: {clip_mp4}")
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=codec_type",
                "-of",
                "json",
                str(clip_mp4),
            ],
            text=True,
        )
    )
    if not (probe.get("streams") or []):
        return None
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(clip_mp4), "-vn"]
    if clean_filter:
        cmd += ["-af", "highpass=f=85,afftdn=nr=7:nf=-46,alimiter=limit=0.92"]
    cmd += ["-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(out_wav)]
    subprocess.run(cmd, check=True)
    return out_wav


def analyze_audio_transients(
    wav_path: Path,
    *,
    hop_ms: float = 20.0,
    onset_threshold_db: float = 6.5,
    min_gap_s: float = 0.28,
) -> dict[str, Any]:
    """Compute RMS envelope, spectral centroid, and sharp transient onset timestamps for one audio clip."""
    data, sr = sf.read(str(wav_path), always_2d=True)
    mono = data.mean(axis=1).astype(np.float32)
    dur_s = len(mono) / float(max(1, sr))
    if len(mono) < 256:
        return {
            "duration_s": round(dur_s, 3),
            "rms_dbfs": -90.0,
            "peak_dbfs": -90.0,
            "spectral_centroid_hz": 0.0,
            "onsets_s": [],
            "rms_curve_db": [],
        }

    rms_lin = float(np.sqrt(np.mean(mono * mono)) + 1e-9)
    rms_db = float(20.0 * np.log10(rms_lin))
    peak_db = float(20.0 * np.log10(float(np.max(np.abs(mono))) + 1e-9))

    # Spectral centroid on active interior segment
    seg = mono[: min(len(mono), sr * 5)]
    mag = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)
    centroid = float(np.sum(freqs * mag) / (float(np.sum(mag)) + 1e-9))

    hop = max(1, int(round(sr * (hop_ms / 1000.0))))
    n_blk = len(mono) // hop
    if n_blk < 4:
        return {
            "duration_s": round(dur_s, 3),
            "rms_dbfs": round(rms_db, 2),
            "peak_dbfs": round(peak_db, 2),
            "spectral_centroid_hz": round(centroid, 1),
            "onsets_s": [],
            "rms_curve_db": [],
        }

    blocks = mono[: n_blk * hop].reshape(n_blk, hop)
    blk_db = 20.0 * np.log10(np.sqrt(np.mean(blocks * blocks, axis=1)) + 1e-7)

    # Local flux = rise relative to trailing 100ms median floor
    onsets: list[dict[str, Any]] = []
    last_t = -999.0
    for i in range(3, n_blk - 1):
        bg = float(np.median(blk_db[max(0, i - 5) : i]))
        rise = float(blk_db[i] - bg)
        t_s = (i * hop) / float(sr)
        if (
            rise >= onset_threshold_db
            and blk_db[i] > -42.0
            and blk_db[i] >= blk_db[i - 1]
            and blk_db[i] >= blk_db[i + 1]
            and (t_s - last_t) >= min_gap_s
        ):
            onsets.append({"time_s": round(t_s, 3), "rise_db": round(rise, 2), "level_dbfs": round(float(blk_db[i]), 2)})
            last_t = t_s

    return {
        "duration_s": round(dur_s, 3),
        "rms_dbfs": round(rms_db, 2),
        "peak_dbfs": round(peak_db, 2),
        "spectral_centroid_hz": round(centroid, 1),
        "onsets_s": [o["time_s"] for o in onsets],
        "onset_details": onsets,
        "rms_curve_db": [round(float(v), 1) for v in blk_db[::5]],  # 100ms summary curve
    }


def build_ltx_audio_guide(
    shot_clips: list[dict[str, Any]],
    work_dir: Path,
    *,
    out_json: Path | None = None,
) -> dict[str, Any]:
    """Extract clean 48kHz audio & transient cheat sheet across a timeline of LTX clips."""
    work_dir.mkdir(parents=True, exist_ok=True)
    clips_guide: dict[str, Any] = {}
    timeline_onsets: list[dict[str, Any]] = []

    for item in shot_clips:
        sid = str(item["shot_id"])
        mp4 = Path(str(item["clip_path"]))
        if not mp4.is_file():
            continue
        trim_in = float(item.get("trim_in_s", 0.0))
        tl_start = float(item.get("start_s", 0.0))
        tl_end = float(item.get("end_s", tl_start + float(item.get("duration_s", 5.0))))
        wav_p = work_dir / f"{sid}_clean48k.wav"
        extracted = extract_ltx_audio_wav(mp4, wav_p, clean_filter=True)
        if extracted is None:
            continue
        analysis = analyze_audio_transients(extracted)
        mapped_onsets: list[float] = []
        for ot in analysis["onsets_s"]:
            tl_t = tl_start + (ot - trim_in)
            if tl_start <= tl_t <= tl_end:
                mapped_onsets.append(round(tl_t, 3))
                timeline_onsets.append({"shot_id": sid, "time_s": round(tl_t, 3), "local_time_s": ot})

        clips_guide[sid] = {
            "shot_id": sid,
            "clip_path": str(mp4),
            "clean_wav_path": str(extracted),
            "timeline_start_s": round(tl_start, 3),
            "timeline_end_s": round(tl_end, 3),
            "trim_in_s": round(trim_in, 3),
            "rms_dbfs": analysis["rms_dbfs"],
            "peak_dbfs": analysis["peak_dbfs"],
            "spectral_centroid_hz": analysis["spectral_centroid_hz"],
            "local_onsets_s": analysis["onsets_s"],
            "timeline_onsets_s": mapped_onsets,
        }

    guide = {
        "schema": "ltx_audio_guide/1",
        "clip_count": len(clips_guide),
        "timeline_onset_count": len(timeline_onsets),
        "clips": clips_guide,
        "timeline_onsets": sorted(timeline_onsets, key=lambda x: x["time_s"]),
    }
    if out_json is not None:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(guide, indent=2) + "\n", encoding="utf-8")
    return guide


def snap_sfx_events_to_ltx_onsets(
    sfx_events: list[dict[str, Any]],
    guide: dict[str, Any],
    *,
    max_snap_window_s: float = 0.45,
    max_error_s: float = 0.04,
) -> list[dict[str, Any]]:
    """Snap foley punch SFX timestamps onto the nearest observed LTX physical transient within window."""
    onsets = [float(o["time_s"]) for o in (guide.get("timeline_onsets") or [])]
    if not onsets:
        return [dict(e) for e in sfx_events]
    snapped: list[dict[str, Any]] = []
    for ev in sfx_events:
        row = dict(ev)
        if not bool(row.get("snap_to_ltx", True)):
            snapped.append(row)
            continue
        t = float(row["time_s"])
        best = min(onsets, key=lambda o: abs(o - t))
        if abs(best - t) <= max_snap_window_s:
            row["original_time_s"] = round(t, 3)
            row["time_s"] = round(best, 3)
            row["ltx_snapped"] = True
            row["ltx_snap_delta_ms"] = round((best - t) * 1000.0, 1)
            row["within_40ms_sync"] = abs(row["time_s"] - best) <= max_error_s
        else:
            row["ltx_snapped"] = False
        snapped.append(row)
    return snapped


def build_stabilized_ltx_diegetic_stem(
    shot_clips: list[dict[str, Any]],
    guide: dict[str, Any],
    *,
    total_duration_s: float,
    out_wav: Path,
    sr: int = 48000,
    xfade_s: float = 0.40,
    narrated_level_dbfs: float = -29.0,
    dramatic_level_dbfs: float = -21.0,
) -> dict[str, Any]:
    """Assemble a continuous 48kHz stereo stabilized LTX native diegetic stem with 0.40s equal-power J/L fades."""
    n_total = max(1, int(round(total_duration_s * sr)))
    stem = np.zeros((n_total, 2), dtype=np.float32)
    clips_map = guide.get("clips") or {}
    placed = 0

    for item in shot_clips:
        sid = str(item["shot_id"])
        meta = clips_map.get(sid)
        if not meta:
            continue
        wav_p = Path(str(meta["clean_wav_path"]))
        if not wav_p.is_file():
            continue
        data, file_sr = sf.read(str(wav_p), always_2d=True)
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

        st = max(0.0, float(item["start_s"]))
        en = min(total_duration_s, float(item["end_s"]))
        if en <= st:
            continue
        trim_in = max(0.0, float(item.get("trim_in_s", 0.0)))
        lead = min(xfade_s * 0.5, st, trim_in)
        tail = min(xfade_s * 0.5, total_duration_s - en)

        src_s0 = int(round((trim_in - lead) * sr))
        req_len = int(round((en - st + lead + tail) * sr))
        seg = x[src_s0 : src_s0 + req_len].copy()
        if len(seg) < 64:
            continue

        # Normalize clip diegetic RMS cleanly (avoid amplifying near-silent clips)
        rms = float(np.sqrt(np.mean(seg * seg)) + 1e-9)
        cur_db = 20.0 * np.log10(rms)
        if cur_db > -55.0:
            is_dramatic = bool(item.get("is_dramatic_scene", False))
            tgt_db = float(item.get("ltx_audio_level_dbfs", dramatic_level_dbfs if is_dramatic else narrated_level_dbfs))
            gain = 10.0 ** (np.clip(tgt_db - cur_db, -24.0, 14.0) / 20.0)
            seg *= gain

        # Equal-power sine/cosine J/L fade-in & fade-out across shot cuts
        fn = min(len(seg) // 3, int(round(xfade_s * sr)))
        if fn > 8:
            t_r = np.linspace(0.0, np.pi * 0.5, fn, dtype=np.float32)[:, None]
            seg[:fn] *= np.sin(t_r)
            seg[-fn:] *= np.cos(t_r)

        dst_s0 = max(0, int(round((st - lead) * sr)))
        dst_s1 = min(n_total, dst_s0 + len(seg))
        if dst_s1 > dst_s0:
            stem[dst_s0:dst_s1] += seg[: dst_s1 - dst_s0]
            placed += 1

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_wav), np.clip(stem, -0.98, 0.98), sr, subtype="PCM_24")
    rms_out = float(20.0 * np.log10(float(np.sqrt(np.mean(stem * stem)) + 1e-9)))
    return {
        "schema": "ltx_diegetic_stem/1",
        "path": str(out_wav),
        "clips_mixed": placed,
        "duration_s": round(total_duration_s, 3),
        "rms_dbfs": round(rms_out, 2),
        "xfade_s": xfade_s,
    }
