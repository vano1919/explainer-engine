"""RETIRED by D-80 (2026-10-26): it loads a banned wldnk LoRA; kept as history, never run.
Keyframes for the night test video: FLUX.2 klein base 4B + the wldnk photo LoRA (diffusers Flux2KleinPipeline).
Character sheets and plates first (text to image), then each shot's FIRST frame (references: the sheets of the
characters in the shot + its plate) and LAST frame (an edit of the first frame). Writes /workspace/out/kf/*.png and
kf/report.json. Usage: python kf.py SHOTS.json LORA.safetensors OUTDIR [--smoke] [--strength 1.0]"""
import json, os, sys, time, traceback
import torch
from PIL import Image

shots_path, lora, out = sys.argv[1], sys.argv[2], sys.argv[3]
smoke = "--smoke" in sys.argv
if smoke and not os.path.exists("/workspace/watchdog.started"):  # one detached watchdog for the whole night (watchdog.py)
    import subprocess
    open("/workspace/watchdog.started", "w").write(str(time.time()))
    subprocess.Popen(["nohup", "python", os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchdog.py")],
                     stdout=open("/workspace/out/watchdog.log", "a"), stderr=subprocess.STDOUT, start_new_session=True)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixhub
fixhub.ensure()
import glob, subprocess
TRAIN_DIR = "/workspace/out/train/wldnk_wan22_v1"
if not smoke and not glob.glob(TRAIN_DIR + "/*_low_noise.safetensors"):
    # night hot fix: the train stage died on the hub version; train here first (watchdog.py stops it at T0+95 min)
    print("training the Wan style LoRA before the keyframes", flush=True)
    import threading

    def _logs():  # the stage's own upload loop is gone: send the training log every 10 minutes
        from huggingface_hub import HfApi
        while True:
            time.sleep(600)
            try:
                HfApi().upload_folder(folder_path="/workspace/out", path_in_repo="night_run_2026-10-22",
                                      repo_id="vano1919/tmr-artifacts", repo_type="dataset",
                                      allow_patterns=["*.log", "*.txt", "train/**/*.safetensors"])
            except Exception as e:
                print("log upload failed", e, flush=True)
    threading.Thread(target=_logs, daemon=True).start()
    with open("/workspace/out/train2.log", "a") as lg:
        subprocess.run(["python", "run.py", "/workspace/code/wan_lora.yaml"], cwd="/app/ai-toolkit", stdout=lg,
                       stderr=subprocess.STDOUT)
    subprocess.run(["python", "-c", "import torch;torch.cuda.empty_cache()"])
    print("training ended", glob.glob(TRAIN_DIR + "/*.safetensors"), flush=True)
strength = float(sys.argv[sys.argv.index("--strength") + 1]) if "--strength" in sys.argv else 1.0
os.makedirs(out, exist_ok=True)
data = json.load(open(shots_path))
TRIG, SUF = data["trigger"], data["style_suffix"]
W, H = (512, 288) if smoke else (1280, 720)
STEPS = 4 if smoke else 28
report = {"started": time.time(), "items": {}}

from diffusers import Flux2KleinPipeline
pipe = Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-base-4B", torch_dtype=torch.bfloat16).to("cuda")
if lora and os.path.exists(lora):
    pipe.load_lora_weights(lora, adapter_name="wldnk")
    pipe.set_adapters(["wldnk"], adapter_weights=[strength])
    report["lora"] = lora
else:
    report["lora"] = None


def gen(name, prompt, refs=None, w=W, h=H, seed=7):
    path = os.path.join(out, name + ".png")
    if os.path.exists(path):
        return Image.open(path).convert("RGB")
    t = time.time()
    kw = dict(prompt=f"{TRIG}, {prompt}, {SUF}", width=w, height=h, num_inference_steps=STEPS, guidance_scale=4.0,
              generator=torch.Generator("cuda").manual_seed(seed))
    if refs:
        kw["image"] = refs
    try:
        img = pipe(**kw).images[0]
    except Exception as e:  # a reference set the model refuses: fall back to text only, say so
        report["items"][name] = {"error": repr(e)[:300]}
        kw.pop("image", None)
        img = pipe(**kw).images[0]
    img.save(path)
    report["items"].setdefault(name, {}).update(prompt=kw["prompt"], refs=len(refs or []), seconds=round(time.time() - t, 1))
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1)
    return img


sheets = {}
for cid, desc in data["characters"].items():
    sheets[cid] = gen(f"sheet_{cid}", f"character design sheet of {desc}, full body front view and three-quarter view "
                      "side by side, plain white background", w=W, h=H, seed=11)
    if smoke:
        break
plates = {}
for pid, desc in data["plates"].items():
    plates[pid] = gen(f"plate_{pid}", desc, seed=13)
    if smoke:
        break
for s in data["shots"][: (1 if smoke else None)]:
    refs = [sheets[c] for c in s["chars"] if c in sheets][:3]
    if s.get("plate") and s["plate"] in plates:
        refs.append(plates[s["plate"]])
    names = ", ".join(data["characters"][c].split(",")[0] for c in s["chars"])
    cast = f" ({names} exactly as in the reference sheets)" if names else ""
    first = gen(f"{s['id']}_first", s["first"] + cast, refs=refs or None, seed=21)
    gen(f"{s['id']}_last", f"the same scene, same characters, same place, same camera framing: {s['last']}",
        refs=[first] + refs[:2], seed=22)
report["finished"] = time.time()
json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1)
print("KF DONE", len(os.listdir(out)))
