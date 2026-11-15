"""The letterless map plate: one per region, drawn from the Natural Earth vectors + optional real shaded relief, cached by the hash of its spec.

A plate is land, coast, lakes, rivers and borders in palette colours (with Natural Earth's shaded relief raster on the land when
`shaded_relief=True`, ``maps/relief.py``; v4.3 P4 removed the synthetic DEM with its hand-placed Toba and Waterloo terrain,
finding F6) and nothing else. When the episode's historical period is before 1945, ``borders_1914.json.gz`` is drawn instead of
modern borders; modern borders are never drawn for 1914 (M7). The colours can follow the episode's map look (``look``: palette
token names, EP-02). It has no letters (CMP-01): this module never calls ``Canvas.text`` and its spec has no text field, so the
guarantee holds by construction, and ``tests/unit/test_maps.py`` fails if the renderer ever draws one. Labels, units and arrows
are drawn over the plate by ``maps/render.py`` at the frame the viewer sees.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.maps import data as MD
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.standards import sourced_rules as SR

LAYERS = ("land", "lakes", "rivers", "borders")
STYLE = {"sea_mix": 0.55, "coast_px": 0.0022, "river_px": 0.0030, "border_px": 0.0016}  # strokes are shares of the frame height
LOOK_KEYS = ("sea", "land", "coast", "river", "border", "lake")
RELIEF_FLAT = 0.82   # Natural Earth SR_HR's grey on flat ground (measured on the Indian Ocean basin's plains, 2026-11-12)


def _extract_year(val) -> int | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, dict):
        for k in ("start_year", "end_year", "year", "period"):
            y = _extract_year(val.get(k))
            if y is not None:
                return y
        if isinstance(val.get("historical_period"), (dict, int, str)):
            return _extract_year(val.get("historical_period"))
        return None
    if isinstance(val, str):
        s = val.strip()
        if s == "borders_1914" or s == "1914":
            return 1914
        m = re.search(r"(-?\d{3,5})", s)
        if m:
            y = int(m.group(1))
            return -abs(y) if "bce" in s.lower() else y
    return None


def is_pre_1945(period=None, look: dict | None = None, layers=LAYERS) -> bool:
    """True when the episode's period is before 1945 (or ``borders_1914`` is requested), so 1914 borders replace modern borders."""
    if layers and "borders_1914" in layers:
        return True
    y = _extract_year(period)
    if y is None and isinstance(look, dict):
        if look.get("borders") in ("1914", "borders_1914"):
            return True
        y = _extract_year(look)
    return y is not None and y < 1945


def spec_hash(
    view: geo.View,
    layers=LAYERS,
    shaded_relief: bool = False,
    look: dict | None = None,
    period=None,
) -> str:
    """The cache key: the view, the layers, the style and the data it was drawn from."""
    sources = json.loads((Path(geo.__file__).with_name("data") / "SOURCES.json").read_text(encoding="utf-8"))
    body = {
        "view": [view.lon, view.lat, view.span_km, view.width, view.height],
        "layers": list(layers),
        "style": STYLE,
        "data": sources["output"]["sha256"],
    }
    if is_pre_1945(period, look, layers):
        body["borders_1914"] = (sources.get("borders_1914") or {}).get("sha256", "1914")
    if shaded_relief:
        from explainer_engine.maps import relief
        body["shaded_relief"] = relief.SOURCE_ZIP_SHA256
    if look:
        clean_look = {k: look[k] for k in sorted(look) if k not in ("period", "historical_period", "start_year", "end_year")}
        if clean_look:
            body["look"] = clean_look
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def colours(look: dict | None = None) -> dict[str, tuple[int, int, int]]:
    """The plate's colours: palette blends, or the episode map look's palette tokens (``look[key]`` names a token)."""
    paper, ink, blue, grey = D.rgb("paper"), D.rgb("ink"), D.rgb("support_blue"), D.rgb("grey_mid")
    base = {
        "sea": D.blend(blue, paper, STYLE["sea_mix"]),
        "land": D.blend(paper, D.rgb("kit_card"), 0.14),
        "coast": ink,
        "river": D.blend(blue, paper, 0.25),
        "border": D.blend(grey, ink, 0.25),
        "lake": D.blend(blue, paper, STYLE["sea_mix"]),
    }
    for k in LOOK_KEYS:
        if look and look.get(k):
            base[k] = D.rgb(look[k])
    return base


def relief_upsample(view: geo.View, raster_km_per_px: float = MD.RASTER_KM_PER_PX) -> float:
    """How much the relief raster is enlarged in ``view`` (above 3x, deterministic micro-relief detail is added, V3)."""
    eff_km_per_px = min(view.km_per_px, view.span_km / 640.0)
    return float(raster_km_per_px) / max(1e-6, eff_km_per_px)


