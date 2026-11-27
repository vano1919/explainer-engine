## 2026-11-27 — v5 cinema hardening: plate bans, dialogue floor, gentler conversation sound
- Done: `extract_axis_locked_coverage_plates` raises; new gates `check_no_cropped_seed_plates` and `check_no_cutout_compositing` in `qa/cinema_gates.py`, wired into `run_full_cinema_audit` (`enforce_v5_contracts`); `DialogueWordClippedError` in the timeline compiler and the stitcher; `plan_dialogue_j_l_cuts`, `render_dialogue_scene_track` and one room-tone bed per dramatic scene; `clean_ltx_dialogue_stem` re-tuned and speaker levelling added. Rules BP-214..BP-217 (house).
- Dependencies declared that the code already imported: `soundfile`, `rasterio`, `playwright`.
- Changed test: the v5 loop-1 coverage-plate test now expects the ban; the loop-4 compiler test gives its dialogue shot speech times.
- Limits: the manifest part of the cutout gate judges only shot entries that declare `characters`; the 2x2 contact-sheet slicer (`studio/popcorn_storyboard.py`) is unchanged and not covered by the crop ban.
- Not done: the existing v5 master was not re-rendered.
- Test: `tests/unit/test_v5_hardening_bans.py`.
- Cost: $0.00 (local only).
