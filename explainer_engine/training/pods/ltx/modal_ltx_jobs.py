"""LTX-2.5 distilled clips on Modal: the video route of a v4.3 episode (D-132, the creator 2026-11-12 19:10 UTC, after the
bake-off run fae4ee9fb9d2_5dd040ac95c8). The bake-off's LTX job (``training/pods/bakeoff/modal_bakeoff.py``: ``ltx_cmd``,
``make_ltx``, the clean deadline, the attempt marker, the Volume copy before the last HF flush) made a production job on the
contract of the Wan worker (``training/pods/wan/modal_wan_jobs.py``), so ``aivideo/wan_adapter`` drives it unchanged through
``aivideo/ltx_modal.ModalLtxBackend``.

One shot per launch: the backend runs ``modal run --detach modal_ltx_jobs.py::main --job <spec>``, priced from the speed
measured on L3 and reserved in the run's ledger before it is sent. The OR-37 ladder, each rung recorded in the ladder file
(``cloud/modal_run.record_rung``, bound to this launch file and this worker) before the next may start:

    L0  local: the unit tests (free)
    L1  ::check    CPU: the image imports torch, ltx_core and the launch's ltx_pipelines module; the launch file is pinned
    L2  ::weights  CPU: the Volume ee-weights holds every model file of the launch with its sha256
    L3  ::smoke    GPU, one short clip under ``caps.smoke_usd``: measures ``s_per_clip_s`` and ``setup_s``; paid, EE_MODAL_GO
    L4  ::main     GPU, the shot of ``--job`` under ``caps.run_usd``; paid, EE_MODAL_GO for the job's plan

What the bake-off audits taught, kept here (BAKEOFF_AUDIT_FABLE_HIGH.md, BAKEOFF_DELTA_AUDIT.md):
- no ``os._exit``: the CLI runs under ``subprocess.run(timeout=)`` bounded by the time left, so the normal end path always writes,
  copies to the Volume and uploads (A1); Modal reschedules a crashed input, so an attempt marker per launch nonce on the Volume
  makes a second attempt return at once (``REFUSED_SECOND_ATTEMPT``);
- the Volume copy comes before the final HF flush and again after it, the flush's backoff is bounded (N2);
- every upload is checked on HF by its sha256 (LFS) or git blob id before the job reports DONE (OR-33);
- the result holds plain JSON only (``libs`` returns strings: torch's ``TorchVersion`` cannot be read by a local client
  without torch, which lost the bake-off's LTX answer).

The clip carries LTX's own sound (speech and effects, the creator 2026-11-12 19:12 UTC): the prompt the backend builds holds
the scene, the spoken words and the sounds (``aivideo/ltx_modal.build_prompt``)."""
import hashlib, json, math, os, re, shutil, subprocess, sys, threading, time, uuid
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
LAUNCH_PATH = Path(__file__).with_name("launch.json")
LADDER_PATH = Path(os.environ.get("EE_LTX_LADDER") or Path(__file__).with_name("ladder.json"))
SECRET_NAME = "huggingface-secret"
PINS = ("model_repo", "model_revision", "model_files", "ltx_code", "module", "uses", "hf_out", "scaledown_window_s",
        "base_image")
