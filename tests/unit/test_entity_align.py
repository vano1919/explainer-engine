"""Names the reader says slightly differently (Blueprint P3): the reduced phonetic key, and the word times of a read marking a
name as heard when Scribe wrote it another way."""

from __future__ import annotations

import pytest

from explainer_engine.audio import scribe_words as SW
from explainer_engine.scripting import entity_align as EA


def test_the_keys_of_the_plan_cards_examples():
    assert (EA.key("Ney"), EA.key("Nay")) == ("N", "N")
    assert (EA.key("Subutai"), EA.key("Subotai")) == ("SBT", "SBT")
    assert EA.key("Knight") == EA.key("Night") and EA.key("Philip") == EA.key("Filip")
    assert EA.key("") == "" and EA.key("1812") == ""


def test_same_is_equal_keys_or_one_edit_between_keys_of_three_letters():
    assert EA.same("Ney", "Nay") and EA.same("Subutai", "Subotai")
    assert EA.same("Subutai", "Sabutay") and not EA.same("Subutai", "Napoleon")
    assert EA.same("Kemal", "Kemel") and not EA.same("Ney", "Murat")
    assert not EA.same("", "x") and not EA.same("Ney", "1812")


def test_heard_marks_only_the_names_it_is_given():
    assert EA.heard(["Marshal", "Ney", "rode"], ["marshal", "Nay", "road"], names={"Ney"}) == [True, True, False]
    assert EA.heard(["Marshal", "Ney"], ["marshal", "Nay"]) == [True, False]


def timed(words):
    return [{"text": w, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, w in enumerate(words)]


def test_align_marks_a_misheard_name_heard_and_leaves_the_times_alone():
    text = "Marshal Ney led the guard."
    heard = timed(["Marshal", "Nay", "led", "the", "guard"])
    plain = SW.align(text, heard)
    named = SW.align(text, heard, entities={"Ney"})
    assert plain["unmatched"] == ["Ney"] and named["unmatched"] == []
    assert named["coverage"] > plain["coverage"] and named["coverage"] == 1.0
    assert [(w["s"], w["e"]) for w in named["words"]] == [(w["s"], w["e"]) for w in plain["words"]]
    assert not any(w.get("estimated") for w in named["words"])


def test_align_without_entities_or_for_a_different_word_is_unchanged():
    text = "Marshal Ney led the guard."
    heard = timed(["Marshal", "Nay", "led", "the", "guard"])
    assert SW.align(text, heard) == SW.align(text, heard, entities=None) == SW.align(text, heard, entities=set())
    wrong = timed(["Marshal", "Murat", "led", "the", "guard"])
    assert SW.align(text, wrong, entities={"Ney"})["unmatched"] == ["Ney"]
    other = SW.align("The tall fog lay.", timed(["The", "small", "fog", "lay"]), entities={"Ney"})
    assert other["unmatched"] == SW.align("The tall fog lay.", timed(["The", "small", "fog", "lay"]))["unmatched"]
