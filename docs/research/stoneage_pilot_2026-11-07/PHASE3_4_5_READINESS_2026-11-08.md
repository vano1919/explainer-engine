# Phase 3 / 4 / 5 readiness — 2026-11-08

Scope: free local code and documentation changes before any paid Qwen/LTX/Modal work. This is a technical readiness record, not approval for production generation.

## A. Architecture audit

- PR #161 provides the D-121 four-state J5 card contract and renderer mapping.
- In the implementation reviewed here, `cut_plan.main assemble` calls `gate(plan)` before creating `seg/`, subtitles, or invoking FFmpeg; the Blender cut renderer also checks the gate before `bpy.ops.render.render`. Invalid plans stop before outputs; a valid plan reaches the assembly commands.
- `pilot.build()` takes `route_shots/1`, not `cut_plan/1`, so it cannot claim to have passed that gate. It now always writes `preview: true` and states this in `preview_reason`, even with every route clip present. This is the route-comparison preview, not the validated final-cut builder.
- Conversation opening duration is not gated. The LTX opener requires a clip, place/drawing provenance for the same place as the dialogue coverage, matching explicit scene metadata, and declared coverage of both conversation speakers. The route then remains free to choose later coverage.
- The J5 renderer derives a blurred copy from the same approved panorama for MCU/OTS close-ups, records source and derived hashes, and places the derived file path in the Blender render job.
- The earlier D-116 J5-only dialogue default conflicts with AS-03's LTX conversation opener. D-122 resolves this: LTX leads; Blender J5 is an optional measured extension.
- D-120 and D-121 remain in force. No rendered frame is sent to Qwen; J2's historical clay path and the production P14 worker are outside this change.

## B. Current decisions (D-122)

A conversation normally opens with an LTX establishing two-shot. About 5-9 seconds is the pilot target for evaluating that opening, not a universal duration. It should show the place, both characters, their positions and who is addressing whom. Further coverage remains editorially flexible.

If LTX gives enough usable dialogue footage, use it directly and create no character cut-outs. If the dialogue needs more coverage, compare additional LTX footage with optional Blender close-ups/reactions. J5 must match the established characters, place, light and style, and earn its place through lower total production cost or effort without unacceptable quality loss. Mouth timing must derive from the actual dialogue audio. For J5 close-ups, blur a derivative of the same approved place image and use one approved character drawing as the source for its mouth/blink/expression variants. Do not generate new angles before the benchmark.

`pilot.build()` remains preview-only until it consumes a cut plan that passes `cut_plan.gate()`. The production final-cut entrypoint must continue to gate before rendering.

## C. Existing assets and benchmark feasibility

The original checkout's `route_test_assets/` handoff was rechecked: it contains the reviewed PNG images, `verdicts.json`, and `HANDOFF.md`, but no LTX dialogue video, verified paired dialogue audio/timing, or approved four-state close-up cut-outs. No Blender executable is available on this Windows host, and the repository has no pinned Windows archive. The tracked scientist assets are unrelated to this story. A complete free/local end-to-end LTX-only versus LTX+Blender benchmark is not currently possible.

Therefore the real visual benchmark is **BLOCKED**, not successful. The benchmark protocol is in [DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08](DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08.md). No paid generation job was launched. A paid LTX dialogue sample or additional LTX coverage would require explicit approval before submission; if a later benchmark also needs generated MCU assets, that operation must be separately priced and approved.

## D. Test and smoke evidence

The latest completed PR CI run at head `0c2d1c7404f2b208aa0c5787217aac5a836d8ed3` reported:

- Quality checks: **passed** (run [42483006822](https://github.com/vano1919/explainer-engine/actions/runs/42483006822)), including the repository's non-system test job, documentation lint and palette check. Its pytest totals are available in the workflow log.
- Blender smoke: **failed** at the smoke validator (run [42483006765](https://github.com/vano1919/explainer-engine/actions/runs/42483006765)); Blender 5.2.3 LTS EEVEE rendered all nine 320x180, 12-frame shots. The failure was that the validator incorrectly required every separate single-state probe to exercise all three active visemes. The speaking shot itself reported half=2, wide=3, round=3. The artifact was downloaded from this run (whose head SHA is `0c2d1c7`) and inspected: the synthetic rest/half/wide/round mouth appearances are visible and differ. This is engineering evidence only, not character-quality proof.

The smoke validator is being strengthened to distinguish the speaking-shot cue coverage from each state probe and to compare a projected mouth-region crop, check that active mouths differ from rest and from one another, and confirm stable camera/card geometry and unchanged pixels outside the mouth region. That updated validator has not yet run in Blender CI.

Local verification on this Windows host:

- Python 3.14 ran the relevant cut-plan, pilot, J5 assembly, video assembly, ICW-01 documentation and scene-reuse documentation tests after the review fixes: **110 passed**.
- The FFmpeg 9 `-fps_mode passthrough` frame-reader change now has a focused test that encodes a 24-frame clip and reads every frame. The targeted suite passed locally.
- The full non-system/non-media suite did not complete on this host. Windows required Git's `which.exe` for POSIX-only test decorators; after that workaround, pytest exited during collection/execution at 13% without a summary. Its last-failed rerun isolated `test_a_pid_of_another_user_is_not_a_crash`, which assumes Linux `PermissionError` semantics for PID 1.
- The prior successful full CI quality run predates the current review patch. New Quality and Blender runs are required after pushing it; do not treat the successful old run as proof for those unpushed changes.
- Blender is unavailable locally. The updated mouth-region probe has not yet run in Blender CI.
- FFmpeg 9 is installed. The route-pilot integration exposed its removal of `-vsync`; `production/assemble.py` uses `-fps_mode passthrough`, now exercised by the local focused video-assembly suite.

## E. Remaining benchmark work

1. Prepare one short, two-character dialogue exchange with real approved voice audio and verified word/phoneme timing.
2. Use an existing usable LTX sample if available; otherwise obtain creator approval for the exact generation and current price before launching it. The opening target is about 5-9 seconds.
3. Render Pipeline A (LTX-only) and Pipeline B (same LTX opening plus only the close-ups/reactions needed, using existing approved character/location assets) at matched output settings.
4. Inspect representative frames and the transition, then record all quality and effort fields in the benchmark template.
5. Extend LTX or retain J5 only if the measured total cost/effort and visual review support that choice.

## F. Cost status

Measured for this continuation: no provider jobs and no production render costs. Local code edits and unit tests have no provider charge. The asset handoff notes a historical roughly US$1.08 route-test Qwen run across its whole asset batch; that is sunk context, not a dialogue benchmark cost. Current LTX prices, asset-preparation hours, Blender setup/render hours and correction time are not measured here, so no pipeline is declared cheaper.

## G. Scope guard

No Qwen, LTX, Modal or RunPod jobs were started. No PR was merged and nothing was deployed. This change does not edit `p14_ltx.py`, P14/RunPod worker code, pinned bundles, deployment/API configuration or credentials, or production workflows.
