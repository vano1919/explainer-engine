"""The six benchmark shots of roadmap 12.4 (S1-S6) as shot_spec/2 documents built by the scene builder (ICW-06 acceptance:
"the six benchmark shots of 12.4 build headless without error"). Free; ICW-09 renders them on the pods under its OR-23 plan.

    python -m explainer_engine.blender.benchmark_shots specs --out D [--cues line.rhubarb.json]     # the six specs + scenes
    python -m explainer_engine.blender.benchmark_shots build --out D --binary B [--frames 2] [--scale 0.5] [--shots S1,S3]

| Shot | 12.4 | Here |
|---|---|---|
| S1 | dialogue CU with lip-sync and Line Art | the ICW-05 dialogue set, the real pair, speaker_a lip-synced, ``push`` |
| S2 | interior / establishing council tableau | the dialogue set's hall, five councillors behind the table, ``orbit`` |
| S3 | crowd battle wide, GN instancing + dust volume | 18 soldiers (rig copies sharing their meshes), the near line advancing, ``dolly`` |
| S4 | travel dolly over a terrain + sky HDRI | the travel set under the Poly Haven sky HDRI, two walkers, ``rail`` |
| S5 | STILL_3D plate with a 48-frame camera drift | the establishing set, one traveller holding a pose, ``dolly`` drift |
| S6 | S1 under ``cycles_hero`` 64 samples + denoise | S1's scene on the Cycles-safe path |

**Deviations (reported, not hidden):** S3 has no Geometry Nodes instancing and no dust volume yet (the crowd is 18 rig copies;
GN scatter and the volume are ICW-09 preflight items); S4's terrain is the ICW-05 primitive hills, not a Poly Haven terrain
(none is registered; PoC 3's download is its own step). Every shot is 48 frames at the 2560x1440 master, 24 fps; ``build``'s
``--frames``/``--scale`` make a quicker check of the same scene (the spec's clock and scale change, the scene does not).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import scene_builder as SB
from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core.store import write_json_atomic

JOB_ID = "benchmark_icw06"
SHOTS = ("S1", "S2", "S3", "S4", "S5", "S6")
FRAMES = 48
VARIANT = "B_light"   # the ICW-05b default look until ვანო's style pick
LIGHT_RIG = "ink_key_sun"


def pose(location, look_at) -> dict:
    yaw, pitch = SB.angles([look_at[i] - location[i] for i in range(3)])
    return {"pos": [float(x) for x in location], "yaw_deg": yaw, "pitch_deg": pitch}


def member(character, costume, xy, yaw, action, *, tint=None, offset=0, to=None, lipsync=None) -> dict:
    return {"character": character, "costume": costume, "position": [xy[0], xy[1], 0.0], "facing_deg": yaw, "action": action,
            "tint": tint, "offset": offset, "to": to, "lipsync": lipsync}


def _set(scene_id: str, paths, drop=()) -> tuple[list[dict], dict]:
    """A style-sheet set without its stand-in mannequins (and without ``drop``): (objects, materials)."""
    sc = SS.scenes(paths)[scene_id]
    figures = ("_body", "_head", "_cap")
    objs = [o for o in sc["objects"] if not o["name"].endswith(figures) and o["name"] not in drop]
    used = {o.get("material") for o in objs}
    return objs, {k: v for k, v in sc["materials"].items() if k in used}


def plans(lipsync: dict | None = None) -> dict[str, dict]:
    """Shot id -> {set, drop, cast (cast_id -> member), camera (shot_spec/2 camera), lane, profile}."""
    a, b = SS.DIALOGUE_CAST
    dialogue = {"speaker_a": member(a[1], a[2], a[4], a[5], a[6], tint=a[3], offset=a[7], lipsync=lipsync),
                "speaker_b": member(b[1], b[2], b[4], b[5], b[6], tint=b[3], offset=b[7])}
    s1_cam = {"rig": "push", "start": pose([-1.0, -3.4, 1.72], [0.12, 0.9, 1.42]), "end": pose([-0.62, -2.15, 1.66], [0.08, 0.9, 1.46]),
              "lens_mm": 40, "ease": "ease_in_out"}
    council = {}
    seats = ((-1.6, 1.65), (-0.8, 2.0), (0.0, 2.15), (0.8, 2.0), (1.6, 1.65))
    who = (("ink_test_m", "costume.mco_male_ranger", "support_blue"), ("ink_test_f", "costume.mco_female_ranger", "answer_coral"),
           ("ink_test_m2", "costume.mco_male_peasant", "faction_a"), ("ink_test_f", "costume.mco_female_peasant", "faction_b"),
           ("ink_test_m", "costume.mco_male_peasant", "kit_shadow"))
    for i, ((x, y), (ch, co, tint)) in enumerate(zip(seats, who)):
        council[f"councillor_{i}"] = member(ch, co, (x, y), round(-x * 18, 3), "Idle_Talking_Loop" if i == 2 else "Idle_Loop",
                                            tint=tint, offset=(i * 13) % 40)
    battle = {}
    for i in range(9):
        ch = "ink_test_m" if i % 2 == 0 else "ink_test_m2"
        xa, ya = -7 + i * 1.3, -3.0 + (i % 2) * 0.5
        battle[f"a{i}"] = member(ch, "costume.mco_male_peasant", (xa, ya), 180.0, "Walk_Formal_Loop", tint="faction_a",
                                 offset=(i * 7) % 32, to=[xa, ya + 1.6, 0.0])
        battle[f"b{i}"] = member(ch, "costume.mco_male_ranger", (-7.5 + i * 1.4, 7.0 - (i % 2) * 0.5), 0.0, "Sword_Idle",
                                 tint="faction_b", offset=(i * 11) % 40)
    walkers = {"walker_a": member("ink_test_m", "costume.mco_male_ranger", (-0.9, 1.6), 180.0, "Walk_Loop", tint="support_blue",
                                  to=[-0.9, 4.6, 0.0]),
               "walker_b": member("ink_test_f", "costume.mco_female_peasant", (1.6, 6.2), 180.0, "Walk_Loop", tint="answer_coral",
                                  offset=11, to=[1.6, 9.2, 0.0])}
    traveller = {"traveller": member("ink_test_m2", "costume.mco_male_ranger", (-0.8, 9.0), 160.0, "Idle_Loop", tint="support_blue")}
    out = {
        "S1": {"set": "dialogue_cu", "drop": (), "cast": dialogue, "camera": s1_cam, "lane": "VIDEO_3D", "profile": "eevee_fast"},
        "S2": {"set": "dialogue_cu", "drop": ("crate",), "cast": council, "lane": "VIDEO_3D", "profile": "eevee_fast",
               "camera": {"rig": "orbit", "start": pose([-1.5, -2.8, 2.0], [0, 1.9, 1.3]), "end": pose([1.5, -2.8, 2.0], [0, 1.9, 1.3]),
                          "lens_mm": 32, "ease": "ease_in_out"}},
        "S3": {"set": "battle_wide", "drop": (), "cast": battle, "lane": "VIDEO_3D", "profile": "eevee_fast",
               "camera": {"rig": "dolly", "start": pose([6.5, -13.5, 4.2], [-1.0, 2.5, 0.9]),
                          "end": pose([3.2, -13.2, 4.0], [-1.6, 3.0, 0.9]), "lens_mm": 32, "ease": "ease_in_out"}},
        "S4": {"set": "travel", "drop": (), "cast": walkers, "lane": "VIDEO_3D", "profile": "eevee_fast",
               "camera": {"rig": "rail", "start": pose([-2.6, -5.5, 1.7], [0.6, 8.0, 1.3]), "end": pose([-2.6, -2.5, 1.7], [0.6, 11.0, 1.3]),
                          "lens_mm": 35, "ease": "linear"}},
        "S5": {"set": "establishing", "drop": (), "cast": traveller, "lane": "STILL_3D", "profile": "eevee_fast",
               "camera": {"rig": "dolly", "start": pose([7.0, -12.0, 9.0], [0, 26, 4]), "end": pose([6.2, -11.6, 8.9], [0, 26, 4]),
                          "lens_mm": 32, "ease": "ease_in_out"}},
    }
    out["S6"] = {**out["S1"], "profile": "cycles_hero"}
    return out


def spec_for(sid: str, plan: dict, *, cues: Path | None = None, frames: int = FRAMES, lib=None, reg=None) -> dict:
    lib = lib or L.load()
    reg = reg or C.registry()
    ref = lambda i: {"id": i, "sha256": L.get(i, lib=lib)["sha256"]}  # noqa: E731
    _, tokens = SS.style_for(VARIANT)
    cycles = plan["profile"] == "cycles_hero"
    chars = [{"cast_id": cid, "asset": ref(C.get(m["character"], reg=reg)["head"]), "rig": ref(C.get(m["character"], reg=reg)["head"]),
              "animation": ref(reg["animation_asset"]) if m["action"] else None, "position": m["position"], "facing_deg": m["facing_deg"]}
             for cid, m in plan["cast"].items()]
    lip = any(m.get("lipsync") for m in plan["cast"].values())
    spec = {
        "schema": "shot_spec/2", "job_id": JOB_ID, "shot_id": sid, "lane": plan["lane"],
        "recipe": "blender_cycles/1" if cycles else "blender_eevee/1",
        "clock": {"fps": 24, "frames": frames, "start_frame": 0},
        "frame": {"width": S.MASTER_W, "height": S.MASTER_H, "render_scale": 1.0},
        "scene": {"template_asset": {"id": f"scene_template.benchmark_{sid.lower()}", "sha256": "0" * 64}, "era": "benchmark",
                  "set_assets": [ref(a["id"]) for a in SS.sources() if a["kind"] in ("model", "material", "hdri")],
                  "characters": chars, "camera": plan["camera"], "light_rig": LIGHT_RIG, "weather": None, "props": []},
        "performance": {"lipsync": lip, "rhubarb": {"path": Path(cues).name, "sha256": L.sha256_file(cues)} if lip else None,
                        "mouth_shapes": 8, "dialogue_cover": "on_screen" if lip else None},
        "look": {"bible_version": "1.5", "line_weight_px": tokens.line_px, "crease_deg": tokens.crease_deg,
                 "shading_steps": tokens.steps, "view_transform": tokens.view_transform, "grade_look": tokens.look,
                 "paper": {"asset": ref("texture.acg_paper003"), "opacity": tokens.paper_opacity}},
        "render": {"profile": plan["profile"], "samples": 64 if cycles else 16, "motion_blur": False, "denoise": cycles,
                   "output": "png_seq"},
        "seed": 1,
    }
    if cycles:
        spec["why"] = "benchmark S6 (roadmap 12.4): S1 under cycles_hero, 64 samples, denoise; the cost row, never an episode shot"
    return spec


def build(sid: str, plan: dict, spec: dict, paths, *, builder: SB.SceneBuilder | None = None) -> tuple[dict, list[dict]]:
    """(described scene with its style graph, sampled camera path); the spec's template hash is set from the scene."""
    builder = builder or SB.SceneBuilder()
    objs, mats = _set(plan["set"], paths, plan["drop"])
    sc, path = builder.build(spec, cast=plan["cast"], set_objects=objs, materials=mats)
    style_path = "cycles_safe" if plan["profile"] == "cycles_hero" else "eevee"
    _, tokens = SS.style_for(VARIANT)
    graph = S.StyleEngine(tokens).graph(style_path, camera=sc["camera"], materials=sc["materials"],
                                        hdri=str(paths["hdri.ph_kloofendal_48d_partly_cloudy_puresky"]),
                                        paper_texture=str(paths["texture.acg_paper003"]))
    problems = S.check(graph)
    if problems:
        raise ValueError(f"{sid}: style graph problems: {problems}")
    scene = {"kind": "described", "objects": sc["objects"], "camera": sc["camera"], "style": graph}
    if sc.get("frames_total"):
        scene["frames_total"] = sc["frames_total"]
    spec["scene"]["template_asset"]["sha256"] = SS.scene_sha256(scene)
    return scene, path


