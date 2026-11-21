"""A bridge is visible from its first word's start to its last word's end, and at least its minimum hold (narration-timed)."""

import pytest

from explainer_engine.maps import bridge_render as B
from explainer_engine.maps import bridge_sync as S

WORDS = [
    {"word": "In", "start_s": 0.0, "end_s": 0.2, "heard": True},
    {"word": "August", "start_s": 1.0, "end_s": 1.4, "heard": True},
    {"word": "1914", "start_s": 1.5, "end_s": 1.9, "heard": True},
    {"word": "Europe", "start_s": 2.5, "end_s": 2.9, "heard": True},
]


def test_bridge_on_screen_from_its_first_word_to_its_last_word():
    win = S.bridge_window(WORDS, "August 1914")
    assert win["ok"] is True
    onset, hold_end = win["onset_s"], win["hold_end_s"]
    fps = 24.0
    assert B.visible_at(round(onset * fps), onset, hold_end, fps) is True
    assert B.visible_at(round(onset * fps) - 2, onset, hold_end, fps) is False
    assert B.visible_at(round(hold_end * fps) + 1, onset, hold_end, fps) is True  # hold after the last word


def test_minimum_hold_extends_a_short_bridge():
    fps = 24.0
    assert B.visible_at(int(1.0 * fps) + int(0.9 * fps), 1.0, 1.1, fps, min_hold_s=1.0) is True


def test_bad_fps_raises():
    with pytest.raises(ValueError):
        B.visible_at(0, 0.0, 1.0, 0.0)
