# TODO Register — Ink Chronicle Blender Pipeline

All items below are open. IDs are local to this planning package and are not official D-/BP-/CN- IDs yet.

Each TODO must retain these fields in the Opus plan and future issue/PR:
**ID | Status | Description | Evidence/current owner | Depends on | Conflict | Acceptance criteria | Decision owner**.

## A. Decisions and rule migration

| ID | Status | Description | Depends on | Conflict | Acceptance |
|---|---|---|---|---|---|
| TODO-RULE-01 | OPEN | Rewrite branch-local and eventual canonical project instructions from 2D raster-first to Ink Chronicle 3D/NPR without weakening safeguards. | Opus plan approval | CLAUDE.md / D-27 | One authoritative visual mission; old rules clearly superseded, no loss of safety rules. |
| TODO-RULE-02 | OPEN | Replace D-27 raster-kit production method with a 3D asset/style system while preserving one-world identity. | Style Bible proposal | D-27 | Before/after comparison and approved style tests. |
| TODO-RULE-03 | OPEN | Retire required Gemini/LTX final visual-generation paths; keep only asset-concept use if justified. | Blender route passes PoC | D-28 / D-78 / D-80 | Router has no unintentional LTX visual dependency. |
| TODO-RULE-04 | OPEN | Fix master terminology and pin 2560×1440 at 24 fps after benchmark. | Resolution PoC | D-30 / D-85 / D-92 | Contract, ffprobe and frame tests agree. |
| TODO-RULE-05 | OPEN | Compare local/cloud/community rendering and amend D-31 only with measured evidence. | Provider benchmark | D-31 | Measured accepted-frame cost and full bill by provider. |
| TODO-RULE-06 | OPEN | Reassign existing GPU compositor and FFmpeg responsibilities cleanly. | Full caller/data-flow audit | D-32 | No duplicate renderer and no broken audio/assembly. |
| TODO-RULE-07 | OPEN | Enable Blender scene routing and remove blanket 3D-blocked refusal only after replacement routes pass. | Contract/router migration | Blueprint A2 / D-89 | Old invalid route fails, new Blender routes pass focused tests. |
| TODO-RULE-08 | OPEN | Lift D-87's absolute no-3D-terrain restriction only for terrain-critical helper shots. | Map benchmark | D-87 | 2D map remains default; 3D terrain used only with narrative justification. |
| TODO-RULE-09 | OPEN | Preserve D-93 10/30/60 shares while replacing LTX/2D render semantics. | Lane contracts | D-93 | Runtime share validator and tests report exact seconds and tolerance. |
| TODO-RULE-10 | OPEN | Amend D-95 midpoint to 70/30; retain outer bands and speech-vs-visual independence. | Spoken-word accounting audit | D-95 | Narrator/dialogue word-count fixture passes at target and both boundaries. |
| TODO-RULE-11 | OPEN | Replace Qwen keyframe/LTX final output path with Blender scenes; determine whether AI images remain useful for asset references only. | Character/environment PoC | D-78 / D-80 | Final pixels come from approved render path; style continuity QA passes. |
| TODO-RULE-12 | OPEN | Extend World Bible and Asset Library to 3D asset provenance and reusable dependencies. | Asset schema audit | D-70 / WB rules | .blend/GLB/FBX/OBJ/texture/rig entries validate and can be resolved. |
| TODO-RULE-13 | OPEN | Keep D-85/D-92 24fps episode clock and preserve existing audio spine unless an actual incompatibility is proven. | Render adapter | D-85 / D-92 | ffprobe, contract and audio timing tests match 24fps. |

## B. Visual grammar and production design

| ID | Status | Description | Depends on | Conflict | Acceptance |
|---|---|---|---|---|---|
| TODO-VIS-01 | OPEN | Map all 20 researched scene archetypes to the 10/30/60 lanes and shot templates. | F.1 review | Existing lane/router taxonomy | No archetype is mapped by name alone; each has purpose, technique, camera, motion, light, edit and QA. |
| TODO-VIS-02 | OPEN | Build a reusable shot technique registry with deterministic selection rules. | TODO-VIS-01 | Current prompt-only / LTX-specific composition | Every shot has explicit visual purpose and explainable shot design. |
| TODO-VIS-03 | OPEN | Define the Ink Chronicle Style Bible and normalization contract. | Style PoC collage | D-27 / D-28 | Character close-up, interior, outdoor world, battle and helper have one recognizable look. |
| TODO-VIS-04 | OPEN | Define camera/lens/composition/continuity controls and a shot-size vocabulary. | Shot design contract | Existing continuity cards | Every shot has readable geography, screen direction and motivated camera. |
| TODO-VIS-05 | OPEN | Define 4-pose action, body blocking, foot contact, follow-through and weapon/prop constraints. | Character rig profile | Current motion prompt route | Representative action passes contact and continuity QA. |
| TODO-VIS-06 | OPEN | Define dialogue coverage, 180-degree axis, eyeline and reaction-shot grammar. | 70/30 + audio spine | D-95 / D-90 | 70/30 words, ≤5s visible lip-sync planning target, no ping-pong editing. |
| TODO-VIS-07 | OPEN | Define still tableaux and confirm live BP-109/BP-170 motion/hold rules. | Rule registry audit | D-93 / D-95 | STILL rules remain independent and testable. |
| TODO-VIS-08 | OPEN | Define helper maps, timeline, chart, counter, cutaway and visual-proof templates. | data-source contracts | D-87 | Sourced data, deterministic text, style-consistent final render. |

