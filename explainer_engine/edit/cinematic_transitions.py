"""First-Class Continuity-Aware Cinematic Transition System (`cinematic_transitions.py`, v4.3).

Aligned with `explainer_engine.production.cut_plan` (`ED-04`):
- Hard cuts (`hard_cut_with_jl_bridge`, `cut_plan_transition = "cut"`) are the editorial default inside a location/scene.
- Special transitions are used ONLY when structurally justified:
  1. `map_to_location_zoom_through` / `infographic_number_to_scene_morph`: Handoffs between a 10% GIS map/infographic
     and a physical historical location shot.
  2. `cross_dissolve_8f` (`cut_plan_transition = "dissolve"`): Segment or location transitions (`not same_location` or `not same_segment`).
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
    vtype_a = str(shot_a.get("visual_type") or "")
    vtype_b = str(shot_b.get("visual_type") or "")
    gmode_a = str(shot_a.get("generation_mode") or "")
    gmode_b = str(shot_b.get("generation_mode") or "")

    is_a_infographic = vtype_a == "map_visualization" or gmode_a in ("TACTILE_MAP", "MAP_25D")
    is_b_infographic = vtype_b == "map_visualization" or gmode_b in ("TACTILE_MAP", "MAP_25D")

    explicit_override = shot_a.get("explicit_transition_override")
    authored = str(shot_a.get("transition_out") or "") if honour_authored else ""
    if authored in AUTHORED_FRAMES:
        dur_frames = AUTHORED_FRAMES[authored]
        t_type = "hard_cut_with_jl_bridge" if dur_frames == 0 else authored
        audio_prelap_s = 0.25 if continuity["same_location"] else 0.35
    elif allow_decorative_wipes and explicit_override in TRANSITION_TYPES:
        t_type = str(explicit_override)
        dur_frames = 0 if t_type == "hard_cut_with_jl_bridge" else 10
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
        audio_prelap_s = 0.25 if continuity["same_location"] else 0.35

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
        "audio_l_cut_postlap_sec": round(audio_prelap_s * 0.85, 3),
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
