# Gemini Handoff — Full Storytelling Engine Migration (Test Branch)
Date: 2026-11-09

## Mission — implement a new engine, not another audit

This branch is a **full migration/test branch**. Your job is to research, choose and implement a new end-to-end video-generation engine for Explainer Engine. The objective is to make a coherent, directed storytelling video reliably — not to preserve the current architecture or merely add another model adapter.

Inspect the repository yourself, identify every conflict, stale rule, broken assumption, incompatible schema, obsolete route and dependent file, then decide and fix them as part of the migration. **Do not return a list of inconsistencies for the creator to resolve. Do not ask which files should change. Trace the dependencies and update every file that needs to change.**

This is a substantial migration. Make the necessary changes across code, schemas, configuration, prompts, workflow definitions, tests, documentation, examples, command entrypoints and progress records. Do not artificially limit the work to a few files or to a thin adapter. Keep the scope focused on the story-to-video production system; do not rewrite unrelated publishing, research, narration or audio subsystems unless the selected engine requires a specific integration change.

Work only on this branch. Do not merge or rewrite other branches.

## Product goal

Explainer Engine creates approximately **12-minute English-language historical What-If documentary / cinematic docudrama** episodes for a general audience.

Visual direction: cinematic, stylized 2.5D / Ink Chronicle.

**Hyperrealism is not the goal.** Do not choose a heavyweight model just because it produces more realistic faces, skin or environments. That advantage has low value here unless it also gives a measurable improvement in control, continuity or reliability.

Priorities, in order:

1. Logical story progression and readable actions.
2. Consistent characters and environments across shots.
3. Reliable control of scene descriptions, composition, framing, camera and action.
4. Repeatable results with low failure and retry rates.
5. Simple production workflow and manageable cost.
6. Sufficient visual quality for a cinematic stylized documentary.

Prefer an efficient, smaller or specialized model when it meets these requirements. Evaluate models by scene-description compliance, controllability, continuity and usable output rate — not parameter count or photorealism.

## Episode structure

- Target duration: approximately **12 minutes**.
- 16 segments (S01–S16), arranged into five narrative phases:
  - Z1, 0:00–2:00, S01–S03: hook and historical setup.
  - Z2, 2:00–4:00, S04–S06: point of divergence and immediate consequences.
  - Z3, 4:00–7:00, S07–S10: escalation, reactions and turning point.
  - Z4, 7:00–10:00, S11–S14: wider consequences and climax.
  - Z5, 10:00–12:00, S15–S16: resolution and reflection.
- Narration carries roughly 70–80% of spoken content; character dialogue roughly 20–30%.
- Flexible visual target: around 60% cinematic video, 30% composed stills/illustrations/collage, 10% maps/explanatory visuals. These are guidelines, not hard quotas.
- Use purposeful establishing wides, two-shots, medium shots, close-ups, OTS, shot/reverse-shot and action coverage where they help the story.
- Clearly distinguish historical facts, the hypothetical divergence and speculative consequences.

Update the project brief and every dependent duration/format specification to this current target. Do not leave conflicting 5–11 minute / 7-minute defaults.

## Choose the production method

Research and compare these three approaches:

A. **Text → Video:** provide a story/scene description and let the engine create a sequence of shots.

B. **Scene image → Multi-shot:** provide a scene/reference image and generate several connected shots from it.

C. **Image per shot → Video per shot:** prepare a still for each shot, generate individual 5–10 second clips, then edit them together.

A simple hybrid is acceptable only if evidence shows it is materially better. Do not combine every possible technique into one pipeline. Choose one primary production mode and implement it as the new default.

## Research — practical evidence only

Investigate working implementations, not only papers, model announcements or attractive demos. Check:

- GitHub repositories, actual inference code, Releases, Issues and Discussions.
- Model cards, workflow examples and licensing terms.
- ComfyUI workflows and practical user reports.
- YouTube creators who demonstrate complete AI storytelling workflows. Watch the actual demonstrations and inspect relevant comments for repeatable techniques, failures and cost information.
- Reddit and other community feedback where it reveals real operating experience.

Start with LTX, Wan, StoryMem, ShotDirector, MultiShotMaster and other relevant projects you find. Do not assume any of these is the winner.

Compare by:
- character and environment consistency between shots;
- scene description and action accuracy;
- camera, composition, pose and motion control;
- support for start/end frames, reference images and multi-shot sequences;
- practical workflow simplicity;
- successful/accepted output rate and retry burden;
- inference requirements, cost and licensing.

Return exactly **two** evidence-backed combinations:
1. Best overall: simplest reliable workflow for this project.
2. Best alternative: a materially different workflow with a clear control or reliability advantage.

Then select one primary combination and proceed with the migration. Do not stop after research or ask the creator to choose between options.

## Existing system — inspect it, but do not preserve it by default

The current system has included:

- Qwen-Image-2.1 with the `xworld_v2` style LoRA.
- Blender/J5 for scene layout, 2.5D assembly and optional dialogue coverage.
- LTX for video generation and dialogue openers.
- Shot plans, scene/reference rules, validators, cut-plan gates and regeneration logic.

Despite substantial work, the creator has not reliably produced one coherent, acceptable 60-second video. Treat this as a reason to reassess the production design, not as a reason to add more layers of control.

The current code is a starting point and a source of reusable components — **not a binding architecture**. Keep only the components that genuinely help the selected workflow. Do not preserve Qwen, its LoRA, Blender/J5 or LTX as active defaults merely because they already exist. Conversely, do not remove a component that demonstrably remains useful.

