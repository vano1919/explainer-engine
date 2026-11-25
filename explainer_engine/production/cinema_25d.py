"""Continuous Depthflow-style zero-tear 2.5D parallax renderer using Depth Anything V2 Small ONNX."""
from __future__ import annotations

import hashlib
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from explainer_engine.finish.cinema_grade import (
    DEFAULT_CINEMA_GRADE,
    CinemaGradeSpec,
    apply_unified_film_grade,
)

DEFAULT_ONNX_CANDIDATES = (
    Path("/working_dir/c_1b68d4d8925e93a3/external_assets/depth_onnx/depth_anything_v2_small_q4.onnx"),
    Path("assets/models/depth_anything_v2_small_q4.onnx"),
    Path("assets/models/depth_anything_v2_small.onnx"),
)

_ONNX_SESSION: Any = None
_ONNX_MODEL_LOADED: str | None = None
_DEPTH_CACHE: dict[str, np.ndarray] = {}


def _resolve_depth_onnx() -> Path | None:
    env_p = os.environ.get("EE_DEPTH_ONNX_PATH", "").strip()
    if env_p and Path(env_p).is_file():
        return Path(env_p)
    for cand in DEFAULT_ONNX_CANDIDATES:
        if cand.is_file():
            return cand
    return None


def estimate_continuous_depth(image_rgb: np.ndarray, *, cache_key: str | None = None) -> tuple[np.ndarray, str]:
    """Return a smooth, continuous ``[0, 1]`` float32 depth map (1=near, 0=far) and backend name."""
    global _ONNX_SESSION, _ONNX_MODEL_LOADED
    h, w = image_rgb.shape[:2]
    if cache_key and cache_key in _DEPTH_CACHE:
        cached = _DEPTH_CACHE[cache_key]
        if cached.shape == (h, w):
            return cached, _ONNX_MODEL_LOADED or "cached"

    model_p = _resolve_depth_onnx()
    backend = "continuous_gradient_fallback"
    depth_raw: np.ndarray | None = None

    if model_p is not None:
        try:
            import onnxruntime as ort

            if _ONNX_SESSION is None or str(model_p) != _ONNX_MODEL_LOADED:
                _ONNX_SESSION = ort.InferenceSession(str(model_p), providers=["CPUExecutionProvider"])
                _ONNX_MODEL_LOADED = str(model_p)
            inp = _ONNX_SESSION.get_inputs()[0]
            resized = cv2.resize(image_rgb, (518, 518), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            tensor = ((resized - mean) / std).transpose(2, 0, 1)[None, ...]
            pred = _ONNX_SESSION.run(None, {inp.name: tensor})[0]
            pred_2d = np.squeeze(pred).astype(np.float32)
            p_lo, p_hi = float(np.percentile(pred_2d, 2.0)), float(np.percentile(pred_2d, 98.0))
            norm = np.clip((pred_2d - p_lo) / max(1e-5, p_hi - p_lo), 0.0, 1.0)
            depth_raw = cv2.resize(norm, (w, h), interpolation=cv2.INTER_CUBIC)
            backend = f"depth_anything_v2_small_onnx:{model_p.name}"
        except Exception:
            depth_raw = None

    if depth_raw is None:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        yn = yy / max(1.0, h - 1.0)
        xn = (xx / max(1.0, w - 1.0) - 0.5) * 2.0
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        detail = cv2.GaussianBlur(np.abs(cv2.Laplacian(gray, cv2.CV_32F)), (0, 0), w * 0.035)
        detail = detail / max(1e-5, float(detail.max()))
        depth_raw = np.clip(0.55 * yn + 0.25 * (1.0 - 0.5 * xn * xn) + 0.20 * detail, 0.0, 1.0)

    assert depth_raw is not None
    sigma = max(11.0, min(w, h) * 0.028)
    depth_smooth = cv2.GaussianBlur(np.asarray(depth_raw, dtype=np.float32), (0, 0), sigmaX=sigma, sigmaY=sigma)
    d_min, d_max = float(depth_smooth.min()), float(depth_smooth.max())
    depth_norm = np.clip((depth_smooth - d_min) / max(1e-5, d_max - d_min), 0.0, 1.0).astype(np.float32)

    if cache_key:
        _DEPTH_CACHE[cache_key] = depth_norm
    return depth_norm, backend


def _living_ease(u: float) -> float:
    """Blended linear + smoothstep curve: visibly alive from frame 0, never frozen at start/end."""
    u = max(0.0, min(1.0, u))
    smooth = u * u * (3.0 - 2.0 * u)
    return 0.42 * u + 0.58 * smooth


def _apply_atmosphere_and_light(
    frame: np.ndarray,
    *,
    t_s: float,
    atmosphere: str,
    warm_flicker: bool,
    seed: int,
) -> np.ndarray:
    """Subtle physically motivated atmosphere (dust, embers, rain, snow, mist) & gentle light breathing."""
    h, w = frame.shape[:2]
    out = frame.astype(np.float32)

    if warm_flicker:
        flick = 1.0 + 0.032 * math.sin(t_s * 6.7 + seed) + 0.018 * math.sin(t_s * 13.3 + seed * 1.7)
        luma = (0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]) / 255.0
        warm_w = np.clip((luma - 0.25) / 0.65, 0.0, 1.0)[..., None]
        tint = np.array([flick, 1.0 + (flick - 1.0) * 0.55, 1.0 - (flick - 1.0) * 0.25], dtype=np.float32)
        out = out * (1.0 - warm_w) + (out * tint[None, None, :]) * warm_w

    if atmosphere in ("dust", "embers", "mist", "rain", "snow"):
        rng = np.random.default_rng(seed + 4099)
        overlay = np.zeros((h, w, 3), dtype=np.float32)
        if atmosphere in ("dust", "embers"):
            n_part = 38 if atmosphere == "dust" else 28
            px0 = rng.uniform(0, w, n_part)
            py0 = rng.uniform(0, h, n_part)
            vx = rng.uniform(-14.0, 22.0, n_part)
            vy = rng.uniform(-28.0, -9.0, n_part) if atmosphere == "embers" else rng.uniform(-8.0, 6.0, n_part)
            rad = rng.uniform(1.5, 3.6, n_part)
            col = (245.0, 150.0, 65.0) if atmosphere == "embers" else (218.0, 210.0, 192.0)
            alpha_scale = 0.34 if atmosphere == "embers" else 0.18
            for i in range(n_part):
                cx = int((px0[i] + vx[i] * t_s + 12.0 * math.sin(t_s * 1.4 + i)) % w)
                cy = int((py0[i] + vy[i] * t_s) % h)
                cv2.circle(overlay, (cx, cy), max(1, int(rad[i])), col, -1, lineType=cv2.LINE_AA)
            overlay = cv2.GaussianBlur(overlay, (0, 0), 2.2)
            out = out + overlay * alpha_scale
        elif atmosphere == "mist":
            yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
            xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
            wave = 0.5 + 0.5 * np.sin(xx * 4.5 - t_s * 0.45 + seed) * np.cos(yy * 3.0 + t_s * 0.2)
            band = np.clip((yy - 0.30) / 0.70, 0.0, 1.0) * wave * 0.10
            fog_col = np.array([182.0, 192.0, 200.0], dtype=np.float32)[None, None, :]
            out = out * (1.0 - band[..., None]) + fog_col * band[..., None]
        elif atmosphere == "rain":
            n_drops = 110
            rx0 = rng.uniform(0, w, n_drops)
            ry0 = rng.uniform(0, h, n_drops)
            spd = rng.uniform(420.0, 680.0, n_drops)
            for i in range(n_drops):
                x1 = int((rx0[i] - 55.0 * t_s) % w)
                y1 = int((ry0[i] + spd[i] * t_s) % h)
                cv2.line(overlay, (x1, y1), (x1 - 4, y1 + 18), (195.0, 208.0, 222.0), 1, lineType=cv2.LINE_AA)
            out = out + overlay * 0.22
        elif atmosphere == "snow":
            n_flakes = 85
            sx0 = rng.uniform(0, w, n_flakes)
            sy0 = rng.uniform(0, h, n_flakes)
            spd_y = rng.uniform(55.0, 140.0, n_flakes)
            spd_x = rng.uniform(-75.0, -25.0, n_flakes)
            rad = rng.uniform(1.2, 3.0, n_flakes)
            for i in range(n_flakes):
                cx = int((sx0[i] + spd_x[i] * t_s + 14.0 * math.sin(t_s * 2.1 + i)) % w)
                cy = int((sy0[i] + spd_y[i] * t_s) % h)
                cv2.circle(overlay, (cx, cy), max(1, int(rad[i])), (235.0, 240.0, 246.0), -1, lineType=cv2.LINE_AA)
            overlay = cv2.GaussianBlur(overlay, (0, 0), 1.4)
            out = out + overlay * 0.34

    return np.clip(out, 0.0, 255.0).astype(np.uint8)


