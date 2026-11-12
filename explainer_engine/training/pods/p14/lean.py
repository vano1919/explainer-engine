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


POD1 = "pod ygg2ztmflr8pv2 (H100, 2026-11-06 14:25-14:48 UTC, HF route_test_2026-11/step3/stages.txt and logs/)"
# stage: (lane, true consumers' inputs, expected min, max min, basis, source). Max = the stage's own timeout or budget; "measured"
# only where a run timed it. E's needs are per job (its layout clip, its first frame): listed as the stages that make them.
SCHEDULE = {
    "install": ("pod", [], 2.5, 20, "measured", f"{POD1}: script_start 14:25:02 -> runner 14:27:30"),
    "weights": ("net", ["install"], 5.5, 90, "measured", f"{POD1}: 14:27:30 -> 14:33:00 (both LTX bases, sha256 checked)"),
    "weights_qwen": ("net", ["install"], 5, 60, "estimated", f"{POD1}: done before 14:40, not timed alone"),
    "A.preflight": ("cpu", ["install"], 0.5, 2, "estimated", "duel line frame 0: 8.3 s on the pod CPU (measured), card unmeasured"),
    "A.frame0.duel": ("cpu", ["A.preflight"], 0.15, 10, "measured", f"{POD1}: duel/line 1 frame in 8.3 s (CPU)"),
    "A.frame0.battle": ("cpu", ["A.frame0.duel"], 10, 10, "measured",
                        f"{POD1}: killed by the kernel (-9, memory) after ~13 min on the CPU; now cut at 600 s"),
    "A.duel": ("cpu", ["A.frame0.battle"], 1.6, 90, "measured", f"{POD1}: clay 121 frames 14:40:26 -> 14:42:02"),
    "A.battle": ("cpu", ["A.duel"], 30, 90, "estimated", "colour + depth, 282 frames each: never finished on any machine"),
    "A.battle.line": ("cpu", ["A.battle", "A.frame0.battle"], 60, 60, "estimated",
                      "runs only when frame 0's seconds x 282 fit 3600 s; pod 1's frame 0 did not finish"),
    "X6.move": ("cpu", ["qwen1"], 1, 15, "estimated", "FFmpeg zoompan of one still"),
    "G": ("cpu", ["D"], 133, None, "measured",
          "8 s/frame x 996 frames on 4 vCPU (this container, assemble_25d 1440p EEVEE 16); pod scaling unmeasured; stops at the reserve"),
    "qwen1": ("gpu", ["weights_qwen"], 2.9, 60, "measured", f"{POD1}: load 61 s + C, C, X6 at 33.5-38.5 s each"),
    "D": ("gpu", ["qwen1"], 2, 30, "estimated", f"{POD1}: failed in 22 s on a float16 input (fixed); 12 pictures"),
    "qwen2": ("gpu", ["D", "A.frame0.duel"], 2.2, 60, "estimated", "Qwen load 61 s + 2 edits at ~35 s (pod 1's Qwen speed)"),
    "E": ("gpu", ["qwen2", "weights", "A.duel", "A.battle", "A.battle.line"], 25, 150, "estimated",
          "5 core clips at ~5 min (docs: the 22B takes >200 s per clip on RunPod), 30 min cap per clip"),
    "E.extras": ("gpu", ["E", "qwen1", "G"], 25, 150, "estimated", "X1, X2, X5 (2560x1472), X3 (G's frame), X6: ~5 min each"),
    "X4": ("gpu", ["E.extras", "G"], 1.7, 60, "estimated", "Qwen load + 1 edit"),
    "F": ("gpu", ["X4"], 0.1, 5, "estimated", "speeds.json from the records"),
}


def schedule() -> dict:
    """``p14_schedule.json``: the stage graph a scheduler reads (lane, needs, expected and max minutes, measured or estimated)."""
    from explainer_engine.training.pods.p14 import p14_pod
    return {"schema": "p14_schedule/1",
            "_doc": ("The lean step-3 pod's stages after the 14:44 UTC fix. lane: pod (p14.sh before the runner), net, cpu (Blender "
                     "on the card when A.preflight finds NVIDIA's EGL, then cpu means 'the Blender lane'), gpu (Qwen, BiRefNet, "
                     "LTX). needs: the stages whose output the stage reads (E's per job). max_min null: runs to the end reserve."),
            "end_reserve_min": stages()["end_reserve_min"], "preflight_s": p14_pod.PREFLIGHT_S,
            "stages": {k: {"lane": v[0], "needs": v[1], "expected_min": v[2], "max_min": v[3], "basis": v[4], "source": v[5]}
                       for k, v in SCHEDULE.items()}}


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
    write_json_atomic(HERE / "p14_schedule.json", schedule())
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
