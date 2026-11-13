"""Camera grammar of the Blender lanes (WP-Q7, roadmap 10.1): named setups -> the ``scene.camera`` block of ``shot_spec/2``.

    resolve("ots_a", {"a": {"pos": [..]}, "b": {"pos": [..]}}, bearing_deg=0) -> {"camera": {rig, start, end, lens_mm, ease, setup,
                                                                                    fstop, rig_kind}, "focus_at": [x, y, z], ...}
    framing(camera_block, point) -> (x, y)     # where a world point lands in the frame, 0..1 from the left / from the bottom
    python -m explainer_engine.blender.camera_setups [list | resolve NAME --a x,y,z [--b x,y,z] [--bearing D] [--frames N]]

The setups are data (``camera_setups.json``: lens, height and distance in head heights, a thirds target, an f-stop, a focus target).
This module is the glue: it places the camera from the subjects' positions, then aims it so that the framed point lands on the
setup's thirds target (a pinhole camera, the same model as Blender's ``world_to_camera_view`` for a lens fit to the width; the
bpy side measures the real frame and records it in the report). Yaw 0 looks along +Y, positive yaw turns towards -X, pitch positive
looks up (``scene_builder.forward``). ``bearing_deg`` is the direction the camera looks along for the shots that have no
second subject to point at (0 = along +Y, so the camera stands at -Y of the subject, like every existing shot).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from explainer_engine.blender import scene_builder as SB
from explainer_engine.core.errors import ContractError

PATH = Path(__file__).with_name("camera_setups.json")
HEAD_M = 0.24         # one head height of a Universal Base Character (1.6 m eye line / ~6.7 heads)
EYE_M = 1.6           # the eye line the cast's centre uses (scene_builder.build adds 1.4 m to the feet)
SENSOR_MM = 36.0      # the engine's sensor width (render_shot: ``sensor_mm`` default)
ASPECT = 16 / 9
RIG_KINDS = ("dolly", "crane")


@lru_cache(maxsize=1)
def load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def setups() -> dict:
    return load()["setups"]


def names() -> list[str]:
    return sorted(setups())


def get(name: str) -> dict:
    sets = setups()
    if name not in sets:
        raise ContractError(f"unknown camera setup {name!r} (known: {', '.join(names())})")
    return sets[name]


def sequence(name: str) -> list[str]:
    seq = load()["sequences"]
    if name not in seq:
        raise ContractError(f"unknown camera sequence {name!r} (known: {', '.join(sorted(seq))})")
    return list(seq[name])


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _unit_xy(v):
    n = math.hypot(v[0], v[1])
    if n < 1e-9:
        raise ContractError("the two subjects stand on the same spot, so there is no A-B axis")
    return [v[0] / n, v[1] / n]


def _basis(yaw_deg: float, pitch_deg: float):
    """(forward, right, up) of a camera pose."""
    f = SB.forward(yaw_deg, pitch_deg)
    y = math.radians(yaw_deg)
    right = (math.cos(y), math.sin(y), 0.0)
    up = (right[1] * f[2] - right[2] * f[1], right[2] * f[0] - right[0] * f[2], right[0] * f[1] - right[1] * f[0])
    return f, right, up


def framing(cam: dict, point, *, which: str = "start") -> tuple[float, float]:
    """(x, y) of a world point in the frame of the camera block's start/end pose: 0..1 from the left / from the bottom
    (x 0.5, y 0.5 is the centre). The lens is fit to the sensor width, 16:9."""
    pose = cam[which]
    f, r, u = _basis(pose["yaw_deg"], pose["pitch_deg"])
    d = _sub(point, pose["pos"])
    depth = sum(d[i] * f[i] for i in range(3))
    if depth <= 1e-6:
        raise ContractError("the point is behind the camera")
    sw = SENSOR_MM
    x = 0.5 + (sum(d[i] * r[i] for i in range(3)) / depth) * cam["lens_mm"] / sw
    y = 0.5 + (sum(d[i] * u[i] for i in range(3)) / depth) * cam["lens_mm"] / (sw / ASPECT)
    return x, y


def aim(pos, point, lens_mm: float, thirds) -> tuple[float, float]:
    """(yaw_deg, pitch_deg) that puts ``point`` at ``thirds`` of the frame from a camera at ``pos``."""
    cam = {"lens_mm": lens_mm, "start": {"pos": pos, "yaw_deg": 0.0, "pitch_deg": 0.0}}
    yaw, pitch = SB.angles(_sub(point, pos))
    for _ in range(8):
        cam["start"]["yaw_deg"], cam["start"]["pitch_deg"] = yaw, pitch
        x, y = framing(cam, point)
        dx = math.degrees(math.atan((x - thirds[0]) * SENSOR_MM / lens_mm))   # the point is too far right: turn right (less yaw)
        dy = math.degrees(math.atan((y - thirds[1]) * (SENSOR_MM / ASPECT) / lens_mm))   # too high: look up (more pitch)
        yaw, pitch = yaw - dx, pitch + dy
        if abs(x - thirds[0]) < 1e-6 and abs(y - thirds[1]) < 1e-6:
            break
    return round(yaw, 6), round(pitch, 6)


def _point(spec: dict, who: str, subjects: dict, head_m: float, eye_m: float):
    """The framed or focus point of a subject keyword: a, b, mid (between a and b) or group (the centre of all)."""
    z = spec.get("target_z_eye", 1.0) * eye_m

    def at(s):
        return [s["pos"][0], s["pos"][1], s["pos"][2] + z]
    if who in ("mid", "group"):
        pts = [at(s) for s in (subjects.values() if who == "group" else [subjects["a"], subjects["b"]])]
        return [sum(p[i] for p in pts) / len(pts) for i in range(3)]
    if who not in subjects:
        raise ContractError(f"the setup needs subject {who!r}, the shot has {sorted(subjects)}")
    return at(subjects[who])


def _view(spec: dict, subjects: dict, bearing_deg: float):
    """Unit xy view direction (the way the camera looks) of the setup."""
    kind = spec["view"]
    if kind == "bearing":
        y = math.radians(bearing_deg)
        return [-math.sin(y), math.cos(y)]
    if "a" not in subjects or "b" not in subjects:
        raise ContractError(f"view {kind!r} needs subjects a and b")
    a, b = subjects["a"]["pos"], subjects["b"]["pos"]
    if kind == "along_ab":
        src, dst = (a, b) if spec["from"] == "a" else (b, a)
        return _unit_xy(_sub(dst, src))
    if kind == "perp_ab":
        v = _unit_xy(_sub(b, a))
        return [v[1], -v[0]]   # the A-B axis turned by -90 degrees: the camera looks at the pair from its right
    raise ContractError(f"unknown view {kind!r}")


def _pose(spec: dict, end: dict, subjects: dict, view, target, head_m: float):
    right = [view[1], -view[0]]   # the right of a forward (x, y), as in scene_builder.forward
    d, side = end["distance_heads"] * head_m, end.get("side_heads", 0.0) * head_m
    # the camera stands ``distance_heads`` behind the framed point along the view, shifted to the right by ``side_heads``
    # (over-the-shoulder: that puts the 'from' subject, who stands on the line, in the foreground)
    pos = [target[0] - view[0] * d + right[0] * side, target[1] - view[1] * d + right[1] * side, end["height_heads"] * head_m]
    yaw, pitch = aim(pos, target, spec["lens_mm"], spec["thirds"])
    return {"pos": [round(x, 6) for x in pos], "yaw_deg": yaw, "pitch_deg": pitch}


def resolve(name: str, subjects: dict, *, bearing_deg: float = 0.0, head_m: float = HEAD_M, eye_m: float = EYE_M) -> dict:
    """The camera block of a named setup for the subjects ({"a": {"pos": [x, y, z]}, "b": ...}; feet positions).

    Returns {"camera": the ``shot_spec/2`` block (+ setup, fstop, rig_kind), "target": the framed point, "focus_at": the point
    the focus sits on, "thirds": [x, y], "tolerance": the setup's}."""
    spec = get(name)
    view = _view(spec, subjects, bearing_deg)
    target = _point(spec, spec["target"], subjects, head_m, eye_m)
    focus_at = _point(spec, spec["focus"], subjects, head_m, eye_m)
    start = _pose(spec, spec["start"], subjects, view, target, head_m)
    end = _pose(spec, spec["end"], subjects, view, target, head_m) if spec["end"] else start
    cam = {"rig": spec["rig"], "start": start, "end": end, "lens_mm": spec["lens_mm"], "ease": spec["ease"], "setup": name,
           "fstop": spec["fstop"], "rig_kind": spec["rig_kind"]}
    return {"camera": cam, "target": [round(x, 6) for x in target], "focus_at": [round(x, 6) for x in focus_at],
            "thirds": spec["thirds"], "tolerance": spec["thirds_tol"]}


def thirds_error(resolved: dict, *, which: str = "start") -> float:
    """The miss of the framed point from the setup's thirds target, in frame widths (the larger of the x and y miss)."""
    x, y = framing(resolved["camera"], resolved["target"], which=which)
    return max(abs(x - resolved["thirds"][0]), abs(y - resolved["thirds"][1]))


def check_camera(cam: dict) -> list[str]:
    """Problems of a ``scene.camera`` block that names a setup: an unknown setup, a lens or f-stop outside the setup's range,
    an unknown rig kind. Empty = fine."""
    out = []
    name = cam.get("setup")
    if name is not None:
        if name not in setups():
            return [f"unknown camera setup {name!r}"]
        spec = setups()[name]
        if abs(cam["lens_mm"] - spec["lens_mm"]) > 1e-6:
            out.append(f"setup {name}: lens {cam['lens_mm']} mm, the setup says {spec['lens_mm']} mm")
    f = cam.get("fstop")
    if f is not None and not (load()["fstop_min"] <= f <= load()["fstop_max"]):
        out.append(f"f-stop {f} outside {load()['fstop_min']}..{load()['fstop_max']}")
    if cam.get("rig_kind") is not None and cam["rig_kind"] not in RIG_KINDS:
        out.append(f"unknown rig kind {cam['rig_kind']!r}")
    return out


def main(argv: list[str] | None = None) -> int:
    """``--list`` (default) prints the table; ``resolve NAME --a x,y,z [--b x,y,z] [--bearing DEG] [--frames N]`` prints the
    ``scene.camera`` block, the framed and focus points and the sampled path as JSON (what a render runner feeds a shot)."""
    import argparse
    ap = argparse.ArgumentParser(description="camera setups of the Blender lanes (WP-Q7)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("list")
    r = sub.add_parser("resolve")
    r.add_argument("name")
    r.add_argument("--a", required=True, help="feet position of subject a: x,y,z")
    r.add_argument("--b", default=None, help="feet position of subject b: x,y,z")
    r.add_argument("--bearing", type=float, default=0.0)
    r.add_argument("--frames", type=int, default=24)
    r.add_argument("--head-m", type=float, default=HEAD_M)
    r.add_argument("--eye-m", type=float, default=EYE_M)
    a = ap.parse_args(argv)
    if a.cmd == "resolve":
        pos = lambda t: {"pos": [float(x) for x in t.split(",")]}  # noqa: E731
        subj = {"a": pos(a.a), **({"b": pos(a.b)} if a.b else {})}
        res = resolve(a.name, subj, bearing_deg=a.bearing, head_m=a.head_m, eye_m=a.eye_m)
        res["frames"] = a.frames
        res["path"] = SB.camera_path(res["camera"], a.frames)
        print(json.dumps(res, indent=1))
        return 0
    for n in names():
        s = setups()[n]
        print(f"{n:20s} {s['lens_mm']:>3} mm  f/{s['fstop']:<4} {s['rig']:7s} {s['rig_kind']:6s} thirds {s['thirds']}  {s['label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
