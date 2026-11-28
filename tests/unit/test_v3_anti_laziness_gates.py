"""Regression tests for v3.2 Anti-Laziness deterministic gates, 5-persona viewer panel, and YouTube A/B lifecycle."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from explainer_engine.publish.youtube_ab_lifecycle import (
    analyze_pattern_interrupt_cadence,
    evaluate_paddy_galloway_matrix,
)
from explainer_engine.publish.youtube_ab_packaging import ThumbnailVariantSpec
from explainer_engine.qa.cinema_gates import (
    check_audio_anti_repetition,
    check_grain_ceiling,
    check_ltx_dominance,
    check_overlay_density,
    check_youtube_rhythm_and_jl_cuts,
    check_zero_photo_clip_reuse,
)
from explainer_engine.qa.youtube_viewer_simulator import verify_viewer_panel_report


def _write_test_video(path: Path, frames_rgb: list[np.ndarray], fps: int = 24) -> None:
    h, w = frames_rgb[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for fr in frames_rgb:
        vw.write(cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    vw.release()


def test_zero_photo_clip_reuse_fails_on_duplicate_image_and_passes_on_unique(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    f1 = np.zeros((180, 320, 3), dtype=np.uint8)
    cv2.circle(f1, (80, 90), 40, (220, 140, 60), -1)
    f2 = np.zeros((180, 320, 3), dtype=np.uint8)
    cv2.rectangle(f2, (160, 20), (300, 150), (60, 160, 220), -1)
    f3 = (rng.integers(0, 255, (180, 320, 3))).astype(np.uint8)

    # Duplicate: shot 3 repeats shot 1 visually
    vid_dup = tmp_path / "dup.mp4"
    _write_test_video(vid_dup, [f1] * 24 + [f2] * 24 + [f1] * 24, fps=24)
    shots = [
        {"shot_id": "s1", "start_s": 0.0, "end_s": 1.0, "source_image_path": "a.png"},
        {"shot_id": "s2", "start_s": 1.0, "end_s": 2.0, "source_image_path": "b.png"},
        {"shot_id": "s3", "start_s": 2.0, "end_s": 3.0, "source_image_path": "c.png"},
    ]
    res_dup = check_zero_photo_clip_reuse(vid_dup, shots)
    assert res_dup["status"] == "FAIL"
    assert res_dup["visual_duplicates"]

    vid_ok = tmp_path / "ok.mp4"
    _write_test_video(vid_ok, [f1] * 24 + [f2] * 24 + [f3] * 24, fps=24)
    res_ok = check_zero_photo_clip_reuse(vid_ok, shots)
    assert res_ok["status"] == "PASS"


def test_ltx_dominance_enforces_65_percent_and_24_unique_clips() -> None:
    # 24 unique 5s LTX clips (120s) + 10 non-LTX 5s shots (50s) -> 70.6% LTX
    shots = []
    t = 0.0
    for i in range(24):
        shots.append(
            {
                "shot_id": f"ltx_{i:02d}",
                "kind": "ltx",
                "start_s": t,
                "end_s": t + 5.0,
                "file_sha256": f"{i:064x}",
                "modal_job_id": f"batch_{i // 6}",
                "playback_speed": 1.0,
            }
        )
        t += 5.0
    for j in range(10):
        shots.append({"shot_id": f"map_{j:02d}", "kind": "map", "start_s": t, "end_s": t + 5.0})
        t += 5.0

    assert check_ltx_dominance(shots)["status"] == "PASS"

    # Looped duplicate clip SHA must fail
    shots[5]["file_sha256"] = shots[0]["file_sha256"]
    assert check_ltx_dominance(shots)["status"] == "FAIL"


def test_youtube_rhythm_overlay_density_and_audio_anti_repetition() -> None:
    shots = []
    t = 0.0
    for i in range(10):  # first 30s -> 3.0s shots
        shots.append({"shot_id": f"h_{i}", "start_s": t, "end_s": t + 3.0, "j_cut_lead_s": 0.4})
        t += 3.0
    for i in range(30):  # next 120s -> 4.0s shots
        shots.append({"shot_id": f"b_{i}", "start_s": t, "end_s": t + 4.0, "l_cut_tail_s": 0.35})
        t += 4.0

    utterances = [
        {"start_s": 0.5, "end_s": 10.0, "dramatic_breather_after": True},
        {"start_s": 11.2, "end_s": 25.0, "dramatic_breather_after": True},
        {"start_s": 26.4, "end_s": 50.0, "dramatic_breather_after": True},
        {"start_s": 51.5, "end_s": 80.0, "dramatic_breather_after": True},
        {"start_s": 81.3, "end_s": 120.0, "dramatic_breather_after": False},
    ]
    assert check_youtube_rhythm_and_jl_cuts(shots, utterances)["status"] == "PASS"

    archetypes = [
        "kinetic_title_reveal",
        "geological_timeline",
        "stat_counter_card",
        "callout_spec_pointer",
        "split_era_card",
        "artifact_callout_card",
        "trajectory_arrow_callout",
        "kinetic_word_burst",
    ]
    bridges = [
        {"bridge_id": f"ov_{i}", "template": archetypes[i % len(archetypes)], "start_s": 3.0 + i * 3.8}
        for i in range(22)
    ]
    assert check_overlay_density(bridges, narration_waves=[(3.0, 40.0)])["status"] == "PASS"
    assert check_overlay_density(bridges[:5])["status"] == "FAIL"

    sfx = [{"time_s": i * 4.0, "wav_path": f"/tmp/sfx_{i:02d}.wav"} for i in range(16)]
    rep = {"integrated_lufs": -14.0, "peak_dbfs": -1.2, "max_pause_pumping_swing_db": 0.65}
    assert check_audio_anti_repetition(sfx, rep)["status"] == "PASS"
    sfx[2]["wav_path"] = sfx[1]["wav_path"]  # back-to-back repeat
    assert check_audio_anti_repetition(sfx, rep)["status"] == "FAIL"


def test_grain_ceiling_rejects_noisy_video_and_accepts_clean_video(tmp_path: Path) -> None:
    clean = np.full((180, 320, 3), 120, dtype=np.uint8)
    vid_clean = tmp_path / "clean.mp4"
    _write_test_video(vid_clean, [clean] * 24, fps=24)
    assert check_grain_ceiling(vid_clean)["status"] == "PASS"

    rng = np.random.default_rng(7)
    noisy = np.clip(120 + rng.normal(0, 28, (180, 320, 3)), 0, 255).astype(np.uint8)
    vid_noisy = tmp_path / "noisy.mp4"
    _write_test_video(vid_noisy, [noisy] * 24, fps=24)
    assert check_grain_ceiling(vid_noisy)["status"] == "FAIL"


def test_five_persona_viewer_panel_and_paddy_galloway_matrix(tmp_path: Path) -> None:
    report = {
        "schema": "youtube_viewer_panel/1",
        "video_sha256": "a" * 64,
        "ab_packaging": {"winner": "A"},
        "personas": [{"name": f"P{i}"} for i in range(5)],
        "aggregate_retention_at_30s_pct": 84.0,
        "aggregate_avg_view_pct": 69.0,
        "overall_youtube_readiness_score": 9.1,
        "critical_drop_off_defects": [],
        "verdict": "APPROVE",
    }
    rp = tmp_path / "panel.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    res = verify_viewer_panel_report(
        rp,
        expected_sha256="a" * 64,
        min_retention_30s_pct=80.0,
        min_avg_view_pct=65.0,
        min_readiness_score=8.8,
        min_personas=5,
    )
    assert res["status"] == "PASS"
    assert res["persona_count"] == 5

    variants = [
        ThumbnailVariantSpec("A", "Stakes", "How 10,000 Humans Survived the Ice Age", "70,000 BCE", "10,000<br/><em>LEFT</em>", tmp_path / "x.png"),
        ThumbnailVariantSpec("B", "Curiosity", "The First Fire That Changed Everything", "ONE SPARK", "THE FIRST<br/><em>FIRE</em>", tmp_path / "x.png"),
    ]
    cards = evaluate_paddy_galloway_matrix(variants)
    assert cards[0]["duplicates_title"] is False
    assert cards[1]["duplicates_title"] is True

    pi = analyze_pattern_interrupt_cadence(
        [{"start_s": i * 3.0} for i in range(12)],
        [{"start_s": 1.5 + i * 3.5} for i in range(10)],
        [{"time_s": i * 2.0} for i in range(15)],
        total_duration_s=36.0,
    )
    assert pi["status"] == "PASS"


def test_stat_counter_card_accepts_end_value_alias() -> None:
    from explainer_engine.overlay.motion_bridges import MotionBridgeSpec, _build_bridge_html

    spec = MotionBridgeSpec(
        bridge_id="ov_alias",
        template="stat_counter_card",
        title="EXTRA HOURS",
        subtitle="Language & cave art",
        duration_s=3.5,
        meta={"start_value": 0, "end_value": 4, "prefix": "+", "suffix": " HRS"},
    )
    doc = _build_bridge_html(spec, width=1920, height=1080)
    assert 'data-end="4.0"' in doc
    assert 'data-start="0.0"' in doc


def test_broadcast_mix_true_peak_limiter_and_gate(tmp_path: Path) -> None:
    import warnings

    import soundfile as sf

    from explainer_engine.audio.broadcast_cinema_mix import mix_broadcast_cinema_audio

    sr = 48000
    t = np.linspace(0.0, 4.0, sr * 4, endpoint=False, dtype=np.float32)
    # Hot transient-rich voice signal that previously caused inter-sample true-peak overshoot
    voice = (0.7 * np.sin(2 * np.pi * 220 * t) + 0.45 * np.sin(2 * np.pi * 1760 * t) * (np.sin(2 * np.pi * 3 * t) > 0.5)).astype(np.float32)
    voice_wav = tmp_path / "voice.wav"
    sf.write(str(voice_wav), voice, sr, subtype="PCM_16")
    out_wav = tmp_path / "mix.wav"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rep = mix_broadcast_cinema_audio(
            total_duration_s=4.0,
            voice_wav=voice_wav,
            music_acts=[],
            scene_ambiences=[],
            sfx_events=[],
            out_wav=out_wav,
            target_lufs=-14.0,
            true_peak_ceiling_db=-1.5,
        )
    clip_warns = [w for w in caught if "clipped" in str(w.message).lower()]
    assert not clip_warns, f"Unexpected clipping warning: {clip_warns}"
    assert -14.4 <= rep["integrated_lufs"] <= -13.6
    assert rep["true_peak_dbtp"] <= -1.35

    # Gate must reject true_peak_dbtp > -1.0 even when sample peak_dbfs looks safe
    sfx = [{"time_s": float(i), "wav_path": f"/tmp/sfx_{i:02d}.wav"} for i in range(15)]
    bad_tp = check_audio_anti_repetition(
        sfx,
        {"integrated_lufs": -14.0, "peak_dbfs": -1.2, "true_peak_dbtp": 2.2, "max_pause_pumping_swing_db": 0.2},
    )
    assert bad_tp["status"] == "FAIL"

