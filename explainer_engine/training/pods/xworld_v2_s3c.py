"""The xworld_v2 depth-ControlNet test S3c (D-75; the Opus thread's plan /mnt/project-files/xworld_v2/S3C_CONTROLNET_PLAN_2026-10-26.md).

Qwen-Image-2.1-Fun-Controlnet-Union (alibaba-pai; the control branch only, `control_img_in` + 16 `control_blocks`, loaded with
strict=False on the base transformer) is a real depth ControlNet for our base model. Its pipeline takes no reference images, so:
  step 0  does the xworld LoRA load on the control transformer? (key match must be 100 %, then a with/without-LoRA sample)
  pass A  layout: the control pipeline + the LoRA + the S3 depth render of the shot + the full text prompt
  pass B  identity: the ordinary edit pipeline: Image 1 = pass A, Image 2 = the master, Image 3 = the subject's sheet
Pictures per scene (tent, rome): control_context_scale 1.0 on s1..s4, a 0.6 / 0.8 sweep on one shot (s1 tent, s2 rome), pass B on
the 1.0 results. The scale cannot be judged on an unattended pod, so the sweep is only drawn; ვანო's eye and the Spearman pick.

    python xworld_v2_s3c.py <scene dir> <p2s out dir> <s3 out dir> <out dir> <lora .safetensors> [scenes] [cfg]    (on the pod)
Reads the master and sheets from the P2S run and the depth renders (<scene>_<shot>_depth.png) from the S3 run.
"""
from __future__ import annotations

import gc
import re
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from .xworld_v1_test import TRIGGER
else:
    from xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from xworld_v1_test import TRIGGER

SCENES = ("tent", "rome")
SEED = SEEDS[0]
SCALES = (1.0, 0.6, 0.8)  # the first is the one every shot is drawn at; the others only on SWEEP_SHOT
SWEEP_SHOT = {"tent": "s1", "rome": "s2"}
CFG_PAIR = ("tent", "s1", 0.8, 1.0)  # (scene, shot, scale, cfg): the card's example runs at cfg 1.0, our LoRA at 2.5; one extra picture
CONTROL_REPO, CONTROL_FILE = "alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union", "Qwen-Image-2.1-Fun-Controlnet-Union.safetensors"
CONTROL_CONFIG = "/workspace/VideoX-Fun/config/qwenimage21/qwenimage21_control.yaml"
SAMPLE_PROMPT = f"{TRIGGER}, a small stone house on a green hill under a blue sky, bold black ink outlines."


def norm(name):
    """One form for a LoRA key or a module name: no prefix, no lora suffix, dots and underscores alike."""
    n = re.sub(r"\.(lora_A|lora_B|lora_down|lora_up)\.weight$|\.alpha$|\.weight$", "", name)
    n = re.sub(r"^(lora_unet_|transformer\.|diffusion_model\.|base_model\.model\.transformer\.)", "", n)
    return n.replace(".", "_")


def match_report(lora_keys, module_names):
    """(matched, total, unmatched) of the LoRA's layers against a transformer's module names. Pass only at 100 %."""
    mods = {norm(m) for m in module_names}
    layers = sorted({norm(k) for k in lora_keys if re.search(r"lora_(A|B|down|up)\.weight$", k)})
    miss = [x for x in layers if x not in mods]
    return len(layers) - len(miss), len(layers), miss


def pass_a_prompt(sc, shot):
    """The whole target image in words: the place, the shot with the cast text, the out-of-frame rule, the background, who is in it."""
    return f"{TRIGGER}, {sc['place']} {frame_desc(shot)} {frame_extras(sc, shot)}".strip()


def pass_b_prompt(sc, shot):
    """Image 1 = pass A, Image 2 = the master, Image 3 = the sheet of the subject (when the shot has one)."""
    role = next((r for r in shot.get("faces", []) if r in sc["cast"]), None)
    first = frame_desc(shot).split(". ")[0].rstrip(".") + "."
    p = (f"{TRIGGER}, Keep the composition, camera and poses of Image 1 exactly. Repaint the place to match Image 2: its landmarks, "
         "light and colours.")
    if role:
        p += f" Repaint {role}'s face and clothes to match Image 3."
    return f"{p} {first}", role


