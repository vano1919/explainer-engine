"""Unit tests for TODO-03: v4.0 JSON Schemas (production_script, shot_route, wan_job, keyframe_manifest, render_telemetry)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "explainer_engine" / "schemas"


def _load_schema(name: str) -> dict:
    schema = json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    return schema


def _sample_v4_production_script() -> dict:
    return {
        "schema_version": "4.0.0",
        "episode_id": "ep_waterloo_napoleon_victory",
        "title": "What If Napoleon Had Crushed Wellington at Waterloo?",
        "what_if_premise": "On June 18, 1815, Marshal Grouchy marches toward the sound of the guns at Wavre, intercepting Blucher's Prussians.",
        "target_duration_seconds": 720,
        "fps": 24,
        "audio_balance_target": {
            "narrator_ratio_min": 0.70,
            "narrator_ratio_max": 0.80,
            "dialogue_ratio_min": 0.20,
            "dialogue_ratio_max": 0.30,
        },
        "visual_mix_target": {
            "cinematic_video_target": 0.60,
            "composed_illustration_target": 0.30,
            "map_visualization_target": 0.10,
        },
        "historical_dossier_ref": "jobs/ep_waterloo_napoleon_victory/01_script/research_dossier.md",
        "world_bible": {
            "style_anchor_token": "Luminescent Chiaroscuro historical docudrama illustration",
            "characters": [
                {
                    "character_id": "char_napoleon_1815",
                    "name": "Napoleon Bonaparte",
                    "historical_role": "Emperor of the French",
                    "fixed_appearance_prompt": "Luminescent Chiaroscuro portrait of Napoleon Bonaparte in 1815, grey chasseur overcoat, bicorne hat, sharp ink contours",
                    "costume_continuity_notes": "Dark green Chasseurs-a-Cheval coat under grey riding overcoat",
                    "voice_profile_id": "voice_napoleon",
                    "reference_sheet_path": "02_keyframes/assets/char_napoleon_1815_turnaround.png",
                }
            ],
            "locations": [
                {
                    "location_id": "loc_waterloo_ridge",
                    "name": "Mont-Saint-Jean Ridge",
                    "era_and_geography": "Belgium, June 18, 1815",
                    "fixed_environment_prompt": "Rain-swept muddy ridge at Mont-Saint-Jean, rolling gun-smoke, soggy rye fields under leaden overcast sky",
                    "lighting_palette": "Cold slate grey dawn with warm cannon-flash highlights",
                    "anchor_image_path": "02_keyframes/assets/loc_waterloo_ridge_anchor.png",
                }
            ],
            "props": [
                {
                    "prop_id": "prop_brass_spyglass",
                    "name": "Imperial Brass Spyglass",
                    "fixed_prop_prompt": "Telescoping nineteenth-century engraved brass field spyglass",
                    "anchor_image_path": "02_keyframes/assets/prop_brass_spyglass_anchor.png",
                }
            ],
        },
        "phases": [
            {
                "phase_id": "Z2",
                "title": "The Point of Divergence",
                "target_window": "2:00-4:00",
                "segment_ids": ["S04"],
                "narrative_objective": "Grouchy turns west at Wavre and pins the Prussian flank.",
            }
        ],
        "segments": [
            {
                "segment_id": "S04",
                "phase_id": "Z2",
                "title": "Marching to the Sound of the Guns",
                "narrative_purpose": "Establish the counterfactual turn at Wavre and its immediate tactical impact.",
                "target_duration_seconds": 60.0,
                "factual_status": "divergence_point",
                "cause_from_segment_id": "S03",
                "effect_to_segment_id": "S05",
            }
        ],
        "audio_lines": [
            {
                "line_id": "S04_L001",
                "segment_id": "S04",
                "speaker_type": "narrator",
                "speaker_id": "narrator_main",
                "addressee_id": None,
                "delivery_direction": "grave, measured documentary pacing",
                "text": "What if at 11:30 AM, Marshal Grouchy turns his thirty thousand men west to save the empire?",
                "register_type": "plausible_counterfactual_inference",
                "citation_ids": ["CITE-04"],
                "estimated_duration_seconds": 5.0,
                "requires_visible_lipsync": False,
            }
        ],
        "shots": [
            {
                "shot_id": "S04_SH001",
                "segment_id": "S04",
                "target_duration_seconds": 5.0,
                "narrative_purpose": "Show Napoleon lowering his brass spyglass as French columns hold the eastern treeline.",
                "visual_type": "cinematic_video",
                "generation_mode": "WAN_FLF2V",
                "location_id": "loc_waterloo_ridge",
                "character_ids": ["char_napoleon_1815"],
                "prop_ids": ["prop_brass_spyglass"],
                "audio_line_ids": ["S04_L001"],
                "action_start_state": "Napoleon holds brass spyglass raised to his right eye",
                "action_end_state": "Napoleon lowers the spyglass to his side with a decisive nod",
                "camera_spec": {
                    "shot_size": "medium_close_up",
                    "vertical_angle": "eye_level_0",
                    "horizontal_azimuth_deg": 315,
                    "camera_move": "static",
                    "multiangle_token": "<sks> front-left quarter view eye-level shot medium close-up",
                },
                "screen_composition": {
                    "foreground": "Rain droplets on brass spyglass barrel",
                    "midground": "Napoleon in grey overcoat facing screen-right",
                    "background": "Drifting cannon smoke over Mont-Saint-Jean ridge",
                    "screen_direction_notes": "Napoleon looks left-to-right toward eastern woods (180-deg axis preserved)",
                },
                "lighting_and_time": "Overcast midday with diffused silver light",
                "continuity_refs": {
                    "reuse_location_anchor": True,
                    "inherit_from_previous_shot_id": None,
                },
                "keyframe_plan": {
                    "needs_start_frame": True,
                    "needs_end_frame": True,
                    "start_frame_source": "multiangle_from_anchor",
                    "end_frame_reason": "Bridges spyglass raised pose to lowered command pose for next cut.",
                },
                "image_prompt": {
                    "start_frame_prompt": "Luminescent Chiaroscuro historical docudrama illustration. Medium close-up, eye-level. Napoleon in grey overcoat holds brass spyglass to eye on muddy ridge.",
                    "end_frame_prompt": "Luminescent Chiaroscuro historical docudrama illustration. Medium close-up, eye-level. Napoleon lowers brass spyglass with a resolute expression.",
                    "negative_prompt": "photorealistic DSLR skin pores, 3D CGI plastic sheen, extra fingers, watermark, text banner",
                },
                "video_prompt": {
                    "motion_prompt": "Subject: Napoleon smoothly lowers the brass spyglass from his eye while rain drifts in the wind. Camera: static locked frame.",
                    "primary_action_count": 1,
                    "camera_move_count": 0,
                    "parallax_preset": None,
                },
                "selective_control": None,
                "transition_out": "hard_cut",
            }
        ],
    }


def test_production_script_v4_validates_and_rejects_invalid_constraints() -> None:
    schema = _load_schema("production_script.schema.json")
    valid_doc = _sample_v4_production_script()
    jsonschema.validate(valid_doc, schema)

    # 1. Reject primary_action_count > 1
    bad_actions = copy.deepcopy(valid_doc)
    bad_actions["shots"][0]["video_prompt"]["primary_action_count"] = 2
    try:
        jsonschema.validate(bad_actions, schema)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for primary_action_count > 1")

    # 2. Reject camera_move_count > 1
    bad_cam = copy.deepcopy(valid_doc)
    bad_cam["shots"][0]["video_prompt"]["camera_move_count"] = 2
    try:
        jsonschema.validate(bad_cam, schema)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for camera_move_count > 1")

    # 3. Reject WAN_FLF2V with needs_end_frame: False
    bad_flf = copy.deepcopy(valid_doc)
    bad_flf["shots"][0]["keyframe_plan"]["needs_end_frame"] = False
    try:
        jsonschema.validate(bad_flf, schema)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for WAN_FLF2V with needs_end_frame=False")

    # 4. Reject WAN_CONTROL without selective_control object
    bad_ctrl = copy.deepcopy(valid_doc)
    bad_ctrl["shots"][0]["generation_mode"] = "WAN_CONTROL"
    bad_ctrl["shots"][0]["keyframe_plan"]["needs_end_frame"] = False
    bad_ctrl["shots"][0]["selective_control"] = None
    try:
        jsonschema.validate(bad_ctrl, schema)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for WAN_CONTROL with selective_control=None")


def test_wan_job_schema_validates_and_enforces_local_and_mode_rules() -> None:
    schema = _load_schema("wan_job.schema.json")
    valid_job = {
        "job_id": "wan_ep_waterloo_S04_SH001",
        "episode_id": "ep_waterloo_napoleon_victory",
        "shot_id": "S04_SH001",
        "generation_mode": "WAN_FLF2V",
        "model_tier": "wan22_fun_5b_inp",
        "workflow_template_path": "workflows/comfyui/wan22_fun_inp_flf2v.json",
        "comfy_local_url": "http://127.0.0.1:8188",
        "start_image_path": "jobs/ep_waterloo/02_keyframes/shots/S04_SH001_start.png",
        "end_image_path": "jobs/ep_waterloo/02_keyframes/shots/S04_SH001_end.png",
        "single_control_input": None,
        "use_lightx2v_4step": False,
        "motion_prompt": "Napoleon smoothly lowers the brass spyglass.",
        "negative_prompt": "blurry, extra fingers, watermark",
        "width": 1280,
        "height": 720,
        "num_frames": 81,
        "fps": 24,
        "steps": 20,
        "cfg_scale": 5.0,
        "seed": 42001,
    }
    jsonschema.validate(valid_job, schema)

    # Reject non-localhost URL in wan_job
    bad_url = dict(valid_job, comfy_local_url="https://api.ltx-cloud.internal/v1/jobs")
    try:
        jsonschema.validate(bad_url, schema)
    except jsonschema.ValidationError:
        pass
    else:
        raise AssertionError("Expected ValidationError for non-localhost comfy_local_url")


def test_keyframe_manifest_and_render_telemetry_schemas_validate() -> None:
    kf_schema = _load_schema("keyframe_manifest.schema.json")
    rt_schema = _load_schema("render_telemetry.schema.json")
    sr_schema = _load_schema("shot_route.schema.json")

    valid_kf = {
        "schema_version": "1.0.0",
        "episode_id": "ep_waterloo_napoleon_victory",
        "generated_at_utc": "2026-11-09T10:00:00Z",
        "stage2_model_id": "qwen_image_edit_2511",
        "comfy_local_url": "http://127.0.0.1:8188",
        "assets": {
            "characters": [
                {
                    "asset_id": "char_napoleon_1815",
                    "path": "02_keyframes/assets/char_napoleon_1815_turnaround.png",
                    "sha256": "a" * 64,
                    "seed": 101,
                    "approved": True,
                }
            ],
            "locations": [],
            "props": [],
        },
        "shots": [
            {
                "shot_id": "S04_SH001",
                "generation_mode": "WAN_I2V",
                "needs_start_frame": True,
                "needs_end_frame": False,
                "start_frame_source": "new_master_anchor",
                "start_frame_path": "02_keyframes/shots/S04_SH001_start.png",
                "start_frame_sha256": "b" * 64,
                "start_frame_seed": 1001,
                "end_frame_path": None,
                "end_frame_sha256": None,
                "end_frame_seed": None,
                "approval_status": "KEYFRAME_APPROVED",
                "repair_attempts": 0,
                "repair_notes": None,
            }
        ],
    }
    jsonschema.validate(valid_kf, kf_schema)

    valid_telemetry = {
        "timestamp_utc": "2026-11-09T10:05:00Z",
        "episode_id": "ep_waterloo_napoleon_victory",
        "shot_id": "S04_SH001",
        "stage": "video_gen",
        "generation_mode": "WAN_I2V",
        "model_id": "wan22_fun_5b_inp",
        "use_lightx2v_4step": False,
        "attempt_number": 1,
        "wall_clock_seconds": 38.4,
        "peak_vram_mb": 11840.0,
        "status": "ACCEPTED",
        "failure_reason": None,
        "qa_metrics": {
            "duration_match": True,
            "frozen_frame_ratio": 0.0,
            "boundary_jump_score": 0.04,
        },
    }
    jsonschema.validate(valid_telemetry, rt_schema)

    valid_sr_v3 = {
        "schema": "shot_route/3",
        "episode_id": "ep_waterloo_napoleon_victory",
        "fps": 24,
        "routes": [
            {
                "shot_id": "S04_SH001",
                "route_type": "WAN_I2V",
                "needs_end_frame": False,
                "start_frame_path": "02_keyframes/shots/S04_SH001_start.png",
                "end_frame_path": None,
                "wan_job_path": "03_video/wan_jobs_manifest.json",
            }
        ],
    }
    jsonschema.validate(valid_sr_v3, sr_schema)
