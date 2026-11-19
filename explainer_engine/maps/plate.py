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
CLOSE_RELIEF_FADE = 0.25          # D-59 hypothesis: at upsample > 3x, fade raster relief down to ~25 %
MICRO_RELIEF_GAIN_CAP = 0.035     # D-59 hypothesis: cap micro-relief / hatch gain so plates never look noisy
MACRO_RELIEF_GAIN = 1.15          # D-59 hypothesis: sharp macro relief gain without harsh clipping noise
CLOSE_BLOB_STD_MAX = 1.2          # D-59 hypothesis: max 64 px Gaussian-blur luma std on a close-span paper plate


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


SCENE_MAP_GRADE_TINTS: dict[str, dict[str, tuple[tuple[int, int, int], float]]] = {
    "late_summer_1914": {
        "land": ((216, 198, 158), 0.28),
        "sea": ((88, 114, 132), 0.20),
        "lake": ((88, 114, 132), 0.20),
        "river": ((84, 108, 126), 0.20),
    },
    "flanders_winter_1914": {
        "land": ((184, 192, 198), 0.34),
        "sea": ((64, 84, 102), 0.28),
        "lake": ((64, 84, 102), 0.28),
        "river": ((70, 90, 108), 0.25),
    },
    "winter_dusk": {
        "land": ((156, 164, 176), 0.40),
        "sea": ((48, 64, 82), 0.35),
        "lake": ((48, 64, 82), 0.35),
        "river": ((56, 74, 94), 0.30),
    },
}


def resolve_scene_map_look(
    look: dict | None = None,
    *,
    scene: dict | None = None,
    shot: dict | None = None,
) -> dict:
    """Resolve a scene-matched map look directly in plate palette space (no generic post-filter).

    Matches the map plate's land/sea/parchment tones to the surrounding scene's season, time of day,
    and emotional tone while preserving explicit caller overrides in ``look``.
    """
    merged: dict = dict(look or {})
    sc = scene or {}
    sh = shot or {}
    text_blob = " ".join(
        str(x or "")
        for x in (
            sc.get("title"),
            sc.get("summary"),
            sc.get("time_of_day"),
            sc.get("atmosphere"),
            sh.get("shot_purpose"),
            (sh.get("director_brief") or {}).get("emotional_intent") if isinstance(sh.get("director_brief"), dict) else "",
            ((sh.get("map_action") or {}).get("date_badge") or {}).get("text") if isinstance((sh.get("map_action") or {}).get("date_badge"), dict) else (sh.get("map_action") or {}).get("date_badge"),
        )
    ).lower()

    profile_name = str(merged.get("scene_grade_profile") or "").strip()
    if not profile_name:
        if any(k in text_blob for k in ("august 1914", "summer", "mobilization", "strategic")):
            if "december" not in text_blob and "winter" not in text_blob and "flanders" not in text_blob:
                profile_name = "late_summer_1914"
        if not profile_name:
            if any(k in text_blob for k in ("dusk", "night", "twilight", "candle", "christmas eve")):
                profile_name = "winter_dusk"
            elif any(k in text_blob for k in ("december", "winter", "frost", "frozen", "flanders", "ypres", "trench", "mud")):
                profile_name = "flanders_winter_1914"
            else:
                profile_name = "flanders_winter_1914"

    merged["scene_grade_profile"] = profile_name
    return merged


def colours(
    look: dict | None = None,
    *,
    scene: dict | None = None,
    shot: dict | None = None,
) -> dict[str, tuple[int, int, int]]:
    """The plate's colours: palette blends, or the episode map look's palette tokens (``look[key]`` names a token),
    plus optional scene-matched palette grading directly in plate colour space (without a post-filter)."""
    eff_look = resolve_scene_map_look(look, scene=scene, shot=shot) if (scene is not None or shot is not None) else (look or {})
    paper, ink, blue, grey = D.rgb("paper"), D.rgb("ink"), D.rgb("support_blue"), D.rgb("grey_mid")
    base = {
        "sea": D.blend(blue, paper, STYLE["sea_mix"]),
        "land": D.blend(paper, D.rgb("kit_card"), 0.14),
        "coast": ink,
        "river": D.blend(blue, paper, 0.25),
        "border": D.blend(grey, ink, 0.25),
        "lake": D.blend(blue, paper, STYLE["sea_mix"]),
    }
    prof = str(eff_look.get("scene_grade_profile") or "").strip()
    if prof in SCENE_MAP_GRADE_TINTS:
        for k, (target_rgb, weight) in SCENE_MAP_GRADE_TINTS[prof].items():
            if k in base:
                base[k] = D.blend(base[k], target_rgb, weight)
    for k in LOOK_KEYS:
        if eff_look and eff_look.get(k):
            val = eff_look[k]
            if isinstance(val, (list, tuple)) and len(val) == 3:
                base[k] = (int(val[0]), int(val[1]), int(val[2]))
            else:
                base[k] = D.rgb(val)
    return base


