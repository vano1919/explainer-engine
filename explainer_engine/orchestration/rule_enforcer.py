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
from explainer_engine.imagegen.asset_plan import extract_complete_asset_plan
from explainer_engine.imagegen.turn_pack import scene_picture_ids
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
    # G5 (v4.3 P3): the pictures come from the Gemini chat through turn packs; the archive's second queue builder is gone.
    # The unique-scene check (PV-NO-CROP-PADDING) stays, as FAIL rows instead of an exception.
    g5_pictures = scene_picture_ids(script_doc)
    g5_unique_errors = extract_complete_asset_plan(script_doc, library=library)["validation_errors"]
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
    # the reference library reports plain strings: they become FAIL rows (a string had no .get and crashed the dedup)
    g0_rows = [{"rule": "G0", "severity": "FAIL", "where": "reference_library", "detail": str(e)} for e in g0_errors]
    raw_issues = (
        g0_rows
        + g2_story_issues
        + g2_scene_issues
        + g3_validate_issues
        + g3_shot_issues
        + [dict(e, severity=e.get("severity", "FAIL")) for e in g5_unique_errors]
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
        # FAIL only on a FAIL row (an issue without a severity counts as FAIL); REVIEW rows (hypothesis rules, D-59)
        # make the audit REVIEW, never FAIL (v4.3 plan P2: the archive failed the whole audit on any REVIEW row)
        "status": ("FAIL" if any(i.get("severity", "FAIL") == "FAIL" for i in all_issues)
                   else "REVIEW" if all_issues else "PASS"),
        "total_issues": len(all_issues),
        "g0_reference_library_valid": len(g0_errors) == 0,
        "g2_story_and_scene_issues": len(g2_story_issues) + len(g2_scene_issues),
        "g3_visual_and_shot_issues": len(g3_validate_issues) + len(g3_shot_issues),
        "g4_sfx_cues_planned": g4_sfx_plan["counts"]["sfx_cues"],
        "g4_melodies_planned": g4_sfx_plan["counts"]["music_melodies"],
        "g5_unique_gemini_images_queued": len(set(g5_pictures)),
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
    from explainer_engine.episode.router import mix_report

    gate_audit = run_all_gate_audits(script_doc)
    chain = wan_chain_check(script_doc)
    mix = mix_report(script_doc)

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
        "overall_status": gate_audit["status"] if chain["status"] != "FAIL" else "FAIL",
        "1_video_planning_logic": {
            "total_duration_sec": tot_sec,
            "phases_count": len(script_doc.get("phases", [])),
            "segments_count": len(segments),
            "causal_chain_intact": gate_audit["g2_story_and_scene_issues"] == 0,
            "shots_count": len(shots),
            "avg_shot_duration_sec": avg_shot_sec,
            "unique_gemini_images_count": gate_audit["g5_unique_gemini_images_queued"],
            # RT-04: by duration, never by shot counts (the archive divided job counts by the shot count)
            "visual_mix_shares": {"basis": mix["basis"], "shares": mix["shares"], "unrouted": mix["unrouted"]},
            "wan_chain": chain,
        },
        "2_validator_coverage_per_gate": {
            "G0_Reference_Library": "explainer_engine.assets.reference_library.validate_reference_library",
            "G2_Narrative_Script": "explainer_engine.scripting.story_lint.lint_v4 + scene_lint.lint_v4 + qa.viewer_critic (advisory)",
            "G3_Visual_Audio_Storyboard": "explainer_engine.production.validate.check_script + scripting.shot_prompt_lint.check_v4_script + orchestration.cohesive_film_engine.check_cohesive_film_invariants_and_bounds",
            "G4_SFX_Ambience_Music": "explainer_engine.audio.sfx_planner.build_g4_audio_fx_plan",
            "G5_Gemini_Chat_Pictures": "explainer_engine.imagegen.turn_pack (export, intake, promote, remake_list; GC-01..GC-17)",
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


def wan_chain_check(script_doc: Dict[str, Any], fps: int = 24, offset_from_end: int = 5) -> Dict[str, Any]:
    """WAN-CHAIN-MINUS-5 measured on the script's own chained shots (v4.3 plan P2, EP-03).

    The archive checked a fixed two-clip example against its own constants, so the row was always true. Here every shot
    with ``continues_from_previous`` must be a ``wan`` shot that follows a ``wan`` shot long enough to hand over frame
    [-5], and the EDL built from the script's frames must lose exactly ``offset_from_end`` frames per hand-over. A
    script without chained shots is NOT_RUN.
    """
    from explainer_engine.production.chunked_edit import build_seamless_continuation_edl
    from explainer_engine.qa.gates import row

    shots = script_doc.get("shots", [])
    chained = [i for i, s in enumerate(shots) if s.get("continues_from_previous")]
    if not chained:
        return row("wan_chain_minus_5", None, "the script has no chained Wan shots")
    frames = [int(round(float(s.get("target_duration_seconds") or 0.0) * fps)) for s in shots]
    bad = []
    for i in chained:
        prev = shots[i - 1] if i > 0 else None
        if prev is None or prev.get("route") != "wan" or shots[i].get("route") != "wan":
            bad.append(f"{shots[i].get('shot_id')}: a chained shot and the one before it must both be wan")
        elif frames[i - 1] <= offset_from_end + 4:
            bad.append(f"{shots[i].get('shot_id')}: the previous clip has {frames[i - 1]} frames, too short to hand over")
    if bad:
        return row("wan_chain_minus_5", False, f"{len(bad)} broken hand-over(s)", bad)
    edl = build_seamless_continuation_edl(
        [{"shot_id": s.get("shot_id"), "frames": f, "continues_from_previous": bool(s.get("continues_from_previous"))}
         for s, f in zip(shots, frames)], offset_from_end=offset_from_end, fps=fps)
    want = sum(frames) - offset_from_end * len(chained)
    got = edl[-1]["timeline_end_frame"] if edl else 0
    return row("wan_chain_minus_5", got == want, f"EDL ends at frame {got}, the script's frames less the hand-overs give {want}",
               {"handovers": len(chained), "edl_end_frame": got})
