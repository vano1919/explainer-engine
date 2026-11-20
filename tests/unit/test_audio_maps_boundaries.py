"""Boundary tests found by the 2026-11-20 mutation spot-check of the audio validators and the two map checkers.

Each test sits exactly ON a limit and pins which side of it is allowed. Only BP-54 (val_cue_binding) is read from the
registry (`SR.T`); the other audio validators keep their numbers in their own `Limits` defaults, so these tests read the
module's own defaults and never write a number of their own. Existing tests are untouched.
"""
import dataclasses

import numpy as np
import pytest

from explainer_engine.audio import (
    val_clip_fit as clip,
    val_cue_binding as bind,
    val_effect_audibility as aud,
    val_pace as pace,
    val_reaction_latency as lat,
    val_voice_similarity as voice,
    val_word_cuts as cuts,
)
from explainer_engine.maps import hud_layout as hud
from explainer_engine.maps.maplibre_spec import validate_shot_spec
from explainer_engine.standards import sourced_rules as SR


# ---- val_clip_fit: a value exactly on a limit is allowed ----
def _line(a, b): return {"id": "L1", "shot_id": "s1", "start": a, "end": b}
CLIP = [{"shot_id": "s1", "start": 10.0, "end": 14.0}]
def _clip_rules(a, b): return [x["rule"] for x in clip.check([_line(a, b)], CLIP)]


def test_clip_lead_exactly_at_tolerance_is_allowed_beyond_it_is_not():
    tol = clip.Limits().lead_tolerance_s
    assert _clip_rules(10.0 - tol, 12.0) == []
    assert _clip_rules(10.0 - tol - 0.01, 12.0) == ["CLIP-02"]


def test_clip_slack_exactly_at_maximum_is_allowed_beyond_it_is_not():
    slack = clip.Limits().max_slack_s  # clip length 4.0 minus line length
    assert _clip_rules(10.2, 10.2 + 4.0 - slack) == []
    assert _clip_rules(10.2, 10.2 + 4.0 - slack - 0.01) == ["CLIP-03"]


# ---- val_cue_binding: BP-54 window, both edges, from the registry ----
EV = [{"id": "e1", "t": 2.0, "type": "object_in"}]
def _bind(t):
    cue = {"id": "c1", "t": t, "sound_id": "p", "event_id": "e1"}
    return {x["where"]: x["severity"] for x in bind.check(EV, [cue])}


def test_cue_exactly_at_early_limit_is_not_a_window_fail():
    early = SR.T("BP-54", "early_max_ms") / 1000
    assert _bind(2.0 - early) == {"c1": "REVIEW"}
    assert _bind(2.0 - early - 0.002) == {"c1": SR.severity("BP-54")}


def test_cue_exactly_at_late_limit_is_not_a_window_fail():
    late = SR.T("BP-54", "late_max_ms") / 1000
    assert _bind(2.0 + late) == {"c1": "REVIEW"}
    assert _bind(2.0 + late + 0.002) == {"c1": SR.severity("BP-54")}


