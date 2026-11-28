"""GeoLayers-Grade MapLibre GL JS WebGL2 Broadcast Documentary Map Renderer.

Upgrades historical/paleo cartography from flat PIL rectangles to GPU-accelerated
MapLibre GL JS v5 WebGL2 + Natural Earth High-Res Shaded Relief + Vector Coastlines/Rivers
+ Pleistocene Ice Sheet GeoJSON Overlays + Turf.js Smooth Migration Arcs + Broadcast
Typography (Cinzel / Plus Jakarta Sans / IBM Plex Mono) + Compass & Animated Scale Bar.

Renders 100% offline in Playwright Headless Chrome WebGL2 at 2560x1440 @ 24fps.
"""
from __future__ import annotations

import base64
import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from explainer_engine.design_system.tokens import (
    PALEO_ICE_AGE_THEME,
    build_font_face_css,
    resolve_vendor_js,
)

ROOT = Path(__file__).resolve().parents[2]
NE_GEOJSON_DIR = ROOT / "assets" / "maps" / "ne_10m_geojson"
RELIEF_TIF = ROOT / "assets" / "maps" / "relief" / "NE1_HR_LC_SR_W.tif"


@dataclass(slots=True)
class WebGLMapSpec:
    map_id: str
    title: str
    subtitle: str
    duration_s: float
    # Viewport interest bounding box [west, south, east, north] for land_ratio metric
    relief_bounds: tuple[float, float, float, float]
    start_camera: dict[str, float]  # center_lon, center_lat, zoom, pitch, bearing
    end_camera: dict[str, float]
    routes: list[dict[str, Any]] = field(default_factory=list)
    markers: list[dict[str, Any]] = field(default_factory=list)
    sea_and_region_labels: list[dict[str, Any]] = field(default_factory=list)
    ice_sheet_polygons: list[list[list[float]]] = field(default_factory=list)
    paleo_land_polygons: list[list[list[float]]] = field(default_factory=list)
    palette: str = "paleo_ice_age_slate"
    era_badge: str = "70,000 - 15,000 BCE"
    lock_horizon: bool = True
    telemetry_subtitle: str = "PLEISTOCENE LGM RELIEF"
    city_layers: dict[str, Any] | None = None


WORLD_RELIEF_CACHE = ROOT / "assets" / "maps" / "relief" / "paleo_mercator_world_v2.png"
MERCATOR_MAX_LAT = 82.0


def _chaikin_smooth_ring(ring: list[list[float]], iterations: int = 3) -> list[list[float]]:
    """Smooth a closed polygon ring into organic natural coastlines/glacial lobes."""
    pts = [list(p) for p in ring]
    if len(pts) < 4:
        return pts
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    for _ in range(iterations):
        nxt: list[list[float]] = []
        n = len(pts)
        for i in range(n):
            p0 = pts[i]
            p1 = pts[(i + 1) % n]
            nxt.append([0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1]])
            nxt.append([0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1]])
        pts = nxt
    pts.append(pts[0])
    return pts


def _shift_coords(coords: Any, delta_lon: float) -> Any:
    if not coords:
        return coords
    if isinstance(coords[0], (int, float)):
        return [float(coords[0]) + delta_lon, float(coords[1])]
    return [_shift_coords(c, delta_lon) for c in coords]


def _grade_relief_plate_paleo(
    bounds: tuple[float, float, float, float],
    out_png: Path,
    *,
    max_dim: int = 3200,
) -> tuple[Path, float]:
    """Reproject full-globe Natural Earth 1:10m shaded relief to exact Web Mercator (EPSG:3857)
    with directional 3D mountain hillshade & bathymetry, eliminating cropped edges & latitude drift."""
    west, south, east, north = bounds
    out_png.parent.mkdir(parents=True, exist_ok=True)

    # Always compute exact land_ratio within requested viewport bounds
    import rasterio
    from rasterio.windows import from_bounds

    with rasterio.open(RELIEF_TIF) as src:
        w_clamped = max(-180.0, min(179.0, west))
        e_clamped = max(w_clamped + 1.0, min(180.0, east))
        s_clamped = max(-85.0, min(84.0, south))
        n_clamped = max(s_clamped + 1.0, min(85.0, north))
        win = from_bounds(w_clamped, s_clamped, e_clamped, n_clamped, src.transform)
        sample_arr = src.read([1, 2, 3], window=win, out_shape=(3, 256, 256))
        s_rgb = np.transpose(sample_arr, (1, 2, 0)).astype(np.float32)
        s_ocean = (s_rgb[..., 2] > s_rgb[..., 0] + 10.0) & (s_rgb[..., 2] >= s_rgb[..., 1] - 3.0)
        land_ratio = float(1.0 - np.mean(s_ocean))

        if WORLD_RELIEF_CACHE.is_file():
            return WORLD_RELIEF_CACHE, land_ratio

        # Read full globe at crisp working resolution (3200x1600 equirectangular)
        src_w = max_dim
        src_h = max_dim // 2
        full_arr = src.read([1, 2, 3], out_shape=(3, src_h, src_w))
        eq_rgb = np.transpose(full_arr, (1, 2, 0)).astype(np.float32)

    # Reproject Equirectangular [-180..180, -90..90] -> Web Mercator [-180..180, -82..82]
    out_w = max_dim
    out_h = int(round(max_dim * 0.78))
    y_max = math.log(math.tan(math.pi / 4.0 + math.radians(MERCATOR_MAX_LAT) / 2.0))
    y_merc = np.linspace(y_max, -y_max, out_h, dtype=np.float32)
    lats = np.degrees(2.0 * np.arctan(np.exp(y_merc)) - math.pi / 2.0)
    src_y = ((90.0 - lats) / 180.0) * (src_h - 1)
    src_x = np.linspace(0.0, src_w - 1.0, out_w, dtype=np.float32)
    map_x, map_y = np.meshgrid(src_x, src_y)
    rgb = cv2.remap(eq_rgb, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    # Water vs land mask from Natural Earth LC_SR_W
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ocean_raw = ((b > r + 10.0) & (b >= g - 3.0)).astype(np.float32)
    ocean_mask = cv2.GaussianBlur(ocean_raw, (5, 5), 1.0)

    # Rich topographic shaded relief + Scharr directional 3D hillshade
    luma = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    luma_u8 = np.clip(luma * 255.0, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(16, 16))
    luma_enh = clahe.apply(luma_u8).astype(np.float32) / 255.0
    gx = cv2.Scharr(luma_enh, cv2.CV_32F, 1, 0) / 32.0
    gy = cv2.Scharr(luma_enh, cv2.CV_32F, 0, 1) / 32.0
    hillshade = np.clip(0.55 + (-gx * 1.8 - gy * 1.4), 0.12, 1.35)

    # Deep moody abyssal ocean with brighter continental shelf bathymetry
    shelf = np.clip((luma - 0.52) * 2.4, 0.0, 1.0)
    ocean_r = 7.0 + 18.0 * (luma**1.4) + 14.0 * shelf
    ocean_g = 19.0 + 36.0 * (luma**1.3) + 28.0 * shelf
    ocean_b = 34.0 + 52.0 * (luma**1.2) + 34.0 * shelf

    # Sculpted slate-stone land with crisp dark valleys & warm sunlit mountain ridges
    relief = np.clip((luma_enh - 0.20) * 1.35, 0.0, 1.0)
    land_r = (26.0 + 92.0 * (relief**1.12)) * (0.68 + 0.44 * hillshade)
    land_g = (35.0 + 96.0 * (relief**1.08)) * (0.68 + 0.44 * hillshade)
    land_b = (44.0 + 100.0 * (relief**1.04)) * (0.68 + 0.42 * hillshade)

    # Warm highland amber-stone accent on major mountain chains (Alps, Caucasus, Himalayas, Rockies)
    ridge = np.clip((relief * hillshade - 0.58) / 0.42, 0.0, 1.0)
    land_r += 34.0 * ridge
    land_g += 24.0 * ridge
    land_b += 12.0 * ridge

    out = np.zeros_like(rgb)
    out[..., 0] = ocean_mask * ocean_r + (1.0 - ocean_mask) * land_r
    out[..., 1] = ocean_mask * ocean_g + (1.0 - ocean_mask) * land_g
    out[..., 2] = ocean_mask * ocean_b + (1.0 - ocean_mask) * land_b

    bgr = cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    WORLD_RELIEF_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(WORLD_RELIEF_CACHE), bgr)
    return WORLD_RELIEF_CACHE, land_ratio


