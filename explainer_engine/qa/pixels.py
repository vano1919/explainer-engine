"""Pixel checks on a rendered chunk range, free and local (the QA loop, ``qa/loop.py``; the creator, 2026-10-20: check the
video after every two rendered parts). They read the rendered frames and compare them with the plan in ``timed.json``, so
they catch what the data checks of ``qa/frame_review`` cannot: a renderer that draws something the plan does not say.

    PX-CUT-EXTRA    FAIL    a cut in the pixels where the plan has none (no shot start, no change of the face frame, no
                            punch / whip / flash): an objective defect, the picture jumps where nothing was cut
    PX-CUT-MISSING  REVIEW  a planned cut between two different pictures that the pixels do not show
    PX-FROZEN       FAIL    the picture stands still for ``FREEZE_MIN_S`` or longer while the plan moves the camera by at
                            least ``FREEZE_PLANNED_PX``: an objective defect (a stuck renderer)
    PX-BLACK        REVIEW  a black stretch outside the planned fade in / fade out
    PX-CAM-JUMP     REVIEW  inside a shot, one frame-to-frame camera step far above the shot's median and the plan's own step
                            (a jump or a reset of the move, CC-06; RX-11 (a) of the 2026-10-20 research, not yet a BP rule)
    PX-JUMP-CUT     REVIEW  a cut to the same picture that neither continues the framing (BP-30's same-framing tolerance)
                            nor changes it by a full step (RX-11 (b), proposed numbers below)
    PX-BUBBLE-FACE  REVIEW  a speech bubble region (found in the pixels) covers a face (found by YuNet)

Tools (the research's free-tools table, all BSD / Apache / MIT): PySceneDetect (cut list), OpenCV (ORB + similarity
transform per frame, YuNet faces), ImageHash (same picture across a cut), ffmpeg ``freezedetect`` / ``blackdetect``. A
missing library or the YuNet model skips its check with a note in ``skipped``, it never fails the run. The YuNet model is read
from ``$EXPLAINER_YUNET`` or ``tools/yunet/face_detection_yunet_2023mar.onnx`` (opencv_zoo, MIT; tools/ is gitignored).

Times: ``video time = timed time - offset`` (as in frame_review). Every number this module invents is in the HYPOTHESIS block
and only ever gives REVIEW; the two FAILs are objective defects (an unplanned cut, a frozen picture where the plan moves).
"""

from __future__ import annotations

import math
import os
import re
import subprocess
from pathlib import Path

import numpy as np

from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import accents as ACC
from explainer_engine.production import assemble as A
from explainer_engine.standards import sourced_rules as SR

# --- tool defaults (PySceneDetect 0.7 ContentDetector: threshold 27, min_scene_len 15 frames, its documented defaults) ------
SCENE_THRESHOLD = 27.0
SCENE_MIN_LEN = 15

