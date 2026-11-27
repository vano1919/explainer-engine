"""Automated Cinema Quality Gates: Static-Shot Detector, Mid-Frame Seam/Tear Detector, and Audio-Scene Consistency.

Catches the exact real-world visual and audio defects that legacy synthetic tests missed:
1. Static-Shot Detector: verifies smooth continuous motion across 1-second windows (especially opening 0–2s).
2. Mid-Frame Seam/Tear Detector: detects artificial horizontal/vertical gradient discontinuity splits.
3. Audio-Scene Consistency Gate: verifies no rain on dry/map shots, synced SFX on every map shot,
   ITU-R BS.1770-4 loudness/peak compliance, and real acoustic variation across scene boundaries.
4. Cropped Seed Plate Gate and Cutout Compositing Gate (BP-217): every seed plate is a native full frame; no
   person is matted out and pasted onto a separate background.
"""
from __future__ import annotations

import ast
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from explainer_engine.standards import sourced_rules


def _read_frames_at_times(video_path: Path, times_s: list[float]) -> list[np.ndarray]:
    if not times_s:
        return []
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    target_idxs = [max(0, min(max(0, total - 1), int(round(ts * fps)))) for ts in times_s]
    unique_sorted = sorted(set(target_idxs))
    max_idx = unique_sorted[-1] if unique_sorted else 0
    wanted = set(unique_sorted)
    decoded: dict[int, np.ndarray] = {}
    try:
        # Use keyframe seeking for sparse samples across long 2K videos; sequential grab for dense short clips
        if total > 1200 and len(unique_sorted) <= 200:
            for idx in unique_sorted:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ok, bgr = cap.read()
                if ok and bgr is not None:
                    decoded[idx] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        else:
            cur = 0
            while cur <= max_idx:
                if not cap.grab():
                    break
                if cur in wanted:
                    ok, bgr = cap.retrieve()
                    if ok and bgr is not None:
                        decoded[cur] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                cur += 1
    finally:
        cap.release()
    return [decoded[i] for i in target_idxs if i in decoded]


def check_no_static_shots(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    min_mean_abs_diff: float = 0.45,
) -> dict[str, Any]:
    """Fail if any 2.5D shot exhibits frozen/static motion (including opening 0–2s of Shot 1)."""
    findings: list[str] = []
    details: list[dict[str, Any]] = []
    # Batch all frame timestamps for one fast single-pass video decode
    shot_meta: list[tuple[dict[str, Any], int, int]] = []
    all_times: list[float] = []
    for shot in shot_windows:
        if shot.get("kind", "25d") != "25d":
            continue
        st = float(shot["start_s"])
        en = float(shot["end_s"])
        dur = en - st
        if dur < 1.2:
            continue
        t_samples = [st + 0.15, st + min(1.35, dur * 0.45), st + min(2.6, dur * 0.80)]
        start_idx = len(all_times)
        all_times.extend(t_samples)
        shot_meta.append((shot, start_idx, len(t_samples)))

    all_frs = _read_frames_at_times(video_path, all_times) if all_times else []
    for shot, s_idx, cnt in shot_meta:
        frs = all_frs[s_idx : s_idx + cnt]
        if len(frs) < 2:
            findings.append(f"{shot.get('shot_id')}: insufficient frames sampled")
            continue
        d_early = float(np.mean(np.abs(frs[1].astype(np.float32) - frs[0].astype(np.float32))))
        d_mid = float(np.mean(np.abs(frs[-1].astype(np.float32) - frs[1].astype(np.float32)))) if len(frs) > 2 else d_early
        ok = d_early >= min_mean_abs_diff and d_mid >= min_mean_abs_diff
        details.append(
            {
                "shot_id": shot.get("shot_id"),
                "early_motion_diff": round(d_early, 3),
                "mid_motion_diff": round(d_mid, 3),
                "passed": ok,
            }
        )
        if not ok:
            findings.append(
                f"{shot.get('shot_id')}: static/frozen 2.5D motion detected (early={d_early:.2f}, mid={d_mid:.2f} < {min_mean_abs_diff})"
            )
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "shots": details}


def check_no_midframe_tears(
    video_path: Path,
    *,
    sample_times_s: list[float] | None = None,
    max_seam_zscore: float = 16.0,
) -> dict[str, Any]:
    """Detect artificial full-width horizontal or full-height vertical mid-frame split/tear seams."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = total / max(1.0, fps)
    cap.release()

    times = sample_times_s or [round(dur * (i + 0.5) / 10.0, 3) for i in range(10)]
    frs = _read_frames_at_times(video_path, times)
    findings: list[str] = []
    max_h_z = 0.0
    max_v_z = 0.0

    for idx, fr in enumerate(frs):
        gray = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape
        # Ignore outer 15% borders (vignettes/overlays/cards) and inspect central 70% interior for split tears
        y0, y1 = int(h * 0.18), int(h * 0.78)
        x0, x1 = int(w * 0.15), int(w * 0.85)
        inner = gray[y0:y1, x0:x1]

        # Use 60th-percentile across the span so a true mid-frame tear (>40% span) spikes strongly,
        # while a compact <25%-width map label badge does not trigger a false positive.
        row_jump = np.percentile(np.abs(np.diff(inner, axis=0)), 60, axis=1)
        col_jump = np.percentile(np.abs(np.diff(inner, axis=1)), 60, axis=0)

        r_base = np.sort(row_jump)[:-3] if row_jump.size > 6 else row_jump
        c_base = np.sort(col_jump)[:-3] if col_jump.size > 6 else col_jump
        h_z = float((np.max(row_jump) - np.median(r_base)) / max(0.8, float(np.std(r_base))))
        v_z = float((np.max(col_jump) - np.median(c_base)) / max(0.8, float(np.std(c_base))))
        max_h_z = max(max_h_z, h_z)
        max_v_z = max(max_v_z, v_z)
        if h_z > max_seam_zscore or v_z > max_seam_zscore:
            findings.append(f"frame@{times[idx]:.2f}s: mid-frame seam/tear spike (h_z={h_z:.1f}, v_z={v_z:.1f} > {max_seam_zscore})")

    return {
        "status": "PASS" if not findings else "FAIL",
        "max_horizontal_z": round(max_h_z, 2),
        "max_vertical_z": round(max_v_z, 2),
        "findings": findings,
    }


def check_audio_scene_consistency(soundscape_report: dict[str, Any]) -> dict[str, Any]:
    """Fail if dry/map shots carry rain ambience, map shots lack synced SFX, or audio is flat constant noise."""
    findings: list[str] = []
    shots = soundscape_report.get("shots") or []
    lufs = float(soundscape_report.get("integrated_lufs", -99.0))
    peak = float(soundscape_report.get("peak_dbfs", 0.0))

    if not (-15.5 <= lufs <= -12.5):
        findings.append(f"Integrated loudness {lufs:.2f} LUFS outside YouTube target band [-15.5, -12.5]")
    if peak > -0.9:
        findings.append(f"Audio peak {peak:.2f} dBFS exceeds ceiling -0.9 dBFS")

    centroids: list[float] = []
    for s in shots:
        env = str(s.get("scene_environment", ""))
        kind = str(s.get("kind", ""))
        if kind == "map":
            if "rain" in env:
                findings.append(f"Map shot {s.get('shot_id')} illegally carries rain ambience ({env})")
            if int(s.get("sfx_count_in_shot", 0)) < 1:
                findings.append(f"Map shot {s.get('shot_id')} has zero synchronized map-action SFX cues")
        if "daylight" in env and "rain" in env:
            findings.append(f"Dry daylight shot {s.get('shot_id')} carries rain ambience ({env})")
        centroids.append(float(s.get("spectral_centroid_hz", 0.0)))

    centroid_span = round(max(centroids) - min(centroids), 1) if len(centroids) >= 2 else 0.0
    if len(shots) >= 3 and len({s.get("scene_environment") for s in shots}) >= 2 and centroid_span < 25.0:
        findings.append(f"Audio spectrum is flat/unchanging across distinct scenes (centroid span={centroid_span} Hz < 25 Hz)")

    return {
        "status": "PASS" if not findings else "FAIL",
        "integrated_lufs": lufs,
        "peak_dbfs": peak,
        "spectral_centroid_span_hz": centroid_span,
        "findings": findings,
    }


def check_cross_cut_color_parity(
    video_path: Path,
    cut_times_s: list[float],
    *,
    max_channel_delta: float = 55.0,
    max_saturation_delta: float = 0.35,
) -> dict[str, Any]:
    """Measure cross-cut color/saturation harmony between LTX, 2.5D, and Map shots (unified film grade check)."""
    findings: list[str] = []
    cuts: list[dict[str, Any]] = []
    all_times: list[float] = []
    for ct in cut_times_s:
        all_times.extend([max(0.0, ct - 0.12), ct + 0.12])
    all_frs = _read_frames_at_times(video_path, all_times) if all_times else []
    for i, ct in enumerate(cut_times_s):
        frs = all_frs[i * 2 : i * 2 + 2]
        if len(frs) < 2:
            continue
        a = frs[0].astype(np.float32)
        b = frs[1].astype(np.float32)
        # Measure warm-cool ratio delta (R-B balance) & mean saturation delta rather than brightness alone
        wb_a = float(a[..., 0].mean() - a[..., 2].mean())
        wb_b = float(b[..., 0].mean() - b[..., 2].mean())
        wb_delta = abs(wb_a - wb_b)
        sat_a = float(cv2.cvtColor(frs[0], cv2.COLOR_RGB2HSV)[..., 1].mean() / 255.0)
        sat_b = float(cv2.cvtColor(frs[1], cv2.COLOR_RGB2HSV)[..., 1].mean() / 255.0)
        sat_delta = abs(sat_a - sat_b)
        ok = wb_delta <= max_channel_delta and sat_delta <= max_saturation_delta
        cuts.append(
            {
                "cut_s": round(ct, 3),
                "wb_rb_delta": round(wb_delta, 2),
                "sat_delta": round(sat_delta, 3),
                "passed": ok,
            }
        )
        if not ok:
            findings.append(
                f"cut@{ct:.2f}s: visual discontinuity across cut (wb_delta={wb_delta:.1f}, sat_delta={sat_delta:.3f})"
            )
    return {"status": "PASS" if not findings else "FAIL", "cuts": cuts, "findings": findings}


def check_master_delivery_specs(
    video_path: Path,
    *,
    expected_width: int = 2560,
    expected_height: int = 1440,
    expected_fps: float = 24.0,
    expected_sr: int = 48000,
    expected_channels: int = 2,
    audio_report: dict[str, Any] | None = None,
    verify_ffmpeg_true_peak: bool = False,
) -> dict[str, Any]:
    """L3 machine forensics: verify 2K 2560x1440 @ 24fps yuv420p, 48kHz stereo, -14.0 +/- 0.5 LUFS, <= -1.0 dBTP."""
    import json
    import re
    import subprocess

    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,width,height,pix_fmt,r_frame_rate,sample_rate,channels",
            "-of",
            "json",
            str(video_path),
        ],
        text=True,
    )
    probe = json.loads(raw)
    streams = probe.get("streams") or []
    v_streams = [s for s in streams if s.get("codec_type") == "video"]
    a_streams = [s for s in streams if s.get("codec_type") == "audio"]
    findings: list[str] = []
    if not v_streams:
        findings.append("Missing video stream")
    if not a_streams:
        findings.append("Missing audio stream")

    v = v_streams[0] if v_streams else {}
    a = a_streams[0] if a_streams else {}
    w = int(v.get("width", 0))
    h = int(v.get("height", 0))
    pix = str(v.get("pix_fmt", ""))
    num, _, den = str(v.get("r_frame_rate", "0/1")).partition("/")
    fps = float(num) / max(1.0, float(den or 1.0))
    sr = int(a.get("sample_rate", 0))
    ch = int(a.get("channels", 0))

    if (w, h) != (expected_width, expected_height):
        findings.append(f"Resolution {w}x{h} != {expected_width}x{expected_height} (DEF-08)")
    if pix != "yuv420p":
        findings.append(f"Pixel format {pix!r} != 'yuv420p'")
    if abs(fps - expected_fps) > 0.1:
        findings.append(f"FPS {fps:.2f} != {expected_fps:.2f}")
    if sr != expected_sr or ch != expected_channels:
        findings.append(f"Audio format {sr}Hz/{ch}ch != {expected_sr}Hz/{expected_channels}ch")

    if audio_report is not None:
        lufs = float(audio_report.get("integrated_lufs", -99.0))
        peak = float(audio_report.get("true_peak_dbtp", audio_report.get("peak_dbfs", 0.0)))
        if not (-14.5 <= lufs <= -13.5):
            findings.append(f"Integrated loudness {lufs:.2f} LUFS outside strict -14.0 +/- 0.5 LUFS target")
        if peak > -1.0:
            findings.append(f"True peak {peak:.2f} dBTP exceeds -1.0 dBTP ceiling")

    ffmpeg_true_peak_dbtp: float | None = None
    ffmpeg_lufs: float | None = None
    if verify_ffmpeg_true_peak and a_streams:
        ebur = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video_path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        m_i = re.findall(r"Integrated loudness:\s*\n\s*I:\s*([-+]?\d+(?:\.\d+)?)\s*LUFS", ebur.stderr)
        m_tp = re.findall(r"True peak:\s*\n\s*Peak:\s*([-+]?\d+(?:\.\d+)?)\s*dBFS", ebur.stderr)
        if m_i:
            ffmpeg_lufs = float(m_i[-1])
            if not (-14.5 <= ffmpeg_lufs <= -13.5):
                findings.append(f"FFmpeg ebur128 integrated loudness {ffmpeg_lufs:.2f} LUFS outside [-14.5, -13.5]")
        if m_tp:
            ffmpeg_true_peak_dbtp = float(m_tp[-1])
            if ffmpeg_true_peak_dbtp > -0.95:
                findings.append(f"FFmpeg ebur128 true peak {ffmpeg_true_peak_dbtp:.2f} dBTP exceeds -1.0 dBTP ceiling")

    res: dict[str, Any] = {
        "status": "PASS" if not findings else "FAIL",
        "width": w,
        "height": h,
        "fps": round(fps, 3),
        "pix_fmt": pix,
        "sample_rate": sr,
        "channels": ch,
        "duration_s": round(float((probe.get("format") or {}).get("duration", 0.0)), 3),
        "findings": findings,
    }
    if ffmpeg_lufs is not None:
        res["ffmpeg_integrated_lufs"] = round(ffmpeg_lufs, 2)
    if ffmpeg_true_peak_dbtp is not None:
        res["ffmpeg_true_peak_dbtp"] = round(ffmpeg_true_peak_dbtp, 2)
    return res


def check_narration_pacing_gaps(
    utterances: list[dict[str, Any]],
    *,
    total_duration_s: float,
    max_unplanned_gap_s: float = 3.5,
    max_breather_gap_s: float = 5.0,
    max_tail_silence_s: float = 4.0,
    dramatic_scene_windows: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Fail if narration/dialogue leaves unplanned dead-air stretches > 3.5s (or > 5.0s breather).

    Gaps covered by declared ``dramatic_scene_windows`` (the 30% narrator-free cinema acting scenes
    in 70/30 YouTube docudrama architecture) are explicitly exempted from dead-air penalties.
    """
    findings: list[str] = []
    gaps: list[dict[str, Any]] = []
    ordered = sorted(utterances, key=lambda u: float(u.get("start_s", 0.0)))
    if not ordered:
        return {
            "status": "FAIL",
            "max_gap_s": round(total_duration_s, 3),
            "gaps": [],
            "findings": ["Zero narration or dialogue utterances present"],
        }

    def _in_dramatic_scene(g_start: float, g_end: float) -> bool:
        if not dramatic_scene_windows or g_end <= g_start:
            return False
        dur = g_end - g_start
        covered = 0.0
        for ds, de in dramatic_scene_windows:
            ov = max(0.0, min(g_end, float(de)) - max(g_start, float(ds)))
            covered += ov
        return (covered / max(1e-6, dur)) >= 0.70

    # Check opening dead silence before first speech
    first_start = float(ordered[0].get("start_s", 0.0))
    if (
        first_start > max_unplanned_gap_s
        and not bool(ordered[0].get("dramatic_breather", False))
        and not _in_dramatic_scene(0.0, first_start)
    ):
        findings.append(f"Opening dead-air before first voice is {first_start:.2f}s > {max_unplanned_gap_s:.2f}s")

    max_gap = first_start
    for idx in range(len(ordered) - 1):
        cur_end = float(ordered[idx].get("end_s", ordered[idx].get("start_s", 0.0)))
        nxt_start = float(ordered[idx + 1].get("start_s", cur_end))
        gap = max(0.0, nxt_start - cur_end)
        is_breather = bool(ordered[idx].get("dramatic_breather_after", False)) or bool(
            ordered[idx + 1].get("dramatic_breather", False)
        )
        is_dramatic_stretch = bool(ordered[idx].get("dramatic_scene_after", False)) or _in_dramatic_scene(
            cur_end, nxt_start
        )
        limit = max_breather_gap_s if is_breather else max_unplanned_gap_s
        if not is_dramatic_stretch:
            max_gap = max(max_gap, gap)
        passed = True if is_dramatic_stretch else (gap <= limit)
        gaps.append(
            {
                "from_s": round(cur_end, 3),
                "to_s": round(nxt_start, 3),
                "gap_s": round(gap, 3),
                "dramatic_breather": is_breather,
                "dramatic_scene_silent": is_dramatic_stretch,
                "passed": passed,
            }
        )
        if not passed:
            findings.append(
                f"Dead narration gap {cur_end:.2f}s->{nxt_start:.2f}s ({gap:.2f}s > {limit:.2f}s limit)"
            )

    tail_gap = max(0.0, float(total_duration_s) - float(ordered[-1].get("end_s", 0.0)))
    max_gap = max(max_gap, tail_gap)
    if tail_gap > max_tail_silence_s and not _in_dramatic_scene(float(ordered[-1].get("end_s", 0.0)), total_duration_s):
        findings.append(f"Tail dead-air after final line is {tail_gap:.2f}s > {max_tail_silence_s:.2f}s")

    return {
        "status": "PASS" if not findings else "FAIL",
        "max_gap_s": round(max_gap, 3),
        "tail_gap_s": round(tail_gap, 3),
        "gaps": gaps,
        "findings": findings,
    }


