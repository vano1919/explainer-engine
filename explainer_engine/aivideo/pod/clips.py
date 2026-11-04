# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/aivideo/pod/clips.py`
# Target Module : explainer_engine/aivideo/pod/clips.py
# Target Classes/Symbols : class BF16Report (methods: dtype), def sd(), def expert(), def fit()
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
Clips for the night test video: Wan 2.2 I2V A14B (bf16 from ai-toolkit/Wan2.2-I2V-A14B-Diffusers-bf16, text encoder and
VAE from Wan-AI/Wan2.2-I2V-A14B-Diffusers) with first AND last frame (diffusers last_image), the lightx2v 4-step distill
LoRAs and, when it exists, our wldnk style LoRA (high + low noise files from ai-toolkit). LoRAs are fused into each expert
on the GPU, then the expert is stored in fp8 (layerwise casting), so both experts fit a 48 GB card without a big CPU RAM.
Usage: python clips.py SHOTS.json KFDIR OUTDIR --res 480|720 [--style HIGH LOW] [--style-strength 1.0] [--smoke]
[--deadline EPOCH]"""
import gc, json, os, sys, time
import numpy as np
import torch
from PIL import Image

a = sys.argv
shots_path, kfdir, out = a[1], a[2], a[3]
res = int(a[a.index("--res") + 1]) if "--res" in a else 480
smoke = "--smoke" in a
deadline = float(a[a.index("--deadline") + 1]) if "--deadline" in a else 1e18
if os.path.exists("/workspace/T0"):  # the money ceiling ends the pod ~182 min after its start (watchdog.py)
    deadline = min(deadline, int(open("/workspace/T0").read()) + 150 * 60)
style = a[a.index("--style") + 1: a.index("--style") + 3] if "--style" in a else None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fixhub, glob
fixhub.ensure()
if not style and not smoke:  # the stage looked before the hot-fixed training finished: take the newest pair now
    hi = sorted(glob.glob("/workspace/out/train/wldnk_wan22_v1/*_high_noise.safetensors"), key=os.path.getmtime)
    lo = sorted(glob.glob("/workspace/out/train/wldnk_wan22_v1/*_low_noise.safetensors"), key=os.path.getmtime)
    if hi and lo:
        style = [hi[-1], lo[-1]]
        print("style LoRA found late", style, flush=True)
sstr = float(a[a.index("--style-strength") + 1]) if "--style-strength" in a else 0.8
os.makedirs(out, exist_ok=True)
data = json.load(open(shots_path))
W, H = (832, 480) if res == 480 else (1280, 720)
FRAMES = 17 if smoke else 81
STEPS = 4

from diffusers import WanImageToVideoPipeline, AutoencoderKLWan, FlowMatchEulerDiscreteScheduler
from diffusers.models import WanTransformer3DModel
from diffusers.utils import export_to_video
from diffusers.loaders.lora_conversion_utils import _convert_non_diffusers_wan_lora_to_diffusers
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
from transformers import UMT5EncoderModel, AutoTokenizer

# TODO [CLAUDE-CLASS-SYNC: BF16Report] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `BF16Report` (methods: dtype) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class BF16Report(WanTransformer3DModel):
    @property
    def dtype(self):
        return torch.bfloat16


BASE = "Wan-AI/Wan2.2-I2V-A14B-Diffusers"
BF16 = "ai-toolkit/Wan2.2-I2V-A14B-Diffusers-bf16"
log = {"res": res, "style": style, "style_strength": sstr, "clips": {}}


def sd(path):
    s = load_file(path)
    if any(k.startswith("diffusion_model.") for k in s):
        s = _convert_non_diffusers_wan_lora_to_diffusers(s)
    return s


light = {k: hf_hub_download("lightx2v/Wan2.2-Distill-Loras", f"wan2.2_i2v_A14b_{k}_noise_lora_rank64_lightx2v_4step_1022.safetensors")
         for k in ("high", "low")}


def expert(sub, loras):
    t = WanTransformer3DModel.from_pretrained(BF16, subfolder=sub, torch_dtype=torch.bfloat16)  # CPU: fuse there, 28.6 GB RAM
    names, weights = [], []
    for name, path, w in loras:
        if path and os.path.exists(path):
            try:
                t.load_lora_adapter(sd(path), adapter_name=name, prefix="transformer")
                names.append(name); weights.append(w)
            except Exception as e:
                log.setdefault("lora_errors", []).append(f"{sub} {name}: {e!r}"[:300])
    if names:
        t.set_adapters(names, weights=weights)
        t.fuse_lora(lora_scale=1.0, adapter_names=names)
        t.unload_lora()
    t.enable_layerwise_casting(storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.bfloat16)
    t.__class__ = BF16Report  # the pipeline casts its inputs to transformer.dtype: keep that bf16, not the fp8 storage
    t.to("cuda")
    gc.collect(); torch.cuda.empty_cache()
    log.setdefault("loras", {})[sub] = names
    return t


# 1) prompts -> embeddings, then free the text encoder
tok = AutoTokenizer.from_pretrained(BASE, subfolder="tokenizer")
te = UMT5EncoderModel.from_pretrained(BASE, subfolder="text_encoder", torch_dtype=torch.bfloat16).to("cuda")
NEG = "blurry, distorted face, extra fingers, extra limbs, deformed hands, text, watermark, photorealistic, 3d render"
pipe0 = WanImageToVideoPipeline(tokenizer=tok, text_encoder=te, vae=None, scheduler=None, transformer=None,
                                transformer_2=None, boundary_ratio=0.9)
emb = {}
shots = data["shots"][: (1 if smoke else None)]
with torch.no_grad():
    for s in shots:
        p = f"{data['trigger']}, {s['motion']}, 2D hand-drawn cartoon animation, bold ink outlines, smooth natural motion"
        pe, ne = pipe0.encode_prompt(prompt=p, negative_prompt=NEG, do_classifier_free_guidance=False, device="cuda")
        emb[s["id"]] = (pe.cpu(), p)
del te, pipe0; gc.collect(); torch.cuda.empty_cache()

# 2) experts with fused LoRAs, fp8 storage
hi = expert("transformer", [("light", light["high"], 1.0)] + ([("style", style[0], sstr)] if style else []))
lo = expert("transformer_2", [("light", light["low"], 1.0)] + ([("style", style[1], sstr)] if style else []))
vae = AutoencoderKLWan.from_pretrained(BASE, subfolder="vae", torch_dtype=torch.float32).to("cuda")
sched = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=5.0)
pipe = WanImageToVideoPipeline(tokenizer=tok, text_encoder=None, vae=vae, scheduler=sched, transformer=hi,
                               transformer_2=lo, boundary_ratio=0.9)
try:
    pipe.vae.enable_tiling()
except Exception:
    pass


def fit(img):
    img = img.convert("RGB")
    r = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


done_secs = []
for i, s in enumerate(shots):
    if done_secs and W == 1280:  # 720p only while the rest still fits before the deadline; else drop to 480p
        need = (sum(done_secs) / len(done_secs)) * (len(shots) - i)
        if time.time() + need > deadline:
            W, H = 832, 480
            log["switched_to_480_at"] = s["id"]
    dst = os.path.join(out, f"{s['id']}.mp4")
    if os.path.exists(dst) or os.path.isdir(os.path.join(out, f"{s['id']}_frames")):
        continue
    if time.time() > deadline:
        log["stopped_at_deadline"] = s["id"]; break
    f0, f1 = os.path.join(kfdir, f"{s['id']}_first.png"), os.path.join(kfdir, f"{s['id']}_last.png")
    if not os.path.exists(f0):
        log["clips"][s["id"]] = {"error": "no first keyframe"}; continue
    t = time.time()
    kw = dict(image=fit(Image.open(f0)), prompt_embeds=emb[s["id"]][0].to("cuda", torch.bfloat16), height=H, width=W,
              num_frames=FRAMES, num_inference_steps=STEPS, guidance_scale=1.0, guidance_scale_2=1.0,
              generator=torch.Generator("cuda").manual_seed(5))
    if os.path.exists(f1):
        kw["last_image"] = fit(Image.open(f1))
    try:
        frames = pipe(**kw).frames[0]
        fd = os.path.join(out, f"{s['id']}_frames")  # frames first: an mp4 writer failure must never lose a clip
        os.makedirs(fd, exist_ok=True)
        for k, fr in enumerate(frames):
            im = fr if isinstance(fr, Image.Image) else Image.fromarray((np.clip(fr, 0, 1) * 255).astype("uint8"))
            im.save(os.path.join(fd, f"{k:03d}.jpg"), quality=95)
        try:
            export_to_video(frames, dst, fps=16)
        except Exception as e:
            log.setdefault("mp4_errors", {})[s["id"]] = repr(e)[:200]
        log["clips"][s["id"]] = {"seconds": round(time.time() - t, 1), "flf": "last_image" in kw, "res": f"{W}x{H}",
                                 "prompt": emb[s["id"]][1]}
        done_secs.append(time.time() - t)
    except Exception as e:
        log["clips"][s["id"]] = {"error": repr(e)[:400]}
        torch.cuda.empty_cache()
    json.dump(log, open(os.path.join(out, "clips_report.json"), "w"), indent=1)
json.dump(log, open(os.path.join(out, "clips_report.json"), "w"), indent=1)
n = len([f for f in os.listdir(out) if f.endswith("_frames")])
print("CLIPS DONE", n)
sys.exit(0 if n else 1)  # no clip at all is a failure, also in the smoke test
