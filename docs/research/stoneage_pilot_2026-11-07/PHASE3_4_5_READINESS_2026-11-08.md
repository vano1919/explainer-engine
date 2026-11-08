# Phase 3 / 4 / 5 readiness — 2026-11-08

Scope: free Blender work and rule reconciliation before any paid Qwen/LTX/Modal step. This is a technical readiness record, not a production approval.

## 3. Free J5 Blender work

### What has actually rendered

GitHub Actions Blender smoke run 42458910449 completed successfully on the previous J5 dialogue branch:

- Blender 5.2.3 LTS, EEVEE, CPU-only GitHub runner.
- Five J5 component shots: master two-shot, OTS, speaking MCU, reaction MCU, and 30-degree pan.
- 12 PNG frames per shot, 320x180, 24 fps, 4 samples, 0.5 seconds per shot.
- The run produced a 115 MB artifact; the rendered frames were inspected.

This is a real Blender render, but only a synthetic software smoke. The characters are deliberately primitive red/blue test figures and the background is a blue/green grid. It is not a Qwen-art quality test, not a 1440p render, and not a final video.

### Defect found after inspecting the artifact

The CI run was green but the speaking shot had `mouth_frames_open: 0`. Its 12 Rhubarb frames were all `X` (rest/closed). The synthetic sentence had six short words; at 0.5 seconds, the spelling-derived cues were shorter than the 40 ms minimum and were folded into rest. The smoke therefore did not prove lip movement even though the planner unit test passed.

On branch `fix/j5-free-render-contracts` this is being corrected by:
- using deterministic test words that exercise all four states at 0.5 seconds;
- normalising the internal closed-lips state name to `rest`, matching D-121 and `cut_plan.MOUTH_STATES`;
- reporting active mouth frames per state and failing the smoke if half, wide, or round is not exercised;
- adding a unit test that requires rest, half, wide and round to appear in the smoke cue plan.

The correction is not accepted until the new branch's CI and Blender artifact both pass and the artifact shows non-zero active mouth frames for all three overlays.

### Still required for the free visual test

1. Render the corrected synthetic smoke in CI and inspect all five shot sequences.
2. Run the same renderer on the creator's RX 5700 PC at 2560x1440 / 24 fps with a short, representative scene.
3. Record PC render time, memory, frame hashes and the creator's visual verdict.
4. Only after the asset-contract questions below are resolved, use approved real Qwen cut-outs and a real place backdrop for a 5-second J5 dialogue component test. No new Qwen asset generation is included in the free Blender step.

## D-120 / D-121 rule conflicts requiring creator decisions

The following are not safe to resolve by silently changing code. Recommendations are explicit; the creator's answer becomes the decision.

### Q1 — Conversation opening: LTX or J5 Blender?

- D-116 assigns V3/V4 dialogue to J5 (Qwen assets + Blender 2.5D, no LTX).
- D-121 AS-03 says every conversation opens on an LTX two-shot of 4–8 seconds, then close-ups.
- D-120 / DL-08 defines the visual form of a two-shot as the place picture or an over-the-shoulder, not a new sharp place drawing.

**Recommendation:** keep AS-03 as the route-wide rule: LTX creates the conversation-opening two-shot; J5 handles the approved close-ups/reactions afterward. The free J5 test should validate the Blender close-up component only, not claim to be a complete D-121-compliant conversation. This preserves the later D-121 hard rule without pretending J5 is LTX-free for the entire dialogue scene.

**Question:** Do you approve this split (LTX opening + J5 close-ups), or should J5 be allowed to create the opening two-shot in Blender as an explicit exception to AS-03?

### Q2 — Dialogue source image: MCU cut-out or full-body card?

- D-120 and DL-01 specify a Qwen-drawn MCU/chest-up hero image on a flat light-grey background, then cut out.
- The current `scene_assets/1` J5 card model stores a full-height hero image with real `height_m`; Blender camera framing crops it to MCU.
- Those are different source-image contracts and should not be mixed.

**Recommendation:** use a dedicated MCU dialogue cut-out for speaking shots, and keep full-height cards for wide/establishing shots. Do not reinterpret a full-body asset's `height_m` as an MCU image height.

**Question:** Should J5 dialogue assets use the dedicated MCU cut-out required by DL-01, while full-body cards remain for non-dialogue shots?

### Q3 — Dialogue background: sharp 360 panorama or blurred place crop?

