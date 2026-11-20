"""Headless Playwright + ffmpeg offline render driver for MapLibre shots (G-04c)."""
from __future__ import annotations
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
try:
    from playwright.sync_api import sync_playwright
except ImportError:  # the module stays importable (tests, spec checks) without Playwright; rendering says what to install
    sync_playwright = None  # type: ignore[assignment]
from explainer_engine.maps.hud_layout import Box, OKABE_ITO, check_palette, place_counter
from explainer_engine.maps.maplibre_spec import (
    camera_state,
    frame_count,
    load_shot_spec,
    offline_tile_url,
    schedule,
    strip_labels,
)
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 704
DEFAULT_COUNTER_SIZE: tuple[float, float] = (232.0, 68.0)
def _lonlat_to_pixel(
    lon: float,
    lat: float,
    center: tuple[float, float],
    zoom: float,
    size: tuple[int, int],
) -> tuple[float, float]:
    """Project WGS84 (lon, lat) to screen pixels matching Web Mercator 512px tile scale."""
    scale = 512.0 * (2.0 ** float(zoom))
    def merc_x(lng: float) -> float:
        return ((lng + 180.0) / 360.0) * scale
    def merc_y(lt: float) -> float:
        rad = math.radians(max(-85.051129, min(85.051129, lt)))
        return (0.5 - math.log(math.tan(rad) + (1.0 / math.cos(rad))) / (2.0 * math.pi)) * scale
    cx, cy = merc_x(float(center[0])), merc_y(float(center[1]))
    px, py = merc_x(float(lon)), merc_y(float(lat))
    return (size[0] / 2.0 + (px - cx), size[1] / 2.0 + (py - cy))
def _extract_line_coords(geojson: dict[str, Any]) -> list[list[float]]:
    """Extract coordinate array from a GeoJSON FeatureCollection, Feature, or LineString."""
    gtype = geojson.get("type")
    if gtype == "FeatureCollection":
        for feat in geojson.get("features", []):
            coords = _extract_line_coords(feat)
            if len(coords) >= 2:
                return coords
    elif gtype == "Feature" and isinstance(geojson.get("geometry"), dict):
        return _extract_line_coords(geojson["geometry"])
    elif gtype == "LineString":
        return list(geojson.get("coordinates", []))
    elif gtype == "MultiLineString":
        lines = geojson.get("coordinates", [])
        if lines:
            return list(lines[0])
    return []
def _build_avoid_boxes(
    spec: dict[str, Any],
    line_coords: list[list[float]],
    size: tuple[int, int],
    k: float = 1.0,
) -> list[Box]:
    """Compute screen-space bounding boxes for line endpoints/path and town labels."""
    center = (float(spec["center"][0]), float(spec["center"][1]))
    zoom = float(spec["zoom"])
    avoid: list[Box] = []
    if line_coords:
        xs: list[float] = []
        ys: list[float] = []
        for coord in line_coords:
            px, py = _lonlat_to_pixel(coord[0], coord[1], center, zoom, size)
            xs.append(px)
            ys.append(py)
        avoid.append((min(xs) - 16.0 * k, min(ys) - 16.0 * k, max(xs) + 16.0 * k, max(ys) + 16.0 * k))
        end_x, end_y = xs[-1], ys[-1]
        avoid.append((end_x - 32.0 * k, end_y - 32.0 * k, end_x + 32.0 * k, end_y + 32.0 * k))
    for town in spec.get("towns", []):
        lon, lat = float(town["lonlat"][0]), float(town["lonlat"][1])
        tx, ty = _lonlat_to_pixel(lon, lat, center, zoom, size)
        label_w = max(64.0, len(str(town["name"])) * 8.5 + 24.0) * k
        avoid.append((tx - label_w / 2.0, ty - 18.0 * k, tx + label_w / 2.0, ty + 18.0 * k))
    if spec.get("footnote"):
        avoid.append((size[0] - 320.0 * k, size[1] - 44.0 * k, float(size[0]), float(size[1])))
    return avoid
def _build_avoid_boxes_over_camera(
    spec: dict[str, Any],
    line_coords: list[list[float]],
    size: tuple[int, int],
    k: float = 1.0,
) -> list[Box]:
    """Avoid boxes for EVERY camera position of the shot (the counter must not jump, so one slot must be free all along)."""
    total = frame_count(spec)
    boxes: list[Box] = []
    for idx in range(total):
        cam = camera_state(spec, idx)
        moved = {**spec, "center": list(cam["center"]), "zoom": cam["zoom"]}
        boxes.extend(_build_avoid_boxes(moved, line_coords, size, k))
        if "camera" not in spec:
            break
    return list(dict.fromkeys(boxes))


