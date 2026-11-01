"""P12 combined pod, process 2 (runs on the pod after p12b.py exits): the LTX-2.5 stages L1, L3, L2, AV of p12b.json.

Started by p12b.sh unless the creator's soft stop was hit (``$EE_OUT/control/stopped_after.txt``). Every clip is one CLI call of
``ltx_pipelines`` (plan 3.4: the fallback path, so no Python API is assumed); every flag string lives in ``FLAGS`` and every
module name in ``MODULES`` (read at Lightricks/LTX-2@e98f6d9, file:line in docs/pods/P12_LTX_FLAGS.md; a wrong flag ends that
clip ``failed``, the pod goes on). Missing weights, a missing clay video or a missing take skip the stage, never fail the pod: the
Qwen results stand.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_NAME = "p12b.json"
MODELS = Path(os.environ.get("P12B_MODELS", "/workspace/models"))
CODE_DIR = Path("/workspace/LTX-2")

# The only place a flag string lives (a test checks it). None = not known yet: the flag is left out of the command.
# Every value was read at Lightricks/LTX-2@e98f6d9 (packages/ltx-pipelines/src/ltx_pipelines/...); table: P12_LTX_FLAGS.md.
FLAGS = {
    "image": "--image",                           # utils/args.py:1003 (ImageAction args.py:189: PATH FRAME_IDX STRENGTH)
    "prompt": "--prompt",                         # utils/args.py:813 (basic_arg_parser, required)
    "width": "--width",                           # utils/args.py:990 (new_video_gen_arg_parser)
    "height": "--height",                         # utils/args.py:984 (new_video_gen_arg_parser)
    # utils/args.py:966 (8k+1); with supports_auto_duration=True (distilled.py:516) it is args.py:940, default None;
    # a2vid default None (a2vid_two_stage.py:563)
    "num_frames": "--num-frames",
    "frame_rate": "--frame-rate",                 # utils/args.py:997
    "seed": "--seed",                             # utils/args.py:759 (add_seed_arg)
    "output": "--output-path",                    # utils/args.py:819 (basic_arg_parser, required)
    "transformer": "--transformer-path",          # utils/args.py:710 (split layout; accepted by args.py:611-622)
    "text_encoder": "--text-encoder-path",        # utils/args.py:720 (split layout, single-file Gemma TE)
    "video_vae": "--video-vae-path",              # utils/args.py:726
    "audio_vae": "--audio-vae-path",              # utils/args.py:737
    "upsampler": "--spatial-upsampler-path",      # utils/args.py:1559 (2-stage) and :1608 (2-stage distilled), required
    "distilled_lora": "--distilled-lora",         # utils/args.py:1543 (LoraAction, required in default_2_stage_arg_parser)
    "audio": "--audio-path",                      # a2vid_two_stage.py:540 (required)
    "audio_max": "--audio-max-duration",          # a2vid_two_stage.py:552 (excludes --num-frames: a2vid_two_stage.py:525)
    "video_cond": "--video-conditioning",         # ic_lora.py:820 (nargs=2: PATH STRENGTH, required)
    "lora": "--lora",                             # utils/args.py:826 (LoraAction args.py:243: PATH [STRENGTH])
    "stage2_ic": "--stage-2-ic-lora",             # ic_lora.py:855 (store_true)
    # One token on purpose: _common() calls _flag(cmd, "fp8") with no value, argparse takes --opt=value for long options.
    # --quantization utils/args.py:886; "fp8-cast" from its help text args.py:891/896.
    # UNVERIFIED: the QuantizationKind values (utils/quantization_factory.py) were not passed; help text only
    "fp8": "--quantization=fp8-cast",
}
MODULES = {
    # distilled.py:510 main(), :512 resolve_cli_params(distilled=True), :516 default_2_stage_distilled_arg_parser
    # (supports_auto_duration=True); --image -> images= distilled.py:542 (image conditioning, L1/L3)
    "ltx_i2v": "ltx_pipelines.distilled",
    "ltx_ic": "ltx_pipelines.ic_lora",            # ic_lora.py:813 main(), :815 resolve_cli_params(distilled=True)
    "ltx_a2v": "ltx_pipelines.a2vid_two_stage",   # a2vid_two_stage.py:596 main(), :599 build_a2vid_arg_parser
}
QWEN = "qwen_mva"


def load_p12b():
    spec = importlib.util.spec_from_file_location("p12b_job", HERE / "p12b.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ltx_file(cfg, part):
    """The local path of the LTX file whose repo path contains ``part`` (files, av_files or the Layout LoRA)."""
    lt = cfg["ltx"]
    names = list(lt["files"]) + list(lt["av_files"]) + [lt["layout_lora"]["file"]]
    return MODELS / lt["local"] / next(f for f in names if part in f)


def _flag(cmd, key, *vals):
    f = FLAGS[key]
    if f is not None:
        cmd += [f, *[str(v) for v in vals]]


def _common(cfg, paths, frames=True):
    r = cfg["ltx"]["render"]
    cmd = []
    _flag(cmd, "image", paths["image"], 0, 1.0)
    _flag(cmd, "prompt", paths["prompt"])
    _flag(cmd, "width", r["width"])
    _flag(cmd, "height", r["height"])
    if frames:
        _flag(cmd, "num_frames", r["frames"])
    _flag(cmd, "frame_rate", r["fps"])
    _flag(cmd, "seed", r["seed"])
    _flag(cmd, "text_encoder", ltx_file(cfg, "text_encoders/"))
    _flag(cmd, "video_vae", ltx_file(cfg, "video-vae"))
    _flag(cmd, "audio_vae", ltx_file(cfg, "audio-vae"))
    _flag(cmd, "upsampler", ltx_file(cfg, "latent_upscale_models/"))
    _flag(cmd, "fp8")
    _flag(cmd, "output", paths["out"])
    return cmd


def cmd_ltx_i2v(cfg, shot, paths):
    """L1/L3: the distilled two-stage pipeline (distilled.py:161 DistilledPipeline); --num-frames is always given, so the
    DurationHead (distilled.py:237, absent before LTX-2.5) is never asked for a length."""
    cmd = [sys.executable, "-m", MODULES["ltx_i2v"]]
    _flag(cmd, "transformer", ltx_file(cfg, "distilled-transformer"))
    return cmd + _common(cfg, paths)


def cmd_ltx_ic(cfg, shot, paths):
    cmd = [sys.executable, "-m", MODULES["ltx_ic"]]
    _flag(cmd, "transformer", ltx_file(cfg, "distilled-transformer"))
    _flag(cmd, "video_cond", paths["clay"], 1.0)
    _flag(cmd, "lora", ltx_file(cfg, cfg["ltx"]["layout_lora"]["file"]))
    _flag(cmd, "stage2_ic")
    return cmd + _common(cfg, paths)


def cmd_ltx_a2v(cfg, shot, paths):
    cmd = [sys.executable, "-m", MODULES["ltx_a2v"]]
    _flag(cmd, "transformer", ltx_file(cfg, "dev-transformer"))
    _flag(cmd, "distilled_lora", ltx_file(cfg, "distilled-lora"))
    _flag(cmd, "audio", paths["wav"])
    _flag(cmd, "audio_max", paths["seconds"])
    return cmd + _common(cfg, paths, frames=False)        # --audio-max-duration excludes --num-frames (plan 3.4b)


CMDS = {"ltx_i2v": cmd_ltx_i2v, "ltx_ic": cmd_ltx_ic, "ltx_a2v": cmd_ltx_a2v}


def out_path(out, kind, shot):
    if kind == "ltx_a2v":
        return Path(out) / "av" / f"{shot}.mp4"
    return Path(out) / "ltx" / f"{shot}_{'layout' if kind == 'ltx_ic' else 'i2v'}.mp4"


def header_ok(p):
    """A safetensors file: 8 bytes of header length, then that much JSON, then data (sha256 of 42 GB is too slow on the pod)."""
    try:
        with open(p, "rb") as f:
            n = int.from_bytes(f.read(8), "little")
            if not 0 < n < 1 << 28:
                return False
            json.loads(f.read(n))
        return Path(p).stat().st_size > 8 + n
    except (OSError, ValueError):
        return False


def verify_weights(cfg, names):
    """The files of ``names`` that are missing, of the wrong size (where p12b.json gives one) or not a safetensors file."""
    lt, bad = cfg["ltx"], []
    sizes = lt.get("sizes", {})
    for f in names:
        p = MODELS / lt["local"] / f
        if not p.is_file() or (f in sizes and p.stat().st_size != sizes[f]) or not header_ok(p):
            bad.append(f)
    return bad


def fetch(repo, path, local):
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download(repo, path, repo_type="dataset", local_dir=str(local)))


def fit_frame(src, dst, w, h):
    """Centre-crop to w:h (2560 x 1408 -> 1.765:1), then resize to w x h."""
    from PIL import Image
    img = Image.open(src).convert("RGB")
    iw, ih = img.size
    if iw * h > ih * w:
        cw = round(ih * w / h)
        box = ((iw - cw) // 2, 0, (iw - cw) // 2 + cw, ih)
    else:
        ch = round(iw * h / w)
        box = (0, (ih - ch) // 2, iw, (ih - ch) // 2 + ch)
    img.crop(box).resize((w, h), Image.LANCZOS).save(dst)


def on_canvas(src, dst, w, h):
    """The Q1 picture scaled to the canvas height, centred on a white w x h canvas (AV2)."""
    from PIL import Image
    img = Image.open(src).convert("RGB")
    img = img.resize((round(img.width * h / img.height), h), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(img, ((w - img.width) // 2, 0))
    canvas.save(dst)


def prepare_inputs(cfg, out, log):
    """Per shot: the first-frame picture, its sha256, the prompt; for L2 the clay video and for AV the take, each sha256-checked
    against p12b.json. A failed input leaves the key out (the shot then ends ``failed ... (no input)``)."""
    lt, r = cfg["ltx"], cfg["ltx"]["render"]
    kf, work, inputs = lt["keyframes"], MODELS / "p12c", {}
    (work / "in").mkdir(parents=True, exist_ok=True)

    def keyframe(shot):
        dst = work / "in" / f"{shot}.png"
        if not dst.exists():
            fit_frame(fetch(kf["repo"], kf["paths"][shot], work / "kf"), dst, r["width"], r["height"])
        return dst

    def checked(repo, path, want, what):
        p = fetch(repo, path, work / what)
        got = sha256_file(p)
        if got != want:
            log.ev("sha256_mismatch", name=path, expected=want, got=got)
            return None, None
        return p, got

    shots = sorted({s for n, st in cfg["stages"].items() if st.get("kind", QWEN) in ("ltx_i2v", "ltx_ic") for s in st["shots"]})
    for shot in shots:
        try:
            img = keyframe(shot)
            inputs[shot] = {"image": img, "keyframe_sha256": sha256_file(img), "prompt": lt["prompts"].get(shot),
                            "clay": None, "clay_sha256": None, "wav": None, "take_sha256": None, "voice_id": None}
        except Exception as e:   # noqa: BLE001
            log.ev("input_failed", shot=shot, what="keyframe", error=str(e)[:300])
    clay = lt["clay"]
    for shot, want in clay["sha256"].items():
        if shot in inputs:
            try:
                inputs[shot]["clay"], inputs[shot]["clay_sha256"] = checked(clay["repo"], f"{clay['dir']}/{shot}.mp4", want, "clay")
            except Exception as e:   # noqa: BLE001
                log.ev("input_failed", shot=shot, what="clay", error=str(e)[:300])
    av = lt["av"]
    for name, take in av["takes"].items():
        try:
            spec = av["images"][name]
            if spec.startswith("keyframe:"):
                img = keyframe(spec.split(":", 1)[1])
            else:
                img = work / "in" / f"{name}.png"
                on_canvas((Path(out) / "qwen_done.txt").read_text(encoding="utf-8").strip(), img, r["width"], r["height"])
            wav, sha = checked(av["repo"], take["path"], take["sha256"], "audio")
            inputs[name] = {"image": img, "keyframe_sha256": sha256_file(img), "prompt": lt["prompts"].get(name), "clay": None,
                            "clay_sha256": None, "wav": wav, "take_sha256": sha, "voice_id": take["voice_id"],
                            "seconds": take["seconds"]}
        except Exception as e:   # noqa: BLE001
            log.ev("input_failed", shot=name, what="take", error=str(e)[:300])
    return inputs


def run_cmd(cmd, timeout, log, label):
    """One clip; progress.txt is rewritten every minute while it runs (the stall rule watches it)."""
    stop = threading.Event()

    def tick():
        t0 = time.time()
        while not stop.wait(60):
            log.progress(f"{label} {int(time.time() - t0)} s")

    threading.Thread(target=tick, daemon=True).start()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(CODE_DIR) if CODE_DIR.is_dir() else None)
        return p.returncode, (p.stderr or "")[-2000:]
    except subprocess.TimeoutExpired as e:
        return "timeout", str(e.stderr or "")[-2000:]
    except OSError as e:
        return "oserror", str(e)[-2000:]
    finally:
        stop.set()


def audio_matches(mp4, take_sha):
    """Plan 3.4b pass criterion 1 as written: the sha256 of the clip's audio track as WAV equals the take's (None when ffmpeg fails). It
    holds only when the audio is copied untouched; ``audio_corr`` is the check that survives a re-encode."""
    try:
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vn", "-f", "wav", "-"], capture_output=True, timeout=300)
        return hashlib.sha256(p.stdout).hexdigest() == take_sha if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _pcm(path, rate=16000):
    """Mono 16 kHz float samples of any file's first audio track through ffmpeg (None when ffmpeg fails)."""
    import numpy as np
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                       capture_output=True, timeout=300)
    if p.returncode != 0 or not p.stdout:
        return None
    return np.frombuffer(p.stdout, dtype=np.int16).astype("float32") / 32768.0