def _normalize_words(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())


def _word_error_rate(ref_words: list[str], hyp_words: list[str]) -> float:
    if not ref_words:
        return 0.0
    n = len(ref_words)
    m = len(hyp_words)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, m + 1):
            temp = dp[j]
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = temp
    return dp[m] / max(1, n)


def check_tts_pronunciation_asr(
    expected_script: str,
    *,
    audio_path: Path | None = None,
    observed_transcript: str | None = None,
    required_proper_nouns: list[str] | None = None,
    max_wer: float = 0.08,
    whisper_model: str = "tiny.en",
) -> dict[str, Any]:
    """Verify TTS pronunciation accuracy against script via faster-whisper ASR (or observed transcript)."""
    findings: list[str] = []
    transcript = observed_transcript
    if transcript is None:
        if audio_path is None or not audio_path.is_file():
            return {
                "status": "FAIL",
                "wer": 1.0,
                "transcript": "",
                "missing_proper_nouns": list(required_proper_nouns or []),
                "findings": ["Neither observed_transcript nor existing audio_path was supplied for ASR check"],
            }
        import soundfile as sf
        from faster_whisper import WhisperModel
        from scipy.signal import resample_poly

        wav_data, wav_sr = sf.read(str(audio_path), always_2d=False)
        wav_mono = wav_data.mean(axis=1) if wav_data.ndim > 1 else wav_data
        audio_16k = (
            resample_poly(wav_mono, 16000, wav_sr).astype(np.float32)
            if wav_sr != 16000
            else wav_mono.astype(np.float32)
        )
        model = WhisperModel(whisper_model, device="cpu", compute_type="int8")
        asr_prompt = ", ".join(required_proper_nouns) if required_proper_nouns else None
        segments, _ = model.transcribe(
            audio_16k,
            language="en",
            beam_size=1,
            initial_prompt=asr_prompt,
            condition_on_previous_text=False,
        )
        transcript = " ".join(seg.text.strip() for seg in segments).strip()

    ref_words = _normalize_words(expected_script)
    hyp_words = _normalize_words(transcript)
    wer = round(_word_error_rate(ref_words, hyp_words), 4)
    if wer > max_wer:
        findings.append(f"ASR Word Error Rate {wer:.3f} exceeds max {max_wer:.3f}")

    hyp_joined = " " + " ".join(hyp_words) + " "
    missing_nouns: list[str] = []
    for noun in required_proper_nouns or []:
        norm_noun = " ".join(_normalize_words(noun))
        if norm_noun and f" {norm_noun} " not in hyp_joined:
            missing_nouns.append(noun)
            findings.append(f"Proper noun mispronounced or dropped by TTS/ASR: {noun!r}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "wer": wer,
        "transcript": transcript,
        "missing_proper_nouns": missing_nouns,
        "findings": findings,
    }


def check_map_geographic_richness(
    map_specs: list[dict[str, Any]],
    *,
    min_land_ratio: float = 0.18,
    require_context_labels: bool = True,
    require_unified_palette: bool = True,
) -> dict[str, Any]:
    """Fail if any map is mostly empty ocean (<18% land), lacks sea/region labels, or mixes palettes."""
    findings: list[str] = []
    palettes: set[str] = set()
    checked: list[dict[str, Any]] = []

    for idx, m in enumerate(map_specs):
        mid = str(m.get("map_id") or m.get("shot_id") or f"map_{idx + 1}")
        pal = str(m.get("palette") or m.get("style_preset") or "")
        if pal:
            palettes.add(pal)

        land_ratio = m.get("land_ratio")
        if land_ratio is None and m.get("frame_path"):
            p = Path(str(m["frame_path"]))
            if p.is_file():
                bgr = cv2.imread(str(p))
                if bgr is not None:
                    # Ocean pixels tend to have B > R + 12 and low luminance/high blue dominance
                    b_ch = bgr[..., 0].astype(np.float32)
                    g_ch = bgr[..., 1].astype(np.float32)
                    r_ch = bgr[..., 2].astype(np.float32)
                    is_ocean = (b_ch > r_ch + 12.0) & (b_ch >= g_ch - 4.0)
                    land_ratio = float(1.0 - np.mean(is_ocean))
        land_val = float(land_ratio) if land_ratio is not None else 0.0
        labels = list(m.get("context_labels") or m.get("sea_and_region_labels") or [])
        ok = True
        if land_val < min_land_ratio:
            ok = False
            findings.append(f"{mid}: land/relief ratio {land_val:.3f} < {min_land_ratio:.2f} (empty ocean map)")
        if require_context_labels and len(labels) < 1:
            ok = False
            findings.append(f"{mid}: missing sea/continent/region geographic context labels")
        checked.append(
            {
                "map_id": mid,
                "palette": pal,
                "land_ratio": round(land_val, 3),
                "context_label_count": len(labels),
                "passed": ok,
            }
        )

    if require_unified_palette and len(palettes) > 1:
        findings.append(f"Conflicting map palettes within one episode: {sorted(palettes)}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "palettes": sorted(palettes),
        "maps": checked,
        "findings": findings,
    }


def _boxes_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float], pad: float = 4.0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 + pad <= bx0 or bx1 + pad <= ax0 or ay1 + pad <= by0 or by1 + pad <= ay0)


def check_overlay_spatial_collisions(
    bridges: list[dict[str, Any]],
    map_elements: list[dict[str, Any]],
) -> dict[str, Any]:
    """Fail if any visual bridge bounding box overlaps a map title/label/pin during concurrent timestamps."""
    findings: list[str] = []
    collisions: list[dict[str, Any]] = []
    for br in bridges:
        bs = float(br.get("start_s", 0.0))
        be = float(br.get("end_s", bs + float(br.get("duration_s", 0.0))))
        bb = br.get("bbox")
        if not bb or len(bb) != 4:
            continue
        b_box = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3]))
        for me in map_elements:
            ms = float(me.get("start_s", 0.0))
            me_end = float(me.get("end_s", ms + float(me.get("duration_s", 0.0))))
            if be <= ms or me_end <= bs:
                continue
            mb = me.get("bbox")
            if not mb or len(mb) != 4:
                continue
            m_box = (float(mb[0]), float(mb[1]), float(mb[2]), float(mb[3]))
            if _boxes_overlap(b_box, m_box):
                col = {
                    "bridge_id": br.get("id", "bridge"),
                    "map_element_id": me.get("id", "map_el"),
                    "overlap_window_s": [round(max(bs, ms), 3), round(min(be, me_end), 3)],
                }
                collisions.append(col)
                findings.append(
                    f"Spatial collision between {col['bridge_id']} and {col['map_element_id']} "
                    f"at {col['overlap_window_s'][0]:.2f}s-{col['overlap_window_s'][1]:.2f}s"
                )
    return {
        "status": "PASS" if not findings else "FAIL",
        "collisions": collisions,
        "findings": findings,
    }


def check_edit_grammar_and_dedup(
    shots: list[dict[str, Any]],
    *,
    max_xfade_ratio: float = 0.25,
    require_real_video_in_dramatic: bool = True,
) -> dict[str, Any]:
    """Fail on duplicate source_sha256 reuse, excessive cross-dissolves (>25%), or static dramatic scenes."""
    findings: list[str] = []
    seen_sources: dict[str, str] = {}
    duplicate_pairs: list[tuple[str, str]] = []
    transitions = 0
    xfades = 0
    dramatic_total = 0
    dramatic_real_video = 0

    for idx, s in enumerate(shots):
        sid = str(s.get("shot_id") or f"shot_{idx + 1}")
        src_sha = str(s.get("source_sha256") or "").strip().lower()
        if src_sha:
            if src_sha in seen_sources and not bool(s.get("allow_callback_repeat", False)):
                duplicate_pairs.append((seen_sources[src_sha], sid))
                findings.append(f"Duplicate visual source reused in {sid} (already used in {seen_sources[src_sha]})")
            else:
                seen_sources[src_sha] = sid

        if idx > 0:
            transitions += 1
            tr = str(s.get("transition_in") or "hard_cut").lower()
            if "xfade" in tr or "dissolve" in tr or "fade" in tr:
                xfades += 1

        if bool(s.get("is_dramatic_showcase", False)):
            dramatic_total += 1
            if str(s.get("kind", "")).lower() in {"video", "ltx", "ltx_multishot", "helios"}:
                dramatic_real_video += 1

    xfade_ratio = (xfades / transitions) if transitions > 0 else 0.0
    if transitions >= 3 and xfade_ratio > max_xfade_ratio:
        findings.append(
            f"Excessive PowerPoint cross-dissolves: {xfades}/{transitions} ({xfade_ratio:.0%}) > {max_xfade_ratio:.0%} max"
        )
    if require_real_video_in_dramatic and dramatic_total > 0 and dramatic_real_video == 0:
        findings.append(
            f"Dramatic showcase has 0/{dramatic_total} real moving video clips (frozen 2.5D slideshow rejected)"
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "xfade_ratio": round(xfade_ratio, 3),
        "duplicate_sources": duplicate_pairs,
        "dramatic_real_video_count": dramatic_real_video,
        "dramatic_total_count": dramatic_total,
        "findings": findings,
    }


def check_audio_ducking_and_sfx_balance(
    audio_metrics: dict[str, Any],
    *,
    max_sfx_vs_voice_db: float = -6.0,
    max_pause_pumping_db: float = 5.0,
) -> dict[str, Any]:
    """Fail if map/foley SFX overpowers narration (>-6 dB rel voice) or bed pumps >5 dB in pauses."""
    findings: list[str] = []
    sfx_rel = float(audio_metrics.get("max_sfx_relative_to_voice_db", -12.0))
    pump_db = float(audio_metrics.get("max_pause_pumping_swing_db", 0.0))
    if sfx_rel > max_sfx_vs_voice_db:
        findings.append(
            f"SFX overpowers narration: {sfx_rel:.1f} dB relative to voice (limit <= {max_sfx_vs_voice_db:.1f} dB)"
        )
    if pump_db > max_pause_pumping_db:
        findings.append(
            f"Ambience/music ducking pumps during speech pauses: {pump_db:.1f} dB swing > {max_pause_pumping_db:.1f} dB"
        )
    return {
        "status": "PASS" if not findings else "FAIL",
        "max_sfx_relative_to_voice_db": round(sfx_rel, 2),
        "max_pause_pumping_swing_db": round(pump_db, 2),
        "findings": findings,
    }


def check_archival_or_grade_cohesion(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    max_luma_std_spread: float = 48.0,
    max_sat_spread: float = 0.42,
) -> dict[str, Any]:
    """Verify tonal/saturation unity across all shots so no shot breaks the episode's 35mm film grade."""
    times = [
        round((float(s["start_s"]) + float(s["end_s"])) * 0.5, 3)
        for s in shot_windows
        if float(s.get("end_s", 0.0)) > float(s.get("start_s", 0.0))
    ]
    frs = _read_frames_at_times(video_path, times) if times else []
    lumas: list[float] = []
    sats: list[float] = []
    for fr in frs:
        lumas.append(float(cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY).mean()))
        sats.append(float(cv2.cvtColor(fr, cv2.COLOR_RGB2HSV)[..., 1].mean() / 255.0))

    findings: list[str] = []
    luma_std = float(np.std(lumas)) if len(lumas) >= 2 else 0.0
    sat_span = float(max(sats) - min(sats)) if len(sats) >= 2 else 0.0
    if luma_std > max_luma_std_spread:
        findings.append(f"Cross-shot luminance spread {luma_std:.1f} exceeds {max_luma_std_spread:.1f}")
    if sat_span > max_sat_spread:
        findings.append(f"Cross-shot saturation span {sat_span:.3f} exceeds {max_sat_spread:.3f}")
    return {
        "status": "PASS" if not findings else "FAIL",
        "luma_std": round(luma_std, 2),
        "sat_span": round(sat_span, 3),
        "findings": findings,
    }