def _geom_intersects_bbox(coords: Any, w: float, s: float, e: float, n: float) -> bool:
    if not coords:
        return False
    if isinstance(coords[0], (int, float)):
        lon, lat = float(coords[0]), float(coords[1])
        return (w <= lon <= e) and (s <= lat <= n)
    return any(_geom_intersects_bbox(c, w, s, e, n) for c in coords)


def _load_geojson_world(
    filename: str,
    *,
    include_east_wrap: bool = True,
    clip_bounds: tuple[float, float, float, float] | None = None,
    pad_deg: float = 38.0,
) -> dict[str, Any]:
    """Load Natural Earth vector GeoJSON (plus optional +360° wrap), clipped to viewport + margin for fast WebGL2 MSAA."""
    p = NE_GEOJSON_DIR / filename
    if not p.is_file():
        return {"type": "FeatureCollection", "features": []}
    raw = json.loads(p.read_text(encoding="utf-8"))
    feats = list(raw.get("features", []))
    if include_east_wrap:
        wrapped = []
        for f in feats:
            geom = f.get("geometry")
            if not geom or not geom.get("coordinates"):
                continue
            wrapped.append(
                {
                    "type": "Feature",
                    "properties": f.get("properties", {}),
                    "geometry": {
                        "type": geom["type"],
                        "coordinates": _shift_coords(geom["coordinates"], 360.0),
                    },
                }
            )
        feats.extend(wrapped)
    if clip_bounds is not None:
        bw, bs, be, bn = clip_bounds
        cw, cs, ce, cn = bw - pad_deg, max(-85.0, bs - pad_deg), be + pad_deg, min(85.0, bn + pad_deg)
        feats = [
            f
            for f in feats
            if f.get("geometry") and _geom_intersects_bbox(f["geometry"].get("coordinates"), cw, cs, ce, cn)
        ]
    return {"type": "FeatureCollection", "features": feats}


def _build_maplibre_html(
    spec: WebGLMapSpec,
    relief_png: Path,
    *,
    width: int,
    height: int,
) -> str:
    theme = dict(PALEO_ICE_AGE_THEME)
    font_css = build_font_face_css(["Cinzel", "Cormorant Garamond", "Plus Jakarta Sans", "IBM Plex Mono"])
    ml_js_uri = resolve_vendor_js("maplibre-gl.js").as_uri()
    ml_css_uri = resolve_vendor_js("maplibre-gl.css").as_uri()
    turf_uri = resolve_vendor_js("turf.min.js").as_uri()

    is_city_mode = bool(spec.city_layers)
    is_roman_palette = spec.palette == "ancient_rome_parchment"
    city_layers = dict(spec.city_layers or {})

    west, south, east, north = spec.relief_bounds
    if is_city_mode:
        relief_uri = ""
        coast_geo = {"type": "FeatureCollection", "features": []}
        rivers_geo = {"type": "FeatureCollection", "features": []}
        grat_geo = {"type": "FeatureCollection", "features": []}
    else:
        _rel_bgr = cv2.imread(str(relief_png))
        assert _rel_bgr is not None, f"Could not read graded world relief plate: {relief_png}"
        _ok, _jpg_buf = cv2.imencode(".jpg", _rel_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        assert _ok
        relief_uri = "data:image/jpeg;base64," + base64.b64encode(_jpg_buf.tobytes()).decode("ascii")
        coast_geo = _load_geojson_world("ne_50m_coastline.geojson", include_east_wrap=True, clip_bounds=spec.relief_bounds)
        rivers_geo = _load_geojson_world(
            "ne_50m_rivers_lake_centerlines.geojson", include_east_wrap=True, clip_bounds=spec.relief_bounds
        )
        grat_geo = _load_geojson_world("ne_50m_graticules_15.geojson", include_east_wrap=True, clip_bounds=spec.relief_bounds)

    glacier_geo: dict[str, Any] = {"type": "FeatureCollection", "features": []}

    # Smooth organic Pleistocene Last Glacial Maximum ice sheet polygons
    for idx, poly in enumerate(spec.ice_sheet_polygons):
        smooth_ring = _chaikin_smooth_ring(poly, iterations=3)
        glacier_geo["features"].append(
            {
                "type": "Feature",
                "properties": {"name": f"LGM_ICE_{idx}", "lgm": True},
                "geometry": {"type": "Polygon", "coordinates": [smooth_ring]},
            }
        )

    # Optional exposed -120m paleo-landmass polygons (e.g. Bering Land Bridge connecting Siberia to Alaska)
    paleo_geo: dict[str, Any] = {"type": "FeatureCollection", "features": []}
    for idx, poly in enumerate(spec.paleo_land_polygons):
        smooth_ring = _chaikin_smooth_ring(poly, iterations=3)
        paleo_geo["features"].append(
            {
                "type": "Feature",
                "properties": {"name": f"PALEO_LAND_{idx}"},
                "geometry": {"type": "Polygon", "coordinates": [smooth_ring]},
            }
        )

    scale = height / 1080.0
    spec_payload = {
        "duration_s": spec.duration_s,
        "start_camera": spec.start_camera,
        "end_camera": spec.end_camera,
        "routes": spec.routes,
        "markers": spec.markers,
        "labels": spec.sea_and_region_labels,
        "bounds": [west, south, east, north],
        "lock_horizon": bool(spec.lock_horizon),
        "is_city_mode": is_city_mode,
        "is_roman_palette": is_roman_palette,
    }

    bg_color = "#1B1612" if is_roman_palette else "#09131E"
    accent_bar_color = "#D89A46" if is_roman_palette else theme["accent_amber"]
    scale_bar_color = "#D89A46" if is_roman_palette else theme["accent_glacial"]
    coord_color = "#E8C68E" if is_roman_palette else "#9ED6F2"
    telemetry_sub = spec.telemetry_subtitle or "PLEISTOCENE LGM RELIEF"

    city_water_geo = city_layers.get("water_geo") or {"type": "FeatureCollection", "features": []}
    city_hills_geo = city_layers.get("hills_geo") or {"type": "FeatureCollection", "features": []}
    city_districts_geo = city_layers.get("districts_geo") or {"type": "FeatureCollection", "features": []}
    city_roads_geo = city_layers.get("roads_geo") or {"type": "FeatureCollection", "features": []}
    city_monuments_geo = city_layers.get("monuments_geo") or {"type": "FeatureCollection", "features": []}
    city_walls_geo = city_layers.get("walls_geo") or {"type": "FeatureCollection", "features": []}

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet" href="{ml_css_uri}" />
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: {width}px; height: {height}px; overflow: hidden; background: {bg_color};
  font-family: {theme["font_sans"]}; color: {theme["text_primary"]};
  -webkit-font-smoothing: antialiased;
}}
#map {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
#overlay-canvas {{ position: absolute; inset: 0; width: {width}px; height: {height}px; pointer-events: none; z-index: 5; }}
#hud-layer {{
  position: absolute; top: 0; left: 0; width: 1920px; height: 1080px;
  transform: scale({scale:.6f}); transform-origin: top left;
  pointer-events: none; z-index: 10;
}}
.vignette {{
  position: absolute; inset: 0; pointer-events: none; z-index: 8;
  background: radial-gradient(ellipse 84% 78% at 50% 50%, rgba(0,0,0,0) 56%, rgba(8,6,4,0.62) 100%);
}}
.hud-title-card {{
  position: absolute; top: 44px; left: 54px; max-width: 680px;
  padding: 16px 26px 18px;
  background: linear-gradient(155deg, rgba(16,12,9,0.90) 0%, rgba(10,8,6,0.94) 100%);
  border-left: 3px solid {accent_bar_color};
  border-top: 1px solid rgba(232,220,200,0.18);
  border-right: 1px solid rgba(232,220,200,0.12);
  border-bottom: 1px solid rgba(232,220,200,0.12);
  border-radius: 4px;
  box-shadow: 0 18px 44px rgba(0,0,0,0.55);
}}
.hud-era {{
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; letter-spacing: 0.22em;
  color: {accent_bar_color}; text-transform: uppercase; margin-bottom: 6px;
}}
.hud-h1 {{
  font-family: {theme["font_display"]}; font-size: 34px; font-weight: 600;
  letter-spacing: 0.08em; color: #F7F4EE; line-height: 1.14;
}}
.hud-sub {{
  font-family: {theme["font_sans"]}; font-size: 19px; font-weight: 500; color: #E8E1D5;
  margin-top: 7px; letter-spacing: 0.02em; word-spacing: 0.08em; line-height: 1.3;
}}
.hud-telemetry {{
  position: absolute; top: 44px; right: 54px; display: flex; align-items: center; gap: 16px;
  padding: 12px 20px; background: rgba(14,11,8,0.88);
  border: 1px solid rgba(232,220,200,0.18); border-radius: 4px;
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; color: {coord_color};
  font-variant-numeric: tabular-nums;
}}
.compass-svg {{ width: 40px; height: 40px; flex-shrink: 0; }}
.hud-scale {{
  position: absolute; bottom: 44px; right: 54px;
  padding: 10px 18px; background: rgba(14,11,8,0.82);
  border: 1px solid rgba(232,220,200,0.18); border-radius: 4px;
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; color: #EAE3D7;
  font-variant-numeric: tabular-nums;
  display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
}}
.scale-bar-line {{
  width: 140px; height: 6px; border-left: 2px solid {scale_bar_color};
  border-right: 2px solid {scale_bar_color};
  border-bottom: 2px solid {scale_bar_color};
}}
.maplibregl-ctrl {{ display: none !important; }}
</style>
</head>
<body>
<div id="map"></div>
<canvas id="overlay-canvas"></canvas>
<div class="vignette"></div>
<div id="hud-layer">
  <div class="hud-title-card" id="map-title-bbox">
    <div class="hud-era">{spec.era_badge}</div>
    <div class="hud-h1">{spec.title}</div>
    <div class="hud-sub">{spec.subtitle}</div>
  </div>
  <div class="hud-telemetry">
    <svg class="compass-svg" viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="20" stroke="rgba(216,154,70,0.45)" stroke-width="1.5"/>
      <polygon points="24,6 28,24 24,20 20,24" fill="{accent_bar_color}"/>
      <polygon points="24,42 28,24 24,28 20,24" fill="rgba(232,240,248,0.52)"/>
      <text x="24" y="5" fill="#F5F7FA" font-size="9" font-weight="700" font-family="IBM Plex Mono" text-anchor="middle">N</text>
    </svg>
    <div>
      <div id="coord-readout">41.89° N  /  12.48° E</div>
      <div style="font-size:12px;color:#C8BFA8;margin-top:3px;letter-spacing:0.12em;">{telemetry_sub}</div>
    </div>
  </div>
  <div class="hud-scale">
    <div id="scale-label">250 M</div>
    <div class="scale-bar-line"></div>
  </div>
