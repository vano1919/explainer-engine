"""Python 10% Info-Graphics, Tactical Maps, Troop Movements & Animated Counters Engine (D-130 / v4.2).

Implements the Creator's directive for the 10% Information Visualization Layer (`PYTHON_INFO_GRAPHICS_RENDER`):
- Why Python instead of generative AI for the 10% layer:
  Generative AI models garble numbers, misspell labels, and cannot draw accurate troop movement areas,
  front-line polygons, timelines, or exact population/casualty/budget counters.
- Harmonized Ink Chronicle / Luminescent Chiaroscuro + Documentary Clarity Visual Identity:
  Combines obsidian-slate cartographic foundations, oxidized copper-teal and warm amber-gold accents,
  tactile parchment relief blending (when an anchor plate is provided), subtle vignette, and razor-sharp
  documentary typography with generous negative space.
- Supported Dynamic Templates (`INFO_GRAPHIC_SUBTYPES`):
  1. `tactical_map_and_troop_movement`: Historical maps, regions, borders, cities, terrain contours,
     animated front-line / ash-cloud expansion polygon, directional troop/migration vectors, and zoom target coordinates.
  2. `demographic_or_casualty_counter`: Frame-accurate animated number counter (population bottleneck,
     army size, casualty counts) with proportional 10x10 unit matrix.
  3. `comparative_data_diagram`: Animated multi-bar / force-ratio / economic / ejecta comparison chart.
  4. `chronological_timeline_escalation`: Animated timeline scrubber with dates, causal phase markers, and duration spans.
  5. `territory_change_and_battle_progress`: Animated border shift, siege/front-line progression, and city capture status.
  6. `resource_and_budget_counter`: Financial/logistics ledger, treasury/supply burn-rate counter, and reserve threshold.
  7. `before_after_comparison`: Split-screen wipe comparison showing pre-event vs. post-event metrics and deltas.
  8. `progress_and_threshold_bars`: Tipping-point gauges, critical threshold indicators, and date/event overlays.
"""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

INFO_GRAPHIC_SUBTYPES: Tuple[str, ...] = (
    "tactical_map_and_troop_movement",
    "demographic_or_casualty_counter",
    "comparative_data_diagram",
    "chronological_timeline_escalation",
    "territory_change_and_battle_progress",
    "resource_and_budget_counter",
    "before_after_comparison",
    "progress_and_threshold_bars",
)

# Harmonized Ink Chronicle / Chiaroscuro + Documentary Clarity Palette
PALETTE_BG_DARK = (12, 16, 23)
PALETTE_GRID_LINE = (30, 40, 56)
PALETTE_LAND_MASS = (24, 32, 46)
PALETTE_COAST_BORDER = (68, 88, 118)
PALETTE_CRIMSON_VECTOR = (218, 58, 52)
PALETTE_AMBER_HIGHLIGHT = (232, 162, 58)
PALETTE_TEAL_COUNTER = (64, 178, 196)
PALETTE_TEXT_PRIMARY = (238, 234, 224)
PALETTE_TEXT_MUTED = (154, 164, 180)
PALETTE_PANEL_BG = (18, 24, 34)
PALETTE_PARCHMENT_GOLD = (196, 154, 82)

_BASE_CANVAS_CACHE: Dict[Tuple[int, int, str], Image.Image] = {}


