"""v4.3 P1 (plan section 5, D-131): one episode id per folder (EP-01), the shot route with its reason, the visual mix by duration,
the new shot fields, and dialogue only inside played scenes. One failing case per new rule."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

from explainer_engine.episode import router as R
from explainer_engine.episode import validate as V
from explainer_engine.scripting import scene_lint

ROOT = Path(__file__).resolve().parents[2]
TOBA = ROOT / "episodes" / "ep_toba"
SCHEMA = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
MANIFEST_SCHEMA = json.loads((ROOT / "explainer_engine" / "schemas" / "episode_manifest.schema.json").read_text(encoding="utf-8"))


def toba() -> dict:
    return json.loads((TOBA / "story" / "production_script.json").read_text(encoding="utf-8"))


def shot(**kw) -> dict:
    base = {"shot_id": "S01_SH001", "segment_id": "S01", "character_ids": [], "narrative_purpose": "", "action_start_state": "",
            "action_end_state": "", "visual_type": "composed_illustration", "generation_mode": "STILL_25D", "audio_line_ids": []}
    base.update(kw)
    return base


# --- EP-01: one id per episode ---------------------------------------------------------------------------------------------

def test_ep01_the_toba_folder_carries_one_id():
    assert V.check_episode_ids(TOBA) == []


def test_ep01_a_document_with_another_id_fails(tmp_path):
    root = tmp_path / "ep_x"
    (root / "story").mkdir(parents=True)
    (root / "episode.json").write_text(json.dumps({"episode_id": "ep_x"}), encoding="utf-8")
    (root / "story" / "production_script.json").write_text(json.dumps({"episode_id": "ep_x_old"}), encoding="utf-8")
    rows = V.check_episode_ids(root)
    assert [r["rule"] for r in rows] == ["EP-01"] and rows[0]["severity"] == "FAIL" and "ep_x_old" in rows[0]["detail"]


def test_ep01_a_folder_named_otherwise_fails(tmp_path):
    root = tmp_path / "wrong"
    root.mkdir()
    (root / "episode.json").write_text(json.dumps({"episode_id": "ep_x"}), encoding="utf-8")
    assert [r["rule"] for r in V.check_episode_ids(root)] == ["EP-01"]


def test_ep01_cli_exits_one_on_a_fail(tmp_path):
    root = tmp_path / "ep_x"
    root.mkdir()
    (root / "episode.json").write_text(json.dumps({"episode_id": "ep_y"}), encoding="utf-8")
    assert V.main([str(root)]) == 1 and V.main([str(TOBA)]) == 0


# --- the router (Q4, Q6, Q7) -----------------------------------------------------------------------------------------------

def test_a_map_goes_to_map_action():
    assert R.route_shot(shot(visual_type="map_visualization"))[0] == "map_action"
    assert R.route_shot(shot(narrative_purpose="A relief map shows the ash spreading west"))[0] == "map_action"


def test_a_speaker_in_frame_goes_to_wan_with_the_reason():
    route, why = R.route_shot(shot(character_ids=["kael"], action_start_state="Kael stands by the fire"), {"kael"})
    assert route == "wan" and "Q7" in why and "kael" in why


def test_a_body_action_goes_to_wan_and_a_held_pose_does_not():
    assert R.route_shot(shot(character_ids=["kael"], action_start_state="Kael sprints across the ash"))[0] == "wan"
    route, why = R.route_shot(shot(character_ids=["kael"], action_start_state="Kael stands and gazes at the sky"))
    assert route == "still_25d" and "Q4" in why


def test_a_distant_crowd_and_an_empty_place_stay_still():
    assert R.route_shot(shot(character_ids=["kael"], action_start_state="tiny figures walk across the plain"))[0] == "still_25d"
    assert R.route_shot(shot(action_start_state="ash falls over the empty riverbed"))[0] == "still_25d"


def test_the_router_is_deterministic_and_keeps_a_locked_route():
    doc = toba()
    a = R.route_script(copy.deepcopy(doc))
    b = R.route_script(copy.deepcopy(doc))
    assert a == b and all(r["route"] in R.ROUTES and len(r["reason"]) > 10 for r in a)
    doc["shots"][0].update(route="wan", route_reason="hand-picked for the opening run", route_locked=True)
    rows = R.route_script(doc)
    assert rows[0] == {"shot_id": doc["shots"][0]["shot_id"], "route": "wan", "reason": "hand-picked for the opening run",
                       "locked": True}


def test_the_mix_is_reported_by_duration_not_by_count():
    doc = {"shots": [{"shot_id": "a", "route": "wan", "target_duration_seconds": 9.0},
                     {"shot_id": "b", "route": "still_25d", "target_duration_seconds": 1.0},
                     {"shot_id": "c", "route": "still_25d", "target_duration_seconds": 1.0},
                     {"shot_id": "d"}]}
    rep = R.mix_report(doc)
    assert rep["basis"] == "estimated" and rep["shares"]["wan"] == round(9 / 11, 4) and rep["unrouted"] == ["d"]
    rep = R.mix_report(doc, durations={"a": 1.0, "b": 1.0, "c": 1.0})
    assert rep["basis"] == "measured" and rep["shares"]["still_25d"] == round(2 / 3, 4)


def test_the_toba_script_routes_and_reports_its_mix():
    doc = toba()
    R.route_script(doc)
    rep = R.mix_report(doc)
    assert rep["unrouted"] == [] and abs(sum(rep["shares"].values()) - 1.0) < 1e-3
    print("Toba mix by duration:", rep["shares"])


# --- schema: the new shot fields --------------------------------------------------------------------------------------------

def shot_validator():
    return jsonschema.Draft202012Validator({**SCHEMA["$defs"]["ShotSpec"], "$defs": SCHEMA["$defs"]})


def a_valid_shot() -> dict:
    doc = toba()
    s = copy.deepcopy(doc["shots"][0])
    s.pop("video_engine_tier", None)
    return s


def test_the_toba_script_validates_against_the_v4_schema():
    errs = sorted(jsonschema.Draft202012Validator(SCHEMA).iter_errors(toba()), key=lambda e: list(e.path))
    assert not errs, [f"{list(e.path)}: {e.message}" for e in errs[:5]]


def test_route_fields_are_accepted_and_an_unknown_route_is_refused():
    v = shot_validator()
    s = a_valid_shot()
    s.update(route="still_25d", route_reason="the heroes hold a pose; the camera carries it",
             motion_imitation={"camera": "push_in", "effects": ["ash_fall", "fire_flicker"]},
             sound_events=[{"kind": "ambience", "what": "wind over ash", "source": "library"}])
    assert not list(v.iter_errors(s))
    bad = dict(s, route="gemini_video")
    assert list(v.iter_errors(bad))


def test_motion_imitation_only_on_still_and_actions_only_on_maps():
    v = shot_validator()
    s = a_valid_shot()
    s.update(route="wan", route_reason="a body performs an action", motion_imitation={"camera": "hold"})
    assert list(v.iter_errors(s))
    s = a_valid_shot()
    s.update(route="still_25d", route_reason="a place at rest, moved by the camera", actions=[{"kind": "pulse", "at_word": "Toba"}])
    assert list(v.iter_errors(s))
    s = a_valid_shot()
    s.update(route="map_action", route_reason="geography: the ash cloud spreads", actions=[{"kind": "spread", "at_word": "ash"}])
    assert not list(v.iter_errors(s))


def test_a_locked_route_needs_its_reason():
    s = a_valid_shot()
    s.pop("route_reason", None)
    s.update(route="wan", route_locked=True)
    assert list(shot_validator().iter_errors(s))
    s["route_reason"] = "the creator picked this shot for the opening"
    assert not list(shot_validator().iter_errors(s))


def test_the_unapproved_gemini_video_engines_are_gone():
    enum = SCHEMA["$defs"]["ShotSpec"]["properties"]["video_engine_tier"]["enum"]
    assert "GEMINI_LIGHT_VIDEO_I2V" not in enum and "GEMINI_VIDEO_API_BATCH" not in enum
    s = a_valid_shot()
    s["video_engine_tier"] = "GEMINI_LIGHT_VIDEO_I2V"
    assert list(shot_validator().iter_errors(s))


def test_the_manifest_takes_the_look_fields_and_refuses_a_small_master():
    m = json.loads((TOBA / "episode.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(MANIFEST_SCHEMA)
    assert not list(v.iter_errors(m))
    assert m["look_id"] and m["map_style"] and m["image_min_long_side"] >= 2048
    assert list(v.iter_errors(dict(m, image_min_long_side=1376)))


# --- dialogue lives in played scenes ----------------------------------------------------------------------------------------

def test_a_hero_line_outside_a_played_scene_fails():
    doc = toba()
    assert not [f for f in scene_lint.lint(doc) if f["rule"] == "SC-01" and "dialogue belongs" in f["detail"]]
    narr = next(s for s in doc["segments"] if s.get("segment_mode") == "narration_led")
    line = copy.deepcopy(next(l for l in doc["audio_lines"] if l["speaker_type"] == "character"))
    line.update(line_id=f"{narr['segment_id']}_X01", segment_id=narr["segment_id"])
    doc["audio_lines"].append(line)
    rows = [f for f in scene_lint.lint(doc) if f["rule"] == "SC-01" and "dialogue belongs" in f["detail"]]
    assert rows and rows[0]["severity"] == "FAIL"
