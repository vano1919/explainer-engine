# Argon handoff, 2026-11-06

For the Gemini "Argon" session. Read this first, then `PRS.md`, `PLANS.md`, `MATERIAL.md` (open every image), `LTX_HELPERS.md`,
`REUSE.md`, `OPEN_QUESTIONS.md`, and the task in `ARGON_PROMPT.md`. A Georgian page for the creator is `README_ka.md`.

Branch `argon/handoff-2026-11-06` (from `icw/19-pilot-pod`, plus five merged PRs, see `PRS.md`). Nothing here is on `main`; this branch
is never merged by a session. Facts are quoted from files you can open; whatever I could not check says "not verified".

## 1. The channel and the look

A solo creator's 2D hand-drawn explainer channel ("worlds collide": history, science and money meeting other eras). The current look
is **Ink Chronicle**: one hand-inked 2D world. Its home documents (link, do not copy):
[decision log](../../DECISIONS_AND_OPEN_QUESTIONS.md) D-96 (as amended: roles, not "Blender is the final picture"), D-116 (route per
scene type: J2, J4, J5, H), D-117 (every combination of a pod's run is costed before the pod, RP-11), D-118 (placement watch);
[route plan](../../architecture/ROUTE_PLAN_2026-11-06.md); [scene assets / J5](../../SCENE_ASSETS.md); [LTX jobs](../../LTX_JOBS.md);
[cloud runbook](../../CLOUD_RUNBOOK.md); [sourced rules](../../SOURCED_RULES.md) (BP-xx); `CLAUDE.md` at the repository root.

## 2. The creator's goal, in his words (translated from Georgian, 2026-11-06 18:54 UTC)

- Cost minimisation is needed now. First wait for how the dialogue test turns out, then make the work a little harder with simpler
  moving shots; but he changed his mind and does not want to wait for the results: prepare **one branch** with every active change and
  every future plan, PRs and everything pushed with READMEs, future plans, generated frames with READMEs, and the Argon prompt.
- All existing generated photo and video material is described with titles, so that Argon (which cannot browse the repository the way
  a session can) has the full context, starts working and does what we say. Argon is clever: it may also read git and the internet and
  may refine the approaches, but the **strategy** is ours.
- **The aim is LTX minimisation: logical generation of shots, so that the video is not fitted to the photos but the photos are fitted
  to the video's script.** Reusability options, "maybe with Blender or something else": ways to use similar shots in future; cutting and
  reusing assets; generating one scene (Blender does that very well in what he has seen: assembling photos from assets). This may make
  everything several times cheaper.
- Each generated frame gets a README that says whether it is good or bad and why; his example: the man in the dialogue picture is bad
  because he was not given enough frames (reference angles). Also the helper photo or video that helps LTX.

## 3. The strategy Argon must follow

1. **LTX minimisation.** Every LTX second costs money plus retries; a still with a Python or Blender camera move costs nothing. Decide
   per shot, from the script, which shots truly need LTX motion.
2. **Shots are derived from the script, in advance and counted** (visual script `visual_script/1`, designed in
   `plans/PLANNING_CHAIN_PLAN.md`, not built). Pictures are made to fit the video, never the video to fit the pictures.
3. **Reusability**: one Blender render may serve several stills; assets are reused across shots and episodes; a reuse planner compares
   every combination and takes the cheapest (`REUSE.md`).
4. **Pictures are built from assets** (cut-outs over backdrops, Blender 2.5D, route J5) where that holds the quality; new generation is
   the last resort.
5. **Everything measured**; unmeasured items are marked (`OPEN_QUESTIONS.md`).

## 4. The pipeline in one paragraph

Qwen-Image-2.1 + the `xworld_v2` LoRA (checkpoint 3000, weight 0.7) draws the look; Blender (EEVEE, free on the PC, the Mac or CI)
builds space, cameras, crowds and the free 2.5D dialogue shots (J5); LTX-2.5 animates only what must move (J2 clay layout, J4 colour/
depth/line layout, or plain image-to-video from a Qwen-restyled Blender still); FFmpeg assembles at 2560x1440, 24 fps. Runtime mix by
seconds: **60 % video / 30 % stills with Python motion / 10 % helper graphics** (D-93, BP-109, tolerance 5 points); speech
**70 % narrator / 30 % voiced dialogue** (D-99, BP-105). Dialogue shots at most 5 s; action scenes 10-15 s; one LTX clip 3-6 s
(limit 2-8 s, BP-172); 8k+1 frames (BP-139).

## 5. Money facts (all from the files; none re-measured here)

- RunPod balance at the last handoff: **US$7.99** (P1 handoff, 16:3x UTC; the creator's memory note says the same). The asset pod
  cost about $1.08, the step-3 pod about the difference 9.09 to 7.99 (its ledger was not opened).
- Target **US$10-15 per 12-minute episode**. The 11-06 recount: about **$13-15** for 12 minutes, built from about 430 s of LTX at about
  $0.016 per second (about $10-11 with retries), Qwen about $3, pod fixed part about $0.5 (`plans/COST_REDUCTION_NOTE.md`).
- Measured speeds: **none** for LTX; `config/job_speeds.json` rows are empty. Qwen 33.5-38.5 s per edit on an H100 NVL after a 61 s
  load (asset/step-3 pods). Blender: see `LTX_HELPERS.md`.
- Caps live only in `config/spend_caps.json`, enforced by `cloud/runpod.py` and the RP rules; you cannot and must not spend.

## 6. Rules you must not break

- **Never decide a system matter on an assumption** (OR-22): list the options and ask the creator, with four options each.
- **Stills hold only what their clip needs** (creator's standing order 14, 2026-11-06 15:53 UTC): every still is the first frame of one
  named clip or a J5/still shot, with an `in_shot` list and a reason per item; walls, floor and backdrop are always allowed.
- **Prompts are generated from shot cards**, never hand-written (`blender/pilot_stills.py`, `qa/style_prompt.check`, at most 90 words,
  each tag once, no camera or layout words in a Qwen prompt).
- **Nothing paid** (pod, Qwen, LTX, ElevenLabs) without an OR-23 plan item by item and the creator's word (OR-23, OR-24, OR-34). Free
  work is never asked about. Pods only through `python -m explainer_engine.cloud.runpod`; nothing deleted.
- Identity comes from approved hero sheets, never redrawn from scratch (invariant 6, D-101); a generated still is never the base of the
  next generation (D-75, D-78; crop reuse is allowed).
- English for everything the viewer sees; the creator reads Georgian only in a short summary at the end of a report.
- Never push to `main`, never delete or weaken a test or a cap, no model identifiers in committed files.

## 7. Map of this tree

| path | what |
|---|---|
| `PRS.md` | every open PR and branch, what is merged here |
| `PLANS.md` + `plans/` | the future plans in order, with their source files (Georgian originals have an English summary on top) |
| `MATERIAL.md`, `MATERIAL.json`, `images/` | every generated picture and clip set: HF path, route, cost, verdict and reason, one JPEG each |
| `LTX_HELPERS.md` | what LTX needs from us and what helps it; measured and unmeasured numbers |
| `REUSE.md` | reuse tooling that exists, and the reuse plan rows R0-R5 |
| `OPEN_QUESTIONS.md` | what waits for the creator or is unmeasured |
| `handoffs/` | the handoff notes of the threads whose work is on this branch |
| `ARGON_PROMPT.md` | the prompt to paste into Argon |
| `README_ka.md` | the Georgian map for the creator |
| [`../../J5_ARGON_REVIEW.md`](../../J5_ARGON_REVIEW.md) | a second, separate review request for Argon from the J5 thread (PR #151): dialogue cutting, montage rules BP-176..181, local animation of stills, hero rigs; exact source links and its own prompt. Read it with `../../J5_DIALOGUE_COLLAGE.md` sections 7d-7j |
