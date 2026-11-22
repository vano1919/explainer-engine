**VERDICT: PASS WITH FIXES.** Nothing in the diff blocks the merge. A few defects let the gate fail open or let captions mistime silently.

## Findings

1. **technical_gate.py `_parse_freezedetect` / `_parse_blackdetect`: should-fix**
   - **Problem:** Only closed intervals are counted. A `freeze_start` with no following `freeze_duration`/`freeze_end` is ignored. Depending on the ffmpeg version, a freeze or black run that lasts to the end of the stream may never be closed in the log.
   - **Scenario:** A clip whose last 3 s are frozen or black reports a ratio of 0.0, and the gate passes. That is fail-open.
   - **Fix:** Close a dangling start at `duration`.

2. **technical_gate.py `sharpness_from_gray`: should-fix**
   - **Problem:** Dividing by `mean² + 1e-6` inflates dark frames.
   - **Scenario:** A badly blurred night shot at mean 0.05 gets its Laplacian variance multiplied by about 400. A near-black frame with encoder noise scores very high.
   - **Impact:** The JSON claims the floor "catches blank or badly blurred output". It does not for dark content. Only truly uniform frames score about 0.

3. **technical_gate.py `measure_video`: nit**
   - `duration == 0` (for example a one-frame file, where ffprobe reports `"0.000000"`) raises ZeroDivisionError, not a clear RuntimeError.

4. **render.py `fps = p.get("fps", 24)`: should-fix**
   - **Problem:** It silently defaults to 24. The test has to inject `payload["fps"]` by hand, so real payloads apparently do not carry it.
   - **Scenario:** A 25 or 30 fps spec shows captions at the wrong frames with no error. This contradicts the test module's "never silently mistimes".
   - **Fix:** Take fps from the spec or timeline, or raise when it is absent.

5. **render.py `bridges_from_words`: should-fix**
   - The render loop honours per-item `fill`/`ink`, but the builder drops them.
   - **Scenario:** An item `{"text": ..., "fill": [..]}` loses its colours with no warning.

6. **render.py loop: nit**
   - `payload["bridges"] = None` raises TypeError. Only a missing key is a no-op.

7. **tests/unit/test_bridge_caller.py `_frame(..., 48)`: should-fix**
   - **Problem:** `duration_frames=48` means valid frames are 0..47. Frame 48 relies on unspecified clamping or extrapolation.
   - **Missing coverage:** Window edges are untested: frame 23/24 (onset 1.0 s) and 71/72 (hold end 3.0 s).
   - **Fix:** Use an in-range frame and add the edge cases.

8. **living.py mask path: nit (conditional)**
   - `output_size_frame(s.m_all)` runs `cv2.resize` on the raw mask.
   - **Scenario:** If `m_all`/`m_far` are ever `bool` (or float16), `cv2.resize` raises. The old `np.clip(...)*255` path tolerated that.
   - Clip-after-resize is correctly ordered, so Lanczos ringing is clipped.

9. **tests/unit/test_technical_gate.py `test_sharpness_invariant_to_unclipped_scaling`: nit**
   - The epsilon makes the ratio `(m²+e)/(m²+4e)`, which is about 1 − 9.6e-5 for this pattern. That sits just inside `rel=1e-4`, so the test is fragile.

10. **`test_measure_video_fills_filter_keys`: nit**
    - It asserts only "not None".
    - testsrc has no black or frozen content, so it could assert `== 0.0` and `sharpness >= 0.002` to actually exercise the parsers end to end.

## Specific checks

**living.py**
- `output_size_frame` is applied to every encoded BGR frame and to both mask streams.
- All three encoders use `OUT_SIZE`, and the byte counts match 1920×1080×3 and 1920×1080×1.
- The remaining 1280×720 writers are diagnostic PNGs only: `_person_zone.png` at working size and the alpha PNGs at 640×360. Neither is an encoder.
- The new test checks only the helper and the constants, not `run()`.

**technical_gate.py**
- All ffmpeg/ffprobe calls use argument lists, with no shell.
- `cv2` and `numpy` are imported at module top. Note that importing the gate now hard-requires cv2, even for audio-only checks.
- `measure_video` uses `measure_video_sharpness` → `sharpness_from_gray`, so the unit matches `sharpness_unit`.
- Parsing is correct for well-formed closed intervals; see finding 1 for open ones.
- No photo measurer in the diff uses `sharpness_from_gray`. The photo `sharpness_unit` is declared but not demonstrated.

**technical_gate.json**
- Video `min_sharpness: 0.002` is marked GUESS with its basis.
- Photo `min_sharpness: 0.002` has **no** basis or GUESS marker, even though it was derived from video samples. Should-fix.
- No other threshold changed.

**render.py**
- Missing `bridges` key → no-op. Confirmed, and the test covers both a missing key and an empty list.
- `visible_at(f, onset, hold_end, fps)` order: `bridge_render` is not in the diff, so the signature cannot be verified here. The test would catch a gross swap but not boundary errors.
- `bridges_from_words` raises ValueError when `ok` is false. The test's `match` depends on wording inside `bridge_sync`.

**Tests**
- Pass values 0.6 → 0.05 are well above the new floor.
- The violation value 0.49 → 0.0015 still violates. However, it now sits at 75% of the floor versus 98% before, so the boundary is probed less tightly. Suggest 0.0019.
- No assertion was removed.

## Provisional values used as if verified

- **blackdetect / freezedetect parameters:** `pix_th=0.10`, `d=0.1`, `n=0.003`, `d=0.5` are hard-coded in code. They are not in the JSON and not marked provisional. Freezes shorter than 0.5 s are never counted.
- **Photo `min_sharpness: 0.002`:** inherits a video-derived guess with no marker.
- **`fps` default of 24** in the bridge path.
- **Upscaled 1080p output:** living.py now upscales 1280×720 to 1920×1080. The gate's `min_width`/`min_height` therefore pass on interpolated frames, and "1080p" is reported without 1080p detail. The sharpness floor, set at only about 9% below the lowest sample (0.00219), was not shown to have been measured on these upscaled outputs.