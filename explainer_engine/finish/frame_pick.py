"""Pick the frame of a clip that a continuation, a crop or a still starts from, by its person (BP-199).

The owner, 2026-11-14 (P1 thread): when we take a frame from the end of a clip and choose the best one, the main parts
decide: the person's position and face. A frame where the face is caught mid-move looks wrong even when the upscale is
good. The frame to take is the one where the person stands most still; that frame is cut out and upscaled
(``finish/superres``).

The scores of every candidate frame (the last ``window_s`` seconds, or after a floor such as the end of a spoken line):

1. **Face** (YuNet, opencv_zoo, MIT; the face track with the best mean score across the window): sharpness (Laplacian
   variance inside the face box), stillness (mean grey change to the ``settle`` frames on each side, inside the box) and
   the face box's own jitter (its centre's move against the neighbours, in face widths).
2. **Body**: the change inside a box below the face (the person's position).
3. **Frame**: sharpness and change of the whole frame, last.

``score = W_FACE * (sharp - change - jitter) + W_BODY * (-change) + W_FRAME * (sharp - change)``, each term relative to the
window. Without a face in the window the frame terms decide and the report says ``person: not_found`` (REVIEW: a hero seen
from behind or a cartoon face YuNet misses goes to the reviewer). The weights are the owner's priority written as numbers;
engineering defaults until he or two source types set them.

    python -m explainer_engine.finish.frame_pick fetch
    python -m explainer_engine.finish.frame_pick pick <clip.mp4> --out DIR [--window-s 1.0] [--after FRAME]
                                                     [--upscale] [--size 1280x704] [--crop x0,y0,x1,y1]

``pick`` writes ``<clip>_f<NNN>.png`` (the chosen frame as it is), ``frame_pick.json`` and ``frame_pick_sheet.jpg``
(every candidate with its face enlarged and the chosen one marked); ``--upscale`` hands the frame to ``superres.upscale``.
Free and local: no paid call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ConfigError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

YUNET = {"repo": "opencv/face_detection_yunet", "revision": "3cc26e7f1014a5ee5d74a42acee58bafc9d0a310",
         "file": "face_detection_yunet_2023mar.onnx",
         "sha256": "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4", "license": "MIT"}
W_FACE = float(SR.T("BP-199", "w_face"))
W_BODY = float(SR.T("BP-199", "w_body"))
W_FRAME = float(SR.T("BP-199", "w_frame"))
FACE_SCORE_MIN = float(SR.T("BP-199", "face_score_min"))
SETTLE = int(SR.T("BP-199", "settle_frames"))
CHANGE_FLOOR = 1.0          # grey levels: a window that changes less than this everywhere is still; its noise is not ranked
BODY_W, BODY_H = 1.6, 6.0   # the body box: the face centre +- BODY_W face widths, from the face top down BODY_H face heights


def _cv2():
    import cv2
    return cv2


def yunet_path() -> Path | None:
    """``$EXPLAINER_YUNET``, the pinned download in ``$EXPLAINER_MODELS_DIR``, or the repo's ``tools/yunet`` copy."""
    from explainer_engine.finish import superres
    from explainer_engine.qa import pixels
    for p in (os.environ.get("EXPLAINER_YUNET"),
              superres.models_dir() / YUNET["repo"].replace("/", "__") / YUNET["file"], pixels.YUNET):
        if p and Path(p).is_file():
            return Path(p)
    return None


def fetch() -> Path:
    from explainer_engine.finish import superres
    p = superres.models_dir() / YUNET["repo"].replace("/", "__") / YUNET["file"]
    if not p.is_file():
        from huggingface_hub import hf_hub_download
        p.parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(YUNET["repo"], YUNET["file"], revision=YUNET["revision"], local_dir=str(p.parent))
    if hashlib.sha256(p.read_bytes()).hexdigest() != YUNET["sha256"]:
        raise ConfigError(f"{p}: sha256 does not match the pinned YuNet model")
    return p


def read_frames(clip: Path, first: int, count: int) -> list[np.ndarray]:
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(clip))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(first))
    out = []
    for _ in range(int(count)):
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    cap.release()
    return out


def clip_info(clip: Path) -> tuple[int, float]:
    cv2 = _cv2()
    cap = cv2.VideoCapture(str(clip))
    n, fps = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), float(cap.get(cv2.CAP_PROP_FPS) or 24.0)
    cap.release()
    return n, fps


# --- the person ------------------------------------------------------------------------------------------------------------

