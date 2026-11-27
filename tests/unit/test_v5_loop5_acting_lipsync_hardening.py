"""Unit tests for v5 Loop 5 acting, lip-sync (VL-02), anti-crop plate, freeze-frame, and layout hardening."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from explainer_engine.explainer.drawing_explainer import DrawingExplainerSpec, _build_explainer_html
from explainer_engine.qa.cinema_gates import (
    check_acting_dynamics_and_freeze,
    check_mouth_motion_sync,
    check_shot_plate_diversity,
)
from explainer_engine.videolane.ltx_loop import (
    CLOSED_MOUTH_LOCK_CLAUSE,
    ContractError,
    PhotoObservation,
    build_photo_grounded_prompt,
    sha256_file,
    validate_acting_blocking_prompt,
    validate_dialogue_framing,
)
from explainer_engine.videolane.multishot_scene_director import (
    extract_axis_locked_coverage_plates,
    validate_native_keyframe_plates,
)


def _write_mp4_from_frames(frames: list[np.ndarray], out_mp4: Path, fps: int = 24) -> Path:
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    vw = cv2.VideoWriter(str(out_mp4), fourcc, float(fps), (w, h))
    for fr in frames:
        vw.write(fr)
    vw.release()
    return out_mp4


def test_anti_crop_plate_guard_blocks_destructive_subcrops(tmp_path: Path) -> None:
    wide = tmp_path / "wide_master.png"
    Image.new("RGB", (1920, 1080), color=(90, 80, 70)).save(wide)

    with pytest.raises(ValueError, match="destructive digital sub-crop"):
        extract_axis_locked_coverage_plates(
            wide,
            [{"shot_id": "s1", "cx": 0.35, "cy": 0.5, "rel_w": 0.42}],
            tmp_path / "out_bad",
        )

    ok = extract_axis_locked_coverage_plates(
        wide,
        [{"shot_id": "s_ok", "cx": 0.5, "cy": 0.5, "rel_w": 0.85, "focus_subject": "caesar", "facing_dir": "right"}],
        tmp_path / "out_ok",
    )
    assert "s_ok" in ok and Path(ok["s_ok"]["path"]).is_file()


def test_validate_native_keyframe_plates_blocks_crops_and_reuse() -> None:
    bad_plan = [
        {"shot_id": "s1", "route": "ltx_video", "picture": "temple_steps.png"},
        {"shot_id": "s2", "route": "ltx_video", "picture": "temple_steps.png"},
        {"shot_id": "s3", "route": "ltx_video", "picture": "crop_caesar.png", "derived_from_crop": True, "crop_upscale_ratio": 2.1},
    ]
    res = validate_native_keyframe_plates(bad_plan)
    assert res["status"] == "FAIL"
    assert any("reused 2 times" in f for f in res["findings"])
    assert any("digitally cropped sub-plate" in f for f in res["findings"])

    good_plan = [
        {"shot_id": "s1", "route": "ltx_video", "picture": "angle_a.png", "plate_width": 1920, "plate_height": 1080},
        {"shot_id": "s2", "route": "ltx_video", "picture": "angle_a.png", "chained_from": "s1"},
        {"shot_id": "s3", "route": "ltx_video", "picture": "angle_b.png", "plate_width": 1920, "plate_height": 1080},
    ]
    assert validate_native_keyframe_plates(good_plan)["status"] == "PASS"


def test_vl02_dialogue_framing_and_closed_mouth_lock(tmp_path: Path) -> None:
    img = tmp_path / "still.png"
    Image.new("RGB", (1280, 720), color=(40, 45, 50)).save(img)
    obs = PhotoObservation(
        photo_path=str(img),
        photo_sha256=sha256_file(img),
        observed_subjects=["Julius Caesar in crimson-bordered cream wool toga"],
        observed_composition="medium close-up",
        observed_lighting="warm directional morning sunlight",
        observed_environment="travertine portico steps",
    )

    # Frontal medium_close_up raw text-only LTX dialogue MUST fail closed (VL-02)
    with pytest.raises(ContractError, match="VL-02 violation"):
        build_photo_grounded_prompt(
            obs,
            camera_move="zoom_in",
            action_beat="turns his head toward Spurinna",
            acting_style="physically grounded cinema acting",
            spoken_line="The Ides of March have come.",
            speaker_name="Julius Caesar",
            voice_description="deep resonant baritone",
            shot_scale="medium_close_up",
            camera_framing="frontal",
            audio_driven_lipsync=False,
        )

    # Safe over_the_shoulder framing PASSES
    p_ots = build_photo_grounded_prompt(
        obs,
        camera_move="zoom_in",
        action_beat="turns his shoulder and steps forward",
        acting_style="physically grounded cinema acting",
        spoken_line="The Ides of March have come.",
        speaker_name="Julius Caesar",
        voice_description="deep resonant baritone",
        shot_scale="medium_close_up",
        camera_framing="over_the_shoulder",
    )
    assert "lips close cleanly" in p_ots.lower()

    # Audio-driven lipsync PASSES even on close_up
    validate_dialogue_framing(
        spoken_line="Aye, Caesar.",
        shot_scale="close_up",
        camera_framing="frontal",
        audio_driven_lipsync=True,
    )

    # Non-dialogue shot MUST lock mouth closed
    p_silent = build_photo_grounded_prompt(
        obs,
        camera_move="truck",
        action_beat="climbs steadily up the stone steps",
        acting_style="physically grounded cinema acting",
    )
    assert CLOSED_MOUTH_LOCK_CLAUSE in p_silent


def test_validate_acting_blocking_prompt() -> None:
    bad = validate_acting_blocking_prompt("Caesar stands with arms lowered and steady posture staring silently.")
    assert len(bad) == 1
    good = validate_acting_blocking_prompt("Caesar pauses mid-stride, turning his shoulder with arms lowered as he steps forward.")
    assert good == []


def test_mouth_motion_sync_gate_catches_silent_flap_and_passes_still_mouth(tmp_path: Path) -> None:
    # 1. Silent shot with still mouth -> PASS
    base = np.full((180, 320, 3), 80, dtype=np.uint8)
    still_frames = [base.copy() for _ in range(24)]
    still_mp4 = _write_mp4_from_frames(still_frames, tmp_path / "silent_clean.mp4")
    r_ok = check_mouth_motion_sync(still_mp4, has_dialogue=False)
    assert r_ok["status"] == "PASS"

    # 2. Silent shot with flapping mouth in lower-face ROI -> FAIL
    flap_frames = []
    for i in range(24):
        fr = base.copy()
        dy = (i % 4) * 5
        cv2.rectangle(fr, (130, 82 + dy), (190, 96 + dy), (240, 240, 240), -1)
        cv2.rectangle(fr, (135, 86 + dy), (185, 92 + dy), (15, 15, 15), -1)
        flap_frames.append(fr)
    flap_mp4 = _write_mp4_from_frames(flap_frames, tmp_path / "silent_flap.mp4")
    r_bad = check_mouth_motion_sync(flap_mp4, has_dialogue=False, max_silent_mouth_flow=0.25)
    assert r_bad["status"] == "FAIL"
    assert any("Phantom mouth movement" in f for f in r_bad["findings"])

    # 3. Dialogue shot with audio silence while mouth flaps -> FAIL
    sr = 16000
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    # First half silent, second half 800Hz speech formant
    audio = np.zeros(sr, dtype=np.float32)
    audio[sr // 2 :] = 0.35 * np.sin(2.0 * np.pi * 800.0 * t[sr // 2 :])
    wav_p = tmp_path / "dlg.wav"
    sf.write(str(wav_p), audio, sr)

    # Mouth flaps ONLY in first half (during silence!) and freezes during speech -> FAIL
    desync_frames = []
    for i in range(24):
        fr = base.copy()
        if i < 12:
            dy = (i % 3) * 6
            cv2.rectangle(fr, (130, 80 + dy), (190, 96 + dy), (250, 250, 250), -1)
        else:
            cv2.rectangle(fr, (130, 84), (190, 96), (250, 250, 250), -1)
        desync_frames.append(fr)
    desync_mp4 = _write_mp4_from_frames(desync_frames, tmp_path / "desync.mp4")
    r_desync = check_mouth_motion_sync(desync_mp4, has_dialogue=True, audio_path=wav_p)
    assert r_desync["status"] == "FAIL"


def test_acting_dynamics_and_freeze_gate(tmp_path: Path) -> None:
    # 1. Frozen 1.5s video -> FAIL
    bg = np.zeros((180, 320, 3), dtype=np.uint8)
    cv2.circle(bg, (160, 90), 30, (200, 180, 150), -1)
    frozen_mp4 = _write_mp4_from_frames([bg.copy() for _ in range(36)], tmp_path / "frozen.mp4")
    r_frz = check_acting_dynamics_and_freeze(frozen_mp4, max_freeze_s=0.85)
    assert r_frz["status"] == "FAIL"
    assert any("Freeze frame" in f for f in r_frz["findings"])

    # 2. Moving foreground subject against textured background -> PASS
    rng = np.random.default_rng(7)
    base = rng.integers(30, 60, size=(180, 320, 3), dtype=np.uint8)
    dyn_frames = []
    for i in range(36):
        fr = base.copy()
        cx = 70 + i * 5
        cv2.circle(fr, (cx, 90), 34, (230, 200, 170), -1)
        cv2.rectangle(fr, (cx - 18, 120), (cx + 18, 165), (180, 60, 60), -1)
        dyn_frames.append(fr)
    dyn_mp4 = _write_mp4_from_frames(dyn_frames, tmp_path / "dynamic.mp4")
    r_dyn = check_acting_dynamics_and_freeze(dyn_mp4, max_freeze_s=0.85, min_residual_subject_flow=0.10)
    assert r_dyn["status"] == "PASS"


def test_shot_plate_diversity_and_drawing_explainer_layout_and_batch_hygiene(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rep = check_shot_plate_diversity(
        [
            {"shot_id": "s1", "picture": "steps.png"},
            {"shot_id": "s2", "picture": "steps.png"},
        ],
        max_plate_reuse=1,
    )
    assert rep["status"] == "FAIL"

    # Drawing explainer roman_conspiracy layout non-overlap & headless HTML build
    art = tmp_path / "bg.png"
    Image.new("RGB", (640, 360), color=(20, 20, 20)).save(art)
    spec = DrawingExplainerSpec(
        explainer_id="consp_test",
        scene_kind="roman_conspiracy",
        title="THE 72-HOUR WINDOW",
        subtitle="Why delaying even one single day kills the entire conspiracy",
        illustration_path=art,
        duration_s=8.0,
    )
    fake_js = tmp_path / 'vendor.js'
    fake_js.write_text('// stub', encoding='utf-8')
    import explainer_engine.explainer.drawing_explainer as de_mod
    monkeypatch.setattr(de_mod, 'resolve_vendor_js', lambda _name: fake_js)
    html_out = _build_explainer_html(spec, width=1920, height=1080)
    assert "white-space:nowrap;" in html_out
    assert "rc.rectangle(1340, 678, 460, 24" in html_out

    # Scene batch JSON has zero hardcoded /home/antigravity paths and zero raw medium close-up dialogue
    batch_path = Path("explainer_engine/training/pods/ltx/scenes/ides_v5_loop5_batch_m4.json")
    raw = batch_path.read_text(encoding="utf-8")
    assert "/home/antigravity" not in raw
    data = json.loads(raw)
    for sh in data["shots"]:
        if "dlg" in sh["shot_id"]:
            assert "medium close-up" not in sh["motion_prompt"].lower()
            assert sh.get("camera_framing") in {"over_the_shoulder", "three_quarter_profile"}
