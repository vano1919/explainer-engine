# Ink Chronicle Visual Production Direction — 2026-11-04

> **CREATOR-APPROVED NEW DIRECTION — HIGH PRIORITY.** This records the creator's explicit decision. It intentionally conflicts with existing decisions, rules, schemas, validators, prompts, TODOs and documentation. Treat those conflicts as required migration work. This is not a claim that runtime behavior has already changed.

## 1. Final goal

Build a cost-efficient, repeatable production system for one consistent visual universe: **Ink Chronicle**.

- Final visual language: real 3D geometry, characters, props and environments rendered as a cinematic illustrated / graphic-novel world.
- Blender is the authoritative source of final visual pixels. EEVEE is the default candidate; Cycles is an exception requiring per-shot justification.
- Long-form master target: **2560×1440, 24 fps**. This is QHD/1440p, commonly called 2K in creator discussion.
- Recurring render/compute target: **US$10–15 per finished 12–15-minute episode**, after reusable assets and infrastructure exist. This is an unproven target, not a measured result.
- Minimize recurring GPU cost without sacrificing style consistency, readable action, animation quality, factual clarity or continuity.
- Preserve compatible research, story, narration, voice, timing, audio, QA, approval, spend-guard, asset-provenance and FFmpeg delivery systems. Do not replace them merely because Blender is introduced.

## 2. Independent ratios — never conflate them

### 2.1 Visual runtime allocation: 10 / 30 / 60

Measured by final runtime, not shot count, frames, assets, narration words or API calls.

| Lane | Target | 12 min | 15 min | New production meaning |
|---|---:|---:|---:|---|
| HELPER | 10% | 72 s | 90 s | Deterministic explanatory graphics: maps, timelines, charts, counters, diagrams, labels and evidence callouts. Use Python/vector tools and/or Blender spatial graphics. |
| STILL | 30% | 216 s | 270 s | Blender-rendered tableaux, still compositions, inserts and 2.5D scenes. May include camera motion, parallax, animated light, particles, environmental motion and selected object motion; full character-body animation is not required. |
| VIDEO | 60% | 432 s | 540 s | Fully animated or materially moving Blender scenes: character acting, dialogue coverage, battles, travel, crafting, reveals, environment action and aftermath. |

**Critical reinterpretation:** Existing D-93 describes VIDEO as LTX-generated video, STILL as Python moving image layers and HELPER as Python graphics. That old implementation mapping is superseded by this new direction. The 10/30/60 runtime allocation remains, but all three lanes must use the same Ink Chronicle visual grammar. VIDEO means Blender animation; STILL means Blender-rendered tableau/2.5D; HELPER means deterministic graphics or Blender spatial graphics. External generative video must not produce final shots in a competing style.

The old ±5 percentage-point tolerance recorded with D-93 is not automatically approved for the new lane definitions. Audit it and recommend retain/change/remove. Do not alter target shares without creator approval.

### 2.2 Spoken-word allocation: 70 / 30

Measured by audible spoken words, independently of visual runtime.

- Narrator: nominal target 70%.
- Voiced character dialogue: nominal target 30%.
- Exclude voiced=false lines, music, ambience, Foley, SFX and silence.
- D-95 currently records a 70–80% narrator / 20–30% character dialogue range with a 75/25 midpoint. The new creator instruction is 70/30. Flag this explicit conflict; propose a canonical decision-log update and test/schema migration. Clarify whether 70/30 is a hard target or nominal split with tolerance before enforcement.
- Visible lip-sync should cover only the readable spoken beat. Reaction shots, inserts and off-screen dialogue remain valid. Do not apply universal short shot caps to non-dialogue action. Revalidate D-95's non-dialogue 15-second planning ceiling against Blender.

### 2.3 Keep three separate measurements

1. Visual lane share = final runtime seconds in HELPER / STILL / VIDEO.
2. Spoken-word share = audible narrator words vs voiced character words.
3. Shot duration = editorial decision based on action, comprehension, performance and rhythm.

They require separate schema fields, validators, reports and tests.

## 3. Shared Ink Chronicle visual grammar

One coherent authored style across every lane and shot:

- Stylized 3D geometry with an illustrated / graphic-novel final appearance.
- Bold deliberate ink contours and ink-shadowed silhouettes.
- Painted limited-plane materials and textured backgrounds; no generic photorealistic/PBR appearance as the default final look.
- Adult human proportions; expressive faces, hands and posture without childlike/chibi proportions.
- Controlled palette, motivated key lighting, readable value grouping and consistent atmospheric depth.
- Consistent camera, lens, composition, line weight, material response, lighting and post-processing.
- Era-specific materials, costumes, architecture, props and palette may change; the underlying drawing grammar may not.
- No imitation of named living artists, studios, films or protected characters. No unlicensed assets.
- Text, maps, labels, numbers and diagrams remain crisp and deterministic; do not rely on AI-generated text.

