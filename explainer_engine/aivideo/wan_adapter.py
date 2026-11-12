"""Wan, only where needed (v4.3 plan P6, RT-07 in docs/EPISODE_FIRST.md): one adapter in front of every Wan backend.

A job goes in (start picture, optional end picture, motion prompt, seconds, seed) and a clip comes out. The adapter does
what every backend needs and none may skip:

1. **Money before the call.** ``Backend.estimate`` prices the job from MEASURED seconds on the backend's GPU
   (``measured_s_per_clip_s`` and ``usd_per_hour``); a backend with no measurement cannot price a job and the adapter refuses
   it. A paid backend also needs an approval record (the OR-23 plan agreed with the creator: its id, the cap in USD) and the
   run's ledger ``core/ledger.Run`` (D-56, R-E of the Fable audit 2026-11-12): the plan's cap and the run's cap of the
   backend's service may not pass the creator's line in ``config/spend_caps.json`` (``modal``: no line = a zero approved
   budget, every paid call refused), every attempt is reserved in the Run before it is sent (the 80 % stop applies), and the
   estimate of every attempt (retries included) must fit under what is left of the plan and of the run.
   The jsonl attempt log stays beside it for the runner's acceptance (``paid_calls_approved``).
   The Modal backend (``ModalWanBackend``) launches the Wan worker ``training/pods/wan/modal_wan_jobs.py`` only on rung L4 of
   the OR-37 ladder (``cloud/modal_run``), with a pinned launch file, a measured speed from L3 and ``EE_MODAL_GO`` set to the
   creator's message id; nothing in the tests sends a call.
2. **Real QA after every clip** (``qa_clip``), replacing the archive's ``passed: True``: the clip decodes, has at least the
   frames the shot needs, is not one frozen picture, its first frame matches the start picture (and the last the end
   picture), it holds no black, blown or flat frames, its longest frozen run, and the face against the start picture (SFace,
   when installed). Objective defects FAIL; the hypothesis thresholds of BP-164 give REVIEW (D-59).
3. **One retry, then a fallback.** A FAIL gets one retry with a new seed (``seed + SEED_STEP``); a second FAIL falls back to
   the layered 2.5D renderer (``production/layers25d``) with the shot's ``fallback_motion_imitation`` and the report says
   so. REVIEW rows are kept for the creator, never retried on money.
4. **Saved as it arrives** (OR-33): every finished clip is hashed and a ledger line is appended before the next attempt.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from explainer_engine.core import spend_caps
from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.ledger import STOP_FRACTION, CapReached
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

SEED_STEP = 1001
MAX_ATTEMPTS = 2   # the first try and one retry (plan P6.2)
ANALYSIS = tuple(SR.T("BP-164", "analysis_size"))
FROZEN_RUN = int(SR.T("BP-164", "frozen_run_frames"))
FROZEN_FRAMES_MAX = int(SR.T("BP-174", "frozen_frames_max"))
FROZEN_DIFF = float(SR.T("BP-164", "frozen_diff_max"))
FRAME0_DIFF = float(SR.T("BP-164", "frame0_mean_abs_diff_max"))
FRAME0_DHASH = int(SR.T("BP-164", "frame0_dhash_max"))
BLACK_LUMA = float(SR.T("BP-164", "black_luma_max"))
BLOWN_LUMA = float(SR.T("BP-164", "blown_luma_min"))
FLAT_STD = float(SR.T("BP-164", "flat_luma_std_max"))
DEFAULT_FALLBACK = [{"effect": "push", "strength": 0.6}, {"effect": "mist", "strength": 0.4}, {"effect": "subject_sway"}]   # BP-185: two families


@dataclass
class WanJob:
    shot_id: str
    start_picture: str
    motion_prompt: str
    seconds: float
    seed: int
    end_picture: str | None = None
    fps: int = 24
    width: int = 1920
    height: int = 1080
    negative_prompt: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def frames(self) -> int:
        return max(1, int(round(self.seconds * self.fps)))


@dataclass
class Approval:
    """The creator's agreed OR-23 plan for a paid batch: its id, the batch cap in USD, when and where he said yes."""
    plan_id: str
    cap_usd: float
    said_by: str
    said_at: str
    message_id: str


