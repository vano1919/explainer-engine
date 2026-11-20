"""Breath and embers (G-01, `production/fx25d/breath_embers.py`): tests written from the rules of
`final_plan_2026-11-19/gemini_dev/G-01/TASK.md` (interface, limits, determinism, occlusion, wind, far pixels, timing), by a
separate chat from the module's author, before reading the module's text. Small frames keep the many-frame checks fast; the
speed rule is measured on 1280x704. Rule numbers in the test names are the TASK's rule numbers."""

from __future__ import annotations

import random
import time

import numpy as np
import pytest

from explainer_engine.production.fx25d import breath_embers as be

FPS = 24.0
H, W = 176, 320                      # a quarter of the 1280x704 frame, same aspect, all positions scale with it
MOUTH = (160.0, 120.0)
SRC = (60.0, 150.0)


def puff_series(mouths, wind, seed, frames, **kw):
    return [be.breath_alpha((H, W), f, FPS, mouths, wind, seed, **kw) for f in frames]


def ember_series(wind, seed, frames, **kw):
    radius, depth = kw.pop("source_radius_px", 10.0), kw.pop("depth", None)
    return [be.embers_layer((H, W), f, FPS, SRC, radius, wind, depth, seed, **kw) for f in frames]


def mean_x(a):
    s = float(a.sum())
    return float((a.sum(axis=0) * np.arange(a.shape[1])).sum() / s) if s > 0 else None


def mean_y(a):
    s = float(a.sum())
    return float((a.sum(axis=1) * np.arange(a.shape[0])).sum() / s) if s > 0 else None


def width_px(a, thr=1e-6):
    cols = np.where((a > thr).any(axis=0))[0]
    return 0 if len(cols) == 0 else int(cols.max() - cols.min() + 1)


# ---------------------------------------------------------------- interface -------------------------------------------

def test_breath_interface_shape_dtype_range():
    a = be.breath_alpha((H, W), 60, FPS, [MOUTH, (200.0, 100.0)], (0.02, 0.0), 7)
    assert a.shape == (H, W) and a.dtype == np.float32
    assert float(a.min()) >= 0.0 and float(a.max()) <= 0.35 + 1e-6


def test_embers_interface_shape_dtype_range():
    rgb, alpha = be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, 7)
    assert rgb.shape == (H, W, 3) and rgb.dtype == np.float32 and alpha.shape == (H, W) and alpha.dtype == np.float32
    assert float(alpha.min()) >= 0.0 and float(alpha.max()) <= 1.0 and float(rgb.min()) >= 0.0 and float(rgb.max()) <= 255.0


def test_composite_interface_and_none_cases():
    rgb = np.random.default_rng(1).uniform(0, 255, (H, W, 3)).astype(np.float32)
    out = be.composite(rgb, None, None)
    assert out.shape == (H, W, 3) and out.dtype == np.float32 and np.array_equal(out, rgb)
    assert out is not rgb


def test_no_mouths_no_breath():
    a = be.breath_alpha((H, W), 30, FPS, [], (0.02, 0.0), 3)
    assert a.shape == (H, W) and float(a.max()) == 0.0


# ---------------------------------------------------------------- rule 1: breath --------------------------------------

def test_r1_peak_alpha_never_above_035_over_time():
    peak = max(float(a.max()) for a in puff_series([MOUTH], (0.0, 0.0), 5, range(0, 24 * 12, 3)))
    assert 0.0 < peak <= 0.35 + 1e-6               # a puff exists, and none is above the cap


def test_r1_plume_never_wider_than_size_share_and_size_share_is_the_knob():
    for share in (0.04, 0.06):
        widest = max(width_px(a) for a in puff_series([MOUTH], (0.0, 0.0), 5, range(0, 24 * 12, 2), size_share=share))
        assert 0.6 * share * W <= widest <= share * W + 1, (share, widest)   # reaches its size, never beyond it
    wide = max(width_px(a) for a in puff_series([MOUTH], (0.0, 0.0), 5, range(0, 24 * 12, 2), size_share=0.08))
    assert wide > 0.04 * W + 1                      # a larger share really allows a larger plume


def test_r1_alpha_is_smooth_no_hard_edges():
    worst = 0.0
    for a in puff_series([MOUTH, (240.0, 90.0)], (0.02, 0.0), 9, range(0, 24 * 10, 2)):
        worst = max(worst, float(np.abs(np.diff(a, axis=1)).max()), float(np.abs(np.diff(a, axis=0)).max()))
    assert worst <= 0.15, worst


