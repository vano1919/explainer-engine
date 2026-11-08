# Gemini Brief — Create the High-Level Migration Plan for Explainer Engine
Date: 2026-11-09

## IMPORTANT: Your role is planning only

There are three separate roles:

1. **ChatGPT (this handoff):** establishes the product goals, selects the research direction and defines the high-level scope.
2. **Gemini (you):** reviews the two research reports and the current repository, resolves architectural questions, and produces a detailed, file-by-file implementation plan for Codex.
3. **Codex:** implements the approved plan and writes the code, schemas, tests and production documentation.

**Do not write application code. Do not implement the migration. Do not edit Python/TypeScript/JSON schemas/configuration or production workflows. Do not start model generation.**

Your deliverable is a detailed, executable plan that Codex can follow without having to repeat your research or make architectural decisions from scratch. You may create/update planning documents on this branch only. The implementation will be performed by Codex after the plan is reviewed.

## Read these materials first

1. This brief.
2. [Research decision digest](../research/AI_VIDEO_WORKFLOW_DECISION_2026-11-09.md).
3. The two supplied research files:
   - Explainer_Engine_AI_Video_Workflows_Report.pdf
   - AI Documentary Video Production Workflows.md
4. Inspect the actual current repository at this branch, especially:
   - docs/PROJECT_BRIEF.md
   - docs/PRODUCTION_SCRIPT.md
   - docs/SCRIPT_ENGINE.md
   - docs/STORY_ENGINE.md
   - docs/SHOT_PROMPTS.md
   - docs/SCENE_ASSETS.md
   - docs/SCENE_REUSE_RULES.md
   - docs/EDITING.md
   - docs/ORCHESTRATION.md
   - docs/PRODUCTION_RULES.md
   - docs/TOOL_STRATEGY.md
   - docs/LTX_JOBS.md
   - docs/CONTRACTS.md
   - docs/DECISIONS_AND_OPEN_QUESTIONS.md
   - explainer_engine/schemas/production_script.schema.json
   - explainer_engine/production/
   - explainer_engine/imagegen/
   - explainer_engine/edit/
   - explainer_engine/blender/
   - tests/
5. Inspect existing local ComfyUI integration, model/workflow registries and environment-variable usage. A tracked root .env.example was not found through the GitHub contents lookup; the creator may have a local, ignored .env file. Do not assume it is absent locally.

## The decision already made

The high-level decision is **Hybrid B → C as the primary workflow**:

- **B — Scene/Shot-to-Storyboard:** prepare and approve images/keyframes that define the characters, location, composition, camera angle and important action states.
- **C — Image-to-Video per Shot:** generate each short shot independently from its approved start image, and use a second/end image only when that shot needs a specific destination state.
- Do not make pure end-to-end multi-shot text-to-video the default.
- Do not build a 7+ stage pipeline with multiple simultaneous references, depth/canny, middle keyframes and multiple LoRAs.
- Keep composed illustrations/maps out of video diffusion by default; animate them locally with deterministic 2.5D pan/parallax/zoom.
- Use a separate control-video route only for difficult actions where the normal image-to-video route cannot execute the shot.

### Primary combination to plan

- Qwen image editing/keyframe workflow, with Qwen-Image-Edit-2511 + its Multiple-Angles LoRA and ComfyUI multi-angle camera node as the main candidate.
- Wan 2.2 Fun InP / I2V for per-shot video.
- Start by testing the 5B option for the local workflow; compare 14B only if the 5B route cannot meet the agreed quality/control bar. The 14B + LightX2V 4-step route must be tested for lost motion dynamics rather than assumed to be a free speed improvement.
- Local DepthFlow or an already-supported local 2.5D renderer for stills and maps.
- Reuse the existing audio/TTS/timing and assembly capabilities where they fit.

### Secondary combination to plan

- Same approved keyframe stage.
- Wan 2.2 Fun Control / Camera per shot, with exactly one selected control input for that shot (OpenPose, Depth, Canny, camera preset or supported trajectory).
- Treat Wan-Move/ATI as optional only after verifying exact checkpoint, weights, wrapper, model compatibility and local execution path.

This secondary route is a selective fallback for shots that need stronger action or camera control. It is not a second full production engine running for every shot.

### Explicitly do not select as the default

