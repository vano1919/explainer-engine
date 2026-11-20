"""Acceptance tests of task G-01 (the Gemini code lane's pilot): ``explainer_engine/production/fx25d/breath_embers.py`` (tester, 2026-11-20).

Written BEFORE the code and BEFORE Gemini sees the task, from TASK.md only. Black box: every test calls ``breath_alpha``, ``embers_layer`` or
``composite`` and measures the arrays they return; nothing here knows how a puff or an ember is drawn, how time is turned into a position, or how the
random numbers are made, so any implementation that obeys the numbered rules of TASK.md passes. Where TASK.md leaves a freedom (do the embers respawn
or live once? is the first puff already in flight? how fast does a puff rise?) the test is written so that both readings pass.

Rule map (TASK.md "Rules the code must follow"): 1 breath = the ``test_breath_*`` tests; 2 embers = ``test_embers_*``; 3 occlusion =
``test_embers_occlusion_*``; 4 no global change = ``test_*_far_pixels_are_exactly_zero``, ``test_composite_leaves_far_pixels_unchanged``;
5 determinism = ``test_*_deterministic*``, ``test_no_global_random_state_and_no_clock``; 6 wind = ``test_*_wind_*``; 7 speed = ``test_speed_*``.
Tolerances are stated next to each assertion and are loose enough for a correct implementation (the intervals are measured at a threshold crossing,
so they carry a few tenths of a second of slack) and tight enough to fail a stub, a flat grey blob, a synchronised stub and a global haze.
numpy only; $0; the slowest test draws 4 s at 1280x704."""
from __future__ import annotations

import random
import time

import numpy as np
import pytest

BE = pytest.importorskip("explainer_engine.production.fx25d.breath_embers", reason="G-01 code (Gemini lane PR) is not merged yet")

TINY, SMALL, BIG = (176, 320), (352, 640), (704, 1280)          # (H, W)
EPS = 1e-5


# ---------------------------------------------------------------------------------------------------------------- helpers
def breath(shape, frame, fps=24.0, mouths=((0.5, 0.75),), wind=(0.0, 0.0), seed=3, **kw):
    """``mouths`` given as shares of (W, H) for readability; handed over in pixels."""
    h, w = shape
    px = [(m[0] * w, m[1] * h) for m in mouths]
    return BE.breath_alpha(shape, frame, fps, px, wind, seed, **kw)


def mass_series(shape, seconds, fps, **kw):
    n = int(seconds * fps)
    return [breath(shape, i, fps, **kw) for i in range(n)]


def window_mass(frames, shape, mouth_share, fps):
    """Alpha mass per frame inside a tall column above one mouth (no other mouth is inside it)."""
    h, w = shape
    x0, x1 = int((mouth_share[0] - 0.09) * w), int((mouth_share[0] + 0.09) * w)
    y0, y1 = int((mouth_share[1] - 0.45) * h), int((mouth_share[1] + 0.05) * h)
    return np.array([float(f[y0:y1, x0:x1].sum()) for f in frames])


def onsets(mass, fps):
    """Times (s) at which a puff appears: the mass crosses 6 % of its maximum after having been under 2 % of it (hysteresis)."""
    m = np.asarray(mass, np.float64)
    if m.max() <= 0:
        return []
    hi, lo = 0.06 * m.max(), 0.02 * m.max()
    out, quiet = [], m[0] <= hi                                                    # a puff already in flight at frame 0 is not an onset (TASK.md rule 1)
    for i, v in enumerate(m):
        if quiet and v > hi:
            out.append(i / fps)
            quiet = False
        elif not quiet and v < lo:
            quiet = True
    return out


def centroid(a):
    s = float(a.sum())
    if s <= 0:
        return None
    ys, xs = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    return float((a * xs).sum() / s), float((a * ys).sum() / s), float(np.sqrt((a * (xs - (a * xs).sum() / s) ** 2).sum() / s))


def mouth_grid(shape, n=4):
    xs = np.linspace(0.2, 0.8, n)
    return tuple((float(x), 0.75) for x in xs)


