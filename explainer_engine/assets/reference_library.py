"""Persistent Reference Library manager (Gate G0, D-124).

Ensures that before any episode's photos are generated at Gate G5, a creator-approved
Reference Library (`reference_library/1`) is locked and its style_anchor_token,
negative_prompt, and category reference plates are injected into every 10%, 30%, and 60% prompt.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "reference_library.schema.json"

DEFAULT_CHIAROSCURO_LIBRARY: Dict[str, Any] = {
    "schema": "reference_library/1",
    "status": "LOCKED_APPROVED_BY_CREATOR",
    "style_name": "Luminescent Chiaroscuro & Tactile Mythic Realism",
    "style_anchor_token": "Luminescent Chiaroscuro and Tactile Mythic Realism historical docudrama",
    "negative_prompt": (
        "2D comic ink outlines, cartoon cel-shading, anime, plastic 3D CGI sheen, "
        "flat digital vector map, blurry faces, extra fingers, watermark, text overlay, subtitles"
    ),
    "visual_principles": [
        "Tactile 35mm anamorphic chiaroscuro and physical material textures (wet mud, heavy wool, hammered copper, vellum, obsidian stone)",
        "Sculptural single-source volumetric golden-amber light shafts cutting through deep indigo/slate shadows",
        "Zero 2D comic outlines and zero plastic CGI sheen",
        "10% Maps built as physical war-room table artifacts (aged walnut, hammered copper relief, liquid gold veins, wax candles)"
    ],
    "categories": {
        "battlefield_and_exterior_anchors": ["REF_01_Battlefield_Chiaroscuro_Anchor.jpg"],
        "interior_and_character_anchors": ["REF_02_Interior_Character_Chiaroscuro_Anchor.jpg"],
        "dynamic_action_anchors": ["REF_03_Dynamic_Action_Chiaroscuro_Anchor.jpg"],
        "tactile_map_and_diagram_anchors": ["REF_04_Tactile_Copper_Gold_Map_Anchor.jpg"]
    }
}


def validate_reference_library(doc: Dict[str, Any]) -> List[str]:
    """Validate a Reference Library manifest against reference_library.schema.json."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors: List[str] = []
    try:
        jsonschema.validate(instance=doc, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(exc.message)
    if doc.get("status") != "LOCKED_APPROVED_BY_CREATOR":
        errors.append("Reference Library status must be LOCKED_APPROVED_BY_CREATOR before Gate G5 photo generation.")
    return errors


def select_reference_plate(shot: Dict[str, Any], library: Dict[str, Any] = DEFAULT_CHIAROSCURO_LIBRARY) -> str:
    """Return the canonical Reference Library anchor filename for a given shot's visual_type and mode."""
    cats = library["categories"]
    vtype = shot.get("visual_type", "")
    gmode = shot.get("generation_mode", "")
    if vtype == "map_visualization" or gmode == "MAP_25D":
        return cats["tactile_map_and_diagram_anchors"][0]
    if vtype == "composed_illustration" or gmode == "STILL_25D":
        return cats["interior_and_character_anchors"][0]
    if shot.get("camera_spec", {}).get("camera_move", "static") != "static":
        return cats["dynamic_action_anchors"][0]
    return cats["battlefield_and_exterior_anchors"][0]