# --- HYPOTHESIS (REVIEW only): numbers invented for this check, to calibrate on our own renders; none is a BP rule yet -------
CUT_TOL_FRAMES = 2  # a detected cut this close to a planned one is that cut
SNAP_TOL_FRAMES = 6  # ... to a punch / whip / flash start (a punch reaches its zoom in accents.PUNCH_IN = 0.12 s)
STEP_W = 640  # px: frames are measured at this width; every px below is at 1920 width
MIN_INLIERS = 12  # a frame step measured on fewer ORB inliers is not trusted
JUMP_MIN_PX = 3.0  # a camera step must exceed the plan's own step by this many px ...
JUMP_PLAN_TOL = 0.5  # ... plus this share of the plan's step (a punch's 30-70 px steps measure within ~15 % of the plan) ...
JUMP_MEDIAN_X = 4.0  # ... and be this many times the shot's median step (the research's "4x the median", RX-11)
EDGE_SKIP_FRAMES = 2  # frames next to a planned cut / face-frame change / dissolve are not measured for jumps
OVERLAY_SKIP_S = 0.3  # nor this long after a bubble or a visual beat appears or before it goes: its pop scales many ORB
#                       features (the 2026-10-20 old chunks: a bubble's pop read as a 5-8 px camera step)
FREEZE_NOISE_DB = -50  # ffmpeg freezedetect noise on a 320 px wide copy (our film grain is ~-45 dB at full size)
FREEZE_MIN_S = 1.0  # freezedetect's minimum stretch
FREEZE_PLANNED_PX = 6.0  # a stretch counts as frozen only when the plan moves the frame corners at least this far over it ...
FREEZE_MEASURED_RATIO = 0.25  # ... and the pixels moved less than this share of the planned distance
BLACK_MIN_S = 0.5  # blackdetect's minimum stretch (pix_th 0.10, its default)
SAME_PICTURE_INLIERS = 0.5  # across a cut, this share of ORB matches agreeing on one similarity = the same picture (RX-11)
SAME_PICTURE_MIN = 20  # ... and at least this many inliers
FULL_STEP_SCALE = 1.25  # RX-11 (b) proposed: a full shot-size step is a scale ratio >= 1.25 ...
FULL_STEP_SHIFT = 0.25  # ... or a centre shift >= 0.25 of the frame width
PHASH_SAME_MAX = 12  # ImageHash phash distance (of 64 bits) at most this = the same picture (second opinion to the inliers)
FACE_SCORE_MIN = 0.7  # YuNet score for a face
BUBBLE_FACE_SHARE = 0.15  # a bubble covers a face when it hides at least this share of the face box
BUBBLE_FILL_MIN = 0.8  # a bubble found in the pixels is a cream shape whose contour fills at least this share of its box
BUBBLE_AREA_MIN = 0.002  # ... of at least this share of the frame
BUBBLE_CREAM_MIN = 0.35  # else the planned layout box counts when at least this share of it is bubble cream in the pixels

SAME_FRAMING = float(SR.T("BP-30", "same_framing_zoom_tol"))  # BP-30: two framings within this are the same framing
YUNET = Path(__file__).resolve().parents[2] / "tools" / "yunet" / "face_detection_yunet_2023mar.onnx"


def _f(out: list, rule: str, sev: str, where: str, detail: str, t: float | None = None) -> None:
    row = {"rule": rule, "severity": sev, "where": where, "detail": detail, "source": "pixels"}
    out.append(row if t is None else dict(row, t=round(t, 3)))


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        return None


def yunet_path() -> Path | None:
    p = Path(os.environ.get("EXPLAINER_YUNET") or YUNET)
    return p if p.is_file() else None


# --- the plan --------------------------------------------------------------------------------------------------------------

def shot_at(shots: list[dict], f: int) -> dict | None:
    return next((s for s in shots if s["start_frame"] <= f < s["end_frame"]), None)


def planned(timed: dict, picture_dirs: list[Path] | None = None) -> dict:
    """What the plan says happens on screen, in timed frames: hard cuts (shot starts with their pictures), soft changes (the
    face frame's changes inside a shot, frame_review's face track: a view plan's close-up cuts in and out), snaps (punch,
    whip, flash starts), dissolve windows, the close-up frames and the planned fades."""
    from explainer_engine.qa import frame_review as FR
    fps = timed["fps"]
    shots = timed["shots"]
    cuts = [{"frame": s["start_frame"], "shot": s["id"], "prev": p["id"], "same_picture": s["picture"] == p["picture"],
             "dissolve": s.get("transition") == "dissolve"} for p, s in zip(shots, shots[1:])]
    _, runs = FR.face_track(timed, picture_dirs)
    soft = [r["start_frame"] for p, r in zip(runs, runs[1:]) if p["shot"] == r["shot"]]
    close = set()
    for r in runs:
        if r["face"] is not None:
            close.update(range(r["start_frame"], r["end_frame"]))
    snaps = [a["start_frame"] for s in shots for a in s.get("accents") or []
             if a["kind"] in ("punch", "whip_in", "flash_in", "slam_text")]
    snaps += [s["start_frame"] for s in shots if s.get("transition") in ("whip", "flash")]
    dissolves = [(s["start_frame"], s["start_frame"] + round(float(s.get("transition_seconds", 1.0)) * fps))
                 for s in shots if s.get("transition") == "dissolve"]
    total = timed.get("frames") or shots[-1]["end_frame"]
    fades = [(0, round(A.FADE_IN * fps) + 1), (total - round(A.FADE_OUT * fps) - 1, total)]
    pad = round(OVERLAY_SKIP_S * fps)
    pops = [(b["start_frame"], b["start_frame"] + pad) for s in shots for b in s.get("bubbles") or []]
    pops += [(b["end_frame"] - pad, b["end_frame"]) for s in shots for b in s.get("bubbles") or []]
    pops += [(b["start_frame"], b["start_frame"] + pad) for b in timed.get("visual_beats", []) if b["kind"] != "expression"]
    pops += [(b["end_frame"] - pad, b["end_frame"]) for b in timed.get("visual_beats", []) if b["kind"] != "expression"]
    from explainer_engine.production import accents as ACC  # BP-97: a slam blurs and dims the whole picture, entry and exit
    pops += [(a["start_frame"], min(s["end_frame"], a["start_frame"] + round(ACC.text_hold(a["text"], a["kind"]) * fps) + 1))
             for s in shots for a in s.get("accents") or [] if a["kind"] == "slam_text"]
    return {"cuts": cuts, "soft": soft, "snaps": snaps, "dissolves": dissolves, "close": close, "fades": fades,
            "pops": pops}


