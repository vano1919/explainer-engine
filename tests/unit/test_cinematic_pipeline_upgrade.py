"""Unit and integration tests for photo-first LTX loop, docudrama structure, unified style bible, and new skills."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import style_bible as SB
from explainer_engine.governance import agent_skills_lint as ASL
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator
from explainer_engine.scripting import docudrama_structure as DS
from explainer_engine.videolane import ltx_loop as LL


def _make_png(path: Path, color: tuple[int, int, int]) -> Path:
    Image.new("RGB", (64, 36), color).save(path)
    return path


def test_ltx_handles_and_8n_plus_1_quantization():
    budget = LL.compute_clip_timing_with_handles(3.5)
    assert budget.head_handle_s == 0.5
    assert budget.tail_handle_s == 0.5
    assert budget.raw_total_seconds == 4.5
    assert (budget.ltx_frames - 1) % 8 == 0
    assert budget.ltx_frames >= 108  # 4.5s * 24fps = 108 -> quantized up to 113
    assert budget.trim_in_s == 0.5
    assert budget.trim_out_s == 4.0


def test_ltx_photo_grounded_prompt_binds_to_actual_pixels_and_camera_vocab(tmp_path: Path):
    img = _make_png(tmp_path / "shot1.png", (40, 60, 80))
    obs = LL.PhotoObservation(
        photo_path=str(img),
        photo_sha256=LL.sha256_file(img),
        observed_subjects=["Commander Vance", "field map"],
        observed_lighting="warm lantern side-light",
        observed_composition="medium two-shot across linen table",
        observed_environment="rainy 1914 canvas command tent",
    )
    prompt = LL.build_photo_grounded_prompt(
        obs,
        camera_move="zoom_in",
        action_beat="Vance leans forward and marks the river crossing",
        acting_style="restrained documentary realism",
        spoken_line="We cross at dawn.",
        speaker_name="Vance",
        voice_description="weathered baritone",
        ambient_sound="rain on canvas",
    )
    assert "warm lantern side-light" in prompt
    assert 'Vance says in weathered baritone: "We cross at dawn."' in prompt

    # Mutating the photo on disk invalidates the stale observation (prevents photo-prompt drift!)
    _make_png(img, (200, 10, 10))
    with pytest.raises(ContractError, match="SHA-256 mismatch"):
        LL.build_photo_grounded_prompt(
            obs,
            camera_move="zoom_in",
            action_beat="leans forward",
            acting_style="restrained",
        )


def test_ltx_mode_router_enforces_flf2v_and_chain_drift_cap():
    assert LL.select_ltx_mode({"scene_id": "S1", "end_image_path": "end.png"}) == "flf2v"
    assert LL.select_ltx_mode({"scene_id": "S1", "blender_layout_pass": "depth.mp4"}) == "ic_lora_layout"
    assert (
        LL.select_ltx_mode(
            {"scene_id": "S1", "continue_from_previous": True},
            prev_scene_id="S1",
            chain_depth=2,
            has_upscaled_tail=True,
        )
        == "last_frame_continuation"
    )
    # Chain depth at MAX_CHAIN_DEPTH resets to fresh keyframe to prevent cumulative drift
    assert (
        LL.select_ltx_mode(
            {"scene_id": "S1", "continue_from_previous": True},
            prev_scene_id="S1",
            chain_depth=LL.MAX_CHAIN_DEPTH,
            has_upscaled_tail=True,
        )
        == "new_keyframe_i2v"
    )


def test_continuous_autonomous_shot_loop_retry_qa_2k_upscale_and_tail_chaining(tmp_path: Path):
    p1 = _make_png(tmp_path / "s1_start.png", (20, 40, 60))
    p3_start = _make_png(tmp_path / "s3_start.png", (60, 40, 20))
    p3_end = _make_png(tmp_path / "s3_end.png", (80, 60, 40))

    def observer(img: Path, _shot: dict) -> LL.PhotoObservation:
        return LL.PhotoObservation(
            photo_path=str(img),
            photo_sha256=LL.sha256_file(img),
            observed_subjects=["Officer"],
            observed_lighting="overcast dawn",
            observed_composition="medium close-up",
            observed_environment="muddy trench",
        )

    def generator(req: dict) -> Path:
        out = tmp_path / f"{req['shot_id']}_a{req['attempt']}.mp4"
        out.write_bytes(b"mp4-stub")
        return out

    def qa(_clip: Path, req: dict) -> dict:
        # Shot 1 fails first attempt, passes second attempt
        if req["shot_id"] == "SH1" and req["attempt"] == 1:
            return {"verdict": "FAIL", "reason": "minor flicker"}
        return {"verdict": "PASS"}

    def tail_extract(clip: Path) -> Path:
        return _make_png(tmp_path / f"{clip.stem}_tail.png", (30, 50, 70))

    def upscale(path: Path, backend: str) -> Path:
        assert backend == "realesrgan_x2"
        out = tmp_path / f"{path.stem}_2k{path.suffix}"
        if path.suffix == ".png":
            _make_png(out, (35, 55, 75))
        else:
            out.write_bytes(b"2k-mp4")
        return out

    shots = [
        {"shot_id": "SH1", "scene_id": "SC1", "editorial_seconds": 3.0, "start_image_path": str(p1), "camera_move": "truck"},
        {"shot_id": "SH2", "scene_id": "SC1", "editorial_seconds": 3.5, "continue_from_previous": True, "camera_move": "zoom_in"},
        {"shot_id": "SH3", "scene_id": "SC2", "editorial_seconds": 4.0, "start_image_path": str(p3_start), "end_image_path": str(p3_end), "camera_move": "truck_zoom_in"},
    ]
    res = LL.run_continuous_shot_loop(
        shots,
        vision_observer=observer,
        video_generator=generator,
        qa_reviewer=qa,
        tail_extractor=tail_extract,
        upscaler_2k=upscale,
    )
    assert res["status"] == "PASS"
    assert res["target_resolution"] == "2560x1440"
    assert res["steps"][0]["attempts"] == 2
    assert res["steps"][1]["ltx_mode"] == "last_frame_continuation"
    assert res["steps"][1]["start_image_path"].endswith("_tail_2k.png")
    assert res["steps"][2]["ltx_mode"] == "flf2v"


def test_docudrama_structure_enforces_2_to_3_dramatic_scenes_and_visual_bridges():
    good_plan = {
        "scenes": [
            {"scene_id": "N1", "scene_role": "narration", "primary_route": "map_action", "duration_s": 45.0, "visual_bridges": [{"kind": "date_location_card"}, {"kind": "tactical_map_overlay"}]},
            {"scene_id": "D1", "scene_role": "dramatic_showcase", "primary_route": "video", "duration_s": 85.0, "dialogue_turns": 6},
            {"scene_id": "N2", "scene_role": "narration", "primary_route": "still_25d", "duration_s": 40.0, "visual_bridges": [{"kind": "kinetic_callout"}, {"kind": "archival_quote_highlight"}]},
            {"scene_id": "D2", "scene_role": "dramatic_showcase", "primary_route": "video", "duration_s": 95.0, "dialogue_turns": 7},
        ]
    }
    assert DS.validate_docudrama_structure(good_plan)["status"] == "PASS"

    bad_plan = {
        "scenes": [
            {"scene_id": "D1", "scene_role": "dramatic_showcase", "primary_route": "video", "duration_s": 12.0, "dialogue_turns": 1},
            {"scene_id": "N1", "scene_role": "narration", "primary_route": "video", "duration_s": 60.0, "visual_bridges": []},
        ]
    }
    rep = DS.validate_docudrama_structure(bad_plan)
    assert rep["status"] == "FAIL"
    codes = {i["code"] for i in rep["issues"]}
    assert {"DOCU-SCENE-COUNT", "DOCU-SCENE-DURATION", "DOCU-NO-THROWAWAY-LINES", "DOCU-LTX-BUDGET-LEAK", "DOCU-BRIDGE-DENSITY"} <= codes

    good_spot = {
        "based_on_assembled_video": True,
        "assembled_video_sha256": "a" * 64,
        "cues": [
            {"source": "free_library", "visual_timestamp_s": 1.25},
            {"source": "elevenlabs_approved", "approval_or_ledger_ref": "cmsg_12345678", "visual_timestamp_s": 4.8},
        ],
    }
    assert DS.validate_post_assembly_spotting(good_spot)["status"] == "PASS"
    assert DS.validate_post_assembly_spotting({"based_on_assembled_video": False, "cues": [{"source": "procedural"}]})["status"] == "FAIL"


def test_unified_film_style_bible_and_system_wide_skill_correspondence():
    bible = {
        "schema": "film_style_bible/1",
        "film_id": "ep_1914_truce",
        "title": "Christmas Truce 1914",
        "era": "World War I (December 1914)",
        "visual_identity": {"look_words": "muted chiaroscuro oil-washed ink", "palette_hex": ["#1B2228", "#6B5A45", "#C8A97E"]},
        "map_aesthetic": {"style_preset": "dark_relief", "font": "Liberation Serif"},
        "photo_direction": {"lighting": "cold overcast dusk and warm lantern key", "lens_grammar": "35mm/50mm naturalistic"},
        "acting_and_motion": {
            "acting_register": "restrained_documentary_realism",
            "motion_discipline": "deliberate human weight, subtle breath and eye-line shifts, zero theatrical flailing",
            "preferred_camera_moves": ["truck", "zoom_in", "zoom_out"],
        },
        "visual_bridges": {"typography": "Liberation Serif + Inter", "accent_hex": "#C8A97E", "pacing": "on-word kinetic reveal"},
        "sound_palette": {"ambience_character": "distant wind and muffled snow crunch", "music_mood": "low cello drone", "foley_realism": "grounded physical cloth and mud"},
    }
    directives = SB.render_layer_directives(bible)
    assert set(directives.keys()) == {
        "map_directive",
        "photo_directive",
        "ltx_acting_motion_directive",
        "visual_bridge_directive",
        "sound_directive",
    }

    # System-wide check: 8 portable skills pass lint & SkillOrchestrator audit passes
    skill_res = ASL.validate_all_skills()
    assert skill_res["ok"] is True, skill_res["errors"]
    assert {"ltx-cinematography", "youtube-docudrama-editing", "film-style-bible"} <= set(skill_res["skills"])

    orch = SkillOrchestrator()
    audit = orch.audit_correspondence(allow_gaps=True)
    assert audit["ok"] is True, audit
    assert orch._stages["S5_gemini_images"]["execution_category"] == "agent_browser_gate"


def test_skill_orchestrator_executes_s2_docudrama_s3_style_bible_and_s6_ltx_loop(tmp_path: Path):
    orch = SkillOrchestrator()
    assert {"S2_story_and_script", "S3_film_direction", "S6_ltx_video"} <= set(orch._executors)

    # S2 structural validation
    s2 = orch.run_stage(
        "S2_story_and_script",
        {
            "episode_plan": {
                "scenes": [
                    {"scene_id": "D1", "scene_role": "dramatic_showcase", "primary_route": "video", "duration_s": 80.0, "dialogue_turns": 5},
                    {"scene_id": "D2", "scene_role": "dramatic_showcase", "primary_route": "video", "duration_s": 90.0, "dialogue_turns": 6},
                ]
            }
        },
        allow_gaps=True,
    )
    assert s2["status"] == "PASS"

    # S3 style bible compilation
    s3 = orch.run_stage(
        "S3_film_direction",
        {
            "style_bible": {
                "schema": "film_style_bible/1",
                "film_id": "ep1",
                "title": "Test",
                "era": "1914",
                "visual_identity": {"look_words": "oil ink", "palette_hex": ["#111111", "#222222", "#333333"]},
                "map_aesthetic": {"style_preset": "dark_relief"},
                "photo_direction": {"lighting": "lantern"},
                "acting_and_motion": {
                    "acting_register": "restrained_documentary_realism",
                    "motion_discipline": "steady natural posture",
                    "preferred_camera_moves": ["truck"],
                },
                "visual_bridges": {"typography": "Liberation Serif"},
                "sound_palette": {"ambience_character": "rain"},
            }
        },
    )
    assert s3["status"] == "PASS"
    assert "ltx_acting_motion_directive" in s3["directives"]
