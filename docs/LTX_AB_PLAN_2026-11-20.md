# LTX continuity A/B (CT-2): the prepared paid plan, NOT run (D-132)

W5, final plan 2026-11-19, P-6 / CT-2. **Status: prepared only. Nothing was run on Modal; $0 spent by this stream.** This is the OR-23
plan for the plan thread to bring to the creator. Facts about the pipelines and CT-1 are in [LTX_PIPELINES.md](LTX_PIPELINES.md). (D-132)

## 1. The question

Does a start+end keyframe, the guided two-stage pipeline, or a restored last-frame hand-over (CT-1 hop 1) give better identity, (D-132)
colour, sharpness and stability than today's frame-0 distilled clip, on real shots with a body move? The earlier "decay numbers"
were synthetic (feedback memory 2026-11-19); this measures real clips.

## 2. Shots (3 existing 1914 shots with a body move; picked from the 56 raw clips)

Source: `episodes/ep_truce_1914/story/production_script.json` (action states, camera) and `assets/asset_records.jsonl` (clip and
picture records). Seconds per run = the script's target rounded up to the model's 8k+1 frames at 24 fps.

| Shot | Why | Action (script) | Seconds / frames | Start picture (vault) | Hop-1 source (arm d) |
|---|---|---|---|---|---|
| S07_SH008 | a named hero (Thomas), a body move with a known end pose, wide; the one pair where an earlier test found a valid continuation (memory 2026-11-14) | climbs down, picks up the rifle, steps onto the fire step | 8.25 s -> 201 f (8.375 s) | `S07_SH008_start` (button_fix) | last frame of the raw `S07_SH007` take |
| S04_SH008 | the longest continuous walk (a tracking shot, 9 s), the hardest case for drift | Thomas walks away from camera between the wire to Friedrich | 9.0 s -> 217 f (9.042 s) | `S04_SH008_start` | last frame of the raw `S04_SH007` take |
| S07_SH006 | a body move with an arm rise and a known end state, wide, a second identity (the captain) | salutes, steps down behind the parapet, arm fires two shots | 6.0 s -> 145 f (6.042 s) | `S07_SH006_start` | last frame of the raw `S07_SH005` take |

Limit: S07_SH006 has no named hero in the script, so its identity metric compares a wide figure and may be NOT_RUN; colour,
sharpness, flicker and the blind look still apply. A swap for a close shot with a hero face is the plan thread's call.

Prerequisites at $0 (not done here): the three **end keyframes** (arms b, c) are fresh pictures from the untouched vault masters (D-132)
(CT-1), made in the Gemini chat like the start pictures, and the three hop-1 start frames (arm d) are made with `finish/frame_pick`
-> `finish/superres` -> `ab_metrics.lab_lock` from the raw takes above, with their `continuation_check` records written by
`ab_metrics.continuation_check`.

## 3. Arms (same seed, prompt, seconds, size per shot across arms)

| Arm | What | Job | Pipeline |
|---|---|---|---|
| a | today: one start picture at frame 0 | kind `clip` | distilled (its stage 2 already uses the pinned x2 upsampler, LTX_PIPELINES finding 1) D-132 |
| b | start + end keyframes, same engine | kind `keyframes`, `engine: distilled` | distilled, end picture bound as `guide` at the last frame D-132 |
| c | start + end keyframes, the official guided two-stage (dev transformer, CFG, stage 2 = pinned x2 upsampler + distilled LoRA) | kind `keyframes`, `engine: guided` | TI2VidTwoStages D-132 |
| d | hop-1 last-frame continuation restored: the previous clip's picked, x2-upscaled, LAB-locked last frame as the start | kind `clip` with that start picture | distilled |

**Deviation from the brief, decided by the source (finding 1):** the brief's arm "(c) = (b) + x2 upscaler" cannot be a switch,
because the upsampler runs in every two-stage pipeline including today's. Arm c is therefore the guided pipeline, the only official
path where the x2 stage is a refine with the dev model; the plan thread may drop c, or swap it for a distilled arm with no end
keyframe (`upscale_x2`, start picture only) to separate "guided" from "end keyframe". Settings of c (all written out, CLI (D-132)
defaults at e98f6d9): 40 steps, video CFG 3.0, STG 1.0, distilled-LoRA strength 0.25 stage 1 and 0.5 stage 2, image strength 1.0.

12 runs = 3 shots x 4 arms, one launch each. Seeds: the shot's existing seed (7112, 7100, 7104) in every arm.

## 4. Metrics (free, code in `training/pods/ltx/ab_metrics.py`, tested on synthetic clips) (D-132)

