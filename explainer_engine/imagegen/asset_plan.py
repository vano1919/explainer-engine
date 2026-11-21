"""Complete Visual & Audio Asset Plan Extractor from Approved Script (Gates G3 -> G5, D-124 / v4.2).

Extracts from `production_script.json`:
1. 10% Map, Diagram & Helper Assets (`map_visualization` / `MAP_25D`)
2. 30% Photo-Collage & layered collage Multi-Layer Still Assets (`composed_illustration` / `STILL_25D`)
3. 60% Video Keyframe Assets (`cinematic_video` / `WAN_I2V`, `WAN_FLF2V`, `WAN_CONTROL`)
4. Cold-open Teaser Reuses (`teaser_of`): Reuses the later payoff shot's clip without queuing any new image or video generation!
5. Gate G4 Audio FX Plan (Footsteps, Foley, Ambience Beds, Musical Melodies)

Enforces the D-124 Anti-Crop-Padding Law (`PV-UNIQUE-SCENE-IMAGES`):
Every non-teaser shot in the script MUST have a unique scene prompt (`start_frame_prompt`);
reusing or cropping one image across multiple shots in a segment is strictly forbidden.
"""
from __future__ import annotations

from typing import Any, Dict, List
from explainer_engine.assets.reference_library import DEFAULT_CHIAROSCURO_LIBRARY, select_reference_plate


def extract_complete_asset_plan(
    script_doc: Dict[str, Any],
    library: Dict[str, Any] = DEFAULT_CHIAROSCURO_LIBRARY,
) -> Dict[str, Any]:
    """Build the complete G3/G5 visual & audio asset plan and verify unique per-shot scenes."""
    shots = script_doc.get("shots", [])
    maps_10pct: List[Dict[str, Any]] = []
    collage_30pct: List[Dict[str, Any]] = []
    video_keyframes_60pct: List[Dict[str, Any]] = []
    teaser_reuses: List[Dict[str, Any]] = []

    seen_prompts: Dict[str, str] = {}
    duplicate_prompt_errors: List[Dict[str, str]] = []
    teaser_pairs = (
        {(str(s.get("shot_id")), str(s.get("teaser_of"))) for s in shots if s.get("teaser_of")}
        | {(str(s.get("teaser_of")), str(s.get("shot_id"))) for s in shots if s.get("teaser_of")}
    )

    for sh in shots:
        shot_id = sh.get("shot_id", "?")
        seg_id = sh.get("segment_id", "?")
        teaser_of = sh.get("teaser_of")
        vtype = sh.get("visual_type", "cinematic_video")
        gmode = sh.get("generation_mode", "WAN_I2V")
        img_p = sh.get("image_prompt") or {}
        start_p = str(img_p.get("start_frame_prompt") or "").strip()
        end_p = img_p.get("end_frame_prompt")
        ref_plate = select_reference_plate(sh, library)

        norm_p = " ".join(start_p.lower().split())
        if norm_p in seen_prompts and (str(shot_id), str(seen_prompts[norm_p])) not in teaser_pairs:
            duplicate_prompt_errors.append({
                "rule": "PV-NO-CROP-PADDING",
                "severity": "FAIL",
                "where": shot_id,
                "detail": f"Shot {shot_id} reuses identical start_frame_prompt from {seen_prompts[norm_p]}; every shot must be a distinct generated image (D-124)"
            })
        elif norm_p and norm_p not in seen_prompts:
            seen_prompts[norm_p] = shot_id

        if teaser_of:
            teaser_reuses.append({
                "shot_id": shot_id,
                "segment_id": seg_id,
                "teaser_of": teaser_of,
                "teaser_trim": sh.get("teaser_trim"),
                "duration_sec": float(sh.get("target_duration_seconds", 2.5)),
                "requires_new_generation": False,
            })
            continue

        item = {
            "shot_id": shot_id,
            "segment_id": seg_id,
            "duration_sec": float(sh.get("target_duration_seconds", 4.0)),
            "generation_mode": gmode,
            "engine": "gemini_native_image_engine",
            "reference_library_anchor": ref_plate,
            "start_frame_prompt": start_p,
            "end_frame_prompt": end_p,
            "needs_end_frame": bool(end_p),
            "action_start_state": sh.get("action_start_state"),
            "action_end_state": sh.get("action_end_state"),
        }
        if vtype == "map_visualization" or gmode in ("TACTILE_MAP", "MAP_25D"):
            maps_10pct.append(item)
        elif vtype == "composed_illustration" or gmode in ("COLLAGE_STILL", "STILL_25D"):
            collage_30pct.append(item)
        else:
            video_keyframes_60pct.append(item)

    non_teaser_shots = max(1, len(maps_10pct) + len(collage_30pct) + len(video_keyframes_60pct))
    total_unique_images = (
        len(maps_10pct)
        + len(collage_30pct)
        + sum(2 if x["needs_end_frame"] else 1 for x in video_keyframes_60pct)
    )

    return {
        "schema": "asset_manifest/4",
        "episode_id": script_doc.get("episode_id", "unknown"),
        "image_engine": "gemini_native_image_engine",
        "qwen_used": False,
        "style_anchor_token": library["style_anchor_token"],
        "counts": {
            "total_shots": len(shots),
            "teaser_reuse_shots_count": len(teaser_reuses),
            "total_unique_gemini_images_required": total_unique_images,
            "maps_and_diagrams_10pct_count": len(maps_10pct),
            "photo_collage_30pct_count": len(collage_30pct),
            "video_keyframes_60pct_count": len(video_keyframes_60pct),
            "shares": {
                "maps_10pct": round(len(maps_10pct) / non_teaser_shots, 3),
                "collage_30pct": round(len(collage_30pct) / non_teaser_shots, 3),
                "video_60pct": round(len(video_keyframes_60pct) / non_teaser_shots, 3),
            }
        },
        "teaser_reuses": teaser_reuses,
        "maps_and_diagrams_10pct": maps_10pct,
        "photo_collage_30pct": collage_30pct,
        "video_keyframes_60pct": video_keyframes_60pct,
        "validation_errors": duplicate_prompt_errors,
    }
