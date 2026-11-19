"""Regional shaded relief from Copernicus DEM GLO-30 for map shots whose frame is far finer than Natural Earth's raster
(lanes test 2026-11-19: a 46 km Flanders frame drew Natural Earth's 1.85 km pixel 40 times enlarged, a blur).

    python -m explainer_engine.production.relief_regional fetch flanders     # download the tile once, make the hillshade
    python -m explainer_engine.production.relief_regional list

The hillshade is written next to the global raster (``tools/maps/regional/<name>.tif`` + ``.tfw``, 8-bit grey like SR_HR, flat
ground at ``RELIEF_FLAT``), and ``maps/relief.py`` uses it for any view that lies inside it. The vertical exaggeration is a house
default (flat country needs it to show at all) and is recorded in ``<name>.json`` next to the raster. The download lives here, not
in ``maps/`` (CMP-14). Copernicus DEM GLO-30: free of charge, attribution required ("Contains modified Copernicus data 2021",
docs/PROVENANCE.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np

from explainer_engine.maps import relief

COP = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM/Copernicus_DSM_COG_10_{lat}_00_{lon}_00_DEM.tif"
REGIONS = {"flanders": {"tiles": [("N50", "E002"), ("N50", "E003")], "z": 1.0,   # a row of tiles, west to east
                        "note": "Flanders and the Ypres salient (lon 2-4, lat 50-51)"}}
AZIMUTH, ALTITUDE = 315.0, 45.0
SMOOTH_PX = 1.5           # Gaussian sigma in DEM pixels (about 45 m) before shading; recorded in the json
FLAT = 0.82               # plate.RELIEF_FLAT: the grey of flat ground in the plate's gain formula


def regional_dir() -> Path:
    return relief.relief_dir() / "regional"


def hillshade(dem: np.ndarray, dx_m: float, dy_m: float, z: float) -> np.ndarray:
    """Float 0..1, flat ground at FLAT (a plain Horn hillshade, NW light, vertical exaggeration ``z``)."""
    d = np.pad(dem.astype(np.float64), 1, mode="edge")
    dzdx = ((d[:-2, 2:] + 2 * d[1:-1, 2:] + d[2:, 2:]) - (d[:-2, :-2] + 2 * d[1:-1, :-2] + d[2:, :-2])) / (8 * dx_m)
    dzdy = ((d[2:, :-2] + 2 * d[2:, 1:-1] + d[2:, 2:]) - (d[:-2, :-2] + 2 * d[:-2, 1:-1] + d[:-2, 2:])) / (8 * dy_m)
    slope = np.arctan(z * np.hypot(dzdx, dzdy))
    aspect = np.arctan2(dzdy, -dzdx)
    az, alt = math.radians(360.0 - AZIMUTH + 90.0), math.radians(ALTITUDE)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(FLAT * shade / math.sin(alt), 0.0, 1.0).astype(np.float32)


def write_world_file(path: Path, a: float, e: float, c: float, f: float) -> None:
    path.write_text(f"{a}\n0.0\n0.0\n{e}\n{c}\n{f}\n")


def _tile(lat: str, lon: str, out: Path):
    """One Copernicus tile: (dem, pixel width deg, pixel height deg, lon of its west edge, lat of its north edge, sha256)."""
    import tifffile
    src = out / f"{lat}_{lon}.dem.tif"
    if not src.is_file():
        tmp = src.with_suffix(".part")
        urllib.request.urlretrieve(COP.format(lat=lat, lon=lon), tmp)
        tmp.replace(src)
    with tifffile.TiffFile(src) as t:
        page = t.pages[0]
        sx, sy, _ = page.tags["ModelPixelScaleTag"].value
        _, _, _, lon0, lat0, _ = page.tags["ModelTiepointTag"].value
        dem = page.asarray()
    return dem, sx, sy, lon0, lat0, hashlib.sha256(src.read_bytes()).hexdigest()


def fetch(name: str) -> Path:
    from PIL import Image
    reg = REGIONS[name]
    out = regional_dir()
    out.mkdir(parents=True, exist_ok=True)
    tiles = [_tile(lat, lon, out) for lat, lon in reg["tiles"]]
    sx, sy = tiles[0][1], tiles[0][2]
    if any(t[1] != sx or t[2] != sy or t[0].shape[0] != tiles[0][0].shape[0] or t[4] != tiles[0][4] for t in tiles):
        raise ValueError(f"{name}: the tiles do not share one grid and one north edge")
    dem = np.concatenate([t[0] for t in tiles], axis=1)
    lon0, lat0 = tiles[0][3], tiles[0][4]
    lat_mid = lat0 - dem.shape[0] * sy / 2
    dx_m, dy_m = sx * 111320.0 * math.cos(math.radians(lat_mid)), sy * 110574.0
    from scipy.ndimage import gaussian_filter
    dem = gaussian_filter(np.where(dem < -50, 0.0, dem).astype(np.float32), SMOOTH_PX)   # a surface model: roofs and tree tops are noise
    shade = hillshade(dem, dx_m, dy_m, reg["z"])
    tif = out / f"{name}.tif"
    Image.fromarray((shade * 255 + 0.5).astype(np.uint8), "L").save(tif)
    write_world_file(tif.with_suffix(".tfw"), sx, -sy, lon0 + sx / 2, lat0 - sy / 2)
    meta = {"name": name, "sources": [COP.format(lat=a, lon=b) for a, b in reg["tiles"]],
            "source_sha256": [t[5] for t in tiles], "vertical_exaggeration": reg["z"], "azimuth": AZIMUTH,
            "altitude": ALTITUDE, "smooth_px": SMOOTH_PX, "pixel_m": [round(dx_m, 1), round(dy_m, 1)],
            "bbox": [lon0, lat0 - dem.shape[0] * sy, lon0 + dem.shape[1] * sx, lat0]}
    tif.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    return tif


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cmd", choices=("fetch", "list"))
    ap.add_argument("name", nargs="?", choices=sorted(REGIONS))
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for k, v in REGIONS.items():
            print(k, v["note"], "ready" if (regional_dir() / f"{k}.tif").is_file() else "not fetched")
        return 0
    if not a.name:
        ap.error("fetch needs a region name")
    print(fetch(a.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
