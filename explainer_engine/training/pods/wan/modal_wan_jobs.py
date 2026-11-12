"""Wan clips on Modal (v4.3 plan P6.3, D-131; Fable audit 2026-11-12 fix 1), on the template of ``p15/modal_qwen_jobs_v15.py``.

One shot per launch: ``aivideo/wan_adapter.ModalWanBackend`` runs ``modal run --detach modal_wan_jobs.py::main --job <spec>``,
prices it from the speed measured on L3 and reserves it in the run's ledger before it is sent. The OR-37 ladder, in order,
each rung recorded in the ladder file (``cloud/modal_run.record_rung``) before the next may start:

    L0  local: the unit tests (free, no Modal; ``python -m explainer_engine.cloud.modal_run l0 <ladder>`` runs them and records
                   the pytest summary and the commit)
    L1  ::check    CPU only: the image imports every module and the pipeline class, the launch file is pinned, the HF token
                   is in the secret (no GPU, no weights; cents of CPU time on the Starter credit)
    L2  ::weights  CPU only: the Volume ee-weights holds every model file of the launch with its sha256 (no GPU)
    L3  ::smoke    GPU, tiny clip under ``caps.smoke_usd``: measures ``s_per_clip_s`` and the cold start ``setup_s`` (the
                   price base of L4); paid, needs EE_MODAL_GO = ``<the creator's message id>:<the plan's sha256[:12]>``
    L4  ::main     GPU, the shot of ``--job`` under ``caps.run_usd``; paid, needs the same EE_MODAL_GO for the job's plan

Each entrypoint records its own rung (final audit A5): green only when its result is good, with the launch file's sha256 and
the worker's own sha256 (``proof``); a bad result records the rung red and exits non-zero. A rung proved on another launch
file or another worker is stale: ``cloud/modal_run.gate`` refuses the rungs above it until it is run again.

Every function's timeout comes from its cap (OR-37: ``cost_timeout``), retries 0. The free rule check (``preflight``) runs on
the local side before the GO gate. Inputs are pinned by sha256 (the start picture's bytes travel with the call and are
re-checked in the container); weights come only from the Volume, never downloaded in the paid function; the clip, the
measurement and the beat go to HF ``hf_out`` as they are made, and to the Volume too (OR-33).

While the launch file has a null pin (model, revision, file shas, pipeline, settings, HF output, caps) nothing here can run:
the creator picks them (OR-22)."""
import hashlib, json, math, os, subprocess, threading, time
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
LAUNCH_PATH = Path(__file__).with_name("launch.json")
LADDER_PATH = Path(os.environ.get("EE_WAN_LADDER") or Path(__file__).with_name("ladder.json"))
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
DIFFUSERS = "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d"
SECRET_NAME = "huggingface-secret"
PINS = ("model_repo", "model_revision", "model_files", "pipeline", "hf_out", "settings", "pip_pins", "scaledown_window_s")
PIP_LIBS = ("transformers", "accelerate")   # pinned in the image (final audit C4); diffusers is pinned by commit above
GO = __import__("re").compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
WAN_FAILED = "WAN_FAILED"   # printed by ::main when the model ran and made no clip (the adapter may retry once with a new seed)
SMOKE_JOB = {"shot_id": "L3_smoke", "seconds": 1.0, "fps": 16, "width": 832, "height": 480, "seed": 7,
             "motion_prompt": "the camera drifts slowly forward"}


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def launch_problems(launch: dict) -> list[str]:
    """The same pins ``aivideo/wan_adapter.launch_problems`` checks, plus the caps (kept here so the container needs no repo)."""
    out = [f"launch {k} is not pinned" for k in PINS if launch.get(k) in (None, "", {}, [])]
    out += [f"launch model file {f} has no sha256" for f, h in (launch.get("model_files") or {}).items()
            if not (isinstance(h, str) and len(h) == 64)]
    pins = launch.get("pip_pins") if isinstance(launch.get("pip_pins"), dict) else {}
    out += [f"launch pip_pins.{k} is not pinned" for k in PIP_LIBS if launch.get("pip_pins") and not pins.get(k)]
    if launch.get("scaledown_window_s") is not None and not (isinstance(launch["scaledown_window_s"], int)
                                                             and 2 <= launch["scaledown_window_s"] <= 60):
        out.append("launch scaledown_window_s must be a short whole number of seconds (2..60): nothing stays warm")
    if not isinstance(launch.get("usd_per_h"), (int, float)) or not launch.get("prices_date"):
        out.append("launch usd_per_h / prices_date is not set")
    caps = launch.get("caps") or {}
    out += [f"launch caps.{k} is not set" for k in ("smoke_usd", "run_usd", "cold_start_s")
            if not isinstance(caps.get(k), (int, float)) or caps[k] <= 0]
    out += native_problems(launch)
    if launch.get("offload") not in OFFLOADS:
        out.append(f"launch offload must be one of {OFFLOADS}")
    return out


