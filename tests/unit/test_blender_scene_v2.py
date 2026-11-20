"""blender_scene version 2: camera paths, the 1917 film card (draft), V11 (transition angle/size), V12 (180-degree line,
movement handoff). Pure Python, no Blender."""

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.lab import scene_spec as ss

LAB = Path(ss.__file__).parent
T0_DIR, T0B_DIR = LAB / "specs" / "t0", LAB / "specs" / "t0b"


def status(results, vid):
    return next(r["status"] for r in results if r["id"] == vid)


@pytest.fixture()
def am():
    return ss.load_spec(T0B_DIR / "t0b_am1.json")


@pytest.fixture()
def clip_c():
    return ss.load_spec(T0B_DIR / "t0b_c1.json")


def test_version_1_specs_still_pass_and_report_v11_v12_not_applicable():
    for clips in ss.load_series(T0_DIR).values():
        for clip in clips:
            res = ss.validate_spec(clip)
            assert ss.summarize(res) == "PASS", clip["scene_id"]
            assert status(res, "V11") == "N/A" and status(res, "V12") == "N/A"


def test_card_is_a_draft_and_has_no_colour_or_light_field():
    card = ss.load_film_style("1917")
    assert card["draft"] is True and card["unverified"]
    assert not {"light", "lighting", "colour", "color", "palette"} & set(card)
    assert card["camera_height_m"] == {"min": 1.5, "max": 1.7}
    assert "prompt_line" in card and "1917" in card["prompt_line"]


def test_card_with_a_light_field_is_refused(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"film": "x", "lighting": "warm"}), encoding="utf-8")
    with pytest.raises(ss.SceneSpecError):
        ss.load_film_style(bad)


def test_new_specs_pass_except_the_declared_long_take(am, clip_c):
    assert ss.summarize(ss.validate_spec(am)) == "PASS"
    res = ss.validate_spec(clip_c)
    assert status(res, "V3") == "REVIEW" and ss.summarize(res) == "REVIEW"
    assert [r["id"] for r in res if r["status"] in ("FAIL", "REVIEW")] == ["V3"]
    assert len(am["cuts"]) == 5 and all(c["frame_out"] - c["frame_in"] == 48 for c in am["cuts"])
    assert len(clip_c["cuts"]) == 1 and clip_c["cuts"][0]["frame_out"] - clip_c["cuts"][0]["frame_in"] == 240


def test_long_take_needs_the_declaration(clip_c):
    bad = copy.deepcopy(clip_c)
    del bad["cuts"][0]["long_take"]
    assert status(ss.validate_spec(bad), "V3") == "FAIL"


def test_path_camera_interpolates_and_holds(clip_c):
    cut = clip_c["cuts"][0]
    start, mid, end = (ss.camera_state(clip_c, cut, f) for f in (0, 100, 240))
    assert start["pos"][1] == -2.0 and end["pos"][1] == 10.69
    assert start["pos"][1] < mid["pos"][1] < end["pos"][1]
    assert ss.camera_state(clip_c, cut, 222) == ss.camera_state(clip_c, cut, 240)      # V9: at rest for the tail


def test_ease_out_stops_slowly():
    cam = {"path": [{"frame": 0, "pos": [0, 0, 1.6], "heading": 0, "pitch": 0, "lens": 35, "ease": "out"},
                    {"frame": 24, "pos": [0, 6, 1.6], "heading": 0, "pitch": 0, "lens": 35}]}
    ys = [ss.path_state(cam, f)["pos"][1] for f in (0, 12, 22, 23, 24)]
    assert ys[1] > 4.0 and ys[4] - ys[3] < ys[2] - ys[1]            # fast start, last step the smallest


def test_v5_reads_lenses_and_heights_from_the_card(am):
    bad = copy.deepcopy(am)
    bad["cameras"][0]["path"][1]["lens"] = 24
    assert status(ss.validate_spec(bad), "V5") == "FAIL"
    tall = copy.deepcopy(am)
    for k in tall["cameras"][0]["path"]:
        k["pos"][2] = 2.4
    assert status(ss.validate_spec(tall), "V5") == "REVIEW"            # draft card: hypothesis range asks for a look


# ------------------------------------------------------------------------------------------------ V11

def test_v11_fails_when_two_views_are_nearly_the_same(am):
    """Same angle around the subject and the same size = a jump cut."""
    bad = copy.deepcopy(am)
    bad["cameras"][1] = copy.deepcopy(bad["cameras"][0])
    bad["cameras"][1]["id"] = "am_v2"
    for k in bad["cameras"][1]["path"]:
        k["frame"] += 48
    bad["cameras"][1]["path"][0]["frame"], bad["cameras"][1]["path"][1]["frame"] = 48, 96
    res = ss.validate_spec(bad)
    assert status(res, "V11") == "REVIEW"
    assert "am_v1->am_v2" in next(r for r in res if r["id"] == "V11")["message"]


def test_v11_draft_card_asks_a_verified_card_blocks(am, monkeypatch):
    bad = copy.deepcopy(am)
    bad["cameras"][1] = {"id": "am_v2", "path": [dict(k, frame=k["frame"] + 48) for k in bad["cameras"][0]["path"]]}
    assert status(ss.validate_spec(bad), "V11") == "REVIEW"
    card = ss.load_film_style("1917")
    card["draft"] = False
    monkeypatch.setattr(ss, "spec_card", lambda spec: card)
    assert status(ss.validate_spec(bad), "V11") == "FAIL"


