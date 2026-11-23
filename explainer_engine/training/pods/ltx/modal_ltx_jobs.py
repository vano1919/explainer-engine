"""LTX-2.5 distilled clips on Modal: the video route of a v4.3 episode (D-132, the creator 2026-11-12 19:10 UTC, after the
bake-off run fae4ee9fb9d2_5dd040ac95c8). The bake-off's LTX job (``training/pods/bakeoff/modal_bakeoff.py``: ``ltx_cmd``,
``make_ltx``, the clean deadline, the attempt marker, the Volume copy before the last HF flush) made a production job on the
contract of the Wan worker (``training/pods/wan/modal_wan_jobs.py``). The video lane drives it (D-137): ``videolane/scene``
writes the scene file (one row per clip, its prompt from ``scene.compose_prompt``), ``training/pods/ltx/scene_run job`` turns
it into the ``--job`` spec (the first shot, the others as its ``chain``) and ``scene_run reserve`` opens the ledger line.

One scene per launch (D-133 CH-03): ``modal run modal_ltx_jobs.py::main --job <spec>``, a plain Bash command the session hook
reads, priced from the speed measured on L3 and reserved in the run's ledger before it is sent. The OR-37 ladder, each rung recorded in the ladder file
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

Two runners (``launch.runner``, the creator's cheaper-video question 2026-11-13 06:40 UTC): ``cli`` runs the LTX-2 CLI once
per clip, so every clip loads Gemma 12B, builds the 22B transformer twice and decodes (the battle run: ~82 s a clip, ~17 s of it
denoising); ``inproc`` (``LtxSession``) runs the CLI's own ``main`` body in this process on one pipeline: every prompt of the
shot and its chain encoded in one Gemma load, the transformer built once and held (``DiffusionStage.resident``) for all
clips, the deadline checked before each denoising pass.

The clip carries LTX's own sound (speech and effects, the creator 2026-11-12 19:12 UTC): the prompt ``videolane/scene``
composes holds the scene, the spoken words in the speaker's one voice text (Q5) and the sounds.

P5 (the creator 2026-11-13 18:15 Georgia time, before the demo): a continuation is handed over only after the clip before has
finished its line (``handover_frame``: the row's ``speech_end_s`` + ``speech_tail_s``, BP-187; no such frame = the chain stops,
never a cut inside the speech), and a clip the model fails to make is retried once with ``seed + SEED_STEP`` inside the same
container and deadline (``body``, the row's ``attempts``)."""
import hashlib, json, logging, math, os, re, shutil, subprocess, sys, threading, time, uuid
from contextlib import ExitStack
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
LAUNCH_PATH = Path(__file__).with_name("launch.json")
LADDER_PATH = Path(os.environ.get("EE_LTX_LADDER") or Path(__file__).with_name("ladder.json"))
NIGHT_LEDGER = Path(os.environ.get("EE_NIGHT_LEDGER") or
                    "/mnt/project-files/explainer-engine/final_plan_2026-11-19/modal_stage/NIGHT_LEDGER_2026-11-19.json")
SECRET_NAME = "custom-secret"   # the owner's second Modal account holds his HF token under this name (his message 2026-11-19 20:41 UTC, plan thread 21:36 UTC); the key inside is HF_TOKEN
PINS = ("model_repo", "model_revision", "model_files", "ltx_code", "module", "uses", "hf_out", "scaledown_window_s",
        "base_image")
USES = ("transformer", "text_encoder", "video_vae", "audio_vae", "spatial_upsampler")
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
LTX_FAILED = "LTX_FAILED"   # printed by ::main when the model ran and made no clip (the adapter may retry once, new seed)
MARGIN_S = 75               # the end path after the last step: Volume copy, final upload, HF check (each clip is
                            # already saved on the Volume and HF when it is made; the love run's whole overhead was 30.5 s)
OUT_ROOT = Path("/workspace/out")
VOL_OUT = "out_ltx"
SEED_STEP = 1001            # the same step as aivideo/wan_adapter.SEED_STEP (RT-07); no repo import inside the container
CLIP_RETRIES = 1            # P5: one more attempt of a clip the model failed to make (wan_adapter.MAX_ATTEMPTS - 1)
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
    if not (isinstance(launch.get("chain_overlap_frames"), int) and launch["chain_overlap_frames"] >= 0):
        out.append("launch chain_overlap_frames (BP-187 audio_overlap_s x fps) is not set")
    st = launch.get("startup_timeout_s")
    if not (isinstance(st, int) and 30 <= st <= caps.get("cold_start_s", 0)):
        out.append("launch startup_timeout_s must be set and no longer than caps.cold_start_s (a hung start bills it)")
    if runner_of(launch) not in RUNNERS:
        out.append(f"launch runner must be one of {RUNNERS}")
    out += native_problems(launch)
    out += kind_launch_problems(launch)
    return out


def kind_launch_problems(launch: dict) -> list[str]:
    """W5: when the launch pins extra files for the job kinds, each has a 64-hex sha256 and ``kind_uses`` names only those."""
    kf, ku = launch.get("kind_model_files"), launch.get("kind_uses")
    if kf is None and ku is None:
        return []
    out = [f"launch kind_model_files {f} has no sha256" for f, h in (kf or {}).items() if not HEX64.match(str(h))]
    out += [f"launch kind_uses.{r} is not one of kind_model_files" for r, f in (ku or {}).items() if f not in (kf or {})]
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


PAINTERLY_NEGATIVE_PROMPT = (
    "blurry, out of focus, overexposed, underexposed, low contrast, washed out colors, excessive noise, "
    "grainy texture, poor lighting, flickering, motion blur, distorted proportions, unnatural skin tones, "
    "deformed facial features, asymmetrical face, extra limbs, disfigured hands, extra fingers, fused fingers, "
    "missing fingers, bad anatomy, warped geometry, jitter, camera shake, text, watermark, subtitle, logo, "
    "signature, compression artifacts, macroblocking"
)
FORBIDDEN_PAINTERLY_NEGATIVE_TERMS = (
    "cartoonish rendering",
    "cartoonish",
    "3d cgi look",
    "3d cgi",
    "illustration",
    "painting",
    "painted",
    "2d",
)


def sanitize_painterly_negative_prompt(neg_prompt: str | None) -> str:
    """P0-8 (R1): Strip anti-painterly / anti-illustration terms ('cartoonish rendering', '3D CGI look', 'illustration',
    'painting', '2D') from an LTX negative prompt while preserving anatomical, glitch, jitter, and watermark exclusions."""
    raw = str(neg_prompt or PAINTERLY_NEGATIVE_PROMPT).strip()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    cleaned: list[str] = []
    for p in parts:
        low = p.lower()
        if any(bad in low for bad in FORBIDDEN_PAINTERLY_NEGATIVE_TERMS):
            continue
        cleaned.append(p)
    joined = ", ".join(cleaned)
    for req in ("deformed facial features", "extra fingers", "flickering", "watermark", "jitter"):
        if req not in joined.lower():
            cleaned.append(req)
    return ", ".join(cleaned)


def resolve_negative_prompt(launch: dict | None = None, job: dict | None = None, style_preset: dict | None = None) -> str:
    """Resolve the painterly-safe negative prompt from job, style_preset, or launch config."""
    raw = (
        (job or {}).get("negative_prompt")
        or (style_preset or {}).get("ltx_negative_prompt")
        or (launch or {}).get("negative_prompt")
        or PAINTERLY_NEGATIVE_PROMPT
    )
    return sanitize_painterly_negative_prompt(raw)


def native_spec(launch: dict, seconds: float, *, resolution_override: tuple[int, int] | list[int] | None = None) -> dict:
    """The clip the model makes for a shot of ``seconds``: its own rate and the launch's size (or an A/B resolution override
    from ``launch['native']['sizes']`` under P1-9/R2), 8k+1 frames; a shot longer than the longest proven clip raises ValueError."""
    n = launch["native"]
    frames = ltx_frames(seconds, n["fps"])
    if frames > n["max_frames"]:
        raise ValueError(f"{seconds:g} s is {frames} frames at {n['fps']} fps, past the longest clip of {n['max_frames']} "
                         f"frames ({max_seconds(launch):.2f} s): split the shot in the script")
    use_wh = list(resolution_override) if resolution_override is not None else list(n.get("ab_use") or n["use"])
    if use_wh not in n["sizes"]:
        raise ValueError(f"resolution {use_wh} is not in launch native.sizes {n['sizes']}")
    return {"fps": n["fps"], "width": use_wh[0], "height": use_wh[1], "frames": frames}


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


