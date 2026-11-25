"""Cinema-grade historical shaded-relief animated map renderer (Natural Earth NE1 + SR + Film Grade).

Replaces flat infographic polygon maps with broadcast historical documentary cartography:
- Real Public Domain Natural Earth color relief + bathymetry (``NE1_HR.tif``) blended with
  multi-directional hillshade & slope-contrast relief (``SR_HR.tif``).
- Harmonized to the episode's unified realistic cinema palette and graded via ``cinema_grade``.
- Smoothly eased camera pan/zoom, subtle graticule grid, progressive ink-textured curved route
  arrows, non-overlapping Liberation Serif cartographic pin badges, and an editorial title cartouche.
- Emits exact synchronized map-action SFX cue timestamps for ``scene_soundscape.py``.
"""
from __future__ import annotations

import hashlib
import math
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.finish.cinema_grade import (
    DEFAULT_CINEMA_GRADE,
    CinemaGradeSpec,
    apply_unified_film_grade,
)
from explainer_engine.maps import draw as MD

DEFAULT_RELIEF_DIRS = (
    Path("/working_dir/c_1b68d4d8925e93a3/external_assets/relief_live"),
    Path("assets/maps/relief"),
)


def _resolve_relief_file(filename: str) -> Path | None:
    env_dir = os.environ.get("EXPLAINER_RELIEF_DIR", "").strip()
    candidates = ([Path(env_dir)] if env_dir else []) + list(DEFAULT_RELIEF_DIRS)
    for d in candidates:
        p = d / filename
        if p.is_file():
            return p
    return None


@lru_cache(maxsize=4)
def _load_geotiff_and_tfw(tif_path: str) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    p = Path(tif_path)
    tfw = p.with_suffix(".tfw")
    vals = [float(x.strip()) for x in tfw.read_text(encoding="utf-8").splitlines() if x.strip()]
    dx, dy, x0, y0 = vals[0], vals[3], vals[4], vals[5]
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(p)
    arr = np.asarray(im)
    return arr, (dx, dy, x0, y0)


def _read_raster_window(tif_path: Path, lon_min: float, lon_max: float, lat_min: float, lat_max: float) -> np.ndarray:
    """Read only the requested geographic window via rasterio (15MB RAM, <0.1s on 668MB 1:10m GeoTIFFs)."""
    try:
        import rasterio
        from rasterio.windows import Window

        with rasterio.open(tif_path) as ds:
            tr = ds.transform
            dx, dy, x0, y0 = float(tr.a), float(tr.e), float(tr.c), float(tr.f)
            rw, rh = ds.width, ds.height
            c0 = int(np.clip((lon_min - x0) / dx, 0, rw - 2))
            c1 = int(np.clip((lon_max - x0) / dx, c0 + 2, rw - 1))
            r0 = int(np.clip((lat_max - y0) / dy, 0, rh - 2))
            r1 = int(np.clip((lat_min - y0) / dy, r0 + 2, rh - 1))
            win = Window.from_slices((r0, r1), (c0, c1))
            arr = ds.read(window=win)  # (C, H, W)
            if arr.shape[0] >= 3:
                return np.transpose(arr[:3], (1, 2, 0))
            return arr[0]
    except Exception:
        arr_full, (dx, dy, x0, y0) = _load_geotiff_and_tfw(str(tif_path))
        rh, rw = arr_full.shape[:2]
        c0 = int(np.clip((lon_min - x0) / dx, 0, rw - 2))
        c1 = int(np.clip((lon_max - x0) / dx, c0 + 2, rw - 1))
        r0 = int(np.clip((lat_max - y0) / dy, 0, rh - 2))
        r1 = int(np.clip((lat_min - y0) / dy, r0 + 2, rh - 1))
        return arr_full[r0:r1, c0:c1, :3] if arr_full.ndim == 3 else arr_full[r0:r1, c0:c1]