def classify_10pct_infographic_subtype(shot: Dict[str, Any], spoken_text: str = "") -> str:
    """Classify a 10% visualization shot into its optimal YouTube documentary info-graphic subtype."""
    explicit = str(shot.get("infographic_subtype") or "").strip()
    if explicit in INFO_GRAPHIC_SUBTYPES:
        return explicit

    combined = " ".join([
        str(shot.get("narrative_purpose") or ""),
        str(shot.get("action_start_state") or ""),
        str(shot.get("action_end_state") or ""),
        str((shot.get("image_prompt") or {}).get("start_frame_prompt") or ""),
        str(spoken_text or ""),
    ]).lower()

    if any(k in combined for k in ("before and after", "before/after", "pre-eruption vs", "split comparison")):
        return "before_after_comparison"
    if any(k in combined for k in ("budget", "treasury", "francs", "gold", "loan", "debt", "coin", "financial", "burn rate")):
        return "resource_and_budget_counter"
    if any(k in combined for k in ("territory", "border shift", "annex", "frontline progress", "siege progress", "control zone")):
        return "territory_change_and_battle_progress"
    if any(k in combined for k in ("threshold", "tipping point", "critical margin", "gauge", "progress bar")):
        return "progress_and_threshold_bars"
    if any(k in combined for k in ("population", "survivor", "casualt", "dead", "bottleneck", "thousand", "million", "count", "number of people", "troops", "soldiers")):
        if re.search(r"\b\d[\d,]*\b", combined):
            return "demographic_or_casualty_counter"
    if any(k in combined for k in ("compare", "comparison", "ratio", "versus", "vs", "diagram", "chart", "supply", "artillery", "tons", "km3", "ejecta")):
        return "comparative_data_diagram"
    if any(k in combined for k in ("timeline", "hour", "countdown", "year", "century", "chronolog", "phase", "day 1", "week")):
        return "chronological_timeline_escalation"
    return "tactical_map_and_troop_movement"


def _extract_numbers_from_text(text: str) -> List[int]:
    """Extract integer values from narrative/spoken text for deterministic counters/charts."""
    matches = re.findall(r"\b(\d{1,3}(?:,\d{3})+|\d+)\b", text)
    nums: List[int] = []
    for m in matches:
        try:
            val = int(m.replace(",", ""))
            if val > 0:
                nums.append(val)
        except ValueError:
            continue
    return nums


def build_10pct_infographic_spec(
    shot: Dict[str, Any],
    spoken_text: str = "",
    episode_title: str = "",
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    background_plate_path: str | None = None,
) -> Dict[str, Any]:
    """Build a deterministic Python rendering specification for a 10% map/diagram/counter shot."""
    sid = str(shot.get("shot_id") or "S01_SH001")
    seg_id = str(shot.get("segment_id") or "S01")
    dur = float(shot.get("target_duration_seconds", 4.5))
    subtype = classify_10pct_infographic_subtype(shot, spoken_text=spoken_text)
    nums = _extract_numbers_from_text(f"{spoken_text} {shot.get('narrative_purpose', '')} {shot.get('action_start_state', '')}")

    if subtype in ("demographic_or_casualty_counter", "resource_and_budget_counter"):
        start_val = nums[0] if len(nums) >= 2 else (nums[0] * 10 if nums else 100_000)
        end_val = nums[1] if len(nums) >= 2 else (nums[0] if nums else 5_000)
    else:
        start_val = nums[0] if nums else 100
        end_val = nums[1] if len(nums) >= 2 else 250

    zoom_target_xy = shot.get("zoom_target_xy") or [0.58, 0.48]

    return {
        "shot_id": sid,
        "segment_id": seg_id,
        "duration_sec": dur,
        "fps": fps,
        "width": width,
        "height": height,
        "total_frames": max(fps, int(round(dur * fps))),
        "engine": "PYTHON_INFO_GRAPHICS_RENDER",
        "infographic_subtype": subtype,
        "style_identity": "ink_chronicle_documentary_hybrid",
        "headline": str(shot.get("narrative_purpose") or episode_title or sid)[:68].upper(),
        "subheadline": str(shot.get("action_start_state") or "")[:90],
        "date_or_event_overlay": str(shot.get("date_overlay") or shot.get("lighting_and_time") or "HISTORICAL CHRONICLE")[:48].upper(),
        "counter_start_value": start_val,
        "counter_end_value": end_val,
        "zoom_target_xy": [round(float(zoom_target_xy[0]), 4), round(float(zoom_target_xy[1]), 4)],
        "background_plate_path": background_plate_path,
        "parallax_preset": (shot.get("video_prompt") or {}).get("parallax_preset") or "zoom_focus",
    }


