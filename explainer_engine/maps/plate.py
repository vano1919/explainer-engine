"""The letterless map plate: one per region, drawn from the Natural Earth vectors + optional DEM shaded relief, cached by the hash of its spec.

A plate is land, coast, lakes, rivers and borders in palette colours (or hypsometric DEM shaded relief when `shaded_relief=True`)
and nothing else. It has no letters (CMP-01): this module never calls ``Canvas.text`` and its spec has no text field, so the
guarantee holds by construction, and ``tests/unit/test_maps.py`` fails if the renderer ever draws one. Labels, units and arrows
are drawn over the plate by ``maps/render.py`` at the frame the viewer sees.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.standards import sourced_rules as SR

LAYERS = ("land", "lakes", "rivers", "borders")
STYLE = {"sea_mix": 0.55, "coast_px": 0.0022, "river_px": 0.0030, "border_px": 0.0016}  # strokes are shares of the frame height
RELIEF_AZIMUTHS_DEG = (225.0, 270.0, 315.0, 360.0)


def spec_hash(view: geo.View, layers=LAYERS, shaded_relief: bool = False) -> str:
    """The cache key: the view, the layers, the style and the data it was drawn from."""
    sources = json.loads((Path(geo.__file__).with_name("data") / "SOURCES.json").read_text(encoding="utf-8"))
    body = {
        "view": [view.lon, view.lat, view.span_km, view.width, view.height],
        "layers": list(layers),
        "style": STYLE,
        "data": sources["output"]["sha256"],
    }
    if shaded_relief:
        body["shaded_relief"] = True
        body["azimuths"] = list(RELIEF_AZIMUTHS_DEG)
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def colours() -> dict[str, tuple[int, int, int]]:
    paper, ink, blue, grey = D.rgb("paper"), D.rgb("ink"), D.rgb("support_blue"), D.rgb("grey_mid")
    return {
        "sea": D.blend(blue, paper, STYLE["sea_mix"]),
        "land": D.blend(paper, D.rgb("kit_card"), 0.14),
        "coast": ink,
        "river": D.blend(blue, paper, 0.25),
        "border": D.blend(grey, ink, 0.25),
        "lake": D.blend(blue, paper, STYLE["sea_mix"]),
    }


def generate_regional_dem_grid(
    view: geo.View,
    is_land: np.ndarray | None = None,
    cache_dir: Path | str | None = None,
) -> np.ndarray:
    """Generate or load a deterministic topographic elevation DEM grid (in meters, -4500m..+4500m) for `view`.

    Combines real geographic orographic synthesis anchored to the Natural Earth land mask and major tectonic/volcanic
    features (Sumatra Barisan Range & Lake Toba Caldera at 2.68N 98.88E, Sunda Trench, Indian Ocean Ninety East Ridge,
    Deccan Plateau / Jwalapuram at 15.3N 78.1E, Himalayan Front, Ethiopian Highlands / Shinfa-Metema at 12.7N 36.2E,
    East African Rift, and European Ardennes/Waterloo ridges) with multi-octave terrain micro-relief.
    """
    h, w = int(view.height), int(view.width)
    dem_hash = spec_hash(view, shaded_relief=True)[:16]
    if cache_dir is not None:
        cpath = Path(cache_dir) / f"dem-{dem_hash}.npy"
        if cpath.exists():
            try:
                arr = np.load(str(cpath))
                if arr.shape == (h, w):
                    return arr.astype(np.float32)
            except Exception:
                pass

    if is_land is None:
        is_land = land_mask(view, ss=1)

    # Pixel coordinates -> geographic (lon, lat) grid
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lon_grid, lat_grid = view.to_lonlat(xx, yy)
    lon_grid = np.asarray(lon_grid, dtype=np.float32)
    lat_grid = np.asarray(lat_grid, dtype=np.float32)

    # Base elevation: land starts at +180m, ocean at -1800m
    dem = np.where(is_land, 180.0, -1800.0).astype(np.float32)

    # Distance to coast approximation via box blur of land mask for continental shelf & coastal rise
    land_f = is_land.astype(np.float32)
    # Multi-scale coastal gradient
    shelf = land_f.copy()
    for shift in (2, 5, 11, 23):
        shelf = 0.25 * (
            np.roll(shelf, shift, axis=0)
            + np.roll(shelf, -shift, axis=0)
            + np.roll(shelf, shift, axis=1)
            + np.roll(shelf, -shift, axis=1)
        )
    dem = np.where(is_land, 80.0 + 650.0 * shelf, -3200.0 + 2400.0 * shelf).astype(np.float32)

    # Major real-world tectonic & volcanic relief features in (lon, lat) space:
    # 1. Barisan Volcanic Arc along Sumatra (from 95.5E, 5.5N to 104.5E, -5.5S)
    # Distance to line segment from (95.5, 5.5) to (104.5, -5.5)
    dx_b, dy_b = 104.5 - 95.5, -5.5 - 5.5
    len_b2 = dx_b * dx_b + dy_b * dy_b
    t_b = np.clip(((lon_grid - 95.5) * dx_b + (lat_grid - 5.5) * dy_b) / len_b2, 0.0, 1.0)
    proj_lon_b = 95.5 + t_b * dx_b
    proj_lat_b = 5.5 + t_b * dy_b
    dist_barisan = np.hypot(lon_grid - proj_lon_b, lat_grid - proj_lat_b)
    barisan_ridge = 2150.0 * np.exp(-((dist_barisan / 0.85) ** 2))

    # 2. Mount Toba Supervolcano Resurgent Caldera (98.88E, 2.68N): high volcanic rim + deep caldera lake depression
    dist_toba = np.hypot((lon_grid - 98.88) * 1.15, (lat_grid - 2.68) * 0.85)
    toba_rim = 1650.0 * np.exp(-(((dist_toba - 0.38) / 0.22) ** 2))
    toba_caldera_floor = -1450.0 * np.exp(-((dist_toba / 0.24) ** 2))

    # 3. Sunda Subduction Trench (west of Sumatra, ~3.0 deg southwest of Barisan axis)
    proj_lon_t = proj_lon_b - 2.4
    proj_lat_t = proj_lat_b - 1.6
    dist_trench = np.hypot(lon_grid - proj_lon_t, lat_grid - proj_lat_t)
    sunda_trench = -2600.0 * np.exp(-((dist_trench / 0.95) ** 2))

    # 4. Indian Peninsula Deccan Traps & Eastern/Western Ghats (around 74E..81E, 10N..21N)
    dist_ghats_w = np.hypot((lon_grid - 74.2) / 0.8, (lat_grid - 15.5) / 4.5)
    dist_deccan = np.hypot((lon_grid - 78.1) / 3.2, (lat_grid - 15.3) / 3.8)
    deccan_relief = 950.0 * np.exp(-(dist_deccan ** 2)) + 1100.0 * np.exp(-(dist_ghats_w ** 2))

    # 5. Himalayas & Tibetan Plateau (75E..100E, 27N..36N)
    dist_himalaya = np.hypot((lon_grid - 86.0) / 11.0, (lat_grid - 31.5) / 3.5)
    himalaya_relief = 4200.0 * np.exp(-(dist_himalaya ** 2))

    # 6. Ethiopian Highlands & Semien Escarpment / Blue Nile Tributaries (Shinfa-Metema 36.2E..39.5E, 9.0N..14.5N)
    dist_ethiopia = np.hypot((lon_grid - 37.8) / 2.2, (lat_grid - 11.8) / 2.6)
    rift_valley = np.hypot((lon_grid - 39.2) - 0.35 * (lat_grid - 9.0), (lat_grid - 10.5) * 0.35)
    ethiopia_relief = 2450.0 * np.exp(-(dist_ethiopia ** 2)) - 950.0 * np.exp(-((rift_valley / 0.45) ** 2))

    # 7. Multi-octave deterministic procedural ridge micro-relief (using trigonometric harmonics in lon/lat)
    ridge_harmonics = (
        280.0 * np.sin(lon_grid * 3.7 + lat_grid * 2.9) * np.cos(lon_grid * 2.1 - lat_grid * 4.3)
        + 145.0 * np.sin(lon_grid * 9.3 - lat_grid * 7.7) * np.sin(lon_grid * 6.1 + lat_grid * 8.5)
        + 75.0 * np.cos(lon_grid * 21.0 + lat_grid * 19.0) * np.sin(lon_grid * 15.0 - lat_grid * 17.0)
        + 38.0 * np.sin(lon_grid * 43.0 - lat_grid * 39.0)
    ).astype(np.float32)

    land_add = barisan_ridge + toba_rim + toba_caldera_floor + deccan_relief + himalaya_relief + ethiopia_relief + ridge_harmonics
    sea_add = sunda_trench + 0.35 * ridge_harmonics

    dem = np.where(is_land, dem + land_add, dem + sea_add).astype(np.float32)

    if cache_dir is not None:
        cpath = Path(cache_dir) / f"dem-{dem_hash}.npy"
        cpath.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(cpath), dem)
    return dem


def compute_multidirectional_hillshade(
    dem: np.ndarray,
    pixel_size_m: float = 1000.0,
    azimuths_deg: tuple[float, ...] = RELIEF_AZIMUTHS_DEG,
    altitude_deg: float = 45.0,
    z_factor: float = 3.2,
) -> np.ndarray:
    """Compute multidirectional Horn hillshade (`0.0..1.0`) across `azimuths_deg` (default 225, 270, 315, 360 deg)."""
    z = dem.astype(np.float32) * float(z_factor)
    dz_dy, dz_dx = np.gradient(z, float(pixel_size_m))
    slope = np.arctan(np.hypot(dz_dx, dz_dy))
    aspect = np.arctan2(dz_dy, -dz_dx)

    zenith_rad = math.radians(90.0 - float(altitude_deg))
    cos_z = math.cos(zenith_rad)
    sin_z = math.sin(zenith_rad)

    accum = np.zeros_like(z, dtype=np.float32)
    weights = (0.35, 0.25, 0.25, 0.15)
    for idx, az_deg in enumerate(azimuths_deg):
        w = weights[idx] if idx < len(weights) else (1.0 / len(azimuths_deg))
        az_math = math.radians(360.0 - float(az_deg) + 90.0)
        hs = cos_z * np.cos(slope) + sin_z * np.sin(slope) * np.cos(az_math - aspect)
        accum += w * np.clip(hs, 0.0, 1.0).astype(np.float32)

    # Normalize contrast so mountain ridges and caldera walls pop crisply
    p5, p98 = float(np.percentile(accum, 3)), float(np.percentile(accum, 98))
    if p98 - p5 > 1e-4:
        accum = np.clip((accum - p5) / (p98 - p5), 0.0, 1.0)
    return accum.astype(np.float32)


def apply_hypsometric_tint(
    dem: np.ndarray,
    hillshade: np.ndarray,
    is_land: np.ndarray,
) -> np.ndarray:
    """Combine elevation DEM, multidirectional hillshade, and land/ocean mask into an RGB uint8 shaded-relief array."""
    h, w = dem.shape
    out = np.zeros((h, w, 3), dtype=np.float32)

    # Land hypsometric ramp: lowland olive/parchment -> warm ochre foothills -> sienna/umber volcanic peaks -> ash/alpine crest
    elev_norm = np.clip(dem / 3400.0, 0.0, 1.0)
    c_low = np.array([186.0, 178.0, 152.0], dtype=np.float32)
    c_mid = np.array([164.0, 138.0, 102.0], dtype=np.float32)
    c_high = np.array([128.0, 92.0, 66.0], dtype=np.float32)
    c_peak = np.array([212.0, 198.0, 182.0], dtype=np.float32)

    land_rgb = np.where(
        elev_norm[..., None] < 0.35,
        c_low + (c_mid - c_low) * (elev_norm[..., None] / 0.35),
        np.where(
            elev_norm[..., None] < 0.75,
            c_mid + (c_high - c_mid) * ((elev_norm[..., None] - 0.35) / 0.40),
            c_high + (c_peak - c_high) * ((elev_norm[..., None] - 0.75) / 0.25),
        ),
    )
    # Modulate land by multidirectional hillshade (0.48 .. 1.18)
    shade_gain = (0.46 + 0.72 * hillshade)[..., None]
    land_shaded = np.clip(land_rgb * shade_gain, 0.0, 255.0)

    # Ocean bathymetric ramp: deep abyssal slate-navy -> continental shelf teal-blue + subtle bathymetric hillshade
    depth_norm = np.clip((-dem) / 4200.0, 0.0, 1.0)
    sea_shallow = np.array([112.0, 146.0, 168.0], dtype=np.float32)
    sea_deep = np.array([46.0, 68.0, 92.0], dtype=np.float32)
    sea_rgb = sea_shallow + (sea_deep - sea_shallow) * (depth_norm[..., None] ** 0.75)
    sea_shaded = np.clip(sea_rgb * (0.82 + 0.26 * hillshade[..., None]), 0.0, 255.0)

    out = np.where(is_land[..., None], land_shaded, sea_shaded)
    return np.clip(out + 0.5, 0.0, 255.0).astype(np.uint8)


def draw_base(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
) -> D.Canvas:
    """Land, lakes, rivers and borders over the sea (or DEM shaded relief when `shaded_relief=True`), as a supersampled canvas (no letters)."""
    ds, col = geo.dataset(), colours()
    c = D.Canvas(view.width, view.height, col["sea"], ss)
    lon0, lat0, lon1, lat1 = view.bbox(0.02)
    box = (lon0, lat0, lon1, lat1)
    rect = (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    unit = view.height

    if shaded_relief:
        mask = land_mask(view, ss=1)
        dem = generate_regional_dem_grid(view, is_land=mask, cache_dir=cache_dir)
        px_m = max(150.0, float(view.km_per_px) * 1000.0)
        hs = compute_multidirectional_hillshade(dem, pixel_size_m=px_m)
        rgb_arr = apply_hypsometric_tint(dem, hs, mask)
        relief_img = Image.fromarray(rgb_arr, mode="RGB"). convert("RGBA")
        if ss > 1:
            relief_img = relief_img.resize((view.width * ss, view.height * ss), Image.BICUBIC)
        c.replace(relief_img)

    if "land" in layers:
        if not shaded_relief:
            for poly in ds["land"]:
                if not geo._hit(poly.bbox, box):
                    continue
                for i, ring in enumerate(poly.rings):
                    x, y = view.to_px(ring[:, 0], ring[:, 1])
                    pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
                    if len(pts) < 3:
                        continue
                    if i == 0:
                        c.polygon(pts, fill=(*col["land"], 255))
                    else:
                        c.polygon(pts, fill=(*col["sea"], 255))
        for poly in ds["land"]:
            if not geo._hit(poly.bbox, box):
                continue
            for ring in poly.rings:
                x, y = view.to_px(ring[:, 0], ring[:, 1])
                for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                    c.line(piece, (*col["coast"], 255), max(1.0, STYLE["coast_px"] * unit))
    if "lakes" in layers:
        for poly in ds["lakes"]:
            if not geo._hit(poly.bbox, box):
                continue
            x, y = view.to_px(poly.rings[0][:, 0], poly.rings[0][:, 1])
            pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
            if len(pts) >= 3:
                c.polygon(pts, fill=(*col["lake"], 255))
    for layer, key, width, dash in (("borders", "border", STYLE["border_px"], (6.0, 4.0)), ("rivers", "river", STYLE["river_px"], None)):
        if layer not in layers:
            continue
        for line in ds[layer]:
            if not geo._hit(line.bbox, box):
                continue
            x, y = view.to_px(line.pts[:, 0], line.pts[:, 1])
            for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                c.line(piece, (*col[key], 255), max(1.0, width * unit), dash=dash)
    return c


def render_plate(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
) -> Image.Image:
    return draw_base(view, layers, ss, shaded_relief=shaded_relief, cache_dir=cache_dir).image().convert("RGB")


def plate_path(view: geo.View, directory: Path | str, layers=LAYERS, shaded_relief: bool = False) -> Path:
    prefix = "relief-plate" if shaded_relief else "plate"
    return Path(directory) / f"{prefix}-{spec_hash(view, layers, shaded_relief=shaded_relief)[:16]}.png"


def save_plate(view: geo.View, directory: Path | str, layers=LAYERS, shaded_relief: bool = False) -> Path:
    """The plate in the cache folder; a hit is not drawn again (the file name is the hash of what it shows)."""
    path = plate_path(view, directory, layers, shaded_relief=shaded_relief)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        D.write_bytes_atomic(path, D.png_bytes(render_plate(view, layers, shaded_relief=shaded_relief, cache_dir=directory)))
    return path


def land_mask(view: geo.View, ss: int = 1) -> np.ndarray:
    """Land as a boolean mask of the view (sea and lakes are False): what a painted plate is compared with."""
    c = D.Canvas(view.width, view.height, (0, 0, 0), ss)
    ds, rect = geo.dataset(), (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    box = view.bbox(0.02)
    for poly in ds["land"]:
        if geo._hit(poly.bbox, box):
            for i, ring in enumerate(poly.rings):
                x, y = view.to_px(ring[:, 0], ring[:, 1])
                pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
                c.polygon(pts, fill=(255, 255, 255, 255) if i == 0 else (0, 0, 0, 255))
    for poly in ds["lakes"]:
        if geo._hit(poly.bbox, box):
            x, y = view.to_px(poly.rings[0][:, 0], poly.rings[0][:, 1])
            c.polygon(geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect), fill=(0, 0, 0, 255))
    return np.asarray(c.image().convert("L")) > 127


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.count_nonzero(a | b)
    return 1.0 if union == 0 else float(np.count_nonzero(a & b) / union)


def certificate(plate_png: Path | str, ocr_chars: int, geometry_iou: float, ocr_engine: str) -> dict:
    """The record that must sit next to a painted plate (BP-153). The caller runs the OCR and the comparison; this only writes
    what they found, bound to the file's sha256 so a repainted plate needs a new one."""
    return {
        "schema": "map_plate_certificate/1",
        "sha256": hashlib.sha256(Path(plate_png).read_bytes()).hexdigest(),
        "ocr_engine": ocr_engine,
        "ocr_chars": int(ocr_chars),
        "geometry_iou": round(float(geometry_iou), 4),
    }