def kind_l2_problems(job: dict, launch: dict, ladder: dict) -> list[str]:
    """A guided kind job (kind_needs) runs only when L2 was proved WITH the guided files (``::weights --with-kind``) on this very
    launch file: otherwise its dev transformer and LoRA would meet only the size check inside the billed GPU function."""
    need = tuple(dict.fromkeys(r for j in all_jobs(job) for r in kind_needs(j)))
    if not need:
        return []
    l2 = (ladder.get("rungs") or {}).get("L2") or {}
    if "L2" in (ladder.get("done") or []) and l2.get("ok") and l2.get("with_kind") is True \
            and l2.get("launch_sha") == launch_sha(launch):
        return []
    return [f"{'+'.join(sorted({kind_of(j) for j in all_jobs(job) if kind_needs(j)}))}: needs {list(need)} proved by an L2 record made with --with-kind on this launch file "
            "(run `::stage --with-kind` then `::weights --with-kind`); nothing was started"]


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
    chain = []
    for c in job.get("chain") or []:
        if c.get("start_picture"):                    # a shot with its own picture (a cut, not a continuation)
            own = Path(c["start_picture"]).read_bytes()
            pin = (c.get("extra") or {}).get("start_sha256")
            if not pin or pin != hashlib.sha256(own).hexdigest():
                raise SystemExit(f"{c.get('shot_id')}: its own start picture is not the one the pictures stage pinned; "
                                 "nothing was started")
            c = dict(c, start_sha256=pin, start_bytes=own)
        if c.get("end_picture"):                      # a chained keyframes shot: its end keyframe, pinned like the top job's
            end_c = Path(c["end_picture"]).read_bytes()
            if (c.get("extra") or {}).get("end_sha256") != hashlib.sha256(end_c).hexdigest():
                raise SystemExit(f"{c.get('shot_id')}: its end picture's sha256 is not the one the pictures stage pinned; "
                                 "nothing was started")
            c = dict(c, end_bytes=end_c)
        chain.append(c)
    if job.get("chain"):
        job["chain"] = chain
    out = dict(job, start_sha256=sha, start_bytes=pic)
    if job.get("end_picture"):                        # W5 keyframes: the end keyframe, pinned like the start
        end = Path(job["end_picture"]).read_bytes()
        if (job.get("extra") or {}).get("end_sha256") != hashlib.sha256(end).hexdigest():
            raise SystemExit(f"{job['shot_id']}: the end picture's sha256 is not the one the pictures stage pinned; "
                             "nothing was started")
        out["end_bytes"] = end
    return out


BAKED_LAUNCH = Path("/root/launch.json")   # the launch file the image was built with (``add_local_file`` below)


def container_gate(job: dict, launch: dict, baked=BAKED_LAUNCH) -> list[str]:
    """D-133's last line, inside the paid container before any model loads (a ``.remote()`` from custom code skips the hook and
    the local entrypoints). No repo import here: the image holds only this file and the launch file. CH-01, CH-02 and CH-04
    against the launch baked into the image; a rule is skipped only when the local entrypoint passed the creator's recorded
    waiver in ``job["cheapest_waive"]``. CH-03 needs the committed scenes and stays with the hook and ``::main``."""
    bad = []
    baked = Path(baked)
    if baked.exists() and json.loads(baked.read_text(encoding="utf-8")) != launch:
        bad.append("the launch passed in is not the launch file baked into the image")
    off = set(job.get("cheapest_waive") or ())
    if "CH-01" not in off and launch.get("runner") != "inproc":
        bad.append("CH-01: the launch must run in process (runner inproc)")
    nat = launch.get("native") or {}
    if "CH-02" not in off:
        if nat.get("use") != [1280, 704] or nat.get("fps") != 24:
            bad.append(f"CH-02: native.use {nat.get('use')} @ {nat.get('fps')}, not 1280x704@24")
        for j in [job] + [c for c in job.get("chain") or [] if isinstance(c, dict)]:
            size = [j.get("width", job.get("width")), j.get("height", job.get("height"))]
            if size != nat.get("use") or j.get("fps", job.get("fps")) != nat.get("fps"):
                bad.append(f"CH-02: {j.get('shot_id')} asks {size[0]}x{size[1]}@{j.get('fps', job.get('fps'))}")
    sd = launch.get("scaledown_window_s")
    if "CH-04" not in off and not (isinstance(sd, int) and sd <= 5):
        bad.append(f"CH-04: scaledown_window_s {sd} is above 5 s")
    return bad


def waivers() -> list[str]:
    """The creator's recorded waivers for this run (D-133), carried into the job for ``container_gate``."""
    from explainer_engine.cloud import cheapest
    return sorted(cheapest.waived()[1])


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
        for j in all_jobs(job):                       # the chained shots too (N2 of the audit of 2026-11-19)
            if j.get("end_picture") and kind_of(j) != "keyframes":
                bad.append(f"{j.get('shot_id')}: an end picture, but only the keyframes kind takes one (the distilled CLI takes "
                           "the frame-0 picture)")
        if any(kind_of(j) != "clip" for j in all_jobs(job)):
            pins = None
            try:
                pins = json.loads((Path(__file__).resolve().parents[4] / "config" / "cloud_pins.json").read_text(
                    encoding="utf-8"))["models"]["video_ltx"]
            except (OSError, KeyError, ValueError):
                bad.append("config/cloud_pins.json (models.video_ltx) cannot be read: the kind's extra files are not proved")
            for j in all_jobs(job):                   # every shot's kind is checked, the chained ones too
                if kind_of(j) != "clip":
                    sub = dict(j, **{k: job[k] for k in ("fps", "width", "height") if k not in j})
                    bad += kind_problems(launch, sub, pins)
    from explainer_engine.cloud import cheapest        # D-133: the cheapest known combination (CH-01, CH-02, CH-04)
    why = cheapest.problems_text(cheapest.launch_problems(launch))
    if why:
        bad.append(why)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def _ledger(spec: dict):
    from explainer_engine.core.ledger import Run
    led = spec.get("ledger") or {}
    if not (led.get("path") and led.get("service") and led.get("item")):
        raise SystemExit(f"{spec.get('shot_id')}: the spec names no ledger (path, service, item); nothing was started (D-56)")
    return Run.open(led["path"]), led


def hard_bill_usd(launch: dict, timeout_s: float) -> float:
    """The most one launch can bill: the function's hard timeout plus the cold start, at the card's rate."""
    return round((float(timeout_s) + float(launch["caps"]["cold_start_s"])) * usd_per_h(launch) / 3600.0, 4)


def night_reserve(item: str, usd: float, why: str = "", path=None) -> None:
    """The creator's night total (``config/spend_caps.json`` modal.night_total_usd, 2026-11-19 22:25 UTC): while that line exists, a
    paid launch reserves its hard bill in the night ledger BEFORE the GPU function is called and is refused past the total or with
    no ledger (``cloud/night_budget``). Without the line the night rule does not apply and nothing is done."""
    from explainer_engine.core import spend_caps
    from explainer_engine.cloud import night_budget as NB
    cfg = spend_caps.load()
    has_night = isinstance((cfg.get("modal") or {}).get("night_total_usd"), (int, float))
    has_env = "modal_modal1" in ((cfg.get("orchestration_envelopes") or {}).get("services") or {})
    if not (has_night or has_env):
        return
    try:
        NB.reserve(path or NIGHT_LEDGER, item, usd, why)
    except NB.NightCapExceeded as exc:
        raise SystemExit(f"night total: {exc}; nothing was started") from None


def night_settle(item: str, usd: float, path=None) -> None:
    """After the launch: the wall clock at the rate replaces the reservation (a failure to settle is printed, never hides the run)."""
    from explainer_engine.core import spend_caps
    from explainer_engine.cloud import night_budget as NB
    cfg = spend_caps.load()
    has_night = isinstance((cfg.get("modal") or {}).get("night_total_usd"), (int, float))
    has_env = "modal_modal1" in ((cfg.get("orchestration_envelopes") or {}).get("services") or {})
    if not (has_night or has_env):
        return
    try:
        NB.settle(path or NIGHT_LEDGER, item, usd)
    except NB.NightCapExceeded as exc:
        print("NIGHT LEDGER SETTLE FAILED:", exc, flush=True)


def claim_launch(spec: dict, now=time.time) -> None:
    """Before ``.remote()`` (audit B2, bake-off A3): this spec's reservation is in the ledger and open, and no launch of it is
    marked; then the launch mark is written, so a second ``main`` of the same spec is refused even if the first one died."""
    run, led = _ledger(spec)
    r = run.data.get("reserved", {}).get(led["item"])
    if not r or r.get("settled") or r.get("service") != led["service"]:
        raise SystemExit(f"{led['item']}: no open {led['service']} reservation in {led['path']}; reserve first (scene_run "
                         "reserve); nothing was started")
    if led["item"] in run.data.get("items", {}).get("launch", {}):
        raise SystemExit(f"{led['item']}: this spec was launched already ({run.data['items']['launch'][led['item']]}); a "
                         "repeat would pay twice; nothing was started")
    run.done("launch", led["item"], at=round(now(), 1), reserved_usd=r["amount"])


def settle_launch(spec: dict, wall_s: float, launch: dict | None = None) -> float:
    """After ``.remote()`` returned or raised: the launch's own wall clock at the GPU rate, an upper bound of the bill."""
    lf = LAUNCH if launch is None else launch
    run, led = _ledger(spec)
    usd = round(max(0.0, float(wall_s)) * usd_per_h(lf) / 3600.0, 4)
    run.settle(led["service"], led["item"], usd)
    return usd


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


def weights_root(launch, vol_root=None):
    """Where the pinned files live: the Modal Volume (``/w``), or ``$EE_LTX_VOL_ROOT`` on a RunPod pod (runpod_ltx_jobs)."""
    return Path(vol_root or os.environ.get("EE_LTX_VOL_ROOT") or "/w") / "model" / launch["model_repo"]


STAGE_CPU, STAGE_MEM_GIB, STAGE_TIMEOUT_S = 4, 16, 3600   # CPU only, ~$0.32 an hour at the 2026-11-07 table


