"""Master Rule Enforcer binding all existing explainer-engine modules to Gates G0..G9 (D-124..D-130).

Ensures Gemini executes every relevant linter, sourced rule (BP-01..BP-175), 3-Tier Cohesive Film law,
and fail-closed post-render forensic check at each gate before asking for Creator approval.
"""
from __future__ import annotations

from typing import Any, Dict, List
from explainer_engine.assets.reference_library import DEFAULT_CHIAROSCURO_LIBRARY, validate_reference_library
from explainer_engine.production.validate import check_script
from explainer_engine.scripting.story_lint import lint_v4 as story_lint_v4
from explainer_engine.scripting.scene_lint import lint_v4 as scene_lint_v4
from explainer_engine.scripting.shot_prompt_lint import check_v4_script
from explainer_engine.audio.sfx_planner import build_g4_audio_fx_plan
from explainer_engine.imagegen.gemini_image_engine import build_gemini_generation_queue
from explainer_engine.aivideo.wan_optimizer import plan_parallel_g7_threads
from explainer_engine.production.chunked_edit import plan_3min_assembly_chunks
from explainer_engine.orchestration.cohesive_film_engine import (
    build_cohesive_film_edl,
    check_cohesive_film_invariants_and_bounds,
    verify_real_api_media_renders,
)


def run_all_gate_audits(
    script_doc: Dict[str, Any],
    library: Dict[str, Any] = DEFAULT_CHIAROSCURO_LIBRARY,
    rendered_video_path: str | None = None,
    rendered_contact_sheets: List[str] | None = None,
    api_receipts_path: str | None = None,
    require_rendered_media: bool = False,
) -> Dict[str, Any]:
    """Run all G0..G8 architectural audits (and optional G9 post-render forensic check) on a v4.0 production_script.json."""
    g0_errors = validate_reference_library(library)
    g2_story_issues = story_lint_v4(script_doc)
    g2_scene_issues = scene_lint_v4(script_doc)
    g3_validate_issues = check_script(script_doc)
    g3_shot_issues = check_v4_script(script_doc)
    g4_sfx_plan = build_g4_audio_fx_plan(script_doc)
    g5_image_queue = build_gemini_generation_queue(script_doc, library=library)
    g7_parallel_plan = plan_parallel_g7_threads(script_doc)
    g8_chunks = plan_3min_assembly_chunks(script_doc, chunk_target_sec=180.0)

    cohesive_issues = check_cohesive_film_invariants_and_bounds(script_doc)
    cohesive_edl = build_cohesive_film_edl(script_doc)

    forensic_issues: List[Dict[str, Any]] = []
    if require_rendered_media or rendered_video_path or api_receipts_path or rendered_contact_sheets:
        forensic_report = verify_real_api_media_renders(
            video_path=rendered_video_path,
            contact_sheet_paths=rendered_contact_sheets,
            receipts_json_path=api_receipts_path,
            require_rendered_media=require_rendered_media,
        )
        forensic_issues = forensic_report["issues"]

    # Deduplicate issues by (rule, where, detail) so no linter failure is double-counted
    raw_issues = (
        g0_errors
        + g2_story_issues
        + g2_scene_issues
        + g3_validate_issues
        + g3_shot_issues
        + cohesive_issues
        + forensic_issues
    )
    seen_keys = set()
    all_issues = []
    for issue in raw_issues:
        key = (issue.get("rule"), issue.get("where"), issue.get("detail"))
        if key not in seen_keys:
            seen_keys.add(key)
            all_issues.append(issue)

    return {
        "status": "PASS" if len(all_issues) == 0 else "FAIL",
        "total_issues": len(all_issues),
        "g0_reference_library_valid": len(g0_errors) == 0,
        "g2_story_and_scene_issues": len(g2_story_issues) + len(g2_scene_issues),
        "g3_visual_and_shot_issues": len(g3_validate_issues) + len(g3_shot_issues),
        "g4_sfx_cues_planned": g4_sfx_plan["counts"]["sfx_cues"],
        "g4_melodies_planned": g4_sfx_plan["counts"]["music_melodies"],
        "g5_unique_gemini_images_queued": g5_image_queue["total_images_to_generate"],
        "g7_thread_a_jobs": g7_parallel_plan["thread_a_10pct_and_30pct"]["total_thread_a_jobs"],
        "g7_thread_b_wan_jobs": g7_parallel_plan["thread_b_60pct_wan_modal"]["total_thread_b_jobs"],
        "g8_3min_chunks_count": len(g8_chunks),
        "g8_edl_total_duration_sec": cohesive_edl["total_duration_sec"],
        "issues": all_issues,
    }


def run_post_render_forensic_gate(
    video_path: str,
    receipts_json_path: str,
    contact_sheet_paths: List[str] | None = None,
    expected_shots_count: int = 1,
    expected_voice_lines_count: int = 1,
) -> Dict[str, Any]:
    """Mandatory fail-closed post-render gate (PK-T1-04 / PV-NO-FAKE-OFFLINE-RENDER)."""
    return verify_real_api_media_renders(
        video_path=video_path,
        contact_sheet_paths=contact_sheet_paths,
        receipts_json_path=receipts_json_path,
        require_rendered_media=True,
        expected_shots_count=expected_shots_count,
        expected_voice_lines_count=expected_voice_lines_count,
    )


