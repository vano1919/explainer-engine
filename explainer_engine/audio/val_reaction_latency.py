"""Validator for audience-reaction cue latency relative to trigger event legibility.

Requirement IDs: OR-S26, OR-A15.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any


@dataclass(frozen=True)
class Limits:
    """Threshold configuration for reaction latency checks."""

    latency_s: dict[str, float] = field(
        default_factory=lambda: {"gasp": 0.2, "cheer": 0.5, "applause": 0.55, "laugh": 0.6}
    )
    tol_s: float = 0.15
    severity: str = "REVIEW"


def _is_valid_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value)


def _validate_inputs(reactions: list[dict[str, Any]], limits: Limits) -> None:
    if not isinstance(limits, Limits):
        raise ValueError("limits must be an instance of Limits.")
    if not isinstance(limits.latency_s, dict):
        raise ValueError("limits.latency_s must be a dictionary.")
    for k, v in limits.latency_s.items():
        if not isinstance(k, str) or not k:
            raise ValueError("limits.latency_s keys must be non-empty strings.")
        if not _is_valid_number(v) or v < 0:
            raise ValueError(f"limits.latency_s[{k!r}] must be a non-negative finite number.")
    if not _is_valid_number(limits.tol_s) or limits.tol_s < 0:
        raise ValueError("limits.tol_s must be a non-negative finite number.")
    if not isinstance(limits.severity, str) or not limits.severity:
        raise ValueError("limits.severity must be a non-empty string.")

    if not isinstance(reactions, list):
        raise ValueError("reactions must be a list of dictionaries.")

    required_keys = {"id", "kind", "t", "event_t"}
    for idx, item in enumerate(reactions):
        if not isinstance(item, dict):
            raise ValueError(f"reactions[{idx}] must be a dictionary.")
        missing = required_keys - item.keys()
        if missing:
            raise ValueError(f"reactions[{idx}] is missing required key(s): {sorted(missing)}.")
        if not isinstance(item["id"], str) or not item["id"]:
            raise ValueError(f"reactions[{idx}]['id'] must be a non-empty string.")
        if not isinstance(item["kind"], str) or not item["kind"]:
            raise ValueError(f"reactions[{idx}]['kind'] must be a non-empty string.")
        if not _is_valid_number(item["t"]):
            raise ValueError(f"reactions[{idx}]['t'] must be a finite number.")
        if not _is_valid_number(item["event_t"]):
            raise ValueError(f"reactions[{idx}]['event_t'] must be a finite number.")


def check(reactions: list[dict[str, Any]], limits: Limits = Limits()) -> list[dict[str, str]]:
    """Check that audience-reaction cues start after trigger legibility within expected latency."""
    _validate_inputs(reactions, limits)

    if not reactions:
        return []

    findings: list[dict[str, str]] = []

    for item in reactions:
        reaction_id: str = item["id"]
        kind: str = item["kind"]
        cue_t = float(item["t"])
        event_t = float(item["event_t"])

        if round(cue_t - event_t, 6) < 0:
            findings.append(
                {
                    "rule": "LAT-01",
                    "severity": limits.severity,
                    "where": reaction_id,
                    "detail": (
                        f"Reaction cue {reaction_id!r} starts at {cue_t}s, "
                        f"which is before trigger event legibility at {event_t}s."
                    ),
                }
            )
            continue

        if kind not in limits.latency_s:
            findings.append(
                {
                    "rule": "LAT-03",
                    "severity": limits.severity,
                    "where": reaction_id,
                    "detail": f"Reaction kind {kind!r} for cue {reaction_id!r} has no configured latency entry.",
                }
            )
            continue

        expected_t = event_t + float(limits.latency_s[kind])
        offset = round(abs(cue_t - expected_t), 6)
        if round(offset - limits.tol_s, 6) > 0:
            findings.append(
                {
                    "rule": "LAT-02",
                    "severity": limits.severity,
                    "where": reaction_id,
                    "detail": (
                        f"Reaction cue {reaction_id!r} ({kind}) starts at {cue_t}s, "
                        f"offset by {offset}s from expected {round(expected_t, 6)}s "
                        f"(tolerance {limits.tol_s}s)."
                    ),
                }
            )

    findings.sort(key=lambda f: (f["where"], f["rule"]))
    return findings
