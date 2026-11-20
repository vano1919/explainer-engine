"""Audio cut timing validator against word-level transcript timestamps.

Requirement IDs: OR-A23
"""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Limits:
    """Thresholds and severity configuration for word-boundary cut validation."""

    pad_min_s: float = 0.030
    fade_min_ms: float = 30.0
    severity: str = "REVIEW"


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _validate_limits(limits: Limits) -> None:
    if not isinstance(limits, Limits):
        raise ValueError("limits must be an instance of Limits.")
    if not _is_finite_number(limits.pad_min_s) or limits.pad_min_s < 0:
        raise ValueError("limits.pad_min_s must be a non-negative finite number.")
    if not _is_finite_number(limits.fade_min_ms) or limits.fade_min_ms < 0:
        raise ValueError("limits.fade_min_ms must be a non-negative finite number.")
    if not isinstance(limits.severity, str) or not limits.severity.strip():
        raise ValueError("limits.severity must be a non-empty string.")


def _validate_words(words: list[dict]) -> list[tuple[str, float, float]]:
    if not isinstance(words, list):
        raise ValueError("words must be a list of word dicts.")

    parsed: list[tuple[str, float, float]] = []
    prev_end: float | None = None

    for idx, item in enumerate(words):
        if not isinstance(item, dict):
            raise ValueError(f"words[{idx}] must be a dict.")
        for key in ("word", "start", "end"):
            if key not in item:
                raise ValueError(f"words[{idx}] is missing required key '{key}'.")

        word_text = item["word"]
        if not isinstance(word_text, str):
            raise ValueError(f"words[{idx}]['word'] must be a str.")

        raw_start = item["start"]
        raw_end = item["end"]
        if not _is_finite_number(raw_start) or not _is_finite_number(raw_end):
            raise ValueError(f"words[{idx}] 'start' and 'end' must be finite numbers.")

        start = float(raw_start)
        end = float(raw_end)

        if round(end - start, 6) < 0:
            raise ValueError(f"words[{idx}] has end ({end}) < start ({start}).")

        if prev_end is not None and round(start - prev_end, 6) < 0:
            raise ValueError(
                f"words[{idx}] starts at {start}, overlapping or preceding previous word end {prev_end}."
            )

        parsed.append((word_text, start, end))
        prev_end = end

    return parsed


def _validate_cuts(cuts: list[dict]) -> list[tuple[float, float | None]]:
    if not isinstance(cuts, list):
        raise ValueError("cuts must be a list of cut dicts.")

    parsed: list[tuple[float, float | None]] = []
    for idx, item in enumerate(cuts):
        if not isinstance(item, dict):
            raise ValueError(f"cuts[{idx}] must be a dict.")
        for key in ("t", "fade_ms"):
            if key not in item:
                raise ValueError(f"cuts[{idx}] is missing required key '{key}'.")

        raw_t = item["t"]
        if not _is_finite_number(raw_t):
            raise ValueError(f"cuts[{idx}]['t'] must be a finite number.")
        t_val = float(raw_t)

        raw_fade = item["fade_ms"]
        fade_val: float | None
        if raw_fade is None:
            fade_val = None
        elif _is_finite_number(raw_fade):
            fade_val = float(raw_fade)
            if round(fade_val, 6) < 0:
                raise ValueError(f"cuts[{idx}]['fade_ms'] cannot be negative.")
        else:
            raise ValueError(f"cuts[{idx}]['fade_ms'] must be a finite number or None.")

        parsed.append((t_val, fade_val))

    return parsed


def check(words: list[dict], cuts: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Validate audio cut timestamps and fade durations against word-level transcript timings."""
    _validate_limits(limits)
    parsed_words = _validate_words(words)
    parsed_cuts = _validate_cuts(cuts)

    if not parsed_cuts:
        return []

    if not parsed_words:
        raise ValueError("words cannot be empty when cuts are provided.")

    raw_findings: list[tuple[float, str, dict]] = []
    pad_min = float(limits.pad_min_s)
    fade_min = float(limits.fade_min_ms)

    for t_val, fade_val in parsed_cuts:
        where = f"{t_val:.3f}s"

        inside_word: tuple[str, float, float] | None = None
        for word_text, w_start, w_end in parsed_words:
            if round(t_val - w_start, 6) > 0 and round(w_end - t_val, 6) > 0:
                inside_word = (word_text, w_start, w_end)
                break

        if inside_word is not None:
            word_text, w_start, w_end = inside_word
            raw_findings.append(
                (
                    t_val,
                    "CUT-01",
                    {
                        "rule": "CUT-01",
                        "severity": limits.severity,
                        "where": where,
                        "detail": (
                            f"Cut at {t_val:.3f}s falls inside word '{word_text}' "
                            f"({w_start:.3f}s to {w_end:.3f}s)."
                        ),
                    },
                )
            )
        else:
            prev_word: tuple[str, float, float] | None = None
            next_word: tuple[str, float, float] | None = None

            for word_entry in parsed_words:
                _, w_start, w_end = word_entry
                if round(w_end - t_val, 6) <= 0:
                    prev_word = word_entry
                elif round(w_start - t_val, 6) >= 0 and next_word is None:
                    next_word = word_entry

            too_close_reasons: list[str] = []
            if prev_word is not None:
                dist_prev = round(t_val - prev_word[2], 6)
                if dist_prev < round(pad_min, 6):
                    too_close_reasons.append(
                        f"{dist_prev:.3f}s after previous word '{prev_word[0]}' end ({prev_word[2]:.3f}s)"
                    )
            if next_word is not None:
                dist_next = round(next_word[1] - t_val, 6)
                if dist_next < round(pad_min, 6):
                    too_close_reasons.append(
                        f"{dist_next:.3f}s before next word '{next_word[0]}' start ({next_word[1]:.3f}s)"
                    )

            if too_close_reasons:
                reason_text = " and ".join(too_close_reasons)
                raw_findings.append(
                    (
                        t_val,
                        "CUT-02",
                        {
                            "rule": "CUT-02",
                            "severity": limits.severity,
                            "where": where,
                            "detail": f"Cut at {t_val:.3f}s is within minimum padding ({pad_min:.3f}s): {reason_text}.",
                        },
                    )
                )

        if fade_val is None:
            raw_findings.append(
                (
                    t_val,
                    "CUT-03",
                    {
                        "rule": "CUT-03",
                        "severity": limits.severity,
                        "where": where,
                        "detail": f"Cut at {t_val:.3f}s is missing fade_ms (minimum required is {fade_min:.1f}ms).",
                    },
                )
            )
        elif round(fade_val - fade_min, 6) < 0:
            raw_findings.append(
                (
                    t_val,
                    "CUT-03",
                    {
                        "rule": "CUT-03",
                        "severity": limits.severity,
                        "where": where,
                        "detail": (
                            f"Cut at {t_val:.3f}s has fade_ms of {fade_val:.1f}ms, "
                            f"below minimum {fade_min:.1f}ms."
                        ),
                    },
                )
            )

    raw_findings.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in raw_findings]
