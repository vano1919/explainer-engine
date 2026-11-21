"""A picture -> a depth map in (assumed) metres, cached as .npy: the input ``fx25d/living.py`` asks for.

The model is Depth-Anything V2 Small (Apache-2.0, free, CPU onnxruntime), loaded by ``production/depth.py`` (``tools/depth`` or
``$EXPLAINER_DEPTH_DIR``). It gives a RELATIVE inverse depth (nearer = larger), not metres. This module turns it into metres with a
documented, monotone assumption: the nearest percentile of the picture sits ``near_m`` from the camera, the farthest ``far_m``, and
disparity is linear between them (d = 1 / (1/far + s * (1/near - 1/far)), s in 0..1). ``near_m`` / ``far_m`` are arguments of the shot spec
(defaults 2.5 / 60 m): they are assumptions, not measurements, and the parallax / flake-depth / fire-light of living.py scale with them.
The result is cached next to nothing else: ``<cache_dir>/<stem>_<sha8>_n<near>_f<far>.npy`` (sha of the picture bytes, so a new
picture never reuses an old map). CPU only, nothing paid.

usage: python -m explainer_engine.fx25d.depth_metres photo.jpeg [--cache-dir DIR] [--near 2.5] [--far 60]
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np

DEFAULT_NEAR_M, DEFAULT_FAR_M = 2.5, 60.0
OUT_SIZE = (640, 360)     # stored map (w, h): living.py resizes it to 1280x720


def relative_to_metres(rel: np.ndarray, near_m: float = DEFAULT_NEAR_M, far_m: float = DEFAULT_FAR_M) -> np.ndarray:
    """Relative inverse depth (any scale, larger = nearer) -> metres, monotone, per-picture normalised on the 1st..99th percentile."""
    if not (0 < near_m < far_m):
        raise ValueError(f"need 0 < near_m < far_m, got {near_m}, {far_m}")
    rel = np.asarray(rel, dtype=np.float32)
    lo, hi = np.percentile(rel, 1.0), np.percentile(rel, 99.0)
    s = np.clip((rel - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    return (1.0 / (1.0 / far_m + s * (1.0 / near_m - 1.0 / far_m))).astype(np.float32)


def raw_relative(image, session=None) -> np.ndarray:
    """A PIL image -> the model's raw relative inverse depth at OUT_SIZE (float32)."""
    import cv2
    from explainer_engine.production import depth as D
    from PIL import Image

    s = session or D._model()
    x = np.asarray(image.convert("RGB").resize(D.INPUT_SIZE, Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - D.MEAN) / D.STD).transpose(2, 0, 1)[None].astype(np.float32)
    d = np.asarray(s.run(None, {s.get_inputs()[0].name: x})[0], dtype=np.float32).reshape(-1, *x.shape[2:])[0]
    return cv2.resize(d, OUT_SIZE, interpolation=cv2.INTER_AREA)


def cache_path(photo: Path, cache_dir: Path, near_m: float, far_m: float) -> Path:
    sha = hashlib.sha256(Path(photo).read_bytes()).hexdigest()[:8]
    return Path(cache_dir) / f"{Path(photo).stem}_{sha}_n{near_m:g}_f{far_m:g}.npy"


def ensure_depth(photo, cache_dir, near_m: float = DEFAULT_NEAR_M, far_m: float = DEFAULT_FAR_M, session=None) -> Path:
    """The cached metric map of a picture, computed now when missing. Raises FileNotFoundError when no model is installed."""
    from explainer_engine.production import depth as D
    from PIL import Image

    out = cache_path(Path(photo), Path(cache_dir), near_m, far_m)
    if out.exists():
        return out
    if session is None and not D.available():
        raise FileNotFoundError(f"no depth model: put {D.MODEL_FILE} (onnx-community/depth-anything-v2-small, Apache-2.0) in {D.folder()}")
    out.parent.mkdir(parents=True, exist_ok=True)
    arr = relative_to_metres(raw_relative(Image.open(photo), session), near_m, far_m)
    tmp = out.with_name(out.name + ".tmp")
    with open(tmp, "wb") as fh:
        np.save(fh, arr)
    tmp.replace(out)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.fx25d.depth_metres")
    ap.add_argument("photo", nargs="+")
    ap.add_argument("--cache-dir", default="jobs/_depth_cache")
    ap.add_argument("--near", type=float, default=DEFAULT_NEAR_M)
    ap.add_argument("--far", type=float, default=DEFAULT_FAR_M)
    a = ap.parse_args(argv)
    for p in a.photo:
        print(ensure_depth(p, a.cache_dir, a.near, a.far))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
