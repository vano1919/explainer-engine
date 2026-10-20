"""D-64 (the creator, 2026-10-20 21:14): the research-backed editing rules of the titans QA loop, one test per rule.

BP-84 bubble = an accent of BP-38's words; BP-31 a 1-2 s dissolve at every change of place or time; BP-37 no per-line
expression quota (REVIEW); BP-93 an untied beat is not "something new" for BP-36 / BP-40; BP-83 MO-06 reported only;
BP-90 / ST-14 exchanges framed by the narrator; BP-91 / PV-57 the establishing cast; BP-92 moves never reset;
BP-94 the held mood after an exchange.
"""

from __future__ import annotations

import copy

from test_integrated_review import scene_mini
from test_production_script import words_for

from explainer_engine.edit import board as B
from explainer_engine.edit import motion_lint as M
from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import beats as BEATS
from explainer_engine.production import compile as C
from explainer_engine.production import continuity as CONT
from explainer_engine.production import silent as SIL
from explainer_engine.production import timing as T
from explainer_engine.production import validate as V
from explainer_engine.scripting import story_lint as SL
from explainer_engine.standards import sourced_rules as SR


def _rules(found, rule):
    return [f for f in found if f["rule"] == rule or f["rule"].endswith(" " + rule)]


# --- BP-84: a bubble is an accent of BP-38's words ---------------------------------------------------------------------

def test_a_bubble_holds_bp38s_words_and_the_accent_line_too():
    cap = SR.T("BP-38", "max_words")
    assert "bubble_words_max" not in SR.rule("BP-84")["thresholds"] and BUB.MAX_WORDS == SIL.max_words() == cap
    ok = " ".join(["word"] * cap)
    assert not _rules(BUB.check_bubbles([{"text": ok, "start": 0.0, "end": 7.0}]), "BUBBLE-1")
    assert _rules(BUB.check_bubbles([{"text": ok + " more", "start": 0.0, "end": 7.0}]), "BUBBLE-1")
    d = {"schema": "production_script/3", "segments": [{"id": "S01", "lines": [
        {"text": "Musk asks O'Leary why."}, {"text": "I can build anything you want, today.", "speaker": "musk",
                                              "voiced": False}]}]}
    assert any("BP-84" in why for why in SIL.check_reported_dialogue(d))
    d["segments"][0]["lines"][1]["text"] = "I build anything."
    assert SIL.check_reported_dialogue(d) == []


# --- BP-31: a dissolve at every change of place or time -----------------------------------------------------------------

def _dissolve_timed(**flags):
    a = {"id": "SH001", "segment": "S01", "picture": "a", "start": 0.0, "end": 4.0, "motion": {"kind": "hold", "z0": 1.0,
                                                                                              "z1": 1.0}, "accents": []}
    b = dict(a, id="SH002", segment="S02", picture="b", start=4.0, end=8.0, transition="dissolve", **flags)
    return {"duration": 8.0, "fps": 30, "shots": [a, b], "cards": []}


def test_a_dissolve_is_allowed_at_a_change_of_place_and_lasts_one_to_two_seconds():
    assert (SR.T("BP-31", "dissolve_s"), SR.T("BP-31", "dissolve_max_s")) == (1.0, 2.0)
    assert _rules(M.check_sourced(_dissolve_timed()), "BP-31")  # inside a scene: a hard cut
    assert not _rules(M.check_sourced(_dissolve_timed(place_change=True, transition_seconds=1.5)), "BP-31")
    long = _rules(M.check_sourced(_dissolve_timed(place_change=True, transition_seconds=2.5)), "BP-31")
    assert [f["severity"] for f in long] == ["REVIEW"]


def test_timing_marks_a_change_of_scene_place_as_a_place_change():
    d = C.compile_doc(copy.deepcopy(scene_mini()))
    timed = T.time_script(d, words_for(d))
    first = {}
    for s in timed["shots"]:
        first.setdefault(s["segment"], s)
    assert first["S02"].get("place_change") and first["S03"].get("place_change")  # S01/S03 have no scene, S02 has one
    assert not any(s.get("place_change") for s in timed["shots"] if first[s["segment"]] is not s)


