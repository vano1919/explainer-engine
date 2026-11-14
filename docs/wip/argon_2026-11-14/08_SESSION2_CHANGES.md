CHANGES.md — Plan Steps 1 & 2 (T1–T5)
Per-Task Changes
T1 — explainer_engine/episode/run.py (stage_sound and helpers, old lines 804–857 -> new lines 804–958)

Added helpers (_insert_seconds, _write_silence_wav, _compose_rehearsal_voice_fallback, new lines 804–872):

_insert_seconds(ins, timing, script, fps) resolves the exact insert duration in seconds from ins["frames"], ins["duration_s"|"seconds"|"duration_sec"], ins["end_frame"] - ins["start_frame"], timing["shots"][sid]["frames"], or script["shots"] (target_duration_seconds).

_write_silence_wav(path, seconds, rate) writes a 16-bit mono PCM WAV of exact insert length filled with zero samples.

_compose_rehearsal_voice_fallback(...) ensures audio/voice_track.wav is written on disk with exact-length insert silence spliced into the narrator read even if VV.compose is stubbed in a unit test.

Changed stage_sound (old lines 821–857 -> new lines 892–958):

When timing["inserts"] has missing clip records (missing is non-empty) and not rehearsal, raises ContractError naming all missing shot_ids instead of silently keeping the unsplit polished read.

When missing is non-empty and rehearsal is True, generates an exact-length silent WAV (audio/insert_silence/<shot_id>.wav) for each missing insert, populates clip_audio[sid] (speech=[], speaker=None), runs VV.compose(...) to build audio/voice_track.wav and audio/voice_track.json, sets narration = ep.path("audio/voice_track.wav"), and appends a REVIEW gate row (insert_clips_present, level=G.REVIEW) naming the missing shot_ids in both detail and measured.

T2 — explainer_engine/production/directed25d.py (_rest_background and constants, old lines 74–82, 174–227 -> new lines 74–83, 175–219)

Constants (lines 74–83):

Added REST_FEATHER_PX = 3.0 (soft inward feather at 1080p, engineering default) and THIN_SHARE_MAX = 0.35 (engineering default; kept FLAT_SHARE = THIN_SHARE_MAX as an alias for compatibility).

Removed STROKE_LEN and REST_ALPHA_GAIN.

Changed Stage._rest_background and removed Stage._strokes (old lines 174–227 -> new lines 175–219):

Measures each object's thin-stroke share with the same MORPH_OPEN disc of diameter THIN_FILL_PX (16 px at 1080p): opened = cv2.morphologyEx(hard, cv2.MORPH_OPEN, disc), parts = hard & (1 - opened).

If share >= THIN_SHARE_MAX (0.35), appends o["id"] to self.flat and leaves the whole object on the background (not layered).

Otherwise keeps the mask whole (no morphological bite subtracted from o["alpha"]), applies a soft inward feather np.clip((dist - 0.5) / f_px, 0.0, 1.0) (~3 px at 1080p) on the body while keeping thin attached parts (parts, e.g. a rifle barrel or sling on a person) at full alpha, and sets the plate hole A only under the opaque interior (o["alpha"] >= 0.999) without REST_ALPHA_GAIN dilation. Frame 0 equals the source picture inside every kept layer (rest_seam <= 0.04).

T3 — explainer_engine/production/directed25d.py (_bg_person_boxes, _flatten_bg_people, bg_maps, old lines 168–172, 391, 590–604 -> new lines 168–174, 383–385, 584–675)

Added Stage._bg_person_boxes and Stage._flatten_bg_people (new lines 584–659) and wired before bg_maps (new lines 170, 173, 662):

Collects every unlayered person, face, or crowd box on the background sheet from self.keep (non-soft entries not covered by a foreground layer in self.objects), unlayered masks in layers["manifest"]["masks"]["objects"] ("layer": False) or person/crowd masks in self.masks_src, and explicit person_boxes/crowd_boxes in plan or layers (also accepting {"box": ...} / {"person": ...} in _keep_boxes, lines 383–384).