def jobs(scenes):
    """[{name, scene, shot, scale, passB}]: pass A at every scale asked for, then B for the full-strength ones."""
    out = []
    for sc in scenes:
        for shot in sc["shots"][1:]:
            for k, scale in enumerate(SCALES):
                if k and shot["id"] != SWEEP_SHOT[sc["name"]]:
                    continue
                out.append({"name": f"{sc['name']}_{shot['id']}_A{scale}", "scene": sc["name"], "shot": shot["id"], "scale": scale,
                            "pass": "A"})
    scene, shot, scale, cfg = CFG_PAIR
    if any(sc["name"] == scene for sc in scenes):
        out.append({"name": f"{scene}_{shot}_A{scale}_cfg{cfg}", "scene": scene, "shot": shot, "scale": scale, "cfg": cfg, "pass": "A"})
    return out + [dict(j, name=j["name"].replace("_A", "_B"), **{"pass": "B"}) for j in out if j["scale"] == SCALES[0]]


def control_load_ok(missing, unexpected):
    """The control branch loaded when no control key is missing in the model and none of the file's control keys is unexpected
    (strict=False hides both; missing base keys are expected because the file holds only the control branch)."""
    own = ("control_img_in", "control_blocks")
    bad = [k for k in list(missing) + list(unexpected) if k.startswith(own)]
    return not bad, bad


def load_control_pipeline():
    """The control pipeline of VideoX-Fun with the control branch on the base transformer; returns (pipe, transformer)."""
    import torch
    sys.path.insert(0, "/workspace/VideoX-Fun")
    from diffusers import FlowMatchEulerDiscreteScheduler
    from huggingface_hub import hf_hub_download, snapshot_download
    from omegaconf import OmegaConf
    from safetensors.torch import load_file
    from videox_fun.models import (AutoencoderKLQwenImage21, Qwen3VLForConditionalGeneration, Qwen3VLProcessor,
                                   QwenImage21ControlTransformer2DModel)
    from videox_fun.pipeline import QwenImage21ControlPipeline
    from videox_fun.utils import apply_gpu_memory_mode
    dt = torch.bfloat16
    base = snapshot_download("Qwen/Qwen-Image-2.1")
    cfg = OmegaConf.load(CONTROL_CONFIG)
    tr = QwenImage21ControlTransformer2DModel.from_pretrained(
        base, subfolder="transformer", low_cpu_mem_usage=True, torch_dtype=dt,
        transformer_additional_kwargs=OmegaConf.to_container(cfg["transformer_additional_kwargs"])).to(dt)
    m, u = tr.load_state_dict(load_file(hf_hub_download(CONTROL_REPO, CONTROL_FILE)), strict=False)
    print("control weights: missing", len(m), "unexpected", len(u), flush=True)
    tr.control_load = (list(m), list(u))
    pipe = QwenImage21ControlPipeline(
        vae=AutoencoderKLQwenImage21.from_pretrained(base, subfolder="vae").to(dt),
        text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(base, subfolder="text_encoder", torch_dtype=dt),
        processor=Qwen3VLProcessor.from_pretrained(base, subfolder="processor"), transformer=tr,
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(base, subfolder="scheduler"))
    apply_gpu_memory_mode(pipe, "model_cpu_offload", "cuda", dt, exclude_module_name=["img_in", "txt_in", "time_text_embed", "modulation"])
    return pipe, tr


def draw_control(pipe, prompt, depth, scale, cfg):
    import torch
    from videox_fun.utils.utils import get_image_latent
    g = torch.Generator(device="cuda").manual_seed(SEED)
    ctrl = get_image_latent(depth, sample_size=[720, 1280])[:, :, 0]
    with torch.no_grad():
        return pipe(prompt, negative_prompt=" ", height=720, width=1280, generator=g, num_inference_steps=30, true_cfg_scale=cfg,
                    control_image=ctrl, control_context_scale=scale).images[0]


