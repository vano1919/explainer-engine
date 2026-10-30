"""The signal pieces of the sound director (P4, explainer_engine/audio/acoustics.py) and the three layers of a composite hit
(foley.hit_*, BP-119): synthetic audio only, deterministic, no files, no network."""

from __future__ import annotations

import numpy as np

from explainer_engine.audio import acoustics as A
from explainer_engine.audio import foley
from explainer_engine.standards import sourced_rules as SR

SR_ = A.SR


def tone(hz: float, seconds: float = 1.0, amp: float = 0.5) -> np.ndarray:
    return (amp * np.sin(2 * np.pi * hz * np.arange(int(seconds * SR_)) / SR_)).astype(np.float32)


def test_pan_is_constant_power_and_centre_is_equal():
    x = tone(440, 0.1)
    for p in (-1.0, -0.45, 0.0, 0.36, 1.0):
        y = A.pan(x, p)
        assert y.shape == (len(x), 2) and y.dtype == np.float32
        assert np.allclose(y[:, 0] ** 2 + y[:, 1] ** 2, x ** 2, atol=1e-6)
    c = A.pan(x, 0.0)
    assert np.array_equal(c[:, 0], c[:, 1])
    assert np.allclose(A.pan(x, 1.0)[:, 0], 0, atol=1e-6) and np.allclose(A.pan(x, -1.0)[:, 1], 0, atol=1e-6)
    r = A.pan(x, 0.36)  # a focal point at 0.9 with BP-121's range: right louder by the constant-power ratio
    want = 20 * np.log10(np.sin((1.36) * np.pi / 4) / np.cos((1.36) * np.pi / 4))
    assert abs(A.rms_db(r[:, 1]) - A.rms_db(r[:, 0]) - want) < 0.01 and want > 4


def test_widen_is_deterministic_decorrelated_and_keeps_each_side_s_magnitude():
    x = A.room_tone("neutral", 3, 2.0)
    a, b = A.widen(x, 7), A.widen(x, 7)
    assert np.array_equal(a, b) and not np.array_equal(a, A.widen(x, 8))
    assert abs(A.rms_db(a[:, 0]) - A.rms_db(x)) < 0.3 and abs(A.rms_db(a[:, 1]) - A.rms_db(x)) < 0.3  # all-pass: same level
    corr = float(np.corrcoef(a[4800:-4800, 0], a[4800:-4800, 1])[0, 1])
    assert abs(corr) < 0.9, corr  # a pair, not a copy


def test_impulse_per_kind_is_deterministic_unit_energy_and_ordered_by_tail():
    for kind in A.KINDS:
        ir = A.impulse(kind, 5, SR_)
        assert np.array_equal(ir, A.impulse(kind, 5, SR_))
        assert abs(float(np.sum(ir.astype(np.float64) ** 2)) - 1.0) < 1e-3
    assert len(A.impulse("outdoor", 5, SR_)) <= int(0.060 * SR_) and len(A.impulse("neutral", 5, SR_)) == 1
    assert len(A.impulse("room", 5, SR_)) < len(A.impulse("hall", 5, SR_)) < len(A.impulse("cave", 5, SR_))
    assert not np.array_equal(A.impulse("hall", 5, SR_), A.impulse("hall", 6, SR_))


def test_convolve_matches_numpy_and_keeps_the_input_length():
    rng = np.random.default_rng(0)
    x, ir = rng.standard_normal(20000).astype(np.float32), rng.standard_normal(3000).astype(np.float32)
    full = A.convolve(x, ir, tail=True)
    assert len(A.convolve(x, ir)) == len(x) and len(full) == len(x) + len(ir) - 1
    assert np.allclose(full, np.convolve(x, ir), atol=2e-2 * np.abs(np.convolve(x, ir)).max() * 0.05)
    assert np.allclose(A.convolve(x, np.array([1.0], np.float32)), x, atol=1e-6)


def test_shelf_and_highpass_move_the_bands_they_name():
    lo, hi = tone(500), tone(10000)
    hs_hi = A.rms_db(A.shelf(hi, SR_, 6000, -4.0, True)[4096:-4096]) - A.rms_db(hi[4096:-4096])
    hs_lo = A.rms_db(A.shelf(lo, SR_, 6000, -4.0, True)[4096:-4096]) - A.rms_db(lo[4096:-4096])
    assert -4.5 < hs_hi < -2.8 and abs(hs_lo) < 0.3  # BP-122's far shelf takes the top off and leaves the voice band
    prox = A.rms_db(A.shelf(tone(60), SR_, 140, 2.0, False)[4096:-4096]) - A.rms_db(tone(60)[4096:-4096])
    assert 1.0 < prox < 2.3
    hp60 = A.rms_db(A.highpass(tone(40), SR_, 80)[8192:-8192]) - A.rms_db(tone(40)[8192:-8192])
    hp1k = A.rms_db(A.highpass(tone(1000), SR_, 80)[8192:-8192]) - A.rms_db(tone(1000)[8192:-8192])
    assert hp60 < -12 and abs(hp1k) < 0.1
    assert A.shelf(lo, SR_, 6000, 0.0, True).dtype == np.float32


