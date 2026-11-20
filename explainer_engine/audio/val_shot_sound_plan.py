"""Validate per-shot sound decision records for a film.

Requirement IDs: OR-A14, OR-A15, OR-A02, OR-A28, OR-C04.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Limits:
    min_reason_chars: int = 12
    filler_reasons: frozenset[str] = frozenset(
        {"n/a", "na", "none", "todo", "tbd", "-", "no reason", "because", "silent", "bed"}
    )
    action_kinds: frozenset[str] = frozenset({"map", "chart", "counter"})
    max_cues_per_shot: int = 6
    max_silent_share: float = 0.5
    severity: str = "REVIEW"


_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"shot_id", "kind", "bed", "silent_by_design", "reason", "cues"}
)


def _validate_shots(shots: Any) -> None:
    if not isinstance(shots, list):
        raise ValueError("shots must be a list of shot dictionaries.")

    seen_ids: set[str] = set()
    for idx, shot in enumerate(shots):
        if not isinstance(shot, dict):
            raise ValueError(f"Shot at index {idx} must be a dictionary.")

        missing = _REQUIRED_KEYS - shot.keys()
        if missing:
            raise ValueError(
                f"Shot at index {idx} is missing required keys: {sorted(missing)}."
            )

        shot_id = shot["shot_id"]
        if not isinstance(shot_id, str) or not shot_id.strip():
            raise ValueError(f"Shot at index {idx} must have a non-empty string shot_id.")
        if shot_id in seen_ids:
            raise ValueError(f"Duplicate shot_id detected: {shot_id!r}.")
        seen_ids.add(shot_id)

        if not isinstance(shot["kind"], str) or not shot["kind"].strip():
            raise ValueError(f"Shot {shot_id!r} must have a non-empty string kind.")

        bed = shot["bed"]
        if bed is not None and not isinstance(bed, str):
            raise ValueError(f"Shot {shot_id!r} field 'bed' must be str or None.")

        if not isinstance(shot["silent_by_design"], bool):
            raise ValueError(f"Shot {shot_id!r} field 'silent_by_design' must be a bool.")

        if not isinstance(shot["reason"], str):
            raise ValueError(f"Shot {shot_id!r} field 'reason' must be a str.")

        cues = shot["cues"]
        if not isinstance(cues, list) or not all(isinstance(c, dict) for c in cues):
            raise ValueError(f"Shot {shot_id!r} field 'cues' must be a list of dicts.")


def check(shots: list[dict[str, Any]], limits: Limits = Limits()) -> list[dict[str, str]]:
    """Validate per-shot sound design plans against SP-01 through SP-06."""
    if not isinstance(limits, Limits):
        raise ValueError("limits must be an instance of Limits.")

    _validate_shots(shots)

    if not shots:
        return []

    findings: list[dict[str, str]] = []
    normalized_fillers = {item.strip().lower() for item in limits.filler_reasons}
    silent_count = 0

    for shot in shots:
        shot_id: str = shot["shot_id"]
        kind: str = shot["kind"]
        bed: str | None = shot["bed"]
        silent_by_design: bool = shot["silent_by_design"]
        reason: str = shot["reason"]
        cues: list[dict[str, Any]] = shot["cues"]

        has_bed = bed is not None and len(bed.strip()) > 0

        if silent_by_design:
            silent_count += 1

        # SP-01
        if not has_bed and not silent_by_design:
            findings.append(
                {
                    "rule": "SP-01",
                    "severity": limits.severity,
                    "where": shot_id,
                    "detail": "Shot specifies neither a non-empty audio bed nor silent_by_design.",
                }
            )

        # SP-02
        if has_bed and silent_by_design:
            findings.append(
                {
                    "rule": "SP-02",
                    "severity": limits.severity,
                    "where": shot_id,
                    "detail": "Shot specifies both an audio bed and silent_by_design.",
                }
            )

        # SP-03
        stripped_reason = reason.strip()
        if (
            len(stripped_reason) < limits.min_reason_chars
            or stripped_reason.lower() in normalized_fillers
        ):
            findings.append(
                {
                    "rule": "SP-03",
                    "severity": limits.severity,
                    "where": shot_id,
                    "detail": (
                        f"Shot sound reason must be at least {limits.min_reason_chars} non-whitespace "
                        "characters and not a filler phrase."
                    ),
                }
            )

        # SP-04
        if kind in limits.action_kinds and not silent_by_design and len(cues) == 0:
            findings.append(
                {
                    "rule": "SP-04",
                    "severity": limits.severity,
                    "where": shot_id,
                    "detail": f"Action shot of kind '{kind}' is not silent_by_design and has zero cues.",
                }
            )

        # SP-05
        if round(len(cues) - limits.max_cues_per_shot, 6) > 0:
            findings.append(
                {
                    "rule": "SP-05",
                    "severity": limits.severity,
                    "where": shot_id,
                    "detail": (
                        f"Shot defines {len(cues)} cues, exceeding the budget of "
                        f"{limits.max_cues_per_shot}."
                    ),
                }
            )

    # SP-06
    silent_share = silent_count / len(shots)
    if round(silent_share - limits.max_silent_share, 6) > 0:
        findings.append(
            {
                "rule": "SP-06",
                "severity": limits.severity,
                "where": "film",
                "detail": (
                    f"Silent-by-design shots make up {round(silent_share, 6)} of the film, "
                    f"exceeding the maximum share of {limits.max_silent_share}."
                ),
            }
        )

    findings.sort(key=lambda item: (item["where"], item["rule"]))
    return findings
