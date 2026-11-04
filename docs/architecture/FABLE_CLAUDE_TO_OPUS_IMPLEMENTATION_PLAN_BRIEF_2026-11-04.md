# Fable / Claude Research Brief → Opus Implementation Plan

> **MANDATORY HANDOFF.** Fable-capable Claude must perform the full repository/research synthesis and produce an implementation-ready plan for a separate Opus session. Do not implement the renderer or run paid work.

## 1. Role and target branch

Act as an independent senior software architect, Blender technical director, animation pipeline engineer, Python architect, QA engineer and cost/performance auditor.

Repository: vano1919/explainer-engine  
Working branch: opus/ink-chronicle-blender-visual-system-2026-11-04  
Context branch: claude/master-mold-ready-2026-11-04

Primary direction: read INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04.md first.

Deliver a complete evidence-based Opus implementation plan, high-level class/module architecture and ordered work packages. Do not implement, start paid jobs, alter production provider settings, publish or merge to main.

## 2. Required reading — full files, not excerpts

Read:
1. The primary direction document in this directory.
2. docs/research/cinematic_audio_visual_craft_and_tool_implementation_report_2026_11_04.md — especially visual craft, camera/lens, lighting, animation, editing, pacing, HELPER graphics, 20 scene archetypes, shot sequences, Blender, reusable repositories/assets, optimization and tool implementation. Do not blindly copy old LTX/Qwen routing.
3. docs/COST_AND_TIME_MODEL.md — separate historical estimates from measured facts and current spend caps.
4. docs/DECISIONS_AND_OPEN_QUESTIONS.md — inspect D-93, D-95, D-70, D-41, D-91, D-92 and relevant D/BP/ED/UR entries.
5. docs/PRODUCTION_SCRIPT.md, VIDEO_PARAMETER_SPEC.md, PRODUCTION_RULES.md, VISUAL_WORLD_ARCHITECTURE.md, WORLD_BIBLE.md, EDITING.md, CRAFT_CURRICULUM.md, SOURCED_RULES.md, STORY_ENGINE.md, ORCHESTRATION.md, PROJECT_BRIEF.md.
6. CLAUDE.md, docs/INDEX.md, relevant package init files, configs, schemas and tests.
7. Actual implementations and call graphs: production/assemble.py, assets/library.py, world/, scripting/, video/, qa/, cloud/, config/, schemas and tests.
8. Scan TODOs across the entire branch. Classify each CURRENT / RELEVANT / SUPERSEDED / DUPLICATE / UNVERIFIED / HISTORICAL. The old CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md and MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md contain unverified legacy proposals, not blanket authority.

## 3. Non-negotiable target

- One Ink Chronicle universe: stylized real 3D geometry rendered as a cinematic illustrated / graphic-novel look.
- Blender final rendering; EEVEE default candidate, Cycles exceptional only.
- 2560×1440 master, 24 fps long-form.
- Visual runtime: 10% HELPER / 30% STILL / 60% VIDEO.
- Spoken words: nominal 70% narrator / 30% voiced character dialogue. Explicitly flag conflict with D-95's 75/25 midpoint and 70–80/20–30 range.
- US$10–15 recurring render/compute target per 12–15-minute episode after reusable assets exist. Unproven until benchmarked.
- Preserve compatible story/research/audio/timing/QA/approval/FFmpeg/cloud safety systems.
- All final visuals share Ink Chronicle. No competing final generative-video style.

## 4. Audit method

- Record exact branch HEAD SHA.
- Distinguish production code, partial implementation, stub, retired module, config, fixture, documentation and unverified TODO.
- Trace callers and data contracts. A TODO is not evidence that its class/function exists or is used.
- Find canonical authority for schemas, ratios, style tokens, timing, cost caps and decisions.
- Inspect tests and current pipeline entry points.
- Run safe local read-only checks only; report exact commands/environment. No paid calls.
- Keep historical evidence, but remove superseded instructions from active handoff docs.

## 5. Required conflict/supersession audit

Create a matrix with: old authority/ID; file+symbol+test; current meaning; new target; severity; proposed disposition; migration; approval state.