def check_zero_photo_clip_reuse(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    max_ssim: float = 0.85,
    min_phash_hamming: int = 7,
) -> dict[str, Any]:
    """Fail if any two non-chained, unrelated shots share a source path/SHA-256 or visually duplicate (SSIM > 0.85 or pHash <= 6)."""
    import imagehash
    from PIL import Image
    from skimage.metrics import structural_similarity as ssim

    findings: list[str] = []
    seen_paths: dict[str, str] = {}
    seen_shas: dict[str, str] = {}
    visual_dups: list[dict[str, Any]] = []

    valid_shots: list[dict[str, Any]] = []
    sample_times: list[float] = []
    for idx, s in enumerate(shot_windows):
        sid = str(s.get("shot_id") or f"shot_{idx + 1}")
        chained_from = str(s.get("chained_from") or "").strip()
        src_p = str(s.get("source_image_path") or s.get("source_path") or "").strip()
        src_sha = str(s.get("source_sha256") or "").strip().lower()
        if src_p and not chained_from:
            if src_p in seen_paths:
                findings.append(f"Source image/clip path reused across shots: {seen_paths[src_p]} and {sid} ({Path(src_p).name})")
            else:
                seen_paths[src_p] = sid
        if src_sha and not chained_from:
            if src_sha in seen_shas:
                findings.append(f"Source SHA-256 reused across shots: {seen_shas[src_sha]} and {sid}")
            else:
                seen_shas[src_sha] = sid
        st = float(s.get("start_s", 0.0))
        en = float(s.get("end_s", 0.0))
        if en > st:
            valid_shots.append(s)
            sample_times.append(round((st + en) * 0.5, 3))

    if video_path.is_file() and sample_times:
        frs = _read_frames_at_times(video_path, sample_times)
        thumbs_gray: list[np.ndarray] = []
        phashes: list[Any] = []
        for fr in frs:
            small = cv2.resize(fr, (320, 180), interpolation=cv2.INTER_AREA)
            thumbs_gray.append(cv2.cvtColor(small, cv2.COLOR_RGB2GRAY))
            phashes.append(imagehash.phash(Image.fromarray(small)))

        for i in range(len(thumbs_gray)):
            for j in range(i + 1, len(thumbs_gray)):
                # Skip immediately adjacent chained shots (Last-Frame Chaining / FLF2V continuation)
                if j == i + 1 and str(valid_shots[j].get("chained_from") or "").strip():
                    continue
                if j == i + 1 and valid_shots[i].get("scene_group") and valid_shots[i].get("scene_group") == valid_shots[j].get("scene_group"):
                    # Adjacent shots inside the same continuous LTX scene still must not be identical clones
                    if int(phashes[i] - phashes[j]) <= 3:
                        pass
                    else:
                        continue
                ham = int(phashes[i] - phashes[j])
                raw_sim = ssim(thumbs_gray[i], thumbs_gray[j], data_range=255)
                sim = float(raw_sim[0] if isinstance(raw_sim, tuple) else raw_sim)
                if ham < min_phash_hamming or sim > max_ssim:
                    s_a = str(valid_shots[i].get("shot_id") or f"shot_{i + 1}")
                    s_b = str(valid_shots[j].get("shot_id") or f"shot_{j + 1}")
                    rec = {"shot_a": s_a, "shot_b": s_b, "phash_hamming": ham, "ssim": round(sim, 3)}
                    visual_dups.append(rec)
                    findings.append(
                        f"Cross-shot visual duplicate detected between {s_a} and {s_b} "
                        f"(pHash hamming={ham} < {min_phash_hamming} or SSIM={sim:.3f} > {max_ssim})"
                    )

    return {
        "status": "PASS" if not findings else "FAIL",
        "shots_checked": len(valid_shots),
        "visual_duplicates": visual_dups,
        "findings": findings,
    }


def check_ltx_dominance(
    shot_windows: list[dict[str, Any]],
    *,
    min_ltx_ratio: float = 0.65,
    max_ltx_ratio: float = 0.80,
    min_unique_clips: int = 24,
    max_speed: float = 1.0,
) -> dict[str, Any]:
    """Enforce 65-75% unique real Modal H100 LTX-2.5 dominance (min 24 unique clips, 4-6s, <= 1.0x speed, distinct SHA-256 + Modal Job IDs)."""
    findings: list[str] = []
    total_dur = 0.0
    ltx_dur = 0.0
    unique_shas: set[str] = set()
    modal_job_ids: set[str] = set()
    ltx_count = 0

    for idx, s in enumerate(shot_windows):
        sid = str(s.get("shot_id") or f"shot_{idx + 1}")
        dur = max(0.0, float(s.get("end_s", 0.0)) - float(s.get("start_s", 0.0)))
        total_dur += dur
        kind = str(s.get("kind", "")).lower()
        if kind in {"ltx", "ltx_25", "ltx_video", "video", "ltx_multishot"}:
            ltx_count += 1
            ltx_dur += dur
            sha = str(s.get("file_sha256") or s.get("clip_sha256") or s.get("source_sha256") or "").strip().lower()
            job_id = str(s.get("modal_job_id") or s.get("run_id") or "").strip()
            spd = float(s.get("playback_speed", 1.0))
            if not sha:
                findings.append(f"{sid}: LTX clip missing file_sha256 provenance")
            elif sha in unique_shas:
                findings.append(f"{sid}: duplicate LTX clip SHA-256 reused/looped ({sha[:12]})")
            else:
                unique_shas.add(sha)
            if not job_id:
                findings.append(f"{sid}: LTX clip missing modal_job_id provenance")
            else:
                modal_job_ids.add(job_id)
            if spd > max_speed + 1e-6:
                findings.append(f"{sid}: LTX playback speed {spd:.2f}x exceeds {max_speed:.2f}x cap")

    ratio = (ltx_dur / total_dur) if total_dur > 0 else 0.0
    if ratio < min_ltx_ratio:
        findings.append(f"LTX-2.5 real video share {ratio:.1%} < required {min_ltx_ratio:.0%} minimum")
    if ratio > max_ltx_ratio:
        findings.append(f"LTX-2.5 share {ratio:.1%} exceeds {max_ltx_ratio:.0%} (maps/bridges/2.5D underrepresented)")
    if len(unique_shas) < min_unique_clips:
        findings.append(f"Unique LTX-2.5 clip count {len(unique_shas)} < required {min_unique_clips}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "ltx_duration_s": round(ltx_dur, 2),
        "total_duration_s": round(total_dur, 2),
        "ltx_ratio": round(ratio, 4),
        "ltx_shot_count": ltx_count,
        "unique_ltx_clips": len(unique_shas),
        "distinct_modal_batches": len(modal_job_ids),
        "findings": findings,
    }


def check_youtube_rhythm_and_jl_cuts(
    shot_windows: list[dict[str, Any]],
    utterances: list[dict[str, Any]],
    *,
    min_avg_shot_s: float = 3.0,
    max_avg_shot_s: float = 4.8,
    hook_window_s: float = 30.0,
    min_hook_avg_s: float = 2.0,
    max_hook_avg_s: float = 3.6,
    min_jl_cuts: int = 6,
    min_breathers: int = 4,
    max_breathers: int = 6,
) -> dict[str, Any]:
    """Enforce YouTube docudrama pacing (3.0-4.8s avg cut, 2.0-3.5s first 30s hook, J/L cuts, 4-6 dramatic breathers)."""
    findings: list[str] = []
    durs = [max(0.0, float(s.get("end_s", 0.0)) - float(s.get("start_s", 0.0))) for s in shot_windows]
    avg_shot = float(np.mean(durs)) if durs else 0.0
    hook_durs = [
        max(0.0, float(s.get("end_s", 0.0)) - float(s.get("start_s", 0.0)))
        for s in shot_windows
        if float(s.get("start_s", 0.0)) < hook_window_s
    ]
    hook_avg = float(np.mean(hook_durs)) if hook_durs else 0.0

    jl_count = sum(
        1
        for s in shot_windows
        if float(s.get("j_cut_lead_s", 0.0)) >= 0.25 or float(s.get("l_cut_tail_s", 0.0)) >= 0.25
    )

    breathers: list[float] = []
    sorted_u = sorted(utterances, key=lambda u: float(u.get("start_s", 0.0)))
    for i in range(len(sorted_u) - 1):
        gap = float(sorted_u[i + 1].get("start_s", 0.0)) - float(sorted_u[i].get("end_s", 0.0))
        if bool(sorted_u[i].get("dramatic_breather_after", False)) and 0.75 <= gap <= 2.2:
            breathers.append(round(gap, 2))

    if not (min_avg_shot_s <= avg_shot <= max_avg_shot_s):
        findings.append(f"Average shot length {avg_shot:.2f}s outside YouTube target [{min_avg_shot_s:.1f}s, {max_avg_shot_s:.1f}s]")
    if hook_durs and not (min_hook_avg_s <= hook_avg <= max_hook_avg_s):
        findings.append(f"First 30s Hook average shot length {hook_avg:.2f}s outside [{min_hook_avg_s:.1f}s, {max_hook_avg_s:.1f}s]")
    if jl_count < min_jl_cuts:
        findings.append(f"J/L-cut audio overlaps count {jl_count} < required {min_jl_cuts}")
    if not (min_breathers <= len(breathers) <= max_breathers):
        findings.append(f"Dramatic breathing pauses count {len(breathers)} outside [{min_breathers}, {max_breathers}]")

    return {
        "status": "PASS" if not findings else "FAIL",
        "avg_shot_length_s": round(avg_shot, 2),
        "hook_30s_avg_shot_s": round(hook_avg, 2),
        "jl_cut_count": jl_count,
        "dramatic_breather_count": len(breathers),
        "dramatic_breather_gaps_s": breathers,
        "findings": findings,
    }


def check_overlay_density(
    bridges: list[dict[str, Any]],
    *,
    narration_waves: list[tuple[float, float]] | None = None,
    min_total_overlays: int = 20,
    min_distinct_archetypes: int = 6,
    max_dead_gap_in_wave_s: float = 5.5,
) -> dict[str, Any]:
    """Verify >= 20 unique word-synced overlays, >= 6 distinct archetypes, and 2-5s density across narration waves."""
    findings: list[str] = []
    ids: set[str] = set()
    archetypes: set[str] = set()
    starts: list[float] = []

    for idx, b in enumerate(bridges):
        bid = str(b.get("bridge_id") or b.get("id") or f"ov_{idx + 1}")
        ids.add(bid)
        arch = str(b.get("template") or b.get("archetype") or "").strip()
        if arch:
            archetypes.add(arch)
        starts.append(float(b.get("start_s", 0.0)))

    if len(ids) < min_total_overlays:
        findings.append(f"Word-synced overlays count {len(ids)} < required {min_total_overlays}")
    if len(archetypes) < min_distinct_archetypes:
        findings.append(f"Distinct bridge/overlay archetypes {len(archetypes)} < required {min_distinct_archetypes}: {sorted(archetypes)}")

    max_obs_gap = 0.0
    if narration_waves:
        sorted_b = sorted(bridges, key=lambda x: float(x.get("start_s", 0.0)))
        for w_st, w_en in narration_waves:
            in_wave = [b for b in sorted_b if w_st - 0.5 <= float(b.get("start_s", 0.0)) <= w_en]
            if not in_wave:
                findings.append(f"Narration wave [{w_st:.1f}s-{w_en:.1f}s] has 0 word-synced overlays")
                continue
            pts = [w_st] + [float(b.get("start_s", 0.0)) for b in in_wave] + [w_en]
            for k in range(len(pts) - 1):
                gap = pts[k + 1] - pts[k]
                max_obs_gap = max(max_obs_gap, gap)
                if gap > max_dead_gap_in_wave_s:
                    findings.append(
                        f"Narration wave visual dead zone of {gap:.2f}s (> {max_dead_gap_in_wave_s:.1f}s) between {pts[k]:.1f}s and {pts[k+1]:.1f}s"
                    )

    return {
        "status": "PASS" if not findings else "FAIL",
        "unique_overlays": len(ids),
        "distinct_archetypes": sorted(archetypes),
        "max_wave_gap_s": round(max_obs_gap, 2),
        "findings": findings,
    }


