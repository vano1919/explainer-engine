"""Intent against measurement, and the three deterministic defect detectors (roadmap 2026-11-14 B.10, H.1; phase P1).

The Stage B prototype (2026-11-14) passed three visible defects through every gate: the fill band of S01_SH001 crane 0.95,
the ghosts of S02_SH008 orbit_small, the blurred photo of S08_SH002 rack_focus "near". This module measures them:

1. ``reveal``: the renderer knows which output pixel shows FILL (inpainted, never painted by the artist); the detector
   measures how much of the frame newly shows fill and how thick the thickest revealed band is.
2. ``double_edge``: a layer that moved by ``v`` against what lies behind it leaves a copy (a ghost, a doubled flame) when the
   frame just outside its edge repeats the layer's own content shifted by ``v``; scored against the same test at the
   perpendicular shift, so plain image smoothness cancels.
3. ``target_sharpness``: the Laplacian variance inside the focus target's mask on the last frame against the first.

Plus the intent check (``intended`` / ``minimal`` / ``still_by_design``) on the measured global motion (ORB + similarity,
the prototype's method). Every threshold here is an engineering default: a miss is REVIEW, never FAIL (D-59), until
``standards/sourced_rules.json`` has two source types for it. ``layers25d_telemetry`` reads a ``layers25d`` Scene (unchanged
renderer) so the detectors can be run on the old clips too.
"""
from __future__ import annotations

import math

import numpy as np

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

ANALYSIS = (960, 540)
REVEAL_SHARE_REVIEW = 0.02      # newly visible fill wider than REVEAL_THIN_PX: share of the frame (engineering default)
REVEAL_BAND_REVIEW = 30.0       # thickest revealed band, px at 1080p (engineering default)
# P1 calibration (old layers25d, 9 clips, judged by eye on the worst frame): visible smears S01 v1 4.0 % / 23 px, S05_SH020 v1
# 3.0 % / 41 px, the defects 6.9 % / 61 px and 8.1 % / 145 px; invisible outline slivers S02 v1 1.0 % / 22 px, S06 v1 0.1 % / 15 px
REVEAL_THIN_PX = 8.0            # a fill sliver thinner than this (px at 1080p) along an outline is not counted in the share
GHOST_REVIEW = 0.20             # double-edge score (engineering default)
GHOST_MIN_SHIFT = 2.0           # px at the analysis size: below it no copy can be told from the edge itself
GHOST_MIN_PIXELS = 40
SHARP_REVIEW = 0.5              # the target keeps at least this share of its first frame's sharpness (engineering default)
SHARP_PICTURE_REVIEW = 0.25      # picture -> last frame: resampling alone costs ~half (accepted v1 clips 0.44-0.5); a blur ~0.02
REST_BAND_REVIEW = REVEAL_THIN_PX  # fill seen on frame 0 wider than this (px at 1080p): the picture is altered at rest (S01 C3 pole)
INVENT_RATIO_REVIEW = 1.5          # edge density of the revealed fill over the real background round it (engineering default)
INVENT_MIN_PIXELS = 400            # at the analysis size: below it the revealed fill is too small to judge
STILL_SCALE, STILL_SHIFT = 0.005, 0.3       # below both the camera is dead (|scale - 1|, shift % of width, first to last)
# still_by_design (the owner, 2026-11-14 12:37 UTC: the camera never fully stops; a slow drift or breathing stays, only a
# deliberate move is wrong): a push or pull at BP-21's slowest deliberate rate or faster, or a pan over DRIFT_SHIFT_PCT_S
# Gates added after the eye review of C4A (2026-11-14): each defect it found had no gate that could see it.
SEAM_FAIL = 0.15                # rest_seam: plate pixels inside a layer's outline per outline pixel (C4A scallops 0.68-1.28,
                                # fixed renderer 0.00-0.04); frame 0 must be the picture (an invariant, so FAIL)
PEOPLE_CUT_FAIL = 0.01          # people_in_frame: worst share of a kept person outside the frame (the owner, 13:29 UTC)
FACE_NCC_FAIL = 0.88            # face_intact: a kept face's first-frame crop searched in a later frame (camera taken
                                # out); the C5 S06 cloud smear scored 0.80, intact faces 0.96-0.99 (engineering default)
