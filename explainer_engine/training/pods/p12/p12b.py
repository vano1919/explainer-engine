"""P12b pod job, process 1 (runs on the pod under pod_wrapper.sh): stage M (setup measurement) and the Qwen run of the paid-tests
plan, section 3.3 / 3.5 (no host stage: D-89). Process 2 (p12c_ltx.py, the LTX-2.5 stages) is started by p12b.sh after this exits.

Every model, revision, setting and prompt comes from ``p12b.json``; nothing is chosen here. One process, the pipeline loaded once,
the xworld LoRA merged once and the multiple-angles (MVA) LoRA merged and unmerged per strength (VideoX-Fun merge_lora). Qwen
stages run in ``order``; an optional stage starts only when the section 3.5 projection fits before ``EE_DEADLINE``, with the LTX
stages still to come counted as a fixed reserve (``ltx.reserve_min``). Every picture is written at once with a JSON sidecar, one
line per event goes to ``$EE_OUT/t.jsonl`` and ``$EE_OUT/progress.txt`` is rewritten after every unit (the wrapper uploads
``$EE_OUT``; the weights live under /workspace/models, outside it). The LTX weights are fetched file by file in a background thread
while the Qwen stages draw; no video step runs in this process. After every stage the creator's soft stop file is read.
"""
import calendar
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

CFG_NAME = "p12b.json"
MODELS = Path(os.environ.get("P12B_MODELS", "/workspace/models"))
EXIT_SHA_MISMATCH = 3
QWEN = "qwen_mva"


def kind_of(stage):
    return stage.get("kind", QWEN)


def units_of(stage):
    """How many pictures (Qwen) or clips (LTX) a stage makes."""
    if kind_of(stage) != QWEN:
        return len(stage["shots"])
    return len(stage["people"]) * len(stage["azimuths"]) * len(stage["mva"])


def estimate_s(name, stages, first_unit_s):
    """Seconds a stage is expected to take: its first unit's measured seconds times its units. Q2 and Q3 use Q1's first unit; an
    LTX stage has only its own measure (process 1 never measures one, so it is None here)."""
    if kind_of(stages[name]) != QWEN:
        first = first_unit_s.get(name)
    else:
        first = first_unit_s.get(name) or first_unit_s.get("Q1")
    return None if first is None else first * units_of(stages[name])


def stage_may_start(name, stages, first_unit_s, done, now, deadline, reserve_s, extra_reserve_s=0.0):
    """Section 3.5. An essential stage always starts. An optional one starts only when
    ``now + est(stage) + est(remaining essential stages of its kind) + extra_reserve + end_reserve <= deadline``; without a measured
    first unit it does not. ``extra_reserve_s`` holds the stages of the other process (the LTX reserve in process 1)."""
    if stages[name]["essential"]:
        return True
    own = estimate_s(name, stages, first_unit_s)
    if own is None:
        return False
    rest = float(extra_reserve_s)
    for other, st in stages.items():
        if other != name and st["essential"] and other not in done and kind_of(st) == kind_of(stages[name]):
            e = estimate_s(other, stages, first_unit_s)
            if e is None:
                return False
            rest += e
    return now + own + rest + reserve_s <= deadline


def ordered(stages, kind=None):
    names = [n for n in stages if kind is None or kind_of(stages[n]) == kind]
    return sorted(names, key=lambda n: stages[n]["order"])


def after_reserve(cfg, name, optional):
    """Seconds of the optional LTX stages that rank AFTER ``name`` in ``drop_order`` and must still fit behind it: a stage dropped first
    may only start when the ones dropped later still fit (Q3 before L3 before Q2)."""
    order = cfg["drop_order"]
    if name not in order:
        return 0.0
    later = order[order.index(name) + 1:]
    return sum(optional.get(n, 0.0) for n in later)


def az_deg(cfg, azimuth):
    """Degrees of an azimuth: the twelve names go round in 30 degree steps from the front view, in the order of ``azimuths``."""
    return 30 * cfg["azimuths"].index(azimuth)


def mva_out(cfg, out, person, azimuth, strength):
    return Path(out) / "mva" / person / f"{az_deg(cfg, azimuth)}_s{strength}.png"


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


def style_weight(cfg):
    """The xworld_v2 LoRA's weight: p12b.json only (0.7, the creator's call of 2026-10-31); nothing is chosen in this script."""
    return float(cfg["style_lora"]["weight"])


def ltx_download_fits(free_bytes, cfg):
    """True when the free disk after the Qwen weights holds the LTX files plus the margin (``ltx.expected_gb`` + ``ltx.margin_gb``)."""
    v = cfg["ltx"]
    return free_bytes >= (float(v["expected_gb"]) + float(v["margin_gb"])) * 2 ** 30


