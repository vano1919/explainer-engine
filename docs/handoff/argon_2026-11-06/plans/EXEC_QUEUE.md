# Execution queue: the pilot, then the chain (2026-11-06, ~16:35 UTC)

Source: the creator 16:18 UTC (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWNYKGTZzr2fF8nFFGuHYjsJ): "Let's do that. ... we have not proved
that Qwen and LTX will work well. So let's just verify this. Also add some photos which we need for LTX to create one minute or
maybe more ... make sure the plan is broad so much that Sonnet High would do it; what he can't, Opus 5.5." Plan behind it:
`PLANNING_CHAIN_PLAN.md` (same folder). Fable is out of limit; no package below needs a Fable thread.

**Rules for every package.** One package at a time, in this order, never in parallel (project rule 7a). Each runs in its own thread
on the model named; at its end the thread writes `HANDOFF_<id>.md` in this folder (what was done, result, inputs for the next) and
the coordinator opens the next one with only that file + this queue. Base branch `icw/05c-ink-round` (one branch per package,
`icw/2N-<name>`, draft PR into it, never main). Every change: a focused test + a `docs/PROGRESS.md` entry (invariant 11). Commit as
`git -c user.name=vano1919 -c user.email=122537395+vano1919@users.noreply.github.com`. Anything paid: OR-23 plan, OR-34 audit,
the creator's "კი", a Haiku watchdog thread, nothing left running (`cloud.runpod check` at start and end).

**The creator's decisions (cards tapped 2026-11-06 16:18-16:19 UTC in the Fable thread cmsg_01Hnu5zB86sjUj5GtTgaUkPWSDJ6dN9sdcVPJPP6ZJszpc;
record them in the decision log with P2):** Q1 A (card …WvthQxP9jFWVTDaNdA3jKm): the sample parts are read before the visual
script, the rest after the sample is approved. Q2 A (…PrsYNeFMY4QocMDq6HiLhk): code computes every combination and takes the
cheapest; an agent reviews only REVIEW rows. Q3 A (…SCMq68ThVpBMPf4HceFzcp): reuse only when the cropped frame holds exactly the
clip's list. Q4 A (…TU1MQZURfqJv3gwUqLKKX8): clips round up to the next valid length (≤ +0.33 s), trimmed in the edit. Q5 A
(…RCZNWpzw8bj21bKmoBmeWr): he approves one readable page per part before anything paid. Q6: the pilot first, then the D-67 sample.

**OR-34 without Fable (the creator's words "checking by you would not be great"):** the audit before the pilot pod is done by an
Opus 5.5 thread (high effort) over the pod package + the repo diff, with the OR-34 checklist (nothing old-era used, new routes
only, shas pinned, step-by-step save proven). If the creator wants the Claude-API Fable audit instead, the API needs credit
(last known: out). This is put to him on the card of P1.

---

## P1 — Pilot ~60 s: existing Blender renders → Qwen restyle → LTX i2v (PAID, the first package)

**Model:** Sonnet high (the work). **Opus 5.5 high** for two steps only: the OR-23 plan confirmation (OR-24) and the OR-34 audit.
**Question it answers:** do Qwen-Image-2.1 + xworld_v2 restyles of our Blender stills hold the look, and does LTX-2.5 distilled i2v
hold the motion, across ~10 clips that cut into one minute (identity across angles, props stay, no melting)?

**Inputs (read first):**
- `PILOT_1MIN_PLAN.md` (v2: room set, 7 cameras, battle frames 0/200, stage 2-4 settings, schedules) and `pilot_1min/*.json`.
- Branch `icw/18-pilot-room` (code `explainer_engine/blender/pilot_stills.py`; if it is not on the remote, ask the Opus rules thread
  cmsg_01Hnu5zB86sjUj5GtTgaUkPWQrHNFwG1sq4pK87SzZ9Adt to push it) and HF `route_test_2026-11/pilot/blender/`.
- Pod packages `training/pods/p14/` (`p14_qwen.py`, `p14_ltx.py`, `lean.py bundle`), `cloud/schedule.py` (RP-11),
  `production/pilot.py`, `finish/upscale` (ROUTE_TEST chain), `STEP3_POD_PLAN_LEAN_ka.md`, `P14_LEAN_AUDIT_HANDOFF.md`.
- Measured speeds: `cloud/job_speeds.json` and pod 1's sidecars (`step3_pod1/` in project files). Use measured numbers; where none
  exists, mark the stage `measured: false` with max = 3 x expected.

**The minute (proposal; each line = one LTX clip, 24 fps, 1920x1088, i2v from the Qwen still):**

| # | Scene | Still (existing unless marked NEW) | Clip | Motion line (one) |
|---|---|---|---|---|
| 1 | room | room_establishing | 6 s (145 f) | the elder walks to the table, candle flame moves; camera holds |
| 2 | room | room_two_shot | 8 s (185 f) | the host talks and gestures, the guest listens and nods |
| 3 | room | room_close_host | 6 s (145 f) | the host leans in, speaks, taps the table |
| 4 | room | room_close_guest | 6 s (145 f) | the guest answers, shakes her head |
| 5 | room | room_reverse | 6 s (145 f) | the host stands up, the guest stays seated |
| 6 | room | room_insert_table | 4 s (97 f) | a hand sets the jug down, candle flickers |
| — | room | room_insert_wall_clock | 3 s | no LTX: J5 push-in on the still (free, `assemble_25d` / parallax) |
| 7 | battle | battle frame 0 (colour) | 6 s (145 f) | the wedge charges into the shield wall, dust rises |
| 8 | battle | NEW battle wide high (Blender, free) | 6 s (145 f) | the two lines collide, banners sway |
| 9 | battle | NEW battle front-line mid (Blender, free) | 6 s (145 f) | shields push, spears thrust, men stagger |
| 10 | battle | battle frame 200 (colour) | 5 s (121 f) | the line breaks, smoke drifts; camera holds |

Total ≈ 62 s, 10 LTX clips (≈ 59 s), 11 Qwen edits (7 room + 4 battle). Room insert 6 has a hand: the still must show it (in_shot).

**Steps:**
1. **Stills (free).** Check every existing still against the creator's 15:53 rule: only what its clip needs (an `in_shot` list per
   still with the reason of each item; walls/floor always). A still with an object its clip does not use is re-rendered without it
   (Blender in this container or CI `pilot-stills.yml`). Render the two NEW battle stills (`layout_passes render --scene battle
   --only-frames ...` with a new camera, or a new camera in the battle composition), colour pass, 1920x1088. Upload to HF
   `route_test_2026-11/pilot/blender/` with sha256 sidecars. Post a contact sheet (all 11 stills) in the thread.
