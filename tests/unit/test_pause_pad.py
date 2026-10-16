"""Pause padding (D-39): silence goes into short punctuated gaps only; words keep their sound and move as a block."""

from __future__ import annotations

import numpy as np

from explainer_engine.audio import pause_pad as P
from explainer_engine.edit import shot_rules as R

SR = 1000


def make():
    words = [{"w": "Hello,", "s": 0.0, "e": 0.4, "para": 0}, {"w": "there", "s": 0.45, "e": 0.8, "para": 0},
             {"w": "friend.", "s": 0.82, "e": 1.2, "para": 0}, {"w": "Next", "s": 2.0, "e": 2.3, "para": 1}]
    audio = np.zeros(int(2.4 * SR), np.float32)
    for w in words:
        audio[int(w["s"] * SR):int(w["e"] * SR)] = 0.5
    return words, audio


def test_only_short_punctuated_gaps_are_padded_and_times_move_as_a_block():
    words, audio = make()
    out, new, rep = P.pad_pauses(words, audio, SR, min_gap=0.26)
    assert rep["inserted"] == 1  # "Hello," 0.05 s; "there" has no mark; "friend." already 0.8 s
    assert abs(rep["added_seconds"] - 0.21) < 1e-6 and len(out) == len(audio) + int(round(0.21 * SR))
    assert new[0]["s"] == 0.0 and new[0]["e"] == 0.4
    assert abs(new[1]["s"] - 0.66) < 1e-3 and abs(new[3]["s"] - 2.21) < 1e-3
    for w in new:  # every word still sits on its own sound
        seg = out[int(round(w["s"] * SR)) + 2:int(round(w["e"] * SR)) - 2]
        assert seg.size and np.all(seg == 0.5)


def test_padded_gap_is_a_legal_cut():
    words, audio = make()
    _, new, _ = P.pad_pauses(words, audio, SR)
    gap = (new[0]["e"] + new[1]["s"]) / 2
    assert R.cut_ok(gap, new)
    assert not R.cut_ok((words[0]["e"] + words[1]["s"]) / 2, words)  # not before padding


def test_nothing_to_pad_returns_the_same_audio():
    words, audio = make()
    words[0]["e"], words[1]["s"] = 0.3, 0.6
    out, new, rep = P.pad_pauses(words, audio, SR)
    assert rep["inserted"] == 0 and np.array_equal(out, audio)
    assert [w["s"] for w in new] == [w["s"] for w in words]
