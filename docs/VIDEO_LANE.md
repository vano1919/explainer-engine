# The video lane: shots planned for the edit, cut by measurement, checked on the master (D-137)

The 60 % `video` route of a v4.3 episode (D-131, D-132: LTX-2.5 distilled on Modal). This page is the one home of the VL rules.
Code: `explainer_engine/videolane/` (plan, storyboard, ingest, voice, cuts, master_qa, scene), the worker's hand-over in
the D-131 video worker `training/pods/ltx/modal_ltx_jobs.py` (`handover_frame`, `crop_filter`), the clock in `episode/timing.py`
(`retime_with_clips`), and the runner's stages G1, G6, G7, G8 and G10 (`episode/run.py`). Tests:
`tests/unit/test_videolane.py`, `tests/unit/test_videolane_media.py`.

The sound side belongs to the 30 %/10 % worker and W1 (D-134, D-136: `episode/sound_plan`, `episode/cue_sheet`, `audio/stems`,
`production/scene_join`). This lane only reads their helpers and hands the stems one voice track.

## Why

The 2026-11-12 battle and love scenes had good clips that did not cut together: sky, ground, helmet and shield changed across
cut 1, the cut fell on dead air, the first line started 0.75 s into its clip, and no code wrote the record the runner reads
for a D-131 video clip, so the scenes were joined by hand outside the runner. A shot that knows how it joins the shot before, where its
one line sits and how much clean picture it keeps can be generated for the cut instead of rescued after it.

## What our generator can and cannot do (D-131 video route, checked 2026-11-13 in the worker)

- The D-131 video CLI (`ltx_pipelines.distilled`) takes one picture at frame 0 (`--image path 0 1.0`), 1280x704 at 24 fps, at most
  10 s (241 frames). There is no end frame, extend, retake or frame interpolation in this build.
- So a continuation is made from a chosen frame of the clip before (VL-05): the worker picks it, crops it when the plan
  reframes, and starts the next clip from it. The chain existed already (`chain_from`, the last frame); VL-05 picks the
  sharpest, stillest tail frame instead of a blurred mid-motion last frame.
- The generator speaks its own lines (D-131, D-132). It starts a line about 0.75 s into a clip and leaves 0.85-1.0 s between two
  sentences, and its mouths are weak close up (the creator, 2026-11-12 20:37 UTC). Hence one line per clip and no speaking
  close-up.

## The rules