At minimum investigate:
- D-93 old LTX VIDEO / Python-moving STILL / Python HELPER mapping vs new Blender lane mapping.
- D-95 75/25 midpoint and range vs new 70/30 spoken-word target.
- D-70 stills+2.5D default / sparse generated video vs Blender-authored animated VIDEO.
- D-41 previous image-generation anchors and look assumptions vs 3D geometry/NPR Blender.
- look_v2.json banned words and world/bible.json anti-3D-render rules.
- BP-170 and all still-motion/duration caps.
- film_shots.py, variant_plan.py, schemas, prompts, validators, shot QA and reports.
- 24 fps long-form vs any 30 fps still lane.
- old Qwen/LTX tiers, LoRA pins, 8k+1 buckets, portrait lip-sync and related TODOs.
- retired production/rig.py and any active references.
- old Master Mold v2.1.0 synchronization TODOs and production_script/4 routing proposals.

Do not silently rewrite old decisions. Propose new canonical IDs with explicit supersession references. Separate approved intent from details still requiring creator approval: tolerance bands, 70/30 tolerance, render scaling defaults, engine settings, cloud provider and Cycles exception policy.

## 6. Complete 10/30/60 grammar

For each subcategory specify purpose, selection triggers, when not to use, required script metadata, shot sizes/lens/composition, camera/subject/environment motion, lighting/atmosphere, duration guidance and evidence status, Blender scene strategy, render tier/optimization, audio interaction, continuity, QA/failure modes, reuse opportunities and relative GPU cost category (not invented seconds/frame).

HELPER:
H1 strategic/route/territory maps; H2 timeline/chronological stepper; H3 quantitative charts/counters; H4 cutaway/process/network diagrams; H5 comparisons/evidence callouts.

STILL:
S1 establishing tableaux; S2 character tableaux; S3 group tableaux; S4 detail/macro inserts; S5 atmospheric/aftermath tableaux; S6 visual contrast/match compositions; S7 freeze/held tableaux.

VIDEO:
V1 large battle/siege/formations; V2 character action/duel; V3 dialogue/negotiation; V4 group dialogue/council; V5 crafting/building/repair; V6 travel/traversal; V7 reveal/discovery; V8 emotional performance; V9 aftermath/consequence; V10 environment-driven action.

Keep the research report's 20 scene archetypes as a higher-level narrative taxonomy. Show how each archetype may combine multiple lanes; do not force one archetype to one lane.

## 7. Versioned shot specification contract

Propose a typed, versioned contract including:
- stable shot/scene/sequence/episode IDs;
- lane and rationale; archetype/subcategory; narrative purpose;
- factual claim references, era and asset constraints;
- characters, props, environment and asset IDs;
- shot size, camera position, lens, focus target, movement, screen direction, composition;
- subject action, action phases, facial performance and lip-sync coverage;
- environment/secondary motion;
- lighting, atmosphere, materials and palette overrides;
- duration, fps, start/end frame, audio cue references;
- render engine, resolution, quality tier, samples/TAA, denoise, scale and upscale policy;
- continuity references;
- QA assertions/severity;
- estimated/actual GPU time, cost, retries, cache key and provenance.

Avoid one huge untyped JSON blob. Recommend typed dataclasses/Pydantic or repository-compatible models plus JSON Schema, strict validation, defaults, migrations and examples. Determine schema version only after auditing current evolution.

## 8. High-level class/module architecture

Evaluate, merge, rename or reject these components as justified:
- VisualProductionOrchestrator — visual-job coordination, not narrative/audio ownership.
- ShotSpec / ShotPlan — canonical typed shot contract.
- VisualLanePlanner — runtime allocation and lane selection.
- SceneArchetypeRegistry — narrative archetypes to shot patterns.
- ShotDesigner — narrative beats to camera/action/coverage.
- InkChronicleStyleResolver — single visual grammar plus era overrides.
- AssetLibrary / AssetResolver — 3D assets, rigs, props, environments, materials, animation, provenance.
- BlenderSceneBuilder — build/update Blender scenes from ShotSpec.
- BlenderRenderAdapter — headless Blender, EEVEE default, exceptional Cycles.
- RenderProfileSelector — preview/look-dev/final/hero tiers and 1440p/scale decisions.
- RenderCache — content-addressed cache and incremental rerender.
- RenderJobPlanner / RenderJobRunner — chunking, parallelism, checkpoints, resumability, safe shutdown.
- CostEstimator / CostLedger — dated prices, expected/actual cost, budget stops.
- UpscaleAdapter — conservative temporal upscale and artifact QA.
- CompositorAdapter — deterministic graphics, maps and final composition.
- TimelineAudioBridge — reuse existing frame-accurate timeline/audio.
- VisualContinuityChecker / VisualQA — style, identity, geometry, direction, text, flicker, frame quality.
- AssetBuildPipeline — import/clean/retopo/rig/LOD/material/style normalization.
- BenchmarkHarness — reproducible representative scene benchmarks.

