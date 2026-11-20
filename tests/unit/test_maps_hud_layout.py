"""Tests for explainer_engine/maps/hud_layout.py (G-04a).

Drafted by Gemini Hydrogen (raw copy kept next to this folder), corrected by the tester (Sonnet) 2026-11-20.

Conventions these tests PIN (the brief does not spell them out; the code chat must follow them):
- boxes_overlap: boxes overlap when the gap between them is STRICTLY smaller than `margin`;
  touching edges (gap 0, margin 0) and gap == margin do NOT overlap.
- place_counter returns a tuple of four floats; a box "inside the frame minus safe_margin" may touch that inner
  edge (inclusive); the 8 px avoid margin is a module-level default, not a parameter.
- simulate_cvd returns a tuple of three ints in 0..255 and raises ValueError for an unknown kind.
- check_palette problem strings name the colours involved (the colour key for a contrast problem, both keys for a
  pair problem); a clean palette returns []. Pair problems are judged on the three simulations only.
- Machado 2009, severity 1.0, matrices on linear RGB (clamped to 0..1 before sRGB encoding); CIE76 delta E on
  CIE L*a*b* (D65).
- Constant NAMES are not fixed by the brief, so no test imports them; only their values are tested by behaviour.
"""
import ast
import inspect

import pytest

import explainer_engine.maps.hud_layout as hud
from explainer_engine.maps.hud_layout import (
    OKABE_ITO,
    HudLayoutError,
    boxes_overlap,
    check_palette,
    contrast_ratio,
    place_counter,
    simulate_cvd,
)

WHITE = (255, 255, 255)
FRAME = (1280, 704)
COUNTER = (220, 64)
TL = (48.0, 48.0, 268.0, 112.0)
TR = (1012.0, 48.0, 1232.0, 112.0)
BL = (48.0, 592.0, 268.0, 656.0)
BR = (1012.0, 592.0, 1232.0, 656.0)


# ---------------------------------------------------------------- Must NOT: cv2/PIL, files, network

def test_module_imports_nothing_forbidden_and_reads_no_files():
    tree = ast.parse(inspect.getsource(hud))
    forbidden = {"cv2", "PIL", "requests", "urllib", "http", "socket", "playwright"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots = {(node.module or "").split(".")[0]}
        else:
            roots = set()
        assert not (roots & forbidden), f"forbidden import {roots & forbidden}"
        if isinstance(node, ast.Call):
            fn = node.func
            assert not (isinstance(fn, ast.Name) and fn.id == "open"), "hud_layout must not read files"
            assert not (isinstance(fn, ast.Attribute) and fn.attr in {"read_text", "read_bytes", "open"})


# ---------------------------------------------------------------- OKABE_ITO

def test_okabe_ito_palette_structure_and_values():
    assert isinstance(OKABE_ITO, dict)
    assert len(OKABE_ITO) == 8
    expected = {
        (0, 0, 0), (230, 159, 0), (86, 180, 233), (0, 158, 115),
        (240, 228, 66), (0, 114, 178), (213, 94, 0), (204, 121, 167),
    }
    actual = set()
    for name, rgb in OKABE_ITO.items():
        assert isinstance(name, str) and name
        assert isinstance(rgb, tuple) and len(rgb) == 3
        assert all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in rgb)
        actual.add(rgb)
    assert actual == expected


# ---------------------------------------------------------------- boxes_overlap

@pytest.mark.parametrize(
    ("a", "b", "margin", "expected"),
    [
        ((0.0, 0.0, 100.0, 100.0), (50.0, 50.0, 150.0, 150.0), 0.0, True),      # partial overlap
        ((10.0, 10.0, 90.0, 90.0), (20.0, 20.0, 40.0, 40.0), 0.0, True),        # containment
        ((0.0, 0.0, 100.0, 100.0), (100.0, 0.0, 200.0, 100.0), 0.0, False),     # touching in x
        ((0.0, 0.0, 100.0, 100.0), (0.0, 100.0, 100.0, 200.0), 0.0, False),     # touching in y
        ((0.0, 0.0, 100.0, 100.0), (110.0, 0.0, 200.0, 100.0), 9.9, False),     # gap 10 > margin
        ((0.0, 0.0, 100.0, 100.0), (110.0, 0.0, 200.0, 100.0), 10.1, True),     # gap 10 < margin
        ((0.0, 0.0, 100.0, 100.0), (0.0, 108.0, 100.0, 200.0), 7.9, False),     # vertical gap 8
        ((0.0, 0.0, 100.0, 100.0), (0.0, 108.0, 100.0, 200.0), 8.1, True),
        ((110.0, 0.0, 200.0, 100.0), (0.0, 0.0, 100.0, 100.0), 10.1, True),     # symmetry
        ((0.0, 0.0, 100.0, 100.0), (110.0, 110.0, 200.0, 200.0), 9.9, False),   # diagonal gap 10/10
        ((0.0, 0.0, 100.0, 100.0), (110.0, 110.0, 200.0, 200.0), 10.1, True),
        ((0.0, 0.0, 100.0, 100.0), (110.0, 300.0, 200.0, 400.0), 50.0, False),  # y far apart, x within margin
    ],
)
def test_boxes_overlap(a, b, margin, expected):
    assert boxes_overlap(a, b, margin=margin) is expected
    assert boxes_overlap(b, a, margin=margin) is expected


