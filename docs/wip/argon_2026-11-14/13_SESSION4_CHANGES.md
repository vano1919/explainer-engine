# CHANGES.md — Plan Step 3 (T6 & T7)

## T6 — Wire Scene Director into `explainer_engine/episode/run.py` (`stage_clips` & `_clip_key`)

### What changed
1. **`explainer_engine/episode/run.py` (`_direction_path`, `_clip_key`)**:
   - Added `_direction_path(ep, shot)` to locate `production/direction/<shot_id>.json` (or `production/direction/<parent_shot_id>.json` for split sub-shots).
   - Extended `_clip_key` with `direction_sha: str | None = None` (auto-computing `_sha(_direction_path(ep, shot))` when `direction_sha` is omitted and `ep` is provided) and included both `"renderer"` and `"direction_sha"` in the clip cache digest. Switching between `layers25d` and `directed25d` or modifying `production/direction/<shot_id>.json` invalidates the cached clip and triggers a re-render.
2. **`explainer_engine/episode/run.py` (`_inspect_director`, `_resolve_direction_plan`, `_directed_qa_rows`, `stage_clips`)**:
   - Added `_inspect_director(ep, shot, start)` to check whether a `still_25d` shot has both:
     1. A valid JSON direction file at `production/direction/<shot_id>.json`, and
     2. A layers cache loaded via `understand.load(understand.layers_dir(picture_path))` whose `manifest["picture_sha256"]` matches the start picture's SHA-256.
   - When both exist and are valid, `stage_clips` resolves the direction document into a `directed25d` plan via `_resolve_direction_plan` (`direction.resolve`), renders the clip with `directed25d.render_clip(pic_path, layers, dplan, out, size=(w, h), fps=ep.fps, watch=qa.motion_intent.Watch())`, converts the resulting `directed25d` and `Watch` measurements into stage gate rows (`fill_reveal`, `double_edge`, `fill_at_rest`, `fill_invents`, `rest_seam`, `people_in_frame`, `face_intact`, `blown_out`, `effect_seen_3s`, `aim_on_target`, `motion_matches_intent`, `camera_never_dead`), and appends them to the stage rows.
   - When either is missing or stale, `stage_clips` keeps the existing `layers25d.render_clip` path unchanged and appends a `REVIEW` row (`gate="director_not_used"`, `level=G.REVIEW`) naming why (`"no direction"`, `"no layers"`, or `"stale layers"`).
   - Heavy ML modules (`torch`, `transformers`) are never imported at module import time, and `stage_clips` never calls `understand.understand()`.
   - Stripped non-JSON-serializable keys (`"stage"`, `"first"`, `"last"`) from the renderer report dict before writing `<shot_id>.clip.json` via `write_json_atomic`.

### Why
- Connects the Stage B scene director (`living_director` / `direction.py`) and precomputed scene layers (`understand.py`) to the episode runner (`G7` / `stage_clips`) while preserving deterministic cache invalidation, `D-59` (`REVIEW` status on hypothesis/fallback rows), and zero GPU/model imports in the runner.

## T7 — Split Long `still_25d` Shots Over 5.0 s (`BP-109`)

### What changed
1. **`explainer_engine/episode/shot_split.py` (new module)**:
   - Added pure function `split_long_still(shot, spine, max_s=5.0, *, fps=None, seen=None) -> list[dict]` and helper `punctuate_spine(spine, text)`.
   - When a `still_25d` shot's duration exceeds `max_s` (`5.0 s`, `BP-109`), recursively splits the shot at the narration word boundary nearest to the segment midpoint that ends a sentence or clause (`.`, `,`, `;`, `:`, `!`, `?`, `—`, `–`, `…`) and yields parts `<= max_s` (preferring legal cuts where the resulting segment is `<= max_s`, e.g., choosing `4.6 s` `"truce."` over `5.2 s` `"failed."` on a `10.96 s` shot, then `8.8 s` `"agreed."`).
   - Assigns sequential part IDs `<id>a`, `<id>b` (and `<id>c`, etc. for 3+ way splits), sets `parent_shot_id` to `<id>`, and gives part B (and any subsequent cut-in part) `framing: {"crop": 1.35, "focus": <named target or people centre>}` while keeping the same start picture.
   - Computes exact integer frame boundaries (`frames`, `total_frames`, `start_frame`, `end_frame`) and contiguous `word_range`s (`[w_lo, w_hi]`) and re-based per-part `spine`s so IDs, frames, durations, and word ranges sum/concatenate identically to the original shot.
   - If no sentence/clause boundary exists inside the shot, returns `[copy.deepcopy(shot)]` unsplit.
2. **`explainer_engine/episode/run.py` (`stage_clips`)**:
   - Before rendering clips, expands `still_25d` shots longer than `5.0 s` in memory via `shot_split.split_long_still` without modifying `story/production_script.json` on disk.
   - Emits a `REVIEW` row `split_long_still` listing the original `shot_id`, the split part IDs, and the cut words whenever a shot is split, or a `REVIEW` row `long_still_unsplit` when a `still_25d` shot `> 5.0 s` has no internal sentence/clause boundary.

### Why
- Enforces `BP-109` (`still_shot_max_s = 5.0`, `REVIEW`) at clip-stage time using $0 cut-in re-framings (`crop: 1.35`) on clause boundaries without mutating the authored `production_script.json`.

## Unit Tests (`tests/unit/test_plan_step_3.py`)

### What changed
- Added 5 unit tests in `tests/unit/test_plan_step_3.py` using synthetic NumPy arrays only (no model weights, no direct `sys.modules` mutation):
  1. `test_t6_direction_and_valid_layers_calls_directed25d_and_records_qa_rows`
  2. `test_t6_missing_or_stale_direction_and_layers_falls_back_to_layers25d_with_review_row`
  3. `test_t6_changing_direction_file_or_renderer_changes_clip_key`
  4. `test_t7_split_long_still_10_96s_splits_at_nearest_legal_boundary_into_parts_le_5s`
  5. `test_t7_7s_shot_without_punctuation_stays_whole_with_review_row`