def test_band_dip_dips_only_where_the_key_is_up_and_only_around_its_centre():
    t2200, t200 = tone(2200, 2.0), tone(200, 2.0)
    one, zero = np.ones(len(t2200), np.float32), np.zeros(len(t2200), np.float32)
    mid = slice(8192, -8192)
    dipped = A.rms_db(A.band_dip(t2200, SR_, one, 2200, 1.2, 3.0)[mid]) - A.rms_db(t2200[mid])
    assert abs(dipped + 3.0) < 0.1  # the full depth at the centre
    assert abs(A.rms_db(A.band_dip(t200, SR_, one, 2200, 1.2, 3.0)[mid]) - A.rms_db(t200[mid])) < 0.5
    off = A.band_dip(t2200, SR_, zero, 2200, 1.2, 3.0)
    assert np.abs(off - t2200).max() < 1e-5  # key down: the signal is unchanged
    half = np.concatenate([one[:len(one) // 2], zero[len(one) // 2:]])
    out = A.band_dip(t2200, SR_, half, 2200, 1.2, 3.0)
    assert A.rms_db(out[:SR_ - 4096][4096:]) < A.rms_db(out[SR_ + 4096:-4096]) - 2.5  # follows the key
    stereo = A.band_dip(np.stack([t2200, t2200], axis=1), SR_, one, 2200, 1.2, 3.0)
    assert stereo.shape == (len(t2200), 2) and np.allclose(stereo[:, 0], stereo[:, 1])


def test_the_dip_centre_depth_delivers_the_band_gap_a_check_measures():
    gap = float(SR.T("BP-118", "notch_depth_db")[1])
    centre = A.dip_centre_for_gap(gap, SR.T("BP-118", "notch_hz"), SR.T("BP-118", "notch_q"), *SR.T("BP-118", "measure_band_hz"))
    assert centre > gap  # a Q 1.2 bell dips its centre more than the band as a whole
    pink = A.room_tone("room", 1, 12.0)
    dipped = A.band_dip(pink, SR_, np.ones(len(pink), np.float32), SR.T("BP-118", "notch_hz"), SR.T("BP-118", "notch_q"), centre)
    lo, hi = SR.T("BP-118", "measure_band_hz")
    moved = 10 * np.log10(A.band_share(dipped, SR_, lo, hi) / A.band_share(pink, SR_, lo, hi))
    assert moved < -SR.T("BP-118", "notch_depth_db")[0], moved


def test_room_tone_is_deterministic_high_passed_circular_and_per_kind():
    a = A.room_tone("hall", 11, 4.0)
    assert np.array_equal(a, A.room_tone("hall", 11, 4.0)) and not np.array_equal(a, A.room_tone("hall", 12, 4.0))
    assert abs(A.rms_db(a) - A.rms_db(np.full(10, 0.05))) < 0.1 and a.dtype == np.float32
    hpf = SR.T("BP-116", "hpf_hz")
    assert A.band_share(np.tile(a, 2), SR_, 0, hpf / 2) < 1e-3  # nothing left below the high-pass
    step = abs(float(a[0] - a[-1]))
    assert step < 6 * float(np.abs(np.diff(a)).std())  # the loop point is as smooth as any other pair of samples
    assert A.band_share(np.tile(A.room_tone("cave", 1, 4.0), 2), SR_, 3000, 20000) < A.band_share(np.tile(A.room_tone("outdoor", 1, 4.0), 2), SR_, 3000, 20000)


def test_beat_grid_reads_a_click_track_and_refuses_noise():
    def clicks(bpm: float, seconds: float, offset: float) -> np.ndarray:
        x = np.zeros(int(seconds * SR_), np.float32)
        burst = (np.random.default_rng(1).standard_normal(240) * np.exp(-np.arange(240) / 60)).astype(np.float32)
        t = offset
        while t < seconds - 0.05:
            x[int(t * SR_):int(t * SR_) + 240] += burst
            t += 60.0 / bpm
        return x
    for bpm in (120, 100, 117):
        g = A.beat_grid(clicks(bpm, 20, 0.13), SR_)
        assert abs(g["bpm"] - bpm) <= 1 and abs(g["offset_s"] - 0.13) < 0.02, (bpm, g)
    assert A.beat_grid(np.random.default_rng(0).standard_normal(SR_ * 10).astype(np.float32) * 0.1, SR_) is None
    assert A.beat_grid(clicks(120, 1, 0.0), SR_) is None  # under ~2 s there is no tempo


def test_band_share_and_its_mask():
    x = np.concatenate([tone(2000, 2.0), tone(100, 2.0)])
    assert A.band_share(x, SR_, 1000, 4000) > 0.45
    mask = np.zeros(len(x), bool)
    mask[:SR_ * 2] = True
    assert A.band_share(x, SR_, 1000, 4000, mask) > 0.99 and A.band_share(x, SR_, 1000, 4000, ~mask) < 0.01
    assert A.band_share(x[:100], SR_, 1000, 4000) is None and A.band_share(x, SR_, 1000, 4000, np.zeros(len(x), bool)) is None
    assert A.band_share(np.stack([x, x], axis=1), SR_, 1000, 4000) == A.band_share(x, SR_, 1000, 4000)


def test_the_three_hit_layers_are_seeded_and_stay_in_bp119_bands():
    sub, (blo, bhi), (alo, ahi) = SR.T("BP-119", "sub_hz"), SR.T("BP-119", "body_hz"), SR.T("BP-119", "air_hz")
    floor = SR.T("BP-161", "hit_band_share_min")
    for fn, band in ((foley.hit_sub, (0, sub)), (foley.hit_body, (blo, bhi)), (foley.hit_air, (alo, ahi))):
        x = fn(1)
        assert np.array_equal(x, fn(1)) and not np.array_equal(x, fn(2)) and x.dtype == np.float32
        padded = np.pad(x, (0, 32768 - len(x)))
        assert A.band_share(padded, SR_, *band) >= floor, fn.__name__
    assert {"hit_sub", "hit_body", "hit_air"} <= set(foley.BUILD)
    assert all("hit" in foley.BUILD[k][0] for k in ("hit_sub", "hit_body", "hit_air"))
