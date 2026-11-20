"""2.5D atmospheric breath vapour and rising fire ember effects for single-frame rendering.

Implements deterministic, pure-NumPy layer generators and compositing for the 2.5D lane:
- `breath_alpha`: renders soft, drifting, fading cold-air breath puffs per character mouth (OR-V19d, LP-09; its living-motion rule lives in the 2.5D stack, not on main yet).
- `embers_layer`: renders sparse, rising, swaying, cooling fire embers with depth occlusion (OR-V19a, OR-V19c, LP-09).
- `composite`: blends breath vapour and screen-lit embers onto an RGB frame without exceeding 255 (OR-V19d, OR-V19a).
"""

from __future__ import annotations

import math

import numpy as np

_MAX_BREATH_ALPHA = 0.35
_PUFF_LIFETIME_S = 1.5
_VAPOUR_RGB = (235.0, 238.0, 242.0)


def breath_alpha(
    shape_hw: tuple[int, int],
    frame_idx: int,
    fps: float,
    mouths: list[tuple[float, float]],
    wind: tuple[float, float],
    seed: int,
    interval_s: tuple[float, float] = (3.0, 4.0),
    size_share: float = 0.04,
) -> np.ndarray:
    """float32 array (H, W) in [0, 1]: the white-grey vapour alpha of all mouths at this frame."""
    height, width = int(shape_hw[0]), int(shape_hw[1])
    if fps <= 0.0:
        raise ValueError("fps must be positive")

    out = np.zeros((height, width), dtype=np.float32)
    if height <= 0 or width <= 0 or not mouths or size_share <= 0.0:
        return out

    t = float(frame_idx) / float(fps)
    rng = np.random.default_rng(int(seed))

    low_s = max(1e-3, float(min(interval_s[0], interval_s[1])))
    high_s = max(low_s, float(max(interval_s[0], interval_s[1])))

    max_diameter_px = max(8.0, float(size_share) * float(width))
    max_radius_px = 0.5 * max_diameter_px
    max_alpha_f32 = np.float32(_MAX_BREATH_ALPHA)

    for mouth_idx, (mx, my) in enumerate(mouths):
        period = float(rng.uniform(low_s, high_s))
        phase = float(rng.uniform(0.0, period))
        base_rise = float(rng.uniform(0.022, 0.036)) * float(height)

        shifted_t = t + phase
        first_cycle = int(math.floor((shifted_t - _PUFF_LIFETIME_S) / period)) + 1
        last_cycle = int(math.floor(shifted_t / period))

        for cycle_idx in range(first_cycle, last_cycle + 1):
            age = shifted_t - cycle_idx * period
            if age < 0.0 or age >= _PUFF_LIFETIME_S:
                continue

            u = age / _PUFF_LIFETIME_S
            puff_rng = np.random.default_rng([int(seed), mouth_idx, cycle_idx])

            sway_freq = float(puff_rng.uniform(2.2, 3.8))
            sway_phase = float(puff_rng.uniform(0.0, 2.0 * math.pi))
            sway_amp = float(puff_rng.uniform(0.06, 0.16)) * max_radius_px

            cx = float(mx) + float(wind[0]) * float(width) * age + sway_amp * math.sin(sway_freq * age + sway_phase)
            cy = float(my) + float(wind[1]) * float(width) * age - base_rise * (age**0.9)

            r_curr = max_radius_px * (0.30 + 0.70 * math.sqrt(u))
            fade_in = math.sin(0.5 * math.pi * min(u / 0.14, 1.0))
            fade_out = (1.0 - u) ** 1.55
            peak_alpha = 0.32 * fade_in * fade_out
            if peak_alpha <= 1e-5 or r_curr <= 0.5:
                continue

            x0 = max(0, int(math.floor(cx - r_curr)))
            x1 = min(width, int(math.ceil(cx + r_curr)) + 1)
            y0 = max(0, int(math.floor(cy - r_curr)))
            y1 = min(height, int(math.ceil(cy + r_curr)) + 1)
            if x0 >= x1 or y0 >= y1:
                continue

            yy, xx = np.ogrid[y0:y1, x0:x1]
            dx = xx.astype(np.float32) - np.float32(cx)
            dy = yy.astype(np.float32) - np.float32(cy)
            norm_r2 = (dx * dx + dy * dy) * np.float32(1.0 / (r_curr * r_curr))

            window = np.maximum(np.float32(0.0), np.float32(1.0) - norm_r2) ** 2

            sigma = max(3.5, 0.38 * r_curr)
            inv_two_sigma2 = np.float32(-0.5 / (sigma * sigma))
            density = np.zeros_like(window)

            lobe_weights = (0.55, 0.30, 0.25)
            for lobe_idx, weight in enumerate(lobe_weights):
                if lobe_idx == 0:
                    ox, oy = 0.0, 0.0
                else:
                    lobe_r = float(puff_rng.uniform(0.08, 0.24)) * r_curr
                    lobe_ang = float(puff_rng.uniform(0.0, 2.0 * math.pi)) + 0.6 * age
                    ox = lobe_r * math.cos(lobe_ang)
                    oy = lobe_r * math.sin(lobe_ang)
                ldx = dx - np.float32(ox)
                ldy = dy - np.float32(oy)
                density += np.float32(weight) * np.exp(inv_two_sigma2 * (ldx * ldx + ldy * ldy))

            puff_patch = np.float32(peak_alpha) * window * np.minimum(np.float32(1.0), density)

            sub = out[y0:y1, x0:x1]
            out[y0:y1, x0:x1] = max_alpha_f32 * (
                np.float32(1.0)
                - (np.float32(1.0) - sub / max_alpha_f32) * (np.float32(1.0) - puff_patch / max_alpha_f32)
            )

    np.clip(out, 0.0, _MAX_BREATH_ALPHA, out=out)
    return out


