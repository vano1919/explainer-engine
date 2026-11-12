"""The v4.3 video bake-off (the creator, 2026-11-12 15:01 UTC): one 10 s dialogue shot and one 10 s action shot from the approved
style pictures, made by every video model we can run on Modal, so price and quality are measured side by side before the
episode's model is chosen. The plan is data: ``plan_v43.json`` (shots, pinned weights with every file's sha256, the variants the creator chose
with their settings, GPU, estimate and cap).

    EE_MODAL_GO=<cmsg_id>:<plan sha256[:12]> modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::stage
    EE_MODAL_GO=... modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::run --variant <id>
    modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::check            # CPU only: the two images import

* ``stage`` (CPU): every pinned file still missing on the Volume ``ee-weights`` is downloaded at its pinned revision, every
  sha256 is checked, the Volume is committed. ``run`` never downloads weights.
* ``run --variant X`` (one GPU container): loads X once, makes both shots, writes each finished clip and its ``measured.json``
  (container seconds per step) to HF ``<hf_out>/<run id>/<variant>/`` and to the Volume as they are made (OR-33).
* Every function's timeout comes from its cap (``cost_timeout``, OR-37), retries 0, nothing stays warm. A variant that fails is
  recorded as failed with its log; the others are not touched.
* The 2K upscale, the quality measurements and the report are free and local: ``training/pods/bakeoff/report.py``.

Wan makes 5 s at most per clip, so a 10 s Wan shot is two clips: the second starts from the first clip's frame[-5] and the
join keeps the first clip up to that frame and drops its last five (D-125 WAN-CHAIN-MINUS-5,
``wan_optimizer.compute_continuation_splice_spec``: the anchor frame is shown once, as the second clip's frame 0). LTX makes the 10 s (241 frames at 24 fps) in one clip,
with its own sound."""
import hashlib, json, os, re, subprocess, threading, time
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

PLAN_PATH = Path(__file__).with_name("plan_v43.json")
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
DIFFUSERS = "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d"
LTX2 = ("https://github.com/Lightricks/LTX-2.git", "e98f6d927d83c92ef2be6aec76c8440b19306e39")
PIP = {"huggingface_hub": "1.33.0", "transformers": "5.21.0", "accelerate": "1.15.0", "peft": "0.21.2"}
SECRET_NAME = "huggingface-secret"
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
FAILED = "BAKEOFF_FAILED"
OUT_ROOT = Path("/workspace/out")
H = re.compile(r"^[0-9a-f]{64}$")
# Modal list prices (modal.com/pricing, read 2026-11-12; equal to cloud/modal_schedule.py of 2026-11-07, held by a test)
USD_S = {"H100": 0.001097, "A100-80GB": 0.000694, "L40S": 0.000542}
CPU_CORE_S, MEM_GIB_S = 0.0000131, 0.00000222