def detect_faces(frames: list[np.ndarray], model: Path | None) -> list[list[list[float]]]:
    """Per frame, every face YuNet finds: ``[x, y, w, h, score]`` in pixels."""
    if model is None or not frames:
        return [[] for _ in frames]
    cv2 = _cv2()
    h, w = frames[0].shape[:2]
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h), FACE_SCORE_MIN)
    out = []
    for f in frames:
        _, faces = det.detect(f)
        out.append([] if faces is None else [[float(v) for v in r[:4]] + [float(r[14])] for r in faces])
    return out


def _iou(a, b) -> float:
    ax1, ay1, bx1, by1 = a[0] + a[2], a[1] + a[3], b[0] + b[2], b[1] + b[3]
    iw, ih = max(0.0, min(ax1, bx1) - max(a[0], b[0])), max(0.0, min(ay1, by1) - max(a[1], b[1]))
    inter = iw * ih
    return inter / max(1e-6, a[2] * a[3] + b[2] * b[3] - inter)


def face_track(faces: list[list[list[float]]]) -> list[list[float] | None]:
    """The one face the window is about: every detection seeds a track (matched frame to frame by overlap); the track with
    the highest summed score wins (a face seen in most frames beats a one-frame false hit). Frames where the track's face
    was missed keep the nearest frame's box, flagged by score 0."""
    seeds = [b for fs in faces for b in fs]
    best, best_sum = None, 0.0
    for s in seeds:
        tr, tot = [], 0.0
        for fs in faces:
            m = max(fs, key=lambda b: _iou(b, s), default=None)
            if m is not None and _iou(m, s) > 0.3:
                tr.append(m)
                tot += m[4]
            else:
                tr.append(None)
        if tot > best_sum:
            best, best_sum = tr, tot
    if best is None:
        return [None] * len(faces)
    idx = [i for i, b in enumerate(best) if b is not None]
    return [best[i] if best[i] is not None else best[min(idx, key=lambda j: abs(j - i))][:4] + [0.0]
            for i in range(len(best))]


def body_box(face, shape) -> list[int]:
    h, w = shape[:2]
    cx, fw, fh = face[0] + face[2] / 2, face[2], face[3]
    x0, x1 = int(max(0, cx - BODY_W * fw)), int(min(w, cx + BODY_W * fw))
    y0, y1 = int(max(0, face[1] - 0.3 * fh)), int(min(h, face[1] + BODY_H * fh))
    return [x0, y0, x1, y1]


# --- the scores ------------------------------------------------------------------------------------------------------------

def _lap_var(g: np.ndarray) -> float:
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def _cut(g: np.ndarray, box) -> np.ndarray:
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    return g[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]


def score(frames: list[np.ndarray], track: list | None = None) -> list[dict]:
    """Every frame's measures and its score (the module's docstring). Pure numpy apart from the grey conversion."""
    cv2 = _cv2()
    grey = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) for f in frames]
    n = len(grey)
    track = track or [None] * n
    have_face = any(t is not None for t in track)

    def change(i, box):
        js = [j for j in range(i - SETTLE, i + SETTLE + 1) if j != i and 0 <= j < n]
        if not js:
            return 0.0
        a = grey[i] if box is None else _cut(grey[i], box)
        return float(np.mean([np.abs(a - (grey[j] if box is None else _cut(grey[j], box))).mean() for j in js]))

    rows = []
    for i in range(n):
        r = {"i": i, "frame_sharp": _lap_var(grey[i]), "frame_change": change(i, None)}
        t = track[i]
        if t is not None:
            fb = [t[0], t[1], t[0] + t[2], t[1] + t[3]]
            js = [j for j in range(i - SETTLE, i + SETTLE + 1) if j != i and 0 <= j < n and track[j] is not None]
            cx, cy = t[0] + t[2] / 2, t[1] + t[3] / 2
            jit = [np.hypot(cx - track[j][0] - track[j][2] / 2, cy - track[j][1] - track[j][3] / 2) / max(1.0, t[2])
                   for j in js]
            r.update({"face": [round(v, 1) for v in t[:4]], "face_score": round(t[4], 3),
                      "face_sharp": _lap_var(_cut(grey[i], fb)), "face_change": change(i, fb),
                      "face_jitter": float(np.mean(jit)) if jit else 0.0, "body_change": change(i, body_box(t, frames[i].shape))})
        rows.append(r)

    def rel(key, floor=0.0):
        top = max([r[key] for r in rows if key in r] + [floor]) or 1.0
        return {r["i"]: r[key] / top for r in rows if key in r}

    fs, fc = rel("frame_sharp"), rel("frame_change", CHANGE_FLOOR)
    if have_face:
        s, c, j, b = rel("face_sharp"), rel("face_change", CHANGE_FLOOR), rel("face_jitter", 0.02), rel("body_change", CHANGE_FLOOR)
    for r in rows:
        i = r["i"]
        frame_term = fs[i] - fc[i]
        if have_face and "face_sharp" in r:
            r["score"] = W_FACE * (s[i] - c[i] - j[i]) + W_BODY * -b[i] + W_FRAME * frame_term
        else:
            r["score"] = frame_term
    return rows


