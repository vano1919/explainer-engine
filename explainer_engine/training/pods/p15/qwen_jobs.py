"""A list of Qwen jobs in one process (the creator 2026-11-07 15:04 UTC: test A new angles with the painted master, test B Qwen-first
assets): text-to-image (no refs) or edit (refs = input files or pictures made earlier in this run). Runs inside the pinned bundle
(/workspace/ee). One style-LoRA weight per process (the merge is in place). Each picture is saved as it is drawn (OR-33).

    python3 qwen_jobs.py --jobs JOBS.json --group N --inputs DIR --out DIR [--smoke]

A ref ``in:<file>`` is read from --inputs, ``out:<name>`` from <out>/qwen/<name>.png (made earlier in this run, or listed in the jobs file's
``inputs`` when a previous run made it). The first failure stops the group; status.json carries each job's traceback."""
import argparse, json, sys, time, traceback
from pathlib import Path


def resolve(ref: str, inputs: Path, qd: Path) -> Path:
    kind, _, name = ref.partition(":")
    if kind == "in":
        return inputs / name
    if kind == "out":
        return qd / f"{name}.png"
    raise ValueError(f"ref {ref!r}: must start with in: or out:")


def check_jobs(doc: dict) -> list[str]:
    """Free: every job has a non-empty str prompt, a size divisible by 16, refs that resolve to an input or an EARLIER job."""
    bad, made = [], set()
    for gi, g in enumerate(doc["groups"]):
        for j in g["jobs"]:
            if not (isinstance(j.get("prompt"), str) and j["prompt"]):
                bad.append(f"{j.get('name')}: prompt must be a non-empty str")
            if any(v % 16 for v in j.get("size", [16, 16])):
                bad.append(f"{j['name']}: size {j['size']} not divisible by 16")
            for r in j.get("refs", []):
                kind, _, name = r.partition(":")
                if kind == "in" and name not in doc.get("inputs", {}):
                    bad.append(f"{j['name']}: input {name} is not pinned in inputs")
                if kind == "out" and name not in made and name not in doc.get("inputs", {}):
                    bad.append(f"{j['name']}: out:{name} is not made before it")
                if kind not in ("in", "out"):
                    bad.append(f"{j['name']}: ref type {kind!r} is unknown (use in: or out:)")
            made.add(j["name"])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=Path); ap.add_argument("--group", type=int, default=0)
    ap.add_argument("--inputs", type=Path); ap.add_argument("--out", type=Path); ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    doc = json.loads(a.jobs.read_text())
    bad = check_jobs(doc)
    if bad:
        raise SystemExit("jobs file refused: " + "; ".join(bad))
    sys.path.insert(0, "/workspace/ee")
    from explainer_engine.training.pods.p14 import p14_qwen as Q
    from explainer_engine.training.pods.p15 import p15_qwen as P
    import os
    from PIL import Image
    cfg = P.load_cfg()
    g = doc["groups"][a.group]
    cfg["qwen"]["style_lora"] = dict(cfg["qwen"]["style_lora"], weight=g["lora_weight"])
    q = cfg["qwen"]
    sys.path.insert(0, str(P.HERE.parent))
    import xworld_v1_test as t
    os.environ.setdefault("XW_GPU_MODE", q["gpu_mode"])
    qd = a.out / "qwen"; qd.mkdir(parents=True, exist_ok=True)
    log = open(qd / "qwen.log", "a")

    def say(*x):
        line = time.strftime("%H:%M:%S ") + " ".join(map(str, x)); print(line, flush=True); log.write(line + "\n"); log.flush()
    t0 = time.time(); pipe, tr = t.load_pipeline(); pipe = Q.style_lora(t, pipe, tr, cfg, say); say("loaded", round(time.time() - t0), "s")
    if a.smoke:   # OR-37: 1 step, small: text-to-image, one, two and three refs (the paths the runs use)
        first = next((j for j in g["jobs"] if any(r.startswith("in:") for r in j.get("refs", []))), g["jobs"][0])
        ins = [r for r in first.get("refs", []) if r.startswith("in:")]
        ref = (Image.open(resolve(ins[0], a.inputs, qd)).convert("RGB").resize((768, 432)) if ins
               else Image.new("RGB", (768, 432), (128, 128, 128)))   # a run without input files (Qwen-first assets) smokes on grey
        base, res = dict(cfg, qwen=dict(q, steps=1)), {}
        for label, refs in (("t2i", []), ("one_ref", [ref]), ("two_refs", [ref, ref]), ("three_refs", [ref, ref, ref])):
            try:
                j = {"name": label, "prompt": first["prompt"], "seed": q["seed"], "cfg": q["cfg_edit"] if refs else q["cfg_text"], "size": [768, 432], "kind": "edit"}
                res[label] = f"ok {Q.draw(pipe, base, j, refs).size}"
            except Exception as e:  # noqa: BLE001
                res[label] = "FAIL " + repr(e)[:200]; say(traceback.format_exc()[-1800:])
            say("smoke", label, res[label])
        (qd / "smoke.json").write_text(json.dumps(res, indent=1))
        sys.exit(0 if all(v.startswith("ok") for v in res.values()) else 1)
    status_p = qd / "status.json"
    status = json.loads(status_p.read_text()) if status_p.exists() else {}
    for j in g["jobs"]:
        p = qd / f"{j['name']}.png"
        if p.exists():
            continue
        t1 = time.time()
        try:
            refs = [Image.open(resolve(r, a.inputs, qd)).convert("RGB") for r in j.get("refs", [])]
            jj = {"name": j["name"], "prompt": j["prompt"], "seed": j.get("seed", q["seed"]), "cfg": q["cfg_edit"] if refs else q["cfg_text"],
                  "size": j.get("size", q["size"]), "kind": "edit" if refs else "t2i"}
            jcfg = dict(cfg, qwen=dict(q, negative=j["negative"])) if j.get("negative") else cfg   # a job may carry its own negative
            im = Q.draw(pipe, jcfg, jj, refs).convert("RGB"); im.save(p)
            (qd / f"{j['name']}.json").write_text(json.dumps({**jj, "refs": j.get("refs", []), "lora_weight": g["lora_weight"], "negative": jcfg["qwen"]["negative"],
                                                              "seconds": round(time.time() - t1, 1), "sha256": Q.sha256_file(p)}, indent=1))
            say("made", j["name"], round(time.time() - t1), "s"); status[j["name"]] = {"status": "ok"}
        except Exception:  # noqa: BLE001
            say("FAIL", j["name"]); say(traceback.format_exc()[-1800:])
            status[j["name"]] = {"status": "error", "traceback": traceback.format_exc()[-1800:]}
            status_p.write_text(json.dumps(status, indent=1)); say("STOP: first failure"); sys.exit(1)
        status_p.write_text(json.dumps(status, indent=1))
    say("group done", a.group)


if __name__ == "__main__":
    main()