def _fit_aspect_preserving_canvas(src_rgb: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
    """Fit any source still to target 16:9 canvas without stretching or decapitating vertical portraits."""
    sh, sw = src_rgb.shape[:2]
    src_aspect = sw / max(1.0, float(sh))
    dst_aspect = target_w / max(1.0, float(target_h))
    if abs(src_aspect - dst_aspect) <= 0.12:
        return cv2.resize(src_rgb, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    if src_aspect < 1.15:
        # Vertical/square archival portrait: darkened blurred backdrop + centered full-height portrait (head/eyes 100% preserved)
        bg = cv2.resize(src_rgb, (target_w, target_h), interpolation=cv2.INTER_AREA)
        bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=max(18.0, target_w * 0.025))
        bg = np.clip(bg.astype(np.float32) * 0.42, 0.0, 255.0).astype(np.uint8)
        new_h = int(round(target_h * 0.94))
        new_w = min(target_w - 16, max(16, int(round(new_h * src_aspect))))
        fg = cv2.resize(src_rgb, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        x0 = (target_w - new_w) // 2
        y0 = (target_h - new_h) // 2
        # Soft feather mask on left/right portrait edges to blend seamlessly with backdrop without triggering tear detector
        feather = max(12, int(new_w * 0.06))
        alpha = np.ones((new_h, new_w, 1), dtype=np.float32)
        ramp = np.linspace(0.0, 1.0, feather, dtype=np.float32)[None, :, None]
        alpha[:, :feather, :] *= ramp
        alpha[:, -feather:, :] *= ramp[:, ::-1, :]
        roi = bg[y0 : y0 + new_h, x0 : x0 + new_w].astype(np.float32)
        bg[y0 : y0 + new_h, x0 : x0 + new_w] = np.clip(
            fg.astype(np.float32) * alpha + roi * (1.0 - alpha), 0.0, 255.0
        ).astype(np.uint8)
        return bg
    # Wider/taller landscape crop: upper-third bias preserves heads/horizons
    if src_aspect > dst_aspect:
        cw = int(round(sh * dst_aspect))
        x0 = max(0, (sw - cw) // 2)
        cropped = src_rgb[:, x0 : x0 + cw]
    else:
        ch = int(round(sw / dst_aspect))
        y0 = max(0, int((sh - ch) * 0.25))
        cropped = src_rgb[y0 : y0 + ch, :]
    return cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)


def render_cinema_25d_clip(
    image_path: Path,
    out_mp4: Path,
    *,
    duration_s: float = 5.0,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    camera_move: str = "push_left",
    parallax_strength: float = 0.028,
    zoom_delta: float = 0.075,
    atmosphere: str = "dust",
    warm_flicker: bool = False,
    grade_spec: CinemaGradeSpec = DEFAULT_CINEMA_GRADE,
) -> dict[str, Any]:
    """Render a zero-tear, living 2.5D parallax MP4 from a high-res historical still."""
    src_bgr = cv2.imread(str(image_path))
    if src_bgr is None:
        raise FileNotFoundError(f"Could not read source still: {image_path}")
    src_rgb = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2RGB)
    out_w, out_h = int(width), int(height)
    if out_w > 1280:
        ren_w, ren_h = 1280, int(round(1280 * out_h / float(out_w))) // 2 * 2
    else:
        ren_w, ren_h = out_w, out_h
    work_w, work_h = int(ren_w * 1.12), int(ren_h * 1.12)
    src_work = _fit_aspect_preserving_canvas(src_rgb, work_w, work_h)

    img_sha = hashlib.sha256(image_path.read_bytes()).hexdigest()[:16]
    depth_map, depth_backend = estimate_continuous_depth(src_work, cache_key=f"{img_sha}_{work_w}x{work_h}")

    n_frames = max(2, int(round(duration_s * fps)))
    out_mp4 = Path(out_mp4)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp4 = out_mp4.with_name(out_mp4.stem + ".part.mp4")

    base_x = np.linspace(0.0, 1.0, ren_w, dtype=np.float32)[None, :]
    base_y = np.linspace(0.0, 1.0, ren_h, dtype=np.float32)[:, None]
    cx_grid = (base_x - 0.5).astype(np.float32)
    cy_grid = (base_y - 0.5).astype(np.float32)

    depth_out = cv2.resize(depth_map, (ren_w, ren_h), interpolation=cv2.INTER_LINEAR)
    depth_centered = (depth_out - 0.45).astype(np.float32)

    seed = int(img_sha[:8], 16) % 100000
    vf_up = ["-vf", f"scale={out_w}:{out_h}:flags=lanczos,cas=0.30"] if (out_w, out_h) != (ren_w, ren_h) else []
    proc = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ren_w}x{ren_h}",
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
            u = _living_ease(f / max(1, n_frames - 1))
            t_s = f / float(fps)

            if camera_move == "push_left":
                zoom = 1.08 + zoom_delta * u
                pan_x = -0.026 * (u - 0.5)
                pan_y = -0.008 * (u - 0.5)
                p_x = parallax_strength * (u - 0.5) * work_w
                p_y = parallax_strength * 0.25 * (u - 0.5) * work_h
            elif camera_move == "push_right":
                zoom = 1.08 + zoom_delta * u
                pan_x = 0.026 * (u - 0.5)
                pan_y = -0.006 * (u - 0.5)
                p_x = -parallax_strength * (u - 0.5) * work_w
                p_y = parallax_strength * 0.22 * (u - 0.5) * work_h
            elif camera_move == "pull_back":
                zoom = 1.08 + zoom_delta * (1.0 - u)
                pan_x = 0.014 * (u - 0.5)
                pan_y = 0.010 * (u - 0.5)
                p_x = -parallax_strength * 0.85 * (u - 0.5) * work_w
                p_y = -parallax_strength * 0.30 * (u - 0.5) * work_h
            elif camera_move == "truck_right":
                zoom = 1.10 + 0.03 * u
                pan_x = 0.042 * (u - 0.5)
                pan_y = 0.005 * math.sin(u * math.pi)
                p_x = -parallax_strength * 1.15 * (u - 0.5) * work_w
                p_y = 0.0
            else:
                zoom = 1.09 + 0.055 * u
                pan_x = 0.022 * math.sin((u - 0.5) * math.pi)
                pan_y = -0.012 * (u - 0.5)
                p_x = parallax_strength * math.sin((u - 0.5) * math.pi) * work_w
                p_y = parallax_strength * 0.35 * (u - 0.5) * work_h

            breath_x = 0.0018 * math.sin(t_s * 1.3 + seed) * work_w
            breath_y = 0.0014 * math.cos(t_s * 0.95 + seed) * work_h

            map_x = ((cx_grid / zoom + 0.5 + pan_x) * work_w + depth_centered * p_x + breath_x).astype(np.float32)
            map_y = ((cy_grid / zoom + 0.5 + pan_y) * work_h + depth_centered * p_y + breath_y).astype(np.float32)

            warped = cv2.remap(
                src_work, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101
            )
            living = _apply_atmosphere_and_light(
                warped, t_s=t_s, atmosphere=atmosphere, warm_flicker=warm_flicker, seed=seed
            )
            graded = apply_unified_film_grade(living, frame_idx=f, spec=grade_spec)
            proc.stdin.write(graded.tobytes())
    finally:
        proc.stdin.close()
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed rendering cinema 2.5D clip: {out_mp4}")
    tmp_mp4.replace(out_mp4)
    return {
        "status": "PASS",
        "path": str(out_mp4),
        "depth_backend": depth_backend,
        "camera_move": camera_move,
        "atmosphere": atmosphere,
        "warm_flicker": warm_flicker,
        "frames": n_frames,
        "fps": fps,
        "resolution": [width, height],
        "sha256": hashlib.sha256(out_mp4.read_bytes()).hexdigest(),
    }
