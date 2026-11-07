"""6 test photos (blockout vs CC0 Blender stills, 3 scenes): the p15 Qwen edit, Image 1 = the still, no hero refs.
Runs inside the pinned bundle (/workspace/ee). Each picture is saved as it is drawn (OR-33). Args: --out DIR --inputs DIR."""
import argparse, json, sys, time
from pathlib import Path
sys.path.insert(0, "/workspace/ee")
from explainer_engine.training.pods.p14 import p14_qwen as Q
from explainer_engine.training.pods.p15 import p15_qwen as P

ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path); ap.add_argument("--inputs", type=Path)
a = ap.parse_args()
cfg = P.load_cfg(); q = cfg["qwen"]
prompts = json.loads((a.inputs / "sa_prompts.json").read_text())
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
fail = 0
for name in sorted(prompts):
    p = qd / f"{name}.png"
    if p.exists(): continue
    t1 = time.time()
    try:
        still = Image.open(a.inputs / f"sa_{name}.png").convert("RGB")
        j = {"name": name, "prompt": prompts[name], "seed": q["seed"], "cfg": q["cfg_edit"], "size": q["size"], "kind": "edit"}
        im = Q.draw(pipe, cfg, j, [still]).convert("RGB"); im.save(p)
        (qd / f"{name}.json").write_text(json.dumps({**j, "seconds": round(time.time() - t1, 1), "sha256": Q.sha256_file(p)}, indent=1))
        say("made", name, round(time.time() - t1), "s")
    except Exception as e:
        fail += 1; say("FAIL", name, repr(e)[:300])
        if fail >= 2: say("STOP: 2 failures"); break
say("done", fail, "failed")
sys.exit(1 if fail else 0)
