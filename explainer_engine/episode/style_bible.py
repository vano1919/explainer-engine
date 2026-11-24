"""Unified Film Style Bible aggregating visual look, maps, photos, LTX acting/motion, visual bridges, and sound.

Extends ``episode_film/1`` so every production layer (MapLibre maps, Gemini reference photos,
2.5D living motion, LTX-2.5 cinematic acting/video, YouTube visual bridges, and sound design)
inherits a single coherent artistic identity instead of drifting across disconnected prompts.
"""
from __future__ import annotations

from typing import Any

from explainer_engine.core.camera_vocab import ALLOWED_CAMERA_MOVES
from explainer_engine.core.errors import ContractError

SCHEMA = "film_style_bible/1"

REQUIRED_SECTIONS = (
    "visual_identity",
    "map_aesthetic",
    "photo_direction",
    "acting_and_motion",
    "visual_bridges",
    "sound_palette",
)

VALID_ACTING_REGISTERS = frozenset(
    {
        "restrained_documentary_realism",
        "intimate_chamber_drama",
        "gritty_field_chronicle",
        "stylized_graphic_noir",
    }
)


def validate_film_style_bible(bible: dict[str, Any]) -> list[str]:
    """Validate a ``film_style_bible/1`` document and return a list of contract violations."""
    errors: list[str] = []
    if not isinstance(bible, dict):
        return ["Film style bible must be a JSON object"]
    if bible.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA!r}, got {bible.get('schema')!r}")
    for key in ("film_id", "era", "title"):
        if not isinstance(bible.get(key), str) or not bible[key].strip():
            errors.append(f"missing non-empty top-level field {key!r}")

    for sec in REQUIRED_SECTIONS:
        if not isinstance(bible.get(sec), dict) or not bible[sec]:
            errors.append(f"missing or empty section {sec!r}")

    am = bible.get("acting_and_motion") or {}
    if isinstance(am, dict):
        reg = am.get("acting_register")
        if reg not in VALID_ACTING_REGISTERS:
            errors.append(f"acting_and_motion.acting_register invalid: {reg!r}")
        moves = am.get("preferred_camera_moves") or []
        if not isinstance(moves, list) or not moves:
            errors.append("acting_and_motion.preferred_camera_moves must be a non-empty list")
        else:
            bad = [m for m in moves if m not in ALLOWED_CAMERA_MOVES]
            if bad:
                errors.append(f"acting_and_motion.preferred_camera_moves contains disallowed ops: {bad}")
        if not isinstance(am.get("motion_discipline"), str) or len(am["motion_discipline"].strip()) < 10:
            errors.append("acting_and_motion.motion_discipline must be a concrete directive (>=10 chars)")

    vis = bible.get("visual_identity") or {}
    if isinstance(vis, dict):
        pal = vis.get("palette_hex")
        if not isinstance(pal, list) or len(pal) < 3:
            errors.append("visual_identity.palette_hex must list at least 3 hex colors")

    return errors


def render_layer_directives(bible: dict[str, Any]) -> dict[str, str]:
    """Compile one unified Film Style Bible into concrete prompt directives for every production layer."""
    errs = validate_film_style_bible(bible)
    if errs:
        raise ContractError(f"Invalid film_style_bible/1: {errs}")

    vis = bible["visual_identity"]
    mp = bible["map_aesthetic"]
    ph = bible["photo_direction"]
    am = bible["acting_and_motion"]
    vb = bible["visual_bridges"]
    snd = bible["sound_palette"]

    palette = ", ".join(vis["palette_hex"])
    return {
        "map_directive": (
            f"MapLibre/Python style '{mp.get('style_preset', 'dark_relief')}', font '{mp.get('font', 'Liberation Serif')}', "
            f"palette [{palette}], era '{bible['era']}'."
        ),
        "photo_directive": (
            f"Reference photo look: {vis.get('look_words', '')}; lighting: {ph.get('lighting', '')}; "
            f"lens: {ph.get('lens_grammar', '35mm/50mm naturalistic')}; palette [{palette}]."
        ),
        "ltx_acting_motion_directive": (
            f"Acting register: {am['acting_register']}; motion discipline: {am['motion_discipline']}; "
            f"allowed camera moves: {', '.join(am['preferred_camera_moves'])}."
        ),
        "visual_bridge_directive": (
            f"YouTube docudrama bridges: typography '{vb.get('typography', 'clean serif/sans pair')}', "
            f"accent '{vb.get('accent_hex', vis['palette_hex'][0])}', pacing '{vb.get('pacing', 'on-word kinetic reveal')}'."
        ),
        "sound_directive": (
            f"Sound bed: {snd.get('ambience_character', 'natural era roomtone')}; "
            f"music: {snd.get('music_mood', 'restrained historical strings')}; "
            f"foley: {snd.get('foley_realism', 'grounded physical foley, library-first')}."
        ),
    }
