"""First-Class Continuity-Aware Cinematic Transition System (`cinematic_transitions.py`, v4.3).

Aligned with `explainer_engine.production.cut_plan` (`ED-04`):
- Hard cuts (`hard_cut_with_jl_bridge`, `cut_plan_transition = "cut"`) are the editorial default inside a location/scene.
- Special transitions are used ONLY when structurally justified:
  1. `map_to_location_zoom_through` / `infographic_number_to_scene_morph`: Handoffs between a 10% GIS map/infographic
     and a physical historical location shot.
  2. `cross_dissolve_8f` (`cut_plan_transition = "dissolve"`): Segment or location transitions (`not same_location` or `not same_segment`).
  3. Map -> Map handoffs (M8): same location + inherited camera -> seamless cut (0 blend frames, 0.15 s audio prelap);
     different location -> `cross_dissolve_8f` (8 frames).
- Decorative wipes (`atmospheric_smoke_ash_wipe`, `foreground_object_wipe`, `motion_matched_pan_whip`) are disabled by default
  and only used if a shot explicitly declares `explicit_transition_override` AND `allow_decorative_wipes=True`.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

TRANSITION_TYPES: Tuple[str, ...] = (
    "map_to_location_zoom_through",
    "infographic_number_to_scene_morph",
    "match_cut_shape_and_focus",
    "motion_matched_pan_whip",
    "foreground_object_wipe",
    "atmospheric_smoke_ash_wipe",
    "cross_dissolve_8f",
    "cross_dissolve_12f",
    "cross_dissolve_14f",
    "cross_dissolve_16f",
    "cross_dissolve_17f",
    "warm_dip",
    "warm_fire_glow_dip",
    "hard_cut_with_jl_bridge",
    "fade_to_black",
)

# HF-1 (Truce 1914 assembly, TD-301): what the script's own ``transition_out`` becomes when the runner honours it.
# ``hard_cut``, ``j_cut`` and ``l_cut`` are cuts (the J/L offsets belong to the sound plan); ``cross_dissolve_8f`` is the
# 8-frame blend; ``fade_to_black`` is 24 frames, 12 out and 12 in (an engineering default: no source fixes the length yet).
AUTHORED_FRAMES: Dict[str, int] = {
    "hard_cut": 0,
    "j_cut": 0,
    "l_cut": 0,
    "cross_dissolve_8f": 8,
    "cross_dissolve_12f": 12,
    "cross_dissolve_14f": 14,
    "cross_dissolve_16f": 16,
    "cross_dissolve_17f": 17,
    "warm_dip": 14,
    "warm_fire_glow_dip": 14,
    "fade_to_black": 24,
}

CAMERA_MOVE_VECTORS: Dict[str, Tuple[float, float, float]] = {
    "static": (0.0, 0.0, 0.0),
    "slow_push_in": (0.0, 0.0, 1.0),
    "push_in": (0.0, 0.0, 1.0),
    "parallax_dolly": (0.0, 0.0, 0.8),
    "slow_pull_back": (0.0, 0.0, -1.0),
    "pull_back": (0.0, 0.0, -1.0),
    "pan_left": (-1.0, 0.0, 0.0),
    "pan_right": (1.0, 0.0, 0.0),
    "parallax_orbital": (0.7, 0.0, 0.4),
    "tracking_shot": (0.9, 0.0, 0.3),
    "tilt_up": (0.0, -1.0, 0.0),
    "tilt_down": (0.0, 1.0, 0.0),
}


def compute_visual_continuity_alignment(
    shot_a: Dict[str, Any],
    shot_b: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze visual continuity across Shot A -> Shot B across 5 dimensions."""
    cam_a = shot_a.get("camera_spec") or {}
    cam_b = shot_b.get("camera_spec") or {}
    move_a = str(cam_a.get("camera_move") or "static")
    move_b = str(cam_b.get("camera_move") or "static")
    vec_a = CAMERA_MOVE_VECTORS.get(move_a, (0.0, 0.0, 0.0))
    vec_b = CAMERA_MOVE_VECTORS.get(move_b, (0.0, 0.0, 0.0))

    dot_motion = vec_a[0] * vec_b[0] + vec_a[1] * vec_b[1] + vec_a[2] * vec_b[2]
    motion_aligned = dot_motion > 0.25

    focal_a = shot_a.get("zoom_target_xy") or shot_a.get("focal_xy") or [0.5, 0.5]
    focal_b = shot_b.get("focal_xy") or [0.5, 0.5]
    focal_dist = math.hypot(float(focal_a[0]) - float(focal_b[0]), float(focal_a[1]) - float(focal_b[1]))

    loc_a = shot_a.get("location_id") or shot_a.get("place")
    loc_b = shot_b.get("location_id") or shot_b.get("place")
    same_location = bool(loc_a == loc_b) if (loc_a is not None or loc_b is not None) else True

    seg_a = shot_a.get("segment_id") or shot_a.get("scene")
    seg_b = shot_b.get("segment_id") or shot_b.get("scene")
    same_segment = bool(seg_a == seg_b) if (seg_a is not None or seg_b is not None) else True

    light_a = str(shot_a.get("lighting_and_time") or "").lower()
    light_b = str(shot_b.get("lighting_and_time") or "").lower()
    shared_light_tokens = set(light_a.split()) & set(light_b.split())
    lighting_coherent = len(shared_light_tokens) >= 1 or same_location

    return {
        "from_shot_id": shot_a.get("shot_id") or shot_a.get("id"),
        "to_shot_id": shot_b.get("shot_id") or shot_b.get("id"),
        "focal_xy_from": [round(float(focal_a[0]), 3), round(float(focal_a[1]), 3)],
        "focal_xy_to": [round(float(focal_b[0]), 3), round(float(focal_b[1]), 3)],
        "focal_distance_norm": round(focal_dist, 4),
        "camera_move_from": move_a,
        "camera_move_to": move_b,
        "motion_vector_dot": round(dot_motion, 3),
        "motion_direction_aligned": motion_aligned,
        "same_location": same_location,
        "same_segment": same_segment,
        "lighting_coherent": lighting_coherent,
    }