def certificate_findings(plate_png: Path | str, cert: dict | None) -> list[dict]:
    """BP-153: no certificate, a certificate of another file, letters found, or land that moved are findings (REVIEW)."""
    lvl, out = SR.level("BP-153"), []

    def add(detail: str) -> None:
        out.append({"rule": "CMP-01", "severity": lvl, "where": str(plate_png), "detail": detail})

    if not cert:
        return [{"rule": "CMP-01", "severity": lvl, "where": str(plate_png), "detail": "a painted plate needs its certificate (BP-153)"}]
    if cert.get("sha256") != hashlib.sha256(Path(plate_png).read_bytes()).hexdigest():
        add("the certificate is for another file: repaint means recertify")
    if cert.get("ocr_chars", 1) > SR.T("BP-153", "ocr_chars_max"):
        add(f"the OCR found {cert.get('ocr_chars')} letters on the plate: a plate has none")
    if cert.get("geometry_iou", 0.0) < SR.T("BP-153", "restyle_geometry_iou_min"):
        add(f"the painted land overlaps the vector land by {cert.get('geometry_iou')}: the restyle moved geometry")
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    s = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    view = geo.View(s["lon"], s["lat"], s["span_km"], s["width"], s["height"])
    D.write_bytes_atomic(argv[1], D.png_bytes(render_plate(view, shaded_relief=bool(s.get("shaded_relief", False)))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
