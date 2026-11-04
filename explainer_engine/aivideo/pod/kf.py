# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/aivideo/pod/kf.py`
# Target Module : explainer_engine/aivideo/pod/kf.py
# Target Classes/Symbols : def gen()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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