def test_boxes_overlap_margin_defaults_to_zero():
    assert boxes_overlap((0, 0, 100, 100), (100, 0, 200, 100)) is False
    assert boxes_overlap((0, 0, 100, 100), (99, 0, 200, 100)) is True


# ---------------------------------------------------------------- place_counter

def test_place_counter_default_top_left_and_brief_example():
    avoid = (900, 100, 1200, 400)
    box = place_counter(FRAME, COUNTER, [avoid])
    assert box == TL
    assert all(isinstance(v, float) for v in box)
    assert not boxes_overlap(box, avoid, margin=8.0)
    assert place_counter(FRAME, COUNTER, []) == TL


def test_place_counter_respects_preference_order():
    block_tl = (40.0, 40.0, 100.0, 100.0)
    block_tr = (1000.0, 40.0, 1100.0, 100.0)
    block_bl = (40.0, 580.0, 100.0, 650.0)
    assert place_counter(FRAME, COUNTER, [block_tl]) == TR
    assert place_counter(FRAME, COUNTER, [block_tl, block_tr]) == BL
    assert place_counter(FRAME, COUNTER, [block_tl, block_tr, block_bl]) == BR
    # a blocked corner that is later in the order does not matter
    assert place_counter(FRAME, COUNTER, [block_tr]) == TL


def test_place_counter_custom_prefer_order():
    assert place_counter(FRAME, COUNTER, [], prefer=("bottom_right", "top_left")) == BR
    assert place_counter(FRAME, COUNTER, [], prefer=("bottom_left",)) == BL
    assert place_counter(FRAME, COUNTER, [], prefer=("top_right", "bottom_right")) == TR
    # with only one corner offered and that one blocked, there is no fallback to the others
    with pytest.raises(HudLayoutError, match="no free slot"):
        place_counter(FRAME, COUNTER, [(1000.0, 40.0, 1100.0, 100.0)], prefer=("top_right",))


def test_place_counter_avoid_margin_8px_boundary():
    # Top-left candidate ends at x=268: an avoid box starting at 276 is exactly 8 px away -> allowed.
    assert place_counter(FRAME, COUNTER, [(276.0, 48.0, 400.0, 112.0)]) == TL
    # 7.9 px away is inside the 8 px margin -> blocked, falls back to top_right.
    assert place_counter(FRAME, COUNTER, [(275.9, 48.0, 400.0, 112.0)]) == TR
    # same on the vertical axis: candidate ends at y=112; 120 is exactly 8 px below, 119.9 is not.
    assert place_counter(FRAME, COUNTER, [(48.0, 120.0, 268.0, 200.0)]) == TL
    assert place_counter(FRAME, COUNTER, [(48.0, 119.9, 268.0, 200.0)]) == TR


def test_place_counter_safe_margin_boundary_and_raises():
    # Usable region of a 316x160 frame with safe_margin 48 is exactly 220x64 -> exact fit succeeds.
    assert place_counter((316, 160), COUNTER, [], safe_margin=48.0) == TL
    # One pixel narrower: no corner fits inside the safe area.
    with pytest.raises(HudLayoutError, match="no free slot"):
        place_counter((315, 160), COUNTER, [], safe_margin=48.0)
    with pytest.raises(HudLayoutError, match="no free slot"):
        place_counter((316, 159), COUNTER, [], safe_margin=48.0)


