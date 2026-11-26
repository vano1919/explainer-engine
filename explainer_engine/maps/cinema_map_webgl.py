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
import rasterio
from playwright.sync_api import sync_playwright
from rasterio.windows import from_bounds

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

    west, south, east, north = spec.relief_bounds
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
    }

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<link rel="stylesheet" href="{ml_css_uri}" />
<style>
{font_css}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{
  width: {width}px; height: {height}px; overflow: hidden; background: #09131E;
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
  background: radial-gradient(ellipse 84% 78% at 50% 50%, rgba(0,0,0,0) 56%, rgba(4,7,12,0.58) 100%);
}}
.hud-title-card {{
  position: absolute; top: 44px; left: 54px; max-width: 680px;
  padding: 16px 26px 18px;
  background: linear-gradient(155deg, rgba(8,13,20,0.88) 0%, rgba(5,9,15,0.92) 100%);
  border-left: 3px solid {theme["accent_amber"]};
  border-top: 1px solid rgba(232,240,248,0.16);
  border-right: 1px solid rgba(232,240,248,0.12);
  border-bottom: 1px solid rgba(232,240,248,0.12);
  border-radius: 4px;
  box-shadow: 0 18px 44px rgba(0,0,0,0.55);
}}
.hud-era {{
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; letter-spacing: 0.22em;
  color: {theme["accent_amber"]}; text-transform: uppercase; margin-bottom: 6px;
}}
.hud-h1 {{
  font-family: {theme["font_display"]}; font-size: 34px; font-weight: 600;
  letter-spacing: 0.08em; color: #F7F9FC; line-height: 1.14;
}}
.hud-sub {{
  font-family: {theme["font_sans"]}; font-size: 18px; font-weight: 500; color: #DCE6F2; margin-top: 6px;
}}
.hud-telemetry {{
  position: absolute; top: 44px; right: 54px; display: flex; align-items: center; gap: 16px;
  padding: 12px 20px; background: rgba(7,12,19,0.88);
  border: 1px solid rgba(232,240,248,0.18); border-radius: 4px;
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; color: #9ED6F2;
  font-variant-numeric: tabular-nums;
}}
.compass-svg {{ width: 40px; height: 40px; flex-shrink: 0; }}
.hud-scale {{
  position: absolute; bottom: 44px; right: 54px;
  padding: 10px 18px; background: rgba(7,12,19,0.80);
  border: 1px solid rgba(232,240,248,0.18); border-radius: 4px;
  font-family: {theme["font_mono"]}; font-size: 15px; font-weight: 600; color: #DCE6F2;
  font-variant-numeric: tabular-nums;
  display: flex; flex-direction: column; align-items: flex-end; gap: 6px;
}}
.scale-bar-line {{
  width: 140px; height: 6px; border-left: 2px solid {theme["accent_glacial"]};
  border-right: 2px solid {theme["accent_glacial"]};
  border-bottom: 2px solid {theme["accent_glacial"]};
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
      <circle cx="24" cy="24" r="20" stroke="rgba(124,196,232,0.45)" stroke-width="1.5"/>
      <polygon points="24,6 28,24 24,20 20,24" fill="{theme["accent_amber"]}"/>
      <polygon points="24,42 28,24 24,28 20,24" fill="rgba(232,240,248,0.52)"/>
      <text x="24" y="5" fill="#F5F7FA" font-size="9" font-weight="700" font-family="IBM Plex Mono" text-anchor="middle">N</text>
    </svg>
    <div>
      <div id="coord-readout">52.00° N  /  38.00° E</div>
      <div style="font-size:12px;color:#B8C9DC;margin-top:3px;letter-spacing:0.12em;">PLEISTOCENE LGM RELIEF</div>
    </div>
  </div>
  <div class="hud-scale">
    <div id="scale-label">1,000 KM</div>
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
const W = {width}, H = {height};
const SCALE = H / 1080.0;
const DPR = Math.max(2, window.devicePixelRatio || 2);

const styleObj = {{
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
  renderWorldCopies: true,
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

  // 1. Pre-rasterized 2x HiDPI sea/region watermark labels (bilinear subpixel drawImage -> 0.0px jumping!)
  for (const sp of labelSprites) {{
    const p = map.project([sp.lbl.lon, sp.lbl.lat]);
    if (p.x < -sp.cssW || p.x > W + sp.cssW || p.y < -sp.cssH || p.y > H + sp.cssH) continue;
    ctx.drawImage(sp.canvas, p.x - sp.cssW * 0.5, p.y - sp.cssH * 0.5, sp.cssW, sp.cssH);
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

// Precompute damped Mercator camera endpoints (avoid micro-jitter simultaneous pitch+bearing twist)
const ZOOM_OFFSET = Math.log2(W / 1920.0);
const START_MY = latToMercY(SPEC.start_camera.center_lat);
const END_MY = latToMercY(SPEC.end_camera.center_lat);
const START_PITCH = SPEC.start_camera.pitch != null ? SPEC.start_camera.pitch : 24;
const END_PITCH = SPEC.end_camera.pitch != null ? SPEC.end_camera.pitch : START_PITCH;
const START_BEARING = SPEC.start_camera.bearing || 0;
const RAW_END_BEARING = SPEC.end_camera.bearing != null ? SPEC.end_camera.bearing : START_BEARING;
// Damp tiny simultaneous bearing micro-twists when pitch is also changing
const DAMPED_END_BEARING = (Math.abs(RAW_END_BEARING - START_BEARING) < 5.0 && Math.abs(END_PITCH - START_PITCH) > 0.5)
  ? START_BEARING
  : RAW_END_BEARING;

window.__renderAt = function(t_s) {{
  const u = Math.max(0, Math.min(1, t_s / Math.max(0.1, SPEC.duration_s)));
  const e = smootherstep(u);
  const lon = SPEC.start_camera.center_lon + (SPEC.end_camera.center_lon - SPEC.start_camera.center_lon) * e;
  const lat = mercYToLat(START_MY + (END_MY - START_MY) * e);
  const zoom = SPEC.start_camera.zoom + (SPEC.end_camera.zoom - SPEC.start_camera.zoom) * e + ZOOM_OFFSET;
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
  const km = Math.max(10, Math.round((mpp * 140 * SCALE) / 1000 / 50) * 50);
  document.getElementById("scale-label").textContent = `${{km.toLocaleString("en-US")}} KM`;
}};

window.__getTitleBBox = function() {{
  const r = document.getElementById("map-title-bbox").getBoundingClientRect();
  return [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)];
}};
</script>
</body>
</html>"""


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
        "medium",
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