BLOWN_REVIEW = 0.01             # blown_out: share of a frame newly burned to flat white by light effects; C5's additive
                                # shaft burned 10-13 % (S01, S05), C4A 3 %, untouched pictures 0.0-0.5 % (engineering
                                # default, D-59: REVIEW)
SEEN_REVIEW = 10.0              # effect_seen_3s: the 95th percentile change of an effect's own light (levels) within 3 s
                                # (engineering default, D-59 hypothesis: REVIEW)
SEGMENT_SHIFT = 1.0             # camera_segments: a truck/crane moves the picture at least this % of the width its way
SEGMENT_SHARE = 0.5             # ... a push/pull shows at least this share of the zoom the camera actually made
DRIFT_SHIFT_PCT_S = 0.25        # engineering default: a drift moves the picture at most this share of the width per second
PERCEPTIBLE_SCALE, PERCEPTIBLE_SHIFT = 0.03, 1.0   # an intended move is visible at this scale change or shift (%)


def _cv2():
    import cv2
    return cv2


def gray(frame: np.ndarray, size=ANALYSIS) -> np.ndarray:
    cv2 = _cv2()
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA).astype(np.float32).mean(axis=2)


# --- motion: what the camera really did -----------------------------------------------------------------------------------

def global_motion(a: np.ndarray, b: np.ndarray) -> dict | None:
    """Similarity transform between two frames (BGR or RGB uint8): zoom ``scale`` and shift (% of the width) of b against a."""
    cv2 = _cv2()
    a = cv2.resize(a, (480, 270), interpolation=cv2.INTER_AREA)
    b = cv2.resize(b, (480, 270), interpolation=cv2.INTER_AREA)
    orb = cv2.ORB_create(3000)
    ka, da = orb.detectAndCompute(cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), None)
    kb, db = orb.detectAndCompute(cv2.cvtColor(b, cv2.COLOR_RGB2GRAY), None)
    if da is None or db is None:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 12:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, inl = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if M is None:
        return None
    s = float(np.hypot(M[0, 0], M[0, 1]))
    return {"scale": round(s, 4), "shift_x_pct": round(float(M[0, 2] - (1 - s) * 240) / 480 * 100, 2),
            "shift_y_pct": round(float(M[1, 2] - (1 - s) * 135) / 480 * 100, 2), "inliers": int(inl.sum())}