def planned_box(timed: dict, s: dict, f: int, size: tuple[int, int] = (1920, 1080)) -> tuple[float, float, float, float]:
    """The crop box of frame ``f`` (picture px of a nominal picture at the shot's aspect): the shot's own move
    (assemble.motion_box) with its camera accents (accents.camera), as assemble.finish_frame draws it before the face lean."""
    aspect = (timed.get("pictures", {}).get(s["picture"], {}) or {}).get("aspect") or 16 / 9
    W, H = 2048, round(2048 / aspect)
    f0, f1 = s["start_frame"], s["end_frame"]
    u = min(max((f - f0) / max(1, f1 - f0 - 1), 0.0), 1.0)
    box = A.motion_box(s.get("render_motion") or s.get("motion") or {"z0": 1.0, "z1": 1.0}, W, H, u)
    acc = s.get("accents") or []
    if acc:
        z, dx, dy = ACC.camera(acc, f, timed["fps"], f0)
        box = ACC.apply_camera(box, W, H, z, dx, dy)
    return box


def box_shift_px(b0, b1, size: tuple[int, int] = (1920, 1080)) -> float:
    """How far the frame's corners move (output px) when the crop goes from box ``b0`` to ``b1``: each corner of the first
    frame is a picture point; where it lands in the second frame."""
    OW, OH = size
    worst = 0.0
    for px, py in ((b0[0], b0[1]), (b0[2], b0[1]), (b0[0], b0[3]), (b0[2], b0[3])):
        x = (px - b1[0]) / (b1[2] - b1[0]) * OW
        y = (py - b1[1]) / (b1[3] - b1[1]) * OH
        x0 = (px - b0[0]) / (b0[2] - b0[0]) * OW
        y0 = (py - b0[1]) / (b0[3] - b0[1]) * OH
        worst = max(worst, math.hypot(x - x0, y - y0))
    return worst


# --- measurements ----------------------------------------------------------------------------------------------------------

def detect_cuts(video: Path) -> list[float]:
    """PySceneDetect's cut list (video seconds), ContentDetector with its defaults."""
    from scenedetect import ContentDetector, detect
    scenes = detect(str(video), ContentDetector(threshold=SCENE_THRESHOLD, min_scene_len=SCENE_MIN_LEN))
    return [a.seconds for a, _ in scenes[1:]]


_FREEZE = re.compile(r"freeze_(start|end): ([0-9.]+)")
_BLACK = re.compile(r"black_start:([0-9.]+) black_end:([0-9.]+)")


def freeze_black(video: Path) -> dict:
    """ffmpeg freezedetect + blackdetect on a 320 px wide copy: [[start, end]] video seconds of each."""
    vf = (f"scale=320:-2:flags=area,freezedetect=n={FREEZE_NOISE_DB}dB:d={FREEZE_MIN_S},"
          f"blackdetect=d={BLACK_MIN_S}:pix_th=0.10")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vf", vf, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    freezes, cur = [], None
    for kind, t in _FREEZE.findall(r.stderr):
        if kind == "start":
            cur = float(t)
        elif cur is not None:
            freezes.append([cur, float(t)])
            cur = None
    if cur is not None:
        freezes.append([cur, None])  # frozen up to the end of the file
    return {"freezes": freezes, "blacks": [[float(a), float(b)] for a, b in _BLACK.findall(r.stderr)]}


