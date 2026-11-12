"""Wan, only where needed (v4.3 plan P6, RT-07 in docs/EPISODE_FIRST.md): one adapter in front of every Wan backend.

A job goes in (start picture, optional end picture, motion prompt, seconds, seed) and a clip comes out. The adapter does
what every backend needs and none may skip:

1. **Money before the call.** ``Backend.estimate`` prices the job from MEASURED seconds on the backend's GPU
   (``measured_s_per_clip_s`` and ``usd_per_hour``); a backend with no measurement cannot price a job and the adapter refuses
   it. A paid backend also needs an approval record (the OR-23 plan agreed with the creator: its id, the cap in USD) and the
   run's ledger; the estimate of every attempt (retries included) must fit under the cap that is left. Nothing in this
   package runs a paid backend: the Modal backend refuses until the creator's word is recorded (plan P6.3, OR-23, OR-34).
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
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ConfigError, ContractError
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
    """One way to make a Wan clip. ``paid`` backends need an Approval; ``measured`` speeds price the jobs."""
    name = "base"
    paid = False
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


class ModalWanBackend(Backend):
    """Wan on Modal: wired only after the OR-23 plan, the OR-34 audit and the creator's word (plan P6.3). Until then it
    refuses every job; the adapter, the QA and the fallback are tested with a fake backend."""
    name = "modal_wan"
    paid = True

    def generate(self, job: WanJob, out_mp4: Path) -> dict:
        raise ConfigError("the Modal Wan backend is not wired: it needs the OR-23 plan agreed with the creator, the "
                          "Fable audit (OR-34) and his word before the first paid clip (plan P6.3)")


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


def run_shot(job: WanJob, backend: Backend, out_dir: Path, ledger: Path, *, approval: Approval | None = None,
             shot: dict | None = None, script: dict | None = None, fallback: bool = True) -> dict:
    """Make one Wan shot: price, cap, generate, QA, one retry on a FAIL, then the 2.5D fallback. Returns the shot report."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    attempts = []
    est = backend.estimate(job)
    if backend.paid:
        if approval is None:
            raise ConfigError(f"{job.shot_id}: {backend.name} is paid and no approved OR-23 plan was given")
        left = approval.cap_usd - spent(ledger)
        if est["usd"] * MAX_ATTEMPTS > left + 1e-9:
            raise ConfigError(f"{job.shot_id}: {MAX_ATTEMPTS} attempt(s) at ${est['usd']:.4f} do not fit under the ${left:.4f} "
                              f"left of plan {approval.plan_id}'s cap; nothing was sent")
    seed = job.seed
    for n in range(1, MAX_ATTEMPTS + 1):
        j = WanJob(**dict(asdict(job), seed=seed))
        clip = out_dir / f"{job.shot_id}_try{n}.mp4"
        t0 = time.time()
        _ledger_line(ledger, {"shot_id": job.shot_id, "attempt": n, "seed": seed, "backend": backend.name, "event": "submit",
                              "estimate_usd": est["usd"] if backend.paid else 0.0,
                              "plan_id": approval.plan_id if approval else None, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        error = None
        try:
            backend.generate(j, clip)
        except ConfigError:
            raise
        except Exception as exc:  # noqa: BLE001 - a backend failure is a FAIL row, recorded, then the retry or fallback
            error = f"{type(exc).__name__}: {exc}"
        rows = qa_clip(clip, j) if error is None else [G.row("clip_made", False, error)]
        v = G.verdict(rows)
        rec = {"attempt": n, "seed": seed, "clip": str(clip), "wall_s": round(time.time() - t0, 2), "gates": v,
               "sha256": hashlib.sha256(clip.read_bytes()).hexdigest() if clip.is_file() else None}
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
