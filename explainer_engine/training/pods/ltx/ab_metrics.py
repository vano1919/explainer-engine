"""The free metrics of the LTX continuity A/B (CT-2, docs/LTX_AB_PLAN_2026-11-20.md), run on the clips later; here written and
tested on synthetic clips. CPU, numpy + PIL + ffmpeg (no OpenCV). Nothing in this module calls a paid or networked service.

Per clip (last frame against the untouched vault master):
- ``identity``: cosine of the last frame to the master with the repo's own embedder (``qa/identity.clip_embedder``; injectable,
  e.g. an ArcFace embedder). NOT_RUN when torch / open_clip are missing: never a guess;
- ``flicker``: frame-to-frame CIE LAB dE76 (mean over the picture) per consecutive pair, reported as the mean and the p95 of
  the pairs;
- ``sharpness_ratio``: Laplacian variance of the last frame over the master's (both grey, at the master's size);
- ``psnr_db`` and ``lpips``: of the last frame against the master at the master's size; ``lpips`` is injectable and NOT_RUN
  without it (the LPIPS weights are not pinned in this repo).

``continuation_check`` writes the three numbers CT-1 asks of a hop (``videolane/plan.CT1_CHECK_KEYS``); ``lab_lock`` is the colour
lock of a hand-over frame (Reinhard mean/std transfer in LAB toward the master). ``blind_labels`` hides the arms for the owner's
look. No threshold is decided here: the numbers are reported, the plan thread registers any rule that uses them.
"""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def rgb_to_lab(rgb) -> np.ndarray:
    """sRGB uint8/float (0-255) ``(..., 3)`` -> CIE LAB (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _M.T / _WHITE
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_rgb(lab) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[..., 0] + 16) / 116
    fx, fz = fy + lab[..., 1] / 500, fy - lab[..., 2] / 200
    f = np.stack([fx, fy, fz], axis=-1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _WHITE
    lin = xyz @ np.linalg.inv(_M).T
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.clip(lin, 0, None) ** (1 / 2.4) - 0.055)
    return np.clip(np.round(c * 255.0), 0, 255).astype(np.uint8)


def read_frames(clip, width: int = 320, sh=subprocess.run) -> np.ndarray:
    """Every frame of a clip as ``(n, h, w, 3)`` uint8 RGB at ``width`` (ffmpeg decode)."""
    clip = Path(clip)
    p = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
            str(clip)], check=True, timeout=60, capture_output=True, text=True)
    w0, h0 = (int(v) for v in p.stdout.strip().split(",")[:2])
    h = max(2, int(round(width * h0 / w0 / 2)) * 2)
    raw = sh(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"scale={width}:{h}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
             check=True, timeout=300, capture_output=True).stdout
    n = len(raw) // (width * h * 3)
    return np.frombuffer(raw[:n * width * h * 3], np.uint8).reshape(n, h, width, 3)


def _grey(a) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    return a @ np.array([0.299, 0.587, 0.114]) if a.ndim == 3 else a


def laplacian_variance(a) -> float:
    g = _grey(a)
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(np.var(lap))


def fit_to(a, like) -> np.ndarray:
    """``a`` resized to the size of ``like`` (Lanczos) when they differ."""
    like = np.asarray(like)
    a = np.asarray(a)
    if a.shape[:2] == like.shape[:2]:
        return a
    return np.asarray(Image.fromarray(a).resize((like.shape[1], like.shape[0]), Image.LANCZOS))


def flicker(frames) -> dict:
    """Frame-to-frame LAB dE76: the mean of every pair's picture-mean dE, and the p95 of those pair values."""
    fr = np.asarray(frames)
    if len(fr) < 2:
        return {"mean": None, "p95": None, "pairs": 0}
    labs = rgb_to_lab(fr)
    per = np.sqrt(((labs[1:] - labs[:-1]) ** 2).sum(axis=-1)).mean(axis=(1, 2))
    return {"mean": round(float(per.mean()), 4), "p95": round(float(np.percentile(per, 95)), 4), "pairs": int(len(per))}


def lab_delta_e(a, b) -> float:
    """Mean CIE dE76 of two pictures (``b`` fitted to ``a``'s size)."""
    la, lb = rgb_to_lab(a), rgb_to_lab(fit_to(b, a))
    return round(float(np.sqrt(((la - lb) ** 2).sum(axis=-1)).mean()), 4)


def sharpness_ratio(frame, master) -> float:
    """Laplacian variance of the frame over the master's, both at the master's size (1.0 = as sharp as the master)."""
    m = laplacian_variance(master)
    return round(laplacian_variance(fit_to(frame, master)) / m, 4) if m > 0 else float("nan")