def intent_rows(intent: str, expect: dict, gm: dict | None, moves_from: int | None = None,
                duration_s: float | None = None) -> list[dict]:
    """The three cases of B.10: intended (did the planned move happen, in its direction, visibly?), minimal (under its caps?),
    still_by_design (no deliberate move, but not a dead camera either). ``gm`` is the first-to-last global motion;
    ``duration_s`` turns the still case into rates (without it: a move below the perceptible one is a drift)."""
    if gm is None:
        return [G.row("intent_measured", None, "no global motion could be measured")]
    ds, sx, sy = gm["scale"] - 1.0, gm["shift_x_pct"], gm["shift_y_pct"]
    rows = []
    if intent == "still_by_design":
        if duration_s:
            rate, pan = abs(ds) / duration_s, max(abs(sx), abs(sy)) / duration_s
            lim_s, lim_t = float(SR.T("BP-21", "rate_min_per_s")), DRIFT_SHIFT_PCT_S
            ok = rate < lim_s and pan <= lim_t
            what = (f"scale {rate * 100:.2f} %/s, pan {pan:.2f} %/s (a drift stays under BP-21's {lim_s * 100:g} %/s and "
                    f"{lim_t} %/s)")
        else:
            ok = abs(ds) < PERCEPTIBLE_SCALE and abs(sx) < PERCEPTIBLE_SHIFT and abs(sy) < PERCEPTIBLE_SHIFT
            what = f"scale {gm['scale']}, shift {sx} / {sy} % (a drift stays below {PERCEPTIBLE_SCALE} and {PERCEPTIBLE_SHIFT} %)"
        rows.append(G.row("still_is_still", ok, "no deliberate move: " + what, gm, level=G.REVIEW))
        dead = abs(ds) <= STILL_SCALE and abs(sx) <= STILL_SHIFT and abs(sy) <= STILL_SHIFT
        rows.append(G.row("camera_breathes", not dead, f"scale {gm['scale']}, shift {sx} / {sy} %: "
                          + ("the camera stands dead (the owner: a slow drift or breathing stays)" if dead else "it drifts"),
                          gm, level=G.REVIEW))
    elif intent == "minimal":
        cap_s, cap_t = float(expect.get("max_scale_change", 0.03)), float(expect.get("max_shift_pct", 1.5))
        ok = abs(ds) <= cap_s and abs(sx) <= cap_t and abs(sy) <= cap_t
        rows.append(G.row("minimal_under_cap", ok, f"scale {gm['scale']}, shift {sx} / {sy} % (caps {cap_s}, {cap_t} %)", gm,
                          level=G.REVIEW))
    else:
        want = expect.get("move")
        if want in ("push", "pull"):
            sign = 1 if want == "push" else -1
            got = sign * ds
            need = float(expect.get("min_scale_change", PERCEPTIBLE_SCALE))
            rows.append(G.row("intended_move", got >= need, f"{want}: scale {gm['scale']} (needs a change of {need} the "
                              "planned way)", gm, level=G.REVIEW))
        elif want in ("truck", "pan", "crane", "tilt"):
            axis, d = ("x", expect.get("direction", "right")) if want in ("truck", "pan") else ("y", expect.get("direction", "up"))
            v = sx if axis == "x" else sy
            # a camera moving right (or up) makes the picture move left (or down) in the frame
            sign = {"right": -1, "left": 1, "up": 1, "down": -1}[d]
            need = float(expect.get("min_shift_pct", PERCEPTIBLE_SHIFT))
            rows.append(G.row("intended_move", sign * v >= need, f"{want} {d}: shift {v} % (needs {need} % that way)", gm,
                              level=G.REVIEW))
        else:
            rows.append(G.row("intended_move", None, f"no measurable expectation for {want!r}"))
    return rows


def target_towards_centre(first_xy, last_xy, size) -> dict:
    """Is the target nearer the frame centre on the last frame than on the first (the targeted push, H.1)?"""
    cx, cy = size[0] / 2, size[1] / 2
    d0 = math.hypot(first_xy[0] - cx, first_xy[1] - cy)
    d1 = math.hypot(last_xy[0] - cx, last_xy[1] - cy)
    return G.row("target_towards_centre", d1 < d0, f"target {d0:.0f} px from the centre at the start, {d1:.0f} px at the end",
                 {"start_px": round(d0, 1), "end_px": round(d1, 1)}, level=G.REVIEW)


# --- detector 1: revealed fill --------------------------------------------------------------------------------------------

def reveal(fill_maps: list[np.ndarray], out_height: int = 1080) -> dict:
    """Fill maps (0..1 per output pixel, any equal size, frame 0 first) -> the worst frame's newly visible fill share and the
    thickest revealed band (px at the output height); a band is measured by the distance transform of the revealed area."""
    cv2 = _cv2()
    base = fill_maps[0] > 0.5
    scale = out_height / fill_maps[0].shape[0]
    worst = {"share": 0.0, "band_px": 0.0, "frame": 0}
    for f, m in enumerate(fill_maps):
        new = (m > 0.5) & ~base
        share = float(new.mean())
        band = thick = 0.0
        if new.any():
            width = cv2.distanceTransform(new.astype(np.uint8), cv2.DIST_L2, 3) * 2 * scale
            band = float(width.max())
            # a pixel belongs to a wide part when a disc of REVEAL_THIN_PX round it fits: grow the wide cores back
            core = (width >= REVEAL_THIN_PX).astype(np.uint8)
            r = max(1, int(round(REVEAL_THIN_PX / 2 / scale)))
            wide = cv2.dilate(core, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) & new
            thick = float(wide.mean())
        if share > worst["share"] or band > worst["band_px"] or thick > worst.get("share_wide", 0.0):
            worst = {"share": max(share, worst["share"]), "band_px": max(band, worst["band_px"]),
                     "share_wide": max(thick, worst.get("share_wide", 0.0)),
                     "frame": f if band >= worst["band_px"] else worst["frame"]}
    worst["share"] = round(worst["share"], 5)
    worst["share_wide"] = round(worst.get("share_wide", 0.0), 5)
    worst["band_px"] = round(worst["band_px"], 1)
    return worst


