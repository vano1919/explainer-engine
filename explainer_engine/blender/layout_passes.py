"""Blender layout passes for the J2 and J4 routes (D-116, guide step 2.3): the same built scene rendered as clay, depth, line and
flat colour, cut into LTX clips, hashed and kept. Free: Blender on the creator's PC or CI (D-114).

    python -m explainer_engine.blender.layout_passes plan                                      # the clips and passes, no render
    python -m explainer_engine.blender.layout_passes render --scene battle|duel --out D [--binary B] [--passes depth,line]
                                                            [--scale 1.0] [--only-frames 0,144] [--count 5000]
    python -m explainer_engine.blender.layout_passes upload --out D                           # to HF route_test_2026-11/layouts/

Route J2 (Layout-To-Render) takes the ``clay`` pass; route J4 (restyle) takes ``colour``, ``depth`` and ``line`` (``ROUTE_PASSES``).
What each pass draws is ``bpy/layout_pass.py`` (render_shot.py runs it last, after the scene, its style and its crowd are built,
so geometry, motion and camera are those of the beauty render). The battle's line pass draws lines only on the fore and mid planes:
the background crowd (the T2 billboards, ``EE_Crowd_t2``) and the dust and smoke cards go out as depth and silhouette colour only
(plan 9.3, ``NO_LINE``).

Geometry (BP-139, CN-08): 24 fps, 1920x1088 (both divisible by 32), every clip 8k+1 frames. The battle scene is 12 s cut into two
LTX clips of 145 frames that overlap by 8 (D-116: one LTX clip is 3-6 s ... at most 8 s, BP-172; 145 frames = 6.04 s); the duel is
one clip of 121 frames. A clip goes out as its PNG frames and an H.264 mp4 per pass, all listed with their sha256 in
``layout_manifest.json`` (``layout_passes/1``).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

PASSES = ("clay", "depth", "line", "colour")
ROUTE_PASSES = {"J2": ("clay",), "J4": ("colour", "depth", "line")}
FPS = 24
SIZE = (1920, 1088)
CLAY_RGB = (0.62, 0.62, 0.62)
CLAY_BACKGROUND = (0.86, 0.86, 0.86)
LINE_PX = 2.0
NO_LINE = ("EE_Crowd_t2", "EE_Crowd_dust", "EE_Crowd_smoke")   # plan 9.3: the background crowd and the fx cards: no lines
SCENES = {
    # scene: (route, clip frames, clips, overlap, near m, far m)
    "battle": {"route": "J4", "clip_frames": 145, "clips": 2, "overlap": 8, "near_m": 2.0, "far_m": 400.0, "no_line": NO_LINE},
    "duel": {"route": "J2", "clip_frames": 121, "clips": 1, "overlap": 0, "near_m": 3.0, "far_m": 40.0, "no_line": ()},
}
# Extra static cameras of the battle for the pilot's stills (P1, 2026-11-06): the default camera creeps behind the near line, so a
# wide high view and a front-line view need their own. Units are metres: the shield wall stands on y = 0 facing +y, the charging
# wedge starts at (6, 26) and runs at JOG_MPS (5.3 m/s) toward it, so contact comes near frame 118; stills are taken just before.
BATTLE_CAMERAS = {
    "wide_high": {"location": [-30.0, -22.0, 14.0], "look_at": [4.0, 14.0, 1.5], "lens_mm": 30, "focus_distance_m": 48.0},
    "front_mid": {"location": [-9.0, 7.5, 1.7], "look_at": [3.0, 1.0, 1.5], "lens_mm": 40, "focus_distance_m": 14.0},
}
HF_PREFIX = "route_test_2026-11/layouts"
SCHEMA = "layout_passes/1"


def clip_ranges(clip_frames: int, clips: int, overlap: int) -> list[tuple[int, int]]:
    """[(first, last)] frames (0-based, inclusive) of consecutive clips that share ``overlap`` frames."""
    if clips < 1 or not 0 <= overlap < clip_frames:
        raise ContractError(f"clips {clips}, overlap {overlap} of {clip_frames}-frame clips")
    step = clip_frames - overlap
    return [(i * step, i * step + clip_frames - 1) for i in range(clips)]


def geometry_findings(scene: str) -> list[dict]:
    """CN-08 on every clip of a scene: 8k+1 frames, sizes divisible by 32, under the registry's frame limit."""
    s = SCENES[scene]
    return [f for i in range(s["clips"]) for f in C._geometry(SIZE[0], SIZE[1], s["clip_frames"], f"{scene}.clip{i + 1}")]


