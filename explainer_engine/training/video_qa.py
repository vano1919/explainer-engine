"""Video QA for generated shots (docs/LORA_TRAINING.md LT-50..LT-62, ვანო 2026-10-23 22:32: "write it in code; watch hands,
faces, the usual AI mistakes; measure every parameter, fix where it is weak; use the hours of cartoons as the norm").

Free, CPU: numpy + OpenCV (CLIP from ``embed.py`` only when asked). What the numbers can and cannot see:

- measured: global flicker (brightness pops), morphing (what optical flow cannot explain: things appear, melt or swap),
  line-art loss ("melting": edge density falling), sharpness and colour drift over time, the time a long clip starts to
  break, a tracked character losing its head or legs (edge density in the top / bottom part of its box against frame 0),
  the motion rhythm (holds, speed) against the creator's cartoon footage, and for IC shots whether the render follows
  its block layout (LT-59).
- weak: the head/legs presence of a tracked box (median flow; background lines dilute it), so LT-55 is REVIEW only.
- not reliably measured: finger counts and face anatomy on cartoons (face/hand detectors are trained on photos).
  ``review_sheet`` cuts head and hand crops every second so a person (or Claude) checks them; the sheet is part of LT-58.

    python -m explainer_engine.training video-qa <clip.mp4> [--layout layout.mp4] [--regions regions.json] [--ref rhythm.json]
           [--sheet out.jpg] [--out qa.json]
    python -m explainer_engine.training footage-rhythm <work dir> --out rhythm.json [--per-show 40]
    python -m explainer_engine.training shot-identity <a.mp4> [<b.mp4>] [--heroes heroes.json] [--out id.json]
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from .audit import RULES, finding

Q = RULES.get("video_qa", {})
SMALL = 320          # analysis width; cartoons keep their lines at this size


def read_video(path, *, width=SMALL, max_frames=None):
    """Frames as uint8 RGB (t, h, w, 3) at ``width`` (ffmpeg, no OpenCV video codecs needed) + fps."""
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    num, den = j["r_frame_rate"].split("/")
    fps = float(num) / float(den or 1)
    w = width
    h = int(round(j["height"] * w / j["width"] / 2)) * 2
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    if max_frames:
        cmd[5:5] = ["-frames:v", str(max_frames)]   # an output option: after -i
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3), fps


def _gray(f):
    import cv2
    return cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_RGB2GRAY)


def _edges(g):
    import cv2
    return cv2.Canny(g, 60, 140) > 0


def flow_series(frames):
    """Per transition: mean flow magnitude (px at SMALL width) and the warp residual (mean |frame t - frame t-1 warped
    by the flow|, 0..1): motion explains the change -> small residual; things appearing, melting or swapping -> large."""
    import cv2
    g = [_gray(f) for f in frames]
    h, w = g[0].shape
    xs, ys = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    speed, resid, flows = [], [], []
    for a, b in zip(g[:-1], g[1:]):
        fl = cv2.calcOpticalFlowFarneback(b, a, None, 0.5, 3, 15, 3, 5, 1.2, 0)   # b -> a: where each b pixel came from
        warped = cv2.remap(a, xs + fl[..., 0], ys + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        speed.append(float(np.hypot(fl[..., 0], fl[..., 1]).mean()))
        resid.append(float(np.abs(warped.astype(np.float32) - b.astype(np.float32)).mean() / 255.0))
        flows.append(fl)
    return np.array(speed), np.array(resid), flows


def per_frame(frames):
    """Brightness, saturation, edge density (line art) and sharpness (Laplacian variance) per frame."""
    import cv2
    out = {"luma": [], "sat": [], "edges": [], "sharp": []}
    for f in frames:
        g = _gray(f)
        hsv = cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_RGB2HSV)
        out["luma"].append(float(g.mean() / 255.0))
        out["sat"].append(float(hsv[..., 1].mean() / 255.0))
        out["edges"].append(float(_edges(g).mean()))
        out["sharp"].append(float(cv2.Laplacian(g, cv2.CV_32F).var()))
    return {k: np.array(v) for k, v in out.items()}


def rhythm(speed, fps):
    """Cartoon timing: hold share (transitions with almost no motion: holds, drawings on twos), speed p50/p90 in
    frame-widths per second (resolution-free)."""
    if len(speed) == 0:
        return {"hold_share": 0.0, "speed_p50": 0.0, "speed_p90": 0.0}
    v = speed * fps / SMALL
    return {"hold_share": round(float((speed < Q.get("hold_px", 0.15)).mean()), 3),
            "speed_p50": round(float(np.percentile(v, 50)), 4), "speed_p90": round(float(np.percentile(v, 90)), 4)}


def track_regions(regions, flows, shape, frames=None):
    """Move each first-frame box (normalised [x0, y0, x1, y1]) by the median flow inside it, frame by frame; with
    ``frames`` only over the box's ink outlines (the character), so a hatched or painted backdrop does not hold it back."""
    h, w = shape
    tracks = {}
    for r in regions:
        x0, y0, x1, y1 = r["box"][0] * w, r["box"][1] * h, r["box"][2] * w, r["box"][3] * h
        boxes = [(x0, y0, x1, y1)]
        for t, fl in enumerate(flows):
            a, b, c, d = (int(round(v)) for v in boxes[-1])
            a, b = max(0, a), max(0, b)
            c, d = min(w, max(a + 2, c)), min(h, max(b + 2, d))
            fx, fy = fl[b:d, a:c, 0], fl[b:d, a:c, 1]
            if frames is not None and fx.size:
                ink = _ink(_gray(frames[t + 1][b:d, a:c]))
                if ink.sum() >= 20:
                    fx, fy = fx[ink], fy[ink]
            # flow is t+1 -> t (backward), so the box moves by minus the median
            dx = -float(np.median(fx)) if fx.size else 0.0
            dy = -float(np.median(fy)) if fy.size else 0.0
            px0, py0, px1, py1 = boxes[-1]
            boxes.append((px0 + dx, py0 + dy, px1 + dx, py1 + dy))
        tracks[r["label"]] = boxes
    return tracks


