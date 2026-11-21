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
