"""Sound licence validator for audio masters (Requirements: OR-A16, OR-A17).

Validates per-item licence records without turning licence metadata into a
quality verdict for sound effects or ambience.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_VALID_CLASSES: frozenset[str] = frozenset({"music", "sfx", "ambience"})
_REQUIRED_KEYS: frozenset[str] = frozenset({"id", "class", "source", "licence", "licence_checked"})


@dataclass(frozen=True)
class Limits:
    banned_markers: tuple[str, ...] = ("bbc remarc", "bbc_remarc", "bbc-remarc")
    banned_ids: frozenset[str] = frozenset()
    severity: str = "REVIEW"


def _validate_inputs(items: list[dict[str, Any]], monetised: bool, limits: Limits) -> None:
    if not isinstance(items, list):
        raise ValueError("items must be a list of dicts")
    if not isinstance(monetised, bool):
        raise ValueError("monetised must be a bool")
    if not isinstance(limits, Limits):
        raise ValueError("limits must be a Limits instance")


def _validate_item(item: Any, index: int) -> tuple[str, str, str, str, bool]:
    if not isinstance(item, dict):
        raise ValueError(f"item at index {index} must be a dict")

    missing = _REQUIRED_KEYS - item.keys()
    if missing:
        raise ValueError(f"item at index {index} missing required keys: {sorted(missing)}")

    item_id = item["id"]
    item_class = item["class"]
    source = item["source"]
    licence = item["licence"]
    licence_checked = item["licence_checked"]

    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError(f"item at index {index} 'id' must be a non-empty str")
    if not isinstance(item_class, str) or item_class not in _VALID_CLASSES:
        raise ValueError(
            f"item '{item_id}' has invalid class {item_class!r}; expected one of {sorted(_VALID_CLASSES)}"
        )
    if not isinstance(source, str):
        raise ValueError(f"item '{item_id}' 'source' must be a str")
    if not isinstance(licence, str):
        raise ValueError(f"item '{item_id}' 'licence' must be a str")
    if not isinstance(licence_checked, bool):
        raise ValueError(f"item '{item_id}' 'licence_checked' must be a bool")

    return item_id, item_class, source, licence, licence_checked


def check(items: list[dict[str, Any]], monetised: bool, limits: Limits = Limits()) -> list[dict[str, str]]:
    """Validate sound item licence records and banned library usage in a master (LIC-01..LIC-03)."""
    _validate_inputs(items, monetised, limits)

    findings: list[dict[str, str]] = []
    markers_lower = tuple(marker.lower() for marker in limits.banned_markers)

    for index, item in enumerate(items):
        item_id, item_class, source, licence, licence_checked = _validate_item(item, index)
        licence_stripped = licence.strip()

        if item_class == "music":
            if not licence_stripped or licence_checked is not True:
                findings.append(
                    {
                        "rule": "LIC-01",
                        "severity": limits.severity,
                        "where": item_id,
                        "detail": f"Music item '{item_id}' has a missing licence or an unchecked licence record.",
                    }
                )
        else:
            if not licence_stripped:
                findings.append(
                    {
                        "rule": "LIC-02",
                        "severity": limits.severity,
                        "where": item_id,
                        "detail": f"Sound item '{item_id}' of class '{item_class}' is missing a recorded licence.",
                    }
                )

        if monetised:
            source_lower = source.lower()
            licence_lower = licence.lower()
            in_banned_ids = item_id in limits.banned_ids
            has_banned_marker = any(
                marker in source_lower or marker in licence_lower for marker in markers_lower
            )
            if in_banned_ids or has_banned_marker:
                findings.append(
                    {
                        "rule": "LIC-03",
                        "severity": limits.severity,
                        "where": item_id,
                        "detail": f"Sound item '{item_id}' matches a banned library in a monetised master.",
                    }
                )

    findings.sort(key=lambda f: (f["where"], f["rule"]))
    return findings
