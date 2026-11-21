"""Unit tests for the provisional bridge sync checks (QUALITY_SPEC.md section 3, B1–B5)."""

import pytest

from explainer_engine.maps.bridge_sync import (
    ENV_VAR,
    bridge_problems,
    bridge_window,
    check_cap_height,
    check_hold,
    check_onset,
    find_bridge,
    normalize,
)

BRIDGE_TEXT = "keep the water"


def _narration() -> list[dict]:
    return [
        {"word": "We", "start_s": 0.0, "end_s": 0.2, "heard": True},
        {"word": "keep", "start_s": 0.2, "end_s": 0.5, "heard": True},
        {"word": "the", "start_s": 0.5, "end_s": 0.7, "heard": True},
        {"word": "water", "start_s": 0.7, "end_s": 1.0, "heard": True},
        {"word": "clean.", "start_s": 1.1, "end_s": 1.5, "heard": True},
    ]


def test_normalize_strips_punctuation_and_case():
    assert normalize("Water,") == "water"
    assert normalize('"Keep"') == "keep"
    assert normalize("clean.") == "clean"
    assert normalize("...") == ""


def test_find_bridge_found():
    assert find_bridge(_narration(), BRIDGE_TEXT) == (1, 3)


def test_find_bridge_matches_case_and_punctuation():
    assert find_bridge(_narration(), "Keep the WATER!") == (1, 3)


def test_find_bridge_not_found():
    assert find_bridge(_narration(), "wash the water") is None
    assert find_bridge(_narration(), "") is None


def test_bridge_window_not_found_is_a_failure():
    window = bridge_window(_narration(), "wash the water")
    assert window["ok"] is False
    assert window["problems"] == ["bridge text not found in narration"]


def test_bridge_window_found():
    window = bridge_window(_narration(), "Keep the water!")
    assert window == {"ok": True, "onset_s": 0.2, "hold_end_s": 1.0, "problems": []}


def test_bridge_window_missing_timing_is_rejected():
    words = _narration()
    words[2]["start_s"] = None
    window = bridge_window(words, BRIDGE_TEXT)
    assert window["ok"] is False
    assert window["problems"] == ["no word timing for bridge: rejected, never placed by estimate"]


def test_bridge_window_absent_timing_key_is_rejected():
    words = _narration()
    del words[3]["end_s"]
    window = bridge_window(words, BRIDGE_TEXT)
    assert window["ok"] is False
    assert window["problems"] == ["no word timing for bridge: rejected, never placed by estimate"]


def test_check_onset_within_one_frame_passes():
    assert check_onset(0.2 + 0.03, 0.2, 30.0) == []
    assert check_onset(0.2 - 0.03, 0.2, 30.0) == []


def test_check_onset_beyond_one_frame_fails():
    problems = check_onset(0.2 + 0.07, 0.2, 30.0)
    assert len(problems) == 1
    assert "onset" in problems[0]


def test_check_onset_rejects_bad_fps():
    with pytest.raises(ValueError):
        check_onset(0.2, 0.2, 0.0)


def test_check_hold_too_short_fails():
    problems = check_hold(0.9, 0.5, 0.2)
    assert len(problems) == 1
    assert "minimum hold" in problems[0]


def test_check_hold_ending_before_last_word_fails():
    problems = check_hold(0.9, 1.0, 0.2, min_hold_s=0.5)
    assert len(problems) == 1
    assert "before the last bridge word ends" in problems[0]


def test_check_cap_height_below_minimum_fails():
    assert check_cap_height(8.0) == []
    problems = check_cap_height(7.9)
    assert len(problems) == 1
    assert "cap height" in problems[0]


def test_bridge_problems_flag_off_returns_empty(monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    assert bridge_problems(_narration(), BRIDGE_TEXT, 5.0, 5.0, 30.0, 2.0) == []


def test_bridge_problems_flag_on_good_input_returns_empty(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "1")
    assert bridge_problems(_narration(), "Keep the water!", 0.2, 1.3, 30.0, 9.0) == []


def test_bridge_problems_flag_on_bad_input_reports(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "1")
    problems = bridge_problems(_narration(), BRIDGE_TEXT, 0.5, 0.9, 30.0, 6.0)
    assert len(problems) == 4  # onset, disappears early, hold too short, cap height


def test_bridge_problems_not_found_returns_only_window_problems(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "1")
    assert bridge_problems(_narration(), "wash the water", 5.0, 5.0, 30.0, 1.0) == [
        "bridge text not found in narration"
    ]