OFFLOADS = ("none", "model_cpu_offload")


def native_problems(launch: dict) -> list[str]:
    """The model's own limits (final audit A2), read from its card: ``native`` = {fps, max_frames (4k+1), sizes [[w, h]],
    use (the size every clip is made at, one of sizes)}."""
    n = launch.get("native")
    if not isinstance(n, dict):
        return ["launch native (fps, max_frames, sizes, use) is not pinned"]
    out = []
    if not (isinstance(n.get("fps"), int) and n["fps"] > 0):
        out.append("launch native.fps must be the model's whole frame rate")
    mf = n.get("max_frames")
    if not (isinstance(mf, int) and mf >= 5 and (mf - 1) % 4 == 0):
        out.append("launch native.max_frames must be the model's longest clip in 4k+1 frames")
    sizes = n.get("sizes")
    if not (isinstance(sizes, list) and sizes and all(isinstance(s, list) and len(s) == 2 and all(
            isinstance(v, int) and v > 0 and v % 16 == 0 for v in s) for s in sizes)):
        out.append("launch native.sizes must list the model's [width, height] sizes (multiples of 16)")
    elif n.get("use") not in sizes:
        out.append("launch native.use must be one of native.sizes")
    return out


def native_spec(launch: dict, seconds: float) -> dict:
    """The clip the model makes for a shot of ``seconds``: its own rate and the launch's size, 4k+1 frames; a shot longer than
    the model's longest clip raises ValueError (split it in the script, or chain two clips on frame[-5]; final audit A2)."""
    n = launch["native"]
    frames = wan_frames(seconds, n["fps"])
    if frames > n["max_frames"]:
        raise ValueError(f"{seconds:g} s is {frames} frames at the model's {n['fps']} fps, past its longest clip of "
                         f"{n['max_frames']} frames ({max_seconds(launch):.2f} s): split the shot in the script, or chain two "
                         "clips on frame[-5]")
    return {"fps": n["fps"], "width": n["use"][0], "height": n["use"][1], "frames": frames}


def max_seconds(launch: dict) -> float:
    """The longest shot one clip holds: round(seconds * fps) may not pass max_frames."""
    n = launch["native"]
    return (n["max_frames"] + 0.49) / n["fps"]


def usd_per_h(launch: dict) -> float:
    """The launch's GPU + CPU + memory price per hour (``usd_per_h``, dated ``prices_date``); the container has no repo, so the
    number is written into the launch file and ``schedule_rate`` holds it to ``cloud/modal_schedule`` on the local side."""
    return float(launch["usd_per_h"])


def schedule_rate(launch: dict) -> float:
    """GPU + CPU + memory per hour from ``cloud/modal_schedule`` (the dated price table), for the worker's own size (local)."""
    from explainer_engine.cloud import modal_schedule as MS
    per_s = MS.GPUS[launch["gpu"]]["usd_s"] + launch["cpu"] * MS.CPU_CORE_S + launch["memory_gib"] * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def cost_timeout(cap_usd, usd_h, cold_start_s):
    """OR-37: the function timeout comes from the cap, never by hand: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    startup = cold_start_s * usd_h / 3600
    return int(0.9 * (cap_usd - startup) / usd_h * 3600)


def check_timeout(timeout_s, cap_usd, usd_h, cold_start_s):
    if timeout_s <= 0 or timeout_s * usd_h / 3600 + cold_start_s * usd_h / 3600 > cap_usd:
        raise ValueError(f"timeout {timeout_s}s costs more than the cap ${cap_usd}")
    return timeout_s


def timeouts(launch: dict) -> tuple[int, int] | None:
    """(smoke, run) timeouts from the caps, or None while the launch is not pinned (then no GPU function is defined)."""
    if launch_problems(launch):
        return None
    c, h = launch["caps"], usd_per_h(launch)
    return (check_timeout(cost_timeout(c["smoke_usd"], h, c["cold_start_s"]), c["smoke_usd"], h, c["cold_start_s"]),
            check_timeout(cost_timeout(c["run_usd"], h, c["cold_start_s"]), c["run_usd"], h, c["cold_start_s"]))


def clip_name(shot_id: str, seed: int) -> str:
    """The clip's name in ``hf_out`` (``aivideo/wan_adapter.clip_name`` is the same)."""
    return f"{shot_id}_seed{seed}.mp4"


