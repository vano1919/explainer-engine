# Incident journal of the Argon loop (append-only)

## 2026-11-15 07:40 Tbilisi - one-frame camera snaps and whips (2.5D)
- Seen by eye: S05_SH020 frame 73 and 143 (C5 and PR #192 before S6); a 3-4 frame whip back at frames 148-151 (S7 render).
- Root cause (73/143, fixed in S6, commit 8c32b7a): layers25d.segment_u divided by (b - 1 - a), so abutting segments froze one
  frame and then dumped a whole accent into one frame; directed25d Stage.view blended unclipped targets and clipped after the loop
  (frame 143); _frame_people kept soft edge lights as people and locked the camera (C5 frame 73).
- Root cause (148-151 whip): directed25d pan_crop_2d returns to its start after the accent window instead of holding (S10, open).
- General guard (this commit): qa/motion_intent.frame_jumps / jumps_from_steps / frame_jumps_row (no_camera_jump, FAIL), collected
  by Watch while every 2.5D clip renders. Calibrated on real renders: FAIL on C5, PR #192-before-S6 and the S7 whip; PASS on the S6
  re-render and on 15-frame accent snaps (S02_SH008). Unit tests: tests/unit/test_camera_jump_guard.py.

## 2026-11-15 08:30 Tbilisi - S10 root causes (2.5D pan, edge crop, close maps, accents)
| defect | root cause (code) | general fix | guard | status |
|---|---|---|---|---|
| pan_crop_2d slid the wrong way (S05_SH020) | directed25d Stage.view: pan_crop_2d overwrote cx,cy with the raw object point (0.30) before the pulls chain; the earlier push segment then kept pulling left | pan_crop_2d joins the sequential pulls chain relative to the start window; every segment target is clamped by _bounds_at_zoom | test_s10_defect1 (sign) | fixed, eye-checked |
| whip back at the end of the accent (148-151) | target interpolated unclamped and clamped only at the end in _frame_people: 12 frames still, then 3 frames across the window | clamp per segment; ease-out; hold at the end until the shot ends | no_camera_jump (FAIL on S7 render, PASS on S10) + test_s10_defect1 (hold, steps < 4x median) | fixed, eye-checked |
| outer soldier cut at the frame edge | _keep_boxes looked for the host mask only at the face-centre pixel (missed torso masks); _frame_people used the group median depth | torso-aware host lookup; per-person depth in the bounds | test_s10_defect1 (people inside frame) | fixed |
| close maps a blur of blobs; macro relief noisy | plate.relief_upsample used output pixel width, so macro views were treated as close and got the micro boost; close views amplified SR_HR + world-octave noise | upsample by span only; close views fade relief to 25 % + parchment + light hatch; macro micro-gain capped (D-59 hypotheses) | test_s10_defect2 (64 px blob contrast) | fixed, eye-checked |
| accents dropped (Liege, Armentieres) | episode.json stored ASCII names; the missing-glyph check did not compare accented glyphs with their base letter | episode.json names corrected (data); draw.has_missing_glyph checks NFD base glyphs; map_label_text kept only as a fallback | test_s10_defect2 + test_m9 | fixed, eye-checked |