def load_plan(path=PLAN_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plan_sha(path=PLAN_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def usd_per_h(gpu, cpu, memory_gib) -> float:
    return round(((USD_S[gpu] if gpu else 0.0) + cpu * CPU_CORE_S + memory_gib * MEM_GIB_S) * 3600.0, 4)


def cost_timeout(cap_usd, usd_h, cold_start_s):
    """OR-37: floor(0.9 * (cap - the cold start's cost) / price per hour * 3600); never set by hand."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600.0) / usd_h * 3600.0)


def variant(plan, vid) -> dict:
    for v in plan["variants"]:
        if v["id"] == vid:
            return v
    raise SystemExit(f"no variant {vid!r} in the plan; nothing was started")


def timeout_of(plan, v) -> int:
    t = cost_timeout(v["cap_usd"], usd_per_h(v["gpu"], v["cpu"], v["memory_gib"]), plan["cold_start_s"])
    if t <= 60:
        raise SystemExit(f"{v['id']}: the cap ${v['cap_usd']} does not cover the cold start; nothing was started")
    return t


def stage_timeout(plan) -> int:
    s = plan["stage"]
    return min(int(s["timeout_s"]), cost_timeout(s["cap_usd"], usd_per_h(None, s["cpu"], s["memory_gib"]), 0))


def frames_ok(v) -> bool:
    """LTX takes 8k+1 frames and sizes divisible by 64 (two stages at half size); Wan 4k+1 frames and sizes divisible by 16."""
    f, w, h = v["frames"], v["width"], v["height"]
    if v["family"] == "ltx":
        return (f - 1) % 8 == 0 and w % 64 == 0 and h % 64 == 0
    return (f - 1) % 4 == 0 and w % 16 == 0 and h % 16 == 0


def chained_frames(v) -> int:
    """Frames of the joined shot: every clip but the last without its last ``chain_back`` frames, then the last clip whole."""
    n, back = v["frames"], v.get("chain_back", 5)
    return n * v["clips"] - back * (v["clips"] - 1)


def shot_seconds(v) -> float:
    return chained_frames(v) / v["fps"]


def plan_problems(plan) -> list:
    """Everything that keeps the plan from a paid call: pins, sizes, lengths, caps, the total under its cap."""
    out = []
    for wid, w in plan["weights"].items():
        if not re.match(r"^[0-9a-f]{40}$", str(w.get("revision") or "")):
            out.append(f"weights {wid}: no pinned revision")
        out += [f"weights {wid}: {f} has no sha256" for f, h in (w.get("files") or {}).items() if not H.match(str(h))]
        if not w.get("files"):
            out.append(f"weights {wid}: no files")
    for s in plan["shots"]:
        if not H.match(str(s.get("sha256") or "")):
            out.append(f"shot {s['id']}: the picture has no sha256")
        if not str(s.get("prompt") or "").strip():
            out.append(f"shot {s['id']}: no prompt")
    ids = [v["id"] for v in plan["variants"]]
    if len(set(ids)) != len(ids):
        out.append("two variants share an id")
    for v in plan["variants"]:
        if v["family"] not in ("ltx", "wan"):
            out.append(f"{v['id']}: family must be ltx or wan")
        if not frames_ok(v):
            out.append(f"{v['id']}: frames/size do not fit the model's grid")
        miss = [w for w in v["weights"] if w not in plan["weights"]]
        if miss:
            out.append(f"{v['id']}: unknown weights {miss}")
        for k, f in (v.get("uses") or {}).items():
            if not any(f in plan["weights"][w]["files"] for w in v["weights"] if w in plan["weights"]):
                out.append(f"{v['id']}: {k} {f} is not a pinned file")
        for k, f in (v.get("lora") or {}).items():
            if not any(f in plan["weights"][w]["files"] for w in v["weights"] if w in plan["weights"]):
                out.append(f"{v['id']}: LoRA {f} is not a pinned file")
        if not 9.5 <= shot_seconds(v) <= 10.5:
            out.append(f"{v['id']}: the shot is {shot_seconds(v):.2f} s, not 10 s")
        if v.get("gpu") not in USD_S:
            out.append(f"{v['id']}: unknown GPU {v.get('gpu')}")
        elif not (0 < v["estimate_usd"] <= v["cap_usd"]):
            out.append(f"{v['id']}: the estimate must be above 0 and under the cap")
        else:
            try:
                timeout_of(plan, v)
            except SystemExit as exc:
                out.append(str(exc))
    total = sum(v["cap_usd"] for v in plan["variants"]) + plan["stage"]["cap_usd"]
    if total > plan["total_cap_usd"] + 1e-9:
        out.append(f"the caps add up to ${total:g}, past the plan's total ${plan['total_cap_usd']:g}")
    return out


def run_id(plan_sha_hex: str, worker_sha: str) -> str:
    return f"{plan_sha_hex[:12]}_{worker_sha[:12]}"


def worker_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def go_gate(env=os.environ, sha=None):
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of this plan file>``: his yes binds this plan's bytes."""
    m = GO.match(str(env.get("EE_MODAL_GO") or ""))
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the creator's message id>:<the plan's sha256[:12]>'; nothing was started")
    if sha is not None and m.group(2) != sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than plan_v43.json as it is now; nothing was started")
    return m.group(1)


def preflight(plan, env=os.environ, spend_line=None) -> None:
    """Free, local, before any call: the plan holds; each cap stays under the creator's per-run Modal line."""
    bad = plan_problems(plan)
    if spend_line is None:
        try:
            from explainer_engine.core import spend_caps
            spend_line = float(spend_caps.modal()["per_run_usd"])
        except Exception as exc:  # noqa: BLE001 - no line = a zero budget
            bad.append(f"no Modal line in config/spend_caps.json ({type(exc).__name__}: {exc})")
    if spend_line is not None:
        bad += [f"{v['id']}: cap ${v['cap_usd']:g} is above the creator's ${spend_line:g} per run" for v in plan["variants"]
                if v["cap_usd"] > spend_line + 1e-9]
    if bad:
        raise SystemExit("bake-off preflight FAILED, nothing was started:\n" + "\n".join(bad))


# --- pictures and frames (container and tests) ---------------------------------------------------------------------------------

def fit_picture(img, width, height):
    """Centre-crop to the clip's aspect, then Lanczos to its size (a PIL image in, a PIL image out)."""
    from PIL import Image
    w, h = img.size
    if w * height > h * width:
        cw, ch = round(h * width / height), h
    else:
        cw, ch = w, round(w * height / width)
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.convert("RGB").crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


def join_clips(clips, back=5):
    """Chained clips into one shot: the next clip starts from frame[-back] of the one before, so every clip but the last loses
    its last ``back`` frames (that frame included; it comes back as the next clip's frame 0, never shown twice)."""
    out = []
    for i, c in enumerate(clips):
        out += list(c[:len(c) - back]) if i < len(clips) - 1 else list(c)
    return out


# --- in the container --------------------------------------------------------------------------------------------------------

def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def weights_root(w, vol_root="/w"):
    return Path(vol_root) / "model" / w["repo"]


def check_weights(w, vol_root="/w"):
    root, bad = weights_root(w, vol_root), []
    for f, want in w["files"].items():
        p = root / f
        if not p.is_file():
            bad.append(f"missing {w['repo']}/{f}")
        elif _sha(p) != want:
            bad.append(f"sha256 mismatch {w['repo']}/{f}")
    return bad


def stage_weights(plan, vol_root="/w", download=None):
    """Every pinned file still missing on the Volume, at its pinned revision, then every sha256."""
    bad = []
    for w in plan["weights"].values():
        root = weights_root(w, vol_root)
        miss = [f for f in w["files"] if not (root / f).is_file()]
        if miss:
            (download or _hf_download)(w["repo"], w["revision"], miss, root)
        bad += check_weights(w, vol_root)
    return bad


def _hf_download(repo, revision, files, root):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), local_dir=str(root), token=_tok())


