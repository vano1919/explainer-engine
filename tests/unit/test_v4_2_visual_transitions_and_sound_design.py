"""Comprehensive Unit Tests for Explainer Engine v4.2 Visual Production, Transitions & Environmental Sound Design."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from explainer_engine.aivideo.wan_optimizer import (
    compute_multifactor_shot_routing,
    evaluate_zero_cost_allowance_and_policy,
)
from explainer_engine.audio import foley
from explainer_engine.audio.environmental_sound_design import (
    render_continuous_environmental_soundscape,
)
from explainer_engine.audio.sfx_planner import (
    build_shot_sound_design_metadata,
)
from explainer_engine.edit.cinematic_transitions import (
    TRANSITION_TYPES,
    render_transition_frame_pair,
    select_optimal_cinematic_transition,
)
from explainer_engine.infographics.python_map_and_chart_engine import (
    INFO_GRAPHIC_SUBTYPES,
    build_10pct_infographic_spec,
    classify_10pct_infographic_subtype,
    render_10pct_infographic_clip_mp4,
)
from explainer_engine.production.cinematic_image_animator import (
    infer_atmospheric_effects_for_shot,
    render_cinematic_25d_clip_from_image,
)
from explainer_engine.production.parallax import (
    estimate_synthetic_depth_and_face_safe_mask,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TOBA_SCRIPT = REPO_ROOT / "jobs" / "ep_toba_74000bce_12min" / "ep_toba_74000bce_12min_production_script.json"


def test_10pct_python_infographics_all_templates_and_zoom_target(tmp_path: Path) -> None:
    """Verify all 8 documentary infographic subtypes classify, build specs with zoom_target_xy, and render 24fps MP4."""
    assert len(INFO_GRAPHIC_SUBTYPES) == 8
    for subtype in INFO_GRAPHIC_SUBTYPES:
        shot = {
            "shot_id": "S01_SH002",
            "segment_id": "S01",
            "target_duration_seconds": 1.5,
            "visual_type": "map_visualization",
            "generation_mode": "TACTILE_MAP",
            "infographic_subtype": subtype,
            "narrative_purpose": f"Visualize {subtype} with exact data 100,000 to 5,000",
            "action_start_state": "Baseline map state",
            "action_end_state": "Final vector expansion",
            "zoom_target_xy": [0.62, 0.44],
        }
        assert classify_10pct_infographic_subtype(shot) == subtype
        spec = build_10pct_infographic_spec(shot, spoken_text="From 100,000 down to 5,000 survivors.")
        assert spec["infographic_subtype"] == subtype
        assert spec["zoom_target_xy"] == [0.62, 0.44]
        assert spec["fps"] == 24

    out_mp4 = tmp_path / "test_map.mp4"
    res = render_10pct_infographic_clip_mp4(
        shot={
            "shot_id": "S01_SH002",
            "segment_id": "S01",
            "target_duration_seconds": 1.2,
            "visual_type": "map_visualization",
            "generation_mode": "TACTILE_MAP",
            "narrative_purpose": "Tactical map and troop movement vectors across Sumatra",
        },
        out_mp4_path=out_mp4,
        width=640,
        height=360,
        fps=24,
    )
    assert out_mp4.is_file() and res["bytes"] > 1000
    assert res["cost_usd"] == 0.0
    assert res["zoom_target_xy"] == [0.58, 0.48]


def test_30pct_python_25d_cinematic_image_animator_preserves_faces(tmp_path: Path) -> None:
    """Verify existing generated images animate with 2.5D depth parallax, face-safe mask, and atmospheric particles."""
    src_png = tmp_path / "anchor_plate.png"
    img = Image.new("RGB", (640, 360), (28, 34, 48))
    img.save(src_png)

    depth, face_mask = estimate_synthetic_depth_and_face_safe_mask(img, protect_center_character=True)
    assert depth.shape == (360, 640)
    assert face_mask.shape == (360, 640)
    assert float(face_mask.max()) > 0.8

    shot = {
        "shot_id": "S01_SH003",
        "segment_id": "S01",
        "target_duration_seconds": 1.2,
        "visual_type": "composed_illustration",
        "generation_mode": "COLLAGE_STILL",
        "narrative_purpose": "Volcanic ash and glowing embers drift past the survivor in candlelight",
        "action_start_state": "Survivor holds torch in ash storm",
        "action_end_state": "Camera slowly pushes in through smoke",
        "lighting_and_time": "Deep chiaroscuro torchlight and volcanic ash",
        "video_prompt": {"parallax_preset": "dolly_in", "motion_prompt": "Slow push in through ash"},
    }
    effects = infer_atmospheric_effects_for_shot(shot)
    assert "ash" in effects and "fire_flicker" in effects

    out_mp4 = tmp_path / "anim_25d.mp4"
    res = render_cinematic_25d_clip_from_image(
        shot=shot,
        source_image_path=src_png,
        out_mp4_path=out_mp4,
        width=640,
        height=360,
        fps=24,
        protect_character_faces=True,
    )
    assert out_mp4.is_file() and res["bytes"] > 1000
    assert res["reused_existing_image"] is True
    assert res["protect_character_faces"] is True
    assert res["face_safe_mask_active"] is True
    assert res["cost_usd"] == 0.0


def test_multifactor_shot_router_and_zero_cost_policy() -> None:
    """Verify shot routing evaluates 10 factors (never duration alone) and enforces Zero-Additional-Cost policy."""
    policy = evaluate_zero_cost_allowance_and_policy(
        verified_free_gemini_video_clips=0,
        authorized_wan_credit_usd=0.0,
        allow_paid_api_fallback=False,
    )
    assert policy["zero_additional_cost_enforced"] is True
    assert policy["gemini_video_free_tier_default"] is False

    # Short 2.0s shot with heavy battle/cavalry action must score high motion complexity despite short duration
    heavy_short_shot = {
        "shot_id": "S02_SH001",
        "segment_id": "S02",
        "target_duration_seconds": 2.0,
        "visual_type": "cinematic_video",
        "generation_mode": "WAN_FLF2V",
        "character_ids": ["char_a", "char_b"],
        "narrative_purpose": "Cavalry charge clashes with infantry in volcanic explosion shockwave",
        "action_start_state": "Cavalry gallops forward",
        "action_end_state": "Swords clash on ridge",
        "camera_spec": {"camera_move": "tracking_shot", "shot_size": "wide"},
        "keyframe_plan": {"needs_end_frame": True},
        "video_prompt": {"motion_prompt": "Cavalry charge and explosion"},
    }
    route_zero_cost = compute_multifactor_shot_routing(
        heavy_short_shot,
        available_reusable_images=["REF_01.jpg", "REF_03.jpg"],
        verified_free_gemini_video_clips=0,
        authorized_wan_credit_usd=0.0,
        allow_paid_api_fallback=False,
    )
    assert route_zero_cost["routed_by_duration_only"] is False
    assert route_zero_cost["factors"]["motion_complexity_score"] >= 0.65
    assert route_zero_cost["planned_cloud_engine"] == "WAN_2_1_HEAVY_ACTION_ENGINE"
    assert route_zero_cost["paid_api_invoked"] is False
    assert route_zero_cost["estimated_cost_usd"] == 0.0


def test_cinematic_transitions_selection_and_rendering() -> None:
    """Verify map-to-location zoom-through, number-to-scene morph, smoke wipe, and object wipe transitions."""
    assert len(TRANSITION_TYPES) >= 7
    shot_map = {
        "shot_id": "S01_SH001",
        "segment_id": "S01",
        "location_id": "loc_map_table",
        "visual_type": "map_visualization",
        "generation_mode": "TACTILE_MAP",
        "infographic_subtype": "tactical_map_and_troop_movement",
        "zoom_target_xy": [0.60, 0.45],
        "camera_spec": {"camera_move": "push_in", "shot_size": "top_down_map"},
    }
    shot_scene = {
        "shot_id": "S01_SH002",
        "segment_id": "S01",
        "location_id": "loc_toba_caldera",
        "visual_type": "cinematic_video",
        "generation_mode": "WAN_I2V",
        "narrative_purpose": "Eruption plume rises over Lake Toba",
        "camera_spec": {"camera_move": "push_in", "shot_size": "extreme_wide"},
    }
    trans = select_optimal_cinematic_transition(shot_map, shot_scene)
    assert trans["transition_type"] == "map_to_location_zoom_through"
    assert trans["transition_frames"] > 0
    assert trans["audio_j_cut_prelap_sec"] >= 0.40

    frame_a = Image.new("RGB", (320, 180), (20, 40, 70))
    frame_b = Image.new("RGB", (320, 180), (180, 90, 40))
    for t_type in TRANSITION_TYPES:
        out_im = render_transition_frame_pair(frame_a, frame_b, t_type, progress_u=0.5)
        assert out_im.size == (320, 180)


def test_environmental_sound_design_metadata_and_continuous_soundscape(tmp_path: Path) -> None:
    """Verify Section 7.4 shot sound-design metadata, procedural foley generators, and continuous stereo soundscape."""
    for key in (
        "wind_howl", "rain_downpour", "thunder_rumble", "fire_crackle_bed",
        "horse_hooves_gallop", "sword_metal_clash", "armor_march_clink",
        "door_wood_creak", "crowd_battle_murmur", "forest_birds_wind",
        "ship_water_hull_creak", "volcanic_explosion_debris",
    ):
        assert key in foley.BUILD
        _, fn, seeds = foley.BUILD[key]
        samples = fn(seeds[0])
        assert len(samples) > 1000 and float(abs(samples).max()) > 0.05

    doc = json.loads(TOBA_SCRIPT.read_text(encoding="utf-8"))
    first_shot = doc["shots"][0]
    sd_meta = build_shot_sound_design_metadata(first_shot, shot_start_sec=0.0)
    required_keys = {
        "environment", "weather", "surface", "physical_actions", "sound_events",
        "event_timestamps", "sound_source", "spatial_context", "continuity_group",
        "suggested_intensity", "mixing_priority",
    }
    assert required_keys.issubset(set(sd_meta.keys()))

    mini_doc = {
        "episode_id": "test_audio_continuity",
        "segments": doc["segments"][:1],
        "audio_lines": doc["audio_lines"][:3],
        "shots": doc["shots"][:3],
    }
    out_wav = tmp_path / "soundscape.wav"
    rep = render_continuous_environmental_soundscape(mini_doc, out_wav_path=out_wav)
    assert out_wav.is_file() and out_wav.stat().st_size > 48000
    assert rep["channels"] == 2
    assert rep["sample_rate_hz"] == 48000
    assert rep["sidechain_ducking_applied"] is True
    assert rep["continuous_ambience_groups_count"] >= 1
    assert rep["spot_foley_cues_placed"] >= 3
