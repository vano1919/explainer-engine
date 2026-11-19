"""The RunPod runner of the LTX A/B (W5, plan RUNPOD_AB_PLAN.md section 3; D-132 video route, platform chosen by the creator,
decision cmsg_01Hnu5zB86sjUj5GtTgaUkPWYBU8BqKt8DFFsw46f9xMHj; no spend approved by that choice).

It does not fork the Modal worker: every pure function (job kinds and their refusals, CLI arguments, run record, file pins, the
clip generator, the HF upload and its sha256 verify) is ``modal_ltx_jobs``'s. Only the place of the weights differs
(``$EE_LTX_VOL_ROOT``, ``/workspace/dl`` on a pod) and the ladder: L0 tests and L1 ``runpod dryrun`` are free and local; L2 is the
first step inside the pod (download every file of the batch, size and sha256, stop at once on any fail, before any model load);
L3 is one smoke clip on that card; L4 is the batch, each clip uploaded and sha256-verified before the next starts (OR-33).

Local, before any ``create``:  ``python -m explainer_engine.training.pods.ltx.runpod_ltx_jobs plan --cap-usd X --card N jobs...``
Pod side (inside ``pod_wrapper.sh``, started by ``runpod_ltx_pod.sh``):  ``... run batch.json``.
Start a pod only through ``python -m explainer_engine.cloud.runpod create --ledger ...`` (guard, heartbeat, verified stop); this
module never creates, stops or deletes anything.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from explainer_engine.core import spend_caps
from explainer_engine.training.pods.ltx import modal_ltx_jobs as M
from explainer_engine.videolane.plan import CT1_MAX_HOP

ROOT = Path(__file__).resolve().parents[4]
PINS_PATH = ROOT / "config" / "cloud_pins.json"
SMOKE_TIMEOUT_S = 900   # the smoke clip alone never runs longer (the plan: 2 / 3 / 5 min)
EXIT = {"DONE": 0, "L2_FAILED": 3, "L3_FAILED": 4, "CAPPED": 5, "UPLOAD_FAILED": 6, "CLIP_FAILED": 7, "REFUSED": 8}


def section(launch: dict | None = None) -> dict:
    return (launch or M.LAUNCH)["runpod"]


def card_of(launch: dict, n: int = 0, cloud: str = "COMMUNITY") -> tuple[str, float]:
    c = section(launch)["cards"][n]
    return c["gpu"], float(c["usd_per_h"][cloud])


def batch_files(launch: dict, jobs: list[dict]) -> dict:
    """What L2 downloads and checks for this batch: the clip route's files, plus the kind files of every job whose kind needs them
    (``needed_files``), so a guided job's dev transformer and LoRA are in the list that is sha256-proved before any load."""
    out = dict(M.needed_files(launch))
    for j in jobs:
        out.update(M.needed_files(launch, j))
    return out


def _minutes(launch: dict, key: str, idx: int) -> float:
    return float(section(launch)["minutes"][key][idx])


def job_minutes(launch: dict, job: dict, idx: int) -> float:
    return _minutes(launch, "run_guided" if M.kind_needs(job) else "run_distilled", idx)


def estimate(launch: dict, jobs: list[dict], price: float) -> dict:
    """The batch's bill as min / expected / max from the plan's minutes table: one pod, setup once, every job, the smoke clip."""
    out = {}
    for name, idx in (("min", 0), ("expected", 1), ("max", 2)):
        setup = sum(_minutes(launch, k, idx) for k in ("boot", "download", "load", "smoke"))
        mins = setup + sum(job_minutes(launch, j, idx) for j in jobs)
        out[name] = {"minutes": round(mins, 1), "usd": round(mins / 60.0 * price, 2)}
    return out


