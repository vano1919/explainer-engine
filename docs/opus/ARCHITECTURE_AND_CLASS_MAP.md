# Architecture and High-Level Class Map

**Status:** proposed target architecture; every class below is `TODO / NOT IMPLEMENTED`.  
**Purpose:** define responsibilities for Opus; do not create empty classes solely to match this list.

## 1. Current pipeline to preserve and extend

The current base branch already has meaningful infrastructure. Opus must inspect exact code and actual callers before moving responsibility.

| Existing area | Verified current role / evidence | Target treatment |
|---|---|---|
| `scripting/film_shots.py`, `variant_plan.py` | Shot/lane authoring, D-93 lane shares and D-95 speech rules are present in the repository's current specs/validators. | KEEP the existing source of shot/story intent; revise only the fields/rules needed for Blender. |
| `edit/router.py` | Currently routes `KEYFRAME_LTX`, `DIALOGUE_CU`, `ATMOS_BROLL`, `STILL_HOLD`, `MAP`, `COMPENSATOR`; checks pinned keyframe/video models and audio spine for dialogue. `DRAMA_BLOCKED_3D` is currently refused under D-89/A2. | CHANGE lane routing to Blender scene types after schema and caller audit. Remove LTX requirements from the primary visual route only after replacement adapters pass. |
| `edit/visual_compensator.py`, `edit/tableau.py`, `maps/`, `hud.py` | Existing map/HUD/tableau archetypes and deterministic graphic logic. | KEEP reusable data, drawing, timing, archetype and validation logic; decide which render output responsibilities must move into Blender. |
| `production/assemble.py` | Current assembly path includes Python/NumPy/Pillow/FFmpeg frame/video handling and audio muxing. | KEEP audio, timing, chunk joining, output packaging and FFmpeg where useful. Audit its exact pixel-generation path before demoting or removing it. |
| `audio/spine.py`, sound director, voice modules | Existing audio clock, dialogue windows and sound mix contracts. | KEEP; integrate Blender-rendered shots against the existing clock. Do not create a parallel voice/audio chain. |
| `core/contracts.py`, `core/shot_cache.py`, `core/ledger.py`, `config/spend_caps.json` | Versioned JSON contracts, shot hashing/cache, one money ledger and cost caps. | KEEP as foundations; extend contracts and cache inputs rather than duplicate them. |
| `world/bible.py`, `world/bible.json`, `look_v2.json`, `eras.json`, `design/palette.json` | Versioned visual-world references and palette inputs. | KEEP versioning/provenance; propose a Blender-specific Ink Chronicle style contract and approved style anchors. |
| `assets/library.py`, asset schema | Reusable asset records exist, but current extension/kind support is raster-oriented. | CHANGE to support Blender project/collection, model, rig, animation, material, texture and dependency bundles. |
| QA frame review, identity, output/audio validators | Existing quality and review gates. | KEEP; add Blender camera/style/geometry, missing frame, flicker and render-cost evidence. |

## 2. Target flow

```text
Story + approved script + voice/timing contracts
                |
                v
Existing screenplay_spine / film_shots
                |
                v
VisualPlanCompiler
  - intent -> lane -> scene archetype
  - 10/30/60 runtime accounting
                |
                v
ShotDesignPlanner + TechniqueSelector
  - shot size, lens, composition, blocking, camera path
  - animation, environment, light, editing and sound cues
                |
                v
WorldBibleResolver + AssetResolver
  - approved Ink Chronicle style / reusable 3D assets
                |
                v
BlenderSceneBuilder
  - scene collections, characters, props, geometry, camera, lighting
                |
                v
RenderProfileSelector + RenderBackend
  - EEVEE primary candidate / selective Cycles / preview modes
  - local / cloud / community farm adapters
                |
                v
RenderCache + RenderOutputValidator
                |
                v
Existing production assembly + audio mix + FFmpeg mux
                |
                v
Existing QA / review bundle / creator approval
```

This flow is a target, not an implemented pipeline.

## 3. Minimal proposed package structure

Opus should simplify this structure if an existing module can own a responsibility without becoming tangled.

