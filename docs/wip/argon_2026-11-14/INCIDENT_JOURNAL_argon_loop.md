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
