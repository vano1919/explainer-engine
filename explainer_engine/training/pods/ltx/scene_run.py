"""The local half of one LTX scene test (D-132): the worker's job spec from a committed scene file, and the ledger around the one
paid launch. The launch itself is a plain Bash command the session hook reads (``modal run ...modal_ltx_jobs.py::main``), never a
subprocess hidden in here.

    python -m explainer_engine.training.pods.ltx.scene_run job     <scene.json> <spec.json>      # free: pins, sizes, chain
    python -m explainer_engine.training.pods.ltx.scene_run reserve <scene.json>                  # before the launch
    EE_MODAL_GO=<cmsg>:<scene sha[:12]> modal run explainer_engine/training/pods/ltx/modal_ltx_jobs.py::main --job <spec.json>

The scene file is the plan the creator said yes to: its sha256 is the plan sha the GO names and the run id carries. One
reservation per scene and run id; a second ``reserve`` is refused (a repeat would pay twice). The reservation is the launch's
``caps.run_usd``, the worker's timeout comes from the same number, so the ledger and the container agree. The worker's ``main``
itself refuses a spec without that open reservation, marks the launch before it starts the GPU, refuses a second launch of the
spec, and settles from its own wall clock at the GPU rate (``modal_ltx_jobs.claim_launch`` / ``settle_launch``; audit B2)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import Run
from explainer_engine.core.store import write_json_atomic
from explainer_engine.training.pods.ltx import modal_ltx_jobs as L

LEDGER = Path("/mnt/project-files/explainer-engine/ledgers/ltx_scene_test.json")
SERVICE = "modal_ltx"


def plan_sha(scene_path) -> str:
    return hashlib.sha256(Path(scene_path).read_bytes()).hexdigest()


def scene_pictures(scene: dict) -> dict:
    """{shot_id: {path, sha256}}: the love scene's one start picture (its other shots chain from the clip before), or, for a
    scene of cuts, the picture of every shot from the pictures stage's manifest (``scene_pictures.py collect``); a
    continuation shot of a /3 scene (``continue_frame``, VL-05) has none: it starts from the clip before."""
    shots = scene["shots"]
    if scene.get("start_picture"):
        return {shots[0]["shot_id"]: scene["start_picture"]}
    man = json.loads(Path(scene["pictures"]["manifest"]).read_text(encoding="utf-8"))
    out = {}
    for k, s in enumerate(shots):
        if k and s.get("continue_frame") and not s.get("picture"):   # VL-05: starts from a frame of the clip before
            continue
        pic = (man.get("shots") or {}).get(s.get("picture") or "")
        if not pic:
            raise SystemExit(f"{s['shot_id']}: no picture {s.get('picture')!r} in the pictures manifest; make it first")
        out[s["shot_id"]] = pic
    return out


def worst_gpu_usd(launch: dict) -> float:
    """The most one launch can bill: the GPU function's hard timeout plus the cold start (startup timeout), at the rate."""
    t = L.timeouts(launch)
    if not t:
        raise SystemExit("the launch file is not pinned")
    return round((t[1] + float(launch["caps"]["cold_start_s"])) * L.usd_per_h(launch) / 3600.0, 4)


def budget_problems(scene: dict, launch: dict) -> list[str]:
    """The creator's total for the scene (``budget.total_usd``) holds the worst case: the GPU launch's hard bill, the
    pictures' batch price and the CPU rungs together."""
    b = scene.get("budget")
    if not b:
        return []
    gpu = worst_gpu_usd(launch)
    worst = gpu + float(b["pictures_usd"]) + float(b["cpu_checks_usd"])
    if worst > float(b["total_usd"]) + 1e-9:
        return [f"the worst case ${worst:.3f} (GPU ${gpu}, pictures ${b['pictures_usd']}, CPU rungs "
                f"${b['cpu_checks_usd']}) passes the scene's total ${b['total_usd']}"]
    return []