def beat(out, **kw):
    (Path(out) / "beat.json").write_text(json.dumps(dict(kw, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))))


def _uploader(out, hf_prefix, stop, repo, interval=30.0):
    """Every new or changed file of ``out`` to HF as it appears (OR-33); the beat too, so a watchdog sees progress."""
    from huggingface_hub import HfApi
    api, seen = HfApi(token=_tok()), {}
    while True:
        last = stop.is_set()
        for p in sorted(Path(out).rglob("*")):
            if not p.is_file():
                continue
            st = p.stat()
            key = (st.st_size, st.st_mtime_ns)
            if seen.get(p) == key:
                continue
            try:
                api.upload_file(path_or_fileobj=str(p), path_in_repo=f"{hf_prefix}/{p.relative_to(out).as_posix()}", repo_id=repo,
                                repo_type="dataset", commit_message=f"bakeoff {p.name}")
                seen[p] = key
            except Exception as e:  # noqa: BLE001 - try again next round
                print("upload failed", p.name, repr(e)[:160], flush=True)
        if last:
            return
        stop.wait(interval)


def _picture(plan, shot, root="/tmp/in"):
    from huggingface_hub import hf_hub_download
    p = hf_hub_download(plan["hf_repo"], shot["picture"], repo_type="dataset", local_dir=root, token=_tok())
    if _sha(p) != shot["sha256"]:
        raise SystemExit(f"{shot['id']}: the picture's sha256 is not the plan's")
    return p


