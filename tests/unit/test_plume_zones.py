"""Plume measurements (explainer_engine/qa/plume_zones.py): share of a smoke plume that lies on a person, and how much of the
frame the plume covers. A measure that cannot be computed is NOT_RUN, never PASS; the limits are hypotheses (REVIEW level)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from explainer_engine.qa import plume_zones as PZ

H, W = 40, 80


def _mask():
    m = np.zeros((H, W), bool)
    m[:, :40] = True            # the person fills the left half
    return m


def _plume(x0, x1, a=0.5):
    p = np.zeros((H, W), np.float32)
    p[:, x0:x1] = a
    return p


def test_tolerances_are_hypotheses_and_say_so():
    t = json.loads((Path(PZ.__file__).parent / "plume_zones_tolerances.json").read_text(encoding="utf-8"))
    assert t["kind"] == "hypothesis"
    assert t["note"] == "REVIEW-level default, not binding until the owner has seen it"
    assert t["person_share_max"] == 0.05 and t["total_share_min"] == 0.02


def test_plume_outside_the_person_is_zero_and_passes():
    r = PZ.plume_in_person_share(_plume(50, 70), _mask())
    assert r["status"] == "PASS" and r["value"] == 0.0


def test_plume_half_inside_is_fifty_percent_and_fails():
    r = PZ.plume_in_person_share(_plume(20, 60), _mask())      # 20 columns inside, 20 outside
    assert abs(r["value"] - 0.5) < 1e-9 and r["status"] == "FAIL"


def test_share_just_under_and_over_the_limit():
    p = np.zeros((H, W), np.float32); p[:, 60:80] = 1.0          # 20 columns outside
    p[0, 0] = 1.0                                                # tiny bit inside: 1 / (20*40 + 1)
    assert PZ.plume_in_person_share(p, _mask())["status"] == "PASS"
    p[:, 30:40] = 1.0                                            # 10 columns inside: far above 5 %
    assert PZ.plume_in_person_share(p, _mask())["status"] == "FAIL"


def test_empty_plume_is_not_run_never_pass():
    r = PZ.plume_in_person_share(np.zeros((H, W), np.float32), _mask())
    assert r["status"] == "NOT_RUN" and r["value"] is None


def test_missing_mask_is_not_run():
    assert PZ.plume_in_person_share(_plume(50, 70), None)["status"] == "NOT_RUN"


def test_empty_person_mask_is_not_run():
    # a mask with no person pixels cannot prove the plume avoids a person: 0 would be a false PASS
    assert PZ.plume_in_person_share(_plume(50, 70), np.zeros((H, W), bool))["status"] == "NOT_RUN"


def test_shape_mismatch_is_not_run():
    assert PZ.plume_in_person_share(_plume(50, 70), np.ones((H, W + 1), bool))["status"] == "NOT_RUN"


def test_bad_alpha_is_not_run():
    p = _plume(50, 70); p[0, 0] = np.nan
    assert PZ.plume_in_person_share(p, _mask())["status"] == "NOT_RUN"
    q = _plume(50, 70); q[0, 0] = -0.2
    assert PZ.plume_in_person_share(q, _mask())["status"] == "NOT_RUN"


def test_soft_mask_counts_above_half():
    m = _mask().astype(np.float32) * 0.9
    assert abs(PZ.plume_in_person_share(_plume(20, 60), m)["value"] - 0.5) < 1e-9


def test_total_share_enough_and_flagged_when_under():
    ok = PZ.plume_total_share(_plume(40, 60))                    # 20 of 80 columns = 25 %
    assert ok["status"] == "PASS" and abs(ok["value"] - 0.25) < 1e-9
    p = np.zeros((H, W), np.float32); p[0, :5] = 1.0             # 5 of 3200 pixels = 0.16 %
    low = PZ.plume_total_share(p)
    assert low["status"] == "FAIL" and low["value"] < 0.02


def test_total_share_ignores_faint_alpha_and_empty_is_flagged():
    assert PZ.plume_total_share(_plume(0, 80, a=0.01))["status"] == "FAIL"     # below the alpha threshold: not visible
    assert PZ.plume_total_share(np.zeros((H, W), np.float32))["status"] == "FAIL"


def test_total_share_bad_input_is_not_run():
    assert PZ.plume_total_share(None)["status"] == "NOT_RUN"
    assert PZ.plume_total_share(np.zeros(5))["status"] == "NOT_RUN"           # not an image


def test_check_frames_worst_status_wins():
    good = (_plume(50, 70), _mask()); bad = (_plume(20, 60), _mask()); empty = (np.zeros((H, W), np.float32), _mask())
    assert PZ.check_frames([good, good])["status"] == "PASS"
    assert PZ.check_frames([good, bad])["status"] == "FAIL"
    assert PZ.check_frames([good, empty])["status"] == "NOT_RUN"
    assert PZ.check_frames([])["status"] == "NOT_RUN"