def plan(scene: str) -> dict:
    if scene not in SCENES:
        raise ContractError(f"unknown layout scene {scene!r} (known: {', '.join(SCENES)})")
    s = SCENES[scene]
    ranges = clip_ranges(s["clip_frames"], s["clips"], s["overlap"])
    bad = [f for f in geometry_findings(scene) if f["severity"] == "FAIL"]
    if bad:
        raise ContractError("; ".join(f"{f['rule']} {f['where']}: {f['detail']}" for f in bad))
    return {"scene": scene, "route": s["route"], "passes": list(ROUTE_PASSES[s["route"]]), "fps": FPS, "size": list(SIZE),
            "frames": ranges[-1][1] + 1, "clips": [{"id": f"{scene}_c{i + 1}", "first": a, "last": b, "frames": b - a + 1,
                                                    "seconds": round((b - a + 1) / FPS, 4)} for i, (a, b) in enumerate(ranges)]}


def block(kind: str, scene: str) -> dict:
    """The ``layout_pass`` block of render_shot's scene for one pass of one layout scene."""
    if kind not in PASSES:
        raise ContractError(f"unknown layout pass {kind!r} (known: {', '.join(PASSES)})")
    s = SCENES[scene]
    b = {"kind": kind, "no_line": list(s["no_line"])}
    if kind == "clay":
        b.update(clay_rgb=list(CLAY_RGB), background_rgb=list(CLAY_BACKGROUND))
    elif kind == "depth":
        b.update(near_m=s["near_m"], far_m=s["far_m"])
    elif kind == "line":
        b.update(line_px=LINE_PX)
    return b


def engine_of(kind: str) -> str:
    return "workbench" if kind == "clay" else "eevee"


# --- the two scenes (built by the existing builders, D-115: nothing new is modelled here) -------------------------------------

def battle_scene(frames: int, *, count: int = 5000, camera: str | None = None) -> tuple[dict, dict]:
    """The overnight battle (crowd.py composition ``battle``: a wedge charging a shield wall, 5,000 soldiers as GN tiers)."""
    from explainer_engine.blender import characters as CH
    from explainer_engine.blender import crowd as CR
    from explainer_engine.blender import style_sheets as SS
    paths, cpaths = SS.fetch(), CH.fetch()
    if camera is not None and camera not in BATTLE_CAMERAS:
        raise ContractError(f"unknown battle camera {camera!r} (known: {', '.join(BATTLE_CAMERAS)})")
    sc = CR.scene(paths, cpaths, count=count, frames=frames, composition="battle",
                  camera_override=BATTLE_CAMERAS[camera] if camera else None)
    problems = CR.check(sc["crowds"])
    if problems:
        raise ContractError("; ".join(problems))
    tokens = CR.look_tokens(CR.BATTLE_LOOK, "battle")
    doc, _ = SS.job_scene("battle_wide", CR.BATTLE_LOOK, sc, paths, tokens)
    doc["crowds"] = sc["crowds"]
    spec = SS.spec_for("battle_wide", CR.BATTLE_LOOK, tokens, samples=4, scene=doc, frames=frames)
    return doc, spec


# The duel (route-test S03-02: WS, eye level, static): two of the battle's cast two metres apart in the dialogue set's yard (the
# ground and the brick wall; the table and the crate go), one attacking, one on guard; the camera square to their axis.
DUEL_CAST = (("duelist_a", "ink_test_m", "costume.mco_male_ranger", "faction_a", (-1.0, 1.2), 90.0, "Sword_Attack", 0),
             ("duelist_b", "ink_test_m2", "costume.mco_male_peasant", "faction_b", (1.0, 1.2), -90.0, "Sword_Idle", 9))
DUEL_KEEP = ("ground", "wall")
DUEL_CAMERA = {"location": [0.0, -5.0, 1.5], "look_at": [0.0, 1.2, 1.05], "lens_mm": 35, "focus_distance_m": 6.2}
LOOK = "q1_c1_lit_preset@E2"   # crowd.BATTLE_LOOK: both scenes under the same look (the passes replace its shading anyway)


def duel_objects(base: dict, cast: list[dict]) -> dict:
    """The dialogue set cut to its yard plus the duel cast; the materials are the set's used ones and the cast's own."""
    objs = [o for o in base["objects"] if o.get("name") in DUEL_KEEP]
    mats = {k: v for k, v in base["materials"].items() if k in {o.get("material") for o in objs}}
    for o in cast:
        for k, v in o.pop("_materials", {}).items():
            if mats.get(k, v) != v:
                raise ContractError(f"duel: material {k} defined twice differently")
            mats[k] = v
    return {"objects": objs + cast, "camera": dict(DUEL_CAMERA), "materials": mats}


