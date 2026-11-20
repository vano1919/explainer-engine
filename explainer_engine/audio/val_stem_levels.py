"""Validate measured per-stem peak levels (dBFS) against layer range targets.

Requirement IDs: OR-E03, OR-A24.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


@dataclass(frozen=True)
class Limits:
    """Configurable dBFS range limits and severity for stem peak validation."""

    ranges: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "dialogue": (-9.0, -3.0),
            "music_under_speech": (-24.0, -18.0),
            "music_solo": (-12.0, -6.0),
            "sfx": (-12.0, -6.0),
            "ambience": (-36.0, -24.0),
            "master": (-3.0, -1.0),
        }
    )
    dense_sfx_drop_db: float = 3.0
    severity: str = "REVIEW"


def _validate_limits(limits: Limits) -> None:
    if not isinstance(limits, Limits):
        raise ValueError("limits must be an instance of Limits")
    if not isinstance(limits.ranges, dict):
        raise ValueError("limits.ranges must be a dict")
    if (
        isinstance(limits.dense_sfx_drop_db, bool)
        or not isinstance(limits.dense_sfx_drop_db, (int, float))
        or math.isnan(limits.dense_sfx_drop_db)
        or math.isinf(limits.dense_sfx_drop_db)
    ):
        raise ValueError("limits.dense_sfx_drop_db must be a finite number")
    if not isinstance(limits.severity, str) or not limits.severity:
        raise ValueError("limits.severity must be a non-empty string")
    for layer, bounds in limits.ranges.items():
        if not isinstance(layer, str) or not layer:
            raise ValueError("limits.ranges keys must be non-empty strings")
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
            raise ValueError(f"limits.ranges[{layer!r}] must be a (low, high) pair")
        low, high = bounds
        if (
            isinstance(low, bool)
            or isinstance(high, bool)
            or not isinstance(low, (int, float))
            or not isinstance(high, (int, float))
            or math.isnan(low)
            or math.isnan(high)
        ):
            raise ValueError(f"limits.ranges[{layer!r}] bounds must be numeric and not NaN")
        if round(float(high) - float(low), 6) < 0:
            raise ValueError(f"limits.ranges[{layer!r}] high bound must be >= low bound")


def _validate_and_extract_stem(stem: Any, index: int) -> tuple[str, str, float, bool]:
    if not isinstance(stem, dict):
        raise ValueError(f"stems[{index}] must be a dict")

    for required_key in ("id", "layer", "peak_dbfs"):
        if required_key not in stem:
            raise ValueError(f"stems[{index}] missing required key {required_key!r}")

    stem_id = stem["id"]
    if not isinstance(stem_id, str) or not stem_id:
        raise ValueError(f"stems[{index}]['id'] must be a non-empty string")

    layer = stem["layer"]
    if not isinstance(layer, str) or not layer:
        raise ValueError(f"stems[{index}]['layer'] must be a non-empty string")

    peak_raw = stem["peak_dbfs"]
    if isinstance(peak_raw, bool) or not isinstance(peak_raw, (int, float)):
        raise ValueError(f"stems[{index}]['peak_dbfs'] must be a float or int")
    peak_dbfs = float(peak_raw)
    if math.isnan(peak_dbfs):
        raise ValueError(f"stems[{index}]['peak_dbfs'] must not be NaN")

    dense_raw = stem.get("dense", False)
    if not isinstance(dense_raw, bool):
        raise ValueError(f"stems[{index}]['dense'] must be a bool")

    return stem_id, layer, peak_dbfs, dense_raw


def check(stems: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Check measured per-stem peak levels (dBFS) against configured layer ranges.

    STEM-01 above range, STEM-02 below range, STEM-03 silent (-inf or < -120.0, suppresses STEM-02),
    STEM-04 layer has no range.
    """
    if not isinstance(stems, list):
        raise ValueError("stems must be a list of dicts")
    _validate_limits(limits)

    if not stems:
        return []

    findings: list[dict] = []

    for idx, raw_stem in enumerate(stems):
        stem_id, layer, peak_dbfs, dense = _validate_and_extract_stem(raw_stem, idx)

        if layer not in limits.ranges:
            findings.append(
                {
                    "rule": "STEM-04",
                    "severity": limits.severity,
                    "where": stem_id,
                    "detail": f"Stem layer '{layer}' has no configured target range in the level table.",
                }
            )
            continue

        raw_low, raw_high = limits.ranges[layer]
        low = float(raw_low)
        high = float(raw_high)
        if layer == "sfx" and dense:
            drop = float(limits.dense_sfx_drop_db)
            low -= drop
            high -= drop

        if math.isinf(peak_dbfs) and peak_dbfs < 0:
            findings.append(
                {
                    "rule": "STEM-03",
                    "severity": limits.severity,
                    "where": stem_id,
                    "detail": (
                        f"Stem layer '{layer}' has a silent peak of -inf dBFS "
                        f"(below -120.0 dBFS threshold for range [{low:.1f}, {high:.1f}] dBFS)."
                    ),
                }
            )
            continue

        if round(peak_dbfs - (-120.0), 6) < 0:
            findings.append(
                {
                    "rule": "STEM-03",
                    "severity": limits.severity,
                    "where": stem_id,
                    "detail": (
                        f"Stem layer '{layer}' peak {peak_dbfs:.2f} dBFS is below -120.0 dBFS "
                        f"(silent stem; target range is [{low:.1f}, {high:.1f}] dBFS)."
                    ),
                }
            )
            continue

        if round(peak_dbfs - high, 6) > 0:
            findings.append(
                {
                    "rule": "STEM-01",
                    "severity": limits.severity,
                    "where": stem_id,
                    "detail": (
                        f"Stem layer '{layer}' peak {peak_dbfs:.2f} dBFS exceeds "
                        f"target range [{low:.1f}, {high:.1f}] dBFS."
                    ),
                }
            )
        elif round(peak_dbfs - low, 6) < 0:
            findings.append(
                {
                    "rule": "STEM-02",
                    "severity": limits.severity,
                    "where": stem_id,
                    "detail": (
                        f"Stem layer '{layer}' peak {peak_dbfs:.2f} dBFS is below "
                        f"target range [{low:.1f}, {high:.1f}] dBFS."
                    ),
                }
            )

    findings.sort(key=lambda item: (item["where"], item["rule"]))
    return findings
