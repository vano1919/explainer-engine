"""Fixes from the 2026-10-19 audit (M3, M4): failures that used to crash or corrupt a script now give a finding."""
import copy

from test_production_script import compiled, mini, words_for

from explainer_engine.production import assemble as A
from explainer_engine.production import fill_holds as F
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V


def test_a_read_that_stops_early_gives_pv20_not_a_crash():
    doc = compiled()
    w = words_for(doc)
    w["words"] = w["words"][:-5]  # the last chunk was cut off
    timed = T.time_script(doc, w)
    assert timed["text_match"] < T.MIN_TEXT_MATCH
    assert "PV-20" in {f["rule"] for f in V.check_timed(timed, doc) if f["severity"] == "FAIL"}


def test_a_line_that_opens_with_a_dash_keeps_the_token_count():
    doc = mini()
    doc["segments"][0]["lines"][1]["text"] = "— and nobody knows, not even the bravest of them, and the cold wind is rising."
    doc["segments"][0]["shots"][1]["at"] = "and nobody"
    toks = S.tokens(doc)  # raised "token count mismatch" before
    assert toks[-1]["seg"] == 1 and any(t["w"].endswith("—") for t in toks)


def test_dropping_a_short_shot_keeps_its_picture_definition():
    doc = mini()
    seg = doc["segments"][0]
    # a second shot reuses the inline picture of a shot the drop will remove
    seg["shots"].append({"at": "the cold wind", "type": "C", "insert": True, "picture": "cold_hands",
                         "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}})
    gone = {"at": "Nobody knows.", "picture": copy.deepcopy(seg["shots"][1]["picture"])}
    seg["shots"].pop(1)
    F._move_definition(doc, gone)
    assert isinstance(seg["shots"][-1]["picture"], dict) and seg["shots"][-1]["picture"]["id"] == "cold_hands"
    assert "PV-03" not in {f["rule"] for f in V.check_script(doc) if f["severity"] == "FAIL"}


def test_the_shrinking_reframe_is_labelled_a_pull():
    assert F.alt_motion({"kind": "push", "z0": 1.0, "z1": 1.06})["kind"] == "pull"


def test_a_library_sound_without_its_file_is_missing(tmp_path, monkeypatch):
    s = A.Sounds([tmp_path])
    s.lib["ghost"] = tmp_path / "nowhere" / "ghost.wav"
    assert s.path("ghost") is None and not s.exists("ghost")