Current look_v2.json bans terms such as "3d render" and "realistic"; world/bible.json bans a 3D-render look. The intended distinction is: **3D geometry is allowed and expected as the production medium; a generic photorealistic or raw 3D-render aesthetic is not the target.** Rewrite prompt policy and validators after audit. Do not remove the anti-photorealism requirement.

## 4. Visual grammar and shot-design library

A lane is not a shot type. A scene archetype may use several lanes and a sequence of shot sizes.

### 4.1 HELPER — 10%

- H1 Strategic / route / territory maps: terrain, front lines, routes, supply, geography; top-down or oblique 3D terrain, animated arrows and controlled labels.
- H2 Timeline / chronological stepper: dated nodes, eras, divergence points and event sequences.
- H3 Quantitative charts: bar, line, step and comparison charts; counters, ledgers and resource depletion.
- H4 Cutaway / process / network diagrams: fortification structure, machine/weapon mechanics, command hierarchy and causal chains.
- H5 Comparison / evidence callouts: before/after, faction comparison, sourced fact emphasis, object/claim annotation.

Cognitive limits and legibility are part of the contract. Avoid crowded maps, excessive labels/highlights, unreadable text or unsupported precision. Research-derived limits (e.g. 3–4 map labels, 3–5 timeline nodes, 4 bars / 2 lines) are hypotheses until source-checked and user-tested; do not hard-code them prematurely.

### 4.2 STILL — 30%

- S1 Establishing tableau: era, city, fortress, palace, landscape, battlefield.
- S2 Character tableau: status, isolation, fear, resolve, moral choice.
- S3 Group tableau: council, assembly, commanders, crowds.
- S4 Detail / macro inserts: letter, seal, sword, hand, map, artifact, mechanism.
- S5 Atmospheric / aftermath tableau: ruins, smoke, rain, snow, dust, dawn, empty throne.
- S6 Visual contrast / match composition: before/after, two powers, plan vs consequence, two eras.
- S7 Freeze / held tableau: pause on a readable composition while narration explains its meaning.

Allowed motion: controlled dolly/pan/tilt, multi-plane parallax, focus changes, animated light, fog cards, particles, cloth/flag/fire/water and selected object motion. Do not fake major perspective changes with flat planes; use true 3D geometry when the camera materially moves around an object.

### 4.3 VIDEO — 60%

- V1 Large-scale action: battle, siege, army formations, tactical maneuvers.
- V2 Character action: duel, chase, physical confrontation, gestures, prop use.
- V3 Dialogue / negotiation / argument: master two-shot, OTS, shot-reverse-shot, reaction and insert coverage.
- V4 Group dialogue / assembly: leader, factions, listening reactions and crowd staging.
- V5 Crafting / building / repairing: hands, tools, materials and transformation.
- V6 Travel / traversal: marching, riding, sailing, climbing and environmental journey.
- V7 Reveal / discovery: threat, army, object, location or evidence reveal.
- V8 Emotional performance: fear, realization, grief, anger, hesitation and resolve.
- V9 Aftermath / consequence: damage, loss, victory, retreat and silence.
- V10 Environment-driven action: storm, fire, collapse, flood, weather and moving architecture.

Action animation should use readable staging and, where appropriate, anticipation → action peak/contact → settle/follow-through, including secondary motion. Do not force every action into one template.

## 5. Shared cinematography and editing grammar

Reusable controls across lanes:
- Shot sizes: EWS, WS, MWS, MS, MCU, CU, ECU, OTS, insert, POV, profile and silhouette.
- Lens/perspective: focal length, camera distance, depth of field and perspective distortion.
- Camera moves: locked-off, dolly, pan, tilt, crane, tracking, orbit, controlled handheld-like motion, top-down, lateral tracking and motivated whip-pan.
- Composition: staging, silhouette readability, foreground/midground/background, leading lines, symmetry, negative space and focal hierarchy.
- Lighting: motivated key, fill/negative fill, rim, chiaroscuro, practical sources, atmosphere and shadow continuity.
- Animation: anticipation, timing/spacing, arcs, follow-through, overlapping action, secondary motion, weight, contact and foot locking.
- Editing: hard cut, cut on action, match cut, J-cut, L-cut, reaction cut, insert cut, cross-cutting, smash cut, motivated wipe, motivated dissolve, fade and held frame.
- Continuity: 180-degree axis, eyeline, screen direction, prop/wardrobe, identity, light direction and geography.
- Rhythm: shot length follows comprehension and dramatic intent, not a fixed timer. Research numbers are guidelines until validated, not universal hard rules.

## 6. Scene archetypes and lane routing

Preserve the research report's 20-archetype library as the narrative/production taxonomy, but audit every archetype for Blender. Each archetype must define narrative purpose, audience information/emotion, suitable lanes and rationale, shot sequence, camera/lens/movement/composition, character/environment action, lighting/palette/atmosphere, audio intent, assets/reuse, render profile, continuity and QA/failure conditions.