def all_jobs(job: dict) -> list[dict]:
    """The job and the shots chained after it, each a spec of its own (``chain_jobs`` adds the shared run keys at run time)."""
    return [job] + [c for c in job.get("chain") or [] if isinstance(c, dict)]


def needed_files(launch, job=None, with_kind=False) -> dict:
    """The pinned files to stage or check: the clip route's model_files always; the guided kinds' kind_model_files only for a job
    whose kind needs them (kind_needs) or when ``with_kind`` asks for all of them (staging the guided files, ~45 GB, on purpose)."""
    out = dict(launch.get("model_files") or {})
    kf, ku = launch.get("kind_model_files") or {}, launch.get("kind_uses") or {}
    if with_kind:
        out.update(kf)
    elif job is not None:
        for j in all_jobs(job):                       # the top job and every chained shot (a keyframes shot can be chained)
            for role in kind_needs(j):
                f = ku.get(role)
                out[f if f else f"<kind_uses.{role} unpinned>"] = kf.get(f, "")
    return out


def check_weights(launch, vol_root="/w", job=None, with_kind=False) -> list[str]:
    """L2: every model file of the launch on the Volume with its sha256 (the paid function never downloads weights)."""
    root, bad = weights_root(launch, vol_root), []
    for f, want in needed_files(launch, job, with_kind).items():
        p = root / f
        if not p.is_file():
            bad.append(f"missing {f}")
        elif _sha(p) != want:
            bad.append(f"sha256 mismatch {f}")
    return bad


def sizes_ok(launch, vol_root="/w", job=None) -> list[str]:
    """The paid function's cheap check: every file there (its full sha256 was proved on L2 for this launch file); a guided kind job
    also needs its dev transformer and distilled LoRA, a clip job does not."""
    root = weights_root(launch, vol_root)
    return [f"missing {f}" for f in needed_files(launch, job) if not (root / f).is_file() or (root / f).stat().st_size == 0]


def stage_weights(launch, vol_root="/w", download=None, with_kind=False) -> list[str]:
    root = weights_root(launch, vol_root)
    missing = [f for f in needed_files(launch, None, with_kind) if not (root / f).is_file()]
    if missing:
        (download or _hf_download)(launch["model_repo"], launch["model_revision"], missing, root)
    return check_weights(launch, vol_root, None, with_kind)


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


def fit_picture(img, width, height, face_box=None, headroom: float = 0.35):
    """Crop to the clip's aspect (preserving ``face_box`` and its top ``headroom`` when given, Audit #8), then Lanczos to its size."""
    from PIL import Image
    w, h = img.size
    if w * height > h * width:
        cw, ch = round(h * width / height), h
    else:
        cw, ch = w, round(w * height / width)
    left, top = (w - cw) // 2, (h - ch) // 2
    if face_box is not None and w > 0 and h > 0:
        from explainer_engine.finish.superres import crop_box_for_face
        box = [left / w, top / h, (left + cw) / w, (top + ch) / h]
        adj = crop_box_for_face(box, face_box, headroom=headroom)
        left = int(round(adj[0] * w))
        top = int(round(adj[1] * h))
        left = max(0, min(w - cw, left))
        top = max(0, min(h - ch, top))
    return img.convert("RGB").crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


def ltx_cmd(launch, job, picture, mp4, python=None):
    """The LTX-2 CLI of one shot (the bake-off's ``ltx_cmd``): split weights from the Volume, the start picture at frame 0,
    and an explicit painterly-safe ``--negative-prompt`` (P0-8/R1) so LTX-2's default 'cartoonish rendering' / '3D CGI look'
    negative prompt never suppresses our illustrated brushwork."""
    root, u = weights_root(launch), launch["uses"]
    neg = resolve_negative_prompt(launch, job)
    cmd = [python or sys.executable, "-m", launch["module"], "--transformer-path", str(root / u["transformer"]),
           "--text-encoder-path", str(root / u["text_encoder"]), "--video-vae-path", str(root / u["video_vae"]),
           "--audio-vae-path", str(root / u["audio_vae"]), "--spatial-upsampler-path", str(root / u["spatial_upsampler"])]
    if u.get("distilled_lora"):
        cmd += ["--distilled-lora", str(root / u["distilled_lora"])]
    # the distilled CLI has no CFG and takes no --negative-prompt (L3 on 2026-11-19 22:46: "unrecognized arguments")
    cmd += ["--image", str(picture), "0", "1.0", "--prompt", job["motion_prompt"],
            "--width", str(job["width"]), "--height", str(job["height"]),
            "--num-frames", str(ltx_frames(job["seconds"], job["fps"])),
            "--frame-rate", str(job["fps"]), "--seed", str(job["seed"]), "--output-path", str(mp4)]
    return cmd

RUNNERS = ("cli", "inproc")
# The arguments that build the pipeline: equal for every clip of one session, or the session refuses the clip.
MODEL_ARGS = ("model_paths", "spatial_upsampler_path", "lora", "quantization", "compile", "offload_mode",
              "prompt_enhancer_gemma_root", "diffvae_optimization", "marker_root_path")
PROMPT_GROUP = 4             # prompts per Gemma forward (each is padded to 1024 tokens, so a group is one [N, 1024] batch)


def runner_of(launch: dict) -> str:
    """``cli``: one LTX-2 CLI process per clip (every clip loads Gemma, builds the transformer twice and decodes); ``inproc``:
    one pipeline per container, every prompt of the shot and its chain encoded in one Gemma load, the transformer built
    once and held for every clip (``DiffusionStage.resident``, as LTX-2's own multi-GPU pipeline does)."""
    return launch.get("runner") or "cli"


def ltx_argv(launch, job, picture, mp4) -> list[str]:
    """The CLI's own arguments of one clip (``ltx_cmd`` without the interpreter): the in-process runner parses exactly these
    with the CLI's own parser, so both runners read the same settings."""
    return ltx_cmd(launch, job, picture, mp4)[3:]


# --- W5 job kinds (final plan 2026-11-19, P-6, CT-2): the other official Lightricks pipelines ------------------------------
# Verified at the pinned LTX-2 commit (launch ``ltx_code``, docs/LTX_PIPELINES.md quotes file and line): each module below exists
# and has a CLI ``main``. Anything not in this table is not built (never an invented API). The default kind ``clip`` is the
# distilled CLI above and is untouched.
KIND_PIPELINES = {
    "keyframes": {"module": "ltx_pipelines.ti2vid_two_stages", "cls": "TI2VidTwoStagesPipeline",
                  "src": "packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages.py:108",
                  "needs": ("dev_transformer", "distilled_lora"), "images": 2},
    "upscale_x2": {"module": "ltx_pipelines.ti2vid_two_stages", "cls": "TI2VidTwoStagesPipeline",
                   "src": "packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages.py:108",
                   "needs": ("dev_transformer", "distilled_lora"), "images": 1},
    "retake": {"module": "ltx_pipelines.retake", "cls": "RetakePipeline",
               "src": "packages/ltx-pipelines/src/ltx_pipelines/retake.py:56", "needs": (), "images": 0},
    "a2v": {"module": "ltx_pipelines.a2vid_two_stage", "cls": "A2VidPipelineTwoStage",
            "src": "packages/ltx-pipelines/src/ltx_pipelines/a2vid_two_stage.py:113",
            "needs": ("dev_transformer", "distilled_lora"), "images": 1},
}
KIND_SETTINGS = ("num_inference_steps", "video_cfg_guidance_scale", "video_stg_guidance_scale",
                 "distilled_lora_strength_stage_1", "distilled_lora_strength_stage_2")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def kind_of(job: dict) -> str:
    return str(job.get("kind") or "clip")


def distilled_engine(job: dict) -> bool:
    """``keyframes`` with ``engine: distilled``: the launch's own distilled pipeline (the one a clip uses, its stage 2 already
    runs the pinned x2 upsampler: ltx_pipelines/distilled.py:164-214, 484) with the end picture bound as a ``guide`` at its
    pixel-frame index. No dev transformer, no CFG: isolates the end keyframe from the guided pipeline. Default engine: guided."""
    return kind_of(job) == "keyframes" and job.get("engine") == "distilled"


def kind_needs(job: dict) -> tuple:
    return () if distilled_engine(job) or kind_of(job) not in KIND_PIPELINES else KIND_PIPELINES[kind_of(job)]["needs"]


