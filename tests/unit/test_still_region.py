"""Still-region measurements (explainer_engine/qa/still_region.py): where nothing should move, a frame must equal the original.
Synthetic images only. No judging limits exist yet (none sourced, none approved by the owner), so the verdict is NOT_RUN with the numbers."""

from __future__ import annotations

import cv2
import numpy as np

from explainer_engine.qa import still_region as SR

H, W = 120, 160


def _photo():
    rs = np.random.RandomState(3)
    base = cv2.GaussianBlur(rs.rand(H, W, 3).astype(np.float32), (0, 0), 2.0)
    return np.clip(60 + 150 * (base - base.min()) / (np.ptp(base) + 1e-9), 0, 255).astype(np.uint8)


def _region():
    m = np.zeros((H, W), bool); m[20:100, 20:140] = True
    return m


def test_an_identical_frame_has_zero_change_and_unit_sharpness():
    p = _photo(); r = SR.still_region_report(p, p.copy(), _region())
    assert r["metrics"]["median_abs_diff"] == 0 and r["metrics"]["noise_sigma"] == 0
    assert abs(r["metrics"]["sharpness_ratio"] - 1.0) < 1e-9 and abs(r["metrics"]["lab_shift"]) < 1e-6
    assert r["status"] == "NOT_RUN" and "limits" in r["detail"]


def test_added_noise_is_measured():
    p = _photo(); noisy = np.clip(p.astype(np.float32) + np.random.RandomState(1).randn(H, W, 3) * 6, 0, 255).astype(np.uint8)
    m = SR.still_region_report(p, noisy, _region())["metrics"]
    assert 3.0 < m["noise_sigma"] < 9.0 and m["sharpness_ratio"] > 1.2        # noise adds fake detail


def test_blur_lowers_sharpness_and_colour_shift_is_measured():
    p = _photo(); soft = cv2.GaussianBlur(p, (0, 0), 2.5)
    assert SR.still_region_report(p, soft, _region())["metrics"]["sharpness_ratio"] < 0.6
    warm = p.copy(); warm[..., 2] = np.clip(warm[..., 2].astype(np.int16) + 20, 0, 255).astype(np.uint8)
    assert SR.still_region_report(p, warm, _region())["metrics"]["lab_shift"] > 3.0


def test_changes_outside_the_region_or_inside_the_exclusion_do_not_count():
    p = _photo(); f = p.copy(); f[:20] = 255; f[40:60, 40:80] = 0              # a changed band outside; a changed patch inside
    excl = np.zeros((H, W), bool); excl[35:65, 35:85] = True
    r = SR.still_region_report(p, f, _region(), exclude=excl)
    assert r["metrics"]["median_abs_diff"] == 0 and r["metrics"]["pixels"] > 0


def test_judging_limits_give_pass_and_fail():
    p = _photo(); lim = {"median_abs_diff_max": 2.0, "noise_sigma_max": 2.0}
    assert SR.still_region_report(p, p.copy(), _region(), limits=lim)["status"] == "PASS"
    f = np.clip(p.astype(np.int16) + 15, 0, 255).astype(np.uint8)
    assert SR.still_region_report(p, f, _region(), limits=lim)["status"] == "FAIL"


def test_not_run_never_pass_for_bad_input():
    p = _photo()
    assert SR.still_region_report(p, p, None)["status"] == "NOT_RUN"
    assert SR.still_region_report(p, p[:, :-1], _region())["status"] == "NOT_RUN"
    assert SR.still_region_report(p, p, np.zeros((H, W), bool))["status"] == "NOT_RUN"      # empty region
    assert SR.still_region_report(p, p, _region(), limits={"median_abs_diff_max": 2.0}, exclude=np.ones((H, W), bool))["status"] == "NOT_RUN"


def test_flow_finds_a_shifted_patch_and_none_in_a_still_one():
    p = _photo(); f = p.copy(); f[40:80, 50:110] = np.roll(p, 4, axis=1)[40:80, 50:110]
    moved = np.zeros((H, W), bool); moved[40:80, 50:110] = True
    assert SR.flow_in_region(p, f, moved)["mean_px"] > 1.0
    still = np.zeros((H, W), bool); still[:30] = True
    assert SR.flow_in_region(p, f, still)["mean_px"] < 0.5
    assert SR.flow_in_region(p, f, None)["status"] == "NOT_RUN"
