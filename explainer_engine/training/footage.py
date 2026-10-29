"""Footage -> training material for the next-pose (photo) and motion (video) LoRAs (docs/LORA_TRAINING.md section 6,
FS-00..FS-07). Free, CPU: ffprobe/ffmpeg + OpenCV + PySceneDetect (``pip install scenedetect opencv-python-headless``).

    python -m explainer_engine.training footage-index <raw dir> --out <work dir>        # FS-00: probe every file
    python -m explainer_engine.training footage-split <work dir>                        # FS-01: shots.json
    python -m explainer_engine.training footage-measure <work dir>                      # FS-02: camera + motion per shot
    python -m explainer_engine.training footage-balance <work dir> [--heldout <show>]   # FS-03/04: shares, held-out show
    python -m explainer_engine.training footage-pairs <work dir> --out <pairs dir>      # F6a: control/target frames
    python -m explainer_engine.training footage-clips <work dir> --out <clips dir>      # F6b: 89-frame clips + clips.json

Show = the raw file's stem up to the first ``_s``/``_season``/digit group (``aladdin_1992.mp4`` -> ``aladdin``).
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np

from .audit import RULES, finding

FS = RULES.get("footage", {})
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"}


def show_of(name):
    stem = Path(name).stem.lower()
    return re.split(r"_(?:s\d|season|\d{4}|collage|part|ep)", stem)[0] or stem


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames,field_order:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"path": str(path), "show": show_of(path), "width": int(s["width"]), "height": int(s["height"]),
            "fps": round(int(num) / max(int(den), 1), 3), "duration": float(j["format"]["duration"]),
            "field_order": s.get("field_order", "progressive")}


def index(raw_dir, work_dir):
    files = sorted(p for p in Path(raw_dir).iterdir() if p.suffix.lower() in VIDEO_EXT)
    rows, f = [], []
    for p in files:
        r = probe(p)
        rows.append(r)
        if r["height"] < FS.get("min_height", 720):
            f.append(finding("FS-00", "WARN", f"{p.name}: {r['width']}x{r['height']} under {FS.get('min_height', 720)}p"))
        if r["fps"] < FS.get("min_fps", 23):
            f.append(finding("FS-00", "WARN", f"{p.name}: {r['fps']} fps"))
        if r["field_order"] not in ("progressive", "unknown"):
            f.append(finding("FS-00", "WARN", f"{p.name}: interlaced ({r['field_order']}); deinterlace first (yadif)"))
    if not rows:
        f.append(finding("FS-00", "FAIL", f"no video files in {raw_dir}"))
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    rep = {"files": rows, "hours": round(sum(r["duration"] for r in rows) / 3600, 2), "findings": f}
    (Path(work_dir) / "index.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    return rep


# ---- FS-01 shots -------------------------------------------------------------------------------------------------------

def split_file(path, *, min_len_s=None, threshold=None):
    """PySceneDetect ContentDetector (hard cuts; dissolves are rare in 2D animation); returns [(start_s, end_s)]."""
    from scenedetect import ContentDetector, detect
    min_len_s = FS.get("min_shot_s", 2.0) if min_len_s is None else min_len_s
    scenes = detect(str(path), ContentDetector(threshold=threshold or FS.get("content_threshold", 27.0)))
    out = []
    for a, b in scenes:
        s, e = a.seconds, b.seconds
        if e - s >= min_len_s:
            out.append((round(s, 3), round(e, 3)))
    return out


def _dhash_frame(gray):
    import cv2
    g = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | int(g[r, c] > g[r, c + 1])
    return bits


def read_frames(path, t0, t1, *, step_s=0.5, size=None):
    """Grey frames every step_s between t0 and t1 (OpenCV), downscaled to ``size`` (w, h)."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames, ts = [], []
    t = t0
    while t < t1:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
        ok, fr = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if size:
            g = cv2.resize(g, size, interpolation=cv2.INTER_AREA)
        frames.append(g)
        ts.append(round(t, 3))
        t += step_s
    cap.release()
    return frames, ts


