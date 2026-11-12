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
5. **No second launch after a lost answer** (final audit A4): the Modal backend looks for the job's finished clip in its run's
   HF folder before it submits; when the launcher dies without an answer it stops the app by name and fetches before it
   decides; an infrastructure or configuration failure (``InfraError``) is never retried with a new seed and its
   reservation stays open until the bill is read. Only a clip the model made badly (``ClipFailed``, the worker's
   ``WAN_FAILED`` exit, or a QA FAIL) gets the one retry.
6. **Settled from what was measured** (final audit B6): the worker's ``measured.json`` (container seconds) plus the launch's
   cold start replace the reservation; the report shows estimate, reserved and billed apart (cloud rules section 8).
7. **The episode's line** (final audit B5): every paid attempt is also reserved in ``core/ledger.EpisodeTotal``, the durable
   total of all the episode's runs against ``modal.per_episode_usd``.
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
from explainer_engine.core.ledger import STOP_FRACTION, CapReached, EpisodeTotal
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
    """The creator's agreed OR-23 plan for a paid batch: its id, the batch cap in USD, when and where he said yes, and the plan
    file he said yes to with its sha256 (final audit B10: the yes binds the plan's bytes; a changed plan needs a new yes)."""
    plan_id: str
    cap_usd: float
    said_by: str
    said_at: str
    message_id: str
    plan_path: str | None = None
    plan_sha256: str | None = None


class InfraError(RuntimeError):
    """The launch failed for a reason that is not the clip (launcher, network, Modal, a refusal in the container) or its
    answer was lost: never retried with a new seed, the reservation stays open until the bill is read (final audit A4)."""