def puff_runs(wind=(0.0, 0.0), seed=11, seconds=40, mouths=None, **kw):
    """(start_frame, end_frame) of every stretch where the vapour alpha is visible, for one mouth, plus the series."""
    frames = range(int(seconds * FPS))
    ser = puff_series(mouths or [MOUTH], wind, seed, frames, **kw)
    vis = [float(a.max()) > 0.004 for a in ser]
    runs, start = [], None
    for f, v in enumerate(vis):
        if v and start is None:
            start = f
        if not v and start is not None:
            runs.append((start, f - 1))
            start = None
    return runs, ser


def test_r1_a_puff_lives_about_one_and_a_half_seconds_and_comes_every_three_to_four():
    runs, _ = puff_runs()
    inner = [r for r in runs if r[0] > 0]            # frame 0 may hold a puff already in flight
    assert len(inner) >= 8, runs
    starts = [r[0] / FPS for r in inner]
    gaps = np.diff(starts)
    assert gaps.min() >= 3.0 - 2 / FPS and gaps.max() <= 4.0 + 2 / FPS, gaps
    lengths = [(r[1] - r[0] + 1) / FPS for r in inner]
    assert 1.0 <= min(lengths) and max(lengths) <= 2.0, lengths      # "about 1.5 s"


def test_r1_interval_argument_is_honoured():
    runs, _ = puff_runs(seconds=30, interval_s=(6.0, 7.0))
    starts = [r[0] / FPS for r in runs if r[0] > 0]
    assert len(starts) >= 3 and 6.0 - 2 / FPS <= min(np.diff(starts)) and max(np.diff(starts)) <= 7.0 + 2 / FPS


def test_r1_a_puff_rises_widens_and_fades():
    runs, ser = puff_runs()
    a, b = next(r for r in runs if r[0] > 0)
    ys = [mean_y(ser[f]) for f in range(a, b + 1)]
    ws = [width_px(ser[f]) for f in range(a, b + 1)]
    tot = [float(ser[f].sum()) for f in range(a, b + 1)]
    assert ys[-1] < ys[0] - 0.5, ys                  # rises (image y decreases)
    assert ws[-1] > ws[0] or max(ws) > ws[0], ws     # widens
    assert tot[-1] < max(tot), tot                   # fades at the end of its life


def test_r1_mouths_do_not_all_puff_at_the_same_moment():
    mouths = [(40.0, 100.0), (120.0, 100.0), (200.0, 100.0), (280.0, 100.0)]
    ser = puff_series(mouths, (0.0, 0.0), 21, range(int(30 * FPS)))
    columns = [(m[0] - 30, m[0] + 30) for m in mouths]
    starts = []
    for lo, hi in columns:
        vis = [bool((a[:, int(lo):int(hi)] > 0.004).any()) for a in ser]
        starts.append(tuple(f for f in range(1, len(vis)) if vis[f] and not vis[f - 1]))
    assert all(len(s_) >= 6 for s_ in starts), starts
    assert len(set(starts)) == len(starts), starts           # no two mouths puff at exactly the same moments
    assert len({s_[0] for s_ in starts}) > 1, starts          # and the first puffs are not all together


def test_r1_frame_zero_may_hold_a_puff_in_flight_but_is_valid():
    ok = [be.breath_alpha((H, W), 0, FPS, [MOUTH], (0.0, 0.0), s) for s in range(1, 12)]
    assert all(a.shape == (H, W) and a.max() <= 0.35 + 1e-6 for a in ok)


def test_r1_the_seed_changes_when_the_puffs_come():
    sched = {seed: tuple(r[0] for r in puff_runs(seed=seed, seconds=20)[0]) for seed in (1, 2, 3, 4)}
    assert len(set(sched.values())) >= 3, sched


def test_r1_stacked_mouths_never_exceed_the_peak_cap():
    mouths = [MOUTH] * 12
    peak = max(float(a.max()) for a in puff_series(mouths, (0.0, 0.0), 3, range(0, 24 * 10, 2)))
    assert 0.0 < peak <= 0.35 + 1e-6, peak


# ---------------------------------------------------------------- rule 2: embers --------------------------------------

