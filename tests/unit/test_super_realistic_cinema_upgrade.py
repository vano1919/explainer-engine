"""Unit & integration tests for Wave 1-2 Super-Realistic Cinema Engine & Antigravity Governance."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from explainer_engine.audio.scene_soundscape import build_scene_locked_soundscape
from explainer_engine.core.external_assets import verify_external_manifest
from explainer_engine.core.spend_caps import OverCeiling
from explainer_engine.edit.trim import detect_speech_end_s, trim_clip_bp187
from explainer_engine.episode.style_bible import lint_super_realistic_prompt, load_super_realistic_film_bible
from explainer_engine.finish.cinema_grade import grade_and_upscale_video_2k
from explainer_engine.governance.antigravity_runner import AntigravityRunner
from explainer_engine.qa import cinema_gates as CG
from explainer_engine.qa.style_prompt import check_super_realistic_prompt
from explainer_engine.videolane.ltx_loop import (
    enforce_ltx_action_clip_contract,
    lint_before_state_keyframe,
    sha256_file,
    validate_anchor_binding,
)

REPO = Path(__file__).resolve().parents[2]


def test_super_realistic_film_bible_and_style_purity_linter() -> None:
    bible = load_super_realistic_film_bible(REPO)
    assert bible["film_id"] == "super_realistic_cinema_35mm_master"
    assert bible["delivery_master"]["width"] == 2560
    assert bible["delivery_master"]["height"] == 1440

    # Clean realistic prompt passes (even with negated forbidden words)
    good = "Photorealistic 35mm live-action historical cinema on ARRI Alexa, weathered wool and iron, natural fog, no cartoon look, never 3d render."
    assert lint_super_realistic_prompt(good) == []
    assert check_super_realistic_prompt(good) == []

    # Affirmative legacy cartoon/storybook/comic tokens MUST FAIL
    for bad in (
        "Painterly storybook illustration with cozy rim light",
        "Colorful cartoon soldier in flat vector hills",
        "Render title with ComicNeue font",
    ):
        assert lint_super_realistic_prompt(bad), f"Expected failure for: {bad}"
        assert check_super_realistic_prompt(bad)


def test_antigravity_runner_enforces_15_usd_cap_and_12_usd_checkpoint(tmp_path: Path) -> None:
    db = tmp_path / "spend.sqlite3"
    log = tmp_path / "exec.jsonl"
    runner = AntigravityRunner(repo_root=REPO, spend_db_path=db, exec_log_path=log)

    # Reserve and settle $10.00 -> under $12 checkpoint
    r1 = runner.reserve_modal_spend("clip_batch_1", 10.0, why="test batch 1")
    assert r1["checkpoint_warning"] is False
    runner.settle_modal_spend("clip_batch_1", 10.0)

    # Reserve $3.00 -> triggers $12.00 checkpoint warning but stays under $15.00 hard ceiling
    r2 = runner.reserve_modal_spend("clip_batch_2", 3.0, why="test batch 2")
    assert r2["checkpoint_warning"] is True
    runner.settle_modal_spend("clip_batch_2", 2.5)

    # Attempt to reserve $3.00 -> $12.50 + $3.00 = $15.50 > $15.00 hard ceiling MUST raise OverCeiling
    with pytest.raises(OverCeiling, match="hard ceiling"):
        runner.reserve_modal_spend("clip_batch_over", 3.0, why="should block")

    rec = runner.reconcile_spend(tmp_path / "reconcile.json")
    assert rec["status"] == "PASS"
    assert rec["modal_total_spent_usd"] == 12.5
    assert rec["stuck_reserved_count"] == 0
    assert rec["other_external_paid_usd"] == 0.0

    # Governance guard blocks unsafe writes and commands
    with pytest.raises(PermissionError):
        runner.check_write(REPO / "config" / "owner_approvals.json")
    with pytest.raises(PermissionError):
        runner.check_bash("git reset --hard HEAD~1")


def test_anchor_binding_before_state_and_prop_continuity(tmp_path: Path) -> None:
    char_p = tmp_path / "char_anchor.png"
    loc_p = tmp_path / "loc_anchor.png"
    char_p.write_bytes(b"char-anchor-bytes")
    loc_p.write_bytes(b"loc-anchor-bytes")
    registry = {
        "hero_a": {"path": str(char_p), "sha256": sha256_file(char_p)},
        "fort_a": {"path": str(loc_p), "sha256": sha256_file(loc_p)},
    }

    good_shot = {
        "shot_id": "s1",
        "character_anchors": ["hero_a"],
        "location_anchor": "fort_a",
        "reference_image_paths": [str(char_p), str(loc_p)],
        "start_frame_description": "Unlit stone beacon brazier stacked with dry timber at twilight",
        "motion_prompt": "The watchman lowers the burning torch into the dry timber; sparks rise while the torch remains in his right hand.",
    }
    assert validate_anchor_binding(good_shot, registry) == []
    assert lint_before_state_keyframe(good_shot) == []

    # Missing ImagePaths reference MUST fail DEF-01/DEF-02
    bad_ref = dict(good_shot, reference_image_paths=[str(char_p)])
    assert validate_anchor_binding(bad_ref, registry)

    # After-state keyframe on transformation shot MUST fail DEF-04
    bad_state = dict(good_shot, start_frame_description="Beacon is already lit and blazing with roaring flames at start")
    assert lint_before_state_keyframe(bad_state)

    # Prop end-state & 4-6s ceiling (DEF-05)
    ok_ltx = enforce_ltx_action_clip_contract(5.0, good_shot["motion_prompt"])
    assert ok_ltx["status"] == "PASS" and ok_ltx["ltx_frames"] == 121

    too_long = enforce_ltx_action_clip_contract(9.5, good_shot["motion_prompt"])
    assert too_long["status"] == "FAIL"

    vanishing_prop = enforce_ltx_action_clip_contract(5.0, "The watchman waves a burning torch near the dry woodpile as sparks rise.")
    assert vanishing_prop["status"] == "FAIL"


def test_bp187_speech_end_trimmer_and_2k_lut_grade(tmp_path: Path) -> None:
    # Synthesize a 6.0s video whose audio speaks from 0.2s to 2.0s then goes silent for 4.0s
    raw_mp4 = tmp_path / "raw_dead_tail.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=0x445058:s=640x352:r=24:d=6.0",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2.0",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=4.0",
            "-filter_complex", "[1:a]aformat=channel_layouts=stereo,volume=0.35[s1];[s1][2:a]concat=n=2:v=0:a=1[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(raw_mp4),
        ],
        check=True,
    )

    det = detect_speech_end_s(raw_mp4)
    assert det["has_activity"] is True
    assert 1.8 <= det["speech_end_s"] <= 2.3

    trimmed = tmp_path / "trimmed.mp4"
    rep = trim_clip_bp187(raw_mp4, trimmed, has_dialogue=True, tail_s=0.42, max_duration_s=5.5)
    assert rep["bp187_pass"] is True
    assert rep["trimmed_duration_s"] < 3.0
    assert rep["trimmed_removed_s"] > 3.0

    # Grade & upscale to 2K 2560x1440 via unified .cube LUT
    graded_2k = tmp_path / "graded_2k.mp4"
    g_rep = grade_and_upscale_video_2k(trimmed, graded_2k, width=640, height=360, fps=24)
    assert Path(g_rep["output_path"]).is_file()
    assert g_rep["lut_used"] is not None

    deliv = CG.check_master_delivery_specs(graded_2k, expected_width=640, expected_height=360, expected_fps=24.0)
    assert deliv["status"] == "PASS", deliv


def test_external_manifest_l2_gate_passes() -> None:
    res = verify_external_manifest(repo_root=REPO, allow_missing_large_optional=True)
    assert res["status"] == "PASS", res


@pytest.mark.media
def test_multitrack_soundscape_with_sidechain_ducking(tmp_path: Path) -> None:
    # Create a short 2.0s synthetic stereo speech track
    sp_wav = tmp_path / "narr.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "sine=frequency=320:sample_rate=48000:duration=2.0",
            "-ac", "2", "-c:a", "pcm_s16le", str(sp_wav),
        ],
        check=True,
    )
    shots = [
        {"shot_id": "s1", "kind": "25d", "scene_environment": "dry_daylight_valley", "start_s": 0.0, "end_s": 3.0},
        {"shot_id": "s2", "kind": "map", "scene_environment": "map_table_war_room", "start_s": 3.0, "end_s": 6.0},
    ]
    cues = [{"cue_id": "m1", "sfx": "parchment_unfold", "timestamp_s": 3.1, "gain_db": -3.0}]
    rep = build_scene_locked_soundscape(
        shots,
        tmp_path / "ducked.wav",
        sfx_cues=cues,
        narration_tracks=[{"label": "narr_1", "wav_path": str(sp_wav), "start_s": 0.3, "gain_db": 0.0}],
        total_duration_s=6.0,
        library_manifest_path=REPO / "assets/audio/library/cc0_cinema_manifest.json",
    )
    assert -14.5 <= rep["integrated_lufs"] <= -13.5
    assert rep["peak_dbfs"] <= -1.0
    assert rep["narrator_s"] > 1.5
    assert CG.check_audio_scene_consistency(rep)["status"] == "PASS"
