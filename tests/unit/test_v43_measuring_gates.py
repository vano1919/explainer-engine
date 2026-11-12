"""v4.3 plan P2 (EP-03): every acceptance gate measures or says NOT_RUN, and each one can FAIL (one negative test per gate)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.episode import acceptance as A
from explainer_engine.orchestration.rule_enforcer import wan_chain_check
from explainer_engine.qa import gates as G

REPO = Path(__file__).resolve().parents[2]


def _episode(tmp_path: Path, eid: str = "ep_x") -> Path:
    root = tmp_path / eid
    (root / "clips").mkdir(parents=True)
    (root / "episode.json").write_text(json.dumps({"episode_id": eid}), encoding="utf-8")
    return root


def _clip(root: Path, name: str) -> str:
    p = root / "clips" / name
    p.write_bytes(b"x" * 64)
    return str(p)


def _script():
    return {"shots": [
        {"shot_id": "S1", "route": "map_action", "target_duration_seconds": 4.0, "image_prompt": "a map of Sumatra"},
        {"shot_id": "S2", "route": "still_25d", "target_duration_seconds": 6.0, "image_prompt": "ash over the forest"},
    ]}


def _good(root: Path, **over):
    kw = dict(
        root=root, script=_script(),
        shot_records=[{"shot_id": "S1", "visual_type": "map_visualization", "clip_path": _clip(root, "S1.mp4")},
                      {"shot_id": "S2", "visual_type": "cinematic_scene", "clip_path": _clip(root, "S2.mp4"),
                       "source_start_keyframe": _clip(root, "S2.jpg")}],
        transition_plans=[{"from_shot_id": "S1", "ed04_compliant": True}],
        audio={"blocked_era_events": []}, stem_audit={"mid_line_narration_dropouts": 0, "sound_director_stem_findings": []},
        video={"duration_sec": 10.0, "total_frames": 240}, fps=24, forbidden_tokens=("waterloo",),
        narration_source=_clip(root, "read.wav"), paid_calls=0)
    kw.update(over)
    return A.gates(**kw)


def _status(rep, gate):
    return next(r["status"] for r in rep["gates"] if r["gate"] == gate)


def test_row_refuses_a_non_bool_outcome_and_none_is_not_run():
    with pytest.raises(TypeError):
        G.row("g", 1, "a number is not a measurement")
    assert G.row("g", None, "why")["status"] == G.NOT_RUN
    assert G.verdict([])["status"] == G.NOT_RUN
    assert G.verdict([G.row("a", True, ""), G.row("b", None, "")])["status"] == "INCOMPLETE"
    assert G.verdict([G.row("a", True, ""), G.row("b", False, "")])["status"] == G.FAIL


def test_a_full_good_run_passes_except_the_unmeasured_camera_row(tmp_path):
    rep = _good(_episode(tmp_path))
    assert rep["failed"] == []
    assert rep["not_run"] == ["camera_motion_measured"]       # P5 adds the measurement; until then never a PASS
    assert rep["status"] == "INCOMPLETE"


@pytest.mark.parametrize("measured, want", [("PASS", "PASS"), ("REVIEW", "PASS"), ("INCOMPLETE", "NOT_RUN"), ("FAIL", "FAIL")])
def test_the_motion_row_reads_the_layered_renderer_gates(tmp_path, measured, want):
    root = _episode(tmp_path)
    recs = [{"shot_id": "S1", "visual_type": "map_visualization", "clip_path": _clip(root, "S1.mp4")},
            {"shot_id": "S2", "visual_type": "cinematic_scene", "clip_path": _clip(root, "S2.mp4"),
             "source_start_keyframe": _clip(root, "S2.jpg"), "gates_25d": measured}]
    assert _status(_good(root, shot_records=recs), "camera_motion_measured") == want


def test_isolation_fails_on_a_second_episode_id(tmp_path):
    root = _episode(tmp_path)
    (root / "other.json").write_text(json.dumps({"episode_id": "ep_waterloo"}), encoding="utf-8")
    assert _status(_good(root), "isolation_one_episode_id") == G.FAIL


def test_assets_fail_when_a_file_comes_from_outside_the_folder(tmp_path):
    root = _episode(tmp_path)
    foreign = tmp_path / "elsewhere.jpg"
    foreign.write_bytes(b"x")
    recs = [{"shot_id": "S1", "visual_type": "map_visualization", "clip_path": _clip(root, "S1.mp4")},
            {"shot_id": "S2", "visual_type": "cinematic_scene", "clip_path": _clip(root, "S2.mp4"),
             "source_start_keyframe": str(foreign)}]
    assert _status(_good(root, shot_records=recs), "assets_inside_the_episode") == G.FAIL


def test_foreign_era_words_in_a_prompt_fail(tmp_path):
    root = _episode(tmp_path)
    sc = _script()
    sc["shots"][1]["image_prompt"] = "Waterloo cavalry over the ash"
    assert _status(_good(root, script=sc), "no_foreign_era_words_in_prompts") == G.FAIL
    assert _status(_good(root, forbidden_tokens=()), "no_foreign_era_words_in_prompts") == G.NOT_RUN


def test_audio_era_gating_fails_on_a_blocked_event(tmp_path):
    root = _episode(tmp_path)
    assert _status(_good(root, audio={"blocked_era_events": ["cavalry_charge"]}), "audio_era_gating") == G.FAIL
    assert _status(_good(root, audio=None), "audio_era_gating") == G.NOT_RUN


def test_a_synthesized_or_missing_narration_fails(tmp_path):
    root = _episode(tmp_path)
    assert _status(_good(root, narration_source="synthesized"), "narration_is_a_real_read") == G.FAIL
    assert _status(_good(root, narration_source=str(root / "gone.wav")), "narration_is_a_real_read") == G.FAIL


def test_narration_dropouts_fail(tmp_path):
    root = _episode(tmp_path)
    bad = {"mid_line_narration_dropouts": 2, "sound_director_stem_findings": []}
    assert _status(_good(root, stem_audit=bad), "narration_has_no_dropouts") == G.FAIL


def test_a_map_shot_without_a_clip_fails_and_the_count_comes_from_the_script(tmp_path):
    root = _episode(tmp_path)
    recs = [{"shot_id": "S1", "visual_type": "map_visualization", "clip_path": str(root / "clips" / "missing.mp4")}]
    assert _status(_good(root, shot_records=recs), "every_map_shot_rendered") == G.FAIL
    sc = _script()
    sc["shots"].append({"shot_id": "S3", "route": "map_action", "target_duration_seconds": 2.0})
    assert _status(_good(root, script=sc), "every_map_shot_rendered") == G.FAIL      # 3 maps fixed in the archive; 2 here


def test_a_transition_that_breaks_ed04_fails(tmp_path):
    root = _episode(tmp_path)
    assert _status(_good(root, transition_plans=[{"from_shot_id": "S1", "ed04_compliant": False}]), "transitions_ed04") == G.FAIL


def test_the_master_length_comes_from_the_script_not_the_two_minute_pilot(tmp_path):
    root = _episode(tmp_path)
    assert _status(_good(root, video={"duration_sec": 120.0, "total_frames": 2880}), "master_length_matches_the_script") == G.FAIL
    assert _status(_good(root, video={"duration_sec": 10.0, "total_frames": 239}), "master_length_matches_the_script") == G.FAIL
    assert _status(_good(root, video=None), "master_length_matches_the_script") == G.NOT_RUN


def test_a_paid_call_fails_and_an_unread_ledger_is_not_run(tmp_path):
    root = _episode(tmp_path)
    assert _status(_good(root, paid_calls=1), "no_paid_call") == G.FAIL
    assert _status(_good(root, paid_calls=None), "no_paid_call") == G.NOT_RUN


def test_wan_chain_is_measured_on_the_scripts_own_shots():
    two = {"shots": [{"shot_id": "A", "route": "wan", "target_duration_seconds": 4.0},
                     {"shot_id": "B", "route": "wan", "target_duration_seconds": 4.0, "continues_from_previous": True}]}
    assert wan_chain_check(two)["status"] == G.PASS
    assert wan_chain_check({"shots": [{"shot_id": "A", "route": "wan"}]})["status"] == G.NOT_RUN
    two["shots"][0]["route"] = "still_25d"
    assert wan_chain_check(two)["status"] == G.FAIL
    short = {"shots": [{"shot_id": "A", "route": "wan", "target_duration_seconds": 0.25},
                       {"shot_id": "B", "route": "wan", "target_duration_seconds": 4.0, "continues_from_previous": True}]}
    assert wan_chain_check(short)["status"] == G.FAIL


def test_runner_has_no_literal_gates_and_no_two_minute_constants():
    src = (REPO / "explainer_engine" / "episode" / "production_runner.py").read_text(encoding="utf-8")
    assert "_2min" not in src and "production_script_2min" not in src
    assert '"isolation_verified": True' not in src
    assert "AC-0" not in src
    enforcer = (REPO / "explainer_engine" / "orchestration" / "rule_enforcer.py").read_text(encoding="utf-8")
    assert "splice_test = " not in enforcer and "wan_jobs\"] / max(len(shots)" not in enforcer


def test_gate_audit_status_is_review_not_fail_on_review_rows(monkeypatch):
    from explainer_engine.orchestration import rule_enforcer as RE
    doc = json.loads((REPO / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(RE, "story_lint_v4", lambda d: [{"rule": "BP-x", "severity": "REVIEW", "where": "s", "detail": "d"}])
    for name in ("scene_lint_v4", "check_script", "check_v4_script", "check_cohesive_film_invariants_and_bounds"):
        monkeypatch.setattr(RE, name, lambda d: [])
    monkeypatch.setattr(RE, "validate_reference_library", lambda lib: [])
    assert RE.run_all_gate_audits(doc)["status"] == "REVIEW"
    monkeypatch.setattr(RE, "validate_reference_library", lambda lib: ["not locked"])
    assert RE.run_all_gate_audits(doc)["status"] == "FAIL"