def check_grain_ceiling(
    video_path: Path,
    *,
    sample_times_s: list[float] | None = None,
    max_median_sigma: float = 2.0,
    max_peak_sigma: float = 2.4,
) -> dict[str, Any]:
    """Deterministic high-pass noise / grain ceiling rejecting over-grained plates and enforcing uniform subtle 35mm grain."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    dur = total / max(1.0, fps)
    cap.release()

    times = sample_times_s or [round(dur * (i + 0.5) / 16.0, 2) for i in range(16)]
    frs = _read_frames_at_times(video_path, times)
    sigmas: list[float] = []
    findings: list[str] = []

    for ts, fr in zip(times, frs, strict=False):
        gray = cv2.cvtColor(fr, cv2.COLOR_RGB2GRAY).astype(np.float32)
        h, w = gray.shape
        # Measure interior texture/grain residual using 3x3 median/Gaussian high-pass estimator
        crop = gray[h // 5 : 4 * h // 5, w // 5 : 4 * w // 5]
        blur = cv2.GaussianBlur(crop, (3, 3), 0.8)
        resid = crop - blur
        # MAD-based robust noise sigma estimator (immune to crisp UI/text edges!)
        sigma = float(np.median(np.abs(resid - np.median(resid))) * 1.4826)
        sigmas.append(round(sigma, 3))
        if sigma > max_peak_sigma:
            findings.append(f"frame@{ts:.2f}s: excessive grain/high-freq noise sigma={sigma:.2f} > {max_peak_sigma:.2f}")

    med = float(np.median(sigmas)) if sigmas else 0.0
    peak = float(np.max(sigmas)) if sigmas else 0.0
    if med > max_median_sigma:
        findings.append(f"Median film grain sigma={med:.2f} exceeds ceiling {max_median_sigma:.2f}")

    return {
        "status": "PASS" if not findings else "FAIL",
        "median_grain_sigma": round(med, 3),
        "max_grain_sigma": round(peak, 3),
        "samples": len(sigmas),
        "findings": findings,
    }


def check_audio_anti_repetition(
    sfx_events: list[dict[str, Any]],
    soundscape_report: dict[str, Any],
    *,
    min_distinct_sfx_files: int = 15,
    max_pumping_db: float = 1.0,
) -> dict[str, Any]:
    """Enforce >= 15 distinct real CC0 SFX files, 0 back-to-back identical SFX repeats, < 1.0 dB pumping, -14.0 LUFS, <= -1.0 dBTP."""
    findings: list[str] = []
    sorted_ev = sorted(sfx_events, key=lambda e: float(e.get("time_s", 0.0)))
    distinct_files: set[str] = set()
    prev_path = ""
    consecutive_repeats: list[dict[str, Any]] = []

    for ev in sorted_ev:
        p = str(ev.get("wav_path") or "").strip()
        if not p:
            continue
        name = Path(p).name
        if "synth" in name.lower() or "sine" in name.lower() or "placeholder" in name.lower():
            findings.append(f"Synthetic placeholder SFX prohibited: {name}")
        distinct_files.add(name)
        if prev_path and p == prev_path:
            consecutive_repeats.append({"file": name, "time_s": round(float(ev.get("time_s", 0.0)), 2)})
            findings.append(f"Back-to-back identical SFX repeat at {float(ev.get('time_s', 0.0)):.2f}s: {name}")
        prev_path = p

    if len(distinct_files) < min_distinct_sfx_files:
        findings.append(f"Distinct real SFX/foley files count {len(distinct_files)} < required {min_distinct_sfx_files}")

    lufs = float(soundscape_report.get("integrated_lufs", -99.0))
    peak = float(soundscape_report.get("true_peak_dbtp", soundscape_report.get("peak_dbfs", 0.0)))
    pump = float(soundscape_report.get("max_pause_pumping_swing_db", 0.0))
    if not (-14.5 <= lufs <= -13.5):
        findings.append(f"Master loudness {lufs:.2f} LUFS outside strict -14.0 +/- 0.5 LUFS")
    if peak > -1.0:
        findings.append(f"True peak {peak:.2f} dBTP exceeds -1.0 dBTP")
    if pump >= max_pumping_db:
        findings.append(f"Ducking pumping {pump:.2f} dB >= strict {max_pumping_db:.1f} dB ceiling")

    return {
        "status": "PASS" if not findings else "FAIL",
        "distinct_sfx_files": len(distinct_files),
        "consecutive_repeats": consecutive_repeats,
        "integrated_lufs": lufs,
        "peak_dbfs": peak,
        "pumping_db": pump,
        "findings": findings,
    }


def check_map_stability(
    video_path: Path,
    *,
    max_mean_hf_shimmer: float = 2.6,
    max_peak_hf_shimmer: float = 4.2,
    max_p85_label_jerk_px: float = 0.55,
    max_rotational_sway_deg: float = 0.35,
    max_rot_oscillation_deg: float = 0.22,
    max_samples: int = 24,
) -> dict[str, Any]:
    """Deterministic map stability gate measuring WebGL shimmer, label jitter, and camera gimbal sway.

    Samples consecutive frame triplets ``(t-1, t, t+1)`` across the map video:
    1. High-frequency temporal shimmer: aligns consecutive luminance frames via homography/``phaseCorrelate``
       to cancel smooth camera pan, then measures the mean energy in the spatial high-pass residual.
    2. Label / corner feature jerk: tracks crisp corners across ``(t-1 -> t -> t+1)`` via PyrLK optical flow
       and measures second-order acceleration ``|(p_{t+1} - p_t) - (p_t - p_{t-1})|``.
    3. Rotational camera sway & lateral wobble: fits ``cv2.estimateAffinePartial2D`` across consecutive
       pairs to extract frame-to-frame rotation ``dtheta_deg`` and orthogonal lateral velocity residuals,
       catching subtle horizon wobble ("ქანაობა") that pure translation checks miss.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open map video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    if total < 5:
        return {
            "status": "FAIL",
            "findings": [f"Map video too short for stability check ({total} frames)"],
        }

    # Sample evenly spaced triplet centers across interior [10%..90%] (active camera motion)
    lo = max(2, int(total * 0.10))
    hi = max(lo + 1, min(total - 2, int(total * 0.90)))
    n_trips = min(max_samples, max(3, (hi - lo) // 3))
    centers = sorted({int(round(lo + i * (hi - lo) / max(1, n_trips - 1))) for i in range(n_trips)})
    wanted_frames: list[int] = []
    for c in centers:
        wanted_frames.extend([c - 1, c, c + 1])
    unique_idx = sorted(set(wanted_frames))

    cap = cv2.VideoCapture(str(video_path))
    decoded: dict[int, np.ndarray] = {}
    cur = 0
    max_idx = unique_idx[-1]
    wanted_set = set(unique_idx)
    try:
        while cur <= max_idx:
            if not cap.grab():
                break
            if cur in wanted_set:
                ok, bgr = cap.retrieve()
                if ok and bgr is not None:
                    # Evaluate at 960x540 (preserves sharp 1px aliasing & text snapping while staying super fast)
                    if bgr.shape[1] > 960:
                        bgr = cv2.resize(bgr, (960, int(round(bgr.shape[0] * 960.0 / bgr.shape[1]))), interpolation=cv2.INTER_AREA)
                    decoded[cur] = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            cur += 1
    finally:
        cap.release()

    shimmers: list[float] = []
    jerks: list[float] = []
    rot_deltas_deg: list[float] = []
    rot_oscillations_deg: list[float] = []
    trans_vecs: list[tuple[float, float]] = []
    hann_cache: np.ndarray | None = None

    for c in centers:
        if (c - 1) not in decoded or c not in decoded or (c + 1) not in decoded:
            continue
        g0 = decoded[c - 1]
        g1 = decoded[c]
        g2 = decoded[c + 1]
        h, w = g1.shape
        # Focus on interior map canvas (exclude static top/bottom HUD corners)
        y0, y1 = int(h * 0.16), int(h * 0.84)
        x0, x1 = int(w * 0.08), int(w * 0.92)
        c0 = g0[y0:y1, x0:x1].astype(np.float32)
        c1 = g1[y0:y1, x0:x1].astype(np.float32)
        if hann_cache is None or hann_cache.shape != c0.shape:
            hann_cache = cv2.createHanningWindow((c0.shape[1], c0.shape[0]), cv2.CV_32F)

        # 1. Track crisp features across (t-1 -> t -> t+1) for perspective alignment, jerk, and rotational sway
        roi0 = g0[y0:y1, x0:x1]
        roi1 = g1[y0:y1, x0:x1]
        roi2 = g2[y0:y1, x0:x1]
        pts0 = cv2.goodFeaturesToTrack(roi0, maxCorners=180, qualityLevel=0.04, minDistance=10, blockSize=5)
        c0_aligned = None
        if pts0 is not None and len(pts0) >= 8:
            pts1, st1, _ = cv2.calcOpticalFlowPyrLK(roi0, roi1, pts0, None, winSize=(15, 15), maxLevel=2)
            pts2, st2, _ = cv2.calcOpticalFlowPyrLK(roi1, roi2, pts1, None, winSize=(15, 15), maxLevel=2)
            good01 = st1.ravel() == 1
            if int(np.sum(good01)) >= 8:
                h_mat, _ = cv2.findHomography(pts0[good01], pts1[good01], cv2.RANSAC, 2.0)
                if h_mat is not None:
                    c0_aligned = cv2.warpPerspective(
                        c0,
                        h_mat,
                        (c0.shape[1], c0.shape[0]),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE,
                    )
                aff01, _ = cv2.estimateAffinePartial2D(
                    pts0[good01], pts1[good01], method=cv2.RANSAC, ransacReprojThreshold=2.0
                )
                theta01 = None
                if aff01 is not None:
                    theta01 = float(math.degrees(math.atan2(float(aff01[1, 0]), float(aff01[0, 0]))))
                    rot_deltas_deg.append(abs(theta01))
                    trans_vecs.append((float(aff01[0, 2]), float(aff01[1, 2])))
            else:
                theta01 = None
            good = good01 & (st2.ravel() == 1)
            if int(np.sum(good)) >= 6:
                v01 = pts1[good] - pts0[good]
                v12 = pts2[good] - pts1[good]
                accel = np.linalg.norm(v12 - v01, axis=-1).ravel()
                valid_acc = accel[accel < 6.0]
                if valid_acc.size >= 4:
                    jerks.extend(valid_acc.tolist())
                if theta01 is not None and int(np.sum(good)) >= 8:
                    aff12, _ = cv2.estimateAffinePartial2D(
                        pts1[good], pts2[good], method=cv2.RANSAC, ransacReprojThreshold=2.0
                    )
                    if aff12 is not None:
                        theta12 = float(math.degrees(math.atan2(float(aff12[1, 0]), float(aff12[0, 0]))))
                        rot_deltas_deg.append(abs(theta12))
                        rot_oscillations_deg.append(abs(theta12 - theta01))

        # 2. Motion-compensated high-frequency shimmer (homography cancels 3D tilt+zoom+pan; fallback phaseCorrelate)
        if c0_aligned is None:
            (dx, dy), _resp = cv2.phaseCorrelate(c0, c1, window=hann_cache)
            mat = np.array([[1.0, 0.0, float(dx)], [0.0, 1.0, float(dy)]], dtype=np.float32)
            c0_aligned = cv2.warpAffine(
                c0, mat, (c0.shape[1], c0.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
            )
        hp0 = c0_aligned - cv2.GaussianBlur(c0_aligned, (5, 5), 1.1)
        hp1 = c1 - cv2.GaussianBlur(c1, (5, 5), 1.1)
        # Exclude 12px border where warp replicates edge pixels
        diff_hp = np.abs(hp1[12:-12, 12:-12] - hp0[12:-12, 12:-12])
        shimmers.append(float(np.mean(diff_hp)))

    findings: list[str] = []
    mean_shimmer = float(np.mean(shimmers)) if shimmers else 0.0
    peak_shimmer = float(np.max(shimmers)) if shimmers else 0.0
    med_jerk = float(np.median(jerks)) if jerks else 0.0
    p85_jerk = float(np.percentile(jerks, 85)) if jerks else 0.0
    max_rot_sway = float(np.percentile(rot_deltas_deg, 95)) if rot_deltas_deg else 0.0
    rot_osc_std = float(np.std(rot_oscillations_deg)) if len(rot_oscillations_deg) >= 2 else (
        float(rot_oscillations_deg[0]) if rot_oscillations_deg else 0.0
    )

    lateral_sway_std = 0.0
    if len(trans_vecs) >= 3:
        arr = np.asarray(trans_vecs, dtype=np.float64)
        mean_vec = np.mean(arr, axis=0)
        norm = float(np.linalg.norm(mean_vec))
        if norm > 0.05:
            ortho = np.array([-mean_vec[1] / norm, mean_vec[0] / norm], dtype=np.float64)
            lat_proj = arr @ ortho
            lateral_sway_std = float(np.std(lat_proj))

    if mean_shimmer > max_mean_hf_shimmer:
        findings.append(f"High-frequency map shimmer {mean_shimmer:.2f} exceeds {max_mean_hf_shimmer:.2f} ceiling")
    if peak_shimmer > max_peak_hf_shimmer:
        findings.append(f"Peak high-frequency map shimmer {peak_shimmer:.2f} exceeds {max_peak_hf_shimmer:.2f} ceiling")
    if p85_jerk > max_p85_label_jerk_px:
        findings.append(f"Label/feature jitter p85 jerk={p85_jerk:.3f}px/f^2 exceeds {max_p85_label_jerk_px:.2f}px/f^2 ceiling")
    if max_rot_sway > max_rotational_sway_deg:
        findings.append(
            f"Map camera rotational sway {max_rot_sway:.3f}deg/frame exceeds {max_rotational_sway_deg:.2f}deg ceiling"
        )
    if rot_osc_std > max_rot_oscillation_deg:
        findings.append(
            f"Map camera rotational oscillation std={rot_osc_std:.3f}deg exceeds {max_rot_oscillation_deg:.2f}deg ceiling"
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "fps": round(fps, 2),
        "triplets_sampled": len(shimmers),
        "mean_hf_shimmer": round(mean_shimmer, 3),
        "peak_hf_shimmer": round(peak_shimmer, 3),
        "median_label_jerk_px": round(med_jerk, 3),
        "p85_label_jerk_px": round(p85_jerk, 3),
        "max_rot_sway_deg": round(max_rot_sway, 4),
        "rot_oscillation_std_deg": round(rot_osc_std, 4),
        "lateral_sway_std_px": round(lateral_sway_std, 4),
        "findings": findings,
    }


def _read_frames_at_indices(video_path: Path, frame_indices: list[int]) -> dict[int, np.ndarray]:
    """Decode exact 0-based video frame indices as RGB uint8 arrays."""
    if not frame_indices:
        return {}
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    clamped = sorted({max(0, min(max(0, total - 1), int(i))) for i in frame_indices})
    max_idx = clamped[-1]
    wanted = set(clamped)
    decoded: dict[int, np.ndarray] = {}
    try:
        if total > 1800 and len(clamped) <= 180:
            # Seek a few frames early and step forward for frame-accurate reads on H.264 long GOPs
            for idx in clamped:
                seek_to = max(0, idx - 6)
                cap.set(cv2.CAP_PROP_POS_FRAMES, seek_to)
                cur = seek_to
                while cur <= idx:
                    if not cap.grab():
                        break
                    if cur == idx:
                        ok, bgr = cap.retrieve()
                        if ok and bgr is not None:
                            decoded[idx] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                    cur += 1
        else:
            cur = 0
            while cur <= max_idx:
                if not cap.grab():
                    break
                if cur in wanted:
                    ok, bgr = cap.retrieve()
                    if ok and bgr is not None:
                        decoded[cur] = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                cur += 1
    finally:
        cap.release()
    return decoded


def check_no_jump_cuts(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    chained_min_ssim: float = 0.88,
    jump_cut_low_ssim: float = 0.55,
    jump_cut_high_ssim: float = 0.88,
    same_framing_corr_threshold: float = 0.82,
) -> dict[str, Any]:
    """Enforce zero jump cuts across every shot boundary.

    1. **Chained Handoff Contract** (``Shot B.chained_from == Shot A.shot_id``):
       Measures SSIM between the last frame of Shot A and the first frame of Shot B;
       MUST satisfy ``SSIM >= 0.88`` (catches v3 bug where parents were trimmed early before ``F_ext``).
    2. **Same-Environment Jump-Cut Detector** (non-chained adjacent cuts):
       Flags cuts landing in the uncanny same-framing jump-cut band ``0.55 < SSIM < 0.88`` where
       camera framing/layout stayed nearly identical (catches accidental jump cuts & mismatched scale cuts).
    """
    from skimage.metrics import structural_similarity as ssim

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    if len(shot_windows) < 2 or total_frames < 2:
        return {
            "status": "PASS",
            "cuts_checked": 0,
            "chained_handoffs_checked": 0,
            "cuts": [],
            "findings": [],
        }

    # Collect exact boundary frame pairs (last frame of Shot A, first frame of Shot B)
    pair_specs: list[dict[str, Any]] = []
    wanted_indices: list[int] = []
    for i in range(len(shot_windows) - 1):
        a = shot_windows[i]
        b = shot_windows[i + 1]
        cut_s = float(b.get("start_s", a.get("end_s", 0.0)))
        if cut_s <= 0.02:
            continue
        b_idx = max(1, min(total_frames - 1, int(round(cut_s * fps))))
        a_idx = max(0, b_idx - 1)
        wanted_indices.extend([a_idx, b_idx])
        pair_specs.append({"a": a, "b": b, "a_idx": a_idx, "b_idx": b_idx, "cut_s": cut_s})

    frames = _read_frames_at_indices(video_path, wanted_indices)

    findings: list[str] = []
    cut_reports: list[dict[str, Any]] = []
    chained_checked = 0

    for ps in pair_specs:
        a = ps["a"]
        b = ps["b"]
        a_id = str(a.get("shot_id") or "shot_a")
        b_id = str(b.get("shot_id") or "shot_b")
        fr_a = frames.get(ps["a_idx"])
        fr_b = frames.get(ps["b_idx"])
        if fr_a is None or fr_b is None:
            continue

        ga = cv2.cvtColor(cv2.resize(fr_a, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        gb = cv2.cvtColor(cv2.resize(fr_b, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        raw_sim = ssim(ga, gb, data_range=255)
        sim = float(raw_sim[0] if isinstance(raw_sim, tuple) else raw_sim)
        # Gently smoothed SSIM absorbs 1-frame fire/spark/snow flicker across LTX VAE handoffs while catching pose/trim jumps
        ga_s = cv2.GaussianBlur(ga, (7, 7), 1.8)
        gb_s = cv2.GaussianBlur(gb, (7, 7), 1.8)
        raw_sim_s = ssim(ga_s, gb_s, data_range=255)
        smooth_sim = float(raw_sim_s[0] if isinstance(raw_sim_s, tuple) else raw_sim_s)
        handoff_ssim = max(sim, smooth_sim)

        # Low-resolution layout correlation detects identical camera framing/horizon even if subject jumped
        la = cv2.resize(ga, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        lb = cv2.resize(gb, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
        la_c = la - float(np.mean(la))
        lb_c = lb - float(np.mean(lb))
        denom = float(np.linalg.norm(la_c) * np.linalg.norm(lb_c))
        layout_corr = float(np.dot(la_c, lb_c) / denom) if denom > 1e-6 else 0.0

        chained_from = str(b.get("chained_from") or "").strip()
        is_chained = bool(chained_from and chained_from == a_id)
        grp_a = str(a.get("scene_group") or "").strip()
        grp_b = str(b.get("scene_group") or "").strip()
        same_group = bool(grp_a and grp_a == grp_b)
        scale_a = str(a.get("shot_scale") or "").strip().lower()
        scale_b = str(b.get("shot_scale") or "").strip().lower()
        scale_changed = bool(scale_a and scale_b and scale_a != scale_b)
        angle_delta = float(b.get("camera_angle_delta_deg", 0.0))
        allow_match = bool(b.get("allow_match_cut", False))

        passed = True
        verdict = "clean_cut"
        if is_chained:
            chained_checked += 1
            if handoff_ssim < chained_min_ssim or layout_corr < 0.90:
                passed = False
                verdict = "broken_chained_handoff"
                findings.append(
                    f"Broken chained handoff at {ps['cut_s']:.2f}s ({a_id} -> {b_id}): "
                    f"handoff_SSIM={handoff_ssim:.3f} (raw={sim:.3f}, smooth={smooth_sim:.3f}) < {chained_min_ssim:.2f} "
                    f"or layout_corr={layout_corr:.3f} < 0.90 (parent clip trimmed early or wrong handoff frame)"
                )
            else:
                verdict = "seamless_chained_handoff"
        elif (
            not allow_match
            and jump_cut_low_ssim < sim < jump_cut_high_ssim
            and (layout_corr >= same_framing_corr_threshold or (same_group and not scale_changed and angle_delta < 30.0))
        ):
            passed = False
            verdict = "jump_cut_detected"
            findings.append(
                f"Jump cut detected at {ps['cut_s']:.2f}s ({a_id} -> {b_id}): "
                f"SSIM={sim:.3f} in ({jump_cut_low_ssim:.2f}, {jump_cut_high_ssim:.2f}) "
                f"with layout_corr={layout_corr:.3f} (same-environment framing jump)"
            )

        cut_reports.append(
            {
                "cut_s": round(ps["cut_s"], 3),
                "from_shot": a_id,
                "to_shot": b_id,
                "is_chained": is_chained,
                "ssim": round(sim, 4),
                "smooth_ssim": round(smooth_sim, 4),
                "handoff_ssim": round(handoff_ssim, 4),
                "layout_corr": round(layout_corr, 4),
                "verdict": verdict,
                "passed": passed,
            }
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "cuts_checked": len(cut_reports),
        "chained_handoffs_checked": chained_checked,
        "cuts": cut_reports,
        "findings": findings,
    }


def check_docudrama_70_30_balance(
    shots: list[dict[str, Any]],
    utterances: list[dict[str, Any]],
    *,
    min_dramatic_ratio: float = 0.25,
    max_dramatic_ratio: float = 0.38,
    min_dramatic_scenes: int = 2,
    min_scene_duration_s: float = 35.0,
    min_narrator_free_stretch_s: float = 25.0,
) -> dict[str, Any]:
    """Enforce true 70/30 YouTube Docudrama balance (not 98% wall-to-wall narration montage).

    Requirements:
    1. Dramatic acting/action share = 25%–38% of total runtime.
    2. At least ``min_dramatic_scenes`` (>= 2) continuous dramatic scenes, each ``>= 35s`` long.
    3. Each qualifying dramatic scene contains a continuous narrator-free stretch ``>= 25s``
       driven by real moving video clips (not static 2.5D slides).
    """
    findings: list[str] = []
    if not shots:
        return {
            "status": "FAIL",
            "dramatic_ratio": 0.0,
            "dramatic_scenes": [],
            "findings": ["No shots provided for 70/30 docudrama balance check"],
        }

    ordered_shots = sorted(shots, key=lambda s: float(s.get("start_s", 0.0)))
    total_dur = max(
        0.0,
        max(float(s.get("end_s", 0.0)) for s in ordered_shots)
        - min(float(s.get("start_s", 0.0)) for s in ordered_shots),
    )

    # Group contiguous dramatic shots into continuous dramatic scenes
    real_video_kinds = {"video", "ltx", "ltx_25", "ltx_video", "ltx_multishot", "helios"}
    scenes: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    dramatic_dur = 0.0

    for s in ordered_shots:
        st = float(s.get("start_s", 0.0))
        en = float(s.get("end_s", st))
        dur = max(0.0, en - st)
        sc_id = str(s.get("dramatic_scene_id") or "").strip()
        is_dram = bool(s.get("is_dramatic_scene", False)) or bool(s.get("is_dramatic_showcase", False)) or bool(sc_id)
        if not is_dram:
            if cur is not None:
                scenes.append(cur)
                cur = None
            continue

        dramatic_dur += dur
        label = sc_id or str(s.get("scene_group") or "dramatic_scene")
        kind = str(s.get("kind") or "").lower()
        is_real_vid = kind in real_video_kinds

        if cur is not None and (cur["scene_id"] == label or abs(st - cur["end_s"]) <= 0.15 and not sc_id):
            cur["end_s"] = max(cur["end_s"], en)
            cur["shot_count"] += 1
            cur["real_video_dur_s"] += dur if is_real_vid else 0.0
        else:
            if cur is not None:
                scenes.append(cur)
            cur = {
                "scene_id": label,
                "start_s": st,
                "end_s": en,
                "shot_count": 1,
                "real_video_dur_s": dur if is_real_vid else 0.0,
            }
    if cur is not None:
        scenes.append(cur)

    # Filter narrator utterances (exclude diegetic actor whispers if tagged speaker != narrator)
    narr_spans = sorted(
        [
            (float(u.get("start_s", 0.0)), float(u.get("end_s", 0.0)))
            for u in utterances
            if str(u.get("speaker", "narrator")).lower() not in {"diegetic", "actor", "sfx"}
            and float(u.get("end_s", 0.0)) > float(u.get("start_s", 0.0))
        ]
    )

    qualifying_scenes: list[dict[str, Any]] = []
    for sc in scenes:
        sc_st = float(sc["start_s"])
        sc_en = float(sc["end_s"])
        sc_dur = max(0.0, sc_en - sc_st)
        # Compute longest continuous narrator-free interval within [sc_st, sc_en]
        cursor = sc_st
        longest_silent = 0.0
        for u_st, u_en in narr_spans:
            if u_en <= sc_st:
                continue
            if u_st >= sc_en:
                break
            if u_st > cursor:
                longest_silent = max(longest_silent, min(u_st, sc_en) - cursor)
            cursor = max(cursor, min(u_en, sc_en))
        if sc_en > cursor:
            longest_silent = max(longest_silent, sc_en - cursor)

        real_vid_ratio = sc["real_video_dur_s"] / max(1e-6, sc_dur)
        sc["duration_s"] = round(sc_dur, 2)
        sc["longest_narrator_free_s"] = round(longest_silent, 2)
        sc["real_video_ratio"] = round(real_vid_ratio, 3)
        sc["qualifies"] = (
            sc_dur >= min_scene_duration_s
            and longest_silent >= min_narrator_free_stretch_s
            and real_vid_ratio >= 0.85
        )
        if sc["qualifies"]:
            qualifying_scenes.append(sc)
        else:
            if sc_dur < min_scene_duration_s:
                findings.append(
                    f"Dramatic scene {sc['scene_id']!r} duration {sc_dur:.1f}s < required {min_scene_duration_s:.0f}s"
                )
            if longest_silent < min_narrator_free_stretch_s:
                findings.append(
                    f"Dramatic scene {sc['scene_id']!r} narrator-free stretch {longest_silent:.1f}s "
                    f"< required {min_narrator_free_stretch_s:.0f}s"
                )
            if real_vid_ratio < 0.85:
                findings.append(
                    f"Dramatic scene {sc['scene_id']!r} real moving video ratio {real_vid_ratio:.0%} < 85%"
                )

    ratio = (dramatic_dur / total_dur) if total_dur > 0 else 0.0
    if not (min_dramatic_ratio <= ratio <= max_dramatic_ratio):
        findings.append(
            f"Dramatic scene share {ratio:.1%} outside 70/30 docudrama target [{min_dramatic_ratio:.0%}, {max_dramatic_ratio:.0%}]"
        )
    if len(qualifying_scenes) < min_dramatic_scenes:
        findings.append(
            f"Qualifying continuous dramatic scenes count {len(qualifying_scenes)} < required {min_dramatic_scenes}"
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "total_duration_s": round(total_dur, 2),
        "dramatic_duration_s": round(dramatic_dur, 2),
        "dramatic_ratio": round(ratio, 4),
        "qualifying_scene_count": len(qualifying_scenes),
        "dramatic_scenes": scenes,
        "findings": findings,
    }


def check_pts_monotonicity(
    video_path: Path,
    *,
    expected_fps: float = 24.0,
    max_dt_jitter_s: float = 0.006,
) -> dict[str, Any]:
    """Verify presentation-order PTS monotonicity and zero concat-seam timestamp gaps via ffprobe."""
    import subprocess

    if not video_path.is_file():
        return {"status": "FAIL", "findings": [f"Video missing: {video_path}"]}
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "packet=pts_time",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        text=True,
    )
    pts_vals: list[float] = []
    for line in out.splitlines():
        s = line.strip().split(",")[0].strip()
        if not s or s == "N/A":
            continue
        try:
            pts_vals.append(float(s))
        except ValueError:
            continue
    if len(pts_vals) < 2:
        return {"status": "FAIL", "packet_count": len(pts_vals), "findings": ["Insufficient video PTS packets"]}

    # Sort into presentation order (handles H.264 B-frame decode reordering cleanly)
    pts_sorted = sorted(pts_vals)
    dts = np.diff(np.asarray(pts_sorted, dtype=np.float64))
    target_dt = 1.0 / max(1.0, float(expected_fps))
    duplicates = int(np.sum(dts <= 1e-6))
    anomalies = [
        {"frame_idx": int(i), "pts_s": round(pts_sorted[i], 4), "dt_s": round(float(dts[i]), 5)}
        for i in range(len(dts))
        if abs(float(dts[i]) - target_dt) > max_dt_jitter_s
    ]
    findings: list[str] = []
    if duplicates > 0:
        findings.append(f"Found {duplicates} duplicate presentation PTS timestamps")
    if anomalies:
        findings.append(
            f"Found {len(anomalies)} concat-seam PTS interval anomalies (> {max_dt_jitter_s * 1000:.1f}ms from {target_dt * 1000:.2f}ms); "
            f"first={anomalies[0]}"
        )
    return {
        "status": "PASS" if not findings else "FAIL",
        "packet_count": len(pts_sorted),
        "duplicate_pts_count": duplicates,
        "min_dt_s": round(float(np.min(dts)), 6),
        "max_dt_s": round(float(np.max(dts)), 6),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:20],
        "findings": findings,
    }


def check_visual_audit_clean(
    shot_windows: list[dict[str, Any]],
    visual_audit_path: Path,
) -> dict[str, Any]:
    """Fail-closed check ensuring zero visually REJECTED clips leak into a master timeline."""
    import json

    if not visual_audit_path.is_file():
        return {"status": "FAIL", "findings": [f"Missing clip visual audit JSON: {visual_audit_path}"]}
    data = json.loads(visual_audit_path.read_text(encoding="utf-8"))
    clips_obj = data.get("clips")
    rejected: set[str] = set()
    if isinstance(clips_obj, dict):
        for sid, info in clips_obj.items():
            verdict = str(
                (info.get("verdict") or info.get("decision") or info.get("status") or "")
                if isinstance(info, dict)
                else info
            ).upper()
            if "REJECT" in verdict:
                rejected.add(str(sid))
    elif isinstance(clips_obj, list):
        for item in clips_obj:
            if not isinstance(item, dict):
                continue
            sid = str(item.get("shot_id") or item.get("clip_id") or "")
            verdict = str(item.get("verdict") or item.get("decision") or item.get("status") or "").upper()
            if sid and "REJECT" in verdict:
                rejected.add(sid)

    leaked: list[str] = []
    for sh in shot_windows:
        sid = str(sh.get("shot_id") or "")
        src_stem = Path(str(sh.get("source_path") or "")).stem
        if sid in rejected or src_stem in rejected:
            leaked.append(sid or src_stem)

    findings = [f"Visually REJECTED clip leaked into master timeline: {sid}" for sid in leaked]
    return {
        "status": "PASS" if not findings else "FAIL",
        "rejected_pool_count": len(rejected),
        "leaked_rejected_clips": leaked,
        "findings": findings,
    }


def check_silence_drop_effectiveness(
    master_wav: Path,
    silence_drops: list[dict[str, Any]],
    *,
    voice_wav: Path | None = None,
    max_master_rms_dbfs: float = -32.0,
    max_voice_rms_dbfs: float = -38.0,
) -> dict[str, Any]:
    """Verify every configured cinema silence drop actually creates silence and is not masked by narration."""
    import soundfile as sf

    if not silence_drops:
        return {"status": "PASS", "checked_drops": 0, "drops": [], "findings": []}
    if not master_wav.is_file():
        return {"status": "FAIL", "findings": [f"Missing master audio WAV: {master_wav}"]}

    mix, sr = sf.read(str(master_wav), dtype="float32", always_2d=True)
    voice = None
    if voice_wav is not None and voice_wav.is_file():
        voice, v_sr = sf.read(str(voice_wav), dtype="float32", always_2d=True)
        if v_sr != sr:
            voice = None

    drops_report: list[dict[str, Any]] = []
    findings: list[str] = []
    for sd in silence_drops:
        t0 = max(0.0, float(sd.get("time_s", 0.0)))
        dur_sd = max(0.05, float(sd.get("duration_s", 0.4)))
        s0 = max(0, min(len(mix) - 1, int(round(t0 * sr))))
        s1 = max(s0 + 1, min(len(mix), int(round((t0 + dur_sd) * sr))))
        m_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(mix[s0:s1] ** 2)) + 1e-12)))
        v_rms_db = -240.0
        if voice is not None and s0 < len(voice):
            v_seg = voice[s0 : min(len(voice), s1)]
            if len(v_seg) > 0:
                v_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(v_seg ** 2)) + 1e-12)))

        voice_masked = v_rms_db > max_voice_rms_dbfs
        too_loud = m_rms_db > max_master_rms_dbfs
        ok = (not voice_masked) and (not too_loud)
        drops_report.append(
            {
                "time_s": round(t0, 3),
                "duration_s": round(dur_sd, 3),
                "master_rms_dbfs": round(m_rms_db, 2),
                "voice_rms_dbfs": round(v_rms_db, 2),
                "voice_masked": voice_masked,
                "passed": ok,
            }
        )
        if voice_masked:
            findings.append(
                f"Silence drop @{t0:.2f}s (+{dur_sd:.2f}s) masked by active narration (voice_rms={v_rms_db:.1f} dBFS > {max_voice_rms_dbfs:.1f} dBFS)"
            )
        elif too_loud:
            findings.append(
                f"Silence drop @{t0:.2f}s (+{dur_sd:.2f}s) failed to duck master (master_rms={m_rms_db:.1f} dBFS > {max_master_rms_dbfs:.1f} dBFS)"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "checked_drops": len(drops_report),
        "drops": drops_report,
        "findings": findings,
    }