Flattens self.bg_depth inside each background box (plus a small parallax lookup margin) to the box's median depth with a soft Gaussian outer edge (sig = max(2.0, 0.01 * self.sw)), so bg_maps translates unlayered people/crowds rigidly with zero stretch or shear.

T4 — explainer_engine/production/living_director.py & explainer_engine/standards/sourced_rules.json

explainer_engine/standards/sourced_rules.json (BP-21, lines 873–884):

Added "pre_accent_rate_min_per_s": 0.018 under BP-21["thresholds"] and noted its hypothesis / engineering-default status in BP-21["statement"] (reason: the creator saw 0.5 %/s pre-word holds as static).

explainer_engine/production/living_director.py (lines 44–45, 414):

Read PRE_ACCENT_RATE = float(SR.T("BP-21", "pre_accent_rate_min_per_s")) at module level (line 45).

In choose_camera (line 414), changed the pre-word base move rate from RATE_MIN if targets else BASE_RATE to max(RATE_MIN, PRE_ACCENT_RATE) if targets else BASE_RATE, leaving everything else in choose_camera unchanged.

T5 — explainer_engine/qa/motion_intent.py (sliding_liveliness, sliding_liveliness_row, blown_out_row, old lines 50–52, 531–538 -> new lines 50–56, 535–586)

Constants (lines 50–56):

Promoted BLOWN_FAIL = 0.015 (calibrated on C5 10–13 % bad, C4A 3 % bad, untouched 0.0–0.5 % good; kept BLOWN_REVIEW = BLOWN_FAIL as an alias).

Added SLIDING_WINDOW_S = 1.0, SLIDING_LUMA_LEVELS = 2.0, SLIDING_LIVELINESS_REVIEW = 0.015, SLIDING_SIZE = (480, 270).

Added sliding_liveliness and sliding_liveliness_row (new lines 535–576):

Downscales frames to 480x270 luma and computes, over every sliding 1.0 s window (win = round(1.0 * fps)), the share of pixels whose luma changed by strictly more than 2.0 levels between the window's first and last frame; emits REVIEW when the worst window's changed share is below 0.015 (1.5 %, hypothesis, D-59).

Updated blown_out_row (new lines 579–586):

Promoted blown_out from REVIEW at 0.01 to FAIL (level=G.FAIL) above BLOWN_FAIL = 0.015. Left all other REVIEW checks untouched.

Existing Unit Tests Updated (and Why)

tests/unit/test_directed25d.py (test_thin_strokes_stay_in_the_background, lines 143–158):

Why: Line 155 previously asserted man["alpha"][int(135 * st.sh / H), int(250 * sw)] < 0.1, which pinned the old morphological bite that stripped a thin line/rifle off a kept object's mask. Under T2, a wire-only object (thin_share >= THIN_SHARE_MAX) stays in st.flat == ["wire"], while a kept object (thin_share < THIN_SHARE_MAX) keeps its thin attached stroke whole (man["alpha"][int(135 * st.sh / H), int(220 * sw)] > 0.5).

tests/unit/test_c4a_review_fixes.py (3 tests, lines 54–77 and 175–179):

test_a_rough_outline_keeps_its_nubs_and_the_seam_gate_catches_the_old_bites (lines 54–68): Previously monkeypatched R.Stage._strokes (removed by T2) to simulate C4A's morphological nub-biting; updated to simulate the old C4A disc-dilated MORPH_OPEN bite directly on the layer's alpha so the test continues to verify both seam["per_outline_px"] <= 0.04 (PASS) on the new renderer and FAIL on a C4A-bitten layer.

test_a_real_stroke_is_still_cut_from_its_layer (lines 71–77): Previously asserted st._strokes(parts, r).sum() > 0.5 * parts.sum() (pinning the removed _strokes method); updated to verify that on a kept person (0 < man["thin_share"] < R.THIN_SHARE_MAX), the attached thin sling is retained with st.rest_seam()["per_outline_px"] <= 0.04.