# --- BP-37: no per-line expression quota ---------------------------------------------------------------------------------

def test_a_dialogue_line_without_a_reaction_is_not_a_finding():
    assert SR.T("BP-37", "changes_per_line_min") == 0 and SR.rule("BP-37")["severity"] == "REVIEW"
    d = C.compile_doc(copy.deepcopy(scene_mini()))
    for ln in d["segments"][1]["lines"]:
        if ln.get("speaker"):
            ln["visual_beats"] = []
    timed = T.time_script(d, words_for(d))
    assert not [f for f in _rules(BEATS.check_timed(timed, d), "VB-02") if "no expression change" in f["detail"]]
    assert all(f["severity"] == "REVIEW" for f in _rules(BEATS.check_timed(timed, d), "VB-02"))


# --- BP-93: a beat needs a word (BP-36 / BP-40 count only tied beats) ----------------------------------------------------

def test_only_a_beat_on_a_narration_word_counts_as_something_new():
    narr, hero = {"text": "Musk signs the contract."}, {"text": "Sign it.", "speaker": "oleary"}
    assert BEATS.anchored({"at": "the contract", "kind": "symbol"}, narr)
    assert not BEATS.anchored({"at": "the", "kind": "symbol"}, narr)  # no content word: a beat on a clock
    assert not BEATS.anchored({"at": "Sign it", "kind": "expression"}, hero)  # a reaction is a choice, not news
    timed = {"duration": 30.0, "shots": [{"id": "SH001", "segment": "S01", "picture": "a", "start": 0.0, "end": 30.0,
                                          "accents": [{"kind": "punch", "start": 9.0, "anchored": False}], "bubbles": []}],
             "visuals": [], "cards": [],
             "visual_beats": [{"kind": "symbol", "start": 5.0, "anchored": True},
                              {"kind": "symbol", "start": 12.0, "anchored": False}, {"kind": "text", "start": 20.0}]}
    assert [t for t, _ in M.events(timed)] == [0.0, 5.0, 20.0]  # an unflagged (older) beat still counts
    assert B.change_times(timed["shots"], 30.0, timed) == [0.0, 5.0, 20.0, 30.0]


def test_vb12_reports_an_untied_beat_on_a_scene_script_only():
    d = scene_mini()
    d["segments"][0]["lines"][0]["visual_beats"].append({"at": "the", "kind": "symbol", "symbol": "question",
                                                         "why": "a question about the pass"})
    found = _rules(BEATS.lint(d), "VB-12")
    assert found and all(f["severity"] == SR.rule("BP-93")["severity"] for f in found)
    assert not any("expression" in f["detail"] for f in found)  # reactions on hero lines are not reported
    d["schema"] = "production_script/2"
    assert not _rules(BEATS.lint(d), "VB-12")  # a /2 keeps its metronome contract


# --- BP-83: MO-06 is reported only ---------------------------------------------------------------------------------------

def test_the_motion_share_is_reported_without_a_target():
    shots = [{"id": f"SH{i:03d}", "segment": "S01", "picture": f"p{i}", "start": i * 4.0, "end": i * 4.0 + 4.0,
              "start_frame": i * 120, "end_frame": i * 120 + 120, "accents": [], "bubbles": []} for i in range(5)]
    mo6 = _rules(M.check({"duration": 20.0, "shots": shots, "visuals": [], "cards": []}), "MO-06")
    assert [f["severity"] for f in mo6] == ["INFO"]


# --- BP-90 / ST-14: setup -> exchange -> conclusion ----------------------------------------------------------------------

def _exchange(lines):
    return {"cast": {"musk": {"names": ["Elon Musk", "Musk"]}, "oleary": {"names": ["O'Leary"]}},
            "segments": [{"id": "S01", "lines": lines}]}


