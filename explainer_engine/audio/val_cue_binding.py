"""Audio validator V-07: cue-to-event binding, coverage, timing tolerance, and sample reuse.

Requirement IDs: OR-S26, OR-A27, OR-V30c.

Registry wiring (D-59): the asymmetric sync window of BIND-03 is BP-54's (early_max_ms, late_max_ms; FAIL), the severity of a
repeated sample (BIND-04) is BP-57's. The one-frame tolerance stays the clean zone; a cue outside it is BIND-03 at the limits'
severity, and at BP-54's severity when it is also outside the sourced window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from explainer_engine.standards import sourced_rules as SR


@dataclass(frozen=True)
class Limits:
    fps: float = 30.0
    tol_frames: float = 1.0
    must_sound: frozenset[str] = frozenset({"object_in", "text_in", "map_move", "chart_move", "counter"})
    severity: str = "REVIEW"
    early_fail_s: float = SR.T("BP-54", "early_max_ms") / 1000  # a cue earlier than this leads its event too far (BP-54)
    late_fail_s: float = SR.T("BP-54", "late_max_ms") / 1000  # a cue later than this trails its event too far (BP-54)
    window_severity: str = SR.severity("BP-54")  # severity of BIND-03 outside the sourced window
    repeat_severity: str = SR.severity("BP-57")  # severity of BIND-04 (the same sample twice in a row)


def _is_number(val: Any) -> bool:
    return isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val)


def _validate_limits(limits: Limits) -> None:
    if not isinstance(limits, Limits):
        raise ValueError("limits must be a Limits instance")
    if not _is_number(limits.fps) or limits.fps <= 0:
        raise ValueError("limits.fps must be a positive finite number")
    if not _is_number(limits.tol_frames) or limits.tol_frames < 0:
        raise ValueError("limits.tol_frames must be a non-negative finite number")
    if not isinstance(limits.must_sound, (frozenset, set)) or not all(
        isinstance(item, str) for item in limits.must_sound
    ):
        raise ValueError("limits.must_sound must be a set or frozenset of strings")
    if not isinstance(limits.severity, str) or not limits.severity.strip():
        raise ValueError("limits.severity must be a non-empty string")
    for name in ("early_fail_s", "late_fail_s"):
        if not _is_number(getattr(limits, name)) or getattr(limits, name) < 0:
            raise ValueError(f"limits.{name} must be a non-negative finite number")
    for name in ("window_severity", "repeat_severity"):
        if not isinstance(getattr(limits, name), str) or not getattr(limits, name).strip():
            raise ValueError(f"limits.{name} must be a non-empty string")


def _validate_events(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not isinstance(events, list):
        raise ValueError("events must be a list")

    by_id: dict[str, dict[str, Any]] = {}
    for idx, ev in enumerate(events):
        if not isinstance(ev, dict):
            raise ValueError(f"events[{idx}] must be a dict")
        for key in ("id", "t", "type"):
            if key not in ev:
                raise ValueError(f"events[{idx}] missing required key: {key!r}")

        ev_id = ev["id"]
        ev_t = ev["t"]
        ev_type = ev["type"]

        if not isinstance(ev_id, str) or not ev_id:
            raise ValueError(f"events[{idx}]['id'] must be a non-empty string")
        if not _is_number(ev_t):
            raise ValueError(f"events[{idx}]['t'] must be a finite number")
        if not isinstance(ev_type, str) or not ev_type:
            raise ValueError(f"events[{idx}]['type'] must be a non-empty string")
        if ev_id in by_id:
            raise ValueError(f"Duplicate event id: {ev_id!r}")

        by_id[ev_id] = {"id": ev_id, "t": float(ev_t), "type": ev_type}
    return by_id


def _validate_cues(cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(cues, list):
        raise ValueError("cues must be a list")

    seen_ids: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for idx, cue in enumerate(cues):
        if not isinstance(cue, dict):
            raise ValueError(f"cues[{idx}] must be a dict")
        for key in ("id", "t", "sound_id", "event_id"):
            if key not in cue:
                raise ValueError(f"cues[{idx}] missing required key: {key!r}")

        cue_id = cue["id"]
        cue_t = cue["t"]
        sound_id = cue["sound_id"]
        event_id = cue["event_id"]
        repeat_ok = cue.get("repeat_ok", False)

        if not isinstance(cue_id, str) or not cue_id:
            raise ValueError(f"cues[{idx}]['id'] must be a non-empty string")
        if not _is_number(cue_t):
            raise ValueError(f"cues[{idx}]['t'] must be a finite number")
        if not isinstance(sound_id, str) or not sound_id:
            raise ValueError(f"cues[{idx}]['sound_id'] must be a non-empty string")
        if event_id is not None and (not isinstance(event_id, str) or not event_id):
            raise ValueError(f"cues[{idx}]['event_id'] must be a non-empty string or None")
        if not isinstance(repeat_ok, bool):
            raise ValueError(f"cues[{idx}]['repeat_ok'] must be a bool")
        if cue_id in seen_ids:
            raise ValueError(f"Duplicate cue id: {cue_id!r}")

        seen_ids.add(cue_id)
        normalized.append(
            {
                "id": cue_id,
                "t": float(cue_t),
                "sound_id": sound_id,
                "event_id": event_id,
                "repeat_ok": repeat_ok,
            }
        )
    return normalized


def check(events: list[dict[str, Any]], cues: list[dict[str, Any]], limits: Limits = Limits()) -> list[dict[str, str]]:
    """Validate cue-to-event binding, sync tolerance, and sample uniqueness."""
    _validate_limits(limits)
    events_by_id = _validate_events(events)
    norm_cues = _validate_cues(cues)

    if not events_by_id and not norm_cues:
        return []

    tol_sec = limits.tol_frames / limits.fps
    bound_event_ids: set[str] = set()
    raw_findings: list[tuple[float, str, str, str]] = []
    sev: dict[tuple[str, str], str] = {}

    # BIND-02 (orphan cues) and BIND-03 (timing offset beyond tolerance)
    for cue in norm_cues:
        ev_id = cue["event_id"]
        if ev_id is None or ev_id not in events_by_id:
            reason = "event_id is None" if ev_id is None else f"event_id {ev_id!r} does not exist in events"
            raw_findings.append(
                (
                    cue["t"],
                    "BIND-02",
                    cue["id"],
                    f"Cue {cue['id']!r} is unbound because {reason}.",
                )
            )
            continue

        bound_event_ids.add(ev_id)
        ev = events_by_id[ev_id]
        diff = abs(cue["t"] - ev["t"])
        if round(diff, 6) > round(tol_sec, 6):
            signed = cue["t"] - ev["t"]
            if round(-signed, 6) > round(limits.early_fail_s, 6) or round(signed, 6) > round(limits.late_fail_s, 6):
                sev[("BIND-03", cue["id"])] = limits.window_severity
            raw_findings.append(
                (
                    cue["t"],
                    "BIND-03",
                    cue["id"],
                    (
                        f"Cue {cue['id']!r} at {cue['t']:.4f}s is {diff:.4f}s from event {ev_id!r} "
                        f"at {ev['t']:.4f}s, exceeding tolerance {tol_sec:.4f}s."
                    ),
                )
            )

    # BIND-01
    for ev_id, ev in events_by_id.items():
        if ev["type"] in limits.must_sound and ev_id not in bound_event_ids:
            raw_findings.append(
                (
                    ev["t"],
                    "BIND-01",
                    ev_id,
                    f"Event {ev_id!r} of type {ev['type']!r} at {ev['t']:.4f}s has no bound audio cue.",
                )
            )

    # BIND-04
    cues_by_sound: dict[str, list[dict[str, Any]]] = {}
    for cue in norm_cues:
        cues_by_sound.setdefault(cue["sound_id"], []).append(cue)

    for sound_id, group in cues_by_sound.items():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda c: (c["t"], c["id"]))
        for prev_cue, curr_cue in zip(ordered, ordered[1:]):
            if not (prev_cue["repeat_ok"] and curr_cue["repeat_ok"]):
                pair_ids = sorted((prev_cue["id"], curr_cue["id"]))
                where = f"{pair_ids[0]}|{pair_ids[1]}"
                sev[("BIND-04", where)] = limits.repeat_severity
                raw_findings.append(
                    (
                        curr_cue["t"],
                        "BIND-04",
                        where,
                        (
                            f"Cues {pair_ids[0]!r} and {pair_ids[1]!r} consecutively reuse sound_id "
                            f"{sound_id!r} without repeat_ok=True on both cues."
                        ),
                    )
                )

    raw_findings.sort(key=lambda item: (round(item[0], 6), item[2], item[1]))

    return [
        {
            "rule": rule,
            "severity": sev.get((rule, where), limits.severity),
            "where": where,
            "detail": detail,
        }
        for _, rule, where, detail in raw_findings
    ]
