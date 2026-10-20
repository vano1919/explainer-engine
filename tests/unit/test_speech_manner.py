"""PV-46 / DW-11: every speaking hero talks in their own known manner or, if invented, from their personality."""

import copy

from explainer_engine.production import script as S
from explainer_engine.scripting import speech as SP

BASE = {"schema": "production_script/2", "episode": {"id": "x", "title": "X episode"},
        "cast": {"vito": {"names": ["vito"], "card": "an older patriarch"},
                 "mizuno": {"names": ["mizuno"], "card": "an invented businessman"}},
        "segments": [{"id": "S01", "lines": [{"text": "Olive oil. Nobody films olive oil.", "speaker": "vito"},
                                             {"text": "The narrator speaks here."}]}]}
VITO = {"basis": "public", "style": "soft, slow, courtly; short sentences, never raises his voice",
        "words": ["friend", "respect", "family"], "avoid": ["dude"], "sources": ["C-24"]}


def test_a_speaking_hero_without_a_manner_fails_on_a_new_script_and_reviews_on_an_old_one():
    assert [(f["severity"], f["where"]) for f in SP.check(BASE)] == [("FAIL", "vito")]
    old = dict(BASE, schema="production_script/1")
    assert [f["severity"] for f in SP.check(old)] == ["REVIEW"]


def test_a_known_manner_needs_sources_and_an_avoided_word_is_flagged():
    d = copy.deepcopy(BASE)
    d["cast"]["vito"]["speech"] = VITO
    assert SP.check(d) == []
    d["cast"]["vito"]["speech"] = dict(VITO, sources=[])
    assert "sources" in SP.check(d)[0]["detail"]
    d["cast"]["vito"]["speech"] = VITO
    d["segments"][0]["lines"][0]["text"] = "Dude, nobody films olive oil."
    assert [f["severity"] for f in SP.check(d)] == ["REVIEW"]


def test_an_invented_hero_talks_from_personality_and_the_schema_takes_it():
    d = copy.deepcopy(BASE)
    d["cast"]["vito"]["speech"] = VITO
    d["cast"]["mizuno"]["speech"] = {"basis": "personality", "style": "clipped, polite, exact; numbers and procedure",
                                     "words": ["schedule", "precisely", "thank you"]}
    d["segments"][0]["lines"].append({"text": "Sign here. And here. Thank you.", "speaker": "mizuno"})
    assert SP.check(d) == []
    assert not [e for e in S.schema_errors(d) if "speech" in str(e)]
