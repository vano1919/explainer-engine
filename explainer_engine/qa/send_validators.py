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
from types import SimpleNamespace

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
              "sky": float(SR.T("BP-215", "sky_min_px_s")), "wind": float(SR.T("BP-215", "wind_min_px_s"))}
FRAME_MIN_PX_S = float(SR.T("BP-215", "frame_min_px_s"))
FRAME_COVER_MIN = float(SR.T("BP-215", "frame_cover_min_pct"))
FIRE_WINDOW_MIN = float(SR.T("BP-215", "fire_window_min_pct"))
NEAR_FAR_MIN = float(SR.T("BP-215", "near_far_ratio_min"))
UNDECLARED_SPECK_MAX = float(SR.T("BP-215", "undeclared_speck_max_pct"))
FG_AREA_MIN = float(SR.T("BP-215", "foreground_area_min_pct"))
FAR_OVER_FG_MAX = float(SR.T("BP-215", "far_over_foreground_max_pct"))
STILL_PRIOR_MIN = float(SR.T("BP-215", "still_prior_min_pct"))
FLOW_CHANGE_MIN = float(SR.T("BP-215", "flow_pixel_change_min"))
FG_DEPTH_MIN = float(SR.T("BP-215", "foreground_depth_min"))
PARTICLE_MAX_PX = int(SR.T("BP-215", "particle_max_px"))
PARTICLE_MAX_SIDE = int(SR.T("BP-215", "particle_max_side_px"))
PARTICLE_SHARE_MIN = float(SR.T("BP-215", "particle_share_min_pct"))
EXPLAIN_RATIO = float(SR.T("BP-215", "explain_ratio_max"))                  # the compensated error must be under this share of the plain error for the flow to count as a motion
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
    """``[(name, kind, mask)]`` of the zones in the clip's ``.zones.json``; ``kind`` (default: the name) is fire, smoke, sky or wind, the kinds that have
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


def _normalised(g: list[np.ndarray]) -> list[np.ndarray]:
    """Every frame brought to the clip's median mean and spread: a brightness pulse of the whole picture (a gain or an offset) is not motion, so it
    must not reach the flow or the change gate (tester Z2). Content that really moves changes neither the mean nor the spread of a frame much."""
    mu = np.array([float(f.mean()) for f in g])
    sd = np.array([float(f.std()) for f in g])
    mu0, sd0 = float(np.median(mu)), float(np.median(sd))
    return [np.clip((f - m) * (sd0 / s_ if s_ > 1e-6 else 1.0) + mu0, 0, 255).astype(np.float32) for f, m, s_ in zip(g, mu, sd)]


def _compensated(a: np.ndarray, b: np.ndarray, flow: np.ndarray, cv2) -> tuple[np.ndarray, np.ndarray]:
    """(plain error, error after compensation) per pixel: ``|b - a|`` and ``|b sampled where the flow from ``a`` points - a|``."""
    h, w = a.shape
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    flow = flow.astype(np.float32)
    warped = cv2.remap(b, gx + flow[..., 0], gy + flow[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return np.abs(b - a), np.abs(warped - a)


def _explained(e0: np.ndarray, e1: np.ndarray, mask: np.ndarray) -> bool:  # e0: error after the camera alone, e1: after the whole flow
    """Is the flow a motion and not noise (tester Z1, Z2)? Over the pixels of ``mask`` that changed, the error left after moving the picture by the
    flow is under ``EXPLAIN_RATIO`` of the plain error: Farneback reads independent noise as smooth flow, but the compensated picture then matches
    the next frame no better than the plain one (measured on the fixtures: noise 0.75, grain 0.75, a swaying band 0.55, drifting smoke 0.05-0.4)."""
    m = mask & (e0 > FLOW_CHANGE_MIN)
    if int(m.sum()) < 20:
        return False
    return float(e1[m].mean() / e0[m].mean()) < EXPLAIN_RATIO


def _flow_fields(g: list[np.ndarray], gap: int, cv2):
    """Farneback flow between frames ``gap`` apart (uint8 grey, 480x270): one (h, w, 2) float32 field per start frame."""
    u8 = [np.clip(f, 0, 255).astype(np.uint8) for f in g]
    return [cv2.calcOpticalFlowFarneback(u8[i], u8[i + gap], None, 0.5, 3, 15, 3, 5, 1.2, 0) for i in range(0, len(u8) - gap)]


LAYERED = True
LAYER_MOVING_PX = float(SR.T("BP-215", "layer_moving_px"))          # a flow vector longer than this (px per gap) is a moving sample
LAYER_EXTENT_MIN = float(SR.T("BP-215", "layer_extent_min_pct"))        # % of the samples outside the zones that must move for a camera to be the cause
LAYER_QUADRANTS_MIN = int(SR.T("BP-215", "layer_quadrants_min"))        # quadrants of the frame in which at least LAYER_QUAD_MIN % of the samples move
LAYER_QUAD_MIN = float(SR.T("BP-215", "layer_quadrant_moving_min_pct"))
LAYER_EXPLAINED_MIN = float(SR.T("BP-215", "layer_explained_min_pct"))     # % of the moving flow energy the banded camera must explain
LAYER_MEDIAN_CELLS = int(SR.T("BP-215", "layer_median_cells"))
LAYER_GUARD_PX = int(SR.T("BP-215", "layer_guard_px"))
LAYER_BORDER_PCT = float(SR.T("BP-215", "layer_border_pct"))         # width of the border strips, % of the frame side
LAYER_BORDER_MOVING_MIN = float(SR.T("BP-215", "layer_border_moving_min_pct")) # % of a strip's samples that move for the strip to count
LAYER_BORDERS_MIN = int(SR.T("BP-215", "layer_borders_min"))          # strips (of top, bottom, left, right) that must move
LAYER_EDGE_S = float(SR.T("BP-215", "layer_edge_share"))
LAYER_MIN_R_PX = float(SR.T("BP-215", "layer_min_radius_px"))


def _layered_camera(flow: np.ndarray, exclude: np.ndarray, cv2):
    """The camera of a depth-layered move (Z17): every pixel moves as ``s(x)`` times one camera field (push about a centre, or a pan), ``s`` the depth band's
    weight, smooth in space. Returns (residual, share of the moving energy the camera explains) or None when the flow is not such a camera: too few of
    the samples outside the declared zones move, or they do not move in most of the frame, or the explained share is low (noise, local life)."""
    h, w = flow.shape[:2]
    ys, xs = np.mgrid[6:h - 6:6, 6:w - 6:6]
    near = cv2.dilate(exclude.astype(np.uint8), np.ones((LAYER_GUARD_PX, LAYER_GUARD_PX), np.uint8)).astype(bool)   # the flow window smears a zone's life over its neighbours
    use = ~near[ys, xs]
    if int(use.sum()) < 40:
        return None
    fx, fy = flow[ys, xs, 0], flow[ys, xs, 1]
    mag = np.hypot(fx, fy)
    mov = (mag >= LAYER_MOVING_PX) & use
    if float(mov.sum()) * 100.0 / float(use.sum()) < LAYER_EXTENT_MIN:
        return None
    quads = 0
    for qy in (slice(0, ys.shape[0] // 2), slice(ys.shape[0] // 2, None)):
        for qx in (slice(0, xs.shape[1] // 2), slice(xs.shape[1] // 2, None)):
            u = use[qy, qx]
            if u.any() and float(mov[qy, qx].sum()) * 100.0 / float(u.sum()) >= LAYER_QUAD_MIN:
                quads += 1
    if quads < LAYER_QUADRANTS_MIN:
        return None
    ring = 0                                             # a camera moves the picture up to its border; a region of life (smoke, cloud) stops short of it
    bw, bh = int(w * LAYER_BORDER_PCT / 100), int(h * LAYER_BORDER_PCT / 100)
    for strip in (ys < bh, ys >= h - bh, xs < bw, xs >= w - bw):
        u = use & strip
        if u.any() and float((mov & strip).sum()) * 100.0 / float(u.sum()) >= LAYER_BORDER_MOVING_MIN:
            ring += 1
    if ring < LAYER_BORDERS_MIN:
        return None
    m = mov
    best = None
    d = np.array([fx[m].mean(), fy[m].mean()])             # candidate 1: a pan, every flow along one direction
    if np.hypot(*d) > 1e-6:
        d = d / np.hypot(*d)
        best = np.stack([np.full((h, w), d[0], np.float32), np.full((h, w), d[1], np.float32)], axis=-1)
    px_, py_ = xs[m].astype(np.float64), ys[m].astype(np.float64)   # candidate 2: a push, every flow along a line through one centre
    ux, uy = fx[m] / mag[m], fy[m] / mag[m]
    wt = np.ones(px_.size)
    c = np.array([w / 2.0, h / 2.0])
    for _ in range(3):
        A = np.stack([uy, -ux], axis=1) * wt[:, None]
        b = (uy * px_ - ux * py_) * wt
        c = np.linalg.lstsq(A, b, rcond=None)[0]
        r = np.abs(ux * (py_ - c[1]) - uy * (px_ - c[0]))
        wt = 1.0 / np.maximum(r, 5.0)
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    shape_r = np.stack([gx - c[0], gy - c[1]], axis=-1).astype(np.float32)
    cands = [shape_r] + ([best] if best is not None else [])
    out = None
    for shp in cands:
        sh = shp[ys, xs]
        n2 = (sh ** 2).sum(-1)
        ok = use & ((np.sqrt(n2) >= LAYER_MIN_R_PX) if shp is shape_r else (n2 > 0.5))
        if int(ok.sum()) < 40:
            continue
        s = np.where(ok, (fx * sh[..., 0] + fy * sh[..., 1]) / np.maximum(n2, 1e-9), np.nan)
        s = np.clip(s, 0.0, None)
        k = LAYER_MEDIAN_CELLS
        sp = np.pad(s, k // 2, mode="edge")
        win = np.lib.stride_tricks.sliding_window_view(sp, (k, k)).reshape(s.shape + (k * k,))
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sm = np.nanmedian(win, axis=-1)
        known = np.isfinite(sm)
        if not known.any():
            continue
        observed = sm.copy()
        if not known.all():
            _, lab = cv2.distanceTransformWithLabels((~known).astype(np.uint8), cv2.DIST_L2, 3, labelType=cv2.DIST_LABEL_PIXEL)
            idx = np.zeros(int(lab.max()) + 1)
            idx[lab[known]] = sm[known]
            sm = idx[lab]
        sfull = cv2.resize(sm.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        resid = flow - sfull[..., None] * shp
        e_f = float((flow[ys, xs][mov] ** 2).sum())
        e_r = float((resid[ys, xs][mov] ** 2).sum())
        explained = 100.0 * (1.0 - e_r / max(e_f, 1e-9))
        # an edge between two bands: the flow there is a blend, not a motion (judged on the cells the flow was read from, never on the filled ones)
        mx = cv2.dilate(np.where(known, observed, -np.inf).astype(np.float32), np.ones((3, 3), np.uint8))
        mn = cv2.erode(np.where(known, observed, np.inf).astype(np.float32), np.ones((3, 3), np.uint8))
        ref = max(float(np.nanpercentile(s[ok], 90)), 1e-9)                     # the band weights are relative to the strongest band
        fin = (mx > -1e30) & (mn < 1e30)                        # cv2 turns the infinities into the largest floats
        edge = (fin & (np.where(fin, mx, 0.0) - np.where(fin, mn, 0.0) > LAYER_EDGE_S * ref)).astype(np.uint8)
        edge = cv2.dilate(cv2.resize(edge, (w, h), interpolation=cv2.INTER_NEAREST), np.ones((9, 9), np.uint8)).astype(bool)
        resid = np.where(edge[..., None], 0.0, resid).astype(np.float32)
        if out is None or explained > out[1]:
            out = (resid, explained)
    if out is None or out[1] < LAYER_EXPLAINED_MIN:
        return None
    return out


def _camera_residual(flow: np.ndarray, exclude: np.ndarray, cv2, unchanged: np.ndarray | None = None) -> tuple[np.ndarray, float | None]:
    """The flow minus the camera: a similarity transform fitted by RANSAC to the flow of the pixels outside ``exclude`` (the declared
    zones and the particles), and the share of its inliers (None when no transform could be fitted)."""
    lay = _layered_camera(flow, exclude, cv2) if LAYERED else None
    if lay is not None:                                  # a depth-layered camera (Z17): every band moves by its own share of one camera path
        return lay
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
    if unchanged is not None and (M is None or float(np.mean(inl)) * 100 < CAMERA_INLIERS_MIN):
        # tester Z4: flakes smear the flow around them and no transform fits, but where the pixels did not change the camera is still
        quiet = float(unchanged[ys[use], xs[use]].mean()) * 100
        if quiet >= STILL_PRIOR_MIN:
            return flow, quiet
    if M is None:
        return flow, None
    cam = np.stack([M[0, 0] * gx + M[0, 1] * gy + M[0, 2] - gx, M[1, 0] * gx + M[1, 1] * gy + M[1, 2] - gy], axis=-1)
    return flow - cam, float(np.mean(inl)) * 100


def _band_stats(frames: list[np.ndarray], cv2) -> tuple[float, float]:
    """(mean size in px of one flake, speed in px/s) of one band of a particle layer, from its matte frames at ``ANALYSIS_FPS``: the size is the mean
    connected-component area; the speed is the phase-correlation shift of the whole band between neighbouring frames (the band falls together)."""
    on = [(f > MATTE_ON).astype(np.uint8) for f in frames]
    areas = []
    for m in on[:: max(1, len(on) // 8)]:
        st = cv2.connectedComponentsWithStats(m, connectivity=8)[2][1:, 4]
        if len(st):
            areas.append(float(st.mean()))
    win = cv2.createHanningWindow((on[0].shape[1], on[0].shape[0]), cv2.CV_32F)
    shifts = []
    for a, b in zip(on, on[1:]):
        (dx, dy), _ = cv2.phaseCorrelate(a.astype(np.float32), b.astype(np.float32), win)
        shifts.append(float(np.hypot(dx, dy)))
    return (float(np.mean(areas)) if areas else 0.0), (float(np.median(shifts)) * ANALYSIS_FPS if shifts else 0.0)


def _near_far_check(path: Path, side: dict, cv2) -> tuple[str, float | None, str]:
    """OR-V19c: near flakes are larger and faster than far ones. Only when the sidecar names both bands (``particles.near`` and ``particles.far``,
    matte videos): the size ratio and the speed ratio near/far must both reach ``near_far_ratio_min`` (BP-215). One band alone is not measured."""
    parts = side.get("particles")
    if not isinstance(parts, dict) or not parts.get("near") or not parts.get("far"):
        return PASS, None, "near/far ratio not measured (the sidecar names no near band)"
    ns, nv = _band_stats(decode_grey(path.parent / parts["near"]), cv2)
    fs, fv = _band_stats(decode_grey(path.parent / parts["far"]), cv2)
    if fs <= 0 or fv <= 0:
        return FAIL, None, "the far band shows no flake or no motion: nothing to compare the near band with"
    rs, rv = ns / fs, nv / fv
    if rs < NEAR_FAR_MIN or rv < NEAR_FAR_MIN:
        return FAIL, round(min(rs, rv), 2), (f"near flakes are {rs:.2f}x the size and {rv:.2f}x the speed of the far ones (both at least "
                                             f"{NEAR_FAR_MIN:g}x): the snow has no depth (OR-V19c, BP-215)")
    return PASS, round(min(rs, rv), 2), f"near flakes {rs:.2f}x the size and {rv:.2f}x the speed of the far ones (at least {NEAR_FAR_MIN:g}x)"


def _depth_check(path: Path, side: dict, series=None) -> tuple[str, float | None, str]:
    """Does the foreground hide the far particles, and is the declared layer the layer the clip shows? Returns (status, share %, text). Every way
    of declaring nothing true is a FAIL (lead's ruling 2026-11-20 on the tester's Z5-Z7): moving specks in the clip that no declared matte lists, a
    declared layer without its far band or its depth map, a depth map with no foreground at all, a matte with no particle."""
    parts, depth = side.get("particles"), side.get("depth")
    seen = float(np.median(series.undeclared)) if series is not None and series.undeclared else 0.0
    if not parts:
        if seen >= UNDECLARED_SPECK_MAX and series is not None and series.zones:    # no sidecar, no zones: the whole-frame rules judge it (a wind band shears into specks too)
            return FAIL, round(seen, 2), (f"the clip shows moving specks (snow, sparks) over {seen:.2f} % of the frame (at most {UNDECLARED_SPECK_MAX:g} %) "
                                          "and the sidecar declares no particle layer: that the foreground hides the far ones is not proven; declare the "
                                          "layer (matte, far band, depth map)")
        return PASS, None, "no particle layer declared and none seen"
    far = parts.get("far") if isinstance(parts, dict) else None
    if not far or not depth:
        return FAIL, None, "a particle layer is declared but its far band or the depth map is missing: nothing proves the foreground hides the far ones"
    from PIL import Image
    dm = np.asarray(Image.open(path.parent / depth).convert("L").resize(SIZE)).astype(np.float32)
    span = float(dm.max() - dm.min()) or 1.0
    fg = (dm - dm.min()) / span >= FG_DEPTH_MIN
    if span < 1.0 or 100.0 * float(fg.mean()) < FG_AREA_MIN:
        return FAIL, round(100.0 * float(fg.mean()), 2), (f"the depth map has a foreground of {100.0 * float(fg.mean()):.1f} % of the frame (at least "
                                                         f"{FG_AREA_MIN:g} %): a flat map hides nothing, so it proves nothing")
    on = [m > MATTE_ON for m in decode_grey(path.parent / far)]
    total = sum(int(m.sum()) for m in on)
    if total == 0:
        return FAIL, None, "the far-particle matte shows no particle at all: nothing proves the far band exists"
    over = 100.0 * sum(int((m & fg).sum()) for m in on) / total
    if over > FAR_OVER_FG_MAX:
        return FAIL, round(over, 2), (f"{over:.1f} % of the far particles are drawn over foreground pixels (at most {FAR_OVER_FG_MAX:g} %): "
                                      f"the foreground does not hide them (client item 8, BP-215)")
    if seen >= UNDECLARED_SPECK_MAX:
        return FAIL, round(seen, 2), (f"the clip shows moving specks over {seen:.2f} % of the frame that the declared matte does not list (at most "
                                      f"{UNDECLARED_SPECK_MAX:g} %): the matte is not the layer the clip shows (BP-215)")
    return PASS, round(over, 2), f"far particles over the foreground {over:.2f} % (at most {FAR_OVER_FG_MAX:g} %); specks outside the matte {seen:.2f} %"


def _motion_series(path, g, cv2):
    """The flow loop of ``living_motion`` and ``flame_never_frozen``: per pair of frames ``gap`` apart, the share (%) of each zone's pixels (outside
    the particle layer) that move faster than the zone's speed once the camera is taken out, and of the whole frame, counting a pixel only where the
    flow is a motion and not noise (``_explained``). Also the connected specks that move (flakes, sparks) and how much of the frame they cover outside
    the declared particle matte. Returns None when the clip is too short for a pair, else a namespace of zones, cover, frame_cover, inliers, gap,
    specks (share of the moving area, %), speck_area and undeclared (% of the frame)."""
    side = _sidecar(path)
    zones = _zone_masks(path, side)
    parts = side.get("particles") if isinstance(side.get("particles"), dict) else {}
    matte = [m > MATTE_ON for m in decode_grey(path.parent / parts["matte"])] if parts.get("matte") else None
    named = parts.get("matte") or parts.get("far")                    # what the sidecar says the particles are (the whole layer, else its far band)
    declared = matte if matte is not None else ([m > MATTE_ON for m in decode_grey(path.parent / named)] if named else None)
    gap = max(1, int(round(FLOW_GAP_S * ANALYSIS_FPS)))
    g = _normalised(g)
    flows = _flow_fields(g, gap, cv2)
    if not flows:
        return None
    zone_union = np.zeros((SIZE[1], SIZE[0]), bool)
    for _, _, m in zones:
        zone_union |= m
    dt = gap / ANALYSIS_FPS
    cover = {name: [] for name, _, _ in zones}
    frame_cover, inliers, specks, speck_area, undeclared = [], [], [], [], []
    k = np.ones((5, 5), np.uint8)
    for i, fl in enumerate(flows):
        parts_i = np.zeros_like(zone_union)
        if matte is not None:
            parts_i = cv2.dilate((matte[i] | matte[min(i + gap, len(matte) - 1)]).astype(np.uint8), k).astype(bool)
        resid, inl = _camera_residual(fl, zone_union | parts_i, cv2, np.abs(g[i + gap] - g[i]) < FLOW_CHANGE_MIN)
        if inl is not None:
            inliers.append(inl)
        speed = np.hypot(resid[..., 0], resid[..., 1]) / dt
        _, e1 = _compensated(g[i], g[i + gap], fl, cv2)
        _, e0 = _compensated(g[i], g[i + gap], fl - resid, cv2)             # what the camera alone explains (nothing, for a still camera)
        speed = np.where(np.abs(g[i + gap] - g[i]) >= FLOW_CHANGE_MIN, speed, 0.0)    # a pixel that did not change does not move (flow smear)
        for name, kind, m in zones:
            valid = m & ~parts_i
            if valid.sum() >= 50:
                cover[name].append(float((speed[valid] >= ZONE_SPEED[kind]).mean() * 100) if _explained(e0, e1, valid) else 0.0)
        keep = ~parts_i
        frame_cover.append(float((speed[keep] >= FRAME_MIN_PX_S).mean() * 100) if keep.any() and _explained(e0, e1, keep) else 0.0)
        mv = ((speed >= FRAME_MIN_PX_S) & keep).astype(np.uint8)                 # tester Z4/Z5: how much of what moves is a speck (a flake, a spark)
        if mv.any():
            lab, stats = cv2.connectedComponentsWithStats(mv, connectivity=8)[1:3]
            small = np.isin(lab, np.flatnonzero((stats[1:, 4] <= PARTICLE_MAX_PX) & (stats[1:, 2] <= PARTICLE_MAX_SIDE) & (stats[1:, 3] <= PARTICLE_MAX_SIDE)) + 1)
            specks.append(100.0 * float(small.sum()) / float(mv.sum()))
            speck_area.append(100.0 * float(small.sum()) / mv.size)
            dcl = cv2.dilate((declared[i] | declared[min(i + gap, len(declared) - 1)]).astype(np.uint8), k).astype(bool) if declared is not None else None
            outside = small & ~zone_union                  # sparks and shear inside a declared zone are the zone's own life
            undeclared.append(100.0 * float((outside & ~dcl).sum() if dcl is not None else outside.sum()) / mv.size)
        else:
            specks.append(0.0)
            speck_area.append(0.0)
            undeclared.append(0.0)
    return SimpleNamespace(zones=zones, cover=cover, frame_cover=frame_cover, inliers=inliers, gap=gap, specks=specks, speck_area=speck_area,
                           undeclared=undeclared)


def living_motion(path) -> dict:
    """OR-V19a/b/c (BP-215, a hypothesis until calibrated on the analyst's run2 clip): the clip is alive when the flow, with the camera and the declared
    particle layer taken out, explains the next frame inside every declared zone (fire, smoke, sky, wind) or, without zones, over the frame; snow alone,
    noise, a brightness pulse and a camera move do not count. NOT ENFORCED (accepted limit, lead 2026-11-20): a blizzard so dense that its flakes merge
    into blobs (about 5000 flakes of 3 px at 480x270) is not recognised as particles by the whole-frame rules; only a sidecar that declares the
    layer (matte, far band, depth map) makes the check hold."""
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
    zones, cover, frame_cover, inliers, gap, specks = series.zones, series.cover, series.frame_cover, series.inliers, series.gap, series.specks
    cam = float(np.median(inliers)) if inliers else 0.0
    declared = side.get("particles") if isinstance(side.get("particles"), dict) else None
    if declared and not zones:
        return {"status": FAIL, "value": round(float(np.median(frame_cover)), 2), "detail": "the sidecar declares a particle layer but no zone of fire, smoke "
                "or sky: nothing but the particles is proven to move, and snow alone is not a living picture (lead's ruling 2026-11-20, BP-215)"}
    if cam < CAMERA_INLIERS_MIN:
        if not zones and not any(frame_cover):
            return {"status": FAIL, "value": round(cam, 1), "detail": f"no motion that the flow explains and no camera that can be fitted ({cam:.0f} % "
                    "inliers): noise or a flicker is not a living picture (BP-215)"}
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
        speck = float(np.median(specks)) if specks else 0.0
        if med >= FRAME_COVER_MIN and speck >= PARTICLE_SHARE_MIN:
            return {"status": FAIL, "value": round(med, 2), "detail": f"{speck:.0f} % of what moves is connected specks of at most {PARTICLE_MAX_PX} px "
                    f"(at least {PARTICLE_SHARE_MIN:g} % fails): only a particle layer moves, and snow alone is not a living picture (BP-215)"}
        if med < FRAME_COVER_MIN:
            return {"status": FAIL, "value": round(med, 2), "detail": f"only {med:.1f} % of the frame moves over {FRAME_MIN_PX_S:g} px/s once the "
                    f"camera is taken out (at least {FRAME_COVER_MIN:g} %): a camera move or a few particles alone do not make it alive (BP-215)"}
        worst = med
        notes.append("no .zones.json, whole frame " + f"{med:.1f} %")
    status, share, text = _depth_check(path, side, series)
    if status == FAIL:
        return {"status": FAIL, "value": share, "detail": text}
    nf_status, nf_value, nf_text = _near_far_check(path, side, cv2)
    if nf_status == FAIL:
        return {"status": FAIL, "value": nf_value, "detail": nf_text}
    text = text + "; " + nf_text
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
    skipped with a reason (routed to LTX) is listed and passes. ``direction.LIVING_KINDS`` gives the kind ``body`` no effect since the lead's ruling of 2026-11-20 (LP-02 wins), so the repo's own gate refuses it too. A file that is not a shot direction is NOT_RUN."""
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


def still_shot_drift(path) -> dict:
    """OR-V24 (the owner's cards of 2026-11-14 12:37 UTC, R-13 and R-14 of the reconciliation journal: a 2.5D shot is at most 5 s, BP-109; the camera
    never stops, a slow drift stays, BP-181 stays in force) on the delivered clip. The clip's whole camera move (zoom, or pan as a share of the width, the
    first frame against the last, ``liveliness.motion_between``) is scaled to 5 s and must lie in the drift band ``still_drift_min_pct`` to
    ``still_drift_max_pct`` (BP-215, a hypothesis: the client's 1-3 %, not a quoted owner word). A clip whose ``.zones.json`` says ``"camera": "push"``
    (a deliberate push the plan declares) is held to BP-181's scale band (4-25 %) instead. A clip over 5 s is a FAIL. Needs OpenCV (else NOT_RUN); a
    camera that cannot be fitted is NOT_RUN."""
    path = Path(path)
    if _cv2() is None:
        return {"status": NOT_RUN, "value": None, "detail": "the camera fit needs OpenCV (opencv-python-headless): not measured"}
    g = decode_grey(path)
    if len(g) < 2:
        return {"status": NOT_RUN, "value": None, "detail": "too short to measure a camera"}
    dur = len(g) / ANALYSIS_FPS
    cap = float(SR.T("BP-109", "still_shot_max_s"))
    if dur > cap + 0.5 / ANALYSIS_FPS * 4:
        return {"status": FAIL, "value": round(dur, 2), "detail": f"a 2.5D shot of {dur:.1f} s is over the {cap:g} s cap (BP-109, the owner's card of 2026-11-14): split it or send it to the video route"}
    mv = LV.motion_between(g[0], g[-1])
    if mv is None:
        return {"status": NOT_RUN, "value": None, "detail": "the camera could not be fitted between the first and the last frame: not measured"}
    amount = max(abs(mv["zoom_pct"]), float(np.hypot(mv["pan_x_pct"], mv["pan_y_pct"]))) * cap / max(dur, 1e-6)
    push = str(_sidecar(path).get("camera", "")).lower() == "push"
    if push:
        lo, hi = (float(SR.T("BP-181", "still_move_min")) - 1) * 100, (float(SR.T("BP-181", "still_move_max")) - 1) * 100
        what = "a declared push (BP-181)"
    else:
        lo, hi = float(SR.T("BP-215", "still_drift_min_pct")), float(SR.T("BP-215", "still_drift_max_pct"))
        what = "a still shot's slow drift (client reading of the 2026-11-14 cards, not verified)"
    if amount < lo:
        return {"status": FAIL, "value": round(amount, 2), "detail": f"the camera moves {amount:.2f} % over {cap:g} s, under {lo:g} %: the camera stands still, and the owner's card says it never stops ({what})"}
    if amount > hi:
        return {"status": FAIL, "value": round(amount, 2), "detail": f"the camera moves {amount:.2f} % over {cap:g} s, over {hi:g} %: that is not {what}; declare a push in the plan or slow it down"}
    return {"status": PASS, "value": round(amount, 2), "detail": f"the camera moves {amount:.2f} % over {cap:g} s, inside {lo:g}-{hi:g} % ({what}); {dur:.1f} s long (cap {cap:g} s)"}


still_shot_drift.kinds = (".mp4", ".mov", ".webm", ".mkv")


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
    cover, inliers = series.cover, series.inliers
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


def alive_beyond_camera(path) -> dict:
    """OR-V19e (the owner: "just a zoom"): a camera move alone is not alive. Takes the camera out (the similarity warp of ``liveliness.local_change_per_s``,
    brightness fades and per-frame grain removed first) and measures what is left of the change per second on the delivered clip; under the BP-194
    ``local_floor_pct_s`` it is a FAIL, with the number printed next to the floor. This is the cheap whole-frame row; where and how the world moves is
    ``living_motion``'s. Without OpenCV the warp cannot be fitted: NOT_RUN."""
    if _cv2() is None:
        return {"status": NOT_RUN, "value": None, "detail": "the camera warp needs OpenCV (opencv-python-headless): not measured"}
    g = decode_grey(Path(path))
    if len(g) <= ANALYSIS_FPS:
        return {"status": NOT_RUN, "value": None, "detail": f"too short for frames one second apart ({len(g)} frames at {ANALYSIS_FPS} fps)"}
    lc = LV.local_change_per_s(g, ANALYSIS_FPS)
    v = lc["pct_per_s"]
    if v is None:
        return {"status": NOT_RUN, "value": None, "detail": "the camera could not be fitted between frames one second apart: not measured"}
    if v < LV.LOCAL_FLOOR:
        return {"status": FAIL, "value": v, "detail": f"with the camera taken out the frame still changes {v} %/s, under the floor {LV.LOCAL_FLOOR:g} "
                "(BP-194, BP-185): a camera move alone is not a living picture"}
    return {"status": PASS, "value": v, "detail": f"with the camera taken out the frame still changes {v} %/s (floor {LV.LOCAL_FLOOR:g}, BP-194)"}


alive_beyond_camera.kinds = (".mp4", ".mov", ".webm", ".mkv")


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
    """``python -m explainer_engine.qa.send_validators living_motion|gemini_task_report|faces_intact|living_inventory|change_per_second|flame_never_frozen|director_reasons|no_body_motion_in_25d|alive_beyond_camera|still_shot_drift <file>...``: one line per clip, exit 1 on any FAIL, 2 on an error."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.send_validators")
    ap.add_argument("validator", choices=("living_motion", "gemini_task_report", "faces_intact", "living_inventory", "change_per_second", "flame_never_frozen", "director_reasons", "no_body_motion_in_25d", "alive_beyond_camera", "still_shot_drift"))
    ap.add_argument("files", nargs="+")
    a = ap.parse_args(argv)
    worst = 0
    for f in a.files:
        try:
            r = {"living_motion": living_motion, "gemini_task_report": gemini_task_report, "faces_intact": faces_intact, "living_inventory": living_inventory,
                 "change_per_second": change_per_second, "flame_never_frozen": flame_never_frozen, "director_reasons": director_reasons,
                 "no_body_motion_in_25d": no_body_motion_in_25d,
                 "alive_beyond_camera": alive_beyond_camera, "still_shot_drift": still_shot_drift}[a.validator](f)
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