def _is_map_shot(shot: Dict[str, Any]) -> bool:
    vtype = str(shot.get("visual_type") or "")
    gmode = str(shot.get("generation_mode") or "")
    route = str(shot.get("route") or "")
    return route == "map_action" or vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D")


def select_optimal_cinematic_transition(
    shot_a: Dict[str, Any],
    shot_b: Dict[str, Any],
    fps: int = 24,
    allow_decorative_wipes: bool = False,
    honour_authored: bool = False,
) -> Dict[str, Any]:
    """Select the optimal cinematic transition and audio bridge between Shot A and Shot B (`ED-04` compliant).

    ``honour_authored`` (HF-1): when the outgoing shot carries the script's own ``transition_out``, that wins over the
    structural choice below (``AUTHORED_FRAMES``). Off by default, so every existing plan is what it was."""
    continuity = compute_visual_continuity_alignment(shot_a, shot_b)
    is_a_infographic = _is_map_shot(shot_a)
    is_b_infographic = _is_map_shot(shot_b)
    inherited_camera = bool(
        is_a_infographic
        and is_b_infographic
        and continuity["same_location"]
        and shot_b.get("inherit_camera", True) is not False
        and shot_b.get("prev_end_view", True) is not False
    )

    explicit_override = shot_a.get("explicit_transition_override")
    authored = str(shot_a.get("transition_out") or "") if honour_authored else ""
    if authored in AUTHORED_FRAMES:
        dur_frames = AUTHORED_FRAMES[authored]
        t_type = "hard_cut_with_jl_bridge" if dur_frames == 0 else authored
        audio_prelap_s = (
            0.15
            if (is_a_infographic and is_b_infographic and continuity["same_location"] and inherited_camera)
            else (0.30 if continuity["same_location"] else 0.40)
        )
    elif allow_decorative_wipes and explicit_override in TRANSITION_TYPES:
        t_type = str(explicit_override)
        dur_frames = 0 if t_type == "hard_cut_with_jl_bridge" else 10
        audio_prelap_s = 0.35
    # 0. Map -> Map handoff (M8): same location + inherited camera -> seamless 0f cut (0.15s prelap); else cross_dissolve_8f
    elif is_a_infographic and is_b_infographic:
        if continuity["same_location"] and inherited_camera:
            t_type = "hard_cut_with_jl_bridge"
            dur_frames = 0
            audio_prelap_s = 0.15
        else:
            t_type = "cross_dissolve_8f"
            dur_frames = 8
            audio_prelap_s = 0.35
    # 1. Map / Infographic -> Physical Location Scene Handoff
    elif is_a_infographic and not is_b_infographic:
        subtype_a = str(shot_a.get("infographic_subtype") or "")
        if "counter" in subtype_a or "diagram" in subtype_a or "timeline" in subtype_a:
            t_type = "infographic_number_to_scene_morph"
            dur_frames = 12
            audio_prelap_s = 0.45
        else:
            t_type = "map_to_location_zoom_through"
            dur_frames = 14
            audio_prelap_s = 0.50
    # 2. Physical Scene -> Map / Infographic Handoff
    elif not is_a_infographic and is_b_infographic:
        t_type = "cross_dissolve_8f"
        dur_frames = 8
        audio_prelap_s = 0.35
    # 3. Segment change or major location change (ED-04: dissolve only where place/segment changes)
    elif not continuity["same_segment"]:
        t_type = "cross_dissolve_8f"
        dur_frames = 8
        audio_prelap_s = 0.45
    # 4. Default inside a scene or across standard narrative cuts: hard cut with J/L audio bridge (ED-04)
    else:
        t_type = "hard_cut_with_jl_bridge"
        dur_frames = 0
        audio_prelap_s = 0.30 if continuity["same_location"] else 0.40

    cut_plan_transition = "cut" if t_type == "hard_cut_with_jl_bridge" or continuity["same_location"] else "dissolve"

    plan = {
        "from_shot_id": shot_a.get("shot_id") or shot_a.get("id"),
        "to_shot_id": shot_b.get("shot_id") or shot_b.get("id"),
        "transition_type": t_type,
        "cut_plan_transition": cut_plan_transition,
        "ed04_compliant": not (cut_plan_transition == "dissolve" and continuity["same_location"] and not (is_a_infographic or is_b_infographic)),
        "transition_frames": dur_frames,
        "transition_duration_sec": round(dur_frames / max(fps, 1), 4),
        "audio_j_cut_prelap_sec": audio_prelap_s,
        "audio_l_cut_postlap_sec": round(max(0.30, audio_prelap_s * 0.85) if audio_prelap_s >= 0.30 else audio_prelap_s * 0.85, 3),
        "zoom_target_xy": continuity["focal_xy_from"],
        "continuity": continuity,
    }
    if authored in AUTHORED_FRAMES:
        plan["authored"] = True
    return plan