def test_r2_embers_are_warm_orange_to_red():
    rgb, alpha = be.embers_layer((H, W), 40, FPS, SRC, 10.0, (0.0, 0.0), None, 4)
    m = alpha > 0
    assert m.any()
    r, g, b = rgb[..., 0][m], rgb[..., 1][m], rgb[..., 2][m]
    assert (r >= g - 1e-3).all() and (g >= b - 1e-3).all() and float(r.max()) >= 150.0 and float(np.median(b)) <= 120.0


def test_r2_embers_are_sparse_at_every_frame():
    """On the real 1280x704 frame (the TASK's size); ember size is in pixels, so a quarter-size frame is not the rule's frame."""
    def worst(count):
        return max(float((be.embers_layer((704, 1280), f, FPS, (180.0, 560.0), 40.0, (0.02, 0.0), None, 6, count=count)[1] > 0).mean())
                   for f in range(0, 24 * 8, 6))
    w = worst(60)
    assert 0.0 < w < 0.02, w


def test_r2_count_scales_how_many_embers_there_are():
    few = np.mean([float(a.sum()) for _, a in ember_series((0.0, 0.0), 8, range(48, 120, 6), count=5)])
    many = np.mean([float(a.sum()) for _, a in ember_series((0.0, 0.0), 8, range(48, 120, 6), count=60)])
    assert many > few > 0.0
    zero = ember_series((0.0, 0.0), 8, [60], count=0)[0]
    assert float(zero[1].max()) == 0.0


def test_r2_one_ember_lives_one_to_three_seconds_rises_and_fades():
    ser = ember_series((0.0, 0.0), 13, range(0, int(14 * FPS)), count=1)
    vis = [float(a.max()) > 0.004 for _, a in ser]
    runs, start = [], None
    for f, v in enumerate(vis):
        if v and start is None:
            start = f
        if not v and start is not None:
            runs.append((start, f - 1))
            start = None
    inner = [r for r in runs if r[0] > 0]
    assert len(inner) >= 3, runs
    for a, b in inner:
        life = (b - a + 1) / FPS
        assert 1.0 - 2 / FPS <= life <= 3.0 + 2 / FPS, (a, b, life)
    a, b = inner[0]
    ys = [mean_y(ser[f][1]) for f in range(a, b + 1)]
    al = [float(ser[f][1].max()) for f in range(a, b + 1)]
    assert ys[-1] < ys[0], ys                        # rises
    assert al[-1] < max(al), al                      # fades while rising


def test_r2_the_seed_changes_when_embers_are_born():
    def births(seed):
        ser = ember_series((0.0, 0.0), seed, range(0, int(14 * FPS)), count=1)
        vis = [float(a.max()) > 0.004 for _, a in ser]
        return tuple(f for f in range(1, len(vis)) if vis[f] and not vis[f - 1])
    assert len({births(sd) for sd in (1, 2, 3, 4)}) >= 3


def test_r2_embers_start_around_the_source():
    # a young ember (the first frames of a run) sits within the radius plus a small sway around the source
    ser = ember_series((0.0, 0.0), 13, range(0, int(14 * FPS)), count=1, source_radius_px=15.0)
    for f in range(1, len(ser)):
        was, now = float(ser[f - 1][1].max()) > 0.004, float(ser[f][1].max()) > 0.004
        if now and not was:
            x, y = mean_x(ser[f][1]), mean_y(ser[f][1])
            assert abs(x - SRC[0]) <= 15.0 + 12.0 and abs(y - SRC[1]) <= 15.0 + 12.0, (f, x, y)


# ---------------------------------------------------------------- rule 3: occlusion -----------------------------------

def test_r3_depth_above_ember_depth_hides_the_ember():
    frames = range(40, 100, 7)
    free = ember_series((0.0, 0.0), 2, frames)
    full = np.ones((H, W), np.float32)
    hid = ember_series((0.0, 0.0), 2, frames, depth=full)
    assert max(float(a.max()) for _, a in free) > 0.0
    assert all(float(a.max()) == 0.0 for _, a in hid)


def test_r3_depth_at_or_below_ember_depth_leaves_the_ember():
    frames = range(40, 100, 7)
    free = ember_series((0.0, 0.0), 2, frames)
    for d in (0.0, 0.5):                              # equal to ember_depth is not "greater than"
        same = ember_series((0.0, 0.0), 2, frames, depth=np.full((H, W), d, np.float32))
        for (r0, a0), (r1, a1) in zip(free, same):
            assert np.array_equal(a0, a1) and np.array_equal(r0, r1)