def embers(shape, frame, fps=24.0, source=(0.3, 0.8), radius=15.0, wind=(0.0, 0.0), depth=None, seed=7, **kw):
    h, w = shape
    return BE.embers_layer(shape, frame, fps, (source[0] * w, source[1] * h), radius, wind, depth, seed, **kw)


def ember_blob_track(shape, seconds, fps, **kw):
    """Follow ONE ember (count=1): per frame (visible, x, y). An ember is visible while its peak alpha is at least 15 % of its strongest frame (a
    fading tail does not count; embers may differ in size, so the peak and not the mass is used); a life ends at a gap in visibility or at a jump of the blob by more than 2.5 % of the width in one frame (a
    respawn at the source). Both readings of TASK.md (respawn forever, or a new ember after the old one died) give the same lives."""
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w]
    data = []
    for i in range(int(seconds * fps)):
        _, a = embers(shape, i, fps, count=1, **kw)
        s = float(a.sum())
        data.append((float(a.max()), float((a * xs).sum() / s) if s > 0 else 0.0, float((a * ys).sum() / s) if s > 0 else 0.0))
    top = max(d[0] for d in data)
    rows = [(d[0] >= max(0.02, 0.15 * top), d[1], d[2]) for d in data]
    lives, cur = [], []
    for i, (vis, x, y) in enumerate(rows):
        if not vis:
            if cur:
                lives.append(cur)
                cur = []
            continue
        if cur and (abs(x - cur[-1][1]) > 0.025 * w or abs(y - cur[-1][2]) > 0.025 * w):
            lives.append(cur)
            cur = []
        cur.append((i / fps, x, y))
    if cur:
        lives.append(cur)
    return rows, lives


# ===================================================================================================== rule 1: breath
@pytest.mark.parametrize("shape", [TINY, SMALL, (233, 411)])
def test_breath_returns_float32_alpha_of_the_frame_shape_in_range(shape):
    for f in (0, 17, 90):
        a = breath(shape, f, mouths=mouth_grid(shape))
        assert isinstance(a, np.ndarray) and a.dtype == np.float32 and a.shape == shape
        assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0


def test_breath_without_a_mouth_is_exactly_zero():
    for f in (0, 5, 200):
        assert not breath(SMALL, f, mouths=()).any()


def test_breath_draws_something_a_stub_that_returns_zeros_fails():
    frames = mass_series(SMALL, 4.5, 24.0, mouths=mouth_grid(SMALL))
    assert max(float(f.max()) for f in frames) >= 0.05, "no puff of any strength in 4.5 s with four mouths"
    assert sum(1 for f in frames if f.max() >= 0.05) >= 12, "puffs must last (more than half a second in total)"


def test_breath_peak_alpha_never_above_035():
    peaks = []
    for seed in (1, 2, 3):
        peaks += [float(f.max()) for f in mass_series(SMALL, 12.0, 12.0, mouths=mouth_grid(SMALL), seed=seed)]
    assert max(peaks) <= 0.35 + EPS, max(peaks)
    assert max(peaks) >= 0.05


@pytest.mark.parametrize("shape,seconds", [(SMALL, 5.0), (BIG, 4.0)])
def test_breath_is_smooth_no_step_over_015_between_neighbours(shape, seconds):
    step = 0.15 + EPS
    seen = False
    for i in range(0, int(seconds * 24), 2):
        a = breath(shape, i, mouths=mouth_grid(shape))
        if a.max() > 0:
            seen = True
            assert np.abs(np.diff(a, axis=1)).max() <= step and np.abs(np.diff(a, axis=0)).max() <= step, i
    assert seen


@pytest.mark.parametrize("fps", [12.0, 24.0])
def test_breath_each_mouth_puffs_every_3_to_4_seconds(fps):
    shape, mouths = TINY, mouth_grid(TINY)
    frames = mass_series(shape, 28.0, fps, mouths=mouths, seed=11)
    for m in mouths:
        t = onsets(window_mass(frames, shape, m, fps), fps)
        assert len(t) >= 5, (m, t)
        gaps = np.diff(t)
        assert gaps.min() >= 3.0 - 0.45 and gaps.max() <= 4.0 + 0.45, (m, np.round(gaps, 2))     # 0.45 s of threshold slack
        assert 3.0 - 0.15 <= gaps.mean() <= 4.0 + 0.15, (m, gaps.mean())