```text
explainer_engine/
  visual/
    __init__.py
    plan.py                 # VisualPlanCompiler, LaneBudgetAllocator
    shot_design.py          # ShotDesignPlanner, TechniqueSelector
    archetypes.py           # VisualArchetypeRegistry
    contracts.py            # thin adapters over core/contracts.py (only if needed)
  blender/
    __init__.py
    project.py              # BlenderProjectResolver
    scene_builder.py        # BlenderSceneBuilder
    style.py                # InkChronicleStyleEngine
    camera.py               # CameraRigBuilder
    characters.py           # CharacterRigAdapter, PerformanceComposer
    data_visuals.py         # BlenderDataVisualBuilder
    render.py               # BlenderBatchRenderer
    profiles.py             # RenderProfileSelector, SceneOptimizer
    cache.py                # BlenderRenderCache adapter over core/shot_cache.py
    backends.py             # RenderBackend protocol + Local/Cloud adapters
    cost.py                 # RenderCostEstimator
    validation.py           # RenderOutputValidator
```

Do not add every named class automatically. Keep the smallest number of abstractions that give clear ownership, test seams and replaceable render providers.

## 4. Class responsibility map — proposed / not implemented

### Visual planning layer

| TODO class | Responsibility | Inputs | Output | Must not do |
|---|---|---|---|---|
| `VisualPlanCompiler` | Convert existing screenplay/shot intentions into a derived visual plan. | `screenplay_spine`, `film_shots/2`, approved episode rules | `visual_plan/<N>` | Write or rewrite story/script content. |
| `LaneBudgetAllocator` | Measure and allocate 10/30/60 by visual timeline duration; report tolerance. | Shot intervals, target shares, mixed-lane ranges | lane assignment/budget report | Derive speech ratio from visual time. |
| `VisualIntentResolver` | Determine what the audience must understand/feel/see for each beat. | Beat intent, claim map, scene context | visual intent / purpose | Literal duplicate every narration sentence in an image. |
| `ShotDesignPlanner` | Select shot size, composition, lens, camera move, blocking, action phase and coverage. | Visual intent, scene geography, continuity | shot design | Randomly rotate techniques without a narrative reason. |
| `TechniqueSelector` | Choose eligible techniques from the craft catalogue based on beat and cost constraints. | Visual intent, archetype, style, camera constraints | technique recipe IDs | Invent new craft rules at render time. |
| `VisualArchetypeRegistry` | Define scene types, lane eligibility, shot sequences, motion, light, audio cues, QA and cost profile. | Curated archetype catalogue | archetype definitions | Hardcode all story content. |

### Blender scene and style layer

| TODO class | Responsibility | Inputs | Output | Must not do |
|---|---|---|---|---|
| `WorldBibleResolver` | Resolve approved Ink Chronicle style, palette, era and version hashes. | World Bible + episode rules | resolved style/world package | Silently change a style version. |
| `AssetResolver` | Find and verify 3D assets, rigs, materials, animation and dependencies in the existing library. | Asset IDs, required tags, license/provenance | immutable asset manifest | Import random assets without license/provenance. |
| `BlenderProjectResolver` | Resolve the pinned Blender binary/version, render engine and environment. | Render profile/config | reproducible Blender invocation | Depend on an interactive GUI session. |
| `BlenderSceneBuilder` | Build one renderable shot scene from a shot spec and reusable assets. | Shot design, asset manifest, style | .blend scene or buildable scene spec | Own narrative choices or audio mixing. |
| `InkChronicleStyleEngine` | Apply shared NPR materials, outline passes, palette, texture scale and light rules. | Style Bible + assets | normalized style on scene objects | Permit each asset pack to keep a contradictory visual style. |
| `CameraRigBuilder` | Build locked/pan/tilt/dolly/crane/tracking/orbit/dolly-zoom camera rigs. | Camera plan, target, scene geometry | Blender camera/action | Substitute a digital zoom for a physical dolly without declaring it. |
| `CharacterRigAdapter` | Normalize rig interface and map reusable body/face/viseme controls. | Asset rig profile, animation clip, voice timing | rigged character action | Assume Mixamo supplies advanced face acting. |
| `PerformanceComposer` | Compose body actions, NLA clips, gestures, gaze, blink, breath and facial performance. | Action intent, timing, rig capabilities | baked character animation | Use lip-sync alone as a full acting system. |
| `BlenderDataVisualBuilder` | Convert deterministic map/chart/timeline data into Blender curves, text, meshes and camera-ready helper scenes. | Sourced data + helper spec | Blender helper scene | Invent facts, labels or geometry measurements. |