</div>

<script src="{ml_js_uri}"></script>
<script src="{turf_uri}"></script>
<script>
const SPEC = {json.dumps(spec_payload)};
const COAST_GEO = {json.dumps(coast_geo)};
const RIVERS_GEO = {json.dumps(rivers_geo)};
const GRAT_GEO = {json.dumps(grat_geo)};
const GLACIER_GEO = {json.dumps(glacier_geo)};
const PALEO_GEO = {json.dumps(paleo_geo)};
const CITY_WATER_GEO = {json.dumps(city_water_geo)};
const CITY_HILLS_GEO = {json.dumps(city_hills_geo)};
const CITY_DISTRICTS_GEO = {json.dumps(city_districts_geo)};
const CITY_ROADS_GEO = {json.dumps(city_roads_geo)};
const CITY_MONUMENTS_GEO = {json.dumps(city_monuments_geo)};
const CITY_WALLS_GEO = {json.dumps(city_walls_geo)};
const W = {width}, H = {height};
const SCALE = H / 1080.0;
const DPR = Math.max(2, window.devicePixelRatio || 2);

const styleObj = SPEC.is_city_mode ? {{
  version: 8,
  light: {{
    anchor: "map",
    color: "#FFEBD0",
    intensity: 0.42,
    position: [1.3, 135, 38]
  }},
  sources: {{
    city_hills: {{ type: "geojson", data: CITY_HILLS_GEO }},
    city_districts: {{ type: "geojson", data: CITY_DISTRICTS_GEO }},
    city_water: {{ type: "geojson", data: CITY_WATER_GEO }},
    city_roads: {{ type: "geojson", data: CITY_ROADS_GEO }},
    city_walls: {{ type: "geojson", data: CITY_WALLS_GEO }},
    city_monuments: {{ type: "geojson", data: CITY_MONUMENTS_GEO }}
  }},
  layers: [
    {{ id: "bg", type: "background", paint: {{ "background-color": "#1E1914" }} }},
    {{ id: "city-hills-fill", type: "fill", source: "city_hills", paint: {{ "fill-color": ["coalesce", ["get", "fill"], "#2C241B"], "fill-opacity": 0.92 }} }},
    {{ id: "city-hills-rim", type: "line", source: "city_hills", paint: {{ "line-color": "#5E4E3B", "line-width": 1.6, "line-blur": 0.8, "line-opacity": 0.65 }} }},
    {{ id: "city-districts-fill", type: "fill", source: "city_districts", paint: {{ "fill-color": ["coalesce", ["get", "fill"], "#2A231B"], "fill-opacity": 0.85 }} }},
    {{ id: "city-districts-rim", type: "line", source: "city_districts", paint: {{ "line-color": "#6A5A45", "line-width": 1.4, "line-opacity": 0.45 }} }},
    {{ id: "city-water-glow", type: "line", source: "city_water", paint: {{ "line-color": "#5F98B8", "line-width": 9.0, "line-blur": 6.0, "line-opacity": 0.28 }} }},
    {{ id: "city-water-fill", type: "fill", source: "city_water", paint: {{ "fill-color": "#1A374A", "fill-opacity": 0.96 }} }},
    {{ id: "city-water-rim", type: "line", source: "city_water", paint: {{ "line-color": "#74A8C4", "line-width": 2.0, "line-blur": 0.6, "line-opacity": 0.72 }} }},
    {{ id: "city-roads-casing", type: "line", source: "city_roads", paint: {{ "line-color": "#120F0C", "line-width": ["coalesce", ["get", "casing_w"], 6.0], "line-opacity": 0.72 }}, layout: {{ "line-cap": "round", "line-join": "round" }} }},
    {{ id: "city-roads-fill", type: "line", source: "city_roads", paint: {{ "line-color": ["coalesce", ["get", "color"], "#8F7C63"], "line-width": ["coalesce", ["get", "width"], 3.0], "line-opacity": 0.88 }}, layout: {{ "line-cap": "round", "line-join": "round" }} }},
    {{ id: "city-walls-line", type: "line", source: "city_walls", paint: {{ "line-color": "#A38A68", "line-width": 3.4, "line-opacity": 0.70 }}, layout: {{ "line-cap": "round", "line-join": "round" }} }},
    {{ id: "city-monuments-shadow", type: "fill", source: "city_monuments", paint: {{ "fill-color": "#0A0806", "fill-opacity": 0.55 }} }},
    {{
      id: "city-monuments-3d",
      type: "fill-extrusion",
      source: "city_monuments",
      paint: {{
        "fill-extrusion-color": ["coalesce", ["get", "color"], "#D5C3A3"],
        "fill-extrusion-height": ["coalesce", ["get", "height"], 18],
        "fill-extrusion-base": 0,
        "fill-extrusion-opacity": 0.94
      }}
    }}
  ]
}} : {{
  version: 8,
  sources: {{
    relief_main: {{
      type: "image",
      url: "{relief_uri}",
      coordinates: [
        [-180, {MERCATOR_MAX_LAT}],
        [180, {MERCATOR_MAX_LAT}],
        [180, {-MERCATOR_MAX_LAT}],
        [-180, {-MERCATOR_MAX_LAT}]
      ]
    }},
    relief_east: {{
      type: "image",
      url: "{relief_uri}",
      coordinates: [
        [180, {MERCATOR_MAX_LAT}],
        [540, {MERCATOR_MAX_LAT}],
        [540, {-MERCATOR_MAX_LAT}],
        [180, {-MERCATOR_MAX_LAT}]
      ]
    }},
    graticules: {{ type: "geojson", data: GRAT_GEO }},
    paleo_land: {{ type: "geojson", data: PALEO_GEO }},
    glaciers: {{ type: "geojson", data: GLACIER_GEO }},
    rivers: {{ type: "geojson", data: RIVERS_GEO }},
    coastline: {{ type: "geojson", data: COAST_GEO }}
  }},
  layers: [
    {{ id: "bg", type: "background", paint: {{ "background-color": "#0A1726" }} }},
    {{ id: "relief-main-layer", type: "raster", source: "relief_main", paint: {{ "raster-opacity": 1.0, "raster-resampling": "linear" }} }},
    {{ id: "relief-east-layer", type: "raster", source: "relief_east", paint: {{ "raster-opacity": 1.0, "raster-resampling": "linear" }} }},
    {{ id: "paleo-land-fill", type: "fill", source: "paleo_land", paint: {{ "fill-color": "#4A5A63", "fill-opacity": 0.84 }} }},
    {{ id: "paleo-land-rim", type: "line", source: "paleo_land", paint: {{ "line-color": "#D4A362", "line-width": 2.4, "line-blur": 0.7, "line-opacity": 0.78 }} }},
    {{ id: "grat-layer", type: "line", source: "graticules", paint: {{ "line-color": "rgba(160,198,224,0.08)", "line-width": 1.8, "line-blur": 0.9 }} }},
    {{ id: "glacier-glow", type: "line", source: "glaciers", paint: {{ "line-color": "#BCE4FA", "line-width": 12.0, "line-opacity": 0.24, "line-blur": 9.0 }} }},
    {{ id: "glacier-fill", type: "fill", source: "glaciers", paint: {{ "fill-color": "#D4EEFC", "fill-opacity": 0.30 }} }},
    {{ id: "glacier-rim", type: "line", source: "glaciers", paint: {{ "line-color": "#9CD2F0", "line-width": 2.4, "line-blur": 0.8, "line-opacity": 0.68 }} }},
    {{ id: "rivers-layer", type: "line", source: "rivers", paint: {{ "line-color": "#589BC2", "line-width": 2.0, "line-blur": 0.65, "line-opacity": 0.54 }} }},
    {{ id: "coast-glow", type: "line", source: "coastline", paint: {{ "line-color": "#7CC4E8", "line-width": 4.4, "line-opacity": 0.20, "line-blur": 3.2 }} }},
    {{ id: "coast-line", type: "line", source: "coastline", paint: {{ "line-color": "#A2CBE0", "line-width": 2.1, "line-blur": 0.6, "line-opacity": 0.80 }} }}
  ]
}};

