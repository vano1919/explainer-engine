## 2026-11-21 — Render fixes and local gate (modal-render branch)

- 2.5D renderer (`fx25d/living.py`): output frames are 1920x1080 (upscaled from the 1280x720 working space; no new detail). Test: `tests/unit/test_living_output_size.py`.
- Technical gate (`qa/technical_gate.py`): `measure_video` now measures black and frozen ratios (ffmpeg blackdetect, freezedetect) and one sharpness unit (contrast-normalised Laplacian, cv2). Limits in `technical_gate.json` stay provisional; the sharpness floor 0.5 belonged to the old unit and is not re-derived yet.
- Map render (`maps/render.py`): `payload.bridges` timed by narration (`bridges_from_words`), drawn with the bridge styles. Test: `tests/unit/test_bridge_caller.py`.
- Local gate on a 1-second 1920x1080 test clip: NOT PASSED (bitrate, frozen ratio and sharpness fail). Results: `llm_calls/night_2026-11-21/render_compare/RESULTS_local_1080_2026-11-21.md`. No paid run.
