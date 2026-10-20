"""Claude's free picture review and the audit's de-hard-coding (2026-10-19 items 11, 13)."""
from test_production_script import compiled

from explainer_engine.production import compile as C
from explainer_engine.production import timing as T
from explainer_engine.audio import layers as L
from explainer_engine.qa import sheet_review as R
from explainer_engine.qa import visual_judge as J

GOOD = {"adults": True, "era_objects": False, "people_in_plate": False, "text": False, "one_light": True,
        "hero_match": True, "too_early": False, "mood": True, "why_adults": "grown men", "why_one_light": "dusk from left",
        "why_hero_match": "spectacles", "why_mood": "they shiver"}


def test_request_lists_every_used_picture(tmp_path):
    doc = compiled()
    md = R.request(doc, [tmp_path])
    assert all(f"## {pid}" in md for pid in R.metas(doc))


def test_answers_become_verdicts():
    doc = compiled()
    ids = list(R.metas(doc))
    review = {"schema": R.SCHEMA, "by": "claude", "pictures": {i: dict(GOOD) for i in ids}}
    assert not [f for f in R.apply(doc, review) if f["severity"] == "FAIL"]
    review["pictures"][ids[0]]["adults"] = False
    assert [f["where"] for f in R.apply(doc, review) if f["severity"] == "FAIL"] == [ids[0]]
    del review["pictures"][ids[0]]
    assert any(f["detail"] == "not reviewed" for f in R.apply(doc, review))


def test_the_episode_names_its_own_visitors():
    doc = compiled()
    assert C._visitor_costume(doc) == C.VISITOR_COSTUME
    doc["world"]["visitor_costume"] = "Roman tunics and sandals"
    assert C._visitor_costume(doc) == "Roman tunics and sandals"
    w = {"topic": "t", "host": {}, "absent": [], "visitors_note": "a legionary in a supermarket"}
    assert "a legionary in a supermarket" in J.build_prompt(w, {})


def test_an_ungained_bed_sits_at_the_cap():
    assert T.BED_DEFAULT_DB <= L.MAX_BED_DB