def batch_problems(launch: dict, jobs: list[dict], *, price: float, cap_usd: float | None, pins: dict | None = None,
                   caps: dict | None = None, check_image: bool = True) -> list[str]:
    """The refusals that run locally before ``create`` (and again in the pod before L2): the Modal worker's own job refusals, hop > 2,
    the EXPECTED estimate over the owner's cap (the max is shown as a review line, not a refusal: the guard stops the pod at the cap), a cap above the creator's ceilings, no pinned image."""
    pins = pins if pins is not None else json.loads(PINS_PATH.read_text(encoding="utf-8"))["models"]["video_ltx"]
    caps = caps if caps is not None else spend_caps.runpod()
    bad = []
    sec = section(launch)
    if check_image:
        if not sec.get("image"):
            bad.append(f"runpod: no pinned image ({sec.get('image_why', 'launch.json runpod.image')})")
        else:
            from explainer_engine.cloud import pins as cloud_pins
            bad += [f"runpod: image: {p} (config/cloud_pins.json)" for p in cloud_pins.check_image(sec["image"])]
    if not cap_usd or cap_usd <= 0:
        bad.append("runpod: no cap: the creator's cap answer is not recorded (pass --cap-usd only from his word)")
    elif cap_usd > float(caps["per_pod_usd"]) + 1e-9:
        bad.append(f"runpod: cap {cap_usd} is above per_pod_usd {caps['per_pod_usd']}")
    files = batch_files(launch, jobs)
    for j in jobs:
        sid = j.get("shot_id")
        bad += [f"{sid}: {p}" for p in M.kind_problems(launch, j, pins)]
        hop = j.get("hop")
        if isinstance(hop, int) and hop > CT1_MAX_HOP:
            bad.append(f"{sid}: hop {hop} is above CT1_MAX_HOP {CT1_MAX_HOP} (CT1-01): a fresh keyframe is needed")
        for role in M.kind_needs(j):
            f = (launch.get("kind_uses") or {}).get(role)
            if f not in files:
                bad.append(f"{sid}: {role} is not in the L2 file list of this batch")
    if cap_usd and jobs:
        est = estimate(launch, jobs, price)
        if est["expected"]["usd"] > cap_usd + 1e-9:
            bad.append(f"runpod: the batch's expected estimate ${est['expected']['usd']} is over the cap ${cap_usd} "
                       f"(max ${est['max']['usd']}): split it by shot or ask for another cap")
        worst_one = max(job_minutes(launch, j, 2) for j in jobs)
        setup_max = sum(_minutes(launch, k, 2) for k in ("boot", "download", "load", "smoke"))
        if (setup_max + worst_one) / 60.0 * price > cap_usd + 1e-9:
            bad.append(f"runpod: setup (max {setup_max} min) plus the largest single run (max {worst_one} min) is over the cap "
                       f"${cap_usd}: not even one clip would fit")
    return bad


def batch_review(launch: dict, jobs: list[dict], *, price: float, cap_usd: float | None) -> list[str]:
    """Lines for the owner, not refusals: the worst case may pass the cap; the guard stops the pod there (a stop, not a refund)."""
    if not (cap_usd and jobs):
        return []
    mx = estimate(launch, jobs, price)["max"]["usd"]
    return [f"REVIEW: the max estimate ${mx} is over the cap ${cap_usd}: the guard stops the pod at the cap, clips not yet made stay unmade"] \
        if mx > cap_usd + 1e-9 else []


LAUNCHER = Path(__file__).with_name("runpod_ltx_pod.sh")


def script_problems(text: str | None = None) -> list[str]:
    """The pod script must be built (its code bundle's sha256 filled in) before a create: an unbuilt template fails closed in the pod
    and is refused here first."""
    text = LAUNCHER.read_text(encoding="utf-8") if text is None else text
    return ["runpod_ltx_pod.sh: the code bundle sha256 is not filled in (@@EE_SRC_SHA256@@): build the bundle first"] if "@@" in text else []


def _ab():
    from explainer_engine.training.pods.ltx import ab_bundle
    return ab_bundle


def smoke_job(launch: dict, first: dict) -> dict:
    """The L3 smoke clip: the Modal ladder's own SMOKE_JOB, at the model's native size, on the first job's start picture."""
    nat = M.native_spec(launch, M.SMOKE_JOB["seconds"])
    pic = first["start_bytes"]
    import hashlib
    return dict(M.SMOKE_JOB, fps=nat["fps"], width=nat["width"], height=nat["height"], start_bytes=pic,
                start_sha256=hashlib.sha256(pic).hexdigest())


def verify_clip(api, out: Path, prefix: str, clip: Path, record: Path, op=None) -> list[str]:
    """OR-33: the clip and its run record are on HF and their sha256 matches; the next clip never starts before this is empty."""
    seen: dict = {}
    for _ in range(2):
        M.upload_round(api, out, prefix, seen, final=True, op=op)
    res = M.verify_uploads(api, out, prefix)
    return [f"{n}: {v}" for n, v in res.items() if n in (clip.name, record.name) and v != "ok"] or \
           ([f"{clip.name}: not verified"] if clip.name not in res else [])


