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
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frames: list[np.ndarray] = []
    try:
        for ts in times_s:
            idx = max(0, min(max(0, total - 1), int(round(ts * fps))))
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, bgr = cap.read()
            if ok and bgr is not None:
                frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    finally:
        cap.release()
    return frames


def check_no_static_shots(
    video_path: Path,
    shot_windows: list[dict[str, Any]],
    *,
    min_mean_abs_diff: float = 0.45,
) -> dict[str, Any]:
    """Fail if any 2.5D shot exhibits frozen/static motion (including opening 0–2s of Shot 1)."""
    findings: list[str] = []
    details: list[dict[str, Any]] = []
    for shot in shot_windows:
        if shot.get("kind", "25d") != "25d":
            continue
        st = float(shot["start_s"])
        en = float(shot["end_s"])
        dur = en - st
        if dur < 1.2:
            continue
        # Measure early window (0.15s -> 1.35s) and mid window
        t_samples = [st + 0.15, st + min(1.35, dur * 0.45), st + min(2.6, dur * 0.80)]
        frs = _read_frames_at_times(video_path, t_samples)
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