def make_wan(plan, v, out, start_pictures, beat_fn=beat):
    """One Wan variant, both shots: the pipeline loaded once from the Volume; a shot is ``clips`` clips chained on frame[-5]."""
    import numpy as np
    import torch
    import diffusers
    from diffusers.utils import export_to_video
    from PIL import Image
    t0 = time.time()
    beat_fn(out, stage="load", variant=v["id"])
    base = plan["weights"][v["weights"][0]]
    kw = {}
    if v.get("vae_fp32"):
        kw["vae"] = diffusers.AutoencoderKLWan.from_pretrained(str(weights_root(base) / "vae"), torch_dtype=torch.float32)
    pipe = getattr(diffusers, v["pipeline"]).from_pretrained(str(weights_root(base)), torch_dtype=torch.bfloat16, **kw)
    if v.get("lora"):
        lw = plan["weights"][v["weights"][1]]
        names = []
        for target, f in v["lora"].items():
            name = f"lightning_{target}"
            pipe.load_lora_weights(str(weights_root(lw) / f), adapter_name=name,
                                   **({"load_into_transformer_2": True} if target == "transformer_2" else {}))
            names.append(name)
        pipe.set_adapters(names, adapter_weights=[1.0] * len(names))
    if v.get("offload") == "model_cpu_offload":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")
    setup_s = time.time() - t0
    settings = {k: x for k, x in v["settings"].items() if k != "source"}
    rows = []
    for shot in plan["shots"]:
        t1, clips = time.time(), []
        start = fit_picture(Image.open(start_pictures[shot["id"]]), v["width"], v["height"])
        for c in range(v["clips"]):
            def _step(p, i, t, cbk, _c=c):
                beat_fn(out, stage="generate", variant=v["id"], shot=shot["id"], clip=_c + 1, step=int(i) + 1)
                return cbk
            res = pipe(image=start, prompt=shot["prompt"], height=v["height"], width=v["width"], num_frames=v["frames"],
                       generator=torch.Generator("cuda").manual_seed(int(shot["seed"]) + c), callback_on_step_end=_step,
                       output_type="np", **settings)
            frames = res.frames[0]
            clips.append(frames)
            start = Image.fromarray((np.clip(frames[-v.get("chain_back", 5)], 0, 1) * 255).astype("uint8"))
        joined = join_clips(clips, v.get("chain_back", 5))
        mp4 = Path(out) / f"{shot['id']}.mp4"
        export_to_video(joined, str(mp4), fps=v["fps"])
        rows.append({"shot": shot["id"], "gen_s": round(time.time() - t1, 1), "frames": len(joined), "fps": v["fps"],
                     "sha256": _sha(mp4)})
        (Path(out) / f"{shot['id']}.measured.json").write_text(json.dumps(rows[-1]))
    return {"setup_s": round(setup_s, 1), "shots": rows}


def ltx_cmd(plan, v, shot, picture, mp4):
    """The LTX-2 CLI of one shot (ltx_pipelines.distilled or .ti2vid_two_stages): split weights from the Volume, the start
    picture at frame 0, every other setting the CLI's own LTX-2.5 default."""
    w = plan["weights"]["ltx25"]
    root = weights_root(w)
    f = lambda part: str(root / next(x for x in w["files"] if part in x))  # noqa: E731
    cmd = ["python3", "-m", v["module"], "--transformer-path", str(root / v["uses"]["transformer"]),
           "--text-encoder-path", f("text_encoders/"), "--video-vae-path", f("video-vae"), "--audio-vae-path", f("audio-vae"),
           "--spatial-upsampler-path", f("spatial-upscaler")]
    if v["uses"].get("distilled_lora"):
        cmd += ["--distilled-lora", str(root / v["uses"]["distilled_lora"])]
    prompt = shot["prompt"] + (" " + shot["audio_prompt"] if shot.get("audio_prompt") else "")
    cmd += ["--image", str(picture), "0", "1.0", "--prompt", prompt, "--width", str(v["width"]), "--height", str(v["height"]),
            "--num-frames", str(v["frames"]), "--frame-rate", str(v["fps"]), "--seed", str(shot["seed"]), "--output-path", str(mp4)]
    return cmd