def sha_json(d) -> str:
    """The sha256 of a JSON value (sorted keys): the launch file's identity on the ladder and in every job."""
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def launch_sha(launch: dict) -> str:
    return sha_json(launch)


def worker_sha() -> str:
    """The sha256 of this file: the code a rung proved (a changed worker makes the rungs above L0 stale)."""
    return _sha(__file__)


def proof(launch: dict) -> dict:
    """What a rung proves: this launch file run by this worker (final audit A5)."""
    return {"launch_sha": launch_sha(launch), "worker_sha": worker_sha()}


def run_id(plan_sha: str, launch: dict) -> str:
    """The folder of one approved plan on one launch file inside ``hf_out`` (final audit A4): a clip of an earlier plan or of
    another launch can never be fetched as this one's, and the same job asked again finds its finished clip."""
    if not (isinstance(plan_sha, str) and len(plan_sha) == 64):
        raise ValueError("a run id needs the approved plan's sha256")
    return f"{plan_sha[:12]}_{launch_sha(launch)[:12]}"


def hf_path(launch: dict, job: dict, name: str) -> str:
    """A file of one job in the HF output: ``<hf_out>/<run_id>/<shot_id>/<name>``."""
    return f"{launch['hf_out']}/{job['run_id']}/{job['shot_id']}/{name}"


def wan_frames(seconds: float, fps: int) -> int:
    """Wan draws 4k+1 frames: the smallest such count that holds the shot (the adapter's QA asks for round(seconds*fps))."""
    n = max(1, int(round(seconds * fps)))
    return 4 * math.ceil((n - 1) / 4) + 1