USES = ("transformer", "text_encoder", "video_vae", "audio_vae", "spatial_upsampler")
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
LTX_FAILED = "LTX_FAILED"   # printed by ::main when the model ran and made no clip (the adapter may retry once, new seed)
MARGIN_S = 150              # the end path after the last step: export, Volume copy, final upload, HF check
OUT_ROOT = Path("/workspace/out")
VOL_OUT = "out_ltx"
SMOKE_JOB = {"shot_id": "L3_smoke", "seconds": 2.0, "seed": 7,
             "motion_prompt": "The camera drifts slowly forward over the scene. Soft wind, distant birds."}


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def launch_problems(launch: dict) -> list[str]:
    """Every pin the run needs (OR-22, OR-23): model, revision, file shas, the LTX-2 code commit, the CLI module, the files it
    uses, the HF output, the image, the dated price and the caps; none left None."""
    out = [f"launch {k} is not pinned" for k in PINS if launch.get(k) in (None, "", {}, [])]
    files = launch.get("model_files") or {}
    out += [f"launch model file {f} has no sha256" for f, h in files.items() if not (isinstance(h, str) and len(h) == 64)]
    uses = launch.get("uses") if isinstance(launch.get("uses"), dict) else {}
    out += [f"launch uses.{k} is not one of the model files" for k in USES if uses and uses.get(k) not in files]
    code = launch.get("ltx_code") if isinstance(launch.get("ltx_code"), dict) else {}
    if code and not (code.get("repo") and re.fullmatch(r"[0-9a-f]{40}", str(code.get("commit") or ""))):
        out.append("launch ltx_code needs the repo and a full 40-hex commit")
    if launch.get("scaledown_window_s") is not None and not (isinstance(launch["scaledown_window_s"], int)
                                                             and 2 <= launch["scaledown_window_s"] <= 60):
        out.append("launch scaledown_window_s must be a short whole number of seconds (2..60): nothing stays warm")
    if not _num(launch.get("usd_per_h")) or not launch.get("prices_date"):
        out.append("launch usd_per_h / prices_date is not set")
    caps = launch.get("caps") or {}
    out += [f"launch caps.{k} is not set" for k in ("smoke_usd", "run_usd", "cold_start_s") if not _num(caps.get(k))]
    out += native_problems(launch)
    return out


def native_problems(launch: dict) -> list[str]:
    """The model's own limits: ``native`` = {fps, max_frames (8k+1), sizes [[w, h]] (multiples of 64: the two stages work at
    half size), use (the size every clip is made at)}."""
    n = launch.get("native")
    if not isinstance(n, dict):
        return ["launch native (fps, max_frames, sizes, use) is not pinned"]
    out = []
    if not (isinstance(n.get("fps"), int) and n["fps"] > 0):
        out.append("launch native.fps must be the model's whole frame rate")
    mf = n.get("max_frames")
    if not (isinstance(mf, int) and mf >= 9 and (mf - 1) % 8 == 0):
        out.append("launch native.max_frames must be the longest clip in 8k+1 frames")
    sizes = n.get("sizes")
    if not (isinstance(sizes, list) and sizes and all(isinstance(s, list) and len(s) == 2 and all(
            isinstance(v, int) and v > 0 and v % 64 == 0 for v in s) for s in sizes)):
        out.append("launch native.sizes must list [width, height] sizes in multiples of 64")
    elif n.get("use") not in sizes:
        out.append("launch native.use must be one of native.sizes")
    return out


def ltx_frames(seconds: float, fps: int) -> int:
    """LTX draws 8k+1 frames: the smallest such count that holds the shot."""
    n = max(1, int(round(seconds * fps)))
    return 8 * math.ceil((n - 1) / 8) + 1


def native_spec(launch: dict, seconds: float) -> dict:
    """The clip the model makes for a shot of ``seconds``: its own rate and the launch's size, 8k+1 frames; a shot longer than
    the longest proven clip raises ValueError (split it in the script)."""
    n = launch["native"]
    frames = ltx_frames(seconds, n["fps"])
    if frames > n["max_frames"]:
        raise ValueError(f"{seconds:g} s is {frames} frames at {n['fps']} fps, past the longest clip of {n['max_frames']} "
                         f"frames ({max_seconds(launch):.2f} s): split the shot in the script")
    return {"fps": n["fps"], "width": n["use"][0], "height": n["use"][1], "frames": frames}


def max_seconds(launch: dict) -> float:
    n = launch["native"]
    return (n["max_frames"] + 0.49) / n["fps"]


def usd_per_h(launch: dict) -> float:
    return float(launch["usd_per_h"])