class Backend:
    """One way to make a Wan clip. ``paid`` backends need an Approval and a Run; ``measured`` speeds price the jobs; a paid
    backend names the ledger ``service`` its money is reserved under."""
    name = "base"
    paid = False
    service: str | None = None
    measured_s_per_clip_s: float | None = None   # wall seconds of GPU per second of clip, measured on this backend
    usd_per_hour: float = 0.0
    setup_usd: float = 0.0

    def estimate(self, job: WanJob) -> dict:
        if self.measured_s_per_clip_s is None:
            raise ConfigError(f"{self.name}: no measured speed, so no price for {job.shot_id}; measure it on a free or "
                              "approved pilot first (plan P6.3, OR-22: never priced from a guess)")
        sec = self.measured_s_per_clip_s * job.seconds
        return {"gpu_s": round(sec, 1), "usd": round(self.setup_usd + sec / 3600.0 * self.usd_per_hour, 4)}

    def generate(self, job: WanJob, out_mp4: Path) -> dict:   # pragma: no cover - interface
        raise NotImplementedError


def service_ceiling(service: str) -> float:
    """The creator's per-run line for a paid service (``config/spend_caps.json``): ``modal_usd`` -> ``modal.per_run_usd``
    (refused while the line is missing), any other service -> its ``per_episode`` line (refused when it has none)."""
    if service == "modal_usd":
        return float(spend_caps.modal()["per_run_usd"])
    v = spend_caps.episode_ceiling(service)
    if v is None:
        raise spend_caps.OverCeiling(f"no {service} line in config/spend_caps.json: it spends nothing without the creator's line")
    return float(v)


WORKER = "explainer_engine/training/pods/wan/modal_wan_jobs.py"


def launch_problems(launch: dict | None) -> list[str]:
    """What keeps a Wan launch file from a paid run (the worker's own check, ``training/pods/wan/modal_wan_jobs``): every pin of
    the model (repo, revision, file shas), the pipeline class, every generation setting, the HF output folder, the dated price
    and the caps must be written down (OR-22, OR-23), none left None."""
    if not isinstance(launch, dict):
        return ["no launch file (training/pods/wan/launch.json)"]
    from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
    return WJ.launch_problems(launch)