def go_gate(env=os.environ, plan_sha: str | None = None):
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of the plan he said yes to>`` (final audit B10): a yes binds one
    plan; a changed plan, or a job of another plan, is refused before anything starts."""
    v = env.get("EE_MODAL_GO", "")
    m = GO.match(v)
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the card id of the creator's yes>:<the plan's sha256[:12]>' (OR-23); "
                         "nothing was started")
    if not plan_sha or m.group(2) != plan_sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than this job's (OR-23: the yes binds the plan's hash); nothing was "
                         "started")
    return v


def ladder_gate(rung: str, path=None, launch=None):
    """The rung may start only when every rung below it is green ON THIS launch file and worker (``proof``)."""
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(path or LADDER_PATH), rung, proof=proof(LAUNCH if launch is None else launch))


def record(rung: str, ok: bool, path=None, launch=None, **info):
    """The entrypoint records its own rung (final audit A5), bound to the launch file and the worker; red exits non-zero."""
    from explainer_engine.cloud import modal_run as MR
    MR.record_rung(path or LADDER_PATH, rung, ok, **proof(LAUNCH if launch is None else launch), **info)
    if not ok:
        raise SystemExit(f"rung {rung} is red: {json.dumps(info, default=str)[:600]}")


def read_job(path: str, launch: dict | None = None) -> dict:
    """The shot spec the adapter wrote, with the start picture's bytes and their sha256. The spec must carry the pin the
    pictures stage wrote (``extra.start_sha256``, from ``production/pictures.json``; final audit B9), its plan's sha256, its run
    id and the launch file's sha256; any of them missing or different stops the job before anything starts."""
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    pic = Path(job["start_picture"]).read_bytes()
    sha = hashlib.sha256(pic).hexdigest()
    want = (job.get("extra") or {}).get("start_sha256")
    if not want:
        raise SystemExit(f"{job['shot_id']}: the spec has no start_sha256 pinned by the pictures stage; nothing was started")
    if want != sha:
        raise SystemExit(f"{job['shot_id']}: the start picture's sha256 is not the one the pictures stage pinned")
    for k in ("plan_sha256", "run_id", "launch_sha"):
        if not job.get(k):
            raise SystemExit(f"{job['shot_id']}: the spec has no {k}; nothing was started")
    lf = LAUNCH if launch is None else launch
    if job["launch_sha"] != launch_sha(lf) or job["run_id"] != run_id(job["plan_sha256"], lf):
        raise SystemExit(f"{job['shot_id']}: the spec was written for another launch file; nothing was started")
    try:   # final audit A2: the model's own rate and size, never past its longest clip
        nat = native_spec(lf, float(job["seconds"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"{job['shot_id']}: {exc}; nothing was started") from None
    if (job.get("fps"), job.get("width"), job.get("height")) != (nat["fps"], nat["width"], nat["height"]):
        raise SystemExit(f"{job['shot_id']}: the spec asks {job.get('width')}x{job.get('height')} at {job.get('fps')} fps, not the "
                         f"model's {nat['width']}x{nat['height']} at {nat['fps']} fps; nothing was started")
    job["start_sha256"] = sha
    if job.get("end_picture"):
        job["end_bytes"] = Path(job["end_picture"]).read_bytes()
    return dict(job, start_bytes=pic)


def preflight(launch: dict, job: dict | None = None):
    """Free check before any paid call (the creator 2026-11-07 22:23 UTC): every pin and cap set; the shot has a motion prompt,
    seconds, a seed and a sha-pinned start picture; an end picture only where the launch names the pipeline's argument."""
    bad = launch_problems(launch)
    if not bad and abs(schedule_rate(launch) - usd_per_h(launch)) > 0.01 * schedule_rate(launch):
        bad.append(f"launch usd_per_h {usd_per_h(launch)} is not the price table's {schedule_rate(launch)} (cloud/modal_schedule)")
    if not bad:   # the launch's caps never pass the creator's per-run line (config/spend_caps.json modal.per_run_usd)
        from explainer_engine.core import spend_caps
        try:
            line = float(spend_caps.modal()["per_run_usd"])
            bad += [f"launch caps.{k} ${launch['caps'][k]:g} is above the creator's ${line:g} per run" for k in ("smoke_usd", "run_usd")
                    if launch["caps"][k] > line + 1e-9]
        except spend_caps.OverCeiling as exc:
            bad.append(str(exc))
    if job is not None:
        if not str(job.get("motion_prompt") or "").strip():
            bad.append(f"{job.get('shot_id')}: no motion prompt")
        if not float(job.get("seconds") or 0) > 0 or not isinstance(job.get("seed"), int):
            bad.append(f"{job.get('shot_id')}: seconds or seed missing")
        if job.get("end_picture") and not launch.get("end_image_arg"):
            bad.append(f"{job.get('shot_id')}: an end picture, but the launch names no end_image_arg")
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


# --- in the container ------------------------------------------------------------------------------------------------------

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


def weights_root(launch, vol_root="/w"):
    return Path(vol_root) / "model" / launch["model_repo"]


STAGE_CPU, STAGE_MEM_GIB, STAGE_TIMEOUT_S = 4, 16, 3600   # final audit A6: CPU only; its price per hour is held to the table
STAGE_USD_PER_H = 0.3165                                    # by a test (cloud/modal_schedule, 2026-11-07): at most ~$0.32 a stage


def stage_weights(launch, vol_root="/w", download=None) -> list[str]:
    """Final audit A6: the launch's model files of the pinned revision into the Volume (only the files it names, only the
    missing ones), then every sha256; returns what is still wrong (an empty list = the weights are there and match)."""
    root = weights_root(launch, vol_root)
    missing = [f for f in launch["model_files"] if not (root / f).is_file()]
    if missing:
        (download or _hf_download)(launch["model_repo"], launch["model_revision"], missing, root)
    return check_weights(launch, vol_root)


def _hf_download(repo, revision, files, root):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), local_dir=str(root),
                      token=os.environ.get("HF_TOKEN") or None)


def check_weights(launch, vol_root="/w") -> list[str]:
    """L2: every model file of the launch on the Volume with its sha256 (the paid function never downloads weights)."""
    root, bad = weights_root(launch, vol_root), []
    for f, want in launch["model_files"].items():
        p = root / f
        if not p.is_file():
            bad.append(f"missing {f}")
        elif _sha(p) != want:
            bad.append(f"sha256 mismatch {f}")
    return bad


