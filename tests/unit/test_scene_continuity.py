"""Owner-approved Python item 1: scene-level soft gates (qa/scene_continuity.py) and their wiring in episode/acceptance.py."""
import copy
import json
from pathlib import Path

from explainer_engine.qa import scene_continuity as SC
from explainer_engine.qa.gates import FAIL, PASS, REVIEW

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json"


def _script():
    return json.loads(SCRIPT.read_text(encoding="utf-8"))


def _by_gate(rows):
    return {r["gate"]: r for r in rows}


def test_an_old_script_without_scene_bibles_gets_no_rows():
    assert SC.scene_rows({"shots": [{"shot_id": "A", "meaning_link": "x"}]}) == []


def test_the_truce_script_has_no_failing_scene_gate():
    rows = _by_gate(SC.scene_rows(_script()))
    assert {"SCENE_BIBLE_COMPLETENESS", "MEANING_LINK_SPECIFICITY", "DOCUMENT_INSERT_MOTIVATION"} <= set(rows)
    assert [g for g, r in rows.items() if r["status"] == FAIL] == []


def test_soft_bands_are_review_never_fail():
    rows = SC.scene_rows(_script())
    soft = [r for r in rows if r["gate"].endswith("_REVIEW")]
    assert soft and all(r["status"] in (PASS, REVIEW) for r in soft)


def test_a_boilerplate_meaning_link_fails():
    sc = _script()
    for s in sc["shots"][:6]:
        s["meaning_link"] = {"type": "CAUSE", "text": "Continues the physical action and emotional beat."}
    r = _by_gate(SC.scene_rows(sc))["MEANING_LINK_SPECIFICITY"]
    assert r["status"] == FAIL and r["measured"]["repeated"]


def test_a_short_meaning_link_fails():
    sc = _script()
    sc["shots"][0]["meaning_link"] = {"type": "CAUSE", "text": "ok"}
    assert _by_gate(SC.scene_rows(sc))["MEANING_LINK_SPECIFICITY"]["status"] == FAIL


def test_a_shot_pointing_at_a_missing_scene_bible_fails():
    sc = _script()
    sc["shots"][0]["scene_bible_ref"] = "SC_DOES_NOT_EXIST"
    r = _by_gate(SC.scene_rows(sc))["SCENE_BIBLE_COMPLETENESS"]
    assert r["status"] == FAIL and "SC_DOES_NOT_EXIST" in r["measured"]["dangling"]


def test_a_document_insert_without_a_valid_motivation_fails():
    sc = _script()
    doc = next(s for s in sc["shots"] if "document_motivation" in s)
    doc["document_motivation"] = "decoration"
    assert _by_gate(SC.scene_rows(sc))["DOCUMENT_INSERT_MOTIVATION"]["status"] == FAIL


def test_a_document_cut_shorter_than_its_hold_is_a_review():
    sc = _script()
    doc = next(s for s in sc["shots"] if "document_motivation" in s)
    doc["minimum_hold_seconds"] = 4.0
    doc["edited_shot_duration_seconds"] = 1.0
    assert _by_gate(SC.scene_rows(sc))["DOCUMENT_INSERT_HOLD_REVIEW"]["status"] == REVIEW


def test_a_scene_outside_the_measured_bands_is_a_review():
    sc = _script()
    sc["scene_bibles"][0]["scene_duration_seconds"] = 5.0
    sc["scene_bibles"][0]["edited_shot_count"] = 2
    rows = _by_gate(SC.scene_rows(sc))
    assert rows["SCENE_DURATION_BAND_REVIEW"]["status"] == REVIEW and rows["SCENE_SHOT_COUNT_BAND_REVIEW"]["status"] == REVIEW


def test_the_gates_are_wired_into_acceptance():
    from explainer_engine.episode import acceptance
    import inspect
    assert "scene_rows(script)" in inspect.getsource(acceptance.gates)