def start_ltx_download(log, cfg):
    """Fetches the LTX-2.5 files (``files`` + ``av_files`` + the Layout LoRA) one by one in a background thread so the Qwen stages
    do not wait for them (not snapshot_download: the repo holds far more than the files listed). Returns the thread, or None when the
    disk is too small. A failed file is logged (``ltx_download_failed``, ``gated_403`` on a 403) and the next one is tried; nothing
    is raised into the Qwen stages. The token is huggingface_hub's own (HF_TOKEN in the env)."""
    lt = cfg["ltx"]
    target = MODELS / lt["local"]
    MODELS.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(MODELS).free
    if not ltx_download_fits(free, cfg):
        log.ev("ltx_download_skipped", why="disk", free_bytes=free, need_gb=float(lt["expected_gb"]) + float(lt["margin_gb"]))
        return None
    from huggingface_hub import hf_hub_download
    ll = lt["layout_lora"]
    jobs = [(lt["repo"], f, lt["revision"]) for f in list(lt["files"]) + list(lt["av_files"])]
    jobs.append((ll["repo"], ll["file"], ll["revision"]))

    def fetch():
        log.ev("ltx_download_start", repo=lt["repo"], revision=lt["revision"], files=len(jobs))
        t0, ok = time.time(), 0
        for repo, f, rev in jobs:
            t1 = time.time()
            try:
                p = hf_hub_download(repo, f, revision=rev, local_dir=str(target))
                ok += 1
                log.ev("ltx_download_file_end", repo=repo, file=f, bytes=dir_bytes(p), seconds=round(time.time() - t1, 1))
            except Exception as e:   # noqa: BLE001 - a failed side download must not stop the Qwen run
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 403:
                    log.ev("gated_403", repo=repo, file=f)
                log.ev("ltx_download_failed", repo=repo, file=f, error=str(e)[:300])
        log.ev("ltx_download_end", files_ok=ok, files=len(jobs), bytes=dir_bytes(target), seconds=round(time.time() - t0, 1))

    th = threading.Thread(target=fetch, name="ltx-download", daemon=True)
    th.start()
    return th


def creator_stop_after(cfg, log, timeout_s=20):
    """The creator's soft stop: the first word of ``control.path`` on HF (one of M Q1 Q2 Q3 L1 L3 L2 AV), or None. A missing file, a
    network error or a read longer than ``timeout_s`` is no stop (``control_check_failed``); this never raises."""
    c = cfg.get("control")
    if not c:
        return None
    box = {}

    def fetch():
        try:
            from huggingface_hub import hf_hub_download
            tmp = tempfile.mkdtemp(prefix="ee_ctl_")
            p = hf_hub_download(c["repo"], c["path"], repo_type="dataset", local_dir=tmp, force_download=True)
            box["text"] = Path(p).read_text(encoding="utf-8")
        except Exception as e:   # noqa: BLE001 - a control read must never stop the run
            box["error"] = str(e)[:200]

    th = threading.Thread(target=fetch, name="control-read", daemon=True)
    th.start()
    th.join(timeout_s)
    if th.is_alive():
        log.ev("control_check_failed", why="timeout")
        return None
    if "error" in box:
        log.ev("control_check_failed", error=box["error"])
        return None
    words = box.get("text", "").split()
    return words[0] if words else None


def stop_here(cfg, log, out, name):
    """True when the creator asked to stop after ``name``: writes stages.txt and ``control/stopped_after.txt`` (p12b.sh then skips
    process 2, and p12c_ltx.py exits at once if it reads it)."""
    if creator_stop_after(cfg, log) != name:
        return False
    log.stage_line(f"creator_stop after {name}")
    log.ev("creator_stop", after=name)
    p = Path(out) / "control" / "stopped_after.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(name + "\n", encoding="utf-8")
    return True


def script_start_epoch(out):
    """The ``script_start`` time p12b.sh wrote to t.jsonl, as epoch seconds, or None."""
    try:
        for line in (Path(out) / "t.jsonl").read_text(encoding="utf-8").splitlines():
            e = json.loads(line)
            if e.get("ev") == "script_start":
                return calendar.timegm(time.strptime(e["t"], "%Y-%m-%dT%H:%M:%SZ"))
    except (OSError, ValueError, KeyError):
        pass
    return None


