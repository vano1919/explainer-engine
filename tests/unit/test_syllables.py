"""The read-time estimate before any voice exists (P3, BP-01, BP-115): the pace is BP-01's, the shape comes from released Scribe reads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.production import validate
from explainer_engine.scripting import syllables as SY
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]
SCRIBE_FILES = [ROOT / "examples/stone_age/day1_v2/words.json", ROOT / "examples/stone_age/day1_v5/words.json"]


@pytest.mark.parametrize("word,n", [("a", 1), ("the", 1), ("history", 3), ("fire", 1), ("little", 2), ("table", 2), ("banana", 3),
                                    ("tree", 1), ("rhythm", 1), ("1930s", 1), ("", 0)])
def test_the_counter_is_the_one_the_flesch_kincaid_grade_uses(word, n):
    assert SY.count(word) == n
    assert validate.syllables is SY.count


def test_more_syllables_and_pauses_take_longer():
    assert SY.seconds("Go.") < SY.seconds("Unbelievably.") < SY.seconds("Unbelievably, unbelievably.")
    assert SY.seconds("Wait, now.") > SY.seconds("Wait now")
    assert SY.seconds("Hold.", pause_after=1.5) == pytest.approx(SY.seconds("Hold.") + 1.5)


def test_the_pace_is_bp_01s_not_the_modules():
    """Over the calibration corpus the average word lasts 60 / BP-01 wpm_target seconds (the shape is fitted, the pace is not)."""
    words = []
    for f in SCRIBE_FILES:
        words += [w["w"] for w in json.loads(f.read_text(encoding="utf-8"))["words"]]
    text = " ".join(words)
    per_word = SY.seconds(text) / len(words)
    assert per_word == pytest.approx(60.0 / SR.T("BP-01", "wpm_target"), rel=0.03)


def test_calibration_keeps_only_scribe_reads(tmp_path):
    cal = SY.calibrate(SCRIBE_FILES + [ROOT / "examples/titans_from_zero/words.json", ROOT / "examples/stone_age/day1_v1/words.json"])
    assert [Path(s["path"]).name for s in cal["sources"]] == ["words.json", "words.json"] and len(cal["sources"]) == 2
    assert len(cal["skipped"]) == 2 and all("not Scribe" in s["why"] for s in cal["skipped"])
    assert cal["ratio_b_over_a"] > 0 and cal["pause_units_sentence"] > cal["pause_units_clause"] > 0
    with pytest.raises(ValueError):
        SY.calibrate([ROOT / "examples/stone_age/day1_v1/words.json"])


def test_the_committed_calibration_is_what_the_cli_computes():
    fresh = SY.calibrate(SCRIBE_FILES)
    stored = SY.calibration()
    for k in ("ratio_b_over_a", "pause_units_sentence", "pause_units_clause", "mean_units_per_word"):
        assert stored[k] == pytest.approx(fresh[k], abs=1e-3), k


def test_a_zone_or_a_pace_changes_the_seconds_and_the_default_does_not():
    S = SY
    text = "Ten thousand men walked across the frozen river before dawn."
    base = S.seconds(text)
    assert S.seconds(text, wpm=None, zone=None) == base                    # nothing asked: BP-01's pace, as before
    hook, middle = S.seconds(text, zone="hook_0_30s"), S.seconds(text, zone="middle_calm_90_480s")
    assert hook < middle                                                   # 193 wpm reads faster than 166 wpm
    assert S.seconds(text, wpm=100) > base > S.seconds(text, wpm=250)
    assert S.seconds(text, zone="hook_0_30s", pause_after=0.5) == pytest.approx(hook + 0.5, abs=1e-3)
