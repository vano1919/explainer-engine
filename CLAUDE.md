# CLAUDE.md — Ink Chronicle Blender Planning Branch

## Mission

You are working on `opus/ink-chronicle-blender-plan-2026-11-04`, an isolated planning branch based on `claude/master-mold-ready-2026-11-04`.

Your task is to produce a complete, evidence-based, Opus-quality implementation plan for the **Ink Chronicle Blender visual pipeline**. This is a planning assignment, not permission to implement a renderer, change production behavior, launch paid compute, create paid assets, upload or publish.

Read the branch README and every file under `docs/opus/` before starting. Those documents define the intended planning scope. The base branch is evidence of current implementation, not an instruction to preserve every old visual decision.

## Creator-set targets

1. **Visual style:** Ink Chronicle — reusable real 3D characters, costumes, props, architecture, terrain and environments; final output appears illustrated / graphic-novel-like, not photorealistic, generic low-poly or a mixture of unrelated styles.
2. **Master output:** 2560×1440, 24 fps. Technical label: 1440p/QHD.
3. **Visual runtime:** 10% HELPER / 30% STILL / 60% VIDEO, measured by timeline duration and retaining D-93's ±5 percentage-point tolerance.
4. **Spoken words:** target 70% narrator / 30% voiced character dialogue. Measure spoken words, excluding `voiced:false`; never infer the ratio from shot/lane duration. Current D-95 outer bands are 70–80% narrator and 20–30% dialogue; the requested target changes its 75/25 midpoint and requires synchronized canonical rule/validator changes.
5. **Cost objective:** US$10–15 visual/render cash cost per finished 12–15-minute episode. This is not proven. Separate GPU rental, setup/boot, storage/egress, retries, upscale, one-time reusable asset creation, paid asset generation, voice/music, development and human time.
6. **Renderer:** Blender is the intended common 3D scene/render system. EEVEE is the primary candidate, not a pre-proven lock. Compare EEVEE, selective Cycles and efficient 2.5D/data paths based on measured visual quality and cost.
7. **Continuity:** one approved Ink Chronicle style system and versioned reusable 3D asset library.
8. **Reuse:** preserve existing narrative, timing, voice/audio, schema, cache, spend control, QA and FFmpeg capabilities when they remain useful. Reuse before replacement.

## Critical precedence warning

The new Ink Chronicle / Blender target conflicts with existing 2D raster-first, Gemini/Qwen/LTX visual routes, the GPU layer-compositor ownership, the current refusal of Blender/3D scene routing, and the 2D/2.5D-only terrain-map rule. The precise conflicts and migration actions are recorded in `docs/opus/RULE_CONFLICTS_AND_MIGRATION.md`.

The creator authorized planning of this new direction. This does **not** mean every technical detail has been decided or that old canonical rules can be silently bypassed. Identify all rules that must be amended and every code/schema/test/agent/skill consumer that must be synchronized.

The imported Master Mold v2.1 TODO annotations and execution guide are unverified proposals. Do not execute their 301-file TODO inventory. Do not add `production_script/4`, a new voice chain, a new timeline solver, or another agent architecture merely because they appear in imported TODOs. Verify actual callers and tests first.

## Evidence labels

Use these labels throughout:
- `VERIFIED CURRENT` — confirmed in current base-branch code/docs/tests.
- `CREATOR-SET TARGET` — explicit direction from the creator.
- `PROPOSED TECHNICAL CHOICE` — Opus recommendation, not yet implemented or approved.
- `HYPOTHESIS / NEEDS BENCHMARK` — unmeasured performance, quality or cost.
- `TODO / NOT IMPLEMENTED` — future work.
- `LEGACY / NOT AUTHORITATIVE FOR THIS BRANCH` — old approach or imported proposal that must not be treated as the new target.

Never promote an imported TODO, estimate, external low-price listing or research hypothesis to an approved creator decision.

## Required analysis format

For every affected area, document:

**CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION**

The recommendation must be grounded in actual source paths, callers, contracts, tests and measured outputs where available.

## Required Opus deliverables

Use Claude Opus at the highest suitable reasoning effort (prefer xhigh). If Opus is unavailable, do not silently substitute a lower model.

Produce:
1. Executive recommendation and rationale.
2. Verified current architecture and real source-to-output flow.
3. Requirements / decisions ledger separating creator decisions, technical choices, hypotheses and unknowns.
4. Complete 10/30/60 visual grammar mapped to the existing 20 scene archetypes.
5. Independent 70/30 speech accounting, timeline reporting and exact rule/validator/test changes.
6. Ink Chronicle Style Bible, asset provenance and 3D asset-reuse design.
7. Minimal high-level Python package/class map with inputs, outputs, responsibilities and dependencies.
8. Contract/schema changes and backward-compatibility strategy.
9. Renderer/provider comparison and a reproducible cost model capable of proving or rejecting the US$10–15 objective.
10. PoC benchmark design at 1440p/24fps using representative scenes.
11. QA, tests and explicit visual acceptance criteria.
12. Dependency-ordered implementation roadmap, TODO IDs and phase gates.
13. File-by-file KEEP / CHANGE / REPLACE / DEPRECATE / REMOVE proposal with evidence.
14. Risks, unresolved creator decisions and the first bounded implementation phase.

## Repository and spend safety

- Do not modify the base branch or any other branch.
- Do not merge, force-push or change branch protection.
- Do not perform broad deletions, remove history or rewrite production code in this planning phase.
- No paid APIs, GPU pods, paid asset generation, full-episode render, YouTube Studio changes, upload or publication.
- No credentials or secrets in files.
- Preserve all existing creator approvals and cost controls.
- Do not weaken existing tests or schema validation.
- Cite exact paths, functions, contracts and test names only after verifying they exist.
- Unknown facts stay UNKNOWN. Do not invent benchmark data, class implementations or test results.

## Stop condition

Finish with the Opus plan, class map, TODO map, rule rewrite map and acceptance criteria only. Do not start production implementation until the creator reviews and approves the architecture and the first bounded phase.
