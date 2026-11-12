"""30% Cinematic 2.5D Image Animation Engine from Existing Generated Images (`cinematic_image_animator.py`, v4.3).

SUPERSEDED (v4.3 plan P5, 2026-11-12): the episode runner renders still_25d shots with `production/layers25d.py`
(real depth planes, rigid faces, motion imitation, measured gates). This module stays only for the archive's tests
until P9 retires it; its keyword-guessed effects and one-sheet warp are not on the v4.3 path.

Extends `explainer_engine.production.parallax` and `explainer_engine.production.depth` to turn
existing high-quality episode keyframes into living 24fps cinematic sequences at zero API cost:
1. Reuses existing episode-scoped generated images without regenerating or altering character designs.
2. Multi-plane 2.5D depth parallax (`parallax.shift` + `estimate_synthetic_depth_and_face_safe_mask`)
   across both X and Y axes while protecting character facial geometry (`protect_character_faces=True`).
3. Multi-axis smoothstep camera trajectories (`dolly_in`, `dolly_out`, `pan_horizontal`, `pan_vertical`,
   `orbital_left`, `orbital_right`, `pan_and_push_ne`, `pan_and_push_nw`, `pan_and_pull_se`, `zoom_focus`)
   with strict edge-safe bounding box clamping (`compute_camera_trajectory_box`).
4. Procedural atmospheric & lighting motion layers (`fog`, `smoke`, `dust`, `ash`, `rain`, `snow`,
   `fire_flicker`, `light_shadow_pulse`).
"""
from __future__ import annotations

import hashlib
import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image

from explainer_engine.production import parallax as PAR

ATMOSPHERIC_EFFECTS = (
    "fog",
    "smoke",
    "dust",
    "ash",
    "rain",
    "snow",
    "fire_flicker",
    "light_shadow_pulse",
)

CAMERA_PRESETS = (
    "dolly_in",
    "dolly_out",
    "pan_horizontal",
    "pan_vertical",
    "orbital_left",
    "orbital_right",
    "pan_and_push_ne",
    "pan_and_push_nw",
    "pan_and_pull_se",
    "zoom_focus",
)


def smoothstep(u: float) -> float:
    """Hermite cubic smoothstep easing (`3u^2 - 2u^3`) on `0.0 <= u <= 1.0`."""
    x = float(min(1.0, max(0.0, u)))
    return x * x * (3.0 - 2.0 * x)


def compute_camera_trajectory_box(
    preset: str,
    u: float,
    width: int = 1920,
    height: int = 1080,
    focal_xy: Sequence[float] = (0.5, 0.5),
    shake_dx: float = 0.0,
    shake_dy: float = 0.0,
) -> Tuple[Tuple[float, float, float, float], float, float, float, float]:
    """Compute edge-safe `(x0, y0, x1, y1)` crop box and `(sign_x, sign_y, amp_x, amp_y)` for `preset` at progress `u`."""
    ease_u = smoothstep(u)
    fx = float(min(0.85, max(0.15, focal_xy[0] if len(focal_xy) >= 2 else 0.5)))
    fy = float(min(0.85, max(0.15, focal_xy[1] if len(focal_xy) >= 2 else 0.5)))

    if preset in ("dolly_out", "slow_pull_back"):
        z = 1.11 - 0.09 * ease_u
        dx_norm = (fx - 0.5) * 0.04 * (1.0 - ease_u)
        dy_norm = (fy - 0.5) * 0.03 * (1.0 - ease_u)
        sign_x, sign_y = -1.0, -0.5
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.4
    elif preset in ("pan_horizontal", "orbital_right", "pan_slide"):
        z = 1.07 + 0.02 * math.sin(math.pi * ease_u)
        dx_norm = (ease_u - 0.5) * 0.055
        dy_norm = (fy - 0.5) * 0.02 * ease_u
        sign_x, sign_y = 1.0, 0.35
        amp_x, amp_y = PAR.DEFAULT_AMP * 1.15, PAR.DEFAULT_AMP * 0.35
    elif preset == "orbital_left":
        z = 1.07 + 0.02 * math.sin(math.pi * ease_u)
        dx_norm = (0.5 - ease_u) * 0.055
        dy_norm = (0.5 - fy) * 0.02 * ease_u
        sign_x, sign_y = -1.0, -0.35
        amp_x, amp_y = PAR.DEFAULT_AMP * 1.15, PAR.DEFAULT_AMP * 0.35
    elif preset == "pan_vertical":
        z = 1.07 + 0.02 * ease_u
        dx_norm = (fx - 0.5) * 0.025 * ease_u
        dy_norm = (0.5 - ease_u) * 0.055
        sign_x, sign_y = 0.5, -1.0
        amp_x, amp_y = PAR.DEFAULT_AMP * 0.45, PAR.DEFAULT_AMP
    elif preset == "pan_and_push_ne":
        z = 1.03 + 0.08 * ease_u
        dx_norm = (ease_u - 0.5) * 0.045
        dy_norm = (0.5 - ease_u) * 0.035
        sign_x, sign_y = 1.0, -1.0
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.65
    elif preset == "pan_and_push_nw":
        z = 1.03 + 0.08 * ease_u
        dx_norm = (0.5 - ease_u) * 0.045
        dy_norm = (0.5 - ease_u) * 0.035
        sign_x, sign_y = -1.0, -1.0
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.65
    elif preset == "pan_and_pull_se":
        z = 1.11 - 0.08 * ease_u
        dx_norm = (ease_u - 0.5) * 0.045
        dy_norm = (ease_u - 0.5) * 0.035
        sign_x, sign_y = 1.0, 1.0
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.65
    elif preset == "zoom_focus":
        z = 1.02 + 0.10 * ease_u
        dx_norm = (fx - 0.5) * 0.06 * ease_u
        dy_norm = (fy - 0.5) * 0.06 * ease_u
        sign_x, sign_y = 1.0, 0.5
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.5
    else:
        # dolly_in with subtle multi-axis drift toward focal_xy
        z = 1.02 + 0.085 * ease_u
        dx_norm = (fx - 0.5) * 0.035 * ease_u
        dy_norm = (fy - 0.5) * 0.025 * ease_u
        sign_x, sign_y = 1.0, 0.4
        amp_x, amp_y = PAR.DEFAULT_AMP, PAR.DEFAULT_AMP * 0.4

    dx_norm += shake_dx
    dy_norm += shake_dy

    crop_w = min(float(width), width / max(z, 1.001))
    crop_h = min(float(height), height / max(z, 1.001))
    cx = (width / 2.0) + dx_norm * width
    cy = (height / 2.0) + dy_norm * height
    x0 = max(0.0, min(float(width) - crop_w, cx - crop_w / 2.0))
    y0 = max(0.0, min(float(height) - crop_h, cy - crop_h / 2.0))
    box = (x0, y0, x0 + crop_w, y0 + crop_h)
    return box, sign_x, sign_y, amp_x, amp_y


