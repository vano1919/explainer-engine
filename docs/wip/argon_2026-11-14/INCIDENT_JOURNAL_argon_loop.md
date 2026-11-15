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

## 2026-11-15 11:55 Tbilisi - full incident audit (all journals) and missing guards
- docs/wip/argon_2026-11-14/INCIDENT_AUDIT_2026-11-15.md: 76 incidents from the three journals checked against d689cd5:
  34 fixed+guard, 2 fixed without guard (+3 partial), 14 process, 24 open, 3 not checkable.
- New finding #29: directed25d.VERSION never changed ("directed25d/0.1-p1"), so the clip cache could reuse clips rendered by older,
  defective code. Fix: VERSION carries a hash of directed25d.py + living_fx.py. Guard: tests/unit/test_renderer_version_guard.py
  (fails on the old constant).
- Missing guards added (tests/unit/test_audit_guards_2026_11_15.py): #51 small face in mist passes face_intact; #42 modern take
  ranks below a period take; #60 map events use the timed script; #61 sector markers sized by view; #65 dual front line colours;
  #23 documented route names exist in the router.
- The 24 open items go to Argon Task 1 (logic fixes).

## 2026-11-15 15:00 Tbilisi - Argon Task 1 (logic fixes) applied and verified by Claude
- Argon returned 34 files (30 defects: the 24 open audit rows + ChatGPT A2.1-A2.5 + its own B1-B8). Claude's checks: comments
  preserved; 36 tests pass, none skipped; 30 guards fail on 4d209a8. About 10 guards first failed only with AttributeError; round 1
  made them assert behaviour through public entry points.
- Correction round 1 (sent in the same chat; Argon fixed all six):
  | # | defect Claude found | root cause | general fix | guard |
  |---|---|---|---|---|
  | C1 | the auto director invented mist, dust and an animated sky on every shot (S02_SH009, a dugout with a brazier: sky_open True, brazier unused) | living_director.build_shot_direction_from_script seeded fixed living elements, sky_open=True, "open field" | seen built only from evidence (layers manifest, the shot's script fields, narration only for kinds in the picture); thin evidence -> needs_eye / REVIEW | test_c1_auto_director_uses_only_evidence_interior_brazier_vs_exterior_sky_mask |
  | C2 | run.stage_direction was dead code | never called | stage_clips calls it (one path) | test_run_generates_and_validates_direction_and_fails_on_director_not_used |
  | C3 | paid preflight checked 40 fixed prop words; an entering prop failed | fixed tuple | general noun heads + entering/held props allowed | test_preflight_refuses_prompt_object_absent_from_start_picture |
  | C5 | scripts/apply_task1_data_fixes.py rewrote JSON with indent=2 (30 000 lines) | one-shot script | removed; data kept in the repo's format | - |
- Defects Claude fixed after round 1 (Argon had claimed every test passed: false):
  | defect | root cause (code) | fix | guard (fails on Argon's version) |
  |---|---|---|---|
  | layers25d and map records kept EMPTY gate_rows; the director's renderer rows were dropped too (Audit #33 looked fixed) | run.py read res["gates"]["rows"]; qa.gates.verdict writes "gates" (older bug at the director path too); Argon's own map test failed with KeyError | run._verdict_rows reads the key verdict writes, used at all four places | tests/unit/test_task1_review_guards.py::test_layers25d_fallback_record_keeps_its_real_gate_rows |
  | modern-era sounds filtered as "modern" in a modern film | sound_plan.resolve compared the era to "modern" exactly; "modern_20th_century" got the 1914 filter | every modern_* era keeps its own world | test_v43_sound_plan::test_a_take_from_a_later_world_never_plays_in_the_era (existing, was failing) |
  | every trench shot "saw" a gunshot | SEEN["gunshot"] contained soldier/soldiers/trench | only weapons/shots count | test_task1_review_guards::test_soldiers_or_a_trench_in_frame_do_not_make_a_gunshot_seen |
  | docs_lint crashed when docs/PRODUCTION_RULES.md is absent | unconditional read | read only if present | test_docs (existing, was failing) |
  | old test pinned 2 camera segments | R-19 says 3 (layers25d now matches) | test updated to 4 -> "at most 3" | test_av_events |
- Eye check (auto director, real layers, no hand-written direction): S08_SH002, S05_SH020, S02_SH008 rendered on CPU (11-15 min each),
  HF explainer-engine/argon_loop_2026-11-15/task1_auto_director/. Good: frame 0 = picture, no jumps, no invented sky, flames/embers/
  candles/sun alive, heads kept. Weak (goes to Task 2, director quality): every push targets the frame centre (0.5, 0.45) instead of
  the subject the words name; S02_SH008's push 2.5 cuts the brazier and feet at the bottom; glitter points on crosses and wire;
  S08_SH002 fails LP-08 (floor of 3 effects, an uncalibrated hypothesis that should be REVIEW by D-59).
