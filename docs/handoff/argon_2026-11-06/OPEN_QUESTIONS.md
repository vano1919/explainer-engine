# OPEN_QUESTIONS: what waits for the creator, and what is unmeasured

Questions for the creator go to the Fable thread as four options each (the creator's rule). Nothing here is decided by this branch.

## A. Waiting on the creator

1. **The p15 pilot pod** (Qwen-only mode: 24 restyled pictures, A100, cap $3.4 / 2 h, RP-10 placement watch, D-118). On the files of this
   branch (`icw/19-pilot-pod` @3e8f994, its head 0e7e030 merged in the refresh adds p15q: 48 GB cards, a 3-failure stop and new pins; still no pod result seen) it has not run; the launch worker was still retrying placement ("no instances available") when
   this branch was cut, and I did not see its later state. Until it runs, **nobody has seen a Qwen restyle of a Blender still of the
   pilot**, so the pilot's central question (does Qwen keep places and props across the room's angles?) is unanswered.
2. **P1 (the 60-second paid pilot minute)** is paused by the creator (16:54 UTC) until everything else is finished (`handoffs/
   HANDOFF_P1.md`). Its p16 package needs p15's measured LTX seconds first.
3. **Cost-reduction plan**: due 2026-11-07 10:00 Tbilisi (memory note, `plans/COST_REDUCTION_NOTE.md`); the Argon task widens it.
4. **J5 real mouth, blink and brow variants** per hero (SA-06): one paid Qwen edit pass, the creator's call; until then every face
   motion is synthetic. Also open: a full-body commander (H1's sheets end at the belt), a left-facing scout card (the one that exists has
   a blotchy background), a slower dip between shots (about 0.7 s), a listening test of the ElevenLabs voices (EL-01).
5. **The sound order**: the creator answered Q1 A (read the sample parts before the visual script), so this is decided; what remains open
   is the ElevenLabs credit estimate for it (about 1,800 credits for two parts is an estimate, not a ledger value) and his approval of
   the actual read.
6. **OR-34 audit of the chain**: the audit by Fable over the Claude API is out of credit and the creator said Fable is no longer used;
   an Opus thread audit was the stand-in (`plans/EXEC_QUEUE.md`). Which one audits the chain before the D-67 sample is open.
7. **Spend ceiling**: `config/spend_caps.json` `per_pod_usd` 6.9 against the step-3 card's $10 (PROGRESS 2026-11-06, lean pod); a card
   above the ceiling is refused until the creator moves it.

## B. Unmeasured (never guessed; marked in the docs)

- LTX seconds and dollars per clip at 1920x1088 and per 185 frames; whether an 8 s clip holds. `config/job_speeds.json` rows are empty.
- Whether J4 (colour, depth, line control) keeps the Ink Chronicle look on crowds; whether J2 holds a two-figure duel; whether chained
  clips join (step-3 E4); native LTX audio and a2v quality.
- Cut-out edge quality on the pod (the BiRefNet run failed with a dtype error; the CPU cut-outs of J5 step 1 look clean but have no number).
- Qwen at 150 words: style holds, anatomy defects are not prevented, no keyframe gate or fix-edit has been run on them.
- Upscaling Ink Chronicle LTX clips to 2560x1440 (only an old clip was checked).
- Real Qwen restyle quality of Blender stills (item A1).
- The brief lists "RTX PRO 6000 torch support" as open; I found no handoff text that states what is open there; **not verified**.

## C. Discrepancies found while building this branch

- The brief says `icw/19-pilot-pod` already holds `icw/16-lean-pod`; it did not hold its newest commits (fix 2, the p14.sh pin). They
  are merged here (PR #146). The p14/p15 bundle sha pins in the scripts refer to bundles built from the PR commits, not from this
  branch: do not launch a pod from here.
- The queue's proposed "D-118" (visual script) collides with the real D-118 (RP-10 placement watch).
- PR #151's head moved while this branch was being built (362be4c to f7add32); both are merged.
- The P1 handoff says `test_p16_pod` has 11 tests; the file has 10 `def test_` functions on this branch.
- Merging PR #140 (asset pod, 90-word cap in group D) with the newer LT-65 band 40-150 words (commit b8ef1c5, creator 12:27 UTC) made
  `tests/unit/test_route_assets.py::test_prompt_check_allows_ninety_words_only_in_d2` fail: its first assertion expected 75 words to
  fail in group D. Resolved towards the newer rule (D-77): the assertion now uses a prompt above the 150-word band; the D2 limit
  assertion is unchanged. This edits an assertion to a newer sourced rule, not to make a phase pass; Argon and the creator may veto it.

## D. Verification (what was run, on which head)

- `python -m explainer_engine.docs_lint`: 0 findings. `python -m explainer_engine.governance check`: ok.
- Full `tests/unit` on the merged tree plus this handoff (CI `quality`, run 42278480125, head adca3ae): 3163 passed, 3 skipped,
  1 xfailed, **1 failed**: `test_icw01_rule_rewrite` flagged the words LTX/Qwen on the INDEX row; fixed in the next commit by naming D-116 on
  that row (the test's own rule). The earlier local run of the merge before the handoff files: 3156 passed, 1 failed (`test_route_assets`,
  fixed, see section C). The final-head run is reported in the thread.
- Not run: any pod, any render, Blender (not installed here), the `system`/`media` tests. The p14/p15 bundle pins were not rebuilt.

## E. Refresh (2026-11-06 ~22:00 UTC)

- Merged again: PR #151 head 7007d7d (adds BP-176..181, `j5_montage`, `j5_minute*`, docs 7g-7j, D-119, `docs/J5_ARGON_REVIEW.md`) and
  `icw/19-pilot-pod` head 0e7e030. Conflicts were only in `docs/PROGRESS.md` and the decision log (D-117/D-118 rows from the base and the
  D-119 row from #151, all kept; no numbering clash). The J5 verdicts of the creator for steps 4c-4f and the minute film v1/v2 are in
  `docs/J5_ARGON_REVIEW.md` (his 21:56 UTC scope verdict: worth it for dialogue and the 30 % still lane; action shots need LTX); the
  clips live only on HF (`route_test_2026-11/j5_minute/`, `j5_dialogue/step4f/`) and have no row in `MATERIAL.md`: not added, because their
  frames were not on this branch (not verified by me).
- Second refresh (2026-11-06 ~22:30 UTC, coordinator relay): merged PR #151 head 9752721, which adds `docs/J5_ARGON_PROMPT.md`; the
  README now names it the main prompt. **Note for the creator:** that prompt tells Argon to start `argon/ltx-minimisation` from
  `claude/project-thread-4nebmi`, which does not contain this handoff tree (PRS, plans, MATERIAL images, p14/p15/p16 material); to give
  Argon both, its first line should name `argon/handoff-2026-11-06` instead. I did not edit the prompt's text; the creator or the
  coordinator decides.

