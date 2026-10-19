"""PV-38: a new episode is compared with the approved ones (inauthentic content, Help 1311392; audit 2026-10-19)."""
from test_production_script import mini

from explainer_engine.scripting import distinct as D

EP1 = D.REGISTRY


def test_no_statement_is_a_review():
    assert [f["where"] for f in D.check(mini())] == ["episode.distinct"]


def test_the_same_situation_with_the_same_outcome_is_flagged():
    doc = mini()
    doc["episode"]["distinct"] = {
        "premise": "one hundred real engineers from history wake up together in the Stone Age, about ten thousand BCE",
        "question": "would engineers do better?",
        "outcome": "early on they beat history, then hit the wall of people, materials, fuel, tools and trade",
        "mechanism": "engineering skill versus materials"}
    assert any(f["where"] == "stone_age_ep1" for f in D.check(doc))


def test_a_different_collision_passes():
    doc = mini()
    doc["episode"]["distinct"] = {
        "premise": "a Roman soldier's pay is carried into a modern supermarket",
        "question": "what could a legionary actually buy?",
        "outcome": "bread and salt are cheap, but a cloak costs a month: prices follow labour, not metal",
        "mechanism": "purchasing power across eras"}
    assert D.check(doc) == []
