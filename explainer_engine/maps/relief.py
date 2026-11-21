"""Real shaded relief for the map plates (v4.3 plan P4.1, finding F6): Natural Earth's 1:10m shaded relief raster.

The archive drew relief from a synthetic DEM with hand-placed Toba, Deccan, Ethiopia and Waterloo features (``plate.py``,
F6). This module reads a public-domain raster instead: Natural Earth ``SR_HR`` (21600x10800 grey, 1/60 degree a pixel,
georeferenced by its world file ``SR_HR.tfw``). Licence: "All versions of Natural Earth raster + vector map data found on
this website are in the public domain" (naturalearthdata.com/about/terms-of-use, read 2026-11-12); the row is in
``docs/PROVENANCE.md``.

The raster is a one-time free download, kept out of git: ``python -m explainer_engine.production.relief_fetch`` puts it in
``tools/maps/`` (or ``$EXPLAINER_RELIEF_DIR``) and checks the archive's sha256 (the download lives outside ``maps/``: CMP-14
keeps the map renderers free of clients). Without it the plate refuses to draw relief
(``ConfigError``); it never falls back to invented terrain.

Sampling is bilinear (bicubic when the frame is much finer than the raster) at the output resolution, on the window of the
raster the view covers, so a plate never shows the moire of a nearest-neighbour resample (plan P4.1).
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]
SOURCE_URL = "https://naciscdn.org/naturalearth/10m/raster/SR_HR.zip"
SOURCE_ZIP_SHA256 = "b2619fff2fc73c17152983c066adfaa25c4b626916b822bad2fae8bcd9be41a5"   # downloaded 2026-11-12, version 2.0.0
RASTER_NAME = "SR_HR.tif"


def relief_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_RELIEF_DIR") or ROOT / "tools" / "maps")


def raster_path() -> Path:
    return relief_dir() / RASTER_NAME


def available() -> bool:
    p = raster_path()
    return p.is_file() and p.with_suffix(".tfw").is_file()


def world_file(path: Path) -> tuple[float, float, float, float]:
    """(x pixel size, y pixel size (negative), lon of the first pixel's centre, lat of the first pixel's centre)."""
    a, _d, _b, e, c, f = (float(v) for v in Path(path).read_text().split())
    return a, e, c, f


@lru_cache(maxsize=2)
def _load(path: str) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as im:
        arr = np.asarray(im.convert("L"))
    return arr, world_file(Path(path).with_suffix(".tfw"))


def raster(path: Path | None = None) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    p = Path(path) if path else raster_path()
    if not p.is_file() or not p.with_suffix(".tfw").is_file():
        raise ConfigError(f"no shaded relief raster at {p} (run: python -m explainer_engine.production.relief_fetch); "
                          "the plate never invents terrain (v4.3 P4, F6)")
    return _load(str(p))


def sample(view, path: Path | None = None) -> np.ndarray:
    """The relief of ``view`` at its pixel size: float32 in 0..1 (1 = lit), shape (height, width)."""
    from scipy.ndimage import map_coordinates
    arr, (a, e, c, f) = raster(path)
    h, w = int(view.height), int(view.width)
    xs = np.arange(w, dtype=np.float64) + 0.5
    ys = np.arange(h, dtype=np.float64) + 0.5
    lon, _ = view.to_lonlat(xs, np.zeros_like(xs))
    _, lat = view.to_lonlat(np.zeros_like(ys), ys)
    col = (np.asarray(lon) - c) / a
    row = (np.asarray(lat) - f) / e
    c0, c1 = int(np.floor(col.min())) - 2, int(np.ceil(col.max())) + 3
    r0, r1 = max(0, int(np.floor(row.min())) - 2), min(arr.shape[0], int(np.ceil(row.max())) + 3)
    cols = np.arange(c0, c1) % arr.shape[1]                     # the date line wraps
    win = arr[r0:r1][:, cols].astype(np.float32) / 255.0
    rr, cc = np.meshgrid(row - r0, col - c0, indexing="ij")
    raster_px_per_out_px = abs(col[-1] - col[0]) / max(1, w - 1)
    order = 3 if raster_px_per_out_px < 0.5 else 1               # upsampled a lot: cubic; else bilinear (never nearest)
    out = map_coordinates(win, [rr, cc], order=order, mode="nearest")
    return np.clip(out, 0.0, 1.0).astype(np.float32)
