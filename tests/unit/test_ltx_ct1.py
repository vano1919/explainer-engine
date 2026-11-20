"""CT-1 in the video-lane planner (final plan P-6; reassessment 4.3c; docs/LTX_PIPELINES.md): a new shot or a camera change is a
fresh keyframe from the untouched vault master; the same shot may continue at hop 1-2 only with a recorded comparison against
the master, the x2 upscale and the LAB colour lock; hop 3 or more is refused; a long action with a known end pose is made from
start+end keyframes. The hop count is stored per clip. One test per branch."""
from __future__ import annotations

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.qa import gates as G
from explainer_engine.videolane import plan as P

GOOD_CHECK = {"master": "S1_master", "face_cosine": 0.91, "lab_delta_e": 3.2, "sharpness_ratio": 0.88,
              "upscaled_x2": True, "lab_lock": True}


def _shot(sid, *, mode="coverage", src=None, size="wide", az=0, **extra):
    ep = {"continuity_mode": mode, "cut_in_reason": "action", "scene_master": "S1_master", "axis_side": "A",
          "camera_in": "rest", "camera_out": "rest"}
    if src:
        ep["continuity_from"] = src
    ep.update(extra.pop("ep", {}))
    s = {"shot_id": sid, "route": "video", "segment_id": "S1", "location_id": "loc", "audio_line_ids": [],
         "camera_spec": {"shot_size": size, "horizontal_azimuth_deg": az, "vertical_angle": "eye_level_0"},
         "target_duration_seconds": 3.0, "edit_plan": ep, "transition_out": "hard_cut",
         "video_prompt": {"motion_prompt": f"motion {sid}", "primary_action_count": 1, "camera_move_count": 0}}
    s.update(extra)
    return s


def _chain(n, **ep_of):
    """A, then n continuations B, C, D... each from the shot before."""
    ids = [chr(65 + k) for k in range(n + 1)]
    shots = [_shot("A", ep={"cut_in_reason": "establish"})]
    for k in range(1, n + 1):
        shots.append(_shot(ids[k], mode="continuation", src=ids[k - 1], ep=ep_of.get(ids[k], {})))
    return {"shots": shots, "audio_lines": [], "fps": 24}


def _rules(doc, severity=None):
    return {(f["rule"], f["shot_id"]) for f in P.ct1_findings(doc) if severity is None or f["severity"] == severity}


def test_hops_count_the_frame_hand_overs_since_the_last_fresh_keyframe():
    doc = _chain(3)
    doc["shots"].append(_shot("E", ep={"cut_in_reason": "scene_change"}))     # a new shot: fresh from the master again
    doc["shots"].append(_shot("F", mode="continuation", src="E"))
    assert P.ct1_hops(doc) == {"A": 0, "B": 1, "C": 2, "D": 3, "E": 0, "F": 1}


def test_hop_one_and_two_without_their_recorded_check_are_listed_not_blocked_and_with_it_pass():
    doc = _chain(2)
    assert _rules(doc, G.FAIL) == set() and _rules(doc, G.REVIEW) == {("CT1-03", "B"), ("CT1-03", "C")}
    ok = _chain(2, B={"continuation_check": dict(GOOD_CHECK)}, C={"continuation_check": dict(GOOD_CHECK)})
    assert _rules(ok) == set()


def test_a_recorded_check_without_its_measurements_or_x2_or_lab_lock_blocks():
    bad = dict(GOOD_CHECK, lab_lock=False)
    assert ("CT1-03", "B") in _rules(_chain(1, B={"continuation_check": bad}), G.FAIL)
    thin = {k: v for k, v in GOOD_CHECK.items() if k != "face_cosine"}
    why = [f["detail"] for f in P.ct1_findings(_chain(1, B={"continuation_check": thin})) if f["severity"] == G.FAIL]
    assert any("face_cosine" in w for w in why)
    nomaster = dict(GOOD_CHECK, master="")
    assert ("CT1-03", "B") in _rules(_chain(1, B={"continuation_check": nomaster}), G.FAIL)
    assert ("CT1-03", "B") in _rules(_chain(1, B={"continuation_check": dict(GOOD_CHECK, upscaled_x2=False)}), G.FAIL)
    assert P.ct1_check_problems(GOOD_CHECK, 2) == [] and P.ct1_check_problems(GOOD_CHECK, 3) != []


def test_hop_three_is_refused_whatever_its_check_says():
    c = {"continuation_check": dict(GOOD_CHECK)}
    doc = _chain(3, B=c, C=c, D=c)
    assert ("CT1-01", "D") in _rules(doc, G.FAIL) and ("CT1-01", "C") not in _rules(doc)
    assert any("forced cut" in f["detail"] for f in P.ct1_findings(doc) if f["rule"] == "CT1-01")
    rows = {r["gate"]: r["status"] for r in P.rows(doc)}
    assert rows["video_edit_plan"] == G.FAIL                                # the paid scene is blocked through the gate row