def infer_atmospheric_effects_for_shot(shot: Dict[str, Any]) -> List[str]:
    """Infer appropriate atmospheric and lighting motion layers from shot narrative and lighting metadata."""
    explicit = shot.get("atmospheric_effects")
    if isinstance(explicit, list) and explicit:
        return [str(x) for x in explicit if str(x) in ATMOSPHERIC_EFFECTS]

    text = " ".join([
        str(shot.get("narrative_purpose") or ""),
        str(shot.get("action_start_state") or ""),
        str(shot.get("action_end_state") or ""),
        str(shot.get("lighting_and_time") or ""),
        str((shot.get("video_prompt") or {}).get("motion_prompt") or ""),
    ]).lower()

    effects: List[str] = ["light_shadow_pulse"]
    if any(k in text for k in ("ash", "volcan", "toba", "eruption", "ember", "pyroclastic", "caldera")):
        effects.extend(["ash", "smoke", "fire_flicker"])
    if any(k in text for k in ("rain", "storm", "mud", "downpour", "monsoon", "waterloo")):
        effects.extend(["rain", "fog"])
    if any(k in text for k in ("snow", "winter", "blizzard", "frost", "ice")):
        effects.extend(["snow", "fog"])
    if any(k in text for k in ("candle", "torch", "lantern", "hearth", "fire", "flame", "lamp")):
        if "fire_flicker" not in effects:
            effects.append("fire_flicker")
    if any(k in text for k in ("dust", "library", "archive", "vault", "interior", "parchment", "sunbeam", "shelter", "cave")):
        effects.append("dust")
    if len(effects) == 1:
        effects.extend(["dust", "fog"])
    return list(dict.fromkeys(effects))


