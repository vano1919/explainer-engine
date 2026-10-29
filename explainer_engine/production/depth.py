# from vano1919/tmr-video-script-engine@1c34e27:tmr_engine/render/depth.py
"""Depth maps for the pictures: the 2.5D parallax of D-70 stage F (motion stays stills + parallax by default, bible.json).

Depth-Anything V2 Small (Apache-2.0; onnx-community/depth-anything-v2-small, ~99 MB) runs once per picture on the CPU
(onnxruntime, ~2.5 s) and its map is stored next to the picture (``<picture>.depth.png``, 8-bit, near = white, softened so
no edge tears). ``production/parallax.py`` then moves the near parts of a picture a little more than the far parts as the
shot runs. The map is computed once, so every frame stays a pure function of its number. Without the model
(``tools/depth`` or ``$EXPLAINER_DEPTH_DIR``) the pictures simply stay flat and the render report says so.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = "depth_anything_v2_small.onnx"
SUFFIX = ".depth.png"
INPUT_SIZE = (924, 518)   # width, height: 518 rows as the model was trained, a multiple of 14, 16:9
MAP_SIZE = (576, 324)     # stored map: smooth enough to be resized to any frame
SOFTEN = 3.0              # Gaussian blur radius of the stored map (px): depth edges become slopes, never tears
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_session = None


def folder() -> Path:
    return Path(os.environ.get("EXPLAINER_DEPTH_DIR") or ROOT / "tools" / "depth")


def available() -> bool:
    return (folder() / MODEL_FILE).exists()


def map_path(picture: Path) -> Path:
    picture = Path(picture)
    return picture.with_name(picture.stem + SUFFIX)


def _model():
    global _session
    if _session is None:
        import onnxruntime as ort

        _session = ort.InferenceSession(str(folder() / MODEL_FILE), providers=["CPUExecutionProvider"])
    return _session


def estimate(image, session=None):
    """A PIL RGB image -> its depth map (PIL "L", MAP_SIZE, 255 = nearest), normalised per picture."""
    from PIL import Image, ImageFilter

    x = np.asarray(image.convert("RGB").resize(INPUT_SIZE, Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
    s = session or _model()
    d = np.asarray(s.run(None, {s.get_inputs()[0].name: x})[0], dtype=np.float32).reshape(-1, *x.shape[2:])[0]
    lo, hi = np.percentile(d, 1.0), np.percentile(d, 99.0)
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    out = Image.fromarray((d * 255.0 + 0.5).astype(np.uint8), mode="L").resize(MAP_SIZE, Image.BILINEAR)
    return out.filter(ImageFilter.GaussianBlur(SOFTEN))


def ensure(picture: Path, session=None) -> Path | None:
    """The stored map of a picture, made now if missing; None when no model is installed."""
    from PIL import Image

    out = map_path(picture)
    if out.exists():
        return out
    if session is None and not available():
        return None
    try:
        estimate(Image.open(picture), session).save(out.with_suffix(".tmp.png"), format="PNG")
        os.replace(out.with_suffix(".tmp.png"), out)
    except Exception as exc:  # a broken model or picture: the picture stays flat, the video goes on
        logger.warning("depth map for %s failed: %s", picture, exc)
        return None
    return out


def main(argv: list[str] | None = None) -> int:
    """Depth maps for picture files or folders (free, local CPU). Exit 1 when the model is not installed."""
    import argparse

    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.depth")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    if not available():
        print(f"no depth model: put {MODEL_FILE} (onnx-community/depth-anything-v2-small, Apache-2.0) in {folder()}")
        return 1
    files = []
    for p in map(Path, a.paths):
        files += sorted(x for x in p.glob("*.png") if not x.name.endswith(SUFFIX)) if p.is_dir() else [p]
    made = [f for f in files if ensure(f)]
    print(f"{len(made)} of {len(files)} pictures have a depth map")
    return 0 if len(made) == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
