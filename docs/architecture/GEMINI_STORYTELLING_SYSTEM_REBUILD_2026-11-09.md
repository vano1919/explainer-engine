# Gemini Handoff — Explainer Engine Storytelling System Rebuild
Date: 2026-11-09

## Mission

Rebuild the production workflow around the simplest reliable way to make coherent, cinematic historical What-If videos. The goal is a directed story, not a collection of impressive AI clips.

**Do not optimize for hyperrealism.** The visual target is cinematic, stylized 2.5D / Ink Chronicle. Prioritize, in this order:

1. Logical story progression and readable actions.
2. Character identity and scene continuity across shots.
3. Control over scene descriptions, composition, framing and camera.
4. Reliable prompt/reference execution and repeatability.
5. Low failure/retry rate and manageable cost.
6. Visual polish, provided it does not make the workflow unnecessarily heavy.

Do not recommend a larger model merely because it is more photorealistic. A smaller model or simpler toolchain is preferable when it delivers sufficient visual quality with better control and reliability.

## Final video format

- Target episode: approximately **12 minutes**, in English.
- Historical What-If documentary / cinematic docudrama for a general audience.
- Narrative structure: **16 segments (S01–S16), grouped into five phases (Z1–Z5)**:
  - Z1, 0:00–2:00, S01–S03: hook and historical setup.
  - Z2, 2:00–4:00, S04–S06: point of divergence and immediate consequences.
  - Z3, 4:00–7:00, S07–S10: escalation, reactions and turning point.
  - Z4, 7:00–10:00, S11–S14: wider consequences and climax.
  - Z5, 10:00–12:00, S15–S16: resolution and reflection.
- Narration should carry roughly 70–80% of spoken content; character dialogue roughly 20–30%. Use dialogue when it advances the scene, not to replace clear narration.
- Flexible visual target: approximately 60% cinematic video, 30% composed stills/illustrations/collage, 10% maps or explanatory visuals. These are targets, not hard quotas.
- Use deliberate cinematic coverage: establishing wides, two-shots, medium shots, close-ups, OTS and shot/reverse-shot when appropriate. Every shot must serve the story.
- Distinguish historical facts from the hypothetical divergence and speculative consequences.

**Conflict to resolve:** the current `docs/PROJECT_BRIEF.md` still states a 5–11 minute range with a 7-minute target. The creator's current direction is approximately 12 minutes. Update the brief and dependent specs so there is one consistent source of truth; do not leave conflicting duration rules.

## The three production modes you must compare

A. **Text → Video:** give the engine a story/scene description and let it create a sequence of shots.

B. **Scene image → Multi-shot:** provide one scene/reference image and ask the model/system to generate several connected shots from that scene.

C. **Image per shot → Video per shot:** provide a prepared image for every shot, generate individual 5–10 second clips, then assemble them.

A simple hybrid is acceptable only when it has a measured advantage. Do not build all three modes into a complex orchestration system before proving one path.

## Current system — inspect before changing

The current direction has included:

- Qwen-Image-2.1 with the existing `xworld_v2` style LoRA.
- Blender/J5 for scene layout, 2.5D assembly and optional dialogue coverage.
- LTX for video generation and conversation openers.
- Shot plans, reference/scene rules, validators, cut-plan gates and regeneration logic.

The creator has not obtained a reliable, coherent 60-second finished video despite substantial experimentation. Treat this as a workflow/design failure to investigate, not as proof that another large model is needed.

Keep the existing LoRA and working components available as a baseline until a replacement is demonstrated. Do not train another LoRA by default. Do not discard Blender, Qwen or LTX merely because a new model is available.

## Current repository decisions and limitations

The current branch already contains the remote work from the stacked PR chain:

- PR #160: D-120/D-121 reconciliation and fail-closed handling of superseded Qwen/Modal routes.
- PR #161: four-state J5 mouth contract and renderer mapping.
- PR #162: J5 smoke fixes and D-122 LTX dialogue / optional Blender rules.

Important current rules recorded in the branch:

- D-120: a rendered Blender/3D image is not used as a Qwen reference; scene staging is expressed through the scene description and cast registry.
- D-121: dialogue close-ups use the approved character drawing and four mouth states (rest/closed, half, wide, round); mouth timing comes from actual dialogue audio.
- D-122: LTX is the normal dialogue opener (an establishing two-shot); Blender/J5 is optional and must earn its place through measured total cost/effort without unacceptable quality loss.
- `production.pilot.build()` is preview-only; it is not a validated final-cut builder until it consumes a cut plan that passes the gate.
- `cut_plan.main assemble` and the Blender cut renderer gate before producing final output.
- The real LTX-only vs LTX+Blender benchmark is recorded as BLOCKED because the paired dialogue clip/audio/timings and approved four-state cut-outs were not available.
- Existing Stone Age Qwen builders are historical/research-only and the stale J2 clay-conditioned route must not be revived as a production path.
- No paid Qwen/LTX/Modal/RunPod generation job was approved or launched as part of this work.

