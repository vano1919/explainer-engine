# PLANS: the future plans in order

Every source file is copied under `plans/` (none holds a key; a pattern scan for tokens, `hf_`, `sk-`, `rpa_`, `api_key` and
passwords found nothing). The Georgian originals keep their text; two have an English summary added on top.

## What the plans decided already (the creator's cards, 2026-11-06)

From `plans/EXEC_QUEUE.md` and `plans/PLANNING_CHAIN_PLAN.md` section 9: **Q1 A** the narration of the sample parts is read before the
visual script, the rest after the sample is approved; **Q2 A** code computes every combination and takes the cheapest, an agent reviews
only REVIEW rows; **Q3 A** reuse only when the cropped frame holds exactly the clip's list; **Q4 A** a clip rounds up to the next valid
length (at most +0.33 s), the extra trimmed in the edit; **Q5 A** he approves one readable page per part before anything is paid; **Q6**
the pilot first, then the D-67 sample. Base branch for the packages: `icw/05c-ink-round`, never `main`.

## The plans in order of use

| # | plan | source in `plans/` | status |
|---|---|---|---|
| 1 | The high-level plan: Qwen draws, Blender assembles/animates, LTX where motion is needed; routes J2/J4/J5/H, matrix by scene type, gaps G1-G13, findings F-01..F-40 | `FINAL_HIGH_LEVEL_PLAN_ka.md` (English summary on top) | decided by the creator at 11:14 Tbilisi; D-116 records it |
| 2 | The story-to-montage chain: script, lanes, narration, **visual script `visual_script/1`**, LTX clips with prompts, stills with `in_shot`, asset needs, Blender + Qwen prompts, **reuse plan**, pod schedule, assembly | `PLANNING_CHAIN_PLAN.md` | planned, **not built**; work packages V0-V10 (about 50 h estimated) |
| 3 | The execution queue: P1 the paid pilot minute, then P2-P12 = the V0-V10 packages, one thread each, sequential | `EXEC_QUEUE.md` | P1 **paused** by the creator; P2-P12 not started |
| 4 | The pilot: Blender stills from the libraries, Qwen restyle, LTX i2v, v2 and v3 | `PILOT_1MIN_PLAN_v2.md`, `PILOT_1MIN_PLAN_v3.md`, `HANDOFF_P1.md` | free part done; the p15 pod waits for a placement |
| 5 | The step-3 route-test pod (A-G, extras) | `STEP3_POD_PLAN_LEAN_ka.md` (English summary on top) | ran once as pod 1; parts failed (see MATERIAL) |
| 6 | Three Fable audits of the pods | `P14_LEAN_AUDIT_FABLE.md`, `P14_FIX2_AUDIT_FABLE.md`, `P15_PILOT_AUDIT_FABLE.md` | on record |
| 7 | J5 dialogue test | `J5_DIALOGUE_TEST_BRIEF.md`, `../handoffs/HANDOFF_STEP1/3/4.md`, `docs/J5_DIALOGUE_COLLAGE.md` | steps 1-4b done, free; real mouth/eye variants open |
| 8 | Cost reduction | `COST_REDUCTION_NOTE.md` | postponed; the Argon task is its widened form |

## New work packages, from the creator's 18:54 UTC order (the packages V0-V10 plus Argon's)

V0 `visual_script/1` schema + contract check; V1 the builder; V2 LTX clips and prompts (8k+1, handles, chains, stable ids
`S03-02.c1`); V3 still needs with `in_shot` and a Blender visibility check (objects in the camera frustum must be a subset of
`in_shot`); V4 `asset_needs/1`; V5 Blender + Qwen prompt generator; V6 the reuse planner (solver + review agent page); V7 reuse plan to
`pod_schedule/1` + OR-23 page; V8 clip QA (identity, flicker, jitter, clip at least as long as its shot); V9 assembly by visual-script
ids; V10 the readable page and a free CI dry run. Details, inputs and test ideas are in `plans/PLANNING_CHAIN_PLAN.md` section 6.

## Where the plans would still let the video be fitted to the pictures (first observations, for Argon's audit A)

- The pilot (v3) starts from **existing Blender stills** of a furnished room and a battle, then writes motion lines per still: the
  pictures came first and the clips are fitted to them (`HANDOFF_P1.md` open points: its motion lines are the rules thread's cards,
  not the queue's proposals, because the objects were not in those stills).
- `PLANNING_CHAIN_PLAN.md` section 3 builds clips from the card's action, which is the right direction, but section 4's reuse option R3
  (one wide render serving several stills) and R0/R1 reuse can turn into picture-led shots if the `in_shot` exactness constraint is
  weakened; the creator's Q3 A keeps it exact.
- The J5 collage (step 1) chose the camera and shot set from the available hero angles (four sheets), not from a script.
- Decision-number clash: the plan proposes "D-118 = the visual script is the one plan of the picture", but D-118 is now the RP-10
  placement watch; the next free number must be taken when V0 lands.