def _world_octave(view: geo.View, step_deg: float, seed_salt: int) -> np.ndarray:
    """Sample a deterministic world-coordinate (lon/lat) terrain octave so relief ridges stay fixed on the ground (V3)."""
    from scipy.ndimage import gaussian_filter, map_coordinates
    h, w = int(view.height), int(view.width)
    xs = np.arange(w, dtype=np.float64) + 0.5
    ys = np.arange(h, dtype=np.float64) + 0.5
    lon, _ = view.to_lonlat(xs, np.zeros_like(xs))
    _, lat = view.to_lonlat(np.zeros_like(ys), ys)
    gx_coord = np.asarray(lon) / step_deg
    gy_coord = np.asarray(lat) / step_deg
    c0, c1 = int(np.floor(gx_coord.min())) - 3, int(np.ceil(gx_coord.max())) + 4
    r0, r1 = int(np.floor(gy_coord.min())) - 3, int(np.ceil(gy_coord.max())) + 4
    # Cap grid dimensions if step_deg is very fine on a wide view
    if (c1 - c0) > 512 or (r1 - r0) > 512:
        scale = max((c1 - c0) / 512.0, (r1 - r0) / 512.0)
        step_deg *= scale
        gx_coord = np.asarray(lon) / step_deg
        gy_coord = np.asarray(lat) / step_deg
        c0, c1 = int(np.floor(gx_coord.min())) - 3, int(np.ceil(gx_coord.max())) + 4
        r0, r1 = int(np.floor(gy_coord.min())) - 3, int(np.ceil(gy_coord.max())) + 4
    rr_idx, cc_idx = np.mgrid[r0:r1, c0:c1].astype(np.int64)
    # Fast deterministic integer hash -> float32 in [-1, 1]
    h_int = (rr_idx * 73856093) ^ (cc_idx * 19349663) ^ (seed_salt * 83492791)
    h_int = ((h_int >> 13) ^ h_int) * 1274126177
    grid = (((h_int ^ (h_int >> 16)) & 0x7FFFFFFF).astype(np.float32) / 1073741824.0) - 1.0
    grid = gaussian_filter(grid, sigma=1.35)
    ry, cx = np.meshgrid(gy_coord - r0, gx_coord - c0, indexing="ij")
    return map_coordinates(grid, [ry, cx], order=3, mode="nearest").astype(np.float32)


def micro_relief_detail(shade: np.ndarray, view: geo.View, upsample: float) -> np.ndarray:
    """Deterministic multi-octave Sobel hillshade from upsampled relief + parchment grain when upsample > 3x (V3)."""
    from scipy.ndimage import gaussian_filter, sobel
    u_micro = float(min(1.0, (upsample - MD.MICRO_RELIEF_UPSAMPLE_MIN) / 3.0))
    # 1. Multi-octave Sobel hillshade extracted from the upsampled relief field
    s_fine = gaussian_filter(shade, sigma=1.2)
    s_med = gaussian_filter(shade, sigma=3.5)
    s_broad = gaussian_filter(shade, sigma=8.0)
    scale_boost = min(22.0, upsample * 0.90)
    dem_gx = (0.50 * sobel(s_fine, axis=1) + 0.35 * sobel(s_med, axis=1) + 0.15 * sobel(s_broad, axis=1)) * scale_boost
    dem_gy = (0.50 * sobel(s_fine, axis=0) + 0.35 * sobel(s_med, axis=0) + 0.15 * sobel(s_broad, axis=0)) * scale_boost
    dem_hill = np.clip((dem_gx * 0.7071 - dem_gy * 0.7071), -0.12, 0.12)
    # 2. World-locked multi-octave topographic ridges + Sobel hillshade + parchment grain (S5 sample)
    oct_broad = _world_octave(view, 0.055, 191401)
    oct_meso = _world_octave(view, 0.018, 191402)
    oct_fine = _world_octave(view, 0.006, 191403)

    def _norm_hill(field: np.ndarray) -> np.ndarray:
        gx = sobel(field, axis=1)
        gy = sobel(field, axis=0)
        hs = gx * 0.7071 - gy * 0.7071
        std = float(hs.std())
        return hs / max(std, 1e-5)

    h_broad = _norm_hill(oct_broad)
    h_meso = _norm_hill(oct_meso)
    h_fine = _norm_hill(oct_fine)
    micro_hill = np.clip((0.52 * h_broad + 0.32 * h_meso + 0.16 * h_fine) * 0.095, -0.20, 0.18)

    rng = D.seeded("micro_relief", round(view.lon, 4), round(view.lat, 4), round(view.span_km, 2), view.width, view.height)
    paper_grain = rng.standard_normal(shade.shape).astype(np.float32) * 0.016
    return ((dem_hill + micro_hill + paper_grain) * (0.55 + 0.45 * u_micro)).astype(np.float32)


