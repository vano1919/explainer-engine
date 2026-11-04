# Fable Master Task — Evidence-Closed Ink Chronicle Plan and Opus Handoff

**Status:** EXECUTE THIS PLANNING TASK ONLY  
**Repository:** `vano1919/explainer-engine`  
**ONLY working branch:** `opus/ink-chronicle-blender-visual-system-2026-11-04`  
**Single authoritative output:** `docs/architecture/INK_CHRONICLE_OPUS_IMPLEMENTATION_ROADMAP_2026-11-04.md`  
**This file is the controlling Fable instruction.** If an older brief, handoff, TODO, research note or branch says something different, apply the authority and reconciliation rules below. Do not silently follow older instructions.

---

## 0. Mission and completion standard

Act as an independent principal software architect, Blender technical director, animation-pipeline engineer, Python architect, QA automation lead, repository auditor and cost/performance researcher.

Your task is to produce one evidence-backed, implementation-ready, dependency-ordered roadmap for the Ink Chronicle visual production system and a complete Opus handoff.

**You are not implementing the system.** You are deciding and specifying exactly what Opus should implement, in what order, why, where, with which contracts, tests, dependencies, acceptance criteria and rollback rules.

The roadmap is not complete if it contains unresolved technical questions, vague TODOs, alternative lists without a recommendation, unnamed owners, missing acceptance criteria, or decisions deferred to Opus.

Before Opus is launched:
1. Every technical decision must have one recommended disposition: KEEP, CHANGE, REMOVE, ADD, DEFER-BEHIND-TEST, or REJECT.
2. Every recommendation must have evidence, alternatives considered, trade-offs, confidence and a validation method.
3. Every implementation work package must have exact repository paths, dependencies, owner, inputs, outputs, tests, acceptance criteria, risks and rollback.
4. Every creator-only approval must be isolated into one concise **Creator Decision Gate** at the end of the roadmap. Do not pretend the creator approved it. Do not ask questions one by one throughout the document.
5. The roadmap must end with a binary **OPUS READY / OPUS BLOCKED** verdict. OPUS READY is allowed only after all creator-only decisions have explicit answers and no other blocking unknown remains.

Do not confuse “closed plan” with “invented certainty.” If a fact cannot be verified without a future benchmark, choose a safe provisional default, specify the exact experiment and pass/fail thresholds, and make the implementation conditional on that gate. Never label a hypothesis as a measurement.

## 1. Authority, scope and non-negotiable creator targets

Use this precedence order:
1. Platform, security, legal and safety requirements.
2. The creator's explicit instructions in this task and current project decisions.
3. Explicitly creator-approved decisions in the canonical decision log.
4. Verified repository behavior and tests.
5. Verified external primary-source evidence.
6. Existing specifications and documentation.
7. Research hypotheses and recommendations.

The following are creator-set targets, not suggestions. Do not change them silently:

| Area | Required target | Measurement |
|---|---|---|
| Visual identity | One coherent **Ink Chronicle** universe | Style acceptance across characters, props, interiors, environments, battles and helper graphics |
| Production method | Reusable real 3D geometry for characters, costumes, props, architecture, terrain and environments | Asset/scene provenance and repeatable Blender builds |
| Final visual appearance | Cinematic illustrated / graphic-novel language; controlled ink contours, graphic value grouping, painterly surfaces, deliberate palette and motivated cinematic lighting | Creator-reviewed style sheets and representative renders |
| Final visual renderer | Blender is the intended authoritative source of final visual pixels | Render manifests and output provenance |
| Render engine | EEVEE is the default candidate; Cycles only by explicit per-shot justification | Measured quality/cost comparison |
| Master output | 2560×1440 (QHD/1440p), 24 fps | ffprobe, frame dimensions and episode contract |
| Visual runtime mix | 10% HELPER / 30% STILL / 60% VIDEO | Lane duration divided by total visual timeline duration |
| Speech mix | 70% narrator / 30% voiced character dialogue target | Audible spoken-word count; exclude `voiced:false` |
| Lip-sync | 5-second maximum planning target only for visible voiced dialogue coverage | Shot purpose and actual coverage |
| Non-dialogue action | 10–15 seconds may be used when continuous action benefits from it | Scene/action continuity; do not split solely to satisfy lip-sync limit |
| Cost objective | US$10–15 recurring render/compute cash cost per finished 12–15-minute episode after reusable assets exist | Measured itemized cost; explicitly unproven until benchmarked |
| Production governance | Preserve compatible story, research, audio, timing, QA, approvals, spend guards, asset provenance and FFmpeg delivery | Current callers/contracts/tests retained or migrated explicitly |