def test_breath_interval_argument_is_used():
    shape, fps, mouths = TINY, 12.0, mouth_grid(TINY, 2)
    frames = mass_series(shape, 44.0, fps, mouths=mouths, seed=5, interval_s=(5.0, 6.0))
    for m in mouths:
        gaps = np.diff(onsets(window_mass(frames, shape, m, fps), fps))
        assert len(gaps) >= 4 and gaps.min() >= 5.0 - 0.45 and gaps.max() <= 6.0 + 0.45 and 5.0 - 0.15 <= gaps.mean() <= 6.0 + 0.15, np.round(gaps, 2)


def test_breath_the_mouths_do_not_puff_in_step():
    shape, fps, mouths = TINY, 12.0, mouth_grid(TINY)
    spans = []
    for seed in (21, 22, 23):
        frames = mass_series(shape, 28.0, fps, mouths=mouths, seed=seed)
        ons = [onsets(window_mass(frames, shape, m, fps), fps) for m in mouths]
        together = [t for t in ons[0] if all(any(abs(t - u) <= 0.3 for u in o) for o in ons[1:])]
        assert len(together) < 0.5 * len(ons[0]), (seed, ons)                       # a synchronised stub scores 1.0
        spans.append(max(o[0] for o in ons) - min(o[0] for o in ons))
    assert sum(1 for s in spans if s >= 0.2) >= 2, spans


def test_breath_a_puff_rises_widens_and_fades_over_about_a_second_and_a_half():
    shape, fps = SMALL, 24.0
    frames = mass_series(shape, 12.0, fps, mouths=((0.5, 0.75),), seed=4)
    ons = onsets([float(f.sum()) for f in frames], fps)
    assert len(ons) >= 2
    t0 = ons[1]                                                                    # the first one may be a puff already in flight
    at = lambda dt: frames[int(round((t0 + dt) * fps))]                           # noqa: E731
    c_early, c_late = centroid(at(0.3)), centroid(at(1.0))
    assert c_early and c_late
    assert c_late[1] < c_early[1] - 0.5, "the puff must rise (y decreases)"
    assert c_late[2] > c_early[2], "the puff must widen"
    peak = max(float(at(d).sum()) for d in np.arange(0.0, 1.6, 0.1))
    assert float(at(2.4).sum()) <= 0.25 * peak, "the puff must be gone (faded) well before the next one"


def test_breath_a_puff_lives_about_one_and_a_half_seconds():
    """TASK.md: rises, widens and fades over about 1.5 s. Visible time = frames whose alpha mass is above 6 % of the puff's maximum."""
    shape, fps = SMALL, 24.0
    frames = mass_series(shape, 14.0, fps, mouths=((0.5, 0.75),), seed=6)
    mass = np.array([float(f.sum()) for f in frames])
    ons = onsets(mass, fps)
    assert len(ons) >= 3
    t0, t1 = ons[1], ons[2]                                                        # a whole puff and the quiet after it
    seg = mass[int(round(t0 * fps)): int(round(t1 * fps))]
    visible = float((seg >= 0.06 * mass.max()).sum()) / fps
    assert 0.8 <= visible <= 2.2, visible
    assert float(seg[int(round(2.3 * fps))]) <= 0.06 * mass.max(), "the puff must be gone 2.3 s after it appeared"


@pytest.mark.parametrize("share", [0.04, 0.08])
def test_breath_plume_is_at_most_size_share_of_the_width(share):
    shape = SMALL
    frames = mass_series(shape, 8.0, 12.0, mouths=((0.5, 0.75),), seed=8, size_share=share)
    widest = 0
    for f in frames:
        cols = np.flatnonzero((f >= 0.05).any(axis=0))
        if len(cols):
            widest = max(widest, cols[-1] - cols[0] + 1)
    assert widest <= share * shape[1] * 1.25, (widest, share * shape[1])
    assert widest >= share * shape[1] * 0.25, "the plume must be visible, not a dot"


