"""Wan clips on Modal (v4.3 plan P6.3, D-131; Fable audit 2026-11-12 fix 1), on the template of ``p15/modal_qwen_jobs_v15.py``.

One shot per launch: ``aivideo/wan_adapter.ModalWanBackend`` runs ``modal run --detach modal_wan_jobs.py::main --job <spec>``,
prices it from the speed measured on L3 and reserves it in the run's ledger before it is sent. The OR-37 ladder, in order,
each rung recorded in the ladder file (``cloud/modal_run.record_rung``) before the next may start:

    L0  local: the unit tests (free, no Modal)
    L1  ::check    CPU only: the image imports every module and the pipeline class, the launch file is pinned, the HF token
                   is in the secret (no GPU, no weights; cents of CPU time on the Starter credit)
    L2  ::weights  CPU only: the Volume ee-weights holds every model file of the launch with its sha256 (no GPU)
    L3  ::smoke    GPU, tiny clip under ``caps.smoke_usd``: measures ``s_per_clip_s`` and the cold start ``setup_s`` (the
                   price base of L4); paid, needs EE_MODAL_GO = the creator's message id
    L4  ::main     GPU, the shot of ``--job`` under ``caps.run_usd``; paid, needs EE_MODAL_GO

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
PINS = ("model_repo", "model_revision", "model_files", "pipeline", "hf_out", "settings")
SMOKE_JOB = {"shot_id": "L3_smoke", "seconds": 1.0, "fps": 16, "width": 832, "height": 480, "seed": 7,
             "motion_prompt": "the camera drifts slowly forward"}


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def launch_problems(launch: dict) -> list[str]:
    """The same pins ``aivideo/wan_adapter.launch_problems`` checks, plus the caps (kept here so the container needs no repo)."""
    out = [f"launch {k} is not pinned" for k in PINS if launch.get(k) in (None, "", {}, [])]
    out += [f"launch model file {f} has no sha256" for f, h in (launch.get("model_files") or {}).items()
            if not (isinstance(h, str) and len(h) == 64)]
    if not isinstance(launch.get("usd_per_h"), (int, float)) or not launch.get("prices_date"):
        out.append("launch usd_per_h / prices_date is not set")
    caps = launch.get("caps") or {}
    out += [f"launch caps.{k} is not set" for k in ("smoke_usd", "run_usd", "cold_start_s")
            if not isinstance(caps.get(k), (int, float)) or caps[k] <= 0]
    return out


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


def wan_frames(seconds: float, fps: int) -> int:
    """Wan draws 4k+1 frames: the smallest such count that holds the shot (the adapter's QA asks for round(seconds*fps))."""
    n = max(1, int(round(seconds * fps)))
    return 4 * math.ceil((n - 1) / 4) + 1


def go_gate(env=os.environ):
    v = env.get("EE_MODAL_GO", "")
    if not v.startswith("cmsg_"):
        raise SystemExit("EE_MODAL_GO must be the card id of the creator's yes (OR-23); nothing was started")
    return v


def ladder_gate(rung: str, path=None):
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(path or LADDER_PATH), rung)


def read_job(path: str) -> dict:
    """The shot spec the adapter wrote, with the start picture's bytes and their sha256 (checked against the spec's pin)."""
    job = json.loads(Path(path).read_text(encoding="utf-8"))
    pic = Path(job["start_picture"]).read_bytes()
    sha = hashlib.sha256(pic).hexdigest()
    want = (job.get("extra") or {}).get("start_sha256")
    if want and want != sha:
        raise SystemExit(f"{job['shot_id']}: the start picture's sha256 is not the one the pictures stage pinned")
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
    new = [p for p in sorted(out.rglob("*")) if p.is_file() and p.stat().st_size > 0 and (str(p), p.stat().st_size) not in seen]
    if not new:
        return 0
    ops = [CommitOperationAdd(path_in_repo=f"{launch['hf_out']}/{p.relative_to(out.parent)}", path_or_fileobj=str(p)) for p in new]
    for k in range(6 if final else 2):
        try:
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops, commit_message=f"{launch['hf_out']}: {len(new)} files")
            seen.update((str(p), p.stat().st_size) for p in new)
            return len(new)
        except Exception as e:  # noqa: BLE001 - a 429/5xx is retried with backoff; the Volume copy is the safety net
            print("upload failed", repr(e)[:160], flush=True)
            time.sleep(15.0 * 2 ** k)
    return 0


