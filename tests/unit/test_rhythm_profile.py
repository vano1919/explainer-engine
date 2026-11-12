"""The rhythm profile reader (BP-169, Argon roadmap WP-R2)."""

import pytest

from explainer_engine.edit import rhythm_profile as RP
from explainer_engine.standards import sourced_rules as SR


def test_default_profile_is_mrbeast_animated_and_legacy_scripts_resolve_to_calm():
    assert RP.resolve_profile_name(None) == "mrbeast_animated"
    assert RP.resolve_profile_name({}) == "mrbeast_animated"
    assert RP.resolve_profile_name({"schema": "production_script/3"}) == "calm_docudrama"
    assert RP.resolve_profile_name({"schema": "production_script/4"}) == "mrbeast_animated"
    assert RP.resolve_profile_name({"schema": "production_script/3", "rhythm_profile": "mrbeast_animated"}) == "mrbeast_animated"
    assert set(RP.available_profiles()) == {"mrbeast_animated", "calm_docudrama"}


def test_zone_lookup_covers_all_five_zones_and_scales_to_custom_duration():
    ids = [RP.zone_at_time(t)["id"] for t in (0, 15, 45, 240, 540, 700, 720)]
    assert ids == ["hook_0_30s", "hook_0_30s", "early_30_90s", "middle_calm_90_480s", "late_third_480_660s",
                   "climax_660_720s", "climax_660_720s"]
    assert RP.zone_at_time(20, total_s=360)["id"] == "early_30_90s"  # 360 s episode: the hook is 15 s long
    assert RP.zone_for_window(20, 100)["id"] == "early_30_90s"


def test_unknown_profile_or_negative_timestamp_raises():
    with pytest.raises(KeyError):
        RP.resolve_profile_name({"rhythm_profile": "nonexistent"})
    with pytest.raises(ValueError):
        RP.zone_at_time(-1.0)
    with pytest.raises(KeyError):
        RP.get_profile("calm_docudrama")  # the legacy profile has no zones
    with pytest.raises(KeyError):
        RP.zone_wpm("nowhere")


def test_pace_comes_from_the_registry_and_words_cross_zone_borders():
    assert RP.zone_wpm("hook_0_30s") == SR.T("BP-169", "profiles")["mrbeast_animated"]["zones"][0]["heard_wpm_target"] == 193
    assert RP.zone_wpm("hook_0_30s", kind="speaking") > RP.zone_wpm("hook_0_30s")
    mean = RP.zone_wpm()
    assert 165 < mean < 180  # the profile's time-weighted pace
    # 96.5 words fill the 30 s hook at 193 wpm
    assert RP.words_to_seconds(96, t_start_s=0) == pytest.approx(96 / 193 * 60, rel=1e-6)
    # a long read from second 20 runs into the next zone at its slower pace: slower than the hook pace alone
    assert RP.words_to_seconds(100, t_start_s=20) > 100 / 193 * 60
    with pytest.raises(ValueError):
        RP.words_to_seconds(-1)