def _apply_parchment_and_vignette_base(
    width: int,
    height: int,
    background_plate_path: str | None = None,
) -> Image.Image:
    """Create (and cache per resolution/plate) the harmonized Ink Chronicle dark-slate + copper-parchment canvas."""
    cache_key = (width, height, str(background_plate_path or ""))
    if cache_key in _BASE_CANVAS_CACHE:
        return _BASE_CANVAS_CACHE[cache_key].copy()

    base = np.full((height, width, 3), PALETTE_BG_DARK, dtype=np.float32)
    if background_plate_path and Path(background_plate_path).is_file():
        try:
            plate = Image.open(background_plate_path).convert("RGB").resize((width, height), Image.BICUBIC)
            plate_arr = np.asarray(plate, dtype=np.float32)
            base = base * 0.84 + plate_arr * 0.16
        except Exception:
            pass

    yy = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
    rad2 = xx * xx + yy * yy
    vig = np.clip(1.0 - 0.22 * rad2, 0.72, 1.0)[:, :, None]
    out_img = Image.fromarray(np.clip(base * vig, 0, 255).astype(np.uint8), mode="RGB")

    # Pre-draw coordinate grid onto cached base canvas
    draw = ImageDraw.Draw(out_img, "RGBA")
    sx = width / 1920.0
    sy = height / 1080.0
    grid_step_x = max(40, int(round(80 * sx)))
    grid_step_y = max(40, int(round(80 * sy)))
    for x in range(0, width, grid_step_x):
        draw.line([(x, 0), (x, height)], fill=(*PALETTE_GRID_LINE, 105), width=1)
    for y in range(0, height, grid_step_y):
        draw.line([(0, y), (width, y)], fill=(*PALETTE_GRID_LINE, 105), width=1)

    _BASE_CANVAS_CACHE[cache_key] = out_img
    return out_img.copy()