class ClipFailed(RuntimeError):
    """The model ran and made no usable clip (the worker's ``WAN_FAILED``): the one retry with a new seed may follow."""


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
        elif isinstance(self.launch, dict) and not launch_problems(self.launch):
            from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
            old = MR.stale(self.ladder, WJ.proof(self.launch))
            if old:
                out.append(f"the ladder's rung(s) {old} were proved on another launch file or worker: run them again")
        if self.measured_s_per_clip_s is None:
            out.append("no speed measured on L3")
        from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
        if not WJ.GO.match(str(self.env.get("EE_MODAL_GO") or "")):
            out.append("EE_MODAL_GO is not '<the creator's message id>:<the plan's sha256[:12]>'")
        try:
            spend_caps.modal()
        except spend_caps.OverCeiling as exc:
            out.append(str(exc))
        if self.runner is None or self.fetch is None:
            out.append("no Modal runner / fetch was given")
        return out

    def _stop(self, app_id: str | None) -> list[str]:
        """Stop the launch's app by id and every running app of the launch's name (ephemeral apps stop only by id); returns
        what could not be done, so a lost network is reported, never taken for a stopped app."""
        from explainer_engine.cloud import modal_run as MR
        problems, ids = [], []
        try:
            rc, text = self.runner(["modal", "app", "list", "--json"])
            ids = MR.stop_target(text, self.launch["app_name"]) if rc == 0 and self.launch.get("app_name") else []
            if rc != 0:
                problems.append(f"modal app list exited {rc}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"modal app list failed: {type(exc).__name__}")
        for i in sorted(set(ids) | ({app_id} if app_id else set())):
            try:
                if self.runner(["modal", "app", "stop", i])[0] != 0:
                    problems.append(f"modal app stop {i} failed")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"modal app stop {i} failed: {type(exc).__name__}")
        return problems

    def job_refusals(self, job: WanJob) -> list[str]:
        """What keeps one job from being sent (B9, B10): the start picture pinned by the pictures stage and still those bytes,
        the plan's sha256, and EE_MODAL_GO naming this plan."""
        out, x = [], job.extra or {}
        want = x.get("start_sha256")
        if not want:
            out.append("no start_sha256 from production/pictures.json")
        elif not Path(job.start_picture).is_file() or _sha_file(job.start_picture) != want:
            out.append("the start picture is not the one production/pictures.json pinned")
        plan_sha, msg = x.get("plan_sha256"), x.get("message_id")
        if not plan_sha:
            out.append("no approved plan sha256")
        elif str(self.env.get("EE_MODAL_GO") or "") != f"{msg}:{plan_sha[:12]}":
            out.append(f"EE_MODAL_GO is not this plan's yes ({msg}:{plan_sha[:12]})")
        return out

    def _try_fetch(self, job: WanJob, out_mp4: Path) -> bool:
        try:
            self.fetch(job, out_mp4)
        except Exception:  # noqa: BLE001 - not there (yet): the caller decides
            return False
        return Path(out_mp4).is_file() and Path(out_mp4).stat().st_size > 0

    def billed(self, out_mp4: Path) -> dict:
        """The cost of one launch from the worker's ``measured.json`` (B6): the container's own seconds plus the launch's
        cold start, at the launch's per-second price; {} when the worker wrote no measurement (the reservation then stays)."""
        f = Path(out_mp4).with_suffix(".measured.json")
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(m.get("body_s"), (int, float)):
            return {}
        cold = float(((self.launch or {}).get("caps") or {}).get("cold_start_s") or 0.0)
        secs = float(m["body_s"]) + cold
        return {"billed_usd": round(secs * self.usd_per_hour / 3600.0, 4), "billed_seconds": round(secs, 1),
                "billed_basis": "measured container seconds + the launch's cold_start_s at the dated price (Modal's usage "
                                "page is the bill of record)", "measured": m}

    def generate(self, job: WanJob, out_mp4: Path) -> dict:
        from explainer_engine.cloud import modal_run as MR
        from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
        bad = self.refusals() + self.job_refusals(job)
        if bad:
            raise ConfigError(f"{job.shot_id}: the Modal Wan backend refuses ({'; '.join(bad)}); nothing was sent "
                              "(plan P6.3, OR-23, OR-34, OR-37)")
        out_mp4 = Path(out_mp4)
        try:   # final audit A2: the clip is made at the model's own rate and size, then conformed to the timeline here
            nat = WJ.native_spec(self.launch, job.seconds)
        except ValueError as exc:
            raise ConfigError(f"{job.shot_id}: {exc}; nothing was sent (final audit A2)") from None
        timeline = job
        x = dict(job.extra or {})
        x["run_id"] = WJ.run_id(x["plan_sha256"], self.launch)
        job = WanJob(**dict(asdict(job), fps=nat["fps"], width=nat["width"], height=nat["height"], extra=x))
        native, final = out_mp4.with_name(out_mp4.stem + ".native.mp4"), out_mp4
        out_mp4 = native
        base = {"gpu": self.gpu, "usd_per_hour": self.usd_per_hour, "prices_date": self.prices_date, "run_id": x["run_id"],
                "native": {k: nat[k] for k in ("fps", "width", "height", "frames")}}

        def done(info):
            return dict(info, conform=conform(native, final, fps=timeline.fps, width=timeline.width, height=timeline.height))
        if self._try_fetch(job, out_mp4):   # the same job of the same plan and launch is already made: nothing is sent
            return done(dict(base, app_id=None, reused=True, billed_usd=0.0,
                             billed_basis="already in the run's HF folder: not sent"))
        spec = out_mp4.with_suffix(".job.json")
        spec.write_text(json.dumps(dict(asdict(job), run_id=x["run_id"], plan_sha256=x["plan_sha256"],
                                        launch_sha=WJ.launch_sha(self.launch), commit=self.commit()), ensure_ascii=False),
                        encoding="utf-8")
        try:
            rc, text = self.runner(["modal", "run", "--detach", f"{WORKER}::main", "--job", str(spec)])
        except Exception as exc:  # noqa: BLE001 - the answer is lost: the app may still run (A4)
            probs = self._stop(None)
            if self._try_fetch(job, out_mp4):
                return done(dict(base, app_id=None, reconciled=True, **self.billed(out_mp4)))
            raise InfraError(f"{job.shot_id}: the launcher gave no answer ({type(exc).__name__}: {exc}); "
                             + (f"COULD NOT STOP the apps named {self.launch.get('app_name')} ({'; '.join(probs)}): look at "
                                "Modal now" if probs else f"the apps named {self.launch.get('app_name')} were stopped")
                             + "; no clip is in the run's HF folder; not retried, the reservation stays until Modal's bill "
                               "is read") from None
        app_id = MR.parse_app_id(text)
        if rc != 0:
            self._stop(app_id)
            if WJ.WAN_FAILED in (text or ""):
                raise ClipFailed(f"{job.shot_id}: the model made no clip (app {app_id}); the app was stopped")
            raise InfraError(f"{job.shot_id}: modal run exited {rc} (app {app_id}); the app was stopped; not retried")
        if not self._try_fetch(job, out_mp4):
            self._stop(app_id)
            raise InfraError(f"{job.shot_id}: the launch ended but no clip is in the run's HF folder (app {app_id}); the app was "
                             "stopped; not retried")
        return done(dict(base, app_id=app_id, **self.billed(out_mp4)))

    def commit(self) -> str | None:
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10,
                               cwd=str(Path(__file__).resolve().parents[2]))
            return r.stdout.strip() or None if r.returncode == 0 else None
        except Exception:  # noqa: BLE001
            return None