def write(out: Path, name: str, obj) -> Path:
    from explainer_engine.core.store import write_json_atomic
    p = Path(out) / name
    write_json_atomic(p, obj)
    return p


def progress(out: Path, text: str):
    (Path(out) / "progress.txt").write_text(text[:60], encoding="utf-8")


def run(batch: dict, jobs: list[dict], out, *, api=None, sh=subprocess.run, download=None, clock=time.time,
        vol_root=None, tmp="/workspace/tmp/in", upload_op=None, created=None) -> dict:
    """The pod side. ``batch``: card, price, cap_usd, prefix (HF folder). ``jobs``: read_job results. Returns the end word and the
    per-step records (also written under ``out``): DONE, L2_FAILED, L3_FAILED, CAPPED, UPLOAD_FAILED, CLIP_FAILED, REFUSED."""
    launch, out = M.LAUNCH, Path(out)
    out.mkdir(parents=True, exist_ok=True)
    price, cap, prefix = float(batch["price"]), float(batch["cap_usd"]), batch["prefix"]
    sec = section(launch)
    vol = vol_root or sec["weights_dir"]
    os.environ["EE_LTX_VOL_ROOT"] = str(vol)
    t0 = float(created if created is not None else (os.environ.get("EE_CREATED") or clock()))   # the pod's birth: boot, pip, clone count
    rec = {"card": batch.get("card"), "price_usd_per_h": price, "cap_usd": cap, "launch_sha": M.launch_sha(launch), "steps": {}}
    spent = lambda: (clock() - t0) / 3600.0 * price      # noqa: E731 - measured pod seconds times the card price

    def end(word: str, **kw) -> dict:
        rec.update(end=word, spent_usd=round(spent(), 3), seconds=round(clock() - t0, 1), **kw)
        write(out, "run_record.json", rec)
        progress(out, f"{word} ${spent():.2f}")
        return rec

    why = batch_problems(launch, jobs, price=price, cap_usd=cap, check_image=False)   # the image was checked by `create` (pins)
    rec_cap = section(launch).get("cap_usd")          # the creator's recorded cap: neither the batch nor the pod's own cap may pass it
    for name, val in (("batch cap_usd", cap), ("EE_MAX_USD", os.environ.get("EE_MAX_USD"))):
        if val not in (None, "") and (not rec_cap or float(val) > float(rec_cap) + 1e-9):
            why.append(f"{name} {val} is above the recorded launch.runpod.cap_usd {rec_cap}: create --max-usd must be the creator's number")
    if why:
        return end("REFUSED", problems=why)
    # L2: the first step, before any model load; any missing or mismatched file ends the pod at once
    progress(out, "L2 weights")
    files = batch_files(launch, jobs)
    with_kind = any(M.kind_needs(j) for j in jobs)
    assert set(files) <= set(M.needed_files(launch, None, with_kind)), "L2 must cover the batch's whole file list in one pass"
    bad = M.stage_weights(launch, vol, download=download, with_kind=with_kind)   # one download and one sha256 pass over the union
    rec["steps"]["L2"] = {"ok": not bad, "files": sorted(files), "with_kind": with_kind, "problems": bad}
    if bad:
        return end("L2_FAILED", problems=bad)
    # L3: one short smoke clip on this card, recorded with the card name and the measured seconds; red stops the pod
    progress(out, "L3 smoke")
    smoke_out = out / "L3"
    smoke_out.mkdir(exist_ok=True)
    sm = smoke_job(launch, jobs[0])
    row = M.generate(sm, launch, smoke_out, M.Deadline(SMOKE_TIMEOUT_S, margin_s=0), sh=sh, tmp=tmp)
    rec["steps"]["L3"] = {"ok": row.get("state") == "DONE", "card": batch.get("card"), "gen_s": row.get("gen_s"),
                          "s_per_clip_s": row.get("s_per_clip_s"), "state": row.get("state")}
    write(out, "L3_smoke.record.json", {"shot_id": sm["shot_id"], "step": rec["steps"]["L3"], "record": row.get("record"),
                                             "card": batch.get("card"), "launch_sha": M.launch_sha(launch)})
    if api is not None:
        M.upload_round(api, out, prefix, {}, final=True, op=upload_op)
    if row.get("state") != "DONE":
        return end("L3_FAILED", problems=[f"smoke clip {row.get('state')} rc={row.get('rc')}"])
    # L4: the batch, shot by shot; at 80 % of the cap no new clip starts; each clip is verified on HF before the next one
    clips = []
    for j in jobs:
        sid = j["shot_id"]
        if spent() >= float(sec["problem_at"]) * cap or spent() + job_minutes(launch, j, 2) / 60.0 * price > cap:
            return end("CAPPED", clips=clips, problems=[f"PROBLEM: ${spent():.2f} of the cap ${cap}: no new clip ({sid} not started)"])
        progress(out, f"L4 {sid}")
        left = max(60.0, (cap - spent()) / price * 3600.0)
        row = M.generate(j, launch, out, M.Deadline(left, margin_s=0), sh=sh, tmp=tmp)
        record = write(out, f"{sid}.record.json", {"shot_id": sid, "row": {k: v for k, v in row.items() if k != "record"},
                                                   "record": row.get("record"), "card": batch.get("card"),
                                                   "launch_sha": M.launch_sha(launch)})
        if row.get("state") != "DONE":
            clips.append({"shot_id": sid, "state": row.get("state")})
            return end("CLIP_FAILED", clips=clips, problems=[f"{sid}: {row.get('state')} rc={row.get('rc')}"])
        clip = out / M.clip_name(sid, j["seed"])
        if api is not None:
            bad = verify_clip(api, out, prefix, clip, record, op=upload_op)
            if bad:
                clips.append({"shot_id": sid, "state": "NOT_VERIFIED"})
                return end("UPLOAD_FAILED", clips=clips, problems=bad)
        clips.append({"shot_id": sid, "state": "DONE", "sha256": row.get("sha256"), "gen_s": row.get("gen_s"), "verified": api is not None})
    return end("DONE", clips=clips)


