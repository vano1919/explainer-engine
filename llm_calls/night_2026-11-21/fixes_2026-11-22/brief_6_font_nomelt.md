Task: add two tested gate pieces. Files: explainer_engine/qa/technical_gate.py, explainer_engine/qa/technical_gate.json, tests/unit/test_technical_gate.py, and a NEW test file tests/unit/test_map_font_and_no_melt.py. Do not change explainer_engine/maps/draw.py or any style file.

A. No-melt gate (pure function, numbers in, verdict out), in technical_gate.py:
- Add to technical_gate.json a block "no_melt": {"residual_motion_per_frame_max": 0.05, "residual_drift_max": 0.2, "unit": "fraction_of_frame_height", "basis": "PROVISIONAL: house proposals T9 and T10 of QUALITY_SPEC.md (plans_2026-11-21), no source; compensation of the camera move is not yet defined, so these numbers are not yet measured. The owner approves on rendered samples."}.
- Add def check_no_melt(metrics: dict) -> list[str]. metrics keys: "residual_motion_per_frame" (float, fraction of frame height, p99 over consecutive frame pairs) and "residual_drift" (float, fraction of frame height, p99 displacement first to last frame). Missing or None key -> problem "missing metric <key>" (fail closed). Value above the limit -> problem naming the key and the limit. Otherwise [].
- check_video(metrics) stays unchanged for every existing caller, EXCEPT: if metrics.get("animated") is True, also run check_no_melt on metrics.get("no_melt", {}) and append its problems (fail closed when a shot is animated but no no-melt numbers exist). If "animated" is absent or False, behaviour is exactly as before.
- Tests (in test_technical_gate.py, add only): check_no_melt passes below both limits, fails above each limit separately, fails closed on missing keys; check_video with animated True and no no_melt returns a "missing metric" problem; check_video with animated absent returns the same problems as before for a passing video dict.

B. Map font tests (new file tests/unit/test_map_font_and_no_melt.py):
- Test 1 (must pass): every JSON file in explainer_engine/maps/maplibre_lane/styles/ has a "font" value whose first family is 'Liberation Serif'. Use glob, not a hard-coded list.
- Test 2 (must pass): the Liberation Serif font file exists on this machine: look for LiberationSerif-Regular.ttf in /usr/share/fonts/truetype/liberation/ and skip with pytest.skip if absent.
- Test 3: mark with @pytest.mark.xfail(strict=True, reason="raster map renderer maps/draw.py uses assets/fonts/Inter.ttf (MAP_FONT); the owner's Liberation Serif rule is not yet applied there") the test that reads explainer_engine/maps/draw.py MAP_FONT path name and asserts it contains "LiberationSerif" or "Liberation". Read the file as text (do not import draw.py). It must FAIL today, so the xfail holds; strict=True makes a fix show as XPASS failure.

Run: python -m pytest -q tests/unit/test_technical_gate.py tests/unit/test_map_font_and_no_melt.py