def duel_scene(frames: int) -> tuple[dict, dict]:
    from explainer_engine.blender import characters as CH
    from explainer_engine.blender import style_sheets as SS
    paths, cpaths = SS.fetch(), CH.fetch()
    base = SS.scenes(paths, cast="mannequin")["dialogue_cu"]
    sc = dict(duel_objects(base, [SS._cast_member(*m, cpaths) for m in DUEL_CAST]), frames_total=frames)
    tokens = SS.style_for(LOOK)[1]
    doc, _ = SS.job_scene("dialogue_cu", LOOK, sc, paths, tokens)
    spec = SS.spec_for("dialogue_cu", LOOK, tokens, samples=4, scene=doc, frames=frames)
    return doc, spec


def job(scene: str, kind: str, doc: dict, spec: dict, out: Path, pin_version: str, *, frames: list[int], scale: float = 1.0,
        device: str = "cpu") -> dict:
    """The render_shot/1 job of one pass (the job HeadlessRender would write, the engine and the scene's ``layout_pass`` set)."""
    from explainer_engine.blender import profiles as PR
    from explainer_engine.blender import render as R
    prof = PR.get(spec["render"]["profile"])
    d = out / scene / kind
    w, h = round(SIZE[0] * scale), round(SIZE[1] * scale)
    return {"job": "render_shot/1", "pin_version": pin_version, "shot_id": f"layout_{scene}_{kind}", "frames": frames,
            "frame_start": 1, "fps": FPS, "width": w, "height": h, "percent": 100, "engine": engine_of(kind), "device": device,
            "settings": prof.settings(spec["render"]), "seed": spec["seed"], "scene": dict(doc, layout_pass=block(kind, scene)),
            "frames_dir": str(d / "frames"), "frame_name": R.FRAME_NAME, "progress": str(d / "progress.jsonl"),
            "report": str(d / "bpy_report.json")}


def _mp4(frames: list[Path], dest: Path, fps: int = FPS) -> dict:
    """H.264 (yuv420p, CRF 16) of the listed frames, in order; LTX reads the clip, the PNGs stay the lossless record."""
    tmp = dest.parent / f".{dest.stem}_list"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(frames):
        link = tmp / f"f_{i:06d}.png"
        if link.exists():
            link.unlink()
        shutil.copyfile(f, link)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "f_%06d.png"), "-c:v", "libx264",
           "-pix_fmt", "yuv420p", "-crf", "16", "-frames:v", str(len(frames)), str(dest)]
    subprocess.run(cmd, check=True)
    shutil.rmtree(tmp)
    return {"path": dest.name, "sha256": C.sha256_file(dest), "frames": len(frames)}


def finished(d: Path, frames: list[int]) -> bool:
    """Every asked frame is in the job's progress file and the report is written: the render is complete even when Blender then
    crashed on exit (Mesa's software EGL segfaults at teardown on a headless CPU host, seen 2026-11-06 after all frames were saved)."""
    from explainer_engine.blender import render as R
    prog, rep = Path(d) / "progress.jsonl", Path(d) / "bpy_report.json"
    if not (prog.exists() and rep.exists()):
        return False
    done = {int(json.loads(ln)["index"]) for ln in prog.read_text(encoding="utf-8").splitlines() if ln.strip()}
    return set(frames) <= done and all((Path(d) / "frames" / R.FRAME_NAME.format(index=i)).exists() for i in frames)


