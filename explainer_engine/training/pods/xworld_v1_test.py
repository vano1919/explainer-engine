"""Prompt-type test of xworld_v1 on held-out scenes (D-80, LT-75); run by xworld_v1_test.sh on a pod (OR-21).

For each held-out chain the REAL first frame is given and frames 2..6 are drawn; each drawn frame is later scored against the
real frame of the same place in the scene (LT-75, free, after the pod). Variants, adapted from the 2026-10-25 continuity
test (film_1min k_s11: D, V1-V6) to R&M scenes, which have no character sheets (so V1 = D and V2 has nothing to reorder):
  D   master (real frame 1) + full description + change line + "Keep everything else the same."
  V3  D with a short description (first sentence only) in place of the full one
  V4  D without the change line
  V5  D + the previous DRAWN frame as a second reference
  V6  a short prompt (about 35 words) + master
  T   the training format: only the previous drawn frame as reference + description + change line
  D0, T0  D and T without the LoRA
LoRA variants run at two checkpoints (chosen from the training samples); the order puts the most informative jobs first
so a money cap that stops the pod early still leaves whole chains of D and T.
Pictures: 1280x720, 30 steps, true_cfg 4 (the training sampler's guidance), seed 11.

    python xworld_v1_test.py <dataset dir> <captions_reviewed.jsonl> <out dir> <lora A> <lora B>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

TRIGGER = "xworld style"
KEEP = "Keep everything else the same."
MASTER = "Image 1 is the place and the people of this scene: keep its landmarks, light, colours and the people's looks."
PREV = "Image 1 is the previous shot of this scene."
LORA_VARIANTS = ("D", "T", "V5", "V4", "V3", "V6")
BASE_VARIANTS = ("D0", "T0")
SEED, STEPS, CFG, W, H = 11, 30, 4.0, 1280, 720


def _short(text, words):
    return " ".join(text.split()[:words]).rstrip(",.;") + "."


def prompt(variant, desc, change):
    first = desc.split(". ")[0].rstrip(".") + "."
    v = variant.rstrip("0") if variant in BASE_VARIANTS else variant
    if v == "D":
        return f"{TRIGGER}, {MASTER} {desc} {change} {KEEP}"
    if v == "V3":
        return f"{TRIGGER}, {MASTER} {first} {change} {KEEP}"
    if v == "V4":
        return f"{TRIGGER}, {MASTER} {desc}"
    if v == "V5":
        return f"{TRIGGER}, {MASTER} Image 2 is the previous shot. {desc} {change} {KEEP}"
    if v == "V6":
        return f"{TRIGGER}, {MASTER} {_short(desc, 35)}"
    if v == "T":
        return f"{TRIGGER}, {PREV} {desc} {change}"
    raise ValueError(variant)


def jobs(manifest, caps, loras=("A", "B"), frames=5):
    """[{name, chain, k, variant, lora, prompt, refs}] in run order; refs: 'real:<img>' or 'drawn:<name>'."""
    chains = [c for c in manifest["hold_out"]["chains"] if len(c) >= frames + 1][:4]
    order = [(v, l) for l in loras for v in ("D", "T")] + [(v, None) for v in BASE_VARIANTS] + \
            [(v, l) for l in loras for v in LORA_VARIANTS if v not in ("D", "T")]
    out = []
    for v, l in order:
        for ci, chain in enumerate(chains):
            prev = None
            for k in range(1, frames + 1):
                a, b = chain[k - 1], chain[k]
                name = f"c{ci}_f{k}_{v}_{l or 'base'}"
                desc, change = caps[f"d:{b}"], caps[f"c:{a}>{b}"]
                if v in ("T", "T0"):
                    refs = [f"real:{chain[0]}"] if k == 1 else [f"drawn:{prev}"]
                elif v == "V5" and k > 1:
                    refs = [f"real:{chain[0]}", f"drawn:{prev}"]
                else:
                    refs = [f"real:{chain[0]}"]
                out.append({"name": name, "chain": ci, "k": k, "truth": b, "variant": v, "lora": l,
                            "prompt": prompt(v, desc, change), "refs": refs})
                prev = name
    return out


def load_pipeline():
    """Qwen-Image-2.1 in bf16 with CPU offload (VideoX-Fun); returns (pipe, transformer)."""
    import torch
    sys.path.insert(0, "/workspace/VideoX-Fun")
    from diffusers import FlowMatchEulerDiscreteScheduler
    from huggingface_hub import snapshot_download
    from videox_fun.models import (AutoencoderKLQwenImage21, Qwen3VLForConditionalGeneration, Qwen3VLProcessor,
                                   QwenImage21Transformer2DModel)
    from videox_fun.pipeline import QwenImage21Pipeline
    from videox_fun.utils import apply_gpu_memory_mode
    dt = torch.bfloat16
    base = snapshot_download("Qwen/Qwen-Image-2.1")
    tr = QwenImage21Transformer2DModel.from_pretrained(base, subfolder="transformer", low_cpu_mem_usage=True, torch_dtype=dt)
    pipe = QwenImage21Pipeline(
        vae=AutoencoderKLQwenImage21.from_pretrained(base, subfolder="vae").to(dt),
        text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(base, subfolder="text_encoder", torch_dtype=dt),
        processor=Qwen3VLProcessor.from_pretrained(base, subfolder="processor"), transformer=tr,
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(base, subfolder="scheduler"))
    apply_gpu_memory_mode(pipe, "model_cpu_offload", "cuda", dt,
                          exclude_module_name=["img_in", "txt_in", "time_text_embed", "modulation"])
    return pipe, tr


class Loras:
    """Merges one LoRA at a time into the pipeline (None = the base model)."""

    def __init__(self, pipe, tr, paths, say):
        self.pipe, self.mods, self.paths, self.say, self.loaded = pipe, dict(tr.named_modules()), paths, say, None

    def gate_up(self, path, sign):
        """ai-toolkit trains the fused img_mlp.gate_up = [gate_layer; proj]; VideoX-Fun's merge skips it (10-25 finding)."""
        import re
        import torch
        from safetensors.torch import load_file
        sd, n = load_file(path), 0
        for key in sd:
            m = re.search(r"transformer_blocks[._](\d+)[._]img_mlp[._]gate_up\.(lora_A|lora_down)\.weight$", key)
            if not m:
                continue
            pre = key[:-len(m.group(2) + ".weight")]
            down = sd[key].float(); up = sd[pre + ("lora_B" if m.group(2) == "lora_A" else "lora_up") + ".weight"].float()
            alpha = float(sd[pre + "alpha"]) if pre + "alpha" in sd else down.shape[0]
            delta = (up @ down) * (alpha / down.shape[0]) * sign
            ff = self.mods[f"transformer_blocks.{m.group(1)}.img_mlp"]; half = ff.gate_layer.weight.shape[0]
            with torch.no_grad():
                for lin, d in ((ff.gate_layer, delta[:half]), (ff.proj, delta[half:])):
                    lin.weight.data += d.to(lin.weight.device, lin.weight.dtype)
            n += 1
        return n

    def use(self, key, weight=1.0):
        """Merges LoRA `key` at `weight` (None = the base model); a different weight unmerges and merges again."""
        import torch
        from videox_fun.utils import merge_lora, unmerge_lora
        want = (key, weight) if key else None
        if want == self.loaded:
            return self.pipe
        dt = torch.bfloat16
        if self.loaded:
            k, w = self.loaded
            self.pipe = unmerge_lora(self.pipe, self.paths[k], w, device="cuda", dtype=dt)
            self.gate_up(self.paths[k], -w)
        if key:
            self.pipe = merge_lora(self.pipe, self.paths[key], weight, device="cuda", dtype=dt)
            self.say("lora", key, weight, self.paths[key], "gate_up fixed", self.gate_up(self.paths[key], weight))
        self.loaded = want
        return self.pipe


