"""Episode map style presets (owner 2026-11-20): every preset is complete, passes the palette check, bad names refused."""
from __future__ import annotations
import pytest
from explainer_engine.maps.maplibre_lane.render import (
    STYLES_DIR, _validate_hud_palette, load_style_preset,
)
from explainer_engine.maps.maplibre_spec import validate_shot_spec

NAMES = sorted(p.stem for p in STYLES_DIR.glob("*.json"))


def test_presets_exist():
    assert "neutral" in NAMES and "1917_film" in NAMES


@pytest.mark.parametrize("name", NAMES)
def test_preset_complete_and_palette_ok(name):
    preset = load_style_preset(name)
    assert preset["name"] == name
    for key in ("background", "water", "waterway", "landcover", "boundary", "roads", "hillshade"):
        assert key in preset["map"]
    for key in ("counter_bg", "counter_border", "counter_value", "chip_bg", "chip_fg", "town_text", "footnote_bg"):
        assert key in preset["hud"]
    _validate_hud_palette(preset)


def test_unknown_or_unsafe_name_refused():
    with pytest.raises(FileNotFoundError):
        load_style_preset("no_such_style")
    with pytest.raises(ValueError):
        load_style_preset("../neutral")


def test_style_preset_spec_key_validated():
    assert any("style_preset" in p for p in validate_shot_spec({"style_preset": ""}))


def test_truce_cold_preset_is_usable_and_follows_the_film_font():
    from explainer_engine.maps.maplibre_lane import render
    cold = render.load_style_preset("truce_cold")
    assert "draft" not in cold
    assert cold["font"] == render.load_style_preset("1917_film")["font"]
    render._validate_hud_palette(cold)
