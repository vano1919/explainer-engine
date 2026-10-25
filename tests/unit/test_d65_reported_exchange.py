"""D-65 (the creator, 2026-10-20 21:14, confirmed 21:17): a narrated exchange is a real exchange (BP-70), a breath before a
change of place or time is no narration hold (BP-10, NR-07), and two REVIEW checks on reported speech (BP-95, BP-96)."""

from __future__ import annotations

from test_scene_system import scene_doc

from explainer_engine.scripting import narration_lint as L
from explainer_engine.scripting import scene_lint as SC
from explainer_engine.scripting import story_lint as ST
from explainer_engine.standards import sourced_rules as SR

CAST = {"musk": {"names": ["Elon Musk", "Musk"]}, "oleary": {"names": ["O'Leary"]}, "trump": {"names": ["Trump"]}}


def _bp70(doc):
    return [f for f in SC.lint(doc) if f["rule"] == "SC-05" and "BP-70" in f["detail"]]


def test_a_reported_exchange_of_four_turns_and_two_speakers_is_a_real_exchange():
    d = scene_doc()
    seg = d["segments"][0]
    seg["lines"] = [seg["lines"][0], {"text": "Capone asks if Enzo counted it twice."}, {"text": "Enzo says three times."},
                    {"text": "Capone repeats the word."}, {"text": "He says it's short."}]
    seg["lines"][-1]["text"] = "Capone says short. Enzo answers that someone is skimming the north side."
    assert ST.reported_turns(" ".join(ln["text"] for ln in seg["lines"]), d["cast"], ["capone", "enzo"]) == \
        ["capone", "enzo", "capone", "enzo"]
    seg["lines"].append({"text": "Fine.", "speaker": "capone"})  # SC-05 runs on a scene with a hero line
    assert not _bp70(d)
    seg["lines"][2]["text"] = "Three times, it seems."  # three turns: not enough
    found = _bp70(d)
    assert found and found[0]["severity"] == SR.rule("BP-70")["severity"]


def test_the_old_unbroken_run_still_counts_and_still_fails_when_broken():
    assert not _bp70(scene_doc())
    d = scene_doc()
    d["segments"][0]["lines"].insert(2, {"text": "The room waits."})
    d["segments"][0]["lines"].insert(4, {"text": "Nobody breathes."})
    assert _bp70(d)


def _two(pause, period2="day2"):
    return {"segments": [{"id": "S01", "period": "day1", "lines": [{"text": "They leave.", "pause_after": pause}]},
                         {"id": "S02", "period": period2, "lines": [{"text": "A week later."}]}]}


def test_a_breath_before_a_change_of_time_is_allowed_up_to_its_band():
    band = SR.T("BP-10", "boundary_breath_max_s")
    assert SR.T("BP-10", "max_hold_s") < band
    assert not [f for f in L.doc_findings(_two(band)) if f["rule"] == "N-15"]
    over = [f for f in L.doc_findings(_two(band + 0.3)) if f["rule"] == "N-15"]
    assert [f["severity"] for f in over] == ["REVIEW"]
    same = [f for f in L.doc_findings(_two(band, period2="day1")) if f["rule"] == "N-15"]  # no jump: the 1 s hold rules
    assert same and "BP-10" in same[0]["detail"]


def test_the_speaker_comes_first_and_two_voices_a_line():
    doc = {"cast": CAST, "segments": [{"id": "S01", "lines": [
        {"text": "That's how fires work, says Musk."}, {"text": "Musk says it is how fires work."},
        {"text": "O'Leary asks, Musk says yes, and Trump says no."}]}]}
    found = ST.reported_speech(doc)
    assert [(f["rule"], f["where"]) for f in found] == [("ST-15", "S01 line 1"), ("ST-16", "S01 line 3")]
    assert {f["severity"] for f in found} == {"REVIEW"} == {SR.rule("BP-95")["severity"], SR.rule("BP-96")["severity"]}
