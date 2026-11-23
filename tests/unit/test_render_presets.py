"""Tests for explainer_engine.maps.render_presets."""

import re

import pytest

from explainer_engine.maps import render_presets

MAP_PRESET_NAMES = ("bold", "balanced", "light")
BRIDGE_STYLE_NAMES = ("card", "outline", "lower_third")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def test_map_presets_exist():
    for name in MAP_PRESET_NAMES:
        preset = render_presets.get_map_preset(name)
        assert preset["name"] == name


def test_bridge_styles_exist():
    for name in BRIDGE_STYLE_NAMES:
        style = render_presets.get_bridge_style(name)
        assert style["name"] == name


def test_unknown_map_preset_raises():
    with pytest.raises(ValueError):
        render_presets.get_map_preset("nope")


def test_active_map_preset_default(monkeypatch):
    monkeypatch.delenv("MAP_PRESET", raising=False)
    assert render_presets.active_map_preset()["name"] == "balanced"


def test_active_map_preset_from_env(monkeypatch):
    monkeypatch.setenv("MAP_PRESET", "bold")
    assert render_presets.active_map_preset()["name"] == "bold"


def test_active_map_preset_unknown_env_raises(monkeypatch):
    monkeypatch.setenv("MAP_PRESET", "bogus")
    with pytest.raises(ValueError):
        render_presets.active_map_preset()


def test_line_px_primary():
    preset = render_presets.get_map_preset("light")
    assert render_presets.line_px(preset, 1080, "primary") == pytest.approx(5.4, abs=1e-9)


def test_line_px_secondary():
    preset = render_presets.get_map_preset("light")
    assert render_presets.line_px(preset, 1080, "secondary") == pytest.approx(2.7, abs=1e-9)


def test_label_px():
    preset = render_presets.get_map_preset("light")
    assert render_presets.label_px(preset, 1080) == pytest.approx(27.0, abs=1e-9)


def test_line_px_invalid_kind_raises():
    preset = render_presets.get_map_preset("light")
    with pytest.raises(ValueError):
        render_presets.line_px(preset, 1080, "tertiary")


def test_line_px_zero_height_raises():
    preset = render_presets.get_map_preset("light")
    with pytest.raises(ValueError):
        render_presets.line_px(preset, 0, "primary")


def test_colours_are_valid_hex():
    for name in MAP_PRESET_NAMES:
        fill, halo = render_presets.colours(render_presets.get_map_preset(name))
        assert HEX_RE.match(fill)
        assert HEX_RE.match(halo)