def _gray(cv2, fr):
    h = round(STEP_W * fr.shape[0] / fr.shape[1])
    return cv2.cvtColor(cv2.resize(fr, (STEP_W, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def similarity(cv2, orb, a, b) -> dict | None:
    """The similarity transform from gray frame ``a`` to ``b`` (ORB + RANSAC): scale, shift (STEP_W px), inliers, matches."""
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 8:
        return {"scale": 1.0, "tx": 0.0, "ty": 0.0, "inliers": 0, "matches": len(m)}
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=1.5)
    if M is None:
        return {"scale": 1.0, "tx": 0.0, "ty": 0.0, "inliers": 0, "matches": len(m)}
    return {"scale": float(math.hypot(M[0, 0], M[1, 0])), "tx": float(M[0, 2]), "ty": float(M[1, 2]),
            "inliers": int(inl.sum()), "matches": len(m), "M": M}


def corner_shift(sim: dict, w: int, h: int) -> float:
    """Output px (at 1920 width) the frame corners move under ``sim`` (a frame measured at ``w`` x ``h``)."""
    M = sim.get("M")
    if M is None:
        return 0.0
    c = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], float)
    moved = c @ np.asarray(M).T
    return float(np.hypot(*(moved - c[:, :2]).T).max() * 1920 / w)


def scan(video: Path, keep: set[int]) -> dict:
    """One pass over the video: the frame-to-frame step of every frame (corner shift in px at 1920 width, ORB inliers) and
    the frames listed in ``keep`` (video frame indices, BGR at 960 px wide)."""
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(video))
    orb = cv2.ORB_create(800)
    steps: list[tuple[float, int] | None] = [None]
    kept: dict[int, np.ndarray] = {}
    prev, i = None, 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i in keep:
            kept[i] = cv2.resize(fr, (960, round(960 * fr.shape[0] / fr.shape[1])), interpolation=cv2.INTER_AREA)
        g = _gray(cv2, fr)
        if prev is not None:
            sim = similarity(cv2, orb, prev, g)
            steps.append(None if sim is None else (corner_shift(sim, g.shape[1], g.shape[0]), sim["inliers"]))
        prev, i = g, i + 1
    cap.release()
    return {"steps": steps, "frames": kept, "count": i}


# --- the checks ------------------------------------------------------------------------------------------------------------

def check_cuts(detected: list[float], plan: dict, fps: int, offset_f: int, n_frames: int) -> list[dict]:
    out: list[dict] = []
    lo, hi = offset_f, offset_f + n_frames
    hard = [c for c in plan["cuts"] if lo < c["frame"] < hi]
    soft = [f for f in plan["soft"] if lo < f < hi]
    for t in detected:
        f = round(t * fps) + offset_f
        near = [c for c in hard if abs(c["frame"] - f) <= CUT_TOL_FRAMES]
        if near or any(abs(x - f) <= CUT_TOL_FRAMES for x in soft):
            continue
        if any(0 <= f - x <= SNAP_TOL_FRAMES for x in plan["snaps"]) or any(a <= f <= b for a, b in plan["dissolves"]):
            continue
        if any(a <= f <= b for a, b in plan["fades"]):
            continue
        _f(out, "PX-CUT-EXTRA", "FAIL", f"frame {f}", f"a cut in the pixels at {f / fps:.2f} s where the plan has no cut, "
           "face-frame change or snap accent: the renderer jumps there (look at the frames either side)", f / fps)
    found = [round(t * fps) + offset_f for t in detected]
    for c in hard:
        if c["same_picture"] or c["dissolve"]:
            continue  # a cut inside one picture may continue the framing (invisible by design); a dissolve has no spike
        if not any(abs(c["frame"] - f) <= CUT_TOL_FRAMES for f in found):
            _f(out, "PX-CUT-MISSING", "REVIEW", c["shot"], f"the planned cut {c['prev']} -> {c['shot']} at "
               f"{c['frame'] / fps:.2f} s is not seen in the pixels: the two pictures look alike, or the cut did not happen",
               c["frame"] / fps)
    return out


