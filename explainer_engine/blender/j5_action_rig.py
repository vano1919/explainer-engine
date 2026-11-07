"""CPU-only 2.5D action animation operators for J5 v3 (BP-182, BP-183; D-116).

Provides three deterministic, zero-GPU animation methods that replace LTX on non-duel action shots:
1. ``render_depth_relief_frame``: depth-displaced perspective warp with Telea-style edge disocclusion guard.
2. ``render_billboard_crowd_frame``: depth-sliced multi-plane (>= 3 tiers) marching column with phase-staggered
   stride bob, lateral parallax differential, and rain/splash overlays.
3. ``render_hinged_action_frame``: hinged rigid-plus-feathered-joint rotation (<= 22 deg) for sword/drum/banner
   strokes and robed characters (solving the Meta AnimatedDrawings robed-leg collapse), plus impact flash/shake.
"""

from __future__ import annotations

import math
import numpy as np

from explainer_engine.standards import sourced_rules as SR

PARALLAX_MAX = float(SR.T("BP-182", "parallax_factor_max"))
YAW_MAX_DEG = float(SR.T("BP-182", "relief_yaw_max_deg"))
INPAINT_RADIUS = int(SR.T("BP-182", "inpaint_radius_px"))
ARAP_MAX_FRAC = float(SR.T("BP-182", "arap_disp_frac_max"))

MIN_PLANES = int(SR.T("BP-183", "min_crowd_planes"))
BOB_FREQ_BAND = list(SR.T("BP-183", "bob_freq_hz_band"))
BOB_AMP_MAX = float(SR.T("BP-183", "bob_amp_px_max"))
SPEED_RATIO_MIN = float(SR.T("BP-183", "plane_speed_ratio_min"))
HINGE_MAX_DEG = float(SR.T("BP-183", "hinge_angle_max_deg"))


def synthetic_depth_from_luma(img: np.ndarray) -> np.ndarray:
    """Fallback vertical+luminance depth estimator in [0, 1] when a precomputed depth PNG is not supplied."""
    h, w = img.shape[:2]
    y_grad = np.linspace(0.15, 1.0, h, dtype=np.float32)[:, None]
    luma = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32) / 255.0
    depth = np.clip(0.75 * y_grad + 0.25 * (1.0 - luma), 0.0, 1.0)
    return depth


def render_depth_relief_frame(
    img: np.ndarray,
    depth: np.ndarray | None = None,
    *,
    yaw_deg: float = 4.0,
    push_zoom: float = 1.08,
) -> np.ndarray:
    """Warp ``img`` through a 2.5D depth-relief camera with clamped parallax and disocclusion fill (BP-182)."""
    h, w, c = img.shape
    if depth is None:
        depth = synthetic_depth_from_luma(img)
    clamped_yaw = max(-YAW_MAX_DEG, min(YAW_MAX_DEG, float(yaw_deg)))
    parallax = min(PARALLAX_MAX, abs(clamped_yaw) / 100.0 + 0.03)
    sign = 1.0 if clamped_yaw >= 0 else -1.0

    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")
    cx, cy = w * 0.5, h * 0.5
    inv_z = 1.0 / max(1.0, float(push_zoom))
    ShiftX = sign * parallax * (depth - 0.5) * w
    src_x = np.clip((xx - cx) * inv_z + cx - ShiftX, 0, w - 1).astype(np.int32)
    src_y = np.clip((yy - cy) * inv_z + cy, 0, h - 1).astype(np.int32)
    out = img[src_y, src_x].copy()

    # Smooth any high-gradient depth disocclusion seam using horizontal neighbor averaging within INPAINT_RADIUS
    grad_d = np.abs(np.diff(depth, axis=1, prepend=depth[:, :1]))
    seam_mask = grad_d > 0.18
    if np.any(seam_mask) and INPAINT_RADIUS > 0:
        r = max(1, min(INPAINT_RADIUS, 6))
        blurred = (np.roll(out, r, axis=1).astype(np.uint16) + np.roll(out, -r, axis=1).astype(np.uint16)) // 2
        out[seam_mask] = blurred[seam_mask].astype(np.uint8)
    return out


