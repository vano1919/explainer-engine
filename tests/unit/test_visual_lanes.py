"""ICW-03: the Ink Chronicle archetype registry (``visual/archetypes_ic.json``, schema ``archetypes_ic/1``), the shot designer
and the lane planner (``visual/lanes.py``): BP-109's 60/30/10 band on three fixture scripts and the Napoleon episode, the
anti-monotony REVIEW (KP-48), and a REVIEW, never a rewrite, for a script that cannot reach the band (roadmap 15, ICW-03)."""

from __future__ import annotations

import copy
import json

import pytest

import _lane_fixtures as LF
from _napoleon import NAPOLEON, _builder, cards_v3
from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.scripting import film_shots as F
from explainer_engine.visual import lanes, shot_design as SD

FIXTURES = {"battle": LF.battle_documentary, "council": LF.council_drama}


def _raw() -> dict:
    return json.loads(SD.REGISTRY.read_text(encoding="utf-8"))


# --- the registry ----------------------------------------------------------------------------------------------------------
def test_the_registry_validates_and_has_no_link_errors():
    doc = _raw()
    contracts.validate(doc)
    assert SD.registry_errors(doc) == []
    assert [a["id"] for a in doc["archetypes"]] == list(range(1, 21))


def test_every_sub_category_of_section_7_4_carries_the_twelve_attributes():
    subs = SD.registry()["sub_categories"]
    by_lane = {lane: [s for s in subs if s["lane"] == lane] for lane in SD.LANES}
    assert {lane: len(v) for lane, v in by_lane.items()} == SD.SUB_COUNTS
    assert len(SD.ATTRIBUTES) == 12
    for s in subs:
        assert set(SD.ATTRIBUTES) <= set(s), s["id"]
        assert s["id"][0] == {"HELPER": "H", "STILL_3D": "S", "VIDEO_3D": "V"}[s["lane"]]


@pytest.mark.parametrize("attr", SD.ATTRIBUTES)
def test_the_schema_requires_each_attribute(attr):
    doc = _raw()
    del doc["sub_categories"][0][attr]
    with pytest.raises(ContractError):
        contracts.validate(doc)


def test_registry_errors_catch_a_broken_link_and_a_lane_mismatch():
    doc = _raw()
    a16 = next(a for a in doc["archetypes"] if a["id"] == 16)
    a16["lanes"] = ["STILL_3D"]  # 16 names V9, a VIDEO_3D sub-category
    a16["default_lane"] = "STILL_3D"
    assert any("16" in e for e in SD.registry_errors(doc))
    doc = _raw()
    doc["archetypes"][0]["helper_archetypes"] = ["PARALLAX_DEPTH_SCENE"]
    assert SD.registry_errors(doc)


def test_helper_archetypes_name_real_catalogue_visuals_and_never_parallax():
    from explainer_engine.edit import visual_compensator as VC
    for a in SD.registry()["archetypes"]:
        for h in a.get("helper_archetypes") or []:
            assert h in VC.ids() and "PARALLAX" not in h
        assert bool(a.get("helper_archetypes")) == (a["id"] in SD.HELPER_IDS)


# --- the planner on three fixture scripts ------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_a_fixture_script_plans_inside_bp109s_band(name):
    src = FIXTURES[name]()
    contracts.validate(src)
    doc, rep = lanes.plan(src)
    contracts.validate(doc)
    shares = F.lane_shares(doc["shots"], F.V3)
    for lane, aim in F.LANE_SHARE.items():
        assert abs(shares[lane] - aim) <= F.LANE_TOLERANCE + 1e-9, (lane, shares)
    assert F.lane_share_findings(shares) == []
    assert not [f for f in rep["findings"] if f["rule"] == "KP-37"]
    assert rep["shares_before"]["video"] == 1.0  # every card came in as VIDEO_3D


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_the_planner_breaks_long_video_runs(name):
    doc, rep = lanes.plan(FIXTURES[name]())
    run_max = SD.registry()["planner"]["video_run_max"]
    assert all(n <= run_max for _, n in lanes.video_runs([s["lane"] for s in doc["shots"]]))
    assert not [f for f in rep["findings"] if f["rule"] == "KP-48"]


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_the_planner_keeps_every_word_and_every_line(name):
    src = FIXTURES[name]()
    doc, _ = lanes.plan(src)
    said = lambda d: [(s.get("narration"), (s.get("dialogue") or {}).get("text")) for s in d["shots"]]  # noqa: E731
    assert said(doc) == said(src)
    assert sum(s["seconds"] for s in doc["shots"]) == sum(s["seconds"] for s in src["shots"])


def test_seen_lines_stay_on_video_and_helpers_carry_no_dialogue():
    for make in FIXTURES.values():
        doc, _ = lanes.plan(make())
        for s in doc["shots"]:
            if s.get("lipsync"):
                assert s["lane"] == "VIDEO_3D", s["id"]
            if s["lane"] == "HELPER":
                assert "dialogue" not in s and s.get("helper_archetype")
                assert s["archetype"] in SD.HELPER_IDS


