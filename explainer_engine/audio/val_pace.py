"""Narration pace per zone and overall validator (OR-A22, OR-A10)."""

from __future__ import annotations

from dataclasses import dataclass

import math

from typing import Any

_EXPECTED_ZONES: frozenset[str] = frozenset({"hook", "middle", "finale"})

@dataclass(frozen=True)
class Limits:
    """Thresholds and severity for narration pace validation."""

    target_wpm: float = 170.0  # OR-A22, owner's number
    band_pct: float = 10.0  # overall must be within target +- band_pct percent (hypothesis)
    zone_gap_wpm: float = 5.0  # hook and finale must beat the middle by at least this many wpm (hypothesis)
    min_words_per_zone: int = 5  # a zone with fewer words is not measured
    severity: str = "REVIEW"

def _is_real_number(value: Any) -> bool:
    """Return True if value is an int or float (excluding bool) and is finite."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))

def _validate_word(word_item: Any, index: int) -> tuple[float, float]:
    """Validate a single word dictionary and return (start, end)."""
    if not isinstance(word_item, dict):
        raise ValueError(f"Word at index {index} must be a dict, got {type(word_item).__name__}.")
    for required_key in ("word", "start", "end"):
        if required_key not in word_item:
            raise ValueError(f"Word at index {index} missing required key '{required_key}'.")

    word_text = word_item["word"]
    if not isinstance(word_text, str):
        raise ValueError(f"Word at index {index} key 'word' must be a str, got {type(word_text).__name__}.")

    start = word_item["start"]
    end = word_item["end"]
    if not _is_real_number(start):
        raise ValueError(f"Word at index {index} key 'start' must be a finite number.")
    if not _is_real_number(end):
        raise ValueError(f"Word at index {index} key 'end' must be a finite number.")

    start_f = float(start)
    end_f = float(end)
    if end_f < start_f:
        raise ValueError(f"Word at index {index} has end ({end_f}) < start ({start_f}).")
    return start_f, end_f

def _validate_words(words: Any) -> list[tuple[float, float]]:
    """Validate the words sequence without mutating it and return list of (start, end)."""
    if not isinstance(words, list):
        raise ValueError(f"'words' must be a list, got {type(words).__name__}.")

    parsed: list[tuple[float, float]] = []
    prev_start: float | None = None
    for idx, item in enumerate(words):
        start_f, end_f = _validate_word(item, idx)
        if prev_start is not None and round(start_f - prev_start, 6) < 0:
            raise ValueError(f"'words' must be sorted by start time; index {idx} starts before index {idx - 1}.")
        prev_start = start_f
        parsed.append((start_f, end_f))
    return parsed

def _validate_zone(zone: Any, require_positive_duration: bool = True) -> tuple[str, float, float]:
    """Validate a single zone dictionary and return (name, start, end)."""
    if not isinstance(zone, dict):
        raise ValueError(f"Zone must be a dict, got {type(zone).__name__}.")
    for required_key in ("zone", "start", "end"):
        if required_key not in zone:
            raise ValueError(f"Zone missing required key '{required_key}'.")

    name = zone["zone"]
    if not isinstance(name, str) or not name:
        raise ValueError("Zone key 'zone' must be a non-empty str.")

    start = zone["start"]
    end = zone["end"]
    if not _is_real_number(start):
        raise ValueError(f"Zone '{name}' key 'start' must be a finite number.")
    if not _is_real_number(end):
        raise ValueError(f"Zone '{name}' key 'end' must be a finite number.")

    start_f = float(start)
    end_f = float(end)
    if require_positive_duration:
        if end_f <= start_f:
            raise ValueError(f"Zone '{name}' must have end > start, got start={start_f}, end={end_f}.")
    elif end_f < start_f:
        raise ValueError(f"Zone '{name}' must have end >= start, got start={start_f}, end={end_f}.")
    return name, start_f, end_f

def _validate_limits(limits: Any) -> Limits:
    """Validate Limits instance fields."""
    if not isinstance(limits, Limits):
        raise ValueError(f"'limits' must be a Limits instance, got {type(limits).__name__}.")
    if not _is_real_number(limits.target_wpm) or limits.target_wpm <= 0:
        raise ValueError("'limits.target_wpm' must be a positive number.")
    if not _is_real_number(limits.band_pct) or limits.band_pct < 0:
        raise ValueError("'limits.band_pct' must be a non-negative number.")
    if not _is_real_number(limits.zone_gap_wpm):
        raise ValueError("'limits.zone_gap_wpm' must be a finite number.")
    if not isinstance(limits.min_words_per_zone, int) or isinstance(limits.min_words_per_zone, bool):
        raise ValueError("'limits.min_words_per_zone' must be an int.")
    if limits.min_words_per_zone < 0:
        raise ValueError("'limits.min_words_per_zone' must be non-negative.")
    if not isinstance(limits.severity, str) or not limits.severity:
        raise ValueError("'limits.severity' must be a non-empty str.")
    return limits

def _count_words_in_zone(parsed_words: list[tuple[float, float]], start: float, end: float) -> int:
    """Count words whose start falls in [start, end)."""
    return sum(1 for word_start, _ in parsed_words if start <= word_start < end)

def zone_wpm(words: list[dict], zone: dict) -> float | None:
    """Compute words per minute inside a single zone [zone.start, zone.end).

    Words whose start timestamp satisfies zone.start <= word.start < zone.end are counted.
    Returns None if zero words fall in the zone. Raises ValueError on invalid input or end <= start.
    """
    parsed_words = _validate_words(words)
    _, start_f, end_f = _validate_zone(zone, require_positive_duration=True)
    n_words = _count_words_in_zone(parsed_words, start_f, end_f)
    if n_words == 0:
        return None
    duration_minutes = (end_f - start_f) / 60.0
    return n_words / duration_minutes

def overall_wpm(words: list[dict]) -> float | None:
    """Compute overall words per minute from first word start to last word end.

    Returns None when fewer than 2 words are present. Raises ValueError on invalid input or non-positive span.
    """
    parsed_words = _validate_words(words)
    if len(parsed_words) < 2:
        return None
    first_start = parsed_words[0][0]
    last_end = parsed_words[-1][1]
    span = last_end - first_start
    if span <= 0.0:
        raise ValueError(f"Overall word span must be positive, got last.end ({last_end}) <= first.start ({first_start}).")
    return len(parsed_words) / (span / 60.0)

def check(words: list[dict], zones: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Validate overall narration pace and per-zone pace relationships (OR-A22, OR-A10).

    Rules checked:
    - PACE-01: overall pace outside target_wpm +- band_pct percent (where="overall").
    - PACE-02: hook wpm < middle wpm + zone_gap_wpm (where="hook").
    - PACE-03: finale wpm < middle wpm + zone_gap_wpm (where="finale").
    - PACE-04: a zone has fewer than min_words_per_zone words, skipping PACE-02/03 for it (where=<zone>).
    """
    valid_limits = _validate_limits(limits)
    parsed_words = _validate_words(words)

    if not isinstance(zones, list) or len(zones) != 3:
        raise ValueError("'zones' must be a list of exactly 3 zone dicts ('hook', 'middle', 'finale').")

    zone_map: dict[str, tuple[float, float]] = {}
    for zone_item in zones:
        name, start_f, end_f = _validate_zone(zone_item, require_positive_duration=True)
        if name not in _EXPECTED_ZONES:
            raise ValueError(f"Unexpected zone name '{name}'; expected one of {sorted(_EXPECTED_ZONES)}.")
        if name in zone_map:
            raise ValueError(f"Duplicate zone name '{name}'; each of 'hook', 'middle', 'finale' must appear once.")
        zone_map[name] = (start_f, end_f)

    findings: list[dict] = []

    # PACE-01: Overall pace check
    total_wpm = overall_wpm(words)
    if total_wpm is not None:
        low_bound = valid_limits.target_wpm * (1.0 - valid_limits.band_pct / 100.0)
        high_bound = valid_limits.target_wpm * (1.0 + valid_limits.band_pct / 100.0)
        if round(total_wpm - low_bound, 6) < 0 or round(total_wpm - high_bound, 6) > 0:
            findings.append(
                {
                    "rule": "PACE-01",
                    "severity": valid_limits.severity,
                    "where": "overall",
                    "detail": (
                        f"Overall narration rate is {total_wpm:.1f} wpm, outside the "
                        f"{low_bound:.1f} to {high_bound:.1f} wpm band."
                    ),
                }
            )

    # Measure zone word counts and WPM
    zone_counts: dict[str, int] = {}
    zone_rates: dict[str, float] = {}
    for name in ("hook", "middle", "finale"):
        z_start, z_end = zone_map[name]
        count = _count_words_in_zone(parsed_words, z_start, z_end)
        zone_counts[name] = count
        if count < valid_limits.min_words_per_zone:
            findings.append(
                {
                    "rule": "PACE-04",
                    "severity": valid_limits.severity,
                    "where": name,
                    "detail": (
                        f"Zone '{name}' has {count} words, below the minimum "
                        f"{valid_limits.min_words_per_zone} words required for pace comparison."
                    ),
                }
            )
        else:
            duration_minutes = (z_end - z_start) / 60.0
            zone_rates[name] = count / duration_minutes

    # PACE-02 & PACE-03: Compare hook and finale against middle when middle and target zone are both measurable
    if "middle" in zone_rates:
        middle_rate = zone_rates["middle"]
        required_rate = middle_rate + valid_limits.zone_gap_wpm

        if "hook" in zone_rates:
            hook_rate = zone_rates["hook"]
            if round(hook_rate - required_rate, 6) < 0:
                findings.append(
                    {
                        "rule": "PACE-02",
                        "severity": valid_limits.severity,
                        "where": "hook",
                        "detail": (
                            f"Hook rate is {hook_rate:.1f} wpm, below the required "
                            f"{required_rate:.1f} wpm ({middle_rate:.1f} middle wpm plus "
                            f"{valid_limits.zone_gap_wpm:.1f} wpm gap)."
                        ),
                    }
                )

        if "finale" in zone_rates:
            finale_rate = zone_rates["finale"]
            if round(finale_rate - required_rate, 6) < 0:
                findings.append(
                    {
                        "rule": "PACE-03",
                        "severity": valid_limits.severity,
                        "where": "finale",
                        "detail": (
                            f"Finale rate is {finale_rate:.1f} wpm, below the required "
                            f"{required_rate:.1f} wpm ({middle_rate:.1f} middle wpm plus "
                            f"{valid_limits.zone_gap_wpm:.1f} wpm gap)."
                        ),
                    }
                )

    findings.sort(key=lambda item: (item["rule"], item["where"]))
    return findings