def draw(pipe, prompt_text, refs):
    """One 1280x720 picture; refs = [] draws from the text alone."""
    import torch
    g = torch.Generator(device="cuda").manual_seed(SEED)
    with torch.no_grad():
        return pipe(prompt_text, image=refs or None, negative_prompt="", height=H, width=W, generator=g,
                    num_inference_steps=STEPS, true_cfg_scale=CFG).images[0]


def logger(outd, name):
    log = open(outd / name, "a")

    def say(*a):
        print(*a, flush=True); log.write(time.strftime("%H:%M:%S ") + " ".join(map(str, a)) + "\n"); log.flush()
    return say


def main(argv):
    from PIL import Image
    ds, caps_path, outd, lora_a, lora_b = argv[:5]
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    caps = {}
    for line in Path(caps_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line); caps[r["id"]] = r["text"]
    todo = jobs(json.loads((Path(ds) / "manifest.json").read_text(encoding="utf-8")), caps)
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = logger(outd, "test.log")
    pipe, tr = load_pipeline()
    loras = Loras(pipe, tr, {"A": lora_a, "B": lora_b}, say)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(Path(ds) / r[5:] if r.startswith("real:") else outd / f"{r[6:]}.png").convert("RGB")
                for r in j["refs"]]
        t = time.time()
        draw(loras.use(j["lora"]), j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