def test_breath_size_share_scales_the_plume():
    def widest(share):
        best = 0
        for f in mass_series(SMALL, 8.0, 12.0, mouths=((0.5, 0.75),), seed=8, size_share=share):
            cols = np.flatnonzero((f >= 0.05).any(axis=0))
            best = max(best, (cols[-1] - cols[0] + 1) if len(cols) else 0)
        return best
    assert widest(0.08) >= 1.3 * widest(0.04)


# ------------------------------------------------------------------------------------------------------- rule 4 (breath)
def test_breath_far_pixels_are_exactly_zero():
    shape, mouths = SMALL, mouth_grid(SMALL)
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w]
    near = np.zeros(shape, bool)
    for mx, my in mouths:
        near |= np.hypot(xs - mx * w, ys - my * h) <= 4 * 0.04 * w
    seen = False
    for i in range(0, 200, 3):
        a = breath(shape, i, mouths=mouths, wind=(0.03, 0.0))
        seen |= bool(a.max() > 0)
        assert not a[~near].any(), f"frame {i}: alpha away from every mouth (4 x the plume) must be exactly 0"
    assert seen


# ------------------------------------------------------------------------------------------------------- rule 6 (breath)
@pytest.mark.parametrize("wind_x,sign", [(0.06, 1), (-0.06, -1)])
def test_breath_plume_drifts_with_the_wind(wind_x, sign):
    shape, fps = SMALL, 24.0
    frames = mass_series(shape, 10.0, fps, mouths=((0.5, 0.75),), seed=4, wind=(wind_x, 0.0))
    t0 = onsets([float(f.sum()) for f in frames], fps)[1]
    c1, c2 = centroid(frames[int(round((t0 + 0.3) * fps))]), centroid(frames[int(round((t0 + 1.0) * fps))])
    expected = abs(wind_x) * shape[1] * 0.7
    assert sign * (c2[0] - c1[0]) >= 0.25 * expected, (c1[0], c2[0], expected)


def test_breath_without_wind_the_plume_does_not_drift_sideways():
    shape, fps = SMALL, 24.0
    frames = mass_series(shape, 10.0, fps, mouths=((0.5, 0.75),), seed=4)
    t0 = onsets([float(f.sum()) for f in frames], fps)[1]
    c1, c2 = centroid(frames[int(round((t0 + 0.3) * fps))]), centroid(frames[int(round((t0 + 1.0) * fps))])
    assert abs(c2[0] - c1[0]) <= 0.01 * shape[1] * 2, (c1[0], c2[0])


# ------------------------------------------------------------------------------------------------------- rule 5 (breath)
def test_breath_is_deterministic_and_seed_sensitive():
    shape, mouths = SMALL, mouth_grid(SMALL)
    differs = False
    for f in range(0, 120, 7):
        a, b = breath(shape, f, mouths=mouths, seed=9), breath(shape, f, mouths=mouths, seed=9)
        assert np.array_equal(a, b)
        differs |= not np.array_equal(a, breath(shape, f, mouths=mouths, seed=10))
    assert differs, "a different seed must change the result"


def test_breath_frames_differ_it_is_animated():
    frames = mass_series(SMALL, 6.0, 24.0, mouths=mouth_grid(SMALL))
    live = [i for i, f in enumerate(frames[:-3]) if f.max() > 0]
    assert live, "no puff in 6 s"
    assert any(not np.array_equal(frames[i], frames[i + 3]) for i in live), "a visible puff must change from frame to frame"


def test_breath_mouths_at_the_border_and_outside_do_not_crash_and_keep_the_contract():
    h, w = SMALL
    for f in (0, 30, 90):
        a = BE.breath_alpha(SMALL, f, 24.0, [(2, 2), (w - 1, h - 1), (-40.0, 10.0), (w + 60.0, h + 60.0), (10, 5)], (0.02, 0.0), 1)
        assert a.shape == SMALL and a.dtype == np.float32 and np.isfinite(a).all() and 0.0 <= a.min() and a.max() <= 0.35 + EPS


