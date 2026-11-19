"""The Klein picture pod of the LTX A/B (W5, plan RUNPOD_AB_PLAN.md section 5; the creator's word
cmsg_01Hnu5zB86sjUj5GtTgaUkPWU9kS1kT1CnB6HveYkz5rfQ; D-132 pictures route, level 3 of picture_route.json as open weights).

The same RunPod pattern as ``runpod_ltx_jobs`` (whose helpers it reuses, no fork): refusals before ``create``, L2 sha256 first and the
pod ends on any fail, one smoke picture as L3, each picture and its record uploaded and verified on HF before the next (OR-33), the
EE_CREATED clock with a stop at 80 % of the cap, and a cap that is the creator's recorded number only. Prompts, settings and
reference pictures come from the batch the plan thread writes; nothing is defaulted here: a missing setting is a refusal (OR-22).
The model id is switchable (``launch.model``: the gated flux-3-image-klein or FLUX.2-klein-4B); open pins (file list and sha256,
pipeline class, diffusers version, image, cap) are null until proven, and until then ``plan`` and ``run`` refuse.

Local:  ``python -m explainer_engine.training.pods.klein.klein_jobs plan batch.json``   Pod side:  ``... run batch.json``.
This module never creates, stops or deletes a pod.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from explainer_engine.core import spend_caps
from explainer_engine.training.pods.ltx import modal_ltx_jobs as M
from explainer_engine.training.pods.ltx import runpod_ltx_jobs as RL

LAUNCH_PATH = Path(__file__).with_name("launch.json")
LAUNCHER = Path(__file__).with_name("klein_pod.sh")
EXIT = {"DONE": 0, "L2_FAILED": 3, "L3_FAILED": 4, "CAPPED": 5, "UPLOAD_FAILED": 6, "PICTURE_FAILED": 7, "REFUSED": 8}
KINDS = ("edit", "sample")
HEX64 = M.HEX64


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


LAUNCH = load_launch()


def model_of(launch: dict, key: str | None = None) -> dict:
    return launch["models"][key or launch["model"]]


def launch_sha(launch: dict) -> str:
    return hashlib.sha256(json.dumps(launch, sort_keys=True).encode()).hexdigest()


def weights_root(launch: dict, vol_root=None) -> Path:
    return Path(vol_root or os.environ.get("EE_KLEIN_VOL_ROOT") or launch["weights_dir"]) / "model" / model_of(launch)["repo"]


def open_pins(launch: dict) -> list[str]:
    """Every null pin that blocks a create (OR-22): nothing is guessed, each is read from its source when proven."""
    m, out = model_of(launch), []
    if launch["model"] not in launch["models"]:
        return [f"model {launch['model']!r} is not one of {sorted(launch['models'])}"]
    if not m.get("revision"):
        out.append(f"{launch['model']}: revision is not pinned")
    if not m.get("files"):
        out.append(f"{launch['model']}: file list with sha256 is open ({m.get('files_why', 'launch.json models.files')})")
    else:
        out += [f"{launch['model']}: {f} has no sha256" for f, h in m["files"].items() if not HEX64.match(str(h))]
    if not launch.get("pipeline_class") or not launch.get("diffusers_version"):
        out.append(f"pipeline class and diffusers version are open ({launch.get('pipeline_why', 'launch.json')})")
    if not launch.get("image"):
        out.append(f"no pinned image ({launch.get('image_why', 'launch.json image')})")
    return out


def job_problems(job: dict, *, smoke: bool = False) -> list[str]:
    """The refusals of one picture job: kind, prompt, seed, size, written-out settings, and a sha256 for every reference picture."""
    sid, bad = job.get("id") or job.get("shot_id") or "?", []
    kind = job.get("kind", "sample")
    if kind not in KINDS:
        return [f"{sid}: kind {kind!r} is not one of {KINDS}"]
    if not str(job.get("prompt") or "").strip():
        bad.append(f"{sid}: no prompt (the plan thread writes every prompt)")
    if not isinstance(job.get("seed"), int):
        bad.append(f"{sid}: seed is not written out")
    if not (isinstance(job.get("width"), int) and isinstance(job.get("height"), int) and job["width"] > 0 and job["height"] > 0):
        bad.append(f"{sid}: width and height are not written out")
    if not isinstance(job.get("settings"), dict) or not job["settings"]:
        bad.append(f"{sid}: settings are not written out (the pipeline call takes them as written; no default is assumed)")
    refs = job.get("refs") or []
    for r in refs:
        if not (r.get("hf_path") and HEX64.match(str(r.get("sha256") or ""))):
            bad.append(f"{sid}: every reference picture needs hf_path and its sha256")
    if kind == "edit" and not refs:
        bad.append(f"{sid}: an edit needs its start picture as a reference (hf_path + sha256)")
    for forbidden in ("model", "repo", "checkpoint_path", "transformer_path", "lora", "loras"):
        if job.get(forbidden):
            bad.append(f"{sid}: the job names its own {forbidden}: the model comes only from the launch pin")
    return bad


def minutes(launch: dict, key: str, idx: int) -> float:
    return float(launch["minutes"][key][idx])


def estimate(launch: dict, n_pictures: int, price: float) -> dict:
    out = {}
    for name, idx in (("min", 0), ("expected", 1), ("max", 2)):
        mins = sum(minutes(launch, k, idx) for k in ("boot", "download", "load")) + \
               (n_pictures + 1) * minutes(launch, "seconds_per_picture", idx) / 60.0       # + the smoke picture
        out[name] = {"minutes": round(mins, 1), "usd": round(mins / 60.0 * price, 2)}
    return out


def batch_problems(launch: dict, batch: dict, *, price: float, cap_usd: float | None, caps: dict | None = None,
                   check_pins: bool = True) -> list[str]:
    """Local refusals before ``create`` (and again in the pod): open pins, no cap, a cap above the recorded one or the creator's
    ceilings, the job refusals, too many pictures, the EXPECTED estimate over the cap, not even one picture fitting."""
    caps = caps if caps is not None else spend_caps.runpod()
    bad = open_pins(launch) if check_pins else []
    rec_cap = launch.get("cap_usd")
    if not rec_cap:
        bad.append(f"runpod: no recorded cap ({launch.get('cap_why', 'launch.json cap_usd')})")
    if not cap_usd or cap_usd <= 0:
        bad.append("runpod: no cap for this batch")
    else:
        if rec_cap and cap_usd > float(rec_cap) + 1e-9:
            bad.append(f"runpod: cap {cap_usd} is above the recorded launch cap_usd {rec_cap}")
        if cap_usd > float(caps["per_pod_usd"]) + 1e-9:
            bad.append(f"runpod: cap {cap_usd} is above per_pod_usd {caps['per_pod_usd']}")
    jobs = batch.get("jobs") or []
    if not batch.get("smoke"):
        bad.append("the batch has no smoke job (L3): the plan thread writes it")
    else:
        bad += job_problems(batch["smoke"], smoke=True)
    if not jobs:
        bad.append("the batch has no pictures")
    ids = [j.get("id") for j in jobs]
    if len(set(ids)) != len(ids) or any(not i for i in ids):
        bad.append("every picture job needs its own id (it names the file and the record)")
    if len(jobs) > int(launch["max_pictures"]):
        bad.append(f"{len(jobs)} pictures are above max_pictures {launch['max_pictures']}")
    for j in jobs:
        bad += job_problems(j)
    if cap_usd and jobs:
        est = estimate(launch, len(jobs), price)
        if est["expected"]["usd"] > cap_usd + 1e-9:
            bad.append(f"runpod: the expected estimate ${est['expected']['usd']} is over the cap ${cap_usd} (max ${est['max']['usd']})")
        one = sum(minutes(launch, k, 2) for k in ("boot", "download", "load")) + 2 * minutes(launch, "seconds_per_picture", 2) / 60.0
        if one / 60.0 * price > cap_usd + 1e-9:
            bad.append(f"runpod: setup plus the smoke and one picture (max {round(one, 1)} min) is over the cap ${cap_usd}")
    return bad


def batch_review(launch: dict, batch: dict, *, price: float, cap_usd: float | None) -> list[str]:
    if not (cap_usd and batch.get("jobs")):
        return []
    mx = estimate(launch, len(batch["jobs"]), price)["max"]["usd"]
    return [f"REVIEW: the max estimate ${mx} is over the cap ${cap_usd}: the guard stops the pod at the cap"] if mx > cap_usd + 1e-9 else []


def script_problems(text: str | None = None) -> list[str]:
    text = LAUNCHER.read_text(encoding="utf-8") if text is None else text
    return ["klein_pod.sh: the code bundle sha256 or the diffusers version is not filled in (@@...@@): build the bundle and pin the version first"] \
        if "@@" in text else []


def picture_record(launch: dict, job: dict, png: Path, refs: dict) -> dict:
    """Every setting of the picture: prompt, reference sha256, seed, settings, model repo + revision + file shas, pipeline, diffusers."""
    m = model_of(launch)
    return {"id": job["id"], "kind": job.get("kind", "sample"), "variant": job.get("variant"), "prompt": job["prompt"], "seed": job["seed"],
            "size": [job["width"], job["height"]], "settings": dict(job["settings"]),
            "refs": [{"hf_path": r["hf_path"], "sha256": r["sha256"]} for r in job.get("refs") or []],
            "model": launch["model"], "repo": m["repo"], "revision": m["revision"], "files": dict(m["files"] or {}),
            "pipeline_class": launch["pipeline_class"], "diffusers_version": launch["diffusers_version"],
            "launch_sha": launch_sha(launch), "png_sha256": M._sha(png)}


_PIPE: dict = {}


def diffusers_generate(job: dict, launch: dict, refs: dict, png: Path) -> None:
    """The real picture: the pinned pipeline class from the model directory, ``job.settings`` as the call's keywords. Nothing is
    defaulted: the class and the version are launch pins (open until proven), the call's arguments are the plan thread's."""
    import diffusers
    import torch
    if "pipe" not in _PIPE:
        cls = getattr(diffusers, launch["pipeline_class"])
        _PIPE["pipe"] = cls.from_pretrained(str(weights_root(launch)), torch_dtype=torch.bfloat16).to("cuda")
    from PIL import Image
    kw = dict(job["settings"])
    if job.get("refs"):
        kw["image"] = [Image.open(refs[r["hf_path"]]).convert("RGB") for r in job["refs"]]
    kw.update(prompt=job["prompt"], width=job["width"], height=job["height"],
              generator=torch.Generator("cuda").manual_seed(job["seed"]))
    _PIPE["pipe"](**kw).images[0].save(png)


def run(batch: dict, out, *, api=None, download=None, generate=None, fetch=None, clock=time.time, vol_root=None, created=None,
        upload_op=None, launch: dict | None = None, tmp="/workspace/tmp/in") -> dict:
    """The pod side. Returns the end word with the records (also written under ``out``): DONE, L2_FAILED, L3_FAILED, CAPPED,
    UPLOAD_FAILED, PICTURE_FAILED, REFUSED. ``generate(job, launch, refs, png)`` and ``fetch(spec, dest)`` are injectable."""
    launch, out = launch or LAUNCH, Path(out)
    out.mkdir(parents=True, exist_ok=True)
    price, cap, prefix = float(batch["price"]), float(batch["cap_usd"]), batch["prefix"]
    vol = vol_root or launch["weights_dir"]
    os.environ["EE_KLEIN_VOL_ROOT"] = str(vol)
    t0 = float(created if created is not None else (os.environ.get("EE_CREATED") or clock()))   # the pod's birth: boot and installs count
    rec = {"card": batch.get("card"), "model": launch.get("model"), "price_usd_per_h": price, "cap_usd": cap,
           "launch_sha": launch_sha(launch), "steps": {}}
    spent = lambda: (clock() - t0) / 3600.0 * price      # noqa: E731 - measured pod seconds times the card price

    def end(word: str, **kw) -> dict:
        rec.update(end=word, spent_usd=round(spent(), 3), seconds=round(clock() - t0, 1), **kw)
        RL.write(out, "run_record.json", rec)
        RL.progress(out, f"{word} ${spent():.2f}")
        return rec

    why = batch_problems(launch, batch, price=price, cap_usd=cap, check_pins=False)
    why += [p for p in open_pins(launch) if "no pinned image" not in p]       # the image was checked by `create`
    for name, val in (("EE_MAX_USD", os.environ.get("EE_MAX_USD")),):
        if val not in (None, "") and (not launch.get("cap_usd") or float(val) > float(launch["cap_usd"]) + 1e-9):
            why.append(f"{name} {val} is above the recorded cap_usd {launch.get('cap_usd')}: create --max-usd must be the creator's number")
    if why:
        return end("REFUSED", problems=why)
    jobs = batch["jobs"]
    # L2: first, before any load; the model files of the active model, size and sha256, any fail ends the pod
    RL.progress(out, "L2 weights")
    m = model_of(launch)
    root = weights_root(launch, vol)
    missing = [f for f in m["files"] if not (root / f).is_file()]
    if missing:
        (download or _hf_download)(m["repo"], m["revision"], missing, root)
    bad = []
    for f, want in m["files"].items():
        p = root / f
        if not p.is_file() or p.stat().st_size == 0:
            bad.append(f"missing {f}")
        elif M._sha(p) != want:
            bad.append(f"sha256 mismatch {f}")
    rec["steps"]["L2"] = {"ok": not bad, "files": sorted(m["files"]), "problems": bad}
    if bad:
        return end("L2_FAILED", problems=bad)
    gen, fetcher = generate or diffusers_generate, fetch or (lambda spec, dest: M.stage_input(spec, dest))
    refs: dict = {}

    def stage_refs(job):
        for r in job.get("refs") or []:
            if r["hf_path"] not in refs:
                refs[r["hf_path"]] = fetcher(r, Path(tmp) / Path(r["hf_path"]).name)

    def make(job) -> dict:
        stage_refs(job)
        png = out / f"{job['id']}.png"
        t = clock()
        try:
            gen(job, launch, refs, png)
            ok = png.is_file() and png.stat().st_size > 0
        except Exception as exc:                                    # noqa: BLE001 - recorded, the pod ends
            return {"state": "FAILED", "why": f"{type(exc).__name__}: {str(exc)[:200]}"}
        if not ok:
            return {"state": "FAILED", "why": "no picture written"}
        record = RL.write(out, f"{job['id']}.record.json", picture_record(launch, job, png, refs))
        return {"state": "DONE", "png": png, "record": record, "gen_s": round(clock() - t, 1), "sha256": M._sha(png)}

    # L3: one smoke picture on this card
    RL.progress(out, "L3 smoke")
    sm = make(dict(batch["smoke"], id=batch["smoke"].get("id") or "L3_smoke"))
    rec["steps"]["L3"] = {"ok": sm["state"] == "DONE", "card": batch.get("card"), "gen_s": sm.get("gen_s"), "state": sm["state"],
                          "why": sm.get("why")}
    if api is not None and sm["state"] == "DONE":
        M.upload_round(api, out, prefix, {}, final=True, op=upload_op)
    if sm["state"] != "DONE":
        return end("L3_FAILED", problems=[f"smoke picture {sm['state']}: {sm.get('why')}"])
    # L4: the pictures; at 80 % of the cap no new picture starts; each is verified on HF before the next
    pictures = []
    worst = minutes(launch, "seconds_per_picture", 2) / 3600.0 * price
    for job in jobs:
        if spent() >= float(launch["problem_at"]) * cap or spent() + worst > cap:
            return end("CAPPED", pictures=pictures, problems=[f"PROBLEM: ${spent():.2f} of the cap ${cap}: no new picture ({job['id']} not started)"])
        RL.progress(out, f"L4 {job['id']}")
        res = make(job)
        if res["state"] != "DONE":
            pictures.append({"id": job["id"], "state": "FAILED"})
            return end("PICTURE_FAILED", pictures=pictures, problems=[f"{job['id']}: {res.get('why')}"])
        if api is not None:
            bad = RL.verify_clip(api, out, prefix, res["png"], res["record"], op=upload_op)
            if bad:
                pictures.append({"id": job["id"], "state": "NOT_VERIFIED"})
                return end("UPLOAD_FAILED", pictures=pictures, problems=bad)
        pictures.append({"id": job["id"], "state": "DONE", "sha256": res["sha256"], "verified": api is not None})
    return end("DONE", pictures=pictures)


def _hf_download(repo, revision, files, root):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), local_dir=str(root), token=M._tok())


def plan(batch_path: str, *, card: int = 0, launch=None) -> dict:
    """What ``create`` may be asked for: the refusals, the estimate, the file list. Reads files only: no pod, no money."""
    launch = launch or LAUNCH
    batch = json.loads(Path(batch_path).read_text(encoding="utf-8"))
    c = launch["cards"][card]
    cap = batch.get("cap_usd") if batch.get("cap_usd") is not None else launch.get("cap_usd")
    why = batch_problems(launch, batch, price=float(c["usd_per_h"]), cap_usd=cap) + script_problems()
    n = len(batch.get("jobs") or [])
    return {"ok": not why, "problems": why, "review": batch_review(launch, batch, price=float(c["usd_per_h"]), cap_usd=cap),
            "card": c["gpu"], "cloud": c["cloud"], "price_usd_per_h": c["usd_per_h"], "cap_usd": cap, "model": launch["model"],
            "estimate": estimate(launch, n, float(c["usd_per_h"])) if n else None,
            "l2_files": sorted(model_of(launch).get("files") or [])}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else ""
    if cmd == "plan" and argv:
        res = plan(argv[0])
        print(json.dumps(res, indent=2))
        raise SystemExit(0 if res["ok"] else 2)
    if cmd == "run" and argv:
        batch = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        from huggingface_hub import HfApi
        res = run(batch, os.environ.get("EE_OUT", "/workspace/out"), api=HfApi(token=M._tok()))
        raise SystemExit(EXIT[res["end"]])
    raise SystemExit("usage: klein_jobs plan batch.json | run batch.json")


if __name__ == "__main__":
    main()
