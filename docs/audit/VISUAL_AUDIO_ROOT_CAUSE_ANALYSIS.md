# Visual & Audio Root-Cause Analysis (Rule vs. Code Audit of `ebd6363a` / `demo_final_v2.mp4`)

## Executive Summary
Human inspection of `demo_final_v2.mp4`, `demo_map_scene.mp4`, and `demo_25d_scene.mp4` exposed 6 systemic cinema-quality failures that passed 153 synthetic unit tests. Every failure traces to a concrete rule-vs-code conflict or rendering architecture defect documented below.

## Root Cause 1 — Flat, Impoverished Maps (Legacy Palette Shadowing + Missing Real Earth Relief)
- **Files & Lines:** `explainer_engine/design/palette.json:4-21` (legacy cartoon Kit-mascot tokens: `kit_card: #E0A458`, `answer_coral: #FF6B5B`, `mechanism_teal: #2EC4B6`, `support_blue: #4D9DE0`) and `explainer_engine/maps/plate.py:48-80` (`colours()` pulls flat infographic tokens; `relief_rgb()` lacks Natural Earth color relief, bathymetry, multi-directional hillshade, and unified film grading).
- **Fix:** Integrate real Public Domain **Natural Earth** color relief (`NE1_HR.tif`) + shaded relief (`SR_HR.tif`) with multi-directional hillshade, bathymetry, and slope contrast in `explainer_engine/maps/cinema_map.py`, harmonized to the active episode's `film_style_bible/1` and graded via `explainer_engine/finish/cinema_grade.py`. Explicitly supersede `design/palette.json` in `.agents/skills/film-style-bible/SKILL.md`.

## Root Cause 2 — Static / Frozen Opening 2.5D Shot
- **Files & Lines:** `explainer_engine/production/layers25d.py:69,280-290` (pure cubic `ease_in_out` yields `du/dt = 0` at `t=0`, freezing the first 1.5–2.0s of opening portrait shots).
- **Fix:** Blend linear + smoothstep easing (`0.42 * u + 0.58 * smoothstep(u)`) in `explainer_engine/production/cinema_25d.py` so continuous sub-pixel motion is visibly alive from frame `0`, enforced by `check_no_static_shots()` in `explainer_engine/qa/cinema_gates.py`.

## Root Cause 3 — Catastrophic Mid-Frame Splitting / Tearing in 2.5D
- **Files & Lines:** `explainer_engine/production/layers25d.py:8-12,402-430` (`_kmeans_1d` and `thresholds()` slice the image into hard discrete RGBA depth planes with separate per-plane affine warps, splitting the frame in half when a threshold lands mid-composition).
- **Fix:** Use **Depth Anything V2 Small ONNX** (`depth_anything_v2_small_q4.onnx`, Apache-2.0, CPU) + heavy Gaussian-smoothed continuous `cv2.remap` Depthflow-style parallax displacement in `explainer_engine/production/cinema_25d.py` with safe overscan zoom (`>= 1.08`), enforced by `check_no_midframe_tears()` in `explainer_engine/qa/cinema_gates.py`.

## Root Cause 4 — Artificial / Fake Procedural Fire in Final Shot
- **Files & Lines:** `explainer_engine/production/layers25d.py:549-560` (`fire_flicker` HSV mask creates synthetic orange blobs over painted torchlight).
- **Fix:** Replace synthetic fire blobs with subtle physically motivated warm highlight flicker (`±3.2%` luminance warmth breathing) and soft depth-blurred dust/ember bokeh in `explainer_engine/production/cinema_25d.py`.

## Root Cause 5 — Broken Visual Unity Across Maps, 2.5D Stills, and Bridges
- **Files & Lines:** `explainer_engine/finish/grade.py`, `explainer_engine/maps/plate.py`, `explainer_engine/overlay/bridge_compiler.py`.
- **Fix:** Apply `explainer_engine/finish/cinema_grade.py` (`apply_unified_film_grade`: filmic S-curve, highlight roll-off, split-tone color unity, 35mm organic grain, optical vignette) uniformly across maps, 2.5D scenes, stills, and bridge-composited frames.

## Root Cause 6 — Constant Unrelated Rain Noise & Zero Map-Action SFX
- **Files & Lines:** `explainer_engine/audio/post_assembly_spotting.py`, `explainer_engine/qa/perceptual_qa.py`.
- **Fix:** Build CC0-1.0 48 kHz stereo audio library (`assets/audio/library/` + SHA-256 `manifest.json`) + `explainer_engine/audio/scene_soundscape.py` enforcing per-shot `scene_environment` ambience with `0.6s` crossfades, automatic map-action SFX binding (`parchment_unfold`, `ink_arrow_sweep`, `camp_pin_stamp`, `troop_march_pulse`, `cinematic_whoosh`), and two-pass ITU-R BS.1770-4 / `pyloudnorm` `-14.0 LUFS` (`<= -1.0 dBTP`) mastering, verified by `check_audio_scene_consistency()` in `explainer_engine/qa/cinema_gates.py`.