def schedule_rate(launch: dict) -> float:
    """GPU + CPU + memory per hour from ``cloud/modal_schedule`` (the dated table), for the worker's own size (local side)."""
    from explainer_engine.cloud import modal_schedule as MS
    per_s = MS.GPUS[launch["gpu"]]["usd_s"] + launch["cpu"] * MS.CPU_CORE_S + launch["memory_gib"] * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def cost_timeout(cap_usd, usd_h, cold_start_s):
    """OR-37: the function timeout comes from the cap: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600) / usd_h * 3600)


def check_timeout(timeout_s, cap_usd, usd_h, cold_start_s):
    if timeout_s <= MARGIN_S or timeout_s * usd_h / 3600 + cold_start_s * usd_h / 3600 > cap_usd:
        raise ValueError(f"timeout {timeout_s}s does not fit the cap ${cap_usd} (or leaves no room for the end path)")
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
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def launch_sha(launch: dict) -> str:
    return sha_json(launch)


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def worker_sha() -> str:
    return _sha(__file__)


def proof(launch: dict) -> dict:
    return {"launch_sha": launch_sha(launch), "worker_sha": worker_sha()}


def run_id(plan_sha: str, launch: dict) -> str:
    if not (isinstance(plan_sha, str) and len(plan_sha) == 64):
        raise ValueError("a run id needs the approved plan's sha256")
    return f"{plan_sha[:12]}_{launch_sha(launch)[:12]}"


def hf_path(launch: dict, job: dict, name: str) -> str:
    return f"{launch['hf_out']}/{job['run_id']}/{job['shot_id']}/{name}"


def go_gate(env=os.environ, plan_sha: str | None = None):
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of the plan he said yes to>`` (final audit B10)."""
    v = env.get("EE_MODAL_GO", "")
    m = GO.match(v)
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the card id of the creator's yes>:<the plan's sha256[:12]>' (OR-23); "
                         "nothing was started")
    if not plan_sha or m.group(2) != plan_sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than this job's (OR-23); nothing was started")
    return v


def ladder_gate(rung: str, path=None, launch=None):
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(path or LADDER_PATH), rung, proof=proof(LAUNCH if launch is None else launch))


def record(rung: str, ok: bool, path=None, launch=None, **info):
    from explainer_engine.cloud import modal_run as MR
    MR.record_rung(path or LADDER_PATH, rung, ok, **proof(LAUNCH if launch is None else launch), **info)
    if not ok:
        raise SystemExit(f"rung {rung} is red: {json.dumps(info, default=str)[:600]}")


