## 2026-11-21 — Assembly line: depth, build_shot (stages 1-2)

Done: `fx25d/depth_metres.py` (photo -> Depth-Anything V2 Small on CPU -> assumed-metre `.npy`, cached by picture hash; the near/far range is an
ASSUMPTION, a spec argument, the model is relative); `fx25d/living.py` got a `camera` argument with the owner's five moves (truck, zoom_in,
zoom_out, truck_zoom_in, truck_zoom_out; orbit/static refused; the old `drift` path is unchanged); `production/build_shot.py`: photo + shot spec -> depth
-> 2.5D parallax + camera + living effects (zones from the spec, smoke needs person zones) -> the episode film's finish (tint/grain/vignette of
`map.style_preset`, the same numbers the map page uses) and caption font -> mp4 + `render_log.json`. Tests: `test_depth_metres.py`, `test_build_shot.py`.
State: CPU only, nothing paid, ~1.3 s per frame. Not decided by the owner (defaults in the spec, overridable): near/far metres 2.5/60, default
snow/mist/sky values, grain look. Model file lives in gitignored `tools/depth/`.
Next: map shot in build_shot (stage 3), `build_episode` (stage 4), test video S01-S02 (stage 5).
Recovery: revert the commit; `living.py` default behaviour is untouched.

### Stages 3-4 (same day)
Done: map shots inside `build_shot` (`"kind": "map"` -> `production/build_map_shot.py` -> the maplibre lane, `truce_cold`, five moves, 1280x720/24 like photo shots);
`maps/trace_front_1914.py` + `examples/maps/truce_front_1914/` (minimal front traced from the public-domain West Point map, georeferenced by 8 towns, RMS about
9 km: a drawing aid, NOT a claim source); `production/build_episode.py` (shot plan + read durations -> every shot as long as its lines, built by build_shot, clip cache,
hard cuts, narration laid at each shot's start + lead, long-form loudness from `qa/targets.py`; `plan_from_shot_plan` matches lines by text, no guessing).
Tests: `test_build_map_shot.py`, `test_build_episode.py` (build_shot faked). Free, nothing paid. maplibre-gl 4.7.1 files were put in `maplibre_lane/vendor/` locally (not committed).
