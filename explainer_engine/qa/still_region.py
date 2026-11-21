"""Still-region measurements for the 2.5D lane: where nothing should move, a rendered frame must still be the original photo.

``still_region_report(original, frame, region)``: median/p95 change, added noise (robust sigma of the high-passed difference), sharpness ratio
(Laplacian variance, frame / original) and Lab colour shift, over ``region`` minus ``exclude`` (e.g. the effect zones or the particle matte).
``flow_in_region(original, frame, region)``: how far the content of a region moved against the original (Farneback optical flow, pixels): a person
bent by a heat haze or cloth sway shows up as flow on the person mask.

Verdicts: no judging number is sourced or approved by the owner, so ``limits`` is None by default and the status is NOT_RUN with the measured
numbers (never PASS, same rule as ``audio/val_effect_audibility.py``). Given explicit limits (``median_abs_diff_max``, ``p95_abs_diff_max``,
``noise_sigma_max``, ``sharpness_ratio_min``, ``sharpness_ratio_max``, ``lab_shift_max``) the same call returns PASS or FAIL.
Images are BGR uint8 arrays of one size; masks are bool (or non-zero).
"""

from __future__ import annotations

import cv2
import numpy as np

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"


def _res(status, metrics, detail):
    return {"status": status, "metrics": metrics, "detail": detail}


def _problem(original, frame, region):
    if original is None or frame is None:
        return "image missing"
    if region is None:
        return "region mask missing"
    o, f, m = np.asarray(original), np.asarray(frame), np.asarray(region)
    if o.shape != f.shape or o.ndim != 3 or o.shape[:2] != m.shape:
        return f"shape mismatch: original {o.shape}, frame {f.shape}, region {m.shape}"
    return None


def _lap_var(gray, sel):
    lap = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    return float(lap[sel].var())


def still_region_report(original, frame, region, exclude=None, limits=None) -> dict:
    bad = _problem(original, frame, region)
    if bad:
        return _res(NOT_RUN, None, bad)
    o = np.asarray(original); f = np.asarray(frame)
    sel = np.asarray(region).astype(bool)
    if exclude is not None:
        ex = np.asarray(exclude).astype(bool)
        if ex.shape != sel.shape:
            return _res(NOT_RUN, None, f"shape mismatch: exclude {ex.shape}")
        sel = sel & ~ex
    sel_in = cv2.erode(sel.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)   # interior: borders of the region do not feed the filters
    if sel_in.sum() < 50:
        return _res(NOT_RUN, None, f"region too small after exclusion ({int(sel_in.sum())} px)")
    d = np.abs(o.astype(np.float32) - f.astype(np.float32)).mean(axis=2)
    diff = f.astype(np.float32).mean(axis=2) - o.astype(np.float32).mean(axis=2)
    hp = diff - cv2.GaussianBlur(diff, (0, 0), 4.0)
    mad = float(np.median(np.abs(hp[sel_in] - np.median(hp[sel_in]))))
    go = cv2.cvtColor(o, cv2.COLOR_BGR2GRAY); gf = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    vo = _lap_var(go, sel_in)
    lo = cv2.cvtColor(o, cv2.COLOR_BGR2LAB).astype(np.float32)[sel_in].mean(axis=0); lf = cv2.cvtColor(f, cv2.COLOR_BGR2LAB).astype(np.float32)[sel_in].mean(axis=0)
    m = dict(pixels=int(sel_in.sum()), median_abs_diff=round(float(np.median(d[sel_in])), 4), p95_abs_diff=round(float(np.percentile(d[sel_in], 95)), 4),
             noise_sigma=round(1.4826 * mad, 4), sharpness_ratio=round(_lap_var(gf, sel_in) / vo, 4) if vo > 0 else None,
             lab_shift=round(float(np.linalg.norm(lf - lo)), 4))
    if not limits:
        return _res(NOT_RUN, m, "measured only: no judging limits are sourced or approved (pass limits= to judge)")
    fails = []
    for key, name in (("median_abs_diff_max", "median_abs_diff"), ("p95_abs_diff_max", "p95_abs_diff"), ("noise_sigma_max", "noise_sigma"), ("lab_shift_max", "lab_shift")):
        if key in limits and m[name] > limits[key]:
            fails.append(f"{name} {m[name]} > {limits[key]}")
    if m["sharpness_ratio"] is not None:
        if "sharpness_ratio_min" in limits and m["sharpness_ratio"] < limits["sharpness_ratio_min"]:
            fails.append(f"sharpness_ratio {m['sharpness_ratio']} < {limits['sharpness_ratio_min']}")
        if "sharpness_ratio_max" in limits and m["sharpness_ratio"] > limits["sharpness_ratio_max"]:
            fails.append(f"sharpness_ratio {m['sharpness_ratio']} > {limits['sharpness_ratio_max']}")
    return _res(FAIL if fails else PASS, m, "; ".join(fails) if fails else "within the given limits")


def flow_in_region(original, frame, region) -> dict:
    """Farneback flow original -> frame inside ``region``: mean, p95 and max displacement in pixels."""
    bad = _problem(original, frame, region)
    if bad:
        return {"status": NOT_RUN, "detail": bad}
    sel = np.asarray(region).astype(bool)
    if not sel.any():
        return {"status": NOT_RUN, "detail": "region is empty"}
    go = cv2.cvtColor(np.asarray(original), cv2.COLOR_BGR2GRAY); gf = cv2.cvtColor(np.asarray(frame), cv2.COLOR_BGR2GRAY)
    fl = cv2.calcOpticalFlowFarneback(go, gf, None, 0.5, 4, 21, 3, 5, 1.1, 0)
    mag = np.hypot(fl[..., 0], fl[..., 1])[sel]
    return {"status": "MEASURED", "mean_px": round(float(mag.mean()), 4), "p95_px": round(float(np.percentile(mag, 95)), 4), "max_px": round(float(mag.max()), 4), "pixels": int(sel.sum())}