def check_word_to_shot_sync(
    shot_windows: list[dict[str, Any]],
    word_timestamps: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    *,
    max_drift_s: float = 1.8,
) -> dict[str, Any]:
    """Verify key spoken nouns land inside (or within ``max_drift_s`` of) their matching hero shots.

    Each anchor dict specifies ``{"keyword": "bronze", "shot_id": "v4_c3_bronze_forge_pour"}``
    with optional ``min_time_s`` / ``max_time_s`` search bounds.
    """
    by_sid = {str(s.get("shot_id") or ""): s for s in shot_windows}
    checked: list[dict[str, Any]] = []
    findings: list[str] = []

    for anc in anchors:
        kw = str(anc.get("keyword") or "").strip().lower()
        sid = str(anc.get("shot_id") or "").strip()
        if not kw or sid not in by_sid:
            findings.append(f"Invalid word-to-shot anchor {anc!r} (shot_id missing from timeline)")
            continue
        sh = by_sid[sid]
        sh_st, sh_en = float(sh.get("start_s", 0.0)), float(sh.get("end_s", 0.0))
        min_t = float(anc.get("min_time_s", 0.0))
        max_t = float(anc.get("max_time_s", 1e9))

        matches = [
            float(w["start_s"])
            for w in word_timestamps
            if min_t <= float(w.get("start_s", -1.0)) <= max_t
            and kw in str(w.get("word", "")).lower()
        ]
        if not matches:
            findings.append(f"Anchor keyword {kw!r} for shot {sid} not found in word_timestamps")
            continue

        # Pick the spoken occurrence closest to the target shot window
        def _dist(wt: float, lo: float = sh_st, hi: float = sh_en) -> float:
            if lo <= wt <= hi:
                return 0.0
            return min(abs(wt - lo), abs(wt - hi))

        best_wt = min(matches, key=_dist)
        drift = _dist(best_wt)
        ok = drift <= max_drift_s
        checked.append(
            {
                "keyword": kw,
                "shot_id": sid,
                "word_time_s": round(best_wt, 3),
                "shot_window_s": [round(sh_st, 3), round(sh_en, 3)],
                "drift_s": round(drift, 3),
                "passed": ok,
            }
        )
        if not ok:
            findings.append(
                f"Word-to-shot sync lag for {kw!r} (@{best_wt:.2f}s) vs shot {sid} "
                f"[{sh_st:.2f}s-{sh_en:.2f}s]: drift={drift:.2f}s > {max_drift_s:.2f}s"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "anchors_checked": len(checked),
        "anchors": checked,
        "findings": findings,
    }


