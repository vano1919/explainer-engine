# Session 5 Map Pipeline Port (`M1`–`M9`) — Changes Summary

- **M1 (`explainer_engine/maps/actions.py` `camera()` & `lerp_view()`)**:
  - Updated `_lerp_view` and added public `lerp_view` to interpolate `span_km` in logarithmic scale (`exp(log(s0) + (log(s1) - log(s0)) * u)`) and couple pan progress to scale change (`pan_u = 0.65 * ((s - s0) / (s1 - s0)) + 0.35 * u` when `|s1 - s0| > 25 km`).
  - Updated `camera()` so both `fly_to` and `zoom` honour `a["value"]` (target `span_km`) rather than keeping `cur["span_km"]` on `fly_to`.

- **M2 (`explainer_engine/maps/actions.py` standing lines)**:
  - Added `_stands(a)` (`bool(a.get("stands") or a.get("cues") == "none")`).
  - Set `start = 0` in `plan()` and returned `1.0` from `_u()` and `_progress()` for standing actions so pre-existing front/route lines are drawn at 100% completion from frame `0` (no blank frames across cuts), while keeping `word_start` for audio/timing inspection.

- **M3 (`explainer_engine/maps/actions.py`, `explainer_engine/production/map_clip.py`, `explainer_engine/episode/run.py`)**:
  - Extended `actions._first_view(shot, acts, prev_end_view=None)` and `actions.plan(..., prev_end_view=None)` to start at `prev_end_view` when provided and smoothly transition to the shot's `_own_view` in `camera()`.
  - Updated `map_clip.render_action_map_clip` to accept `prev_end_view` (dict or path) and atomically write `<cache>/<shot_id>_end_view.json` containing `{"lon", "lat", "span_km"}` at `frames - 1`.
  - Updated `episode/run.py` `stage_clips` (and `_clip_key`) to pass `prev_end_view` from the preceding map shot's end view only when consecutive shots are both map shots in the same `location_id`/`place`.

- **M4 (`explainer_engine/maps/actions.py`, `explainer_engine/production/map_clip.py`)**:
  - Updated `word_frames` and `map_clip._resolve_spine` to consume the measured word spine passed by `stage_clips` (or `production/spines/<shot_id>.json` / `audio/timing.json`), falling back to the uniform `[LEAD_IN, 1 - LEAD_OUT]` spread only when no measured spine exists, and recording `spine_basis` (`"measured"` vs `"estimated"`) on both `plan` and `render_action_map_clip` return dicts.

- **M5 (`explainer_engine/maps/actions.py` `place_label_8pos()`, `safe_frame_bounds()`, HUD date chips)**:
  - Added `safe_frame_bounds` (`54 px` horizontal, `40 px` top, `66 px` bottom at `1920x1080`, scaled proportionally) and `place_label_8pos` (8-candidate greedy solver with leader-line fallback).
  - Pre-collected obstacle bounding boxes (`_precollect_obstacles`) for active path segments, HUD date chips, counters, and bars so geo labels avoid overlapping drawn lines, HUD cards, and earlier labels.
  - Rendered `label` actions authored at `from: "chip_*"` as top-left screen-space HUD cards rather than geographic map pins.

- **M6 (`explainer_engine/maps/actions.py` `counter_layout()`, `_u_counter()`)**:
  - Locked the `counter` panel width to `c.text_width(final_text, size) + size` across all frames so the box never jitters as digits grow.
  - Added `_u_counter(a, f)` starting at `(f - a["start"] + 1) / span` with a non-zero floor (`>= 1` for integer targets) so the first visible frame never displays `0`.

- **M7 (`explainer_engine/maps/data/build_1914.py`, `borders_1914.json.gz`, `SOURCES.json`, `geo.py`, `plate.py`)**:
  - Added `explainer_engine/maps/data/build_1914.py` to build `borders_1914.json.gz` (`5,223` bytes, sha256 `96b07a722963ea034892f1a3dce586ebce81a230c5fa0b1fe43638fb8dff1fa6`) covering 1914 Germany (incl. Alsace-Lorraine and Eupen-Malmedy), France, Belgium, Netherlands, Luxembourg, Switzerland, United Kingdom, Austria-Hungary, Italy, and Denmark, and recorded its source + licence under `borders_1914` in `SOURCES.json`.
  - Updated `geo.py` (`dataset_1914`, `borders_1914`) and `plate.py` (`is_pre_1945`, `draw_base`, `spec_hash`) to draw `borders_1914` instead of modern borders whenever the episode/shot period is `< 1945`.

- **M8 (`explainer_engine/edit/cinematic_transitions.py`)**:
  - Added the `map -> map` branch in `select_optimal_cinematic_transition`: same location + inherited camera -> `hard_cut_with_jl_bridge` (`0` blend frames, `0.15 s` audio prelap); different location -> `cross_dissolve_8f` (`8` frames).

- **M9 (`explainer_engine/maps/draw.py`)**:
  - Added `glyph_mask`, `has_missing_glyph`, `font_for_text`, and `MAP_FONT_FALLBACKS` (`Inter`, `DejaVuSans`, `LiberationSans`) so accented and special characters (`Liège–Armentières`) never render as `.notdef` boxes even if `assets/fonts/Inter.ttf` is absent.

- **Tests (`tests/unit/test_v43_map_actions.py`)**:
  - Added 9 focused unit tests (`test_m1_*` .. `test_m9_*`) and 1 visual keyframe contact-sheet test (`test_visual_s02_sh001_to_003_keyframes_contact_sheet_and_safe_frame`).
