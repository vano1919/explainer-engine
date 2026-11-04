# Ink Chronicle — Blender Visual Pipeline (Planning Branch)

**Branch:** `opus/ink-chronicle-blender-plan-2026-11-04`  
**Status:** Planning package only. No new Blender production renderer is implemented by this branch.  
**Base:** `claude/master-mold-ready-2026-11-04`

This isolated branch prepares a clean, Opus-led implementation plan for a lower-cost, visually consistent **Ink Chronicle** production pipeline.

## Creator-set target

- **Visual universe:** Ink Chronicle — reusable real 3D geometry rendered as illustrated / graphic-novel imagery using controlled ink contours, stylized materials, lighting and palette.
- **Master delivery:** 2560×1440 (1440p/QHD), 24 fps. The creator may call this “2K” informally; technical documents must say 1440p/QHD.
- **Visual runtime:** 10% HELPER / 30% STILL / 60% VIDEO, retaining D-93's ±5 percentage-point tolerance.
- **Spoken-word target:** 70% narrator / 30% voiced character dialogue, measured by spoken-word count and independently from visual runtime.
- **Cost objective:** US$10–15 visual/render cash cost per 12–15-minute episode. This is an unproven target, not a measured cost or guarantee.

## Read in this order

1. [CLAUDE.md](CLAUDE.md) — branch-specific operating instructions.
2. [Opus master task](docs/opus/OPUS_MASTER_TASK.md) — complete mission and required deliverables.
3. [Rule conflicts and migration](docs/opus/RULE_CONFLICTS_AND_MIGRATION.md) — legacy policies that require rewriting.
4. [10/30/60 visual grammar](docs/opus/VISUAL_GRAMMAR_10_30_60.md) — practical shot and technique library.
5. [Architecture and class map](docs/opus/ARCHITECTURE_AND_CLASS_MAP.md) — proposed modules, classes and data flow.
6. [Render cost and benchmark plan](docs/opus/RENDER_COST_AND_BENCHMARK_PLAN.md) — cheap render candidates and cost proof.
7. [TODO register](docs/opus/TODO_REGISTER.md) — dependency-ordered open tasks and acceptance criteria.
8. [Research source scope](docs/opus/RESEARCH_SOURCE_SCOPE.md) — useful research and explicit exclusions.

## Planning boundary

This branch is a **planning branch**. It must not silently replace the base branch, implement production renderer code, run paid GPU jobs, generate paid assets, publish content or delete historical source files.

Opus must first produce a complete, dependency-aware implementation blueprint and a minimal code-change map. The creator reviews and approves that plan before implementation.

The original research and existing source code remain available for evidence and traceability. They are not all active instructions for this new direction.