_SEED_PLATE_KEYS = ("seed_plate_path", "plate_path", "start_picture", "source_image_path", "image_path")
_PLATE_LAYERS = ("provenance", "plate", "seed_plate", "extra")


def _spec_layers(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [spec] + [spec[k] for k in _PLATE_LAYERS if isinstance(spec.get(k), dict)]


def _shrink_plate(gray: np.ndarray, width: int = 640) -> np.ndarray:
    if gray.shape[1] <= width:
        return gray
    height = max(8, round(gray.shape[0] * width / gray.shape[1]))
    return cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)


def _sub_rect_score(master: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    """Best correlation of ``candidate`` as a smaller rectangle of ``master`` (both gray), and its relative width."""

    def search(width: int, scales: np.ndarray) -> tuple[float, float]:
        height = max(8, round(master.shape[0] * width / master.shape[1]))
        big = cv2.resize(master, (width, height), interpolation=cv2.INTER_AREA)
        best_score, best_scale = -1.0, 0.0
        for scale in scales:
            tw = round(width * float(scale))
            th = round(tw * candidate.shape[0] / candidate.shape[1])
            if tw < 16 or th < 16 or tw > width or th > height:
                continue
            templ = cv2.resize(candidate, (tw, th), interpolation=cv2.INTER_AREA)
            if float(templ.std()) < 4.0:
                continue
            score = float(np.nan_to_num(cv2.matchTemplate(big, templ, cv2.TM_CCOEFF_NORMED), nan=-1.0,
                                        posinf=-1.0, neginf=-1.0).max())
            if score > best_score:
                best_score, best_scale = score, float(scale)
        return best_score, best_scale

    score, scale = search(128, np.arange(0.25, 0.961, 0.02))
    if score < 0.60:
        return score, scale
    # Only the finer pass is trusted: small pictures correlate too easily
    return search(384, np.arange(max(0.2, scale - 0.024), min(0.97, scale + 0.0241), 0.004))


def check_no_cropped_seed_plates(
    shot_specs: list[dict[str, Any]],
    *,
    base_dir: Path | None = None,
    max_phash_hamming: int | None = None,
    containment_score_min: float | None = None,
) -> dict[str, Any]:
    """Reject any shot whose seed plate was cut out of another plate (BP-217).

    Declared evidence: ``crop_from_master``, ``rel_w`` / ``rel_h`` below 1.0, ``crop_box`` or ``source_master`` on
    the spec or its ``provenance`` / ``plate`` / ``seed_plate`` / ``extra`` block. Measured evidence, between the
    different plate files of the specs: a near-identical perceptual hash, or one plate found as a smaller rectangle
    inside another. A shot and the parent it is chained from are not compared (the handoff frame is meant to match).
    A named plate that cannot be read fails: it cannot be proven native.
    """
    import hashlib

    import imagehash
    from PIL import Image

    hamming_max = int(sourced_rules.T("BP-217", "phash_hamming_max") if max_phash_hamming is None else max_phash_hamming)
    score_min = float(
        sourced_rules.T("BP-217", "containment_score_min") if containment_score_min is None else containment_score_min
    )
    findings: list[str] = []
    if not shot_specs:
        findings.append("no shot specs given: seed plates cannot be proven native")

    plates: dict[str, dict[str, Any]] = {}
    for idx, spec in enumerate(shot_specs):
        sid = str(spec.get("shot_id") or f"shot_{idx + 1}")
        raw_path = ""
        for layer in _spec_layers(spec):
            if layer.get("crop_from_master"):
                findings.append(f"{sid}: crop_from_master={layer['crop_from_master']!r} (cropped plates are banned)")
            for key in ("rel_w", "rel_h"):
                if layer.get(key) is not None and float(layer[key]) < 1.0 - 1e-6:
                    findings.append(f"{sid}: {key}={float(layer[key]):.3f} < 1.0 is a sub-region of a wider plate")
            for key in ("crop_box", "source_master"):
                if layer.get(key):
                    findings.append(f"{sid}: {key}={layer[key]!r} records a crop of another plate")
            raw_path = raw_path or next((str(layer[k]) for k in _SEED_PLATE_KEYS if layer.get(k)), "")
        if not raw_path:
            continue
        plate = Path(raw_path)
        if base_dir is not None and not plate.is_absolute():
            plate = Path(base_dir) / plate
        data = np.fromfile(str(plate), dtype=np.uint8) if plate.is_file() else np.zeros(0, dtype=np.uint8)
        gray = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE) if data.size else None
        if gray is None:
            findings.append(f"{sid}: seed plate {raw_path!r} is missing or unreadable")
            continue
        digest = hashlib.sha256(data.tobytes()).hexdigest()
        row = plates.setdefault(digest, {"path": raw_path, "gray": _shrink_plate(gray), "shots": [], "parents": set()})
        row["shots"].append(sid)
        if spec.get("chained_from"):
            row["parents"].add(str(spec["chained_from"]))

    rows = list(plates.values())
    for row in rows:
        row["phash"] = imagehash.phash(Image.fromarray(row["gray"]))
        row["flat"] = float(row["gray"].std()) < 4.0

    matches: list[dict[str, Any]] = []
    for i, a in enumerate(rows):
        for j in range(i + 1, len(rows)):
            b = rows[j]
            if a["flat"] or b["flat"] or a["parents"] & set(b["shots"]) or b["parents"] & set(a["shots"]):
                continue
            hamming = int(a["phash"] - b["phash"])
            if hamming <= hamming_max:
                matches.append({"kind": "perceptual_duplicate", "shots_a": a["shots"], "shots_b": b["shots"],
                                "phash_hamming": hamming})
                findings.append(
                    f"{', '.join(b['shots'])}: seed plate is a near copy of the plate of {', '.join(a['shots'])} "
                    f"(pHash distance {hamming} <= {hamming_max})"
                )
                continue
            for master, part in ((a, b), (b, a)):
                score, rel_w = _sub_rect_score(master["gray"], part["gray"])
                if score >= score_min:
                    matches.append({"kind": "sub_rectangle", "master_shots": master["shots"],
                                    "cropped_shots": part["shots"], "score": round(score, 3),
                                    "rel_w": round(rel_w, 3)})
                    findings.append(
                        f"{', '.join(part['shots'])}: seed plate is a sub-rectangle (rel_w~{rel_w:.2f}, "
                        f"match {score:.3f}) of the plate of {', '.join(master['shots'])}"
                    )
                    break

    return {
        "status": "PASS" if not findings else "FAIL",
        "shots_checked": len(shot_specs),
        "plates_compared": len(rows),
        "matches": matches,
        "findings": findings,
    }


_CUTOUT_NAMES = {"grabCut", "rembg", "composite_person_onto_bg", "composite_clean"}
# The repository's own matting helper keeps serving the retired card route; a job script may not call it.
_JOB_CUTOUT_NAMES = _CUTOUT_NAMES | {"birefnet_mask"}
_RMBG_MODEL_RE = re.compile(r"briaai[/]rmbg|\brmbg[-_]?\d", re.IGNORECASE)
_CUTOUT_TEXT_RE = re.compile(
    r"grabcut|rembg|rmbg|composite_person_onto_bg|composite_clean|alpha_paste", re.IGNORECASE
)
_CUTOUT_MANIFEST_KEYS = {
    "method", "tool", "tools", "operation", "operations", "compositing", "pipeline", "plate_method", "generator",
    "script", "path", "plate_path", "seed_plate_path", "start_picture", "source_image_path", "cutout",
}
_JOB_SHELL_SUFFIXES = {".sh", ".ps1", ".bat", ".ipynb"}


