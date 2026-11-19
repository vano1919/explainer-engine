"""Is a photo shot alive, and does its camera follow the words? (the owner, 2026-11-14; Fable's 2.5D audit of P1 round 2.)

The P1 round 2 clips passed every gate while 27 of their 38 seconds stood still: the gates checked only that the director's
words were carried out, so a cautious director ("still", "holds until the word") collected PASS rows. The owner's verdict
(2026-11-14, message cmsg_01Hnu5zB86sjUj5GtTgaUkPW2SvHqtHd2XF1GyLPoL9Gnw and the three before it): the director sees the
photo as an opportunity and moves it as much as it allows; the camera goes to the part of the picture the words are about,
on those words; zooms are snappier; the camera move is measured the way the LTX clips are measured.

This module measures the delivered frames, so no director note can talk a clip past it:

- ``change_per_s``: the 2026-11-12 reference method (128x72 grey, frames one second apart, mean absolute difference in % of
  the full range); the Gemini demo's photo shots measured 3.6-12.2 %/s, ours 1.3-3.8 (BP-194).
- ``frozen_windows``: one-second windows in which less than ``frozen_change_pct`` of the frame changes visibly (a pixel
  moves more than 12/255 between the window's ends, the audit's measure): a still camera is allowed, a still world is not.
- ``local_change_per_s``: the change left after the camera is taken out (each pair aligned by its own similarity
  transform): what is alive beyond the camera (BP-185 says a camera move alone does not count).
- ``camera_curve`` / ``moves``: the camera's zoom and pan over time from chained ORB similarity transforms (the LTX lane's
  zoom/shift estimate, made per frame step), and each move's amount, its 10-90 % duration and its peak speed (BP-197).
- ``word_focus``: did the target the words name grow on screen or come towards the centre within ``settle_s`` of the word
  (BP-195)?

Every number is read from ``standards/sourced_rules.json``; all of them are hypotheses (REVIEW, D-59) until two source
types or the owner's word back them. ``delivery_row`` makes a REVIEW stop the clip before the owner sees it until the
director has looked at the frames and written a round (Fable's audit point 5): REVIEW still never FAILs a render.
"""
from __future__ import annotations

import math

import numpy as np

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

REF_SIZE = (128, 72)                      # the 2026-11-12 reference measurement's size
FROZEN_SIZE = (480, 270)                  # the audit's size for the visible-change share
FROZEN_PIXEL = 12.0                       # a pixel "changes visibly" above this many grey levels (the audit's measure)
CHANGE_FLOOR = float(SR.T("BP-194", "change_floor_pct_s"))
CHANGE_REF = tuple(SR.T("BP-194", "reference_pct_s"))
FROZEN_WINDOW_S = float(SR.T("BP-194", "frozen_window_s"))
FROZEN_CHANGE = float(SR.T("BP-194", "frozen_change_pct"))
LOCAL_FLOOR = float(SR.T("BP-194", "local_floor_pct_s"))
LEAD_S = float(SR.T("BP-195", "lead_s"))
LAG_S = float(SR.T("BP-195", "lag_s"))
SETTLE_S = float(SR.T("BP-195", "settle_s"))
FOCUS_GROW = float(SR.T("BP-195", "area_grow_min"))
FOCUS_CENTRE = float(SR.T("BP-195", "centre_gain_min"))
SNAP_S = float(SR.T("BP-197", "snap_s_max"))
ZOOM_MIN = float(SR.T("BP-197", "zoom_min_pct"))
PAN_MIN = float(SR.T("BP-197", "pan_min_pct"))
MOVE_MIN_PCT = 1.0                        # a camera change under 1 % (zoom or pan) is no move (PERCEPTIBLE_SHIFT of motion_intent)


def _cv2():
    import cv2
    return cv2


def _grey(frame: np.ndarray, size) -> np.ndarray:
    cv2 = _cv2()
    g = frame.astype(np.float32).mean(axis=2) if frame.ndim == 3 else frame.astype(np.float32)
    return cv2.resize(g, size, interpolation=cv2.INTER_AREA)


# --- how much the frame changes ---------------------------------------------------------------------------------------------

def change_per_s(frames: list[np.ndarray], fps: float) -> dict:
    """The reference method: frames one second apart, sampled every half second, mean |difference| in % of 255."""
    step, half = max(1, int(round(fps))), max(1, int(round(fps / 2)))
    g = [_grey(f, REF_SIZE) for f in frames]
    d = [float(np.mean(np.abs(g[i + step] - g[i])) / 255 * 100) for i in range(0, len(g) - step, half)]
    return {"pct_per_s": round(float(np.mean(d)), 2) if d else None, "series": [round(x, 2) for x in d]}


