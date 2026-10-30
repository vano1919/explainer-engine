"""P12b pod job (runs on the pod under pod_wrapper.sh): the Qwen run of the paid-tests plan, section 3.3 / 3.3a / 3.5.

Every model, revision, setting and prompt comes from ``p12b.json`` (T10); nothing is chosen here. One process, the pipeline loaded
once, the xworld LoRA merged once and the multiple-angles (MVA) LoRA merged and unmerged per strength (VideoX-Fun merge_lora). Stages run in ``order``; an optional stage
starts only when the section 3.5 projection fits before ``EE_DEADLINE``. Every picture is written at once with a JSON sidecar, one
line per event goes to ``$EE_OUT/t.jsonl`` and ``$EE_OUT/progress.txt`` is rewritten after every unit (the wrapper uploads
``$EE_OUT``; the weights live under /workspace/models, outside it). Only Qwen: no video model, no layout, no audio (P12c).
"""
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

CFG_NAME = "p12b.json"
MODELS = Path(os.environ.get("P12B_MODELS", "/workspace/models"))
EXIT_SHA_MISMATCH = 3


def units_of(stage):
    """How many pictures a stage makes."""
    if "hosts" in stage:
        return len(stage["hosts"]) * len(stage["seeds"])
    return len(stage["people"]) * len(stage["azimuths"]) * len(stage["mva"])


def estimate_s(name, stages, first_unit_s):
    """Seconds a stage is expected to take: its first unit's measured seconds times its units. Q2 and Q3 use Q1's first unit; a
    stage with no measure yet uses Q1's too (the same pipeline, the same size)."""
    first = first_unit_s.get(name) or first_unit_s.get("Q1")
    return None if first is None else first * units_of(stages[name])


def stage_may_start(name, stages, first_unit_s, done, now, deadline, reserve_s):
    """Section 3.5. An essential stage always starts. An optional one starts only when
    ``now + est(stage) + est(remaining essential stages) + end_reserve <= deadline``; without a measured first unit it does not."""
    if stages[name]["essential"]:
        return True
    own = estimate_s(name, stages, first_unit_s)
    if own is None:
        return False
    rest = 0.0
    for other, st in stages.items():
        if other != name and st["essential"] and other not in done:
            e = estimate_s(other, stages, first_unit_s)
            if e is None:
                return False
            rest += e
    return now + own + rest + reserve_s <= deadline


def ordered(stages):
    return sorted(stages, key=lambda n: stages[n]["order"])


def az_deg(cfg, azimuth):
    """Degrees of an azimuth: the twelve names go round in 30 degree steps from the front view, in the order of ``azimuths``."""
    return 30 * cfg["azimuths"].index(azimuth)


def mva_out(cfg, out, person, azimuth, strength):
    return Path(out) / "mva" / person / f"{az_deg(cfg, azimuth)}_s{strength}.png"


def host_out(out, host, seed):
    return Path(out) / "hosts" / f"{host}_seed{seed}.png"