def render(scene: str, out: Path | str, *, binary: str | None = None, passes: list[str] | None = None, scale: float = 1.0,
           only_frames: list[int] | None = None, count: int = 5000, camera: str | None = None, log=print) -> dict:
    """Render the scene's passes, cut the clips, write the manifest. ``only_frames`` renders a review subset (no clips)."""
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    out = Path(out)
    p = plan(scene)
    kinds = passes or p["passes"]
    for k in kinds:
        if k not in PASSES:
            raise ContractError(f"unknown pass {k!r}")
    frames = p["frames"]
    if camera and scene != "battle":
        raise ContractError("a named camera belongs to the battle scene")
    doc, spec = battle_scene(frames, count=count, camera=camera) if scene == "battle" else duel_scene(frames)
    b = BlenderProject().resolve(binary)
    want = sorted(only_frames) if only_frames else list(range(frames))
    rows = {}
    for kind in kinds:
        j = job(scene, kind, doc, spec, out, b.version, frames=want, scale=scale, device=b.device)
        d = out / scene / kind
        d.mkdir(parents=True, exist_ok=True)
        write_json_atomic(d / "job.json", j)
        t0 = time.time()
        cmd = R.HeadlessRender(b, R.LocalVault(out / "vault")).command(d / "job.json")
        with open(d / "blender.log", "w", encoding="utf-8") as lf:
            rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT).returncode
        if rc and not finished(d, want):
            raise ContractError(f"{scene}/{kind}: Blender exited {rc} (see {d / 'blender.log'})")
        rep = json.loads((d / "bpy_report.json").read_text(encoding="utf-8"))
        files = sorted((d / "frames").glob("frame_*.png"))
        row = {"engine": j["engine"], "frames": len(files), "exit_code": rc, "wall_seconds": round(time.time() - t0, 1),
               "seconds_per_frame": round((time.time() - t0) / max(len(files), 1), 3), "layout_pass": rep.get("layout_pass"),
               "frame_sha256": {f.name: C.sha256_file(f) for f in files}}
        if only_frames is None:
            by_index = {int(f.stem.split("_")[1]): f for f in files}
            row["clips"] = {}
            for c in p["clips"]:
                seq = [by_index[i] for i in range(c["first"], c["last"] + 1)]
                row["clips"][c["id"]] = _mp4(seq, d / f"{c['id']}_{kind}.mp4")
        rows[kind] = row
        log(f"{scene}/{kind}: {len(files)} frames in {row['wall_seconds']} s ({j['width']}x{j['height']}, {j['engine']})")
    man = {"schema": SCHEMA, "scene": scene, "route": p["route"], "plan": p, "scale": scale, "subset": bool(only_frames),
           "blender": b.version, "camera": camera, "passes": rows, "hf_prefix": f"{HF_PREFIX}/{scene}"}
    write_json_atomic(out / scene / "layout_manifest.json", man)
    return man


def _same(row: dict | None, local: Path) -> bool:
    """A vault row is the local file: its sha256 (LFS files) or, for small files kept in git, its blob id."""
    from explainer_engine import vault as V
    if not row:
        return False
    sha, blob, _ = V.file_hashes(local)
    return row.get("sha256") == sha if row.get("sha256") else row.get("blob") == blob


def upload(out: Path | str, scene: str, *, vault=None) -> list[str]:
    """Every clip mp4, every frame and the manifest of a full (not subset) render to the vault under ``HF_PREFIX/<scene>/``,
    verified by sha256 against the vault's listing. Returns the remote paths."""
    from explainer_engine.blender import render as R
    d = Path(out) / scene
    man = json.loads((d / "layout_manifest.json").read_text(encoding="utf-8"))
    if man["subset"] or man["scale"] != 1.0:
        raise ContractError("only a full-size, full-length render is uploaded (this one is a review subset or scaled)")
    vault = vault or R.HFVault()
    pairs = [(d / "layout_manifest.json", f"{HF_PREFIX}/{scene}/layout_manifest.json")]
    for kind, row in man["passes"].items():
        for c in row["clips"].values():
            pairs.append((d / kind / c["path"], f"{HF_PREFIX}/{scene}/{kind}/{c['path']}"))
    vault.upload_many(pairs, f"layout passes {scene} ({', '.join(man['passes'])})")
    listed = vault.listing(f"{HF_PREFIX}/{scene}/")
    missing = [r for loc, r in pairs if not _same(listed.get(r), loc)]
    if missing:
        raise ContractError(f"not on the vault with the local hashes: {missing}")
    return [r for _, r in pairs]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    r = sub.add_parser("render")
    r.add_argument("--scene", choices=sorted(SCENES), required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--binary")
    r.add_argument("--passes")
    r.add_argument("--scale", type=float, default=1.0)
    r.add_argument("--only-frames")
    r.add_argument("--count", type=int, default=5000)
    r.add_argument("--camera", choices=sorted(BATTLE_CAMERAS), help="a named static battle camera instead of the creeping one")
    u = sub.add_parser("upload")
    u.add_argument("--out", type=Path, required=True)
    u.add_argument("--scene", choices=sorted(SCENES), required=True)
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        print(json.dumps({s: plan(s) for s in SCENES}, indent=1))
        return 0
    if a.cmd == "upload":
        print("\n".join(upload(a.out, a.scene)))
        return 0
    m = render(a.scene, a.out, binary=a.binary, passes=a.passes.split(",") if a.passes else None, scale=a.scale,
               only_frames=[int(x) for x in a.only_frames.split(",")] if a.only_frames else None, count=a.count, camera=a.camera)
    print(json.dumps({k: {x: v[x] for x in v if x != "frame_sha256"} for k, v in m["passes"].items()}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
