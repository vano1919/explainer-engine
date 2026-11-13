"""The cuts of the assembled master, checked on its REAL frames by what each cut is meant to be (VL-11, docs/VIDEO_LANE.md).

One global threshold would fail every intended angle change or pass every broken continuation, so the incoming shot's
``edit_plan.continuity_mode`` picks the check:

* ``continuation``: the action runs on. The frames either side of the cut must be close (mean grey change at most
  ``CONT_DIFF_MAX``, or ``CONT_MOTION_RATIO`` times the change between the frames either side of it when the shot moves fast:
  the size of an in-shot move, not of a new picture), and the horizontal motion (dense optical flow over the last and first
  frames) must not reverse: a subject running right does not run left after the cut (FAIL).
* ``coverage``: a new angle is expected (a cut whose two sides are near-identical is a jump cut: FAIL, CT-07), but the place
  holds: the top third (sky, far set) and the palette stay inside BP-166 (REVIEW: a hypothesis threshold) and the brightness
  gap stays under ``LUMA_GAP_REVIEW``.
* ``insert`` / a scene change / a non-video neighbour: measured and listed, nothing enforced.

Every cut writes its numbers and the frame numbers they come from; ``boundary_sheet`` draws three frames each side of every
cut with the verdict, for Claude and the creator to look at (a metric is never the only look).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

W = 160
CONT_DIFF_MAX = 18.0         # engineering default (0..255 grey, 160 px wide): calibrated in tests/unit/test_videolane_media.py
CONT_MOTION_RATIO = 2.0      # engineering default: a fast move changes every frame a lot, so the cut may change up to twice the
                             # median change between the frames either side of it, never less than CONT_DIFF_MAX
SAME_DIFF_MIN = 2.5          # engineering default: two sides closer than this are the same picture (a jump cut on coverage)
SAME_MOTION_RATIO = 1.5      # engineering default: a coverage cut that changes no more than 1.5x the in-shot change is the
                             # same shot going on (a jump cut)
FLOW_MIN = 0.25              # engineering default: px/frame at 160 px wide below which there is no direction to keep
LUMA_GAP_REVIEW = 0.18
SIDE = 4                     # frames each side of a cut that the flow and the sheet read


def decode(path: Path, width: int = W, rgb: bool = False) -> np.ndarray:
    """The whole file at ``width`` (grey uint8 (n, h, w), or RGB (n, h, w, 3))."""
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                         "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w0, h0 = int(pr[0]), int(pr[1])
    h = max(2, int(round(width * h0 / w0 / 2)) * 2)
    fmt, ch = ("rgb24", 3) if rgb else ("gray", 1)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={width}:{h}", "-f", "rawvideo",
                          "-pix_fmt", fmt, "-"], capture_output=True, check=True).stdout
    n = len(raw) // (width * h * ch)
    a = np.frombuffer(raw[: n * width * h * ch], np.uint8)
    return a.reshape(n, h, width, ch) if rgb else a.reshape(n, h, width)


def mean_dx(frames: np.ndarray) -> float:
    """The median horizontal optical flow (px/frame) over consecutive frames (Farneback, OpenCV)."""
    import cv2
    if len(frames) < 2:
        return 0.0
    vals = []
    for a, b in zip(frames[:-1], frames[1:]):
        f = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag = np.hypot(f[..., 0], f[..., 1])
        moving = mag > max(0.2, np.percentile(mag, 60))
        vals.append(float(np.median(f[..., 0][moving])) if moving.any() else 0.0)
    return float(np.median(vals))


def check_cut(grey: np.ndarray, rgb: np.ndarray, at: int, mode: str | None) -> dict:
    """One cut at master frame ``at`` (the first frame of the incoming shot)."""
    from explainer_engine.training import video_qa as VQ
    a, b = grey[max(0, at - SIDE):at], grey[at:at + SIDE]
    inner = [float(np.abs(x[i + 1].astype(np.float32) - x[i].astype(np.float32)).mean()) for x in (a, b)
             for i in range(len(x) - 1)]
    m = {"at_frame": at, "mode": mode,
         "diff": round(float(np.abs(grey[at - 1].astype(np.float32) - grey[at].astype(np.float32)).mean()), 3),
         "in_shot_diff": round(float(np.median(inner)), 3) if inner else 0.0,
         "dx_out": round(mean_dx(a), 3), "dx_in": round(mean_dx(b), 3),
         "palette_dist": VQ._dist(VQ._palette(rgb[at - 1]), VQ._palette(rgb[at])),
         "top_palette_dist": VQ._dist(VQ._palette(rgb[at - 1], (0, 0, 1, 1 / 3)), VQ._palette(rgb[at], (0, 0, 1, 1 / 3))),
         "luma_gap": round(abs(float(rgb[at - 1].mean()) - float(rgb[at].mean())) / 255.0, 4)}
    status, why = G.PASS, []
    pal = float(SR.T("BP-166", "palette_dist_max"))
    if mode == "continuation":
        lim = round(max(CONT_DIFF_MAX, CONT_MOTION_RATIO * m["in_shot_diff"]), 3)
        if m["diff"] > lim:
            status, why = G.FAIL, why + [f"the picture jumps {m['diff']} across a continuation (max {lim}: the in-shot "
                                         f"change is {m['in_shot_diff']})"]
        if abs(m["dx_out"]) > FLOW_MIN and abs(m["dx_in"]) > FLOW_MIN and np.sign(m["dx_out"]) != np.sign(m["dx_in"]):
            status, why = G.FAIL, why + [f"the motion reverses across a continuation ({m['dx_out']} -> {m['dx_in']} px/frame)"]
    elif mode == "coverage":
        if m["diff"] < max(SAME_DIFF_MIN, SAME_MOTION_RATIO * m["in_shot_diff"]):
            status, why = G.FAIL, why + [f"both sides are the same picture (change {m['diff']}, in-shot "
                                         f"{m['in_shot_diff']}): a jump cut, not coverage"]
        elif m["top_palette_dist"] > pal or m["palette_dist"] > pal or m["luma_gap"] > LUMA_GAP_REVIEW:
            status, why = G.REVIEW, why + [f"the place or light moves (palette {m['palette_dist']}, top third "
                                           f"{m['top_palette_dist']}, max {pal}; brightness gap {m['luma_gap']})"]
    m["status"], m["why"] = status, why
    return m


def check_master(master: Path, records: list[dict], script: dict, fps: int) -> dict:
    """Every cut of the master between two shots, by the incoming shot's mode. ``records``: the shot records in order (their
    ``total_frames``)."""
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    grey = decode(master)
    rgb = decode(master, rgb=True)
    cuts, t = [], 0
    for k, r in enumerate(records):
        if k:
            shot = by.get(r["shot_id"], {})
            prev = by.get(records[k - 1]["shot_id"], {})
            same_scene = shot.get("segment_id") == prev.get("segment_id") and shot.get("location_id") == prev.get("location_id")
            mode = (shot.get("edit_plan") or {}).get("continuity_mode") if same_scene else "scene_change"
            if 0 < t < len(grey):
                c = check_cut(grey, rgb, t, mode)
                c.update(shot_out=records[k - 1]["shot_id"], shot_in=r["shot_id"], at_s=round(t / fps, 3))
                cuts.append(c)
        t += int(r["total_frames"])
    fail = [f"{c['shot_out']}->{c['shot_in']} @{c['at_s']}s: {'; '.join(c['why'])}" for c in cuts if c["status"] == G.FAIL]
    rev = [f"{c['shot_out']}->{c['shot_in']} @{c['at_s']}s: {'; '.join(c['why'])}" for c in cuts if c["status"] == G.REVIEW]
    rows = [G.row("cuts_continuation_and_coverage", not fail, f"{len(fail)} of {len(cuts)} cut(s) FAIL on the real frames",
                  fail[:20]),
            G.row("cuts_place_holds", not rev, f"{len(rev)} cut(s) where the place or light moves", rev[:20], level=G.REVIEW)]
    return {"cuts": cuts, "rows": rows}


def boundary_sheet(master: Path, cuts: list[dict], out: Path, side: int = 3, width: int = 240) -> Path:
    """Three frames before and after every cut, one row per cut, labelled with the verdict."""
    rgb = decode(master, width=width, rgb=True)
    h = rgb.shape[1]
    rows = max(1, len(cuts))
    sheet = Image.new("RGB", (2 * side * width + 8, rows * (h + 20)), (14, 14, 14))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cuts):
        y = i * (h + 20)
        for j, f in enumerate(range(c["at_frame"] - side, c["at_frame"] + side)):
            if 0 <= f < len(rgb):
                x = j * width + (8 if j >= side else 0)
                sheet.paste(Image.fromarray(rgb[f]), (x, y))
        col = {G.PASS: (120, 220, 120), G.REVIEW: (240, 200, 80), G.FAIL: (240, 80, 80)}[c["status"]]
        d.text((4, y + h + 3), f"{c.get('shot_out')} -> {c.get('shot_in')} @ {c.get('at_s')}s  {c['mode']}  {c['status']}  "
               f"diff {c['diff']} dx {c['dx_out']}->{c['dx_in']}", fill=col)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out