def test_a_talk_heavy_script_gets_a_review_and_is_never_rewritten():
    src = LF.talk_heavy()
    doc, rep = lanes.plan(src)
    kp37 = [f for f in rep["findings"] if f["rule"] == "KP-37"]
    assert kp37 and all(f["severity"] == "REVIEW" for f in rep["findings"])
    video = next(f for f in kp37 if f["detail"].startswith("video"))
    assert "writers' room" in video["detail"] and "never a silent rewrite" in video["detail"]
    assert [s["dialogue"]["text"] for s in doc["shots"] if "dialogue" in s] == \
        [s["dialogue"]["text"] for s in src["shots"] if "dialogue" in s]
    assert len(doc["shots"]) == len(src["shots"])


def test_kp48_reviews_a_locked_video_run():
    _, rep = lanes.plan(LF.talk_heavy())
    kp48 = [f for f in rep["findings"] if f["rule"] == "KP-48"]
    assert len(kp48) == 8 and all(f["severity"] == "REVIEW" for f in kp48)
    assert all("may only be VIDEO_3D" in f["detail"] for f in kp48)
    assert kp48[0]["where"] == "S01-01..S01-08"


def test_video_runs():
    assert lanes.video_runs(["VIDEO_3D", "VIDEO_3D", "STILL_3D", "VIDEO_3D", "HELPER"]) == [(0, 2), (3, 1)]
    assert lanes.video_runs([]) == []


# --- the shot designer -------------------------------------------------------------------------------------------------------
def test_a_long_seen_line_is_split_onto_an_off_screen_cover_with_no_word_lost():
    src = LF.council_drama()
    shot = copy.deepcopy(src["shots"][1])
    shot["seconds"], shot["duration_frames"] = 9, 216
    shot["dialogue"]["text"] = "We ride tonight, all of us, before the river rises and the bridge is gone."
    a, b = SD.ShotDesigner(src).split_voiced(shot)
    assert a["seconds"] == F.DIALOGUE_SHOT_MAX_S and a["seconds"] + b["seconds"] == 9
    assert (a["dialogue"]["text"] + " " + b["dialogue"]["text"]).split() == shot["dialogue"]["text"].split()
    assert b["id"] == shot["id"] + "b" and a["duration_frames"] + b["duration_frames"] == 216
    assert all(p["who"] != "anna" for p in b.get("blocking", []))
    short = copy.deepcopy(src["shots"][2])
    assert SD.ShotDesigner(src).split_voiced(short) == [short]


def test_a_split_shot_validates_after_planning():
    src = LF.council_drama()
    src["shots"][1]["seconds"], src["shots"][1]["duration_frames"] = 9, 216
    doc, rep = lanes.plan(src)
    contracts.validate(doc)
    assert rep["split_voiced"] and any(s["id"] == "S01-02b" for s in doc["shots"])
    b = next(s for s in doc["shots"] if s["id"] == "S01-02b")
    assert b.get("dialogue_cover") != "on_screen" and not b.get("lipsync")


def test_the_climax_peak_and_the_last_scene_take_their_archetypes():
    src = LF.battle_documentary()
    d = SD.ShotDesigner(src, climax_scene="S03")
    peak = next(s for s in src["shots"] if s["scene"] == "S03" and d.is_peak(s))
    assert d.visual_archetype(peak) == 19
    last = next(s for s in src["shots"] if s["scene"] == "S06" and not s.get("dialogue"))
    assert d.visual_archetype(last) == 20


# --- the Napoleon episode ----------------------------------------------------------------------------------------------------
def test_napoleon_plans_inside_the_band_and_the_file_is_the_planners_output():
    doc, _, plan = _builder().planned()
    on_disk = json.loads((NAPOLEON / "film_shots.json").read_text(encoding="utf-8"))
    assert doc == on_disk
    contracts.validate(on_disk)
    shares = F.lane_shares(on_disk["shots"], F.V3)
    assert F.lane_share_findings(shares) == []
    assert not [f for f in plan["findings"] if f["rule"] == "KP-37"]
    assert all(f["severity"] == "REVIEW" for f in plan["findings"])


def test_every_napoleon_shot_has_an_archetype_from_the_registry():
    shots = cards_v3()["shots"]
    assert all(isinstance(s["archetype"], int) and 1 <= s["archetype"] <= 20 for s in shots)
    for s in shots:
        assert s["lane"] in SD.archetype(s["archetype"])["lanes"], s["id"]
    assert {s["archetype"] for s in shots if s["lane"] == "HELPER"} <= set(SD.HELPER_IDS)


def test_napoleons_lane_plan_page_is_current():
    _, _, plan = _builder().planned()
    assert (NAPOLEON / "lane_plan.md").read_text(encoding="utf-8") == _builder().lane_plan(plan)
