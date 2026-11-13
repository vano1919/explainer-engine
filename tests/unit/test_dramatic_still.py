"""BP-170: a held still changes dramatically (WP-R4)."""

import pytest
from PIL import Image, ImageDraw

from explainer_engine.edit import dramatic_still as DS

GOOD = {"kind": "cutout_relocation", "subject_layer": "hero", "from_box": [0.05, 0.2, 0.30, 0.85],
        "to_box": [0.60, 0.15, 0.85, 0.80], "relocation_distance_frac": 0.55, "subject_area_frac": 0.16, "at_s": 2.0}


def _rules(findings):
    return [f["severity"] for f in findings]


def test_cutout_relocation_over_25_percent_on_4s_still_passes_and_renders():
    assert DS.validate_dramatic_change(GOOD, shot_seconds=4.0) == []
    plate = Image.new("RGB", (192, 108), (200, 190, 170))
    hero = Image.new("RGBA", (40, 80), (20, 40, 160, 255))
    before = DS.render_dramatic_still(plate, hero, GOOD, t_s=0.5)
    after = DS.render_dramatic_still(plate, hero, GOOD, t_s=3.0)
    assert before.size == after.size == (192, 108)
    m = DS.measure_frame_change(before, after)
    assert m["is_dramatic"] and m["changed_frac"] >= 0.08       # the old and the new place both differ
    assert before.getpixel((int(0.15 * 192), int(0.5 * 108))) != after.getpixel((int(0.15 * 192), int(0.5 * 108)))


def test_small_dot_or_tiny_object_change_is_rejected_as_not_dramatic():
    dot = dict(GOOD, from_box=[0.10, 0.50, 0.14, 0.58], to_box=[0.80, 0.50, 0.84, 0.58])   # moves far, covers < 1 %
    f = DS.validate_dramatic_change(dot, shot_seconds=4.0)
    assert f and "small thing" in f[0]["detail"] and _rules(f)[0] == "FAIL"
    plate = Image.new("RGB", (192, 108), (200, 190, 170))
    a, b = plate.copy(), plate.copy()
    ImageDraw.Draw(a).ellipse((10, 50, 18, 58), fill=(0, 0, 0))
    ImageDraw.Draw(b).ellipse((150, 50, 158, 58), fill=(0, 0, 0))
    assert not DS.measure_frame_change(a, b)["is_dramatic"]


def test_plain_zoom_or_4_percent_shift_on_4s_still_is_rejected():
    nudge = dict(GOOD, from_box=[0.10, 0.2, 0.40, 0.8], to_box=[0.14, 0.2, 0.44, 0.8])     # a big character that shifts 4 %
    f = DS.validate_dramatic_change(nudge, shot_seconds=4.0)
    assert any("nudge" in x["detail"] for x in f)
    assert DS.validate_dramatic_change(None, shot_seconds=4.0)[0]["severity"] == "FAIL"        # nothing at all


def test_still_over_5_seconds_fails_even_with_dramatic_change():
    f = DS.validate_dramatic_change(GOOD, shot_seconds=5.2)
    assert len(f) == 1 and "cap" in f[0]["detail"]


def test_a_short_hold_needs_no_change_and_the_change_must_sit_in_the_middle_of_the_hold():
    assert DS.validate_dramatic_change(None, shot_seconds=1.4, zone_id="hook_0_30s") == []
    assert DS.validate_dramatic_change(None, shot_seconds=2.4, zone_id="hook_0_30s")     # over the hook's static limit
    late = dict(GOOD, at_s=3.9)
    assert any("middle of the hold" in x["detail"] for x in DS.validate_dramatic_change(late, shot_seconds=4.0))
    with pytest.raises(KeyError):
        DS.validate_dramatic_change(None, shot_seconds=3.0, zone_id="nowhere")


def test_a_plate_swap_must_change_a_third_of_the_pixels():
    swap = {"kind": "plate_swap", "bg_before": "a.png", "bg_after": "b.png", "plate_swap_pixel_frac": 0.5, "at_s": 2.0}
    assert DS.validate_dramatic_change(swap, shot_seconds=4.0) == []
    assert DS.validate_dramatic_change(dict(swap, plate_swap_pixel_frac=0.1), shot_seconds=4.0)
    a, b = Image.new("RGB", (64, 36), (255, 255, 255)), Image.new("RGB", (64, 36), (0, 0, 0))
    assert DS.measure_frame_change(a, b)["plate_swap"]


def test_script_stills_are_checked_in_their_zone():
    shots = [{"id": "s1", "seconds": 4.0, "tier": "hold"}, {"id": "v1", "seconds": 4.0},
             {"id": "s2", "seconds": 4.0, "tier": "hold", "dramatic_change": GOOD}]
    found = DS.check_script_stills(shots)
    assert [f["where"] for f in found] == ["s1"]
