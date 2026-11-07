"""6 test photos (blockout vs CC0 Blender stills, 3 scenes): the p15 Qwen edit, Image 1 = the still, no hero refs.
Runs inside the pinned bundle (/workspace/ee). Each picture is saved as it is drawn (OR-33). Args: --out DIR --inputs DIR."""
import argparse, json, sys, time, traceback
from pathlib import Path
sys.path.insert(0, "/workspace/ee")
from explainer_engine.training.pods.p14 import p14_qwen as Q
from explainer_engine.training.pods.p15 import p15_qwen as P

ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path); ap.add_argument("--inputs", type=Path); ap.add_argument("--smoke", action="store_true"); ap.add_argument("--seeds", default=""); ap.add_argument("--lora-weight", type=float, default=None)
a = ap.parse_args()
cfg = P.load_cfg()
if a.lora_weight is not None:   # creator 2026-11-07 14:42 UTC: every frame once also at style strength 1; the merge is in place, so one weight per process
    cfg["qwen"]["style_lora"] = dict(cfg["qwen"]["style_lora"], weight=a.lora_weight)
q = cfg["qwen"]
wtag = "" if a.lora_weight is None else f"_w{int(round(a.lora_weight * 10)):02d}"
raw = json.loads((a.inputs / "sa_prompts.json").read_text())
prompts = {k: (v["qwen"] if isinstance(v, dict) else v) for k, v in raw.items()}   # the file holds {qwen, words, ltx} per name
assert all(isinstance(v, str) and v for v in prompts.values()), "every prompt must be a non-empty str (a dict made the pipeline read 3 prompts)"
sys.path.insert(0, str(P.HERE.parent))
import xworld_v1_test as t
from PIL import Image
import os
os.environ.setdefault("XW_GPU_MODE", q["gpu_mode"])
qd = a.out / "qwen"; qd.mkdir(parents=True, exist_ok=True)
log = open(qd / "qwen.log", "a")
def say(*x):
    l = time.strftime("%H:%M:%S ") + " ".join(map(str, x)); print(l, flush=True); log.write(l + "\n"); log.flush()
t0 = time.time(); pipe, tr = t.load_pipeline(); pipe = Q.style_lora(t, pipe, tr, cfg, say); say("loaded", round(time.time() - t0), "s")

if a.smoke:   # OR-37 smoke: 1 step, tiny size, [still] then [still, still]: shows whether the single-image edit path itself works
    still = Image.open(a.inputs / "sa_cave_block.png").convert("RGB").resize((768, 432))
    base = dict(cfg, qwen=dict(q, steps=1))
    res = {}
    for label, refs in (("one_ref", [still]), ("two_refs", [still, still])):
        try:
            j = {"name": label, "prompt": prompts["cave_block"], "seed": q["seed"], "cfg": q["cfg_edit"], "size": [768, 432], "kind": "edit"}
            im = Q.draw(pipe, base, j, refs); res[label] = f"ok {im.size}"
        except Exception as e:
            res[label] = "FAIL " + repr(e)[:200]; say(traceback.format_exc()[-1800:])
        say("smoke", label, res[label])
    (qd / "smoke.json").write_text(json.dumps(res, indent=1))
    sys.exit(0 if all(v.startswith("ok") for v in res.values()) else 1)
status = {}
fail = 0
seeds = [int(x) for x in a.seeds.split(",") if x] or [q["seed"]]
jobs = [(name, s) for s in seeds for name in sorted(prompts)]
for name, seed in jobs:
    tag = (name if not a.seeds else f"{name}_s{seed}") + wtag
    p = qd / f"{tag}.png"
    if p.exists(): continue
    t1 = time.time()
    try:
        still = Image.open(a.inputs / f"sa_{name}.png").convert("RGB")
        j = {"name": tag, "prompt": prompts[name], "seed": seed, "cfg": q["cfg_edit"], "size": q["size"], "kind": "edit", "lora_weight": q["style_lora"]["weight"]}
        im = Q.draw(pipe, cfg, j, [still]).convert("RGB"); im.save(p)
        (qd / f"{tag}.json").write_text(json.dumps({**j, "seconds": round(time.time() - t1, 1), "sha256": Q.sha256_file(p)}, indent=1))
        say("made", tag, round(time.time() - t1), "s"); status[tag] = {"status": "ok"}; (qd / "status.json").write_text(json.dumps(status, indent=1))
    except Exception as e:
        fail += 1; say("FAIL", tag, repr(e)[:300]); say(traceback.format_exc()[-1800:]); status[tag] = {"status": "error", "traceback": traceback.format_exc()[-1800:]}; (qd / "status.json").write_text(json.dumps(status, indent=1))
        if fail >= 1: say("STOP: first failure"); break
say("done", fail, "failed")
sys.exit(1 if fail else 0)
