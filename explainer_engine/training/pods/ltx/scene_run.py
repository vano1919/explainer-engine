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


def job_spec(scene_path, launch=None) -> dict:
    """The worker's ``--job`` spec: the first shot with the start picture's pin, the run's ids, the model's own size and rate,
    and the other shots as its ``chain`` (each starts from the clip before it)."""
    launch = L.LAUNCH if launch is None else launch
    scene = json.loads(Path(scene_path).read_text(encoding="utf-8"))
    pic = scene["start_picture"]
    have = hashlib.sha256(Path(pic["path"]).read_bytes()).hexdigest()
    if have != pic["sha256"]:
        raise SystemExit(f"the start picture {pic['path']} is not the one the scene pins")
    shots = scene["shots"]
    secs = {float(s["seconds"]) for s in shots}
    nat = L.native_spec(launch, max(secs))
    sha = plan_sha(scene_path)
    first = dict(shots[0], start_picture=pic["path"], extra={"start_sha256": pic["sha256"]}, plan_sha256=sha,
                 run_id=L.run_id(sha, launch), launch_sha=L.launch_sha(launch), fps=nat["fps"], width=nat["width"],
                 height=nat["height"], chain=[dict(s) for s in shots[1:]])
    first["ledger"] = {"path": str(LEDGER), "service": SERVICE, "item": f"{first['run_id']}/{first['shot_id']}"}
    L.preflight(launch, first)
    return first


def item(spec: dict) -> str:
    return spec["ledger"]["item"] if spec.get("ledger") else f"{spec['run_id']}/{spec['shot_id']}"


def open_ledger(path=LEDGER) -> Run:
    return Run.open(path, caps={SERVICE: float(spend_caps.modal_ltx()["per_run_usd"])}, what="LTX scene tests (D-132)")


def reserve(spec: dict, launch=None, path=LEDGER) -> float:
    launch = L.LAUNCH if launch is None else launch
    run = open_ledger(path)
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