def kind_problems(launch: dict, job: dict, pins: dict | None = None) -> list[str]:
    """Free check of a non-``clip`` job: the kind is built, every extra file is pinned by sha256 (and equals ``pins`` =
    config/cloud_pins.json ``models.video_ltx`` when given), the upsampler is the pinned one, the settings are written out
    (never the CLI's silent defaults), frames and size are native, and the conditioning pictures are pinned."""
    kind = kind_of(job)
    if kind == "clip":
        return []
    if kind not in KIND_PIPELINES:
        return [f"job kind {kind!r} is not built (built: clip, {', '.join(KIND_PIPELINES)})"]
    spec, bad = KIND_PIPELINES[kind], []
    files, uses, kfiles = launch.get("model_files") or {}, launch.get("uses") or {}, launch.get("kind_model_files") or {}
    kuses = launch.get("kind_uses") or {}
    if kind == "keyframes" and job.get("engine") not in (None, "guided", "distilled"):
        bad.append(f"keyframes: engine {job.get('engine')!r} is not built (guided or distilled)")
    for role in kind_needs(job):
        f = kuses.get(role)
        if not f or f not in kfiles or not HEX64.match(str(kfiles[f])):
            bad.append(f"{kind}: launch kind_uses.{role} is not a pinned file (needs a name and its sha256 in kind_model_files)")
    if not (uses.get("spatial_upsampler") in files and HEX64.match(str(files.get(uses.get("spatial_upsampler"), "")))):
        bad.append(f"{kind}: the pinned spatial upsampler (uses.spatial_upsampler) is not in model_files with a sha256")
    if pins is not None:
        want = pins.get("sha256_files") or {}
        for f, h in {**files, **kfiles}.items():
            if f in kfiles or f == uses.get("spatial_upsampler"):
                if want.get(f) != h:
                    bad.append(f"{kind}: {f} sha256 is not the one in config/cloud_pins.json models.video_ltx")
        if pins.get("revision") != launch.get("model_revision"):
            bad.append(f"{kind}: launch model_revision is not config/cloud_pins.json's models.video_ltx.revision")
    for forbidden in ("checkpoint_path", "transformer_path", "lora", "loras", "distilled_lora", "spatial_upsampler_path"):
        if job.get(forbidden):
            bad.append(f"{kind}: the job names its own {forbidden}: files come only from the launch pins")
    st = job.get("settings") or {}
    bad += [f"{kind}: settings.{k} is not written out (the run record holds every setting)" for k in KIND_SETTINGS
            if kind != "retake" and not distilled_engine(job) and not _num(st.get(k))]
    if kind == "retake":
        if st:
            bad.append("retake: takes no settings (the distilled retake CLI is run with its own defaults; none is passed)")
        src = job.get("source") or {}
        if not (src.get("hf_path") and HEX64.match(str(src.get("sha256") or ""))):
            bad.append("retake: source needs hf_path and the sha256 of the clip to regenerate")
        t0, t1 = job.get("start_time"), job.get("end_time")
        if not (isinstance(t0, (int, float)) and isinstance(t1, (int, float)) and 0 <= t0 < t1):
            bad.append("retake: start_time < end_time (seconds) are required")
    if kind == "a2v":
        au = job.get("audio") or {}
        if not (au.get("hf_path") and HEX64.match(str(au.get("sha256") or ""))):
            bad.append("a2v: audio needs hf_path and its sha256")
    if kind != "retake":
        frames = ltx_frames(float(job.get("seconds") or 0), int(job.get("fps") or 0) or 24)
        nat = launch.get("native") or {}
        if frames > int(nat.get("max_frames") or 0):
            bad.append(f"{kind}: {frames} frames are longer than the model's {nat.get('max_frames')}")
        if [job.get("width"), job.get("height")] != nat.get("use"):
            bad.append(f"{kind}: size {job.get('width')}x{job.get('height')} is not native {nat.get('use')}")
        if kind == "keyframes":
            e = job.get("end_frame")
            if not job.get("end_picture") or not HEX64.match(str((job.get("extra") or {}).get("end_sha256") or "")):
                bad.append("keyframes: needs end_picture pinned by extra.end_sha256 (start+end keyframes)")
            if not (isinstance(e, int) and 1 <= e <= frames - 1):
                bad.append(f"keyframes: end_frame must be a pixel-frame index in 1..{frames - 1}")
        elif job.get("end_picture"):
            bad.append(f"{kind}: takes no end picture")
    return bad


def kind_conditioning(job: dict, frames: int) -> list[dict]:
    """The conditioning stills of a kind job, written as the pipeline takes them (``--image PATH FRAME_IDX STRENGTH BINDING``,
    args.py ImageAction): the start replaces frame 0, the end is a ``guide`` at its pixel-frame index."""
    st = job.get("settings") or {}
    out = [{"role": "start", "frame": 0, "strength": float(st.get("image_strength", 1.0)), "binding": "replace",
            "sha256": job.get("start_sha256")}]
    if kind_of(job) == "keyframes":
        out.append({"role": "end", "frame": int(job["end_frame"]), "strength": float(st.get("end_image_strength", 1.0)),
                    "binding": "guide", "sha256": (job.get("extra") or {}).get("end_sha256")})
    return out


def kind_cmd(launch, job, start_png, mp4, end_png=None, source=None, audio=None, python=None) -> list[str]:
    """The official CLI of one kind job, every file from the launch pins, every setting from the job (written out)."""
    kind = kind_of(job)
    spec, root, u, ku = KIND_PIPELINES[kind], weights_root(launch), launch["uses"], launch.get("kind_uses") or {}
    st = job.get("settings") or {}
    neg = resolve_negative_prompt(launch, job)
    if distilled_engine(job):
        frames = ltx_frames(job["seconds"], job["fps"])
        cmd = [python or sys.executable, "-m", launch["module"], "--transformer-path", str(root / u["transformer"]),
               "--text-encoder-path", str(root / u["text_encoder"]), "--video-vae-path", str(root / u["video_vae"]),
               "--audio-vae-path", str(root / u["audio_vae"]), "--spatial-upsampler-path", str(root / u["spatial_upsampler"])]
        paths = {"start": start_png, "end": end_png}
        for c in kind_conditioning(job, frames):
            cmd += ["--image", str(paths[c["role"]]), str(c["frame"]), str(c["strength"]), c["binding"]]
        return cmd + ["--prompt", job["motion_prompt"], "--width", str(job["width"]),   # distilled CLI: no --negative-prompt
                      "--height", str(job["height"]), "--num-frames", str(frames), "--frame-rate", str(job["fps"]),
                      "--seed", str(job["seed"]), "--output-path", str(mp4)]
    cmd = [python or sys.executable, "-m", spec["module"], "--text-encoder-path", str(root / u["text_encoder"]),
           "--video-vae-path", str(root / u["video_vae"]), "--audio-vae-path", str(root / u["audio_vae"])]
    if kind == "retake":
        cmd += ["--transformer-path", str(root / u["transformer"]),
                "--video-path", str(source), "--start-time", str(job["start_time"]), "--end-time", str(job["end_time"]),
                "--prompt", job["motion_prompt"], "--seed", str(job["seed"]), "--output-path", str(mp4)]
        return cmd
    cmd += ["--transformer-path", str(root / ku["dev_transformer"]),
            "--spatial-upsampler-path", str(root / u["spatial_upsampler"]),
            "--distilled-lora", str(root / ku["distilled_lora"]),
            "--distilled-lora-strength-stage-1", str(st["distilled_lora_strength_stage_1"]),
            "--distilled-lora-strength-stage-2", str(st["distilled_lora_strength_stage_2"]),
            "--num-inference-steps", str(int(st["num_inference_steps"])),
            "--video-cfg-guidance-scale", str(st["video_cfg_guidance_scale"]),
            "--video-stg-guidance-scale", str(st["video_stg_guidance_scale"])]
    frames = ltx_frames(job["seconds"], job["fps"])
    cond = kind_conditioning(job, frames)
    paths = {"start": start_png, "end": end_png}
    for c in cond:
        cmd += ["--image", str(paths[c["role"]]), str(c["frame"]), str(c["strength"]), c["binding"]]
    cmd += ["--prompt", job["motion_prompt"], "--negative-prompt", neg, "--width", str(job["width"]),
            "--height", str(job["height"]), "--num-frames", str(frames), "--frame-rate", str(job["fps"]),
            "--seed", str(job["seed"]), "--output-path", str(mp4)]
    if kind == "keyframes":                       # args.py: keyframe interpolation also refines audio in stage 2
        cmd += ["--refine-audio"]
    if kind == "a2v":
        cmd += ["--audio-path", str(audio)]
    return cmd


def kind_record(launch: dict, job: dict, cmd: list[str]) -> dict:
    """Every setting of the run, written into the run record (seed, steps, guidance, conditioning frames and strengths, the
    upscaler file's sha256): what the A/B metrics and a later audit read; never reconstructed from the command line."""
    kind = kind_of(job)
    files, uses, kuses = launch["model_files"], launch["uses"], launch.get("kind_uses") or {}
    frames = ltx_frames(job["seconds"], job["fps"]) if kind != "retake" else None
    dist = distilled_engine(job)
    rec = {"kind": kind, "engine": "distilled" if dist else "guided" if kind == "keyframes" else None,
           "module": launch["module"] if dist else KIND_PIPELINES[kind]["module"],
           "pipeline": "DistilledPipeline" if dist else KIND_PIPELINES[kind]["cls"],
           "ltx_commit": (launch.get("ltx_code") or {}).get("commit"), "model_revision": launch["model_revision"],
           "seed": job["seed"], "frames": frames, "fps": job.get("fps"), "size": [job.get("width"), job.get("height")],
           "settings": {} if kind == "retake" else dict(job.get("settings") or {}), "prompt": job["motion_prompt"],
           "negative_prompt": None if kind == "retake" else resolve_negative_prompt(launch, job),
           "conditioning": kind_conditioning(job, frames) if frames else [],
           "spatial_upsampler": {"file": uses["spatial_upsampler"], "sha256": files[uses["spatial_upsampler"]]},
           "argv_sha256": hashlib.sha256("\0".join(cmd).encode()).hexdigest()}
    for role in kind_needs(job):
        rec[role] = {"file": kuses[role], "sha256": launch["kind_model_files"][kuses[role]]}
    if kind == "retake":
        rec.update(start_time=job["start_time"], end_time=job["end_time"], source=job["source"])
    if kind == "a2v":
        rec["audio"] = job["audio"]
    return rec