- Blender clay playblast + LTX-2.5 22B Layout-to-Render. The PDF presents it as an alternative, but it reintroduces the heavy Blender/LTX approach the creator is trying to simplify.
- StoryMem, ShotDirector or MultiShotMaster as the production default. The supplied reports identify significant operational/weight/code limitations.
- A pipeline that stacks all references, multiple LoRAs, 3D passes and multi-keyframes into a single video job.

### Technical caveats you must retain

- Qwen-Image-Edit-2511 is a 20B-class image model, not a small model. Its only justification is a demonstrated gain in editing, camera framing or character consistency — not extra photorealism. Compare against the existing Qwen-Image-2.1 path and choose the smallest local option that passes.
- The existing xworld_v2 LoRA was made for the current Qwen path. Do not assume it is compatible with Qwen-Image-Edit-2511.
- The Next-Scene LoRA's published base is Qwen-Image-Edit-2509. Do not assume compatibility with 2511 or stack it into the baseline without a controlled test.
- The Multiple-Angles LoRA and ComfyUI node provide learned camera-prompt control, not deterministic physical 3D camera rendering. Do not promise exact geometry.
- Wan 2.2 Fun InP is appropriate for controlled start/end transitions; not every shot needs both frames.
- 4-step LightX2V acceleration may reduce motion dynamics. Benchmark it against the unaccelerated option.
- The two reports' retry-rate and cost-per-minute numbers are estimates, not measured Explainer Engine outcomes. Treat them as hypotheses and specify how Codex will measure actual local time, retries and accepted outputs.

See the decision digest for source links and further caveats.

## Product context

Explainer Engine creates approximately **12-minute English historical What-If documentary / cinematic docudrama** episodes.

Narrative structure:
- 16 segments: S01–S16.
- Five phases:
  - Z1, 0:00–2:00, S01–S03: hook and historical setup.
  - Z2, 2:00–4:00, S04–S06: point of divergence.
  - Z3, 4:00–7:00, S07–S10: escalation and turning point.
  - Z4, 7:00–10:00, S11–S14: consequences and climax.
  - Z5, 10:00–12:00, S15–S16: resolution and reflection.
- Spoken content target: roughly 70–80% narration and 20–30% character dialogue.
- Flexible visual target: approximately 60% cinematic video, 30% composed illustrations/collages, 10% maps/explanatory visuals.
- Visual direction: stylized cinematic 2.5D / Ink Chronicle. Hyperrealism is not the objective.
- The video must feel like one logically directed story, not an AI clip compilation.

Resolve the current contradiction: docs/PROJECT_BRIEF.md still contains a 5–11 minute range with a 7-minute target. The new canonical project brief must use the current 12-minute target and update dependent specifications.

## Local-only / free-by-default constraint

The intended engine is a **local workflow**:
- Run image and video inference through the local ComfyUI installation and local scripts.
- Use local model weights and local workflow JSON files.
- Read the existing local .env variable names and service paths where available. Never reveal, copy, commit or print secret values.
- Do not call hosted fal.ai, hosted image/video APIs, paid inference endpoints or paid cloud GPUs by default.
- Do not assume an API key means that inference is free.
- If a chosen model cannot run through the current local stack, the plan must identify the exact limitation and propose a free local fallback. Do not silently change the architecture to a paid endpoint.
- Keep model weights outside Git. Include only model identifiers, file names, revisions, licence notes and expected local paths in the repository.
- Check the base model, every adapter/LoRA, custom node and utility licence separately.
- Use local/free TTS where possible; keep existing audio timing, mixing and assembly code where it remains useful. Any paid audio service must remain explicitly opt-in.

Do not include hardware specifications in your recommendation. Instead, make Codex verify local resource requirements from the installed environment and model files.

## Your task — produce a high-level plan that becomes a detailed Codex plan

Do not write code. Analyse the current repository and create a plan with the following phases and sections.

### Phase 0 — Repository and decision audit
- Map the current topic/script → visual script → image assets → video jobs → audio → assembly → QA path.
- Identify every active and legacy route.
- Trace schemas, CLI entrypoints, model registries, workflows, docs, prompts and tests.
- Identify contradictions between D-80, D-96, D-116, D-120, D-121, D-122 and the new selected B→C direction.
- Identify which existing work remains reusable and which route assumptions must be retired.
- Do not ask the creator to resolve routine inconsistencies; make a recommendation and explain the trade-off.