def split(work_dir, *, min_len_s=None):
    idx = json.loads((Path(work_dir) / "index.json").read_text(encoding="utf-8"))
    shots, seen = [], {}
    for r in idx["files"]:
        for k, (s, e) in enumerate(split_file(r["path"], min_len_s=min_len_s)):
            fr, _ = read_frames(r["path"], s + 0.25, s + 0.26, size=(160, 90))
            h = _dhash_frame(fr[0]) if fr else None
            dup = None
            if h is not None:
                for h2, sid in seen.items():
                    if bin(h ^ h2).count("1") <= FS.get("dup_hamming", 4):
                        dup = sid
                        break
            sid = f"{Path(r['path']).stem}_{k:04d}"
            if dup is None and h is not None:
                seen[h] = sid
            shots.append({"id": sid, "file": r["path"], "show": r["show"], "start": s, "end": e,
                          "dur": round(e - s, 3), "dup_of": dup})
    (Path(work_dir) / "shots.json").write_text(json.dumps(shots, indent=1), encoding="utf-8")
    return shots


# ---- FS-02 camera and motion ---------------------------------------------------------------------------------------------

def camera_motion(frames):
    """Per step: global shift (fraction of width, phase correlation) and residual motion (mean abs diff after the shift)."""
    import cv2
    shifts, residual = [], []
    for a, b in zip(frames, frames[1:]):
        fa, fb = np.float32(a), np.float32(b)
        raw = float(np.abs(fa - fb).mean() / 255.0)
        if raw < FS.get("static_residual", 0.01) or fa.std() < 2.0:  # nothing moved, or a flat frame: no correlation
            shifts.append(0.0)
            residual.append(raw)
            continue
        (dx, dy), _ = cv2.phaseCorrelate(fa, fb)
        shifts.append(float(np.hypot(dx, dy) / a.shape[1]))
        m = np.float32([[1, 0, -dx], [0, 1, -dy]])
        bb = cv2.warpAffine(fb, m, (a.shape[1], a.shape[0]))
        residual.append(float(np.abs(fa - bb).mean() / 255.0))
    return shifts, residual


def measure_shot(shot):
    frames, ts = read_frames(shot["file"], shot["start"] + 0.1, shot["end"] - 0.05, step_s=FS.get("measure_step_s", 0.5), size=(320, 180))
    if len(frames) < 2:
        return {"camera": None, "motion": None, "static_share": None}
    shifts, resid = camera_motion(frames)
    return {"camera": round(float(np.percentile(shifts, 90)), 4), "motion": round(float(np.median(resid)), 4),
            "static_share": round(float(np.mean(np.array(resid) < FS.get("static_residual", 0.01))), 3)}


def measure(work_dir):
    p = Path(work_dir) / "shots.json"
    shots = json.loads(p.read_text(encoding="utf-8"))
    for s in shots:
        if "camera" not in s:
            s.update(measure_shot(s))
    p.write_text(json.dumps(shots, indent=1), encoding="utf-8")
    return shots


def classify(shot):
    """'pair' = fixed camera + real motion (photo pairs); 'clip' = real motion (video); 'static'/'dup' = out."""
    if shot.get("dup_of"):
        return "dup"
    if shot.get("motion") is None or shot["motion"] < FS.get("min_motion", 0.015):
        return "static"
    if shot["camera"] is not None and shot["camera"] <= FS.get("fixed_camera_shift", 0.01):
        return "pair"
    return "clip"


# ---- FS-03/04 balance ------------------------------------------------------------------------------------------------------

def balance(shots, *, heldout=None):
    use = [s for s in shots if classify(s) in ("pair", "clip")]
    by_show = Counter()
    for s in use:
        by_show[s["show"]] += s["dur"]
    total = sum(by_show.values()) or 1.0
    shares = {k: round(v / total, 3) for k, v in by_show.items()}
    f = []
    for k, v in shares.items():
        if v > FS.get("max_show_share", 0.3) and len(shares) > 1:
            f.append(finding("FS-03", "WARN", f"{k} = {v:.0%} of usable footage (max {FS.get('max_show_share', 0.3):.0%}): "
                                              "cap its shots or add shows"))
    if heldout is None and len(shares) >= 3:
        heldout = min(shares, key=shares.get)
    if heldout is None:
        f.append(finding("FS-04", "WARN", "no held-out show (need 3+ shows): the judge has no unseen footage"))
    else:
        f.append(finding("FS-04", "INFO", f"held-out show: {heldout} ({shares.get(heldout, 0):.0%})"))
    kinds = Counter(classify(s) for s in shots)
    return {"shares": shares, "heldout": heldout, "kinds": dict(kinds), "findings": f}


