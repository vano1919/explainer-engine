---
name: film-style-bible
description: Aggregate and enforce one unified Film Style Bible across maps, Gemini reference photos, 2.5D living stills, LTX-2.5 acting/motion style, visual bridges, and sound palette.
---
# Unified Film Style Bible

## Purpose
Prevent visual, tonal, or acting drift between maps, reference photos, 2.5D living stills, video clips, YouTube visual bridges, and audio mixes by compiling all layer directives from a single `film_style_bible/1` document (`explainer_engine.episode.style_bible`).

## Precedence Rule (Supersedes Legacy Infographic & Storybook Palettes — Antigravity + Claude Code)
`config/super_realistic_film_bible.json` and the active episode's `film_style_bible/1` realistic 35mm cinema palette + unified post-grade (`explainer_engine.finish.cinema_grade`, `assets/luts/historical_docudrama_35mm.cube`) **strictly supersede** legacy flat/cartoon/storybook tokens in `explainer_engine/design/palette.json` and `config/visual_style_presets.json` (`main_style_5709.png`, `ComicNeue`, `Bangers`). Every active prompt MUST pass `lint_super_realistic_prompt()`. Maps, 2.5D scenes, LTX-2.5 clips, stills, and visual bridges MUST share one unified filmic contrast curve, color temperature, subtle 35mm grain, and soft optical vignette.

## Required Sections
1. `visual_identity`: era look words, minimum 3-color `palette_hex`, film grain/grade target (`cinema_grade`).
2. `map_aesthetic`: real Natural Earth shaded relief + bathymetry tinted to the episode film palette, `Liberation Serif` typography, non-overlapping dark translucent cartographic pins/badges, smooth eased camera moves, and synced map-action SFX.
3. `photo_direction`: lighting discipline, lens grammar (`35mm`/`50mm`), composition framing rules.
4. `acting_and_motion`: `acting_register` (`restrained_documentary_realism`, `intimate_chamber_drama`, `gritty_field_chronicle`, or `stylized_graphic_noir`), continuous Depthflow-style zero-tear 2.5D parallax (zero static opening shots, zero fake procedural fire blobs), and `preferred_camera_moves` (strictly from `explainer_engine.core.camera_vocab.ALLOWED_CAMERA_MOVES`).
5. `visual_bridges`: `Liberation Serif` typography, tight dynamic `textbbox` sizing, smooth alpha fade-in/fade-out, unified film grade.
6. `sound_palette`: strictly scene-locked `scene_environment` ambience (never constant unrelated rain across dry/map scenes), synchronized CC0 map-action SFX, subtle ducked documentary underscore, and ITU-R BS.1770-4 `-14.0 LUFS` / `<= -1.0 dBTP` mastering.

## Usage
Call `validate_film_style_bible(bible)` before production starts and inject `render_layer_directives(bible)` into map specs, photo turn-packs, 2.5D renders, visual bridges, and scene-locked sound plans.
