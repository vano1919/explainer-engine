"""Host side of the lean step-3 pod (free, no pod, no upload): the files the pod reads, written from the route shots, the stage list
and the pins, and the sha256 lines of ``p14.sh``.

    python -m explainer_engine.training.pods.p14.lean build    # ltx_jobs.json (the 5 lean jobs), ltx_extra.json (X1, X2, X5, X3, X6),
                                                               # p14.json, then the code bundle and the sha256 line in p14.sh
    python -m explainer_engine.training.pods.p14.lean bundle --out ee_src.tar.gz [--ref HEAD]   # the bundle only; prints its sha256

The bundle is the code the pod runs: every file git tracks under ``explainer_engine/``, ``config/`` and ``assets/`` at ``--ref``
(the working tree when no ref is given), except ``p14.sh`` itself (it pins the bundle's sha256, so it cannot be inside it). The tar is
byte-stable: sorted names, mtime 0, uid/gid 0, mode 0644, gzip without a name or time. The worker thread
uploads it with the three-line upload of the OR-34-audited commit (HF ``code/p14/ee_src.tar.gz``); this module never uploads.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

from explainer_engine.core.store import write_json_atomic
from explainer_engine.edit import ltx_jobs as LJ

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ROUTE_SHOTS = ROOT / "tests" / "fixtures" / "route_test" / "route_shots.json"
BUNDLE_DIRS = ("explainer_engine", "config", "assets")
EXCLUDE = ("explainer_engine/training/pods/p14/p14.sh",)
PLACE = "PLACE" + "HOLDER_SHA_EE_SRC_TAR_GZ"   # split so the dry run's placeholder check does not read this file as an unfilled pin
SHA_LINE = re.compile(r"^(printf '%s  %s\\n' )([0-9a-f]{64}|" + PLACE + r")( \"\$JOB/ee_src.tar.gz\")", re.M)
EXTRA_ORDER = ("X1", "X2", "X5", "X3", "X6")   # the creator's card 13:33 UTC: core 5 -> X1, X2, X5, X3 on the GPU; X6's LTX last


def stages() -> dict:
    return json.loads((HERE / "p14_stages.json").read_text(encoding="utf-8"))


def extra_jobs(core: dict, st: dict) -> dict:
    """The extras as pod jobs of the same shape as the core ones (the LTX-2.5 model, text encoder and LoRA rows copied from E1, so
    every weight stays pinned): X2 and X5 are IC-LoRA jobs like E1 with another conditioning or size; X1, X3 and X6 are plain
    image-to-video (``pipeline: distilled``, no LoRA, no control video)."""
    x, root = st["X"], f"{LJ.HF_ROOT}/step3"
    by = {j["id"]: j for j in core["jobs"]}
    e1 = by[x["X2"]["from_job"]]
    lay = lambda pas: f"{LJ.HF_ROOT}/layouts/battle/{pas}/battle_c1_{pas}.mp4"   # noqa: E731

    def i2v(key: str, spec: dict, clip: str) -> dict:
        jid = f"{key}.{clip}.{spec['base']}.i2v.s{spec['seed']}"
        return {"id": jid, "question": spec.get("question") or x[key]["question"], "recipe": spec["recipe"], "pipeline": "distilled",
                "shot_id": clip, "clip_id": clip, "base": spec["base"], "variant": "i2v", "model": copy.deepcopy(e1["model"]),
                "text_encoder": copy.deepcopy(e1["text_encoder"]), "lora": None, "frames": spec["frames"], "fps": 24,
                "width": spec["width"], "height": spec["height"], "seed": spec["seed"],
                "first_frame": {"path": f"{root}/{spec['first_frame']}", "sha256": None, "pose": "start"},
                "conditioning": [], "attention_mask": None, "chain_from": None, "prompt": spec["prompt"], "stage2_ic": False,
                "output": f"{root}/ltx/{jid}.mp4"}

    def ic(key: str, **over) -> dict:
        j = copy.deepcopy(e1)
        j.update(over, question=x[key]["question"], conditioning=[
            {"pass": c["pass"], "path": lay(c["pass"]), "sha256": None, "derive": c["derive"], "strength": c["strength"]}
            for c in x[key]["conditioning"]])
        j["output"] = f"{root}/ltx/{j['id']}.mp4"
        return j

    jobs = {
        "X1": i2v("X1", x["X1"], "S03-02"),
        "X2": ic("X2", id=f"X2.{e1['clip_id']}.ltx25.line_inv.s{e1['seed']}", variant="line_inv"),
        "X5": ic("X5", id=f"X5.{e1['clip_id']}.ltx25.colour2k.s{e1['seed']}", variant="colour_2k", width=x["X5"]["width"],
                 height=x["X5"]["height"], size_note=x["X5"]["size_note"]),
        "X3": i2v("X3", x["X3"], x["X3"]["shot"]),
        "X6": i2v("X6", dict(x["X6"]["ltx"], question=x["X6"]["question"]), x["X6"]["shot"]),
    }
    for k in ("X2", "X5"):
        jobs[k]["first_frame"] = copy.deepcopy(e1["first_frame"])
    return {"schema": "p14_extra_jobs/1", "code": core["code"], "jobs": [jobs[k] for k in EXTRA_ORDER]}


def pod_config() -> dict:
    cfg = LJ.pod_config()
    cfg["extra_jobs_file"] = "ltx_extra.json"
    # X5 (2560x1472): the 1920x1088 colour pass scaled to cover the 2K grid size and cut from the centre (1920 * 1472 / 1088 = 2597.6)
    cfg["controls"]["scale_2k_vf"] = "scale=2598:1472:flags=lanczos,crop=2560:1472"
    return cfg


def bundle(out: Path, ref: str | None = None) -> str:
    """The byte-stable code tarball (see the module text); returns its sha256."""
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files" if ref is None else "ls-tree", *([] if ref is None else ["-r",
                            "--name-only", ref]), "--", *BUNDLE_DIRS], check=True, capture_output=True, text=True).stdout.split("\n")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for n in sorted(x for x in names if x and x not in EXCLUDE):
            if ref is None:
                p = ROOT / n
                if not p.is_file():
                    continue
                data = p.read_bytes()
            else:
                data = subprocess.run(["git", "-C", str(ROOT), "show", f"{ref}:{n}"], check=True, capture_output=True).stdout
            ti = tarfile.TarInfo(n)   # every file 0644: the pod runs scripts through bash / python, never by their mode
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid, ti.uname, ti.gname = len(data), 0, 0o644, 0, 0, "", ""
            tar.addfile(ti, io.BytesIO(data))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0, compresslevel=9) as gz:
        gz.write(buf.getvalue())
    return hashlib.sha256(out.read_bytes()).hexdigest()


def pin(sha: str, sh: Path = HERE / "p14.sh") -> None:
    text = sh.read_text(encoding="utf-8")
    new, n = SHA_LINE.subn(lambda m: m.group(1) + sha + m.group(3), text)
    if n != 1:
        raise SystemExit(f"{sh}: the bundle's sha256 line was found {n} times, not once")
    sh.write_text(new, encoding="utf-8")


def build(bundle_out: Path) -> dict:
    rs = json.loads(ROUTE_SHOTS.read_text(encoding="utf-8"))
    core = LJ.build(rs, matrix=LJ.LEAN, out_root="step3")
    write_json_atomic(HERE / "ltx_jobs.json", core)
    write_json_atomic(HERE / "ltx_extra.json", extra_jobs(core, stages()))
    write_json_atomic(HERE / "p14.json", pod_config())
    sha = bundle(bundle_out)
    pin(sha)
    return {"bundle": str(bundle_out), "sha256": sha, "jobs": [j["id"] for j in core["jobs"]],
            "extras": [j["id"] for j in json.loads((HERE / "ltx_extra.json").read_text())["jobs"]]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--bundle", type=Path, default=ROOT / "jobs" / "p14" / "ee_src.tar.gz")
    u = sub.add_parser("bundle")
    u.add_argument("--out", type=Path, required=True)
    u.add_argument("--ref")
    a = ap.parse_args(argv)
    if a.cmd == "bundle":
        print(bundle(a.out, a.ref))
        return 0
    print(json.dumps(build(a.bundle), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