# ---- F6a pairs / F6b clips -------------------------------------------------------------------------------------------------

def _grab(path, t, out, *, long_side=1024):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                    "-vf", f"scale='if(gt(iw,ih),{long_side},-2)':'if(gt(iw,ih),-2,{long_side})'", str(out)], check=True)


def pairs(work_dir, out_dir, *, heldout=None, gap=None):
    """control = the shot's first clean frame (master), target = the frame ``gap`` seconds later (and one more pair for
    long shots, both from the master: never chained). Held-out show -> out_dir/heldout/."""
    lo, hi = gap or FS.get("pair_gap_s", [2.5, 4.0])
    shots = json.loads((Path(work_dir) / "shots.json").read_text(encoding="utf-8"))
    made = []
    for s in shots:
        if classify(s) != "pair":
            continue
        base = Path(out_dir) / ("heldout" if s["show"] == heldout else "train")
        (base / "control").mkdir(parents=True, exist_ok=True)
        (base / "target").mkdir(parents=True, exist_ok=True)
        t0 = s["start"] + 0.2
        targets = [t0 + (lo + hi) / 2]
        if s["dur"] >= 2 * hi:
            targets.append(t0 + 2 * hi - 0.5)
        for k, t1 in enumerate(targets):
            if t1 >= s["end"] - 0.1:
                continue
            name = f"{s['id']}_{k}.png"
            _grab(s["file"], t0, base / "control" / name)
            _grab(s["file"], t1, base / "target" / name)
            made.append({"name": name, "shot": s["id"], "show": s["show"], "t_control": round(t0, 3),
                         "t_target": round(t1, 3), "split": base.name})
    (Path(out_dir) / "pairs.json").write_text(json.dumps(made, indent=1), encoding="utf-8")
    return made


def clips(work_dir, out_dir, *, heldout=None, frames=None, fps=24, width=768, height=448, max_per_show=None):
    """89-frame clips from the start of each moving shot, resized/cropped to the bucket; clips.json for audit-video."""
    frames = frames or FS.get("clip_frames", 89)
    shots = json.loads((Path(work_dir) / "shots.json").read_text(encoding="utf-8"))
    per_show = Counter()
    made = []
    for s in sorted(shots, key=lambda x: -(x.get("motion") or 0)):
        if classify(s) not in ("pair", "clip") or s["dur"] * fps < frames + 2:
            continue
        if max_per_show and per_show[s["show"]] >= max_per_show:
            continue
        base = Path(out_dir) / ("heldout" if s["show"] == heldout else "train")
        base.mkdir(parents=True, exist_ok=True)
        out = base / f"{s['id']}.mp4"
        vf = (f"fps={fps},scale='if(gt(a,{width}/{height}),-2,{width})':'if(gt(a,{width}/{height}),{height},-2)',"
              f"crop={width}:{height}")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s['start']:.3f}", "-i", s["file"], "-an", "-vf", vf,
                        "-frames:v", str(frames), "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(out)],
                       check=True)
        per_show[s["show"]] += 1
        made.append({"path": str(out), "frames": frames, "width": width, "height": height, "caption": "",
                     "shot": s["id"], "show": s["show"], "split": base.name, "motion": s.get("motion")})
    (Path(out_dir) / "clips.json").write_text(json.dumps(made, indent=1), encoding="utf-8")
    return made


def caption_findings_motion(captions, banned=()):
    """FS-05: no character/show/studio names and no style words in motion captions."""
    bad = [w.lower() for w in (list(banned) + FS.get("banned_words", []))]
    f = []
    for i, c in enumerate(captions):
        hits = [w for w in bad if re.search(rf"\b{re.escape(w)}\b", c.lower())]
        if hits:
            f.append(finding("FS-05", "FAIL", f"caption {i}: names/style words {hits}"))
    return f