def conform(src: Path, dst: Path, *, fps: int, width: int, height: int) -> dict:
    """The free CPU step after a Wan clip (final audit A2): the model's own rate and size become the timeline's. Frames are
    repeated or dropped to the timeline's rate (no interpolation, no new pixels) and the picture is scaled with Lanczos and
    centre-cropped to the timeline's aspect; the length stays. A clip already at the timeline's rate and size is copied."""
    import subprocess

    import cv2
    src, dst = Path(src), Path(dst)
    cap = cv2.VideoCapture(str(src))
    have = (round(float(cap.get(cv2.CAP_PROP_FPS) or 0.0)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    cap.release()
    if have == (int(fps), int(width), int(height)):
        dst.write_bytes(src.read_bytes())
        return {"conformed": False, "native": list(have)}
    vf = f"fps={int(fps)},scale={int(width)}:{int(height)}:force_original_aspect_ratio=increase:flags=lanczos," \
         f"crop={int(width)}:{int(height)}"
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "12",
                        "-pix_fmt", "yuv420p", "-an", str(dst)], capture_output=True, text=True)
    if r.returncode != 0 or not dst.is_file():
        raise ConfigError(f"conform of {src.name} failed: {(r.stderr or '')[-300:]}")
    return {"conformed": True, "native": list(have), "timeline": [int(fps), int(width), int(height)]}


def fit_rows(shots: list[dict], launch: dict | None) -> list[dict]:
    """G1 (final audit A2): every Wan shot fits one clip of the pinned model; NOT_RUN while the model's limits are not pinned.
    The remedies of a longer shot: split it in the script, or chain two clips on frame[-5] (not built yet)."""
    from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
    wan = [s for s in shots if s.get("route") == "wan"]
    if not isinstance(launch, dict) or WJ.native_problems(launch):
        return [G.row("wan_shots_fit_the_model", None, "NOT_RUN: the Wan model's native limits are not pinned in "
                      "training/pods/wan/launch.json", len(wan))]
    longest = WJ.max_seconds(launch)
    long_ = []
    for s in wan:
        try:
            WJ.native_spec(launch, float(s.get("target_duration_seconds") or 0))
        except ValueError:
            long_.append(f"{s.get('shot_id')}: {float(s.get('target_duration_seconds') or 0):g} s")
    return [G.row("wan_shots_fit_the_model", not long_, f"{len(long_)} of {len(wan)} Wan shot(s) are longer than one clip of "
                  f"{launch.get('model_repo')} ({longest:.2f} s at {launch['native']['fps']} fps): split the shot in the "
                  "script, or chain two clips on frame[-5] (final audit A2)", long_[:30])]


def clip_name(shot_id: str, seed: int) -> str:
    """The clip's name in the worker's ``hf_out`` (``training/pods/wan/modal_wan_jobs.clip_name`` is the same)."""
    return f"{shot_id}_seed{seed}.mp4"


