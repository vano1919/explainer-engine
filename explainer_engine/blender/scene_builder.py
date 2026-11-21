"""Scene builder of the Blender lanes (roadmap 15 ICW-06, 10.1, section 11 ``SceneBuilder``): shot_spec/2 -> the scene job of
``bpy/render_shot.py`` and, after the render, ``blender_scene_manifest/1``.

    SceneBuilder(paths, cpaths).build(spec, cast=..., set_objects=..., materials=...) -> (described scene, camera path)
    SceneBuilder.manifest(spec, sdir, camera_path) -> blender_scene_manifest/1 (from the bpy report of the render)
    python -m explainer_engine.blender.scene_builder smoke --out D [--binary B]   # CI: one rigged character, a camera rail

**Camera rigs (10.1):** ``static``, ``push``, ``dolly``, ``rail``, ``orbit``, ``dramatic_curve``, each from the spec's ``start`` and
``end`` poses ({pos, yaw_deg, pitch_deg}; yaw 0 looks along +Y, positive yaw turns towards -X, pitch positive looks up) and
``ease``. Every rig is sampled into camera keys every ``KEY_EVERY`` frames (and the last frame), LINEAR between keys, so the
camera path is plain data the manifest records and the render reproduces exactly:
- static: the start pose held; push / dolly / rail: start -> end in a straight line (push moves along the view, dolly sideways,
  rail is a dolly whose heading stays the start's; the names keep the planner's intent, the geometry is the spec's poses);
- orbit: an arc around the pivot (the cast's centre, else the point ``ORBIT_PIVOT_M`` ahead of the start pose) from the start's
  bearing to the end's, the radius eased between the two distances, the camera always facing the pivot;
- dramatic_curve: start -> end along a quadratic Bezier bowed sideways by ``CURVE_BOW`` of the distance (the BP-170 curve's
  intent in 3D: a push that does not travel in a straight line), eased in and out.
Easing: linear, ease_in (t^2), ease_out (1-(1-t)^2), ease_in_out (smoothstep).

**Cast:** every ``scene.characters`` entry names a ``cast_id``; ``cast`` maps it to {character, costume, action, tint, offset,
lipsync} (characters.json; shot_spec/2 has no field for the costume or the clip name, proposed to ICW-07). The spec's
``asset`` must be the character's head model and ``animation`` the registered animation set (refused otherwise, so a
renamed or swapped asset never renders silently); ``position`` and ``facing_deg`` place it. A lip-synced cast member makes
the shot obey BP-108's cap (``rigs.LipSync.plan``).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import assets as A
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

RIGS = ("static", "push", "dolly", "rail", "orbit", "dramatic_curve")
EASES = ("linear", "ease_in", "ease_out", "ease_in_out")
KEY_EVERY = 4          # frames between sampled camera keys (6 keys a second at 24 fps)
ORBIT_PIVOT_M = 5.0    # pivot distance ahead of the start pose when the shot has no cast
CURVE_BOW = 0.12       # sideways bow of the dramatic curve, share of the start-end distance
LOOK_M = 10.0          # look-at distance written into the scene job (direction only)


def ease(kind: str, t: float) -> float:
    t = min(max(t, 0.0), 1.0)
    if kind == "linear":
        return t
    if kind == "ease_in":
        return t * t
    if kind == "ease_out":
        return 1 - (1 - t) ** 2
    if kind == "ease_in_out":
        return t * t * (3 - 2 * t)
    raise ValueError(f"unknown ease {kind!r} (known: {', '.join(EASES)})")


def forward(yaw_deg: float, pitch_deg: float) -> tuple[float, float, float]:
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    return (-math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p))


def angles(direction) -> tuple[float, float]:
    """(yaw_deg, pitch_deg) of a view direction."""
    x, y, z = direction
    h = math.hypot(x, y)
    return round(math.degrees(math.atan2(-x, y)), 6), round(math.degrees(math.atan2(z, h)), 6)


def _lerp(a, b, t):
    return [a[i] + (b[i] - a[i]) * t for i in range(len(a))]


def _yaw_lerp(a: float, b: float, t: float) -> float:
    d = (b - a + 180.0) % 360.0 - 180.0
    return a + d * t


def camera_path(cam: dict, frames: int, *, pivot=None) -> list[dict]:
    """The sampled camera of a rig: [{frame, pos, yaw_deg, pitch_deg}] at 0, KEY_EVERY, ..., frames-1."""
    rig, ez = cam["rig"], cam["ease"]
    if rig not in RIGS:
        raise ContractError(f"unknown camera rig {rig!r} (known: {', '.join(RIGS)})")
    s, e = cam["start"], cam["end"]
    p0, p1 = list(map(float, s["pos"])), list(map(float, e["pos"]))
    last = max(frames - 1, 0)
    idx = sorted(set(list(range(0, last + 1, KEY_EVERY)) + [last]))
    out = []
    if rig == "orbit":
        f0 = forward(s["yaw_deg"], s["pitch_deg"])
        piv = list(pivot) if pivot is not None else [p0[i] + f0[i] * ORBIT_PIVOT_M for i in range(3)]
        a0, a1 = math.atan2(p0[1] - piv[1], p0[0] - piv[0]), math.atan2(p1[1] - piv[1], p1[0] - piv[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        r0, r1 = math.hypot(p0[0] - piv[0], p0[1] - piv[1]), math.hypot(p1[0] - piv[0], p1[1] - piv[1])
    for f in idx:
        t = ease(ez, f / last) if last else 0.0
        if rig == "static":
            pos, yaw, pitch = p0, s["yaw_deg"], s["pitch_deg"]
        elif rig in ("push", "dolly"):
            pos, yaw, pitch = _lerp(p0, p1, t), _yaw_lerp(s["yaw_deg"], e["yaw_deg"], t), s["pitch_deg"] + (e["pitch_deg"] - s["pitch_deg"]) * t
        elif rig == "rail":
            pos, yaw, pitch = _lerp(p0, p1, t), s["yaw_deg"], s["pitch_deg"]
        elif rig == "orbit":
            a, r = a0 + da * t, r0 + (r1 - r0) * t
            z = p0[2] + (p1[2] - p0[2]) * t
            pos = [piv[0] + r * math.cos(a), piv[1] + r * math.sin(a), z]
            yaw, pitch = angles([piv[i] - pos[i] for i in range(3)])
        else:  # dramatic_curve
            d = [p1[i] - p0[i] for i in range(3)]
            dist = math.sqrt(sum(x * x for x in d)) or 1.0
            side = [-d[1] / dist, d[0] / dist, 0.0]
            ctrl = [(p0[i] + p1[i]) / 2 + side[i] * dist * CURVE_BOW for i in range(3)]
            pos = [(1 - t) ** 2 * p0[i] + 2 * (1 - t) * t * ctrl[i] + t * t * p1[i] for i in range(3)]
            yaw, pitch = _yaw_lerp(s["yaw_deg"], e["yaw_deg"], t), s["pitch_deg"] + (e["pitch_deg"] - s["pitch_deg"]) * t
        out.append({"frame": f, "pos": [round(x, 6) for x in pos], "yaw_deg": round(yaw, 6), "pitch_deg": round(pitch, 6)})
    return out


def camera_job(path: list[dict], lens_mm: float, focus_m: float, *, fstop: float | None = None, rig_kind: str | None = None,
               focus_at=None, extension: str | None = None) -> dict:
    """The ``camera`` block of a described scene from a sampled path (LINEAR keys). WP-Q7: ``rig_kind`` (dolly | crane) builds the
    Add Camera Rigs rig from ``extension`` (the zip) and keys it with the same path; ``fstop`` is its aperture and ``focus_at`` a
    world point the focus distance follows (else ``focus_m`` holds)."""
    keys = []
    for k in path:
        f = forward(k["yaw_deg"], k["pitch_deg"])
        keys.append({"frame": k["frame"], "location": k["pos"], "look_at": [k["pos"][i] + f[i] * LOOK_M for i in range(3)]})
    first = keys[0]
    cam = {"location": first["location"], "look_at": first["look_at"], "lens_mm": lens_mm, "focus_distance_m": focus_m}
    if len(keys) > 1:
        cam.update(keys=keys, interp="LINEAR")
    if fstop is not None:
        cam["fstop"] = fstop
    if focus_at is not None:
        cam["focus_at"] = [float(x) for x in focus_at]
    if rig_kind is not None:
        if extension is None:
            raise ContractError(f"camera rig {rig_kind!r} needs the extension zip (camera_rigs.ensure())")
        cam.update(rig_kind=rig_kind, extension=str(extension))
    return cam


class SceneBuilder:
    """shot_spec/2 + the cast table -> the described scene of ``bpy/render_shot.py``."""

    def __init__(self, cpaths: dict[str, Path] | None = None, *, reg: dict | None = None, lib: dict | None = None):
        self.reg = reg or C.registry()
        self.lib = lib if lib is not None else L.load()
        self.cpaths = cpaths

    def cast_objects(self, spec: dict, cast: dict[str, dict]) -> tuple[list[dict], dict[str, dict], list]:
        chars = spec["scene"]["characters"]
        objs, mats, centre = [], {}, []
        anim_id = self.reg["animation_asset"]
        for c in chars:
            if c["cast_id"] not in cast:
                raise ContractError(f"{spec['shot_id']}: cast {c['cast_id']!r} has no entry in the cast table")
            m = cast[c["cast_id"]]
            ch = C.get(m["character"], reg=self.reg)
            if c["asset"]["id"] != ch["head"]:
                raise ContractError(f"{c['cast_id']}: the spec names {c['asset']['id']}, the character {m['character']} is {ch['head']}")
            if c["animation"] is not None and c["animation"]["id"] != anim_id:
                raise ContractError(f"{c['cast_id']}: animation {c['animation']['id']} is not the registered set {anim_id}")
            for ref in (c["asset"], c["rig"], *(x for x in [c["animation"]] if x)):
                if L.get(ref["id"], lib=self.lib)["sha256"] != ref["sha256"]:
                    raise ContractError(f"{c['cast_id']}: {ref['id']} sha256 differs from the library")
            if self.cpaths is None:
                self.cpaths = C.fetch()
            obj, mm = C.scene_object(c["cast_id"], m["character"], m["costume"], self.cpaths, location=c["position"],
                                     yaw_deg=c["facing_deg"], action=m.get("action") if c["animation"] else None,
                                     action_offset=m.get("offset", 0), tint=m.get("tint"), lipsync=m.get("lipsync"), reg=self.reg)
            if m.get("to"):
                obj["to"], obj["interp"] = {"location": m["to"]}, "LINEAR"
            for k, v in mm.items():
                if mats.get(k, v) != v:
                    raise ContractError(f"two cast members define material {k} differently")
                mats[k] = v
            objs.append(obj)
            centre.append(c["position"])
        if spec["performance"]["lipsync"] and not any(cast[c["cast_id"]].get("lipsync") for c in chars):
            raise ContractError(f"{spec['shot_id']}: performance.lipsync is true but no cast member has lip-sync tracks")
        pivot = [sum(p[i] for p in centre) / len(centre) for i in range(3)] if centre else None
        if pivot is not None:
            pivot[2] += 1.4   # the cast's eye line (UBC heads stand at ~1.6 m), not their feet
        return objs, mats, pivot

    def build(self, spec: dict, *, cast: dict[str, dict] | None = None, set_objects: list[dict] | None = None,
              materials: dict[str, dict] | None = None, focus_m: float | None = None, focus_at=None,
              extension: str | None = None) -> tuple[dict, list[dict]]:
        """(described scene without its style graph, camera path). ``set_objects``/``materials`` are the set (primitives and
        library .blend appends, the style-sheet vocabulary); the style graph is added by the caller (``style_sheets.job_scene``)."""
        objs, mats, pivot = self.cast_objects(spec, cast or {})
        frames = spec["clock"]["frames"]
        path = camera_path(spec["scene"]["camera"], frames, pivot=pivot)
        focus = focus_m or (math.dist(path[0]["pos"], pivot) if pivot else ORBIT_PIVOT_M)
        sc = {"objects": [*(set_objects or []), *objs], "materials": {**(materials or {}), **mats},
              "camera": camera_job(path, spec["scene"]["camera"]["lens_mm"], round(focus, 3), fstop=spec["scene"]["camera"].get("fstop"),
                                   rig_kind=spec["scene"]["camera"].get("rig_kind"), focus_at=focus_at, extension=extension)}
        if frames > 1:
            sc["frames_total"] = frames
        return sc, path

    def manifest(self, spec: dict, sdir: Path, path: list[dict]) -> dict:
        """blender_scene_manifest/1 of a rendered shot: object counts and bounds from the bpy report, the assets the spec and
        the cast named (with sha256), the sampled camera path, the fixed import settings."""
        sdir = Path(sdir)
        rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
        objs = rep.get("objects", {})
        ids = {r["id"] for r in spec["scene"]["set_assets"]} | {spec["scene"]["template_asset"]["id"]}
        for c in rep.get("characters", {}).values():
            ids |= set(c["assets"])
        for c in spec["scene"]["characters"]:
            ids |= {c["asset"]["id"], c["rig"]["id"]} | ({c["animation"]["id"]} if c["animation"] else set())
        assets = []
        for i in sorted(ids):
            try:
                r = L.get(i, lib=self.lib)
            except KeyError:
                continue   # a described scene's template hash (style sheets) is not a library record
            assets.append({"id": i, "sha256": r["sha256"], "kind": r["kind"]})
        spec_file = sdir / "spec.json"
        doc = {"schema": "blender_scene_manifest/1", "job_id": spec["job_id"], "shot_id": spec["shot_id"],
               "spec": {"path": "spec.json", "sha256": L.sha256_file(spec_file)}, "cache_key": sdir.name,
               "blender_version": rep["blender_version"],
               "objects": {"total": sum(objs.values()), "meshes": objs.get("MESH", 0), "armatures": objs.get("ARMATURE", 0),
                           "lights": objs.get("LIGHT", 0), "cameras": objs.get("CAMERA", 0)},
               "assets": assets, "bounds": rep.get("bounds", []), "camera_path": path,
               "import_settings": {k: v for k, v in A.IMPORT_SETTINGS.items() if k in ("glb", "gltf", "blend")}}
        from explainer_engine.core import contracts
        contracts.validate(doc)
        return doc


# --- the CI smoke (roadmap 15 ICW-06: one rigged character, one camera rail, Workbench) ----------------------------------------

SMOKE_CAST = {"walker": {"character": "ink_test_m", "costume": "costume.mco_male_peasant", "action": "Walk_Loop", "tint": "faction_a",
                         "offset": 0, "to": None, "lipsync": None}}


def smoke_spec(frames: int = 8) -> dict:
    """The ICW-04 smoke spec with one cast member (the walker, its clip from the UAL set) and a ``rail`` camera."""
    from explainer_engine.blender import render as R
    lib, reg = L.load(), C.registry()
    ref = lambda i: {"id": i, "sha256": L.get(i, lib=lib)["sha256"]}  # noqa: E731
    spec = R.smoke_spec("smoke_character", frames)
    spec["shot_id"] = "smoke_character_01"
    head = C.get("ink_test_m", reg=reg)["head"]
    spec["scene"]["characters"] = [{"cast_id": "walker", "asset": ref(head), "rig": ref(head), "animation": ref(reg["animation_asset"]),
                                    "position": [0.0, 0.0, 0.0], "facing_deg": 0.0}]
    spec["scene"]["camera"] = {"rig": "rail", "start": {"pos": [-1.6, -4.0, 1.3], "yaw_deg": -12.0, "pitch_deg": -4.0},
                               "end": {"pos": [1.6, -4.0, 1.3], "yaw_deg": -12.0, "pitch_deg": -4.0}, "lens_mm": 40, "ease": "linear"}
    return spec


def smoke(out: Path, *, binary: str | None = None, frames: int = 8, log=print) -> dict:
    """Render the character smoke with the Workbench override (320x180) and write its scene manifest; returns a summary."""
    from explainer_engine.blender import profiles as P
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    out = Path(out)
    spec = smoke_spec(frames)
    b = SceneBuilder(C.fetch())
    sc, path = b.build(spec, cast=SMOKE_CAST, set_objects=[{"name": "ground", "add": "plane", "params": {"size": 20}}])
    scene = {"kind": "described", **sc}
    m = R.HeadlessRender(BlenderProject().resolve(binary), R.LocalVault(out / "vault")).run(spec, out / "work", scene=scene,
                                                                                          smoke=P.SMOKE)
    sdir = out / "work" / m["cache_key"]
    manifest = b.manifest(spec, sdir, path)
    write_json_atomic(sdir / "scene_manifest.json", manifest)
    rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
    summary = {"engine": m["engine"], "frames_written": m["frames_written"], "seconds_per_frame": m["seconds_per_frame"],
               "frames_dir": str(sdir / "frames"), "characters": rep.get("characters"), "actions": rep.get("actions"),
               "objects": manifest["objects"], "camera_keys": len(path), "scene_manifest": str(sdir / "scene_manifest.json"),
               "findings": [f for f in m["_findings"] if f["severity"] == "FAIL" and not (f["rule"] == "CN-17" and "master" in f["detail"])]}
    write_json_atomic(out / "smoke_summary.json", summary)
    log(json.dumps(summary, indent=1))
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.scene_builder", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sm = sub.add_parser("smoke")
    sm.add_argument("--out", required=True)
    sm.add_argument("--binary", default=None)
    sm.add_argument("--frames", type=int, default=8)
    a = ap.parse_args(argv)
    s = smoke(Path(a.out), binary=a.binary, frames=a.frames)
    return 1 if s["findings"] or s["frames_written"] != a.frames else 0


if __name__ == "__main__":
    raise SystemExit(main())
