"""Provisional map-quality checks behind an env flag.

Pure numeric checks; no image libraries, no rendering, no network. The thresholds are proposals from QUALITY_SPEC.md section 7.
"""

from __future__ import annotations

import os

ENV_VAR = "EXPLAINER_QUALITY_PROVISIONAL"

# provisional, owner approves on rendered samples
MIN_PRIMARY_LINE_WIDTH_PCT = 0.5
MIN_SECONDARY_LINE_WIDTH_PCT = 0.25
MIN_LABEL_CAP_HEIGHT_PCT = 2.5
MIN_LABEL_CONTRAST_RATIO = 4.5
GREEN_HUE_MIN_DEG = 80
GREEN_HUE_MAX_DEG = 160
GREEN_SATURATION_MIN_PCT = 35


def enabled() -> bool:
    """The flag is read on every call so a test or a live process can toggle it without re-importing."""
    return os.environ.get(ENV_VAR) == "1"


def check_line_width(kind: str, width_pct: float) -> list[str]:
    """Line width check; ``kind`` is "primary" or "secondary", width is a percentage of frame height."""
    problems: list[str] = []
    if kind == "primary" and width_pct < MIN_PRIMARY_LINE_WIDTH_PCT:
        problems.append(
            f"primary line width {width_pct:.2f}% is below the provisional minimum "
            f"{MIN_PRIMARY_LINE_WIDTH_PCT}% of frame height"
        )
    elif kind == "secondary" and width_pct < MIN_SECONDARY_LINE_WIDTH_PCT:
        problems.append(
            f"secondary line width {width_pct:.2f}% is below the provisional minimum "
            f"{MIN_SECONDARY_LINE_WIDTH_PCT}% of frame height"
        )
    return problems


def check_label(cap_height_pct: float, contrast_ratio: float) -> list[str]:
    """Label legibility check: cap height in percent of frame height and contrast ratio."""
    problems: list[str] = []
    if cap_height_pct < MIN_LABEL_CAP_HEIGHT_PCT:
        problems.append(
            f"label cap height {cap_height_pct:.2f}% is below the provisional minimum "
            f"{MIN_LABEL_CAP_HEIGHT_PCT}% of frame height"
        )
    if contrast_ratio < MIN_LABEL_CONTRAST_RATIO:
        problems.append(
            f"label contrast ratio {contrast_ratio:.2f} is below the provisional minimum "
            f"{MIN_LABEL_CONTRAST_RATIO}"
        )
    return problems


def check_green(hue_deg: float, saturation_pct: float) -> list[str]:
    """Green fill check: hue must be in the provisional green range and saturation must be high enough."""
    problems: list[str] = []
    if not (GREEN_HUE_MIN_DEG <= hue_deg <= GREEN_HUE_MAX_DEG):
        problems.append(
            f"green hue {hue_deg:.1f} degrees is outside the provisional green range "
            f"{GREEN_HUE_MIN_DEG}-{GREEN_HUE_MAX_DEG} degrees"
        )
    if saturation_pct < GREEN_SATURATION_MIN_PCT:
        problems.append(
            f"green saturation {saturation_pct:.1f}% is below the provisional minimum "
            f"{GREEN_SATURATION_MIN_PCT}%"
        )
    return problems


def quality_problems(items: list[dict]) -> list[str]:
    """Run all provisional checks over a list of item dicts. Returns [] when the flag is off."""
    if not enabled():
        return []
    problems: list[str] = []
    for item in items:
        typ = item.get("type")
        if typ == "line":
            problems.extend(check_line_width(str(item.get("kind", "")), float(item.get("width_pct", 0.0))))
        elif typ == "label":
            problems.extend(check_label(float(item.get("cap_height_pct", 0.0)), float(item.get("contrast_ratio", 0.0))))
        elif typ == "green":
            problems.extend(check_green(float(item.get("hue_deg", 0.0)), float(item.get("saturation_pct", 0.0))))
    return problems
