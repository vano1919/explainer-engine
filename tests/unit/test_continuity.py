"""Scene continuity cards (CT-01..CT-14, docs/SHOT_CONTINUITY.md)."""

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.qa import style_prompt
from explainer_engine.scripting import continuity as cc
from explainer_engine.training import lora_rules

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "continuity" / "napoleon_tent.json"


@pytest.fixture()
def doc():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def rules(found, level="FAIL"):
    return {f["rule"] for f in found if f["level"] == level}


def test_example_passes(doc):
    assert cc.check(doc) == []


def test_schema_rejects_unknown_field(doc):
    doc["shots"][0]["mood"] = "tense"
    assert rules(cc.check(doc)) == {"CT-01"}


def test_where_when_needs_the_bg_note_shape(doc):
    doc["location"]["where_when"] = "the tent at night"
    assert "CT-01" in rules(cc.check(doc))


def test_person_and_costume_come_from_the_cast(doc):
    doc["shots"][1]["characters"][0]["costume"] = "parade"
    assert "CT-02" in rules(cc.check(doc))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["shots"][2]["characters"][0]["id"] = "drummer"
    assert "CT-02" in rules(cc.check(doc))


def test_image_one_is_the_master_frame(doc):
    doc["shots"][1]["refs"] = doc["shots"][1]["refs"][1:] + doc["shots"][1]["refs"][:1]
    assert "CT-03" in rules(cc.check(doc))


def test_head_count_is_named_plus_extras(doc):
    doc["shots"][1]["head_count"] = 3
    assert "CT-04" in rules(cc.check(doc))
    doc["shots"][1]["extras"] = 1
    assert "CT-04" not in rules(cc.check(doc))


def test_reference_cap_per_model(doc):
    doc["shots"][1]["refs"].append({"path": "style.png", "role": "style"})
    assert "CT-05" in rules(cc.check(doc))
    doc["model"] = "gemini_3_1_flash_image"
    assert "CT-05" not in rules(cc.check(doc))


def test_every_person_needs_their_sheet(doc):
    doc["shots"][2]["refs"] = doc["shots"][2]["refs"][:1]
    assert "CT-05" in rules(cc.check(doc))


def test_two_people_need_an_axis(doc):
    del doc["shots"][1]["axis"]
    assert "CT-06" in rules(cc.check(doc))


def test_crossing_the_axis_without_a_reason_is_a_review(doc):
    doc["shots"][1]["camera_side"] = "B"
    found = cc.check(doc)
    assert "CT-06" in rules(found, "REVIEW")
    assert [f["shot"] for f in found if f["rule"] == "CT-06"] == ["S04-02", "S04-03"]   # over and back again
    doc["shots"][1]["axis_cross_reason"] = "on_screen_move"
    assert [f["shot"] for f in cc.check(doc) if f["rule"] == "CT-06"] == ["S04-03"]


def test_jump_cut(doc):
    doc["shots"][1]["shot_size"] = "WS"
    found = cc.check(doc)
    assert "CT-07" in rules(found)
    doc["shots"][1]["angle_change_deg"] = 30
    assert "CT-07" not in rules(cc.check(doc))


def test_unlisted_change_fails_and_needless_change_is_a_review(doc):
    doc["shots"][1]["changes"] = []
    assert "CT-08" in rules(cc.check(doc))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["shots"][1]["characters"][0]["flags"] = ["wet"]
    assert "CT-08" in rules(cc.check(doc))
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["shots"][2]["changes"] = [{"entity": "emperor", "field": "costume", "to": "field", "cause": "none really"}]
    assert "CT-08" in rules(cc.check(doc), "REVIEW")


def test_scene_light_change_needs_a_cause(doc):
    doc["shots"][2]["key_light_dir"] = "right"
    assert "CT-08" in rules(cc.check(doc))
    doc["shots"][2]["changes"] = [{"entity": "scene", "field": "key_light_dir", "to": "right",
                                    "cause": "the marshal carries the lantern past him"}]
    assert "CT-08" not in rules(cc.check(doc))


def test_new_camera_side_does_not_demand_position_changes(doc):
    shot = doc["shots"][1]
    shot["camera_side"], shot["axis_cross_reason"] = "B", "on_screen_move"
    shot["characters"][0]["screen_pos"], shot["characters"][1]["screen_pos"] = "right", "left"
    shot["characters"][0]["facing"], shot["characters"][1]["facing"] = "left", "right"
    assert "CT-08" not in rules(cc.check(doc))


def test_chain_depth(doc):
    doc["shots"][2]["derive_from"], doc["shots"][2]["chain_depth"] = "S04-02", 2
    assert "CT-09" in rules(cc.check(doc))
    doc["shots"][2]["derive_from"] = "S04-09"
    doc["shots"][2]["chain_depth"] = 1
    assert "CT-09" in rules(cc.check(doc))


def test_no_edit_pass_on_an_earlier_shot(doc):
    """D-78 (ვანო 2026-10-25 10:50 Tbilisi): no edit model, no img2img pass; every shot is drawn from the references."""
    assert cc.MAX_CHAIN == 0
    doc["shots"][2]["derive_from"], doc["shots"][2]["chain_depth"] = "S04-02", 0
    assert any(f["rule"] == "CT-09" and "D-78" in f["detail"] for f in cc.check(doc))
    doc["shots"][2]["derive_from"] = "original"
    assert "CT-09" not in rules(cc.check(doc))


