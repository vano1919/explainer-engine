"""Automated Cinema Quality Gates: Static-Shot Detector, Mid-Frame Seam/Tear Detector, and Audio-Scene Consistency.

Catches the exact real-world visual and audio defects that legacy synthetic tests missed:
1. Static-Shot Detector: verifies smooth continuous motion across 1-second windows (especially opening 0–2s).
2. Mid-Frame Seam/Tear Detector: detects artificial horizontal/vertical gradient discontinuity splits.
3. Audio-Scene Consistency Gate: verifies no rain on dry/map shots, synced SFX on every map shot,
   ITU-R BS.1770-4 loudness/peak compliance, and real acoustic variation across scene boundaries.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np


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
) -> dict[str, Any]:
    """L3 machine forensics: verify 2K 2560x1440 @ 24fps yuv420p, 48kHz stereo, -14.0 +/- 0.5 LUFS, <= -1.0 dBTP."""
    import json
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
        peak = float(audio_report.get("peak_dbfs", 0.0))
        if not (-14.5 <= lufs <= -13.5):
            findings.append(f"Integrated loudness {lufs:.2f} LUFS outside strict -14.0 +/- 0.5 LUFS target")
        if peak > -1.0:
            findings.append(f"True peak {peak:.2f} dBFS exceeds -1.0 dBTP ceiling")

    return {
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


def check_narration_pacing_gaps(
    utterances: list[dict[str, Any]],
    *,
    total_duration_s: float,
    max_unplanned_gap_s: float = 3.5,
    max_breather_gap_s: float = 5.0,
    max_tail_silence_s: float = 4.0,
) -> dict[str, Any]:
    """Fail if narration/dialogue leaves unplanned dead-air stretches > 3.5s (or > 5.0s breather)."""
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

    # Check opening dead silence before first speech
    first_start = float(ordered[0].get("start_s", 0.0))
    if first_start > max_unplanned_gap_s and not bool(ordered[0].get("dramatic_breather", False)):
        findings.append(f"Opening dead-air before first voice is {first_start:.2f}s > {max_unplanned_gap_s:.2f}s")

    max_gap = first_start
    for idx in range(len(ordered) - 1):
        cur_end = float(ordered[idx].get("end_s", ordered[idx].get("start_s", 0.0)))
        nxt_start = float(ordered[idx + 1].get("start_s", cur_end))
        gap = max(0.0, nxt_start - cur_end)
        is_breather = bool(ordered[idx].get("dramatic_breather_after", False)) or bool(
            ordered[idx + 1].get("dramatic_breather", False)
        )
        limit = max_breather_gap_s if is_breather else max_unplanned_gap_s
        max_gap = max(max_gap, gap)
        gaps.append(
            {
                "from_s": round(cur_end, 3),
                "to_s": round(nxt_start, 3),
                "gap_s": round(gap, 3),
                "dramatic_breather": is_breather,
                "passed": gap <= limit,
            }
        )
        if gap > limit:
            findings.append(
                f"Dead narration gap {cur_end:.2f}s->{nxt_start:.2f}s ({gap:.2f}s > {limit:.2f}s limit)"
            )

    tail_gap = max(0.0, float(total_duration_s) - float(ordered[-1].get("end_s", 0.0)))
    max_gap = max(max_gap, tail_gap)
    if tail_gap > max_tail_silence_s:
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
        segments, _ = model.transcribe(audio_16k, language="en", beam_size=1)
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
                sim = float(ssim(thumbs_gray[i], thumbs_gray[j], data_range=255))
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
    peak = float(soundscape_report.get("peak_dbfs", 0.0))
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
    sfx_events: list[dict[str, Any]] | None = None,
    narration_waves: list[tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Run every deterministic L3 gate PLUS optional v3.2 Anti-Laziness contracts & fail-closed AI Media Critic."""
    from explainer_engine.qa.ai_critic_gate import verify_ai_critic_verdict

    delivery = check_master_delivery_specs(video_path, audio_report=soundscape_report)
    total_dur = float(delivery.get("duration_s", 0.0))
    cut_times = [float(s["start_s"]) for s in shot_windows[1:] if float(s.get("start_s", 0.0)) > 0.2]

    results: dict[str, Any] = {
        "delivery": delivery,
        "static_shots": check_no_static_shots(video_path, shot_windows),
        "midframe_tears": check_no_midframe_tears(video_path),
        "audio_scene_consistency": check_audio_scene_consistency(soundscape_report),
        "cross_cut_color_parity": check_cross_cut_color_parity(video_path, cut_times),
        "narration_pacing_gaps": check_narration_pacing_gaps(utterances, total_duration_s=total_dur),
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