Do not misrepresent tests. The readiness document records a prior Quality pass and a Blender smoke failure at commit `0c2d1c7`; the smoke validator was then changed, and the current branch head must be validated again. A prior passing workflow is not proof that the current head is green.

Read these before editing:
- `docs/PROJECT_BRIEF.md`
- `docs/DECISIONS_AND_OPEN_QUESTIONS.md`
- `docs/PRODUCTION_RULES.md`
- `docs/ORCHESTRATION.md`
- `docs/LTX_JOBS.md`
- `docs/SCENE_ASSETS.md`
- `docs/SCENE_REUSE_RULES.md`
- `docs/architecture/ROUTE_PLAN_2026-11-06.md`
- `docs/research/stoneage_pilot_2026-11-07/PHASE3_4_5_READINESS_2026-11-08.md`
- `docs/research/stoneage_pilot_2026-11-07/DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08.md`
- relevant code and tests under `explainer_engine/production`, `explainer_engine/edit`, `explainer_engine/blender`, and `tests/unit`.

Also inspect relevant work that is not part of this branch's PR stack before deciding it is obsolete:
- PR #157 / branch `claude/project-thread-a6ccn6`: character-specific speech registers and script validation.
- `argon/ltx-minimisation` and `argon/handoff-2026-11-06`: divergent LTX simplification/handoff work.
- `systemic/next-video`: earlier scene-reuse direction.

Do not merge these branches wholesale. Identify useful, non-conflicting decisions and selectively preserve them.

## Required research and decision

Research actual usable implementations, not only papers or model announcements. Check GitHub code, releases, issues/discussions, ComfyUI workflows, model cards and real creator demonstrations on YouTube. Read relevant viewer comments when they reveal practical failures or successful repeatable workflows.

Compare the three production modes above and candidate models/tools by:
- character consistency across shots and environments;
- scene/action accuracy;
- prompt and reference following;
- camera, composition and motion control;
- multi-shot continuity;
- ease of implementation and number of stages;
- real inference requirements;
- retries/failure rate and cost per accepted usable minute;
- licenses and commercial restrictions.

Return **exactly two recommended tool/workflow combinations**:
1. best overall: simplest reliable storytelling workflow;
2. alternative: a materially different workflow with stronger control where justified.

Explain why each beats the current approach for this specific project. Do not return a long list of models. Do not treat hyperrealism as a primary metric.

## Implementation task

After the comparison, select the best default and implement the migration on this branch.

- Aim for **3–5 major production stages**, not a chain of unnecessary agents, validators, conditioning layers and intermediate assets.
- Choose one default generation mode. Keep the second recommendation as a narrow fallback/experimental route, not a second full orchestration stack.
- Keep interfaces modular enough to swap the video backend without rewriting story planning, audio or editing.
- Preserve useful existing contracts, source provenance, spend caps, creator approval gates and safety checks.
- Remove or simplify duplicated/conflicting controls only after tracing their callers and tests.
- Do not add controls that the chosen model does not actually support.
- Do not claim that a reference image, camera control or character memory works unless demonstrated by the selected implementation.
- Update documentation, configuration, tests and progress records together. Remove contradictory/stale instructions.
- No broad rewrite of the script engine, audio engine or publishing system unless a demonstrated dependency requires it.

## Acceptance test — one coherent 60-second story

Build a small, reproducible comparison using the same story, characters, references and shot intent for both recommended approaches. Use about 6–8 shots and include:
- an establishing shot;
- a two-character interaction;
- shot/reverse-shot or equivalent dialogue coverage;
- a visible action with a clear cause and result;
- a location or time transition;
- a concluding shot that follows from the preceding action.

Measure:
- character identity consistency;
- logical continuity and action accuracy;
- scene/layout fidelity;
- camera and framing compliance;
- continuity between clip boundaries;
- accepted vs rejected generations and number of retries;
- actual cost and operator effort per accepted 60 seconds.

Do not optimize for photorealism. The test passes only if the sequence is understandable as one directed story and the workflow is repeatable.

Do not launch paid provider jobs, consume credits, create cloud resources, change credentials, deploy, publish or merge PRs without the creator's explicit approval. Use dry-runs/free tests first and state clearly what could not be validated.

## Required final report

Be concise and decisive. Deliver:
1. the two selected combinations and evidence;
2. KEEP / CHANGE / REMOVE from the existing system;
3. the implemented default workflow and exact entrypoints/configuration;
4. tests run and results;
5. the 60-second benchmark result or explicit blockers;
6. unresolved risks and exact next action.

Do not stop at another research document or architecture diagram. Make the agreed changes in this branch, but do not hide failed tests or unverified claims.