class ModalWanBackend(Backend):
    """Wan on Modal (D-131): the worker ``training/pods/wan/modal_wan_jobs.py`` on the v15 template, launched with
    ``modal run --detach <worker>::main`` by an injected ``runner(argv) -> (returncode, output)``; the clip is read back from
    the worker's HF output by an injected ``fetch(job, out_mp4)``.

    Price: the GPU's per-second rate plus the CPU cores and memory the worker asks for (``cloud/modal_schedule``, prices of
    ``PRICES_DATE``), times the speed MEASURED on rung L3 (``ladder.json``: ``measured.s_per_clip_s`` and the cold start
    ``measured.setup_s`` paid per launch). It refuses (ConfigError, nothing sent) while: the launch file is not pinned, the
    ladder's next rung is not L4 (L0-L3 not all green, or one red), ``EE_MODAL_GO`` is not the creator's message id, the
    ``modal`` line is missing in ``config/spend_caps.json``, or no runner was given. A failed launch stops its app by id
    (``modal_run.stop_target``: ephemeral apps stop only by id)."""
    name = "modal_wan"
    paid = True
    service = "modal_usd"

    def __init__(self, launch: dict | None = None, ladder: dict | None = None, *, runner=None, fetch=None,
                 gpu: str = "A100-80GB", cores: int = 8, ram_gib: int = 64, env=None):
        from explainer_engine.cloud import modal_schedule as MS
        if isinstance(launch, dict):
            gpu = launch.get("gpu") or gpu
        if gpu not in MS.GPUS:
            raise ConfigError(f"unknown Modal GPU {gpu!r}; known: {sorted(MS.GPUS)}")
        self.launch, self.ladder = launch, ladder or {}
        self.runner, self.fetch, self.env = runner, fetch, os.environ if env is None else env
        if isinstance(launch, dict):   # the worker's size is the launch file's, so the price is the one it pays
            gpu, cores, ram_gib = launch.get("gpu") or gpu, launch.get("cpu") or cores, launch.get("memory_gib") or ram_gib
        self.gpu, self.cores, self.ram_gib = gpu, cores, ram_gib
        per_s = MS.GPUS[gpu]["usd_s"] + cores * MS.CPU_CORE_S + ram_gib * MS.MEM_GIB_S
        self.usd_per_hour = round(per_s * 3600.0, 4)
        self.prices_date = MS.PRICES_DATE
        m = self.ladder.get("measured") or {}
        if m and m.get("gpu") not in (None, gpu):
            raise ConfigError(f"the L3 speed was measured on {m.get('gpu')}, not on {gpu}: measure it there first")
        self.measured_s_per_clip_s = m.get("s_per_clip_s")
        self.setup_usd = round(float(m.get("setup_s") or 0.0) * per_s, 4)

    def refusals(self) -> list[str]:
        from explainer_engine.cloud import modal_run as MR
        out = launch_problems(self.launch)
        rung = MR.next_rung(list(self.ladder.get("done") or []), self.ladder.get("red"))
        if rung != "L4":
            out.append(f"the OR-37 ladder is at {rung or 'a red rung'}, not L4: L0-L3 run first, in order")
        if self.measured_s_per_clip_s is None:
            out.append("no speed measured on L3")
        if not str(self.env.get("EE_MODAL_GO") or "").startswith("cmsg_"):
            out.append("EE_MODAL_GO is not set to the creator's message id")
        try:
            spend_caps.modal()
        except spend_caps.OverCeiling as exc:
            out.append(str(exc))
        if self.runner is None or self.fetch is None:
            out.append("no Modal runner / fetch was given")
        return out

    def _stop(self, app_id: str | None) -> None:
        from explainer_engine.cloud import modal_run as MR
        rc, text = self.runner(["modal", "app", "list", "--json"])
        ids = MR.stop_target(text, self.launch["app_name"]) if rc == 0 and self.launch.get("app_name") else []
        for i in sorted(set(ids) | ({app_id} if app_id else set())):
            self.runner(["modal", "app", "stop", i])

    def generate(self, job: WanJob, out_mp4: Path) -> dict:
        from explainer_engine.cloud import modal_run as MR
        bad = self.refusals()
        if bad:
            raise ConfigError(f"{job.shot_id}: the Modal Wan backend refuses ({'; '.join(bad)}); nothing was sent "
                              "(plan P6.3, OR-23, OR-34, OR-37)")
        out_mp4 = Path(out_mp4)
        spec = out_mp4.with_suffix(".job.json")
        spec.write_text(json.dumps(dict(asdict(job), launch_sha=_sha_json(self.launch)), ensure_ascii=False), encoding="utf-8")
        rc, text = self.runner(["modal", "run", "--detach", f"{WORKER}::main", "--job", str(spec)])
        app_id = MR.parse_app_id(text)
        if rc != 0:
            self._stop(app_id)
            raise RuntimeError(f"modal run exited {rc} (app {app_id}); the app was stopped")
        try:
            self.fetch(job, out_mp4)
        except Exception:
            self._stop(app_id)
            raise
        return {"app_id": app_id, "gpu": self.gpu, "usd_per_hour": self.usd_per_hour, "prices_date": self.prices_date}