def render_billboard_crowd_frame(
    img: np.ndarray,
    depth: np.ndarray | None = None,
    *,
    t_sec: float = 1.0,
    n_planes: int = 3,
    bob_freq_hz: float = 1.6,
    bob_amp_px: float = 4.5,
    rain: bool = False,
    water_splash: bool = False,
) -> np.ndarray:
    """Animate a crowd or marching-column still by slicing into >= 3 depth billboard planes (BP-183)."""
    h, w, _ = img.shape
    if depth is None:
        depth = synthetic_depth_from_luma(img)
    planes = max(MIN_PLANES, int(n_planes))
    freq = max(BOB_FREQ_BAND[0], min(BOB_FREQ_BAND[1], float(bob_freq_hz)))
    amp = min(BOB_AMP_MAX, float(bob_amp_px))

    out = img.copy()
    edges = np.linspace(0.0, 1.0, planes + 1)
    for p_idx in range(planes):
        d_lo, d_hi = edges[p_idx], edges[p_idx + 1]
        mask = (depth >= d_lo) & (depth <= d_hi)
        speed_mult = (SPEED_RATIO_MIN ** p_idx)
        phase = p_idx * 1.15
        scale_p = 0.5 + 0.5 * (p_idx / max(1, planes - 1))
        dy = int(round(amp * scale_p * math.sin(2.0 * math.pi * freq * t_sec + phase)))
        dx = int(round(2.0 * speed_mult * t_sec))
        shifted = np.roll(np.roll(img, dy, axis=0), dx, axis=1)
        out[mask] = shifted[mask]

    if rain:
        rng = np.random.default_rng(seed=int(t_sec * 24) + 17)
        for _ in range(90):
            rx = int(rng.integers(8, w - 12))
            ry = int(rng.integers(8, h - 28))
            for k in range(18):
                if ry + k < h and rx - k // 3 >= 0:
                    out[ry + k, rx - k // 3] = np.clip(out[ry + k, rx - k // 3].astype(np.int32) + 55, 0, 255)

    if water_splash:
        band_y0 = int(h * 0.72)
        band_y1 = int(h * 0.88)
        xs = np.arange(w, dtype=np.float32)
        wave = (np.sin(xs * 0.08 + t_sec * 9.0) > 0.55)
        for y in range(band_y0, band_y1, 3):
            out[y, wave] = np.clip(out[y, wave].astype(np.int32) + 65, 0, 255).astype(np.uint8)

    return out


def render_hinged_action_frame(
    img: np.ndarray,
    *,
    pivot_xy: tuple[float, float] = (0.5, 0.55),
    angle_deg: float = 14.0,
    region_box: tuple[float, float, float, float] = (0.25, 0.15, 0.75, 0.75),
    slash_smear: bool = False,
    shake_px: float = 0.0,
) -> np.ndarray:
    """Apply a bounded hinged upper-body/weapon rotation (<= 22 deg, BP-183) with feathered seam and smear arc."""
    h, w, _ = img.shape
    clamped_deg = max(-HINGE_MAX_DEG, min(HINGE_MAX_DEG, float(angle_deg)))
    theta = math.radians(clamped_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    px, py = pivot_xy[0] * w, pivot_xy[1] * h
    x0, y0, x1, y1 = int(region_box[0] * w), int(region_box[1] * h), int(region_box[2] * w), int(region_box[3] * h)
    out = img.copy()

    yy, xx = np.meshgrid(np.arange(y0, y1, dtype=np.float32), np.arange(x0, x1, dtype=np.float32), indexing="ij")
    dx, dy = xx - px, yy - py
    max_r = max(1.0, math.hypot(x1 - x0, y1 - y0) * 0.5)
    weight = np.clip(1.0 - np.hypot(dx, dy) / max_r, 0.0, 1.0)
    eff_limit = ARAP_MAX_FRAC * h
    sx = np.clip(px + cos_t * dx + sin_t * dy, 0, w - 1).astype(np.int32)
    sy = np.clip(py - sin_t * dx + cos_t * dy, 0, h - 1).astype(np.int32)
    rotated = img[sy, sx]
    alpha = (weight[:, :, None] * 0.85).astype(np.float32)
    out[y0:y1, x0:x1] = (alpha * rotated + (1.0 - alpha) * out[y0:y1, x0:x1]).astype(np.uint8)

    if slash_smear:
        for deg in range(-35, 25, 2):
            rad = math.radians(deg)
            for r_off in range(int(max_r * 0.48), int(max_r * 0.56)):
                ax = int(px + r_off * math.cos(rad))
                ay = int(py + r_off * math.sin(rad))
                if 0 <= ax < w and 0 <= ay < h:
                    out[ay, ax] = np.array([250, 235, 180], dtype=np.uint8)

    if shake_px > 0:
        s_px = int(min(10.0, shake_px))
        out = np.roll(np.roll(out, s_px, axis=1), -s_px // 2, axis=0)

    return out
