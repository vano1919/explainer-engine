# Opus Master Task — Ink Chronicle Blender Visual Pipeline

**Status:** TODO — full Opus architecture plan required.  
**Target branch:** `opus/ink-chronicle-blender-plan-2026-11-04`  
**Base evidence branch:** `claude/master-mold-ready-2026-11-04`  
**Authority:** creator's instruction in the current conversation, 2026-11-04.

## 1. Mission

Design a production architecture that can assemble 12–15-minute historical / counterfactual explainer videos in one coherent **Ink Chronicle** visual universe at a much lower recurring cost.

The intended visual system uses real reusable 3D geometry for characters, costumes, props, architecture, terrain and environments, but renders the final image as an illustrated / graphic-novel world: controlled ink outlines, graphic value grouping, painterly surface treatment, deliberate palette, motivated cinematic lighting and a stable visual bible.

The objective is not “use Blender for everything because Blender can do everything.” The objective is to choose the cheapest production method that preserves the approved visual quality, continuity, camera control and story clarity.

The new plan must be compared with the actual current repository and must avoid importing unrelated Master Mold v2.1.0 architecture.

## 2. Creator-set target inputs

These are the target inputs for the plan. Do not silently alter them.

| Requirement | Target | How it is measured |
|---|---|---|
| Visual identity | Ink Chronicle, monostyle 3D-to-illustration | Approved visual style tests across characters, props, interiors, environments, maps and shots |
| Master output | 2560×1440, 24 fps | ffprobe + frame dimensions + job contract |
| Visual runtime | 10% HELPER / 30% STILL / 60% VIDEO | Sum of lane durations divided by total visual timeline duration |
| Visual tolerance | D-93 existing ±5 percentage points | Per-episode lane validator |
| Spoken words | 70% narrator / 30% voiced character dialogue | Audible spoken-word count; exclude `voiced:false` |
| Speech measurement | Keep it independent of visual lanes | Report narrator words, dialogue words and actual audible seconds separately |
| Visible lip-sync | 5-second maximum planning target | Applies only to shots intended to show a character visibly speaking |
| Non-dialogue action | 10–15 seconds when it benefits continuous action | Not split merely to satisfy the dialogue limit; provider or Blender constraints still apply |
| Cost objective | US$10–15 per finished 12–15-minute episode | Measured visual/render cash cost; scope must be broken into line items |
| Asset reuse | One versioned, searchable library | Every reusable 3D asset has provenance, license, style/bible version, hash and approval |
| Production | Repeatable, deterministic where practical, recoverable | Cache hit rate, render retry rate, missing-frame count and review effort |

**Resolution terminology:** 2560×1440 is 1440p/QHD. The creator calls this “2K” informally; technical docs should use 1440p/QHD to avoid resolution ambiguity.

**70/30 update:** current D-95 allows 70–80% narrator and 20–30% dialogue but sets a 75/25 midpoint. The new requested target is 70/30. Opus must plan the canonical amendment and dependent validators/tests; do not alter the historical decision log as if the amendment were already merged.

## 3. The required 10/30/60 model

The numbers represent visual timeline runtime, not shot count, asset count or spoken-word percentage.

### 10% HELPER
Use deterministic explanatory graphics when a cinematic scene cannot communicate the facts clearly enough: maps, route/territory changes, timelines, statistics, counters, cutaways, process flows and proof/evidence inserts. Data, labels, dates, boundaries and numbers must be generated deterministically; AI must not invent or draw them.

### 30% STILL
Use composed illustrated tableaux and inserts where full character animation adds little value. A STILL is not necessarily a dead image: it may use a 3D camera move, 2.5D depth/parallax, focus pull, light flicker, particles, environment movement or small pose changes. Use full 3D only when perspective or camera travel requires it. Preserve the current STILL hold/motion rules only after tracing BP-109 and BP-170 in the active rule registry.

### 60% VIDEO
Use full animated scenes for actions whose physical or emotional progression matters: battles, movement, duels, dialogue, council scenes, crafting, travel, discovery, reactions, consequences and environmental action. Dialogue coverage and non-dialogue action have different duration logic. VIDEO does not mean “a character must speak.”