def reveal_row(r: dict) -> dict:
    ok = r.get("share_wide", r["share"]) <= REVEAL_SHARE_REVIEW and r["band_px"] <= REVEAL_BAND_REVIEW
    return G.row("fill_reveal", ok, f"newly visible fill: worst {r['share'] * 100:.2f} % of the frame "
                 f"({r.get('share_wide', r['share']) * 100:.2f} % wider than {REVEAL_THIN_PX:.0f} px), thickest band "
                 f"{r['band_px']:.0f} px at frame {r['frame']} (engineering defaults {REVEAL_SHARE_REVIEW * 100:.1f} %, "
                 f"{REVEAL_BAND_REVIEW:.0f} px)", r, level=G.REVIEW)


def fill_at_rest(fill0: np.ndarray, out_height: int = 1080) -> dict:
    """Frame 0 must be the picture: plate fill visible before anything has moved means a cut-out lost part of what it
    covers (P1 round 2 S01 C3: the post cut on the first frame, Fable's audit 2026-11-14). The widest band of fill (px)."""
    cv2 = _cv2()
    m = (fill0 > 0.5).astype(np.uint8)
    scale = out_height / fill0.shape[0]
    band = float(cv2.distanceTransform(m, cv2.DIST_L2, 3).max() * 2 * scale) if m.any() else 0.0
    return {"share": round(float(m.mean()), 5), "band_px": round(band, 1)}


def fill_at_rest_row(r: dict) -> dict:
    return G.row("fill_at_rest", r["band_px"] <= REST_BAND_REVIEW, f"frame 0 shows plate fill {r['share'] * 100:.2f} % of the "
                 f"frame, widest band {r['band_px']:.0f} px (frame 0 must be the picture; engineering default "
                 f"{REST_BAND_REVIEW:.0f} px)", r, level=G.REVIEW)


def _edge_density(g: np.ndarray, m: np.ndarray) -> float:
    cv2 = _cv2()
    e = cv2.Canny(np.clip(g, 0, 255).astype(np.uint8), 40, 110) > 0
    return float(e[m].mean()) if m.any() else 0.0


def invented_detail(frame_gray: np.ndarray, new_fill: np.ndarray) -> dict | None:
    """Does the newly revealed fill carry more structure than the real background round it (the S01 C3 wire rings the
    inpainting model made up)? Edge density inside the revealed fill over the density in a ring of non-fill pixels."""
    cv2 = _cv2()
    m = new_fill > 0.5
    if m.sum() < INVENT_MIN_PIXELS:
        return None
    ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=12).astype(bool) & ~m
    inside, outside = _edge_density(frame_gray, m), _edge_density(frame_gray, ring)
    return {"inside": round(inside, 4), "around": round(outside, 4), "ratio": round(inside / max(outside, 0.005), 2),
            "pixels": int(m.sum())}


def invented_detail_row(r: dict | None) -> dict:
    if r is None:
        return G.row("fill_invents", None, "the revealed fill is too small to judge")
    return G.row("fill_invents", r["ratio"] <= INVENT_RATIO_REVIEW, f"revealed fill edge density {r['inside']} against "
                 f"{r['around']} round it (x{r['ratio']}; engineering default x{INVENT_RATIO_REVIEW}: more structure than the "
                 "real background means the plate made something up)", r, level=G.REVIEW)


# --- detector 2: double edge (ghost) ---------------------------------------------------------------------------------------