def _ink(g):
    """Outline pixels: edges next to near-black ink (characters carry bold dark outlines; painted backdrops mostly do not)."""
    import cv2
    dark = cv2.dilate((g < Q.get("ink_max", 50)).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    return _edges(g) & dark


def part_presence(frames, boxes, *, top=0.3, bottom=0.35):
    """Outline density of the top (head) and bottom (legs/feet) part of a tracked box, relative to frame 0."""
    h, w = frames[0].shape[:2]
    head, legs = [], []
    for f, (x0, y0, x1, y1) in zip(frames, boxes):
        a, b, c, d = int(max(0, x0)), int(max(0, y0)), int(min(w, x1)), int(min(h, y1))
        if c - a < 4 or d - b < 6:
            head.append(0.0); legs.append(0.0); continue
        e = _ink(_gray(f[b:d, a:c]))
        hh = e.shape[0]
        head.append(float(e[: max(1, int(hh * top))].mean()))
        legs.append(float(e[int(hh * (1 - bottom)):].mean()))
    head, legs = np.array(head), np.array(legs)
    return head / max(head[0], 1e-6), legs / max(legs[0], 1e-6)


def windows(series, fps, sec=1.0):
    """Mean of a per-transition series per window of ``sec`` seconds."""
    n = max(1, int(round(fps * sec)))
    return [float(np.mean(series[i:i + n])) for i in range(0, len(series), n)]


def analyse(frames, fps, regions=None):
    speed, resid, flows = flow_series(frames)
    pf = per_frame(frames)
    m = {"frames": int(len(frames)), "seconds": round(len(frames) / fps, 2), "fps": round(fps, 3)}
    m["flicker_max"] = round(float(np.abs(np.diff(pf["luma"])).max()) if len(frames) > 1 else 0.0, 4)
    m["morph_p95"] = round(float(np.percentile(resid, 95)) if len(resid) else 0.0, 4)
    m["morph_by_second"] = [round(v, 4) for v in windows(resid, fps)]
    m["edges_end_vs_start"] = round(float(pf["edges"][-1] / max(pf["edges"][0], 1e-6)), 3)
    m["edges_min_vs_start"] = round(float(pf["edges"].min() / max(pf["edges"][0], 1e-6)), 3)
    m["sharp_end_vs_start"] = round(float(pf["sharp"][-1] / max(pf["sharp"][0], 1e-6)), 3)
    m["sharp_min_vs_start"] = round(float(pf["sharp"].min() / max(pf["sharp"][0], 1e-6)), 3)
    m["sat_end_minus_start"] = round(float(pf["sat"][-1] - pf["sat"][0]), 4)
    m["luma_end_minus_start"] = round(float(pf["luma"][-1] - pf["luma"][0]), 4)
    m["rhythm"] = rhythm(speed, fps)
    # the first second where morphing runs over the limit = where a long clip starts to break
    lim = Q.get("morph_second_max", 0.05)
    bad = [i for i, v in enumerate(m["morph_by_second"]) if v > lim]
    m["breaks_at_second"] = bad[0] if bad else None
    if regions:
        tr = track_regions(regions, flows, frames[0].shape[:2], frames)
        m["regions"] = {}
        for r in regions:
            head, legs = part_presence(frames, tr[r["label"]])
            m["regions"][r["label"]] = {"head_min": round(float(head.min()), 3), "legs_min": round(float(legs.min()), 3),
                                         "legs_end": round(float(legs[-1]), 3),
                                         "legs_lost_at_s": _first_below(legs, Q.get("part_keep_min", 0.45), fps),
                                         "head_lost_at_s": _first_below(head, Q.get("part_keep_min", 0.45), fps)}
        m["_tracks"] = tr
    return m


def _first_below(series, lim, fps, hold=6):
    """First time (s) the series stays under lim for ``hold`` frames in a row; None if never."""
    run = 0
    for i, v in enumerate(series):
        run = run + 1 if v < lim else 0
        if run >= hold:
            return round((i - hold + 1) / fps, 2)
    return None


def judge(m, ref=None):
    """Findings LT-50..LT-57 for one clip (ref = footage rhythm from ``footage_rhythm``)."""
    f = []
    if m["flicker_max"] > Q.get("flicker_max", 0.06):
        f.append(finding("LT-51", "FAIL", f"brightness pop {m['flicker_max']} > {Q.get('flicker_max', 0.06)} between frames"))
    if m["breaks_at_second"] is not None:
        f.append(finding("LT-52", "FAIL", f"morphing over {Q.get('morph_second_max', 0.05)} from second "
                                          f"{m['breaks_at_second']} (things appear, melt or swap)"))
    if m["edges_min_vs_start"] < Q.get("edges_keep_min", 0.7):
        f.append(finding("LT-53", "FAIL", f"line art falls to {m['edges_min_vs_start']} x frame 0 (melting / blur)"))
    if m.get("sharp_min_vs_start", 1) < Q.get("sharp_keep_min", 0.65):
        f.append(finding("LT-53", "REVIEW", f"detail falls to {m['sharp_min_vs_start']} x frame 0 (soft, ghosting or "
                                            f"translucent people: the 20 s max-length test faded two heroes out)"))
    if m["sat_end_minus_start"] < -Q.get("sat_loss_fail", 0.2):
        f.append(finding("LT-54", "FAIL", f"colour lost ({m['sat_end_minus_start']:+} saturation): an IC render copying its grey "
                                          f"layout (conditioning strength under 1.0, test 2026-10-24)"))
    elif abs(m["sat_end_minus_start"]) > Q.get("sat_drift_max", 0.08) or abs(m["luma_end_minus_start"]) > Q.get("luma_drift_max", 0.08):
        f.append(finding("LT-54", "REVIEW", f"colour drift: saturation {m['sat_end_minus_start']:+}, brightness "
                                            f"{m['luma_end_minus_start']:+} (fine when the scene asks for it)"))
    for lab, r in (m.get("regions") or {}).items():
        if r["legs_lost_at_s"] is not None:
            f.append(finding("LT-55", "REVIEW", f"{lab}: legs/feet fade out at {r['legs_lost_at_s']} s "
                                              f"(edge density {r['legs_min']} x frame 0)"))
        if r["head_lost_at_s"] is not None:
            f.append(finding("LT-55", "REVIEW", f"{lab}: head/face fades out at {r['head_lost_at_s']} s"))
    if ref:
        rh = m["rhythm"]
        lo, hi = ref["speed_p90"]["p10"], ref["speed_p90"]["p90"]
        if not lo <= rh["speed_p90"] <= hi:
            f.append(finding("LT-56", "REVIEW", f"fast-motion speed p90 {rh['speed_p90']} outside the cartoons' "
                                                f"{lo}..{hi} (frame widths/s)"))
        if rh["hold_share"] < ref["hold_share"]["p10"]:
            f.append(finding("LT-57", "REVIEW", f"holds {rh['hold_share']} < cartoons' p10 {ref['hold_share']['p10']}: "
                                                f"floaty, always-moving AI motion"))
    for c in (m.get("layout") or {}).get("cells", []):
        f.append(finding("LT-59", "REVIEW", f"cell {c['cell']} (column, row of a 6x4 grid): the render {c['render']} "
                                            f"lines the layout does not, from {c['at_s']} s (invented or lost content)"))
    return f or [finding("LT-50", "PASS", f"{m['seconds']} s: morph p95 {m['morph_p95']}, lines x{m['edges_min_vs_start']}, "
                                          f"flicker {m['flicker_max']}")]


def footage_rhythm(work_dir, *, per_show=40, max_seconds=6.0):
    """The creator's cartoons as the norm: rhythm of up to ``per_show`` moving shots per show (shots.json from
    footage-measure), as p10/p50/p90 over shots."""
    shots = json.loads((Path(work_dir) / "shots.json").read_text(encoding="utf-8"))
    by_show = {}
    for s in shots:
        if s.get("dup_of") or s.get("dur", 0) < 1.5 or s.get("motion") is None:
            continue
        by_show.setdefault(s["show"], []).append(s)
    rows = []
    for show, ss in sorted(by_show.items()):
        step = max(1, len(ss) // per_show)
        for s in ss[::step][:per_show]:
            frames, fps = _read_segment(s["file"], s["start"] + 0.1, min(s["end"], s["start"] + max_seconds))
            if len(frames) < 6:
                continue
            speed, _, _ = flow_series(frames)
            r = rhythm(speed, fps)
            r["show"] = show
            rows.append(r)
    out = {"shots": len(rows), "shows": sorted({r["show"] for r in rows})}
    for k in ("hold_share", "speed_p50", "speed_p90"):
        v = np.array([r[k] for r in rows]) if rows else np.zeros(1)
        out[k] = {p: round(float(np.percentile(v, q)), 4) for p, q in (("p10", 10), ("p50", 50), ("p90", 90))}
    return out


def _read_segment(path, t0, t1, width=SMALL):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    num, den = j["r_frame_rate"].split("/")
    fps = float(num) / float(den or 1)
    h = int(round(j["height"] * width / j["width"] / 2)) * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(path), "-vf",
                          f"scale={width}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, width, 3), fps


def review_sheet(path, out, regions=None, *, every_s=1.0, width=960):
    """Contact sheet for the eye check (LT-58): one row per second, the full frame plus, per region, a head crop and the
    middle band (hands). Hands and faces are judged here by a person or Claude, not by a number."""
    import cv2
    frames, fps = read_video(path, width=width)
    small_h = frames.shape[1]
    idx = list(range(0, len(frames), max(1, int(round(fps * every_s)))))
    if idx[-1] != len(frames) - 1:
        idx.append(len(frames) - 1)
    tracks = None
    if regions:
        sm, _ = read_video(path)
        _, _, flows = flow_series(sm)
        tr = track_regions(regions, flows, sm.shape[1:3], sm)
        k = width / SMALL
        tracks = {lab: [tuple(v * k for v in b) for b in bs] for lab, bs in tr.items()}
    th = 180
    rows = []
    for i in idx:
        f = frames[i]
        tiles = [cv2.resize(f, (int(f.shape[1] * th / small_h), th))]
        for lab, bs in (tracks or {}).items():
            x0, y0, x1, y1 = bs[i]
            bh = y1 - y0
            for a, b in ((y0, y0 + 0.32 * bh), (y0 + 0.3 * bh, y0 + 0.7 * bh)):
                crop = f[int(max(0, a)):int(min(small_h, b)), int(max(0, x0)):int(min(f.shape[1], x1))]
                tiles.append(cv2.resize(crop, (th, th)) if crop.size else np.zeros((th, th, 3), np.uint8))
        rows.append(np.concatenate(tiles, axis=1))
    sheet = np.concatenate(rows, axis=0)
    cv2.imwrite(str(out), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(out)


def qa_file(path, regions=None, ref=None, layout=None):
    frames, fps = read_video(path)
    m = analyse(frames, fps, regions)
    m.pop("_tracks", None)
    if layout:
        m["layout"] = layout_fidelity(frames, read_video(layout)[0], fps=fps)
    return m, judge(m, ref)


def layout_fidelity(out_frames, layout_frames, *, grid=(6, 4), fps=24.0):
    """IC / Layout-To-Render shots: does the render follow its block layout? Per grid cell, line density over time
    relative to frame 0 in the render and in the layout; a cell where one gains or loses lines (x2 or more) while the
    other does not, for half a second, is invented or lost content (a person appearing in a gap, legs vanishing).
    B_ic 2026-10-23: the layout's warp left a dark ghost where the scientist stood and the render drew a second caveman."""
    import cv2
    n = min(len(out_frames), len(layout_frames))
    gx, gy = grid
    h, w = out_frames[0].shape[:2]
    lay = [cv2.resize(np.ascontiguousarray(f), (w, h)) for f in layout_frames[:n]]

    def dens(frames):
        d = np.zeros((n, gy, gx))
        for t in range(n):
            e = _edges(_gray(frames[t]))
            for j in range(gy):
                for i in range(gx):
                    d[t, j, i] = e[j * h // gy:(j + 1) * h // gy, i * w // gx:(i + 1) * w // gx].mean()
        return d
    a, b = dens(out_frames[:n]), dens(lay)
    ra = np.log2((a + 0.01) / (a[0] + 0.01))
    rb = np.log2((b + 0.01) / (b[0] + 0.01))
    gap = np.abs(ra - rb)
    hold = max(1, int(round(fps * 0.5)))
    cells = []
    for j in range(gy):
        for i in range(gx):
            t0 = _first_below(-gap[:, j, i], -Q.get("layout_gap_max", 1.0), fps, hold=hold)
            if t0 is not None:
                cells.append({"cell": [i, j], "at_s": t0, "gap_max": round(float(gap[:, j, i].max()), 2),
                              "render": "gains" if ra[:, j, i].max() > -ra[:, j, i].min() else "loses"})
    return {"cells": cells, "gap_p95": round(float(np.percentile(gap, 95)), 3)}


# ---- continuity between shots (LT-60..LT-62, ვანო 2026-10-24 07:17: "does anything check consistency between the frames
# of the video, or is the scene LoRA drawing the stills right enough?") -----------------------------------------------
# A scene is cut from several <= 10 s shots (the max-length test), so the join between two shots is where the look can
# jump: the set's palette, the line weight and a hero's colours. Numbers only: whether it is the same person is for the
# eye (LT-58 sheet) or CLIP (LT-43 identity) on the pod.

def _palette(f, box=None):
    """Colour signature of the painted pixels (ink dropped): hue x saturation bins (grey collapsed to one bin, hue is
    noise without saturation) plus a brightness histogram; two halves of 0.5 each, so the distance is in 0..1."""
    import cv2
    if box is not None:
        h, w = f.shape[:2]
        x0, y0, x1, y1 = box
        f = f[int(max(0, y0 * h)):int(min(h, y1 * h)), int(max(0, x0 * w)):int(min(w, x1 * w))]
    if f.size == 0:
        return np.zeros(45)
    hsv = cv2.cvtColor(np.ascontiguousarray(f), cv2.COLOR_RGB2HSV)
    g = _gray(f)
    keep = g >= Q.get("ink_max", 50)
    hue, sat = hsv[..., 0][keep].astype(int), hsv[..., 1][keep].astype(int)
    hs = np.zeros(1 + 12 * 3)
    grey = sat < 32
    hs[0] = grey.sum()
    idx = 1 + (hue[~grey] * 12 // 180) * 3 + np.minimum((sat[~grey] - 32) * 3 // 224, 2)
    np.add.at(hs, idx, 1)
    lum = np.histogram(g[keep], bins=8, range=(0, 256))[0].astype(float)
    hs = hs / max(hs.sum(), 1) * 0.5
    lum = lum / max(lum.sum(), 1) * 0.5
    return np.concatenate([hs, lum])


def _dist(a, b):
    """1 - Bhattacharyya coefficient of two normalised histograms: 0 identical, 1 disjoint."""
    return round(float(1.0 - np.sqrt(a * b).sum()), 4)


def shot_identity(frame_a, frame_b, heroes=None):
    """A's last frame against B's first frame (or one shot's first against its last): set palette distance, brightness
    and saturation gaps, line-weight and detail ratios, and for each hero {label, a: box, b: box} the palette distance
    of its box (what a hero wears and what colour its skin and hair are)."""
    import cv2
    pa = per_frame([frame_a, frame_b])
    m = {"palette_dist": _dist(_palette(frame_a), _palette(frame_b)),
         "luma_gap": round(float(pa["luma"][1] - pa["luma"][0]), 4),
         "sat_gap": round(float(pa["sat"][1] - pa["sat"][0]), 4),
         "edges_ratio": round(float(pa["edges"][1] / max(pa["edges"][0], 1e-6)), 3),
         "sharp_ratio": round(float(pa["sharp"][1] / max(pa["sharp"][0], 1e-6)), 3)}
    ink = [float((_gray(f) < Q.get("ink_max", 50)).mean()) for f in (frame_a, frame_b)]
    m["ink_ratio"] = round(ink[1] / max(ink[0], 1e-6), 3)        # share of ink pixels: the line weight (edges miss it)
    ga, gb = (cv2.GaussianBlur(_gray(f), (0, 0), 4).astype(np.float32) for f in (frame_a, frame_b))
    m["backdrop_corr"] = round(float(np.corrcoef(ga.ravel(), gb.ravel())[0, 1]), 3)   # same camera and set: near 1 (information only)
    m["heroes"] = {h["label"]: _dist(_palette(frame_a, h["a"]), _palette(frame_b, h.get("b", h["a"]))) for h in heroes or []}
    return m


def judge_identity(m, what="shot A -> shot B"):
    f = []
    if m["palette_dist"] > Q.get("palette_dist_max", 0.08):
        f.append(finding("LT-60", "REVIEW", f"{what}: the set's palette moves {m['palette_dist']} (> "
                                            f"{Q.get('palette_dist_max', 0.08)}): different light, colours or style"))
    lo, hi = Q.get("line_ratio", [0.7, 1.4])
    if not lo <= m["ink_ratio"] <= hi:
        f.append(finding("LT-61", "REVIEW", f"{what}: ink x{m['ink_ratio']} (outside {lo}..{hi}): a thicker or thinner "
                                            f"drawing, or lost outlines"))
    for lab, d in m["heroes"].items():
        if d > Q.get("hero_palette_max", 0.15):
            f.append(finding("LT-62", "REVIEW", f"{what}: {lab}'s colours move {d} (> {Q.get('hero_palette_max', 0.15)}): "
                                                f"clothes, skin or hair changed"))
    return f or [finding("LT-60", "PASS", f"{what}: palette {m['palette_dist']}, ink x{m['ink_ratio']}, "
                                          f"backdrop corr {m['backdrop_corr']}")]


def identity_file(a, b=None, heroes=None):
    """Two clips: A's last frame vs B's first. One clip: its first frame vs its last (identity drift inside a shot)."""
    fa = read_video(a)[0]
    fb = read_video(b)[0] if b else fa
    what = "shot A -> shot B" if b else "first -> last frame"
    m = shot_identity(fa[-1] if b else fa[0], fb[0] if b else fa[-1], heroes)
    return m, judge_identity(m, what)