def clip_name(shot_id: str, seed: int) -> str:
    """The clip's name in the worker's ``hf_out`` (``training/pods/wan/modal_wan_jobs.clip_name`` is the same)."""
    return f"{shot_id}_seed{seed}.mp4"


def hf_fetch(launch: dict, repo: str = "vano1919/tmr-artifacts"):
    """The default ``fetch`` of ModalWanBackend: the worker's clip from HF ``hf_out`` (it was uploaded as it was made, OR-33)."""
    def fetch(job: WanJob, out_mp4: Path) -> None:
        from huggingface_hub import hf_hub_download
        p = hf_hub_download(repo, f"{launch['hf_out']}/{job.shot_id}/{clip_name(job.shot_id, job.seed)}", repo_type="dataset",
                            local_dir=str(Path(out_mp4).parent / "_hf"))
        Path(out_mp4).write_bytes(Path(p).read_bytes())
    return fetch


def _sha_json(d) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class ComfyWanBackend(Backend):
    """The creator's local ComfyUI (``aivideo/wan_runner``'s workflow graphs), free, on his own GPU; the clip it writes is
    QA'd like any other. ``submit`` posts the graph and ``wait`` returns the written clip path (or None)."""
    name = "local_comfyui"
    paid = False

    def __init__(self, runner, wait, measured_s_per_clip_s: float | None = None):
        self.runner, self.wait = runner, wait
        self.measured_s_per_clip_s = measured_s_per_clip_s

    def generate(self, job: WanJob, out_mp4: Path) -> dict:
        graph = self.runner.compile_workflow_graph(job.extra["comfy_job"])
        url = f"{job.extra['comfy_job']['comfy_local_url'].rstrip('/')}/prompt"
        resp = self.runner.post_fn(url, {"prompt": graph, "client_id": job.extra["comfy_job"]["job_id"]})
        made = self.wait(resp, out_mp4)
        if not made or not Path(made).is_file():
            raise RuntimeError(f"{job.shot_id}: ComfyUI wrote no clip")
        if Path(made) != Path(out_mp4):
            Path(out_mp4).write_bytes(Path(made).read_bytes())
        return {"backend_response": resp}


# --- QA ------------------------------------------------------------------------------------------------------------------

def _read_frames(path: Path) -> tuple[list[np.ndarray], float]:
    import cv2
    cap = cv2.VideoCapture(str(path))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    out = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        out.append(np.ascontiguousarray(fr[..., ::-1]))
    cap.release()
    return out, fps


def _small(rgb: np.ndarray) -> np.ndarray:
    import cv2
    return cv2.resize(rgb, ANALYSIS, interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)