def _uploader(out, launch, stop, interval=30.0):
    from huggingface_hub import HfApi
    api, seen = HfApi(token=_tok()), set()
    while True:
        done = stop.is_set()
        _upload(api, out, launch, seen, final=done)
        if done:
            return
        stop.wait(interval)


def generate(job: dict, launch: dict, out: Path) -> dict:
    """One clip with the launch's diffusers pipeline, from the Volume's weights, every setting from the launch file."""
    import io
    import torch
    import diffusers
    from diffusers.utils import export_to_video
    from PIL import Image
    t0 = time.time()
    pipe = getattr(diffusers, launch["pipeline"]).from_pretrained(str(weights_root(launch)), torch_dtype=torch.bfloat16).to("cuda")
    setup_s = time.time() - t0
    kw = dict(launch["settings"])
    if job.get("end_bytes"):
        kw[launch["end_image_arg"]] = Image.open(io.BytesIO(job["end_bytes"])).convert("RGB")
    t1 = time.time()
    res = pipe(image=Image.open(io.BytesIO(job["start_bytes"])).convert("RGB"), prompt=job["motion_prompt"],
               negative_prompt=job.get("negative_prompt") or None, num_frames=wan_frames(job["seconds"], job["fps"]),
               height=job["height"], width=job["width"], generator=torch.Generator("cuda").manual_seed(job["seed"]), **kw)
    export_to_video(res.frames[0], str(out / clip_name(job["shot_id"], job["seed"])), fps=job["fps"])
    gen_s = time.time() - t1
    return {"gpu": launch["gpu"], "setup_s": round(setup_s, 1), "gen_s": round(gen_s, 1),
            "s_per_clip_s": round(gen_s / job["seconds"], 2), "frames": wan_frames(job["seconds"], job["fps"])}


def body(job: dict, launch: dict, timeout_s: int) -> dict:
    if import_check(launch["pipeline"]) != 0:
        raise SystemExit("OR-37: the image lacks a module or the pipeline; stopped before any weight was read")
    if hashlib.sha256(job["start_bytes"]).hexdigest() != job["start_sha256"]:
        raise SystemExit("the start picture changed in transit")
    out = Path("/workspace/out") / job["shot_id"]
    out.mkdir(parents=True, exist_ok=True)
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
    (out / f"{job['shot_id']}.measured.json").write_text(json.dumps(measured))
    (out / f"{job['shot_id']}.beat.txt").write_text(f"{state}\n")
    persist(out)
    stop.set()
    th.join(timeout=300)
    return {"state": state, **measured}


def persist(out):
    import shutil
    try:
        shutil.copytree(out, f"/w/out_wan/{Path(out).name}", dirs_exist_ok=True)
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
             .run_commands(f'pip install -q "huggingface_hub==1.33.0" "{DIFFUSERS}" transformers accelerate ftfy "imageio[ffmpeg]"')
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

    if TIMEOUTS:
        GPU_KW = dict(image=image, gpu=LAUNCH["gpu"], cpu=LAUNCH["cpu"], memory=LAUNCH["memory_gib"] * 1024, retries=0,
                      volumes={"/w": vol}, secrets=secrets)

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
        print("env_check rc", env_check.remote(LAUNCH["pipeline"]))

    @app.local_entrypoint()
    def weights():
        ladder_gate("L2")
        preflight(LAUNCH)
        print("weights", weights_check.remote(LAUNCH) or "all files present, sha256 match")

    @app.local_entrypoint()
    def smoke(picture: str = ""):
        preflight(LAUNCH)
        print("GO card", go_gate(), "smoke timeout", TIMEOUTS[0], "s", flush=True)
        ladder_gate("L3")
        pic = Path(picture).read_bytes()
        job = dict(SMOKE_JOB, start_bytes=pic, start_sha256=hashlib.sha256(pic).hexdigest())
        print("result", json.dumps(wan_smoke.remote(job, LAUNCH)))

    @app.local_entrypoint()
    def main(job: str = ""):
        spec = read_job(job)
        preflight(LAUNCH, spec)
        print("GO card", go_gate(), "timeout", TIMEOUTS[1], "s", flush=True)
        ladder_gate("L4")
        print("result", json.dumps(wan_main.remote(spec, LAUNCH)))