CHECK = ("import importlib, sys; mods = ['torch', 'diffusers', 'transformers', 'huggingface_hub', 'PIL', 'imageio', 'ftfy']; bad = []\n"
         "for m in mods:\n"
         "    try: importlib.import_module(m); print('ok', m)\n"
         "    except Exception as e: bad.append(m); print('MISSING', m, repr(e)[:150])\n"
         "import diffusers\n"
         "p = sys.argv[1]\n"
         "if not hasattr(diffusers, p): bad.append(p); print('MISSING pipeline', p)\n"
         "sys.exit(1 if bad else 0)")


def import_check(pipeline: str):
    """OR-37: every module the run imports and the launch's pipeline class, on the container's python; fails in seconds."""
    r = subprocess.run(["python3", "-c", CHECK, pipeline], capture_output=True, text=True)
    print(r.stdout, r.stderr[-500:], flush=True)
    return r.returncode


def _upload(api, out: Path, launch, seen: set, final=False):
    from huggingface_hub import CommitOperationAdd
    new = [p for p in sorted(out.rglob("*")) if p.is_file() and p.stat().st_size > 0 and _key(p) not in seen]
    if not new:
        return 0
    ops = [CommitOperationAdd(path_in_repo=f"{launch['hf_out']}/{p.relative_to(OUT_ROOT)}", path_or_fileobj=str(p)) for p in new]
    for k in range(6 if final else 2):
        try:
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops, commit_message=f"{launch['hf_out']}: {len(new)} files")
            seen.update(_key(p) for p in new)
            return len(new)
        except Exception as e:  # noqa: BLE001 - a 429/5xx is retried with backoff; the Volume copy is the safety net
            print("upload failed", repr(e)[:160], flush=True)
            time.sleep(15.0 * 2 ** k)
    return 0


def _key(p: Path):
    st = p.stat()
    return str(p), st.st_size, st.st_mtime_ns


def beat(out: Path, job: dict, stage: str, **info):
    """The step beat the OR-36 watchdog reads (final audit A7): what the worker is doing now, and since when; the uploader
    sends it with the next 30 s commit, so a hang is told apart from work while the GPU bills."""
    (out / f"{job['shot_id']}.beat.txt").write_text(json.dumps(dict(info, stage=stage, at=round(time.time(), 1))) + "\n")


def _uploader(out, launch, stop, interval=30.0):
    from huggingface_hub import HfApi
    api, seen = HfApi(token=_tok()), set()
    while True:
        done = stop.is_set()
        _upload(api, out, launch, seen, final=done)
        if done:
            return
        stop.wait(interval)


def libs() -> dict:
    """The versions of the libraries the clip was made with (recorded in ``measured.json``, final audit B9)."""
    import importlib
    out = {}
    for m in ("torch", "diffusers", "transformers", "accelerate"):
        try:
            out[m] = getattr(importlib.import_module(m), "__version__", "?")
        except Exception:  # noqa: BLE001
            out[m] = None
    return out


def generate(job: dict, launch: dict, out: Path) -> dict:
    """One clip with the launch's diffusers pipeline, from the Volume's weights, every setting from the launch file."""
    import inspect
    import io
    import torch
    import diffusers
    from diffusers.utils import export_to_video
    from PIL import Image
    t0 = time.time()
    beat(out, job, "load")
    pipe = getattr(diffusers, launch["pipeline"]).from_pretrained(str(weights_root(launch)), torch_dtype=torch.bfloat16)
    if launch.get("offload") == "model_cpu_offload":   # the card's single-GPU recipe: one part on the GPU at a time
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")
    setup_s = time.time() - t0
    kw = dict(launch["settings"])
    if job.get("end_bytes"):
        kw[launch["end_image_arg"]] = Image.open(io.BytesIO(job["end_bytes"])).convert("RGB")
    if "callback_on_step_end" in inspect.signature(pipe.__call__).parameters:
        def _step(p, i, t, cbk):
            beat(out, job, "generate", step=int(i) + 1)
            return cbk
        kw["callback_on_step_end"] = _step
    t1 = time.time()
    beat(out, job, "generate", step=0)
    res = pipe(image=Image.open(io.BytesIO(job["start_bytes"])).convert("RGB"), prompt=job["motion_prompt"],
               negative_prompt=job.get("negative_prompt") or None, num_frames=wan_frames(job["seconds"], job["fps"]),
               height=job["height"], width=job["width"], generator=torch.Generator("cuda").manual_seed(job["seed"]), **kw)
    beat(out, job, "export")
    export_to_video(res.frames[0], str(out / clip_name(job["shot_id"], job["seed"])), fps=job["fps"])
    gen_s = time.time() - t1
    return {"gpu": launch["gpu"], "setup_s": round(setup_s, 1), "gen_s": round(gen_s, 1),
            "s_per_clip_s": round(gen_s / job["seconds"], 2), "frames": wan_frames(job["seconds"], job["fps"])}