# ======================================================================================================= rule 2: embers
@pytest.mark.parametrize("shape", [TINY, SMALL, (233, 411)])
def test_embers_return_rgb_and_alpha_of_the_frame_shape_in_range(shape):
    for f in (0, 11, 70):
        rgb, a = embers(shape, f)
        assert rgb.dtype == np.float32 and rgb.shape == (*shape, 3) and a.dtype == np.float32 and a.shape == shape
        assert np.isfinite(rgb).all() and np.isfinite(a).all()
        assert rgb.min() >= 0.0 and rgb.max() <= 255.0 + 1e-3 and a.min() >= 0.0 and a.max() <= 1.0


def test_embers_draw_something_a_stub_fails():
    best = 0
    for f in range(0, 72, 4):
        _, a = embers(SMALL, f)
        best = max(best, int((a >= 0.2).sum()))
    assert best >= 20, "60 embers must show as at least 20 clearly visible pixels at some frame"


def test_embers_keep_coming_for_as_long_as_the_fire_burns():
    """Embers live 1-3 s each, so a fire that is still burning at 8, 20 or 35 s must still throw embers (new ones are born as old ones die)."""
    for sec in (0.5, 3.4, 8.2, 14.9, 20.3, 27.7, 35.1):
        best = max(int((embers(SMALL, int(sec * 24) + k, 24.0)[1] >= 0.2).sum()) for k in range(0, 12, 3))
        assert best >= 8, f"at {sec} s only {best} clearly visible ember pixels: the embers died and were not replaced"


def test_embers_with_count_zero_draw_nothing():
    for f in (0, 10, 50):
        rgb, a = embers(SMALL, f, count=0)
        assert not a.any() and rgb.shape == (*SMALL, 3)


def test_embers_count_scales_the_layer():
    def mean_mass(count):
        return float(np.mean([embers(SMALL, f, count=count)[1].sum() for f in range(0, 72, 3)]))
    assert mean_mass(120) >= 1.5 * mean_mass(30)


@pytest.mark.parametrize("shape,step", [(SMALL, 3), (BIG, 7)])          # BIG = the real delivery frame 1280x704 (client, 13:28)
def test_embers_cover_under_2_percent_of_the_frame_at_any_frame(shape, step):
    worst = 0.0
    for f in range(0, 240, step):
        _, a = embers(shape, f)
        worst = max(worst, float((a > 0.01).mean()))
    assert worst < 0.02, worst


def test_embers_are_warm_orange_to_red():
    num, den = np.zeros(3), 0.0
    for f in range(0, 72, 3):
        rgb, a = embers(SMALL, f)
        m = a > 0.2
        if m.any():
            num += (rgb[m] * a[m][:, None]).sum(axis=0)
            den += float(a[m].sum())
    assert den > 0
    r, g, b = num / den                                                            # hue only: the rgb may be straight or alpha-weighted
    assert r >= g >= b and (r - b) >= 0.5 * r and b <= 0.6 * g + 1e-6 and g >= 0.1 * r, (r, g, b)


def test_embers_live_between_one_and_three_seconds_rise_and_sway_a_little():
    shape, fps = SMALL, 24.0
    rows, lives = ember_blob_track(shape, 36.0, fps, seed=5)
    assert any(v for v, _, _ in rows[: int(3 * fps)]), "the ember must be visible within the first 3 s"
    spans = [(l[-1][0] - l[0][0] + 1.0 / fps, l) for l in lives]
    assert all(d <= 3.0 + 0.15 for d, _ in spans), [round(d, 2) for d, _ in spans]
    for d, l in spans[1:-1]:                                                           # the first and the last life may be cut by the run
        assert 0.45 <= d, round(d, 2)                                                   # a 1 s life minus its faint start and its faint end
    for d, l in spans:
        if d >= 0.8:
            assert l[-1][2] - l[0][2] <= -0.005 * shape[0], "an ember rises (y decreases)"
            assert abs(l[-1][1] - l[0][1]) <= 0.08 * shape[1], "with no wind the drift is only a small sway"