**Important target architecture:** the three lanes must share the same Ink Chronicle style engine and asset universe. HELPER data may be authored by Python and imported as text/curves/geometry, but the final visual composition must preserve the same look and must have a clearly defined final render path. Opus must explicitly compare a Blender-final-frame route with any minimal post-render compositor route and recommend one without compromising visual consistency.

## 4. Independent 70/30 spoken-word model

Target **70% narrator / 30% voiced character dialogue**, measured by spoken words, not seconds, shots or visual-lane share.

- Exclude lines explicitly marked `voiced: false`.
- A VIDEO shot can be silent or narrated.
- A STILL or HELPER can sit under narration.
- Visible lip-sync is a shot-purpose constraint; it does not define the spoken-word ratio.
- The actual final audible seconds must be reported separately because delivery speed, pauses and silence can change elapsed time.
- Update D-95's planning midpoint from 75/25 to 70/30 while preserving its current allowed bands unless Opus identifies a precise contradiction and presents a testable proposal.

## 5. Desired production flow

Plan an end-to-end flow similar to:

`approved story/script + narration/dialogue timing`
→ `screenplay_spine / film_shots`
→ `visual intent and lane allocation`
→ `scene archetype + shot design`
→ `asset/world resolution`
→ `Blender scene build`
→ `lane-specific render profile`
→ `headless Blender render / frame cache`
→ `existing assembly + audio mix + FFmpeg mux`
→ `visual, timing, style, continuity and cost QA`
→ `creator review`.

This is a target flow, not a claim that the complete Blender path exists. Mark every missing module as TODO.

## 6. Required research synthesis

Use the research report at:

`docs/research/cinematic_audio_visual_craft_and_tool_implementation_report_2026_11_04.md`

Relevant areas:
- C.1–C.5: visual storytelling, shot framing, camera, lighting, animation and helper graphics.
- D.1–D.2: cutting, transitions, pacing and explanatory clarity.
- F.1: 20 visual/audio scene archetypes.
- I.1: coordinated 12-minute audiovisual blueprint.
- J: reusable craft/technique cards; keep Blender-relevant cards and translate LTX-dependent ones into deterministic Blender techniques.
- M–N: Blender alternative and `bpy` architecture.
- O: reusable repositories and packages, after license and maintenance checks.
- Q: camera, crowd, painterly NPR, lip-sync and map modules.
- R: scene-archetype implementation ideas.
- S: reusable Blender technique cards.
- T: LTX vs Blender comparison, with its technical claims independently revalidated.
- U–X: asset libraries, style unification, world reuse and world archetypes.

Use the source-scope document for exclusions. Do not carry LTX-only constraints such as local `8n+1` frames into a Blender pipeline.

## 7. Current-vs-target investigation

Inspect the exact base branch, not only old architecture docs.

At minimum trace:
- `explainer_engine/edit/router.py`: current LTX/still/compensator route decisions and the refusal of `DRAMA_BLOCKED_3D`.
- `explainer_engine/edit/visual_compensator.py`, `edit/tableau.py`, `maps/` and `hud.py`: what rendering logic can be reused as data/graphic builders versus what must leave the final render path.
- `explainer_engine/production/assemble.py`: preserve audio, timeline, chunk assembly, FFmpeg mux and QA hooks where possible; verify exact current frame-generation ownership before changing it.
- `explainer_engine/audio/spine.py`, sound director and voice code: keep existing timing/audio contracts unless a verified gap exists.
- `explainer_engine/core/contracts.py`, `core/shot_cache.py`, `core/ledger.py`, `config/spend_caps.json`: extend rather than duplicate.
- `explainer_engine/world/bible.py`, `world/bible.json`, `world/look_v2.json`, `world/eras.json` and `design/palette.json`: migration to an approved Ink Chronicle visual bible.
- `explainer_engine/assets/library.py` and its schema: currently raster-oriented; assess how to register .blend, .fbx, .glb/.gltf, .obj and texture dependencies.
- `scripting/film_shots.py`, `variant_plan.py`, validators, rule registry and contracts: trace existing D-93 and D-95 enforcement.
- Existing QA frame review, identity, audio and output validators: retain and add only the checks Blender requires.