OUT_ROOT = Path("/workspace/out")


def body(job: dict, launch: dict, timeout_s: int) -> dict:
    t_in = time.time()
    if import_check(launch["pipeline"]) != 0:
        raise SystemExit("OR-37: the image lacks a module or the pipeline; stopped before any weight was read")
    if hashlib.sha256(job["start_bytes"]).hexdigest() != job["start_sha256"]:
        raise SystemExit("the start picture changed in transit")
    if job.get("launch_sha") and job["launch_sha"] != launch_sha(launch):
        raise SystemExit("the launch file changed between the spec and the container")
    out = OUT_ROOT / job["run_id"] / job["shot_id"]
    out.mkdir(parents=True, exist_ok=True)
    beat(out, job, "start")
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(out, launch, stop), daemon=True)
    th.start()

    def _fire():
        (out / f"{job['shot_id']}.beat.txt").write_text("TIMEOUT: the in-container deadline fired\n")
        persist(out)
        stop.set()
        th.join(timeout=40)
        os._exit(3)
    t = threading.Timer(max(30, timeout_s - 60), _fire)
    t.daemon = True
    t.start()
    try:
        measured = generate(job, launch, out)
        state = "DONE" if (out / clip_name(job["shot_id"], job["seed"])).stat().st_size > 0 else "FAILED"
    except Exception as e:  # noqa: BLE001 - one attempt: the failure is written, uploaded and returned
        measured, state = {"error": repr(e)[:400]}, "FAILED"
    t.cancel()   # final audit C4: the deadline belongs to this job only
    measured.update(state=state, body_s=round(time.time() - t_in, 1), commit=job.get("commit"), worker_sha=job.get("worker_sha"),
                    launch_sha=launch_sha(launch), run_id=job["run_id"], libs=libs())
    (out / f"{job['shot_id']}.measured.json").write_text(json.dumps(measured))
    beat(out, job, state)
    persist(out)
    stop.set()
    th.join(timeout=300)
    return {"state": state, **measured}


def persist(out):
    import shutil
    try:
        shutil.copytree(out, f"/w/out_wan/{Path(out).relative_to(OUT_ROOT)}", dirs_exist_ok=True)
        vol.commit()
    except Exception as e:  # noqa: BLE001
        print("volume copy failed", repr(e)[:200], flush=True)


LAUNCH = load_launch()
TIMEOUTS = timeouts(LAUNCH)