The old path may remain isolated as a legacy comparison/rollback route where that is inexpensive and technically sensible. It must not remain an equally active, competing default that makes the migrated system ambiguous. The new selected engine must be the clear default for this test branch.

## Branch snapshot and known repository context

This branch was created from `fix/j5-free-render-contracts` at remote commit `21a4e36d59ae0c951e88b4430b1fc60ae83db847`. The remote branch `codex/j5-ltx-first-pr162` was identical to that source at the time of preparation. Commit `0c2d1c7404f2b208aa0c5787217aac5a836d8ed3` is an ancestor of the source head.

The short SHA `20b218e` from the creator's earlier local note could not be resolved in GitHub when this branch was prepared. Check whether the corresponding changes exist in the current checkout or another reachable commit. If they do, incorporate the relevant information. If they do not, proceed using verified repository state; do not block the migration or assume the missing commit is present.

The source branch includes the current remote PR #160–#162 stack and the D-120/D-121/D-122 decisions. These are historical inputs to review, not untouchable constraints. Re-evaluate them against the chosen engine and update/retire any rule that no longer applies.

Relevant existing work outside this branch stack:
- PR #157 / branch `claude/project-thread-a6ccn6`: character-specific speech registers and script validation.
- `argon/ltx-minimisation` and `argon/handoff-2026-11-06`: LTX simplification/handoff work.
- `systemic/next-video`: earlier scene-reuse direction.

Inspect their useful ideas and changes. Do not merge whole branches blindly.

## Migration requirements — change all dependent files

After selecting the new engine, perform the migration end to end.

1. Map the current story-to-video path: inputs, data contracts, schemas, prompts, configuration, model calls, asset/reference handling, editing/assembly, validation, CLI/jobs and tests.
2. Define the new minimal production flow (ideally 3–5 meaningful stages). Each stage must have a real responsibility and supported controls. Remove redundant intermediate representations and controls that confuse the selected model or duplicate the same decision.
3. Implement the selected model/toolchain as the **new default**, including real provider/model configuration, prompt construction, reference handling, job execution, output normalization and editing/assembly integration.
4. Update every affected caller, schema, validator, test fixture, config file, workflow, example, CLI entrypoint, documentation page and project decision. Search the whole repository for stale model names, old route assumptions, obsolete contracts and contradictory instructions. Do not leave half-migrated paths.
5. Retire or isolate the superseded route. Keep a legacy baseline only if useful for comparison or rollback; clearly mark it as legacy and prevent accidental selection as the default.
6. Preserve unrelated working capabilities: story research/fact checking, script structure, narration/dialogue, audio, captions, licensing/provenance, spend limits, creator approval and final edit/review. Adapt interfaces only where required.
7. Add only controls that are genuinely supported by the chosen model. Do not claim character memory, reference strength, camera movement, start/end frame or pose control unless the implementation actually supports it.
8. Simplify validators to check real failure modes in the new workflow. Remove duplicate or speculative gates that do not improve output quality or safety. Keep essential correctness, provenance, budget and creator-approval safeguards.
9. Keep documentation and progress records synchronized with the actual code. Mark old research and decisions as superseded where appropriate; do not silently delete useful history.

This is not a request to patch a few mismatches. It is an explicit authorization to make a broad, coherent migration throughout the files required by the selected new test engine.

## Required end-to-end acceptance test

Implement a reproducible **60-second storytelling pilot** using the new default engine. Use approximately 6–8 shots and the same story, characters, references and shot intent throughout.

The sequence must include:
- an establishing shot;
- a two-character interaction;
- dialogue coverage (shot/reverse-shot or a suitable alternative);
- a visible action with a clear cause and result;
- a location or time transition;
- a concluding shot that follows logically from the preceding action.

Evaluate:
- character identity and environment consistency;
- whether the described action actually happens;
- scene/composition and camera compliance;
- continuity across shot boundaries;
- accepted vs rejected generations and retry count;
- generation cost and operator effort per accepted 60 seconds.

The goal is a coherent, directed story in the intended stylized 2.5D look. Do not grade it primarily on hyperrealism.

Run code-level tests and free/dry-run validation. If a genuine model generation is necessary to validate visual quality, prepare the exact job, price and required inputs, but do not submit a paid job or create billable cloud resources without the creator's explicit approval. Clearly distinguish code tests from a visually validated generation.

## Autonomy and safeguards

- Make implementation decisions independently within this objective. Do not ask the creator to identify every conflict or approve routine file-level changes.
- Do not wait for permission to update dependent files, schemas, tests and documentation required by this migration.
- Do not merge other branches, merge PRs, deploy, publish, alter credentials/secrets or start paid jobs without explicit approval.
- Do not overwrite user work that is not present in the branch. Inspect the available worktree and remote refs first.
- Do not hide failed tests, incomplete integration, missing credentials, unavailable hardware or unverified visual claims.
- Avoid unrelated refactoring.

## Final report

Be concise and decisive. Report:
1. the two researched combinations and why the selected one won;
2. the new default architecture and exact end-to-end path;
3. the files/contracts/configs changed and old paths retired or retained;
4. tests run, with exact results;
5. the 60-second pilot result or the precise blocker to visual generation;
6. known limitations, cost implications and the next action.

**Deliver a working migrated test engine, not just a proposal, research document, adapter or architecture diagram.**
