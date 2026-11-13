"""CI and local smoke of the camera setups (WP-Q7): all the named setups on two stand-in figures, each a 48-frame Workbench clip
through the pinned Blender and ``bpy/render_shot.py``, camera built as the Add Camera Rigs rig. Free.

    python -m explainer_engine.blender.camera_smoke --out D [--binary B] [--frames 48] [--size 960x540] [--only a,b]

Per setup it checks: every frame is a valid PNG and the frames differ when the setup moves; the rig the extension built was keyed
(``camera_rig`` in the bpy report); and the framing Blender measured (``world_to_camera_view``) equals the framing
``camera_setups.framing`` computes, at the first and the last frame, within ``TOL`` of a frame width. Writes ``<out>/camera_smoke.json``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from explainer_engine.blender import camera_rigs as R
from explainer_engine.blender import camera_setups as C
from explainer_engine.blender import project as P
from explainer_engine.blender import scene_builder as SB
from explainer_engine.blender.render import check_png
from explainer_engine.core.store import write_json_atomic

SCRIPT = Path(__file__).with_name("bpy") / "render_shot.py"
TOL = 2e-3
SUBJECTS = {"a": {"pos": [-1.2, 2.0, 0.0]}, "b": {"pos": [1.0, 2.5, 0.0]}}


def objects() -> list[dict]:
    out = []
    for k, s in SUBJECTS.items():
        x, y, _ = s["pos"]
        out.append({"name": f"body_{k}", "add": "cylinder", "params": {"radius": 0.22, "depth": 1.4}, "location": [x, y, 0.7]})
        out.append({"name": f"head_{k}", "add": "cube", "params": {"size": C.HEAD_M}, "location": [x, y, 1.52]})
    out.append({"name": "floor", "add": "plane", "params": {"size": 60}, "location": [0, 5, 0]})
    return out


def job(name: str, out: Path, frames: int, width: int, height: int, pin_version: str, ext: Path) -> tuple[dict, dict]:
    r = C.resolve(name, SUBJECTS)
    cam = r["camera"]
    cj = SB.camera_job(SB.camera_path(cam, frames), cam["lens_mm"], 5.0, fstop=cam["fstop"], rig_kind=cam["rig_kind"],
                       focus_at=r["focus_at"], extension=str(ext))
    cj["probe"] = [{"name": "target", "at": r["target"]}]
    d = out / name
    return {"job": "render_shot/1", "pin_version": pin_version, "shot_id": name, "frames": list(range(frames)), "frame_start": 1,
            "fps": 24, "width": width, "height": height, "percent": 100, "engine": "workbench", "device": "cpu", "settings": {},
            "seed": 1, "scene": {"kind": "described", "frames_total": frames, "objects": objects(), "materials": {}, "camera": cj},
            "frames_dir": str(d / "frames"), "frame_name": "frame_{index:06d}.png", "progress": str(d / "progress.jsonl"),
            "report": str(d / "bpy_report.json")}, r


def run(out: Path, binary: str | None, frames: int, width: int, height: int, only: list[str] | None) -> dict:
    project = P.BlenderProject()
    blender = project.resolve(binary)   # refuses a binary that is not the pinned version
    path, pin = blender.path, project.version
    ext = R.ensure()
    summary, failures = {}, []
    for name in only or C.names():
        d = Path(out) / name
        d.mkdir(parents=True, exist_ok=True)
        j, r = job(name, Path(out), frames, width, height, pin, ext)
        jp = d / "job.json"
        write_json_atomic(jp, j)
        proc = subprocess.run([path, "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(SCRIPT), "--", str(jp)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (d / "blender.log").write_text(proc.stdout, encoding="utf-8")
        row = {"returncode": proc.returncode}
        summary[name] = row
        if proc.returncode:
            failures.append(f"{name}: Blender exited {proc.returncode} (see {d / 'blender.log'})")
            continue
        rep = json.loads((d / "bpy_report.json").read_text(encoding="utf-8"))
        files = sorted((d / "frames").glob("frame_*.png"))
        bad = [str(f) for f in files if check_png(str(f), width, height)]
        moving = r["camera"]["rig"] != "static"
        distinct = len({f.read_bytes() for f in files})
        row.update(frames=len(files), distinct=distinct, rig=rep.get("camera_rig", {}).get("kind"), framing=rep.get("framing"))
        if len(files) != frames or bad:
            failures.append(f"{name}: {len(files)} frames, bad {bad[:2]}")
        if moving and distinct != frames:
            failures.append(f"{name}: the camera moves but only {distinct} of {frames} frames differ")
        if row["rig"] != r["camera"]["rig_kind"]:
            failures.append(f"{name}: expected a {r['camera']['rig_kind']} rig, the report says {row['rig']}")
        for idx, which in (("0", "start"), (str(frames - 1), "end")):
            want = C.framing(r["camera"], r["target"], which=which)
            got = rep["framing"][idx]["target"]
            row[f"miss_{which}"] = round(max(abs(want[0] - got[0]), abs(want[1] - got[1])), 5)
            if row[f"miss_{which}"] > TOL:
                failures.append(f"{name}: Blender frames the target at {got}, the pinhole says {list(want)} ({which})")
    summary = {"schema": "camera_smoke/1", "setups": summary, "failures": failures, "tolerance": TOL}
    write_json_atomic(Path(out) / "camera_smoke.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--binary", default=None)
    ap.add_argument("--frames", type=int, default=48)
    ap.add_argument("--size", default="960x540")
    ap.add_argument("--only", default=None)
    a = ap.parse_args(argv)
    w, h = (int(x) for x in a.size.split("x"))
    s = run(Path(a.out), a.binary, a.frames, w, h, a.only.split(",") if a.only else None)
    print(json.dumps(s, indent=1))
    return 1 if s["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