def relief_upsample(view: geo.View, raster_km_per_px: float = MD.RASTER_KM_PER_PX) -> float:
    """How much the relief raster is enlarged in ``view`` (above 3x, deterministic micro-relief detail is added, V3)."""
    eff_km_per_px = view.span_km / 640.0
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
    u_micro = float(min(1.0, max(0.0, (upsample - MD.MICRO_RELIEF_UPSAMPLE_MIN) / 3.0)))
    # 1. Multi-octave Sobel hillshade extracted from the upsampled relief field
    s_fine = gaussian_filter(shade, sigma=1.5)
    gx = sobel(s_fine, axis=1)
    gy = sobel(s_fine, axis=0)
    slope = np.hypot(gx, gy)
    p90 = float(np.percentile(slope, 90))
    slope_weight = np.clip(0.50 + 0.50 * (slope / max(p90, 1e-4)), 0.50, 1.0).astype(np.float32)
    # 2. World-locked multi-octave topographic ridges + Sobel hillshade + parchment grain (S5 sample)
    # At close spans (upsample > 3x), a clean high-pass parchment weave + light procedural cartographic hatch
    # carries the paper texture without inventing coastlines, rivers, or low-frequency terrain blobs (D-59).
    h, w = shade.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    h_primary = np.sin(2.0 * np.pi * (xx + yy) / 4.0)
    h_cross = np.sin(2.0 * np.pi * (xx - yy) / 5.5)
    hatch = (0.70 * h_primary + 0.30 * h_cross).astype(np.float32) * 0.018 * slope_weight

    rng = D.seeded("micro_relief", round(view.lon, 4), round(view.lat, 4), round(view.span_km, 2), view.width, view.height)
    raw_grain = rng.standard_normal(shade.shape).astype(np.float32)
    paper_grain = (raw_grain - gaussian_filter(raw_grain, sigma=2.5)).astype(np.float32) * 0.012
    detail = (hatch + paper_grain) * (0.65 + 0.35 * u_micro)
    return np.clip(detail, -MICRO_RELIEF_GAIN_CAP, MICRO_RELIEF_GAIN_CAP).astype(np.float32)


def relief_rgb(view: geo.View, col: dict, look: dict | None = None, path=None) -> np.ndarray:
    """Land lit by the real relief, the sea flat (a hint of the raster's sea floor), seeded grain if the look asks for it."""
    from scipy.ndimage import gaussian_filter, sobel
    from explainer_engine.maps import relief
    look = look or {}
    shade = relief.sample(view, path)
    mask = land_mask(view, ss=1)
    k = float(look.get("relief_strength", 1.0))
    upsample = relief_upsample(view)
    if upsample > MD.MICRO_RELIEF_UPSAMPLE_MIN and not look.get("disable_micro_relief"):
        u_micro = float(min(1.0, (upsample - MD.MICRO_RELIEF_UPSAMPLE_MIN) / 3.0))
        fade = 1.0 - (1.0 - CLOSE_RELIEF_FADE) * u_micro
        land_vals = shade[mask] if mask.any() else shade
        local_mean = float(land_vals.mean())
        broad_sigma = max(4.0, min(view.width, view.height) * 0.04)
        shade_broad = gaussian_filter(shade, sigma=broad_sigma)
        ref = (1.0 - u_micro) * RELIEF_FLAT + u_micro * (0.80 * shade_broad + 0.20 * local_mean)
        base_gain = 1.0 + k * MACRO_RELIEF_GAIN * fade * ((shade - ref) / RELIEF_FLAT)
        detail = micro_relief_detail(shade, view, upsample)
        gain = np.clip(base_gain + (k * detail) * mask, 0.78, 1.06)[..., None]
    elif not look.get("disable_micro_relief"):
        s_macro = gaussian_filter(shade, sigma=max(0.8, view.width / 1280.0)) if view.width > 1280 else shade
        macro_hill = np.clip((sobel(s_macro, axis=1) - sobel(s_macro, axis=0)) * 0.18, -MICRO_RELIEF_GAIN_CAP * 0.5, MICRO_RELIEF_GAIN_CAP * 0.5)
        gain = np.clip(1.0 + k * MACRO_RELIEF_GAIN * (s_macro / RELIEF_FLAT - 1.0) + (k * macro_hill) * mask, 0.68, 1.12)[..., None]
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
