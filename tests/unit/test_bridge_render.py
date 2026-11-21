"""Tests of the bridge renderer: each style paints, an unknown style is refused, and an empty text draws nothing."""

import numpy as np
import pytest

from explainer_engine.maps.bridge_render import bridge_text_width, draw_bridge
from explainer_engine.maps.draw import Canvas

W, H = 480, 270


def _canvas() -> Canvas:
    return Canvas(W, H, background=(0, 0, 0))


@pytest.mark.parametrize("name", ["card", "outline", "lower_third"])
def test_each_style_changes_the_canvas(name):
    c = _canvas()
    before = c.im.tobytes()
    draw_bridge(c, "The bridge", {"name": name, "cap_height_pct": 12})
    assert c.im.tobytes() != before


def test_unknown_style_raises():
    c = _canvas()
    with pytest.raises(ValueError):
        draw_bridge(c, "The bridge", {"name": "neon", "cap_height_pct": 12})


def test_empty_text_draws_nothing():
    c = _canvas()
    before = c.im.tobytes()
    draw_bridge(c, "", {"name": "card", "cap_height_pct": 12})
    assert c.im.tobytes() == before


def test_card_paints_the_bottom_band():
    c = _canvas()
    before = np.array(c.im).copy()
    draw_bridge(c, "A line of the bridge", {"name": "card", "cap_height_pct": 12})
    after = np.array(c.im)
    band = slice(int(H * 0.7) * c.ss, H * c.ss)  # bottom band, in supersampled pixel rows
    assert np.any(before[band] != after[band])


def test_bridge_text_width_matches_canvas():
    c = _canvas()
    style = {"name": "card", "cap_height_pct": 12}
    size = style["cap_height_pct"] / 100.0 * c.h
    assert bridge_text_width(c, "Width", style) == pytest.approx(c.text_width("Width", size))
