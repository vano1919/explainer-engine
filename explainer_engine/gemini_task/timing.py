"""Voice first (build item 6): the read's measured clock sets every shot's length and every Wan clip's length before any
picture batch is planned for sending.

The clock is the episode's own G6 timing (``episode/timing.py``: Scribe words aligned to the lines, ``audio/timing.json``);
nothing is timed twice. Here it is only read and judged:

- every number is a frame with a +-10 % band (the creator, 2026-11-12 18:18 UTC; ``07_REVIEW_PROTOCOL.md`` "Numbers are a
  frame"): a measured length within 10 % of the planned one is fine, outside it is a REVIEW line for the story to decide,
  never a correction the code makes;
- a ``video`` shot gets its LTX clip (D-132; Fable audit FA-01/FA-04): the seconds the video lane generates
  (``videolane/plan.clip_seconds``, VL-06) on the measured length, against the LTX launch (``training/pods/ltx/launch.json``
  ``native``, read only); a shot longer than one clip is a REVIEW here (split it in the script) and a FAIL at G1. The Wan
  helpers below (``wan_native``, ``wan_clip``) stay for the legacy route's tests only.

SFX are placed in the edit on the timed words, music and the loudness pass come last (``audio/layers``, ``qa/targets``);
this module has no part in them.
"""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.episode import timing as ET

FRAME_BAND = 0.10            # the creator, 2026-11-12 18:18 UTC: every count is a frame, +-10 %
LAUNCH = Path(__file__).resolve().parents[1] / "training" / "pods" / "wan" / "launch.json"   # legacy Wan route only
LTX_LAUNCH = Path(__file__).resolve().parents[1] / "training" / "pods" / "ltx" / "launch.json"


def in_band(value: float, frame: float, band: float = FRAME_BAND) -> bool:
    """True when ``value`` is within ``band`` of ``frame``, over or under (a zero frame only holds zero)."""
    if not frame:
        return value == 0
    return abs(value - frame) <= band * abs(frame) + 1e-9


def wan_native() -> dict | None:
    try:
        return json.loads(LAUNCH.read_text(encoding="utf-8")).get("native")
    except (OSError, ValueError):
        return None


def wan_frames(seconds: float, fps: int) -> int:
    """Wan draws 4k+1 frames: the smallest such count that holds the shot (as the worker counts them)."""
    n = max(1, int(round(seconds * fps)))
    return n if (n - 1) % 4 == 0 else n + (4 - (n - 1) % 4)


def wan_clip(seconds: float) -> dict:
    n = wan_native()
    if not n or not n.get("fps") or not n.get("max_frames"):
        return {"status": "NOT_RUN", "detail": "launch.json native limits are not pinned"}
    frames = wan_frames(seconds, int(n["fps"]))
    fits = frames <= int(n["max_frames"])
    return {"status": "PASS" if fits else "REVIEW", "fps": int(n["fps"]), "frames": frames,
            "clip_seconds": round(frames / int(n["fps"]), 3), "max_frames": int(n["max_frames"]),
            "detail": "one clip holds the shot" if fits else
            f"{seconds:g} s needs {frames} frames, past the model's {n['max_frames']}: split the shot in the script or "
            "chain two clips (the adapter refuses it at G1)"}


def ltx_native() -> dict | None:
    try:
        return json.loads(LTX_LAUNCH.read_text(encoding="utf-8")).get("native")
    except (OSError, ValueError):
        return None


def video_clip(script: dict, shot: dict, seconds: float, measured: bool = False) -> dict:
    """The LTX clip of one ``video`` shot of ``seconds`` (``measured``: the read's length, else the plan): the same number
    the video lane generates (VL-06), the same limit G1 checks (FA-01)."""
    from explainer_engine.videolane import plan as VP
    n = ltx_native()
    if not n or not n.get("fps") or not n.get("max_frames"):
        return {"status": "NOT_RUN", "detail": "the LTX launch.json native limits are not pinned"}
    fps, max_frames = int(n["fps"]), int(n["max_frames"])
    max_s = (max_frames + 0.49) / fps
    c = VP.clip_seconds(script, dict(shot, target_duration_seconds=seconds), max_s,
                        measured_s=seconds if measured else None)
    return {"status": "REVIEW" if c["over"] else "PASS", "model": "LTX", "fps": fps, "max_frames": max_frames,
            "clip_seconds": c["seconds"], "needed_s": c["needed_s"], "basis": c["basis"],
            "detail": "one clip holds the shot" if not c["over"] else
            f"needs {c['needed_s']:g} s of clip, past LTX's {max_s:.2f} s: split the line or the shot in the script "
            "(G1 FAILs it, VL-06)"}


def durations(root: Path, script: dict) -> dict:
    """``{"timed": bool, "source", "shots": {shot_id: {seconds, planned_seconds, source, frame}}}`` from the episode's
    G6 clock, else the planned lengths (``timed`` False: no picture batch may be sent, voice comes first)."""
    tim = ET.load(Path(root))
    out = {}
    for s in script.get("shots", []):
        planned = float(s.get("target_duration_seconds") or 0.0)
        t = (tim or {}).get("shots", {}).get(s["shot_id"]) if tim else None
        secs = float(t["seconds"]) if t else planned
        row = {"seconds": round(secs, 4), "planned_seconds": planned, "source": "scribe" if t else "planned"}
        if t:
            ok = in_band(secs, planned)
            row["frame"] = {"status": "PASS" if ok else "REVIEW",
                            "detail": f"measured {secs:.2f} s vs planned {planned:.2f} s"
                                      + ("" if ok else ": outside the 10 % frame, the story decides (no correction)")}
        else:
            row["frame"] = {"status": "NOT_RUN", "detail": "no timed read yet (audio/timing.json)"}
        out[s["shot_id"]] = row
    timed = bool(tim) and all(r["source"] == "scribe" for r in out.values())
    return {"timed": timed, "source": "audio/timing.json" if tim else "planned target_duration_seconds",
            "coverage": (tim or {}).get("coverage"), "shots": out}