def embers_layer(
    shape_hw: tuple[int, int],
    frame_idx: int,
    fps: float,
    source_xy: tuple[float, float],
    source_radius_px: float,
    wind: tuple[float, float],
    depth: np.ndarray | None,
    seed: int,
    count: int = 60,
    ember_depth: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """(rgb float32 (H, W, 3) in 0..255, alpha float32 (H, W) in [0, 1]) of the embers at this frame."""
    height, width = int(shape_hw[0]), int(shape_hw[1])
    if fps <= 0.0:
        raise ValueError("fps must be positive")

    rgb_out = np.zeros((height, width, 3), dtype=np.float32)
    alpha_out = np.zeros((height, width), dtype=np.float32)
    if height <= 0 or width <= 0 or count <= 0:
        return rgb_out, alpha_out

    t = float(frame_idx) / float(fps)
    rng = np.random.default_rng(int(seed))

    lives = rng.uniform(1.0, 3.0, size=count)
    phases = rng.uniform(0.0, lives)
    shifted_t = t + phases
    gens = np.floor(shifted_t / lives).astype(np.int64)
    ages = shifted_t - gens * lives
    progress = ages / lives

    sx, sy = float(source_xy[0]), float(source_xy[1])
    spawn_rad_max = max(0.0, float(source_radius_px))
    wind_vx = float(wind[0]) * float(width)
    wind_vy = float(wind[1]) * float(width)

    for idx in range(count):
        gen = int(gens[idx])
        age = float(ages[idx])
        ui = float(progress[idx])

        erng = np.random.default_rng([int(seed), idx, gen])

        r_spawn = spawn_rad_max * math.sqrt(float(erng.uniform(0.0, 1.0)))
        theta = float(erng.uniform(0.0, 2.0 * math.pi))
        x0 = sx + r_spawn * math.cos(theta)
        y0 = sy + r_spawn * math.sin(theta)

        rise_speed = float(erng.uniform(0.06, 0.16)) * float(height)
        sway_amp = float(erng.uniform(2.5, 9.0))
        sway_freq = float(erng.uniform(3.0, 7.5))
        sway_phase = float(erng.uniform(0.0, 2.0 * math.pi))

        ex = x0 + wind_vx * age + sway_amp * math.sin(sway_freq * age + sway_phase)
        ey = y0 - rise_speed * age + wind_vy * age + 0.3 * sway_amp * math.cos(0.8 * sway_freq * age + sway_phase)

        radius = float(erng.uniform(1.1, 2.2))
        fade_in = math.sin(0.5 * math.pi * min(ui / 0.10, 1.0))
        fade_out = (1.0 - ui) ** 1.35
        brightness = float(erng.uniform(0.75, 1.0)) * fade_in * fade_out
        if brightness <= 1e-4:
            continue

        r_col = 255.0 - 10.0 * ui
        g_col = 185.0 * ((1.0 - ui) ** 1.2) + 45.0 * ui
        b_col = 55.0 * ((1.0 - ui) ** 1.8) + 10.0 * ui

        extent = 3.0 * radius
        bx0 = max(0, int(math.floor(ex - extent)))
        bx1 = min(width, int(math.ceil(ex + extent)) + 1)
        by0 = max(0, int(math.floor(ey - extent)))
        by1 = min(height, int(math.ceil(ey + extent)) + 1)
        if bx0 >= bx1 or by0 >= by1:
            continue

        yy, xx = np.ogrid[by0:by1, bx0:bx1]
        dx = xx.astype(np.float32) - np.float32(ex)
        dy = yy.astype(np.float32) - np.float32(ey)
        r2 = dx * dx + dy * dy
        cutoff2 = np.float32(extent * extent)
        mask = r2 < cutoff2
        if not np.any(mask):
            continue

        kernel = np.where(
            mask,
            np.exp(np.float32(-0.5 / (radius * radius)) * r2),
            np.float32(0.0),
        )
        patch_a = np.float32(brightness) * kernel

        sub_a = alpha_out[by0:by1, bx0:bx1]
        alpha_out[by0:by1, bx0:bx1] = np.float32(1.0) - (np.float32(1.0) - sub_a) * (np.float32(1.0) - patch_a)

        ember_rgb = np.array([r_col, g_col, b_col], dtype=np.float32)
        sub_rgb = rgb_out[by0:by1, bx0:bx1]
        rgb_out[by0:by1, bx0:bx1] = np.minimum(np.float32(255.0), sub_rgb + patch_a[..., None] * ember_rgb)

    if depth is not None:
        depth_arr = np.asarray(depth, dtype=np.float32)
        if depth_arr.shape != (height, width):
            raise ValueError(f"depth shape {depth_arr.shape} does not match expected {(height, width)}")
        occluded = depth_arr > np.float32(ember_depth)
        alpha_out[occluded] = np.float32(0.0)
        rgb_out[occluded] = np.float32(0.0)

    np.clip(rgb_out, 0.0, 255.0, out=rgb_out)
    np.clip(alpha_out, 0.0, 1.0, out=alpha_out)
    return rgb_out, alpha_out


def composite(
    rgb: np.ndarray,
    breath: np.ndarray | None,
    embers: tuple[np.ndarray, np.ndarray] | None,
) -> np.ndarray:
    """float32 (H, W, 3): vapour mixed in as light grey-white, embers added as screen light; never above 255."""
    out = np.array(rgb, dtype=np.float32, copy=True)

    if breath is not None:
        a = np.clip(np.asarray(breath, dtype=np.float32), 0.0, 1.0)
        mask = a > 0.0
        if np.any(mask):
            vapour = np.array(_VAPOUR_RGB, dtype=np.float32)
            a3 = a[..., None]
            out = np.where(mask[..., None], out * (np.float32(1.0) - a3) + vapour * a3, out)

    if embers is not None:
        e_rgb, e_alpha = embers
        er = np.clip(np.asarray(e_rgb, dtype=np.float32), 0.0, 255.0)
        ea = np.clip(np.asarray(e_alpha, dtype=np.float32), 0.0, 1.0)
        emask = ea > 0.0
        if np.any(emask):
            light = er * ea[..., None]
            base_clamped = np.clip(out, 0.0, 255.0)
            screened = (
                np.float32(255.0)
                - (np.float32(255.0) - base_clamped) * (np.float32(255.0) - light) / np.float32(255.0)
            )
            out = np.where(emask[..., None], screened, out)

    np.clip(out, 0.0, 255.0, out=out)
    return out.astype(np.float32, copy=False)
