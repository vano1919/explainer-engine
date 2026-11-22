# Technical review: explainer-engine diff (branch claude/project-thread-3j9l41-modal-render)

## 1. Verdict

**PASS WITH FIXES.**

## 2. Findings

**F1. technical_gate.py `sharpness_from_gray`: dark frames read as very sharp.** Severity: **should-fix**.
- **What is wrong:** The `+1e-6` denominator inflates the score on dark frames.
- **Failure scenario:** A near-black "blank" frame with mean about 2/255 and ±1-level codec noise gives a Laplacian variance of about 3e-4 over about 6e-5. That scores about 5, far above 0.002.
- **Impact:** A black or near-black failed render passes the sharpness floor. The JSON `sharpness_basis` says the floor "catches blank … output". That holds only for flat mid-grey or exact zero, not for noisy dark output. Black detection must carry that case alone.

**F2. technical_gate.py `_parse_freezedetect`: a freeze that runs to end of file may be lost.** Severity: **should-fix**.
- **What is wrong:** The parser counts only `freeze_duration` lines.
- **Failure scenario:** In ffmpeg builds that do not flush at EOF, a freeze lasting to the end logs `freeze_start` with no duration or end line. A clip that goes static from second 2 to the end then reports `frozen_frame_ratio` of 0 and passes.
- **Fix:** Close an unpaired `freeze_start` at `duration`.
- **Dead code:** The `elif` branch expects start and end on the same line, which freezedetect never prints.

**F3. technical_gate.py `measure_video` duration handling.** Severity: **should-fix**.
- `duration == 0` raises `ZeroDivisionError`.
- A non-numeric duration raises `ValueError`.
- Neither is the `RuntimeError` callers expect.
- Fix: reject `duration <= 0` explicitly.

**F4. technical_gate.json `photo.min_sharpness`: unmarked guess.** Severity: **should-fix**.
- It moved 0.5 → 0.002 with no basis note.
- The GUESS note exists only in `video`, and its samples were videos.
- Separately, verify that any `measure_photo` uses `sharpness_from_gray`. Otherwise `sharpness_unit` is false for photos.

**F5. living.py: output size is satisfied by resampling, not native resolution.** Severity: **should-fix** (process, not code).
- `output_size_frame` upsamples the 1280x720 render to 1920x1080 with Lanczos.
- This satisfies `min_width`/`min_height` mechanically, but detail is unchanged.
- Upsampling lowers Laplacian variance. The 0.00219 floor sample's resolution and source pipeline are unstated, so living-photo outputs may land near or below 0.002 for reasons unrelated to blur.
- Measure at least one upscaled living output before trusting the floor.

**F6. tests/unit/test_bridge_caller.py:35: frame index out of range.** Severity: **should-fix**.
- **What is wrong:** `_frame(..., 48)` renders frame 48 with `total_frames=48` / `duration_frames=48`, so valid frames are 0..47. The result depends on clamping behaviour.
- **Fix:** Use frame 36 (1.5 s, inside the 1.0–3.0 s window).
- **Missing coverage:** No test exercises the window edges (frames 23/24 and 72/73). A swapped `onset_s`/`hold_end_s` argument order in `visible_at` would not reliably be caught.

**F7. technical_gate.py `measure_video` now hard-requires ffmpeg and cv2 decode.** Severity: **should-fix (verify)**.
- Any existing test that monkeypatches `subprocess.run` with fake ffprobe JSON for `measure_video` will now fail. It would hit `_ffmpeg_filter_seconds` and `cv2.VideoCapture` on a fake path.
- Confirm no such test exists outside the shown hunks.

**F8. render.py:427 `fps = p.get("fps", 24)`.** Severity: **nit**.
- The bridge timing fps is decoupled from the timeline/clock fps.
- A payload rendered at 25/30 fps without an `fps` key mistimes captions silently.
- Prefer the clock's fps.
- `"bridges": None` crashes the loop (also nit).

**F9. test_technical_gate.py `test_measure_video_fills_filter_keys`.** Severity: **nit**.
- It asserts only `is not None`.
- For `testsrc` it could assert `black_frame_ratio == 0` and `frozen_frame_ratio == 0`.

## 3. Specific checks

**living.py**
- `output_size_frame` is applied to every encoder write: the BGR frame plus both `matte` and `far` masks.
- All three pipes use `-s OUT_SIZE`, matching 1920x1080.
- Clipping is applied after resize, so Lanczos overshoot on masks is handled.
- The remaining 1280x720 / 640x360 writes are diagnostic PNGs (`_alpha`, `_person_zone`), not encoders. That is acceptable.
- Smoke metrics are measured in working space, which is consistent with earlier reports.
- If `m_all`/`m_far` can ever be `bool`, `cv2.resize` will throw. Confirm the dtype.

**technical_gate.py**
- All ffmpeg/ffprobe calls use argument lists. No shell.
- `cv2` and `numpy` are imported at module top.
- `measure_video_sharpness` calls the same `sharpness_from_gray`. The unit is consistent with `sharpness_unit`.
- Blackdetect parsing is correct for standard single-line output.
- Freezedetect parsing has the EOF gap described in F2.

**technical_gate.json**
- Video `min_sharpness` is marked GUESS. Photo is not (F4).
- No other numeric threshold changed in the shown hunks.

**maps/render.py**
- The bridges loop is a no-op when the key is absent or the list is empty, and a test covers both.
- `visible_at(f, onset_s, hold_end_s, fps)` cannot be confirmed: `bridge_render` is not in the diff. Verify the signature.
- `bridges_from_words` raises `ValueError` when `window["ok"]` is false.
- `bridge_render`, `bridge_sync` and `render_presets` must already exist on the branch, with no import back into `maps.render`. Not verifiable here.

**Tests**
- The pass value 0.6 → 0.05 is above the floor.
- The violation value 0.49 → 0.0015 is below 0.002 and still yields exactly one problem.
- The photo value 0.05 is fine.
- No test was weakened. The new tests are additive.

## 4. Provisional values used as if verified

- `min_sharpness: 0.002` in `photo`. It is unmarked and borrowed from video samples.
- `blackdetect=d=0.1:pix_th=0.10` and `freezedetect=n=0.003:d=0.5`. These are hard-coded in code, not in the JSON, and carry no GUESS marker. They directly determine `black_frame_ratio` and `frozen_frame_ratio`, which the gate compares against the provisional 0.02/0.05.
- The `sharpness_basis` claim "catches blank … output". This is not true for dark noisy frames (F1).
- Bridge `fps` default of 24 (F8).
- The upsca