Do not assume a class, renderer, adapter or TODO exists because it is named in a plan. Cite code and callers.

## 8. Cost and quality objective

The $10–15 target must be compared using like-for-like scenarios:
- 12-minute and 15-minute episode.
- 2560×1440, 24 fps final delivery.
- 10/30/60 runtime mix.
- Same representative scene complexity and approved Ink Chronicle quality.
- Include GPU hours, billed boot/setup, downloads, storage, egress, failed frames, retries and upscale.
- Separately list one-time asset-library creation, asset generation, narration, music, development and human authoring/review time.
- Report both cash cost per episode and amortized recurring cost after asset reuse.
- Do not price a future pipeline using invented 0.3–1.2 second/frame claims. Those values in the report are hypotheses until reproduced.

Compare at least:
1. Local M4 Pro / Apple Silicon Blender render (preview and measured final-render suitability).
2. Low-cost Vast.ai marketplace NVIDIA GPUs, including lowest and median offers, storage/egress and host reliability.
3. RunPod Community/Secure alternatives, not just one advertised tier.
4. SheepIt free distributed render as a non-guaranteed supplementary route.
5. Mixed render strategy: EEVEE + camera culling/instances + frame cache + lower-resolution tests + selective full-resolution hero shots.
6. Native 1440p versus 75%/67% render resolution with tested upscale and line-art stability.

## 9. Opus output required

Create a dependency-aware plan with these sections:

1. Executive recommendation and why.
2. Verified current state and code path diagram.
3. Requirements and decisions ledger.
4. Full 10/30/60 visual grammar, mapped to all relevant scene archetypes.
5. Independent 70/30 speech model and exact rule/code/test changes.
6. Ink Chronicle style system and asset/world-bible design.
7. High-level Python module/class tree, responsibilities, inputs/outputs, dependencies and non-goals.
8. Contracts/schemas and migration/backward compatibility.
9. Renderer/provider alternatives and a measured cost model.
10. Reproducible PoC benchmark design.
11. QA, tests, visual acceptance criteria and failure handling.
12. Implementation phases with dependencies, affected paths, TODO IDs and acceptance criteria.
13. Keep/change/remove/deprecate list.
14. Risks and unresolved creator decisions.
15. Final recommendation and the first bounded implementation phase.

Every proposed class, module and schema must say `TODO / NOT IMPLEMENTED` until code is actually written and tested.

## 10. No-go list

Do not:
- Implement all imported Master Mold v2.1 TODOs.
- Introduce a new voice chain, a new timeline solver or another agent hierarchy without proof that the current ones cannot serve.
- Keep LTX as a required final visual renderer merely because current `edit/router.py` routes to LTX.
- Replace the audio system, script pipeline, contracts, ledger or FFmpeg assembly wholesale.
- Make every visual shot a full-geometry scene when a tableau or deterministic helper is cheaper.
- Use Cycles for all frames by default.
- Use creative AI video upscaling by default; temporal flicker and invented details must be tested.
- Treat low public GPU-marketplace floor prices as guaranteed production rates.
- Call estimates measurements.
- Delete legacy source/research in this planning phase.

## 11. Acceptance criteria for the plan

The plan is acceptable only if:
- It clearly describes all three visual lanes and how they are produced in one visual universe.
- It separates 10/30/60 visual runtime from 70/30 spoken-word share.
- It names actual current files and exact changes, not vague “build Blender integration.”
- It proposes a small, coherent high-level class structure rather than dozens of unnecessary abstractions.
- It explains which old rules conflict and which stay.
- It contains a benchmark that can prove or reject the $10–15 target.
- It defines a quality bar for the same Ink Chronicle style across a character close-up, council/interior, outdoor environment, large battle and helper map/chart.
- It preserves existing contracts, cost controls, audio and QA unless an evidence-based replacement is proposed.
- It ends with an approval gate and does not begin production implementation.
