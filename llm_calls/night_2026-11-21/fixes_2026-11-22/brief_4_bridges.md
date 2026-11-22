Task: fix four bridge-path defects in explainer_engine/maps/render.py and tests/unit/test_bridge_caller.py. Do not change bridge_render.py or bridge_sync.py.

1. fps (render_frame): currently `fps = p.get("fps", 24)` silently defaults to 24. Change it: when the payload has a non-empty "bridges" list, fps must come from p["fps"]; if p has no "fps" key, raise ValueError("bridges need payload fps: the caption timing depends on it"). When there are no bridges, the function must behave exactly as before (no new error, no change in output).
2. None (render_frame): `p.get("bridges") or []` so bridges=None is a no-op (currently it raises TypeError).
3. bridges_from_words: keep the per-item "fill" and "ink" keys in the returned dict when the input item has them (copy them through unchanged, only when present). Do not add defaults.
4. Tests in tests/unit/test_bridge_caller.py:
   - a spec with bridges and no fps raises ValueError.
   - bridges=None renders identical to a spec without the key (compare the image bytes).
   - bridges_from_words keeps "fill" and "ink" when given.
   - the frame-48 test: the clip has 48 frames (valid frames 0..47). Replace the out-of-range frame 48 with an in-range frame. Add edge tests with onset 1.0 s and hold_end 3.0 s at 24 fps: frame 23 is NOT drawn, frame 24 IS drawn, frame 71 IS drawn, frame 72 is NOT drawn. Use the same 'drawn' check the file already uses (image differs from the no-bridge render of the same frame). If a frame index above the clip length is needed, set duration_frames accordingly (for example 100) so every index is in range.
Run: python -m pytest -q tests/unit/test_bridge_caller.py tests/unit/test_bridge_render.py tests/unit/test_bridge_timing.py tests/unit/test_bridge_sync.py tests/unit/test_preset_render_switch.py tests/unit/test_render_presets.py