The 10/30/60 visual runtime ratio and 70/30 spoken-word ratio are independent. Never use one as a proxy for the other. A VIDEO shot may be silent or narrated; STILL and HELPER can sit under narration. Report spoken words and audible seconds separately.

The creator calls 2560×1440 “2K” informally. Use the technically precise term QHD/1440p in specifications.

## 2. Mandatory branch and prior-work reconciliation — do this first

The remote branch inventory previously showed these relevant branches:

- `opus/ink-chronicle-blender-visual-system-2026-11-04` — the ONLY working/final branch.
- `claude/master-mold-ready-2026-11-04` — Claude research/base work.
- `opus/ink-chronicle-blender-plan-2026-11-04` — separate Opus planning branch containing prior architecture/task documents.
- `experiment/blender-scene-poc-2026-11-04` — isolated Blender scene PoC.
- `main` — default branch, with a relevant manual Blender PoC workflow commit.
- Other `claude/project-thread-*` branches — inspect only if branch history or the research index shows relevant work.

These branches are not interchangeable. A prior remote comparison showed the final branch and the Opus-plan branch diverged (the Opus-plan branch had 9 commits not present in the final branch; the final branch had 16 commits not present in the Opus-plan branch). The final branch and Blender PoC branch also diverged (8 PoC commits were not present in the final branch). Re-run all comparisons because refs may have moved.

### Required branch audit

Before writing the roadmap:
1. Record the exact branch name and HEAD SHA for every relevant branch, plus the final branch's upstream and clean/dirty state if local Git access is available.
2. If local Git is unavailable, state that clearly. Do not pretend a remote API check proves the local worktree is clean or on the correct branch.
3. Compare ancestry and unique commits for the final branch against Claude research, Opus-plan, Blender-PoC and main.
4. For every unique commit on a source branch, inspect the commit diff and affected files. Classify it as:
   - PRESERVE AS-IS
   - INTEGRATE INTO FINAL BRANCH
   - ADAPT / SUMMARIZE
   - REFERENCE WITHOUT COPYING
   - REJECT AS OBSOLETE / CONFLICTING
5. Explain the reason and evidence for each disposition. Pay special attention to the 9 Opus-plan-only commits and 8 Blender-PoC-only commits; do not omit them because they are on another branch.
6. Inspect the Opus-plan branch's existing `docs/opus/` documents. Treat them as prior work to reconcile, not as an instruction to create duplicate deliverables.
7. Inspect the PoC branch's source, README, workflow and render artifacts. Preserve its useful evidence in the roadmap; do not overstate its proof.
8. Inspect the relevant main-only workflow commit and decide whether it is useful evidence or should remain separate.
9. Do not blindly merge, cherry-pick, reset, force-push, delete or overwrite source branches. No destructive Git operations.
10. All Fable work and the final roadmap belong on the ONLY working branch named above. Do not create another working branch.

If branches have moved, record the new facts and use the current remote state. If the final branch does not exist or its HEAD cannot be safely identified, STOP and report the blocker rather than creating a substitute branch.

## 3. Existing repository evidence to reconcile

Read full files, not only search excerpts. Inspect the complete repository structure and trace code callers, contracts, schemas, tests and runtime entry points. At minimum inspect:

### Canonical project and decision sources
- `CLAUDE.md`
- `docs/INDEX.md`
- `docs/DECISIONS_AND_OPEN_QUESTIONS.md`
- `docs/SOURCED_RULES.md`
- `docs/PRODUCTION_RULES.md`
- `docs/PRODUCTION_SCRIPT.md`
- `docs/VIDEO_PARAMETER_SPEC.md`
- `docs/VISUAL_WORLD_ARCHITECTURE.md`
- `docs/WORLD_BIBLE.md`
- `docs/EDITING.md`
- `docs/CRAFT_CURRICULUM.md`
- `docs/COST_AND_TIME_MODEL.md`
- `docs/CONTRACTS.md`
- `docs/ORCHESTRATION.md`
- `docs/PROJECT_BRIEF.md`
- `docs/PROGRESS.md`
- relevant schemas, registries, configs and tests.

### Existing branch-specific planning material
- `docs/architecture/INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04.md`
- `docs/architecture/BRANCH_HANDOFF_README_2026-11-04.md`
- `docs/architecture/FABLE_CLAUDE_TO_OPUS_IMPLEMENTATION_PLAN_BRIEF_2026-11-04.md` (this file)
- `docs/architecture/INITIAL_TODO_DISPOSITION_2026-11-04.md`
- `docs/research/cinematic_audio_visual_craft_and_tool_implementation_report_2026_11_04.md`
- Opus-plan branch files under `docs/opus/`, including master task, architecture/class map, render-cost benchmark, research source scope, rule conflicts/migration, TODO register and 10/30/60 grammar.

### Runtime implementation and tests
Trace at least:
- `explainer_engine/edit/router.py`
- `explainer_engine/edit/visual_compensator.py`
- `explainer_engine/edit/tableau.py`
- `explainer_engine/maps/` and `hud.py`
- `explainer_engine/production/assemble.py`
- `explainer_engine/production/rig.py` and every caller/reference (do not assume retired code is safe to delete)
- `explainer_engine/assets/library.py` and its schema
- `explainer_engine/world/bible.py`, `world/bible.json`, `world/look_v2.json`, `world/eras.json`, `design/palette.json`
- `explainer_engine/audio/spine.py`, sound director and voice modules
- `explainer_engine/core/contracts.py`, `core/shot_cache.py`, `core/ledger.py`
- `explainer_engine/config/spend_caps.json`
- `scripting/film_shots.py`, `variant_plan.py`, all relevant validators and rule registries
- `explainer_engine/video/`, `qa/`, `cloud/`, `schemas/` and their tests.

For every important claim include exact file path, symbol, line range and commit/HEAD context. If line numbers cannot be obtained, provide file path and immutable commit SHA, and explicitly say line range unavailable. Do not invent line numbers.

## 4. Mandatory conflict resolution

Create a complete old-vs-new rule matrix inside the single roadmap. For each row include: current authority/ID, current behavior, evidence path/symbol/test, new target, severity, KEEP/CHANGE/REMOVE/DEFER decision, exact migration, dependent consumers, test and approval state.

At minimum resolve:

1. D-93 old mapping (LTX VIDEO / Python-moving STILL / Python HELPER) versus new Blender lane mapping.
2. D-93 ±5 percentage-point tolerance: decide retain/change/remove with reasoning; do not change the target lane shares.
3. D-95 current 70–80% narrator / 20–30% dialogue range and 75/25 midpoint versus creator's 70/30 target. Preserve historical record; specify exact canonical amendment and dependent validators/tests. Do not claim an unmerged amendment is already in effect.
4. D-70 still-first / 2.5D / sparse generated-video default versus Blender-authored animated VIDEO.
5. D-41 image-generation anchors and visual assumptions versus 3D geometry and NPR rendering.
6. `world/bible.json` ban on a 3D-render look and `look_v2.json` banned words such as realistic / 3d render. Distinguish **3D geometry as a production method** from **photorealistic or generic CGI final appearance**. The final look must remain illustrated Ink Chronicle, not photorealism.
7. BP-109, BP-170 and every still-motion, hold, duration and frame rule.
8. 24 fps long-form contract versus any 30 fps lane or legacy output assumptions.
9. LTX/Qwen keyframe tiers, LoRA pins, 8k+1 constraints, portrait lip-sync and related TODOs.
10. `DRAMA_BLOCKED_3D` and any route refusing Blender scenes.
11. Retired `production/rig.py` and every active reference/caller.
12. Master Mold v2.1.0 synchronization TODOs and stale routing proposals.
13. Current raster compositor, Remotion, FFmpeg and Blender responsibilities.
14. Current asset library raster assumptions versus .blend, .fbx, .glb/.gltf, .obj, textures, rigs and animation dependencies.
15. Current cloud/RunPod spend controls and proposed Blender execution model.