2. **Prompts (free).** Qwen edit prompt per still from its `in_shot` + START pose + place/era/light; no camera/layout words; ≤ 90
   words; each tag once; `qa/style_prompt.check` passes. LTX prompt = the house style sentence + the motion line above. All in one
   `pilot_jobs.json` (the jobs file the pod reads), committed.
3. **Pod package (free).** `training/pods/p15/` reusing p14 (`p14_qwen.py` job list = the 11 stills, `p14_ltx.py` = the 10 clips at
   the frames above, seed 42, one take each). Order inside the pod: Qwen restyles first (all 11), then LTX clips in table order,
   each uploaded to HF `route_test_2026-11/pilot/{qwen,first_frames,ltx}/` the moment it lands (OR-33) + `speeds.json`.
   RP-11 schedule `pod_schedule/1` → `cloud.schedule check` exits 0; offline dry run; tests (job count, frame counts 8k+1,
   upload-per-item, stop on two LTX failures).
4. **OR-23 plan (free)** item by item from the schedule's output (card, expected and worst $ and hours, caps, stop conditions,
   outputs, what he sees, what follows) → **Opus 5.5 thread confirms** → **Opus 5.5 OR-34 audit** of the package and the diff.
5. **The creator's "კი"** on a decision card (cost, card, caps; and the OR-34 choice above). Then `runpod create --schedule`
   with the Haiku watchdog thread opened by the coordinator.
6. **After the pod (free):** `production/pilot.py` cuts the 10 clips + the J5 clock insert into one 60 s video at 2560x1440
   (upscale ROUTE_TEST chain); a side-by-side page: Blender still | Qwen still | LTX clip, per shot. Upload; post in the thread.
   `cloud.runpod check` shows nothing billing.

**Cost estimate (EST until the schedule computes it):** Qwen 11 edits ≈ 61 s load + 11 x 36 s ≈ 7.6 min on an H100 NVL (measured
rate). LTX 10 clips ≈ 55 min on an H100 at the unmeasured ~6 min per 193 f (scaled by frames). Setup ~8-10 min, reserve 10 min.
- H100 NVL COMMUNITY $2.59/h: ≈ 85 min ≈ **$3.7 expected**, worst (3 x unmeasured LTX) ≈ **$8+** → too close to the ~$8 balance.
- A100 80GB COMMUNITY $1.39/h (speed 0.6): ≈ 125 min ≈ **$2.9 expected**, worst ≈ **$6.5**.
- Proposed caps: **max-usd 5, max-hours 3**, and a stop after the first 2 LTX clips if their measured time puts the total over
  the cap (the remaining clips are then dropped from the end of the table, battle last two first). Fits `per_pod_usd` 6.9.