def _skip_frames(plan: dict, timed: dict) -> set[int]:
    skip = set(plan["close"])
    for f in [c["frame"] for c in plan["cuts"]] + plan["soft"]:
        skip.update(range(f - EDGE_SKIP_FRAMES, f + EDGE_SKIP_FRAMES + 1))
    for a, b in plan["dissolves"] + plan["fades"] + plan.get("pops", []):
        skip.update(range(a - 1, b + 1))
    return skip


def check_camera(timed: dict, plan: dict, steps: list, offset_f: int) -> tuple[list[dict], dict]:
    """PX-CAM-JUMP: inside each shot, steps far above the shot's median AND the plan's own step (punches are planned)."""
    out: list[dict] = []
    fps = timed["fps"]
    skip = _skip_frames(plan, timed)
    stats = {}
    n = len(steps)
    for s in timed["shots"]:
        rows = []
        for f in range(max(s["start_frame"] + 1, offset_f + 1), min(s["end_frame"], offset_f + n)):
            st = steps[f - offset_f]
            if f in skip or st is None or st[1] < MIN_INLIERS:
                continue
            want = box_shift_px(planned_box(timed, s, f - 1), planned_box(timed, s, f))
            rows.append((f, st[0], want))
        if not rows:
            continue
        med = float(np.median([r[1] for r in rows]))
        stats[s["id"]] = {"median_px": round(med, 3), "max_px": round(max(r[1] for r in rows), 2), "frames": len(rows)}
        jumps = [r for r in rows if r[1] > r[2] * (1 + JUMP_PLAN_TOL) + JUMP_MIN_PX and r[1] > JUMP_MEDIAN_X * med]
        for f, got, want in jumps[:5]:
            _f(out, "PX-CAM-JUMP", "REVIEW", s["id"], f"the camera steps {got:.1f} px in one frame at {f / fps:.2f} s (shot "
               f"median {med:.2f} px, the plan's step {want:.1f} px): a jump or reset of the move", f / fps)
    return out, stats


def _pair_sim(cv2, a: np.ndarray, b: np.ndarray) -> tuple[dict | None, tuple]:
    ga, gb = _gray(cv2, a), _gray(cv2, b)
    return similarity(cv2, cv2.ORB_create(1500), ga, gb), ga.shape


def check_jump_cuts(timed: dict, plan: dict, frames: dict, offset_f: int) -> tuple[list[dict], list[dict]]:
    """PX-JUMP-CUT: across each planned cut, the last frame before and the first after. The same picture (ORB inliers, phash
    as second opinion) at a framing that is neither a continuation (BP-30) nor a full step (RX-11 (b))."""
    cv2 = _cv2()
    out, rows = [], []
    fps = timed["fps"]
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        imagehash = None
    for c in plan["cuts"]:
        a, b = frames.get(c["frame"] - 1 - offset_f), frames.get(c["frame"] - offset_f)
        if a is None or b is None or c["dissolve"]:
            continue
        sim, (h, w) = _pair_sim(cv2, a, b)
        if sim is None:
            continue
        share = sim["inliers"] / max(1, sim["matches"])
        dist = None
        if imagehash is not None:
            ha = imagehash.phash(Image.fromarray(cv2.cvtColor(a, cv2.COLOR_BGR2RGB)))
            hb = imagehash.phash(Image.fromarray(cv2.cvtColor(b, cv2.COLOR_BGR2RGB)))
            dist = int(ha - hb)
        same = sim["inliers"] >= SAME_PICTURE_MIN and share >= SAME_PICTURE_INLIERS
        if dist is not None and not same and dist <= PHASH_SAME_MAX and sim["inliers"] >= SAME_PICTURE_MIN:
            same = True
        ratio = sim["scale"] if sim["scale"] >= 1 else 1 / sim["scale"]
        # the centre's shift as a share of the width: where the first frame's centre lands in the second
        M = sim.get("M")
        cx = (M @ np.array([w / 2, h / 2, 1.0]))[:2] if M is not None else np.array([w / 2, h / 2])
        shift = float(math.hypot(cx[0] - w / 2, cx[1] - h / 2) / w)
        row = {"cut": c["shot"], "t": round(c["frame"] / fps, 3), "same_picture": same, "inlier_share": round(share, 2),
               "inliers": sim["inliers"], "scale_ratio": round(ratio, 3), "centre_shift": round(shift, 3), "phash": dist,
               "planned_same_picture": c["same_picture"]}
        rows.append(row)
        if not same:
            continue
        continues = ratio - 1 <= SAME_FRAMING and shift <= SAME_FRAMING
        full = ratio >= FULL_STEP_SCALE or shift >= FULL_STEP_SHIFT
        if not continues and not full:
            _f(out, "PX-JUMP-CUT", "REVIEW", c["shot"], f"the cut {c['prev']} -> {c['shot']} at {c['frame'] / fps:.2f} s "
               f"shows the same picture at a scale ratio {ratio:.2f} and a centre shift {shift:.2f} of the width: neither the "
               f"same framing (BP-30, {SAME_FRAMING}) nor a full step ({FULL_STEP_SCALE} / {FULL_STEP_SHIFT}): a jump cut",
               c["frame"] / fps)
    return out, rows


