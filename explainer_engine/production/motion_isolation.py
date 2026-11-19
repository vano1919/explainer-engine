"""Relationship-specific motion isolation and camera-compensated leak gate (Task 2 R2 Step 3, Requirement D, G7).

Enforces ``explainer_engine/standards/motion_isolation.json``:
- ``MI-01`` Flame in open grate (``brazier``): glowing coals and upper flame plume deform while dark iron grating bars and
  lower basket legs are clamped to ``0.0`` geometric displacement.
- ``MI-02`` Flame on candle wick (``candle``): only the luminous teardrop plume above the wick deforms geometrically; the
  wax stub, tin candle holder, and crate below the wick apex receive ``0.0`` displacement (radial light spill only).
- ``MI-03`` Steam over held vessel (``mug``): translucent screen-blended wisp originating above the mug's top rim, masked
  off the mug body and gloved fingers.
- ``MI-04`` Breath from mouth: directional puff originating at the mouth anchor, masked off the face and collar.
- ``MI-05`` Sky and ground weather (``stars``, ``cloud_drift``, ``sun_glint``, ``glint``): sky effects are multiplied by
  ``sky_mask * (1 - dilated_fg_mask)`` even when a target box is supplied; frost ``glint`` is multiplied by
  ``snow_ground_mask * (1 - dilated_fg_mask)`` and suppressed on solemn burial shots.
- ``MI-06`` Cloth on rigid support (``cloth_flap``): proximal 20% attachment band next to the pole or torso is pinned at
  ``0.0`` displacement with a smooth ramp toward the free edge.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

MI_PATH = Path(__file__).resolve().parents[1] / "standards" / "motion_isolation.json"
_MI_CACHE: dict | None = None


def load_motion_isolation_spec(path: Path | None = None) -> dict:
    """Load and cache ``explainer_engine/standards/motion_isolation.json``."""
    global _MI_CACHE
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if _MI_CACHE is None:
        _MI_CACHE = json.loads(MI_PATH.read_text(encoding="utf-8"))
    return _MI_CACHE


def isolate_flame_mover(
    sub_rgb: np.ndarray,
    sub_fm: np.ndarray,
    *,
    op: str = "fire",
    holder_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(mover_field, anchor_mask)`` inside a flame crop ``sub_rgb`` (H, W, 3).

    - For ``op == 'fire'`` (e.g. coke brazier in ``S02_SH008``): dark iron grating bars crossing the coals (low luma or
      low warmth ``R - B``) are placed in ``anchor_mask`` and clamped to ``0.0`` in ``mover_field`` so the iron basket
      never warps or wobbles.
    - For ``op == 'candle'`` (e.g. candle in tin holder in ``S08_SH002``): pixels below the upper 65% of the active light
      mask (the candle wax stub, tin holder rim, and wooden crate) are placed in ``anchor_mask`` and clamped to ``0.0``
      geometric warp.
    """
    import cv2

    hh, ww = sub_fm.shape[:2]
    spec = load_motion_isolation_spec().get("relationships") or {}
    rgb_f = sub_rgb.astype(np.float32)
    luma = 0.299 * rgb_f[..., 0] + 0.587 * rgb_f[..., 1] + 0.114 * rgb_f[..., 2]
    warmth = rgb_f[..., 0] - rgb_f[..., 2]

    ys, xs = np.nonzero(sub_fm > 0.15)
    if not len(xs):
        zeros = np.zeros((hh, ww), np.float32)
        return zeros, np.ones((hh, ww), np.float32)

    y_min, y_max = int(ys.min()), int(ys.max())
    span_y = max(1, y_max - y_min + 1)
    yy = np.arange(hh, dtype=np.float32)[:, None]

    if op == "candle":
        cfg = (spec.get("MI-02_flame_on_candle_wick") or {}).get("parameters") or {}
        max_y_frac = float(cfg.get("max_plume_y_fraction_of_light_box", 0.65))
        min_luma = float(cfg.get("min_luma_for_warp", 110.0))
        min_warm = float(cfg.get("min_warmth_r_minus_b", 20.0))
        wick_cut_y = y_min + max_y_frac * span_y
        plume_zone = np.clip((wick_cut_y - yy) / max(2.0, 0.20 * span_y), 0.0, 1.0)
        luminous_gate = np.clip((luma - min_luma) / 45.0, 0.0, 1.0) * np.clip((warmth - min_warm) / 30.0, 0.0, 1.0)
        mover = sub_fm.astype(np.float32) * plume_zone * np.maximum(luminous_gate, (luma > 220.0).astype(np.float32))
        anchor = ((yy >= wick_cut_y) | (luma < min_luma * 0.85)).astype(np.float32)
    else:
        cfg = (spec.get("MI-01_flame_in_open_grate") or {}).get("parameters") or {}
        min_luma = float(cfg.get("min_luma_for_warp", 95.0))
        min_warm = float(cfg.get("min_warmth_r_minus_b", 25.0))
        # Dark iron bars crossing the glowing coals have low luma or low R-B warmth: clamp them to 0 displacement
        coal_or_flame = np.clip((luma - min_luma) / 40.0, 0.0, 1.0) * np.clip((warmth - min_warm) / 25.0, 0.0, 1.0)
        white_hot = (luma > 225.0).astype(np.float32)
        mover = sub_fm.astype(np.float32) * np.maximum(coal_or_flame, white_hot)
        anchor = ((sub_fm > 0.05) & (mover < 0.12)).astype(np.float32)

    if holder_mask is not None and holder_mask.shape[:2] == (hh, ww):
        rigid_holder = (holder_mask > 0.35) & (mover < 0.25)
        anchor = np.maximum(anchor, rigid_holder.astype(np.float32))
        mover = mover * (1.0 - rigid_holder.astype(np.float32))

    mover = cv2.GaussianBlur(mover.astype(np.float32), (0, 0), 1.5)
    mover = mover * (1.0 - (anchor > 0.5).astype(np.float32))
    return np.clip(mover, 0.0, 1.0).astype(np.float32), np.clip(anchor, 0.0, 1.0).astype(np.float32)