def hf_fetch(launch: dict, repo: str = "vano1919/tmr-artifacts"):
    """The default ``fetch`` of ModalWanBackend: the worker's clip from its run's folder in HF ``hf_out``
    (``<hf_out>/<run_id>/<shot>/``, uploaded as it was made, OR-33) and its ``measured.json`` beside it, when there is one."""
    from explainer_engine.training.pods.wan import modal_wan_jobs as WJ

    def fetch(job: WanJob, out_mp4: Path) -> None:
        from huggingface_hub import hf_hub_download
        spec = {"run_id": job.extra["run_id"], "shot_id": job.shot_id}
        local = str(Path(out_mp4).parent / "_hf")
        p = hf_hub_download(repo, WJ.hf_path(launch, spec, clip_name(job.shot_id, job.seed)), repo_type="dataset", local_dir=local)
        Path(out_mp4).write_bytes(Path(p).read_bytes())
        try:
            m = hf_hub_download(repo, WJ.hf_path(launch, spec, f"{job.shot_id}.measured.json"), repo_type="dataset", local_dir=local)
            Path(out_mp4).with_suffix(".measured.json").write_bytes(Path(m).read_bytes())
        except Exception:  # noqa: BLE001 - the clip is the result; without its measurement the reservation stays the estimate
            pass
    return fetch


def _sha_json(d) -> str:
    from explainer_engine.training.pods.wan import modal_wan_jobs as WJ
    return WJ.sha_json(d)