const map = new maplibregl.Map({{
  container: "map",
  style: styleObj,
  center: [SPEC.start_camera.center_lon, SPEC.start_camera.center_lat],
  zoom: SPEC.start_camera.zoom,
  pitch: SPEC.start_camera.pitch || 24,
  bearing: SPEC.start_camera.bearing || 0,
  antialias: true,
  pixelRatio: DPR,
  renderWorldCopies: !SPEC.is_city_mode,
  interactive: false,
  attributionControl: false,
  preserveDrawingBuffer: true,
  fadeDuration: 0
}});

window.__mapReady = false;
map.on("load", () => {{ window.__mapReady = true; }});

// Pre-build smooth Turf bezier curves for every route
const builtRoutes = (SPEC.routes || []).map((r) => {{
  const line = turf.lineString(r.coords);
  const curved = r.coords.length >= 3 ? turf.bezierSpline(line, {{ resolution: 6000, sharpness: 0.75 }}) : line;
  const totalKm = turf.length(curved, {{ units: "kilometers" }});
  const pts = [];
  const N = 220;
  for (let i = 0; i <= N; i++) {{
    const pt = turf.along(curved, (totalKm * i) / N, {{ units: "kilometers" }});
    pts.push(pt.geometry.coordinates);
  }}
  return {{ ...r, pts }};
}});

// Quintic smootherstep: zero velocity AND zero acceleration at endpoints -> silk-smooth motion
function smootherstep(x) {{
  const u = Math.max(0, Math.min(1, x));
  return u * u * u * (u * (u * 6 - 15) + 10);
}}

// Mercator latitude projection so high-latitude camera travel moves at uniform screen velocity
function latToMercY(lat) {{
  const rad = Math.max(-82, Math.min(82, lat)) * Math.PI / 180.0;
  return Math.log(Math.tan(Math.PI / 4.0 + rad / 2.0));
}}
function mercYToLat(y) {{
  return (2.0 * Math.atan(Math.exp(y)) - Math.PI / 2.0) * 180.0 / Math.PI;
}}

// Configure HiDPI 2x overlay canvas with subpixel bilinear image smoothing
const ovCanvas = document.getElementById("overlay-canvas");
ovCanvas.width = Math.round(W * DPR);
ovCanvas.height = Math.round(H * DPR);
const ctx = ovCanvas.getContext("2d");
ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
ctx.imageSmoothingEnabled = true;
ctx.imageSmoothingQuality = "high";

// 2x HiDPI Offscreen Pre-Rasterized Label & Marker Badge Sprites (ZERO ctx.fillText per frame!)
const SPRITE_DPR = Math.max(2, DPR);
let labelSprites = [];
let markerSprites = [];

function buildLabelSprite(lbl) {{
  const isOcean = lbl.kind === "ocean" || lbl.kind === "sea";
  const fsize = (lbl.size || (isOcean ? 26 : 24)) * SCALE;
  const fontStr = isOcean
    ? `italic 600 ${{fsize.toFixed(2)}}px 'Cormorant Garamond', Georgia, serif`
    : `600 ${{fsize.toFixed(2)}}px 'Cinzel', Georgia, serif`;
  const text = (lbl.text || "").toUpperCase();

  const tmp = document.createElement("canvas").getContext("2d");
  tmp.font = fontStr;
  const metrics = tmp.measureText(text);
  const padX = Math.ceil(28 * SCALE);
  const padY = Math.ceil(22 * SCALE);
  const cssW = Math.ceil(metrics.width + padX * 2);
  const cssH = Math.ceil(fsize * 1.45 + padY * 2);

  const c = document.createElement("canvas");
  c.width = Math.ceil(cssW * SPRITE_DPR);
  c.height = Math.ceil(cssH * SPRITE_DPR);
  const g = c.getContext("2d");
  g.scale(SPRITE_DPR, SPRITE_DPR);
  g.font = fontStr;
  g.textAlign = "center";
  g.textBaseline = "middle";
  g.shadowColor = "rgba(3, 8, 16, 0.94)";
  g.shadowBlur = 12 * SCALE;
  g.shadowOffsetX = 0;
  g.shadowOffsetY = 2 * SCALE;
  g.fillStyle = isOcean ? "rgba(168, 214, 240, 0.92)" : "rgba(235, 242, 249, 0.88)";
  g.fillText(text, cssW * 0.5, cssH * 0.5);
  return {{ lbl, canvas: c, cssW, cssH }};
}}

function buildMarkerBadgeSprite(m) {{
  const color = m.color || "#E39B43";
  const title = m.label || "";
  const sub = m.sublabel || "";
  const titleFont = `700 ${{(21 * SCALE).toFixed(2)}}px 'Plus Jakarta Sans', sans-serif`;
  const subFont = `600 ${{(15.5 * SCALE).toFixed(2)}}px 'IBM Plex Mono', monospace`;

  const tmp = document.createElement("canvas").getContext("2d");
  tmp.font = titleFont;
  const tw = tmp.measureText(title).width;
  tmp.font = subFont;
  const sw = sub ? tmp.measureText(sub).width : 0;
  const bw = Math.ceil(Math.max(tw, sw) + 34 * SCALE);
  const bh = Math.ceil((sub ? 62 : 40) * SCALE);
  const pad = Math.ceil(10 * SCALE);
  const cssW = bw + pad * 2;
  const cssH = bh + pad * 2;

  const c = document.createElement("canvas");
  c.width = Math.ceil(cssW * SPRITE_DPR);
  c.height = Math.ceil(cssH * SPRITE_DPR);
  const g = c.getContext("2d");
  g.scale(SPRITE_DPR, SPRITE_DPR);

  // Subtle shadow + frosted slate badge
  g.save();
  g.shadowColor = "rgba(0, 0, 0, 0.55)";
  g.shadowBlur = 10 * SCALE;
  g.shadowOffsetY = 3 * SCALE;
  g.fillStyle = "rgba(7, 11, 18, 0.90)";
  g.strokeStyle = "rgba(232, 240, 248, 0.28)";
  g.lineWidth = 1.4 * SCALE;
  g.beginPath();
  g.roundRect(pad, pad, bw, bh, 6 * SCALE);
  g.fill();
  g.restore();
  g.strokeStyle = "rgba(232, 240, 248, 0.28)";
  g.lineWidth = 1.4 * SCALE;
  g.beginPath();
  g.roundRect(pad, pad, bw, bh, 6 * SCALE);
  g.stroke();

  // Accent strip
  g.fillStyle = color;
  g.fillRect(pad, pad + 5 * SCALE, 4.0 * SCALE, bh - 10 * SCALE);

  g.textAlign = "left";
  g.textBaseline = "top";
  g.fillStyle = "#F7F9FC";
  g.font = titleFont;
  g.fillText(title, pad + 16 * SCALE, pad + 8 * SCALE);
  if (sub) {{
    g.fillStyle = "#B4DCF2";
    g.font = subFont;
    g.fillText(sub, pad + 16 * SCALE, pad + 35 * SCALE);
  }}
  return {{ m, canvas: c, cssW, cssH, bw, bh, pad }};
}}