def pick(clip: Path, window_s: float = 1.0, after: int | None = None, model: Path | None | str = "auto") -> dict:
    """The chosen frame of ``clip``: candidates from ``after`` (or the last ``window_s`` seconds) to the last frame."""
    n, fps = clip_info(clip)
    if n < 1:
        raise ConfigError(f"{clip}: no frames")
    last = n - 1
    first = max(0, last + 1 - max(2, int(round(window_s * fps))))
    if after is not None:
        if after > last:
            return {"frame": None, "status": G.FAIL, "why": f"no frame after {after}: the clip ends at {last}"}
        first = max(first, int(after)) if after <= last else first
    frames = read_frames(clip, first, last + 1 - first)
    model = yunet_path() if model == "auto" else model
    track = face_track(detect_faces(frames, model))
    rows = score(frames, track)
    best = max(rows, key=lambda r: r["score"])
    found = any(t is not None for t in track)
    rep = {"clip": str(clip), "frame": first + best["i"], "window": [first, last], "fps": fps,
           "person": "face" if found else ("not_found" if model else "NOT_RUN: no YuNet model"),
           "status": G.PASS if found else G.REVIEW, "weights": {"face": W_FACE, "body": W_BODY, "frame": W_FRAME},
           "rule": "BP-199", "scores": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} | {"frame": first + r["i"]}
                                         for r in rows]}
    rep["_frames"] = frames
    return rep


def sheet(rep: dict, out: Path, cols: int = 6, tile_w: int = 320) -> Path:
    """Every candidate: the frame small with its face enlarged beside it, its score; the chosen one framed in green."""
    cv2 = _cv2()
    frames, rows = rep["_frames"], rep["scores"]
    h0, w0 = frames[0].shape[:2]
    th = int(round(tile_w * h0 / w0))
    tiles = []
    for f, r in zip(frames, rows):
        t = cv2.resize(f, (tile_w, th), interpolation=cv2.INTER_AREA)
        if r.get("face"):
            x, y, w, h = r["face"]
            m = 0.4 * max(w, h)
            fc = f[int(max(0, y - m)):int(min(h0, y + h + m)), int(max(0, x - m)):int(min(w0, x + w + m))]
            if fc.size:
                s = th // 2
                t[:s, tile_w - s:] = cv2.resize(fc, (s, s), interpolation=cv2.INTER_CUBIC)
        chosen = r["frame"] == rep["frame"]
        cv2.putText(t, f"f{r['frame']} {r['score']:+.2f}", (6, th - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(t, f"f{r['frame']} {r['score']:+.2f}", (6, th - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (80, 255, 80) if chosen else (255, 255, 255), 1)
        if chosen:
            cv2.rectangle(t, (1, 1), (tile_w - 2, th - 2), (80, 255, 80), 4)
        tiles.append(t)
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    img = np.vstack([np.hstack(tiles[i:i + cols]) for i in range(0, len(tiles), cols)])
    cv2.imwrite(str(out), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.finish.frame_pick")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    p = sub.add_parser("pick")
    p.add_argument("clip", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--window-s", type=float, default=1.0)
    p.add_argument("--after", type=int)
    p.add_argument("--upscale", action="store_true")
    p.add_argument("--size")
    p.add_argument("--crop")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        print(fetch())
        return 0
    cv2 = _cv2()
    a.out.mkdir(parents=True, exist_ok=True)
    rep = pick(a.clip, a.window_s, a.after)
    if rep.get("frame") is None:
        print(json.dumps(rep, indent=1))
        return 1
    frames = rep.pop("_frames")
    img = frames[rep["frame"] - rep["window"][0]]
    dst = a.out / f"{a.clip.stem}_f{rep['frame']:03d}.png"
    cv2.imwrite(str(dst), img)
    rep["file"], rep["sha256"] = str(dst), hashlib.sha256(dst.read_bytes()).hexdigest()
    rep["_frames"] = frames
    rep["sheet"] = str(sheet(rep, a.out / "frame_pick_sheet.jpg"))
    rep.pop("_frames")
    if a.upscale:
        from explainer_engine.finish import superres
        size = tuple(int(v) for v in a.size.lower().split("x")) if a.size else None
        crop = [float(v) for v in a.crop.split(",")] if a.crop else None
        up = superres.upscale(img, a.out, dst.stem, size=size, crop=crop)
        rep["upscale"] = {k: v for k, v in up.items() if k != "image"}
    write_json_atomic(a.out / "frame_pick.json", rep)
    print(json.dumps({k: rep[k] for k in ("frame", "window", "person", "status", "file", "sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