# ---- val_effect_audibility: limits are None by default -> NOT_RUN; equality at a sourced limit is not a finding ----
def test_default_limits_have_no_numbers_and_every_measurement_is_not_run():
    L = aud.Limits()
    assert L.masked_below_db is None and L.silent_peak_dbfs is None and L.hf_hz is None
    rate = 8000
    z = np.zeros(rate // 10)
    got = aud.check([{"id": "a", "effect": z + 0.1, "bed": z + 0.01, "sr": rate},
                     {"id": "b", "mix": z + 0.01, "sr": rate}])
    assert [(f["rule"], f["severity"]) for f in got] == [("AUD-01", "NOT_RUN"), ("CLK-01", "NOT_RUN")]


def test_margin_exactly_at_masked_limit_is_allowed(monkeypatch):
    monkeypatch.setattr(aud, "audibility", lambda e, b, sr: {"peak_dbfs": -20.0, "margin_db": 6.0, "dominant_hz": 100.0,
                                                           "window_start_s": 0.0})
    item = [{"id": "a", "effect": [0.0], "bed": [0.0], "sr": 8000}]
    assert aud.check(item, aud.Limits(masked_below_db=6.0)) == []
    assert [f["rule"] for f in aud.check(item, aud.Limits(masked_below_db=6.001))] == ["AUD-01"]


def test_click_with_concentration_exactly_at_minimum_is_a_click(monkeypatch):
    cand = {"t": 0.1, "local_ratio": 9.0, "near_ratio": 9.0, "concentration": 0.5}
    monkeypatch.setattr(aud, "click_candidates", lambda mix, sr, limits: [dict(cand)])
    item = [{"id": "m", "mix": [0.0], "sr": 8000}]
    base = dict(hf_hz=1000.0, local_ratio=9.0, near_ratio=9.0, concentration_min=0.5)
    # ratios are strict (equal = no click); concentration is inclusive (equal = click)
    assert aud.check(item, aud.Limits(**{**base, "local_ratio": 8.99, "near_ratio": 8.99}))[0]["rule"] == "CLK-01"
    assert aud.check(item, aud.Limits(**base)) == []
    assert aud.check(item, aud.Limits(**{**base, "local_ratio": 8.99})) == []
    assert aud.check(item, aud.Limits(**{**base, "local_ratio": 8.99, "near_ratio": 8.99, "concentration_min": 0.5001})) == []


# ---- val_pace: a zone exactly gap_wpm above the middle passes ----
def _zones(h_n, f_n):
    words, zs = [], []
    for name, a, b, n in [("hook", 0, 20, h_n), ("middle", 20, 80, 100), ("finale", 80, 100, f_n)]:
        step = (b - a) / n
        words += [{"word": "w", "start": a + i * step, "end": a + i * step + step / 2} for i in range(n)]
        zs.append({"zone": name, "start": a, "end": b})
    return words, zs


def test_hook_and_finale_exactly_at_required_rate_pass_one_word_less_fails():
    gap = pace.Limits().zone_gap_wpm  # middle is 100 wpm; a 20 s zone needs 3 words per wpm-gap-step
    n_ok = round((100 + gap) / 3)
    assert abs(n_ok * 3 - (100 + gap)) < 1e-9, "fixture: the required rate must be a whole number of words in 20 s"
    r = lambda *a: [x["rule"] for x in pace.check(*_zones(*a)) if x["rule"] in ("PACE-02", "PACE-03")]
    assert r(n_ok, n_ok) == []
    assert r(n_ok - 1, n_ok) == ["PACE-02"]
    assert r(n_ok, n_ok - 1) == ["PACE-03"]


def test_zero_is_a_legal_minimum_word_count():
    words, zs = _zones(35, 35)
    pace.check(words, zs, pace.Limits(min_words_per_zone=0))
    with pytest.raises(ValueError):
        pace.check(words, zs, pace.Limits(min_words_per_zone=-1))


# ---- val_reaction_latency: zero is legal, negative is not ----
def test_zero_latency_and_zero_tolerance_are_accepted_negative_are_not():
    assert lat.check([], lat.Limits(tol_s=0.0)) == []
    assert lat.check([], lat.Limits(latency_s={"cheer": 0.0})) == []
    with pytest.raises(ValueError):
        lat.check([], lat.Limits(tol_s=-0.001))
    with pytest.raises(ValueError):
        lat.check([], lat.Limits(latency_s={"cheer": -0.001}))


# ---- val_voice_similarity: similarity exactly at the self floor is allowed ----
def test_clip_exactly_at_self_floor_is_allowed_just_above_floor_fails():
    vecs = {"a1": [1, 0, 0], "a2": [0.99, 0.1, 0], "a3": [0, 1, 0]}
    clips = [{"id": k, "character": "anna", "embedding": v} for k, v in vecs.items()]
    cen = voice.centroid([np.array(v, float) for v in vecs.values()])
    sim = float(voice.cosine(np.array(vecs["a3"], float), cen))
    L = voice.Limits()
    ok = dataclasses.replace(L, self_floor=round(sim, 6))
    assert [x["where"] for x in voice.check(clips, ok) if x["rule"] == "VOICE-01"] == []
    bad = dataclasses.replace(L, self_floor=round(sim, 6) + 0.001)
    assert "a3" in [x["where"] for x in voice.check(clips, bad) if x["rule"] == "VOICE-01"]


# ---- val_word_cuts: a fade exactly at the minimum is allowed; zero minimums are legal ----
W = [{"word": "hello", "start": 0.0, "end": 0.4}, {"word": "world", "start": 0.6, "end": 1.0}]


def test_fade_exactly_at_minimum_is_allowed():
    fm = cuts.Limits().fade_min_ms
    assert [x["rule"] for x in cuts.check(W, [{"t": 0.5, "fade_ms": fm}])] == []
    assert [x["rule"] for x in cuts.check(W, [{"t": 0.5, "fade_ms": fm - 0.5}])] == ["CUT-03"]


def test_zero_pad_and_zero_fade_minimums_are_legal_negative_are_not():
    assert cuts.check(W, [], cuts.Limits(pad_min_s=0.0, fade_min_ms=0.0)) == []
    with pytest.raises(ValueError):
        cuts.check(W, [], cuts.Limits(pad_min_s=-0.01))


# ---- maps/hud_layout.check_palette: equal to the limit passes ----
def test_contrast_exactly_at_minimum_passes_just_above_fails():
    fg, bg = (200, 120, 40), (20, 20, 30)
    ratio = hud.contrast_ratio(fg, bg)
    assert hud.check_palette({"a": fg}, bg, min_ratio=ratio, min_delta_e=0.0) == []
    assert hud.check_palette({"a": fg}, bg, min_ratio=ratio + 0.01, min_delta_e=0.0) != []


def test_delta_e_exactly_at_minimum_passes_just_above_fails():
    a, b = (230, 159, 0), (0, 114, 178)
    smallest = min(hud._delta_e_cie76(hud.simulate_cvd(a, k), hud.simulate_cvd(b, k))
                   for k in ("protanopia", "deuteranopia", "tritanopia"))
    assert hud.check_palette({"a": a, "b": b}, (0, 0, 0), min_ratio=0.0, min_delta_e=smallest) == []
    assert hud.check_palette({"a": a, "b": b}, (0, 0, 0), min_ratio=0.0, min_delta_e=smallest + 0.01) != []


# ---- maps/maplibre_spec: a truck must move on either axis; only an identical centre is refused ----
def _truck(frm, to):
    from tests.unit.test_maps_maplibre_spec import _valid_spec
    s = _valid_spec()
    s["camera"] = {"move": "truck", "center_from": frm, "center_to": to}
    return validate_shot_spec(s)


def test_truck_moving_on_one_axis_only_is_valid_identical_centres_are_refused():
    assert _truck([2.0, 50.0], [3.0, 50.0]) == []
    assert _truck([2.0, 50.0], [2.0, 51.0]) == []
    assert any("must differ" in p for p in _truck([2.0, 50.0], [2.0, 50.0]))
