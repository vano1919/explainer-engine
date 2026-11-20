# Overlay for `v-scenario-quality-gate`: The perceptual gate: nothing moves on unseen (layer L24, stage G5 to G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from scenario-labs/skills, page `scenario-quality-gate` (MIT, commit `a14d061fe5`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for our own observers: Claude looking in the session (free),
Gemini watching a clip in the chat (free), ffmpeg and numpy measurements, and a transcript of what a clip says. The
upstream text describes Scenario's paid scoring tool; it is this folder's `SKILL.md` and that tool is never
called. The folder has no `references/`.

## The rule we serve

Final plan P-5: a picture is looked at, a clip is watched, an audio take is transcribed and compared, and the record is
written per asset; the stage refuses an asset without one. Each defect maps to R1 fix, R2 prompt patch, R3 new keyframe or
R4 fallback, with at most two generative retries. Statuses (P-7): PASS, REVIEW, RETRY, BLOCK, NOT_RUN. REVIEW is not PASS,
and a check that did not run is NOT_RUN, never a success.

## What upstream learned that holds for us

1. **A score is not a fix.** A verdict only sorts assets; the reasons drive the next attempt. Write defects as concrete,
   located flaws ("the private's left hand has six fingers on the rifle stock"), each with its fix path.
2. **Artifact checks miss the impossible.** A clean, sharp picture can still show two left boots, a rifle with no
   trigger, a candle burning upside down, a man standing on air above the fire step. Run a structural pass of your own:
   counts (heads against `head_count`, hands, fingers, rifles, wheels), attachment (each limb on one body, each strap on
   one shoulder), support (what carries the weight), cause and effect (smoke from the muzzle, not the stock).
3. **The judge never saw your reference.** No generic score knows this is not the approved private. Compare the asset
   with its anchor item by item: face, cap, greatcoat, webbing, the prop; and the place with its master: walls, ladder,
   sky band, light direction.
4. **A composite averages its parts.** A contact sheet that looks fine can hide one broken shot. Judge each shot, repair
   only the failures, then rebuild the sheet.
5. **Re-read the flaw list, not the number.** A broken shot and its repair can score alike; only the described defect
   tells you the repair landed.
6. **Fix the exit bar and the round cap first.** Our cap is two generative tries per shot. When a round repeats the same
   flaw, rewording will not fix it: change the picture (R3) or the shot (R4).

## Our period and docudrama checks (judgement, written into the record)

- Period truth against the claim map: caps not steel helmets in December 1914, puttees, no wristwatches on privates,
  no rubber soles, no modern zips; a wrong object breaks a docudrama more than a soft frame.
- Reenactment shows actions, never claims: no invented document or newspaper presented as genuine (invariant 5).
- The series film's look holds (rule 20): live-action faces, the film's palette and light; no cartoon or 3D-animation face.
- Letter-free (GC-07): any glyph-like texture is a defect.
- For a clip: one action done to its end state, the one line heard in the shot and only once, no speaking close-up
  (VL-02), no freeze or fade to black inside the shot, no second person appearing, the face stays its picture's face.
- For a `still_25d` shot: it is alive beyond the camera (BP-185), no tears at plane edges, the face sits in one plane.

## Procedure per asset

1. Open it: the picture at full size; the clip at real speed with sound, then scrubbed; contact tiles for long clips.
2. Run what the code measures first (below) and read its rows; NOT MEASURED stays REVIEW.
3. Ask the fixed questions: the card's (`explainer_engine/scripting/continuity.py` `vision_questions`) and the visual
   judge's (`explainer_engine/qa/visual_judge.py`); answer them in the session with `python -m
   explainer_engine.qa.sheet_review request` and `apply`.
4. Write the observation record: asset sha256, observer, questions and answers, defects (F1-F19), times in the clip,
   verdict, action R1-R4. The record's home is `explainer_engine/qa/observe.py` (planned, W2); until it exists, the
   stage's own record and `explainer_engine/episode/shot_state.py` (IMAGE_OBSERVED, VIDEO_OBSERVED) hold it.
5. Act on the rung: R1 free fixes first; R2 or R3 inside the retry cap (a paid clip only inside the approved scene plan);
   R4 the fallback (`explainer_engine/videolane/failure.py` `fallback_shot`). A third idea changes the shot.
6. A changed file is a new asset: its old observation no longer counts (the state machine resets on the hash).

## Checks in code (SK-2)

| Asset | Measured by |
|---|---|
| Gemini picture | `explainer_engine/imagegen/turn_pack.py` (intake, identity hook), `explainer_engine/gemini_task/batch.py` (verdict, redo) |
| Picture upscale | `explainer_engine/finish/superres.py` `qc` (BP-198, REVIEW) |
| Scene sheet | `explainer_engine/videolane/storyboard.py` (VL-10), `explainer_engine/videolane/identity.py` |
| LTX clip | `explainer_engine/videolane/ingest.py` (speech heard), `explainer_engine/videolane/cuts.py` (VL-11), `explainer_engine/videolane/master_qa.py` (VL-12) |
| 2.5D clip | `explainer_engine/production/layers25d.py` clip report (RT-06), `explainer_engine/qa/liveliness.py`, `explainer_engine/qa/motion_intent.py` |
| Rendered shot or master | `explainer_engine/qa/look_and_listen.py`, `explainer_engine/qa/frame_review.py`, `explainer_engine/episode/acceptance.py` (G10) |
| Statuses | `explainer_engine/qa/gates.py` today; `explainer_engine/qa/status.py` (planned, W2) |

## Failure modes of the gate itself

- Reporting a REVIEW row as passed, or a NOT_RUN as fine: say exactly what was and was not checked.
- Judging a downscaled sheet and passing a broken shot: open the shot.
- Spending a third generation on the same flaw: change the shot.
- Watching without sound: a clip's line, its timing and its effects are half the check.
- Letting Gemini's own "looks good" stand alone: its answer is one observer among several; disagreement goes to the
  record and, if it matters, to the creator.

## Upstream sections: when to open which

| Need | Open in this folder's `SKILL.md` |
|---|---|
| Turning reasons and suggestions into the next attempt | "Turning the verdict into a better image" |
| The three blind spots of any automatic score | "What the verdict does not cover" |
| A worked loop with a round cap | "Worked example: iterate a hero prop to pass" |

## Not used from upstream

The Scenario quality-gate tool, its credit pricing, stored verdicts, dry runs, sensitivity levels, brand briefs and the
Enterprise fallback; inpainting through Scenario. Our briefs are the claim map, the continuity card and the series film,
and our scoring is the observation record.
