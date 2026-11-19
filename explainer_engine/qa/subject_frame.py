"""Subject-frame integrity and the 2.5D motion envelope (owner-approved Python item 3, 2026-11-16).

Pure functions over data (no I/O, no pixels): a shot's ``crop_policy`` / sub-shot ``framing`` and a measured motion summary.
Every row follows ``qa/gates.row`` and is a REVIEW row (the envelope numbers are DESIGN_RULE / HYPOTHESIS until a calibrated
run), so nothing here can FAIL an episode. The pixel-level protection stays in production/directed25d.py (SAFE_MARGIN) and
production/motion_isolation.py; this module checks the PLAN against the same intent before a render is paid for.
"""
from __future__ import annotations

from explainer_engine.qa.gates import REVIEW, row

SAFE_MARGIN_PCT = 2.0
# 2.5D motion envelope, as shares of the frame width (ChatGPT owner-feedback rules, DESIGN_RULE / HYPOTHESIS)
ENVELOPE = {"drift_pct": (0.0, 3.0), "scale_pct": (0.0, 3.0), "parallax_pct": (0.0, 1.5), "velocity_pct_per_s": (0.0, 0.25)}


def crop_rows(shot: dict) -> list[dict]:
    """A shot whose ``crop_policy`` says 'preserve_required_subject_regions' must not zoom (``framing.crop`` > 1) onto a
    sub-shot unless the policy lists the ``intentional_crop_regions``. Root cause of S08_SH002: a 1.35 cut-in on a part of a
    medium shot clipped a hand, a prop and the candle, and no gate looked at the plan."""
    pol = shot.get("crop_policy")
    if not pol:
        return []
    allowed = pol.get("intentional_crop_regions") if isinstance(pol, dict) else None
    keep = pol if isinstance(pol, str) else pol.get("policy", "")
    if keep != "preserve_required_subject_regions":
        return []
    parts = ((shot.get("split_plan") or {}).get("parts")) or []
    zoomed = [p.get("part_shot_id") for p in parts if float((p.get("framing") or {}).get("crop") or 1.0) > 1.0]
    return [row(f"SUBJECT_FRAME_INTEGRITY:{shot.get('shot_id', '?')}", not zoomed or bool(allowed),
                f"{len(zoomed)} sub-shot(s) cut in on a shot that must keep its required subject regions"
                + (" (the policy lists intentional crop regions)" if allowed else ""), zoomed, level=REVIEW)]


def envelope_rows(shot_id: str, measured: dict | None) -> list[dict]:
    """``measured``: {drift_pct, scale_pct, parallax_pct, velocity_pct_per_s} of a rendered or planned 2.5D move. A key that
    was not measured is skipped (NOT_RUN is the caller's call); a value outside ENVELOPE is a REVIEW row."""
    if not measured:
        return [row(f"MOTION_ENVELOPE:{shot_id}", None, "no motion summary for this shot")]
    out = {k: v for k, v in measured.items() if k in ENVELOPE and not ENVELOPE[k][0] <= float(v) <= ENVELOPE[k][1]}
    return [row(f"MOTION_ENVELOPE:{shot_id}", not out, f"{len(out)} of {len(measured)} motion value(s) outside the 2.5D envelope "
                "(drift/scale 3 %, parallax 1.5 %, velocity 0.25 %/s: design rule)", out, level=REVIEW)]
