"""WP-Q4: the Blender Studio rig (Rain v3.3, CC-BY 4.0) as the appeal benchmark, rendered through the same style graph and
HeadlessRender as the look round (``style_sheets``): a face close-up that pushes in, the character lip-synced by bone poses
(``rigs.ActionVisemes``) from Rhubarb cues, her materials re-made by ``style.StyleEngine`` (skin, hair, eyes, costume classes),
optionally re-proportioned through the rig's own head lattice. Glue only: the rig, the render adapter and the style are other
people's code or earlier packages; the one thing added is the ``rig_blend`` object kind of ``bpy/render_shot.py``.

    python -m explainer_engine.blender.character_benchmark --blend "<Rain v3.3>/rain_v3.2.blend" --out out/wpq4 \\
        --variant q1_lit_pbrn_cinematic --frames 24 --scale 0.375 [--cues line.rhubarb.json] [--angular 1.0]

Credit (CC-BY, every video that shows her): ``Rain Rig © Blender Foundation | cloud.blender.org``.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from explainer_engine.blender import rigs
from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core.store import write_json_atomic

POSES = Path(__file__).with_name("viseme_poses_rain.json")
CREDIT = "Rain Rig © Blender Foundation | cloud.blender.org"
SKIN_TEXTURE = 0.0   # 0.2 left hard stripes on the cheeks in the first frames: the texture is flat-field, judged on the clip
LATTICE = "HLP-rain-lattice-head"
# toon material name -> StyleEngine.material kwargs; the blend's own material names map onto them (slot class by name suffix)
MATERIAL_MAP = {
    "MAT-rain.body": "rain_skin", "MAT-rain.hands": "rain_skin", "MAT-rain.hair": "rain_hair", "MAT-rain.eyebrows": "rain_hair",
    "MAT-rain.eyelashes": "rain_hair", "MAT-rain.eyes": "rain_eyes", "MAT-rain.eyedot": "rain_pupil", "MAT-rain.cornea": "rain_cornea",
    "MAT-rain.teeth": "rain_teeth", "MAT-rain.gums": "rain_gums", "MAT-rain.tongue": "rain_gums",
    "MAT-rain.top": "rain_costume", "MAT-rain.scarf": "rain_cloak", "MAT-rain.jeans": "rain_costume", "MAT-rain.hairband": "rain_cloak",
    "MAT-lead.cloak": "rain_cloak", "MAT-lead.tunic": "rain_costume", "MAT-rain.shoes": "rain_leather", "MAT-rain.socks": "rain_costume", "MAT-rain.laces": "rain_leather", "MAT-rain.metal": "rain_leather",
}


def poses(path: Path = POSES) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["poses"]


def lattice_deltas(angular: float) -> dict[str, list[float]]:
    """Re-proportion by the rig's shared 2x2x3 head lattice (points are x fastest, then y, then z; z = 0 is the chin row): the
    chin row is lowered and narrowed, the cheek row narrowed, so the jaw is longer and the head less round. ``angular`` 0 = Rain
    as made; the amounts are first guesses to be judged on the clip, in lattice units (the lattice is scaled 0.287)."""
    if not angular:
        return {}
    d = {}
    for i in range(12):
        x, y, z = i % 2, (i // 2) % 2, i // 4
        sx = -1.0 if x == 0 else 1.0
        if z == 0:      # chin row
            d[str(i)] = [-0.12 * angular * sx, 0.0, -0.18 * angular]
        elif z == 1:    # cheek row
            d[str(i)] = [-0.06 * angular * sx, 0.0, 0.0]
    return d


def textures(root: Path, names=("body_diffuse", "eyes")) -> dict[str, Path]:
    return {n: Path(root) / f"TEX-rain_{n}.png" for n in names}


def toon_materials(tex_dir: Path | None) -> dict[str, dict]:
    """The toon materials of the rig's classes (names end in the class the shadow tints are chosen by)."""
    m = {"rain_skin": {"base": [0.8, 0.5, 0.34, 1.0]}, "rain_hair": {"base": [0.08, 0.045, 0.03, 1.0]},
         "rain_eyes": {"base": [0.9, 0.9, 0.88, 1.0]}, "rain_pupil": {"base": [0.02, 0.02, 0.02, 1.0]},
         "rain_cornea": {"base": [0.9, 0.9, 0.9, 1.0]}, "rain_teeth": {"base": [0.92, 0.88, 0.8, 1.0]},
         "rain_gums": {"base": [0.62, 0.22, 0.22, 1.0]}, "rain_leather": {"base": [0.16, 0.09, 0.05, 1.0]},
         "rain_costume": {"base": [0.42, 0.30, 0.18, 1.0], "slot": "costume"}, "rain_cloak": {"base": [0.16, 0.03, 0.025, 1.0], "slot": "costume"}}
    if tex_dir is not None:
        t = textures(tex_dir)
        if t["body_diffuse"].exists():
            mean = SS.texture_mean(t["body_diffuse"])
            m["rain_skin"] = {"base": mean + [1.0], "texture": str(t["body_diffuse"]), "texture_mean": mean, "strength": SKIN_TEXTURE}
        if t["eyes"].exists():
            mean = SS.texture_mean(t["eyes"])
            m["rain_eyes"] = {"base": mean + [1.0], "texture": str(t["eyes"]), "texture_mean": mean, "strength": 1.0}
    return m


