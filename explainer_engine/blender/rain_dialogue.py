"""WP-Q4: two-line dialogue for the Rain lead (``cast_lead/rain_lead.blend``): the mouth from Rhubarb cues (``rigs.ActionVisemes``,
the same bone poses as the benchmark) plus, per line, a head turn and one gesture on the rig's own CloudRig FK controls.
Pure Python, no bpy: it returns the ``visemes`` track map of the ``rig_blend`` object kind of ``bpy/render_shot.py`` (a dict
"bone|property|index" -> [[frame, value], ...], rotations in radians, keys on frames from the clip start), so a caller adds::

    rig_blend = {..., "visemes": rain_dialogue.dialogue(lines, frames)["visemes"]}

and swapping the cue files (synthetic -> Rhubarb on the ElevenLabs line) changes nothing else. ``lines`` is a list of::

    {"cues": <Rhubarb JSON path or dict>, "start_s": 0.0, "turn_deg": 12, "gesture": "explain" | "nod" | "none"}

Axes (measured on the baked lead, bone matrices at rest): FK-Head local Y is up, so rotation Y = yaw and a positive value looks
to the camera's right (+X world); rotation X is pitch and positive nods forward; the right forearm's positive X flexes the elbow
forward. The neck takes 40 % of every head move. The lead's held arm pose is Upperarm Z +-62 deg and forearm X +8 deg (rest).
"""
from __future__ import annotations

import math
from pathlib import Path

from explainer_engine.blender import rigs

POSES = Path(__file__).with_name("viseme_poses_rain.json")
REST_FOREARM_DEG = 8.0      # character_benchmark.ARMS_DOWN / make_rain_lead.ARMS_DOWN
GESTURES = ("explain", "nod", "none")
KEY_EVERY = 2               # frames between keys on the head and arm channels (bezier fills the rest)


def _smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _line_end_s(cues) -> float:
    return float(rigs.load_cues(cues)["duration"])


def _lines(lines: list[dict]) -> list[dict]:
    out = []
    for i, ln in enumerate(lines):
        g = ln.get("gesture", "none")
        if g not in GESTURES:
            raise ValueError(f"line {i}: gesture {g!r} is not one of {', '.join(GESTURES)}")
        start = float(ln.get("start_s", 0.0))
        out.append({"cues": ln["cues"], "start": start, "end": start + _line_end_s(ln["cues"]),
                    "turn": float(ln.get("turn_deg", 0.0)), "gesture": g})
    out.sort(key=lambda d: d["start"])
    return out


def _yaw_deg(t: float, ls: list[dict]) -> float:
    """Eased hold of each line's turn (0.35 s, begun 0.08 s before the line), back to 0 half a second after the last."""
    steps = [(l["start"] - 0.08, l["turn"]) for l in ls] + [(ls[-1]["end"] + 0.5, 0.0)]
    cur, prev = 0.0, 0.0
    for tk, target in steps:
        if t >= tk:
            cur = prev + (target - prev) * _smooth((t - tk) / 0.35) if t < tk + 0.35 else target
            if t >= tk + 0.35:
                prev = target
            else:
                break
    return cur


def _gesture(t: float, ls: list[dict]) -> float:
    g = 0.0
    for l in ls:
        if l["gesture"] != "explain":
            continue
        up = _smooth((t - l["start"]) / 0.4)
        down = 1.0 - _smooth((t - (l["end"] - 0.1)) / 0.45)
        g = max(g, min(up, down))
    return g


def _nod_deg(t: float, ls: list[dict]) -> float:
    v = 0.0
    for l in ls:
        if l["gesture"] != "nod":
            continue
        for c in (l["start"] + 0.3, (l["start"] + l["end"]) / 2):
            v += 8.0 * math.exp(-((t - c) / 0.13) ** 2)
    return v


def dialogue(lines: list[dict], frames: int, fps: int = 24, poses: dict | None = None) -> dict:
    """{"visemes": merged track map, "report": {...}}: mouth for every line (X, the closed mouth, between them) + head and gesture."""
    import json
    ls = _lines(lines)
    if not ls:
        raise ValueError("a dialogue needs at least one line")
    ap = rigs.ActionVisemes(poses or json.loads(POSES.read_text(encoding="utf-8"))["poses"], fps)
    shapes = ["X"] * frames
    for l in ls:
        f0 = int(round(l["start"] * fps))
        for i, s in enumerate(ap.lip.frames(l["cues"])):
            if 0 <= f0 + i < frames:
                shapes[f0 + i] = s
    tracks = ap.tracks_for(shapes)
    keys = sorted(set(range(0, frames, KEY_EVERY)) | {frames - 1})

    def add(bone: str, idx: int, fn) -> None:
        tracks[f"{bone}|rotation_euler|{idx}"] = [[f, round(math.radians(fn(f / fps)), 6)] for f in keys]

    add("FK-Head", 1, lambda t: 0.6 * _yaw_deg(t, ls))
    add("FK-Neck", 1, lambda t: 0.4 * _yaw_deg(t, ls))
    add("FK-Head", 0, lambda t: 0.6 * _nod_deg(t, ls))
    add("FK-Neck", 0, lambda t: 0.4 * _nod_deg(t, ls))
    add("FK-Forearm.R", 0, lambda t: REST_FOREARM_DEG + _gesture(t, ls) * (62 + 5 * math.sin(2 * math.pi * 1.8 * t)))
    add("FK-Upperarm.R", 0, lambda t: 12.0 * _gesture(t, ls))
    return {"visemes": tracks, "report": {"frames": frames, "fps": fps, "lines": [
        {k: l[k] for k in ("start", "end", "turn", "gesture")} for l in ls], "channels": len(tracks)}}