Do not rewrite canonical decisions, rule registries, schemas, prompts or code in this planning task. The roadmap must state exactly what Opus should change, where and in which order.

## 5. Visual grammar — complete 10/30/60 specification

The three lanes must share the same Ink Chronicle style engine, world bible and reusable asset universe.

### HELPER — 10% runtime
Cover strategic/route/territory maps, timeline/chronological stepper, charts/counters, cutaway/process/network diagrams, comparisons and evidence callouts. Data, labels, dates, boundaries and numbers must be deterministic and sourced; AI must not invent or draw data labels.

### STILL — 30% runtime
Cover establishing tableaux, character tableaux, group tableaux, detail/macro inserts, atmospheric/aftermath tableaux, visual contrast/match compositions and held/freeze tableaux. A STILL may have controlled camera movement, parallax, focus pulls, animated light, particles, environment motion or small pose changes. Do not require full character animation where it adds no value.

### VIDEO — 60% runtime
Cover battles/sieges/formations, character action/duels, dialogue/negotiation, group dialogue/council, crafting/building/repair, travel/traversal, reveal/discovery, emotional performance, aftermath/consequence and environment-driven action. Dialogue and non-dialogue action have different duration rules.

For every subcategory specify:
- narrative purpose and selection trigger;
- when not to use it;
- required script/shot metadata;
- scene/shot design, shot sizes, lens, camera, composition and screen direction;
- character, prop, environment and secondary motion;
- lighting, atmosphere, material and palette rules;
- duration guidance and evidence status;
- Blender scene strategy and reusable asset requirements;
- render profile/optimization and relative cost category;
- audio interaction and continuity;
- QA assertions, failure modes and recovery;
- examples mapped to researched scene archetypes.

Keep the research report's 20 scene archetypes as a higher-level narrative taxonomy. An archetype may combine multiple lanes; never force one archetype into one lane by name alone.

## 6. Shot Specification contract

Design one typed, versioned Shot Specification contract only after tracing current schema evolution. Avoid a huge untyped JSON blob and avoid duplicating existing contracts.

Evaluate repository-compatible dataclasses/Pydantic plus JSON Schema. Include:
- stable episode/sequence/scene/shot IDs;
- lane, rationale, archetype/subcategory and narrative purpose;
- factual claim references, era and asset constraints;
- characters, props, environment, asset IDs and provenance;
- shot size, camera position, lens, focus target, movement, screen direction and composition;
- subject action, action phases, facial performance and lip-sync coverage;
- environment/secondary motion;
- lighting, atmosphere, materials and palette overrides;
- duration, fps, start/end frame and audio cue references;
- render engine, resolution, quality tier, samples/TAA, denoise, scale and upscale policy;
- continuity references and QA assertions/severity;
- estimated/actual GPU time, cost, retries, cache key and provenance.

Specify validation, defaults, migrations, compatibility, invalid-input behavior and examples. Recommend exact versioning only after auditing current contracts.

## 7. Architecture and implementation plan

Evaluate these candidate responsibilities; do not create every class by default:

- VisualProductionOrchestrator
- ShotSpec / ShotPlan
- VisualLanePlanner
- SceneArchetypeRegistry
- ShotDesigner
- InkChronicleStyleResolver
- AssetLibrary / AssetResolver
- BlenderSceneBuilder
- BlenderRenderAdapter
- RenderProfileSelector
- RenderCache
- RenderJobPlanner / RenderJobRunner
- CostEstimator / CostLedger
- UpscaleAdapter
- CompositorAdapter
- TimelineAudioBridge
- VisualContinuityChecker / VisualQA
- AssetBuildPipeline
- BenchmarkHarness

For each retained/new/adapted component provide responsibility, exact owning package/path, key methods/signatures, inputs/outputs, state ownership, dependencies, failure behavior, tests, and status (EXISTS / PARTIAL / PROPOSED / NOT IMPLEMENTED). Every class must have a distinct responsibility. Prefer extending existing abstractions over parallel subsystems.

Show the end-to-end target flow:
approved story/script and narration/dialogue timing → screenplay spine / film shots → visual intent and lane allocation → archetype and shot design → asset/world resolution → Blender scene build → lane-specific render profile → headless Blender render/frame cache → existing assembly/audio/FFmpeg mux → visual/timing/style/continuity/cost QA → creator review.

Mark every missing stage as NOT IMPLEMENTED. This is a target flow, not evidence that the pipeline already exists.

## 8. Cost, provider and benchmark decision

Treat US$10–15 as a target to test, not a promise. Compare like-for-like 12-minute and 15-minute episodes at 2560×1440 / 24 fps and 10/30/60 runtime.

Separate:
- GPU render time;
- boot/setup/warm-up;
- scene preparation and transfer;
- storage and egress;
- failed frames and retries;
- upscale/compositing;
- one-time asset creation and library setup;
- narration, music, development and human authoring/review.

Report both cash cost per episode and amortized recurring cost after asset reuse. Compare:
1. Local M4 Pro / Apple Silicon Blender preview and final-render suitability.
2. Vast.ai marketplace NVIDIA GPUs, including low and median offers, storage/egress and host reliability.
3. RunPod Community and Secure alternatives.
4. SheepIt as optional, non-guaranteed supplementary capacity.
5. EEVEE plus culling, instancing, frame cache and selective full-resolution hero shots.
6. Native 1440p versus 75%/67% render scale plus tested upscale and line-art stability.

Benchmark at least three representative scenes: character/dialogue close-up, interior/establishing tableau and large battle/tactical scene. Use local M4 Pro and at least one cloud NVIDIA GPU, ideally two, with at least three repeats. Record Blender version, scene complexity, settings, frame time, peak memory, output size, visual defects, wall time and actual bill. A cost pass is invalid if visual quality fails.

Use current primary sources for current prices, hardware specs, Blender version/engine features, marketplace conditions and license terms. Include source date, exact claim and URL. Distinguish measured / vendor claim / estimate / hypothesis. Do not reuse unsupported seconds-per-frame claims from research as measured facts. Do not start paid GPU/API jobs.

## 9. Asset system, licensing and style acceptance

Assess reusable humanoid meshes, rigging, retargetable cycles, hand/face rigs, shape keys, visemes, costume layers, era variants, modular props/architecture, terrain, foliage, crowd instances, lighting/camera rigs, shot templates and Geometry Nodes.

For each source/library assess:
- license and commercial-use permissions;
- attribution, redistribution and derivative restrictions;
- file formats, topology, rig compatibility and dependencies;
- provenance, version/hash, style-bible version and approval;
- import/cleanup/retopology/rigging/LOD/material normalization cost;
- risks of inconsistent proportions, line weight, textures and facial identity.

Define a visual acceptance matrix for at least: character close-up, council/interior, outdoor environment, large battle and HELPER map/chart. All must look like the same illustrated universe. Explicitly test line integrity, temporal flicker, identity, costume/material consistency, composition, readability and motion.

## 10. Repository TODO and artifact cleanup

