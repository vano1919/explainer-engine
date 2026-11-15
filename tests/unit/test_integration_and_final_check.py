"""Integration & Final System Check Reproducer Suite (o239-argon-impl).

Every test in this file verifies one of the P0/P1/P2 integration defects and final system check invariants,
and is designed to FAIL on the baseline f0f99037 code and PASS on the integrated code.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from explainer_engine.audio import duck as DUCK
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import sound_plan as SP
from explainer_engine.episode import shot_split as SS
from explainer_engine.episode import timing as ET
from explainer_engine.finish import superres as SR_UP
from explainer_engine.finish import upscale as FIN_UP
from explainer_engine.production import continuity as CONT
from explainer_engine.production import directed25d as D25
from explainer_engine.production import living_fx as LFX
from explainer_engine.production import visual_bridge as VB
from explainer_engine.qa import look_and_listen as LL
from explainer_engine.standards import sourced_rules as SR
from explainer_engine.training.pods.ltx import modal_ltx_jobs as LTX
from explainer_engine.videolane import ingest as IN
from explainer_engine.videolane import plan as VP


def test_p0_1_retime_with_edit_points_updates_all_shots_and_downstream_schedules(tmp_path):
    """P0-1: retime_with_edit_points must update BOTH spoken inserts AND non-insert video/render shots,
    recompute start_frame/end_frame/segments/narrator_offsets/dialogue_positions/map_events, and attach timing_id."""
    script = {
        "shots": [
            {"shot_id": "S01_SH001", "segment_id": "S01", "route": "video"},
            {"shot_id": "S01_SH002", "segment_id": "S01", "route": "video"},
            {"shot_id": "S01_SH003", "segment_id": "S01", "route": "map", "map_spec": {"line_style": "chalk"}},
        ],
        "inserts": [{"shot_id": "S01_SH001", "kind": "character"}],
    }
    timing = {
        "fps": 24,
        "total_frames": 288,
        "inserts": [{"shot_id": "S01_SH001", "at_read_frame": 0, "frames": 96}],
        "shots": {
            "S01_SH001": {"segment_id": "S01", "start_frame": 0, "end_frame": 96, "frames": 96},
            "S01_SH002": {"segment_id": "S01", "start_frame": 96, "end_frame": 192, "frames": 96},
            "S01_SH003": {"segment_id": "S01", "start_frame": 192, "end_frame": 288, "frames": 96},
        },
    }
    edit_points = {
        "clips": {
            "S01_SH001": {"in": 0.40, "out": 5.40, "clip_path": "production/video/cut/S01_SH001.mp4"},
            # Non-insert video shot trimmed shorter (3.0 s = 72 frames instead of 96): old code ignored this!
            "S01_SH002": {"in": 0.20, "out": 3.20, "clip_path": "production/video/cut/S01_SH002.mp4"},
        }
    }
    retimed = ET.retime_with_edit_points(timing, script, edit_points)
    assert retimed["schema"] == "episode_timing/2"
    assert retimed["shots"]["S01_SH001"]["frames"] == 120
    assert retimed["shots"]["S01_SH002"]["frames"] == 72
    assert retimed["shots"]["S01_SH002"]["start_frame"] == 120
    assert retimed["shots"]["S01_SH003"]["start_frame"] == 192
    assert retimed["total_frames"] == 120 + 72 + 96 == 288
    assert "timing_id" in retimed and "render_epoch" in retimed
    assert "S01_SH001" in retimed["dialogue_positions"]
    assert "S01_SH003" in retimed["map_events"]
    assert len(retimed["narrator_offsets"]) == 3

    persisted_path = tmp_path / "timing.json"
    ET.persist_authoritative_clock(retimed, persisted_path)
    loaded = json.loads(persisted_path.read_text(encoding="utf-8"))
    assert loaded["timing_id"] == retimed["timing_id"]
    assert ET.verify_clock_alignment(loaded, {"shot_id": "S01_SH002", "timing_id": loaded["timing_id"], "frames": 72}) == []
    mismatch = ET.verify_clock_alignment(loaded, {"shot_id": "S01_SH002", "timing_id": "stale_clock", "frames": 96})
    assert len(mismatch) >= 2 and all(m["status"] == "FAIL" for m in mismatch)


def test_p0_1_ingest_edit_points_enforces_bp201_040s_head_lead_and_single_trim_contract(tmp_path):
    from tools.render_tools import build_segments as BS
    """P0-1: ingest.edit_points must enforce BP-201's 0.40s head lead and >=0.50s reaction tail,
    and build_segments.resolve_video_source must enforce the single trim contract (clip_path, ss=0.0)."""
    assert IN.HEAD_LEAD[1] == pytest.approx(0.40)
    assert IN.CUT_TAIL[0] == pytest.approx(0.50)
    pts = IN.edit_points(5.0, [(0.80, 2.80)], {}, 4.0, 24, spoken=True, shot_id="S01_SH002")
    # Speech starts at 0.80s: with BP-201 0.40s head lead, in_s must be <= 0.40s (old code cut at 0.55s!)
    assert pts["in_s"] <= 0.40 + 1e-3
    assert pts["out_s"] >= 2.80 + 0.50 - 1e-3

    cut_dir = tmp_path / "production" / "video" / "cut"
    cut_dir.mkdir(parents=True)
    cut_file = cut_dir / "S01_SH002.mp4"
    cut_file.write_bytes(b"trimmed_mp4_bytes")
    rec = {"shot_id": "S01_SH002", "clip_path": "production/video/cut/S01_SH002.mp4", "raw_path": "production/video/raw/S01_SH002.mp4", "in_s": 0.40}
    resolved_path, ss, is_trimmed = BS.resolve_video_source(tmp_path, rec)
    assert resolved_path == cut_file and ss == 0.0 and is_trimmed is True

    with pytest.raises(ContractError, match="single trim contract"):
        BS.resolve_video_source(tmp_path, {"shot_id": "S01_SH999", "clip_path": "production/video/cut/missing.mp4"})


def test_p0_1_segment_cache_invalidates_when_inputs_or_clock_change(tmp_path):
    from tools.render_tools import build_segments as BS
    """P0-1: build_segments cache must depend on script, timing_id, frames, edit_points, source_sha256, and render_epoch."""
    out_mp4 = tmp_path / "S01_SH001.mp4"
    out_mp4.write_bytes(b"rendered_segment_v1")
    shot_spec = {"shot_id": "S01_SH001", "route": "still_25d", "on_screen_text": "Hello"}
    t_shot_1 = {"frames": 96, "start_frame": 0, "end_frame": 96}
    key1 = BS.compute_segment_cache_key(
        "S01_SH001", shot_spec, t_shot_1,
        timing_id="clock_v1", render_epoch="epoch_1", source_sha256="src_sha_1",
    )
    # Without .seg.json sidecar, bare existing .mp4 is NOT valid cache!
    assert BS.is_segment_cache_valid(out_mp4, key1) is False

    out_mp4.with_suffix(".seg.json").write_text(json.dumps({
        "cache_key": key1,
        "output_sha256": BS._file_sha256(out_mp4),
    }), encoding="utf-8")
    assert BS.is_segment_cache_valid(out_mp4, key1) is True

    # Changing timing frame count or source_sha256 changes cache key and invalidates cache
    key2 = BS.compute_segment_cache_key(
        "S01_SH001", shot_spec, {"frames": 120, "start_frame": 0, "end_frame": 120},
        timing_id="clock_v2", render_epoch="epoch_2", source_sha256="src_sha_1",
    )
    assert key2 != key1
    assert BS.is_segment_cache_valid(out_mp4, key2) is False


def test_p0_2_ltx_route_resolution_persists_to_script_and_visual_start_frame_catches_non_keyword_shots(tmp_path):
    """P0-2: Keyword list is only a first screen; start-frame visual inspection catches close faces, two-person contact,
    and low confidence even without prop keywords, and reroute_unnatural_ltx_shots persists route changes to disk."""
    script = {
        "shots": [
            {
                "shot_id": "S03_SH004",
                "route": "video",
                "camera_spec": {"shot_size": "medium"},
                "character_ids": ["arthur"],
                "action_start_state": "Arthur looks across the trench in silence",
                "action_end_state": "Arthur nods slowly",
                "positions": [{"id": "arthur", "face_box": [0.30, 0.15, 0.65, 0.45]}],
            },
            {
                "shot_id": "S03_SH005",
                "route": "video",
                "camera_spec": {"shot_size": "wide"},
                "character_ids": ["arthur"],
                "action_start_state": "Wide atmospheric snow drifting over empty parapet",
                "action_end_state": "Smoke rises in the distance",
            },
        ],
        "audio_lines": [],
    }
    # S03_SH004 has NO keyword from LTX_UNNATURAL_PROPS, but has a prominent frontal face box (0.35 * 0.30 = 10.5% > 4.5%)
    ev = VP.classify_ltx_natural_fit(script["shots"][0], script)
    assert ev["natural_for_ltx"] is False
    assert ev["status"] == "REVIEW"
    assert any("start-frame visual check" in r for r in ev["reasons"])

    # Also check low-confidence start frame inspection triggers REVIEW
    ev_low = VP.classify_ltx_natural_fit(script["shots"][1], script, inspection_meta={"confidence": "low"})
    assert ev_low["natural_for_ltx"] is False and ev_low["status"] == "REVIEW"

    # Frame-0 comparison catches diverged first frame
    f0_src = np.full((64, 64, 3), 40, dtype=np.uint8)
    f0_bad = np.full((64, 64, 3), 200, dtype=np.uint8)
    cmp_bad = VP.compare_ltx_first_frame_to_source(f0_src, f0_bad)
    assert cmp_bad["status"] == "FAIL" and cmp_bad["matched"] is False

    # Route persistence writes updated route and route_decision to production_script.json
    script_path = tmp_path / "production_script.json"
    script_path.write_text(json.dumps(script), encoding="utf-8")
    res = VP.apply_and_persist_ltx_routes(script_path)
    assert "S03_SH004" in res["rerouted_to_25d"]
    saved = json.loads(script_path.read_text(encoding="utf-8"))
    s4 = next(s for s in saved["shots"] if s["shot_id"] == "S03_SH004")
    assert s4["route"] == "still_25d"
    assert s4["route_decision"]["original_route"] == "video"
    assert s4["route_decision"]["resolved_route"] == "still_25d"


def test_p1_3_neighbouring_shot_continuity_and_split_clip_fallback_guard():
    """P1-3: Neighbouring-shot continuity checks bbox position jumps, roster, light/warmth, weather, posture,
    forbids static photos inside ongoing live video scenes, and guards split-clip fallback."""
    shots = [
        {
            "shot_id": "S04_SH001",
            "scene_id": "SC_TRENCH",
            "route": "video",
            "camera_spec": {"shot_size": "medium", "angle_deg": 10},
            "roster": ["arthur", "heinrich"],
            "positions": {"arthur": [0.20, 0.50], "heinrich": [0.75, 0.50]},
            "weather": "snow",
            "end_luma": 0.42,
            "end_warmth": 0.50,
            "action_end_state": "Arthur standing holding rifle",
        },
        {
            "shot_id": "S04_SH002",
            "scene_id": "SC_TRENCH",
            "continues": True,
            "route": "still_25d",  # static photo inserted inside ongoing live video scene!
            "camera_spec": {"shot_size": "medium", "angle_deg": 135},  # >90 deg flip, no shot-size step!
            "roster": ["arthur"],  # heinrich vanished without announcement!
            "positions": {"arthur": [0.82, 0.50]},  # jumped > 0.10 without motivated reframe!
            "weather": "clear",  # jumped snow -> clear!
            "start_luma": 0.78,  # luma jump > 0.18!
            "start_warmth": 0.75,
            "action_start_state": "Arthur sitting with rifle on the ground",
        },
        {
            "shot_id": "S04_SH003",
            "scene_id": "SC_TRENCH",
            "route": "video",
            "camera_spec": {"shot_size": "wide"},
            "roster": ["arthur", "heinrich"],
        },
    ]
    found = CONT.findings(shots)
    rules_hit = {f["rule"] for f in found}
    assert "VL-15 PROP-STATE" in rules_hit
    assert "CONT-BBOX-JUMP" in rules_hit
    assert "CONT-ROSTER" in rules_hit
    assert "CONT-CAMERA-DIRECTION" in rules_hit
    assert "CONT-LIGHT-COLOUR" in rules_hit
    assert "CONT-WEATHER" in rules_hit
    assert "CONT-ACTION-STATE" in rules_hit
    assert "CONT-PHOTO-IN-LIVE-SCENE" in rules_hit

    # Split-clip fallback guard fails when part b resets scale from 1.09 back to 1.00
    bad_split = CONT.verify_split_clip_continuity([
        {"part": "a", "end_scale": 1.09, "end_luma": 95.0},
        {"part": "b", "start_scale": 1.00, "start_luma": 95.0},
    ])
    assert bad_split["status"] == "FAIL"
    assert any(f["rule"] == "CONT-SPLIT-ZOOM-JUMP" for f in bad_split["findings"])


def test_p1_4_mix_uses_tactile_emitter_shared_duck_mood_music_intentional_silence_and_lufs_dbtp_report():
    from tools.render_tools import mix as MIX
    """P1-4: mix.py has no hardcoded MAP_DRAW_SPANS_S, emits map SFX from tactile_renderer.AudioEventEmitter,
    calls shared duck functions, derives mood music cues, honours intentional_silence, and reports LUFS & True Peak."""
    assert not hasattr(MIX, "MAP_DRAW_SPANS_S")

    map_shot = {"shot_id": "S02_SH001", "route": "map", "map_spec": {"line_style": "chalk"}, "draw_spans_frames": [[6, 54, "chalk"]]}
    t_shot = {"start_frame": 48, "frames": 72, "end_frame": 120}
    evs = MIX.emit_map_audio_events_for_shot(map_shot, t_shot, fps=24)
    assert len(evs) == 1
    assert evs[0]["sfx_id"] == "chalk_line__v1"
    assert evs[0]["timeline_start_s"] == pytest.approx(2.0 + 6 / 24.0)
    assert evs[0]["timeline_end_s"] == pytest.approx(2.0 + 54 / 24.0)

    # Mood-driven music spotting & intentional_silence
    script_doc = {
        "segments": [
            {"id": "S01", "mood": "somber"},
            {"id": "S02", "mood": "tense"},
            {"id": "S03", "mood": "warmth"},
        ],
        "shots": [
            {"shot_id": "S01_SH001", "segment_id": "S01", "route": "still_25d"},
            {"shot_id": "S02_SH001", "segment_id": "S02", "route": "still_25d", "intentional_silence": True},
            {"shot_id": "S03_SH001", "segment_id": "S03", "route": "still_25d"},
        ],
    }
    timing_doc = {
        "fps": 24,
        "timing_id": "clk_test",
        "render_epoch": "epoch_clk_test",
        "shots": {
            "S01_SH001": {"segment_id": "S01", "start_frame": 0, "end_frame": 240, "frames": 240},
            "S02_SH001": {"segment_id": "S02", "start_frame": 240, "end_frame": 504, "frames": 264},
            "S03_SH001": {"segment_id": "S03", "start_frame": 504, "end_frame": 744, "frames": 240},
        },
    }
    cues = MIX.build_music_cues_from_script(script_doc, timing_doc)
    seg_cues = {c["segment_id"]: c for c in cues}
    assert "S01" in seg_cues and seg_cues["S01"]["cue"] == "somber_strings"
    assert "S02" not in seg_cues  # intentional_silence / no-music stretch honoured!
    assert "S03" in seg_cues and seg_cues["S03"]["cue"] == "warm_cello"

    # Shared ducking on (N, 2) stereo + integrated LUFS & 4x oversampled True Peak report
    n_samp = MIX.SR * 2
    t = np.linspace(0.0, 2.0, n_samp, dtype=np.float32)
    voice = np.stack([0.22 * np.sin(2 * np.pi * 440.0 * t)] * 2, axis=-1)
    bed = np.stack([0.02 * np.sin(2 * np.pi * 1000.0 * t)] * 2, axis=-1)
    bed_ducked = DUCK.duck_presence_band(bed, voice[:, 0], sr=MIX.SR)
    assert bed_ducked.shape == (n_samp, 2)
    assert float(np.sqrt(np.mean(bed_ducked ** 2))) < float(np.sqrt(np.mean(bed ** 2)))

    norm_mix, norm_meta = MIX.normalize_to_target_lufs_and_true_peak(voice + bed_ducked, sr=MIX.SR)
    assert norm_meta["pass_lufs"] is True
    assert norm_meta["pass_true_peak"] is True
    rep = MIX.measure_mix_loudness_report(norm_mix, voice_stem=voice, bed_stem=bed_ducked, timing_doc=timing_doc, sr=MIX.SR)
    assert -15.0 <= rep["integrated_lufs"] <= -13.0
    assert rep["true_peak_dbtp"] <= -1.0


def test_p1_5_particle_leakage_foreground_shield_split_camera_trajectory_and_single_safe_overlay():
    from tools.render_tools import build_segments as BS
    """P1-5: Particle leakage inside foreground/face masks is <10% (>=90% shield), split camera slices match
    across boundaries, safe_overlay_box never returns a face-colliding box, and build_segments never double-draws overlays."""
    mask = np.zeros((100, 100), dtype=np.float32)
    mask[20:80, 20:80] = 1.0
    unprot = np.full((100, 100), 0.8, dtype=np.float32)
    prot = unprot * (1.0 - 0.94 * mask)
    leak = LFX.measure_particle_leakage(prot, unprot, mask)
    assert leak["status"] == "PASS" and leak["leakage_ratio"] <= 0.10

    # Split long still preserves continuous scale across part boundary
    shot = {"shot_id": "S05_SH020", "route": "still_25d", "target_duration_seconds": 8.0, "fps": 24}
    parts = SS.split_long_still(shot, None, max_s=5.0, text="One two three four, five six seven eight.")
    assert len(parts) == 2
    assert parts[0]["split_from"]["end_scale"] == pytest.approx(parts[1]["split_from"]["start_scale"])

    # verify_rendered_split_camera_continuity catches a boundary jump
    views_ok = [{"s": 1.0 + 0.001 * f, "cx": 0.5, "cy": 0.5} for f in range(40)]
    assert D25.verify_rendered_split_camera_continuity(views_ok, [20])["status"] == "PASS"
    views_jump = views_ok[:20] + [{"s": 1.0, "cx": 0.5, "cy": 0.5} for _ in range(20)]
    assert D25.verify_rendered_split_camera_continuity(views_jump, [20])["status"] == "FAIL"

    # safe_overlay_box when all 4 corner candidates collide with faces: relocates to clear center/compact or suppresses
    four_corner_faces = [
        {"face": (0.04, 0.72, 0.35, 0.92)},
        {"face": (0.04, 0.04, 0.35, 0.25)},
        {"face": (0.65, 0.72, 0.96, 0.92)},
        {"face": (0.65, 0.04, 0.96, 0.25)},
    ]
    resolved = VB.resolve_safe_overlay_box((0.06, 0.78, 0.34, 0.88), four_corner_faces)
    assert resolved["suppressed"] is False
    assert resolved["box"] != (0.06, 0.78, 0.34, 0.88)

    # Full-frame face coverage suppresses overlay with REVIEW instead of drawing over the face
    full_face = [{"face": (0.0, 0.0, 1.0, 1.0)}]
    suppressed = VB.resolve_safe_overlay_box((0.06, 0.78, 0.54, 0.88), full_face)
    assert suppressed["suppressed"] is True and suppressed["status"] == "REVIEW"
    assert VB.safe_overlay_box((0.06, 0.78, 0.54, 0.88), full_face) == (0.0, 0.0, 0.0, 0.0)

    # Single overlay authority: still_25d never draws epilogue text a second time in build_segments
    epilogue_shot = {"shot_id": "S08_SH004", "route": "still_25d", "on_screen_text": "No official order ever sanctioned the truce."}
    assert BS.should_apply_segment_overlay(epilogue_shot, "still_25d") is False


def test_p2_6_honest_upscale_backend_contract_and_5shot_ab_harness(tmp_path):
    """P2-6: temporal_video without a registered model returns NOT_RUN (never PASS), as_is/none never resizes,
    restore_grain defaults to False, and run_5shot_upscale_ab_harness runs all 5 archetypes."""
    cv2 = pytest.importorskip("cv2")
    src = tmp_path / "src.png"
    img = np.full((90, 160, 3), 120, dtype=np.uint8)
    cv2.imwrite(str(src), img)

    # 1. temporal_video without registered sequence model -> NOT_RUN
    res_tv = SR_UP.upscale_with_backend(src, tmp_path / "tv.png", lane="video", backend="temporal_video", size=(320, 180))
    assert res_tv["status"] == "NOT_RUN" and res_tv["resized"] is False

    # 2. as_is / none -> keeps native size (160, 90), never resizes with Lanczos
    res_asis = SR_UP.upscale_with_backend(src, tmp_path / "asis.png", lane="still_25d", backend="as_is", size=(320, 180))
    assert res_asis["status"] == "PASS" and res_asis["resized"] is False and res_asis["output_size"] == [160, 90]
    assert res_asis["restore_grain"] is False and res_asis["synthetic_dither_applied"] is False

    # 3. 5-shot A/B harness evaluates all 5 archetypes honestly
    ab = SR_UP.run_5shot_upscale_ab_harness(tmp_path / "ab", target_size=(320, 180))
    assert ab["shot_count"] == 5
    for row in ab["shots"]:
        assert row["backends"]["temporal_video"]["status"] == "NOT_RUN"
        assert row["backends"]["as_is"]["resized"] is False
        assert row["backends"]["lanczos"]["resized"] is True


def test_p2_7_per_shot_review_record_and_rule_conflict_resolution():
    """P2-7: Missing or stale review records return NOT_REVIEWED (never PASS), and deliberately still shots
    with stillness_reason do not fail stage_direction."""
    shots = [
        {"shot_id": "S01_SH001", "route": "still_25d", "scene_id": "S01"},
        {"shot_id": "S01_SH002", "route": "video", "scene_id": "S01"},
    ]
    rec1 = LL.build_per_shot_review_record(
        "S01_SH001",
        route="still_25d",
        scene_id="S01",
        source_sha256="abc123",
        output_sha256="def456",
        frame_count=96,
        timing_range=[0.0, 4.0],
        visual_findings=[],
        audio_findings=[],
        render_epoch="epoch_1",
        timing_id="clk_1",
    )
    assert rec1["decision"] == "PASS"

    # S01_SH002 has no review record -> episode status must be NOT_REVIEWED, never PASS!
    audit = LL.validate_episode_review_records(shots, {"S01_SH001": rec1}, expected_render_epoch="epoch_1")
    assert audit["status"] == "NOT_REVIEWED"
    assert "S01_SH002" in audit["not_reviewed"]

    # Stale render_epoch also marks S01_SH001 as NOT_REVIEWED
    stale_audit = LL.validate_episode_review_records(shots[:1], {"S01_SH001": rec1}, expected_render_epoch="epoch_2")
    assert stale_audit["status"] == "NOT_REVIEWED"

    # Rule C1 / BP-204 advisory density hint never blocks
    hint = SP.advisory_density_hint({"shot_id": "S01_SH001", "dur_s": 5.0, "events": [], "design": {"state": "INTENTIONAL_SILENCE"}})
    assert hint["blocking"] is False and hint["status"] == "PASS"


def test_p0_8_and_p1_9_ltx_painterly_negative_prompt_and_single_resize_switch():
    """P0-8 (R1) & P1-9 (R2): ltx_cmd passes --negative-prompt with anatomical/glitch exclusions and NO
    'cartoonish'/'3D CGI'/'illustration'/'painting'/'2D' terms; native_spec supports A/B resolution switch;
    and FIN_UP.needs_resize guards against double resizing."""
    launch = LTX.load_launch()
    job = {"shot_id": "S02_SH002", "seconds": 5.0, "fps": 24, "width": 1280, "height": 704, "seed": 42, "motion_prompt": "Soldiers walk in snow"}
    cmd = LTX.ltx_cmd(launch, job, "/tmp/in.png", "/tmp/out.mp4")
    assert "--negative-prompt" in cmd
    neg = cmd[cmd.index("--negative-prompt") + 1].lower()
    for required_term in ("deformed facial features", "extra fingers", "flickering", "watermark", "jitter"):
        assert required_term in neg
    for forbidden_term in ("cartoonish", "3d cgi", "illustration", "painting", "2d"):
        assert forbidden_term not in neg

    # Even if a caller passes LTX's default negative prompt with 'cartoonish rendering, 3D CGI look', sanitize strips them
    sanitized = LTX.sanitize_painterly_negative_prompt("cartoonish rendering, 3D CGI look, blurry, extra fingers")
    assert "cartoonish" not in sanitized.lower() and "3d cgi" not in sanitized.lower()
    assert "extra fingers" in sanitized.lower()

    # P1-9 A/B resolution switch in native_spec
    spec_default = LTX.native_spec(launch, 5.0)
    assert (spec_default["width"], spec_default["height"]) == (1280, 704)
    higher_size = launch["native"]["sizes"][-1]
    spec_ab = LTX.native_spec(launch, 5.0, resolution_override=higher_size)
    assert [spec_ab["width"], spec_ab["height"]] == higher_size

    # P1-9 single resize guard
    assert FIN_UP.needs_resize(2560, 1440, (2560, 1440)) is False
    assert FIN_UP.needs_resize(1280, 704, (2560, 1440)) is True
