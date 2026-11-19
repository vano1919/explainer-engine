# Explainer Engine V4.3 — Complete Repository & Episode-First Production Package (`ep_toba` 3D Bande Dessinée Edition)

## 1. Repository-Wide Architecture Overview (Applies to ALL Episodes)
- **Episode-First Isolation (`explainer_engine/episode/context.py`, `explainer_engine/schemas/episode_manifest.schema.json`)**:
  - Every episode lives in an isolated project tree under `episodes/<episode_id>/` (`episode.json`, `episode_lock.json`, `story/`, `planning/`, `assets/`, `production/`, `audio/`, `editing/`, `renders/`, `qa/`, `logs/`).
  - `EpisodeContext`, `EpisodeResolver`, `validate_asset_compatibility()`, and `assets/library.py::find_for_episode()` enforce path isolation and historical-era compatibility across all eras (`prehistoric_pleistocene`, `ancient_classical`, `medieval`, `napoleonic_19th_century`, `modern_20th_century`).
- **Canonical Default Visual Style (`config/visual_style_presets.json`)**:
  - Default style preset: `bande_dessinee_3d_cinematic_adventure` (Cinematic Historical Realism + High-Budget European 3D Bande Dessinée Adventure hybrid: anatomical human proportions, no cartoon giant noses, expressive eyes, smooth 3D sculpted shading without 2D ink outlines, tactile leather/stone/moss/hide textures, warm diffused volumetric light, earthy palette of gold, moss green, slate grey, and terracotta).
- **Era-Gated Audio & Independent Narration Stem Verification (`explainer_engine/audio/`)**:
  - `sfx_planner.py`: Word-boundary regexes (`CAVALRY_REGEX`, `METAL_CLASH_REGEX`, `LITHIC_WEAPON_REGEX`, `VOLCANIC_REGEX`) + `SOUND_EVENT_TAXONOMY` + `ERA_COMPATIBILITY_TABLE`.
  - `environmental_sound_design.py`: `validate_narration_source_file()` blocks SFX/ambience packs from being loaded as narration; exports 5 separate 48kHz stereo stems (`narration.wav`, `music.wav`, `ambience.wav`, `sfx.wav`, `mix.wav`) with speech-gated sidechain ducking (`-5.0 dB` music, `-3.0 dB` ambience).
  - `sound_director.py`: `_check_stems()` runs independent `SD-02` + `dropouts.scan()` verification on `stems["narration"]` across active spoken word spans.
- **Real Natural Earth 1:50m GIS + Multidirectional DEM Shaded-Relief Maps (`explainer_engine/maps/`)**:
  - `plate.py`: `generate_regional_dem_grid()`, `compute_multidirectional_hillshade()` (`225°, 270°, 315°, 360°` Horn gradient), `apply_hypsometric_tint()`, and deterministic `spec_hash()` caching.
  - `render.py`: `build_episode_gis_map_spec()` and `render_episode_gis_map_clip()` support any episode map shot via custom `shot["map_spec"]` or preset coordinates.
- **Multi-Axis 2.5D Smoothstep Camera & Blender Non-Rig DOF (`explainer_engine/production/`, `explainer_engine/blender/bpy/render_shot.py`)**:
  - `parallax.py` & `cinematic_image_animator.py`: 2D `(dx, dy)` depth parallax with face-safe mask protection and edge-clamped smoothstep trajectories.
  - `blender/bpy/render_shot.py`: Keyframes `focus_distance` (`focus_at`) and `aperture_fstop` (`fstop`) on non-rig cameras as well as rig cameras.
- **Editorial Transitions (`explainer_engine/edit/cinematic_transitions.py`)**:
  - Aligned with `cut_plan.py` (`ED-04`): `hard_cut_with_jl_bridge` by default, `map_to_location_zoom_through` on map handoffs, `cross_dissolve_8f` on segment/location transitions, zero decorative `smoke_wipe` spam.

## 2. Included `episodes/ep_toba/` 3D Bande Dessinée Assets
- **6 Replaced Reference Anchors**:
  - Characters (`episodes/ep_toba/assets/reference/characters/`): `char_kael_74000bce.jpg`, `char_sena_74000bce.jpg`, `char_thar_74000bce.jpg`
  - Locations (`episodes/ep_toba/assets/reference/locations/`): `loc_rift_cave_hearth.jpg`, `loc_shinfa_ash_riverbed.jpg`, `loc_sumatra_toba_caldera.jpg`
- **22 Replaced 3D Bande Dessinée Scene Keyframes (`episodes/ep_toba/assets/generated/images/`)**:
  - `S01_SH001_start.jpg` .. `S03_SH004_start.jpg`
- **3 GIS + DEM Shaded-Relief Map Renders (`episodes/ep_toba/assets/maps/renders/`)**:
  - `S01_SH008_gis_start.png` / `_end.png`, `S02_SH001_gis_start.png` / `_end.png`, `S02_SH010_gis_start.png` / `_end.png`
- **Visual Verification Contact Sheet**:
  - `episodes/ep_toba/qa/contact_sheets/ep_toba_3d_style_all_scenes_contact_sheet.jpg`
- **12-Minute & 2-Minute Scripts & Manifests**:
  - `episodes/ep_toba/story/production_script.json` (Full 12-minute, 138-shot script with 3 multi-line dramatic dialogue scenes `S05`, `S08`, `S09`)
  - `episodes/ep_toba/planning/production_script_2min.json` (2-minute, 25-shot pilot script)
  - `episodes/ep_toba/planning/g6_g7_manifest.json` & `g4_audio_manifest.json`

## 3. Quick Verification Commands
```bash
python3 -m pytest tests/unit/test_episode_first_isolation_and_v4_3_fixes.py tests/unit/test_maps.py tests/unit/test_sound_director.py tests/unit/test_cut_plan.py tests/unit/test_parallax.py tests/unit/test_asset_library.py tests/unit/test_asset_library_v2.py tests/unit/test_dramatic_scene_and_cold_open_integration.py
```
