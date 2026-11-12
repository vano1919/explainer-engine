"""Unit tests for Story-First Accordion Pacing & Anti-Robotic Linter Gates (D-125).

Verifies that:
1. Organic scripts (`pilot_60s_waterloo.json` and `ep_waterloo_12min/production_script.json`) pass with 0 FAIL.
2. Robotic loop-generated scripts (modeled on `ep_fortress_sterling_12min` with constant 6.0s shots,
   identical 60.0s segments, repeated 10-shot mode arrays, constant dialogue indices, monotonous sentence lengths,
   and template phrases like 'Initial composition of' / 'Completed motion cadence' / 'Cinematic sequence at loc_')
   are caught and rejected with FAIL across all 6 new gates.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from explainer_engine.aivideo.wan_optimizer import plan_story_driven_shot_render
from explainer_engine.orchestration.rule_enforcer import run_all_gate_audits
from explainer_engine.scripting import shot_prompt_lint, story_lint

ROOT = Path(__file__).resolve().parents[2]


def test_organic_waterloo_scripts_pass_all_story_first_gates() -> None:
    pilot = json.loads((ROOT / "tests/fixtures/pilot_60s_waterloo.json").read_text(encoding="utf-8"))
    ep12 = json.loads((ROOT / "jobs/ep_waterloo_12min/production_script.json").read_text(encoding="utf-8"))

    assert shot_prompt_lint.check_v4_script(pilot) == []
    assert shot_prompt_lint.check_v4_script(ep12) == []
    audit = run_all_gate_audits(ep12)
    assert audit["status"] == "PASS"
    assert audit["total_issues"] == 0


def test_robotic_fortress_sterling_clone_triggers_all_anti_robotic_gates() -> None:
    ep12 = json.loads((ROOT / "jobs/ep_waterloo_12min/production_script.json").read_text(encoding="utf-8"))
    robotic = copy.deepcopy(ep12)

    # 1. Force constant 60.0s segments and identical 10-shot mode sequences (like ep_fortress_sterling_12min)
    fixed_pattern = [
        "COLLAGE_STILL", "TACTILE_MAP", "WAN_I2V", "WAN_FLF2V", "WAN_I2V",
        "WAN_FLF2V", "COLLAGE_STILL", "WAN_I2V", "WAN_I2V", "COLLAGE_STILL",
    ]
    new_shots = []
    new_lines = []
    idx = 0
    for seg_i, seg in enumerate(robotic["segments"]):
        seg_id = seg["segment_id"]
        seg["target_duration_seconds"] = 60.0
        for sh_i in range(10):
            base_sh = copy.deepcopy(ep12["shots"][idx % len(ep12["shots"])])
            base_ln = copy.deepcopy(ep12["audio_lines"][idx % len(ep12["audio_lines"])])
            sh_id = f"{seg_id}_SH{sh_i + 1:03d}"
            ln_id = f"{seg_id}_L{sh_i + 1:03d}"
            base_sh["shot_id"] = sh_id
            base_sh["segment_id"] = seg_id
            base_sh["target_duration_seconds"] = 6.0  # Metronome 6.0s
            base_sh["generation_mode"] = fixed_pattern[sh_i]
            base_sh["visual_type"] = (
                "map_visualization" if fixed_pattern[sh_i] == "TACTILE_MAP"
                else ("composed_illustration" if fixed_pattern[sh_i] == "COLLAGE_STILL" else "cinematic_video")
            )
            base_sh["keyframe_plan"]["needs_end_frame"] = fixed_pattern[sh_i] == "WAN_FLF2V"
            base_sh["keyframe_plan"]["end_frame_reason"] = "End frame" if fixed_pattern[sh_i] == "WAN_FLF2V" else None
            base_sh["video_prompt"]["parallax_preset"] = "dolly_in" if fixed_pattern[sh_i] in ("COLLAGE_STILL", "TACTILE_MAP") else None
            base_sh["audio_line_ids"] = [ln_id]
            # Inject loop boilerplate and raw IDs
            base_sh["action_start_state"] = f"Initial composition of scene for {sh_id}"
            base_sh["action_end_state"] = f"Completed motion cadence for {sh_id}"
            base_sh["image_prompt"]["start_frame_prompt"] = (
                f"{robotic['world_bible']['style_anchor_token']}. Cinematic sequence at loc_ridge with char_napoleon, frame {sh_id}"
            )
            base_sh["image_prompt"]["end_frame_prompt"] = (
                f"{robotic['world_bible']['style_anchor_token']}. End frame for {sh_id}" if fixed_pattern[sh_i] == "WAN_FLF2V" else None
            )
            new_shots.append(base_sh)

            # Force identical character dialogue slots (sh_i in (2, 3, 4)) and monotonous 19-word sentences
            base_ln["line_id"] = ln_id
            base_ln["segment_id"] = seg_id
            base_ln["speaker_type"] = "character" if sh_i in (2, 3, 4) else "narrator"
            base_ln["estimated_duration_seconds"] = 6.0
            base_ln["text"] = "In nineteen forty-six the exhausted imperial treasury faced an unprecedented structural crisis across every single overseas colonial territory."
            new_lines.append(base_ln)
            idx += 1

    robotic["shots"] = new_shots
    robotic["audio_lines"] = new_lines

    issues = shot_prompt_lint.check_v4_script(robotic)
    rules_hit = {i["rule"] for i in issues if i["severity"] == "FAIL"}

    assert "KP-NO-LOOP-BOILERPLATE" in rules_hit
    assert "PV-NO-METRONOME-DURATIONS" in rules_hit
    assert "PV-NO-METRONOME-SEGMENTS" in rules_hit
    assert "PV-NO-COOKIE-CUTTER-SEGMENTS" in rules_hit
    assert "PV-NO-COOKIE-CUTTER-DIALOGUE" in rules_hit
    assert "YT-04-BURSTINESS" in rules_hit


def test_story_driven_shot_render_only_chains_frame_minus_5_above_5_seconds() -> None:
    short_video = {"shot_id": "S01_SH001", "target_duration_seconds": 3.4, "generation_mode": "WAN_I2V", "visual_type": "cinematic_video"}
    long_video = {"shot_id": "S01_SH002", "target_duration_seconds": 6.8, "generation_mode": "WAN_I2V", "visual_type": "cinematic_video"}
    long_still = {"shot_id": "S01_SH003", "target_duration_seconds": 7.2, "generation_mode": "COLLAGE_STILL", "visual_type": "composed_illustration"}

    r_short = plan_story_driven_shot_render(short_video)
    assert r_short["requires_frame_minus_5_chain"] is False
    assert len(r_short["sub_clips"]) == 1

    r_long = plan_story_driven_shot_render(long_video)
    assert r_long["requires_frame_minus_5_chain"] is True
    assert len(r_long["sub_clips"]) == 2
    assert r_long["splice_spec"]["rule"] == "WAN-CHAIN-MINUS-5"

    r_still = plan_story_driven_shot_render(long_still)
    assert r_still["requires_frame_minus_5_chain"] is False
    assert r_still["story_duration_sec"] == 7.2