def psnr_db(frame, master) -> float:
    a, b = np.asarray(fit_to(frame, master), dtype=np.float64), np.asarray(master, dtype=np.float64)
    mse = float(np.mean((a - b) ** 2))
    return float("inf") if mse == 0 else round(10 * np.log10(255.0 ** 2 / mse), 3)


def lab_lock(frame, master, strength: float = 1.0) -> np.ndarray:
    """The colour lock of a hand-over frame: mean and standard deviation of L, a, b moved toward the master's (Reinhard 2001),
    blended by ``strength`` (1 = full). Returns uint8 RGB of the frame's size."""
    lf, lm = rgb_to_lab(frame), rgb_to_lab(master)
    out = np.empty_like(lf)
    for c in range(3):
        sf, sm = lf[..., c].std(), lm[..., c].std()
        scale = sm / sf if sf > 1e-6 else 1.0
        moved = (lf[..., c] - lf[..., c].mean()) * scale + lm[..., c].mean()
        out[..., c] = lf[..., c] + strength * (moved - lf[..., c])
    return lab_to_rgb(out)


def identity_cosine(frame, master, embedder=None, tmp: Path | None = None) -> dict:
    """Cosine of two pictures' embeddings; ``{"state": "NOT_RUN", "why": ...}`` when no embedder can run (never a guess)."""
    import tempfile
    from explainer_engine.core.errors import ConfigError
    from explainer_engine.qa import identity as ID
    d = Path(tmp) if tmp else Path(tempfile.mkdtemp(prefix="ab_id_"))
    d.mkdir(parents=True, exist_ok=True)
    pa, pb = d / "frame.png", d / "master.png"
    Image.fromarray(np.asarray(frame)).save(pa)
    Image.fromarray(np.asarray(master)).save(pb)
    try:
        e = np.asarray((embedder or ID.clip_embedder)([str(pa), str(pb)]), dtype=float)
    except ConfigError as exc:
        return {"state": "NOT_RUN", "why": str(exc)}
    return {"state": "MEASURED", "cosine": round(ID.cosine(e[0], e[1]), 4)}


def continuation_check(frame, master, master_id: str, *, embedder=None, upscaled_x2: bool = False, lab_locked: bool = False) -> dict:
    """The record CT-1 asks of a hop 1-2 hand-over (``videolane/plan.CT1_CHECK_KEYS``) plus the two processing flags. A missing
    face embedding is written as ``None``: ``plan.ct1_check_problems`` then refuses the hand-over (never a made-up number)."""
    ident = identity_cosine(frame, master, embedder)
    return {"master": master_id, "face_cosine": ident.get("cosine"), "lab_delta_e": lab_delta_e(master, frame),
            "sharpness_ratio": sharpness_ratio(frame, master), "upscaled_x2": bool(upscaled_x2), "lab_lock": bool(lab_locked),
            "identity_state": ident["state"]}


def score_clip(clip, master_path, *, embedder=None, lpips_fn=None, width: int = 320, frames=None) -> dict:
    """All metrics of one clip against its master. ``frames`` (n, h, w, 3) may be passed instead of decoding ``clip``."""
    fr = np.asarray(frames) if frames is not None else read_frames(clip, width)
    master = np.asarray(Image.open(master_path).convert("RGB").resize((fr.shape[2], fr.shape[1]), Image.LANCZOS))
    last = fr[-1]
    out = {"frames": int(len(fr)), "flicker": flicker(fr), "identity": identity_cosine(last, master, embedder),
           "sharpness_ratio": sharpness_ratio(last, master), "psnr_db": psnr_db(last, master),
           "last_frame_lab_delta_e": lab_delta_e(master, last)}
    if lpips_fn is None:
        out["lpips"] = {"state": "NOT_RUN", "why": "no LPIPS function given (the weights are not pinned in this repo)"}
    else:
        out["lpips"] = {"state": "MEASURED", "value": round(float(lpips_fn(last, master)), 4)}
    return out


def blind_labels(items: dict, seed: int) -> dict:
    """The owner's blind look: ``items`` = ``{shot: {arm: clip_path}}``. Each shot's arms are shuffled (reproducible by
    ``seed``) under the neutral labels A, B, C, D; ``sheet`` holds only the labels and the clip paths to open, ``key`` maps
    them back and stays out of the owner's sight until he has chosen."""
    rng = random.Random(seed)
    sheet, key = {}, {}
    for shot in sorted(items):
        arms = sorted(items[shot])
        order = arms[:]
        rng.shuffle(order)
        labels = [chr(65 + i) for i in range(len(order))]
        sheet[shot] = {lab: str(items[shot][arm]) for lab, arm in zip(labels, order)}
        key[shot] = dict(zip(labels, order))
    return {"sheet": sheet, "key": key, "seed": seed, "key_sha256": hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()}
