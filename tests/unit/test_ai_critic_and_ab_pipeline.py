"""Regression & Unit Tests for Stage 0-2 AI Critic, 7 Deterministic Blind-Spot Gates, Design System, Studio & YouTube A/B."""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from explainer_engine.design_system.tokens import verify_design_system_assets
from explainer_engine.qa.ai_critic_gate import make_verdict_template, sha256_file, verify_ai_critic_verdict
from explainer_engine.qa.cinema_gates import (
    check_audio_ducking_and_sfx_balance,
    check_edit_grammar_and_dedup,
    check_map_geographic_richness,
    check_narration_pacing_gaps,
    check_overlay_spatial_collisions,
    check_tts_pronunciation_asr,
)
from explainer_engine.qa.youtube_viewer_simulator import render_retention_curve_png, verify_viewer_panel_report
from explainer_engine.studio.elements_vault import ElementsVault
from explainer_engine.studio.popcorn_storyboard import build_popcorn_2x2_prompt, slice_and_upscale_2x2_sheet
from explainer_engine.studio.scenebuilder import SceneShotCard, plan_dramatic_scene_sequence


def test_old_defect_14s_narration_gap_fails_closed() -> None:
    utterances = [
        {"id": "u1", "start_s": 0.5, "end_s": 4.0},
        {"id": "u2", "start_s": 18.2, "end_s": 22.0},  # 14.2s dead gap (Film 1/2 bug!)
    ]
    res = check_narration_pacing_gaps(utterances, total_duration_s=24.0)
    assert res["status"] == "FAIL"
    assert res["max_gap_s"] >= 14.0


def test_old_defect_shackleto_mispronunciation_fails_asr_gate() -> None:
    expected = "Ernest Shackleton led twenty eight men across the Weddell Sea."
    observed = "Ernest Shackleto led twenty eight men across the Weddell Sea."
    res = check_tts_pronunciation_asr(
        expected,
        observed_transcript=observed,
        required_proper_nouns=["Shackleton", "Weddell Sea"],
    )
    assert res["status"] == "FAIL"
    assert "Shackleton" in res["missing_proper_nouns"]


def test_old_defect_empty_blue_ocean_map_and_palette_conflict_fail(tmp_path: Path) -> None:
    # 95% flat blue ocean square
    blue_img = np.zeros((360, 640, 3), dtype=np.uint8)
    blue_img[:, :] = (180, 90, 35)  # BGR strong blue ocean
    p = tmp_path / "empty_ocean.png"
    cv2.imwrite(str(p), blue_img)

    res = check_map_geographic_richness(
        [
            {"map_id": "m1", "palette": "dark_blue", "frame_path": str(p), "context_labels": []},
            {"map_id": "m2", "palette": "bright_parchment", "land_ratio": 0.45, "context_labels": ["Eurasia"]},
        ]
    )
    assert res["status"] == "FAIL"
    assert any("empty ocean" in f for f in res["findings"])
    assert any("Conflicting map palettes" in f for f in res["findings"])


def test_old_defect_bridge_vs_map_collision_fails() -> None:
    bridges = [{"id": "br_01", "start_s": 10.0, "end_s": 14.0, "bbox": [60, 40, 620, 180]}]
    map_els = [{"id": "map_title", "start_s": 8.0, "end_s": 16.0, "bbox": [54, 44, 680, 175]}]
    res = check_overlay_spatial_collisions(bridges, map_els)
    assert res["status"] == "FAIL"
    assert len(res["collisions"]) == 1


def test_old_defect_duplicate_stills_100pct_xfade_and_zero_real_video_fail() -> None:
    shots = [
        {"shot_id": "s1", "kind": "25d", "source_sha256": "aaa", "transition_in": "hard_cut", "is_dramatic_showcase": True},
        {"shot_id": "s2", "kind": "25d", "source_sha256": "bbb", "transition_in": "xfade", "is_dramatic_showcase": True},
        {"shot_id": "s3", "kind": "25d", "source_sha256": "aaa", "transition_in": "xfade", "is_dramatic_showcase": True},
        {"shot_id": "s4", "kind": "25d", "source_sha256": "ccc", "transition_in": "xfade", "is_dramatic_showcase": False},
    ]
    res = check_edit_grammar_and_dedup(shots)
    assert res["status"] == "FAIL"
    assert any("Duplicate visual source" in f for f in res["findings"])
    assert any("Excessive PowerPoint cross-dissolves" in f for f in res["findings"])
    assert any("0/3 real moving video clips" in f for f in res["findings"])


def test_old_defect_sfx_overpowering_and_pumping_fail() -> None:
    res = check_audio_ducking_and_sfx_balance(
        {"max_sfx_relative_to_voice_db": -2.5, "max_pause_pumping_swing_db": 7.4}
    )
    assert res["status"] == "FAIL"
    assert len(res["findings"]) == 2