def step0(pipe, tr, lora, outd, say, t):
    """Key match (100 % or stop) and a sample with and without the LoRA from the same seed. Returns True when S3c may go on."""
    from safetensors import safe_open
    with safe_open(lora, framework="pt") as f:
        keys = list(f.keys())
    cok, bad = control_load_ok(*tr.control_load)
    say("STEP0 control branch: missing", len(tr.control_load[0]), "unexpected", len(tr.control_load[1]), "control keys not loaded", bad[:8])
    if not cok:
        say("STEP0 FAIL: control_img_in / control_blocks keys did not load (strict=False hid it); S3c stops")
        return False
    ok, total, miss = match_report(keys, [n for n, _ in tr.named_modules()])
    say("STEP0 lora layers matched", ok, "of", total, "unmatched sample", miss[:8])
    if ok != total:
        say("STEP0 FAIL: the LoRA does not match the control transformer; S3c stops (no training, plan section Step 0)")
        return False
    import torch
    from PIL import Image
    loras = t.Loras(pipe, tr, {"R": lora}, say)
    grey = Image.new("RGB", (1280, 720), (128, 128, 128))
    for tag, key in (("base", None), ("lora", "R")):
        p = loras.use(key, 1.0)
        draw_control(p, SAMPLE_PROMPT, grey, 0.0, 4.0).convert("RGB").save(Path(outd) / f"step0_{tag}.png")
    say("STEP0 samples saved: step0_base.png, step0_lora.png (the style must differ visibly)")
    return True


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, p2s_dir, s3_dir, outd, lora = argv[:5]
    only = argv[5].split(",") if len(argv) > 5 and argv[5] else SCENES
    cfg = float(argv[6]) if len(argv) > 6 else 2.5
    outd, p2s_dir, s3_dir = Path(outd), Path(p2s_dir), Path(s3_dir); outd.mkdir(parents=True, exist_ok=True)
    say = t.logger(outd, "s3c.log")
    scenes = [x for x in load(scene_dir) if x["name"] in only]
    todo = jobs(scenes)
    say("S3c cfg", cfg, "seed", SEED, "pictures", len(todo))
    pipe, tr = load_control_pipeline()
    if not step0(pipe, tr, lora, outd, say, t):
        return
    p = t.Loras(pipe, tr, {"R": lora}, say).use("R", 1.0)
    shots = {(s["name"], sh["id"]): (s, sh) for s in scenes for sh in s["shots"]}
    for j in (x for x in todo if x["pass"] == "A"):
        f = outd / f"{j['name']}.png"
        if f.exists():
            continue
        sc, sh = shots[(j["scene"], j["shot"])]
        t0 = time.time()
        draw_control(p, pass_a_prompt(sc, sh), Image.open(s3_dir / f"{sc['name']}_{sh['id']}_depth.png").convert("RGB"), j["scale"], j.get("cfg", cfg)
                     ).convert("RGB").save(f)
        say("made", j["name"], round(time.time() - t0), "s")
    del pipe, tr, p
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    pipe, tr = t.load_pipeline()  # pass B is the ordinary edit pipeline: the control pipeline takes no reference images
    p = t.Loras(pipe, tr, {"R": lora}, say).use("R", 1.0)
    t.SEED, t.CFG = SEED, cfg
    for j in (x for x in todo if x["pass"] == "B"):
        f = outd / f"{j['name']}.png"
        if f.exists():
            continue
        sc, sh = shots[(j["scene"], j["shot"])]
        prompt, role = pass_b_prompt(sc, sh)
        refs = [outd / f"{sc['name']}_{sh['id']}_A{SCALES[0]}.png", p2s_dir / f"{sc['name']}_{SEED}_s0.png"]
        if role:
            refs.append(p2s_dir / f"{sc['name']}_sheet_{role}.png")
        t0 = time.time()
        t.draw(p, prompt, [Image.open(r).convert("RGB") for r in refs]).convert("RGB").save(f)
        f.with_suffix(".txt").write_text(prompt, encoding="utf-8")
        say("made", j["name"], round(time.time() - t0), "s")


def sheet(outd):
    """<out>/s3c_sheet.jpg: per scene a depth row (the control image), pass A at 1.0, pass B, and the 0.6 / 0.8 sweep of its shot."""
    from PIL import Image
    outd = Path(outd)
    rows = []
    for scene in SCENES:
        for kind in ("A1.0", "B1.0"):
            ims = [outd / f"{scene}_s{k}_{kind}.png" for k in range(1, 5)]
            if any(f.exists() for f in ims):
                rows.append([Image.open(f).convert("RGB").resize((480, 270)) for f in ims if f.exists()])
        sw = [outd / f"{scene}_{SWEEP_SHOT[scene]}_A{s}.png" for s in (0.6, 0.8)]
        if scene == CFG_PAIR[0]:
            sw.append(outd / f"{scene}_{CFG_PAIR[1]}_A{CFG_PAIR[2]}_cfg{CFG_PAIR[3]}.png")
        if any(f.exists() for f in sw):
            rows.append([Image.open(f).convert("RGB").resize((480, 270)) for f in sw if f.exists()])
    out = outd / "s3c_sheet.jpg"
    img = Image.new("RGB", (480 * 4, 270 * max(len(rows), 1)), (255, 255, 255))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            img.paste(im, (c * 480, r * 270))
    img.save(out, quality=88)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["sheet"]:
        print(sheet(sys.argv[2]))
    else:
        main(sys.argv[1:])