def write_measure(log, out, nbytes, secs):
    """Stage M: ``measure.json`` with the Qwen download's bytes, seconds and MB/s and the setup minutes from script_start (the image
    pull and boot before the script are not seen in the pod: boot_s stays null, the session reads it from the create record)."""
    start = script_start_epoch(out)
    m = {"boot_s": None, "script_start": start,
         "setup_min": round((time.time() - start) / 60, 1) if start else None,
         "qwen_dl_bytes": nbytes, "qwen_dl_s": round(secs, 1),
         "mb_s": round(nbytes / 1e6 / secs, 1) if secs > 0 else None,
         "xet": os.environ.get("HF_XET_HIGH_PERFORMANCE") == "1"}
    (Path(out) / "measure.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    log.ev("measure", **m)
    log.stage_line(f"done M setup={m['setup_min']} mb_s={m['mb_s']}")
    return m


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
    """The pictures of a stage in order: dicts with the person, azimuth, mva strength, seed, prompt and output path."""
    out = []
    for person in stage["people"]:
        for az in stage["azimuths"]:
            for s in stage["mva"]:
                out.append({"person": person, "azimuth": az, "mva": s, "seed": cfg["seed"],
                            "prompt": cfg["prompt_mva"].replace("{azimuth}", az), "path": mva_out(cfg, "{OUT}", person, az, s)})
    return out


class ticker:
    """``with ticker(log, "loading the model"):`` rewrites progress.txt every minute while the block runs (the stall rule must see change)."""

    def __init__(self, log, text, every=60):
        self.log, self.text, self.every, self.stop = log, text, every, threading.Event()

    def __enter__(self):
        t0 = time.time()

        def tick():
            while not self.stop.wait(self.every):
                self.log.progress(f"{self.text} {int(time.time() - t0)} s")

        self.log.progress(self.text)
        threading.Thread(target=tick, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        return False


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
    t_dl = time.time()
    base = timed_download(log, "base", base_dir, lambda: snapshot_download(
        cfg["base"]["repo"], revision=cfg["base"]["revision"], local_dir=str(base_dir)))
    write_measure(log, out, dir_bytes(base_dir), time.time() - t_dl)          # stage M
    if stop_here(cfg, log, out, "M"):                                          # the creator may stop right after the measurement
        log.progress("creator stop")
        return 0
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

    ltx = start_ltx_download(log, cfg)                         # in parallel with the model load and the Qwen stages
    t0 = time.time()
    with ticker(log, "loading the model"):
        pipe = load_pipeline(base)
        from videox_fun.utils import merge_lora, unmerge_lora    # the call shape of xworld_v1_test.py (pipe in, pipe out)
        dt = torch.bfloat16
        gu = GateUp(pipe.transformer)
        w = style_weight(cfg)                                      # xworld_v2 at 0.7 (creator 2026-10-31), from p12b.json
        pipe = merge_lora(pipe, style, w, device="cuda", dtype=dt)
        log.ev("lora_gate_up", lora="style", sign=w, layers=gu.gate_up(style, w))
    mva_on = None                                              # the MVA strength merged now (None = not merged)
    log.ev("model_loaded", seconds=round(time.time() - t0, 1))

    stages = cfg["stages"]
    reserve = cfg["end_reserve_min"] * 60
    ltx_reserve = float(cfg["ltx"]["reserve_min"]) * 60       # the LTX process still to come (a plan number, not measured)
    optional = {k: float(v) * 60 for k, v in cfg["ltx"].get("optional_reserve_min", {}).items()}
    first_unit_s, done = {}, set()
    for name in ordered(stages, kind=QWEN):
        st = stages[name]
        if not stage_may_start(name, stages, first_unit_s, done, time.time(), deadline, reserve,
                               extra_reserve_s=ltx_reserve + after_reserve(cfg, name, optional)):
            log.stage_line(f"skipped {name} (projection)")
            log.ev("stage_skipped", stage=name, reason="projection")
            continue
        log.stage_line(f"start {name}")
        todo = units(cfg, name, st)
        for i, u in enumerate(todo, 1):
            path = Path(str(u["path"]).replace("{OUT}", str(out)))
            path.parent.mkdir(parents=True, exist_ok=True)
            want = u["mva"]
            if want != mva_on:
                if mva_on is not None:
                    pipe = unmerge_lora(pipe, mva, mva_on, device="cuda", dtype=dt)
                    gu.gate_up(mva, -mva_on)
                if want is not None:
                    pipe = merge_lora(pipe, mva, want, device="cuda", dtype=dt)
                    log.ev("lora_gate_up", lora="mva", sign=want, layers=gu.gate_up(mva, want))
                mva_on = want
            ref, negative = refs[u["person"]], ""
            t = time.time()
            img = draw(pipe, u["prompt"], ref, cfg, u["seed"], st["steps"], st["true_cfg_scale"], negative)
            secs = round(time.time() - t, 1)
            img.convert("RGB").save(path)
            side = {"stage": name, "azimuth": u["azimuth"], "mva": u["mva"], "seed": u["seed"], "steps": st["steps"],
                    "true_cfg_scale": st["true_cfg_scale"], "seconds": secs, "prompt": u["prompt"]}
            side["person"] = u["person"]
            path.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
            if i == 1:
                first_unit_s[name] = secs
                log.ev("first_unit", stage=name, seconds=secs)
            log.progress(f"{name} {i}/{len(todo)}")
        done.add(name)
        log.stage_line(f"done {name}")
        if stop_here(cfg, log, out, name):
            log.progress("creator stop")
            return 0
    q1 = mva_out(cfg, out, "napoleon", "front-right quarter view", 0.8)   # AV2's picture (plan 3.4b, O-AV2)
    if q1.exists():
        (Path(out) / "qwen_done.txt").write_text(str(q1) + "\n", encoding="utf-8")
    limit = deadline - reserve
    while ltx is not None and ltx.is_alive() and time.time() < limit:            # keep progress.txt moving: the stall rule watches it
        log.progress(f"waiting for the LTX weights {dir_bytes(MODELS / cfg['ltx']['local'])} bytes")
        ltx.join(timeout=60)
    log.progress("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