def read_job(path: str, launch: dict | None = None) -> dict:
    """The shot spec the adapter wrote, with the start picture's bytes. The pictures stage's pin (``extra.start_sha256``), the
    plan's sha256, the run id and the launch file's sha256 must all be there and agree, or nothing starts."""
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
    try:
        nat = native_spec(lf, float(job["seconds"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"{job['shot_id']}: {exc}; nothing was started") from None
    if (job.get("fps"), job.get("width"), job.get("height")) != (nat["fps"], nat["width"], nat["height"]):
        raise SystemExit(f"{job['shot_id']}: the spec asks {job.get('width')}x{job.get('height')} at {job.get('fps')} fps, not "
                         f"the model's {nat['width']}x{nat['height']} at {nat['fps']} fps; nothing was started")
    return dict(job, start_sha256=sha, start_bytes=pic)


def preflight(launch: dict, job: dict | None = None):
    """Free check before any paid call: every pin and cap set, the price equal to the dated table, the caps under the
    creator's ``modal_ltx`` line (``config/spend_caps.json``; missing = a zero budget), and the shot has a prompt, seconds,
    a seed. An end picture is refused: the distilled CLI takes one conditioning picture at frame 0."""
    bad = launch_problems(launch)
    if not bad and abs(schedule_rate(launch) - usd_per_h(launch)) > 0.01 * schedule_rate(launch):
        bad.append(f"launch usd_per_h {usd_per_h(launch)} is not the price table's {schedule_rate(launch)} (cloud/modal_schedule)")
    if not bad:
        from explainer_engine.core import spend_caps
        try:
            line = float(spend_caps.modal_ltx()["per_run_usd"])
            stop = 0.8 * line   # core/ledger STOP_FRACTION: a reservation past 80 % of the line is refused, so the cap stays under it
            bad += [f"launch caps.{k} ${launch['caps'][k]:g} is above 80 % of the creator's ${line:g} per run (${stop:g})"
                    for k in ("smoke_usd", "run_usd") if launch["caps"][k] > stop + 1e-9]
        except spend_caps.OverCeiling as exc:
            bad.append(str(exc))
    if job is not None:
        if not str(job.get("motion_prompt") or "").strip():
            bad.append(f"{job.get('shot_id')}: no prompt")
        if not float(job.get("seconds") or 0) > 0 or not isinstance(job.get("seed"), int):
            bad.append(f"{job.get('shot_id')}: seconds or seed missing")
        for c in job.get("chain") or []:
            if not str(c.get("motion_prompt") or "").strip() or not float(c.get("seconds") or 0) > 0 \
                    or not isinstance(c.get("seed"), int) or not c.get("shot_id"):
                bad.append(f"{job.get('shot_id')}: a chained shot lacks its shot_id, prompt, seconds or seed")
            elif float(c["seconds"]) > max_seconds(launch):
                bad.append(f"{c['shot_id']}: {c['seconds']} s is longer than the model's {max_seconds(launch):g} s")
        if job.get("end_picture"):
            bad.append(f"{job.get('shot_id')}: an end picture, but the LTX distilled CLI takes only the frame-0 picture")
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


# --- in the container ------------------------------------------------------------------------------------------------------

class DeadlineHit(RuntimeError):
    """The in-container deadline: raised inside the work so the normal end path writes, copies and uploads."""


class Deadline:
    """The in-container clock (bake-off audit A1): ``left()`` seconds until the function must wrap up."""

    def __init__(self, timeout_s, margin_s=MARGIN_S, now=time.time):
        self.now, self.end = now, now() + float(timeout_s) - float(margin_s)

    def left(self) -> float:
        return self.end - self.now()

    def check(self):
        if self.left() <= 0:
            raise DeadlineHit("the in-container deadline came; the job ends cleanly with what it has")


def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def weights_root(launch, vol_root="/w"):
    return Path(vol_root) / "model" / launch["model_repo"]


STAGE_CPU, STAGE_MEM_GIB, STAGE_TIMEOUT_S = 4, 16, 3600   # CPU only, ~$0.32 an hour at the 2026-11-07 table


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


def sizes_ok(launch, vol_root="/w") -> list[str]:
    """The paid function's cheap check: every file there (its full sha256 was proved on L2 for this launch file)."""
    root = weights_root(launch, vol_root)
    return [f"missing {f}" for f in launch["model_files"] if not (root / f).is_file() or (root / f).stat().st_size == 0]


def stage_weights(launch, vol_root="/w", download=None) -> list[str]:
    root = weights_root(launch, vol_root)
    missing = [f for f in launch["model_files"] if not (root / f).is_file()]
    if missing:
        (download or _hf_download)(launch["model_repo"], launch["model_revision"], missing, root)
    return check_weights(launch, vol_root)


def _hf_download(repo, revision, files, root):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), local_dir=str(root), token=_tok())


def import_check(module: str, run=subprocess.run) -> list[str]:
    """L1: torch, ltx_core, the launch's ltx_pipelines module and PIL import on the container's python."""
    code = ("import importlib, sys\nbad = []\nfor m in sys.argv[1:]:\n    try: importlib.import_module(m)\n"
            "    except Exception as e: bad.append(m); print('MISSING', m, repr(e)[:150])\nsys.exit(1 if bad else 0)")
    mods = ["torch", "ltx_core", module, "PIL"]
    r = run([sys.executable, "-c", code, *mods], capture_output=True, text=True)
    print(r.stdout, (r.stderr or "")[-500:], flush=True)
    return [] if r.returncode == 0 else [ln.split()[1] for ln in (r.stdout or "").splitlines() if ln.startswith("MISSING")] or mods


def fit_picture(img, width, height):
    """Centre-crop to the clip's aspect, then Lanczos to its size."""
    from PIL import Image
    w, h = img.size
    if w * height > h * width:
        cw, ch = round(h * width / height), h
    else:
        cw, ch = w, round(w * height / width)
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.convert("RGB").crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