def job_spec(scene_path, launch=None) -> dict:
    """The worker's ``--job`` spec: the first shot with the start picture's pin, the run's ids, the model's own size and rate,
    and the other shots as its ``chain``: each starts from the clip before it, or from its own pinned picture (a cut)."""
    launch = L.LAUNCH if launch is None else launch
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    from explainer_engine.videolane.scene import storyboard_problems
    bad = storyboard_problems(scene) + budget_problems(scene, launch)
    if bad:
        raise SystemExit("; ".join(bad))
    pics = scene_pictures(scene)
    for sid, pic in pics.items():
        have = hashlib.sha256(Path(pic["path"]).read_bytes()).hexdigest()
        if have != pic["sha256"]:
            raise SystemExit(f"the start picture {pic['path']} of {sid} is not the one the scene pins")
    shots = scene["shots"]
    secs = {float(s["seconds"]) for s in shots}
    nat = L.native_spec(launch, max(secs))
    sha = plan_sha(scene_path)
    chain = []
    for s in shots[1:]:
        c = dict(s)
        if s["shot_id"] in pics:
            c.update(start_picture=pics[s["shot_id"]]["path"], extra={"start_sha256": pics[s["shot_id"]]["sha256"]})
        chain.append(c)
    pic = pics[shots[0]["shot_id"]]
    first = dict(shots[0], start_picture=pic["path"], extra={"start_sha256": pic["sha256"]}, plan_sha256=sha,
                 run_id=L.run_id(sha, launch), launch_sha=L.launch_sha(launch), fps=nat["fps"], width=nat["width"],
                 height=nat["height"], chain=chain)
    path = (scene.get("ledger") or {}).get("path") or str(LEDGER)
    first["ledger"] = {"path": path, "service": SERVICE, "item": f"{first['run_id']}/{first['shot_id']}"}
    if (scene.get("ledger") or {}).get("caps"):
        first["ledger"]["caps"] = scene["ledger"]["caps"]
    L.preflight(launch, first)
    return first


def item(spec: dict) -> str:
    return spec["ledger"]["item"] if spec.get("ledger") else f"{spec['run_id']}/{spec['shot_id']}"


def open_ledger(path=LEDGER, caps: dict | None = None) -> Run:
    """The scene's ledger: its own caps when the scene names them (``ledger.caps``, every line under the creator's ceilings),
    else the creator's modal_ltx line (the love scene)."""
    return Run.open(path, caps=caps or {SERVICE: float(spend_caps.modal_ltx()["per_run_usd"])}, what="LTX scene tests (D-132)")


def reserve(spec: dict, launch=None, path=LEDGER) -> float:
    launch = L.LAUNCH if launch is None else launch
    run = open_ledger(path, (spec.get("ledger") or {}).get("caps"))
    if item(spec) in run.data.get("reserved", {}):
        raise SystemExit(f"the ledger already holds {item(spec)}: this scene was launched; a repeat needs a new scene file")
    usd = float(launch["caps"]["run_usd"])
    run.reserve(SERVICE, usd, item(spec))
    return usd


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scene_run")
    ap.add_argument("cmd", choices=("job", "reserve"))
    ap.add_argument("scene")
    ap.add_argument("out", nargs="?")
    a = ap.parse_args(argv)
    spec = job_spec(a.scene)
    if a.cmd == "job":
        if not a.out:
            raise SystemExit("job needs the spec path to write")
        write_json_atomic(Path(a.out), spec)
        print(json.dumps({"spec": a.out, "run_id": spec["run_id"], "go_sha12": spec["plan_sha256"][:12],
                          "shots": [spec["shot_id"]] + [c["shot_id"] for c in spec["chain"]]}))
    else:
        print(json.dumps({"reserved_usd": reserve(spec, path=spec["ledger"]["path"]), "item": item(spec)}))


if __name__ == "__main__":
    main()
