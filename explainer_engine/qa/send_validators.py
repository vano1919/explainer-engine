"""Validators the send gate runs on a candidate before the owner sees it (``governance/send_gate``, spec section 4). Each one is named by a
registry entry of ``owner_requirements.json`` (``check.ref`` = ``module:function``) and has a test on a compliant and on a violating
fixture. Contract: ``fn(path) -> {"status": PASS | FAIL | NOT_RUN, "value": number | None, "detail": str}``; ``fn.kinds`` lists the file
suffixes it applies to. Numpy and ffmpeg, plus OpenCV for the optical flow of ``living_motion`` (without it that validator says NOT_RUN, never a pass).

``living_motion`` (R-LIVING, the owner 2026-11-20 08:33 UTC and 2026-11-14: "only the fire moves" is not alive): on a clip with a still camera
the world must move, not only the flame. Measured on the delivered frames (480x270 grey, 8 frames a second):
- the camera is still: the phase-correlation shift between the two ends of every one-second window stays under ``STILL_SHIFT_PX`` of 480
  (else NOT_RUN: with a moving camera the pixel change is the camera, the rule is about a still one; BP-194 says a camera move alone does not count);
- G-LIVE-1 (BP-194, ``standards/sourced_rules.json``; the 1 px and 25 % are BP-194 thresholds too): no one-second window changes less than ``frozen_change_pct`` of the frame (a pixel counts above
  12 grey levels) - ``value`` is the deadest window's share in %;
- G-LIVE-3 (LIVING_PHOTO_RULES_2026-11-14): when ``<clip>.zones.json`` names the zones of the effects (``{"zones": [{"name": "smoke", "mask": "smoke.png"}]}``,
  mask paths relative to the json, white = zone) at least ``ZONE_MIN_PCT`` % of every zone's pixels change in the median window; without the file the zone
  part is reported as not measured in ``detail`` (the whole-frame number still decides).
The numbers are BP-194's engineering defaults and the rules document's proposals until the owner confirms them (D-59)."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

from explainer_engine.qa import liveliness as LV
from explainer_engine.standards import sourced_rules as SR

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"
SIZE = LV.FROZEN_SIZE                 # (480, 270)
ANALYSIS_FPS = 8
STILL_SHIFT_PX = float(SR.T("BP-194", "still_shift_px"))   # of 480: a camera that moves more than this in a second is not still
ZONE_MIN_PCT = float(SR.T("BP-194", "zone_min_pct"))        # G-LIVE-3: a quarter of the zone's pixels change


def decode_grey(path: Path, fps: int = ANALYSIS_FPS) -> list[np.ndarray]:
    """The clip's frames as float32 grey 480x270 arrays at ``fps`` frames a second (ffmpeg through a pipe)."""
    w, h = SIZE
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg could not decode the file: " + r.stderr.decode("utf-8", "replace")[-200:])
    n = len(r.stdout) // (w * h)
    return list(np.frombuffer(r.stdout[: n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32))


def phase_shift(a: np.ndarray, b: np.ndarray) -> float:
    """The translation between two grey frames in pixels (phase correlation; the length of the shift vector)."""
    fa, fb = np.fft.fft2(a - a.mean()), np.fft.fft2(b - b.mean())
    cross = fa * np.conj(fb)
    cross /= np.maximum(np.abs(cross), 1e-9)
    corr = np.fft.ifft2(cross).real
    iy, ix = np.unravel_index(int(np.argmax(corr)), corr.shape)
    h, w = corr.shape
    dy, dx = (iy - h if iy > h // 2 else iy), (ix - w if ix > w // 2 else ix)
    return float(np.hypot(dx, dy))


def _zones(path: Path) -> list[tuple[str, np.ndarray]]:
    side = path.with_suffix(".zones.json")
    if not side.is_file():
        return []
    from PIL import Image
    out = []
    for z in json.loads(side.read_text(encoding="utf-8")).get("zones", []):
        m = Image.open(side.parent / z["mask"]).convert("L").resize(SIZE)
        out.append((z["name"], np.asarray(m) > 127))
    return out


FLOW_GAP_S = float(SR.T("BP-215", "flow_gap_s"))
CAMERA_INLIERS_MIN = float(SR.T("BP-215", "camera_inliers_min_pct"))
ZONE_COVER_MIN = float(SR.T("BP-215", "zone_cover_min_pct"))
ZONE_SPEED = {"fire": float(SR.T("BP-215", "fire_min_px_s")), "smoke": float(SR.T("BP-215", "smoke_min_px_s")),
              "sky": float(SR.T("BP-215", "sky_min_px_s"))}
FRAME_MIN_PX_S = float(SR.T("BP-215", "frame_min_px_s"))
FRAME_COVER_MIN = float(SR.T("BP-215", "frame_cover_min_pct"))
FIRE_WINDOW_MIN = float(SR.T("BP-215", "fire_window_min_pct"))
FAR_OVER_FG_MAX = float(SR.T("BP-215", "far_over_foreground_max_pct"))
STILL_PRIOR_MIN = float(SR.T("BP-215", "still_prior_min_pct"))
FLOW_CHANGE_MIN = float(SR.T("BP-215", "flow_pixel_change_min"))
FG_DEPTH_MIN = float(SR.T("BP-215", "foreground_depth_min"))
MATTE_ON = 30                         # a matte pixel above this grey level is a particle


def _cv2():
    try:
        import cv2
    except ImportError:
        return None
    return cv2


def _sidecar(path: Path) -> dict:
    side = path.with_suffix(".zones.json")
    if not side.is_file():
        return {}
    data = json.loads(side.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{side.name} is not an object")
    return data


def _zone_masks(path: Path, side: dict) -> list[tuple[str, str, np.ndarray]]:
    """``[(name, kind, mask)]`` of the zones in the clip's ``.zones.json``; ``kind`` (default: the name) is fire, smoke or sky, the kinds that have
    a speed in BP-215 (any other kind raises, so the send gate BLOCKs: a zone with no threshold is never a pass)."""
    from PIL import Image
    out = []
    for z in side.get("zones", []):
        kind = str(z.get("kind") or z["name"]).lower()
        if kind not in ZONE_SPEED:
            raise ValueError(f"zone {z['name']!r} has kind {kind!r}: BP-215 sets a speed for {', '.join(ZONE_SPEED)} only")
        m = Image.open(path.parent / z["mask"]).convert("L").resize(SIZE)
        out.append((z["name"], kind, np.asarray(m) > 127))
    return out


def _flow_fields(g: list[np.ndarray], gap: int, cv2):
    """Farneback flow between frames ``gap`` apart (uint8 grey, 480x270): one (h, w, 2) float32 field per start frame."""
    u8 = [np.clip(f, 0, 255).astype(np.uint8) for f in g]
    return [cv2.calcOpticalFlowFarneback(u8[i], u8[i + gap], None, 0.5, 3, 15, 3, 5, 1.2, 0) for i in range(0, len(u8) - gap)]


def _camera_residual(flow: np.ndarray, exclude: np.ndarray, cv2) -> tuple[np.ndarray, float | None]:
    """The flow minus the camera: a similarity transform fitted by RANSAC to the flow of the pixels outside ``exclude`` (the declared
    zones and the particles), and the share of its inliers (None when no transform could be fitted)."""
    h, w = flow.shape[:2]
    ys, xs = np.mgrid[6:h - 6:6, 6:w - 6:6]
    use = ~exclude[ys, xs]
    if use.sum() < 40:
        use = np.ones_like(use, dtype=bool)
    src = np.stack([xs[use], ys[use]], axis=1).astype(np.float32)
    fv = flow[ys[use], xs[use]]
    still = float((np.hypot(fv[:, 0], fv[:, 1]) < 0.35).mean()) * 100
    if still >= STILL_PRIOR_MIN:                       # a still camera is the default: the world that moves is the minority
        return flow, still
    dst = src + fv
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=0.35, maxIters=2000)
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    if M is None:
        return flow, None
    cam = np.stack([M[0, 0] * gx + M[0, 1] * gy + M[0, 2] - gx, M[1, 0] * gx + M[1, 1] * gy + M[1, 2] - gy], axis=-1)
    return flow - cam, float(np.mean(inl)) * 100


def _depth_check(path: Path, side: dict) -> tuple[str, float | None, str]:
    """Does the foreground hide the far particles? Returns (status, share %, text)."""
    parts, depth = side.get("particles"), side.get("depth")
    if not parts:
        return PASS, None, "no particle layer declared"
    far = parts.get("far") if isinstance(parts, dict) else None
    if not far or not depth:
        return NOT_RUN, None, "a particle layer is declared but its far band or the depth map is missing: occlusion not proven"
    from PIL import Image
    dm = np.asarray(Image.open(path.parent / depth).convert("L").resize(SIZE)).astype(np.float32)
    span = float(dm.max() - dm.min()) or 1.0
    fg = (dm - dm.min()) / span >= FG_DEPTH_MIN
    on = [m > MATTE_ON for m in decode_grey(path.parent / far)]
    total = sum(int(m.sum()) for m in on)
    if total == 0:
        return FAIL, None, "the far-particle matte shows no particle at all: nothing proves the far band exists"
    over = 100.0 * sum(int((m & fg).sum()) for m in on) / total
    if over > FAR_OVER_FG_MAX:
        return FAIL, round(over, 2), (f"{over:.1f} % of the far particles are drawn over foreground pixels (at most {FAR_OVER_FG_MAX:g} %): "
                                      f"the foreground does not hide them (client item 8, BP-215)")
    return PASS, round(over, 2), f"far particles over the foreground {over:.2f} % (at most {FAR_OVER_FG_MAX:g} %)"


def _motion_series(path, g, cv2):
    """The flow loop of ``living_motion`` and ``flame_never_frozen``: per pair of frames ``gap`` apart, the share (%) of each zone's pixels (outside
    the particle layer) that move faster than the zone's speed once the camera is taken out, and of the whole frame. Returns None when the clip is
    too short for a pair, else (zones, cover, frame_cover, inliers, gap)."""
    side = _sidecar(path)
    zones = _zone_masks(path, side)
    parts = side.get("particles") if isinstance(side.get("particles"), dict) else {}
    matte = [m > MATTE_ON for m in decode_grey(path.parent / parts["matte"])] if parts.get("matte") else None
    gap = max(1, int(round(FLOW_GAP_S * ANALYSIS_FPS)))
    flows = _flow_fields(g, gap, cv2)
    if not flows:
        return None
    zone_union = np.zeros((SIZE[1], SIZE[0]), bool)
    for _, _, m in zones:
        zone_union |= m
    dt = gap / ANALYSIS_FPS
    cover = {name: [] for name, _, _ in zones}
    frame_cover, inliers = [], []
    k = np.ones((5, 5), np.uint8)
    for i, fl in enumerate(flows):
        parts_i = np.zeros_like(zone_union)
        if matte is not None:
            parts_i = cv2.dilate((matte[i] | matte[min(i + gap, len(matte) - 1)]).astype(np.uint8), k).astype(bool)
        resid, inl = _camera_residual(fl, zone_union | parts_i, cv2)
        if inl is not None:
            inliers.append(inl)
        speed = np.hypot(resid[..., 0], resid[..., 1]) / dt
        speed = np.where(np.abs(g[i + gap] - g[i]) >= FLOW_CHANGE_MIN, speed, 0.0)    # a pixel that did not change does not move (flow smear)
        for name, kind, m in zones:
            valid = m & ~parts_i
            if valid.sum() >= 50:
                cover[name].append(float((speed[valid] >= ZONE_SPEED[kind]).mean() * 100))
        keep = ~parts_i
        frame_cover.append(float((speed[keep] >= FRAME_MIN_PX_S).mean() * 100) if keep.any() else 0.0)
    return zones, cover, frame_cover, inliers, gap


def living_motion(path) -> dict:
    path = Path(path)
    g = decode_grey(path)
    step = max(1, int(round(ANALYSIS_FPS * LV.FROZEN_WINDOW_S)))
    if len(g) <= step:
        return {"status": NOT_RUN, "value": None, "detail": f"too short for a one-second window ({len(g)} frames at {ANALYSIS_FPS} fps)"}
    # 1. G-LIVE-1: no one-second window may stand (pixel change, kept: it is the cheap guard of the whole frame)
    fw = LV.frozen_windows_grey(g, ANALYSIS_FPS)
    low = fw["min_share_pct"]
    if fw["frozen"]:
        return {"status": FAIL, "value": low, "detail": f"{fw['frozen']} of {fw['windows']} one-second windows change under {LV.FROZEN_CHANGE:g} % of the "
                f"frame (deadest {low:.2f} % from {fw['frozen_from_s'][0]:.1f} s): only a small part moves (G-LIVE-1, BP-194)"}
    # 2. optical flow with the camera taken out (client item 8, BP-215)
    cv2 = _cv2()
    if cv2 is None:
        return {"status": NOT_RUN, "value": low, "detail": "optical flow needs OpenCV (opencv-python-headless): the motion is not measured, "
                "never passed; the owner's eye judges this clip"}
    side = _sidecar(path)
    series = _motion_series(path, g, cv2)
    if series is None:
        return {"status": NOT_RUN, "value": low, "detail": f"too short for optical flow ({len(g)} frames, gap {max(1, int(round(FLOW_GAP_S * ANALYSIS_FPS)))})"}
    zones, cover, frame_cover, inliers, gap = series
    cam = float(np.median(inliers)) if inliers else 0.0
    if cam < CAMERA_INLIERS_MIN:
        return {"status": NOT_RUN, "value": round(cam, 1), "detail": f"the camera could not be separated from the motion ({cam:.0f} % inliers, at "
                f"least {CAMERA_INLIERS_MIN:g} %): the owner's eye judges this clip"}
    notes, worst = [], None
    if zones:
        for name, kind, _ in zones:
            vals = cover[name]
            med = float(np.median(vals)) if vals else 0.0
            if med < ZONE_COVER_MIN:
                why = "only the particle layer moves in it" if not vals else "the effect barely moves"
                return {"status": FAIL, "value": round(med, 2), "detail": f"the {name} zone has {med:.1f} % of its pixels moving over "
                        f"{ZONE_SPEED[kind]:g} px/s with the camera and the particles taken out (at least {ZONE_COVER_MIN:g} %): {why} (G-LIVE-3, BP-215)"}
            notes.append(f"{name} {med:.1f} %")
            worst = med if worst is None else min(worst, med)
    else:
        med = float(np.median(frame_cover))
        if med < FRAME_COVER_MIN:
            return {"status": FAIL, "value": round(med, 2), "detail": f"only {med:.1f} % of the frame moves over {FRAME_MIN_PX_S:g} px/s once the "
                    f"camera is taken out (at least {FRAME_COVER_MIN:g} %): a camera move or a few particles alone do not make it alive (BP-215)"}
        worst = med
        notes.append("no .zones.json, whole frame " + f"{med:.1f} %")
    status, share, text = _depth_check(path, side)
    if status == FAIL:
        return {"status": FAIL, "value": share, "detail": text}
    zone_text = ("zones " + ", ".join(notes)) if zones else notes[0]
    return {"status": status, "value": round(worst, 2) if worst is not None else low,
            "detail": f"deadest second changes {low:.2f} % of the frame (floor {LV.FROZEN_CHANGE:g} %); flow with the camera out ({cam:.0f} % inliers): "
                      f"{zone_text}; {text}"}


living_motion.kinds = (".mp4", ".mov", ".webm", ".mkv")


def director_reasons(path) -> dict:
    """OR-V29 and OR-V51 (the owner: the director decides each effect himself from the words, the photo and the tool list, and records a short reason;
    every effect and every sound cue carries a reason field from the director stage; no hand-written lists) on a shot-direction file: every
    ``seen.living`` element (animate, add and skip alike), every ``weather`` record, the audio track and every sound event of ``sound.events`` carries a
    non-empty ``why``, and every effect track belongs to an inventory element that names it in ``effects`` (a track no element names was typed by hand).
    The director's own writer (``production/living_director``) emits all of these, so a file it wrote passes. Not checked: that the plan can be
    reproduced from the photo and the words alone (OR-V51's last clause needs the director run again). A file that is not a shot direction is NOT_RUN."""
    from explainer_engine.production import direction as DIR
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("schema") != DIR.SCHEMA:
        return {"status": NOT_RUN, "value": None, "detail": f"not a shot direction file (schema {DIR.SCHEMA!r}): the reasons are not measured"}
    living = (d.get("seen") or {}).get("living")
    effect_tracks = [t for t in d.get("tracks") or [] if t.get("track") not in ("camera", "audio") and t.get("op") in DIR.EFFECT_OPS]
    if living is None:
        if effect_tracks:
            return {"status": FAIL, "value": len(effect_tracks), "detail": f"{len(effect_tracks)} effect track(s) and no seen.living: the effects were typed "
                    "by hand, not chosen from an inventory (OR-V51)"}
        return {"status": NOT_RUN, "value": None, "detail": "no seen.living and no effect track: nothing to give a reason"}
    bad = []
    for e in living:
        if not str(e.get("why", "")).strip():
            bad.append(f"living {e.get('id', '?')} ({e.get('decision')}) has no why")
    named = {tid for e in living for tid in (e.get("effects") or [])}
    for t in effect_tracks:
        if t.get("id") not in named:
            bad.append(f"effect track {t.get('id', '?')} ({t.get('op')}) is named by no living element: typed by hand")
    for r in d.get("weather") or []:
        if not str(r.get("why", "")).strip():
            bad.append(f"weather {r.get('weather', '?')} has no why")
    for t in d.get("tracks") or []:
        if t.get("track") == "audio" and not str(t.get("why", "")).strip():
            bad.append("the audio track has no why")
    for ev in ((d.get("sound") or {}).get("events") or []):
        if not str(ev.get("why", "")).strip():
            bad.append(f"sound event {ev.get('event_id') or ev.get('class', '?')} has no why")
    if bad:
        return {"status": FAIL, "value": len(bad), "detail": f"{len(bad)} choice(s) without the director's reason: {bad[0]}" + (f" (+{len(bad) - 1} more)" if len(bad) > 1 else "")}
    n = len(living) + len(d.get("weather") or []) + len((d.get("sound") or {}).get("events") or [])
    return {"status": PASS, "value": 0, "detail": f"{n} choices (living elements, weather, sound events) carry a reason and {len(effect_tracks)} effect track(s) belong to the inventory"}


director_reasons.kinds = (".json",)


def no_body_motion_in_25d(path) -> dict:
    """OR-V25 (LP-02 of LIVING_PHOTO_RULES_2026-11-14, the team's rule until the owner confirms it: a body that must move - lips, hands, a turned head -
    is LTX's work, not 2.5D's) on a shot-direction file: FAIL when a 2.5D track moves a body (``subject_sway`` on ``directed25d`` or ``layers25d``) or
    an inventory element of kind ``body`` (or flagged ``body_motion``) is animated or added instead of being routed to LTX. A body element that is
    skipped with a reason (routed to LTX) is listed and passes. NOTE for the lead: ``direction.LIVING_KINDS`` still lets the kind ``body`` take
    ``subject_sway``, so the repo's own gate accepts what this one fails; the owner's LP-02 wins here. A file that is not a shot direction is NOT_RUN."""
    from explainer_engine.production import direction as DIR
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("schema") != DIR.SCHEMA:
        return {"status": NOT_RUN, "value": None, "detail": f"not a shot direction file (schema {DIR.SCHEMA!r}): body motion is not measured"}
    bad, routed = [], []
    for t in d.get("tracks") or []:
        if t.get("track") not in ("camera", "audio") and t.get("op") == "subject_sway" and t.get("renderer") in ("directed25d", "layers25d"):
            bad.append(f"track {t.get('id', '?')} sways the subject in 2.5D")
    for e in (d.get("seen") or {}).get("living") or []:
        if e.get("kind") == "body" or e.get("body_motion"):
            if e.get("decision") in ("animate", "add"):
                bad.append(f"living {e.get('id', '?')} is a body animated in 2.5D")
            else:
                routed.append(str(e.get("id", "?")))
    if bad:
        return {"status": FAIL, "value": len(bad), "detail": f"body motion in the 2.5D plan: {bad[0]}" + (f" (+{len(bad) - 1} more)" if len(bad) > 1 else "") + " (LP-02: LTX moves bodies)"}
    tail = f"; {len(routed)} body element(s) left to LTX: {', '.join(routed)}" if routed else ""
    return {"status": PASS, "value": 0, "detail": "the 2.5D plan moves no body (LP-02)" + tail}


no_body_motion_in_25d.kinds = (".json",)


def flame_never_frozen(path) -> dict:
    """OR-V21 (LP-06: a visible flame is never frozen; the entry: flow inside the flame mask above zero in every one-second window): the flow of
    ``living_motion`` (camera and particle layer out) read per one-second window instead of as a median over the clip. Every zone of kind ``fire`` in
    the clip's ``.zones.json`` must have, in each full one-second window, at least one pair of frames in which ``fire_window_min_pct`` % (BP-215) of
    its pixels move faster than the fire speed. A window under that is a FAIL naming the zone and the second it starts. No fire zone declared,
    no OpenCV, a clip shorter than a second or a camera that cannot be separated is NOT_RUN: a flame that was not looked for is never a pass."""
    path = Path(path)
    cv2 = _cv2()
    if cv2 is None:
        return {"status": NOT_RUN, "value": None, "detail": "optical flow needs OpenCV (opencv-python-headless): the flame is not measured"}
    fires = [(n, m) for n, k, m in _zone_masks(path, _sidecar(path)) if k == "fire"]
    if not fires:
        return {"status": NOT_RUN, "value": None, "detail": "no zone of kind fire in the clip's .zones.json: the flame is not located, so not measured"}
    g = decode_grey(path)
    series = _motion_series(path, g, cv2)
    if series is None:
        return {"status": NOT_RUN, "value": None, "detail": f"too short for optical flow ({len(g)} frames)"}
    _, cover, _, inliers, _ = series
    cam = float(np.median(inliers)) if inliers else 0.0
    if cam < CAMERA_INLIERS_MIN:
        return {"status": NOT_RUN, "value": round(cam, 1), "detail": f"the camera could not be separated from the motion ({cam:.0f} % inliers, at least "
                f"{CAMERA_INLIERS_MIN:g} %): the flame is not measured"}
    step = int(round(ANALYSIS_FPS * LV.FROZEN_WINDOW_S))
    worst, bad = None, []
    for name, _ in fires:
        vals = cover.get(name) or []
        wins = [vals[i:i + step] for i in range(0, len(vals) - step + 1, step)]
        if not wins:
            return {"status": NOT_RUN, "value": None, "detail": f"the {name} zone is too small to measure (under 50 pixels) or the clip is under one window"}
        for w, win in enumerate(wins):
            best = max(win)
            worst = best if worst is None else min(worst, best)
            if best < FIRE_WINDOW_MIN:
                bad.append(f"{name} from {w * LV.FROZEN_WINDOW_S:.0f} s ({best:.1f} %)")
    if bad:
        return {"status": FAIL, "value": round(worst, 2), "detail": f"a visible flame stands still: {len(bad)} one-second window(s) with under "
                f"{FIRE_WINDOW_MIN:g} % of the fire zone moving over {ZONE_SPEED['fire']:g} px/s, first {bad[0]} (LP-06, BP-215)"}
    return {"status": PASS, "value": round(worst, 2), "detail": f"every one-second window of {len(fires)} fire zone(s) moves; the quietest window has "
            f"{worst:.1f} % of the zone moving (floor {FIRE_WINDOW_MIN:g} %, LP-06, BP-215)"}


flame_never_frozen.kinds = (".mp4", ".mov", ".webm", ".mkv")


def change_per_second(path) -> dict:
    """OR-V26 (memory feedback-realism-audit 2026-11-12: "motion at least as alive as Gemini's demo, 3.6-12.2 % frame change per second on photos"):
    the 2026-11-12 reference measurement (``liveliness.change_per_s``: 128x72 grey, frames one second apart, mean absolute difference in % of 255,
    sampled every half second) on the delivered clip. Under the BP-194 floor ``change_floor_pct_s`` is a FAIL; the number is printed next to the
    reference range. Whole frame, camera included (the reference method; the camera is taken out by ``living_motion``, not here). Needs OpenCV
    for the resize (without it NOT_RUN). The registry entry's own text says "< 5 %/s fails": the 5 % there is G-LIVE-1's deadest-window floor,
    which ``living_motion`` checks; the floor of this check is BP-194's 3.6 %/s, the lower end of the reference."""
    if _cv2() is None:
        return {"status": NOT_RUN, "value": None, "detail": "the reference measurement needs OpenCV for its resize: not measured"}
    g = decode_grey(Path(path))
    if len(g) <= ANALYSIS_FPS:
        return {"status": NOT_RUN, "value": None, "detail": f"too short for frames one second apart ({len(g)} frames at {ANALYSIS_FPS} fps)"}
    ch = LV.change_per_s(g, ANALYSIS_FPS)
    v = ch["pct_per_s"]
    lo, hi = LV.CHANGE_REF
    ref = f"reference {lo:g}-{hi:g} %/s"
    if v is None:
        return {"status": NOT_RUN, "value": None, "detail": "no pair of frames one second apart"}
    if v < LV.CHANGE_FLOOR:
        return {"status": FAIL, "value": v, "detail": f"the frame changes {v} %/s, under the floor {LV.CHANGE_FLOOR:g} ({ref}; BP-194)"}
    return {"status": PASS, "value": v, "detail": f"the frame changes {v} %/s (floor {LV.CHANGE_FLOOR:g}, {ref}; BP-194)"}


change_per_second.kinds = (".mp4", ".mov", ".webm", ".mkv")


def living_inventory(path) -> dict:
    """OR-V20 (the owner 2026-11-14: the director lists the photo's living elements, gives each an effect by priority, with the balance rules
    LP-01..LP-12; G-INV, G-BAL, G-WX of LIVING_PHOTO_RULES_2026-11-14) on a shot-direction file (``shot_direction/1``): runs the repo's own
    gates, the same ones ``production/direction.check`` runs before a render: the living inventory with a decision or a reason for every element
    (``_living``, BP-196), the scene's weather as a ceiling (``_weather``, LP-09 as amended 12:38 UTC) and the balance of the plan (``living.check``:
    LP-01..LP-08, the 5-second caps, the floor of moving air; it needs the shot's ``duration_s`` or ``frames`` and ``fps``). A FAIL finding is a FAIL;
    REVIEW findings are listed in ``detail`` and never fail. A file that is not a shot direction is NOT_RUN; a balance that could not be measured
    (no duration) is NOT_RUN, never a pass. The mp4 gates G-LIVE-1..4 are ``living_motion``'s (OR-V19, OR-V26), not this one's."""
    from explainer_engine.production import direction as DIR
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict) or d.get("schema") != DIR.SCHEMA:
        return {"status": NOT_RUN, "value": None, "detail": f"not a shot direction file (schema {DIR.SCHEMA!r}): the living inventory is not measured"}
    findings = DIR._living(d, None) + DIR._weather(d)
    dur = d.get("duration_s")
    if dur is None and d.get("frames"):
        dur = float(d["frames"]) / float(d.get("fps") or 24)
    if dur:
        findings += DIR._balance(d, float(dur))
    fails = [f["what"] for f in findings if f.get("level") == "FAIL"]
    reviews = [f["what"] for f in findings if f.get("level") != "FAIL"]
    tail = (f"; REVIEW: {reviews[0]}" + (f" (+{len(reviews) - 1} more)" if len(reviews) > 1 else "")) if reviews else ""
    if fails:
        return {"status": FAIL, "value": len(fails), "detail": f"{len(fails)} living-inventory finding(s): {fails[0]}"
                + (f" (+{len(fails) - 1} more)" if len(fails) > 1 else "") + tail + " (G-INV/G-BAL/G-WX, BP-196, BP-200)"}
    if not dur:
        return {"status": NOT_RUN, "value": 0, "detail": "the inventory and the weather pass; the balance (LP-07/LP-08) is not measured: the file has no "
                "duration_s (or frames) " + tail}
    return {"status": PASS, "value": 0, "detail": f"the living inventory, the weather ceiling and the balance of a {float(dur):.1f} s shot pass{tail}"}


living_inventory.kinds = (".json",)


_OPERATOR_MODE = re.compile(r"^(?:MODE:\s*(\w+)|chat mode\s*\**\s*(\w+))", re.I)


def operator_mode(text: str) -> str | None:
    """The mode the OPERATOR (the person or thread that pasted the batch) recorded: a ``MODE: task`` line, or the REPORT.md form
    ``chat mode **Task**``. The chat cannot know its own mode, so the ``MODE:`` inside a ``T0 REPORT`` (``MODEL: x | MODE: y``, the
    chat's own words) is not an operator line."""
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip().lstrip(">*- ").replace("**", "").replace("`", "").strip()
        m = _OPERATOR_MODE.match(line)
        if m:
            return (m.group(1) or m.group(2)).lower()
    return None


def gemini_task_report(path) -> dict:
    """Rule 19 (OR-V35, the owner's memory rule: Gemini photos only in Task mode, 6 per batch) on the intake record of a Gemini turn: a text
    file holding the pasted answer (a ``T0 REPORT`` or a ``BATCH REPORT`` of ``gemini_task/report.py``; a structure that does not parse
    raises, so the send gate BLOCKs, it is never a pass) and the operator's mode line (``operator_mode``).

    - **Count**: more picture lines than ``imagegen.turn_pack.DEFAULT_TURN`` (6) is a FAIL; a shorter batch is fine (a queue's last
      batch or a limit stop is shorter and the report cannot say which).
    - **Mode** (lead 2026-11-20 09:06): an operator line naming Task and a count of 6 or less is PASS; no operator line is NOT_RUN
      "mode not measured"; an operator mode other than Task is FAIL. A chat's own T0 ``MODE:`` naming something else is a FAIL too, but
      never a pass by itself."""
    from explainer_engine.gemini_task import report as RP
    from explainer_engine.imagegen import turn_pack as TP
    text = Path(path).read_text(encoding="utf-8")
    t0 = "T0 REPORT" in text.upper()
    rep = RP.parse_t0_report(text) if t0 else {"batch": RP.parse_batch_report(text), "mode": None}
    n = len(rep["batch"]["items"])
    limit = int(TP.DEFAULT_TURN)
    mode = operator_mode(text)
    if mode is not None and mode != "task":
        return {"status": FAIL, "value": n, "detail": f"the operator recorded mode {mode!r}, rule 19 allows Gemini photos only in Task mode"}
    if t0 and rep["mode"] and "task" not in rep["mode"].lower():
        return {"status": FAIL, "value": n, "detail": f"the chat reports MODE {rep['mode']!r}, rule 19 allows Gemini photos only in Task mode"}
    if n > limit:
        return {"status": FAIL, "value": n, "detail": f"{n} pictures in one batch, rule 19 allows {limit}"}
    if mode is None:
        return {"status": NOT_RUN, "value": n, "detail": f"{n} of at most {limit} pictures (counted), but no operator MODE line "
                "(`MODE: task` or `chat mode **Task**`): the mode is not measured"}
    return {"status": PASS, "value": n, "detail": f"{n} of at most {limit} pictures; operator mode task"}


gemini_task_report.kinds = (".txt", ".md")


FACE_IOU_MIN = float(SR.T("BP-214", "face_iou_min"))   # REVIEW-level engineering default (hypothesis, not binding until the owner has seen it)


def yunet_boxes(path) -> list[tuple[float, float, float, float]]:
    """YuNet face boxes of one picture as ``(x0, y0, x1, y1)`` in shares of the picture, from ``qa.face_points.detect`` (the project's one
    YuNet call). Raises ``RuntimeError`` when OpenCV or the model is missing: the caller says NOT_RUN."""
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    model = PX.yunet_path()
    if PX._cv2() is None or model is None:
        raise RuntimeError("OpenCV or the YuNet model (tools/yunet or $EXPLAINER_YUNET) is missing")
    return [(f["x"] - f["w"] / 2, f["y"] - f["h"] / 2, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2) for f in FP.detect(Path(path), model)]


def iou(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    inter = max(0.0, w) * max(0.0, h)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def faces_intact_pair(before, after, detect=None) -> dict:
    """BP-214 (OR-V36): the same number of faces before and after, and every face box of the result overlapping its original at IoU of at
    least ``FACE_IOU_MIN``. Each original face is matched to the unused result face with the best overlap, in left-to-right order of the
    originals. ``detect(path)`` returns boxes in shares (default ``yunet_boxes``); no OpenCV or model, or no face in the original, is
    NOT_RUN, never a pass. The value is the lowest IoU. A hypothesis rule: the FAIL text says so."""
    detect = detect or yunet_boxes
    try:
        b, a = detect(before), detect(after)
    except RuntimeError as exc:
        return {"status": NOT_RUN, "value": None, "detail": f"faces not measured: {exc}"}
    tag = f"(BP-214 REVIEW-level default, IoU at least {FACE_IOU_MIN}, not binding until the owner has seen it)"
    if not b and not a:
        return {"status": NOT_RUN, "value": None, "detail": "no face found in the original or the result: nothing to compare"}
    if len(b) != len(a):
        return {"status": FAIL, "value": None, "detail": f"{len(b)} face(s) before, {len(a)} after {tag}"}
    free = list(a)
    worst = 1.0
    for box in sorted(b, key=lambda x: x[0]):
        best = max(free, key=lambda c: iou(box, c))
        free.remove(best)
        worst = min(worst, iou(box, best))
    worst = round(worst, 4)
    if worst < FACE_IOU_MIN:
        return {"status": FAIL, "value": worst, "detail": f"a face moved or changed: lowest IoU {worst} of {len(b)} face(s) {tag}"}
    return {"status": PASS, "value": worst, "detail": f"{len(b)} face(s), lowest IoU {worst} {tag}"}


def faces_intact(path) -> dict:
    """The send-gate adapter of ``faces_intact_pair``: a ``<name>.faces.json`` pair file ``{"before": "a.png", "after": "b.png"}`` (paths
    relative to the pair file). A ``.json`` without those two keys is NOT_RUN (not a pair file); a missing picture raises (BLOCK)."""
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not {"before", "after"} <= set(doc):
        return {"status": NOT_RUN, "value": None, "detail": "not a faces pair file (needs keys before and after)"}
    before, after = p.parent / doc["before"], p.parent / doc["after"]
    for f in (before, after):
        if not f.is_file():
            raise FileNotFoundError(f"{f} is not a picture")
    return faces_intact_pair(before, after)


faces_intact.kinds = (".json",)


def main(argv=None) -> int:
    """``python -m explainer_engine.qa.send_validators living_motion|gemini_task_report|faces_intact|living_inventory|change_per_second|flame_never_frozen|director_reasons|no_body_motion_in_25d <file>...``: one line per clip, exit 1 on any FAIL, 2 on an error."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.send_validators")
    ap.add_argument("validator", choices=("living_motion", "gemini_task_report", "faces_intact", "living_inventory", "change_per_second", "flame_never_frozen", "director_reasons", "no_body_motion_in_25d"))
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    worst = 0
    for f in a.files:
        try:
            r = {"living_motion": living_motion, "gemini_task_report": gemini_task_report, "faces_intact": faces_intact, "living_inventory": living_inventory,
                 "change_per_second": change_per_second, "flame_never_frozen": flame_never_frozen, "director_reasons": director_reasons,
                 "no_body_motion_in_25d": no_body_motion_in_25d}[a.validator](f)
        except Exception as exc:                       # an undecodable file is an error, never a pass
            print(f"BLOCK {f}: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        print(f"{r['status']:8} {'' if r['value'] is None else r['value']!s:>7}  {f}  {r['detail']}")
        worst = max(worst, 1 if r["status"] == FAIL else 0)
    return worst


if __name__ == "__main__":
    import sys
    sys.exit(main())