def _apply_atmospheric_and_lighting_layers(
    frame_rgb: np.ndarray,
    u: float,
    frame_idx: int,
    fps: int,
    effects: Sequence[str],
    seed: int,
    yy: np.ndarray,
    xx: np.ndarray,
) -> np.ndarray:
    """Apply fast vectorized procedural fog, smoke, ash, dust, rain, snow, and firelight flicker."""
    h, w, _ = frame_rgb.shape
    out = frame_rgb.astype(np.float32)
    t_sec = frame_idx / max(fps, 1)

    if "fire_flicker" in effects or "light_shadow_pulse" in effects:
        pulse = 0.045 * math.sin(2.0 * math.pi * 1.35 * t_sec + (seed % 17))
        if "fire_flicker" in effects:
            pulse += 0.035 * math.sin(2.0 * math.pi * 4.2 * t_sec + (seed % 31))
        out[:, :, 0] *= 1.0 + pulse * 1.15
        out[:, :, 1] *= 1.0 + pulse * 0.75
        out[:, :, 2] *= 1.0 + pulse * 0.25

    if "fog" in effects or "smoke" in effects:
        wx = 0.5 + 0.5 * np.sin(2.0 * math.pi * (xx * 2.5 + 0.35 * t_sec))
        wy = (0.5 + 0.5 * np.cos(2.0 * math.pi * (yy * 1.8 - 0.15 * t_sec))) * np.clip((yy - 0.20) / 0.80, 0.0, 1.0)
        fog_alpha = (0.11 * (wy * wx))[:, :, None]
        fog_color = np.array([150.0, 158.0, 170.0] if "fog" in effects else [110.0, 102.0, 96.0], dtype=np.float32)
        out = out * (1.0 - fog_alpha) + fog_color[None, None, :] * fog_alpha

    if any(k in effects for k in ("ash", "dust", "snow")):
        rng = np.random.default_rng(seed + 101)
        n_particles = 42 if "ash" in effects or "snow" in effects else 26
        px0 = rng.uniform(0.0, 1.0, n_particles)
        py0 = rng.uniform(0.0, 1.0, n_particles)
        vx = rng.uniform(-0.06, 0.08, n_particles)
        vy = rng.uniform(-0.14, -0.04, n_particles) if "ash" in effects else (
            rng.uniform(0.12, 0.24, n_particles) if "snow" in effects else rng.uniform(-0.03, 0.03, n_particles)
        )
        radii = rng.integers(2, max(3, int(round(5 * (w / 1920.0)))), n_particles)
        is_ember = rng.uniform(0.0, 1.0, n_particles) < (0.45 if "ash" in effects else 0.0)

        for i in range(n_particles):
            cx = int(((px0[i] + vx[i] * t_sec + 0.015 * math.sin(2.5 * t_sec + i)) % 1.0) * (w - 1))
            cy = int(((py0[i] + vy[i] * t_sec) % 1.0) * (h - 1))
            r = int(radii[i])
            y0_p, y1_p = max(0, cy - r), min(h, cy + r + 1)
            x0_p, x1_p = max(0, cx - r), min(w, cx + r + 1)
            if is_ember[i]:
                col = np.array([255.0, 148.0, 52.0], dtype=np.float32)
                alpha = 0.72
            elif "snow" in effects:
                col = np.array([235.0, 242.0, 250.0], dtype=np.float32)
                alpha = 0.55
            else:
                col = np.array([210.0, 202.0, 188.0], dtype=np.float32)
                alpha = 0.38
            out[y0_p:y1_p, x0_p:x1_p] = out[y0_p:y1_p, x0_p:x1_p] * (1.0 - alpha) + col * alpha

    if "rain" in effects:
        rng_r = np.random.default_rng(seed + 303 + frame_idx)
        n_drops = 36
        rx = rng_r.integers(10, w - 25, n_drops)
        ry = rng_r.integers(10, h - 45, n_drops)
        rain_col = np.array([185.0, 200.0, 220.0], dtype=np.float32)
        for dx_r, dy_r in zip(rx, ry):
            for step in range(12):
                yy_p = min(h - 1, int(dy_r + step * 2))
                xx_p = min(w - 1, int(dx_r + step * 0.5))
                out[yy_p, xx_p] = out[yy_p, xx_p] * 0.55 + rain_col * 0.45

    return np.clip(out, 0.0, 255.0).astype(np.uint8)


