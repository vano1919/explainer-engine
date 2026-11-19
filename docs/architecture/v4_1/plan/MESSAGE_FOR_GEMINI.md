# Message for Gemini (Argon chat), 2026-11-19

Thank you for the reply to the review. The creator decided today (decision card, 2026-11-19 13:46 Georgia time):

1. **P1.2 accepted.** PR #196 (`e4521cd`, your 31 files on top of `fc35615`) passed CI: 4476 passed, 0 failed. Please upload
   `git bundle create p1_2.bundle argon/p1-2-timing-contract` to Drive and send the output of
   `git rev-parse eb80e443 eb80e443^{tree} 0592114`, so the exact commits can be pushed to GitHub. PR #196's tree is
   `52e6feee432c1dfaaa23346f571c23b2ed521542`. V4.1 continues the PR #195 plan. Precedence: decision log, then
   DEC-2026-11-17-01 and the PR #195 plan, then V4.1 as amended by MA-01..MA-18; each conflict gets an ADR line.
2. **One render path: `episode/run.py`.** Sound comes only from G8 `audio/stems`. Since `0e299cd`, `tools/render_tools/mix.py`
   synthesizes every bed (band-passed noise, L547-567, L720), the map sounds (L782) and the music (sine chords, L570-598,
   L795), against D-136 and OV-56, and it plays no library file. It becomes preview only. `build_segments`' guards move into
   G9 or are called by G9, decided by a 60-second parity slice.
3. **No BBC RemArc sound in a monetised master.** They are replaced from the same pools (crowd_talking_big,
   campfire_crackles, forest_wind_birds, soft_thud, ...). PC-10 is added to `qa/publish_check.py`, reading
   `audio/stems_report.json`.
4. **Who writes.** The Step 0 and Step 1 code is written by a Claude implementation thread, which has GitHub CI and the raw
   1914 media. You do not write Step 1 code.

Corrections to your Step 1:
(a) The picture check is fail-closed: `NO_PERCEPTION_INPUT` refuses too, not only `regeneration_required`. `read_job` is not
touched now, because it changes `worker_sha` and needs a paid L3 smoke.
(b) `whisper_edit_points` is not wired as it is. The recorded Whisper words of several 1914 clips are not supported by the
measured sound (for example S07_SH006: "I'll see you next time" at 0-7.64 s, while the clip's only onset is at 7.80 s). One
trim function (detector spans + words + an energy check) is used by both ingest and the edit points.
(c) The start-frame checks record REVIEW; route changes are written only as proposals.

Your tasks now (no Step 1 code, no paid calls; deliver each as a file on Drive against base `e4521cd`):
- **Bundle:** as in point 1.
- **G2 contracts:** the six missing schemas, `v4_1_schemas.json` and the manifest corrections (MA-03, MA-07, MA-12).
- **G3 review:** when we send a Step 1 PR diff, list findings with file:line.
- **G4 pictures:** the 5 photo fixes and 5 bridge stills still open, in the chat's image tool.
- **G1 eyes and ears** runs in a separate fresh chat that has not read the review, so the observation stays blind. You do
  not need to do it here.

The full plan is `FINAL_ACTION_PLAN_STEP0_STEP1.md` in `Explainer_Engine_V4_Main`.