# --- local side -------------------------------------------------------------------------------------------------------------
def plan(job_paths: list[str], *, card: int = 0, cloud: str = "COMMUNITY", cap_usd: float | None = None, launch=None) -> dict:
    """What ``create`` may be asked for: the refusals, the estimate and the L2 list. Reads files only: no pod, no money."""
    launch = launch or M.LAUNCH
    cap_usd = cap_usd if cap_usd is not None else section(launch).get("cap_usd")   # the creator's recorded $3.50 unless another is passed
    jobs = [M.read_job(p, launch) for p in job_paths]
    gpu, price = card_of(launch, card, cloud)
    why = batch_problems(launch, jobs, price=price, cap_usd=cap_usd) + script_problems()
    why += [w for w in _ab().code_problems(LAUNCHER) if "is not filled in" not in w or not script_problems()]
    return {"ok": not why, "problems": why, "review": batch_review(launch, jobs, price=price, cap_usd=cap_usd), "card": gpu, "cloud": cloud, "price_usd_per_h": price, "cap_usd": cap_usd,
            "estimate": estimate(launch, jobs, price) if jobs else None, "l2_files": sorted(batch_files(launch, jobs)),
            "problem_at_usd": round(float(section(launch)["problem_at"]) * cap_usd, 2) if cap_usd else None}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else ""
    opts = {}
    while argv and argv[0].startswith("--"):
        k = argv.pop(0)
        opts[k] = argv.pop(0)
    if cmd == "plan":
        res = plan(argv, card=int(opts.get("--card", 0)), cloud=opts.get("--cloud", "COMMUNITY"),
                   cap_usd=float(opts["--cap-usd"]) if "--cap-usd" in opts else None)
        print(json.dumps(res, indent=2))
        raise SystemExit(0 if res["ok"] else 2)
    if cmd == "run":
        batch = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        os.chdir(Path(argv[0]).resolve().parent)            # job specs and pictures are relative to the unpacked batch
        jobs = [M.read_job(p) for p in batch["jobs"]]
        from huggingface_hub import HfApi
        res = run(batch, jobs, os.environ.get("EE_OUT", "/workspace/out"), api=HfApi(token=M._tok()))
        raise SystemExit(EXIT[res["end"]])
    raise SystemExit("usage: runpod_ltx_jobs plan [--card N] [--cloud C] --cap-usd X job.json... | run batch.json")


if __name__ == "__main__":
    main()