Scan TODOs across the whole final branch and relevant source branches. Classify each:
- CURRENT / KEEP
- RELEVANT / REWRITE AS WORK PACKAGE
- SUPERSEDED
- DUPLICATE
- UNVERIFIED
- HISTORICAL / ARCHIVE
- REMOVE ONLY AFTER CALLER AND TEST PROOF

For every proposed removal record path/symbol, reason, active caller check, test evidence and replacement/supersession reference. Do not delete active code, tests, research or decision history. Do not copy generic Master Mold TODOs into unrelated files. Each future code TODO must have a stable ID, owner, intended behavior, dependency, contract impact, test and acceptance criteria.

## 11. Complexity estimator and task sizing — mandatory early gate

The previous instruction asks to use the repository's existing task-complexity estimator. Do not assume one exists.

1. Search the full repository, `CLAUDE.md`, `.claude/`, skills, scripts and task-planning docs for the actual estimator or documented sizing method.
2. If found, identify its exact path/name/version and use it for every Opus work package. Show inputs and outputs.
3. If no estimator exists, state **NOT FOUND** with the search scope and evidence. Do not invent a replacement or pretend a generic estimate is the repository's estimator.
4. In that case, provide a transparent dependency/effort/risk breakdown using clearly labelled estimates, but make the missing estimator a named Creator Decision Gate item only if the creator must choose a sizing standard. Otherwise recommend a minimal temporary method and state why.
5. Resolve this gate before producing the final task breakdown, not as a footnote.

## 12. One authoritative roadmap — no document sprawl

Create exactly one primary deliverable:

`docs/architecture/INK_CHRONICLE_OPUS_IMPLEMENTATION_ROADMAP_2026-11-04.md`

Do not create multiple overlapping architecture, visual grammar, schema, TODO, cost and decision documents. Put all required detail into this roadmap, using appendices/tables where appropriate. Existing documents remain evidence and historical context; link to them rather than copying them wholesale.

The roadmap must contain, in this order:
1. Executive recommendation and final verdict.
2. Scope, creator targets and evidence labels.
3. Branch reconciliation and exact HEAD/ancestry/unique-commit summary.
4. Verified current architecture and code-path diagram.
5. CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION.
6. Complete decision/supersession matrix.
7. Full 10/30/60 visual grammar and 20-archetype mapping.
8. Independent 70/30 spoken-word model and exact rule/code/test changes.
9. Ink Chronicle style system, world bible and asset architecture.
10. Typed Shot Specification contract and migration.
11. Minimal high-level module/class tree with responsibilities and APIs.
12. Provider alternatives, cost model and reproducible benchmark protocol.
13. QA strategy, tests, visual acceptance criteria and failure handling.
14. TODO disposition register.
15. Dependency-ordered implementation phases and Opus task packages.
16. Risk register, rollback and stop/go gates.
17. Consolidated Creator Decision Gate.
18. Opus launch checklist and OPUS READY / OPUS BLOCKED verdict.

Every work package must specify:
- ID and title;
- objective and non-goals;
- prerequisite packages;
- exact paths to add/change/remove;
- existing abstractions to reuse;
- detailed implementation sequence;
- API/schema/contract impacts;
- tests and commands;
- acceptance criteria;
- risks and rollback;
- estimated complexity/effort and confidence;
- parallelization boundaries and integration owner.

Avoid circular dependencies. Identify the critical path. Use the actual existing task-complexity estimator if it exists.

## 13. Decision closure rules

For every decision, use this record:
- Decision ID;
- current state and evidence;
- alternatives considered;
- selected recommendation;
- why it wins;
- trade-offs and rejected alternatives;
- confidence;
- verification/benchmark required;
- exact pass/fail threshold;
- downstream files, contracts and tests;
- approval state: CREATOR-APPROVED / RECOMMENDED / NEEDS-CREATOR-APPROVAL / BLOCKED.

Do not leave open-ended wording such as “TBD”, “to be decided by Opus”, “investigate later” or “choose the best option.” Replace it with a recommendation and a bounded gate. If a choice genuinely requires creator authority, place it in the single consolidated Creator Decision Gate and state why Fable cannot decide it.

