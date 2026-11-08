# Phase 3 / 4 / 5 readiness — 2026-11-08

Scope: free local code and documentation changes before any paid Qwen/LTX/Modal work. This is a technical readiness record, not approval for production generation.

## A. Architecture audit

- PR #161 provides the D-121 four-state J5 card contract and renderer mapping.
- PR #162 fixes the 0.5-second cue false-green at the planner level and records per-state active frames. Its latest Quality CI failed in `test_icw01_rule_rewrite`; the Blender smoke passed. The failure is a documentation banner mismatch, not an observed renderer regression.
- `cut_plan.gate()` is called by the final `cut_plan assemble` entrypoint. The route-comparison `pilot.build()` accepts a different schema and currently marks a complete clip set non-preview, despite bypassing that gate.
- The J5 renderer previously used a sharp panorama for close-ups. This continuation derives a blurred copy from the same approved panorama for MCU/OTS close-up setups and retains file-hash provenance.
- The earlier D-116 J5-only dialogue default conflicts with AS-03's LTX conversation opener. D-122 resolves this: LTX leads; Blender J5 is an optional measured extension.
- D-120 and D-121 remain in force. No rendered frame is sent to Qwen; J2's historical clay path and the production P14 worker are outside this change.

## B. Current decisions (D-122)

A conversation normally opens with an LTX establishing two-shot. About 5-9 seconds is the pilot target for evaluating that opening, not a universal duration. It should show the place, both characters, their positions and who is addressing whom. Further coverage remains editorially flexible.

If LTX gives enough usable dialogue footage, use it directly and create no character cut-outs. If the dialogue needs more coverage, compare additional LTX footage with optional Blender close-ups/reactions. J5 must match the established characters, place, light and style, and earn its place through lower total production cost or effort without unacceptable quality loss. Mouth timing must derive from the actual dialogue audio. For J5 close-ups, blur a derivative of the same approved place image and use one approved character drawing as the source for its mouth/blink/expression variants. Do not generate new angles before the benchmark.

`pilot.build()` remains preview-only until it consumes a cut plan that passes `cut_plan.gate()`. The production final-cut entrypoint must continue to gate before rendering.

## C. Existing assets and benchmark feasibility

The local `route_test_assets/` handoff contains creator-reviewed Qwen images, including approved character references, scene images and environment panoramas. It contains no LTX dialogue clip, no paired dialogue audio with verified timings, and no four-state close-up cut-outs. The repository's tracked scientist assets are unrelated to that story. Blender is not installed on this Windows host. No free/local resource set is currently sufficient for a fair end-to-end LTX-only versus LTX+Blender dialogue comparison.

Therefore the real visual benchmark is **BLOCKED**, not successful. The benchmark protocol is in [DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08](DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08.md). No paid generation job was launched. A paid LTX dialogue sample or additional LTX coverage would require explicit approval before submission; if a later benchmark also needs generated MCU assets, that operation must be separately priced and approved.

## D. Test and smoke evidence

The previous CI run for PR #162 (head `c8354f97144c463abaf7ffa7b234385bf6b6e83e`) reported:

- Quality checks: **failed**, 1 failed, 3,208 passed, 3 skipped, 3 deselected, 1 xfailed. Failure: `tests/unit/test_icw01_rule_rewrite.py::test_old_route_words_appear_only_under_a_dated_legacy_banner_or_marked_legacy`; route-scoped document banners did not meet the test's exact date check.
- Blender smoke: **passed** on Blender 5.2.3 LTS, EEVEE, CPU runner, 320x180, 12 frames per shot, 24 fps, 4 samples. Its figures and grid are synthetic; this is not a quality benchmark.

This continuation adds source-level checks for a derived same-source background blur, removes the hardcoded 4-8 second conversation-opener gate, makes the route pilot preview-only regardless of clip completeness, tests cut-plan gate refusal on an invalid final cut, and adds actual rendered-image hashes for separate rest/half/wide/round Blender smoke probes. Those probes share identical camera and body-motion seeds so the decoded image differences come from the mouth images. They still need to run in Blender CI before their render evidence can be accepted.

Local verification on this Windows host:

- Python 3.14.7 with Pillow 13.0.0 ran the relevant cut-plan, pilot, J5 assembly, video assembly, ICW-01 documentation and scene-reuse documentation tests: **101 passed**.
- `python -m explainer_engine.docs_lint`: **0 findings**. `python -m explainer_engine.design.palette`: **passed**.
- The full non-system/non-media suite did not complete on this host. Windows required Git's `which.exe` for POSIX-only test decorators; after that workaround, pytest exited during collection/execution at 13% without a summary. Its last-failed rerun isolated `test_a_pid_of_another_user_is_not_a_crash`, which assumes Linux `PermissionError` semantics for PID 1.
- Blender is not installed and the repository has no pinned Windows archive. The updated Blender smoke has not run locally. The previous CI Blender smoke is evidence only for the prior revision.
- FFmpeg 9.0.2 is installed. A route-pilot integration test initially exposed that FFmpeg 9 removed `-vsync`; `production/assemble.py` now uses `-fps_mode passthrough`, and its video-assembly tests passed in the 101-test run.

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