For each component give purpose, methods/signatures, inputs/outputs, state ownership, dependencies, failure behavior, tests, and whether new/adapted/retained. Avoid classes without distinct responsibility.

## 9. Cost and benchmark plan

Recalculate the target for 12 and 15 minutes at 24 fps / 2560×1440. Separate pure render GPU time, boot/warm-up, scene prep/transfers, storage/egress, retries, upscale/compositing, one-time asset creation and human authoring.

Compare M4 Pro 24GB unified memory, RTX 3090/4090/A40/A6000-class cloud options and community render farms using current primary sources. Hourly price alone is insufficient: calculate cost per accepted final minute and include queue, interruption, durability, setup and failure overhead.

Benchmark:
- 3 scenes: character/dialogue close-up, interior/establishing tableau, large battle/Tactical Diorama.
- Native 2560×1440 and 1920×1080 render scale + upscale.
- Preview and final profiles.
- Local M4 Pro plus at least one cloud NVIDIA GPU, ideally two.
- At least 3 repeats to estimate variance/cache benefit.
- Record Blender version, scene complexity, settings, frame time, peak memory, output size, quality defects, wall time and actual bill.
- QA line integrity, temporal flicker, identity, costume/material consistency and composition.
- A cost pass is invalid if visual quality fails.

## 10. Asset reuse and production time

Assess humanoid meshes, rigging, retargetable cycles, hand/face rigs, shape keys, Rhubarb/visemes, costume layers, era variants, modular props/architecture, terrain, foliage, crowd instances, lighting/camera rigs, shot templates and Geometry Nodes. Verify licenses and compatibility. Label savings measured / vendor claim / estimate / hypothesis; do not invent percentage reductions.

## 11. TODO cleanup and branch hygiene

Scan the whole branch. Remove only TODOs demonstrably obsolete or duplicate. For each removal record path/symbol/reason, confirm no active dependency and preserve useful history in a supersession record. Do not delete active runtime code or tests. Replace old LTX/Qwen TODO-only stubs with Blender TODO contracts only after caller/schema/test audit. Keep relevant TODOs but rewrite them as bounded work packages with inputs, outputs, tests, acceptance criteria and dependencies. Do not copy CLAUDE-MASTER-MOLD-SYNC TODOs forward.

The old 2D rig is retired. Do not reuse it as the Blender character rig; retain it only as historical code unless dependency audit proves safe deletion.

## 12. Required deliverables on this branch

1. docs/architecture/OPUS_IMPLEMENTATION_PLAN_2026-11-04.md — phases, dependencies, class/module structure, APIs, migrations, tests, cost, risks, rollback and acceptance.
2. docs/architecture/VISUAL_GRAMMAR_10_30_60_SPEC_2026-11-04.md — detailed lane taxonomy and selection rules.
3. docs/architecture/SHOT_SPEC_SCHEMA_DESIGN_2026-11-04.md — typed schema proposal and examples.
4. docs/architecture/DECISION_AND_RULE_SUPERSESSION_MATRIX_2026-11-04.md — all legacy conflicts.
5. docs/architecture/CLASS_ARCHITECTURE_2026-11-04.md — high-level class/module tree.
6. docs/architecture/RENDER_COST_BENCHMARK_PLAN_2026-11-04.md — reproducible budget validation.
7. docs/architecture/TODO_DISPOSITION_2026-11-04.md — kept/rewritten/removed/archived TODOs.
8. Update docs/INDEX.md and CLAUDE.md so this new direction is prominent without erasing history.
9. Add branch handoff explaining what is planned vs not implemented and what Opus must decide.

## 13. Evidence and output quality

Start the Opus plan with executive recommendation; verified current architecture facts (paths and immutable SHA/line ranges); target architecture; CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION; approved vs open decisions; migration sequence and stop gates.

Label material claims as VERIFIED REPO FACT (path/SHA/line), VERIFIED EXTERNAL FACT (primary source/date/version), CREATOR-APPROVED REQUIREMENT, MEASURED RESULT, ESTIMATE, HYPOTHESIS or OPEN DECISION.

Include negative findings. If a module/schema/caller/test/measurement does not exist, say so. Do not invent assumptions. Opus must independently verify current repo state and current external prices/versions.

## 14. Final gate

Verify branch/HEAD, link every new document from docs/INDEX.md, mark old conflicting TODOs superseded or evidence-audited, run available safe documentation checks, and report files/checks. No paid tests, no merge, no PR unless requested.
