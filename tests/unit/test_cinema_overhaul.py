"""Tests for the Unified Cinema Overhaul: cinema_grade, cinema_25d, cinema_map, scene_soundscape, cinema_gates, ClaudeSimulator."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio.scene_soundscape import build_scene_locked_soundscape
from explainer_engine.finish.cinema_grade import apply_unified_film_grade
from explainer_engine.orchestration.claude_simulator import ClaudeSimulator
from explainer_engine.production.cinema_25d import estimate_continuous_depth, render_cinema_25d_clip
from explainer_engine.qa import cinema_gates as CG

REPO = Path(__file__).resolve().parents[2]


def _write_test_video(frames_rgb: list[np.ndarray], out_mp4: Path, fps: int = 24) -> Path:
    h, w = frames_rgb[0].shape[:2]
    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(out_mp4),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for fr in frames_rgb:
        proc.stdin.write(fr.astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    assert proc.returncode == 0
    return out_mp4


def test_unified_cinema_grade_deterministic_and_bounded() -> None:
    src = np.full((180, 320, 3), (140, 120, 100), dtype=np.uint8)
    g1 = apply_unified_film_grade(src, frame_idx=3)
    g2 = apply_unified_film_grade(src, frame_idx=3)
    assert g1.shape == src.shape and g1.dtype == np.uint8
    assert np.array_equal(g1, g2)
    # Vignette darkens corners relative to center
    assert float(g1[90, 160].mean()) > float(g1[2, 2].mean())


def test_cinema_25d_living_motion_and_zero_midframe_tears(tmp_path: Path) -> None:
    yy, xx = np.mgrid[0:360, 0:640]
    img = np.stack(
        [
            np.clip(80 + 70 * np.sin(xx / 45.0) + 40 * np.cos(yy / 35.0), 0, 255),
            np.clip(75 + 50 * np.cos(xx / 60.0), 0, 255),
            np.clip(70 + 60 * np.sin((xx + yy) / 55.0), 0, 255),
        ],
        axis=-1,
    ).astype(np.uint8)
    still = tmp_path / "still.png"
    Image.fromarray(img).save(still)

    depth, _ = estimate_continuous_depth(img)
    assert depth.shape == (360, 640) and 0.0 <= float(depth.min()) <= float(depth.max()) <= 1.0

    out_mp4 = tmp_path / "living_25d.mp4"
    rep = render_cinema_25d_clip(still, out_mp4, duration_s=2.0, width=320, height=180, fps=24, camera_move="push_left")
    assert rep["status"] == "PASS" and out_mp4.is_file()

    s_qa = CG.check_no_static_shots(out_mp4, [{"shot_id": "s1", "kind": "25d", "start_s": 0.0, "end_s": 2.0}])
    assert s_qa["status"] == "PASS", s_qa
    t_qa = CG.check_no_midframe_tears(out_mp4)
    assert t_qa["status"] == "PASS", t_qa


def test_cinema_gates_catch_static_shot_and_midframe_tear(tmp_path: Path) -> None:
    # 1. Frozen video MUST fail check_no_static_shots
    base = np.full((180, 320, 3), (90, 95, 100), dtype=np.uint8)
    frozen_mp4 = _write_test_video([base] * 48, tmp_path / "frozen.mp4")
    s_qa = CG.check_no_static_shots(frozen_mp4, [{"shot_id": "frozen_1", "kind": "25d", "start_s": 0.0, "end_s": 2.0}])
    assert s_qa["status"] == "FAIL" and s_qa["findings"]

    # 2. Artificial horizontal mid-frame split/tear MUST fail check_no_midframe_tears
    torn = np.full((180, 320, 3), (40, 42, 45), dtype=np.uint8)
    torn[90:, :] = (230, 225, 220)  # razor-sharp mid-frame split across full width
    torn_mp4 = _write_test_video([torn] * 12, tmp_path / "torn.mp4")
    t_qa = CG.check_no_midframe_tears(torn_mp4)
    assert t_qa["status"] == "FAIL" and t_qa["findings"]


def test_scene_soundscape_and_audio_scene_consistency_gate(tmp_path: Path) -> None:
    shots = [
        {"shot_id": "s1_dry", "kind": "25d", "scene_environment": "dry_daylight_valley", "start_s": 0.0, "end_s": 2.0},
        {"shot_id": "s2_map", "kind": "map", "scene_environment": "map_table_war_room", "start_s": 2.0, "end_s": 4.0},
        {"shot_id": "s3_rain", "kind": "25d", "scene_environment": "night_rain_camp", "start_s": 4.0, "end_s": 6.0},
    ]
    cues = [
        {"cue_id": "m_rev", "sfx": "parchment_unfold", "timestamp_s": 2.1, "gain_db": -4.0},
        {"cue_id": "m_arr", "sfx": "ink_arrow_sweep", "timestamp_s": 2.6, "gain_db": -3.0},
    ]
    rep = build_scene_locked_soundscape(
        shots,
        tmp_path / "mix.wav",
        sfx_cues=cues,
        total_duration_s=6.0,
        library_manifest_path=REPO / "assets/audio/library/cc0_cinema_manifest.json",
    )
    qa_ok = CG.check_audio_scene_consistency(rep)
    assert qa_ok["status"] == "PASS", qa_ok
    assert qa_ok["spectral_centroid_span_hz"] > 100.0

    # Negative check: rain on a map shot with 0 SFX MUST fail
    bad_rep = {
        "integrated_lufs": -14.0,
        "peak_dbfs": -2.0,
        "shots": [
            {"shot_id": "bad_map", "kind": "map", "scene_environment": "night_rain_camp", "sfx_count_in_shot": 0, "spectral_centroid_hz": 400.0},
        ],
    }
    qa_bad = CG.check_audio_scene_consistency(bad_rep)
    assert qa_bad["status"] == "FAIL" and len(qa_bad["findings"]) >= 2


def test_claude_simulator_enforces_real_governance_hooks(tmp_path: Path) -> None:
    sim = ClaudeSimulator(REPO)
    assert sim.check_bash("python -m pytest -q") is True
    assert sim.check_write(tmp_path / "safe_output.json") is True
    with pytest.raises(PermissionError, match="pre-write-guard"):
        sim.check_write(REPO / "config" / "owner_approvals.json")
