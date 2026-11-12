"""Unit tests for TODO-08: v4.0 shot prompt, scene, and story causal-chain lints."""

from __future__ import annotations

import copy

from explainer_engine.scripting import scene_lint, shot_prompt_lint, story_lint
from tests.unit.test_schemas_v4 import _sample_v4_production_script


def test_v4_valid_script_passes_shot_story_and_scene_lints() -> None:
    doc = _sample_v4_production_script()
    assert shot_prompt_lint.check_v4_script(doc) == []
    assert story_lint.lint(doc) == []
    assert scene_lint.check(doc) == []


def test_shot_prompt_lint_rejects_overconditioned_or_leaky_prompts() -> None:
    doc = _sample_v4_production_script()

    # 1. Over-conditioned primary_action_count > 1 and camera_move_count > 1
    bad = copy.deepcopy(doc)
    bad["shots"][0]["video_prompt"]["primary_action_count"] = 2
    bad["shots"][0]["video_prompt"]["camera_move_count"] = 2
    bad["shots"][0]["video_prompt"]["motion_prompt"] = "Camera pans left and dollies in while Napoleon runs and jumps."
    rules = {f["rule"] for f in shot_prompt_lint.check_v4_script(bad) if f["severity"] == "FAIL"}
    assert "KP-V4-ACTION" in rules
    assert "KP-V4-CAMERA" in rules

    # 2. Missing style_anchor_token
    bad_style = copy.deepcopy(doc)
    bad_style["shots"][0]["image_prompt"]["start_frame_prompt"] = "Medium close-up of Napoleon holding a brass spyglass."
    rules_style = {f["rule"] for f in shot_prompt_lint.check_v4_script(bad_style) if f["severity"] == "FAIL"}
    assert "KP-V4-STYLE" in rules_style

    # 3. Spoken dialogue leaked into video_prompt
    bad_leak = copy.deepcopy(doc)
    bad_leak["shots"][0]["video_prompt"]["motion_prompt"] = (
        'Subject: Napoleon says "Wheel the vanguard west toward Chapelle-Saint-Lambert!" Camera: static locked frame.'
    )
    rules_leak = {f["rule"] for f in shot_prompt_lint.check_v4_script(bad_leak) if f["severity"] == "FAIL"}
    assert "KP-V4-DIALOGUE-LEAK" in rules_leak

    # 4. Invalid WAN_CONTROL multi-modality or missing escalation_reason
    bad_ctrl = copy.deepcopy(doc)
    bad_ctrl["shots"][0]["generation_mode"] = "WAN_CONTROL"
    bad_ctrl["shots"][0]["keyframe_plan"]["needs_end_frame"] = False
    bad_ctrl["shots"][0]["selective_control"] = {
        "control_modality": ["openpose", "depth"],
        "control_source_path": "02_keyframes/shots/S04_SH001_depth.png",
        "escalation_reason": "",
    }
    rules_ctrl = {f["rule"] for f in shot_prompt_lint.check_v4_script(bad_ctrl) if f["severity"] == "FAIL"}
    assert "KP-V4-CONTROL" in rules_ctrl


def test_story_lint_v4_catches_broken_causal_chain() -> None:
    doc = _sample_v4_production_script()
    seg_s05 = copy.deepcopy(doc["segments"][0])
    seg_s05["segment_id"] = "S05"
    seg_s05["cause_from_segment_id"] = "S01"  # Should be S04!
    seg_s05["effect_to_segment_id"] = None
    doc["segments"][0]["effect_to_segment_id"] = "S05"
    doc["segments"].append(seg_s05)

    findings = story_lint.lint(doc)
    assert any(f["rule"] == "ST-V4-CAUSE" and f["severity"] == "FAIL" for f in findings)