def test_r3_occlusion_is_per_pixel_and_only_where_something_nearer_stands():
    frames = range(40, 100, 7)
    free = ember_series((0.0, 0.0), 2, frames)
    depth = np.zeros((H, W), np.float32)
    depth[:, : W // 2] = 1.0
    part = ember_series((0.0, 0.0), 2, frames, depth=depth)
    for (_, a0), (_, a1) in zip(free, part):
        assert float(a1[:, : W // 2].max()) == 0.0
        assert np.array_equal(a1[:, W // 2:], a0[:, W // 2:])


def test_r3_ember_depth_threshold_argument_is_honoured():
    frames = range(40, 100, 7)
    depth = np.full((H, W), 0.6, np.float32)
    hidden = ember_series((0.0, 0.0), 2, frames, depth=depth, ember_depth=0.5)
    shown = ember_series((0.0, 0.0), 2, frames, depth=depth, ember_depth=0.7)
    assert all(float(a.max()) == 0.0 for _, a in hidden) and max(float(a.max()) for _, a in shown) > 0.0


# ---------------------------------------------------------------- rule 4: no global change ----------------------------

def test_r4_breath_far_pixels_have_alpha_exactly_zero():
    reach = 4 * 0.04 * W
    yy, xx = np.mgrid[0:H, 0:W]
    far = np.hypot(xx - MOUTH[0], yy - MOUTH[1]) > reach
    assert far.any()
    for a in puff_series([MOUTH], (0.0, 0.0), 5, range(0, 24 * 12, 3)):
        assert float(a[far].max()) == 0.0


def test_r4_breath_far_from_every_mouth_with_wind():
    mouths = [(40.0, 60.0), (280.0, 60.0)]
    reach = 4 * 0.04 * W + 0.05 * W * 2.0           # four times the plume plus the drift of one puff's life
    yy, xx = np.mgrid[0:H, 0:W]
    near = np.zeros((H, W), bool)
    for mx, my in mouths:
        near |= np.hypot(xx - mx, yy - my) <= reach
    far = ~near
    assert far.any()
    for a in puff_series(mouths, (0.05, 0.0), 5, range(0, 24 * 12, 3)):
        assert float(a[far].max()) == 0.0


def test_r4_embers_far_pixels_have_alpha_zero():
    yy, xx = np.mgrid[0:H, 0:W]
    far = np.hypot(xx - SRC[0], yy - SRC[1]) > 0.5 * float(np.hypot(H, W))
    assert far.any()
    for _, a in ember_series((0.0, 0.0), 6, range(0, 24 * 8, 4)):
        assert float(a[far].max()) == 0.0


def test_r4_composite_leaves_far_pixels_unchanged():
    rgb = np.random.default_rng(2).uniform(0, 255, (H, W, 3)).astype(np.float32)
    br = be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.0, 0.0), 5)
    em = be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.0, 0.0), None, 5)
    out = be.composite(rgb, br, em)
    touched = (br > 0) | (em[1] > 0)
    assert touched.any() and np.array_equal(out[~touched], rgb[~touched])


# ---------------------------------------------------------------- rule 5: determinism ---------------------------------

def test_r5_same_arguments_same_pixels_and_other_seed_other_pixels():
    args = ((H, W), 60, FPS, [MOUTH, (200.0, 100.0)], (0.02, 0.0))
    a1, a2 = be.breath_alpha(*args, 7), be.breath_alpha(*args, 7)
    assert np.array_equal(a1, a2)
    assert any(not np.array_equal(be.breath_alpha((H, W), f, FPS, [MOUTH, (200.0, 100.0)], (0.02, 0.0), 8),
                                  be.breath_alpha((H, W), f, FPS, [MOUTH, (200.0, 100.0)], (0.02, 0.0), 7))
               for f in range(30, 130, 10))
    e = lambda seed: be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, seed)       # noqa: E731
    (r1, b1), (r2, b2), (r3, b3) = e(7), e(7), e(8)
    assert np.array_equal(r1, r2) and np.array_equal(b1, b2)
    assert not (np.array_equal(r1, r3) and np.array_equal(b1, b3))