Per clip, last frame against the untouched master: identity (cosine, the repo's embedder `qa/identity.clip_embedder` or an injected
ArcFace one; NOT_RUN without it), flicker (frame-to-frame LAB dE76, mean and p95 of the pairs), sharpness ratio (Laplacian variance
vs the master), PSNR, LPIPS (injected; NOT_RUN: weights not pinned in the repo). No pass threshold is invented: the numbers are
reported next to the owner's choice. The owner's blind look: `ab_metrics.blind_labels` shuffles the four arms of each shot under
A-D, the key stays hidden until he has chosen.

## 5. Cost (estimate; H100 $5.0937/h = $0.001415/s, prices 2026-11-07; startup cap 120 s; per-run cap `launch.caps.run_usd` $0.97)

Measured past rate: the three Modal LTX ledgers hold **19 settled launches, min $0.154, mean $0.301, max $0.533** (a launch = a (D-132)
cold start plus one scene of 1-4 clips; `ltx_scene_test`, `ltx_scene_battle`, `ltx_truce_A`). The guided arm has **no measurement**: (D-132)
its range is built from the measured parts (Gemma 29.5 s, transformer build 18.2 s, decode, cold start) plus 80-120 guided passes
at half size, an estimate, marked as such.

| Item | Runs | Min | Expected | Max |
|---|---|---|---|---|
| arms a, b, d (distilled) | 9 | $1.39 | $2.71 | $4.80 |
| arm c (guided, unmeasured) | 3 | $0.93 | $1.50 | $2.67 (hard bill of one run: timeout + startup $0.89) |
| stage-in of the dev transformer + LoRA to the Volume (CPU, ~45 GB, $0.32/h) | 1 | $0.06 | $0.10 | $0.16 |
| OR-37 rung L3 smoke again (worker and launch bytes changed) | 1 | $0.16 | $0.17 | $0.50 |
| **Total** | 12 + 2 | **$2.54** | **$4.48** | **$8.13** |

**Money available: $0.62** (spent $4.58 of $5.20). The A/B does not fit; only the creator changes `config/spend_caps.json`
(`modal_ltx`). Proposal for him: a hard cap of **$2.00** for stage 1 (staging, L3 smoke, all four arms of S07_SH008: expected (D-132)
$0.10 + $0.17 + about $1.5) and a separate word for the other two shots after he has seen stage 1; if he wants all three at once, a
hard cap of **$4.50** (the expected total) with the 80 % stop rule below. Each run is held by `caps.run_usd` $0.97 and the ledger.

## 6. Hard caps, stop rule, protection

- Per run: the launch's `run_usd` $0.97, timeout from it; per A/B: the cap the creator sets above; the ledger refuses reservations
  past 80 % of the line (core/ledger STOP_FRACTION) and the plan stops starting new runs at 80 % of the A/B cap and asks.
- Stop earlier if: the L3 smoke or the first guided run fails or exceeds its timeout (then arm c is dropped, not retried blind); two
  runs in a row end FAILED or UPLOAD_UNVERIFIED; an unmeasured cost is already above the max of its row.
- Order: shot by shot (S07_SH008 first, arms a, b, d, c), so the creator can stop after stage 1.
- Arm a may reuse an existing raw take instead of a new run (review of PR #214, D-132): only when the launch pins, seed, prompt and
  seconds of that take equal the A/B job's; the record names the take path and its sha256 (the metrics read the file as any arm).
  With arm a reused for S07_SH008, stage 1 is about $1.4 expected, hard cap $2.00 (one run less than the table above).
- OR-33: every clip is saved to the Volume and HF per clip and sha256-checked before DONE (the worker's existing path, tested for
  kinds); the run record holds seed, steps, guidance, conditioning frames and strengths and the upsampler's sha256.
- OR-36: a Haiku low watchdog thread beside each run, every 5 minutes (the price is under $1 a run, the risk is the 22B guided load).
- Nothing left running: `scaledown_window_s` 2 and `min_containers` 0 (launch file, unchanged).

## 7. What the creator watches

For each shot a sheet of four clips labelled A-D (arms hidden): he picks the one that holds the face, the colour and the move best
and says if any is unusable; afterwards the metric table with the arms revealed. The result decides which arm is the CT-1 default:
fresh keyframe only, start+end, guided, or hop-1 continuation. (D-132)

## 8. Gates before any of it runs

1. **OR-34:** the full-repo Fable audit (through the Claude API, `llm/claude_api.py`) must pass first; it must confirm the run uses the
   v4.3 route and the changed worker bytes of this stream (LTX_PIPELINES section 2) and nothing from the old era. (D-132)
2. OR-23 plan approved by the plan thread (OR-24) and the creator's word, the cap decided by him, GO card bound to the plan sha.
3. OR-37 ladder again for the new worker and launch bytes (L1, L2 free CPU; L3 paid).
4. The $0 prerequisites of section 2 done and looked at.