def test_a_camera_change_inside_a_continuation_needs_a_fresh_keyframe():
    doc = _chain(1)
    doc["shots"][1]["camera_spec"]["shot_size"] = "close_up"
    assert ("CT1-02", "B") in _rules(doc, G.FAIL)
    doc = _chain(1)
    doc["shots"][1]["camera_spec"]["horizontal_azimuth_deg"] = 90
    assert ("CT1-02", "B") in _rules(doc, G.FAIL)
    assert ("CT1-02", "B") not in _rules(_chain(1))


def test_a_long_action_with_a_known_end_pose_is_made_from_start_and_end_keyframes():
    shot = _shot("A", action_end_state="Thomas steps onto the fire step", keyframe_plan={"needs_end_frame": True})
    doc = {"shots": [shot], "audio_lines": [], "fps": 24}
    assert _rules(doc, G.REVIEW) == {("CT1-04", "A")} and P.ct1_kind(shot) == "clip"          # no end picture named yet
    shot["edit_plan"]["end_keyframe"] = "A_end"
    assert _rules(doc) == set() and P.ct1_kind(shot) == "keyframes"
    shot["action_end_state"] = ""
    assert any("no end pose" in f["detail"] for f in P.ct1_findings(doc))


def test_a_new_shot_never_starts_from_a_last_frame():
    doc = {"shots": [_shot("A", ep={"cut_in_reason": "establish"}),
                     _shot("B", ep={"start_source": "prev_clip_last_frame"})], "audio_lines": [], "fps": 24}
    assert ("CT1-05", "B") in _rules(doc, G.FAIL)
    doc["shots"][1]["edit_plan"]["start_source"] = "vault_master"
    assert _rules(doc) == set()


def test_ct1_findings_are_part_of_the_edit_plan_gate():
    c = {"continuation_check": dict(GOOD_CHECK)}
    doc = _chain(3, B=c, C=c, D=c)
    assert any(f["rule"] == "CT1-01" for f in P.findings(doc))


def test_the_hop_is_stored_per_clip_in_the_scene_row_and_hop_three_is_refused(tmp_path, monkeypatch):
    """scene.build writes ``hop`` and ``ct1_kind`` on every row; the worker's ``kind`` is never set from it."""
    import json
    from explainer_engine.core import open_questions as OQ
    from explainer_engine.videolane import scene as S, storyboard as SB
    doc = _chain(3)
    doc["shots"][0]["keyframe_plan"] = {"needs_end_frame": True}
    doc["shots"][0]["action_end_state"] = "end"
    doc["shots"][0]["edit_plan"]["end_keyframe"] = "A_end"
    root = tmp_path / "ep"
    (root / "production" / "storyboard").mkdir(parents=True)
    ids = [s["shot_id"] for s in doc["shots"]]
    pics = {f"{i}_start": {"file": f"p/{i}.png"} for i in ids}
    (root / "p").mkdir()
    for i in ids:
        (root / "p" / f"{i}.png").write_bytes(b"x")
    (root / "production" / "pictures.json").write_text(json.dumps({"pictures": pics}))
    (root / "production" / "storyboard" / "sc.json").write_text(json.dumps({"verdict": {"status": "PASS", "failed": []},
                                                                           "shots": ids}))
    monkeypatch.setattr(OQ, "value", lambda q: {"Q5": "prompt_description", "Q4": "advisory"}.get(q))
    monkeypatch.setattr(SB, "fresh", lambda *a, **k: [])
    monkeypatch.setattr(S, "picture_check", lambda *a, **k: {"state": "OK", "regeneration_required": False})
    monkeypatch.setattr(S, "compose_prompt", lambda *a, **k: {"prompt": "p", "parts": {}, "voice_missing": []})
    with pytest.raises(ContractError, match="hop 3"):
        S.build(root, doc, "sc", tmp_path / "scene.json")
    doc["shots"].pop()                                            # a chain of A, B, C: hops 0, 1, 2
    sb = root / "production" / "storyboard"
    (sb / "sc2.json").write_text(json.dumps({"verdict": {"status": "PASS", "failed": []}, "shots": ids[:3]}))
    ok = S.build(root, doc, "sc2", tmp_path / "scene2.json")
    assert [r["hop"] for r in ok["shots"]] == [0, 1, 2] and ok["shots"][0]["ct1_kind"] == "keyframes"
    assert all("kind" not in r for r in ok["shots"])