def ltx_cmd(launch, job, picture, mp4, python=None):
    """The LTX-2 CLI of one shot (the bake-off's ``ltx_cmd``): split weights from the Volume, the start picture at frame 0,
    every other setting the CLI's own LTX-2.5 default."""
    root, u = weights_root(launch), launch["uses"]
    cmd = [python or sys.executable, "-m", launch["module"], "--transformer-path", str(root / u["transformer"]),
           "--text-encoder-path", str(root / u["text_encoder"]), "--video-vae-path", str(root / u["video_vae"]),
           "--audio-vae-path", str(root / u["audio_vae"]), "--spatial-upsampler-path", str(root / u["spatial_upsampler"])]
    if u.get("distilled_lora"):
        cmd += ["--distilled-lora", str(root / u["distilled_lora"])]
    cmd += ["--image", str(picture), "0", "1.0", "--prompt", job["motion_prompt"], "--width", str(job["width"]),
            "--height", str(job["height"]), "--num-frames", str(ltx_frames(job["seconds"], job["fps"])),
            "--frame-rate", str(job["fps"]), "--seed", str(job["seed"]), "--output-path", str(mp4)]
    return cmd


def tmp_name(p: Path) -> Path:
    """A temp name that keeps the suffix (imageio and ffmpeg pick the format by it; delta audit N1)."""
    return p.with_name("." + p.name)


def beat(out: Path, job: dict, stage: str, **info):
    (Path(out) / f"{job['shot_id']}.beat.json").write_text(json.dumps(dict(info, stage=stage, at=round(time.time(), 1))))


def git_blob_id(p) -> str:
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _files(root):
    out = []
    for p in sorted(Path(root).rglob("*")):
        try:
            if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".tmp"):
                st = p.stat()
                if st.st_size > 0:
                    out.append((p, (st.st_size, st.st_mtime_ns)))
        except OSError:
            continue
    return out


def upload_round(api, root, prefix, seen: dict, final=False, sleep=time.sleep, op=None, budget_s=None) -> int:
    """One batched commit of every new or changed file; bounded backoff (no sleep past ``budget_s``)."""
    new = [(p, k) for p, k in _files(root) if seen.get(str(p)) != k]
    if not new:
        return 0
    if op is None:
        from huggingface_hub import CommitOperationAdd as op
    ops = [op(path_in_repo=f"{prefix}/{p.relative_to(root).as_posix()}", path_or_fileobj=str(p)) for p, _ in new]
    tries, slept = (5 if final else 2), 0.0
    for k in range(tries):
        try:
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops, commit_message=f"ltx: {len(new)} files")
            seen.update({str(p): key for p, key in new})
            return len(new)
        except Exception as e:  # noqa: BLE001 - retried with backoff; the Volume copy is the safety net
            print("upload failed", repr(e)[:160], flush=True)
            wait = 10.0 * 2 ** k
            if k == tries - 1 or (budget_s is not None and slept + wait > budget_s):
                return 0
            sleep(wait)
            slept += wait
    return 0


def verify_uploads(api, root, prefix) -> dict:
    """Each local file against HF: an LFS file by its sha256, a small one by its git blob id."""
    files = [p for p, _ in _files(root)]
    paths = [f"{prefix}/{p.relative_to(root).as_posix()}" for p in files]
    try:
        info = {i.path: i for i in api.get_paths_info(HF_REPO, paths, repo_type="dataset", expand=True)}
    except Exception as e:  # noqa: BLE001
        return {p.name: f"not checked: {type(e).__name__}" for p in files}
    out = {}
    for p, hp in zip(files, paths):
        i = info.get(hp)
        if i is None:
            out[p.name] = "missing on HF"
            continue
        lfs = getattr(i, "lfs", None)
        want = (lfs.sha256 if hasattr(lfs, "sha256") else (lfs or {}).get("sha256")) if lfs else None
        ok = (want == _sha(p)) if want else (getattr(i, "blob_id", None) == git_blob_id(p))
        out[p.name] = "ok" if ok else "hash differs on HF"
    return out