| ID | Rule | Level | Code |
|----|------|-------|------|
| VL-01 | Every `video` shot carries its `edit_plan` (schema `production_script`, `ShotSpec.edit_plan`) with one continuity mode (`continuation`, `coverage`, `insert`) BEFORE any paid clip. | FAIL | `plan.findings` |
| VL-02 | One line per video clip (D-131), and no speaking `close_up` / `extreme_close_up`. | FAIL | `plan.findings` |
| VL-03 | A `continuation` follows its source directly, inside the same scene, from a video clip; screen direction holds unless `axis_cross_reason` says why; the camera move at the source's end (`camera_out`) is the move at its start (`camera_in`); a dissolve inside a continuous action is REVIEW. | FAIL / REVIEW | `plan.findings` |
| VL-04 | A `coverage` or `insert` shot names its `scene_master` (drawn fresh from it and the hero sheets, CT-03, never from the clip before's last frame); a coverage cut steps the size or turns at least 30 degrees (CT-07); the axis side holds across the scene, an insert in between does not reset it (CT-06); every shared character keeps their screen side on one axis side. An insert with a character line is REVIEW. | FAIL / REVIEW | `plan.findings` |
| VL-05 | The hand-over of a continuation is a chosen frame: `continue_frame.pick` `best_tail` (default in a scene file) scores the last `window_s` (0.75 s) on sharpness minus motion and takes the best; `last` keeps `chain_from`. An optional `crop` reframes it, at most a 1.5x enlargement. The outgoing clip ends ON that frame and the continuation drops its frame 0 (the same picture). | FAIL | worker `handover_frame`, `crop_filter`; `ingest.edit_points` |
| VL-06 | A clip is generated only as long as its edit needs: onset (0.75 s, house) + its line + BP-187's tail + the tail handle; a silent shot its planned length + both handles; rounded up to 0.25 s, at least 2 s; a line that needs more than the model's 10 s FAILs (split it). | FAIL | `plan.clip_seconds` |
| VL-07 | Every D-131 video clip is ingested by `videolane.ingest`: the raw clip kept (`production/video/raw/`, sha256 pinned, never overwritten), cut by its MEASURED speech (in = first word minus BP-190's head lead, the first word never cut; out = last word plus BP-190's tail), resampled to the episode's rate (24/30 fps clips mix without drift), and recorded in `production/video/<shot>.json` (`video_clip_record/1`). A spoken clip with no speech in its sound is refused. A clip-spoken shot is timed by its cut: the read does not speak its line (`timing.read_order`) and the clock inserts it at its place (`timing.retime_with_clips`). | FAIL | `ingest`, `episode/timing`, G6 |
| VL-08 | More than three character lines in a row without a reaction or an insert is REVIEW (ED-14). | REVIEW | `plan.findings` |
| VL-09 | Every cut says why it cuts (`cut_in_reason`); a scene opens on an establishing, place or time cut; a cut "on a line" after a shot without one is REVIEW. | REVIEW | `plan.findings` |
| VL-10 | Before a paid D-131 video scene, its start pictures are laid out in cut order on one contact sheet (`production/storyboard/<scene>.jpg`) and checked on the pictures: each shot that needs its own picture has it, no composition repeats (64-bit dHash within 6 bits: FAIL), every coverage picture stays in the master's place and light (BP-166 palette and top third, brightness gap: REVIEW). The paid scene file (`ltx_scene_test/3`, `videolane/scene.py`) is written only from a fresh, non-FAIL storyboard and pins its sha256; `scene_run.job_spec` refuses a /3 scene whose pin moved, or a draft without the creator's budget and ledger (OR-23). | FAIL / REVIEW | `storyboard`, `scene`, `scene_run` |
| VL-11 | The cuts of the master are measured on its real frames by the incoming shot's mode: a continuation may change at most `CONT_DIFF_MAX` (or twice the in-shot change when the shot moves fast) and its horizontal motion (dense optical flow) must not reverse; a coverage cut that changes no more than the in-shot change is a jump cut (FAIL), one that leaves the place's palette is REVIEW; inserts and scene changes are measured only. A narrated video shot whose clock differs from its first cut is cut again from its raw clip (never stretched, never past a hand-over). | FAIL / REVIEW | `cuts`, `ingest.recut`, G7 |
| VL-12 | The master is measured as a file at G10 (`qa/video_master_qa.json`): container (rate, sound, picture and sound one length), frames against the plan, black and frozen runs inside video shots (BP-164), shot order (each video shot's middle frame against every video clip), the VL-11 cuts, the dialogue heard in its shot and laid once, the bed never under BP-189's floor inside its place (ducked, never muted, BP-52), a bed jump at a cut over BP-191 (REVIEW), no dead air. Every FAIL gets a repair line: A free and automatic, B free after a stage or plan changes, C paid (the clip is made again on the creator's word). | FAIL / REVIEW | `master_qa`, G10 |
| VL-13 | The voice track: the narrator's read split where the clock inserted a clip-timed shot, each clip's own sound laid on its shot's frames at the read's speech level (at most 12 dB of gain), the clip's own track kept 15 dB down between its lines (`scene_join.BETWEEN_LINES_DB`), its ends faded over BP-191. This one file is the `narration` the stems duck the bed and the music under, so the dialogue is heard once and the bed runs across the cuts. | FAIL | `voice`, G8 |

Thresholds without a registry source are engineering defaults, named in the code next to their number and calibrated by the
paired positive and negative cases of `test_videolane_media.py`: `CONT_DIFF_MAX` 18, `CONT_MOTION_RATIO` 2.0, `SAME_DIFF_MIN`
2.5, `SAME_MOTION_RATIO` 1.5, `FLOW_MIN` 0.25 px/frame, `ORDER_DIFF_MAX` 14 (0..255 grey at 160 px wide), `DUP_BITS` 6,
`LUMA_GAP_REVIEW` 0.18, `GAIN_MAX_DB` 12, the hand-over's motion weight 1.5, `MIN_CLIP_S` 2.0, `WORDS_PER_S` 2.6. Where they
are hypotheses the gate is REVIEW (D-59). The LX rules of `SCENE_REUSE_RULES.md` (handles, trimmed head, settle on the cut)
stay; VL-06 and VL-07 measure what LX-01..LX-03 ask by eye. LX-04's "clip audio is not used for speech" predates D-132.

## How one video scene goes now

1. The script writes each video shot's `edit_plan` (G1 checks VL-01..VL-09 with the video launch's max seconds).
2. The pictures stage makes the coverage and insert pictures; `videolane.storyboard` lays them out (VL-10). Claude and the
   creator look at the sheet.
3. `videolane.scene.build` writes the D-131 scene file (`ltx_scene_test/3`) (seconds from VL-06, continuations with `continue_frame`); the
   creator's budget and ledger go in; the usual OR-23 plan, D-133 cheapest gate and the creator's GO follow.
4. The worker generates the chain; each continuation starts from its hand-over frame (VL-05).
5. `python -m explainer_engine.videolane.ingest <episode> <clips.json>` keeps and cuts every clip (VL-07).
6. `python -m explainer_engine.episode run <episode> --to qa`: G6 times the clip shots, G7 takes the cuts (re-cut from raw
   where the read moved a narrated shot), G8 renders the stems over the voice track, G9 assembles, G10 measures the master.

## Not done here (open)

- No automatic repair loop: G10 writes the repair lines with their class and inputs; running them is a person's or the next
  stage's step.
- The face and costume identity of a hero across a cut (CT- cards, `training/video_qa.shot_identity`) is not a VL-12 gate yet.
- `qa/sound_realism` (W1's measured realism) runs on the master in the AV thread, not here.
