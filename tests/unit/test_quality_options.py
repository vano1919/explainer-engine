from __future__ import annotations

import pytest

from explainer_engine.maps import bridge_sync, quality_provisional
from explainer_engine.maps.quality_options.loader import (
    active_option,
    load_bridge_styles,
    load_presets,
    load_thresholds,
)

THRESHOLD_KEYS = {
    "option",
    "primary_line_width_pct",
    "secondary_line_width_pct",
    "label_cap_height_pct",
    "label_contrast_ratio",
    "green_hue_min_deg",
    "green_hue_max_deg",
    "green_saturation_min_pct",
    "bridge_onset_tol_frames",
    "bridge_cap_height_min_pct",
    "bridge_hold_min_s",
    "residual_motion_per_frame_max_pct",
    "residual_displacement_shot_max_pct",
    "visual_meaning",
}

MIN_KEYS = (
    "primary_line_width_pct",
    "secondary_line_width_pct",
    "label_cap_height_pct",
    "label_contrast_ratio",
    "green_hue_min_deg",
    "green_saturation_min_pct",
    "bridge_cap_height_min_pct",
    "bridge_hold_min_s",
)

MAX_KEYS = (
    "green_hue_max_deg",
    "bridge_onset_tol_frames",
    "residual_motion_per_frame_max_pct",
    "residual_displacement_shot_max_pct",
)


@pytest.mark.parametrize("option", ["strict", "medium", "light"])
def test_threshold_files_load_with_all_keys(option):
    thresholds = load_thresholds(option)
    assert set(thresholds) == THRESHOLD_KEYS
    assert thresholds["option"] == option


def test_strict_is_at_least_as_strict_as_medium():
    medium = load_thresholds("medium")
    strict = load_thresholds("strict")
    for key in MIN_KEYS:
        assert strict[key] >= medium[key], key
    for key in MAX_KEYS:
        assert strict[key] <= medium[key], key


def test_light_is_at_most_as_strict_as_medium():
    medium = load_thresholds("medium")
    light = load_thresholds("light")
    for key in MIN_KEYS:
        assert light[key] <= medium[key], key
    for key in MAX_KEYS:
        assert light[key] >= medium[key], key


def test_medium_matches_current_constants():
    medium = load_thresholds("medium")
    assert medium["primary_line_width_pct"] == quality_provisional.MIN_PRIMARY_LINE_WIDTH_PCT
    assert medium["secondary_line_width_pct"] == quality_provisional.MIN_SECONDARY_LINE_WIDTH_PCT
    assert medium["label_cap_height_pct"] == quality_provisional.MIN_LABEL_CAP_HEIGHT_PCT
    assert medium["label_contrast_ratio"] == quality_provisional.MIN_LABEL_CONTRAST_RATIO
    assert medium["green_hue_min_deg"] == quality_provisional.GREEN_HUE_MIN_DEG
    assert medium["green_hue_max_deg"] == quality_provisional.GREEN_HUE_MAX_DEG
    assert medium["green_saturation_min_pct"] == quality_provisional.GREEN_SATURATION_MIN_PCT
    assert medium["bridge_onset_tol_frames"] == bridge_sync.BRIDGE_ONSET_TOL_FRAMES
    assert medium["bridge_cap_height_min_pct"] == bridge_sync.BRIDGE_CAP_HEIGHT_MIN_PCT
    assert medium["bridge_hold_min_s"] == bridge_sync.BRIDGE_HOLD_MIN_S


def test_active_option_defaults_to_medium(monkeypatch):
    monkeypatch.delenv("QUALITY_OPTION", raising=False)
    assert active_option() == "medium"


def test_active_option_rejects_unknown(monkeypatch):
    monkeypatch.setenv("QUALITY_OPTION", "bogus")
    with pytest.raises(ValueError):
        active_option()


def test_load_thresholds_rejects_unknown():
    with pytest.raises(ValueError):
        load_thresholds("bogus")


def test_presets_loaded():
    presets = load_presets()
    assert [preset["name"] for preset in presets] == ["bold", "balanced", "light"]


def test_bridge_styles_loaded():
    styles = load_bridge_styles()
    assert [style["name"] for style in styles] == ["card", "outline", "lower_third"]