Do not map one archetype to exactly one lane. A battle may combine a HELPER route map, a STILL establishing tableau and VIDEO action shots while preserving continuous geography and one style.

## 7. Render-cost and quality strategy

The recurring target is US$10–15 per 12–15-minute episode. It is a measured target only after benchmark.

Investigate and compare:
- Blender EEVEE default; Cycles only for justified exceptions.
- Native 2560×1440 vs 75% render scale (1920×1080) followed by conservative upscale; hero close-ups/line-critical shots at native 1440p.
- Preview, look-dev, final and hero-final tiers.
- Simplified shadows, bounce limits, texture resolution, camera/distance culling, instances/Geometry Nodes, linked assets and reusable animation cycles.
- Content-addressed frame/shot caching; incremental rerender; chunked/headless rendering; resumable cloud jobs.
- Local Apple Silicon M4 Pro 24GB unified memory for preview and selected scenes, benchmarked rather than assumed.
- Low-cost cloud NVIDIA GPUs and community render farms; compare cost per accepted final minute, not hourly rate alone. Interruptible instances require resumability and durable outputs.
- Temporal-consistent conservative upscaling; test flicker and line integrity. Avoid creative hallucination on faces, costumes and ink lines.
- Add text/maps/labels deterministically, preferably after upscale where appropriate.
- Cost model includes boot/setup, upload/download, storage/egress, retries, failed jobs, idle billing, upscale, compositing and actual render time. Separate one-time asset creation and human authoring time from recurring compute.

Benchmark at least three scenes: character/dialogue close-up, interior/establishing tableau, large battle/Tactical Diorama. Measure M4 Pro and at least two plausible cloud GPU classes. Record Blender version, scene complexity, resolution, samples/TAA, output codec, wall time, memory, quality defects and actual bill. A budget pass requires representative full-episode extrapolation plus uncertainty and contingency.

## 8. Preserve / change / remove — initial direction

**Preserve unless evidence proves incompatibility:** research dossier, evidence/claim map, story engine, script approval gates, narration/ElevenLabs, timeline and 24 fps long-form policy, audio mixing, QA, FFmpeg assembly/mux, asset provenance/licensing, versioned World Bible, cloud spend caps, job ledger, self-stop, watchdog, durable output and recovery protections.

**Replace or redesign:** final visual generation route; old lane definitions that bind VIDEO to LTX, STILL to Python-moving AI pictures and HELPER to Python only; prompt/style bans that accidentally prohibit 3D geometry rather than photorealistic appearance; old schemas, shot planners, validators and TODOs enforcing incompatible assumptions. Renderer/scene-builder/keyframe stubs must be redesigned for Blender, not blindly implemented according to imported LTX/Qwen TODOs.

**Remove only after reference/dependency audit:** retired 2D puppet rig as production dependency; superseded TODO blocks, duplicate migration plans, stale LTX/Qwen routing instructions and old conflicting ratio descriptions. Preserve historical records where useful. Never delete working code, tests or evidence just because it is old.

## 9. Acceptance criteria for implementation

1. All final visuals use Ink Chronicle; no competing AI-video style.
2. Runtime accounting measures HELPER/STILL/VIDEO seconds separately from narrator/dialogue words.
3. 10/30/60 targets are configurable and reported; tolerance is documented.
4. Spoken-word split uses approved 70/30 target and excludes non-voiced lines and non-speech audio.
5. Shot specs encode narrative purpose, archetype, lane, camera, lens, action, duration, continuity, render mode and QA.
6. Blender scenes render headlessly and deterministically; failed jobs resume without rerendering unchanged completed frames.
7. Reusable characters, props, environments, rigs, animation cycles, materials, lighting and cameras have provenance/versioning.
8. HELPER graphics are legible/accurate/deterministic; STILL tableaux have meaningful controlled motion; VIDEO shots have readable action/performance.
9. A 12–15-minute episode is costed transparently; measured recurring render/compute is within $10–15 or a documented gap analysis is returned.
10. Existing story/audio/approval/safety/cost/delivery gates pass or are replaced by equivalent verified tests.
11. No paid GPU/API run, destructive deletion, production publish or main merge without existing explicit approval gates.

## 10. Conflict authority

This is a new creator-approved design direction. Where it conflicts with D-93, D-95, D-70, D-41, BP rules, schemas, look_v2.json, world/bible.json, film_shots.py, variant_plan.py, tier_router.py, generator.py, scene_builder.py, keyframe logic, tests or docs, record the conflict explicitly.

Create a supersession matrix: old rule/ID/file/test → reason incompatible → new rule → code/schema/test/doc migration → risk → approval state. Update canonical decisions with new IDs and explicit supersession references. Never erase history. New decisions supersede old ones only within explicit scope.

This authorizes planning and architecture work only. It does not authorize paid runs or production rollout.