def make_ltx(plan, v, out, start_pictures, beat_fn=beat, sh=subprocess.run):
    from PIL import Image
    rows = []
    for shot in plan["shots"]:
        t1 = time.time()
        beat_fn(out, stage="generate", variant=v["id"], shot=shot["id"])
        pic = Path("/tmp/in") / f"{shot['id']}_{v['width']}x{v['height']}.png"
        fit_picture(Image.open(start_pictures[shot["id"]]), v["width"], v["height"]).save(pic)
        mp4 = Path(out) / f"{shot['id']}.mp4"
        with open(Path(out) / f"{shot['id']}.log", "w") as log:
            rc = sh(ltx_cmd(plan, v, shot, pic, mp4), stdout=log, stderr=subprocess.STDOUT, cwd="/workspace/LTX-2").returncode
        row = {"shot": shot["id"], "gen_s": round(time.time() - t1, 1), "rc": rc, "fps": v["fps"], "frames": v["frames"]}
        if rc == 0 and mp4.is_file():
            row["sha256"] = _sha(mp4)
        rows.append(row)
        (Path(out) / f"{shot['id']}.measured.json").write_text(json.dumps(row))
    return {"setup_s": None, "shots": rows}


def body(plan, vid, rid, timeout_s):
    t_in = time.time()
    v = variant(plan, vid)
    out = OUT_ROOT / rid / vid
    out.mkdir(parents=True, exist_ok=True)
    beat(out, stage="start", variant=vid)
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(OUT_ROOT / rid, f"{plan['hf_out']}/{rid}", stop, plan["hf_repo"]), daemon=True)
    th.start()

    def _fire():
        (out / "TIMEOUT.txt").write_text("the in-container deadline fired\n")
        stop.set()
        th.join(timeout=60)
        os._exit(3)
    timer = threading.Timer(max(30, timeout_s - 90), _fire)
    timer.daemon = True
    timer.start()
    state, err, res = "DONE", None, {}
    try:
        bad = [b for w in v["weights"] for b in check_weights(plan["weights"][w])]
        if bad:
            raise SystemExit("weights not staged: " + "; ".join(bad[:5]))
        pics = {s["id"]: _picture(plan, s) for s in plan["shots"]}
        res = (make_ltx if v["family"] == "ltx" else make_wan)(plan, v, out, pics)
        if any(r.get("rc", 0) != 0 or not r.get("sha256") for r in res["shots"]):
            state = "FAILED"
    except BaseException as e:  # noqa: BLE001 - recorded, then the run ends
        state, err = "FAILED", f"{type(e).__name__}: {str(e)[:400]}"
    finally:
        timer.cancel()
    m = dict(res, state=state, error=err, variant=vid, run_id=rid, body_s=round(time.time() - t_in, 1), gpu=v["gpu"],
             usd_per_h=usd_per_h(v["gpu"], v["cpu"], v["memory_gib"]), worker_sha=worker_sha())
    (out / "measured.json").write_text(json.dumps(m, indent=1))
    beat(out, stage="end", variant=vid, state=state)
    stop.set()
    th.join(timeout=600)
    try:
        import shutil
        shutil.copytree(OUT_ROOT / rid, f"/w/out_bakeoff/{rid}", dirs_exist_ok=True)
        vol.commit()
    except Exception as e:  # noqa: BLE001
        print("volume copy failed", repr(e)[:200], flush=True)
    return m


PLAN = load_plan()