def _sha_file(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def start_sha_from_pictures(episode_root: Path, shot_id: str, which: str = "start") -> str:
    """The start picture's sha256 the pictures stage pinned (``production/pictures.json``, final audit B9): the Wan job carries
    it, the worker re-checks the bytes against it, so a picture changed after the intake never reaches the GPU."""
    f = Path(episode_root) / "production" / "pictures.json"
    pics = json.loads(f.read_text(encoding="utf-8"))["pictures"] if f.is_file() else {}
    rec = pics.get(f"{shot_id}_{which}") or {}
    if not rec.get("sha256"):
        raise ContractError(f"{shot_id}: no {which} picture pinned in production/pictures.json (run the pictures stage first)")
    return rec["sha256"]


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


def episode_total(backend: Backend, run) -> EpisodeTotal | None:
    """The episode-wide total of a paid service with an episode line (``modal_usd`` -> ``modal.per_episode_usd``; B5)."""
    if backend.service != "modal_usd":
        return None
    ep = (run.data.get("meta") or {}).get("episode")
    if not ep:
        raise ConfigError("the run ledger names no episode (meta episode): the episode's Modal line cannot be held")
    try:
        return EpisodeTotal(ep, backend.service, float(spend_caps.modal(episode=True)["per_episode_usd"]))
    except (ValueError, spend_caps.OverCeiling) as exc:
        raise ConfigError(f"{exc}; nothing was sent") from None


def _check_money(job: WanJob, backend: Backend, est: dict, approval: Approval | None, run) -> EpisodeTotal | None:
    if approval is None:
        raise ConfigError(f"{job.shot_id}: {backend.name} is paid and no approved OR-23 plan was given")
    if not approval.plan_path or not approval.plan_sha256 or not Path(approval.plan_path).is_file() \
            or _sha_file(approval.plan_path) != approval.plan_sha256:
        raise ConfigError(f"{job.shot_id}: plan {approval.plan_id} is not the file the creator said yes to (its sha256 must "
                          "match the approval, final audit B10); nothing was sent")
    if not str(approval.message_id or "").startswith("cmsg_"):
        raise ConfigError(f"{job.shot_id}: the approval names no creator's message id; nothing was sent")
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
    ep = episode_total(backend, run)
    left = min(approval.cap_usd - _plan_spent(run, approval.plan_id), cap * STOP_FRACTION - run.spent(backend.service),
               ep.left() if ep else float("inf"))
    if est["usd"] * MAX_ATTEMPTS > left + 1e-9:
        raise ConfigError(f"{job.shot_id}: {MAX_ATTEMPTS} attempt(s) at ${est['usd']:.4f} do not fit under the ${left:.4f} "
                          f"left of plan {approval.plan_id}, the run's and the episode's {int(STOP_FRACTION * 100)} % stop; "
                          "nothing was sent")
    return ep


def run_shot(job: WanJob, backend: Backend, out_dir: Path, ledger: Path, *, approval: Approval | None = None, run=None,
             shot: dict | None = None, script: dict | None = None, fallback: bool = True) -> dict:
    """Make one Wan shot: price, cap, generate, QA, one retry on a FAIL, then the 2.5D fallback. Returns the shot report.
    ``run`` is the paid run's ``core/ledger.Run``: each paid attempt is reserved in it before it is sent."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    est = backend.estimate(job)
    ep = _check_money(job, backend, est, approval, run) if backend.paid else None
    seed = job.seed
    extra = dict(job.extra or {})
    if backend.paid:   # the plan the job belongs to travels with it (B10)
        extra.update(plan_id=approval.plan_id, plan_sha256=approval.plan_sha256, message_id=approval.message_id)
    for n in range(1, MAX_ATTEMPTS + 1):
        j = WanJob(**dict(asdict(job), seed=seed, extra=extra))
        clip = out_dir / f"{job.shot_id}_try{n}.mp4"
        t0 = time.time()
        item = f"wan/{approval.plan_id}/{job.shot_id}/try{n}" if backend.paid else None
        if backend.paid:
            try:
                run.reserve(backend.service, est["usd"], item)
            except CapReached as exc:
                raise ConfigError(f"{job.shot_id}: attempt {n}: {exc}; nothing more was sent") from None
            if ep is not None:
                try:
                    ep.reserve(item, est["usd"], run=str(run.path))
                except CapReached as exc:
                    run.settle(backend.service, item, 0.0)
                    raise ConfigError(f"{job.shot_id}: attempt {n}: {exc}; nothing more was sent") from None
        _ledger_line(ledger, {"shot_id": job.shot_id, "attempt": n, "seed": seed, "backend": backend.name, "event": "submit",
                              "estimate_usd": est["usd"] if backend.paid else 0.0, "ledger_item": item,
                              "plan_id": approval.plan_id if approval else None, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        error, info, infra = None, {}, None
        try:
            info = backend.generate(j, clip) or {}
        except ConfigError:
            if backend.paid:   # refused before anything was sent: the reservation is given back
                run.settle(backend.service, item, 0.0)
                if ep is not None:
                    ep.settle(item, 0.0)
            raise
        except InfraError as exc:   # A4: not the clip's fault, the outcome is uncertain: no new seed, the money stays reserved
            error = infra = f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # noqa: BLE001 - a backend failure is a FAIL row, recorded, then the retry or fallback
            error = f"{type(exc).__name__}: {exc}"
        rows = qa_clip(clip, j) if error is None else [G.row("clip_made", False, error)]
        v = G.verdict(rows)
        if backend.paid and isinstance(info.get("billed_usd"), (int, float)):
            run.settle(backend.service, item, float(info["billed_usd"]))
            if ep is not None:
                ep.settle(item, float(info["billed_usd"]))
        rec = {"attempt": n, "seed": seed, "clip": str(clip), "wall_s": round(time.time() - t0, 2), "gates": v,
               "sha256": hashlib.sha256(clip.read_bytes()).hexdigest() if clip.is_file() else None,
               "backend_info": {k: info[k] for k in ("app_id", "gpu", "billed_usd", "run_id", "reused", "reconciled")
                                if k in info}}
        if backend.paid:   # cloud rules section 8: estimate, reserved and billed apart
            rec["money"] = {"estimate_usd": est["usd"], "reserved_usd": run.data["reserved"].get(item, {}).get("amount"),
                            "billed_usd": info.get("billed_usd"), "billed_basis": info.get("billed_basis"),
                            "episode_total_usd": ep.total() if ep else None}
        _ledger_line(ledger, {"shot_id": job.shot_id, "attempt": n, "event": "done", "status": v["status"],
                              "sha256": rec["sha256"], "estimate_usd": 0.0})
        attempts.append(rec)
        if infra:
            return {"shot_id": job.shot_id, "route": "wan", "backend": backend.name, "clip_path": None, "attempts": attempts,
                    "status": G.FAIL, "fallback": None, "stopped": "infrastructure", "estimate_usd_per_attempt": est["usd"]}
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
