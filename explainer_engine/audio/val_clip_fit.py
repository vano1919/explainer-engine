"""Validate that spoken lines fit cleanly within their matched video clips.

Requirement IDs:
  - OR-A29: A character always finishes the spoken line inside the clip.
  - OR-S28: Clip length comes from the measured read of its line, never the other way round.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Any

@dataclass(frozen=True)
class Limits:
    """Threshold configuration for clip-to-line fit validation."""

    tail_margin_s: float = 0.25  # line must end at least this long before clip ends (hypothesis)
    lead_tolerance_s: float = 0.05  # line may start this early before clip starts (word-time drift)
    max_slack_s: float = 2.0  # clip length may exceed line length by at most this (hypothesis)
    severity: str = "REVIEW"

def _is_real_number(value: Any) -> bool:
    """Return True for finite int/float values, excluding booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))

def _validate_limits(limits: Limits) -> None:
    """Ensure the Limits instance has valid field types and non-negative thresholds."""
    if not isinstance(limits, Limits):
        raise ValueError("limits must be a Limits instance.")
    for field_name in ("tail_margin_s", "lead_tolerance_s", "max_slack_s"):
        val = getattr(limits, field_name)
        if not _is_real_number(val) or float(val) < 0.0:
            raise ValueError(f"limits.{field_name} must be a non-negative finite number.")
    if not isinstance(limits.severity, str) or not limits.severity.strip():
        raise ValueError("limits.severity must be a non-empty string.")

def _validate_item(item: Any, *, kind: str, index: int, required_str_keys: tuple[str, ...], strict_positive_duration: bool) -> dict[str, Any]:
    """Validate structure, types, and time bounds of a single line or clip dict."""
    if not isinstance(item, dict):
        raise ValueError(f"{kind}[{index}] must be a dict.")

    for key in required_str_keys:
        if key not in item:
            raise ValueError(f"{kind}[{index}] is missing required key '{key}'.")
        val = item[key]
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"{kind}[{index}]['{key}'] must be a non-empty string.")

    for key in ("start", "end"):
        if key not in item:
            raise ValueError(f"{kind}[{index}] is missing required key '{key}'.")
        if not _is_real_number(item[key]):
            raise ValueError(f"{kind}[{index}]['{key}'] must be a finite number.")

    start = float(item["start"])
    end = float(item["end"])
    if strict_positive_duration:
        if end <= start:
            raise ValueError(f"{kind}[{index}] end ({end}) must be strictly greater than start ({start}).")
    else:
        if end < start:
            raise ValueError(f"{kind}[{index}] end ({end}) must not be less than start ({start}).")

    parsed: dict[str, Any] = {key: item[key] for key in required_str_keys}
    parsed["start"] = start
    parsed["end"] = end
    return parsed