def run_system_logic_check(script_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Comprehensive System Logic Check across Video Planning, Gate Validator Coverage,
    YouTube Storytelling Docudrama Fit, Wan 2.2 Frame[-5] Chaining, and Model Routing."""
    from explainer_engine.aivideo.wan_optimizer import compute_continuation_splice_spec
    from explainer_engine.production.chunked_edit import build_seamless_continuation_edl

    gate_audit = run_all_gate_audits(script_doc)
    splice_test = compute_continuation_splice_spec(97, 97, offset_from_end=5, fps=24)
    edl_test = build_seamless_continuation_edl(
        [
            {"shot_id": "SH_A", "frames": 97, "continues_from_previous": False},
            {"shot_id": "SH_B", "frames": 97, "continues_from_previous": True},
        ],
        offset_from_end=5,
        fps=24,
    )

    segments = script_doc.get("segments", [])
    audio_lines = script_doc.get("audio_lines", [])
    shots = script_doc.get("shots", [])

    narr_sec = sum(float(l.get("estimated_duration_seconds", 0.0)) for l in audio_lines if l.get("speaker_type") == "narrator")
    char_sec = sum(float(l.get("estimated_duration_seconds", 0.0)) for l in audio_lines if l.get("speaker_type") == "character")
    tot_sec = narr_sec + char_sec
    avg_words_per_line = round(sum(len(str(l.get("text", "")).split()) for l in audio_lines) / max(len(audio_lines), 1), 1)
    avg_shot_sec = round(sum(float(s.get("target_duration_seconds", 0.0)) for s in shots) / max(len(shots), 1), 2)

    hook_failed = any(
        i.get("rule") in ("YT-01-HOOK", "YT-00-3SEC-KINETIC-HOOK") and i.get("severity") == "FAIL"
        for i in gate_audit["issues"]
    )
    valid_bridges = sum(
        1 for idx, seg in enumerate(segments[:-1])
        if seg.get("effect_to_segment_id") == segments[idx + 1].get("segment_id")
    ) + (1 if segments else 0)

    return {
        "overall_status": "PASS" if gate_audit["status"] == "PASS" else "FAIL",
        "1_video_planning_logic": {
            "total_duration_sec": tot_sec,
            "phases_count": len(script_doc.get("phases", [])),
            "segments_count": len(segments),
            "causal_chain_intact": gate_audit["g2_story_and_scene_issues"] == 0,
            "shots_count": len(shots),
            "avg_shot_duration_sec": avg_shot_sec,
            "unique_gemini_images_count": gate_audit["g5_unique_gemini_images_queued"],
            "visual_mix_shares": {
                "cinematic_video_60pct": round(gate_audit["g7_thread_b_wan_jobs"] / max(len(shots), 1), 2),
                "collage_and_maps_40pct": round(gate_audit["g7_thread_a_jobs"] / max(len(shots), 1), 2),
            },
            "wan_chain_minus_5_verified": (
                splice_test["extracted_start_frame_index_0based"] == 92
                and edl_test[0]["play_frames"] == 92
                and edl_test[1]["timeline_start_frame"] == 92
            ),
        },
        "2_validator_coverage_per_gate": {
            "G0_Reference_Library": "explainer_engine.assets.reference_library.validate_reference_library",
            "G2_Narrative_Script": "explainer_engine.scripting.story_lint.lint_v4 + scene_lint.lint_v4 + qa.viewer_critic (advisory)",
            "G3_Visual_Audio_Storyboard": "explainer_engine.production.validate.check_script + scripting.shot_prompt_lint.check_v4_script + orchestration.cohesive_film_engine.check_cohesive_film_invariants_and_bounds",
            "G4_SFX_Ambience_Music": "explainer_engine.audio.sfx_planner.build_g4_audio_fx_plan",
            "G5_Autonomous_API_Image_Generation": "explainer_engine.imagegen.gemini_image_engine.build_gemini_generation_queue + infographics.python_map_and_chart_engine",
            "G6_ElevenLabs_Voice_Spine": "explainer_engine.aivideo.wan_optimizer.analyze_character_appearance_cadence (Odom + Wan S2V routing)",
            "G7_Parallel_10_30_60_Render": "explainer_engine.aivideo.wan_optimizer.plan_parallel_g7_threads + compute_continuation_splice_spec (WAN-CHAIN-MINUS-5)",
            "G8_3Min_Chunked_Assembly": "explainer_engine.production.chunked_edit.plan_3min_assembly_chunks + orchestration.cohesive_film_engine.build_cohesive_film_edl",
            "G9_Post_Render_Forensic_Gate": "explainer_engine.orchestration.cohesive_film_engine.verify_real_api_media_renders (fail-closed)",
        },
        "3_youtube_docudrama_fit": {
            "cold_open_12s_hook_verified": not hook_failed,
            "segment_end_cliffhangers_count": valid_bridges,
            "narrator_share": round(narr_sec / max(tot_sec, 1e-6), 3),
            "character_dialogue_share": round(char_sec / max(tot_sec, 1e-6), 3),
            "avg_words_per_line": avg_words_per_line,
            "qwen_removed_gemini_native": "qwen" not in str(script_doc.get("world_bible", {})).lower(),
        },
    }