**Done when:** the 60 s video + the side-by-side page are on HF (exact paths in the reply), `speeds.json` and
`cloud/job_speeds.json` hold the measured Qwen and LTX times, nothing bills, `HANDOFF_P1.md` written.

---

## P2 … P12 — the chain (FREE, after P1; each with its own thread)

Each package: inputs = `PLANNING_CHAIN_PLAN.md` sections named + the previous handoff; done = its tests pass, the fast suite and
`docs_lint` pass, draft PR into `icw/05c-ink-round`, `HANDOFF_<id>.md`. Model Sonnet high unless marked.

| Pkg | = plan WP | What (one line) | Inputs | Done when | Model | h EST |
|---|---|---|---|---|---|---|
| P2 | V0 | `visual_script/1` schema + `core/contracts` check + CONTRACTS entry + D-118 in the decision log | plan §2, `tests/fixtures/route_test/route_shots.json`, `schemas/shot_spec.schema.json` | the converted route-test fixture validates; one failing test per rule of §2 | Sonnet high | 3 |
| P3 | V1 | `visual/visual_script.py build` from film_shots/3 + lanes + spine (or syllable estimate, `timing: estimate`) | plan §2/§5, `visual/lanes.py`, `audio/spine.py`, `production/timing.py`, `scripting/syllables.py` | route-test cards rebuild the fixture's shots/seconds; frames tile the spine exactly | Sonnet high | 6 |
| P4 | V2 | `visual/ltx_prompts.py`: clips per shot, 8k+1 + round-up handle, chain overlap 8, stable ids `S03-02.c1`, motion line from the card | plan §3, `blender/layout_passes.py`, `edit/ltx_jobs.py`, P1's measured `clip_max` | 12 s battle → 2 x 145 f overlap 8; ids stable on rebuild; BP-172 cap | Sonnet high | 4 |
| P5 | V3 | `visual/still_needs.py`: one still per clip, `in_shot` with reasons, START pose; **bpy visibility check** (objects in the camera frustum ⊆ in_shot) | plan §2, `blender/pilot_stills.py`, `world_layouts.json`, P1's in_shot lists | pilot-room two-shot passes; an extra visible prop FAILs (bpy test in CI) | **Opus 5.5** (bpy frustum test) then Sonnet high | 6 |
| P6 | V5 | `visual/still_prompts.py`: Blender job + Qwen edit prompt per still | plan §2, `p14_qwen.py` job format, `qa/style_prompt.check`, P1's prompts | ≤ 90 words, no camera words, tags once, in_shot only; P1's prompts regenerate | Sonnet high | 4 |
| P7 | V4 | `asset_needs/1` derivation + OR-18 record per item | plan §1 row 8, `compose/library.py`, `assets_reuse.py`, `scene_assets/1` | fixture: needs = exactly the missing sheets/angles/props | Sonnet high | 4 |
| P8 | V6 | `visual/reuse_plan.py` solver R0-R5 + agent page `asset-reuse-planner` | plan §4, `compose/reuse.py`, `cloud/schedule.py`, P1 speeds | the §4 fixture returns the hand-known plan; each constraint's failing case | **Opus 5.5** | 8 |
| P9 | V7 | reuse_plan → `pod_schedule/1` + OR-23 page generator; `p15` generalised to read reuse_plan | plan §1 rows 11-15, P1's `p15` | RP-11 check 0; dry run; OR-33 save test | Sonnet high | 6 |
| P10 | V8 | `qa/clip_check.py`: identity vs sheet, flicker, jitter, clip ≥ shot | plan §1 row 16, P1's clips as real test data | synthetic flicker + short clip FAIL; P1 clips get a report | Sonnet high | 4 |
| P11 | V9 | episode/sample assembly by visual_script ids (pilot.py generalised), spine audio, mix | `production/pilot.py`, `assemble.py`, `sample.py` | slate run of the fixture = full-length preview with audio | Sonnet high | 3 |
| P12 | V10 | `visual_script.md` readable page + end-to-end free dry run in CI | all above | CI builds the fixture episode's preview | Sonnet high | 2 |

Total free work ≈ 50 h EST. After P12: the OR-34 audit of the whole chain (Opus 5.5, or Fable via API if the creator funds it), then
the D-67 sample of a real episode through the chain (its own OR-23 plan and "კი").

## For the coordinator

- Open P1 now (Sonnet high) with this file; it needs from the Opus rules thread only `icw/18-pilot-room` pushed and the HF still paths.
- P1's money: the creator's "გაუშვი" (16:05) covered the 2-clip pilot v2; this 10-clip minute is bigger, so P1 step 5 asks him again.
- Open P2 only after `HANDOFF_P1.md` exists (sequential), unless the creator says to start the free packages during the pod.