def audio_corr(mp4, wav, max_lag_s=0.25, rate=16000):
    """How alike the clip's audio and the take are: the best normalised correlation over lags of +-``max_lag_s`` of both decoded to mono
    16 kHz PCM, plus the two lengths. The clip's audio is re-encoded (a container sha256 can never match, audit 2026-11-01 #17), so the
    comparison is on the samples. Returns {"corr", "lag_s", "clip_s", "take_s"} or None; no threshold is applied here (the creator's call)."""
    try:
        import numpy as np
        a, b = _pcm(mp4, rate), _pcm(wav, rate)
        if a is None or b is None:
            return None
        n = min(len(a), len(b))
        if n < rate // 10:
            return None
        m, best = int(max_lag_s * rate), (-2.0, 0)
        for lag in range(-m, m + 1, max(1, rate // 200)):                  # 5 ms steps
            x, y = (a[lag:n], b[:n - lag]) if lag >= 0 else (a[:n + lag], b[-lag:n])
            d = float(np.linalg.norm(x) * np.linalg.norm(y))
            c = float(np.dot(x, y) / d) if d else 0.0
            if c > best[0]:
                best = (c, lag)
        return {"corr": round(best[0], 4), "lag_s": round(best[1] / rate, 3), "clip_s": round(len(a) / rate, 2), "take_s": round(len(b) / rate, 2)}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def run_stage(name, st, cfg, out, log, inputs, first_unit_s):
    kind, r = st["kind"], cfg["ltx"]["render"]
    timeout = cfg["stall_minutes"] * 60 - 60
    res = {"ok": 0, "failed": 0, "oom": False}
    for i, shot in enumerate(st["shots"], 1):
        inp = inputs.get(shot)
        if (not inp or not inp.get("prompt") or (kind == "ltx_ic" and not inp.get("clay"))
                or (kind == "ltx_a2v" and not inp.get("wav"))):
            log.stage_line(f"failed {name}/{shot} (no input)")
            res["failed"] += 1
            continue
        mp4 = out_path(out, kind, shot)
        mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd = CMDS[kind](cfg, shot, {**inp, "out": mp4})
        t = time.time()
        rc, err = run_cmd(cmd, timeout, log, f"{name} {i}/{len(st['shots'])} {shot}")
        secs = round(time.time() - t, 1)
        oom = "CUDA out of memory" in err
        side = {"stage": name, "shot": shot, "kind": kind, "seed": r["seed"], "width": r["width"], "height": r["height"],
                # AV is driven by the take's length (--audio-max-duration, no --num-frames; the pipeline's own steps): never log L1's numbers for it
                "frames": None if kind == "ltx_a2v" else r["frames"], "fps": r["fps"],
                "steps": None if kind == "ltx_a2v" else {"stage1": r["stage1"]["steps"], "stage2": r["stage2_steps"]},
                "audio_max_s": inp.get("seconds") if kind == "ltx_a2v" else None,
                "cmd": [str(c) for c in cmd], "seconds": secs, "rc": rc, "oom": oom,
                "stderr_tail": err if rc != 0 else "",
                "inputs": {k: inp.get(k) for k in ("keyframe_sha256", "clay_sha256", "take_sha256", "voice_id")},
                "model_files": [str(c) for c in cmd if str(c).endswith(".safetensors")]}
        if rc == 0 and kind == "ltx_a2v":
            side["audio_sha_match"] = audio_matches(mp4, inp["take_sha256"])    # only true when the clip carries the take's samples untouched
            side["audio_corr"] = audio_corr(mp4, inp["wav"])                    # the evidence that counts: samples, not container bytes
        if rc == 0 and kind == "ltx_ic":
            (Path(out) / "ltx" / "clay").mkdir(parents=True, exist_ok=True)
            shutil.copy(inp["clay"], Path(out) / "ltx" / "clay" / f"{shot}.mp4")
        mp4.with_suffix(".json").write_text(json.dumps(side, indent=1), encoding="utf-8")
        if i == 1:
            first_unit_s[name] = secs
            log.ev("first_unit", stage=name, seconds=secs)
        if rc == 0:
            res["ok"] += 1
        else:
            res["failed"] += 1
            log.stage_line(f"failed {name}/{shot} rc={rc}")
        res["oom"] = res["oom"] or oom
        if oom and kind == "ltx_a2v":
            log.stage_line(f"failed {name} (oom)")
            break
    return res


def ltx_may_start(p12b, name, cfg, first_unit_s, done, now, deadline):
    """Section 3.5 for the LTX stages: L3 uses L1's first clip; an essential LTX stage not measured yet counts with its share of
    ``ltx.reserve_parts_min`` (plan numbers, not measured)."""
    stages = cfg["stages"]
    if stages[name]["essential"]:
        return True
    first = dict(first_unit_s)
    if name == "L3" and "L3" not in first and "L1" in first:
        first["L3"] = first["L1"]
    parts, rest = cfg["ltx"]["reserve_parts_min"], 0.0
    for other in p12b.ordered(stages):
        so = stages[other]
        if p12b.kind_of(so) == QWEN or other == name or other in done or not so["essential"]:
            continue
        e = p12b.estimate_s(other, stages, first)
        rest += e if e is not None else float(parts.get(other, 0)) * 60
    return p12b.stage_may_start(name, {name: stages[name]}, first, done, now, deadline, cfg["end_reserve_min"] * 60,
                                extra_reserve_s=rest)


def run(cfg, out, deadline, log, p12b):
    lt = cfg["ltx"]
    missing = verify_weights(cfg, lt["files"])
    if missing:
        log.ev("ltx_weights_missing", files=missing)
        log.stage_line("skipped L1 L2 L3 AV (weights missing)")
        return 0
    log.stage_line("ltx_weights ok")
    no_layout = verify_weights(cfg, [lt["layout_lora"]["file"]])
    no_av = verify_weights(cfg, lt["av_files"])
    inputs = prepare_inputs(cfg, out, log)
    stages, first, done = cfg["stages"], {}, set()
    for name in [n for n in p12b.ordered(stages) if p12b.kind_of(stages[n]) != QWEN]:
        st, kind = stages[name], stages[name]["kind"]
        why = None
        if not MODULES.get(kind):
            why = "module unverified"
        elif kind == "ltx_ic" and no_layout:
            why = "no layout lora"
        elif kind == "ltx_ic" and not any(inputs.get(s, {}).get("clay") for s in st["shots"]):
            why = "no clay"
        elif kind == "ltx_a2v" and no_av:
            why = "weights missing"
        elif kind == "ltx_a2v" and not any(inputs.get(s, {}).get("wav") for s in st["shots"]):
            why = "no take"
        elif not ltx_may_start(p12b, name, cfg, first, done, time.time(), deadline):
            why = "projection"
        if why:
            log.stage_line(f"skipped {name} ({why})")
            log.ev("stage_skipped", stage=name, reason=why)
            continue
        log.stage_line(f"start {name}")
        res = run_stage(name, st, cfg, out, log, inputs, first)
        done.add(name)
        if kind == "ltx_a2v" and res["oom"]:
            return 0
        log.stage_line(f"done {name}" if res["ok"] else f"failed {name}")
        if p12b.stop_here(cfg, log, out, name):
            return 0
    log.progress("done")
    return 0


def main():
    cfg = json.loads((HERE / CFG_NAME).read_text(encoding="utf-8"))
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    if (out / "control" / "stopped_after.txt").exists():
        return 0
    deadline = float(os.environ["EE_DEADLINE"])
    p12b = load_p12b()
    log = p12b.Log(out)
    rc = 0
    try:
        rc = run(cfg, out, deadline, log, p12b)
    finally:
        log.ev("ltx_exit", rc=rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