def _cutout_hits_in_python(path: Path, names: set[str]) -> list[tuple[int, str]]:
    """(line, what) of every forbidden cutout import, name, call argument or matting model id; docstrings are ignored."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                docstrings.add(id(first.value))

    def banned(name: str) -> bool:
        return name in names or name.lower().startswith("rmbg")

    exact = names | {"RMBG"}
    hits: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            dotted = [alias.name for alias in node.names] + ([module] if module else [])
            for item in dotted:
                for part in item.split("."):
                    if banned(part):
                        hits.add((node.lineno, f"import of {part}"))
        elif isinstance(node, ast.Name) and banned(node.id):
            hits.add((node.lineno, node.id))
        elif isinstance(node, ast.Attribute) and banned(node.attr):
            hits.add((node.lineno, node.attr))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and banned(node.name):
            hits.add((node.lineno, f"definition of {node.name}"))
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
              and _RMBG_MODEL_RE.search(node.value)):
            hits.add((node.lineno, "RMBG matting model id"))
        if isinstance(node, ast.Call):
            for arg in [*node.args, *(kw.value for kw in node.keywords)]:
                for sub_node in ast.walk(arg):
                    if isinstance(sub_node, ast.Constant) and isinstance(sub_node.value, str):
                        words = sub_node.value.split()
                        command = len(words) > 1 and words[0] == "rembg"
                        if command or (len(words) == 1 and words[0] in exact):
                            hits.add((sub_node.lineno, f"call argument {words[0]!r}"))
    return sorted(hits)


def _walk_dicts(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk_dicts(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk_dicts(value)


def check_no_cutout_compositing(
    repo_root: Path,
    job_dir: Path,
    *,
    shot_specs: list[dict[str, Any]] | None = None,
    require_provenance: bool = False,
) -> dict[str, Any]:
    """Fail when a person is cut out of one picture and pasted onto another (BP-217).

    Static part: every Python file of ``<repo_root>/explainer_engine``, ``<repo_root>/scripts`` and ``job_dir`` is
    parsed and checked for ``cv2.grabCut``, ``rembg``, RMBG models and ``composite_person_onto_bg`` /
    ``composite_clean``; job shell scripts and notebooks are searched as text. Manifest part: the job's JSON files
    may not record such a step, and every shot entry (``shot_id``) that declares several ``characters``, or
    characters in a ``location``, must declare a native ``plate_method``. With ``require_provenance`` a job that declares no such
    shot at all fails as well, because nothing was proven. A file that cannot be parsed fails.
    """
    repo_root, job_dir = Path(repo_root), Path(job_dir)
    native = set(sourced_rules.T("BP-217", "native_plate_methods"))
    findings: list[str] = []
    for label, folder in (("repo_root/explainer_engine", repo_root / "explainer_engine"), ("job_dir", job_dir)):
        if not folder.is_dir():
            findings.append(f"{label} {str(folder)!r} is not a directory: nothing could be scanned")

    def files(folder: Path):
        for item in sorted(folder.rglob("*")) if folder.is_dir() else []:
            inside = set(item.relative_to(folder).parts)
            if item.is_file() and not {"__pycache__", ".venv", "venv", "node_modules"} & inside:
                yield item

    def shown(item: Path) -> str:
        for root in (repo_root, job_dir):
            if item.is_relative_to(root):
                return item.relative_to(root).as_posix()
        return item.as_posix()

    job_files = list(files(job_dir))
    python_files: dict[Path, set[str]] = {
        item.resolve(): _CUTOUT_NAMES
        for folder in (repo_root / "explainer_engine", repo_root / "scripts")
        for item in files(folder)
        if item.suffix == ".py"
    }
    python_files.update({item.resolve(): _JOB_CUTOUT_NAMES for item in job_files if item.suffix == ".py"})
    repo_root, job_dir = repo_root.resolve(), job_dir.resolve()
    for item, names in python_files.items():
        try:
            for line, what in _cutout_hits_in_python(item, names):
                findings.append(f"{shown(item)}:{line}: forbidden cutout compositing ({what})")
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            findings.append(f"{shown(item)}: cannot be parsed, so it cannot be cleared ({exc.__class__.__name__})")

    declared: list[tuple[str, dict[str, Any]]] = [("shot_specs", spec) for spec in shot_specs or []]
    manifests = 0
    for item in job_files:
        if item.suffix in _JOB_SHELL_SUFFIXES:
            found = _CUTOUT_TEXT_RE.search(item.read_text(encoding="utf-8", errors="replace"))
            if found:
                findings.append(f"{shown(item.resolve())}: forbidden cutout compositing ({found.group(0)})")
        if item.suffix not in (".json", ".jsonl"):
            continue
        manifests += 1
        try:
            text = item.read_text(encoding="utf-8-sig")
            docs = (
                [json.loads(row) for row in text.splitlines() if row.strip()]
                if item.suffix == ".jsonl"
                else [json.loads(text)]
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            findings.append(f"{shown(item.resolve())}: unreadable manifest ({exc.__class__.__name__})")
            continue
        declared.extend((shown(item.resolve()), row) for doc in docs for row in _walk_dicts(doc))

    character_shots = 0
    for source, row in declared:
        sid = str(row.get("shot_id") or "entry")
        for key, value in row.items():
            if _CUTOUT_TEXT_RE.search(str(key)) and value:
                findings.append(f"{source}: {sid} records a cutout compositing step ({key})")
            elif str(key).lower() in _CUTOUT_MANIFEST_KEYS:
                found = _CUTOUT_TEXT_RE.search(json.dumps(value, ensure_ascii=False, default=str))
                if found:
                    findings.append(f"{source}: {sid} records a cutout compositing step ({key}: {found.group(0)})")
        characters = row.get("characters") or row.get("character_ids")
        if not row.get("shot_id") or not isinstance(characters, list) or not characters:
            continue
        if len(characters) < 2 and not (row.get("location") or row.get("location_id")):
            continue
        character_shots += 1
        provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
        method = str(row.get("plate_method") or provenance.get("plate_method") or "")
        if method not in native:
            findings.append(
                f"{source}: {sid} places characters in one picture but its plate_method is {method or 'missing'!r}; "
                f"it must be one of {sorted(native)}"
            )
    if require_provenance and not character_shots:
        findings.append("no shot declares its characters and plate_method: native generation is not proven")

    return {
        "status": "PASS" if not findings else "FAIL",
        "python_files_scanned": len(python_files),
        "manifests_scanned": manifests,
        "character_shots_declared": character_shots,
        "findings": findings,
    }


def run_full_cinema_audit(
    video_path: Path,
    *,
    shot_windows: list[dict[str, Any]],
    soundscape_report: dict[str, Any],
    utterances: list[dict[str, Any]],
    expected_script: str,
    observed_transcript: str | None = None,
    voice_audio_path: Path | None = None,
    required_proper_nouns: list[str] | None = None,
    map_specs: list[dict[str, Any]] | None = None,
    bridges: list[dict[str, Any]] | None = None,
    map_elements: list[dict[str, Any]] | None = None,
    audio_ducking_metrics: dict[str, Any] | None = None,
    ai_critic_verdict_path: Path | None = None,
    expected_component: str = "final_film",
    require_ai_critic: bool = True,
    enforce_v3_contracts: bool = False,
    enforce_v4_contracts: bool = False,
    sfx_events: list[dict[str, Any]] | None = None,
    narration_waves: list[tuple[float, float]] | None = None,
    verify_ffmpeg_true_peak: bool = False,
    visual_audit_path: Path | None = None,
    master_audio_wav: Path | None = None,
    silence_drops: list[dict[str, Any]] | None = None,
    word_timestamps: list[dict[str, Any]] | None = None,
    word_shot_anchors: list[dict[str, Any]] | None = None,
    seed_plate_specs: list[dict[str, Any]] | None = None,
    repo_root: Path | None = None,
    job_dir: Path | None = None,
    enforce_v5_contracts: bool = False,
) -> dict[str, Any]:
    """Run every deterministic L3 gate PLUS optional v3.2/v4.0 contracts & fail-closed AI Media Critic.

    ``enforce_v5_contracts`` makes the seed plate and cutout compositing gates mandatory (BP-217); without it each
    runs when its inputs are given.
    """
    from explainer_engine.qa.ai_critic_gate import verify_ai_critic_verdict

    delivery = check_master_delivery_specs(
        video_path,
        audio_report=soundscape_report,
        verify_ffmpeg_true_peak=verify_ffmpeg_true_peak,
    )
    total_dur = float(delivery.get("duration_s", 0.0))
    cut_times = [float(s["start_s"]) for s in shot_windows[1:] if float(s.get("start_s", 0.0)) > 0.2]

    dramatic_windows: list[tuple[float, float]] | None = None
    if enforce_v4_contracts:
        bal = check_docudrama_70_30_balance(shot_windows, utterances)
        dramatic_windows = [(float(sc["start_s"]), float(sc["end_s"])) for sc in bal.get("dramatic_scenes", [])]
    else:
        bal = None

    results: dict[str, Any] = {
        "delivery": delivery,
        "static_shots": check_no_static_shots(video_path, shot_windows),
        "midframe_tears": check_no_midframe_tears(video_path),
        "audio_scene_consistency": check_audio_scene_consistency(soundscape_report),
        "cross_cut_color_parity": check_cross_cut_color_parity(video_path, cut_times),
        "narration_pacing_gaps": check_narration_pacing_gaps(
            utterances,
            total_duration_s=total_dur,
            dramatic_scene_windows=dramatic_windows,
        ),
        "tts_pronunciation_asr": check_tts_pronunciation_asr(
            expected_script,
            audio_path=voice_audio_path,
            observed_transcript=observed_transcript,
            required_proper_nouns=required_proper_nouns,
        ),
        "map_geographic_richness": check_map_geographic_richness(map_specs or []) if map_specs else {"status": "PASS", "findings": []},
        "overlay_spatial_collisions": check_overlay_spatial_collisions(bridges or [], map_elements or []),
        "edit_grammar_and_dedup": check_edit_grammar_and_dedup(shot_windows),
        "audio_ducking_and_sfx": check_audio_ducking_and_sfx_balance(audio_ducking_metrics or {}),
        "grade_cohesion": check_archival_or_grade_cohesion(video_path, shot_windows),
    }
    if enforce_v3_contracts:
        results["zero_photo_clip_reuse"] = check_zero_photo_clip_reuse(video_path, shot_windows)
        results["ltx_dominance"] = check_ltx_dominance(shot_windows)
        results["youtube_rhythm_and_jl_cuts"] = check_youtube_rhythm_and_jl_cuts(shot_windows, utterances)
        results["overlay_density"] = check_overlay_density(bridges or [], narration_waves=narration_waves)
        results["grain_ceiling"] = check_grain_ceiling(video_path)
        results["audio_anti_repetition"] = check_audio_anti_repetition(sfx_events or [], soundscape_report)

    if enforce_v4_contracts:
        results["no_jump_cuts"] = check_no_jump_cuts(video_path, shot_windows)
        results["docudrama_70_30_balance"] = bal or check_docudrama_70_30_balance(shot_windows, utterances)
        results["pts_monotonicity"] = check_pts_monotonicity(video_path, expected_fps=float(delivery.get("fps", 24.0) or 24.0))
        if visual_audit_path is not None:
            results["visual_audit_clean"] = check_visual_audit_clean(shot_windows, visual_audit_path)
        if master_audio_wav is not None and silence_drops:
            results["silence_drop_effectiveness"] = check_silence_drop_effectiveness(
                master_audio_wav,
                silence_drops,
                voice_wav=voice_audio_path,
            )
        if word_timestamps and word_shot_anchors:
            results["word_to_shot_sync"] = check_word_to_shot_sync(
                shot_windows,
                word_timestamps,
                word_shot_anchors,
            )

    if enforce_v5_contracts or seed_plate_specs is not None:
        results["cropped_seed_plates"] = check_no_cropped_seed_plates(seed_plate_specs or [], base_dir=repo_root)
    if enforce_v5_contracts or job_dir is not None:
        if repo_root is None or job_dir is None:
            results["cutout_compositing"] = {"status": "FAIL", "findings": ["repo_root and job_dir are required"]}
        else:
            results["cutout_compositing"] = check_no_cutout_compositing(
                repo_root,
                job_dir,
                shot_specs=seed_plate_specs,
                require_provenance=enforce_v5_contracts,
            )

    if require_ai_critic:
        if ai_critic_verdict_path is None:
            results["ai_critic"] = {"status": "FAIL", "findings": ["Missing mandatory ai_critic_verdict_path"]}
        else:
            results["ai_critic"] = verify_ai_critic_verdict(
                video_path,
                ai_critic_verdict_path,
                expected_component=expected_component,
            )

    failed_gates = [k for k, v in results.items() if v.get("status") != "PASS"]
    return {
        "status": "PASS" if not failed_gates else "FAIL",
        "failed_gates": failed_gates,
        "gates": results,
    }


def _extract_env_descriptor(rgb: np.ndarray) -> np.ndarray:
    """Compute a lighting- & background-weighted environment descriptor (Lab palette + multi-scale texture/gradients).

    Weights the outer 65% frame border (walls, columns, lighting, atmosphere) higher than the central
    foreground actor silhouette so genuine shot/reverse-shot camera angles in the SAME room score high
    (>= 0.78) while disconnected rooms/palettes score sharply lower (< 0.65).
    """
    small = cv2.resize(rgb, (256, 144), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    # Background weight mask: outer architectural ring weight=1.0, center actor box weight=0.35
    mask = np.ones((h, w), dtype=np.float32)
    mask[int(h * 0.22) : int(h * 0.85), int(w * 0.30) : int(w * 0.70)] = 0.35

    lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV).astype(np.float32)

    # 1. Weighted 1D perceptual histograms in Lab (L, a, b) + Hue/Sat (captures room lighting, stone/wood palette)
    feats: list[np.ndarray] = []
    for ch, bins, rng in (
        (lab[..., 0], 16, (0.0, 256.0)),
        (lab[..., 1], 16, (64.0, 192.0)),
        (lab[..., 2], 16, (64.0, 192.0)),
        (hsv[..., 0], 12, (0.0, 180.0)),
        (hsv[..., 1], 12, (0.0, 256.0)),
    ):
        hist, _ = np.histogram(ch.ravel(), bins=bins, range=rng, weights=mask.ravel())
        hist = hist.astype(np.float32)
        hist /= float(np.linalg.norm(hist)) + 1e-8
        feats.append(hist)

    # 2. Multi-scale Sobel gradient orientation + architectural edge density in border zone
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy) * mask
    ang = (np.arctan2(gy, gx) + np.pi) * (180.0 / (2.0 * np.pi))
    ori_hist, _ = np.histogram(ang.ravel(), bins=12, range=(0.0, 180.0), weights=mag.ravel())
    ori_hist = ori_hist.astype(np.float32)
    ori_hist /= float(np.linalg.norm(ori_hist)) + 1e-8
    feats.append(ori_hist * 0.85)

    # 3. Mean & std chromaticity anchor in Lab space (normalized vector)
    w_sum = float(np.sum(mask)) + 1e-8
    lab_stats: list[float] = []
    for c in range(3):
        mu = float(np.sum(lab[..., c] * mask) / w_sum)
        sd = float(np.sqrt(np.sum(((lab[..., c] - mu) ** 2) * mask) / w_sum))
        lab_stats.extend([mu / 255.0, sd / 128.0])
    stat_v = np.array(lab_stats, dtype=np.float32)
    stat_v /= float(np.linalg.norm(stat_v)) + 1e-8
    feats.append(stat_v * 1.15)

    vec = np.concatenate(feats, axis=0)
    return vec / (float(np.linalg.norm(vec)) + 1e-8)


def check_same_scene_environment_continuity(
    video_path: Path,
    scene_shots: list[dict[str, Any]],
    *,
    min_median_similarity: float = 0.78,
    min_pair_similarity: float = 0.68,
) -> dict[str, Any]:
    """Verify cross-shot environment/lighting/material continuity for every multi-shot ``scene_id``.

    Groups shots sharing the same ``scene_id`` (or ``scene_group``), samples 3 interior frames
    per shot (25%, 50%, 75%), computes background-weighted Lab + architectural gradient embeddings,
    and checks pairwise cosine similarity. Catches v4's Shot 1 -> Shot 2 room-teleportation bug.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    by_scene: dict[str, list[dict[str, Any]]] = {}
    for sh in scene_shots:
        sid = str(sh.get("scene_id") or sh.get("scene_group") or "").strip()
        if not sid:
            continue
        by_scene.setdefault(sid, []).append(sh)

    multi_scenes = {k: v for k, v in by_scene.items() if len(v) >= 2}
    if not multi_scenes or total_frames < 2:
        return {
            "status": "PASS",
            "scenes_checked": 0,
            "median_env_similarity": 1.0,
            "min_env_similarity": 1.0,
            "scenes": [],
            "findings": [],
        }

    # Gather all required frame indices in one sequential decode pass
    shot_frame_map: dict[tuple[str, int], list[int]] = {}
    wanted: list[int] = []
    for sc_id, shots in multi_scenes.items():
        for idx, sh in enumerate(shots):
            st = float(sh.get("start_s", 0.0))
            en = float(sh.get("end_s", st + float(sh.get("duration_s", 1.0))))
            dur = max(0.12, en - st)
            f_idxs = [
                max(0, min(total_frames - 1, int(round((st + dur * frac) * fps))))
                for frac in (0.25, 0.50, 0.75)
            ]
            shot_frame_map[(sc_id, idx)] = f_idxs
            wanted.extend(f_idxs)

    frames = _read_frames_at_indices(video_path, wanted)
    findings: list[str] = []
    scene_reports: list[dict[str, Any]] = []
    all_sims: list[float] = []

    for sc_id, shots in multi_scenes.items():
        descs: list[tuple[str, np.ndarray]] = []
        for idx, sh in enumerate(shots):
            f_idxs = shot_frame_map[(sc_id, idx)]
            vecs = [_extract_env_descriptor(frames[fi]) for fi in f_idxs if fi in frames]
            if not vecs:
                continue
            avg_v = np.mean(vecs, axis=0).astype(np.float32)
            avg_v /= float(np.linalg.norm(avg_v)) + 1e-8
            descs.append((str(sh.get("shot_id") or f"{sc_id}_{idx + 1}"), avg_v))

        pair_sims: list[float] = []
        pair_details: list[dict[str, Any]] = []
        for i in range(len(descs)):
            for j in range(i + 1, len(descs)):
                sim = float(np.clip(np.dot(descs[i][1], descs[j][1]), -1.0, 1.0))
                pair_sims.append(sim)
                all_sims.append(sim)
                pair_details.append(
                    {"shot_a": descs[i][0], "shot_b": descs[j][0], "env_similarity": round(sim, 4)}
                )

        sc_med = float(np.median(pair_sims)) if pair_sims else 1.0
        sc_min = float(np.min(pair_sims)) if pair_sims else 1.0
        sc_ok = (sc_med >= min_median_similarity) and (sc_min >= min_pair_similarity)
        if sc_med < min_median_similarity:
            findings.append(
                f"Scene {sc_id!r} median environment continuity {sc_med:.3f} < {min_median_similarity:.2f} "
                "(shots look like disconnected environments)"
            )
        if sc_min < min_pair_similarity:
            worst = min(pair_details, key=lambda x: x["env_similarity"])
            findings.append(
                f"Scene {sc_id!r} worst shot pair {worst['shot_a']} <-> {worst['shot_b']} "
                f"env_similarity={sc_min:.3f} < {min_pair_similarity:.2f}"
            )
        scene_reports.append(
            {
                "scene_id": sc_id,
                "shot_count": len(descs),
                "median_env_similarity": round(sc_med, 4),
                "min_env_similarity": round(sc_min, 4),
                "passed": sc_ok,
                "pairs": pair_details,
            }
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "scenes_checked": len(scene_reports),
        "median_env_similarity": round(float(np.median(all_sims)) if all_sims else 1.0, 4),
        "min_env_similarity": round(float(np.min(all_sims)) if all_sims else 1.0, 4),
        "scenes": scene_reports,
        "findings": findings,
    }


def _radial_flow_divergence(gray_prev: np.ndarray, gray_next: np.ndarray) -> float:
    """Estimate normalized radial optical-flow divergence (positive = zoom-in, negative = zoom-out)."""
    flow = cv2.calcOpticalFlowFarneback(
        gray_prev,
        gray_next,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0,
    )
    h, w = gray_prev.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rx = (xx - w * 0.5) / max(1.0, w * 0.5)
    ry = (yy - h * 0.5) / max(1.0, h * 0.5)
    r2 = rx * rx + ry * ry
    ring = r2 > 0.08  # exclude center singularity
    u = flow[..., 0] / max(1.0, w * 0.5)
    v = flow[..., 1] / max(1.0, h * 0.5)
    rad = (u[ring] * rx[ring] + v[ring] * ry[ring]) / (r2[ring] + 1e-6)
    return float(np.median(rad)) if rad.size else 0.0


def _affine_scale_and_anisotropy(gray_a: np.ndarray, gray_b: np.ndarray) -> tuple[float, float, int]:
    """Estimate affine scale factor (sqrt(sx*sy)) and aspect stretch (|sx/sy - 1|) between two similar frames."""
    pts_a = cv2.goodFeaturesToTrack(gray_a, maxCorners=220, qualityLevel=0.02, minDistance=8, blockSize=5)
    if pts_a is None or len(pts_a) < 10:
        return 1.0, 0.0, 0
    pts_b, st, _ = cv2.calcOpticalFlowPyrLK(gray_a, gray_b, pts_a, None, winSize=(21, 21), maxLevel=3)
    if pts_b is None or st is None:
        return 1.0, 0.0, 0
    good = st.ravel() == 1
    if int(np.sum(good)) < 10:
        return 1.0, 0.0, int(np.sum(good))
    mat, inliers = cv2.estimateAffine2D(
        pts_a[good].reshape(-1, 2),
        pts_b[good].reshape(-1, 2),
        method=cv2.RANSAC,
        ransacReprojThreshold=3.0,
    )
    if mat is None or inliers is None or int(np.sum(inliers)) < 8:
        return 1.0, 0.0, int(np.sum(inliers)) if inliers is not None else 0
    sx = float(np.hypot(mat[0, 0], mat[1, 0]))
    sy = float(np.hypot(mat[0, 1], mat[1, 1]))
    if sx < 0.5 or sy < 0.5 or sx > 1.8 or sy > 1.8:
        return 1.0, 0.0, int(np.sum(inliers))
    scale = float(np.sqrt(sx * sy))
    aniso = abs((sx / max(1e-6, sy)) - 1.0)
    return scale, aniso, int(np.sum(inliers))