def render_cinematic_25d_clip_from_image(
    shot: Dict[str, Any],
    source_image_path: Path | str,
    out_mp4_path: Path | str,
    end_image_path: Path | str | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    protect_character_faces: bool = True,
    camera_shake_intensity: float | None = None,
) -> Dict[str, Any]:
    """Animate an existing generated image (or start->end keyframe pair) into a 24fps cinematic MP4 using multi-axis
    2.5D parallax and procedural atmospheric layers streamed directly via rawvideo pipe at $0.00 cost."""
    source_image_path = Path(source_image_path)
    out_mp4_path = Path(out_mp4_path)
    out_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    sid = str(shot.get("shot_id") or source_image_path.stem)
    dur = float(shot.get("target_duration_seconds", 4.0))
    total_frames = max(fps, int(round(dur * fps)))

    # Cycle varied multi-axis presets when not explicitly locked so consecutive shots have distinct camera trajectories
    seed = int(hashlib.sha256(sid.encode("utf-8")).hexdigest()[:8], 16)
    explicit_preset = (shot.get("video_prompt") or {}).get("parallax_preset")
    if explicit_preset and str(explicit_preset) not in ("dolly_in", "static"):
        preset = str(explicit_preset)
    else:
        varied_presets = ("pan_and_push_ne", "dolly_in", "orbital_right", "pan_and_push_nw", "dolly_out", "orbital_left", "zoom_focus")
        preset = varied_presets[seed % len(varied_presets)]

    focal_xy = shot.get("focal_xy") or [0.52, 0.46]
    effects = infer_atmospheric_effects_for_shot(shot)

    if camera_shake_intensity is None:
        text_low = " ".join([
            str(shot.get("narrative_purpose") or ""),
            str(shot.get("action_start_state") or ""),
        ]).lower()
        camera_shake_intensity = 0.005 if any(k in text_low for k in ("eruption", "cannon", "explosion", "quake", "shockwave", "impact")) else 0.0

    src_img = Image.open(source_image_path).convert("RGB").resize((width, height), Image.BICUBIC)
    end_img = None
    if end_image_path and Path(end_image_path).is_file() and Path(end_image_path) != source_image_path:
        end_img = Image.open(end_image_path).convert("RGB").resize((width, height), Image.BICUBIC)

    depth_map = PAR.load(source_image_path)
    if depth_map is None:
        depth_map, face_mask = PAR.estimate_synthetic_depth_and_face_safe_mask(
            src_img,
            protect_center_character=protect_character_faces,
        )
    else:
        _, face_mask = PAR.estimate_synthetic_depth_and_face_safe_mask(
            src_img,
            protect_center_character=protect_character_faces,
        )

    rng_shake = np.random.default_rng(seed + 77)
    yy = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :]

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
        u = f_idx / max(1, total_frames - 1)
        ease_u = smoothstep(u)

        shake_dx, shake_dy = 0.0, 0.0
        if camera_shake_intensity > 0:
            decay = math.exp(-2.5 * u)
            shake_dx = float(rng_shake.uniform(-1.0, 1.0) * camera_shake_intensity * decay)
            shake_dy = float(rng_shake.uniform(-1.0, 1.0) * camera_shake_intensity * decay)

        box, sign_x, sign_y, amp_x, amp_y = compute_camera_trajectory_box(
            preset=preset,
            u=u,
            width=width,
            height=height,
            focal_xy=focal_xy,
            shake_dx=shake_dx,
            shake_dy=shake_dy,
        )

        if end_img is not None and 0.35 <= ease_u <= 1.0:
            blend_w = smoothstep((ease_u - 0.35) / 0.65)
            crop_a = np.asarray(src_img.resize((width, height), Image.BILINEAR, box=box), dtype=np.float32)
            crop_b = np.asarray(end_img.resize((width, height), Image.BILINEAR, box=box), dtype=np.float32)
            cropped = Image.fromarray(np.clip(crop_a * (1.0 - blend_w) + crop_b * blend_w, 0.0, 255.0).astype(np.uint8), mode="RGB")
        else:
            cropped = src_img.resize((width, height), Image.BILINEAR, box=box)

        shifted = PAR.shift(
            frame=cropped,
            depth=depth_map,
            box=box,
            src_size=(width, height),
            u=ease_u,
            amp=amp_x,
            sign=sign_x,
            dy_amp=amp_y,
            sign_y=sign_y,
        )

        frame_arr = _apply_atmospheric_and_lighting_layers(
            frame_rgb=np.asarray(shifted),
            u=ease_u,
            frame_idx=f_idx,
            fps=fps,
            effects=effects,
            seed=seed,
            yy=yy,
            xx=xx,
        )
        proc.stdin.write(frame_arr.tobytes())

    proc.stdin.close()
    proc.wait(timeout=60)

    sha256_hex = (
        hashlib.sha256(out_mp4_path.read_bytes()).hexdigest()
        if out_mp4_path.exists()
        else ""
    )
    return {
        "status": "generated",
        "provider": "python_25d_cinematic_animator",
        "cost_usd": 0.0,
        "shot_id": sid,
        "source_image_path": str(source_image_path),
        "end_image_path": str(end_image_path) if end_image_path else None,
        "reused_existing_image": True,
        "protect_character_faces": protect_character_faces,
        "face_safe_mask_active": bool(face_mask.max() > 0.1),
        "parallax_preset": preset,
        "atmospheric_effects": effects,
        "camera_shake_intensity": camera_shake_intensity,
        "duration_sec": dur,
        "fps": fps,
        "resolution": [width, height],
        "total_frames": total_frames,
        "path": str(out_mp4_path),
        "bytes": out_mp4_path.stat().st_size if out_mp4_path.exists() else 0,
        "output_sha256": sha256_hex,
    }
