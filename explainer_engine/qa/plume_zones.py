"""Smoke-plume measurements for the 2.5D lane: how much of a plume lies on a person, and how much of the frame it covers.

Inputs are numpy arrays of one frame: ``plume_alpha`` (float, 0..1, the plume's own opacity) and ``person_mask`` (bool, or
float where a value above ``person_mask_min`` is person). Every result is ``{"status": PASS|FAIL|NOT_RUN, "value", "detail"}``.

A measure that cannot be computed is NOT_RUN and never PASS: no mask, an empty mask, differing shapes, bad alpha, or a plume
with zero total alpha (0/0). In particular a plume that was cut by the person's silhouette still has a measured, honest share
only when something of it remains; an empty plume proves nothing.

The limits live in ``plume_zones_tolerances.json`` with ``kind: hypothesis`` (REVIEW-level default, not binding until the
owner has seen it); nothing here copies a number.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

TOLERANCES_PATH = Path(__file__).with_name("plume_zones_tolerances.json")
PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"


def tolerances() -> dict:
    return json.loads(TOLERANCES_PATH.read_text(encoding="utf-8"))


def _res(status: str, value, detail: str) -> dict:
    return {"status": status, "value": value, "detail": detail}


def _alpha_problem(a) -> str | None:
    if a is None:
        return "plume alpha missing"
    a = np.asarray(a)
    if a.ndim != 2 or a.size == 0:
        return "plume alpha is not a 2-D image"
    if not np.issubdtype(a.dtype, np.number) or not np.isfinite(a).all():
        return "plume alpha has NaN/inf or is not numeric"
    if (a < 0).any():
        return "plume alpha has negative values"
    return None


def plume_in_person_share(plume_alpha, person_mask) -> dict:
    """Plume alpha inside the person zones divided by the total plume alpha (0..1); PASS when at most ``person_share_max``."""
    bad = _alpha_problem(plume_alpha)
    if bad:
        return _res(NOT_RUN, None, bad)
    if person_mask is None:
        return _res(NOT_RUN, None, "person mask missing")
    a = np.asarray(plume_alpha, dtype=np.float64); m = np.asarray(person_mask)
    if m.shape != a.shape:
        return _res(NOT_RUN, None, f"shape mismatch: plume {a.shape}, mask {m.shape}")
    t = tolerances()
    person = m.astype(bool) if m.dtype == bool else m > t["person_mask_min"]
    if not person.any():
        return _res(NOT_RUN, None, "person mask is empty: nothing to avoid, so 0 would prove nothing")
    total = float(a.sum())
    if total <= 0.0:
        return _res(NOT_RUN, None, "plume has zero total alpha (0/0)")
    share = float(a[person].sum()) / total
    ok = share <= t["person_share_max"]
    return _res(PASS if ok else FAIL, share, f"{share:.4f} of the plume alpha lies on a person; limit {t['person_share_max']} (hypothesis)")


def plume_total_share(plume_alpha) -> dict:
    """Share of the frame's pixels where the plume is visible (alpha above ``alpha_visible``); FAIL (flagged) under ``total_share_min``."""
    bad = _alpha_problem(plume_alpha)
    if bad:
        return _res(NOT_RUN, None, bad)
    t = tolerances()
    a = np.asarray(plume_alpha, dtype=np.float64)
    share = float((a > t["alpha_visible"]).mean())
    ok = share >= t["total_share_min"]
    return _res(PASS if ok else FAIL, share, f"plume visible on {share:.4f} of the frame; minimum {t['total_share_min']} (hypothesis)")


def check_frames(frames) -> dict:
    """``frames`` = iterable of (plume_alpha, person_mask). Both measures on every frame; the worst status wins (NOT_RUN > FAIL > PASS)."""
    rank = {PASS: 0, FAIL: 1, NOT_RUN: 2}
    per_frame = []
    for a, m in frames:
        per_frame.append({"person_share": plume_in_person_share(a, m), "total_share": plume_total_share(a)})
    if not per_frame:
        return {"status": NOT_RUN, "value": None, "detail": "no frames", "frames": []}
    worst = max((r["status"] for f in per_frame for r in f.values()), key=rank.__getitem__)
    return {"status": worst, "value": None, "detail": f"{len(per_frame)} frames, worst status {worst}", "frames": per_frame}