def check_freeze_black(fb: dict, timed: dict, plan: dict, steps: list, offset_f: int, n_frames: int) -> list[dict]:
    """PX-FROZEN (FAIL) where ffmpeg sees a still stretch, the plan moves the frame corners >= FREEZE_PLANNED_PX over it and
    the pixels moved less than FREEZE_MEASURED_RATIO of that; PX-BLACK (REVIEW) outside the planned fades."""
    out: list[dict] = []
    fps = timed["fps"]
    shots = timed["shots"]
    for a, b in fb["freezes"]:
        fa = round(a * fps) + offset_f
        fb_ = (round(b * fps) if b is not None else n_frames) + offset_f
        moved_plan = moved_px = 0.0
        for f in range(fa + 1, fb_):
            s = shot_at(shots, f)
            if s is None or f in plan["close"] or f == s["start_frame"]:
                continue
            moved_plan += box_shift_px(planned_box(timed, s, f - 1), planned_box(timed, s, f))
            st = steps[f - offset_f] if 0 <= f - offset_f < len(steps) else None
            if st is not None:
                moved_px += st[0]
        if moved_plan >= FREEZE_PLANNED_PX and moved_px < FREEZE_MEASURED_RATIO * moved_plan:
            s = shot_at(shots, fa) or {"id": f"frame {fa}"}
            _f(out, "PX-FROZEN", "FAIL", s["id"], f"the picture stands still {((fb_ - fa) / fps):.2f} s from {fa / fps:.2f} s "
               f"while the plan moves it {moved_plan:.0f} px (the pixels moved {moved_px:.1f} px): the render is stuck",
               fa / fps)
    for a, b in fb["blacks"]:
        fa, fz = round(a * fps) + offset_f, round(b * fps) + offset_f
        if any(x - 1 <= fa and fz <= y + 1 for x, y in plan["fades"]):
            continue
        _f(out, "PX-BLACK", "REVIEW", f"frame {fa}", f"black from {fa / fps:.2f} to {fz / fps:.2f} s outside the planned fades",
           fa / fps)
    return out


