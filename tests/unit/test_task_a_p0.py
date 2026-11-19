"""Regression tests for Task A (P0-1 .. P0-5) on branch o239-argon-impl."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.edit import cinematic_transitions as CT
from explainer_engine.episode import shot_split as SS
from explainer_engine.episode import sound_plan as SP
from explainer_engine.episode import timing as TM
from explainer_engine.production import directed25d as D25
from explainer_engine.production import layers25d as L25
from explainer_engine.qa import motion_intent as MI


def test_p0_1_nine_second_still_one_visual_timeline_and_continuity_gate():
    """P0-1: A 9 s still_25d moving-camera shot produces ONE visual timeline with continuous camera waypoints."""
    words = [
        {"word": f"w{i}", "start_s": i * 0.5, "end_s": (i + 1) * 0.5, "start_frame": i * 12, "end_frame": (i + 1) * 12}
        for i in range(18)
    ]
    words[7]["word"] = "pause,"
    shot = {
        "shot_id": "S08_SH002",
        "route": "still_25d",
        "target_duration_seconds": 9.0,
        "total_frames": 216,
        "camera_spec": {"camera_move": "push_in"},
        "spine": words,
    }
    plan = SS.plan_continuous_still_timeline(shot, words, max_s=5.0, fps=24)
    assert len(plan["visual_clips"]) == 1
    clip = plan["visual_clips"][0]
    assert clip["shot_id"] == "S08_SH002"
    assert clip["total_frames"] == 216
    assert len(plan["narration_segments"]) >= 2
    wps = clip["continuous_camera_waypoints"]
    assert wps[0]["start"] == 0 and wps[-1]["end"] == 216

    # Gate fails on boundary jump, passes on smooth trajectory
    smooth_views = [{"s": 1.0 + 0.0004 * f, "cx": 0.5, "cy": 0.5} for f in range(216)]
    assert D25.verify_rendered_split_camera_continuity(smooth_views, [96])["status"] == "PASS"
    jumpy_views = list(smooth_views)
    jumpy_views[96] = {"s": 1.0, "cx": 0.5, "cy": 0.5}  # camera reset at boundary
    assert D25.verify_rendered_split_camera_continuity(jumpy_views, [96])["status"] == "FAIL"


def test_p0_2_people_in_frame_clipping_and_missing_protection(tmp_path):
    """P0-2: 2-3 % outside-frame clipping FAILS (even on soft boxes / odd frames); missing keep_in_frame -> REVIEW."""
    from PIL import Image

    pic = tmp_path / "scene.png"
    Image.new("RGB", (320, 180), (90, 90, 90)).save(pic)
    mask = np.zeros((180, 320), dtype=np.float32)
    mask[20:160, 0:60] = 1.0  # person near left edge
    layers = {
        "plate": np.full((180, 320, 3), 90, dtype=np.uint8),
        "depth": np.full((180, 320), 0.5, dtype=np.float32),
        "masks": {"soldier_left": mask},
        "objects": [],
        "lights": [],
        "faces": [],
        "manifest": {"masks": {"objects": [{"id": "soldier_left", "layer": False}]}},
    }
    # 1) Soft box / trajectory pushing > 1% outside must FAIL
    plan_soft = {
        "shot_id": "T_SOFT",
        "frames": 12,
        "cameras": [{"op": "truck", "direction": "right", "from": 0, "to": 12, "strength": 1.5}],
        "keep_in_frame": [{"mask": "soldier_left", "soft": True, "why": "soldier_left"}],
        "effects": [],
    }
    st_soft = D25.Stage(pic, layers, plan_soft, (320, 180), 24)
    peop_soft = st_soft.people_cut(every=1, include_soft=True)
    # Force a trajectory check when box is clipped by 2-3%
    row_fail = MI.people_in_frame_row({"share": 0.025, "frame": 5, "what": "soldier_left", "kept": 1})
    assert row_fail["status"] == "FAIL"
    assert peop_soft["kept"] >= 1

    # 2) Person in masks missing from keep_in_frame -> auto-registered & REVIEW (NOT_MEASURED), never PASS
    plan_unreg = {"shot_id": "T_UNREG", "frames": 6, "cameras": [], "keep_in_frame": [], "effects": []}
    st_unreg = D25.Stage(pic, layers, plan_unreg, (320, 180), 24)
    peop_unreg = st_unreg.people_cut()
    assert "soldier_left" in peop_unreg["unregistered_people"]
    row_rev = MI.people_in_frame_row(peop_unreg)
    assert row_rev["status"] == "REVIEW"
    assert "NOT_MEASURED" in row_rev["detail"]

    # 3) L25 fallback also measures people_in_frame and returns REVIEW when faces=None
    p_l25 = L25.plan({"shot_id": "T_L25", "target_duration_seconds": 0.5}, 24)
    sc_l25 = L25.build_scene(pic, p_l25, (320, 180), depth=np.full((180, 320), 0.5, dtype=np.float32), faces=None)
    peop_l25 = L25.measure_people_in_frame(sc_l25)
    assert peop_l25["missing_protection"] is True
    assert MI.people_in_frame_row(peop_l25)["status"] == "REVIEW"


def test_p0_3_narration_contract_shared_resolver(tmp_path):
    """P0-3: audio/narration.wav is canonical; missing both files is a hard ContractError."""
    ep = tmp_path / "ep"
    (ep / "audio").mkdir(parents=True)
    with pytest.raises(ContractError):
        TM.resolve_narration_path(ep, dl_dir=tmp_path / "dl")

    wav = ep / "audio" / "narration.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        sig = (np.sin(np.linspace(0, 200, 4800)) * 12000).astype(np.int16)
        w.writeframes(sig.tobytes())

    resolved = TM.resolve_narration_path(ep, dl_dir=tmp_path / "dl")
    assert resolved == wav


def test_p0_4_one_boundary_manifest_and_severe_jump_flag():
    """P0-4: Three-shot fixture (2 same-loc cuts + 1 loc change) -> one manifest, 0.3-0.6s overlap, severe jump REVIEW."""
    script = {
        "episode_id": "ep_test",
        "segments": [{"segment_id": "S01", "mood": "tense"}],
        "audio_lines": [],
        "shots": [
            {"shot_id": "S01_SH001", "segment_id": "S01", "location_id": "loc_a", "target_duration_seconds": 3.0,
             "route": "still_25d", "transition_out": "hard_cut"},
            {"shot_id": "S01_SH002", "segment_id": "S01", "location_id": "loc_a", "target_duration_seconds": 3.0,
             "route": "video", "transition_out": "hard_cut"},
            {"shot_id": "S01_SH003", "segment_id": "S01", "location_id": "loc_b", "target_duration_seconds": 3.0,
             "route": "video", "transition_out": "hard_cut"},
        ],
    }
    bright = np.full((64, 64, 3), 156, dtype=np.uint8)
    dark = np.full((64, 64, 3), 80, dtype=np.uint8)
    bm = CT.build_boundary_manifest(
        script,
        fps=24,
        honour_authored=True,
        boundary_frames={"S01_SH001->S01_SH002": (bright, dark), "S01_SH002->S01_SH003": (dark, dark)},
    )
    assert len(bm["boundaries"]) == 2
    b0, b1 = bm["boundaries"]
    # Every boundary has either shared_ambience or 0.3-0.6s bridge
    assert b0["shared_ambience"] is True
    assert 0.3 <= b0["j_cut_prelap_sec"] <= 0.6
    assert b1["shared_ambience"] is False
    assert 0.3 <= b1["ambience_bridge_sec"] <= 0.6
    # Severe-jump authored hard cut without editorial_reason is flagged REVIEW
    assert b0["visual_analysis"]["severe_jump"] is True
    assert b0["editorial_review_status"] == "REVIEW"
    assert b0["editorial_flag"] == "severe_jump_unmotivated_hard_cut"

    # G8 sound_plan consumes boundary_manifest
    sp = SP.build(script, fps=24, boundary_manifest=bm)
    assert len(sp["boundaries"]) == 2
    assert sp["bridges"][0]["at_s"] == 6.0

    # 14f warm_dip supported
    assert CT.AUTHORED_FRAMES["warm_dip"] == 14
    assert CT.AUTHORED_FRAMES["cross_dissolve_14f"] == 14


def test_p0_5_clock_proof_and_sample_mapping():
    """P0-5: 1-frame offset or stale timing_id FAILS verify_clock_alignment; 1 frame @ 48k/24fps == 2000 samples."""
    auth = {
        "schema": TM.SCHEMA_V2,
        "episode_id": "ep_test",
        "fps": 24,
        "total_frames": 72,
        "shots": {"S01_SH001": {"start_frame": 0, "end_frame": 72, "frames": 72}},
    }
    auth["timing_id"] = TM.compute_timing_id(auth)
    auth["render_epoch"] = f"epoch_{auth['timing_id']}"

    assert TM.verify_clock_alignment(auth, {"shot_id": "S01_SH001", "frames": 72, "timing_id": auth["timing_id"], "render_epoch": auth["render_epoch"]}) == []
    assert TM.verify_clock_alignment(auth, {"shot_id": "S01_SH001", "frames": 71, "timing_id": auth["timing_id"]})
    assert TM.verify_clock_alignment(auth, {"shot_id": "S01_SH001", "frames": 72, "timing_id": "stale_id"})
    assert TM.frame_to_sample(1, sample_rate=48000, fps=24) == 2000