def test_ai_critic_gate_fail_closed_on_sha_mismatch_and_critical(tmp_path: Path) -> None:
    media = tmp_path / "clip.mp4"
    media.write_bytes(b"fake-video-bytes-v1")
    verdict_file = tmp_path / "verdict.json"

    # Missing verdict -> FAIL
    assert verify_ai_critic_verdict(media, verdict_file, expected_component="maps")["status"] == "FAIL"

    # Valid template with APPROVE & >=8.5 -> PASS
    tpl = make_verdict_template(component="maps", media_path=media, duration_s=10.0)
    tpl["overall_score"] = 9.0
    tpl["verdict"] = "APPROVE"
    tpl["audio_visual_sync_verified"] = True
    tpl["scores"] = {k: 8.8 for k in tpl["scores"]}
    verdict_file.write_text(json.dumps(tpl), encoding="utf-8")
    assert verify_ai_critic_verdict(media, verdict_file, expected_component="maps")["status"] == "PASS"

    # Mutate media bytes -> stale SHA-256 MUST fail closed!
    media.write_bytes(b"fake-video-bytes-v2-rerendered")
    stale = verify_ai_critic_verdict(media, verdict_file, expected_component="maps")
    assert stale["status"] == "FAIL"
    assert any("SHA-256" in f for f in stale["findings"])

    # Update SHA-256 but add 1 critical defect -> MUST fail closed!
    tpl["video_sha256"] = sha256_file(media)
    tpl["defects"] = [
        {
            "timecode": "00:04",
            "severity": "critical",
            "category": "map",
            "description": "Empty ocean frame",
            "recommended_fix": "Zoom out to show coastline",
        }
    ]
    verdict_file.write_text(json.dumps(tpl), encoding="utf-8")
    assert verify_ai_critic_verdict(media, verdict_file, expected_component="maps")["status"] == "FAIL"


def test_design_system_assets_present_and_verified() -> None:
    audit = verify_design_system_assets()
    assert audit["status"] == "PASS", audit


def test_elements_vault_popcorn_slicer_and_scenebuilder(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor.png"
    sheet = tmp_path / "sheet_2x2.png"
    img = np.full((720, 1280, 3), 80, dtype=np.uint8)
    # Draw crisp 4px black cross divider like a 2x2 contact sheet
    img[358:362, :] = 0
    img[:, 638:642] = 0
    cv2.imwrite(str(anchor), img)
    cv2.imwrite(str(sheet), img)

    vault = ElementsVault("stone_age_test", "35mm anamorphic Netflix Life on Our Planet")
    vault.register(element_id="loc_cave", kind="location", display_name="Cave Shelter", canonical_traits="limestone arch", anchor_image=anchor)
    vault.register(element_id="char_hunter", kind="character", display_name="Hunter", canonical_traits="wolf fur pelt", anchor_image=anchor)

    p = build_popcorn_2x2_prompt(
        vault,
        scene_title="First Spark",
        element_ids=["loc_cave", "char_hunter"],
        panels={"top_left": "wide", "top_right": "ots", "bottom_left": "cu", "bottom_right": "macro"},
    )
    assert len(p["reference_images"]) == 1  # deduplicated path

    sliced = slice_and_upscale_2x2_sheet(sheet, tmp_path / "sliced", target_size=(640, 360))
    assert len(sliced["panels"]) == 4
    for pan in sliced["panels"]:
        assert Path(pan["path"]).is_file()
        assert len(pan["sha256"]) == 64

    seq = plan_dramatic_scene_sequence(
        scene_id="act2_spark",
        cards=[
            SceneShotCard("sh1", "native_multishot", "zoom_in", 6.0, "Hunter strikes flint", "cold hearth", "sparks fly"),
            SceneShotCard("sh2", "extend_last_frame", "truck", 5.0, "Ember catches birch bark", "glowing spark", "steady flame", chain_depth=1),
        ],
        style_directive=vault.style_directive,
    )
    assert seq["shot_count"] == 2
    with pytest.raises(ValueError):
        SceneShotCard("bad", "extend_last_frame", "zoom_in", 5.0, "Action", "a", "b", chain_depth=4).validate()


def test_youtube_viewer_panel_validator_and_curve_render(tmp_path: Path) -> None:
    report = {
        "schema": "youtube_viewer_panel/1",
        "video_sha256": "a" * 64,
        "ab_packaging": {"winner": "B", "variants": []},
        "personas": [{"name": "P1"}, {"name": "P2"}, {"name": "P3"}],
        "retention_curve_15s": [{"time_s": 0, "pct": 100}, {"time_s": 30, "pct": 78}, {"time_s": 180, "pct": 56}],
        "aggregate_retention_at_30s_pct": 78.0,
        "aggregate_avg_view_pct": 66.5,
        "critical_drop_off_defects": [],
        "overall_youtube_readiness_score": 8.9,
        "verdict": "APPROVE",
    }
    rp = tmp_path / "viewer_panel.json"
    rp.write_text(json.dumps(report), encoding="utf-8")
    v = verify_viewer_panel_report(rp, expected_sha256="a" * 64)
    assert v["status"] == "PASS"

    png = render_retention_curve_png(report, tmp_path / "curve.png")
    assert png.is_file() and png.stat().st_size > 5000