def stage_input(spec: dict, dest: Path, api=None, repo=HF_REPO, download=None) -> Path:
    """A retake's source clip or an a2v's audio: fetched from HF by its path and refused unless its sha256 is the pinned one."""
    dest = Path(dest)
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if download is not None:
            download(repo, spec["hf_path"], dest)
        else:
            from huggingface_hub import hf_hub_download
            shutil.copyfile(hf_hub_download(repo_id=repo, repo_type="dataset", filename=spec["hf_path"], token=_tok()), dest)
    if _sha(dest) != spec["sha256"]:
        raise RuntimeError(f"{spec['hf_path']}: sha256 is not the pinned one; nothing was run")
    return dest


class _Argv:
    """``sys.argv`` for the LTX-2 parser while it reads it: ``resolve_cli_params`` pre-parses the process arguments to
    find the checkpoint and its model version."""

    def __init__(self, argv):
        self.argv, self.old = ["ltx_pipelines.distilled", *argv], None

    def __enter__(self):
        self.old, sys.argv = sys.argv, self.argv

    def __exit__(self, *exc):
        sys.argv = self.old


def ltx_modules():
    """The pinned LTX-2 code the CLI runs, imported in the container: ``ltx_pipelines.distilled`` (its module namespace holds
    every helper its ``main`` calls), torch and the memory cleanup."""
    import importlib
    from types import SimpleNamespace
    import torch
    return SimpleNamespace(D=importlib.import_module("ltx_pipelines.distilled"), torch=torch,
                           cleanup=importlib.import_module("ltx_pipelines.utils.helpers").cleanup_memory)


class _CachedPrompts:
    """Stands in for the pipeline's ``PromptEncoder`` once every prompt is encoded: Gemma never loads beside the resident
    transformer. A prompt that was not encoded first, or a prompt enhancement, is refused (it would load Gemma there)."""

    def __init__(self, cache: dict):
        self.cache = cache

    def __call__(self, prompts, *, enhance_first_prompt=False, enhance_prompt_image=None, enhance_prompt_seed=42,
                 enhance_static_cache=False):
        if enhance_first_prompt:
            raise RuntimeError("prompt enhancement is not part of the in-process runner")
        missing = [p[:60] for p in prompts if p not in self.cache]
        if missing:
            raise RuntimeError(f"prompt not encoded before the clips: {missing}")
        return [self.cache[p] for p in prompts]


class _GuardedStage:
    """The pipeline's diffusion stage with the in-container deadline checked before each denoising pass (two per clip):
    a clip that would run past it ends with ``DeadlineHit`` and the normal end path still writes and uploads."""

    def __init__(self, stage, deadline):
        self._stage, self._deadline = stage, deadline

    def __call__(self, *a, **kw):
        if self._deadline is not None:
            self._deadline.check()
        return self._stage(*a, **kw)

    def __getattr__(self, name):
        return getattr(self._stage, name)


class LtxSession:
    """The in-process runner (``runner: inproc``): the CLI's ``main`` (LTX-2 ``ltx_pipelines.distilled`` at the launch's
    commit) split in two. The first clip parses its arguments with the CLI's parser, builds ``DistilledPipeline`` with the
    CLI's arguments, encodes every prompt of the shot in one Gemma load and builds the transformer once, held until
    ``close``; each clip then runs ``main``'s own body: ``stream_chunks``, the decode and ``encode_video``. ``setup`` holds
    the measured seconds of the one-time steps."""

    def __init__(self, prompts, deadline=None, ltx=None, now=time.time):
        self.prompts = list(dict.fromkeys(prompts))
        self.deadline, self._ltx, self.now = deadline, ltx, now
        self.pipe, self.key, self.setup, self._resident = None, None, {}, None

    def _parse(self, argv):
        L = self._ltx
        D = L.D
        with _Argv(argv):
            params = D.resolve_cli_params(distilled=True)
            parser = D.add_chunk_layout_args(D.add_keyframe_decode_arg(D.add_generated_keyframes_arg(
                D.default_2_stage_distilled_arg_parser(params=params, supports_auto_duration=True))))
            return parser.parse_args(argv)

    @staticmethod
    def model_key(args) -> str:
        return repr([(k, getattr(args, k, None)) for k in MODEL_ARGS])

    def _open(self, args):
        L, t0 = self._ltx, self.now()
        D = L.D
        pipe = D.DistilledPipeline(model_paths=args.model_paths, spatial_upsampler_path=args.spatial_upsampler_path,
                                   loras=tuple(args.lora) if args.lora else (), quantization=args.quantization,
                                   compilation_config=args.compile, offload_mode=args.offload_mode,
                                   prompt_enhancer_gemma_root=args.prompt_enhancer_gemma_root,
                                   diffvae_optimization=args.diffvae_optimization)
        self.setup["pipeline_s"] = round(self.now() - t0, 1)
        t1, cache = self.now(), {}
        prompts_to_encode = list(self.prompts)
        neg_init = getattr(args, "negative_prompt", None)
        if neg_init:
            san_neg = sanitize_painterly_negative_prompt(neg_init)
            for cand in (neg_init, san_neg):
                if cand and cand not in prompts_to_encode:
                    prompts_to_encode.append(cand)
        for i in range(0, len(prompts_to_encode), PROMPT_GROUP):
            group = prompts_to_encode[i:i + PROMPT_GROUP]
            cache.update(zip(group, pipe.prompt_encoder(group)))
        pipe.prompt_encoder = _CachedPrompts(cache)
        L.cleanup()
        self.setup["prompts_s"], self.setup["prompts"] = round(self.now() - t1, 1), len(cache)
        t2 = self.now()
        self._resident = ExitStack()
        self._resident.enter_context(pipe.stage.resident())
        with pipe.stage._transformer_ctx():     # built now, before the first clip plans its decode tiles on free memory
            pass
        pipe.stage = _GuardedStage(pipe.stage, self.deadline)
        self.setup["transformer_s"] = round(self.now() - t2, 1)
        self.pipe, self.key = pipe, self.model_key(args)

    def clip(self, argv) -> None:
        L = self._ltx = self._ltx or ltx_modules()
        D, torch = L.D, L.torch
        args = self._parse(argv)
        with torch.inference_mode():
            # L3 2026-11-13 (CUDA out of memory on the H100): the CLI's ``main`` is ``@torch.inference_mode()`` and the
            # library's Gemma ``encode`` has no no_grad of its own, so the session opens inside inference mode too: outside
            # it the prompt embeddings kept an autograd graph that held Gemma's weights on the GPU after its dispose, and
            # the transformer no longer fit beside them.
            if self.pipe is None:
                self._open(args)
            elif self.model_key(args) != self.key:
                raise RuntimeError("this clip's model arguments differ from the session's")
            if self.deadline is not None:
                self.deadline.check()
            hdr = D.resolve_hdr_color_space(images=args.images, hdr=args.hdr)
            video_marker, audio_marker = D.markers_from_args(args, device=D.get_device(), color_space=hdr)
            vae_dtype = D.vae_dtype_for_hdr(hdr, torch.bfloat16)
            chunk_config = D.chunk_config_from_args(args)
            neg_prompt = sanitize_painterly_negative_prompt(getattr(args, "negative_prompt", None))
            stream_kw = dict(
                prompt=args.prompt, seed=args.seed, height=args.height, width=args.width, num_frames=args.num_frames,
                frame_rate=args.frame_rate, images=args.images, vae_dtype=vae_dtype, color_space=hdr,
                enhance_prompt=args.enhance_prompt, enhance_static_cache=args.enhance_static_cache,
                tiling_config=D.AUTO_TILING, generated_keyframes=args.num_generated_keyframes,
                decode_with_keyframes=args.decode_with_keyframes, chunk_config=chunk_config,
            )
            import inspect       # the distilled pipeline has no CFG: its stream_chunks takes a negative prompt only if it declares one
            if neg_prompt is not None and getattr(args, "negative_prompt", None) \
                    and any(p.name == "negative_prompt" or p.kind is p.VAR_KEYWORD
                            for p in inspect.signature(self.pipe.stream_chunks).parameters.values()):
                stream_kw["negative_prompt"] = neg_prompt
            chunks, num_frames, tiling_config = self.pipe.stream_chunks(**stream_kw)
            if chunk_config is not None:
                video, audio, audio_sampling_rate = D.split_decoded_chunks(chunks)
                video_chunks_number = 1
            else:
                result = D.pipeline_output_from_chunks(chunks, num_frames=num_frames, tiling_config=tiling_config)
                video, audio, audio_sampling_rate = result.video, result.audio, None
                video_chunks_number = D.get_video_chunks_number(result.num_frames, result.tiling_config)
            D.encode_video(video=video, fps=args.frame_rate, audio=audio, output_path=args.output_path,
                           video_chunks_number=video_chunks_number, color_space=hdr,
                           audio_sampling_rate=audio_sampling_rate, video_marker=video_marker, audio_marker=audio_marker)
        del video, audio
        L.cleanup()

    def close(self) -> None:
        if self._resident is not None:
            self._resident.close()
            self._resident = None


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