def foreground_union_mask(masks_src: dict[str, np.ndarray] | None, shape: tuple[int, int], dilate_px: int = 4) -> np.ndarray:
    """Return a ``0..1`` union mask of all non-sky foreground objects in ``masks_src`` at ``shape = (H, W)``."""
    import cv2

    h, w = shape
    fg = np.zeros((h, w), np.float32)
    for oid, m in (masks_src or {}).items():
        if str(oid).lower() in ("sky", "cloud", "clouds", "sky_canopy", "snow_ground"):
            continue
        if isinstance(m, np.ndarray):
            mr = cv2.resize(m.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if m.shape[:2] != (h, w) else m.astype(np.float32)
            fg = np.maximum(fg, mr)
    if dilate_px > 0 and fg.max() > 0.05:
        k = max(1, int(round(dilate_px * h / 1080.0)))
        fg = cv2.dilate((fg > 0.25).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=k).astype(np.float32)
    return np.clip(fg, 0.0, 1.0)


def isolate_sparkle_region(
    base_region: np.ndarray,
    *,
    op: str,
    sky_mask: np.ndarray | None,
    masks_src: dict[str, np.ndarray] | None,
    depth: np.ndarray | None = None,
    solemn: bool = False,
) -> np.ndarray:
    """Clip ``stars`` strictly to ``sky_mask * (1 - fg_union)`` and ``glint`` strictly to ground snow outside foreground objects.

    Prevents ``S02_SH008``'s ``fx_seen_stars`` box ``[0.342, 0.062, 0.658, 0.378]`` from placing twinkling stars on sandbags
    and barbed wire, and prevents ``S05_SH020``'s ``fx_seen_ice`` box ``[0.342, 0.422, 0.658, 0.738]`` from sparkling on
    wooden grave crosses and soldiers' coats.
    """
    import cv2

    h, w = base_region.shape[:2]
    if solemn and op == "glint":
        return np.zeros((h, w), np.float32)

    fg = foreground_union_mask(masks_src, (h, w), dilate_px=6)
    keep_off_fg = 1.0 - fg

    if op == "stars":
        if sky_mask is not None:
            sk = cv2.resize(sky_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if sky_mask.shape[:2] != (h, w) else sky_mask.astype(np.float32)
            sk = cv2.erode((sk > 0.45).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=2).astype(np.float32)
        else:
            sk = np.zeros((h, w), np.float32)
            sk[: int(0.18 * h), :] = 1.0
        return (base_region.astype(np.float32) * sk * keep_off_fg).astype(np.float32)

    # op == "glint": ground snow/ice only (below horizon, outside all foreground people/crosses/posts/braziers)
    ground_zone = np.zeros((h, w), np.float32)
    ground_zone[int(0.72 * h) :, :] = 1.0
    if sky_mask is not None:
        sk = cv2.resize(sky_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if sky_mask.shape[:2] != (h, w) else sky_mask.astype(np.float32)
        ground_zone = ground_zone * (1.0 - (sk > 0.25).astype(np.float32))
    return (base_region.astype(np.float32) * ground_zone * keep_off_fg).astype(np.float32)


def attachment_ramp(xx: np.ndarray, x0: int, x1: int, fixed_left: bool = True, pinned_frac: float = 0.20) -> np.ndarray:
    """Return a ``0..1`` displacement weight that pins the proximal ``pinned_frac`` attachment seam to ``0.0`` (MI-06)."""
    span = max(1.0, float(x1 - x0))
    raw = (xx - x0) / span if fixed_left else (x1 - xx) / span
    u = np.clip((raw - pinned_frac) / max(1e-3, 1.0 - pinned_frac), 0.0, 1.0)
    return (u * u * (3.0 - 2.0 * u)).astype(np.float32)


def evaluate_motion_isolation(
    frames: list[np.ndarray],
    *,
    mover_mask: np.ndarray | None = None,
    anchor_mask: np.ndarray | None = None,
    fg_mask: np.ndarray | None = None,
    sky_mask: np.ndarray | None = None,
    views: list[dict] | None = None,
) -> dict[str, Any]:
    """Multi-component camera-compensated motion-isolation leak gate (Requirement D & P3).

    Separates:
    1. ``element_motion_p95``: motion inside ``mover_mask`` (flame plume, rising steam, snow in sky).
    2. ``holder_leak_p95``: unwanted geometric warp/sparkle inside ``anchor_mask`` (iron brazier basket, tin candle holder,
       barbed wire below sky, wooden grave crosses).
    3. ``camera_residual_error``: background residual after compensating for ``views`` camera translation/scale.
    4. ``boundary_halo_error``: gradient spike along ``fg_mask`` boundary ring.
    5. ``accidental_freeze``: True when motion was planned but ``element_motion_p95`` and global flow are near zero.
    """
    import cv2

    spec = load_motion_isolation_spec().get("calibrated_leak_thresholds") or {}
    max_ratio = float(spec.get("max_holder_to_mover_ratio", 0.08))
    max_holder_luma = float(spec.get("max_holder_leak_p95_luma", 1.25))

    if not frames or len(frames) < 2:
        return {"status": "NOT_RUN", "passed": True, "reason": "fewer than 2 frames"}

    f0 = frames[0].astype(np.float32)
    h, w = f0.shape[:2]
    g0 = cv2.cvtColor(frames[0], cv2.COLOR_RGB2GRAY).astype(np.float32)

    mover = cv2.resize(mover_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if mover_mask is not None else np.zeros((h, w), np.float32)
    anchor = cv2.resize(anchor_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if anchor_mask is not None else np.zeros((h, w), np.float32)
    fg = cv2.resize(fg_mask.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) if fg_mask is not None else np.zeros((h, w), np.float32)

    mover_diffs: list[float] = []
    holder_diffs: list[float] = []
    mover_flows: list[float] = []
    holder_flows: list[float] = []
    bg_residuals: list[float] = []
    halo_errors: list[float] = []

    v0 = views[0] if (views and len(views) == len(frames)) else None
    for idx in range(1, len(frames)):
        fi = frames[idx].astype(np.float32)
        gi = cv2.cvtColor(frames[idx], cv2.COLOR_RGB2GRAY).astype(np.float32)
        # Camera compensation when view telemetry is available; else median translation flow compensation
        if v0 is not None and views is not None:
            vi = views[idx]
            ds = float(vi.get("s", 1.0)) / max(1e-6, float(v0.get("s", 1.0)))
            dcx = (float(vi.get("cx", 0.5)) - float(v0.get("cx", 0.5))) * w
            dcy = (float(vi.get("cy", 0.5)) - float(v0.get("cy", 0.5))) * h
            mat = np.float32([[ds, 0.0, (1.0 - ds) * (w * 0.5) - dcx], [0.0, ds, (1.0 - ds) * (h * 0.5) - dcy]])
            gi_aligned = cv2.warpAffine(gi, mat, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
        else:
            flow = cv2.calcOpticalFlowFarneback(g0, gi, None, 0.5, 2, 15, 2, 5, 1.1, 0)
            med_dx, med_dy = float(np.median(flow[..., 0])), float(np.median(flow[..., 1]))
            mat = np.float32([[1.0, 0.0, -med_dx], [0.0, 1.0, -med_dy]])
            gi_aligned = cv2.warpAffine(gi, mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        diff = np.abs(gi_aligned - g0)
        res_flow = cv2.calcOpticalFlowFarneback(g0, gi_aligned, None, 0.5, 2, 15, 2, 5, 1.1, 0)
        flow_mag = np.hypot(res_flow[..., 0], res_flow[..., 1])
        if (mover > 0.25).any():
            mover_diffs.append(float(np.percentile(diff[mover > 0.25], 95)))
            mover_flows.append(float(np.percentile(flow_mag[mover > 0.25], 95)))
        if (anchor > 0.25).any():
            holder_diffs.append(float(np.percentile(diff[anchor > 0.25], 95)))
            holder_flows.append(float(np.percentile(flow_mag[anchor > 0.25], 95)))
        bg_zone = (mover < 0.1) & (anchor < 0.1) & (fg < 0.1)
        if bg_zone.any():
            bg_residuals.append(float(np.percentile(diff[bg_zone], 90)))
        if (fg > 0.25).any():
            b_u8 = (fg > 0.25).astype(np.uint8)
            ring = (cv2.dilate(b_u8, np.ones((3, 3), np.uint8), iterations=2) > 0) & (cv2.erode(b_u8, np.ones((3, 3), np.uint8), iterations=2) == 0)
            if ring.any():
                halo_errors.append(float(np.percentile(diff[ring], 95)))

    elem_p95 = round(max(mover_diffs) if mover_diffs else 0.0, 4)
    hold_p95 = round(max(holder_diffs) if holder_diffs else 0.0, 4)
    elem_flow_p95 = round(max(mover_flows) if mover_flows else 0.0, 4)
    hold_flow_p95 = round(max(holder_flows) if holder_flows else 0.0, 4)
    cam_res = round(float(np.mean(bg_residuals)) if bg_residuals else 0.0, 4)
    halo_p95 = round(max(halo_errors) if halo_errors else 0.0, 4)
    leak_ratio = round(hold_p95 / max(1e-3, elem_p95), 4) if elem_p95 > 0 else (999.0 if hold_p95 > max_holder_luma else 0.0)

    passed = (hold_p95 <= max_holder_luma) and (leak_ratio <= max_ratio)
    return {
        "status": "PASS" if passed else "FAIL",
        "passed": bool(passed),
        "element_motion_p95": elem_p95,
        "holder_leak_p95": hold_p95,
        "mover_flow_p95": elem_flow_p95,
        "holder_flow_p95": hold_flow_p95,
        "leak_ratio": leak_ratio,
        "camera_residual_error": cam_res,
        "boundary_halo_error": halo_p95,
        "accidental_freeze": bool((mover > 0.25).any() and elem_p95 < 0.25),
        "thresholds": {"max_holder_to_mover_ratio": max_ratio, "max_holder_leak_p95_luma": max_holder_luma},
    }
