"""The bridge caller in the map frame path: a bridge paints only inside its narrated window, and never silently mistimes."""

import copy

import numpy as np
import pytest

from explainer_engine.maps import render as R
from explainer_engine.maps import timeline as T

W, H, FPS = 320, 180, 24
WORDS = [
    {"word": "The", "start_s": 0.5, "end_s": 0.75},
    {"word": "bridge", "start_s": 0.75, "end_s": 1.25},
    {"word": "holds", "start_s": 1.25, "end_s": 1.9},
]


def _spec(with_bridge: bool = False) -> tuple[dict, dict]:
    spec, spine = R.build_toba_gis_map_spec("bridge_caller", width=W, height=H, total_frames=48)
    if with_bridge:
        spec["payload"]["fps"] = FPS
        spec["payload"]["bridges"] = [{"text": "The bridge", "onset_s": 1.0, "hold_end_s": 3.0, "style": "card"}]
    return spec, spine


def _frame(spec: dict, spine: dict, f: int) -> np.ndarray:
    tl, clock = T.build(spec, spine, trigger_word_index=0, duration_frames=48)
    return np.array(R.render_frame(spec, tl, clock, f))


def test_bridge_paints_only_inside_its_window():
    plain, spine = _spec()
    bridged, _ = _spec(with_bridge=True)
    assert np.array_equal(_frame(plain, spine, 0), _frame(bridged, spine, 0))
    assert not np.array_equal(_frame(plain, spine, 48), _frame(bridged, spine, 48))


def test_bridges_from_words_times_from_the_narration():
    out = R.bridges_from_words(WORDS, [{"text": "the bridge"}])
    assert out == [{"text": "the bridge", "onset_s": 0.5, "hold_end_s": 1.25, "style": "card"}]


def test_bridges_from_words_refuses_missing_text():
    with pytest.raises(ValueError, match="not found in narration"):
        R.bridges_from_words(WORDS, [{"text": "a missing caption"}])


def test_spec_without_bridges_renders_identically():
    spec, spine = _spec()
    assert "bridges" not in spec["payload"]
    base = _frame(spec, spine, 24)
    assert base.max() > 0
    assert np.array_equal(base, _frame(spec, spine, 24))
    empty = copy.deepcopy(spec)
    empty["payload"]["bridges"] = []
    assert np.array_equal(base, _frame(empty, spine, 24))