if modal is not None:
    app = modal.App(LAUNCH["app_name"])
    vol = modal.Volume.from_name("ee-weights", version=2)
    image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12")
             .apt_install("ffmpeg")
             .run_commands(f'pip install -q "huggingface_hub==1.33.0" "{DIFFUSERS}" '
                           + " ".join(f'"{k}=={(LAUNCH.get("pip_pins") or {}).get(k)}"' for k in PIP_LIBS)
                           + ' ftfy "imageio[ffmpeg]"')
             .add_local_file(str(LAUNCH_PATH), "/root/launch.json"))
    secrets = [modal.Secret.from_name(SECRET_NAME)]

    @app.function(image=image, cpu=2, memory=4096, timeout=300, retries=0, secrets=secrets)
    def env_check(pipeline: str):
        """L1, CPU only: imports, the pipeline class, the HF token."""
        _tok()
        return import_check(pipeline)

    @app.function(image=image, cpu=2, memory=4096, timeout=1800, retries=0, volumes={"/w": vol})
    def weights_check(launch: dict):
        """L2, CPU only: the Volume's weights against the launch's sha256 pins."""
        return check_weights(launch)

    @app.function(image=image, cpu=STAGE_CPU, memory=STAGE_MEM_GIB * 1024, timeout=STAGE_TIMEOUT_S, retries=0,
                  volumes={"/w": vol}, secrets=secrets)
    def weights_stage(launch: dict):
        """A6, CPU only: the pinned revision's files into the Volume, every sha256 checked, then committed."""
        bad = stage_weights(launch)
        vol.commit()
        return bad

    if TIMEOUTS:
        GPU_KW = dict(image=image, gpu=LAUNCH["gpu"], cpu=LAUNCH["cpu"], memory=LAUNCH["memory_gib"] * 1024, retries=0,
                      volumes={"/w": vol}, secrets=secrets, scaledown_window=LAUNCH["scaledown_window_s"])

        @app.function(timeout=TIMEOUTS[0], **GPU_KW)
        def wan_smoke(job: dict, launch: dict):
            return body(job, launch, TIMEOUTS[0])

        @app.function(timeout=TIMEOUTS[1], **GPU_KW)
        def wan_main(job: dict, launch: dict):
            return body(job, launch, TIMEOUTS[1])

    @app.local_entrypoint()
    def check():
        ladder_gate("L1")
        bad = launch_problems(LAUNCH)
        if bad:
            raise SystemExit("the launch file is not pinned:\n" + "\n".join(bad))
        rc = env_check.remote(LAUNCH["pipeline"])
        print("env_check rc", rc)
        record("L1", rc == 0, note=f"env_check rc {rc}")

    @app.local_entrypoint()
    def stage(plan: str = ""):
        """Between L1 and L2 (final audit A6): a paid CPU step under the creator's GO; L2 then proves the files."""
        preflight(LAUNCH)
        print("GO card", go_gate(plan_sha=_sha(plan)), "stage timeout", STAGE_TIMEOUT_S, "s", flush=True)
        ladder_gate("L2")
        bad = weights_stage.remote(LAUNCH)
        print("stage", bad or "all files on the Volume, sha256 match")
        if bad:
            raise SystemExit("the weights stage-in is not complete:\n" + "\n".join(bad))

    @app.local_entrypoint()
    def weights():
        ladder_gate("L2")
        preflight(LAUNCH)
        bad = weights_check.remote(LAUNCH)
        print("weights", bad or "all files present, sha256 match")
        record("L2", not bad, problems=bad)

    @app.local_entrypoint()
    def smoke(picture: str = "", plan: str = ""):
        preflight(LAUNCH)
        plan_sha = _sha(plan)
        print("GO card", go_gate(plan_sha=plan_sha), "smoke timeout", TIMEOUTS[0], "s", flush=True)
        ladder_gate("L3")
        pic = Path(picture).read_bytes()
        nat = native_spec(LAUNCH, SMOKE_JOB["seconds"])   # A2: the smoke is made at the model's own rate and the launch's size
        job = dict(SMOKE_JOB, fps=nat["fps"], width=nat["width"], height=nat["height"], start_bytes=pic, start_sha256=hashlib.sha256(pic).hexdigest(), run_id=run_id(plan_sha, LAUNCH),
                   launch_sha=launch_sha(LAUNCH), worker_sha=worker_sha())
        res = wan_smoke.remote(job, LAUNCH)
        print("result", json.dumps(res))
        ok = res.get("state") == "DONE"
        record("L3", ok, measured={k: res.get(k) for k in ("gpu", "s_per_clip_s", "setup_s", "body_s")} if ok else None,
               result={k: res.get(k) for k in ("state", "error")})

    @app.local_entrypoint()
    def main(job: str = ""):
        spec = read_job(job)
        preflight(LAUNCH, spec)
        print("GO card", go_gate(plan_sha=spec["plan_sha256"]), "timeout", TIMEOUTS[1], "s", flush=True)
        ladder_gate("L4")
        res = wan_main.remote(dict(spec, worker_sha=worker_sha()), LAUNCH)
        print("result", json.dumps(res))
        if res.get("state") != "DONE":   # final audit A4: a FAILED clip is a non-zero exit, never a 0
            print(WAN_FAILED, flush=True)
            raise SystemExit(4)