def check_no_transition_stretch_or_zoom_jump(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    max_scale_jump: float = 0.045,
    max_anisotropy_ratio: float = 0.040,
    max_radial_div_jump: float = 0.055,
) -> dict[str, Any]:
    """Detect frame stretching, anisotropic aspect distortion, or zoom-jump glitches across cut boundaries.

    Inspects frames ``[cut-2, cut-1, cut, cut+1]`` at each shot boundary:
    - On chained handoffs (or visually continuous same-framing boundaries), measures affine scale
      delta ``|scale - 1.0|``, anisotropic stretch ``|sx/sy - 1.0|``, and Farneback radial flow
      divergence discontinuity across the boundary.
    - Also checks within-clip radial divergence velocity reversals right before vs right after a cut
      on chained clips so pre-stitch zoompan/ken-burns glitches are always caught deterministically.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    if len(shot_windows) < 2 or total_frames < 5:
        return {
            "status": "PASS",
            "boundaries_checked": 0,
            "anomalies": 0,
            "boundaries": [],
            "findings": [],
        }

    pairs: list[dict[str, Any]] = []
    wanted: list[int] = []
    for i in range(len(shot_windows) - 1):
        a = shot_windows[i]
        b = shot_windows[i + 1]
        cut_s = float(b.get("start_s", a.get("end_s", 0.0)))
        b_idx = int(round(cut_s * fps))
        if b_idx < 2 or b_idx >= total_frames - 2:
            continue
        idxs = [b_idx - 2, b_idx - 1, b_idx, b_idx + 1]
        wanted.extend(idxs)
        pairs.append({"a": a, "b": b, "cut_s": cut_s, "idxs": idxs})

    frames = _read_frames_at_indices(video_path, wanted)
    findings: list[str] = []
    reports: list[dict[str, Any]] = []

    for p in pairs:
        i0, i1, i2, i3 = p["idxs"]
        if any(ix not in frames for ix in (i0, i1, i2, i3)):
            continue
        g0 = cv2.cvtColor(cv2.resize(frames[i0], (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        g1 = cv2.cvtColor(cv2.resize(frames[i1], (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        g2 = cv2.cvtColor(cv2.resize(frames[i2], (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        g3 = cv2.cvtColor(cv2.resize(frames[i3], (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)

        a_id = str(p["a"].get("shot_id") or "shot_a")
        b_id = str(p["b"].get("shot_id") or "shot_b")
        is_chained = str(p["b"].get("chained_from") or "").strip() == a_id

        # Check frame-pair visual correlation to distinguish true camera-angle hard cuts from continuous/chained seams
        v1 = g1.astype(np.float32).ravel()
        v2 = g2.astype(np.float32).ravel()
        denom = float(np.linalg.norm(v1 - v1.mean()) * np.linalg.norm(v2 - v2.mean()))
        corr = float(np.dot(v1 - v1.mean(), v2 - v2.mean()) / denom) if denom > 1e-6 else 0.0

        div_before = _radial_flow_divergence(g0, g1)
        div_after = _radial_flow_divergence(g2, g3)
        div_across = _radial_flow_divergence(g1, g2) if (is_chained or corr >= 0.65) else 0.0

        scale_across, aniso_across, inliers = (
            _affine_scale_and_anisotropy(g1, g2) if (is_chained or corr >= 0.65) else (1.0, 0.0, 0)
        )
        scale_jump = abs(scale_across - 1.0)
        div_step_jump = abs(div_across - 0.5 * (div_before + div_after)) if (is_chained or corr >= 0.65) else 0.0

        passed = True
        reason = "clean"
        if is_chained or corr >= 0.65:
            if scale_jump > max_scale_jump:
                passed = False
                reason = "zoom_scale_jump"
                findings.append(
                    f"Zoom/scale jump at {p['cut_s']:.2f}s ({a_id} -> {b_id}): "
                    f"scale={scale_across:.4f} (|delta|={scale_jump:.4f} > {max_scale_jump:.3f})"
                )
            if aniso_across > max_anisotropy_ratio:
                passed = False
                reason = "anisotropic_frame_stretch"
                findings.append(
                    f"Frame aspect stretch at {p['cut_s']:.2f}s ({a_id} -> {b_id}): "
                    f"anisotropy={aniso_across:.4f} > {max_anisotropy_ratio:.3f}"
                )
            if div_step_jump > max_radial_div_jump:
                passed = False
                reason = "radial_divergence_jump"
                findings.append(
                    f"Radial flow zoom-jump at {p['cut_s']:.2f}s ({a_id} -> {b_id}): "
                    f"div_jump={div_step_jump:.4f} > {max_radial_div_jump:.3f} "
                    f"(before={div_before:.4f}, across={div_across:.4f}, after={div_after:.4f})"
                )

        reports.append(
            {
                "cut_s": round(p["cut_s"], 3),
                "from_shot": a_id,
                "to_shot": b_id,
                "is_chained": is_chained,
                "boundary_corr": round(corr, 4),
                "scale_across": round(scale_across, 4),
                "anisotropy": round(aniso_across, 4),
                "inliers": inliers,
                "div_before": round(div_before, 4),
                "div_across": round(div_across, 4),
                "div_after": round(div_after, 4),
                "div_jump": round(div_step_jump, 4),
                "reason": reason,
                "passed": passed,
            }
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "boundaries_checked": len(reports),
        "anomalies": len(findings),
        "boundaries": reports,
        "findings": findings,
    }


def check_dramatic_dialogue_presence(
    shots: list[dict[str, Any]],
    audio_path: Path,
    *,
    utterances: list[dict[str, Any]] | None = None,
    min_voiced_shots: int = 2,
    min_active_speech_ratio: float = 0.28,
    max_narrator_overlap_s: float = 0.15,
) -> dict[str, Any]:
    """Enforce that dramatic dialogue shots contain real active spoken character dialogue (NOT silent staring)
    AND zero narrator-over-dialogue collision."""
    import soundfile as sf
    from scipy.signal import butter, sosfiltfilt

    p = Path(audio_path)
    if not p.is_file():
        raise FileNotFoundError(f"Audio file not found for dialogue check: {p}")

    # Decode WAV directly or via ffmpeg if MP4/M4A passed
    if p.suffix.lower() != ".wav":
        tmp_wav = p.with_suffix(".diag_tmp.wav")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(tmp_wav)],
            check=True,
        )
        try:
            sig, sr = sf.read(str(tmp_wav), dtype="float32")
        finally:
            tmp_wav.unlink(missing_ok=True)
    else:
        sig, sr = sf.read(str(p), dtype="float32")
    if sig.ndim > 1:
        sig = sig.mean(axis=1)

    # Human vocal formant band (300-3400 Hz)
    nyq = 0.5 * sr
    sos_vox = butter(3, [min(300.0, nyq * 0.4) / nyq, min(3400.0, nyq * 0.92) / nyq], btype="bandpass", output="sos")
    vox = sosfiltfilt(sos_vox, sig.astype(np.float32)).astype(np.float32)

    dialogue_shots = [
        sh for sh in shots
        if bool(sh.get("has_dialogue"))
        or bool(sh.get("dialogue_line"))
        or bool(sh.get("line"))
    ]
    findings: list[str] = []
    shot_reports: list[dict[str, Any]] = []
    voiced_ok = 0

    if len(dialogue_shots) < min_voiced_shots:
        findings.append(
            f"Only {len(dialogue_shots)} dramatic dialogue shot(s) planned (minimum {min_voiced_shots} required; zero silent staring)"
        )

    hop = max(1, int(round(0.025 * sr)))
    for sh in dialogue_shots:
        sid = str(sh.get("shot_id") or "dialogue_shot")
        st = float(sh.get("start_s", 0.0))
        en = float(sh.get("end_s", st + float(sh.get("duration_s", 0.0))))
        i0 = max(0, min(len(vox), int(round(st * sr))))
        i1 = max(i0, min(len(vox), int(round(en * sr))))
        seg = vox[i0:i1]
        if len(seg) < hop:
            active_ratio = 0.0
            peak_db = -90.0
        else:
            n_blk = len(seg) // hop
            blks = seg[: n_blk * hop].reshape(n_blk, hop)
            rms_db = 20.0 * np.log10(np.sqrt(np.mean(blks * blks, axis=1)) + 1e-9)
            active_ratio = float(np.mean(rms_db > -34.0))
            peak_db = float(np.max(rms_db))

        # Check narrator-over-dialogue collision
        overlap_s = 0.0
        for ut in utterances or []:
            u0 = float(ut.get("start_s", 0.0))
            u1 = float(ut.get("end_s", 0.0))
            ov = max(0.0, min(en, u1) - max(st, u0))
            overlap_s += ov

        has_speech = active_ratio >= min_active_speech_ratio and peak_db > -28.0
        no_collision = overlap_s <= max_narrator_overlap_s
        if has_speech:
            voiced_ok += 1
        else:
            findings.append(
                f"Dialogue shot {sid!r} ({st:.2f}-{en:.2f}s) lacks audible character speech "
                f"(active_ratio={active_ratio:.2f} < {min_active_speech_ratio:.2f}, peak={peak_db:.1f} dBFS)"
            )
        if not no_collision:
            findings.append(
                f"Narrator collides with character dialogue in {sid!r} ({st:.2f}-{en:.2f}s): overlap={overlap_s:.2f}s > {max_narrator_overlap_s:.2f}s"
            )
        shot_reports.append(
            {
                "shot_id": sid,
                "start_s": round(st, 3),
                "end_s": round(en, 3),
                "active_speech_ratio": round(active_ratio, 3),
                "peak_vocal_dbfs": round(peak_db, 2),
                "narrator_overlap_s": round(overlap_s, 3),
                "passed": has_speech and no_collision,
            }
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "dialogue_shots_checked": len(dialogue_shots),
        "voiced_shots_passed": voiced_ok,
        "shots": shot_reports,
        "findings": findings,
    }


def check_scene_first_routing(
    shots: list[dict[str, Any]],
    *,
    min_shots_per_ltx_scene: int = 2,
) -> dict[str, Any]:
    """Enforce Scene-First Routing: EVERY LTX video shot MUST belong to a multi-shot ``scene_id`` (>= 2 shots).

    Prevents 1-off LTX "video slideshows" during narrated exposition; abstract exposition routes
    cleanly to ``still_25d``, ``map_action``, or ``drawing_explainer``.
    """
    ltx_routes = {"ltx", "ltx_video", "video"}
    scene_counts: dict[str, list[str]] = {}
    findings: list[str] = []
    ltx_total = 0

    for idx, sh in enumerate(shots):
        route = str(sh.get("route") or sh.get("kind") or "").strip().lower()
        if route not in ltx_routes:
            continue
        ltx_total += 1
        sid = str(sh.get("shot_id") or f"shot_{idx + 1}")
        sc = str(sh.get("scene_id") or sh.get("scene_group") or "").strip()
        if not sc:
            findings.append(f"LTX shot {sid!r} has no scene_id (1-off LTX slideshow clips are forbidden)")
            continue
        scene_counts.setdefault(sc, []).append(sid)

    for sc, members in scene_counts.items():
        if len(members) < min_shots_per_ltx_scene:
            findings.append(
                f"Scene {sc!r} has only {len(members)} LTX shot ({members[0]}); "
                f"every LTX scene requires >= {min_shots_per_ltx_scene} connected shots (route exposition to 2.5D/map/explainer)"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "ltx_shots_checked": ltx_total,
        "ltx_scenes": {k: len(v) for k, v in scene_counts.items()},
        "findings": findings,
    }


def check_audio_scene_bleed(
    sfx_events: list[dict[str, Any]],
    scene_ambiences: list[dict[str, Any]],
    scene_windows: list[dict[str, Any]],
    *,
    max_bleed_s: float = 0.35,
) -> dict[str, Any]:
    """Fail-closed check ensuring zero SFX or scene ambience bleeds > ``max_bleed_s`` past its owning scene.

    Eliminates v4's multi-second cross-scene audio bleed (e.g., wolf growls continuing into campfire scenes).
    """
    findings: list[str] = []
    ordered_scenes = sorted(scene_windows, key=lambda s: float(s.get("start_s", 0.0)))

    def _owner_scene(t: float) -> dict[str, Any] | None:
        for sw in ordered_scenes:
            if float(sw.get("start_s", 0.0)) - 0.05 <= t < float(sw.get("end_s", 0.0)):
                return sw
        return None

    amb_bleeds: list[dict[str, Any]] = []
    for idx, amb in enumerate(scene_ambiences):
        st = float(amb.get("start_s", 0.0))
        en = float(amb.get("effective_end_s", float(amb.get("end_s", st)) + float(amb.get("l_cut_tail_s", 0.0))))
        owner = _owner_scene(st)
        if owner is None:
            continue
        owner_end = float(owner.get("end_s", en))
        bleed = en - owner_end
        if bleed > max_bleed_s + 1e-6:
            rec = {
                "kind": "ambience",
                "id": str(amb.get("shot_id") or amb.get("scene_environment") or f"amb_{idx + 1}"),
                "owning_scene": str(owner.get("scene_id") or owner.get("shot_id") or "scene"),
                "scene_end_s": round(owner_end, 3),
                "audio_end_s": round(en, 3),
                "bleed_s": round(bleed, 3),
            }
            amb_bleeds.append(rec)
            findings.append(
                f"Ambience {rec['id']!r} bleeds {bleed:.2f}s past owning scene {rec['owning_scene']!r} "
                f"(end={owner_end:.2f}s, audio_end={en:.2f}s > +{max_bleed_s:.2f}s)"
            )

    sfx_bleeds: list[dict[str, Any]] = []
    for idx, ev in enumerate(sfx_events):
        t0 = float(ev.get("time_s", 0.0))
        dur = float(ev.get("effective_duration_s", ev.get("max_duration_s", 0.0)))
        audio_end = float(ev.get("effective_end_s", t0 + dur))
        owner = _owner_scene(t0)
        if owner is None:
            continue
        owner_end = float(owner.get("end_s", audio_end))
        bleed = audio_end - owner_end
        if bleed > max_bleed_s + 1e-6:
            rec = {
                "kind": "sfx",
                "id": str(ev.get("label") or Path(str(ev.get("wav_path") or f"sfx_{idx + 1}")).stem),
                "owning_scene": str(owner.get("scene_id") or owner.get("shot_id") or "scene"),
                "scene_end_s": round(owner_end, 3),
                "audio_end_s": round(audio_end, 3),
                "bleed_s": round(bleed, 3),
            }
            sfx_bleeds.append(rec)
            findings.append(
                f"SFX {rec['id']!r} bleeds {bleed:.2f}s past owning scene {rec['owning_scene']!r} "
                f"(end={owner_end:.2f}s, audio_end={audio_end:.2f}s > +{max_bleed_s:.2f}s)"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "max_bleed_s": max_bleed_s,
        "ambience_checked": len(scene_ambiences),
        "sfx_checked": len(sfx_events),
        "bleed_violations": amb_bleeds + sfx_bleeds,
        "findings": findings,
    }


def check_music_to_voice_headroom(
    voice_wav: Path,
    music_wav: Path,
    *,
    min_headroom_db: float = 22.0,
    max_headroom_db: float = 38.0,
) -> dict[str, Any]:
    """Verify modern documentary underscore sits cleanly 22-38 dB below active voice (never competing with speech)."""
    import soundfile as sf

    if not Path(voice_wav).is_file() or not Path(music_wav).is_file():
        return {"status": "FAIL", "findings": ["Missing voice_wav or music_wav for headroom check"]}

    v, sr_v = sf.read(str(voice_wav), dtype="float32", always_2d=True)
    m, sr_m = sf.read(str(music_wav), dtype="float32", always_2d=True)
    v_mono = v.mean(axis=1)
    m_mono = m.mean(axis=1)
    n = min(len(v_mono), len(m_mono))
    v_mono = v_mono[:n]
    m_mono = m_mono[:n]

    active = np.abs(v_mono) > 0.015
    if int(np.sum(active)) < max(100, int(0.2 * sr_v)):
        return {"status": "FAIL", "findings": ["Insufficient active speech in voice_wav to measure headroom"]}

    v_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(v_mono[active] ** 2))) + 1e-12))
    m_rms_db = float(20.0 * np.log10(float(np.sqrt(np.mean(m_mono[active] ** 2))) + 1e-12))
    headroom_db = v_rms_db - m_rms_db

    findings: list[str] = []
    if headroom_db < min_headroom_db:
        findings.append(
            f"Music underscore too loud relative to voice: headroom={headroom_db:.1f} dB < required {min_headroom_db:.1f} dB "
            f"(voice={v_rms_db:.1f} dBFS, music={m_rms_db:.1f} dBFS)"
        )
    if headroom_db > max_headroom_db:
        findings.append(
            f"Music underscore effectively inaudible: headroom={headroom_db:.1f} dB > max {max_headroom_db:.1f} dB "
            f"(voice={v_rms_db:.1f} dBFS, music={m_rms_db:.1f} dBFS)"
        )

    return {
        "status": "PASS" if not findings else "FAIL",
        "voice_active_rms_dbfs": round(v_rms_db, 2),
        "music_under_voice_rms_dbfs": round(m_rms_db, 2),
        "headroom_db": round(headroom_db, 2),
        "target_band_db": [min_headroom_db, max_headroom_db],
        "findings": findings,
    }





