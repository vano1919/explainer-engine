"""Gate G5 Gemini Native Image Generation Engine (D-124).

Replaces Qwen-Image-2.1 and Qwen-Image-Edit-2511 completely.
Gemini is the sole Image Generation Engine for:
1. 10% Map, Diagram & War-Table Relief Assets
2. 30% Photo-Collage & layered collage Multi-Layer Still Assets
3. 60% Video Keyframe Assets (Start & End Frames for Wan 2.2)

Enforces:
- Reference Library style & reference plate injection (`reference_library.py`)
- 100% unique scene generation per shot (`PV-NO-CROP-PADDING`: never cropping 1 image across a minute)
- Contact sheet generation (`qa/frame_review.py`) for Creator Gate G5 inspection.
"""
from __future__ import annotations

from typing import Any, Dict, List
from explainer_engine.assets.reference_library import (
    DEFAULT_CHIAROSCURO_LIBRARY,
    select_reference_plate,
    validate_reference_library,
)
from explainer_engine.imagegen.asset_plan import extract_complete_asset_plan


def build_gemini_generation_queue(
    script_doc: Dict[str, Any],
    library: Dict[str, Any] = DEFAULT_CHIAROSCURO_LIBRARY,
) -> Dict[str, Any]:
    """Build the ordered queue of `image_gen:generate_image` calls for Gate G5."""
    lib_errors = validate_reference_library(library)
    if lib_errors:
        raise ValueError(f"Cannot build Gate G5 queue with unlocked Reference Library: {lib_errors}")

    plan = extract_complete_asset_plan(script_doc, library=library)
    if plan["validation_errors"]:
        raise ValueError(f"Asset plan failed D-124 unique-scene check: {plan['validation_errors'][0]['detail']}")

    queue: List[Dict[str, Any]] = []
    for bucket_name, items in (
        ("10pct_maps_and_diagrams", plan["maps_and_diagrams_10pct"]),
        ("30pct_photo_collage", plan["photo_collage_30pct"]),
        ("60pct_video_keyframes", plan["video_keyframes_60pct"]),
    ):
        for item in items:
            shot_id = item["shot_id"]
            ref_anchor = item["reference_library_anchor"]
            queue.append({
                "asset_id": f"{shot_id}_start",
                "shot_id": shot_id,
                "segment_id": item["segment_id"],
                "bucket": bucket_name,
                "frame_role": "start_frame",
                "aspect_ratio": "16:9",
                "image_references": [ref_anchor],
                "query": f"{item['start_frame_prompt']} clean composition, text-free, no labels, no watermarks",
            })
            if item.get("needs_end_frame") and item.get("end_frame_prompt"):
                queue.append({
                    "asset_id": f"{shot_id}_end",
                    "shot_id": shot_id,
                    "segment_id": item["segment_id"],
                    "bucket": bucket_name,
                    "frame_role": "end_frame",
                    "aspect_ratio": "16:9",
                    "image_references": [ref_anchor, f"{shot_id}_start"],
                    "query": f"{item['end_frame_prompt']} clean composition, text-free, no labels, no watermarks",
                })

    return {
        "schema": "g5_gemini_image_queue/1",
        "episode_id": script_doc.get("episode_id", "unknown"),
        "engine": "gemini_native_image_engine",
        "qwen_removed": True,
        "total_images_to_generate": len(queue),
        "bucket_breakdown": plan["counts"],
        "queue": queue,
    }