def test_place_counter_safe_margin_parameter_changes_the_slot():
    assert place_counter(FRAME, COUNTER, [], safe_margin=10.0) == (10.0, 10.0, 230.0, 74.0)
    assert place_counter(FRAME, COUNTER, [], safe_margin=10.0, prefer=("bottom_right",)) == (
        1050.0, 630.0, 1270.0, 694.0)


def test_place_counter_all_corners_blocked_raises():
    with pytest.raises(HudLayoutError, match="no free slot"):
        place_counter(FRAME, COUNTER, [(0.0, 0.0, 1280.0, 704.0)])
    # four separate avoid boxes, one per corner
    with pytest.raises(HudLayoutError, match="no free slot"):
        place_counter(FRAME, COUNTER, [TL, TR, BL, BR])


def test_place_counter_error_type():
    assert issubclass(HudLayoutError, Exception)


# ---------------------------------------------------------------- contrast_ratio (WCAG 2.1)

def test_contrast_ratio_wcag21():
    assert contrast_ratio((0, 0, 0), WHITE) == pytest.approx(21.0, rel=1e-4)
    assert contrast_ratio(WHITE, (0, 0, 0)) == pytest.approx(21.0, rel=1e-4)
    assert contrast_ratio((128, 128, 128), (128, 128, 128)) == pytest.approx(1.0, rel=1e-6)
    # Pure primaries on black: (L + 0.05) / 0.05 with L = 0.2126 / 0.7152 / 0.0722.
    assert contrast_ratio((255, 0, 0), (0, 0, 0)) == pytest.approx(5.252, rel=1e-3)
    assert contrast_ratio((0, 255, 0), (0, 0, 0)) == pytest.approx(15.304, rel=1e-3)
    assert contrast_ratio((0, 0, 255), (0, 0, 0)) == pytest.approx(2.444, rel=1e-3)
    # Well-known WCAG AA mid-gray: #767676 on white is 4.54:1.
    assert contrast_ratio((118, 118, 118), WHITE) == pytest.approx(4.54, abs=0.02)
    # Okabe-Ito vermillion / blue on white (sRGB piecewise transfer function exercised on both branches).
    assert contrast_ratio((213, 94, 0), WHITE) == pytest.approx(3.87, abs=0.02)
    assert contrast_ratio((0, 114, 178), WHITE) == pytest.approx(5.19, abs=0.02)
    # near-black value on the linear segment of the transfer function (c/255 <= 0.04045)
    assert contrast_ratio((5, 5, 5), (0, 0, 0)) == pytest.approx(1.0 + (5 / 255 / 12.92) / 0.05, rel=1e-3)


# ---------------------------------------------------------------- simulate_cvd (Machado 2009, severity 1.0)

@pytest.mark.parametrize("kind", ["protanopia", "deuteranopia", "tritanopia"])
def test_simulate_cvd_output_format_and_achromatic_invariance(kind):
    for level in (0, 64, 128, 200, 255):
        out = simulate_cvd((level, level, level), kind)
        assert isinstance(out, tuple) and len(out) == 3
        assert all(isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255 for c in out)
        # Machado matrices have row sums 1.0, so greys stay grey.
        assert all(abs(c - level) <= 2 for c in out)


@pytest.mark.parametrize(
    ("kind", "rgb", "expected"),
    [
        ("protanopia", (255, 0, 0), (109, 95, 0)),
        ("protanopia", (0, 255, 0), (255, 229, 0)),
        ("protanopia", (100, 150, 200), (130, 151, 202)),
        ("deuteranopia", (255, 0, 0), (163, 144, 0)),
        ("deuteranopia", (0, 255, 0), (239, 214, 58)),
        ("deuteranopia", (230, 159, 0), (202, 180, 17)),
        ("tritanopia", (0, 0, 255), (0, 107, 150)),
        ("tritanopia", (0, 255, 0), (0, 247, 217)),
        ("tritanopia", (100, 150, 200), (51, 162, 167)),
    ],
)
def test_simulate_cvd_matches_machado_severity_one(kind, rgb, expected):
    out = simulate_cvd(rgb, kind)
    assert all(abs(o - e) <= 3 for o, e in zip(out, expected)), (kind, rgb, out, expected)


def test_simulate_cvd_kinds_differ_and_invalid_kind_raises():
    rgb = (230, 100, 60)
    outs = {simulate_cvd(rgb, k) for k in ("protanopia", "deuteranopia", "tritanopia")}
    assert len(outs) == 3
    with pytest.raises(ValueError):
        simulate_cvd((100, 150, 200), "achromatopsia")