def scene(blend: Path, frames: int, *, tex_dir: Path | None = None, lip: dict | None = None, angular: float = 0.0,
          hide: tuple = ("GEO-rain-eyes_viewport", "GEO-rain-eye_cornea", "GEO-rain-top"), push: bool = True, wall: bool = True, framing: str = "cu") -> dict:
    """{objects, camera, materials, frames_total}: Rain facing the camera in front of a plain wall, a slow push-in."""
    visemes = rigs.ActionVisemes(poses()).tracks_for(list(lip["shapes"])) if lip else None
    rb = {"path": str(blend), "collection": "CH-rain", "rig": "RIG-rain", "materials": MATERIAL_MAP, "hide": list(hide),
          "pose": {}, "lattice": {"object": LATTICE, "deltas": lattice_deltas(angular)} if angular else None, "visemes": visemes}
    objs = [{"name": "rain", "rig_blend": rb}]
    if wall:   # without it the camera sees the sky of the look (an HDRI behind the head)
        objs.insert(0, {"name": "wall", "add": "cube", "params": {"size": 1}, "location": [0, 1.0, 1.4], "scale": [6, 0.2, 4],
                        "material": "wall"})
    cam = {"location": [0.0, -1.75, 1.47], "look_at": [0.0, 0.0, 1.43], "lens_mm": 85, "focus_distance_m": 1.45}
    if framing == "bust":   # shoulders and cloak in frame (judging the costume and the head's proportions)
        cam = {"location": [0.0, -3.4, 1.25], "look_at": [0.0, 0.0, 1.12], "lens_mm": 50, "focus_distance_m": 3.4}
        push = False
    if push:
        cam["to"] = {"location": [0.0, -1.35, 1.46], "look_at": [0.0, 0.0, 1.43]}
    mats = {"wall": {"base": "grey_mid"}, **toon_materials(tex_dir)}
    return {"objects": objs, "camera": cam, "materials": mats, "frames_total": frames}


def run(blend: Path, out: Path, *, variant: str = "q1_lit_pbrn_cinematic", frames: int = 24, scale: float = 1.0, samples: int = 16,
        cues: Path | None = None, angular: float = 0.0, binary: str | None = None, device: str = "auto", light_preset: str | None = None,
        sky: str | None = None, wall: bool = True, framing: str = "cu", log=print) -> dict:
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core import shot_cache
    from explainer_engine.core.errors import ContractError
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paths = SS.fetch()
    lip, cue_file = SS.lipsync_for(frames, cues=cues, out=out) if cues else (None, None)
    sc = scene(Path(blend), frames, tex_dir=Path(blend).parent / "textures", lip=lip, angular=angular, wall=wall, framing=framing)
    path, tokens = SS.style_for(variant)
    if light_preset or sky:   # WP-Q1's named light presets and the HDRI sky (Wing It!'s rule), over the chosen q1 look
        art = S.replace(tokens.art, **{k: v for k, v in (("light_preset", light_preset), ("sky", sky)) if v})
        tokens = S.replace(tokens, art=art)
    graph = S.StyleEngine(tokens).graph(path, camera=sc["camera"], materials=sc["materials"],
                                        hdri=str(paths["hdri.ph_kloofendal_48d_partly_cloudy_puresky"]),
                                        paper_texture=str(paths["texture.acg_paper003"]))
    problems = S.check(graph)
    if problems:
        raise ValueError(f"rain/{variant}: style graph problems: {problems}")
    jscene = {"kind": "described", "objects": sc["objects"], "camera": sc["camera"], "style": graph, "frames_total": frames}
    spec = SS.spec_for("dialogue_cu", variant, tokens, samples=samples, scene=jscene, frames=frames, cues=cue_file)
    spec["shot_id"] = f"rain_cu_{variant}"
    if scale != 1.0:
        spec["frame"]["render_scale"] = scale
    b = BlenderProject().resolve(binary, device=device)
    vault = R.LocalVault(out / "vault")
    t0 = time.time()
    try:
        m = R.HeadlessRender(b, vault).run(spec, out / "work", scene=jscene)
    except ContractError as e:
        if scale == 1.0 or "master" not in str(e):
            raise
        m = dict(json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8")), _findings=[])
    sdir = out / "work" / m["cache_key"]
    row = {"variant": variant, "credit": CREDIT, "angular": angular, "frames": frames, "scale": scale, "engine": m["engine"],
           "seconds_per_frame": m["seconds_per_frame"], "times": SS.frame_times(sdir), "wall_seconds": round(time.time() - t0, 2),
           "mp4": SS.mp4(sdir / "frames", out / f"rain_cu_{variant}.mp4"), "frames_dir": str(sdir / "frames"),
           "findings": [f for f in m["_findings"] if f["severity"] == "FAIL"]}
    write_json_atomic(out / "rain_benchmark.json", row)
    log(f"rain/{variant}: {row['times']['steady_median_s']} s/frame steady ({row['engine']})")
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--blend", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--variant", default="q1_lit_pbrn_cinematic")
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--cues", type=Path)
    ap.add_argument("--angular", type=float, default=0.0)
    ap.add_argument("--light-preset", choices=sorted(S.light_presets()))
    ap.add_argument("--sky", choices=list(S.SKIES))
    ap.add_argument("--no-wall", action="store_true")
    ap.add_argument("--framing", choices=("cu", "bust"), default="cu")
    ap.add_argument("--binary")
    a = ap.parse_args(argv)
    run(a.blend, a.out, variant=a.variant, frames=a.frames, scale=a.scale, samples=a.samples, cues=a.cues, angular=a.angular,
        binary=a.binary, light_preset=a.light_preset, sky=a.sky, wall=not a.no_wall, framing=a.framing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