def generate(job, launch, out: Path, deadline: Deadline, sh=subprocess.run, tmp="/tmp/in", now=time.time,
             session=None) -> dict:
    """One clip: the start picture fitted to the clip's size, then the CLI as its own process, bounded by the time left, or,
    with a ``session`` (``runner: inproc``), the same arguments run in this process on the session's loaded pipeline, its
    log written to the same file and the deadline checked before each denoising pass."""
    import io
    from PIL import Image
    t0 = now()
    Path(tmp).mkdir(parents=True, exist_ok=True)
    pic = Path(tmp) / f"{job['shot_id']}_{job['width']}x{job['height']}.png"
    fit_picture(Image.open(io.BytesIO(job["start_bytes"])), job["width"], job["height"]).save(pic)
    final = Path(out) / clip_name(job["shot_id"], job["seed"])
    mp4 = tmp_name(final)
    beat(out, job, "generate")
    row = {"frames": ltx_frames(job["seconds"], job["fps"]) if kind_of(job) != "retake" else None, "fps": job["fps"]}
    if kind_of(job) != "clip":                   # W5: another official pipeline, always its own CLI process
        end_png = None
        if job.get("end_bytes"):
            end_png = Path(tmp) / f"{job['shot_id']}_end_{job['width']}x{job['height']}.png"
            fit_picture(Image.open(io.BytesIO(job["end_bytes"])), job["width"], job["height"]).save(end_png)
        source = audio = None
        if kind_of(job) == "retake":
            source = stage_input(job["source"], Path(tmp) / f"{job['shot_id']}_source.mp4")
        if kind_of(job) == "a2v":
            audio = stage_input(job["audio"], Path(tmp) / f"{job['shot_id']}_audio" / Path(job["audio"]["hf_path"]).name)
        cmd = kind_cmd(launch, job, pic, mp4, end_png=end_png, source=source, audio=audio)
        row["record"] = kind_record(launch, job, cmd)
        with open(Path(out) / f"{job['shot_id']}.log", "w") as log:
            try:
                row["rc"] = sh(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=launch.get("code_dir") or "/workspace/LTX-2",
                               timeout=max(1.0, deadline.left())).returncode
            except subprocess.TimeoutExpired:
                row["rc"], row["why"] = None, "the in-container deadline came during the clip"
    elif session is not None:
        row.update(in_process_clip(session, ltx_argv(launch, job, pic, mp4), Path(out) / f"{job['shot_id']}.log"))
    else:
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


def in_process_clip(session, argv, log_path) -> dict:
    """One clip on the session, its LTX log in the clip's log file: ``rc`` 0 when it ran, None when the deadline stopped it
    (PARTIAL), 1 with ``why`` when it raised (FAILED; ``body`` may retry it once with a new seed, P5)."""
    import traceback
    handler = logging.FileHandler(log_path, mode="w")
    handler.setLevel(logging.INFO)
    root = logging.getLogger()
    root.addHandler(handler)
    level, root.level = root.level, min(root.level or logging.INFO, logging.INFO)
    try:
        session.clip(argv)
        return {"rc": 0}
    except DeadlineHit:
        _free(session)
        return {"rc": None, "why": "the in-container deadline came during the clip"}
    except Exception as e:  # noqa: BLE001 - written to the clip's row and log
        with open(log_path, "a") as f:
            f.write(traceback.format_exc())
        _free(session)                            # P5: the retry of this clip starts on freed memory
        return {"rc": 1, "why": f"{type(e).__name__}: {str(e)[:300]}"}
    finally:
        root.removeHandler(handler)
        root.level = level
        handler.close()


def _free(session) -> None:
    """The library's memory clean-up after a clip that did not finish (a fake session in the tests has none)."""
    cleanup = getattr(getattr(session, "_ltx", None), "cleanup", None)
    if callable(cleanup):
        try:
            cleanup()
        except Exception as e:  # noqa: BLE001
            print("cleanup after a failed clip failed", repr(e)[:200], flush=True)


def chain_from(launch: dict, frames: int) -> int:
    """The frame of a clip that starts the next chained clip: ``chain_overlap_frames`` before its last one. BP-188: LTX makes
    picture and sound together, so the clips meet at a hard cut with no overlap (0: the last frame; assembly drops the next
    clip's repeated first frame). A non-zero overlap is kept for a route whose seams need picture under a crossfade."""
    k = int(launch["chain_overlap_frames"])
    if not 0 <= k < frames - 1:
        raise ValueError(f"chain_overlap_frames {k} does not fit a clip of {frames} frames")
    return frames - 1 - k


HANDOVER_W = 160            # VL-05: frames are scored on a small grey copy (sharpness and motion are relative measures)
HANDOVER_MOTION_W = 1.5     # engineering default: one unit of mean frame-to-frame change costs this much relative sharpness
CROP_MIN_SIDE = 2.0 / 3.0   # VL-05: a crop keeps at least 2/3 of each side (at most a 1.5x enlargement of the clip's frame)


def _grey_frames(clip: Path, first: int, count: int, width: int = HANDOVER_W, sh=subprocess.run):
    """Frames ``first .. first+count-1`` of the clip as small grey float arrays (ffmpeg decode, numpy only: the container
    has no OpenCV)."""
    import numpy as np
    probe = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                str(clip)], check=True, timeout=60, capture_output=True, text=True)
    w0, h0 = (int(v) for v in probe.stdout.strip().split(",")[:2])
    h = max(2, int(round(width * h0 / w0 / 2)) * 2)
    raw = sh(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"select=gte(n\\,{int(first)}),scale={width}:{h},format=gray",
              "-vsync", "0", "-frames:v", str(int(count)), "-f", "rawvideo", "-"], check=True, timeout=120,
             capture_output=True).stdout
    n = len(raw) // (width * h)
    return np.frombuffer(raw[:n * width * h], np.uint8).reshape(n, h, width).astype(np.float32)


HANDOVER_WINDOW_S = 1.5      # VL-16 (Audit #7b): 1.5 s handover search window
W_FACE = 0.6                 # BP-199 (Audit #7b): person face weight
W_BODY = 0.3                 # BP-199 (Audit #7b): person body weight
W_FRAME = 0.1                # BP-199 (Audit #7b): whole-frame weight


def _lap_var_2d(g) -> float:
    import numpy as np
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return float(np.var(lap))


def _crop_norm(g, box) -> "np.ndarray":
    h, w = g.shape[:2]
    x0 = max(0, min(w - 1, int(round(box[0] * w))))
    y0 = max(0, min(h - 1, int(round(box[1] * h))))
    x1 = max(x0 + 1, min(w, int(round(box[2] * w))))
    y1 = max(y0 + 1, min(h, int(round(box[3] * h))))
    return g[y0:y1, x0:x1]


def handover_scores(frames, face_box=None, body_box=None) -> list[dict]:
    """VL-05 / VL-16 / BP-199 (Audit #7b): score every candidate handover frame by person stillness and face sharpness
    first (``W_FACE=0.6, W_BODY=0.3, W_FRAME=0.1``) so a sharp background never overrides a moving face/body."""
    import numpy as np
    fbox = list(face_box) if face_box is not None else [0.30, 0.12, 0.70, 0.50]
    bbox = list(body_box) if body_box is not None else [0.22, 0.45, 0.78, 0.92]
    out = []
    for i, g in enumerate(frames):
        js = [j for j in (i - 1, i + 1) if 0 <= j < len(frames)]
        f_crop = _crop_norm(g, fbox)
        b_crop = _crop_norm(g, bbox)
        frame_diffs = [float(np.abs(g - frames[j]).mean()) for j in js]
        face_diffs = [float(np.abs(f_crop - _crop_norm(frames[j], fbox)).mean()) for j in js]
        body_diffs = [float(np.abs(b_crop - _crop_norm(frames[j], bbox)).mean()) for j in js]
        out.append({
            "i": i,
            "sharpness": _lap_var_2d(g),
            "motion": float(np.mean(frame_diffs)) if frame_diffs else 0.0,
            "face_sharp": _lap_var_2d(f_crop),
            "face_motion": float(np.mean(face_diffs)) if face_diffs else 0.0,
            "body_motion": float(np.mean(body_diffs)) if body_diffs else 0.0,
        })
    top_frame_s = max((o["sharpness"] for o in out), default=0.0) or 1.0
    top_face_s = max((o["face_sharp"] for o in out), default=0.0) or 1.0
    top_frame_m = max([o["motion"] for o in out] + [1.0]) or 1.0
    top_face_m = max([o["face_motion"] for o in out] + [1.0]) or 1.0
    top_body_m = max([o["body_motion"] for o in out] + [1.0]) or 1.0
    for o in out:
        face_term = (o["face_sharp"] / top_face_s) - (o["face_motion"] / top_face_m)
        body_term = -(o["body_motion"] / top_body_m)
        frame_term = (o["sharpness"] / top_frame_s) - HANDOVER_MOTION_W * (o["motion"] / top_frame_m)
        o["person_score"] = W_FACE * face_term + W_BODY * body_term + W_FRAME * frame_term
        o["score"] = o["person_score"]
    return out