def _sample_raster_crop(
    lon_center: float,
    lat_center: float,
    span_deg_lon: float,
    width: int,
    height: int,
    *,
    ne1_path: Path | None,
    sr_path: Path | None,
    palette_mode: str = "temperate_europe",
) -> np.ndarray:
    """Sample Natural Earth NE1 color relief + SR hillshade into a cinema-harmonized RGB terrain plate."""
    aspect = width / float(height)
    cos_lat = max(0.25, math.cos(math.radians(lat_center)))
    span_deg_lat = (span_deg_lon / aspect) * cos_lat

    lon_min = lon_center - span_deg_lon * 0.5
    lon_max = lon_center + span_deg_lon * 0.5
    lat_max = lat_center + span_deg_lat * 0.5
    lat_min = lat_center - span_deg_lat * 0.5

    if ne1_path is not None and ne1_path.is_file():
        sub = _read_raster_window(ne1_path, lon_min, lon_max, lat_min, lat_max)
        crop_rgb = cv2.resize(sub[..., :3] if sub.ndim == 3 else np.repeat(sub[..., None], 3, axis=-1), (width, height), interpolation=cv2.INTER_CUBIC).astype(
            np.float32
        )
    else:
        crop_rgb = np.full((height, width, 3), (118.0, 112.0, 96.0), dtype=np.float32)

    # Blend multi-directional SR hillshade + slope-contrast shading for dramatic 3D mountain relief
    if sr_path is not None and sr_path.is_file():
        sr_sub = _read_raster_window(sr_path, lon_min, lon_max, lat_min, lat_max)
        sr_crop = cv2.resize(sr_sub, (width, height), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        if sr_crop.ndim == 3:
            sr_crop = sr_crop[..., 0]
        # Amplify relief contrast & compute slope shading
        sr_norm = (sr_crop - float(np.median(sr_crop))) / max(12.0, float(np.std(sr_crop)))
        gx = cv2.Sobel(sr_crop, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(sr_crop, cv2.CV_32F, 0, 1, ksize=3)
        slope = np.hypot(gx, gy)
        slope_n = slope / max(1.0, float(np.percentile(slope, 95)))
        hill_gain = np.clip(1.0 + 0.22 * sr_norm - 0.14 * np.clip(slope_n, 0.0, 1.4), 0.58, 1.32)
        crop_rgb = crop_rgb * hill_gain[..., None]

    # Detect sea/water pixels (blue-dominant in NE1) vs land and harmonize to realistic historical film palette
    r, g, b = crop_rgb[..., 0], crop_rgb[..., 1], crop_rgb[..., 2]
    is_water = (b > r + 10.0) & (b > g + 2.0)

    # Desaturate land into rich muted antique-atlas cinema earth tones (olive/umber/ochre/slate)
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    land = np.stack([luma * 0.86 + r * 0.14, luma * 0.84 + g * 0.16, luma * 0.72 + b * 0.12], axis=-1)
    if palette_mode == "alpine_winter":
        # Cooler slate-stone mountains + crisp snow peaks for polar/Alpine campaigns
        land = land * np.array([0.82, 0.84, 0.88], dtype=np.float32)
        water = np.stack([luma * 0.28 + 14.0, luma * 0.36 + 22.0, luma * 0.44 + 32.0], axis=-1)
    elif palette_mode == "twilight_tactical":
        # Deep indigo-slate museum atlas matching twilight/night live-action cuts seamlessly
        land = land * np.array([0.62, 0.65, 0.70], dtype=np.float32)
        water = np.stack([luma * 0.16 + 10.0, luma * 0.22 + 16.0, luma * 0.30 + 24.0], axis=-1)
    else:
        # Warm muted ochre/umber/slate historical atlas look harmonized to 35mm documentary shadow/midtone balance
        land = land * np.array([0.80, 0.77, 0.70], dtype=np.float32)
        water = np.stack([luma * 0.22 + 15.0, luma * 0.30 + 22.0, luma * 0.36 + 28.0], axis=-1)

    base = np.where(is_water[..., None], water, land)
    # Subtle warm dark-ink coastal rim where water meets land
    water_u8 = is_water.astype(np.uint8) * 255
    coast_edge = cv2.Canny(water_u8, 80, 160)
    coast_edge = cv2.dilate(coast_edge, np.ones((2, 2), np.uint8)) > 0
    base[coast_edge] = base[coast_edge] * 0.45 + np.array([28.0, 34.0, 40.0], dtype=np.float32) * 0.55
    return np.clip(base, 0.0, 255.0).astype(np.uint8)


def _cubic_ease(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)


def _curved_arc(p0: tuple[float, float], p1: tuple[float, float], bend: float = 0.14, n: int = 48) -> list[tuple[float, float]]:
    mx, my = (p0[0] + p1[0]) * 0.5, (p0[1] + p1[1]) * 0.5
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    cx, cy = mx - dy * bend, my + dx * bend
    pts = []
    for i in range(n):
        t = i / float(n - 1)
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t * t * p1[1]
        pts.append((x, y))
    return pts


def render_cinema_map_clip(
    spec: dict[str, Any],
    out_mp4: Path,
    *,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    grade_spec: CinemaGradeSpec = DEFAULT_CINEMA_GRADE,
) -> dict[str, Any]:
    """Render a rich Natural Earth shaded-relief animated tactical map clip and emit synced SFX cues."""
    duration_s = float(spec.get("duration_s", 8.0))
    n_frames = max(2, int(round(duration_s * fps)))
    v0 = spec["view_start"]
    v1 = spec.get("view_end", v0)
    palette_mode = str(spec.get("palette_mode", "temperate_europe"))
    title = str(spec.get("title", "")).strip()
    subtitle = str(spec.get("subtitle", "")).strip()
    accent_rgb = tuple(spec.get("accent_rgb", (184, 58, 46)))

    ne1_path = _resolve_relief_file("NE1_HR.tif")
    sr_path = _resolve_relief_file("SR_HR.tif")

    out_w, out_h = int(width), int(height)
    if out_w > 1280:
        width, height = 1280, int(round(1280 * out_h / float(out_w))) // 2 * 2
    else:
        width, height = out_w, out_h

    # Render one high-resolution master geographic plate covering the union of start & end views
    lon_c = (float(v0["lon"]) + float(v1["lon"])) * 0.5
    lat_c = (float(v0["lat"]) + float(v1["lat"])) * 0.5
    max_span = max(float(v0["span_deg"]), float(v1["span_deg"])) + max(
        abs(float(v1["lon"]) - float(v0["lon"])), abs(float(v1["lat"]) - float(v0["lat"])) * 1.6
    ) + 2.5
    plate_w, plate_h = int(width * 1.8), int(height * 1.8)
    master_plate = _sample_raster_crop(
        lon_c, lat_c, max_span, plate_w, plate_h, ne1_path=ne1_path, sr_path=sr_path, palette_mode=palette_mode
    )

    aspect = width / float(height)
    cos_lat_c = max(0.25, math.cos(math.radians(lat_c)))
    plate_span_lat = (max_span / aspect) * cos_lat_c
    p_lon_min = lon_c - max_span * 0.5
    p_lat_max = lat_c + plate_span_lat * 0.5

    def lonlat_to_plate_px(lon: float, lat: float) -> tuple[float, float]:
        px = (lon - p_lon_min) / max_span * plate_w
        py = (p_lat_max - lat) / plate_span_lat * plate_h
        return px, py

    # Pre-load verified Liberation Serif fonts scaled cleanly for 720p -> 2K 2560x1440
    sf = max(1.0, width / 1280.0)
    f_title = MD.font(int(round(26 * sf)), face="map")
    f_sub = MD.font(int(round(16 * sf)), face="map")
    f_pin = MD.font(int(round(20 * sf)), face="map")

    # Collect synchronized map-action SFX cues
    sfx_events: list[dict[str, Any]] = [
        {"cue_id": f"{spec.get('shot_id', 'map')}_reveal", "sfx": "parchment_unfold", "offset_s": 0.15, "gain_db": -5.0}
    ]
    for idx, act in enumerate(spec.get("actions") or []):
        kind = act["kind"]
        t_start = float(act.get("start_s", 0.5))
        if kind == "route_arrow":
            sfx_events.append(
                {"cue_id": f"{spec.get('shot_id', 'map')}_arrow_{idx}", "sfx": "ink_arrow_sweep", "offset_s": t_start, "gain_db": -4.0}
            )
        elif kind == "pin":
            sfx_events.append(
                {"cue_id": f"{spec.get('shot_id', 'map')}_pin_{idx}", "sfx": "camp_pin_stamp", "offset_s": t_start, "gain_db": -3.5}
            )
        elif kind == "pulse":
            sfx_events.append(
                {"cue_id": f"{spec.get('shot_id', 'map')}_pulse_{idx}", "sfx": "troop_march_pulse", "offset_s": t_start, "gain_db": -5.0}
            )

    places = spec.get("places") or {}
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp4 = out_mp4.with_name(out_mp4.stem + ".part.mp4")

    vf_up = ["-vf", f"scale={out_w}:{out_h}:flags=lanczos,cas=0.30"] if (out_w, out_h) != (width, height) else []
    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
            "-r", str(fps), "-i", "-", "-frames:v", str(n_frames),
            *vf_up,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
            str(tmp_mp4),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    try:
        for f in range(n_frames):
            t_s = f / float(fps)
            u_cam = _cubic_ease(f / max(1, n_frames - 1))
            cur_lon = float(v0["lon"]) + (float(v1["lon"]) - float(v0["lon"])) * u_cam
            cur_lat = float(v0["lat"]) + (float(v1["lat"]) - float(v0["lat"])) * u_cam
            cur_span = float(v0["span_deg"]) + (float(v1["span_deg"]) - float(v0["span_deg"])) * u_cam
            cur_span_lat = (cur_span / aspect) * cos_lat_c

            # Crop view window from master plate cleanly via warpAffine (sub-pixel smooth!)
            cx_p, cy_p = lonlat_to_plate_px(cur_lon, cur_lat)
            vw_p = cur_span / max_span * plate_w
            vh_p = cur_span_lat / plate_span_lat * plate_h
            x0_p = cx_p - vw_p * 0.5
            y0_p = cy_p - vh_p * 0.5
            M = np.array(
                [[width / vw_p, 0.0, -x0_p * width / vw_p], [0.0, height / vh_p, -y0_p * height / vh_p]],
                dtype=np.float32,
            )
            frame_rgb = cv2.warpAffine(
                master_plate, M, (width, height), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
            )

            def ll_to_screen(lon: float, lat: float, _x0: float = x0_p, _y0: float = y0_p, _vw: float = vw_p, _vh: float = vh_p) -> tuple[float, float]:
                px_p, py_p = lonlat_to_plate_px(lon, lat)
                return (px_p - _x0) * (width / _vw), (py_p - _y0) * (height / _vh)

            pil_im = Image.fromarray(frame_rgb, mode="RGB").convert("RGBA")
            ov = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            dr = ImageDraw.Draw(ov)

            # Subtle antique cartographic graticule lines + outer editorial border
            step_deg = 2.0 if cur_span < 12.0 else 5.0
            lon_start = math.floor((cur_lon - cur_span * 0.6) / step_deg) * step_deg
            lon_end = math.ceil((cur_lon + cur_span * 0.6) / step_deg) * step_deg
            lat_start = math.floor((cur_lat - cur_span_lat * 0.6) / step_deg) * step_deg
            lat_end = math.ceil((cur_lat + cur_span_lat * 0.6) / step_deg) * step_deg
            g_lon = lon_start
            while g_lon <= lon_end:
                sx, _ = ll_to_screen(g_lon, cur_lat)
                if 0 <= sx <= width:
                    dr.line([(sx, 0), (sx, height)], fill=(235, 224, 200, 26), width=1)
                g_lon += step_deg
            g_lat = lat_start
            while g_lat <= lat_end:
                _, sy = ll_to_screen(cur_lon, g_lat)
                if 0 <= sy <= height:
                    dr.line([(0, sy), (width, sy)], fill=(235, 224, 200, 26), width=1)
                g_lat += step_deg

            # Pass 1: Draw all routes & pulses FIRST (underneath pins/labels -> zero collision!)
            for act in spec.get("actions") or []:
                t0_a = float(act.get("start_s", 0.5))
                if t_s < t0_a:
                    continue
                dur_a = max(0.25, float(act.get("duration_s", 1.4)))
                prog = _cubic_ease((t_s - t0_a) / dur_a)
                kind = act["kind"]
                if kind == "route_arrow":
                    p_from = places[act["from"]]
                    p_to = places[act["to"]]
                    s0 = ll_to_screen(p_from["lon"], p_from["lat"])
                    s1 = ll_to_screen(p_to["lon"], p_to["lat"])
                    pts = _curved_arc(s0, s1, bend=float(act.get("bend", 0.14)), n=56)
                    k_end = max(2, int(round(prog * (len(pts) - 1))) + 1)
                    sub = pts[:k_end]
                    # Soft dark shadow + outer warm glow + crisp crimson/accent core
                    dr.line([(x + 2 * sf, y + 3 * sf) for x, y in sub], fill=(10, 12, 16, 145), width=int(round(9 * sf)))
                    dr.line(sub, fill=(*accent_rgb, 95), width=int(round(11 * sf)))
                    dr.line(sub, fill=(*accent_rgb, 245), width=int(round(5 * sf)))
                    # Subtle marching dots along finished route
                    if prog >= 0.95:
                        for d_i in range(5):
                            idx_d = int(((d_i / 5.0 + (t_s * 0.35)) % 1.0) * (len(pts) - 1))
                            dx_p, dy_p = pts[idx_d]
                            dr_r = 2.5 * sf
                            dr.ellipse([dx_p - dr_r, dy_p - dr_r, dx_p + dr_r, dy_p + dr_r], fill=(252, 236, 205, 220))
                    # Crisp arrowhead at tip
                    tip, prev = sub[-1], sub[-2]
                    ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
                    hl = 14.0 * sf
                    p_l = (tip[0] - hl * math.cos(ang - 0.48), tip[1] - hl * math.sin(ang - 0.48))
                    p_r = (tip[0] - hl * math.cos(ang + 0.48), tip[1] - hl * math.sin(ang + 0.48))
                    dr.polygon([tip, p_l, p_r], fill=(*accent_rgb, 255), outline=(248, 238, 218, 220))
                elif kind == "pulse":
                    pl = places[act["place"]]
                    cx, cy = ll_to_screen(pl["lon"], pl["lat"])
                    for ring in range(3):
                        rt = ((t_s - t0_a) * 0.75 + ring / 3.0) % 1.0
                        rad = (8.0 + 46.0 * rt) * sf
                        al = int(220 * (1.0 - rt))
                        dr.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(*accent_rgb, al), width=int(round(3 * sf)))

            # Pass 2: Draw all cartographic pins & non-overlapping Liberation Serif pill badges ON TOP
            placed_boxes: list[tuple[float, float, float, float]] = []
            for act in spec.get("actions") or []:
                if act["kind"] != "pin":
                    continue
                t0_a = float(act.get("start_s", 0.2))
                if t_s < t0_a:
                    continue
                a_frac = min(1.0, (t_s - t0_a) / 0.30)
                al = int(255 * a_frac)
                pl = places[act["place"]]
                cx, cy = ll_to_screen(pl["lon"], pl["lat"])
                label_text = str(act.get("label") or pl.get("name") or pl.get("label") or act["place"])
                pos = str(act.get("label_pos", "below"))

                # Crisp concentric cartographic marker
                r_out, r_in = 8 * sf, 5 * sf
                dr.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], fill=(16, 20, 26, al))
                dr.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=(248, 240, 224, al), outline=(*accent_rgb, al), width=int(round(2 * sf)))

                tb = dr.textbbox((0, 0), label_text, font=f_pin)
                tw, th = tb[2] - tb[0], tb[3] - tb[1]
                bw, bh = tw + 24 * sf, th + 14 * sf
                gap = 16 * sf
                if pos == "above":
                    bx, by = cx - bw * 0.5, cy - bh - gap
                elif pos == "right":
                    bx, by = cx + gap, cy - bh * 0.5
                elif pos == "left":
                    bx, by = cx - bw - gap, cy - bh * 0.5
                else:
                    bx, by = cx - bw * 0.5, cy + gap
                margin = 18.0 * sf
                bx = max(margin, min(width - bw - margin, bx))
                by = max(margin, min(height - bh - margin, by))
                # Deterministic label collision avoidance: nudge vertically if overlapping an existing badge
                for _ in range(4):
                    if any(not (bx + bw < ox0 or bx > ox1 or by + bh < oy0 or by > oy1) for ox0, oy0, ox1, oy1 in placed_boxes):
                        by = max(margin, min(height - bh - margin, by + bh + 8 * sf))
                placed_boxes.append((bx, by, bx + bw, by + bh))

                # Leader line + drop shadow + dark charcoal badge + warm hairline border
                ex = max(bx, min(bx + bw, cx))
                ey = max(by, min(by + bh, cy))
                dr.line([(cx, cy), (ex, ey)], fill=(242, 232, 210, int(185 * a_frac)), width=int(round(2 * sf)))
                rad_b = int(round(5 * sf))
                dr.rounded_rectangle([bx + 3 * sf, by + 4 * sf, bx + bw + 3 * sf, by + bh + 4 * sf], radius=rad_b, fill=(0, 0, 0, int(115 * a_frac)))
                dr.rounded_rectangle(
                    [bx, by, bx + bw, by + bh],
                    radius=rad_b,
                    fill=(18, 22, 28, int(225 * a_frac)),
                    outline=(228, 216, 194, int(155 * a_frac)),
                    width=max(1, int(round(sf))),
                )
                dr.text((bx + 12 * sf, by + 5 * sf), label_text, font=f_pin, fill=(248, 244, 234, al))

            # Editorial top-left cartouche title (Johnny Harris / Vox discipline)
            if title:
                t_alpha = min(1.0, t_s / 0.45) * min(1.0, (duration_s - t_s) / 0.45)
                tal = int(255 * max(0.0, t_alpha))
                tb1 = dr.textbbox((0, 0), title, font=f_title)
                tb2 = dr.textbbox((0, 0), subtitle, font=f_sub) if subtitle else (0, 0, 0, 0)
                t1_h = tb1[3] - tb1[1]
                t2_h = (tb2[3] - tb2[1]) if subtitle else 0
                cw = max(tb1[2] - tb1[0], tb2[2] - tb2[0]) + 44 * sf
                ch = (t1_h + t2_h + 32 * sf) if subtitle else (t1_h + 24 * sf)
                cx0, cy0 = 36 * sf, 32 * sf
                dr.rectangle([cx0 + 4 * sf, cy0 + 5 * sf, cx0 + cw + 4 * sf, cy0 + ch + 5 * sf], fill=(0, 0, 0, int(100 * t_alpha)))
                dr.rectangle(
                    [cx0, cy0, cx0 + cw, cy0 + ch],
                    fill=(18, 22, 28, int(225 * t_alpha)),
                    outline=(235, 224, 200, int(65 * t_alpha)),
                    width=max(1, int(round(sf))),
                )
                dr.rectangle([cx0, cy0, cx0 + 5 * sf, cy0 + ch], fill=(*accent_rgb, tal))
                dr.text((cx0 + 18 * sf, cy0 + 10 * sf), title, font=f_title, fill=(250, 246, 236, tal))
                if subtitle:
                    dr.text((cx0 + 18 * sf, cy0 + 16 * sf + t1_h), subtitle, font=f_sub, fill=(224, 214, 194, int(235 * t_alpha)))

            # Subtle inner cartographic frame hairline
            m_f = int(round(14 * sf))
            dr.rectangle([m_f, m_f, width - m_f - 1, height - m_f - 1], outline=(235, 224, 200, 48), width=max(1, int(round(sf))))

            comp = Image.alpha_composite(pil_im, ov).convert("RGB")
            graded = apply_unified_film_grade(np.asarray(comp, dtype=np.uint8), frame_idx=f, spec=grade_spec)
            proc.stdin.write(graded.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed rendering cinema map clip: {out_mp4}")
    tmp_mp4.replace(out_mp4)
    return {
        "status": "PASS",
        "path": str(out_mp4),
        "ne1_relief_used": str(ne1_path) if ne1_path else None,
        "sr_hillshade_used": str(sr_path) if sr_path else None,
        "duration_s": duration_s,
        "frames": n_frames,
        "fps": fps,
        "resolution": [out_w, out_h],
        "sfx_events": sfx_events,
        "sha256": hashlib.sha256(out_mp4.read_bytes()).hexdigest(),
    }
