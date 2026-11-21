"""Provisional no-melt quality checks, gated behind the same flag as the provisional map checks.

Values are from QUALITY_SPEC.md section 7 PROPOSALS and are not yet approved;
they render no verdict until the owner approves them on rendered samples.
"""
from __future__ import annotations

import os

# provisional, owner approves on rendered samples
T9_RESIDUAL_MOTION_PCT_MAX = 0.05
# provisional, owner approves on rendered samples
T10_RESIDUAL_DISPLACEMENT_PCT_MAX = 0.2

ALLOWLIST = frozenset({"clouds", "fire", "smoke", "light"})


def enabled() -> bool:
    return os.environ.get("EXPLAINER_QUALITY_PROVISIONAL") == "1"


def check_frame_motion(residual_pct: float) -> list[str]:
    if residual_pct <= T9_RESIDUAL_MOTION_PCT_MAX:
        return []
    return [f"residual motion per frame {residual_pct}% exceeds T9 maximum {T9_RESIDUAL_MOTION_PCT_MAX}%"]


def check_shot_motion(residual_pct: float) -> list[str]:
    if residual_pct <= T10_RESIDUAL_DISPLACEMENT_PCT_MAX:
        return []
    return [
        f"residual displacement over shot {residual_pct}% exceeds T10 maximum {T10_RESIDUAL_DISPLACEMENT_PCT_MAX}%"
    ]


def effect_allowed(effect: str) -> bool:
    return effect.strip().lower() in ALLOWLIST


def no_melt_problems(items: list[dict]) -> list[str]:
    if not enabled():
        return []
    problems = []
    for item in items:
        effect = item.get("effect") or ""
        if not effect_allowed(effect):
            problems.append(f"effect {effect!r} is not on the provisional no-melt allowlist")
        frame_pct = item.get("frame_pct")
        if frame_pct is not None:
            problems.extend(check_frame_motion(frame_pct))
        shot_pct = item.get("shot_pct")
        if shot_pct is not None:
            problems.extend(check_shot_motion(shot_pct))
    return problems