def libs() -> dict:
    """The library versions, as plain strings (a TorchVersion lost the bake-off's answer on a client without torch)."""
    import importlib
    out = {"python": sys.version.split()[0]}
    for m in ("torch", "ltx_core", "ltx_pipelines", "PIL"):
        try:
            v = getattr(importlib.import_module(m), "__version__", None)
            out[m] = None if v is None else str(v)
        except Exception:  # noqa: BLE001
            out[m] = None
    return out


def attempt_guard(vol_out: Path, job: dict) -> str | None:
    """The first act of the GPU function: a marker per launch nonce on the Volume; a rescheduled input finds it and returns."""
    d = Path(vol_out) / job["run_id"] / job["shot_id"]
    d.mkdir(parents=True, exist_ok=True)
    m = d / f"attempt_{job['nonce']}"
    if m.exists():
        return "REFUSED_SECOND_ATTEMPT"
    m.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return None


def generate(job, launch, out: Path, deadline: Deadline, sh=subprocess.run, tmp="/tmp/in", now=time.time) -> dict:
    """One clip: the start picture fitted to the clip's size, then the CLI as its own process, bounded by the time left."""
    import io
    from PIL import Image
    t0 = now()
    Path(tmp).mkdir(parents=True, exist_ok=True)
    pic = Path(tmp) / f"{job['shot_id']}_{job['width']}x{job['height']}.png"
    fit_picture(Image.open(io.BytesIO(job["start_bytes"])), job["width"], job["height"]).save(pic)
    final = Path(out) / clip_name(job["shot_id"], job["seed"])
    mp4 = tmp_name(final)
    beat(out, job, "generate")
    row = {"frames": ltx_frames(job["seconds"], job["fps"]), "fps": job["fps"]}
    with open(Path(out) / f"{job['shot_id']}.log", "w") as log:
        try:
            row["rc"] = sh(ltx_cmd(launch, job, pic, mp4), stdout=log, stderr=subprocess.STDOUT,
                           cwd=launch.get("code_dir") or "/workspace/LTX-2", timeout=max(1.0, deadline.left())).returncode
        except subprocess.TimeoutExpired:
            row["rc"], row["why"] = None, "the in-container deadline came during the clip"
    row["gen_s"] = round(now() - t0, 1)
    if row["rc"] == 0 and mp4.is_file() and mp4.stat().st_size > 0:
        os.replace(mp4, final)
        row.update(sha256=_sha(final), state="DONE", s_per_clip_s=round(row["gen_s"] / float(job["seconds"]), 2))
    else:
        row["state"] = "PARTIAL" if row["rc"] is None else "FAILED"
    return row


def last_frame(clip: Path, png: Path, sh=subprocess.run) -> bytes:
    """The clip's last frame as a PNG: the start picture of the next chained shot (the scene goes on where it stopped)."""
    sh(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.5", "-i", str(clip), "-update", "1", "-q:v", "1", str(png)],
       check=True, timeout=60)
    return Path(png).read_bytes()


def chain_jobs(job: dict) -> list[dict]:
    """The shot and the shots chained after it (``job["chain"]``): each a full spec of its own, sharing the run, size and
    rate; its start picture is the previous clip's last frame, made in the container."""
    keep = ("run_id", "launch_sha", "plan_sha256", "fps", "width", "height", "nonce", "worker_sha", "commit")
    return [job] + [dict({k: job[k] for k in keep if k in job}, **c) for c in job.get("chain") or []]