def test_embers_spread_follows_the_source_radius():
    def spread(radius):
        xs = []
        for f in range(0, 48, 2):
            _, a = embers(SMALL, f, radius=radius, seed=2)
            c = np.flatnonzero((a > 0.05).any(axis=0))
            xs += list(c)
        return float(np.std(xs)) if xs else 0.0
    assert spread(80.0) >= 1.3 * spread(4.0)


# ====================================================================================================== rule 3: occlusion
def depth_map(shape, left_value):
    d = np.zeros(shape, np.float32)
    d[:, : shape[1] // 2] = left_value                                             # the left half is nearer (1 = nearest to the lens)
    return d


def test_embers_occlusion_alpha_is_exactly_zero_where_something_nearer_stands():
    shape = SMALL
    h, w = shape
    depth = depth_map(shape, 0.9)
    free_seen = hidden_without = 0
    for f in range(0, 120, 3):
        _, a = embers(shape, f, source=(0.5, 0.8), radius=40.0, depth=depth, ember_depth=0.5)
        assert not a[depth > 0.5].any(), f"frame {f}: an ember is drawn through a nearer surface"
        free_seen += int((a[:, w // 2:] > 0.05).sum())
        _, free = embers(shape, f, source=(0.5, 0.8), radius=40.0, depth=None)
        hidden_without += int((free[:, : w // 2] > 0.05).sum())
    assert free_seen > 0, "embers must still be drawn on the free half"
    assert hidden_without > 0, "the test is void if the embers never reach the covered half without a depth map"


def test_embers_occlusion_follows_the_ember_depth_argument():
    shape = SMALL
    depth = depth_map(shape, 0.8)
    def left_pixels(ember_depth):
        return sum(int((embers(shape, f, source=(0.5, 0.8), radius=40.0, depth=depth, ember_depth=ember_depth)[1][:, : shape[1] // 2] > 0.05).sum())
                   for f in range(0, 96, 3))
    assert left_pixels(0.5) == 0
    assert left_pixels(0.9) > 0, "depth 0.8 is not nearer than ember_depth 0.9: the embers show"


def test_embers_without_a_depth_map_are_not_occluded():
    _, a = embers(SMALL, 20, depth=None)
    assert a.max() > 0


# ================================================================================================== rule 4: no global change
def test_embers_far_pixels_are_exactly_zero():
    shape = SMALL
    h, w = shape
    sx, sy, radius = 0.2 * w, 0.8 * h, 15.0
    seen = False
    for f in range(0, 240, 4):
        _, a = embers(shape, f, source=(0.2, 0.8), radius=radius)
        seen |= bool(a.max() > 0)
        assert not a[:, int(0.7 * w):].any(), f"frame {f}: alpha far to the right of the fire (no wind)"
        assert not a[int(sy + radius + 0.05 * h):, :].any(), f"frame {f}: an ember below its birth place"
    assert seen


def test_composite_leaves_far_pixels_unchanged_and_never_exceeds_255():
    shape = SMALL
    h, w = shape
    rng = np.random.default_rng(0)
    rgb = rng.uniform(0, 255, (*shape, 3)).astype(np.float32)
    mouths = mouth_grid(shape)
    for f in (10, 40, 70):
        b, e = breath(shape, f, mouths=mouths), embers(shape, f, source=(0.3, 0.8))
        out = BE.composite(rgb, b, e)
        assert out.dtype == np.float32 and out.shape == rgb.shape and np.isfinite(out).all()
        assert out.max() <= 255.0 + 1e-3 and out.min() >= 0.0
        untouched = (b == 0) & (e[1] == 0)
        assert untouched.mean() > 0.5
        assert np.allclose(out[untouched], rgb[untouched], atol=1e-3, rtol=0)
    white = np.full((*shape, 3), 255.0, np.float32)
    for f in range(0, 72, 6):
        assert BE.composite(white, breath(shape, f, mouths=mouths), embers(shape, f, source=(0.3, 0.8))).max() <= 255.0 + 1e-3


def test_composite_with_nothing_returns_the_picture():
    rgb = np.random.default_rng(1).uniform(0, 255, (*TINY, 3)).astype(np.float32)
    out = BE.composite(rgb, None, None)
    assert out.dtype == np.float32 and np.allclose(out, rgb, atol=1e-3)


def test_composite_does_not_change_its_input():
    rgb = np.random.default_rng(2).uniform(0, 255, (*SMALL, 3)).astype(np.float32)
    before = rgb.copy()
    BE.composite(rgb, breath(SMALL, 40, mouths=mouth_grid(SMALL)), embers(SMALL, 40))
    assert np.array_equal(rgb, before)


def test_composite_vapour_is_light_grey_white_and_brightens_a_dark_picture():
    shape = SMALL
    rgb = np.full((*shape, 3), 20.0, np.float32)
    best = None
    for f in range(0, 100, 2):
        b = breath(shape, f, mouths=((0.5, 0.75),), seed=3)
        if best is None or b.max() > best[1].max():
            best = (f, b)
    b = best[1]
    out = BE.composite(rgb, b, None)
    strong = b >= 0.8 * b.max()
    assert b.max() >= 0.1 and strong.any()
    assert (out[strong] >= 20.0 + 100.0 * b[strong][:, None] - 1e-3).all(), "vapour must lighten the picture where it is dense"
    assert (out[strong].max(axis=1) - out[strong].min(axis=1)).max() <= 15.0, "vapour is grey-white, not coloured"


@pytest.mark.parametrize("base", [20.0, 120.0, 200.0])
def test_composite_vapour_is_an_alpha_mix_with_light_grey_white(base):
    """Between mixing in a colour of at least 200 (light grey) and mixing in pure white, in proportion to the alpha, on any background."""
    shape = SMALL
    rgb = np.full((*shape, 3), base, np.float32)
    b = max((breath(shape, f, mouths=((0.5, 0.75),), seed=3) for f in range(0, 100, 4)), key=lambda x: x.max())
    out = BE.composite(rgb, b, None)
    on = b > 0.01
    assert on.any() and b.max() >= 0.1
    a = b[on][:, None]
    lo = (1 - a) * base + a * 200.0 - 1e-2
    hi = (1 - a) * base + a * 255.0 + 1e-2
    assert (out[on] >= lo).all() and (out[on] <= hi).all(), "vapour must be a proportional mix, not a flash to white and not a darkening"


def test_composite_embers_are_screen_light_warm_and_never_darken():
    shape = SMALL
    rgb = np.full((*shape, 3), 40.0, np.float32)
    best = None
    for f in range(0, 72, 2):
        e = embers(shape, f, source=(0.5, 0.8))
        if best is None or e[1].sum() > best[1][1].sum():
            best = (f, e)
    e = best[1]
    out = BE.composite(rgb, None, e)
    bright = e[1] >= 0.5
    assert bright.any()
    assert (out >= rgb - 1e-3).all(), "screen light never darkens"
    assert (out[bright][:, 0] > out[bright][:, 2]).all(), "embers are warm: red above blue"


# =============================================================================================================== rule 5: determinism
def test_embers_deterministic_and_seed_sensitive():
    differs = False
    for f in range(0, 90, 6):
        r1, a1 = embers(SMALL, f, seed=4)
        r2, a2 = embers(SMALL, f, seed=4)
        assert np.array_equal(r1, r2) and np.array_equal(a1, a2)
        differs |= not np.array_equal(a1, embers(SMALL, f, seed=5)[1])
    assert differs


def test_embers_frames_differ_it_is_animated():
    assert not np.array_equal(embers(SMALL, 10)[1], embers(SMALL, 20)[1])


def test_no_global_random_state_and_no_clock(monkeypatch):
    np_before, py_before = np.random.get_state(), random.getstate()
    ref_b, ref_e = breath(SMALL, 30, mouths=mouth_grid(SMALL)), embers(SMALL, 30)

    def boom(*a, **k):
        raise AssertionError("the clock must not be read")
    for name in ("time", "time_ns", "perf_counter", "perf_counter_ns", "monotonic", "monotonic_ns", "process_time"):
        monkeypatch.setattr(time, name, boom)
    np.random.seed(123)
    random.seed(456)
    b, e = breath(SMALL, 30, mouths=mouth_grid(SMALL)), embers(SMALL, 30)
    np.random.seed(999)
    random.seed(1)
    b2, e2 = breath(SMALL, 30, mouths=mouth_grid(SMALL)), embers(SMALL, 30)
    assert np.array_equal(b, ref_b) and np.array_equal(b2, ref_b) and np.array_equal(e[1], ref_e[1]) and np.array_equal(e2[1], ref_e[1])
    np.random.seed(77)
    random.seed(778)
    state = np.random.get_state()
    pystate = random.getstate()
    breath(SMALL, 31, mouths=mouth_grid(SMALL))
    embers(SMALL, 31)
    after = np.random.get_state()
    assert state[0] == after[0] and np.array_equal(state[1], after[1]) and state[2:] == after[2:], "numpy's global random state was used"
    assert pystate == random.getstate(), "the random module's global state was used"
    del np_before, py_before


# ===================================================================================================== rule 6: wind (embers)
def mean_x_offset(wind, seconds=8.0, fps=12.0, seed=6):
    shape = SMALL
    h, w = shape
    total = weight = 0.0
    xs = np.arange(w)[None, :]
    for i in range(int(seconds * fps)):
        _, a = embers(shape, i, fps, source=(0.5, 0.8), wind=wind, seed=seed)
        s = float(a.sum())
        if s > 0:
            total += float((a * xs).sum())
            weight += s
    return (total / weight - 0.5 * w) / w


def test_embers_wind_moves_them_in_its_direction_and_no_wind_is_only_sway():
    still, right, left, strong = mean_x_offset((0.0, 0.0)), mean_x_offset((0.1, 0.0)), mean_x_offset((-0.1, 0.0)), mean_x_offset((0.2, 0.0))
    assert abs(still) <= 0.03, still
    assert right >= still + 0.02 and left <= still - 0.02, (left, still, right)
    assert strong > right, (right, strong)


def test_embers_each_life_drifts_with_the_wind_over_time():
    shape, fps = SMALL, 24.0
    for wind_x, sign in ((0.1, 1), (-0.1, -1)):
        _, lives = ember_blob_track(shape, 24.0, fps, seed=5, wind=(wind_x, 0.0))
        long = [l for l in lives if l[-1][0] - l[0][0] >= 0.8]
        assert long, "no life of 0.8 s or more was followed"
        for l in long:
            dt = l[-1][0] - l[0][0]
            assert sign * (l[-1][1] - l[0][1]) >= 0.25 * abs(wind_x) * shape[1] * dt, (round(dt, 2), l[0][1], l[-1][1])


# ==================================================================================================================== rule 7: speed
def best_of(fn, runs=7):
    fn()
    t = []
    for _ in range(runs):
        t0 = time.perf_counter()
        fn()
        t.append(time.perf_counter() - t0)
    return min(t)


def test_speed_breath_one_1280x704_frame_with_four_mouths_under_015_s():
    mouths = [(300.0, 500.0), (500.0, 520.0), (800.0, 480.0), (1000.0, 510.0)]
    assert best_of(lambda: BE.breath_alpha(BIG, 40, 24.0, mouths, (0.02, 0.0), 1)) < 0.15


def test_speed_embers_one_1280x704_frame_with_60_embers_under_015_s():
    depth = np.random.default_rng(0).uniform(0, 1, BIG).astype(np.float32)
    assert best_of(lambda: BE.embers_layer(BIG, 40, 24.0, (640.0, 560.0), 40.0, (0.02, 0.0), depth, 1, count=60)) < 0.15
