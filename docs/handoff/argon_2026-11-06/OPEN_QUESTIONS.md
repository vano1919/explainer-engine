# OPEN_QUESTIONS: what waits for the creator, and what is unmeasured

Questions for the creator go to the Fable thread as four options each (the creator's rule). Nothing here is decided by this branch.

## A. Waiting on the creator

1. **The p15 pilot pod** (Qwen-only mode: 24 restyled pictures, A100, cap $3.4 / 2 h, RP-10 placement watch, D-118). On the files of this
   branch (`icw/19-pilot-pod` @3e8f994) it has not run; the launch worker was still retrying placement ("no instances available") when
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
