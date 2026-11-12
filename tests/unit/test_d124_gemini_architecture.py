"""Unit tests for D-124 Gemini Architecture (ARCH-01..ARCH-12)."""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.assets.reference_library import (
    DEFAULT_CHIAROSCURO_LIBRARY,
    select_reference_plate,
    validate_reference_library,
)
from explainer_engine.imagegen.asset_plan import extract_complete_asset_plan
from explainer_engine.imagegen.gemini_image_engine import build_gemini_generation_queue
from explainer_engine.audio.sfx_planner import build_g4_audio_fx_plan
from explainer_engine.aivideo.wan_optimizer import (
    evaluate_dialogue_render_route,
    plan_parallel_g7_threads,
    seconds_to_wan_frames,
)
from explainer_engine.production.chunked_edit import plan_3min_assembly_chunks
from explainer_engine.orchestration.rule_enforcer import run_all_gate_audits

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_g0_reference_library_validation():
    errors = validate_reference_library(DEFAULT_CHIAROSCURO_LIBRARY)
    assert errors == []
    unlocked = dict(DEFAULT_CHIAROSCURO_LIBRARY, status="PROPOSED")
    assert len(validate_reference_library(unlocked)) == 1


def test_full_12min_script_passes_all_g0_to_g8_audits():
    script_path = REPO_ROOT / "jobs" / "ep_waterloo_12min" / "production_script.json"
    script_doc = json.loads(script_path.read_text(encoding="utf-8"))
    report = run_all_gate_audits(script_doc)
    assert report["status"] == "PASS", f"Unexpected gate issues: {report['issues']}"
    assert report["total_issues"] == 0
    assert report["g0_reference_library_valid"] is True
    assert report["g4_sfx_cues_planned"] > 20
    assert report["g4_melodies_planned"] == 12
    assert report["g5_unique_gemini_images_queued"] >= 120
    assert report["g7_thread_a_jobs"] == 48   # 12 maps (10%) + 36 collage (30%) = 48
    assert report["g7_thread_b_wan_jobs"] == 72  # 72 video shots (60%)
    assert report["g8_3min_chunks_count"] == 4   # Four 3-minute chunks (0-3, 3-6, 6-9, 9-12)


def test_anti_crop_padding_rejects_duplicate_shot_prompts():
    script_path = REPO_ROOT / "jobs" / "ep_waterloo_12min" / "production_script.json"
    script_doc = json.loads(script_path.read_text(encoding="utf-8"))
    # Force shot 1 to reuse shot 0's prompt
    script_doc["shots"][1]["image_prompt"]["start_frame_prompt"] = (
        script_doc["shots"][0]["image_prompt"]["start_frame_prompt"]
    )
    plan = extract_complete_asset_plan(script_doc)
    assert len(plan["validation_errors"]) == 1
    assert plan["validation_errors"][0]["rule"] == "PV-NO-CROP-PADDING"


def test_wan_optimizer_duration_and_dialogue_cost_gate():
    assert seconds_to_wan_frames(4.0) == 97
    assert seconds_to_wan_frames(5.0) == 121
    assert seconds_to_wan_frames(9.0) == 121  # Capped at 5.0s (121 frames)

    short_line = {"line_id": "L1", "speaker_type": "character", "estimated_duration_seconds": 4.5}
    mcu_shot = {"shot_id": "SH1", "camera_spec": {"shot_size": "medium_close_up"}, "keyframe_plan": {"needs_end_frame": False}}
    res_short = evaluate_dialogue_render_route(short_line, mcu_shot)
    assert res_short["use_rendered_lipsync"] is False

    long_monologue = {"line_id": "L2", "speaker_type": "character", "estimated_duration_seconds": 12.0}
    res_long = evaluate_dialogue_render_route(long_monologue, mcu_shot)
    assert res_long["use_rendered_lipsync"] is True
    assert res_long["recommended_mode"] == "WAN_S2V_LIPSYNC"



def test_wan_chain_minus_5_and_system_logic_check():
    from explainer_engine.aivideo.wan_optimizer import compute_continuation_splice_spec
    from explainer_engine.production.chunked_edit import build_seamless_continuation_edl
    from explainer_engine.orchestration.rule_enforcer import run_system_logic_check

    spec = compute_continuation_splice_spec(97, 97, offset_from_end=5, fps=24)
    assert spec["extracted_start_frame_index_0based"] == 92
    assert spec["prev_clip_play_frames_before_splice"] == 92
    assert spec["prev_clip_dropped_tail_frames"] == 5
    assert spec["combined_seamless_frames"] == 189

    edl = build_seamless_continuation_edl([
        {"shot_id": "S01_SH001_A", "frames": 97, "continues_from_previous": False},
        {"shot_id": "S01_SH001_B", "frames": 97, "continues_from_previous": True},
    ])
    assert edl[0]["play_frames"] == 92
    assert edl[1]["timeline_start_frame"] == 92
    assert edl[1]["timeline_end_frame"] == 189

    script_doc = json.loads((REPO_ROOT / "jobs/ep_waterloo_12min/production_script.json").read_text(encoding="utf-8"))
    check_report = run_system_logic_check(script_doc)
    assert check_report["overall_status"] == "PASS"
    assert check_report["1_video_planning_logic"]["wan_chain_minus_5_verified"] is True