def frozen_windows(frames: list[np.ndarray], fps: float) -> dict:
    """One-second windows (every half second) and the share of the frame that changes visibly between their ends."""
    step, half = max(1, int(round(fps * FROZEN_WINDOW_S))), max(1, int(round(fps / 2)))
    g = [_grey(f, FROZEN_SIZE) for f in frames]
    rows = []
    for i in range(0, len(g) - step, half):
        share = float((np.abs(g[i + step] - g[i]) > FROZEN_PIXEL).mean() * 100)
        rows.append({"from_s": round(i / fps, 2), "share_pct": round(share, 2)})
    frozen = [r for r in rows if r["share_pct"] < FROZEN_CHANGE]
    return {"windows": len(rows), "frozen": len(frozen), "frozen_from_s": [r["from_s"] for r in frozen],
            "min_share_pct": min((r["share_pct"] for r in rows), default=None)}


def _similarity(a: np.ndarray, b: np.ndarray):
    """ORB + RANSAC similarity b <- a at 480x270 (uint8 grey), or None."""
    cv2 = _cv2()
    orb = cv2.ORB_create(2000)
    ka, da = orb.detectAndCompute(a, None)
    kb, db = orb.detectAndCompute(b, None)
    if da is None or db is None:
        return None
    m = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db)
    if len(m) < 12:
        return None
    pa = np.float32([ka[x.queryIdx].pt for x in m])
    pb = np.float32([kb[x.trainIdx].pt for x in m])
    M, _ = cv2.estimateAffinePartial2D(pa, pb, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    return M


def motion_between(a: np.ndarray, b: np.ndarray) -> dict | None:
    """Zoom (%) and pan (% of the width) of frame ``b`` against frame ``a``, measured directly (not chained): a slow move
    lost step by step in ``camera_curve`` is whole here (camera_segments)."""
    size = (960, 540)
    M = _similarity(_grey(a, size).astype(np.uint8), _grey(b, size).astype(np.uint8))
    if M is None:
        return None
    w, h = size
    c = np.vstack([M, [0, 0, 1]]) @ np.array([w / 2, h / 2, 1.0])
    return {"zoom_pct": round((float(math.hypot(M[0, 0], M[0, 1])) - 1) * 100, 2),
            "pan_x_pct": round(float((c[0] - w / 2) / w * 100), 2), "pan_y_pct": round(float((c[1] - h / 2) / w * 100), 2)}


def local_change_per_s(frames: list[np.ndarray], fps: float) -> dict:
    """``change_per_s`` after the camera is taken out: frame i is warped onto frame i + 1 s by their similarity transform
    and the difference is measured inside the area both frames show. What remains is what moves in the world."""
    cv2 = _cv2()
    step, half = max(1, int(round(fps))), max(1, int(round(fps / 2)))
    g8 = [_grey(f, FROZEN_SIZE).astype(np.uint8) for f in frames]
    d = []
    for i in range(0, len(g8) - step, half):
        a, b = g8[i], g8[i + step]
        M = _similarity(a, b)
        if M is None:
            M = np.float32([[1, 0, 0], [0, 1, 0]])
        w = cv2.warpAffine(a.astype(np.float32), M, (a.shape[1], a.shape[0]), flags=cv2.INTER_LINEAR,
                           borderMode=cv2.BORDER_CONSTANT, borderValue=-1)
        keep = cv2.erode((w >= 0).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        if keep.mean() < 0.3:
            continue
        aw = cv2.resize(np.where(keep, w, 0), REF_SIZE, interpolation=cv2.INTER_AREA)
        bb = cv2.resize(np.where(keep, b.astype(np.float32), 0), REF_SIZE, interpolation=cv2.INTER_AREA)
        kk = cv2.resize(keep.astype(np.float32), REF_SIZE, interpolation=cv2.INTER_AREA) > 0.99
        d.append(float(np.mean(np.abs(aw - bb)[kk]) / 255 * 100))
    return {"pct_per_s": round(float(np.mean(d)), 2) if d else None, "series": [round(x, 2) for x in d]}


# --- what the camera did, over time -----------------------------------------------------------------------------------------

def camera_curve(frames: list[np.ndarray], fps: float, step: int = 2) -> list[dict]:
    """Cumulative zoom (%) and pan (% of the width, the picture's own motion) per sampled frame, from chained similarity
    transforms between neighbours ``step`` frames apart (frame 0 = 0 %). The LTX lane's zoom/shift estimate, per step."""
    g8 = [_grey(f, FROZEN_SIZE).astype(np.uint8) for f in frames[::step]]
    w, h = FROZEN_SIZE
    C = np.eye(3)
    out = [{"t": 0.0, "zoom_pct": 0.0, "pan_x_pct": 0.0, "pan_y_pct": 0.0}]
    for k in range(1, len(g8)):
        M = _similarity(g8[k - 1], g8[k])
        if M is not None:
            C = np.vstack([M, [0, 0, 1]]) @ C
        s = float(math.hypot(C[0, 0], C[0, 1]))
        c = C @ np.array([w / 2, h / 2, 1.0])
        out.append({"t": round(k * step / fps, 3), "zoom_pct": round((s - 1) * 100, 2),
                    "pan_x_pct": round(float((c[0] - w / 2) / w * 100), 2), "pan_y_pct": round(float((c[1] - h / 2) / w * 100), 2)})
    return out


def _runs(dv: np.ndarray, eps: float = 0.02):
    """Index runs [i, j] of steps that go one way; a step under ``eps`` continues a run, two such steps in a row end it."""
    sign = np.where(np.abs(dv) < eps, 0, np.sign(dv))
    out, i = [], 0
    while i < len(sign):
        if sign[i] == 0:
            i += 1
            continue
        j, quiet = i, 0
        while j + 1 < len(sign) and sign[j + 1] != -sign[i]:
            quiet = quiet + 1 if sign[j + 1] == 0 else 0
            if quiet >= 2:
                break
            j += 1
        while sign[j] == 0:
            j -= 1
        out.append((i, j))
        i = j + 1
    return out


def moves(curve: list[dict]) -> list[dict]:
    """Split the curve into moves (runs of one direction of zoom or pan) and measure each: amount (%), the 10-90 % duration
    (s) and the peak speed (%/s). Runs under ``MOVE_MIN_PCT`` are not moves."""
    out = []
    for key in ("zoom_pct", "pan_x_pct", "pan_y_pct"):
        v = np.array([c[key] for c in curve], np.float64)
        t = np.array([c["t"] for c in curve], np.float64)
        if len(v) < 3:
            continue
        for i, j in _runs(np.diff(v)):
            a, b = v[i], v[j + 1]
            amount = abs(b - a)
            if amount < MOVE_MIN_PCT:
                continue
            seg_v, seg_t = v[i:j + 2], t[i:j + 2]
            frac = np.abs(seg_v - a) / amount
            t10 = float(seg_t[np.argmax(frac >= 0.1)])
            t90 = float(seg_t[np.argmax(frac >= 0.9)])
            speed = np.abs(np.diff(seg_v)) / np.maximum(1e-6, np.diff(seg_t))
            out.append({"axis": key.replace("_pct", ""), "from_s": round(float(t[i]), 2), "to_s": round(float(t[j + 1]), 2),
                        "amount_pct": round(float(b - a), 2), "rise_s": round(t90 - t10, 2),
                        "peak_pct_per_s": round(float(speed.max()), 2)})
    return sorted(out, key=lambda m: m["from_s"])


def word_focus(boxes: list, word_frame: int, fps: float) -> dict:
    """``boxes[f]`` = the named target's box on screen (x0, y0, x1, y1 as shares of the frame) or None. Compared at
    ``LEAD_S`` before the word and ``SETTLE_S`` after it: how much the target grew and how much nearer the centre it came."""
    n = len(boxes)
    f0 = max(0, min(n - 1, word_frame - int(round(LEAD_S * fps))))
    f1 = max(0, min(n - 1, word_frame + int(round(SETTLE_S * fps))))
    a, b = boxes[f0], boxes[f1]
    if a is None or b is None:
        return {"word_frame": word_frame, "measured": False}

    def area(x):
        return max(1e-6, (x[2] - x[0]) * (x[3] - x[1]))

    def dist(x):
        return math.hypot((x[0] + x[2]) / 2 - 0.5, (x[1] + x[3]) / 2 - 0.5)
    return {"word_frame": word_frame, "measured": True, "from_frame": f0, "to_frame": f1,
            "area_grow": round(area(b) / area(a), 3), "centre_gain": round(dist(a) - dist(b), 3)}


# --- rows -------------------------------------------------------------------------------------------------------------------

def liveliness_rows(frames: list[np.ndarray], fps: float, intent: str | None = None) -> tuple[list[dict], dict]:
    """The three liveliness rows of one clip and what was measured (``reference`` printed beside every clip, audit point 6)."""
    ch, fz, lc = change_per_s(frames, fps), frozen_windows(frames, fps), local_change_per_s(frames, fps)
    ref = f"Gemini reference {CHANGE_REF[0]}-{CHANGE_REF[1]} %/s"
    rows = [
        G.row("alive_change", None if ch["pct_per_s"] is None else ch["pct_per_s"] >= CHANGE_FLOOR,
              f"the frame changes {ch['pct_per_s']} %/s ({ref}; floor {CHANGE_FLOOR}, BP-194)", ch["pct_per_s"], level=G.REVIEW),
        G.row("no_frozen_second", fz["frozen"] == 0,
              f"{fz['frozen']} of {fz['windows']} one-second windows change less than {FROZEN_CHANGE} % of the frame"
              + (f" (from {fz['frozen_from_s'][:6]} s)" if fz["frozen"] else "") + "; the camera may stand, the world may not "
              "(BP-194)", fz, level=G.REVIEW),
        G.row("alive_beyond_camera", None if lc["pct_per_s"] is None else lc["pct_per_s"] >= LOCAL_FLOOR,
              f"with the camera taken out the frame still changes {lc['pct_per_s']} %/s (floor {LOCAL_FLOOR}, BP-194, BP-185)",
              lc["pct_per_s"], level=G.REVIEW),
    ]
    return rows, {"change": ch, "frozen": fz, "local": lc, "reference_pct_s": list(CHANGE_REF), "intent": intent}


def camera_rows(curve: list[dict], word_moves: list[dict] | None = None, intent: str | None = None) -> tuple[list[dict], dict]:
    """The camera, measured: a shot that is not still by design moves at least the reference amount (zoom ``ZOOM_MIN`` or
    pan ``PAN_MIN``), and every move the words call (``word_moves`` = ``[{"word", "frame", "fps"}]``) starts near its word and
    rises in at most ``SNAP_S`` (BP-197)."""
    ms = moves(curve)
    rows = []
    zmax = max((abs(m["amount_pct"]) for m in ms if m["axis"] == "zoom"), default=0.0)
    pmax = max((abs(m["amount_pct"]) for m in ms if m["axis"] != "zoom"), default=0.0)
    if intent != "still_by_design":
        rows.append(G.row("camera_amount", zmax >= ZOOM_MIN or pmax >= PAN_MIN,
                          f"largest zoom {zmax:.1f} %, largest pan {pmax:.1f} % (reference: zoom {ZOOM_MIN} % or pan {PAN_MIN} %, "
                          "BP-197)", {"zoom_max_pct": zmax, "pan_max_pct": pmax}, level=G.REVIEW))
    for wm in word_moves or []:
        tw = wm["frame"] / wm["fps"]
        near = [m for m in ms if tw - LEAD_S - 0.05 <= m["from_s"] <= tw + LAG_S + 0.05]
        if not near:
            rows.append(G.row("move_on_word", False, f"no camera move starts within -{LEAD_S}/+{LAG_S} s of '{wm['word']}' "
                              f"at {tw:.2f} s (BP-195)", None, level=G.REVIEW))
            continue
        m = max(near, key=lambda x: abs(x["amount_pct"]))
        rows.append(G.row("move_on_word", m["rise_s"] <= SNAP_S,
                          f"'{wm['word']}' at {tw:.2f} s: {m['axis']} {m['amount_pct']:+.1f} % from {m['from_s']} s, 10-90 % in "
                          f"{m['rise_s']} s (snappy: at most {SNAP_S} s, BP-197), peak {m['peak_pct_per_s']} %/s", m,
                          level=G.REVIEW))
    return rows, {"moves": ms}


def word_focus_row(r: dict, word: str, target: str) -> dict:
    if not r.get("measured"):
        return G.row("focus_on_word", None, f"'{word}' -> {target}: the target is not on screen at both ends")
    ok = r["area_grow"] >= FOCUS_GROW or r["centre_gain"] >= FOCUS_CENTRE
    return G.row("focus_on_word", ok, f"'{word}' -> {target}: on screen x{r['area_grow']} larger, {r['centre_gain']:+.3f} nearer "
                 f"the centre within {SETTLE_S} s (needs x{FOCUS_GROW} or {FOCUS_CENTRE}, BP-195)", r, level=G.REVIEW)


def delivery_row(rows: list[dict], rounds: list[dict] | None) -> dict:
    """A clip with any REVIEW row goes to the owner only after the director has looked at its frames and written a round
    that answers every REVIEW gate (``rounds[-1]["answers"]`` names them, ``looked_at`` lists the frames seen)."""
    review = sorted({r["gate"] for r in rows if r["status"] == G.REVIEW})
    if not review:
        return G.row("ready_for_owner", True, "no REVIEW row")
    last = (rounds or [{}])[-1]
    answered = set(last.get("answers", {})) if isinstance(last.get("answers"), dict) else set(last.get("answers", []))
    missing = [g for g in review if g not in answered]
    ok = bool(last.get("looked_at")) and not missing
    return G.row("ready_for_owner", ok, "REVIEW rows " + ", ".join(review) + (" answered by the director's round" if ok else
                 ": the director has not looked at the frames and answered " + ", ".join(missing or review)),
                 {"review": review, "missing": missing})