window.__initSprites = function() {{
  labelSprites = (SPEC.labels || []).map(buildLabelSprite);
  markerSprites = (SPEC.markers || []).map(buildMarkerBadgeSprite);
}};

function drawOverlay(t_s) {{
  ctx.clearRect(0, 0, W, H);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";

  // 1. Pre-rasterized 2x HiDPI sea/region watermark labels (bilinear subpixel drawImage + viewport/HUD safe fade!)
  for (const sp of labelSprites) {{
    const p = map.project([sp.lbl.lon, sp.lbl.lat]);
    const halfW = sp.cssW * 0.5;
    const halfH = sp.cssH * 0.5;
    const lx0 = p.x - halfW, lx1 = p.x + halfW;
    const ly0 = p.y - halfH, ly1 = p.y + halfH;
    const padEdge = 36 * SCALE;
    // Exclude all 3 HUD corners (top-left title card, top-right compass/telemetry, bottom-right scale bar)
    const hitTitle = (lx0 < 760 * SCALE) && (ly0 < 215 * SCALE);
    const hitTelem = (lx1 > W - 400 * SCALE) && (ly0 < 155 * SCALE);
    const hitScale = (lx1 > W - 300 * SCALE) && (ly1 > H - 155 * SCALE);
    let distOut = Math.max(
      padEdge - lx0,
      padEdge - ly0,
      lx1 - (W - padEdge),
      ly1 - (H - padEdge),
      0
    );
    if (hitTitle) distOut = Math.max(distOut, 70 * SCALE);
    if (hitTelem) distOut = Math.max(distOut, 70 * SCALE);
    if (hitScale) distOut = Math.max(distOut, 70 * SCALE);
    const lblFade = Math.max(0, Math.min(1, 1.0 - distOut / (64 * SCALE)));
    if (lblFade <= 0.02) continue;
    ctx.save();
    ctx.globalAlpha = lblFade;
    ctx.drawImage(sp.canvas, lx0, ly0, sp.cssW, sp.cssH);
    ctx.restore();
  }}

  // 2. Animated glowing migration routes (smooth subpixel fractional interpolation at comet tip)
  for (const r of builtRoutes) {{
    const rs = r.start_s || 0.4;
    const re = r.end_s || (SPEC.duration_s - 0.8);
    const prog = Math.max(0, Math.min(1, (t_s - rs) / Math.max(0.2, re - rs)));
    if (prog <= 0.005) continue;
    const eased = smootherstep(prog);
    const exactIdx = (r.pts.length - 1) * eased;
    const fullCount = Math.max(1, Math.floor(exactIdx));
    const frac = exactIdx - fullCount;
    const projPts = [];
    for (let i = 0; i <= fullCount; i++) projPts.push(map.project(r.pts[i]));
    if (fullCount + 1 < r.pts.length && frac > 1e-4) {{
      const pA = map.project(r.pts[fullCount]);
      const pB = map.project(r.pts[fullCount + 1]);
      projPts.push({{ x: pA.x + (pB.x - pA.x) * frac, y: pA.y + (pB.y - pA.y) * frac }});
    }}
    if (projPts.length < 2) continue;
    const color = r.color || "#E39B43";

    // Outer bloom pass
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(projPts[0].x, projPts[0].y);
    for (let i = 1; i < projPts.length; i++) ctx.lineTo(projPts[i].x, projPts[i].y);
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.28;
    ctx.lineWidth = 11.5 * SCALE;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();

    // Core crisp route line (solid anti-aliased stroke; avoid thin aliasing dashes)
    ctx.globalAlpha = 0.96;
    ctx.lineWidth = 4.0 * SCALE;
    if (r.dashed) ctx.setLineDash([16 * SCALE, 9 * SCALE]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Glowing comet head & directional arrowhead
    const head = projPts[projPts.length - 1];
    const prev = projPts[Math.max(0, projPts.length - 4)];
    const ang = Math.atan2(head.y - prev.y, head.x - prev.x);
    const grad = ctx.createRadialGradient(head.x, head.y, 1, head.x, head.y, 18 * SCALE);
    grad.addColorStop(0, "#FFF7E6");
    grad.addColorStop(0.35, color);
    grad.addColorStop(1, "rgba(227,155,67,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(head.x, head.y, 18 * SCALE, 0, Math.PI * 2);
    ctx.fill();

    ctx.translate(head.x, head.y);
    ctx.rotate(ang);
    ctx.fillStyle = "#FFF7E6";
    ctx.beginPath();
    ctx.moveTo(9.5 * SCALE, 0);
    ctx.lineTo(-6 * SCALE, -5.5 * SCALE);
    ctx.lineTo(-3 * SCALE, 0);
    ctx.lineTo(-6 * SCALE, 5.5 * SCALE);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }}

  // 3. Pulsing site markers + pre-rasterized 2x HiDPI badge sprites (subpixel smooth + HUD-safe edge fade!)
  for (const sp of markerSprites) {{
    const m = sp.m;
    const ms = m.start_s || 0.2;
    const me = m.end_s || (SPEC.duration_s + 1.0);
    if (t_s < ms || t_s > me + 0.5) continue;
    let fade = smootherstep(Math.min(1, (t_s - ms) / 0.50));
    if (t_s > me) fade *= (1.0 - smootherstep(Math.min(1, (t_s - me) / 0.45)));
    const p = map.project([m.lon, m.lat]);
    const dx = (m.offset_x || 22) * SCALE;
    const dy = (m.offset_y || -38) * SCALE;
    const lx = p.x + dx;
    const ly = p.y + dy;
    // Gracefully fade out before badge clips off-screen or collides with bottom-right HUD scale bar
    const edgeMargin = 28 * SCALE;
    const hudRightSafe = (lx + sp.bw > W - 260 * SCALE) && (ly + sp.bh > H - 125 * SCALE);
    if (hudRightSafe || lx < edgeMargin || ly < edgeMargin || (lx + sp.bw) > (W - edgeMargin) || (ly + sp.bh) > (H - edgeMargin)) {{
      const distOut = Math.max(
        edgeMargin - lx,
        edgeMargin - ly,
        (lx + sp.bw) - (W - edgeMargin),
        (ly + sp.bh) - (H - edgeMargin),
        hudRightSafe ? 48 * SCALE : 0
      );
      fade *= Math.max(0, 1.0 - distOut / (48 * SCALE));
    }}
    if (fade <= 0.01) continue;
    const color = m.color || "#E39B43";
    const pulse = ((t_s - ms) % 1.8) / 1.8;

    ctx.save();
    // Radar ring
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.2 * SCALE;
    ctx.globalAlpha = fade * (1 - pulse) * 0.80;
    ctx.beginPath();
    ctx.arc(p.x, p.y, (8 + pulse * 24) * SCALE, 0, Math.PI * 2);
    ctx.stroke();

    // Core dot
    ctx.globalAlpha = fade;
    ctx.fillStyle = "#FFF7E6";
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6.2 * SCALE, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.8 * SCALE;
    ctx.stroke();

    // Leader line from pin to nearest badge edge
    const anchorX = lx > p.x ? lx : (lx + sp.bw);
    ctx.strokeStyle = "rgba(232,240,248,0.68)";
    ctx.lineWidth = 1.8 * SCALE;
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(anchorX, ly + sp.bh * 0.5);
    ctx.stroke();

    // Blit pre-rasterized 2x HiDPI badge bitmap at exact floating-point coordinates
    ctx.drawImage(sp.canvas, lx - sp.pad, ly - sp.pad, sp.cssW, sp.cssH);
    ctx.restore();
  }}
  ctx.restore();
}}

// Precompute locked-horizon Mercator-scale camera endpoints (zero simultaneous pitch+bearing gimbal sway!)
const ZOOM_OFFSET = Math.log2(W / 1920.0);
const START_MY = latToMercY(SPEC.start_camera.center_lat);
const END_MY = latToMercY(SPEC.end_camera.center_lat);
const START_Z = SPEC.start_camera.zoom;
const END_Z = SPEC.end_camera.zoom;
const INV_SCALE_START = Math.pow(2, -START_Z);
const INV_SCALE_END = Math.pow(2, -END_Z);
const START_PITCH = SPEC.start_camera.pitch != null ? SPEC.start_camera.pitch : 24;
const RAW_END_PITCH = SPEC.end_camera.pitch != null ? SPEC.end_camera.pitch : START_PITCH;
const START_BEARING = SPEC.start_camera.bearing || 0;
const RAW_END_BEARING = SPEC.end_camera.bearing != null ? SPEC.end_camera.bearing : START_BEARING;
// When lock_horizon is enabled, hold pitch and bearing strictly constant to eradicate camera sway ("ქანაობა")
const END_PITCH = SPEC.lock_horizon ? START_PITCH : RAW_END_PITCH;
const DAMPED_END_BEARING = SPEC.lock_horizon
  ? START_BEARING
  : ((Math.abs(RAW_END_BEARING - START_BEARING) < 5.0 && Math.abs(END_PITCH - START_PITCH) > 0.5)
      ? START_BEARING
      : RAW_END_BEARING);

window.__renderAt = function(t_s) {{
  const u = Math.max(0, Math.min(1, t_s / Math.max(0.1, SPEC.duration_s)));
  const e = smootherstep(u);
  const zRaw = START_Z + (END_Z - START_Z) * e;
  // Scale-weighted Mercator ground position keeps screen-space pan velocity dead-linear during zoom
  let posE = e;
  if (Math.abs(END_Z - START_Z) > 0.02) {{
    const invCur = Math.pow(2, -zRaw);
    posE = (INV_SCALE_START - invCur) / (INV_SCALE_START - INV_SCALE_END);
  }}
  const lon = SPEC.start_camera.center_lon + (SPEC.end_camera.center_lon - SPEC.start_camera.center_lon) * posE;
  const lat = mercYToLat(START_MY + (END_MY - START_MY) * posE);
  const zoom = zRaw + ZOOM_OFFSET;
  const pitch = START_PITCH + (END_PITCH - START_PITCH) * e;
  const bearing = START_BEARING + (DAMPED_END_BEARING - START_BEARING) * e;

  map.jumpTo({{ center: [lon, lat], zoom, pitch, bearing }});
  map._render();
  drawOverlay(t_s);

  let normLon = ((lon + 180) % 360 + 360) % 360 - 180;
  const ns = lat >= 0 ? "N" : "S";
  const ew = normLon >= 0 ? "E" : "W";
  document.getElementById("coord-readout").textContent =
    `${{Math.abs(lat).toFixed(2)}}° ${{ns}}  /  ${{Math.abs(normLon).toFixed(2)}}° ${{ew}}`;

  const mpp = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom);
  const meters = mpp * 140 * SCALE;
  let scaleTxt;
  if (meters < 1800) {{
    const step = meters < 200 ? 25 : (meters < 600 ? 50 : 100);
    const mRounded = Math.max(50, Math.round(meters / step) * step);
    scaleTxt = `${{mRounded.toLocaleString("en-US")}} M`;
  }} else if (meters < 20000) {{
    scaleTxt = `${{(meters / 1000).toFixed(1)}} KM`;
  }} else {{
    const km = Math.max(10, Math.round(meters / 1000 / 50) * 50);
    scaleTxt = `${{km.toLocaleString("en-US")}} KM`;
  }}
  document.getElementById("scale-label").textContent = scaleTxt;
}};

window.__getTitleBBox = function() {{
  const r = document.getElementById("map-title-bbox").getBoundingClientRect();
  return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
}};
</script>
</body>
</html>"""


def _rect_poly(lon: float, lat: float, half_lon: float, half_lat: float, angle_deg: float = 0.0) -> list[list[float]]:
    """Build a rotated closed lon/lat rectangle ring for Roman architectural footprints."""
    rad = math.radians(angle_deg)
    ca, sa = math.cos(rad), math.sin(rad)
    cos_lat = max(0.2, math.cos(math.radians(lat)))
    corners = [(-half_lon, -half_lat), (half_lon, -half_lat), (half_lon, half_lat), (-half_lon, half_lat)]
    ring: list[list[float]] = []
    for dx, dy in corners:
        rx = (dx * cos_lat * ca - dy * sa) / cos_lat
        ry = dx * cos_lat * sa + dy * ca
        ring.append([round(lon + rx, 6), round(lat + ry, 6)])
    ring.append(ring[0])
    return ring


def _semicircle_theater_poly(
    lon: float,
    lat: float,
    radius_lon: float,
    radius_lat: float,
    *,
    start_deg: float = 95.0,
    end_deg: float = 265.0,
    steps: int = 18,
) -> list[list[float]]:
    """Build a semicircular Roman theater cavea polygon (Theatre of Pompey facing east into its Porticus)."""
    ring: list[list[float]] = []
    for i in range(steps + 1):
        ang = math.radians(start_deg + (end_deg - start_deg) * (i / float(steps)))
        ring.append([round(lon + math.cos(ang) * radius_lon, 6), round(lat + math.sin(ang) * radius_lat, 6)])
    ring.append(ring[0])
    return ring


def _build_ancient_rome_city_layers() -> dict[str, Any]:
    """Historically grounded vector topography & 3D monuments of central Rome on March 15, 44 BCE."""
    tiber_ring = _chaikin_smooth_ring(
        [
            [12.4670, 41.9045],
            [12.4702, 41.9005],
            [12.4695, 41.8962],
            [12.4718, 41.8924],
            [12.4754, 41.8902],
            [12.4778, 41.8884],
            [12.4788, 41.8842],
            [12.4758, 41.8842],
            [12.4748, 41.8880],
            [12.4720, 41.8904],
            [12.4686, 41.8930],
            [12.4664, 41.8968],
            [12.4668, 41.9012],
            [12.4638, 41.9045],
            [12.4670, 41.9045],
        ],
        iterations=2,
    )
    water_geo = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"name": "Tiber River"}, "geometry": {"type": "Polygon", "coordinates": [tiber_ring]}}],
    }

    hills_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Capitoline Hill", "fill": "#32281F"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        _chaikin_smooth_ring(
                            [[12.4810, 41.8920], [12.4844, 41.8924], [12.4848, 41.8948], [12.4820, 41.8950], [12.4806, 41.8934], [12.4810, 41.8920]],
                            iterations=2,
                        )
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Palatine Hill", "fill": "#352A20"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        _chaikin_smooth_ring(
                            [[12.4842, 41.8872], [12.4906, 41.8876], [12.4912, 41.8912], [12.4852, 41.8914], [12.4836, 41.8892], [12.4842, 41.8872]],
                            iterations=2,
                        )
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Quirinal Slope", "fill": "#2D241C"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        _chaikin_smooth_ring(
                            [[12.4820, 41.8968], [12.4925, 41.8970], [12.4930, 41.9018], [12.4825, 41.9015], [12.4820, 41.8968]],
                            iterations=2,
                        )
                    ],
                },
            },
        ],
    }

    districts_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Campus Martius", "fill": "#262019"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        _chaikin_smooth_ring(
                            [[12.4706, 41.8926], [12.4802, 41.8928], [12.4806, 41.8998], [12.4712, 41.8995], [12.4706, 41.8926]],
                            iterations=2,
                        )
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Forum Romanum Plaza", "fill": "#3A3024"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[12.4838, 41.8921], [12.4872, 41.8914], [12.4876, 41.8928], [12.4842, 41.8934], [12.4838, 41.8921]]
                    ],
                },
            },
        ],
    }

    roads_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Via Sacra", "color": "#C5A87E", "width": 4.2, "casing_w": 7.5},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4898, 41.8908], [12.4870, 41.8918], [12.4852, 41.8925], [12.4834, 41.8929]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Vicus Jugarius to Campus Martius", "color": "#B39770", "width": 3.6, "casing_w": 6.5},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4834, 41.8929], [12.4810, 41.8925], [12.4784, 41.8935], [12.4760, 41.8946], [12.4738, 41.8954]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Via Lata / Flaminia", "color": "#8E7A60", "width": 3.2, "casing_w": 6.0},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4822, 41.8950], [12.4806, 41.8982], [12.4788, 41.9022]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Argiletum / Subura", "color": "#87745B", "width": 2.8, "casing_w": 5.4},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4856, 41.8928], [12.4874, 41.8944], [12.4898, 41.8962]],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Via Triumphalis / Circus Flaminius", "color": "#8E7A60", "width": 2.8, "casing_w": 5.4},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4792, 41.8914], [12.4768, 41.8928], [12.4744, 41.8942], [12.4720, 41.8962]],
                },
            },
        ],
    }

    walls_geo = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Servian Wall Segment"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[12.4790, 41.8910], [12.4808, 41.8934], [12.4828, 41.8958], [12.4856, 41.8986]],
                },
            }
        ],
    }

    monuments_geo = {
        "type": "FeatureCollection",
        "features": [
            # Caesar's residence — Domus Publica & Atrium Vestae
            {
                "type": "Feature",
                "properties": {"name": "Domus Publica", "color": "#E5B567", "height": 26},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4865, 41.8919, 0.00055, 0.00038, -16.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Atrium Vestae", "color": "#C9B08A", "height": 18},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4860, 41.8914, 0.00048, 0.00028, -16.0)]},
            },
            # Forum Romanum civic monuments
            {
                "type": "Feature",
                "properties": {"name": "Basilica Julia", "color": "#D4C09E", "height": 24},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4847, 41.8920, 0.00062, 0.00028, -15.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Basilica Aemilia", "color": "#CBB694", "height": 22},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4857, 41.8929, 0.00056, 0.00024, -15.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Temple of Saturn", "color": "#DECBA9", "height": 28},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4839, 41.8926, 0.00030, 0.00024, -12.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Tabularium", "color": "#C3AF8F", "height": 34},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4832, 41.8931, 0.00045, 0.00022, -18.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Temple of Jupiter Capitolinus", "color": "#E0CEAE", "height": 36},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4824, 41.8928, 0.00044, 0.00036, -15.0)]},
            },
            # Circus Flaminius colonnade
            {
                "type": "Feature",
                "properties": {"name": "Circus Flaminius", "color": "#B9A587", "height": 15},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4778, 41.8933, 0.00105, 0.00032, -24.0)]},
            },
            # Largo Argentina Sacred Temples (just east of Curia of Pompey)
            {
                "type": "Feature",
                "properties": {"name": "Sacred Area Temples", "color": "#CBB89A", "height": 18},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4766, 41.8954, 0.00038, 0.00042, 0.0)]},
            },
            # Theatre of Pompey (semicircular stone cavea) + Porticus of Pompey + Curia of Pompey!
            {
                "type": "Feature",
                "properties": {"name": "Theatre of Pompey", "color": "#D9C5A3", "height": 36},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [_semicircle_theater_poly(12.4730, 41.8954, 0.00095, 0.00072)],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Porticus of Pompey", "color": "#C4AE8B", "height": 16},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4741, 41.8954, 0.00105, 0.00058, 0.0)]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Curia of Pompey", "color": "#D4523B", "height": 32},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(12.4754, 41.8954, 0.00038, 0.00034, 0.0)]},
            },
        ],
    }

    # Add subtle ancient urban insulae city-block footprints around Forum, Subura, Velabrum, Campus Martius, and Palatine slopes
    insulae_centers = [
        # Subura & Quirinal urban quarter (north-east of Forum)
        (12.4876, 41.8942, 0.00050, 0.00028, 12, "#46392C", 11),
        (12.4888, 41.8950, 0.00058, 0.00032, 18, "#413529", 10),
        (12.4864, 41.8954, 0.00052, 0.00028, 8, "#483B2E", 12),
        (12.4848, 41.8958, 0.00060, 0.00030, -6, "#43372B", 11),
        (12.4878, 41.8966, 0.00064, 0.00034, 15, "#3E3227", 9),
        (12.4896, 41.8932, 0.00056, 0.00030, -14, "#463A2D", 11),
        # Velabrum & Palatine slopes (south of Forum)
        (12.4820, 41.8906, 0.00054, 0.00028, -12, "#483B2E", 11),
        (12.4838, 41.8902, 0.00058, 0.00030, -18, "#45382B", 12),
        (12.4868, 41.8896, 0.00070, 0.00042, -10, "#5B4A38", 15),  # Palatine aristocratic villas
        (12.4885, 41.8892, 0.00064, 0.00038, -15, "#544434", 14),
        (12.4854, 41.8886, 0.00062, 0.00036, -8, "#514232", 13),
        # Campus Martius civic & residential quarters (west & north of Pompey's Theatre)
        (12.4788, 41.8956, 0.00056, 0.00032, 4, "#473A2D", 12),
        (12.4796, 41.8970, 0.00062, 0.00034, 6, "#413529", 10),
        (12.4774, 41.8974, 0.00060, 0.00034, 2, "#44372A", 11),
        (12.4750, 41.8978, 0.00065, 0.00036, 0, "#46392C", 11),
        (12.4728, 41.8974, 0.00054, 0.00032, -8, "#42362A", 10),
        (12.4748, 41.8932, 0.00056, 0.00028, -22, "#46392C", 11),
        (12.4728, 41.8938, 0.00048, 0.00026, -18, "#42362A", 10),
        (12.4810, 41.8962, 0.00052, 0.00030, 10, "#473A2D", 12),
        # Tiber Island (Isola Tiberina) temple & stone banks
        (12.4774, 41.8906, 0.00065, 0.00022, -32, "#7C6A54", 10),
    ]
    for idx_in, (ilon, ilat, hlon, hlat, ang, col, ht) in enumerate(insulae_centers):
        monuments_geo["features"].append(
            {
                "type": "Feature",
                "properties": {"name": f"Roman Quarter {idx_in}", "color": col, "height": ht},
                "geometry": {"type": "Polygon", "coordinates": [_rect_poly(ilon, ilat, hlon, hlat, ang)]},
            }
        )

    # Add Roman stone bridges across Tiber River (Pons Fabricius & Pons Aemilius) + secondary street network
    roads_geo["features"].extend(
        [
            {
                "type": "Feature",
                "properties": {"name": "Pons Fabricius", "color": "#CBB28A", "width": 3.4, "casing_w": 5.8},
                "geometry": {"type": "LineString", "coordinates": [[12.4792, 41.8914], [12.4774, 41.8906], [12.4756, 41.8898]]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Campus Martius Cross Street", "color": "#73624D", "width": 2.2, "casing_w": 4.2},
                "geometry": {"type": "LineString", "coordinates": [[12.4720, 41.8968], [12.4765, 41.8968], [12.4812, 41.8966], [12.4865, 41.8964]]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Vicus Tuscus", "color": "#7D6B54", "width": 2.4, "casing_w": 4.6},
                "geometry": {"type": "LineString", "coordinates": [[12.4848, 41.8920], [12.4832, 41.8904], [12.4812, 41.8888]]},
            },
        ]
    )

    return {
        "water_geo": water_geo,
        "hills_geo": hills_geo,
        "districts_geo": districts_geo,
        "roads_geo": roads_geo,
        "walls_geo": walls_geo,
        "monuments_geo": monuments_geo,
    }


def build_ancient_rome_ides_map_spec(
    kind: str = "overview",
    *,
    duration_s: float = 12.0,
) -> WebGLMapSpec:
    """Build a locked-horizon, zero-sway 3D WebGL2 cartography spec for Caesar's walk on March 15, 44 BCE.

    ``kind="overview"`` (Block 1): Smooth locked-horizon zoom-in establishing the 1.3 km / 20-min distance
    between Caesar's home (Domus Publica) and the Senate meeting hall (Curia of Pompey).
    ``kind="route"`` (Block 4): Smooth locked-horizon west tracking pan following Caesar's footsteps
    from the Domus Publica past the Forum Romanum and Artemidorus's warning to the Curia of Pompey.
    """
    city_layers = _build_ancient_rome_city_layers()
    caesar_route_coords = [
        [12.4865, 41.8919],  # Domus Publica
        [12.4852, 41.8925],  # Forum Romanum / Via Sacra
        [12.4834, 41.8929],  # Temple of Saturn / Rostra
        [12.4809, 41.8926],  # Vicus Jugarius
        [12.4784, 41.8936],  # Circus Flaminius / Campus Martius edge
        [12.4765, 41.8947],  # Approach past Sacred Temples
        [12.4754, 41.8954],  # Curia of Pompey (Eastern Porticus)
    ]

    if kind == "route":
        return WebGLMapSpec(
            map_id="rome_route_b4",
            title="THE WALK TO THE SENATE",
            subtitle="1.3 km through central Rome · Every block narrows the escape window",
            duration_s=duration_s,
            relief_bounds=(12.465, 41.885, 12.495, 41.903),
            start_camera={"center_lon": 12.4848, "center_lat": 41.8925, "zoom": 15.45, "pitch": 36.0, "bearing": 0.0},
            end_camera={"center_lon": 12.4764, "center_lat": 41.8950, "zoom": 15.65, "pitch": 36.0, "bearing": 0.0},
            routes=[
                {
                    "coords": caesar_route_coords,
                    "color": "#DF563D",
                    "start_s": 0.5,
                    "end_s": max(2.0, duration_s - 2.2),
                    "dashed": False,
                }
            ],
            markers=[
                {
                    "label": "DOMUS PUBLICA",
                    "sublabel": "CAESAR DEPARTS · ~11:00 AM",
                    "lon": 12.4865,
                    "lat": 41.8919,
                    "color": "#E5B567",
                    "start_s": 0.2,
                    "end_s": duration_s + 1.0,
                    "offset_x": -290,
                    "offset_y": 32,
                },
                {
                    "label": "FORUM ROMANUM",
                    "sublabel": "ARTEMIDORUS SCROLL WARNING",
                    "lon": 12.4834,
                    "lat": 41.8929,
                    "color": "#E39B43",
                    "start_s": 2.0,
                    "end_s": duration_s + 1.0,
                    "offset_x": 26,
                    "offset_y": -82,
                },
                {
                    "label": "CURIA OF POMPEY",
                    "sublabel": "60 SENATORS WAITING INSIDE",
                    "lon": 12.4754,
                    "lat": 41.8954,
                    "color": "#DF563D",
                    "start_s": 1.2,
                    "end_s": duration_s + 1.0,
                    "offset_x": 28,
                    "offset_y": -76,
                },
            ],
            sea_and_region_labels=[
                {"text": "TIBER RIVER", "lon": 12.4694, "lat": 41.8938, "kind": "sea", "size": 21},
                {"text": "CAMPUS MARTIUS", "lon": 12.4754, "lat": 41.8984, "kind": "region", "size": 20},
                {"text": "CAPITOLINE HILL", "lon": 12.4827, "lat": 41.8942, "kind": "region", "size": 17},
                {"text": "PALATINE HILL", "lon": 12.4876, "lat": 41.8894, "kind": "region", "size": 19},
            ],
            palette="ancient_rome_parchment",
            era_badge="MARCH 15, 44 BCE · 11:00 AM",
            lock_horizon=True,
            telemetry_subtitle="ANCIENT ROME · 44 BCE",
            city_layers=city_layers,
        )

    return WebGLMapSpec(
        map_id="rome_overview_b1",
        title="ROME · MARCH 15, 44 BCE",
        subtitle="Domus Publica to the Curia of Pompey — barely a 20-minute walk",
        duration_s=duration_s,
        relief_bounds=(12.465, 41.885, 12.495, 41.903),
        start_camera={"center_lon": 12.4809, "center_lat": 41.8936, "zoom": 14.75, "pitch": 34.0, "bearing": 0.0},
        end_camera={"center_lon": 12.4807, "center_lat": 41.8937, "zoom": 15.30, "pitch": 34.0, "bearing": 0.0},
        routes=[
            {
                "coords": caesar_route_coords,
                "color": "#DF563D",
                "start_s": 1.0,
                "end_s": max(2.5, duration_s - 1.6),
                "dashed": False,
            }
        ],
        markers=[
            {
                "label": "DOMUS PUBLICA",
                "sublabel": "CAESAR'S RESIDENCE · DAWN",
                "lon": 12.4865,
                "lat": 41.8919,
                "color": "#E5B567",
                "start_s": 0.3,
                "end_s": duration_s + 1.0,
                "offset_x": -300,
                "offset_y": 38,
            },
            {
                "label": "CURIA OF POMPEY",
                "sublabel": "SENATE SESSION · 1.3 KM WEST",
                "lon": 12.4754,
                "lat": 41.8954,
                "color": "#DF563D",
                "start_s": 2.0,
                "end_s": duration_s + 1.0,
                "offset_x": 28,
                "offset_y": -74,
            },
        ],
        sea_and_region_labels=[
            {"text": "TIBER RIVER", "lon": 12.4704, "lat": 41.8942, "kind": "sea", "size": 21},
            {"text": "CAMPUS MARTIUS", "lon": 12.4756, "lat": 41.8982, "kind": "region", "size": 20},
            {"text": "FORUM ROMANUM", "lon": 12.4852, "lat": 41.8938, "kind": "region", "size": 17},
            {"text": "PALATINE HILL", "lon": 12.4876, "lat": 41.8894, "kind": "region", "size": 19},
        ],
        palette="ancient_rome_parchment",
        era_badge="IDES OF MARCH · 44 BCE",
        lock_horizon=True,
        telemetry_subtitle="ANCIENT ROME · 44 BCE",
        city_layers=city_layers,
    )


def render_webgl_cinema_map(
    spec: WebGLMapSpec,
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    render_width: int = 960,
    render_height: int = 540,
    device_scale_factor: int = 2,
) -> dict[str, Any]:
    """Render a 2K 24fps zero-jitter 2x-supersampled MapLibre GL WebGL2 documentary map animation."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    if spec.city_layers:
        relief_png = out_mp4.with_suffix(".relief.png")
        land_ratio = 0.88
    else:
        relief_png, land_ratio = _grade_relief_plate_paleo(spec.relief_bounds, out_mp4.with_suffix(".relief.png"))

    html_path = out_mp4.with_suffix(".html")
    html_path.write_text(_build_maplibre_html(spec, relief_png, width=render_width, height=render_height), encoding="utf-8")

    total_frames = max(2, int(round(spec.duration_s * fps)))
    phys_w = render_width * max(1, int(device_scale_factor))
    phys_h = render_height * max(1, int(device_scale_factor))
    vf = f"scale={width}:{height}:flags=lanczos" if (phys_w, phys_h) != (width, height) else "null"
    ff_cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        str(fps),
        "-i",
        "-",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(ff_cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    title_bbox = [0, 0, 0, 0]
    sx = width / float(render_width)
    sy = height / float(render_height)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--enable-antialiasing",
            ],
        )
        page = browser.new_page(
            viewport={"width": render_width, "height": render_height},
            device_scale_factor=max(1, int(device_scale_factor)),
        )
        page.goto(html_path.resolve().as_uri(), wait_until="load")
        page.wait_for_function("() => window.__mapReady === true", timeout=60000)
        page.evaluate("() => document.fonts.ready")
        page.evaluate("() => window.__initSprites()")
        raw_bb = list(page.evaluate("() => window.__getTitleBBox()"))
        title_bbox = [int(round(raw_bb[0] * sx)), int(round(raw_bb[1] * sy)), int(round(raw_bb[2] * sx)), int(round(raw_bb[3] * sy))]
        cdp = page.context.new_cdp_session(page)

        for f_idx in range(total_frames):
            t_s = f_idx / float(fps)
            page.evaluate(f"() => window.__renderAt({t_s:.4f})")
            res = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 96})
            proc.stdin.write(base64.b64decode(res["data"]))

        browser.close()

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"FFmpeg WebGL map encode failed with exit code {ret}")

    return {
        "map_id": spec.map_id,
        "path": str(out_mp4),
        "palette": spec.palette,
        "lock_horizon": bool(spec.lock_horizon),
        "land_ratio": round(land_ratio, 3),
        "context_labels": [str(lbl.get("text", "")) for lbl in spec.sea_and_region_labels],
        "title_bbox": title_bbox,
        "duration_s": spec.duration_s,
        "width": width,
        "height": height,
        "fps": fps,
        "supersample_scale": max(1, int(device_scale_factor)),
        "physical_render_size": [phys_w, phys_h],
    }