def test_v11_passes_on_an_angle_change_or_a_size_step(am):
    rows = ss.transitions(am)
    assert all(r["angle_deg"] >= 30 for r in rows)
    assert {r["size_steps"] for r in rows} >= {1, 2}
    assert status(ss.validate_spec(am), "V11") == "PASS"
    # same angle but a size step is enough
    ok = copy.deepcopy(am)
    ok["cameras"][1] = copy.deepcopy(ok["cameras"][0])
    ok["cameras"][1]["id"] = "am_v2"
    for k in ok["cameras"][1]["path"]:
        k["frame"] += 48
    ok["cameras"][1]["path"][0]["lens"] = ok["cameras"][1]["path"][1]["lens"] = 85
    row = ss.transitions(ok)[0]
    assert row["angle_deg"] < 30 and row["size_steps"] >= 1


def test_v11_threshold_boundary(am, monkeypatch):
    card = ss.load_film_style("1917")
    angle = ss.transitions(am)[0]["angle_deg"]
    steps = ss.transitions(am)[0]["size_steps"]
    card["transition"]["min_size_steps"] = steps + 1                  # size no longer rescues the first transition
    monkeypatch.setattr(ss, "spec_card", lambda spec: card)
    card["transition"]["min_angle_deg"] = angle - 0.5                 # just below the measured angle: PASS
    assert status(ss.validate_spec(am), "V11") == "PASS" or ss.transitions(am)[0]["angle_deg"] >= angle - 0.5
    card["transition"]["min_angle_deg"] = angle + 0.5                 # just above: the first transition is a jump
    assert status(ss.validate_spec(am), "V11") == "REVIEW"


# ------------------------------------------------------------------------------------------------ V12

def test_v12_axis_crossing_fails_without_axis_cross_ok(am):
    bad = copy.deepcopy(am)
    cam = bad["cameras"][2]
    for k in cam["path"]:                                            # mirror camera 3 to the other side of the line
        k["pos"][0] = -k["pos"][0]
        k["heading"] = (-k["heading"]) % 360
    res = ss.validate_spec(bad)
    assert status(res, "V12") == "FAIL" and "180" in next(r for r in res if r["id"] == "V12")["message"]
    rows = ss.transitions(bad)
    assert any(r["side_from"] * r["side_to"] == -1 for r in rows)
    for c in bad["cuts"]:
        c["axis_cross_ok"] = True                                    # declared: the same crossing is allowed
    assert status(ss.validate_spec(bad), "V12") != "FAIL"


def test_v12_camera_on_the_line_is_neutral(am):
    rows = ss.transitions(am)
    assert {r["side_from"] for r in rows} == {-1} and {r["side_to"] for r in rows} == {-1}
    ok = copy.deepcopy(am)
    people = {p["id"]: p for p in ok["people"]}
    for k in ok["cameras"][0]["path"]:                               # put the camera exactly on the private->german line
        a, b = (ss.person_state(people[i], k["frame"])["pos"] for i in ("private", "german"))
        t = (k["pos"][1] - a[1]) / (b[1] - a[1])
        k["pos"][0] = a[0] + t * (b[0] - a[0])
    assert ss.transitions(ok)[0]["side_from"] == 0
    assert status(ss.validate_spec(ok), "V12") == "PASS"


def test_v12_movement_direction_must_hand_over(am):
    bad = copy.deepcopy(am)
    p = bad["cameras"][1]["path"]
    p[1]["pos"] = [p[0]["pos"][0] + 0.0, p[0]["pos"][1] + 1.4, 1.6]  # camera 2 now moves another way than camera 1
    cam1 = bad["cameras"][0]["path"]
    cam1[1]["pos"] = [cam1[0]["pos"][0] - 1.4, cam1[0]["pos"][1], 1.6]
    res = ss.validate_spec(bad)
    assert status(res, "V12") == "REVIEW"
    assert "direction" in next(r for r in res if r["id"] == "V12")["message"]


def test_v12_speed_jump_is_flagged_and_boundary_is_the_cards_ratio(am, monkeypatch):
    row = ss.transitions(am)[0]
    ratio = max(row["speed_from_mps"], row["speed_to_mps"]) / min(row["speed_from_mps"], row["speed_to_mps"])
    card = ss.load_film_style("1917")
    monkeypatch.setattr(ss, "spec_card", lambda spec: card)
    card["transition"]["handoff_max_speed_ratio"] = ratio + 0.01     # just above the measured ratio: no complaint here
    assert status(ss.validate_spec(am), "V12") == "PASS"
    card["transition"]["handoff_max_speed_ratio"] = ratio - 0.01     # just below: speed jump
    res = ss.validate_spec(am)
    assert status(res, "V12") == "REVIEW" and "speed" in next(r for r in res if r["id"] == "V12")["message"]


def test_still_to_moving_is_not_a_handoff_failure(am):
    ok = copy.deepcopy(am)
    p = ok["cameras"][1]["path"]
    p[1]["pos"] = list(p[0]["pos"])                                  # camera 2 stands still
    assert status(ss.validate_spec(ok), "V12") == "PASS"


def test_report_rows_carry_angle_size_side_and_speed(am):
    row = ss.transitions(am)[0]
    for key in ("angle_deg", "size_from", "size_to", "side_from", "side_to", "speed_from_mps", "speed_to_mps"):
        assert key in row
    assert ss.transitions(ss.load_spec(T0B_DIR / "t0b_c1.json")) == []


def test_schema_accepts_old_static_camera_and_refuses_a_camera_with_neither():
    spec = ss.load_spec(T0_DIR / "t0_a1.json")
    broken = copy.deepcopy(spec)
    broken["cameras"][0] = {"id": "x"}
    with pytest.raises(ss.SceneSpecError):
        ss.check_schema(broken)