def specs(out: Path, *, cues: Path | None = None, frames: int = FRAMES, shots=SHOTS) -> list[dict]:
    """Every shot's spec + described scene + camera path under ``out/<shot>/`` (no render)."""
    from explainer_engine.blender import rigs
    out = Path(out)
    paths = SS.fetch()
    lip = None
    if cues is not None:
        ls = rigs.LipSync(24)
        lip = ls.plan(cues, frames, offset_s=ls.busiest(cues, frames))
    builder = SB.SceneBuilder(C.fetch())
    rows = []
    for sid, plan in plans(lip).items():
        if sid not in shots:
            continue
        if lip is None:
            plan = {**plan, "cast": {k: {**m, "lipsync": None} for k, m in plan["cast"].items()}}
        spec = spec_for(sid, plan, cues=cues, frames=frames)
        scene, path = build(sid, plan, spec, paths, builder=builder)
        d = out / sid
        write_json_atomic(d / "spec.json", spec)
        write_json_atomic(d / "scene.json", scene)
        write_json_atomic(d / "camera_path.json", path)
        rows.append({"shot": sid, "spec": spec, "scene": scene, "camera_path": path, "plan": plan})
    return rows


def render(out: Path, *, binary: str | None = None, cues: Path | None = None, frames: int = FRAMES, scale: float = 1.0,
           shots=SHOTS, device: str = "auto", log=print) -> list[dict]:
    """Build and render each shot through HeadlessRender, then write its blender_scene_manifest/1 (``scene_manifest.json``)
    and a row in ``out/benchmark_shots.json``. A scaled check is refused by CN-17 after its frames are kept: kept as a test row."""
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core import shot_cache
    from explainer_engine.core.errors import ContractError
    out = Path(out)
    b = BlenderProject().resolve(binary, device=device)
    vault = R.LocalVault(out / "vault")
    builder = SB.SceneBuilder(C.fetch())
    rows = []
    for row in specs(out / "specs", cues=cues, frames=frames, shots=shots):
        spec, scene, sid = row["spec"], row["scene"], row["shot"]
        if scale != 1.0:
            spec["frame"]["render_scale"] = scale
        t0 = time.time()
        try:
            m = R.HeadlessRender(b, vault).run(spec, out / "work", scene=scene)
        except ContractError as e:
            if scale == 1.0 or "master" not in str(e):
                raise
            m = dict(json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8")),
                     _findings=[])
        sdir = out / "work" / m["cache_key"]
        manifest = builder.manifest(spec, sdir, row["camera_path"])
        write_json_atomic(sdir / "scene_manifest.json", manifest)
        rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
        rows.append({"shot": sid, "lane": spec["lane"], "profile": spec["render"]["profile"], "rig": spec["scene"]["camera"]["rig"],
                     "frames": m["frames_written"], "seconds_per_frame": m["seconds_per_frame"],
                     "wall_seconds": round(time.time() - t0, 2), "engine": m["engine"], "objects": manifest["objects"],
                     "characters": len(rep.get("characters", {})), "lipsync": rep.get("lipsync"), "scaled": scale != 1.0,
                     "scene_manifest": str(sdir / "scene_manifest.json"),
                     "frame": str(sdir / "frames" / R.FRAME_NAME.format(index=0)),
                     "findings": [f for f in m["_findings"] if f["severity"] == "FAIL"]})
        log(f"{sid}: {rows[-1]['seconds_per_frame']} s/frame, {rows[-1]['characters']} characters, {manifest['objects']['total']} objects")
        write_json_atomic(out / "benchmark_shots.json", {"schema": "benchmark_shots/1", "job_id": JOB_ID, "rows": rows})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.benchmark_shots", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("specs", "build"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("--cues", default=None)
        p.add_argument("--frames", type=int, default=FRAMES)
        p.add_argument("--shots", default=",".join(SHOTS))
        if name == "build":
            p.add_argument("--binary", default=None)
            p.add_argument("--scale", type=float, default=1.0)
            p.add_argument("--device", default="auto", choices=("auto", "cpu", "gpu"))
    a = ap.parse_args(argv)
    cues = Path(a.cues) if a.cues else None
    if a.cmd == "specs":
        for r in specs(Path(a.out), cues=cues, frames=a.frames, shots=a.shots.split(",")):
            print(f"{r['shot']}: {len(r['scene']['objects'])} objects, camera {r['spec']['scene']['camera']['rig']}")
        return 0
    rows = render(Path(a.out), binary=a.binary, cues=cues, frames=a.frames, scale=a.scale, shots=a.shots.split(","), device=a.device)
    return 1 if any(r["findings"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