def pad_to_3_4(img):
    """Pads to 3:4 (width:height) on white, the picture centred."""
    from PIL import Image
    w, h = img.size
    if w * 4 >= h * 3:      # wider than 3:4: grow the height
        tw, th = w, round(w * 4 / 3)
    else:                   # narrower: grow the width
        tw, th = round(h * 3 / 4), h
    canvas = Image.new("RGB", (tw, th), (255, 255, 255))
    canvas.paste(img.convert("RGB"), ((tw - w) // 2, (th - h) // 2))
    return canvas


def person_reference(sheet, size):
    """The left third of a hero sheet (the front view), padded to 3:4 on white, resized to ``size`` (width, height)."""
    from PIL import Image
    img = Image.open(sheet).convert("RGB")
    w, h = img.size
    return pad_to_3_4(img.crop((0, 0, w // 3, h))).resize(tuple(size), Image.LANCZOS)


def host_reference(path, size):
    """A host's v0 picture padded to 3:4 on white, resized to ``size``."""
    from PIL import Image
    return pad_to_3_4(Image.open(path).convert("RGB")).resize(tuple(size), Image.LANCZOS)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Log:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)

    def ev(self, name, **kw):
        line = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ev": name, **kw}
        with open(self.out / "t.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")

    def stage_line(self, text):
        with open(self.out / "stages.txt", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S', time.gmtime())} {text}\n")

    def progress(self, text):
        (self.out / "progress.txt").write_text(f"{time.strftime('%T', time.gmtime())} {text}\n", encoding="utf-8")


def dir_bytes(p):
    p = Path(p)
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0


def timed_download(log, name, target, fn):
    """Runs a download ``fn``; a thread rewrites progress.txt every minute with the bytes on disk (the stall rule must see change)."""
    stop = threading.Event()

    def tick():
        while not stop.wait(60):
            log.progress(f"downloading {name} {dir_bytes(target)} bytes")

    th = threading.Thread(target=tick, daemon=True)
    th.start()
    log.ev("download_start", name=name)
    t0 = time.time()
    try:
        res = fn()
    finally:
        stop.set()
    log.ev("download_end", name=name, bytes=dir_bytes(target), seconds=round(time.time() - t0, 1))
    return res


def load_pipeline(base_dir):
    """Qwen-Image-2.1 in bf16 through VideoX-Fun, built exactly as xworld_v1_test.load_pipeline does (model_full_load on a big card,
    the tested offload path when that fails)."""
    import torch
    sys.path.insert(0, "/workspace/VideoX-Fun")
    from diffusers import FlowMatchEulerDiscreteScheduler
    from videox_fun.models import (AutoencoderKLQwenImage21, Qwen3VLForConditionalGeneration, Qwen3VLProcessor,
                                   QwenImage21Transformer2DModel)
    from videox_fun.pipeline import QwenImage21Pipeline
    from videox_fun.utils import apply_gpu_memory_mode
    dt = torch.bfloat16
    base = str(base_dir)
    tr = QwenImage21Transformer2DModel.from_pretrained(base, subfolder="transformer", low_cpu_mem_usage=True, torch_dtype=dt)
    pipe = QwenImage21Pipeline(
        vae=AutoencoderKLQwenImage21.from_pretrained(base, subfolder="vae").to(dt),
        text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(base, subfolder="text_encoder", torch_dtype=dt),
        processor=Qwen3VLProcessor.from_pretrained(base, subfolder="processor"), transformer=tr,
        scheduler=FlowMatchEulerDiscreteScheduler.from_pretrained(base, subfolder="scheduler"))
    skip = ["img_in", "txt_in", "time_text_embed", "modulation"]
    try:
        apply_gpu_memory_mode(pipe, "model_full_load", "cuda", dt, exclude_module_name=skip)
    except Exception as e:  # too little memory: the tested offload path
        print("gpu mode model_full_load failed:", e, "-> model_cpu_offload", flush=True)
        apply_gpu_memory_mode(pipe, "model_cpu_offload", "cuda", dt, exclude_module_name=skip)
    return pipe


class GateUp:
    """The gate_up correction of xworld_v1_test.Loras: mods = dict(transformer.named_modules())."""

    def __init__(self, tr):
        self.mods = dict(tr.named_modules())

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


def draw(pipe, prompt, ref, cfg, seed, steps, true_cfg, negative):
    import torch
    w, h = cfg["size"]
    g = torch.Generator(device="cuda").manual_seed(seed)
    with torch.no_grad():
        return pipe(prompt, image=[ref], negative_prompt=negative, height=h, width=w, generator=g,
                    num_inference_steps=steps, true_cfg_scale=true_cfg).images[0]


def units(cfg, name, stage):
    """The pictures of a stage in order: dicts with the person or host, azimuth, mva strength, seed, prompt and output path."""
    out = []
    if name == "Q4":
        for host in stage["hosts"]:
            for seed in stage["seeds"]:
                out.append({"host": host, "azimuth": None, "mva": None, "seed": seed, "prompt": cfg["prompt_hosts"][host],
                            "path": host_out("{OUT}", host, seed)})
        return out
    for person in stage["people"]:
        for az in stage["azimuths"]:
            for s in stage["mva"]:
                out.append({"person": person, "azimuth": az, "mva": s, "seed": cfg["seed"],
                            "prompt": cfg["prompt_mva"].replace("{azimuth}", az), "path": mva_out(cfg, "{OUT}", person, az, s)})
    return out


def main():
    here = Path(__file__).resolve().parent
    cfg = json.loads((here / CFG_NAME).read_text(encoding="utf-8"))
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    deadline = float(os.environ["EE_DEADLINE"])
    log = Log(out)
    rc = 0
    try:
        rc = run(cfg, out, deadline, log)
    finally:
        log.ev("exit", rc=rc)
    return rc


def run(cfg, out, deadline, log):
    import torch
    from huggingface_hub import hf_hub_download, snapshot_download
    log.progress("start")
    log.ev("boot", deadline=deadline, pod=os.environ.get("RUNPOD_POD_ID", ""), python=sys.version.split()[0],
           torch=torch.__version__, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
    base_dir = MODELS / "qwen"
    base = timed_download(log, "base", base_dir, lambda: snapshot_download(
        cfg["base"]["repo"], revision=cfg["base"]["revision"], local_dir=str(base_dir)))
    sl = cfg["style_lora"]
    style = timed_download(log, "style_lora", MODELS / "style", lambda: hf_hub_download(
        sl["hf"], sl["path"], repo_type="dataset", local_dir=str(MODELS / "style")))
    got = sha256_file(style)
    if got != sl["sha256"]:
        log.ev("sha256_mismatch", name="style_lora", expected=sl["sha256"], got=got)
        log.progress("style lora sha256 mismatch")
        return EXIT_SHA_MISMATCH
    ml = cfg["mva_lora"]
    mva = timed_download(log, "mva_lora", MODELS / "mva", lambda: hf_hub_download(
        ml["repo"], ml["file"], revision=ml["revision"], local_dir=str(MODELS / "mva")))
    refs_cfg = cfg["references"]
    size = cfg["size"]
    refs = {}
    for person in ("napoleon", "general", "baker", "legionary"):
        sheet = timed_download(log, f"sheet_{person}", MODELS / "sheets" / person, lambda p=person: hf_hub_download(
            refs_cfg["repo"], refs_cfg[p], repo_type=refs_cfg["repo_type"], local_dir=str(MODELS / "sheets" / p)))
        refs[person] = person_reference(sheet, size)
    for host, rel in cfg["hosts"].items():
        pic = timed_download(log, f"host_{host}", MODELS / "hosts" / host, lambda r=rel, h=host: hf_hub_download(
            refs_cfg["repo"], r, repo_type=refs_cfg["repo_type"], local_dir=str(MODELS / "hosts" / h)))
        refs[host] = host_reference(pic, size)

    t0 = time.time()
    pipe = load_pipeline(base)
    from videox_fun.utils import merge_lora, unmerge_lora    # the call shape of xworld_v1_test.py (pipe in, pipe out)
    dt = torch.bfloat16
    gu = GateUp(pipe.transformer)
    pipe = merge_lora(pipe, style, 1.0, device="cuda", dtype=dt)
    log.ev("lora_gate_up", lora="style", sign=1.0, layers=gu.gate_up(style, 1.0))
    mva_on = None                                              # the MVA strength merged now (None = not merged)
    log.ev("model_loaded", seconds=round(time.time() - t0, 1))

    stages = cfg["stages"]
    reserve = cfg["end_reserve_min"] * 60
    first_unit_s, done = {}, set()
    for name in ordered(stages):
        st = stages[name]
        if not stage_may_start(name, stages, first_unit_s, done, time.time(), deadline, reserve):
            log.stage_line(f"skipped {name} (projection)")
            log.ev("stage_skipped", stage=name, reason="projection")
            continue
        log.stage_line(f"start {name}")
        todo = units(cfg, name, st)
        for i, u in enumerate(todo, 1):
            path = Path(str(u["path"]).replace("{OUT}", str(out)))
            path.parent.mkdir(parents=True, exist_ok=True)
            want = None if name == "Q4" else u["mva"]
            if want != mva_on:
                if mva_on is not None:
                    pipe = unmerge_lora(pipe, mva, mva_on, device="cuda", dtype=dt)
                    gu.gate_up(mva, -mva_on)
                if want is not None:
                    pipe = merge_lora(pipe, mva, want, device="cuda", dtype=dt)
                    log.ev("lora_gate_up", lora="mva", sign=want, layers=gu.gate_up(mva, want))
                mva_on = want
            if name == "Q4":
                ref, negative = refs[u["host"]], st["negative"]
            else:
                ref, negative = refs[u["person"]], ""
            t = time.time()
            img = draw(pipe, u["prompt"], ref, cfg, u["seed"], st["steps"], st["true_cfg_scale"], negative)
            secs = round(time.time() - t, 1)
            img.convert("RGB").save(path)
            side = {"stage": name, "azimuth": u["azimuth"], "mva": u["mva"], "seed": u["seed"], "steps": st["steps"],
                    "true_cfg_scale": st["true_cfg_scale"], "seconds": secs, "prompt": u["prompt"]}
            side["host" if "host" in u else "person"] = u.get("host") or u.get("person")
            path.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
            if i == 1:
                first_unit_s[name] = secs
                log.ev("first_unit", stage=name, seconds=secs)
            log.progress(f"{name} {i}/{len(todo)}")
        done.add(name)
        log.stage_line(f"done {name}")
    log.progress("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