def plan_episode_cinematic_transitions(
    script_doc: Dict[str, Any],
    fps: int = 24,
    allow_decorative_wipes: bool = False,
    honour_authored: bool = False,
) -> List[Dict[str, Any]]:
    """Build the complete shot-to-shot cinematic transition plan for an episode (`ED-04` compliant)."""
    shots = script_doc.get("shots", [])
    plans: List[Dict[str, Any]] = []
    for a, b in zip(shots, shots[1:]):
        plans.append(select_optimal_cinematic_transition(a, b, fps=fps, allow_decorative_wipes=allow_decorative_wipes,
                                                         honour_authored=honour_authored))
    return plans


def render_transition_frame_pair(
    frame_a: Image.Image,
    frame_b: Image.Image,
    transition_type: str,
    progress_u: float,
    zoom_target_xy: Sequence[float] = (0.58, 0.48),
    motion_direction: str = "right",
) -> Image.Image:
    """Render an intermediate transition frame (`0.0 <= progress_u <= 1.0`) between `frame_a` and `frame_b`."""
    u = float(min(1.0, max(0.0, progress_u)))
    ease_u = u * u * (3.0 - 2.0 * u)
    w, h = frame_a.size
    if frame_b.size != (w, h):
        frame_b = frame_b.resize((w, h), Image.BICUBIC)

    if transition_type == "hard_cut_with_jl_bridge":
        return frame_a if u < 0.5 else frame_b

    if transition_type == "fade_to_black":   # HF-1: the first half takes A down to black, the second brings B up from it
        src = np.asarray(frame_a if u <= 0.5 else frame_b, dtype=np.float32)
        gain = (1.0 - 2.0 * u) if u <= 0.5 else (2.0 * u - 1.0)
        return Image.fromarray(np.clip(src * gain, 0, 255).astype(np.uint8), mode="RGB")

    if transition_type in ("warm_dip", "warm_fire_glow_dip"):
        glow = np.array([235.0, 145.0, 62.0], dtype=np.float32)
        src = np.asarray(frame_a if u <= 0.5 else frame_b, dtype=np.float32)
        mix_g = (2.0 * u) if u <= 0.5 else (2.0 * (1.0 - u))
        out_arr = src * (1.0 - 0.78 * mix_g) + glow[None, None, :] * (0.78 * mix_g)
        return Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8), mode="RGB")

    if transition_type == "map_to_location_zoom_through":
        tx, ty = float(zoom_target_xy[0]) * w, float(zoom_target_xy[1]) * h
        z_a = 1.0 + 2.2 * (ease_u ** 1.6)
        cw_a, ch_a = w / z_a, h / z_a
        x0_a = max(0.0, min(w - cw_a, tx - cw_a * float(zoom_target_xy[0])))
        y0_a = max(0.0, min(h - ch_a, ty - ch_a * float(zoom_target_xy[1])))
        zoomed_a = frame_a.resize((w, h), Image.BICUBIC, box=(x0_a, y0_a, x0_a + cw_a, y0_a + ch_a))
        if ease_u > 0.25:
            zoomed_a = zoomed_a.filter(ImageFilter.GaussianBlur(radius=float(6.0 * ease_u)))

        z_b = 1.25 - 0.25 * ease_u
        cw_b, ch_b = w / z_b, h / z_b
        x0_b = (w - cw_b) / 2.0
        y0_b = (h - ch_b) / 2.0
        zoomed_b = frame_b.resize((w, h), Image.BICUBIC, box=(x0_b, y0_b, x0_b + cw_b, y0_b + ch_b))

        arr_a = np.asarray(zoomed_a, dtype=np.float32)
        arr_b = np.asarray(zoomed_b, dtype=np.float32)
        cloud_veil = math.sin(math.pi * ease_u) ** 2 * 0.22
        veil_color = np.array([210.0, 175.0, 120.0], dtype=np.float32)
        mixed = arr_a * (1.0 - ease_u) + arr_b * ease_u
        mixed = mixed * (1.0 - cloud_veil) + veil_color[None, None, :] * cloud_veil
        return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8), mode="RGB")

    if transition_type in ("infographic_number_to_scene_morph", "match_cut_shape_and_focus"):
        arr_a = np.asarray(frame_a, dtype=np.float32)
        arr_b = np.asarray(frame_b, dtype=np.float32)
        bloom = math.sin(math.pi * ease_u) * 0.14
        mixed = arr_a * (1.0 - ease_u) + arr_b * ease_u
        mixed[:, :, 0] += 255.0 * bloom * 0.9
        mixed[:, :, 1] += 255.0 * bloom * 0.65
        mixed[:, :, 2] += 255.0 * bloom * 0.25
        return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8), mode="RGB")

    # Default cross_dissolve_8f
    arr_a = np.asarray(frame_a, dtype=np.float32)
    arr_b = np.asarray(frame_b, dtype=np.float32)
    mixed = arr_a * (1.0 - ease_u) + arr_b * ease_u
    return Image.fromarray(np.clip(mixed, 0, 255).astype(np.uint8), mode="RGB")