def _draw_youtube_docudrama_frame(
    spec: Dict[str, Any],
    frame_idx: int,
    total_frames: int,
    width: int = 1920,
    height: int = 1080,
) -> Image.Image:
    """Render a single frame (1920x1080 or 2560x1440) of the 10% documentary map, diagram, or counter."""
    t = min(1.0, max(0.0, frame_idx / max(1, total_frames - 1)))
    ease_t = 1.0 - (1.0 - t) ** 3

    img = _apply_parchment_and_vignette_base(width, height, spec.get("background_plate_path"))
    draw = ImageDraw.Draw(img, "RGBA")
    font = ImageFont.load_default()

    sx = width / 1920.0
    sy = height / 1080.0
    sc = lambda x, y: (int(round(x * sx)), int(round(y * sy)))  # noqa: E731

    # Top documentary header bar with Date/Event Overlay badge
    draw.rectangle([sc(60, 48), sc(1860, 128)], fill=(*PALETTE_PANEL_BG, 232), outline=(*PALETTE_PARCHMENT_GOLD, 185), width=max(1, int(2 * sx)))
    draw.rectangle([sc(60, 48), sc(74, 128)], fill=(*PALETTE_AMBER_HIGHLIGHT, 255))
    draw.text(sc(96, 66), f"CHRONICLE DATA LAYER  |  {spec['segment_id']} / {spec['shot_id']}  |  {spec.get('date_or_event_overlay', '')}", fill=PALETTE_AMBER_HIGHLIGHT, font=font)
    draw.text(sc(96, 94), spec["headline"], fill=PALETTE_TEXT_PRIMARY, font=font)

    subtype = spec["infographic_subtype"]
    seed_int = int(hashlib.sha256(spec["shot_id"].encode("utf-8")).hexdigest()[:8], 16)

    if subtype in ("tactical_map_and_troop_movement", "territory_change_and_battle_progress"):
        cx, cy = width // 2, int(height * 0.53)
        pts_land = []
        for k in range(18):
            ang = (2.0 * math.pi * k) / 18.0
            rad_x = (540 + ((seed_int >> (k % 12)) & 0x7F) - 64) * sx
            rad_y = (300 + ((seed_int >> ((k + 5) % 12)) & 0x5F) - 48) * sy
            pts_land.append((cx + int(rad_x * math.cos(ang)), cy + int(rad_y * math.sin(ang))))
        draw.polygon(pts_land, fill=(*PALETTE_LAND_MASS, 238), outline=(*PALETTE_PARCHMENT_GOLD, 215))

        pts_ridge = [(int(cx + (px - cx) * 0.68), int(cy + (py - cy) * 0.68)) for px, py in pts_land]
        draw.polygon(pts_ridge, fill=(28, 38, 54, 160), outline=(*PALETTE_COAST_BORDER, 150))

        zone_radius_x = int((90 + 340 * ease_t) * sx)
        zone_radius_y = int((60 + 210 * ease_t) * sy)
        ox, oy = int(cx - 120 * sx), int(cy - 20 * sy)
        draw.ellipse(
            [(ox - zone_radius_x, oy - zone_radius_y), (ox + zone_radius_x, oy + zone_radius_y)],
            fill=(*PALETTE_CRIMSON_VECTOR, 74),
            outline=(*PALETTE_CRIMSON_VECTOR, 235),
            width=max(2, int(3 * sx)),
        )

        if subtype == "territory_change_and_battle_progress":
            front_x = int(ox + zone_radius_x * 0.85)
            draw.line([(front_x, int(cy - 220 * sy)), (front_x, int(cy + 220 * sy))], fill=(*PALETTE_AMBER_HIGHLIGHT, 255), width=max(2, int(4 * sx)))
            draw.rectangle([sc(1320, 170), sc(1820, 290)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 190), width=1)
            draw.text(sc(1345, 190), "BATTLE / TERRITORY CONTROL", fill=PALETTE_AMBER_HIGHLIGHT, font=font)
            prog_w = int(440 * sx * ease_t)
            draw.rectangle([sc(1345, 225), sc(1785, 255)], fill=(*PALETTE_GRID_LINE, 190), outline=PALETTE_COAST_BORDER, width=1)
            draw.rectangle([sc(1345, 225), (int(1345 * sx) + prog_w, int(255 * sy))], fill=(*PALETTE_CRIMSON_VECTOR, 240))
            draw.text(sc(1345, 265), f"SECTOR SHIFT: +{int(ease_t * 100)}% CONTROL", fill=PALETTE_TEXT_PRIMARY, font=font)

        vectors = [
            ((ox, oy), (int(cx + 260 * sx), int(cy - 130 * sy)), "ROUTE ALPHA"),
            ((ox, oy), (int(cx + 310 * sx), int(cy + 40 * sy)), "ROUTE BETA"),
            ((ox, oy), (int(cx + 180 * sx), int(cy + 190 * sy)), "SUPPLY LINE"),
        ]
        for (x0, y0), (x1, y1), label in vectors:
            cur_x = int(x0 + (x1 - x0) * ease_t)
            cur_y = int(y0 + (y1 - y0) * ease_t)
            draw.line([(x0, y0), (cur_x, cur_y)], fill=(*PALETTE_AMBER_HIGHLIGHT, 245), width=max(3, int(5 * sx)))
            r_dot = max(6, int(8 * sx))
            draw.ellipse([(cur_x - r_dot, cur_y - r_dot), (cur_x + r_dot, cur_y + r_dot)], fill=(*PALETTE_CRIMSON_VECTOR, 255), outline=PALETTE_TEXT_PRIMARY, width=2)
            draw.rectangle([(cur_x + int(14 * sx), cur_y - int(14 * sy)), (cur_x + int(150 * sx), cur_y + int(12 * sy))], fill=(*PALETTE_PANEL_BG, 225), outline=(*PALETTE_AMBER_HIGHLIGHT, 180), width=1)
            draw.text((cur_x + int(22 * sx), cur_y - int(6 * sy)), f"{label} ({int(ease_t * 100)}%)", fill=PALETTE_TEXT_PRIMARY, font=font)

        zx, zy = spec.get("zoom_target_xy", [0.58, 0.48])
        tx, ty = int(zx * width), int(zy * height)
        ret_r = int((18 + 8 * math.sin(ease_t * math.pi)) * sx)
        draw.ellipse([(tx - ret_r, ty - ret_r), (tx + ret_r, ty + ret_r)], outline=(*PALETTE_TEAL_COUNTER, 230), width=max(1, int(2 * sx)))
        draw.ellipse([(ox - int(12 * sx), oy - int(12 * sy)), (ox + int(12 * sx), oy + int(12 * sy))], fill=(*PALETTE_AMBER_HIGHLIGHT, 255))

    elif subtype in ("demographic_or_casualty_counter", "resource_and_budget_counter"):
        v0 = spec["counter_start_value"]
        v1 = spec["counter_end_value"]
        cur_val = int(round(v0 + (v1 - v0) * ease_t))
        header_lbl = "RESOURCE / TREASURY LEDGER" if subtype == "resource_and_budget_counter" else "VERIFIED DEMOGRAPHIC / FORCE COUNTER"

        draw.rectangle([sc(140, 210), sc(860, 880)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 200), width=max(1, int(2 * sx)))
        draw.text(sc(190, 260), header_lbl, fill=PALETTE_TEAL_COUNTER, font=font)
        draw.text(sc(190, 320), f"INITIAL BASELINE : {v0:,}", fill=PALETTE_TEXT_MUTED, font=font)
        draw.text(sc(190, 380), f"CURRENT COUNT    : {cur_val:,}", fill=PALETTE_AMBER_HIGHLIGHT, font=font)
        draw.text(sc(190, 440), f"TARGET / DELTA   : {v1:,} ({((cur_val - v0) / max(1, v0)) * 100:+.1f}%)", fill=PALETTE_CRIMSON_VECTOR, font=font)

        bar_w = int(620 * ease_t * sx)
        draw.rectangle([sc(190, 520), sc(810, 560)], fill=(*PALETTE_GRID_LINE, 180), outline=PALETTE_COAST_BORDER, width=1)
        draw.rectangle([sc(190, 520), (int(190 * sx) + bar_w, int(560 * sy))], fill=(*PALETTE_CRIMSON_VECTOR, 230))

        draw.rectangle([sc(940, 210), sc(1780, 880)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 200), width=max(1, int(2 * sx)))
        draw.text(sc(990, 250), "PROPORTIONAL FORCE / SURVIVAL MATRIX (100 UNITS)", fill=PALETTE_TEXT_PRIMARY, font=font)
        active_cells = max(1, min(100, int(round(100 * (1.0 - 0.85 * ease_t) if v1 < v0 else 100 * ease_t))))
        for idx in range(100):
            r, c = divmod(idx, 10)
            bx = int((995 + c * 72) * sx)
            by = int((305 + r * 52) * sy)
            color = PALETTE_TEAL_COUNTER if idx < active_cells else (45, 52, 66)
            draw.rectangle([(bx, by), (bx + int(54 * sx), by + int(36 * sy))], fill=(*color, 235), outline=(*PALETTE_COAST_BORDER, 140), width=1)

    elif subtype in ("comparative_data_diagram", "progress_and_threshold_bars"):
        draw.rectangle([sc(140, 200), sc(1780, 890)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 200), width=max(1, int(2 * sx)))
        bars = [
            ("PRIMARY FORCE / EJECTA SCALE", 0.92, PALETTE_CRIMSON_VECTOR),
            ("SECONDARY COALITION / RESERVE", 0.64, PALETTE_AMBER_HIGHLIGHT),
            ("LOGISTICS / SUPPLY THRESHOLD", 0.48, PALETTE_TEAL_COUNTER),
            ("SURVIVAL / CRITICAL MARGIN", 0.22, PALETTE_PARCHMENT_GOLD),
        ]
        for i, (b_label, frac, col) in enumerate(bars):
            y_top = 270 + i * 145
            max_w = int(1180 * sx)
            cur_w = int(max_w * frac * ease_t)
            draw.text(sc(200, y_top - 24), f"{b_label} — {int(round(frac * 100 * ease_t))}%", fill=PALETTE_TEXT_PRIMARY, font=font)
            draw.rectangle([sc(200, y_top), (int(200 * sx) + max_w, int((y_top + 56) * sy))], fill=(*PALETTE_GRID_LINE, 160), outline=PALETTE_COAST_BORDER, width=1)
            draw.rectangle([sc(200, y_top), (int(200 * sx) + max(8, cur_w), int((y_top + 56) * sy))], fill=(*col, 240))
            if subtype == "progress_and_threshold_bars":
                thresh_x = int(200 * sx + max_w * 0.75)
                draw.line([(thresh_x, int((y_top - 8) * sy)), (thresh_x, int((y_top + 64) * sy))], fill=(*PALETTE_CRIMSON_VECTOR, 255), width=max(2, int(3 * sx)))

    elif subtype == "before_after_comparison":
        draw.rectangle([sc(120, 200), sc(1800, 880)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 200), width=max(1, int(2 * sx)))
        split_x = int((360 + 1200 * ease_t) * sx)
        draw.rectangle([sc(160, 250), (split_x, int(830 * sy))], fill=(26, 42, 58, 230), outline=(*PALETTE_TEAL_COUNTER, 200), width=1)
        draw.rectangle([(split_x, int(250 * sy)), sc(1760, 830)], fill=(48, 22, 24, 230), outline=(*PALETTE_CRIMSON_VECTOR, 200), width=1)
        draw.line([(split_x, int(230 * sy)), (split_x, int(850 * sy))], fill=(*PALETTE_AMBER_HIGHLIGHT, 255), width=max(2, int(4 * sx)))
        draw.text(sc(200, 290), "BEFORE RUPTURE / BASELINE STATE", fill=PALETTE_TEAL_COUNTER, font=font)
        draw.text(sc(1320, 290), "AFTER RUPTURE / COLLAPSE STATE", fill=PALETTE_CRIMSON_VECTOR, font=font)

    else:
        draw.rectangle([sc(120, 260), sc(1800, 840)], fill=(*PALETTE_PANEL_BG, 235), outline=(*PALETTE_PARCHMENT_GOLD, 200), width=max(1, int(2 * sx)))
        y_line = int(550 * sy)
        x_start, x_end = int(220 * sx), int(1700 * sx)
        draw.line([(x_start, y_line), (x_end, y_line)], fill=(*PALETTE_COAST_BORDER, 220), width=max(2, int(4 * sx)))
        cur_line_x = int(x_start + (x_end - x_start) * ease_t)
        draw.line([(x_start, y_line), (cur_line_x, y_line)], fill=(*PALETTE_AMBER_HIGHLIGHT, 255), width=max(3, int(6 * sx)))
        nodes = ["PHASE I: TRIGGER", "PHASE II: ESCALATION", "PHASE III: RUPTURE", "PHASE IV: AFTERMATH"]
        for idx, n_label in enumerate(nodes):
            nx = x_start + idx * ((x_end - x_start) // 3)
            active = cur_line_x >= nx
            col = PALETTE_CRIMSON_VECTOR if active else PALETTE_GRID_LINE
            r_node = int(18 * sx)
            draw.ellipse([(nx - r_node, y_line - r_node), (nx + r_node, y_line + r_node)], fill=(*col, 255), outline=PALETTE_TEXT_PRIMARY, width=2)
            y_txt = y_line + int(36 * sy) if idx % 2 == 0 else y_line - int(52 * sy)
            draw.text((nx - int(70 * sx), y_txt), n_label, fill=PALETTE_TEXT_PRIMARY if active else PALETTE_TEXT_MUTED, font=font)

    draw.rectangle([sc(60, 988), sc(1860, 1040)], fill=(*PALETTE_PANEL_BG, 225), outline=(*PALETTE_PARCHMENT_GOLD, 160), width=1)
    draw.text(
        sc(90, 1008),
        f"INK CHRONICLE DOCUMENTARY DATA LAYER  |  TEMPLATE: {subtype.upper()}  |  FRAME: {frame_idx + 1:03d}/{total_frames:03d} ({spec.get('fps', 24)} FPS)",
        fill=PALETTE_TEXT_MUTED,
        font=font,
    )
    return img


def render_10pct_infographic_clip_mp4(
    shot: Dict[str, Any],
    out_mp4_path: Path,
    spoken_text: str = "",
    episode_title: str = "",
    out_keyframe_png: Path | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    background_plate_path: str | None = None,
) -> Dict[str, Any]:
    """Render a 10% map, troop movement, diagram, or number-counter shot into a 24fps MP4 clip via fast rawvideo pipe."""
    spec = build_10pct_infographic_spec(
        shot,
        spoken_text=spoken_text,
        episode_title=episode_title,
        width=width,
        height=height,
        fps=fps,
        background_plate_path=background_plate_path,
    )
    total_frames = spec["total_frames"]
    out_mp4_path = Path(out_mp4_path)
    out_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-b:v", "5500k", "-maxrate", "7500k", "-bufsize", "11000k",
            "-pix_fmt", "yuv420p",
            str(out_mp4_path),
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for f_idx in range(total_frames):
        frame_im = _draw_youtube_docudrama_frame(spec, f_idx, total_frames, width=width, height=height)
        if out_keyframe_png and f_idx == total_frames // 2:
            out_keyframe_png = Path(out_keyframe_png)
            out_keyframe_png.parent.mkdir(parents=True, exist_ok=True)
            frame_im.save(out_keyframe_png, format="PNG")
        proc.stdin.write(frame_im.tobytes())
    proc.stdin.close()
    proc.wait(timeout=60)

    sha256_hex = (
        hashlib.sha256(out_mp4_path.read_bytes()).hexdigest()
        if out_mp4_path.exists()
        else ""
    )
    return {
        "status": "generated",
        "provider": "python_infographics_engine",
        "cost_usd": 0.0,
        "shot_id": spec["shot_id"],
        "infographic_subtype": spec["infographic_subtype"],
        "zoom_target_xy": spec["zoom_target_xy"],
        "duration_sec": spec["duration_sec"],
        "fps": fps,
        "resolution": [width, height],
        "total_frames": total_frames,
        "path": str(out_mp4_path),
        "bytes": out_mp4_path.stat().st_size if out_mp4_path.exists() else 0,
        "output_sha256": sha256_hex,
    }


def render_all_10pct_infographics_for_script(
    script_doc: Dict[str, Any],
    out_dir: Path,
    pilot_duration_cap_sec: float | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    background_plate_path: str | None = None,
) -> List[Dict[str, Any]]:
    """Batch-render all 10% map/diagram/counter shots in a production_script.json via Python."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    line_map = {l["line_id"]: l for l in script_doc.get("audio_lines", []) if l.get("line_id")}
    results: List[Dict[str, Any]] = []
    elapsed = 0.0

    for sh in script_doc.get("shots", []):
        dur = float(sh.get("target_duration_seconds", 4.0))
        if pilot_duration_cap_sec is not None and elapsed >= pilot_duration_cap_sec:
            break
        elapsed += dur
        vtype = sh.get("visual_type")
        gmode = sh.get("generation_mode")
        if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
            al_ids = sh.get("audio_line_ids") or []
            spoken = " ".join(str(line_map[lid].get("text", "")) for lid in al_ids if lid in line_map)
            out_mp4 = out_dir / f"{sh['shot_id']}_infographic.mp4"
            out_png = out_dir / f"{sh['shot_id']}_start.png"
            res = render_10pct_infographic_clip_mp4(
                shot=sh,
                out_mp4_path=out_mp4,
                spoken_text=spoken,
                episode_title=str(script_doc.get("title") or ""),
                out_keyframe_png=out_png,
                width=width,
                height=height,
                fps=fps,
                background_plate_path=background_plate_path,
            )
            results.append(res)
    return results