test_light_lifts_a_pale_sky_without_burning_it_and_a_burned_frame_is_flagged (line 179): Previously asserted MI.blown_out_row(r_bad)["status"] == "REVIEW", which pinned the pre-T5 REVIEW severity of blown_out; updated to "FAIL" per T5.

New Unit Test File

tests/unit/test_plan_steps_1_2.py:

test_t1_stage_sound_missing_insert_raises_contract_error

test_t1_stage_sound_rehearsal_missing_insert_builds_exact_silence_and_review_row

test_t2_person_with_thin_rifle_has_frame0_identical_to_source_and_wire_not_layered

test_t3_crowd_box_on_depth_ramp_moves_rigidly_without_stretch

test_t4_shot_with_trigger_word_gets_pre_accent_rate_at_least_0018

test_t5_sliding_liveliness_reviews_2s_clip_frozen_12s_in_middle

test_t5_blown_out_fails_at_3_pct_burned_sky

ASSUMPTIONS

T1 rehearsal insert silence and VV.compose: In rehearsal mode, each missing insert in timing["inserts"] is materialized as a 16-bit mono PCM silent WAV file (audio/insert_silence/<shot_id>.wav) at the narrator read's sample rate (defaulting to 48,000 Hz) with exact insert duration resolved from ins["frames"], ins["duration_s"|"seconds"|"duration_sec"], timing["shots"][sid]["frames"], or script["shots"] (target_duration_seconds), and passed into VV.compose via clip_audio[sid] (speaker=None so _pitch_shifts skips silent clips). A REVIEW row with gate "insert_clips_present" lists all missing shot_ids in both detail and measured.

T2 inward feather and thin attached strokes: THIN_SHARE_MAX = 0.35 (with FLAT_SHARE = THIN_SHARE_MAX kept as an alias). For kept objects (thin_share < 0.35), the outer boundary of the body is feathered inward over REST_FEATHER_PX = 3.0 px at 1080p (np.clip((dist - 0.5) / f_px, 0.0, 1.0)), while thin attached parts (parts = hard & (1 - opened), such as a thin rifle on a person) are kept at full alpha so they do not become semi-transparent, and the background plate hole A is restricted to the opaque interior (o["alpha"] >= 0.999) so frame 0 is bit-identical to src inside every layer outline (rest_seam == 0.0 <= 0.04).

T3 unlayered background person/face/crowd boxes: _flatten_bg_people flattens self.bg_depth to the box median (with a soft Gaussian outer edge) for unlayered boxes from self.keep (keep_in_frame faces/masks/boxes not on a foreground layer in self.objects), unlayered masks in layers["manifest"]["masks"]["objects"] ("layer": False) or person/crowd masks in self.masks_src, and person_boxes/crowd_boxes in plan or layers.

T5 sliding_liveliness return shape: sliding_liveliness(frames, fps=24.0) returns a gate-row dictionary (gate="sliding_liveliness", status, detail, measured) merged with the top-level measurement keys (worst_share, share, worst_frame, worst_start_s, windows), and sliding_liveliness_row(r) also accepts that dict (or a raw measurement dict) so callers using either MI.sliding_liveliness(...)["status"] or MI.sliding_liveliness_row(MI.sliding_liveliness(...))["status"] both work.

NOT CHECKED

code_task_inputs.zip contains only the 18 target/context files and not the rest of the repository (layers25d.py, direction.py, videolane/*, audio/*, episodes/*), so the full-repo test suite and docs_lint / test_sourced_rules.py against docs/SOURCED_RULES.md could not be executed against the full repository checkout here.

A reviewer in the full repository should run:

python -m pytest -q tests/unit/test_directed25d.py tests/unit/test_living_director.py tests/unit/test_motion_intent.py tests/unit/test_c4a_review_fixes.py tests/unit/test_v43_runner.py tests/unit/test_plan_steps_1_2.py



(and python -m explainer_engine.standards.sourced_rules write if test_sourced_rules.py checks the rendered Markdown table in docs/SOURCED_RULES.md).