def analyze_boundary_frames(frame_a: np.ndarray, frame_b: np.ndarray) -> Dict[str, Any]:
    """P0-4: Post-G7 visual-boundary analysis (MAD, luma distribution, colour temperature, composition continuity).

    Used as an editorial REVIEW signal, not an automatic override rule.
    """
    a = np.asarray(frame_a, dtype=np.float32)
    b = np.asarray(frame_b, dtype=np.float32)
    if a.shape != b.shape:
        im_b = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).resize((a.shape[1], a.shape[0]), Image.BILINEAR)
        b = np.asarray(im_b, dtype=np.float32)
    mad = float(np.mean(np.abs(a - b)))
    luma_a = 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    luma_b = 0.2126 * b[:, :, 0] + 0.7152 * b[:, :, 1] + 0.0722 * b[:, :, 2]
    mean_la = float(np.mean(luma_a))
    mean_lb = float(np.mean(luma_b))
    luma_delta = mean_lb - mean_la
    ha, _ = np.histogram(luma_a, bins=16, range=(0.0, 256.0), density=True)
    hb, _ = np.histogram(luma_b, bins=16, range=(0.0, 256.0), density=True)
    luma_hist_dist = float(np.sum(np.abs(ha - hb)) * 16.0)
    temp_a = float(np.mean(a[:, :, 0] - a[:, :, 2]))
    temp_b = float(np.mean(b[:, :, 0] - b[:, :, 2]))
    color_temp_delta = temp_b - temp_a
    # Composition continuity via normalized cross-correlation of downsampled luma
    la_flat = (luma_a - mean_la).ravel()
    lb_flat = (luma_b - mean_lb).ravel()
    denom = float(np.linalg.norm(la_flat) * np.linalg.norm(lb_flat))
    comp_corr = float(np.dot(la_flat, lb_flat) / denom) if denom > 1e-6 else (1.0 if abs(luma_delta) < 1.0 else 0.0)
    severe_jump = bool(mad >= 45.0 or abs(luma_delta) >= 40.0 or abs(color_temp_delta) >= 35.0)
    return {
        "measured": True,
        "mad": round(mad, 2),
        "luma_a": round(mean_la, 2),
        "luma_b": round(mean_lb, 2),
        "luma_delta": round(luma_delta, 2),
        "luma_hist_dist": round(luma_hist_dist, 4),
        "color_temp_delta": round(color_temp_delta, 2),
        "composition_continuity": round(comp_corr, 4),
        "severe_jump": severe_jump,
    }