- DL-02 requires the place's own picture as a blurred background crop, with no readable landmark.
- Current J5 Blender jobs use the unblurred 360 panorama as the world texture for MCU shots.
- This means the current renderer does not yet meet DL-02 for dialogue close-ups.

**Recommendation:** derive a blurred background texture from the same approved place image for dialogue close-ups; do not generate a second Qwen view. Keep the sharp panorama for wide shots.

**Question:** Approve this derived blurred-background variant for J5 dialogue shots?

### Q4 — Hero angles and reference reuse

- The current scene-assets guide describes drawing every angle a shot needs.
- RF-03 says a hero's approved close-up may be used as Image 1 for mouth/blink/expression variants of that same drawing; a hero sheet as Image 2 for a new pose is not used until measured.
- D-120 forbids Blender/3D renders as Qwen references.

**Recommendation:** for the first free dialogue component test, use one creator-approved hero drawing per speaker and derive only mouth/blink/expression variants from that same drawing. Do not generate new camera angles from a prior render or use an unmeasured hero sheet as Image 2. Add a separate angle only after the RF-03 test and creator approval.

**Question:** Approve this conservative single-approved-drawing rule for the first dialogue test?

### Q5 — Does `production.pilot.build()` produce a preview or a final cut?

- D-121 requires `production/cut_plan.py` to gate the cut before rendering.
- `production/pilot.py::build()` currently builds `film_shots/3` and calls `assemble.build_video_v2()` without `cut_plan.gate()`.
- The two input schemas are not interchangeable: `cut_plan` requires dialogue lines, ambience, cast, `must_show` and cut metadata that `route_shots` does not necessarily contain.

**Recommendation:** classify `pilot.build()` as a route-comparison preview only until it accepts a real cut-plan artifact or a validated adapter. Do not label its output as a final/production cut. If it is intended to produce a final cut, implement the adapter and fail closed when required fields are missing.

**Question:** Is `pilot.build()` preview-only, or must it become a fully gated final-cut builder?

## 4. Formal Phase 3 benchmark

### D-120 route correction

The previous J2 implementation still contains a Blender clay-conditioned route:
- `blender/layout_passes.py` can render the historical J2 clay pass;
- `edit/ltx_jobs.py` and `core/contracts.py` still describe/require clay for the old J2 recipe;
- `docs/LTX_JOBS.md` still documents the old recipe.

D-120 amends D-116: J2 must start from a Qwen image generated from scene words, with no Blender/3D render supplied to Qwen. The intended current route is Qwen text-first frame -> LTX image-to-video. J4 retains Blender colour/depth/line conditioning for LTX restyle. J5 remains approved Qwen assets -> Blender 2.5D.

The old J2 writer/schema/contract/pod job are migration debt. They remain blocked from a paid benchmark until they agree on the text-first recipe and pass preflight.

### Benchmark design after migration

- J2: Qwen text-to-image first frame from scene words -> LTX image-to-video.
- J4: Blender colour/depth/line layout -> LTX restyle / Union-Control variants.
- J5: approved Qwen assets -> Blender 2.5D component renders; no LTX inside a J5 shot.
- Keep the existing lean matrix's question-led order and stop rules.
- Record input/output hashes, runtime, retry count, clip cost, identity, palette/line share, flicker, motion continuity and upscale impact.
- Preserve watchdog, per-job caps, output persistence and stop-after-two-consecutive-failures behavior.

### Spend gate

The route plan's US$3–6 Phase 3 estimate is not authorization. The OR-23 spend plan, Opus review, OR-34 audit and explicit creator approval remain mandatory. No paid Qwen, LTX, Modal or RunPod job was started in this work.

## 5. Preliminary verdict

| Route / capability | Evidence | Verdict |
|---|---|---|
| J5 synthetic Blender renderer | Prior smoke rendered; mouth-cue false-green defect found; fix is in progress | NOT ACCEPTED until new smoke artifact proves all four states |
| J5 real Qwen dialogue | No approved MCU cut-outs and matching blurred place crop verified for this test | NOT TESTED |
| J2 | Old clay-conditioned implementation conflicts with D-120 | BLOCKED |
| J4 | Layout and LTX job infrastructure exists; no comparable measured paid run in this step | NOT MEASURED |
| End-to-end route choice | No comparable J2/J4/J5 result set under current decisions | NO WINNER SELECTED |

No route is production-ready from this evidence. The immediate safe work is to fix and re-render the free J5 smoke, answer Q1–Q5, and then perform the creator-PC 1440p Blender test. Paid benchmarking remains closed until the J2 migration, asset approvals and spend gates are complete.