def relief_rgb(view: geo.View, col: dict, look: dict | None = None, path=None) -> np.ndarray:
    """Land lit by the real relief, the sea flat (a hint of the raster's sea floor), seeded grain if the look asks for it."""
    from explainer_engine.maps import relief
    look = look or {}
    shade = relief.sample(view, path)
    mask = land_mask(view, ss=1)
    k = float(look.get("relief_strength", 1.0))
    upsample = relief_upsample(view)
    if upsample > MD.MICRO_RELIEF_UPSAMPLE_MIN and not look.get("disable_micro_relief"):
        u_micro = float(min(1.0, (upsample - MD.MICRO_RELIEF_UPSAMPLE_MIN) / 3.0))
        land_vals = shade[mask] if mask.any() else shade
        local_mean = float(land_vals.mean())
        shade_adj = shade - u_micro * 0.85 * (local_mean - RELIEF_FLAT)
        base_gain = (1.0 - 0.08 * u_micro) + k * 1.35 * (shade_adj / RELIEF_FLAT - 1.0)
        detail = micro_relief_detail(shade, view, upsample)
        gain = np.clip(base_gain + (k * detail) * mask, 0.50, 1.06)[..., None]
    else:
        gain = np.clip(1.0 + k * 1.6 * (shade / RELIEF_FLAT - 1.0), 0.45, 1.3)[..., None]
    land = np.asarray(col["land"], np.float32) * gain
    sea = np.asarray(col["sea"], np.float32) * (0.97 + 0.03 * shade)[..., None]
    out = np.where(mask[..., None], land, sea)
    grain = float(look.get("grain", 0.0))
    if grain > 0:
        rng = D.seeded("grain", view.lon, view.lat, view.span_km, view.width, view.height)
        out = out * (1.0 + grain * rng.standard_normal(out.shape[:2]).astype(np.float32))[..., None]
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def draw_base(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
    look: dict | None = None,
    period=None,
) -> D.Canvas:
    """Land, lakes, rivers and borders over the sea (land lit by the real relief when `shaded_relief=True`), as a supersampled
    canvas (no letters). When the episode's period is before 1945, ``borders_1914`` replaces modern borders."""
    ds, col = geo.dataset(), colours(look)
    c = D.Canvas(view.width, view.height, col["sea"], ss)
    lon0, lat0, lon1, lat1 = view.bbox(0.02)
    box = (lon0, lat0, lon1, lat1)
    rect = (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    unit = view.height

    if shaded_relief:
        big = geo.View(view.lon, view.lat, view.span_km, view.width * ss, view.height * ss)
        c.replace(Image.fromarray(relief_rgb(big, col, look), mode="RGB").convert("RGBA"))

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
    use_1914 = is_pre_1945(period, look, layers)
    border_lines = geo.borders_1914() if use_1914 else ds["borders"]
    has_borders = ("borders" in layers) or ("borders_1914" in layers)
    if has_borders:
        border_w = (
            min(MD.BORDER_1914_MAX_PX_1080, max(1.0, STYLE["border_px"] * min(unit, 1080) * 0.85))
            if use_1914
            else max(1.0, STYLE["border_px"] * unit)
        )
        border_dash = (MD.BORDER_1914_DASH_ON, MD.BORDER_1914_DASH_OFF) if use_1914 else (6.0, 4.0)
        for line in border_lines:
            if not geo._hit(line.bbox, box):
                continue
            x, y = view.to_px(line.pts[:, 0], line.pts[:, 1])
            for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                c.line(piece, (*col["border"], 255), border_w, dash=border_dash)
    if "rivers" in layers:
        river_w = min(2.5, max(1.0, STYLE["river_px"] * min(unit, 1080))) if use_1914 else max(1.0, STYLE["river_px"] * unit)
        for line in ds["rivers"]:
            if not geo._hit(line.bbox, box):
                continue
            x, y = view.to_px(line.pts[:, 0], line.pts[:, 1])
            for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                c.line(piece, (*col["river"], 255), river_w, dash=None)
    return c


def render_plate(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
    look: dict | None = None,
    period=None,
) -> Image.Image:
    return draw_base(view, layers, ss, shaded_relief=shaded_relief, cache_dir=cache_dir, look=look, period=period).image().convert("RGB")


def plate_path(
    view: geo.View,
    directory: Path | str,
    layers=LAYERS,
    shaded_relief: bool = False,
    look: dict | None = None,
    period=None,
) -> Path:
    prefix = "relief-plate" if shaded_relief else "plate"
    return Path(directory) / f"{prefix}-{spec_hash(view, layers, shaded_relief=shaded_relief, look=look, period=period)[:16]}.png"


def save_plate(
    view: geo.View,
    directory: Path | str,
    layers=LAYERS,
    shaded_relief: bool = False,
    look: dict | None = None,
    period=None,
) -> Path:
    """The plate in the cache folder; a hit is not drawn again (the file name is the hash of what it shows)."""
    path = plate_path(view, directory, layers, shaded_relief=shaded_relief, look=look, period=period)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        D.write_bytes_atomic(path, D.png_bytes(render_plate(view, layers, shaded_relief=shaded_relief, cache_dir=directory, look=look, period=period)))
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
    period = s.get("period") or s.get("historical_period") or s.get("start_year")
    D.write_bytes_atomic(argv[1], D.png_bytes(render_plate(view, shaded_relief=bool(s.get("shaded_relief", False)), period=period)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