def speech_floor(fps: int, speech_end_s=None, tail_s=0.0) -> int | None:
    """P5 / BP-187: the first frame at or after the clip's expected speech end plus the tail (the same bound
    ``videolane/ingest.edit_points`` checks on the real sound); None for a clip that speaks no line."""
    if speech_end_s is None:
        return None
    return int(math.ceil((float(speech_end_s) + float(tail_s or 0.0)) * fps - 1e-6))


def handover_frame(clip: Path, frames: int, fps: int, cont: dict | None, launch: dict, sh=subprocess.run,
                   speech_end_s=None, tail_s=0.0) -> dict:
    """The frame of a clip that starts its continuation (VL-05, VL-16, BP-199). ``pick: last`` (or no plan) is ``chain_from``;
    ``pick: best_tail`` scores the last ``window_s`` seconds (default 1.5 s, VL-16) using BP-199 person weights."""
    last = chain_from(launch, frames)
    cont = cont or {}
    pick = cont.get("pick", "last")
    floor = speech_floor(fps, speech_end_s, tail_s)
    after = {} if floor is None else {"after": floor}
    if floor is not None and floor > last:
        return {"frame": None, "pick": pick, **after,
                "why": f"the line ends at {float(speech_end_s):.3f} s and BP-187's tail adds {float(tail_s or 0):g} s (frame "
                       f"{floor}), after the clip's last frame {last}: no hand-over frame that keeps the line whole"}
    if pick == "last":
        return {"frame": last, "pick": "last", **after}
    n = max(2, min(last + 1, int(round(float(cont.get("window_s", HANDOVER_WINDOW_S)) * fps))))
    first = last + 1 - n
    if floor is not None and floor > first:
        first = floor                             # never a frame inside the line or its tail
    scores = handover_scores(_grey_frames(clip, first, last + 1 - first, sh=sh))
    best = max(scores, key=lambda o: o["score"])
    return {"frame": first + best["i"], "pick": "best_tail", "window": [first, last], **after,
            "scores": [{k: round(v, 4) if isinstance(v, float) else v for k, v in s.items()} for s in scores]}


def crop_filter(crop) -> str:
    """The ffmpeg crop of a ``[x0, y0, x1, y1]`` share box (VL-05: each side at least CROP_MIN_SIDE)."""
    x0, y0, x1, y1 = (float(v) for v in crop)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ValueError(f"crop {crop} is not a box inside the frame")
    if x1 - x0 < CROP_MIN_SIDE - 1e-9 or y1 - y0 < CROP_MIN_SIDE - 1e-9:
        raise ValueError(f"crop {crop} enlarges the frame more than {1 / CROP_MIN_SIDE:.2f}x: it would be soft")
    return f"crop=iw*{x1 - x0:.6f}:ih*{y1 - y0:.6f}:iw*{x0:.6f}:ih*{y0:.6f}"


def frame_png(clip: Path, index: int, png: Path, sh=subprocess.run, crop=None) -> bytes:
    """Frame ``index`` (0-based, by decode order) of the clip as a PNG: the start picture of the next chained shot, cropped
    when the continuation plan reframes it (``fit_picture`` then brings it to the clip size)."""
    vf = f"select=eq(n\\,{int(index)})" + (f",{crop_filter(crop)}" if crop else "")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf", vf, "-vsync", "0",
        "-frames:v", "1", str(png)], check=True, timeout=60)
    if not Path(png).is_file() or Path(png).stat().st_size == 0:
        raise RuntimeError(f"frame {index} of {Path(clip).name} was not written")
    return Path(png).read_bytes()


def chain_jobs(job: dict) -> list[dict]:
    """The shot and the shots chained after it (``job["chain"]``): each a full spec of its own, sharing the run, size and
    rate; its start picture is a frame of the previous clip (``chain_from``), made in the container, unless the shot brings
    its own pinned picture (``start_bytes``, read by ``read_job``): then it is a cut, made from that picture."""
    keep = ("run_id", "launch_sha", "plan_sha256", "fps", "width", "height", "nonce", "worker_sha", "commit")
    return [job] + [dict({k: job[k] for k in keep if k in job}, **c) for c in job.get("chain") or []]


SAVE_BUDGET_S = 45   # the upload after each clip (audit B1): short; the final flush retries longer


def _attempt(row: dict) -> dict:
    """One attempt of a clip, as its row's ``attempts`` keeps it (P5)."""
    return {k: row.get(k) for k in ("seed", "state", "rc", "why", "gen_s")}


