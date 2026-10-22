"""Clips for the night test video: Wan 2.2 I2V A14B (bf16 from ai-toolkit/Wan2.2-I2V-A14B-Diffusers-bf16, text encoder and
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
    if os.path.exists(dst):
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
        export_to_video(frames, dst, fps=16)
        log["clips"][s["id"]] = {"seconds": round(time.time() - t, 1), "flf": "last_image" in kw, "res": f"{W}x{H}",
                                 "prompt": emb[s["id"]][1]}
        done_secs.append(time.time() - t)
    except Exception as e:
        log["clips"][s["id"]] = {"error": repr(e)[:400]}
        torch.cuda.empty_cache()
    json.dump(log, open(os.path.join(out, "clips_report.json"), "w"), indent=1)
json.dump(log, open(os.path.join(out, "clips_report.json"), "w"), indent=1)
print("CLIPS DONE", len([f for f in os.listdir(out) if f.endswith(".mp4")]))