def test_an_exchange_needs_the_narrators_setup_and_conclusion():
    setup = {"text": "O'Leary slides along the bench to Musk."}
    a = {"text": "Sign here.", "speaker": "oleary"}
    b = {"text": "Why?", "speaker": "musk"}
    end = {"text": "Musk signs, and the price is forty dollars."}
    assert SL.exchanges(_exchange([setup, a, b, end])) == []
    no_setup = SL.exchanges(_exchange([a, b, end]))
    assert any("setup" in f["detail"] and f["severity"] == SR.rule("BP-90")["severity"] for f in no_setup)
    chained = SL.exchanges(_exchange([setup, a, b]))  # the next scene would start straight on talk
    assert any("conclusion" in f["detail"] and f["severity"] == "FAIL" for f in chained)
    unnamed = SL.exchanges(_exchange([{"text": "A man in a grey suit sits down."}, a, end]))
    assert [f["severity"] for f in unnamed] == ["REVIEW"]  # a description may stand for the name


# --- BP-91 / PV-57: the establishing cast is the scene's cast ------------------------------------------------------------

def _cast_doc(later_heroes, text="Ten men sit on the bench. Two of them talk."):
    return {"schema": "production_script/3", "cast": {h: {"names": [h.title()]} for h in ("musk", "trump", "cuban")},
            "library": {"wide": {"heroes": ["musk", "trump"]}, "close": {"heroes": later_heroes}},
            "segments": [{"id": "S01", "light_beat": 5, "lines": [{"text": text}], "shots": [
                {"at": "Ten men", "type": "A", "picture": "wide", "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}},
                {"at": "Two of them", "type": "B", "picture": "close", "motion": {"kind": "hold", "z0": 1.0, "z1": 1.0}}]}]}


def test_a_closer_shot_shows_part_of_the_establishing_view():
    assert V.establishing_cast(_cast_doc(["musk"])) == []
    assert V.establishing_cast(_cast_doc(["musk", "cuban"]))  # a stranger nobody was shown or told about
    assert V.establishing_cast(_cast_doc(["cuban"], "Ten men sit on the bench. Two of them talk to Cuban.")) == []
    revealed = _cast_doc(["cuban"])
    revealed["segments"][0]["shots"][1]["reveal"] = "cuban"  # a deliberate reveal, named after the picture
    assert V.establishing_cast(revealed) == []


# --- BP-92: a camera move never resets -----------------------------------------------------------------------------------

def _shot(i, pic, kind, z0, z1):
    return {"id": f"SH{i:03d}", "picture": pic, "motion": {"kind": kind, "z0": z0, "z1": z1}}


def test_a_chained_pull_never_goes_all_the_way_back():
    shots = CONT.chain([_shot(1, "a", "push", 1.0, 1.08), _shot(2, "a", "pull", 1.09, 1.0)])
    assert shots[1]["render_motion"]["z1"] > 1.0 + SR.T("BP-30", "same_framing_zoom_tol")  # one step, not a reset
    assert shots[0]["render_motion"]["eout"] and shots[1]["render_motion"]["ein"]  # the turn comes to rest
    assert not _rules(CONT.findings(shots), "BP-92")
    capped = CONT.chain([_shot(1, "a", "push", 1.0, 1.15), _shot(2, "a", "push", 1.0, 1.05)])
    assert capped[1]["render_motion"]["z1"] == round(1.15 - CONT.STEP, 4)


def test_a_run_that_returns_to_its_start_framing_is_a_reset():
    a = {"id": "SH001", "picture": "a", "render_motion": {"z0": 1.0, "z1": 1.06, "x0": 0.0, "x1": 0.0}}
    b = {"id": "SH002", "picture": "a", "render_motion": {"z0": 1.06, "z1": 1.0, "x0": 0.0, "x1": 0.0}}
    found = _rules(CONT.findings([a, b]), "BP-92")
    assert [f["where"] for f in found] == ["SH002"] and found[0]["severity"] == SR.rule("BP-92")["severity"]


# --- BP-94: the mood is held after an exchange ---------------------------------------------------------------------------

def test_the_cut_waits_after_the_last_hero_line():
    hold = SR.T("BP-94", "hold_min_s")
    timed = {"lines": [{"segment": "S01", "line": 2, "speaker": "musk", "start": 3.0, "end": 5.0}],
             "shots": [{"start": 0.0}, {"start": 5.0 + hold / 2}]}
    found = M.exchange_holds(timed)
    assert [f["severity"] for f in found] == ["REVIEW"]
    timed["shots"][1]["start"] = 5.0 + hold
    assert M.exchange_holds(timed) == []