if modal is not None:
    app = modal.App(PLAN["app_name"])
    vol = modal.Volume.from_name(PLAN["volume"], version=2)
    secrets = [modal.Secret.from_name(SECRET_NAME)]
    pins = " ".join(f'"{k}=={x}"' for k, x in PIP.items())
    wan_image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12").apt_install("ffmpeg")
                 .run_commands(f'pip install -q "{DIFFUSERS}" {pins} ftfy "imageio[ffmpeg]"')
                 .add_local_file(str(PLAN_PATH), "/root/plan_v43.json"))
    ltx_image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12").apt_install("ffmpeg", "git")
                 .run_commands(f'pip install -q "huggingface_hub=={PIP["huggingface_hub"]}"',
                               f"git clone -q {LTX2[0]} /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q {LTX2[1]} && "
                               "pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines")
                 .add_local_file(str(PLAN_PATH), "/root/plan_v43.json"))
    kw = dict(retries=0, volumes={"/w": vol}, secrets=secrets, scaledown_window=2)

    @app.function(image=wan_image, cpu=2, memory=4096, timeout=300, retries=0, secrets=secrets)
    def wan_env():
        import importlib
        bad = [m for m in ("torch", "diffusers", "transformers", "peft", "PIL", "imageio") if importlib.util.find_spec(m) is None]
        import diffusers
        bad += [p for p in ("WanImageToVideoPipeline", "AutoencoderKLWan") if not hasattr(diffusers, p)]
        return bad

    @app.function(image=ltx_image, cpu=2, memory=4096, timeout=300, retries=0, secrets=secrets)
    def ltx_env():
        import importlib
        return [m for m in ("torch", "ltx_core", "ltx_pipelines.distilled", "ltx_pipelines.ti2vid_two_stages", "PIL")
                if importlib.util.find_spec(m) is None]

    @app.function(image=wan_image, cpu=PLAN["stage"]["cpu"], memory=PLAN["stage"]["memory_gib"] * 1024,
                  timeout=stage_timeout(PLAN), **kw)
    def stage_fn():
        bad = stage_weights(PLAN)
        vol.commit()
        return bad

    GPU_FNS = {}
    for _v in PLAN["variants"]:
        _img = ltx_image if _v["family"] == "ltx" else wan_image

        def _make(vid):
            def run_variant(rid: str):
                return body(PLAN, vid, rid, timeout_of(PLAN, variant(PLAN, vid)))
            run_variant.__name__ = f"run_{vid}"
            return run_variant
        GPU_FNS[_v["id"]] = app.function(image=_img, gpu=_v["gpu"], cpu=_v["cpu"], memory=_v["memory_gib"] * 1024,
                                         timeout=timeout_of(PLAN, _v), name=f"run_{_v['id']}", serialized=True, **kw)(_make(_v["id"]))

    @app.local_entrypoint()
    def check():
        print("wan image", wan_env.remote() or "imports ok")
        print("ltx image", ltx_env.remote() or "imports ok")

    @app.local_entrypoint()
    def stage():
        preflight(PLAN)
        print("GO card", go_gate(sha=plan_sha()), "stage timeout", stage_timeout(PLAN), "s", flush=True)
        bad = stage_fn.remote()
        print("stage", bad or "every pinned file on the Volume, sha256 match")
        if bad:
            raise SystemExit(4)

    @app.local_entrypoint()
    def run(variant: str = ""):
        preflight(PLAN)
        sha = plan_sha()
        print("GO card", go_gate(sha=sha), "variant", variant, flush=True)
        v = next((x for x in PLAN["variants"] if x["id"] == variant), None)   # the parameter hides variant()
        if v is None:
            raise SystemExit(f"no variant {variant!r}; one of {[x['id'] for x in PLAN['variants']]}")
        rid = run_id(sha, worker_sha())
        print("run id", rid, "timeout", timeout_of(PLAN, v), "s, cap $", v["cap_usd"], flush=True)
        res = GPU_FNS[variant].remote(rid)
        print("result", json.dumps(res))
        if res.get("state") != "DONE":
            print(FAILED, flush=True)
            raise SystemExit(4)