def _tile_lonlat(z: int, x: int, y: int) -> tuple[float, float]:
    """North-west corner (lon, lat) of XYZ tile."""
    n = 2.0 ** z
    return x / n * 360.0 - 180.0, math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))


def _dem_coverage(dem_dir: Path) -> tuple[int, list[float]] | None:
    """Deepest DEM zoom actually on disk and the lon/lat bounds of its tiles (None when no tiles)."""
    zooms = sorted(int(p.name) for p in dem_dir.iterdir() if p.is_dir() and p.name.isdigit())
    if not zooms:
        return None
    z = zooms[-1]
    xs = [int(p.name) for p in (dem_dir / str(z)).iterdir() if p.is_dir() and p.name.isdigit()]
    ys = [int(f.stem) for x in xs for f in (dem_dir / str(z) / str(x)).glob("*.png")]
    if not xs or not ys:
        return None
    west, north = _tile_lonlat(z, min(xs), min(ys))
    east, south = _tile_lonlat(z, max(xs) + 1, max(ys) + 1)
    return z, [west, south, east, north]


def _resolve_line_geojson(spec_path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Resolve `line_geojson` path relative to the shot spec file or CWD."""
    raw = Path(spec["line_geojson"])
    if raw.is_absolute() and raw.exists():
        target = raw
    elif (spec_path.parent / raw).exists():
        target = spec_path.parent / raw
    else:
        target = raw.resolve()
    return json.loads(target.read_text(encoding="utf-8"))
STYLES_DIR = Path(__file__).resolve().parent / "styles"
DEFAULT_STYLE_PRESET = "neutral"


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def load_style_preset(name: str) -> dict[str, Any]:
    """Load `styles/<name>.json` (the episode's map style); refuse unknown names and unsafe file names."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError(f"style_preset {name!r} must be letters, digits and underscores only")
    path = STYLES_DIR / f"{name}.json"
    if not path.exists():
        known = ", ".join(sorted(p.stem for p in STYLES_DIR.glob("*.json")))
        raise FileNotFoundError(f"style preset {name!r} not found in {STYLES_DIR} (known: {known})")
    preset = json.loads(path.read_text(encoding="utf-8"))
    for key in ("map", "line", "hud", "finish", "palette_check"):
        if key not in preset:
            raise ValueError(f"style preset {name!r} is missing the {key!r} block")
    return preset


def _dig(preset: dict[str, Any], dotted: str) -> Any:
    node: Any = preset
    for part in dotted.split("."):
        node = node[part]
    return node


def _validate_hud_palette(preset: dict[str, Any] | None = None) -> None:
    """Verify the preset's foreground colours pass contrast and CVD checks against its map background."""
    preset = preset or load_style_preset(DEFAULT_STYLE_PRESET)
    check = preset["palette_check"]
    palette = {name: _hex_rgb(_dig(preset, name)) for name in check["foreground"]}
    bg = _hex_rgb(_dig(preset, check["background"]))
    problems = check_palette(palette, bg)
    if problems:
        raise ValueError(
            f"HUD palette of style {preset.get('name')!r} failed colour-blind / contrast check: {'; '.join(problems)}"
        )
def render_shot(spec_path: str, out_mp4: str, tile_dir: str, work_dir: str) -> dict[str, Any]:
    """Render an offline MapLibre shot to MP4 using headless Playwright and ffmpeg."""
    spec_file = Path(spec_path).resolve()
    spec = load_shot_spec(spec_file)
    preset = load_style_preset(str(spec.get("style_preset", DEFAULT_STYLE_PRESET)))
    _validate_hud_palette(preset)
    width = int(spec["size"][0]) if spec.get("size") else DEFAULT_WIDTH
    height = int(spec["size"][1]) if spec.get("size") else DEFAULT_HEIGHT
    fps = float(spec["fps"])
    total_frames = frame_count(spec)
    seconds = float(total_frames) / fps
    lane_dir = Path(__file__).resolve().parent
    for vendored in ("vendor/maplibre-gl.js", "vendor/maplibre-gl.css"):
        if not (lane_dir / vendored).exists():
            raise FileNotFoundError(
                f"{lane_dir / vendored} is missing: copy dist/maplibre-gl.js and dist/maplibre-gl.css of the "
                "maplibre-gl npm package into maplibre_lane/vendor/ (page.html loads them from there)"
            )
    tiles_root = Path(tile_dir).resolve()
    if not tiles_root.exists():
        raise FileNotFoundError(f"Offline tile directory does not exist: {tiles_root}")
    work_path = Path(work_dir).resolve()
    frames_dir = work_path / "frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    out_video = Path(out_mp4).resolve()
    out_video.parent.mkdir(parents=True, exist_ok=True)
    line_geojson = _resolve_line_geojson(spec_file, spec)
    line_coords = _extract_line_coords(line_geojson)
    k = width / float(DEFAULT_WIDTH)  # HUD is designed for 1280 px width; scale it with the frame
    avoid_boxes = _build_avoid_boxes_over_camera(spec, line_coords, (width, height), k)
    counter_box = place_counter((width, height), (DEFAULT_COUNTER_SIZE[0] * k, DEFAULT_COUNTER_SIZE[1] * k), avoid_boxes)
    date_box: Box = (
        counter_box[0],
        counter_box[3] + 10.0 * k,
        counter_box[0] + 190.0 * k,
        counter_box[3] + 44.0 * k,
    )
    vector_url = offline_tile_url(tiles_root / "vector", "vector")
    dem_dir = tiles_root / "dem"
    dem_url = offline_tile_url(dem_dir, "dem") if dem_dir.exists() else None
    dem_cov = _dem_coverage(dem_dir) if dem_dir.exists() else None
    optional_style: dict[str, Any] | None = None
    style_candidate = tiles_root / "style.json"
    if style_candidate.exists():
        raw_style = json.loads(style_candidate.read_text(encoding="utf-8"))
        optional_style = strip_labels(raw_style)
    frame_states = [schedule(spec, idx) for idx in range(total_frames)]
    boot_payload = {
        "spec": spec,
        "lineGeojson": line_geojson,
        "vectorTileUrl": vector_url,
        "demTileUrl": dem_url,
        "preset": preset,
        "demMaxZoom": dem_cov[0] if dem_cov else None,
        "demBounds": dem_cov[1] if dem_cov else None,
        "style": optional_style,
        "hudLayout": {
            "counter_box": list(counter_box),
            "date_box": list(date_box),
        },
        "frames": frame_states,
        "camera0": {"center": list(camera_state(spec, 0)["center"]), "zoom": camera_state(spec, 0)["zoom"]},
    }
    page_html = (Path(__file__).resolve().parent / "page.html").as_uri()
    if sync_playwright is None:
        raise RuntimeError("playwright is not installed: pip install playwright (and a Chromium, or set EXPLAINER_CHROMIUM)")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.environ.get("EXPLAINER_CHROMIUM") or None,
            args=[
                "--allow-file-access-from-files",
                "--disable-web-security",
                "--use-gl=angle",
                "--use-angle=swiftshader",
            ],
        )
        try:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
                offline=True,
            )
            def _block_non_file(route: Any) -> None:
                url = route.request.url
                if url.startswith("file://") or url.startswith("data:") or url.startswith("blob:"):
                    route.continue_()
                else:
                    route.abort("blockedbyclient")
            context.route("**/*", _block_non_file)
            page = context.new_page()
            if os.environ.get("EXPLAINER_MAP_DEBUG"):  # print browser console, failed requests and page errors
                page.on("console", lambda m: print("console:", m.text))
                page.on("requestfailed", lambda r: print("request failed:", r.url, r.failure))
                page.on("pageerror", lambda e: print("page error:", e))
            page.goto(page_html, wait_until="domcontentloaded")
            page.evaluate("async (cfg) => { await window.initScene(cfg); }", boot_payload)
            for idx in range(total_frames):
                cam = camera_state(spec, idx)
                # camera FIRST: setFrame projects the town labels with the camera the map has at that moment
                page.evaluate(
                    "async (cam) => { await window.setCamera(cam.center, cam.zoom); }",
                    {"center": list(cam["center"]), "zoom": cam["zoom"]},
                )
                page.evaluate("async (f) => { await window.setFrame(f); }", idx)
                png_path = frames_dir / f"frame_{idx:05d}.png"
                page.screenshot(path=str(png_path), type="png")
            idle_timeouts = int(page.evaluate("window.idleTimeouts || 0") or 0)
        finally:
            browser.close()
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        f"{fps:g}",
        "-i",
        str(frames_dir / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        "-movflags",
        "+faststart",
        str(out_video),
    ]
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
    return {
        "frames": total_frames,
        "mp4": str(out_video),
        "seconds": seconds,
        "idle_timeouts": idle_timeouts,
        "style_preset": preset["name"],
    }