def _read_boundary_frame_pair(clip_a: str | None, clip_b: str | None) -> Tuple[np.ndarray, np.ndarray] | None:
    if not clip_a or not clip_b:
        return None
    try:
        import cv2
    except Exception:
        return None
    cap_a = cv2.VideoCapture(str(clip_a))
    cap_b = cv2.VideoCapture(str(clip_b))
    try:
        if not cap_a.isOpened() or not cap_b.isOpened():
            return None
        n_a = int(cap_a.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if n_a > 0:
            cap_a.set(cv2.CAP_PROP_POS_FRAMES, max(0, n_a - 1))
        ok_a, fa = cap_a.read()
        ok_b, fb = cap_b.read()
        if not ok_a or not ok_b or fa is None or fb is None:
            return None
        return fa[:, :, ::-1], fb[:, :, ::-1]
    finally:
        cap_a.release()
        cap_b.release()


def build_boundary_manifest(
    script_doc: Dict[str, Any],
    shot_records: List[Dict[str, Any]] | None = None,
    fps: int = 24,
    *,
    honour_authored: bool = True,
    boundary_frames: Dict[str, Tuple[np.ndarray, np.ndarray]] | None = None,
) -> Dict[str, Any]:
    """P0-4: Build ONE authoritative picture-and-audio boundary manifest before G8.

    Both G8 (sound_plan / cue_sheet) and G9 (stage_assemble) consume this manifest so J/L overlaps,
    ambience bridges, foley/action continuations, intentional silence, and visual transitions share one timeline.
    """
    shots = list(script_doc.get("shots") or [])
    rec_by_id = {str(r.get("shot_id")): r for r in (shot_records or []) if isinstance(r, dict) and r.get("shot_id")}
    boundaries: List[Dict[str, Any]] = []
    for idx, (a, b) in enumerate(zip(shots, shots[1:])):
        sid_a = str(a.get("shot_id") or a.get("id") or f"shot_{idx}")
        sid_b = str(b.get("shot_id") or b.get("id") or f"shot_{idx + 1}")
        key = f"{sid_a}->{sid_b}"
        plan = select_optimal_cinematic_transition(a, b, fps=fps, allow_decorative_wipes=False, honour_authored=honour_authored)
        cont = plan["continuity"]
        same_loc = bool(cont.get("same_location"))
        silence = bool(a.get("intentional_silence") or b.get("intentional_silence"))
        ambience_bridge_s = 0.0 if (same_loc or silence) else 0.5
        foley_cont = bool(a.get("action_continuation") or b.get("action_continuation") or (same_loc and plan["transition_type"] == "hard_cut_with_jl_bridge"))

        pair = (boundary_frames or {}).get(key)
        if pair is None and sid_a in rec_by_id and sid_b in rec_by_id:
            pair = _read_boundary_frame_pair(rec_by_id[sid_a].get("clip_path"), rec_by_id[sid_b].get("clip_path"))
        vis = analyze_boundary_frames(pair[0], pair[1]) if pair is not None else {"measured": False, "severe_jump": False}

        authored_out = str(a.get("transition_out") or "")
        editorial_reason = str(a.get("editorial_reason") or a.get("cut_reason") or "").strip()
        flagged = bool(
            vis.get("severe_jump")
            and plan["transition_type"] == "hard_cut_with_jl_bridge"
            and authored_out == "hard_cut"
            and not editorial_reason
        )
        boundaries.append({
            "cut_index": idx,
            "boundary_id": key,
            "from_shot_id": sid_a,
            "to_shot_id": sid_b,
            "picture_transition": {
                "transition_type": plan["transition_type"],
                "transition_frames": plan["transition_frames"],
                "transition_duration_sec": plan["transition_duration_sec"],
                "cut_plan_transition": plan["cut_plan_transition"],
                "authored": bool(plan.get("authored")),
                "authored_transition_out": authored_out or None,
                "editorial_reason": editorial_reason or None,
            },
            "j_cut_prelap_sec": float(plan["audio_j_cut_prelap_sec"]),
            "l_cut_postlap_sec": float(plan["audio_l_cut_postlap_sec"]),
            "shared_ambience": bool(same_loc and not silence),
            "ambience_bridge_sec": ambience_bridge_s,
            "foley_action_continuation": foley_cont,
            "intentional_silence": silence,
            "visual_analysis": vis,
            "editorial_review_status": "REVIEW" if flagged else "PASS",
            "editorial_flag": "severe_jump_unmotivated_hard_cut" if flagged else None,
            "transition_plan": plan,
        })
    return {
        "schema": "boundary_manifest/1",
        "fps": int(fps),
        "boundaries": boundaries,
    }
