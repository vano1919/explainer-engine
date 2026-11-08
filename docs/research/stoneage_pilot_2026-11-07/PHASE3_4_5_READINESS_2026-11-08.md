# Phase 3 / 4 / 5 readiness — 2026-11-08

Scope: the creator-requested continuation after the D-120/D-121 reconciliation. This is a readiness audit, not a claim that paid tests or a visual review have run.

## 3. Free dialogue test

### Existing evidence

- The J5 2.5D assembly has a synthetic smoke builder in `explainer_engine/blender/assemble_25d.py`.
- The smoke plans a two-character conversation, a speaking close-up, a reverse reaction, and a 30-degree pan. Unit coverage checks camera framing, the speaker's mouth track, breathing, blink, and the horizon.
- The prior documented Blender smoke ran on CPU at 480x270 / 4 samples and measured about 1.8–2.0 seconds per frame in that environment. This is not the creator's PC speed and is not a quality verdict on real Qwen artwork.
- The real J5 dialogue render at 1440p was explicitly still waiting for Qwen hero sheets and a place backdrop in `docs/SCENE_ASSETS.md`.

### D-121 correction in this branch

The previous J5 scene-assets implementation only supported three mouth states (closed / half / open), while D-121 requires four (rest/closed / half / wide / round). This branch updates:
- `scene_assets/1` schema to accept `mouth_wide` and `mouth_round` (legacy `mouth_open` remains deprecated for reading old manifests);
- the J5 planner and Blender material to blend all four states;
- synthetic smoke assets and unit tests to exercise the four-state mapping and the two-frame cross-blend;
- `docs/SCENE_ASSETS.md` to make D-121 authoritative.

### Still required to complete the free visual test

1. Use approved real Qwen assets: one 360° place backdrop and two approved hero cut-outs/sheets with all four mouth states. The synthetic figures are not substitutes.
2. Render the 5-second dialogue and reverse-angle reaction at the creator's PC, 2560x1440 / 24 fps, using the current `assemble_25d` path.
3. Inspect the actual video for face identity, mouth readability, chest-up framing, card edges/halos, backdrop stability, camera reverse, breathing/blinks, and whether it reads as a puppet.
4. Record the output hashes, machine, render time, and creator's visual verdict.

Status: **software smoke exists; real-asset dialogue review is not complete**. No asset pod or GPU was started in this step.

## 4. Formal Phase 3 benchmark

### Critical D-120 conflict

The 2026-11-06 route plan and current J2 code still describe a Blender clay layout as Qwen/LTX conditioning:
- `explainer_engine/blender/layout_passes.py` maps J2 to the clay pass;
- `explainer_engine/edit/ltx_jobs.py` includes the J2 duel in `LAYOUT_OF` and emits `clay` conditioning;
- `explainer_engine/core/contracts.py` requires J2/`ltx25` to carry `clay`;
- `docs/LTX_JOBS.md` and `docs/architecture/ROUTE_PLAN_2026-11-06.md` still describe the old clay-based J2 recipe.

D-120 supersedes that approach: no Blender/3D render is a Qwen input, and J2's first frame must be a Qwen picture from scene words; Blender remains in J4/J5. The J2 writer, contract, schema, and documentation must be migrated to a text-first Qwen frame -> LTX image-to-video job before a formal benchmark can be trusted.

The P14 worker already contains a `pipeline: distilled` image-to-video path (used by the lean pod's X1/X3/X6 jobs) with no IC-LoRA or video-conditioning. That is a candidate implementation to reuse, not proof that the new J2 route has been validated.

### Benchmark design after migration

- J2: Qwen first frame from scene words -> LTX-2.5 distilled image-to-video; no Blender layout input.
- J4: Blender colour/depth/line layout -> LTX restyle / Union-Control variants.
- Keep identical scene prompt, frame geometry, output resolution, and seed where the two routes permit a fair comparison.
- Preserve the existing lean matrix's question-led order and stop rules; do not expand to the full matrix without a reason.
- Record generation seconds, input/output hashes, failure/retry count, clip price, identity, palette/line share, flicker, motion continuity, and upscale impact.
- Keep the existing watchdog, per-job caps, output persistence, and stop-after-two-consecutive-failures behavior.

### Spend gate

The route plan estimates US$3–6 for Phase 3, but this is an estimate, not authorization. The existing project rules require the OR-23 spend plan, Opus review, OR-34 audit, and the creator's explicit approval before any paid run. No RunPod/Modal job was started by this work.

Status: **not ready to launch** until J2 is migrated, the J5 free dialogue review is recorded, the benchmark jobs pass all preflights, and the spend gate is approved.

## 5. Verdict — preliminary only

| Route / capability | Evidence available | Verdict |
|---|---|---|
| J5 synthetic dialogue assembly | Existing synthetic smoke and unit coverage; this branch updates four mouth states | Software path only; real visual verdict pending |
| J5 real Qwen dialogue | Approved real assets and 1440p review not evidenced in this branch | NOT TESTED |
| J2 | Existing clay-conditioned implementation conflicts with D-120 | BLOCKED; migrate to text-first Qwen I2V |
| J4 | Layout and LTX job infrastructure exists; route test still needs a paid measured run | NOT MEASURED |
| End-to-end route choice | No comparable J2/J4/J5 clip set under current decisions | NO WINNER SELECTED |

No route is declared production-ready from these results. The next safe implementation task is the J2 recipe migration, followed by the real-asset J5 dialogue review. Only then should the approved Phase 3 spend be executed and the final verdict generated from measured clips.

## Acceptance criteria for a final verdict

- J5: real 1440p dialogue video reviewed and accepted/rejected by the creator.
- J2: text-first Qwen image-to-video job passes schema, preflight, and a measured run.
- J4: layout-conditioned jobs pass schema, preflight, and a measured run.
- Every comparison row has a verified output, matching inputs, measured runtime/cost, and visual QA metrics.
- The final recommendation explicitly separates measured results, subjective creator preference, and remaining unknowns.