# ---------------------------------------------------------------- check_palette

def test_check_palette_brief_example_flags_only_the_low_contrast_line():
    # Brief example: on (240,240,235) the Okabe-Ito orange has contrast 1.97 (< 3.0), the blue 4.54.
    bg = (240, 240, 235)
    problems = check_palette({"line": (230, 159, 0), "chip": (0, 114, 178)}, bg)
    assert len(problems) == 1
    assert isinstance(problems[0], str)
    assert "line" in problems[0] and "chip" not in problems[0]
    # With a lower bar the same palette is clean (min_ratio and the pair check are both honoured).
    assert check_palette({"line": (230, 159, 0), "chip": (0, 114, 178)}, bg, min_ratio=1.5) == []


def test_check_palette_clean_palette_returns_empty_list_with_defaults():
    bg = (240, 240, 235)
    assert check_palette({"line": (213, 94, 0), "chip": (0, 114, 178)}, bg) == []
    assert check_palette({"line": (213, 94, 0), "chip": (0, 114, 178)}, WHITE) == []
    assert check_palette({}, bg) == []
    assert check_palette({"only": (0, 0, 0)}, bg) == []


def test_check_palette_default_contrast_threshold_is_3():
    # #949494 on white is 3.03:1, #959595 is 2.99:1.
    assert check_palette({"grey": (148, 148, 148)}, WHITE) == []
    problems = check_palette({"grey": (149, 149, 149)}, WHITE)
    assert len(problems) == 1 and "grey" in problems[0]
    # explicit min_ratio overrides the default in both directions
    assert check_palette({"grey": (149, 149, 149)}, WHITE, min_ratio=2.5) == []
    assert len(check_palette({"grey": (148, 148, 148)}, WHITE, min_ratio=3.5)) == 1


def test_check_palette_every_failing_colour_gets_its_own_problem():
    bg = WHITE
    problems = check_palette({"pale_yellow": (240, 228, 66), "pale_blue": (86, 180, 233), "black": (0, 0, 0)}, bg, min_delta_e=0.0)
    assert len(problems) == 2
    assert any("pale_yellow" in p for p in problems) and any("pale_blue" in p for p in problems)
    assert not any("black" in p for p in problems)


def test_check_palette_pair_problem_only_under_deuteranopia():
    # Distinct to normal eyes; delta E under protanopia 46, tritanopia 123, but only 11 under deuteranopia (< 20).
    problems = check_palette({"red_series": (200, 30, 30), "green_series": (30, 170, 30)}, WHITE)
    assert len(problems) >= 1
    assert any("red_series" in m and "green_series" in m for m in problems)
    # Default 20 is the threshold: passes when the bar is lowered under 11.
    assert check_palette({"red_series": (200, 30, 30), "green_series": (30, 170, 30)}, WHITE, min_delta_e=5.0) == []


def test_check_palette_pair_problem_only_under_tritanopia():
    # delta E under protanopia 26, deuteranopia 23, but only 8 under tritanopia (< 20).
    pair = {"sky_blue": (86, 180, 233), "cyan_green": (40, 200, 200)}
    problems = check_palette(pair, WHITE, min_ratio=1.0)
    assert len(problems) >= 1
    assert any("sky_blue" in m and "cyan_green" in m for m in problems)


def test_check_palette_near_identical_pair_fails_and_threshold_is_honoured():
    pair = {"navy_a": (10, 20, 90), "navy_b": (12, 22, 95)}  # delta E 1.5-2.0 under all three simulations
    problems = check_palette(pair, WHITE)
    assert len(problems) >= 1
    assert any("navy_a" in m and "navy_b" in m for m in problems)
    assert check_palette(pair, WHITE, min_delta_e=1.0) == []
    assert len(check_palette(pair, WHITE, min_delta_e=5.0)) >= 1


def test_check_palette_far_apart_pair_has_no_pair_problem():
    assert check_palette({"dark": (0, 0, 0), "light": (255, 255, 255)}, (128, 128, 128), min_ratio=1.0) == []
    # vermillion vs blue stay far apart under every simulation (delta E 90+)
    assert check_palette({"line": (213, 94, 0), "chip": (0, 114, 178)}, WHITE, min_delta_e=80.0) == []