## C. Architecture and asset reuse

| ID | Status | Description | Depends on | Conflict | Acceptance |
|---|---|---|---|---|---|
| TODO-ARCH-01 | OPEN | Produce minimal package/class graph and decide which current modules own each responsibility. | CURRENT code map | Avoid parallel subsystems | Every new class has one owner, input/output and test boundary. |
| TODO-ARCH-02 | OPEN | Define Blender project versioning and headless CLI invocation. | EEVEE test | Current RunPod script architecture | Reproducible run with pinned Blender build, environment and logs. |
| TODO-ARCH-03 | OPEN | Define scene/shot/render manifests with dependency hashes. | Contracts audit | CN-/shot cache | Stale inputs invalidate exactly affected outputs. |
| TODO-ARCH-04 | OPEN | Extend asset registry for 3D formats, rigs, animation clips and dependencies. | Schema audit | Raster-only library | Full provenance/license/bible/version/dependency validation. |
| TODO-ARCH-05 | OPEN | Define character/face/viseme rig compatibility and reusable animation bank. | Character pilot | Mixamo's humanoid-only auto-rig limits | Same identity across front/side/three-quarter/OTS and repeated episodes. |
| TODO-ARCH-06 | OPEN | Evaluate Geometry Nodes instancing for armies/crowds/modular environments. | Battle PoC | Scene complexity | Memory and render time measured versus duplicated objects. |
| TODO-ARCH-07 | OPEN | Evaluate Blender NPR line-art/shading pipeline and camera-distance line-width stability. | Style PoC | look_v2 ban terms and raster style rules | Lines remain readable at wide/close scales and during camera motion. |
| TODO-ARCH-08 | OPEN | Implement a single approved Ink Chronicle style normalization layer. | TODO-ARCH-07 | mixed assets from repositories | No asset retains a contradictory look. |

## D. Rendering cost, optimization and cloud

| ID | Status | Description | Depends on | Conflict | Acceptance |
|---|---|---|---|---|---|
| TODO-COST-01 | OPEN | Define visual cash vs fully-loaded episode cost boundary. | creator budget approval | Existing cost model excludes Blender | Separate line items and honest amortization. |
| TODO-COST-02 | OPEN | Benchmark EEVEE render cost by shot archetype at 100/75/67% scale. | 3 benchmark scenes | Unverified research seconds/frame | Median/p90 seconds/frame and image QA captured. |
| TODO-COST-03 | OPEN | Compare M4 Pro, Vast 3090/4090, RunPod 3090/4090/A40/A6000 and SheepIt. | TODO-COST-02 | D-31 cloud-first | Actual cost per accepted rendered frame including setup/storage/retry. |
| TODO-COST-04 | OPEN | Build an episode-level cost estimator based on measured job_speeds and actual provider quotes. | Ledger/manifest design | Missing job speed must be UNKNOWN | No guessed price; cost report is auditable. |
| TODO-COST-05 | OPEN | Evaluate spatial upscaling vs conservative temporal upscale for line-art stability. | 100/75/67 renders | Temporal flicker / hallucination | Blind visual review and motion test pass. |
| TODO-COST-06 | OPEN | Add interruption/resume, frame-range cache and cleanup behavior to renderer. | Render backend | RunPod paid-time safety | Failed job resumes only missing frames and leaves no paid resource running. |
| TODO-COST-07 | OPEN | Evaluate SheepIt compatibility, throughput and point economics as non-guaranteed secondary capacity. | test package | queue and point rules | Optional route only; no production SLA assumption. |

## E. QA, tests and rollout

| ID | Status | Description | Depends on | Conflict | Acceptance |
|---|---|---|---|---|---|
| TODO-QA-01 | OPEN | Define style consistency QA across all lanes and shot sizes. | Style Bible | old image-based style QA | same world identity and controlled line width. |
| TODO-QA-02 | OPEN | Define geometry/camera/motion continuity checks. | Shot design schema | 2D-only QA assumptions | no broken camera axis, clipping, floating props, foot slide or missing frames. |
| TODO-QA-03 | OPEN | Define lip-sync/audio timing and 70/30 reporting. | audio spine audit | D-95 midpoint | report word share and actual voiced seconds separately. |
| TODO-QA-04 | OPEN | Extend frame review/contact sheet and output QA to Blender sequences. | renderer manifest | existing QA | no black/frozen/duplicate/missing frames; frame-to-audio sync pass. |
| TODO-QA-05 | OPEN | Write fixtures for new schemas and regression tests for old jobs. | versioned contract plan | backward compatibility | old supported jobs remain readable; invalid Blender scenes fail early. |
| TODO-QA-06 | OPEN | Run full-repo read-only audit before any paid pilot. | code implementation complete | OR-34 | audit proves no old route remains unintentionally active. |
| TODO-QA-07 | OPEN | Prepare one creator-reviewed pilot with three shot classes before full episode. | all previous gates | paid render requires OR-23 | Go / Pivot / Stop decision backed by footage and bill. |

## F. TODO annotation convention for future code

Every code TODO added by Opus must include:
- stable TODO ID from this register;
- concise problem statement;
- intended behavior;
- current owner/caller;
- dependency and contract/schema impact;
- conflict with legacy rules;
- test / acceptance criterion;
- status (`TODO / NOT IMPLEMENTED`, `IN PROGRESS`, `DONE`).

Do not paste the same generic Master Mold block into hundreds of unrelated source files. Put the detailed TODO next to the owning class/function and keep this register as the one canonical task index.
