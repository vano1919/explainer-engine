"""Unit tests for v5 Loop 5 acting, lip-sync (VL-02), anti-crop plate, freeze-frame, and layout hardening."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
import soundfile as sf
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.explainer.drawing_explainer import DrawingExplainerSpec, _build_explainer_html
from explainer_engine.qa.cinema_gates import (
    check_acting_dynamics_and_freeze,
    check_mouth_motion_sync,
    check_shot_plate_diversity,
)
from explainer_engine.videolane.ltx_loop import (
    CLOSED_MOUTH_LOCK_CLAUSE,
    PhotoObservation,
    build_photo_grounded_prompt,
    sha256_file,
    validate_acting_blocking_prompt,
)
from explainer_engine.videolane.multishot_scene_director import extract_axis_locked_coverage_plates


def _write_mp4_from_frames(frames: list[np.ndarray], out_mp4: Path, fps: int = 24) -> Path:
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    vw = cv2.VideoWriter(str(out_mp4), fourcc, float(fps), (w, h))
    for fr in frames:
        vw.write(fr)
    vw.release()
    return out_mp4


def test_coverage_plates_cannot_be_cropped_at_any_width(tmp_path: Path) -> None:
    wide = tmp_path / "wide_master.png"
    Image.new("RGB", (1920, 1080), color=(90, 80, 70)).save(wide)
    for rel_w in (0.42, 0.85):
        with pytest.raises(RuntimeError, match="permanently banned"):
            extract_axis_locked_coverage_plates(wide, [{"shot_id": "s", "cx": 0.5, "cy": 0.5, "rel_w": rel_w}], tmp_path / "o")
    assert not (tmp_path / "o").exists()


def test_closeup_dialogue_routes_to_voice_first_lipsync_and_silent_locks_mouth(tmp_path: Path) -> None:
    from explainer_engine.videolane.lipsync_pipeline import (
        build_lipsync_refinement_command,
        plan_dialogue_lipsync_route,
    )

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

    # Frontal medium_close_up dialogue is ALLOWED (never banned) and routes to Voice-First A2V + LatentSync!
    line_wav = tmp_path / "caesar.wav"
    sf.write(str(line_wav), np.zeros(16000, dtype=np.float32), 16000)
    cu_args = dict(
        camera_move="zoom_in",
        action_beat="turns his head toward Spurinna with a sharp ironic glance",
        acting_style="physically grounded cinema acting",
        spoken_line="The Ides of March have come.",
        speaker_name="Julius Caesar",
        voice_description="deep resonant baritone",
        shot_scale="medium_close_up",
        camera_framing="frontal",
    )
    # Fail-closed: a speaking close-up without its voice-first WAV is never prompted as a text-driven talking face
    with pytest.raises(ContractError, match="voice-first"):
        build_photo_grounded_prompt(obs, **cu_args)
    p_cu = build_photo_grounded_prompt(obs, **cu_args, audio_driver_path=line_wav)
    assert "audio-driven cinema close-up acting" in p_cu.lower()
    assert "lips close cleanly" in p_cu.lower()

    plan_cu = plan_dialogue_lipsync_route(
        shot_id="cu_01",
        spoken_line="The Ides of March have come.",
        shot_scale="close_up",
        camera_framing="frontal",
        audio_driver_path=line_wav,
        preferred_backend="latentsync_1_6",
    )
    assert plan_cu.route == "ltx_a2v_plus_lipsync_refinement"
    assert plan_cu.primary_engine == "ltx_a2v"
    assert plan_cu.refinement_backend == "latentsync_1_6"
    assert plan_cu.requires_voice_first_wav is True
    from explainer_engine.videolane.lipsync_pipeline import require_voice_first_inputs

    pin = require_voice_first_inputs(plan_cu)
    assert pin["path"] == str(line_wav) and len(pin["sha256"]) == 64

    # A wider dialogue shot without a WAV keeps the clip-spoken route; with a WAV it is audio-driven
    wide = plan_dialogue_lipsync_route(spoken_line="Move along.", shot_scale="medium_wide", camera_framing="over_the_shoulder")
    assert (wide.route, wide.requires_voice_first_wav) == ("ltx_i2v_clip_spoken", False)
    wide_wav = plan_dialogue_lipsync_route(
        spoken_line="Move along.", shot_scale="medium_wide", camera_framing="over_the_shoulder", audio_driver_path=line_wav
    )
    assert wide_wav.route == "ltx_a2v_direct" and wide_wav.refinement_backend is None

    job_ls = build_lipsync_refinement_command(
        backend="latentsync_1_6",
        video_path=tmp_path / "raw_ltx.mp4",
        audio_wav_path=tmp_path / "caesar.wav",
        out_mp4=tmp_path / "synced.mp4",
    )
    assert job_ls["license"] == "Apache-2.0"
    assert "stage2_512.yaml" in " ".join(job_ls["cmd"])

    job_mt = build_lipsync_refinement_command(
        backend="musetalk_1_5",
        video_path=tmp_path / "raw_ltx.mp4",
        audio_wav_path=tmp_path / "caesar.wav",
        out_mp4=tmp_path / "synced_mt.mp4",
    )
    assert job_mt["license"] == "MIT"

    # Non-dialogue shot MUST still lock mouth closed during narrator-over scenes
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
    # whole words only: 'handsome' is no hand, the stone steps are no step, a pause is no action
    still = validate_acting_blocking_prompt("Handsome Caesar pauses on the stone steps, arms lowered, steady posture.")
    assert len(still) == 1


def _face_clip(path: Path, mouth_open: list[float], fps: int = 24) -> tuple[Path, list[list[float]]]:
    """A textured head that bobs, with a mouth whose opening follows ``mouth_open`` (0 closed .. 1 open)."""
    rng = np.random.default_rng(3)
    bg = rng.integers(40, 70, size=(360, 640, 3), dtype=np.uint8)
    frames, boxes = [], []
    for i, k in enumerate(mouth_open):
        fr = bg.copy()
        x, y, size = 250 + (i % 6), 90 + (i % 4), 140
        cv2.rectangle(fr, (x, y), (x + size, y + size), (150, 170, 200), -1)
        tex = rng.integers(0, 25, size=(size, size, 3), dtype=np.uint8)
        fr[y : y + size, x : x + size] = np.clip(fr[y : y + size, x : x + size].astype(int) - tex, 0, 255).astype(np.uint8)
        cv2.circle(fr, (x + 45, y + 50), 9, (30, 30, 30), -1)
        cv2.circle(fr, (x + 95, y + 50), 9, (30, 30, 30), -1)
        h = int(4 + 26 * k)
        cv2.rectangle(fr, (x + 48, y + 108 - h // 2), (x + 92, y + 108 + h // 2), (20, 10, 10), -1)
        frames.append(fr)
        boxes.append([x, y, size, size])
    return _write_mp4_from_frames(frames, path, fps), boxes


def _voice_wav(path: Path, envelope: np.ndarray, n: int, sr: int = 16000) -> Path:
    t = np.arange(int(sr * n / 24)) / sr
    sf.write(str(path), (0.3 * np.sin(2 * np.pi * 900 * t) * np.interp(t, np.arange(n) / 24, envelope)).astype(np.float32), sr)
    return path


def test_mouth_gate_measures_the_face_not_the_frame(tmp_path: Path) -> None:
    n = 96
    talk = np.random.default_rng(11).random(n)
    still_mp4, still_boxes = _face_clip(tmp_path / "still.mp4", [0.0] * n)
    talk_mp4, talk_boxes = _face_clip(tmp_path / "talk.mp4", [float(v) for v in talk])

    # A closed mouth on a moving head passes; a talking mouth on a silent shot is phantom speech
    assert check_mouth_motion_sync(still_mp4, has_dialogue=False, face_boxes=still_boxes)["status"] == "PASS"
    phantom = check_mouth_motion_sync(talk_mp4, has_dialogue=False, face_boxes=talk_boxes)
    assert phantom["status"] == "FAIL" and "Phantom speech" in phantom["findings"][0]

    # The voice is loud where the mouth articulates -> PASS
    articulation = np.convolve(np.abs(np.diff(talk, prepend=talk[0])), np.ones(2) / 2, mode="same")
    ok = check_mouth_motion_sync(talk_mp4, has_dialogue=True, audio_path=_voice_wav(tmp_path / "s.wav", articulation, n),
                                 face_boxes=talk_boxes)
    assert ok["status"] == "PASS", ok

    # Desync: the mouth talks in the first half, the voice speaks only in the second -> FAIL
    half = np.where(np.arange(n) < n // 2, talk, 0.0)
    desync_mp4, desync_boxes = _face_clip(tmp_path / "desync.mp4", [float(v) for v in half])
    late_voice = np.where(np.arange(n) >= n // 2, 1.0, 0.0)
    bad = check_mouth_motion_sync(desync_mp4, has_dialogue=True, audio_path=_voice_wav(tmp_path / "d.wav", late_voice, n),
                                  face_boxes=desync_boxes)
    assert bad["status"] == "FAIL", bad


def test_mouth_gate_says_not_run_without_a_face(tmp_path: Path) -> None:
    frames = [np.full((180, 320, 3), 80, dtype=np.uint8) for _ in range(24)]
    clip = _write_mp4_from_frames(frames, tmp_path / "no_face.mp4")
    res = check_mouth_motion_sync(clip, has_dialogue=False)
    assert res["status"] == "NOT_RUN"


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

    # Scene batch JSON has no absolute home paths and no text-prompted medium close-up dialogue
    batch_path = Path("explainer_engine/training/pods/ltx/scenes/ides_v5_loop5_batch_m4.json")
    raw = batch_path.read_text(encoding="utf-8")
    assert '"/home/' not in raw and '"/Users/' not in raw
    data = json.loads(raw)
    for sh in data["shots"]:
        if "dlg" in sh["shot_id"]:
            assert "medium close-up" not in sh["motion_prompt"].lower()
            assert sh.get("camera_framing") in {"over_the_shoulder", "three_quarter_profile"}
