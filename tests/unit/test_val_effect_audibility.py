import math

import numpy as np
import pytest

from explainer_engine.audio import val_effect_audibility as m

SR = 48000


def tone(hz, dur, db, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    return 10 ** (db / 20) * np.sin(2 * np.pi * hz * t)


def scene(effect_db, bed_db, hz=1000.0):
    """1 s of a pseudo-random bed with a 100 ms tone in it (the effect stem holds only the tone)."""
    rng = np.random.default_rng(1)
    bed = 10 ** (bed_db / 20) * rng.standard_normal(SR)
    eff = np.zeros(SR)
    eff[24000:28800] = tone(hz, 0.1, effect_db)
    return eff, bed


def test_margin_follows_the_levels():
    e1, b = scene(-30, -30)
    e2, _ = scene(-50, -30)
    a1, a2 = m.audibility(e1, b, SR), m.audibility(e2, b, SR)
    assert a1["dominant_hz"] == 1000.0 and a2["dominant_hz"] == 1000.0
    assert a1["margin_db"] - a2["margin_db"] == pytest.approx(20.0, abs=0.5)
    assert a2["margin_db"] < a1["margin_db"] and a1["margin_db"] > 0


def test_window_is_where_the_effect_is():
    e, b = scene(-20, -30)
    assert 0.49 <= m.audibility(e, b, SR)["window_start_s"] <= 0.58


def test_silent_effect_is_flagged_not_a_margin():
    a = m.audibility(np.zeros(SR), np.ones(SR) * 0.01, SR)
    assert a["silent"] is True and a["margin_db"] is None and a["peak_dbfs"] == -math.inf


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        m.audibility(np.zeros(10), np.zeros(11), SR)
    with pytest.raises(ValueError):
        m.audibility([], [], SR)
    with pytest.raises(ValueError):
        m.audibility([float("nan")] * 4, [0.0] * 4, SR)


def test_bands_cover_the_audible_range():
    assert m.BAND_CENTRES[0] == pytest.approx(25.1, abs=0.1) and m.BAND_CENTRES[-1] == pytest.approx(19953, abs=5)
    assert len(m.BAND_CENTRES) == 30


def test_no_sourced_limit_gives_not_run_never_pass():
    e, b = scene(-20, -30)
    f = m.check([{"id": "fx1", "effect": e, "bed": b, "sr": SR}])
    assert [(x["rule"], x["severity"]) for x in f] == [("AUD-01", "NOT_RUN")] and "dominant band 1000" in f[0]["detail"]


def test_with_limits_it_judges():
    e, b = scene(-70, -30)
    lim = m.Limits(masked_below_db=0.0)
    assert [x["rule"] for x in m.check([{"id": "fx", "effect": e, "bed": b, "sr": SR}], lim)] == ["AUD-01"]
    e2, _ = scene(-20, -30)
    assert m.check([{"id": "fx", "effect": e2, "bed": b, "sr": SR}], lim) == []
    silent = m.check([{"id": "fx", "effect": np.zeros(SR), "bed": b, "sr": SR}], m.Limits(silent_peak_dbfs=-70.0))
    assert [x["rule"] for x in silent] == ["AUD-02"]


CLICK = m.Limits(hf_hz=14000.0, local_ratio=9.0, near_ratio=6.0, concentration_min=0.8)


def test_step_discontinuity_is_a_click_and_a_clean_tone_is_not():
    x = tone(200, 1.0, -20)
    clean = m.check([{"id": "stem", "mix": x, "sr": SR}], CLICK)
    assert clean == []
    y = x.copy()
    y[24000:] += 0.1  # one-sample step: the classic cut click
    f = m.check([{"id": "stem", "mix": y, "sr": SR}], CLICK)
    assert [x["rule"] for x in f] == ["CLK-01"] and f[0]["where"].startswith("stem@0.5")


def test_a_long_high_noise_burst_is_not_concentrated():
    x = tone(200, 1.0, -20)
    rng = np.random.default_rng(2)
    hf = np.zeros(SR)
    hf[24000:26400] = np.convolve(rng.standard_normal(2400), [1, -1], mode="same") * 0.05  # 50 ms of treble
    cands = m.click_candidates(x + hf, SR, CLICK)
    assert max(c["concentration"] for c in cands) < 0.8
    assert m.check([{"id": "stem", "mix": x + hf, "sr": SR}], CLICK) == []


def test_click_check_is_not_run_without_a_corner_or_ratios():
    x = tone(200, 0.5, -20)
    assert [(f["rule"], f["severity"]) for f in m.check([{"id": "s", "mix": x, "sr": SR}])] == [("CLK-01", "NOT_RUN")]
    part = m.check([{"id": "s", "mix": x, "sr": SR}], m.Limits(hf_hz=14000.0))
    assert part[0]["severity"] == "NOT_RUN" and "not sourced" in part[0]["detail"]


def test_default_limits_hold_no_unsourced_number():
    d = m.Limits()
    assert (d.masked_below_db, d.silent_peak_dbfs, d.hf_hz, d.local_ratio, d.near_ratio, d.concentration_min) == (None,) * 6
