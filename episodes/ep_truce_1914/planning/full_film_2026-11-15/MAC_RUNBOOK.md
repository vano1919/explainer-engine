# Mac Render Runbook (`o239-argon-impl`)

> **V4.1 update (D-139, decision 2, 2026-11-19): ONE render path.** A master is made only by `python -m explainer_engine.episode run <episode> --to qa` (G8 sound from `audio/stems`, library takes logged in `audio/stems_report.json`; G9 chunked assembly). `tools/render_tools/mix.py` synthesizes its sound (D-136, OV-56) and is **preview only**: it refuses to write into any `renders/final` folder and its report says `preview_only`. `tools/render_tools/build_segments.py` is a standalone preview helper too; its hard-coded `DIPS` are NOT ported (the script's authored `transition_out` is the single source, plan owner decision 2026-11-19; `qa/known_review_items.json` lists the difference). No BBC RemArc sound in a monetised master (PC-10). The "Standalone segment + mix path" commands below are for previews only.

**Branch / Base Commit:** `o239-argon-impl` (`817be690` + Task A P0 fixes)  
**Canonical Narration Input:** `audio/narration.wav` (both `episode/run.py` and `tools/render_tools/mix.py` resolve via `explainer_engine.episode.timing.resolve_narration_path`; missing narration is a hard `ContractError`, never silent zeros).

## Current Pipeline Behaviour (P0-1..P0-5)

1. **One Still = One Visual Clip (P0-1):** Long `still_25d` shots (> 5.0 s) are no longer split into separate `a`/`b` visual clips in G7 (`stage_clips`). They render as a single continuous visual timeline using `shot_split.plan_continuous_still_timeline` + `build_continuous_camera_waypoints`, gated by `directed25d.verify_rendered_split_camera_continuity`.
2. **All-People Framing Protection (P0-2):** `directed25d` and the `layers25d` fallback auto-register all detected/masked people, check every output frame (`every=1`, including soft boxes) against the 1 % outside-frame limit, and report missing protection data as `REVIEW` (`NOT_MEASURED`), never `PASS`.
3. **Transition & Audio Boundary Contract (P0-4):**
   - `editing/boundary_manifest.json` is built post-G7 and consumed by **both** G8 (`sound_plan.py`) and G9 (`stage_assemble`).
   - `stage_assemble` honours authored `transition_out` (`honour_authored=True`) through the shared boundary manifest, supporting 12–17 frame dissolves (`cross_dissolve_12f`..`17f`) and `warm_dip` / `warm_fire_glow_dip`.
   - Post-G7 visual boundary analysis (MAD, luma distribution, colour temperature, composition continuity) flags unmotivated authored `hard_cut`s with severe visual jumps as `REVIEW`.
4. **Authoritative Clock Proof (P0-5):**
   - `timing_id` and `render_epoch` are stamped into G7 (`shot_records.json`), G8 (`sound_plan.json`), and G9 (`master.json`), and verified by `verify_clock_alignment`.
   - **Audio-sample vs frame proof:** `sample_index = round(frame_index * sample_rate / fps)` (at **48 kHz / 24 fps**, **1 frame = 2,000 samples**). Compare decoded master frame counts, `timing.json` shot boundaries, and narration/dialogue sample onsets against `frame_to_sample(start_frame, 48000, 24)`.

## Render Commands

```sh
# Episode-first pipeline (G7-G10)
python3 -m explainer_engine.episode.run --episode episodes/ep_truce_1914 --from G7 --to G10

# PREVIEW ONLY (D-139): standalone segment + mix path (uses same timing.json & resolve_narration_path); never a master
python3 tools/render_tools/build_segments.py <SHOT_ID>
python3 tools/render_tools/mix.py
```