def cream_mask(cv2, frame: np.ndarray) -> np.ndarray:
    """Pixels of bubble cream (finish/bubbles.FILL after the grade and the vignette: warm hue, low saturation, light) on a
    smooth surface (local deviation under 8 levels: not a textured wall or skin)."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(int)
    r, g, b = BUB.FILL[:3]
    hue = cv2.cvtColor(np.uint8([[[b, g, r]]]), cv2.COLOR_BGR2HSV)[0, 0, 0]
    cream = (abs(hsv[..., 0] - int(hue)) <= 11) & (hsv[..., 1] >= 10) & (hsv[..., 1] <= 70) & (hsv[..., 2] >= 120)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32)
    mu = cv2.blur(gray, (5, 5))
    sd = np.sqrt(np.maximum(cv2.blur(gray * gray, (5, 5)) - mu * mu, 0))
    return cream & (sd < 8)


def bubble_box(cv2, before: np.ndarray, during: np.ndarray, planned_box=None) -> tuple[int, int, int, int] | None:
    """The speech bubble that appeared between two frames: in the pixels, a cream shape that was not there before and whose
    contour fills BUBBLE_FILL_MIN of its box (the largest such); else the planned layout box (``planned_box``, the frames'
    px) when at least BUBBLE_CREAM_MIN of it is cream in the pixels. (x0, y0, x1, y1), or None."""
    cream = cream_mask(cv2, during)
    diff = cv2.absdiff(cv2.cvtColor(during, cv2.COLOR_BGR2GRAY), cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)) >= 20
    mask = cv2.morphologyEx(((cream & diff) * 255).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best, area_min = None, BUBBLE_AREA_MIN * during.shape[0] * during.shape[1]
    for c in cs:
        x, y, w, h = cv2.boundingRect(c)
        if w * h < area_min or cv2.contourArea(c) < BUBBLE_FILL_MIN * w * h:
            continue
        if best is None or w * h > (best[2] - best[0]) * (best[3] - best[1]):
            best = (x, y, x + w, y + h)
    if best is None and planned_box is not None:
        x0, y0, x1, y1 = (max(0, int(round(v))) for v in planned_box)
        part = cream[y0:y1, x0:x1]
        if part.size and part.mean() >= BUBBLE_CREAM_MIN:
            best = (x0, y0, x1, y1)
    return best


def layout_boxes(timed: dict, picture_dirs: list[Path] | None, width: int = 960) -> dict:
    """{(shot id, bubble start frame): box} where today's assembler lays each bubble out (assemble.shot_bubbles, frame px at
    ``width``). Empty when the layout cannot be made (no picture data)."""
    out = {}
    pics = timed.get("pictures", {})
    try:
        hero_faces = A.hero_faces_of(timed)
        beats = timed.get("visual_beats", [])
        for s in timed["shots"]:
            if not s.get("bubbles"):
                continue
            p = pics.get(s["picture"], {})
            aspect = p.get("aspect") or 16 / 9
            sb = A.beats_for_shot(beats, s, pics, hero_faces, picture_dirs) if picture_dirs and beats else []
            laid = A.shot_bubbles(s, p, (2048, round(2048 / aspect)), (1920, 1080), sb, timed["fps"], sorted(hero_faces))
            for b, lb in zip(s["bubbles"], laid):
                out[(s["id"], b["start_frame"])] = tuple(v * width / 1920 for v in lb.box)
    except Exception:  # noqa: BLE001 - a layout the data cannot make leaves the pixels alone to find the bubble
        return {}
    return out


def detect_faces(cv2, frame: np.ndarray, model: Path) -> list[tuple[float, float, float, float]]:
    h, w = frame.shape[:2]
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h), FACE_SCORE_MIN, 0.3, 50)
    _, faces = det.detect(frame)
    return [] if faces is None else [(float(r[0]), float(r[1]), float(r[0] + r[2]), float(r[1] + r[3])) for r in faces]


def covered_share(bubble, face) -> float:
    ix = max(0.0, min(bubble[2], face[2]) - max(bubble[0], face[0]))
    iy = max(0.0, min(bubble[3], face[3]) - max(bubble[1], face[1]))
    return ix * iy / max(1e-9, (face[2] - face[0]) * (face[3] - face[1]))


def bubble_frames(timed: dict, offset_f: int, n_frames: int) -> list[dict]:
    """For each bubble inside the range: the frame two before it starts and its middle frame (video indices)."""
    out = []
    for s in timed["shots"]:
        for b in s.get("bubbles") or []:
            pre, mid = b["start_frame"] - 2, (b["start_frame"] + b["end_frame"]) // 2
            if offset_f <= pre and mid < offset_f + n_frames:
                out.append({"shot": s["id"], "who": b.get("who"), "text": b["text"], "pre": pre - offset_f,
                            "mid": mid - offset_f, "t": mid / timed["fps"], "start_frame": b["start_frame"]})
    return out


def check_bubble_faces(timed: dict, frames: dict, items: list[dict], model: Path | None,
                       faces_fn=None, layout: dict | None = None) -> tuple[list[dict], list[dict]]:
    """PX-BUBBLE-FACE: the bubble found in the pixels hides a face YuNet finds (``faces_fn`` replaces YuNet in tests)."""
    cv2 = _cv2()
    out, rows = [], []
    if faces_fn is None:
        if model is None:
            return out, rows
        faces_fn = lambda fr: detect_faces(cv2, fr, model)  # noqa: E731
    for it in items:
        a, b = frames.get(it["pre"]), frames.get(it["mid"])
        if a is None or b is None:
            continue
        box = bubble_box(cv2, a, b, (layout or {}).get((it["shot"], it["start_frame"])))
        faces = faces_fn(b)
        hit = max((covered_share(box, f) for f in faces), default=0.0) if box else 0.0
        rows.append({"shot": it["shot"], "t": round(it["t"], 3), "bubble": box, "faces": [list(map(round, f)) for f in faces],
                     "covered": round(hit, 2)})
        if box and hit >= BUBBLE_FACE_SHARE:
            _f(out, "PX-BUBBLE-FACE", "REVIEW", f"{it['shot']} {it['text'][:40]!r}", f"the bubble covers {hit:.0%} of a face "
               f"at {it['t']:.2f} s (bubble box {box} on the 960 px frame)", it["t"])
    return out, rows


# --- the whole pass --------------------------------------------------------------------------------------------------------

def available() -> dict:
    have = {}
    for mod in ("cv2", "scenedetect", "skimage", "imagehash"):
        try:
            __import__(mod)
            have[mod] = True
        except ImportError:
            have[mod] = False
    have["yunet"] = yunet_path() is not None
    return have


def check_video(timed: dict, video: Path, offset: float = 0.0, picture_dirs: list[Path] | None = None,
                faces_fn=None) -> dict:
    """Every pixel check on ``video`` (whose first frame is timed time ``offset``): {findings, skipped, measured}."""
    fps = timed["fps"]
    offset_f = round(offset * fps)
    have = available()
    findings: list[dict] = []
    skipped: list[str] = []
    measured: dict = {}
    if not have["cv2"]:
        return {"findings": [], "skipped": ["all pixel checks: opencv-python-headless is not installed"], "measured": {}}
    plan = planned(timed, picture_dirs)
    if have["scenedetect"]:
        detected = detect_cuts(video)
        measured["cuts"] = [round(t + offset, 3) for t in detected]
    else:
        detected = None
        skipped.append("cut list: scenedetect is not installed")
    fb = freeze_black(video)
    measured["freezes"] = [[round(a + offset, 3), None if b is None else round(b + offset, 3)] for a, b in fb["freezes"]]
    measured["blacks"] = [[round(a + offset, 3), round(b + offset, 3)] for a, b in fb["blacks"]]
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(video))
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    items = bubble_frames(timed, offset_f, n_frames)
    keep = {c["frame"] - offset_f + d for c in plan["cuts"] for d in (-1, 0)} | {x for it in items for x in (it["pre"], it["mid"])}
    sc = scan(video, keep)
    n_frames = sc["count"]
    if detected is not None:
        findings += check_cuts(detected, plan, fps, offset_f, n_frames)
    cam, measured["camera"] = check_camera(timed, plan, sc["steps"], offset_f)
    findings += cam
    jc, measured["cuts_framing"] = check_jump_cuts(timed, plan, sc["frames"], offset_f)
    findings += jc
    findings += check_freeze_black(fb, timed, plan, sc["steps"], offset_f, n_frames)
    model = yunet_path()
    if model is None and faces_fn is None:
        skipped.append("bubble over a face: the YuNet model is not in tools/yunet (or $EXPLAINER_YUNET)")
    layout = layout_boxes(timed, picture_dirs) if items else {}
    bf, measured["bubbles"] = check_bubble_faces(timed, sc["frames"], items, model, faces_fn, layout)
    findings += bf
    for f in findings:  # the shot a finding lies in, for the loop's classification
        if "t" in f:
            s = shot_at(timed["shots"], round(f["t"] * fps))
            if s is not None:
                f.setdefault("shot", s["id"])
    return {"findings": findings, "skipped": skipped, "measured": measured, "frames": n_frames, "offset": offset}