def test_landmarks_belong_to_the_location(doc):
    doc["shots"][1]["landmarks"].append({"id": "cannon", "side": "right"})
    assert "CT-10" in rules(cc.check(doc))


def test_eyeline_must_point_at_the_target(doc):
    doc["shots"][0]["characters"][0]["facing"] = "left"
    assert "CT-11" in rules(cc.check(doc), "REVIEW")


def test_match_on_action_keeps_screen_direction(doc):
    shot = doc["shots"][1]
    shot["hook_up"] = "match_on_action"
    shot["characters"][0]["facing"] = "left"
    assert "CT-12" in rules(cc.check(doc))


def test_prompt_is_assembled_with_verbatim_identity(doc):
    out = cc.prompts(doc)
    assert [p["shot_id"] for p in out] == ["S04-01", "S04-02", "S04-03"]
    second = out[1]["prompt"]
    assert second.startswith(doc["style_line"])
    assert "Image 1 is the place" in second and "Image 3 is the tall marshal" in second
    assert doc["cast"]["emperor"]["description"] in second
    assert "Exactly 2 people." in second and "Keep everything else the same." in second
    assert out[1]["refs"][0] == doc["location"]["master_frame"]
    assert "Keep everything else the same." not in out[2]["prompt"]


def test_vision_questions(doc):
    qs = cc.vision_questions(doc, doc["shots"][1])
    assert qs[0].endswith("(expected 2)")
    assert any("dispatch letter in the right hand" in q for q in qs)
    assert qs[-1].startswith("Is the framing clearly different")
    assert not cc.vision_questions(doc, doc["shots"][0])[-1].startswith("Is the framing")


def test_cli_refuses_prompts_on_fail(doc, tmp_path, capsys):
    bad = copy.deepcopy(doc)
    bad["shots"][1]["head_count"] = 5
    path = tmp_path / "cards.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert cc.main(["prompts", str(path)]) == 1
    assert "no prompts" in capsys.readouterr().out
    path.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "prompts.json"
    assert cc.main(["prompts", str(path), "--out", str(out)]) == 0
    assert len(json.loads(out.read_text(encoding="utf-8"))) == 3


def test_the_example_style_line_passes_the_d80_trigger_check(doc):
    assert doc["style_line"] == lora_rules.trigger()
    assert [f for f in style_prompt.check(doc["style_line"]) if f["severity"] == "FAIL"] == []


# --- CT-17..CT-20 (L10: identity bible, geography ids, film id) ---

def _with_identity(d):
    d["film_id"] = "owner_film_01"
    for c in d["cast"].values():
        c["identity"] = {"canon_frame": "canon/" + c["name"] + ".png", "locked": ["face shape"]}
    return d


def test_old_card_without_new_fields_is_unchanged(doc):
    assert "CT-17" not in rules(cc.check(doc)) and not cc.identity_findings(doc)


def test_identity_card_passes(doc):
    assert not [f for f in cc.check(_with_identity(doc)) if f["rule"] in {"CT-17", "CT-18", "CT-19", "CT-20"}]


def test_new_fields_need_a_film_id(doc):
    d = _with_identity(doc)
    del d["film_id"]
    assert "CT-17" in rules(cc.check(d))
    d2 = copy.deepcopy(doc)
    d2["location"]["geo_id"] = "tent_a"
    assert "CT-17" in rules(cc.check(d2))


def test_film_id_must_match_the_episode_film(doc):
    d = _with_identity(doc)
    assert "CT-17" not in rules(cc.check(d, film_id="owner_film_01"))
    assert "CT-17" in rules(cc.check(d, film_id="other_film"))


def test_bad_film_id_shape_is_a_schema_failure(doc):
    d = _with_identity(doc)
    d["film_id"] = "Owner Film"
    assert rules(cc.check(d)) == {"CT-01"}


def test_every_person_on_screen_needs_an_identity(doc):
    d = _with_identity(doc)
    shown = d["shots"][0]["characters"][0]["id"]
    del d["cast"][shown]["identity"]
    assert any(f["rule"] == "CT-18" and shown in f["detail"] for f in cc.check(d))


def test_identity_needs_canon_frame_and_locked_list(doc):
    d = _with_identity(doc)
    cid = next(iter(d["cast"]))
    del d["cast"][cid]["identity"]["canon_frame"]
    assert rules(cc.check(d)) == {"CT-01"}
    d = _with_identity(copy.deepcopy(doc))
    d["cast"][cid]["identity"]["locked"] = []
    assert any(f["rule"] == "CT-18" and "locked" in f["detail"] for f in cc.check(d))


def test_trait_cannot_be_locked_and_flexible(doc):
    d = _with_identity(doc)
    cid = next(iter(d["cast"]))
    d["cast"][cid]["identity"]["flexible"] = ["face shape"]
    assert "CT-19" in rules(cc.check(d))


def test_geography_inheritance(doc):
    d = copy.deepcopy(doc)
    d["film_id"] = "owner_film_01"
    d["location"]["inherits_from"] = "camp"
    assert "CT-20" in rules(cc.check(d))                     # no own geo_id
    d["location"]["geo_id"] = "camp"
    assert "CT-20" in rules(cc.check(d))                     # itself
    d["location"]["geo_id"] = "tent"
    assert "CT-20" not in rules(cc.check(d))                 # known ids not given: not compared
    assert "CT-20" not in rules(cc.check(d, known_geo_ids={"camp"}))
    assert "CT-20" in rules(cc.check(d, known_geo_ids={"hill"}))