def body(job: dict, launch: dict, timeout_s: int, *, vol_root="/w", commit=lambda: None, api=None, sh=subprocess.run,
         now=time.time, out_root=OUT_ROOT) -> dict:
    """The GPU function: attempt marker, weights there, the clip, the Volume copy, the final upload checked on HF."""
    t_in = now()
    vol_out = Path(vol_root) / VOL_OUT
    seen = attempt_guard(vol_out, job)
    if seen:
        return {"state": seen, "shot_id": job["shot_id"], "run_id": job["run_id"], "body_s": round(now() - t_in, 1)}
    commit()
    deadline = Deadline(timeout_s, now=now)
    out = Path(out_root) / job["run_id"] / job["shot_id"]
    out.mkdir(parents=True, exist_ok=True)
    m = {"shot_id": job["shot_id"], "run_id": job["run_id"], "gpu": launch["gpu"], "launch_sha": launch_sha(launch),
         "worker_sha": job.get("worker_sha"), "commit": job.get("commit"), "error": None}
    try:
        if hashlib.sha256(job["start_bytes"]).hexdigest() != job["start_sha256"]:
            raise RuntimeError("the start picture changed in transit")
        if job.get("launch_sha") and job["launch_sha"] != launch_sha(launch):
            raise RuntimeError("the launch file changed between the spec and the container")
        bad = sizes_ok(launch, vol_root)
        if bad:
            raise RuntimeError("weights not on the Volume: " + "; ".join(bad[:5]))
        rows, prev = [], None
        for k, sub in enumerate(chain_jobs(job)):
            if prev is not None:
                if prev.get("state") != "DONE":
                    break
                need = 1.15 * float(prev["gen_s"])           # a warm clip takes no longer than the one before it
                if deadline.left() < need:
                    rows.append({"shot_id": sub["shot_id"], "state": "PARTIAL", "why": f"{deadline.left():.0f} s left, the "
                                 f"clip needs ~{need:.0f} s: not started"})
                    break
                sub = dict(sub, start_bytes=last_frame(out / prev["clip"], out / f"{sub['shot_id']}.start.png", sh=sh))
            row = dict(generate(sub, launch, out, deadline, sh=sh, now=now), shot_id=sub["shot_id"])
            if row.get("state") == "DONE":
                row["clip"] = clip_name(sub["shot_id"], sub["seed"])
            rows.append(row)
            prev = row
        m.update({k: v for k, v in rows[0].items() if k != "shot_id"})
        if job.get("chain"):
            m["chain"] = rows
            if any(r.get("state") != "DONE" for r in rows) and m["state"] == "DONE":
                m["state"] = "PARTIAL"
    except Exception as e:  # noqa: BLE001 - one attempt: the failure is written, copied and returned
        m.update(state="FAILED", error=f"{type(e).__name__}: {str(e)[:300]}")
    m.update(body_s=round(now() - t_in, 1), libs=libs())
    (out / f"{job['shot_id']}.measured.json").write_text(json.dumps(m))
    beat(out, job, m["state"])

    def to_volume():
        try:
            shutil.copytree(out, vol_out / job["run_id"] / job["shot_id"], dirs_exist_ok=True)
            commit()
        except Exception as e:  # noqa: BLE001
            print("volume copy failed", repr(e)[:200], flush=True)
    to_volume()                                  # the Volume first (delta audit N2)
    prefix = f"{launch['hf_out']}/{job['run_id']}/{job['shot_id']}"
    if api is not None:
        upload_round(api, out, prefix, {}, final=True, budget_s=max(0.0, deadline.left() + MARGIN_S - 60))
        m["verified"] = verify_uploads(api, out, prefix)
        if m["state"] == "DONE" and any(v != "ok" for v in m["verified"].values()):
            m["state"] = "UPLOAD_UNVERIFIED"
        (out / f"{job['shot_id']}.verified.json").write_text(json.dumps(m["verified"]))
        to_volume()
    m["body_s"] = round(now() - t_in, 1)
    return json.loads(json.dumps(m, default=str))   # plain JSON only, never a library object


LAUNCH = load_launch()
TIMEOUTS = timeouts(LAUNCH)

