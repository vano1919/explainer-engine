---
name: film-style-bible
description: Aggregate and enforce one unified Film Style Bible across maps, Gemini reference photos, 2.5D living stills, LTX-2.5 acting/motion style, visual bridges, and sound palette.
---
# Unified Film Style Bible

## Purpose
Prevent visual, tonal, or acting drift between MapLibre maps, Gemini reference photos, 2.5D living stills, LTX-2.5 video clips, YouTube visual bridges, and audio mixes by compiling all layer directives from a single `film_style_bible/1` document (`explainer_engine.episode.style_bible`).

## Required Sections
1. `visual_identity`: era look words, minimum 3-color `palette_hex`, film grain/grade target.
2. `map_aesthetic`: MapLibre style preset, typography (`Liberation Serif` or era-matched font), tactical vector colors.
3. `photo_direction`: lighting discipline, lens grammar (`35mm`/`50mm`), composition framing rules.
4. `acting_and_motion`: `acting_register` (`restrained_documentary_realism`, `intimate_chamber_drama`, `gritty_field_chronicle`, or `stylized_graphic_noir`), `motion_discipline`, and `preferred_camera_moves` (strictly from `explainer_engine.core.camera_vocab.ALLOWED_CAMERA_MOVES`).
5. `visual_bridges`: typography pair, accent color, on-word kinetic reveal pacing.
6. `sound_palette`: ambience bed character, music mood, grounded physical foley standard.

## Usage
Call `validate_film_style_bible(bible)` before production starts and inject `render_layer_directives(bible)` into map specs, Gemini browser photo turn-packs, LTX photo-grounded prompts, and sound plans.