The Creator Decision Gate must be concise and actionable. For each item provide:
- exact question;
- Fable's recommended default;
- alternatives and consequence;
- whether the answer blocks Opus;
- exact answer format.

Do not ask the creator to approve dozens of low-level implementation details. Fable must decide technical details within the approved targets. Only genuine product, budget, visual-identity or risk-tolerance decisions belong to the creator.

## 14. Safety and execution boundaries

During this task:
- No implementation of renderer, scene builder, asset pipeline, production classes or runtime routes.
- No paid API calls, GPU jobs, pod starts, render jobs or asset-generation jobs.
- No production provider setting changes.
- No changes to `main` or production branches.
- No force-push, reset, destructive merge, branch deletion or history rewrite.
- No deletion of active code, tests, research or decision history.
- No claim that Blender is production-ready based only on the PoC.
- No claim that a future cost target has been achieved without measured evidence.

Allowed changes on the ONLY working branch:
- create/update the single authoritative roadmap;
- update `docs/INDEX.md` only to add or correct the roadmap link if required;
- update this prompt only if a contradiction is discovered, preserving the task's scope;
- commit these documentation-only changes to the designated branch.
Do not modify runtime code or tests in this planning phase.

## 15. Blender PoC — evidence boundary

The existing isolated PoC is a five-second Blender EEVEE scene render at 1280×720 / 24 fps. Its README explicitly does not prove:
- AI mesh conversion;
- production character rigging;
- facial animation or lip-sync;
- final Ink Chronicle visual quality;
- production render cost;
- compatibility with existing episode contracts.

Treat it as a Blender installation/scene/render smoke test only unless the branch contains additional verified evidence. Inspect the actual source, workflow and generated artifacts. Record what passed, what failed, what was not tested and the next bounded PoC needed. Do not promote the PoC to production feasibility proof.

## 16. Research quality and source discipline

Use the existing research report as an index and evidence source, not as unquestionable truth. Revalidate important technical claims against current primary sources:
- Blender official manual/API/release notes;
- official provider pricing and terms;
- official asset-library licenses;
- official format/tool documentation;
- source repositories and maintenance history.

For each external source record title, publisher, URL, publication/update date, access date, exact claim supported and confidence. Separate:
- VERIFIED REPO FACT
- VERIFIED EXTERNAL FACT
- CREATOR-APPROVED REQUIREMENT
- MEASURED RESULT
- VENDOR CLAIM
- ESTIMATE
- HYPOTHESIS
- OPEN CREATOR DECISION

Include negative findings. If a class, schema, caller, test, benchmark, price, license or estimator does not exist or cannot be verified, say so.

## 17. Final quality-control pass

Before declaring complete:
1. Re-read the entire roadmap against this prompt.
2. Confirm every creator target is preserved exactly.
3. Confirm visual runtime and spoken-word ratios remain separate.
4. Confirm every conflict has a disposition and exact migration.
5. Confirm every work package has paths, dependencies, tests, acceptance criteria, risks and rollback.
6. Confirm no duplicate architecture or parallel source of truth is proposed without evidence.
7. Confirm all branch-only work was inspected and dispositioned.
8. Confirm the Blender PoC is not overstated.
9. Confirm all cost and performance claims are correctly labelled.
10. Confirm the task-complexity estimator was found and used, or explicitly reported NOT FOUND.
11. Confirm the Creator Decision Gate is consolidated and contains only genuine creator decisions.
12. Confirm `docs/INDEX.md` links to the one authoritative roadmap.
13. Confirm only documentation files changed.
14. Report exact branch, HEAD SHA, changed files, commit(s), safe checks run and checks not run.
15. End with exactly one of:
   - **OPUS READY — creator decisions resolved; no blocking unknowns remain.**
   - **OPUS BLOCKED — list only the specific creator answers or evidence gates that prevent launch.**

Do not start Opus. Do not implement. Deliver the roadmap and wait for the creator's explicit launch approval.