if modal is not None:
    app = modal.App(LAUNCH["app_name"])
    vol = modal.Volume.from_name("ee-weights", version=2)
    _code = LAUNCH.get("ltx_code") or {}
    image = (modal.Image.from_registry(LAUNCH.get("base_image") or "python:3.12-slim", add_python="3.12")
             .apt_install("ffmpeg", "git")
             .run_commands(f'pip install -q "huggingface_hub=={LAUNCH.get("hf_hub_pin") or "1.33.0"}"',
                           f"git clone -q {_code.get('repo')} /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q "
                           f"{_code.get('commit')} && pip install -q -e /workspace/LTX-2/packages/ltx-core "
                           "-e /workspace/LTX-2/packages/ltx-pipelines")
             .add_local_file(str(LAUNCH_PATH), "/root/launch.json"))
    secrets = [modal.Secret.from_name(SECRET_NAME)]

    @app.function(image=image, cpu=(2.0, 2.0), memory=(4096, 4096), timeout=300, retries=0, secrets=secrets)
    def env_check(module: str):
        _tok()
        return import_check(module)

    @app.function(image=image, cpu=(2.0, 2.0), memory=(4096, 4096), timeout=1800, retries=0, volumes={"/w": vol})
    def weights_check(launch: dict):
        return check_weights(launch)

    @app.function(image=image, cpu=(float(STAGE_CPU),) * 2, memory=(STAGE_MEM_GIB * 1024,) * 2, timeout=STAGE_TIMEOUT_S,
                  retries=0, volumes={"/w": vol}, secrets=secrets)
    def weights_stage(launch: dict):
        bad = stage_weights(launch)
        vol.commit()
        return bad

    if TIMEOUTS:
        GPU_KW = dict(image=image, gpu=LAUNCH["gpu"] + "!", cpu=(float(LAUNCH["cpu"]),) * 2,
                      memory=(LAUNCH["memory_gib"] * 1024,) * 2, retries=0, volumes={"/w": vol}, secrets=secrets,
                      scaledown_window=LAUNCH["scaledown_window_s"])

        def _remote_body(job, launch, timeout_s):
            from huggingface_hub import HfApi
            vol.reload()
            return body(job, launch, timeout_s, commit=vol.commit, api=HfApi(token=_tok()))

        @app.function(timeout=TIMEOUTS[0], **GPU_KW)
        def ltx_smoke(job: dict, launch: dict):
            return _remote_body(job, launch, TIMEOUTS[0])

        @app.function(timeout=TIMEOUTS[1], **GPU_KW)
        def ltx_main(job: dict, launch: dict):
            return _remote_body(job, launch, TIMEOUTS[1])

    @app.local_entrypoint()
    def check():
        ladder_gate("L1")
        bad = launch_problems(LAUNCH)
        if bad:
            raise SystemExit("the launch file is not pinned:\n" + "\n".join(bad))
        missing = env_check.remote(LAUNCH["module"])
        print("env_check", missing or "imports ok")
        record("L1", not missing, missing=missing)

    @app.local_entrypoint()
    def stage(plan: str = ""):
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
        nat = native_spec(LAUNCH, SMOKE_JOB["seconds"])
        job = dict(SMOKE_JOB, fps=nat["fps"], width=nat["width"], height=nat["height"], start_bytes=pic,
                   start_sha256=hashlib.sha256(pic).hexdigest(), run_id=run_id(plan_sha, LAUNCH), launch_sha=launch_sha(LAUNCH),
                   worker_sha=worker_sha(), nonce=uuid.uuid4().hex[:12])
        res = ltx_smoke.remote(job, LAUNCH)
        print("result", json.dumps(res))
        ok = res.get("state") == "DONE"
        record("L3", ok, measured={"gpu": res.get("gpu"), "s_per_clip_s": res.get("s_per_clip_s"),
                                   "setup_s": round(max(0.0, float(res.get("body_s") or 0) - float(res.get("gen_s") or 0)), 1),
                                   "body_s": res.get("body_s")} if ok else None,
               result={k: res.get(k) for k in ("state", "error")})

    @app.local_entrypoint()
    def main(job: str = ""):
        spec = read_job(job)
        preflight(LAUNCH, spec)
        print("GO card", go_gate(plan_sha=spec["plan_sha256"]), "timeout", TIMEOUTS[1], "s", flush=True)
        ladder_gate("L4")
        res = ltx_main.remote(dict(spec, worker_sha=worker_sha(), nonce=uuid.uuid4().hex[:12]), LAUNCH)
        print("result", json.dumps(res))
        if res.get("state") != "DONE":   # a FAILED clip is a non-zero exit, never a 0
            print(LTX_FAILED, flush=True)
            raise SystemExit(4)