### Phase 1 — Validate the two selected local combinations
- Confirm the exact downloadable model/checkpoint names and current revisions.
- Confirm that the required ComfyUI nodes and workflows exist and are locally runnable.
- Confirm model/adapter compatibility: Qwen-Image-Edit-2511 with Multiple-Angles LoRA; xworld_v2 compatibility; Next-Scene 2509 compatibility; Wan 2.2 Fun InP 5B/14B; LightX2V compatibility; Fun Control and trajectory options.
- Separate official features from community nodes and experimental work.
- Record model sizes, actual local runtime/memory, licences and known failure modes.
- Choose the smallest configuration that passes the visual/control pilot. Do not prefer 14B/20B/22B models for realism alone.
- Recommend exactly one primary route and one selective fallback.

### Phase 2 — Target architecture and minimal contracts
Design a simple pipeline with no more than four major production stages:
1. **Script and visual plan:** structured story/script and per-shot visual script.
2. **Approved visual assets/keyframes:** character/location references, shot start frames and optional end frames.
3. **Per-shot video generation:** local Wan I2V/FLF2V; optional single-control fallback for difficult shots.
4. **Assembly and review:** still/map motion, narration/dialogue, music/foley, edit and QA.

Define the exact data flow, state transitions, folder outputs, IDs, manifests, retry handling and required metadata. Keep the story and shot plan as the single source of truth; avoid duplicate scripts/shotlists that can drift apart.

### Phase 3 — Documentation and specification restructure

Give Codex an exact file-by-file TODO list. At minimum, plan these documentation groups:

**A. Project and episode format**
- Update docs/PROJECT_BRIEF.md and dependent episode standards to the 12-minute S01–S16 / Z1–Z5 format.
- Keep the 60/30/10 visual mix flexible, not a forced quota.

**B. ChatGPT main production method**
- Create one canonical, self-contained docs/MAIN_METHOD.md.
- This is the document ChatGPT will follow when preparing a new episode.
- It must be easy to open and understand without searching dozens of unrelated rules.
- It should link to machine schemas only where necessary, and it must not contradict them.

**C. Story and script rules**
- Reconcile docs/STORY_ENGINE.md, docs/SCRIPT_ENGINE.md and docs/PRODUCTION_SCRIPT.md.
- Define one canonical script format and remove duplicate/conflicting rules.
- Preserve fact checking, citations, factual-vs-speculative distinction, character motivation, cause/effect and dialogue register rules.

**D. Visual script, assets and image generation**
- Reconcile docs/SHOT_PROMPTS.md, docs/SCENE_ASSETS.md and docs/SCENE_REUSE_RULES.md.
- Define the visual-script contract and the character/location/prop reference contract.
- Create or consolidate a clear image/keyframe generation guide.

**E. Video generation**
- Replace obsolete LTX multi-keyframe/default instructions with the selected Wan B→C workflow.
- Create a clear local video-generation guide: I2V vs FLF2V selection, start/end frame rules, prompt format, clip duration, allowed controls, ComfyUI workflow, model settings and retry rules.
- Keep the secondary control-video route separate and explicitly optional.

**F. Local runtime and model setup**
- Define a single local model/workflow registry and safe .env configuration.
- Keep model weights out of Git.
- Document install/update/check commands and how the engine validates a local ComfyUI endpoint.
- No paid provider routes in the default execution path.

**G. Audio, editing, orchestration and QA**
- Preserve and reconcile docs/AUDIO_SYSTEM.md, docs/EDITING.md, docs/ORCHESTRATION.md, docs/PRODUCTION_RULES.md, docs/CONTRACTS.md and docs/TOOL_STRATEGY.md.
- Remove route-specific LTX/J5/Blender rules that no longer apply to the default, but retain optional/legacy notes where useful.
- Do not rewrite unrelated publishing or research features.

### Phase 4 — Define docs/MAIN_METHOD.md in detail

The Codex plan must define the exact outline, required instructions, templates and examples for this ChatGPT-facing guide.

It must explain the work in this order:

1. **Episode brief:** what information ChatGPT needs from the creator (What-If premise, historical period, key event, audience, target duration, tone, existing constraints).
2. **Historical research dossier:** source-backed facts, timeline, key figures, real-world outcome, point of divergence, uncertain claims and explicit speculation boundaries.
3. **12-minute story structure:** 16 segments and five phases; dramatic question, hook, setup, divergence, cause/effect escalation, climax, resolution and final reflection.
4. **Script-writing guide:** mandatory story beats; narration/dialogue balance; character voice/register; readable dialogue; factual vs speculative phrasing; transitions; pacing; no filler; every important line must advance the story.
5. **Visual-script guide:** how to translate every relevant story beat into a shot. Define shot IDs, segment IDs, target duration, narrative purpose, location, cast, props, action start/end, camera shot size/angle/movement, screen positions/composition, lighting/time, continuity references, audio line IDs, visual type, generation mode, start/end frame needs, image prompt, video prompt and transition.
6. **Character/location/prop bible:** fixed appearance descriptions, approved references, costume/prop continuity, location identity and scene state. Do not invent a new design for every shot.
7. **Image generation guide:** when an image is actually needed; when to reuse an approved asset; how to create a master anchor; how to request a new angle; when to create an end frame; how to repair a bad still before video generation. Give a reusable prompt template.
8. **Video generation guide:** when to choose I2V vs FLF2V; how to write one clear motion/action prompt; one main action and at most one camera move per simple clip; how to specify subject, action, environment, camera, temporal progression and continuity; how to avoid contradictory instructions and over-conditioning; how to select optional control input.
9. **Dialogue/audio guide:** narration, dialogue, speaker, intended addressee, delivery, audio file/timing and when lip-sync is actually required. Keep narrator audio as the spine of the edit.
10. **Stills/maps guide:** how to create composed visuals and animate them locally with deterministic parallax/pan/zoom instead of video diffusion.
11. **Assembly and QA guide:** continuity, shot order, transitions, captions, audio mix, 24fps/target output, fact-check and creator review.
12. **Output package:** exact files ChatGPT must produce and the one canonical machine-readable source consumed by the engine. Avoid parallel duplicate shotlists.

For every stage, the guide must state:
- required inputs;
- mandatory output fields;
- reusable prompt/template;
- validation checklist;
- what ChatGPT must not invent or overcomplicate;
- what gets passed to the local engine.

ChatGPT writes the script, visual script and generation instructions. The local engine executes the image/video workflows. ChatGPT does not claim that it has rendered or approved a clip.

### Phase 5 — Detailed Codex implementation plan

Create one detailed plan file, recommended path:
docs/architecture/CODEX_IMPLEMENTATION_PLAN_2026-11-09.md

The plan must be executable by Codex and contain:
1. Final selected architecture and why.
2. Explicit KEEP / CHANGE / REMOVE decisions.
3. A dependency-ordered TODO list.
4. Exact files to create, modify, consolidate, deprecate or delete.
5. Exact schemas/contracts and example payloads.
6. Local ComfyUI integration and .env variable requirements (names only, never values).
7. Model/workflow registry changes and pinning/version rules.
8. CLI/entrypoint changes and example commands.
9. Unit, integration, schema, dry-run and local smoke tests.
10. A controlled 60-second visual benchmark and scoring rubric.
11. Acceptance criteria for each phase.
12. Risks, rollback path and unresolved blockers.

Every TODO must say what changes, why, expected result and how it is tested. No vague tasks such as "improve continuity" or "fix prompts".

### Phase 6 — Pilot and validation plan
- Use a single, historically checked 60-second story and the same character references.
- Target approximately 12 shots: 7 video shots / 4 composed illustrations / 1 map shot, subject to actual story needs.
- Test the primary workflow first and the secondary workflow only on shots requiring additional control.
- Measure character consistency, scene/action accuracy, camera compliance, continuity, accepted/rejected jobs, retries, local generation time and manual effort.
- Code-level tests and dry-runs are not visual proof. State clearly which results require a real local model run.
- Do not authorize or start paid jobs; do not create paid cloud resources.

## Gemini deliverables — planning documents only

Create/update only these planning artifacts on this branch:
1. A concise decision record, if the digest above needs a correction based on the repository audit.
2. docs/architecture/CODEX_IMPLEMENTATION_PLAN_2026-11-09.md — the detailed implementation plan for Codex.

Do not implement code or change runtime configuration. Do not modify application source files. Do not create a new branch. Do not merge PRs. Do not launch model inference.

## Quality bar for your plan

The plan is successful only if Codex can implement it without having to:
- choose the model architecture again;
- guess what ChatGPT should produce;
- invent script/visual-script fields;
- guess the local model/workflow setup;
- decide which legacy rules are still active;
- rediscover which tests and acceptance criteria matter.

Be specific, critical and concise. The purpose is to end the architecture debate and give Codex an unambiguous implementation sequence.