def test_r5_a_frame_does_not_depend_on_which_frames_were_drawn_before():
    a = be.breath_alpha((H, W), 100, FPS, [MOUTH], (0.02, 0.0), 3)
    for f in (5, 99, 100, 7):
        be.breath_alpha((H, W), f, FPS, [MOUTH], (0.02, 0.0), 3)
    assert np.array_equal(a, be.breath_alpha((H, W), 100, FPS, [MOUTH], (0.02, 0.0), 3))
    e = be.embers_layer((H, W), 100, FPS, SRC, 10.0, (0.02, 0.0), None, 3)
    be.embers_layer((H, W), 3, FPS, SRC, 10.0, (0.02, 0.0), None, 3)
    assert np.array_equal(e[1], be.embers_layer((H, W), 100, FPS, SRC, 10.0, (0.02, 0.0), None, 3)[1])


def test_r5_global_random_state_is_never_used_and_never_touched(monkeypatch):
    np_state, py_state = np.random.get_state(), random.getstate()
    be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.02, 0.0), 7)
    be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, 7)
    new_np = np.random.get_state()
    assert py_state == random.getstate() and new_np[0] == np_state[0] and np.array_equal(new_np[1], np_state[1]) and new_np[2:] == np_state[2:]
    np.random.seed(123)
    first = be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, 7)[1], be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.02, 0.0), 7)
    np.random.seed(999)
    random.seed(5)
    second = be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, 7)[1], be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.02, 0.0), 7)
    assert np.array_equal(first[0], second[0]) and np.array_equal(first[1], second[1])


def test_r5_the_clock_is_never_read(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("the clock was read")
    for name in ("time", "time_ns", "monotonic", "monotonic_ns"):
        monkeypatch.setattr(time, name, boom)
    be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.02, 0.0), 7)
    be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.02, 0.0), None, 7)


# ---------------------------------------------------------------- rule 6: wind ----------------------------------------

def test_r6_embers_drift_with_the_wind_direction():
    frames = range(36, 144, 4)

    def mx(wind):
        s = [mean_x(a) for _, a in ember_series(wind, 10, frames, count=60) if float(a.sum()) > 0]
        return float(np.mean(s))
    right, still, left = mx((0.05, 0.0)), mx((0.0, 0.0)), mx((-0.05, 0.0))
    assert right > still + 2.0 and left < still - 2.0, (left, still, right)


def test_r6_without_wind_the_embers_have_only_sway():
    frames = range(36, 144, 4)
    s = [mean_x(a) for _, a in ember_series((0.0, 0.0), 10, frames, count=60) if float(a.sum()) > 0]
    assert abs(np.mean(s) - SRC[0]) <= 0.1 * W, np.mean(s)


def test_r6_plumes_drift_with_the_wind_direction():
    frames = range(0, 24 * 20, 2)

    def mx(wind):
        return float(np.mean([mean_x(a) for a in puff_series([MOUTH], wind, 5, frames) if float(a.sum()) > 0]))
    right, still, left = mx((0.05, 0.0)), mx((0.0, 0.0)), mx((-0.05, 0.0))
    assert right > still + 2.0 and left < still - 2.0, (left, still, right)


def test_r6_one_puff_moves_right_over_its_life_with_wind_right_and_not_without():
    runs, ser = puff_runs(wind=(0.05, 0.0))
    a, b = next(r for r in runs if r[0] > 0)
    assert mean_x(ser[b]) > mean_x(ser[a]) + 1.0
    runs0, ser0 = puff_runs(wind=(0.0, 0.0))
    a0, b0 = next(r for r in runs0 if r[0] > 0)
    assert abs(mean_x(ser0[b0]) - mean_x(ser0[a0])) < 0.5 * (mean_x(ser[b]) - mean_x(ser[a]))


# ---------------------------------------------------------------- composite -------------------------------------------

def test_composite_vapour_lightens_towards_grey_white_and_never_darkens():
    dark = np.zeros((H, W, 3), np.float32)
    br = np.zeros((H, W), np.float32)
    br[50:60, 50:60] = 0.3
    out = be.composite(dark, br, None)
    px = out[55, 55]
    assert 0.0 < px.min() and px.max() <= 255.0 and (px.max() - px.min()) <= 0.1 * px.max()   # grey-white: the channels agree within 10 %
    assert np.array_equal(out[br == 0], dark[br == 0])
    bright = np.full((H, W, 3), 255.0, np.float32)
    assert float(be.composite(bright, br, None).max()) <= 255.0
    mid = np.full((H, W, 3), 100.0, np.float32)
    assert (be.composite(mid, br, None) >= mid).all()