### Render and delivery layer

| TODO class | Responsibility | Inputs | Output | Must not do |
|---|---|---|---|---|
| `RenderProfileSelector` | Choose preview/lookdev/final/hero profile per shot based on quality and budget. | Scene complexity, lane, quality target, measured speeds | render profile | Treat an unmeasured seconds/frame number as fact. |
| `SceneOptimizer` | Apply instancing, camera/distance culling, simplify, texture caps, volume/shadow reductions and selective render scale. | Scene + profile | optimized render scene | Change visible composition or line-art quality without QA. |
| `BlenderBatchRenderer` | Run headless frame-range renders, report progress and recover incomplete ranges. | .blend, frames, render profile | image sequence + manifest | Launch uncontrolled background jobs. |
| `RenderBackend` | Define a replaceable rendering-provider interface. | Render job manifest | submitted / retrieved frames | Mix provider-specific pricing into scene-building code. |
| `LocalBlenderBackend` | Run on available local hardware, initially for Preview and benchmark. | Local machine | rendered frames | Assume Mac performance equals NVIDIA. |
| `CloudBlenderBackend` | Execute on selected cloud GPU provider with approved cap. | Cloud job plan | frames + billing evidence | Rent a GPU without an itemized approved budget. |
| `RenderCostEstimator` | Estimate/measure compute + setup + storage + egress + retry cost per episode. | Measured job speeds + current price quote | cost ledger rows | Use global market low as a guaranteed rate. |
| `BlenderRenderCache` | Cache by scene/asset/style/Blender version/render profile/engine settings hash. | Render manifest | cache hit/miss and reusable frames | Reuse outputs after dependency changes. |
| `RenderOutputValidator` | Verify dimensions, fps, frame count, missing/black/frozen frames, color/alpha/codec and render manifest. | Frame sequence + render manifest | QA report | Replace editorial review or style review. |

## 5. Contracts and artifacts — TODO

Propose new versioned contracts only where the current contracts cannot express the required state.

Potential artifacts:
- `visual_plan/<N>`: derived lane and shot-intent plan with 10/30/60 budget.
- `shot_design/<N>`: derived camera, composition, action, lighting and technique plan.
- `blender_scene_manifest/<N>`: scene asset/style references, build version, dependencies and hashes.
- `blender_render_manifest/<N>`: engine, Blender version, device, render scale, samples, frame interval, output files, measured time and cost.
- `spoken_mix_report/<N>`: narrator/dialogue word counts and actual audible seconds.

The exact names and schema versions are TODO. Reuse `film_shots/2`, `audio_spine/2`, `core/contracts.py` and current lifecycle unless a real incompatibility is demonstrated. Use JSON Schema as required by existing contracts; do not introduce Pydantic or a second contract validator.

## 6. Determinism and cache requirements

Cache key candidates:
- source shot / scene intent hash;
- shot-design hash;
- World Bible and Ink Chronicle style version/hash;
- every asset and dependency hash;
- Blender version/build;
- render engine;
- GPU/backend identity where output differences matter;
- color management and OCIO config;
- resolution, scale, frame rate, samples, volume/shadow and line-art settings;
- animation action versions and seed.

Re-render only affected frames/shots. Keep frame-range manifests so a restarted job can resume without repeating accepted work. Define whether a cache can be shared across devices; do not assume pixel-identical results across GPU vendors or engine builds.

## 7. Explicitly out of scope unless evidence changes

- Replacing the existing audio chain.
- Rebuilding the story/script/claim system.
- Replacing the spend ledger or creating a second budget system.
- Replacing FFmpeg solely because Blender has a Video Sequence Editor.
- A new autonomous multi-agent framework.
- Bulk adoption of every imported Master Mold v2.1 TODO.
