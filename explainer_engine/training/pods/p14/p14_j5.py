"""The lean step-3 pod, stage G (the creator 2026-11-06 13:25 UTC): the J5 shots of the pilot window (``production/pilot.py`` at 60 s:
S01-01..06, S02-04, S03-01, S03-03) rendered with ``blender/assemble_25d`` on the pod's CPU at 2560x1440 from the asset pod's
backdrops and stage D's cut-outs, with ``handles_frames`` (12, BP-128) before and after each shot. It runs beside the LTX stage on the
CPU (``nice``; Mesa's software EGL, the card stays LTX's), shot by shot, frame by frame (the frames land under ``$EE_OUT`` and the
wrapper uploads them: OR-33), and stops at the deadline reserve: the LTX jobs come first.

What is NOT in this render, and why (each also in ``j5/report.json``): no prop cards (no prop picture is drawn yet), no mouth states and
no lip-sync (no mouth sheets are drawn; the narration comes later), no camera move beyond each named setup's own rig, one figure
height for every hero (``height_m``, the assemble smoke's 1.75 m). The pilot reads ``j5/<shot>/frames/`` and ``handles.json``.

    python3 -m explainer_engine.training.pods.p14.p14_j5 --out <step3 dir> --assets <dir> --binary <blender> [--deadline EPOCH]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine.training.pods.p14.p14_qwen import load_cfg, sha256_file

ANGLES = ("front", "3q_left", "3q_right", "back")
LIGHTING = "flat ambient lighting, no cast shadows"


def scene_assets(cfg: dict, cutouts: Path, backdrops: Path) -> dict:
    """The ``scene_assets/1`` document of the window: per scene its backdrop and every hero card stage D cut (paths relative to the
    document's folder, the cards' own sha256)."""
    from explainer_engine.qa import style_prompt
    g, d = cfg["G"], cfg["D"]
    rows = {}
    rep = Path(cutouts) / "report.json"
    if rep.exists():
        rows = {r["name"]: r for r in json.loads(rep.read_text(encoding="utf-8"))["pictures"] if r.get("status") == "ok"}
    heroes = {}
    for pic in d["pictures"]:
        r = rows.get(pic["name"])
        if not r:
            continue
        h = heroes.setdefault(pic["hero"], {"hero": pic["hero"], "sheet": f"sheet.{pic['hero'].lower()}", "height_m": g["height_m"],
                                            "lighting_note": LIGHTING, "prompt": f"{style_prompt.TRIGGER}, hero sheet {pic['hero']}, "
                                            f"{LIGHTING}, plain neutral background", "angles": {}})
        h["angles"][pic["angle"]] = {"base": {"path": f"cutout/{pic['name']}.png", "sha256": r["sha256"]}}
    scenes = {}
    for sc, ref in g["backdrops"].items():
        scenes[sc] = {"backdrop_360": {"asset": ref["name"], "size": [2048, 1024], "prompt": g["backdrop_prompts"][sc], "yaw_deg": 0,
                                       "file": {"path": f"backdrops/{ref['name']}.png", "sha256": ref["sha256"]}},
                      "heroes": list(heroes.values()), "props": [], "defects": []}
    return {"schema": "scene_assets/1", "episode": "route_test_2026-11 lean pod",
            "style": {k: style_prompt.INFERENCE[k] for k in ("base", "lora", "lora_weight")}, "scenes": scenes}


def shots(cfg: dict) -> list[dict]:
    """The assemble shots of the window, each lengthened by the handles before and after (the camera rig spans the whole render)."""
    g = cfg["G"]
    extra = 2 * g["handles_frames"] / 24.0
    return [dict(s, seconds=g["seconds"][s["id"]] + extra) for s in g["shots"]]


def fetch_backdrops(cfg: dict, assets: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for ref in cfg["G"]["backdrops"].values():
        src = Path(assets) / ref["path"].split("/", 1)[1]
        if not src.exists():
            from huggingface_hub import hf_hub_download
            src = Path(hf_hub_download("vano1919/tmr-artifacts", ref["path"], repo_type="dataset", local_dir=str(assets)))
        if sha256_file(src) != ref["sha256"]:
            raise ValueError(f"{ref['name']}: not the pinned sha256")
        shutil.copyfile(src, dest / f"{ref['name']}.png")


def render_shot(body: dict, d: Path, launcher: list[str], pin: str, *, deadline: float | None, nice: int, popen=subprocess.Popen) -> dict:
    """One shot through bpy/assemble_25d.py, killed at ``deadline`` (frames already written stay: the job writes frame by frame)."""
    from explainer_engine.blender import assemble_25d as A
    from explainer_engine.core.store import write_json_atomic
    d.mkdir(parents=True, exist_ok=True)
    write_json_atomic(d / "job.json", A.job(body, d, pin))
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", __EGL_VENDOR_LIBRARY_FILENAMES="/usr/share/glvnd/egl_vendor.d/50_mesa.json")
    cmd = ["nice", "-n", str(nice), *A.command(launcher, d / "job.json")]
    t0 = time.time()
    with open(d / "blender.log", "w", encoding="utf-8") as lf:
        p = popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env)
        while p.poll() is None:
            if deadline and time.time() > deadline:
                p.kill()
                p.wait()
                break
            time.sleep(5)
    frames = sorted((d / "frames").glob("frame_*.png"))
    return {"rc": p.returncode, "frames": len(frames), "of": body["frames"], "wall_s": round(time.time() - t0, 1),
            "s_per_frame": round((time.time() - t0) / max(len(frames), 1), 2), "stopped_at_deadline": bool(deadline and time.time() > deadline)}


def run(out: Path, assets: Path, binary: str, *, deadline: float | None = None, render=render_shot, on_shot=None) -> int:
    from explainer_engine.blender import assemble_25d as A
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core.store import write_json_atomic
    cfg = load_cfg()
    g = cfg["G"]
    out = Path(out)
    jd = out / "j5"
    jd.mkdir(parents=True, exist_ok=True)
    fetch_backdrops(cfg, assets, out / "backdrops")
    doc = scene_assets(cfg, out / "cutout", out / "backdrops")
    write_json_atomic(out / "scene_assets.json", doc)
    proj = BlenderProject()
    launcher, pin = [proj.resolve(binary).path], proj.version
    report = {"schema": "p14_j5/1", "what": g["what"], "not_in_this_run": g["not_in_this_run"], "size": g["size"],
              "handles_frames": g["handles_frames"], "shots": {}}
    w, h = g["size"]
    for sh in shots(cfg):
        sid = sh["id"]
        row = report["shots"].setdefault(sid, {})
        if deadline and time.time() > deadline:
            row.update(status="skipped", reason="the deadline reserve (the LTX jobs come first)")
            continue
        try:
            body = A.plan(doc, sh, base=out, width=w, height=h, engine=g["engine"], samples=g["samples"])
        except Exception as e:   # noqa: BLE001 - a shot that cannot be planned (a missing card) is skipped, the next one runs
            row.update(status="skipped", reason=str(e)[:300])
            write_json_atomic(jd / "report.json", report)
            continue
        write_json_atomic(jd / sid / "handles.json", {"head": g["handles_frames"], "tail": g["handles_frames"], "fps": 24,
                                                      "shot_seconds": g["seconds"][sid]})
        r = render(body, jd / sid, launcher, pin, deadline=deadline, nice=g["nice"])
        row.update(r, status="ok" if r["frames"] == body["frames"] else "partial")
        write_json_atomic(jd / "report.json", report)
        if on_shot:
            on_shot(sid, jd / sid)
    done = [s for s, r in report["shots"].items() if r.get("status") == "ok"]
    write_json_atomic(jd / "report.json", report)
    return 0 if done else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lean step-3 pod: the J5 shots of the pilot window")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--assets", type=Path, required=True)
    ap.add_argument("--binary", required=True)
    ap.add_argument("--deadline", type=float)
    a = ap.parse_args(argv)
    return run(a.out, a.assets, a.binary, deadline=a.deadline)


if __name__ == "__main__":
    sys.exit(main())