def dhash(rgb: np.ndarray) -> int:
    import cv2
    g = cv2.resize(rgb, (9, 8), interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)
    bits = (g[:, 1:] > g[:, :-1]).ravel()
    return int(sum(1 << i for i, b in enumerate(bits) if b))


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _cover(rgb: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """The picture cover-cropped to the clip's frame (what frame 0 should show)."""
    import cv2
    w, h = size
    sh, sw = rgb.shape[:2]
    k = max(w / sw, h / sh)
    r = cv2.resize(rgb, (int(round(sw * k)), int(round(sh * k))), interpolation=cv2.INTER_AREA)
    y0, x0 = (r.shape[0] - h) // 2, (r.shape[1] - w) // 2
    return r[y0:y0 + h, x0:x0 + w]


def _face_match(frames: list[np.ndarray], picture: np.ndarray):
    """SFace cosine of the clip's faces (first, middle, last frame) to the start picture's best face; None without models."""
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    import cv2
    rec = FP.recognizer()
    model = PX.yunet_path()
    if rec is None or model is None:
        return None

    def faces(rgb):
        h, w = rgb.shape[:2]
        det = cv2.FaceDetectorYN.create(str(model), "", (w, h), PX.FACE_SCORE_MIN, 0.3, 50)
        bgr = np.ascontiguousarray(rgb[..., ::-1])
        _, fs = det.detect(bgr)
        return [rec.feature(rec.alignCrop(bgr, f)) for f in (fs if fs is not None else [])]

    ref = faces(picture)
    if not ref:
        return {"faces_in_picture": 0}
    scores = []
    for fr in (frames[0], frames[len(frames) // 2], frames[-1]):
        got = faces(fr)
        scores.append(max((float(rec.match(g, r, cv2.FaceRecognizerSF_FR_COSINE)) for g in got for r in ref), default=None))
    return {"faces_in_picture": len(ref), "scores": scores}


def qa_clip(clip: Path, job: WanJob) -> list[dict]:
    """Gate rows of one Wan clip (plan P6.2). FAIL = objective defects; REVIEW = BP-164 hypothesis thresholds."""
    from PIL import Image
    rows = []
    clip = Path(clip)
    frames, fps = _read_frames(clip) if clip.is_file() else ([], 0.0)
    if not frames:
        return [G.row("clip_decodes", False, f"{clip.name}: no frame could be decoded", 0)]
    rows.append(G.row("clip_decodes", True, f"{len(frames)} frames at {fps:.2f} fps", len(frames)))
    rows.append(G.row("enough_frames", len(frames) >= job.frames,
                      f"{len(frames)} frames for a shot of {job.frames} (the timeline cannot stretch a clip)", len(frames)))
    smalls = [_small(f) for f in frames]
    ref, run, longest = smalls[0], 1, 1          # a run lasts while frames stay within FROZEN_DIFF of its first frame
    for sm in smalls[1:]:
        if float(np.abs(sm - ref).mean()) < FROZEN_DIFF:
            run += 1
        else:
            ref, run = sm, 1
        longest = max(longest, run)
    rows.append(G.row("not_a_still", longest <= FROZEN_FRAMES_MAX,
                      f"longest run without visible change {longest} frames (BP-174: a FAIL past {FROZEN_FRAMES_MAX})",
                      longest, level=SR.level("BP-174")))
    rows.append(G.row("no_frozen_run", longest <= FROZEN_RUN,
                      f"longest frozen run {longest} frames (BP-164: {FROZEN_RUN})", longest, level=SR.level("BP-164")))
    lum = [float(s.mean()) for s in smalls]
    std = [float(s.std()) for s in smalls]
    bad = [i for i, (m, d) in enumerate(zip(lum, std)) if m <= BLACK_LUMA or m >= BLOWN_LUMA or d <= FLAT_STD]
    rows.append(G.row("no_black_blown_flat", not bad, f"{len(bad)} black, blown or flat frame(s) (BP-164)", bad[:10],
                      level=SR.level("BP-164")))
    size = (frames[0].shape[1], frames[0].shape[0])
    start = np.asarray(Image.open(job.start_picture).convert("RGB"))
    ref0 = _cover(start, size)
    d0 = float(np.abs(_small(frames[0]) - _small(ref0)).mean())
    h0 = _hamming(dhash(frames[0]), dhash(ref0))
    rows.append(G.row("first_frame_is_the_picture", d0 <= FRAME0_DIFF and h0 <= FRAME0_DHASH,
                      f"frame 0 against the start picture: mean difference {d0:.2f}, dHash distance {h0} (BP-164: "
                      f"{FRAME0_DIFF}, {FRAME0_DHASH})", {"mean_abs": round(d0, 3), "dhash": h0}, level=SR.level("BP-164")))
    if job.end_picture:
        ref1 = _cover(np.asarray(Image.open(job.end_picture).convert("RGB")), size)
        d1 = float(np.abs(_small(frames[-1]) - _small(ref1)).mean())
        h1 = _hamming(dhash(frames[-1]), dhash(ref1))
        rows.append(G.row("last_frame_is_the_end_picture", d1 <= FRAME0_DIFF and h1 <= FRAME0_DHASH,
                          f"last frame against the end picture: mean difference {d1:.2f}, dHash distance {h1}",
                          {"mean_abs": round(d1, 3), "dhash": h1}, level=SR.level("BP-164")))
    fm = _face_match(frames, start)
    if fm is None:
        rows.append(G.row("face_matches_the_picture", None, "no face models installed (tools/yunet: YuNet + SFace)"))
    elif not fm["faces_in_picture"]:
        rows.append(G.row("face_matches_the_picture", True, "no face in the start picture", 0))
    else:
        from explainer_engine.qa import face_points as FP
        ok = all(s is not None and s >= FP.ID_MIN for s in fm["scores"])
        rows.append(G.row("face_matches_the_picture", ok,
                          f"SFace cosine of the first, middle and last frame to the picture: {fm['scores']} (face_points "
                          f"ID_MIN {FP.ID_MIN}, a hypothesis)", fm["scores"], level="REVIEW"))
    return rows


# --- the adapter ---------------------------------------------------------------------------------------------------------

def _ledger_line(ledger: Path, rec: dict) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def spent(ledger: Path) -> float:
    if not Path(ledger).is_file():
        return 0.0
    return round(sum(float(json.loads(l).get("estimate_usd") or 0.0) for l in Path(ledger).read_text().splitlines()
                     if l.strip()), 4)


def _plan_spent(run, plan_id: str) -> float:
    return round(sum(r["amount"] for k, r in run.data.get("reserved", {}).items() if k.startswith(f"wan/{plan_id}/")), 6)


def _check_money(job: WanJob, backend: Backend, est: dict, approval: Approval | None, run) -> None:
    if approval is None:
        raise ConfigError(f"{job.shot_id}: {backend.name} is paid and no approved OR-23 plan was given")
    if run is None:
        raise ConfigError(f"{job.shot_id}: {backend.name} is paid and no run ledger (core/ledger.Run) was given")
    if not backend.service:
        raise ConfigError(f"{backend.name} is paid and names no ledger service")
    try:
        ceiling = service_ceiling(backend.service)
    except spend_caps.OverCeiling as exc:
        raise ConfigError(f"{job.shot_id}: {exc}; nothing was sent") from None
    cap = run.data["caps"].get(backend.service)
    if cap is None:
        raise ConfigError(f"{job.shot_id}: the run has no {backend.service} cap; nothing was sent")
    for what, v in (("plan " + approval.plan_id, approval.cap_usd), ("the run's", cap)):
        if v > ceiling + 1e-9:
            raise ConfigError(f"{job.shot_id}: {what} cap ${v:g} is above the creator's ${ceiling:g} line for "
                              f"{backend.service} (config/spend_caps.json); nothing was sent")
    left = min(approval.cap_usd - _plan_spent(run, approval.plan_id), cap * STOP_FRACTION - run.spent(backend.service))
    if est["usd"] * MAX_ATTEMPTS > left + 1e-9:
        raise ConfigError(f"{job.shot_id}: {MAX_ATTEMPTS} attempt(s) at ${est['usd']:.4f} do not fit under the ${left:.4f} "
                          f"left of plan {approval.plan_id} and the run's {int(STOP_FRACTION * 100)} % stop; nothing was sent")


def run_shot(job: WanJob, backend: Backend, out_dir: Path, ledger: Path, *, approval: Approval | None = None, run=None,
             shot: dict | None = None, script: dict | None = None, fallback: bool = True) -> dict:
    """Make one Wan shot: price, cap, generate, QA, one retry on a FAIL, then the 2.5D fallback. Returns the shot report.
    ``run`` is the paid run's ``core/ledger.Run``: each paid attempt is reserved in it before it is sent."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    est = backend.estimate(job)
    if backend.paid:
        _check_money(job, backend, est, approval, run)
    seed = job.seed
    for n in range(1, MAX_ATTEMPTS + 1):
        j = WanJob(**dict(asdict(job), seed=seed))
        clip = out_dir / f"{job.shot_id}_try{n}.mp4"
        t0 = time.time()
        item = f"wan/{approval.plan_id}/{job.shot_id}/try{n}" if backend.paid else None
        if backend.paid:
            try:
                run.reserve(backend.service, est["usd"], item)
            except CapReached as exc:
                raise ConfigError(f"{job.shot_id}: attempt {n}: {exc}; nothing more was sent") from None
        _ledger_line(ledger, {"shot_id": job.shot_id, "attempt": n, "seed": seed, "backend": backend.name, "event": "submit",
                              "estimate_usd": est["usd"] if backend.paid else 0.0, "ledger_item": item,
                              "plan_id": approval.plan_id if approval else None, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        error, info = None, {}
        try:
            info = backend.generate(j, clip) or {}
        except ConfigError:
            if backend.paid:   # refused before anything was sent: the reservation is given back
                run.settle(backend.service, item, 0.0)
            raise
        except Exception as exc:  # noqa: BLE001 - a backend failure is a FAIL row, recorded, then the retry or fallback
            error = f"{type(exc).__name__}: {exc}"
        rows = qa_clip(clip, j) if error is None else [G.row("clip_made", False, error)]
        v = G.verdict(rows)
        if backend.paid and isinstance(info.get("billed_usd"), (int, float)):
            run.settle(backend.service, item, float(info["billed_usd"]))
        rec = {"attempt": n, "seed": seed, "clip": str(clip), "wall_s": round(time.time() - t0, 2), "gates": v,
               "sha256": hashlib.sha256(clip.read_bytes()).hexdigest() if clip.is_file() else None,
               "backend_info": {k: info[k] for k in ("app_id", "gpu", "billed_usd") if k in info}}
        _ledger_line(ledger, {"shot_id": job.shot_id, "attempt": n, "event": "done", "status": v["status"],
                              "sha256": rec["sha256"], "estimate_usd": 0.0})
        attempts.append(rec)
        if v["status"] != G.FAIL:
            final = out_dir / f"{job.shot_id}.mp4"
            final.write_bytes(clip.read_bytes())
            return {"shot_id": job.shot_id, "route": "wan", "backend": backend.name, "clip_path": str(final),
                    "attempts": attempts, "status": v["status"], "fallback": None, "estimate_usd_per_attempt": est["usd"]}
        seed += SEED_STEP
    if not fallback:
        return {"shot_id": job.shot_id, "route": "wan", "backend": backend.name, "clip_path": None, "attempts": attempts,
                "status": G.FAIL, "fallback": None, "estimate_usd_per_attempt": est["usd"]}
    from explainer_engine.production import layers25d as L25
    fb_shot = dict(shot or {"shot_id": job.shot_id}, target_duration_seconds=job.seconds,
                   motion_imitation=(shot or {}).get("fallback_motion_imitation") or DEFAULT_FALLBACK)
    try:
        res = L25.render_clip(fb_shot, Path(job.start_picture), out_dir / f"{job.shot_id}.mp4", width=job.width,
                              height=job.height, fps=job.fps, script=script)
    except ContractError as exc:
        return {"shot_id": job.shot_id, "route": "wan", "backend": backend.name, "clip_path": None, "attempts": attempts,
                "status": G.FAIL, "fallback": {"error": str(exc)}, "estimate_usd_per_attempt": est["usd"]}
    return {"shot_id": job.shot_id, "route": "still_25d", "backend": backend.name, "clip_path": res["path"],
            "attempts": attempts, "status": res["gates"]["status"], "estimate_usd_per_attempt": est["usd"],
            "fallback": {"reason": f"Wan failed {MAX_ATTEMPTS} attempt(s); the layered 2.5D renderer made the shot",
                         "motion_imitation": fb_shot["motion_imitation"], "gates_25d": res["gates"]["status"]}}