def body(job: dict, launch: dict, timeout_s: int, *, vol_root="/w", commit=lambda: None, api=None, sh=subprocess.run,
         now=time.time, out_root=OUT_ROOT, session_factory=None) -> dict:
    """The GPU function: attempt marker, weights there, each clip saved to the Volume and HF as soon as it is made (OR-33,
    audit B1), then the final upload checked on HF."""
    t_in = now()
    vol_out = Path(vol_root) / VOL_OUT
    seen = attempt_guard(vol_out, job)
    if seen:
        return {"state": seen, "shot_id": job["shot_id"], "run_id": job["run_id"], "body_s": round(now() - t_in, 1)}
    commit()
    deadline = Deadline(timeout_s, now=now)
    out = Path(out_root) / job["run_id"] / job["shot_id"]
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"{launch['hf_out']}/{job['run_id']}/{job['shot_id']}"
    sent: dict = {}
    m = {"shot_id": job["shot_id"], "run_id": job["run_id"], "gpu": launch["gpu"], "launch_sha": launch_sha(launch),
         "worker_sha": job.get("worker_sha"), "commit": job.get("commit"), "error": None}

    def to_volume():
        try:
            shutil.copytree(out, vol_out / job["run_id"] / job["shot_id"], dirs_exist_ok=True)
            commit()
        except Exception as e:  # noqa: BLE001
            print("volume copy failed", repr(e)[:200], flush=True)

    def write_measured():
        (out / f"{job['shot_id']}.measured.json").write_text(json.dumps(m, default=str))

    def save_now(rows):
        """After every finished clip: the rows so far, the Volume copy, one short HF round (the clip leaves the container)."""
        if job.get("chain"):
            m["chain"] = rows
        write_measured()
        to_volume()
        if api is not None:
            upload_round(api, out, prefix, sent, budget_s=min(SAVE_BUDGET_S, max(0.0, deadline.left())))

    session = None
    try:
        if hashlib.sha256(job["start_bytes"]).hexdigest() != job["start_sha256"]:
            raise RuntimeError("the start picture changed in transit")
        if job.get("launch_sha") and job["launch_sha"] != launch_sha(launch):
            raise RuntimeError("the launch file changed between the spec and the container")
        bad = sizes_ok(launch, vol_root, job)
        if bad:
            raise RuntimeError("weights not on the Volume: " + "; ".join(bad[:5]))
        rows, prev, prev_s, prev_sub = [], None, None, None
        if runner_of(launch) == "inproc" and kind_of(job) == "clip":   # W5 kinds run as their own CLI process
            session = (session_factory or LtxSession)([s["motion_prompt"] for s in chain_jobs(job)], deadline=deadline,
                                                      now=now)
            m["runner"] = "inproc"
        for sub in chain_jobs(job):
            if prev is not None:
                if prev.get("state") != "DONE":
                    break
                # a warm clip takes no longer than the one before it, scaled up when it is longer
                need = 1.15 * float(prev["gen_s"]) * max(1.0, float(sub["seconds"]) / float(prev_s))
                if deadline.left() < need:
                    rows.append({"shot_id": sub["shot_id"], "state": "PARTIAL", "why": f"{deadline.left():.0f} s left, the "
                                 f"clip needs ~{need:.0f} s: not started"})
                    print("clip", sub["shot_id"], "PARTIAL: not started, the deadline", flush=True)
                    break
                if sub.get("start_bytes") is not None:        # its own pinned picture: a cut
                    if hashlib.sha256(sub["start_bytes"]).hexdigest() != sub.get("start_sha256"):
                        raise RuntimeError(f"{sub['shot_id']}: its start picture changed in transit")
                else:
                    cont = sub.get("continue_frame") or {}
                    hand = handover_frame(out / prev["clip"], int(prev["frames"]), int(sub["fps"]), cont, launch, sh=sh,
                                          speech_end_s=prev_sub.get("speech_end_s"), tail_s=prev_sub.get("speech_tail_s"))
                    if hand["frame"] is None:             # P5: never a hand-over inside the line
                        rows.append({"shot_id": sub["shot_id"], "state": "FAILED", "why": hand["why"] + "; not started",
                                     "handover": hand})
                        print("clip", sub["shot_id"], "FAILED: no hand-over frame after the line", flush=True)
                        break
                    idx = hand["frame"]
                    sub = dict(sub, start_bytes=frame_png(out / prev["clip"], idx, out / f"{sub['shot_id']}.start.png", sh=sh,
                                                          crop=cont.get("crop")))
                    sub["chain_from_frame"] = {"clip": prev["clip"], "frame": idx, "pick": hand["pick"],
                                               "crop": cont.get("crop"), "window": hand.get("window"),
                                               "after": hand.get("after")}
            row = dict(generate(sub, launch, out, deadline, sh=sh, now=now, session=session), shot_id=sub["shot_id"],
                       seed=sub["seed"])
            if row.get("state") == "FAILED":              # P5: one more attempt with a new seed, same container and deadline
                attempts = [_attempt(row)]
                for _ in range(CLIP_RETRIES):
                    need = 1.15 * float(row.get("gen_s") or 0.0)
                    if prev is not None and prev.get("state") == "DONE":
                        need = max(need, 1.15 * float(prev["gen_s"]) * max(1.0, float(sub["seconds"]) / float(prev_s)))
                    if deadline.left() < need:
                        attempts[-1]["retry"] = f"{deadline.left():.0f} s left, a retry needs ~{need:.0f} s: not retried"
                        break
                    sub = dict(sub, seed=int(sub["seed"]) + SEED_STEP)
                    print("clip", sub["shot_id"], "FAILED: retry with seed", sub["seed"], flush=True)
                    row = dict(generate(sub, launch, out, deadline, sh=sh, now=now, session=session), shot_id=sub["shot_id"],
                               seed=sub["seed"])
                    attempts.append(_attempt(row))
                    if row.get("state") != "FAILED":
                        break
                row["attempts"] = attempts
            if session is not None and not rows:
                row["setup"] = dict(session.setup)        # the one-time steps, inside the first clip's gen_s
            if sub.get("chain_from_frame"):
                row["chain_from_frame"] = sub["chain_from_frame"]
            if row.get("state") == "DONE":
                row["clip"] = clip_name(sub["shot_id"], sub["seed"])
            rows.append(row)
            prev, prev_s, prev_sub = row, sub["seconds"], sub
            print("clip", sub["shot_id"], row.get("state"), f"gen {row.get('gen_s')} s", flush=True)
            if row.get("state") == "DONE":
                m.update({k: v for k, v in rows[0].items() if k != "shot_id"})
                save_now(rows)
        m.update({k: v for k, v in rows[0].items() if k != "shot_id"})
        if job.get("chain"):
            m["chain"] = rows
            if any(r.get("state") != "DONE" for r in rows) and m["state"] == "DONE":
                m["state"] = "PARTIAL"
    except Exception as e:  # noqa: BLE001 - one attempt: the failure is written, copied and returned
        m.update(state="FAILED", error=f"{type(e).__name__}: {str(e)[:300]}")
    finally:
        if session is not None:
            try:
                session.close()                   # the resident transformer is released before the end path
            except Exception as e:  # noqa: BLE001
                print("session close failed", repr(e)[:200], flush=True)
    m.update(body_s=round(now() - t_in, 1), libs=libs())
    write_measured()
    beat(out, job, m["state"])
    to_volume()                                  # the Volume first (delta audit N2)
    if api is not None:
        upload_round(api, out, prefix, sent, final=True, budget_s=max(0.0, deadline.left() + MARGIN_S - 60))
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
    def weights_check(launch: dict, with_kind: bool = False):
        return check_weights(launch, with_kind=with_kind)

    @app.function(image=image, cpu=(float(STAGE_CPU),) * 2, memory=(STAGE_MEM_GIB * 1024,) * 2, timeout=STAGE_TIMEOUT_S,
                  retries=0, volumes={"/w": vol}, secrets=secrets)
    def weights_stage(launch: dict, with_kind: bool = False):
        bad = stage_weights(launch, with_kind=with_kind)
        vol.commit()
        return bad

    if TIMEOUTS:
        GPU_KW = dict(image=image, gpu=LAUNCH["gpu"] + "!", cpu=(float(LAUNCH["cpu"]),) * 2,
                      memory=(LAUNCH["memory_gib"] * 1024,) * 2, retries=0, volumes={"/w": vol}, secrets=secrets,
                      scaledown_window=LAUNCH["scaledown_window_s"], startup_timeout=LAUNCH["startup_timeout_s"])

        def _remote_body(job, launch, timeout_s):
            from huggingface_hub import HfApi
            bad = container_gate(job, launch)
            if bad:
                return {"state": "FAILED", "error": "cheapest-run rules (D-133) refused in the container: " + "; ".join(bad)}
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
    def stage(plan: str = "", with_kind: bool = False):
        preflight(LAUNCH)
        print("GO card", go_gate(plan_sha=_sha(plan)), "stage timeout", STAGE_TIMEOUT_S, "s", flush=True)
        ladder_gate("L2")
        bad = weights_stage.remote(LAUNCH, with_kind)
        print("stage", bad or "all files on the Volume, sha256 match")
        if bad:
            raise SystemExit("the weights stage-in is not complete:\n" + "\n".join(bad))

    @app.local_entrypoint()
    def weights(with_kind: bool = False):
        ladder_gate("L2")
        preflight(LAUNCH)
        bad = weights_check.remote(LAUNCH, with_kind)
        print("weights", bad or "all files present, sha256 match")
        record("L2", not bad, problems=bad, with_kind=bool(with_kind))

    @app.local_entrypoint()
    def smoke(picture: str = "", plan: str = ""):
        preflight(LAUNCH)
        plan_sha = _sha(plan)
        print("GO card", go_gate(plan_sha=plan_sha), "smoke timeout", TIMEOUTS[0], "s", flush=True)
        ladder_gate("L3")
        smoke_item = f"ltx_smoke_{run_id(plan_sha, LAUNCH)}_{worker_sha()[:8]}"   # a repeat on FIXED bytes is a new item; the same bytes stay refused
        night_reserve(smoke_item, hard_bill_usd(LAUNCH, TIMEOUTS[0]), "L3 smoke")
        pic = Path(picture).read_bytes()
        nat = native_spec(LAUNCH, SMOKE_JOB["seconds"])
        job = dict(SMOKE_JOB, fps=nat["fps"], width=nat["width"], height=nat["height"], start_bytes=pic,
                   start_sha256=hashlib.sha256(pic).hexdigest(), run_id=run_id(plan_sha, LAUNCH), launch_sha=launch_sha(LAUNCH),
                   worker_sha=worker_sha(), nonce=uuid.uuid4().hex[:12], cheapest_waive=waivers())
        t_smoke = time.time()
        try:
            res = ltx_smoke.remote(job, LAUNCH)
        finally:
            night_settle(smoke_item, round((time.time() - t_smoke) * usd_per_h(LAUNCH) / 3600.0, 4))
        print("result", json.dumps(res))
        ok = res.get("state") == "DONE"
        record("L3", ok, measured={"gpu": res.get("gpu"), "s_per_clip_s": res.get("s_per_clip_s"),
                                   "setup_s": round(max(0.0, float(res.get("body_s") or 0) - float(res.get("gen_s") or 0)), 1),
                                   "body_s": res.get("body_s"), "runner": res.get("runner") or "cli",
                                   "setup": res.get("setup")} if ok else None,
               result={k: res.get(k) for k in ("state", "error")})

    @app.local_entrypoint()
    def main(job: str = ""):
        spec = read_job(job)
        preflight(LAUNCH, spec)
        from explainer_engine.cloud import cheapest    # D-133 CH-02, CH-03: every clip native, the whole scene in this container
        why = cheapest.problems_text(cheapest.spec_problems(LAUNCH, json.loads(Path(job).read_text(encoding="utf-8"))))
        if why:
            raise SystemExit("paid preflight FAILED, nothing was started:\n" + why)
        from explainer_engine.cloud import modal_run as MR
        why = kind_l2_problems(spec, LAUNCH, MR.load_ladder(LADDER_PATH))
        if why:
            raise SystemExit("\n".join(why))
        print("GO card", go_gate(plan_sha=spec["plan_sha256"]), "timeout", TIMEOUTS[1], "s", flush=True)
        ladder_gate("L4")
        night_item = f"ltx_main_{spec['run_id']}"
        night_reserve(night_item, hard_bill_usd(LAUNCH, TIMEOUTS[1]), f"L4 {spec.get('shot_id')} and {len(spec.get('chain') or [])} chained")
        claim_launch(spec)
        t0, res = time.time(), None
        try:
            res = ltx_main.remote(dict(spec, worker_sha=worker_sha(), nonce=uuid.uuid4().hex[:12], cheapest_waive=waivers()),
                                  LAUNCH)
        finally:
            wall = time.time() - t0
            print("settled", settle_launch(spec, wall), "USD for", round(wall, 1), "s", flush=True)
            night_settle(night_item, round(wall * usd_per_h(LAUNCH) / 3600.0, 4))
            if res is not None:
                Path(job).with_suffix(".result.json").write_text(json.dumps(res))
        print("result", json.dumps(res))
        if res.get("state") != "DONE":   # a FAILED clip is a non-zero exit, never a 0
            print(LTX_FAILED, flush=True)
            raise SystemExit(4)


def build_ltx_render_manifest(launch: dict, job: dict, *, lora: str | None = None) -> dict:
    """B-P1(d): Pin model, LoRA, prompt, sanitized negative prompt, and seed in the LTX render manifest."""
    uses = launch.get("uses") or {}
    return {
        "schema": "ltx_render_manifest/1",
        "shot_id": job.get("shot_id"),
        "model": uses.get("transformer") or launch.get("module"),
        "lora": lora or uses.get("distilled_lora"),
        "prompt": job.get("motion_prompt", ""),
        "negative_prompt": resolve_negative_prompt(launch, job),
        "seed": int(job.get("seed", 0)),
        "width": int(job.get("width", 1920)),
        "height": int(job.get("height", 1088)),
        "fps": int(job.get("fps", 24)),
        "seconds": float(job.get("seconds", 1.0)),
    }
