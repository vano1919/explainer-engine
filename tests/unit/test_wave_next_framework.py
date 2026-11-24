"""End-to-end tests and real local FFmpeg render-inspect-correct-rerender verification for Wave Next Framework."""
from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.audio import post_assembly_spotting as PAS
from explainer_engine.core import approvals
from explainer_engine.core.errors import ContractError
from explainer_engine.core.execution_gateway import ProductionStateMachine
from explainer_engine.governance import gateway_hook as GH
from explainer_engine.maps import draw as map_draw
from explainer_engine.overlay import bridge_compiler as BC
from explainer_engine.qa import identity_lock as IL
from explainer_engine.qa import perceptual_qa as PQA
from explainer_engine.videolane import adapters as AD

REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_portrait(path: Path, bg: tuple[int, int, int], accent: tuple[int, int, int]) -> Path:
    im = Image.new("RGB", (320, 180), bg)
    d = ImageDraw.Draw(im)
    d.rectangle([100, 30, 220, 150], fill=accent)
    d.ellipse([135, 45, 185, 95], fill=(230, 200, 175))
    im.save(path, format="PNG")
    return path


def _make_tone_wav(path: Path, *, value: float, sr: int = 16000, seconds: float = 0.5) -> Path:
    n = int(sr * seconds)
    arr = np.full(n, value, dtype=np.float32)
    pcm = np.clip(arr * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def test_execution_gateway_enforces_stage_order_sha256_and_downstream_invalidation(tmp_path: Path):
    state_p = tmp_path / "production_state.json"
    sm = ProductionStateMachine(state_p, episode_id="ep_nextgen_test")

    # Cannot skip directly to clips before script/pictures/voice
    ok, blockers = sm.can_start_stage("clips")
    assert ok is False
    assert blockers

    # Cannot mark script PASS with nonexistent output
    with pytest.raises(ContractError):
        sm.record_stage_completion("script", status="PASS", output_paths=[tmp_path / "missing.json"])

    script_f = tmp_path / "script.json"
    script_f.write_text('{"v": 1}', encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[script_f])

    sp_f = tmp_path / "sound_plan.json"
    sp_f.write_text('{"cues": []}', encoding="utf-8")
    sm.record_stage_completion("sound_plan", status="PASS", output_paths=[sp_f])

    # Mutating script and re-recording automatically invalidates downstream sound_plan
    script_f.write_text('{"v": 2}', encoding="utf-8")
    res = sm.record_stage_completion("script", status="PASS", output_paths=[script_f])
    assert "sound_plan" in res["invalidated_downstream"]
    assert sm.status_summary()["stages"]["sound_plan"] == "INVALIDATED"

    # CLI status runs cleanly
    proc = subprocess.run(
        [sys.executable, "-m", "explainer_engine.core.execution_gateway", "status", str(state_p)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0
    assert "ep_nextgen_test" in proc.stdout

    # Paid authorization fails closed without valid owner_approvals.json entry
    with pytest.raises(approvals.ApprovalError):
        sm.authorize_paid_action(
            approval_id="cmsg_fake_00001",
            provider="modal_modal1",
            operation_mode="modal-ltx-smoke",
            manifest={"shot": "s1"},
            estimated_usd=0.5,
            cap_usd=1.5,
            item_id="item_1",
            ledger_path=tmp_path / "ledger.sqlite3",
        )


def test_map_raster_renderer_uses_approved_liberation_serif_typography():
    assert map_draw.MAP_FONT.name == "LiberationSerif-Regular.ttf"
    assert map_draw.MAP_FONT.is_file()


def test_calibrated_cross_scene_identity_lock_is_commercial_safe_and_confidence_aware(tmp_path: Path):
    ref = _make_portrait(tmp_path / "char_ref.png", (25, 35, 45), (120, 90, 60))
    same = _make_portrait(tmp_path / "char_scene2_same.png", (28, 38, 48), (118, 88, 62))
    diff = _make_portrait(tmp_path / "char_scene3_diff.png", (210, 210, 200), (20, 180, 220))

    # Back-facing / distant shots never produce arbitrary identity failures
    na = IL.check_cross_scene_identity(ref, diff, character_id="hero_1", pose_tag="back_facing")
    assert na["status"] == "NOT_APPLICABLE"
    na2 = IL.check_cross_scene_identity(ref, diff, character_id="hero_1", face_width_ratio=0.02)
    assert na2["status"] == "NOT_APPLICABLE"

    # Matching portrait passes; divergent cross-scene portrait emits calibrated REVIEW (not hard FAIL)
    ok = IL.check_cross_scene_identity(ref, same, character_id="hero_1")
    assert ok["status"] == "PASS"
    assert ok["license_safe"] is True
    rev = IL.check_cross_scene_identity(ref, diff, character_id="hero_1")
    assert rev["status"] == "REVIEW"


def test_claude_opus_gateway_hook_blocks_ungoverned_bypasses_and_verifies_state(tmp_path: Path):
    assert GH.check_hook_payload({"tool_input": {"command": "modal secret create custom-secret HF_TOKEN=x --force"}})["decision"] == "deny"
    assert GH.check_hook_payload({"tool_input": {"command": "modal run explainer_engine/training/pods/ltx/modal_ltx_jobs.py::smoke"}})["decision"] == "deny"
    assert GH.check_hook_payload({"tool_input": {"command": "curl https://generativelanguage.googleapis.com/v1beta/models?key=SECRET"}})["decision"] == "deny"
    assert GH.check_hook_payload({"tool_input": {"command": "git reset --hard HEAD~1"}})["decision"] == "deny"
    assert GH.check_hook_payload({"tool_input": {"command": "python -m explainer_engine.episode status ep1"}})["decision"] == "allow"

    state_p = tmp_path / "state.json"
    sm = ProductionStateMachine(state_p, episode_id="ep_hook")
    assert GH.verify_production_state_gate(state_p, required_stages=("script",))["ok"] is False
    sf = tmp_path / "script.json"
    sf.write_text("{}", encoding="utf-8")
    sm.record_stage_completion("script", status="PASS", output_paths=[sf])
    assert GH.verify_production_state_gate(state_p, required_stages=("script",))["ok"] is True


def test_real_local_render_inspect_correct_rerender_loop_with_bridges_2k_upscale_and_spotting(tmp_path: Path):
    """Phase 6 real media proof: frozen V1 -> QA FAIL -> corrected animated V2 + Liberation Serif bridges + 2K upscale + spotting + 30ms fade A/B."""
    # 1. Still upscaler adapter produces real 2K PNG
    start_img = _make_portrait(tmp_path / "scene_start.png", (25, 35, 50), (140, 100, 65))
    still_up = AD.LocalStillUpscaler().upscale_still(start_img, tmp_path / "scene_start_2k.png")
    assert still_up["width"] == 2560 and still_up["height"] == 1440
    assert Path(still_up["output_path"]).is_file()

    # 2. V1 defect render (frozen frame) caught deterministically by 3-layer perceptual_qa
    v1_frozen = tmp_path / "v1_frozen.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-loop", "1", "-i", str(start_img),
            "-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.08:duration=2.0,pan=stereo|c0=c0|c1=0.9*c0",
            "-t", "2.0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(v1_frozen),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    qa_v1 = PQA.evaluate_clip_perceptual(v1_frozen, out_dir=tmp_path / "qa_v1", use_gemini=False)
    assert qa_v1["technical_status"] == "FAIL"
    assert any(d["defect_id"] == "SIG-VID-FROZEN" for d in qa_v1["defects"])

    # 3. Correction & V2 rerender: real motion via LocalRehearsalVideoAdapter + Liberation Serif visual bridge composite + 2K video upscale
    rehearsal_rec = AD.LocalRehearsalVideoAdapter().generate_clip(
        {"start_image_path": str(start_img), "ltx_frames": 73, "fps": 24},
        tmp_path / "v2_motion.mp4",
    )
    assert rehearsal_rec["rehearsal"] is True
    assert Path(rehearsal_rec["clip_path"]).is_file()

    ov_spec = BC.compile_bridges_to_overlay_spec(
        [
            {"kind": "date_location_card", "text": "DECEMBER 1914 — FLANDERS", "subtext": "Western Front", "timestamp_s": 0.4, "duration_s": 1.2},
            {"kind": "kinetic_callout", "text": "100,000 SOLDIERS", "subtext": "Unofficial ceasefire", "timestamp_s": 1.8, "duration_s": 1.0},
        ],
        size=(1280, 720),
    )
    comp = BC.composite_bridges_onto_video(Path(rehearsal_rec["clip_path"]), ov_spec, tmp_path / "v2_composited.mp4", work_dir=tmp_path / "bridges")
    assert comp["bridges_composited"] == 2

    up_vid = AD.LocalFFmpeg2KVideoUpscaler().upscale_video(Path(comp["output_video"]), tmp_path / "v2_final_2k.mp4")
    assert up_vid["width"] == 2560 and up_vid["height"] == 1440

    qa_v2 = PQA.evaluate_clip_perceptual(Path(up_vid["output_path"]), out_dir=tmp_path / "qa_v2", use_gemini=False)
    assert qa_v2["technical_status"] == "PASS"
    assert qa_v2["technical_metrics"]["audio_channels"] == 2
    assert len(qa_v2["temporal_frames_inspected"]) == 8

    # 4. Post-assembly visual-aware sound spotting + SHA-256 invalidation check
    events = PAS.detect_visual_event_timestamps(Path(up_vid["output_path"]), tmp_path / "spot_work", diff_threshold=0.005)
    cues = [{"source": "free_library", "visual_timestamp_s": e["visual_timestamp_s"]} for e in events] or [{"source": "free_library", "visual_timestamp_s": 0.5}]
    spot = PAS.build_spotting_record(Path(up_vid["output_path"]), cues, out_path=tmp_path / "spotting.json")
    assert spot["validation"]["status"] == "PASS"
    assert PAS.is_spotting_fresh(spot, Path(up_vid["output_path"])) is True
    assert PAS.is_spotting_fresh(spot, v1_frozen) is False  # different video invalidates spotting!

    # 5. Objective 30ms fade vs hard-cut A/B measurement (step discontinuity from +0.6 to -0.6)
    wav_a = _make_tone_wav(tmp_path / "a.wav", value=0.6)
    wav_b = _make_tone_wav(tmp_path / "b.wav", value=-0.6)
    ab = PAS.measure_audio_cut_ab(wav_a, wav_b, tmp_path / "ab_audio", fade_ms=30.0)
    assert ab["hard_cut_boundary_jump"] > 1.0
    assert ab["faded_boundary_max_step"] < 0.05
    assert ab["pop_reduction_ratio"] > 0.95