def _shift(a: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """``out(x) = a(x + (dx, dy))``."""
    cv2 = _cv2()
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(a.astype(np.float32), m, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float((a * a).sum()) * float((b * b).sum()))
    return float((a * b).sum() / den) if den > 1e-9 else 0.0


def ghost_score(frame_gray: np.ndarray, alpha: np.ndarray, v: tuple[float, float]) -> dict | None:
    """One layer on one frame: ``alpha`` its visible mask and ``v`` its shift against what lies behind it since frame 0
    (both at the analysis size). A ghost repeats the layer's content at ``-v`` outside its edge."""
    cv2 = _cv2()
    n = math.hypot(*v)
    if n < GHOST_MIN_SHIFT:
        return None
    A = (alpha > 0.5).astype(np.uint8)
    if A.sum() < GHOST_MIN_PIXELS:
        return None
    r = int(math.ceil(n)) + 2
    ring = cv2.dilate(A, np.ones((3, 3), np.uint8), iterations=r).astype(bool) & ~A.astype(bool)
    grad = np.hypot(cv2.Sobel(frame_gray, cv2.CV_32F, 1, 0), cv2.Sobel(frame_gray, cv2.CV_32F, 0, 1))
    perp = [(-v[1], v[0]), (v[1], -v[0])]

    def ncc_at(s):
        cand = ring & (_shift(A, s[0], s[1]) > 0.5)
        if cand.sum() < GHOST_MIN_PIXELS:
            return None
        best = -1.0
        for img in (frame_gray, grad):
            best = max(best, _ncc(img[cand], _shift(img, s[0], s[1])[cand]))
        return best, int(cand.sum())
    main = ncc_at(v)
    if main is None:
        return None
    base = [x[0] for x in (ncc_at(p) for p in perp) if x is not None]
    if not base:
        return None
    return {"score": round(main[0] - max(base), 3), "ncc": round(main[0], 3), "baseline": round(max(base), 3),
            "pixels": main[1], "shift_px": round(n, 1)}


def double_edge(frames_gray: list[np.ndarray], layer_rows: list[list[dict]], every: int = 4) -> dict:
    """The worst ghost score over the sampled frames and layers. ``layer_rows[f]`` = ``[{"id", "alpha", "v": (dx, dy)}]`` at
    the analysis size."""
    worst = {"score": 0.0, "frame": None, "layer": None}
    for f in range(0, len(frames_gray), every):
        for lay in layer_rows[f]:
            g = ghost_score(frames_gray[f], lay["alpha"], lay["v"])
            if g and g["score"] > worst["score"]:
                worst = {"score": g["score"], "frame": f, "layer": lay["id"], **g}
    return worst


def double_edge_row(r: dict) -> dict:
    return G.row("double_edge", r["score"] <= GHOST_REVIEW,
                 f"worst ghost score {r['score']:.2f}" + (f" ({r['layer']} at frame {r['frame']}, shift {r.get('shift_px')} px)"
                                                         if r.get("layer") is not None else "")
                 + f" (engineering default {GHOST_REVIEW})", r, level=G.REVIEW)


# --- detector 3: target sharpness -----------------------------------------------------------------------------------------

def sharpness(frame: np.ndarray, mask: np.ndarray) -> float:
    cv2 = _cv2()
    g = frame.astype(np.float32).mean(axis=2) if frame.ndim == 3 else frame.astype(np.float32)
    m = cv2.resize(mask.astype(np.float32), (g.shape[1], g.shape[0]), interpolation=cv2.INTER_LINEAR) > 0.5
    for it in (3, 1, 0):                          # thin targets (a wire) survive a lighter erosion
        e = cv2.erode(m.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=it).astype(bool) if it else m
        if e.sum() >= 50:
            return float(cv2.Laplacian(g, cv2.CV_32F)[e].var())
    return float("nan")


def _ratio(a: float, b: float):
    return round(b / a, 3) if a and a == a and b == b else None


def target_sharpness(first: np.ndarray, last: np.ndarray, mask_first: np.ndarray, mask_last: np.ndarray,
                     picture: np.ndarray | None = None, mask_picture: np.ndarray | None = None) -> dict:
    """Laplacian variance of the target first -> last. With ``picture`` (the source resized to the output) also picture ->
    last: a clip blurred from its first frame on (Stage B v1 S08_SH002, rack 'near') keeps first == last and is caught only
    against the picture."""
    s0, s1 = sharpness(first, mask_first), sharpness(last, mask_last)
    r = {"start": round(s0, 1), "end": round(s1, 1), "ratio": _ratio(s0, s1)}
    if picture is not None:
        sp = sharpness(picture, mask_first if mask_picture is None else mask_picture)
        r["picture"] = round(sp, 1)
        r["picture_to_end"] = _ratio(sp, s1)
    return r


def target_sharpness_row(r: dict, target: str) -> dict:
    checks = [(r.get("ratio"), SHARP_REVIEW), (r.get("picture_to_end"), SHARP_PICTURE_REVIEW)]
    checks = [(v, t) for v, t in checks if v is not None]
    ok = None if not checks else all(v >= t for v, t in checks)
    pic = f", picture {r['picture']} -> end" if "picture" in r else ""
    return G.row("target_sharpness", ok, f"{target}: Laplacian variance {r['start']} -> {r['end']}{pic} (keeps at least "
                 f"{SHARP_REVIEW:.0%} of the first frame and {SHARP_PICTURE_REVIEW:.0%} of the picture, engineering defaults)", r,
                 level=G.REVIEW)


# --- the old renderer: telemetry from a layers25d Scene (the renderer itself is not changed) --------------------------------

def layers25d_telemetry(sc, f: int, size=ANALYSIS) -> dict:
    """For a ``production.layers25d.Scene`` at frame ``f``: the fill map (output pixels whose top plane shows its Telea fill)
    and one row per plane k >= 1 with its visible mask and its shift against plane k - 1 since frame 0 (analysis size)."""
    cv2 = _cv2()
    ms = sc.matrices(f)
    W, H = sc.W, sc.H
    top = np.zeros((H, W), np.int16)
    alphas = []
    for k, m in enumerate(ms):
        a = cv2.warpAffine(sc.layers[k][..., 3], m, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                           borderMode=cv2.BORDER_CONSTANT).astype(np.float32) / 255.0
        alphas.append(a)
        top[a > 0.5] = k
    fill = np.zeros((H, W), np.float32)
    kernel = np.ones((5, 5), np.uint8)
    for k in range(len(ms) - 1):
        hole = cv2.dilate((sc.labels >= k + 1).astype(np.uint8) * 255, kernel, iterations=1)
        hm = cv2.warpAffine(hole, ms[k], (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP,
                            borderMode=cv2.BORDER_CONSTANT) > 127
        fill[(top == k) & hm] = 1.0
    if not hasattr(sc, "_tele0"):
        sc._tele0 = sc.matrices(0)
    rows = []
    sx, sy = size[0] / W, size[1] / H
    for k in range(1, len(ms)):
        a_src = sc.layers[k][..., 3] > 128
        ys, xs = np.nonzero(a_src)
        if not len(xs):
            continue
        p = np.array([xs.mean(), ys.mean(), 1.0])

        def out(mm):
            return cv2.invertAffineTransform(mm) @ p
        rel = (out(ms[k]) - out(ms[k - 1])) - (out(sc._tele0[k]) - out(sc._tele0[k - 1]))
        vis = alphas[k] * (top == k)
        rows.append({"id": f"plane{k}", "alpha": cv2.resize(vis, size, interpolation=cv2.INTER_AREA),
                     "v": (float(rel[0] * sx), float(rel[1] * sy))})
    return {"fill": cv2.resize(fill, (480, 270), interpolation=cv2.INTER_AREA), "layers": rows}


def directed_layer_rows(tele_rows: list[dict], out_size=(1920, 1080), size=ANALYSIS) -> list[list[dict]]:
    """``production.directed25d.render_clip`` telemetry -> per-frame layer rows at the analysis size (shift of each object
    against the background under its centroid, since frame 0)."""
    cv2 = _cv2()
    sx, sy = size[0] / out_size[0], size[1] / out_size[1]
    first = {lay["id"]: (lay["p_obj"], lay["p_bg"]) for lay in tele_rows[0]["layers"]}
    out = []
    for row in tele_rows:
        rows = []
        for lay in row["layers"]:
            po0, pb0 = first[lay["id"]]
            rel = (lay["p_obj"] - lay["p_bg"]) - (po0 - pb0)
            rows.append({"id": lay["id"], "alpha": cv2.resize(lay["alpha"], size, interpolation=cv2.INTER_LINEAR),
                         "v": (float(rel[0] * sx), float(rel[1] * sy))})
        out.append(rows)
    return out


class Watch:
    """Collects what the detectors need while a clip renders (memory stays small: the ghost test runs on the sampled frames
    as they come). ``add`` takes the frame, its fill map and its layer rows (analysis size, shift since frame 0)."""

    def __init__(self, every: int = 4):
        self.every = every
        self.fills: list[np.ndarray] = []
        self.ghost = {"score": 0.0, "frame": None, "layer": None}
        self.first = self.last = None
        self.n = 0
        self.invent = None

    def add(self, f: int, frame: np.ndarray, fill: np.ndarray, layer_rows: list[dict] | None) -> None:
        cv2 = _cv2()
        self.fills.append(cv2.resize(fill.astype(np.float32), (480, 270), interpolation=cv2.INTER_AREA).astype(np.float16))
        if self.first is None:
            self.first = frame.copy()
        self.last = frame
        self.n += 1
        if f % (2 * self.every) == 0 and f > 0:
            fill_a = cv2.resize(fill.astype(np.float32), ANALYSIS, interpolation=cv2.INTER_AREA)
            base = cv2.resize(self.fills[0].astype(np.float32), ANALYSIS, interpolation=cv2.INTER_AREA)
            r = invented_detail(gray(frame), (fill_a > 0.5) & ~(base > 0.5))
            if r and (self.invent is None or r["ratio"] > self.invent["ratio"]):
                self.invent = {**r, "frame": f}
        if layer_rows and f % self.every == 0:
            g = gray(frame)
            for lay in layer_rows:
                s = ghost_score(g, lay["alpha"], lay["v"])
                if s and s["score"] > self.ghost["score"]:
                    self.ghost = {"score": s["score"], "frame": f, "layer": lay["id"], **s}

    def summary(self, out_height: int = 1080) -> dict:
        rv = reveal([m.astype(np.float32) for m in self.fills], out_height)
        gm = global_motion(self.first, self.last) if self.first is not None else None
        rest = fill_at_rest(self.fills[0].astype(np.float32), out_height) if self.fills else None
        return {"reveal": rv, "double_edge": self.ghost, "global_motion_first_to_last": gm, "fill_at_rest": rest,
                "fill_invents": self.invent}


# --- the gates the C4A eye review asked for (2026-11-14) -------------------------------------------------------------------

def rest_seam_row(r: dict | None) -> dict:
    if not r or not r.get("outline"):
        return G.row("rest_seam", None, "no layered object: nothing to compare at rest")
    return G.row("rest_seam", r["per_outline_px"] <= SEAM_FAIL, f"frame 0 shows plate inside layer outlines: "
                 f"{r['per_outline_px']:.3f} px per outline px (frame 0 must be the picture; FAIL above {SEAM_FAIL})", r)


def people_in_frame_row(r: dict | None) -> dict:
    if not r or not r.get("kept"):
        return G.row("people_in_frame", None, "no live person to keep in the frame")
    return G.row("people_in_frame", r["share"] <= PEOPLE_CUT_FAIL, f"worst {r['share'] * 100:.1f} % of a person outside the "
                 f"frame ({r.get('what')}, frame {r.get('frame')}; FAIL above {PEOPLE_CUT_FAIL * 100:g} %)", r)


def aim_row(rows: list[dict] | None) -> dict:
    if not rows:
        return G.row("aim_on_target", None, "no camera move aimed at a named object")
    bad = [r for r in rows if not r["inside"]]
    return G.row("aim_on_target", not bad, "every aimed move points inside its object" if not bad else
                 "; ".join(f"{r['op']} at {r['mask']} aims at {r['point']}, outside its box {r['box']}" for r in bad), rows)


def effects_seen_row(rows: list[dict] | None) -> dict:
    if not rows:
        return G.row("effect_seen_3s", None, "no effect in the shot")
    weak = [r for r in rows if r["change_p95"] < SEEN_REVIEW]
    return G.row("effect_seen_3s", not weak, ("every effect changes visibly within 3 s" if not weak else
                 "unseen in 3 s: " + ", ".join(f"{r['op']} ({r['change_p95']:.1f} levels)" for r in weak))
                 + f" (REVIEW below {SEEN_REVIEW:g} levels)", rows, level=G.REVIEW)


def segment_rows(cameras: list[dict], curve: list[dict], fps: float, views: list[dict] | None = None,
                 frames: list | None = None) -> list[dict]:
    """Each planned camera move, in its own frames, against the measured picture motion (``liveliness.camera_curve``):
    a truck/crane moves the picture its way, a push/pull shows the zoom the camera really made (``views``, after the safe
    zone). A first-to-last check could not see a truck that came out as a zoom (S05_SH020 C4A)."""
    if not curve or not cameras:
        return [G.row("camera_segments", None, "no planned move or no measured motion")]

    def at(f):
        t = f / fps
        return min(curve, key=lambda c: abs(c["t"] - t))
    out, bad = [], []
    for seg in cameras:
        op = seg["op"]
        if op not in ("push", "pull", "truck", "crane"):
            continue
        direct = None
        if frames:                                      # measured between the segment's own two frames, not chained
            from explainer_engine.qa import liveliness as LV
            direct = LV.motion_between(frames[min(seg["from"], len(frames) - 1)], frames[min(seg["to"], len(frames) - 1)])
        if direct is not None:
            dz, dx, dy = direct["zoom_pct"], direct["pan_x_pct"], direct["pan_y_pct"]
        else:
            a, b = at(seg["from"]), at(min(seg["to"], int(round(curve[-1]["t"] * fps))))
            dz, dx, dy = b["zoom_pct"] - a["zoom_pct"], b["pan_x_pct"] - a["pan_x_pct"], b["pan_y_pct"] - a["pan_y_pct"]
        rec = {"op": op, "from": seg["from"], "to": seg["to"], "zoom_pct": round(dz, 2), "pan_x_pct": round(dx, 2),
               "pan_y_pct": round(dy, 2)}
        if op in ("truck", "crane"):
            sign = {"right": -1, "left": 1}.get(seg.get("direction"), -1) if op == "truck" else \
                {"up": 1, "down": -1}.get(seg.get("direction"), 1)
            v = dx if op == "truck" else dy
            rec["ok"] = sign * v >= SEGMENT_SHIFT
            rec["why"] = f"{op} {seg.get('direction')}: picture moved {v:+.2f} % (needs {SEGMENT_SHIFT} % its way)"
        else:
            made = None
            if views:
                s0, s1 = views[min(seg["from"], len(views) - 1)]["s"], views[min(seg["to"], len(views) - 1)]["s"]
                made = (s1 / s0 - 1) * 100
            sign = 1 if op == "push" else -1
            need = SEGMENT_SHARE * abs(made) if made is not None else PERCEPTIBLE_SCALE * 100 / 2
            rec["ok"] = sign * dz >= need - 1e-6
            rec["why"] = (f"{op}: picture zoomed {dz:+.2f} % (camera made {made:+.2f} %, needs {SEGMENT_SHARE:g} of it)"
                          if made is not None else f"{op}: picture zoomed {dz:+.2f} % (needs {need:.1f} %)")
        out.append(rec)
        if not rec["ok"]:
            bad.append(rec["why"])
    if not out:
        return [G.row("camera_segments", None, "no push, pull, truck or crane planned")]
    return [G.row("camera_segments", not bad, "every planned move happened its way" if not bad else "; ".join(bad), out)]


def blown_out_row(r: dict | None) -> dict:
    """Light effects must not burn the picture to flat white: the share of the frame newly blown (beyond the source's own)."""
    if not r or r.get("frame") is None and not r.get("worst"):
        return G.row("blown_out", None, "no frame measured")
    new = max(0.0, r["worst"] - r.get("source", 0.0))
    return G.row("blown_out", new <= BLOWN_REVIEW, f"{100 * new:.2f} % of the frame burned to flat white beyond the "
                 f"picture's own (frame {r.get('frame')}; REVIEW above {100 * BLOWN_REVIEW:.0f} %)", r, level=G.REVIEW)


def face_intact_row(r: dict | None) -> dict:
    if not r or not r.get("faces"):
        return G.row("face_intact", None, "no live face kept in the frame")
    return G.row("face_intact", r["ncc"] >= FACE_NCC_FAIL, f"worst face likeness to its first frame {r['ncc']:.2f} "
                 f"(frame {r.get('frame')}; FAIL below {FACE_NCC_FAIL}: a smeared or warped face)", r)