def test_composite_embers_are_screen_light_and_never_above_255():
    rgb_e = np.zeros((H, W, 3), np.float32)
    rgb_e[..., 0], rgb_e[..., 1], rgb_e[..., 2] = 255.0, 120.0, 20.0
    al = np.zeros((H, W), np.float32)
    al[30:40, 30:40] = 1.0
    base = np.full((H, W, 3), 80.0, np.float32)
    out = be.composite(base, None, (rgb_e, al))
    assert (out >= base).all() and (out[35, 35] > base[35, 35]).all()
    assert np.array_equal(out[al == 0], base[al == 0])
    assert float(be.composite(np.full((H, W, 3), 255.0, np.float32), None, (rgb_e, al)).max()) <= 255.0
    assert float(be.composite(np.full((H, W, 3), 250.0, np.float32), be.breath_alpha((H, W), 60, FPS, [MOUTH], (0, 0), 5),
                              (rgb_e, al)).max()) <= 255.0


def test_composite_ember_alpha_scales_the_light_and_it_is_a_screen():
    rgb_e = np.zeros((H, W, 3), np.float32)
    rgb_e[..., 0], rgb_e[..., 1], rgb_e[..., 2] = 255.0, 120.0, 20.0
    base = np.full((H, W, 3), 80.0, np.float32)
    outs = {}
    for a in (0.25, 0.5, 1.0):
        al = np.zeros((H, W), np.float32)
        al[30:40, 30:40] = a
        outs[a] = be.composite(base, None, (rgb_e, al))[35, 35]
        light = rgb_e[35, 35] * a
        screen = 255.0 - (255.0 - 80.0) * (255.0 - light) / 255.0
        assert np.allclose(outs[a], screen, rtol=1e-3, atol=0.5), (a, outs[a], screen)
    assert (outs[0.25] < outs[0.5]).all() and (outs[0.5] < outs[1.0]).all() and (outs[0.25] > 80.0).all()


def test_composite_does_not_modify_its_inputs():
    rgb = np.full((H, W, 3), 90.0, np.float32)
    keep = rgb.copy()
    br = be.breath_alpha((H, W), 60, FPS, [MOUTH], (0.0, 0.0), 5)
    em = be.embers_layer((H, W), 60, FPS, SRC, 10.0, (0.0, 0.0), None, 5)
    br_keep, em_keep = br.copy(), (em[0].copy(), em[1].copy())
    be.composite(rgb, br, em)
    assert np.array_equal(rgb, keep) and np.array_equal(br, br_keep) and np.array_equal(em[0], em_keep[0]) and np.array_equal(em[1], em_keep[1])


def test_composite_task_example():
    Hh, Ww = 704, 1280
    a = be.breath_alpha((Hh, Ww), 60, 24.0, [(300.0, 280.0), (520.0, 300.0)], (0.02, 0.0), 7)
    assert a.shape == (Hh, Ww) and a.dtype == np.float32 and 0.0 <= a.min() and a.max() <= 0.35
    rgb_e, alpha_e = be.embers_layer((Hh, Ww), 60, 24.0, (180.0, 560.0), 40.0, (0.02, 0.0), None, seed=7)
    assert rgb_e.shape == (Hh, Ww, 3) and alpha_e.shape == (Hh, Ww) and (alpha_e > 0).mean() < 0.02
    out = be.composite(np.zeros((Hh, Ww, 3), np.float32), a, (rgb_e, alpha_e))
    assert out.shape == (Hh, Ww, 3) and out.max() <= 255.0


# ---------------------------------------------------------------- rule 7: speed ---------------------------------------

def best_of(fn, n=5):
    t = []
    for _ in range(n):
        s = time.perf_counter()
        fn()
        t.append(time.perf_counter() - s)
    return min(t)


def test_r7_one_full_frame_under_a_hundred_and_fifty_milliseconds():
    shape = (704, 1280)
    mouths = [(300.0, 280.0), (520.0, 300.0), (700.0, 290.0), (900.0, 310.0)]
    assert best_of(lambda: be.breath_alpha(shape, 60, 24.0, mouths, (0.02, 0.0), 7)) < 0.15
    assert best_of(lambda: be.embers_layer(shape, 60, 24.0, (180.0, 560.0), 40.0, (0.02, 0.0), None, 7, count=60)) < 0.15