def check(lines: list[dict], clips: list[dict], limits: Limits = Limits()) -> list[dict]:
    """Validate that spoken lines fit within their corresponding clip windows.

    Rules checked:
    - CLIP-01: line.end > clip.end - tail_margin_s (line cut off or lacks tail room)
    - CLIP-02: line.start < clip.start - lead_tolerance_s (line starts before clip)
    - CLIP-03: (clip.end - clip.start) - (line.end - line.start) > max_slack_s (clip longer than read needs)
    - CLIP-04: no clip with the line's shot_id
    """
    _validate_limits(limits)

    if not isinstance(lines, list):
        raise ValueError("lines must be a list of dicts.")
    if not isinstance(clips, list):
        raise ValueError("clips must be a list of dicts.")

    parsed_lines = [
        _validate_item(line, kind="lines", index=idx, required_str_keys=("id", "shot_id"), strict_positive_duration=False)
        for idx, line in enumerate(lines)
    ]

    parsed_clips = [
        _validate_item(clip, kind="clips", index=idx, required_str_keys=("shot_id",), strict_positive_duration=True)
        for idx, clip in enumerate(clips)
    ]

    if not parsed_lines:
        return []

    clips_by_shot: dict[str, dict[str, Any]] = {}
    for clip in parsed_clips:
        shot_id = clip["shot_id"]
        if shot_id in clips_by_shot:
            raise ValueError(f"Duplicate clip found for shot_id '{shot_id}'.")
        clips_by_shot[shot_id] = clip

    lines_by_shot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_line_ids: set[str] = set()
    for line in parsed_lines:
        line_id = line["id"]
        if line_id in seen_line_ids:
            raise ValueError(f"Duplicate line id '{line_id}'.")
        seen_line_ids.add(line_id)
        lines_by_shot[line["shot_id"]].append(line)

    tail_margin = float(limits.tail_margin_s)
    lead_tolerance = float(limits.lead_tolerance_s)
    max_slack = float(limits.max_slack_s)

    sortable_findings: list[tuple[float, str, str, dict[str, str]]] = []

    for shot_id, shot_lines in lines_by_shot.items():
        if len(shot_lines) == 1:
            where_label = shot_lines[0]["id"]
            line_start = shot_lines[0]["start"]
            line_end = shot_lines[0]["end"]
        else:
            where_label = shot_id
            line_start = min(item["start"] for item in shot_lines)
            line_end = max(item["end"] for item in shot_lines)

        clip = clips_by_shot.get(shot_id)
        if clip is None:
            finding = {
                "rule": "CLIP-04",
                "severity": limits.severity,
                "where": where_label,
                "detail": f"No clip matches shot_id '{shot_id}' for line span {line_start:.3f}s..{line_end:.3f}s.",
            }
            sortable_findings.append((line_start, where_label, "CLIP-04", finding))
            continue

        clip_start = clip["start"]
        clip_end = clip["end"]

        # CLIP-01: line.end > clip.end - tail_margin_s
        tail_overflow = round(line_end - (clip_end - tail_margin), 6)
        if tail_overflow > 0.0:
            available_tail = round(clip_end - line_end, 6)
            finding = {
                "rule": "CLIP-01",
                "severity": limits.severity,
                "where": where_label,
                "detail": (
                    f"Line ends at {line_end:.3f}s against clip end {clip_end:.3f}s, leaving {available_tail:.3f}s "
                    f"tail room below required {tail_margin:.3f}s."
                ),
            }
            sortable_findings.append((line_start, where_label, "CLIP-01", finding))

        # CLIP-02: line.start < clip.start - lead_tolerance_s
        early_lead = round((clip_start - lead_tolerance) - line_start, 6)
        if early_lead > 0.0:
            lead_offset = round(clip_start - line_start, 6)
            finding = {
                "rule": "CLIP-02",
                "severity": limits.severity,
                "where": where_label,
                "detail": (
                    f"Line starts at {line_start:.3f}s, which is {lead_offset:.3f}s before clip start "
                    f"{clip_start:.3f}s and exceeds {lead_tolerance:.3f}s tolerance."
                ),
            }
            sortable_findings.append((line_start, where_label, "CLIP-02", finding))

        # CLIP-03: (clip.end - clip.start) - (line.end - line.start) > max_slack_s
        clip_duration = clip_end - clip_start
        line_duration = line_end - line_start
        slack = round(clip_duration - line_duration, 6)
        excess_slack = round(slack - max_slack, 6)
        if excess_slack > 0.0:
            finding = {
                "rule": "CLIP-03",
                "severity": limits.severity,
                "where": where_label,
                "detail": (
                    f"Clip duration {clip_duration:.3f}s exceeds line duration {line_duration:.3f}s by "
                    f"{slack:.3f}s, over the {max_slack:.3f}s maximum slack."
                ),
            }
            sortable_findings.append((line_start, where_label, "CLIP-03", finding))

    sortable_findings.sort(key=lambda entry: (entry[0], entry[1], entry[2]))
    return [entry[3] for entry in sortable_findings]
