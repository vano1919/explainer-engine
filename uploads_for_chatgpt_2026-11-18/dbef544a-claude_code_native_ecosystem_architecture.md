# Claude Code Native Agent, Skill, Tool & Plugin Ecosystem Architecture

> **Status:** PROPOSED ARCHITECTURE & GLOBAL DISCOVERY POLICY (`DEC-2026-11-17-02` — **PROPOSED, AWAITING OWNER APPROVAL**).  
> **Scope Boundary:** Cross-cutting development and orchestration ecosystem architecture for Claude Code (`vano1919/explainer-engine`). This specification preserves `P1.3` (`Read-only Production State and dependency snapshot`) as a strictly separate workstream and modifies zero `.py`, `.json`, or schema files until explicit Owner approval.

---

## 1. Strategic Decision & Architectural Precedence

1. **Primary Environment:** Explainer Engine is architected specifically for **Claude Code** ([official documentation](https://code.claude.com/docs/en/skills)) as its primary development and episode-orchestration agent environment.
2. **Native-First Design:** All project instructions (`CLAUDE.md`), path/domain rules (`.claude/rules/*.md`), on-demand Skills (`.claude/skills/<skill-name>/SKILL.md`), Subagents and stage pages (`.claude/agents/<name>.md`), deterministic lifecycle Hooks (`.claude/settings.json`), MCP server integrations (`.mcp.json`), and Plugins (`.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json`) are designed directly around Claude Code's native runtime semantics rather than a generic wrapper framework.
3. **Open Standard Interoperability:** Project Skills conform to the open [Agent Skills Specification (`agentskills.io/specification`)](https://agentskills.io/specification) (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`, and progressive disclosure across `SKILL.md`, `references/`, `scripts/`, and `assets/`) while leveraging Claude Code native extensions (`disable-model-invocation`, dynamic `!` command context injection, `/skill-name` slash invocation, and subagent `skills` preloading) where beneficial.
4. **Strict Separation from `P1.3`:** Phase 1 `P1.3` (`Read-only Production State and dependency snapshot` over `episodes/<id>/production/stages/<stage>.json`, `jobs/<id>/state.json`, `job_manifest.json`, and `audio/timing.json`) remains an independent runtime-state workstream in [MASTER\_ARCHITECTURE\_AND\_IMPLEMENTATION\_PLAN.md](https://www.google.com/search?q=MASTER_ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md). Global agent/skill/tool/plugin governance never competes with or replaces episode Production State.

---

## 2. Audit of Existing Repository Claude Code Assets (Baseline @ `eb80e443` / `a060cf0b`)

Before proposing any addition, the complete existing Claude Code footprint in `vano1919/explainer-engine` was inspected and verified against active unit tests (`tests/unit/test_agent_roles.py`, `tests/unit/test_agent_governance.py`, `tests/unit/test_t3_agent_skill_banners.py`, and `tests/unit/test_governance_hooks.py`):

### 2.1 Existing Native Configuration & Rules

| Path | Current Role | Enforced Invariants & Test Locks | Disposition |
|---|---|---|---|
| `CLAUDE.md` (141 lines) | Root project instructions loaded at session startup; imports `@.claude/rules/cloud-platforms.md` | Defines the v4.3 episode-first rebuild ([DECISIONS\_AND\_OPEN\_QUESTIONS.md](https://www.google.com/search?q=../DECISIONS_AND_OPEN_QUESTIONS.md)), retired routes (`config/retired_era.json`), precedence, commands, 12 hard invariants, orchestration rules ([ORCHESTRATION.md](https://www.google.com/search?q=../ORCHESTRATION.md)), sourced rules ([SOURCED\_RULES.md](https://www.google.com/search?q=../SOURCED_RULES.md)), episode rulebook ([EPISODE\_STANDARDS.md](https://www.google.com/search?q=../EPISODE_STANDARDS.md)), and repo layout | **Retain & streamline** (keep `< 200` lines; move repeatable discovery/validation runbooks into on-demand Skills after Owner approval) |
| `.claude/settings.json` | Project-shared deterministic lifecycle hooks (`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, `StopFailure`, `PreModelSwitch`, `PostModelSwitch`, `UserPromptSubmit`) + `statusLine` | Tested by `tests/unit/test_agent_governance.py::test_every_hook_command_names_an_existing_module_and_hook` and `tests/unit/test_governance_hooks.py` | **Retain**; extend only via tested Python hook handlers when approved |
| `.claude/rules/cloud-platforms.md` | Cloud GPU/API execution and billing rules across RunPod, Hyperstack, and Modal | Enforces `spend_caps.json`, `EE_MODAL_GO`, Hyperstack `SHUTOFF` billing trap guard, and 9-point provider adapter contract | **Retain**; add `.claude/rules/skill-and-tool-discovery.md` only upon Owner approval |
| `config/model_routing.json` | Single source of truth for models (`haiku`, `sonnet`, `opus`, `fable`), effort ceilings (`high` for code), 18 task classes (`S0–S4`), critics, spawners, and `protected_files` | Protected by `explainer_engine/governance/hooks.py` (`pre-write` & `pre-bash`) and `tests/unit/test_agent_governance.py` | **Retain untouched** (changes require explicit Owner word recorded via `governance ok`) |

### 2.2 Existing `.claude/agents/` Inventory (16 Active Files + 1 Pending)

Under repository governance (`tests/unit/test_agent_roles.py` and `tests/unit/test_agent_governance.py`), `.claude/agents/` intentionally distinguishes **spawned agents** from **in-process stage pages**:

1. **Main Spawner Agents (`role: main`, `model: opus`, `effort: high`, allowed `Agent` tool):**
   - `.claude/agents/orchestrator.md` — End-to-end episode orchestrator (spawns only `script-critic`).
   - `.claude/agents/lora-coordinator.md` — Legacy LoRA training coordinator (spawns only `lora-checkpoint-judge`).
2. **Independent Read-Only Critics (`role: critic`, `model: opus`, `effort: high`, `tools: Read, Grep, Glob`):**
   - `.claude/agents/script-critic.md` — Fresh-context viewer/editor critic for `production_script.json`.
   - `.claude/agents/lora-checkpoint-judge.md` — Fresh-context checkpoint evaluator for legacy LoRA runs.
3. **In-Process Stage Pages (`role: stage` / `stage-story`, followed by the main agent without spawning a separate subagent context):**
   - `story-architect.md` (`sonnet`/`high`), `scene-writer.md` (`sonnet`/`high`), `beat-writer.md` (`sonnet`/`high`), `performance-director.md` (`sonnet`/`high`), `edit-planner.md` (`sonnet`/`high`), `voice-caster.md` (`sonnet`/`high`), `shorts-writer.md` (`sonnet`/`high`), `shot-continuity-writer.md` (`sonnet`/`high`), `episode-standards-director.md` (`sonnet`/`high`), `lora-dataset-auditor.md` (`sonnet`/`medium`), `lora-run-operator.md` (`sonnet`/`high`), and `paid-run-watchdog.md` (`haiku`/`low` side thread).
4. **Pending Clean-Room Critic:**
   - `docs/agents_pending/youtube-viewer-critic.md` (`model: opus`, `effort: high`, `tools: Read`) — Awaits Owner approval to join `.claude/agents/` and `config/model_routing.json`.

### 2.3 Existing `.claude/skills/` Inventory (21 Project Skills)

All 21 existing project skills under `.claude/skills/<name>/SKILL.md` are verified by `tests/unit/test_agent_governance.py`:
- **Story, Research & Scripting (6):** `science-grounding`, `crossover-episode`, `time-jump-episode`, `story-engine`, `dialogue-scenes`, `narration-script`.
- **Visual Direction, Animation & Maps (5):** `shot-visuals`, `visual-beats`, `animated-universe`, `animation-principles`, `cartography`.
- **Audio, Voice & Editing (5):** `elevenlabs-voice`, `voice-search`, `editing-style`, `video-editing-architect`, `shorts-for-video`.
- **Cloud, Cost & Infrastructure (5):** `cloud-cost-audit`, `cloud-provider-selection`, `hyperstack-operations`, `modal-operations`, `lora-training`.

---

## 3. Claude Code Native Component Architecture & Separation of Responsibilities

| Component Layer | Canonical Location | Primary Responsibility | What It Must NEVER Do |
|---|---|---|---|
| **A. `CLAUDE.md` & `.claude/rules/`** | `CLAUDE.md`, `.claude/rules/*.md` | Always-loaded architectural invariants, source-of-truth order, approval gates, budget/security fences, and concise routing pointers (`< 200` lines target per file) | Must not inline 500-line procedural manuals, tool recipe tables, or per-shot prompt templates |
| **B. Project Skills (`SKILL.md`)** | `.claude/skills/<skill-name>/SKILL.md` (+ `references/`, `scripts/`, `assets/`, `evals/`) | On-demand procedural workflows, domain checklists, decision trees, and progressive-disclosure reference loading (`~100` tokens metadata at startup; `< 5,000` tokens / `< 500` lines body on activation) | Must not claim to install/connect an executable Tool or bypass `spend_caps.json` / `.claude/settings.json` hooks |
| **C. Subagents & Stage Pages** | `.claude/agents/<name>.md` (governed by `config/model_routing.json`) | Context isolation for high-volume read-only exploration, independent fresh-eyes critique (`script-critic`, `youtube-viewer-critic`), or stage-locked checklists (`stage_guard`) | Must not violate the single-spawner/read-only-critic lock in `tests/unit/test_agent_roles.py` or mutate files from a critic |
| **D. Lifecycle Hooks** | `.claude/settings.json` -> `explainer_engine/{governance,cloud,standards}/hooks.py` | Deterministic, zero-cost pre/post enforcement: blocking unapproved spend, force-push, `branch -D`, protected config edits, invalid model switches, and post-edit `py_compile`/`docs_lint` checks | Must not replace domain reasoning or fail closed on non-financial transient network errors (except when a known live pod is billing) |
| **E. Executable Tools & MCP Servers** | `.mcp.json`, Python modules (`explainer_engine/**`, `tools/render_tools/**`), CLI binaries (`ffmpeg`, `ffprobe`, `blender`, `modal`) | Actual deterministic execution, file probing, rendering, schema validation, and external API/process transport | Must not embed unreviewed creative taste or execute billable cloud/API calls without passing repository gates |
| **F. Claude Plugins** | `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` | Versioned packaging unit bundling related Skills, Agents, Hooks, Commands, and `.mcp.json` when multi-repo distribution or immutable release pinning is required | Must not wrap every standalone project Skill into a separate plugin or rely on plugin subagent `hooks`/`mcpServers`/`permissionMode` frontmatter (which Claude Code ignores for plugin subagents for security) |

### 3.1 Evaluation of the 14 Proposed Specialized Subagent Roles

Per [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents) and repository governance (`config/model_routing.json` and `tests/unit/test_agent_roles.py`), adding standalone spawned subagents indiscriminately increases context overhead (Claude Code warns when combined subagent descriptions exceed `15,000` tokens) and breaks `test_every_agent_file_is_a_main_agent_a_critic_or_a_stage_page`. Below is the evidence-based disposition for each of the 14 candidate roles:

| # | Candidate Role | Existing Coverage in Repository | Delegation vs. Stage-Page / Skill Assessment | Recommended Architectural Disposition |
|---|---|---|---|---|
| 1 | **Creative Director** | `.claude/agents/orchestrator.md`, `.claude/skills/story-engine/SKILL.md`, `explainer_engine/production/living_director.py` | High-level creative direction requires full episode context (`world_bible`, `production_script.json`); spawning loses shared state | **Do NOT create a new spawned subagent.** Keep creative direction in `orchestrator` + `story-architect` stage page, enhanced by a `cinematic-directing` skill reference |
| 2 | **Historical Researcher** | `.claude/skills/science-grounding/SKILL.md`, `.claude/skills/crossover-episode/SKILL.md`, `explainer_engine/research/fan_brief.py` | Web/source gathering generates high-volume search snippets that bloat the main context window; maps to `research-facts` (`S2`, `haiku`/`sonnet`) in `config/model_routing.json` | **Delegate via built-in `Explore` / `research-facts` pattern + `science-grounding` Skill** (or an approved read-only `historical-researcher` subagent with `omitClaudeMd: true` if Owner updates `model_routing.json`) |
| 3 | **Screenwriter** | `.claude/agents/story-architect.md`, `.claude/agents/scene-writer.md`, `.claude/skills/narration-script/SKILL.md`, `.claude/skills/dialogue-scenes/SKILL.md` | Must run sequentially in the main agent under `scripting/stage_guard.py` (`architect` -> `writer`) on frozen script state | **Keep as existing Stage Pages (`story-architect`, `scene-writer`) + Skills (`narration-script`, `dialogue-scenes`)** |
| 4 | **Storyboard / Previsualization Specialist** | `.claude/agents/shot-continuity-writer.md`, `explainer_engine/videolane/storyboard.py`, `.claude/skills/shot-visuals/SKILL.md` | Already covered by `shot-continuity-writer` (`continuity_card/1`) and `videolane/storyboard.py` ([VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md)) | **Keep as existing `shot-continuity-writer` Stage Page + `shot-visuals` Skill** |
| 5 | **Cinematography Specialist** | `.claude/agents/edit-planner.md`, `explainer_engine/videolane/plan.py`, `explainer_engine/production/direction.py` | Camera framing, lens choice, `axis_side`, and `continuity_mode` are tightly coupled to `edit-planner` (`ProductionScriptV4.shots[].edit_plan`) | **Keep in `edit-planner` Stage Page**; enrich `.claude/skills/shot-visuals/` with focal-length, lighting-ratio, and `F1–F19` failure-diagnosis references |
| 6 | **Blender 3D Artist / Technical Operator** | `explainer_engine/blender/*` (48 modules), `.claude/skills/animated-universe/SKILL.md` | Note: Blender scene/J5 route is **retired inside v4.3 episodes** (`config/retired_era.json`), used only for legacy episodes and free PC/CI benchmarks | **Do NOT add a standing subagent** (saves startup context tokens on v4.3 episodes); use on-demand Blender skill/recipes only when legacy or benchmark tasks are invoked |
| 7 | **Animation / Rendering Specialist** | `.claude/skills/animation-principles/SKILL.md`, `explainer_engine/production/layers25d.py`, `explainer_engine/production/directed25d.py` | 2.5D motion imitation (`still_25d`, 30%) and LTX motion review (`video`, 60%) are deterministic Python + QA gates (`qa/motion_intent.py`) | **Keep as `animation-principles` Skill + deterministic Python modules (`layers25d.py`, `directed25d.py`, `motion_intent.py`)** |
| 8 | **FFmpeg Video Editor** | `explainer_engine/production/assemble.py`, `tools/render_tools/build_segments.py`, `.claude/skills/editing-style/SKILL.md`, `.claude/skills/video-editing-architect/SKILL.md` | Frame-exact 24fps chunk assembly (`assemble_shot_clips`) must obey `episode_timing/1` & `/2` (`load_clock`), never ad-hoc millisecond shell cuts | **Keep execution in `production/assemble.py` & `tools/render_tools/`**, paired with a project-adapted `ffmpeg-media-ops` Skill for probing/diagnostics |
| 9 | **Audio Engineer** | `.claude/agents/beat-writer.md`, `.claude/agents/voice-caster.md`, `explainer_engine/audio/*` (33 modules), `tools/render_tools/mix.py`, `.claude/skills/elevenlabs-voice/SKILL.md` | `sound_plan.py`, `stems.py`, `level.py`, `duck.py`, and `mix.py` enforce sourced loudness rules ([SOURCED\_RULES.md](https://www.google.com/search?q=../SOURCED_RULES.md)) deterministically | **Keep in `beat-writer` / `voice-caster` Stage Pages + `elevenlabs-voice` / `voice-search` Skills + `explainer_engine/audio/` tools** |
| 10 | **Color Grading Specialist** | `explainer_engine/finish/grade.py`, `explainer_engine/blender/grade.py`, `explainer_engine/design/palette.py`, `explainer_engine/qa/motion_intent.py` (`blown_out` gate) | Color grading and palette contrast (`15 tokens PASS`, `LIGHT_CEIL`, `SHAFT_CEIL`) are enforced deterministically in Python | **Keep in `finish/grade.py` & `design/palette.py`**; document LUT/HDR->SDR probe rules inside the media-ops Skill reference |
| 11 | **AI Image / Video Workflow Specialist** | `explainer_engine/videolane/*`, `explainer_engine/gemini_task/*`, `explainer_engine/training/pods/ltx/*`, `.claude/skills/modal-operations/SKILL.md` | Covers Gemini turn-pack intake ([GEMINI\_CONSISTENCY\_RULES.md](https://www.google.com/search?q=../GEMINI_CONSISTENCY_RULES.md)) and Modal LTX-2.5 distilled execution ([VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md)) | **Propose a dedicated on-demand Skill (`.claude/skills/videolane-ltx-workflow/SKILL.md`)** rather than a separate subagent |
| 12 | **Pipeline Architect** | `docs/architecture/MASTER_ARCHITECTURE_AND_IMPLEMENTATION_PLAN.md`, `config/model_routing.json` (`architecture-design`, `S3`, `opus`/`high`) | Architectural decisions require full repository visibility and Owner sign-off (`DEC-*`) | **Handled by the Lead Architect session (`opus`/`high` thread per `model_routing.json`)** |
| 13 | **QA / Production Validator** | `.claude/agents/script-critic.md`, `.claude/agents/lora-checkpoint-judge.md`, `docs/agents_pending/youtube-viewer-critic.md`, `explainer_engine/episode/acceptance.py` (G10) | Fresh-context critique is the #1 high-value subagent use case because the critic must not share the writer's bias ([ORCHESTRATION.md](https://www.google.com/search?q=../ORCHESTRATION.md)) | **Retain `script-critic` & `lora-checkpoint-judge`; activate `youtube-viewer-critic` once Owner approves its `model_routing.json` entry** |
| 14 | **Skill and Tool Researcher** | Currently ad-hoc | Searching external GitHub repos, `SKILL.md` bodies, `.claude-plugin/plugin.json`, and MCP schemas generates large temporary text dumps ideal for context isolation (`omitClaudeMd: true`, read-only tools) | **Propose a dedicated Skill (`.claude/skills/skill-and-tool-discovery/SKILL.md`) + optional read-only subagent specification** (requires Owner approval to register in `config/model_routing.json`) |

---

## 4. Mandatory 10-Dimension Content-Based Skill & Tool Discovery Policy

Searching only by repository name, GitHub star count, or one-line summary is **strictly forbidden** across all phases of Explainer Engine. Every candidate Skill, Plugin, MCP server, or executable Tool must be discovered and evaluated across **10 mandatory dimensions**:

1. **User Task & Intended Outcome:** Exact production problem solved (e.g., frame-exact 24fps shot assembly vs. generic social-media clipping).
2. **Functional Behavior:** Step-by-step runtime behavior when invoked (routing tables, preflight checks, dry-run support, repair loops).
3. **Required Operations:** Exact atomic operations performed (e.g., `ffprobe` stream inspection, EBU R128 loudness normalization, `bpy.ops` level-0 multires baking).
4. **Technical Implementation Methods:** Pure prompt instructions vs. typed CLI wrapper scripts (`argparse` -> JSON) vs. socket/stdio MCP server.
5. **Input & Output Formats:** Exact schema versions (`episode_timing/2`, `production_script/4`), file containers (`.mp4`, `.wav`, `.blend`, `.json`), and exit-code conventions.
6. **Relevant APIs & Tool Names:** Exact Claude Code tool identifiers (`Read`, `Edit`, `Bash`, `mcp__<server>__<tool>`, `mcp__plugin_<plugin>_<server>__<tool>`).
7. **Workflow Steps & Decision Logic:** Branching logic, capability-first routing, fallback chains, and when the skill stops to ask the user.
8. **Known Failure Modes & Validation Requirements:** Coded failure taxonomies, post-execution verification (`probe.py`, contact-sheet inspection, schema validation), and open upstream bugs.
9. **Required Dependencies & Runtime Environment:** OS compatibility (Windows PowerShell/Git Bash, Linux CI), Python version, third-party packages vs. stdlib-only, binary versions (`ffmpeg >= 6.1`, `Blender >= 5.1`), and GPU/VRAM requirements.
10. **Domain Terminology & Synonyms:** Search queries must expand domain synonyms (e.g., `dialogue timing` <-> `word spine` / `forced alignment` / `Scribe` / `edit_points`; `2.5D parallax` <-> `DepthFlow` / `layered still` / `motion imitation`; `loudness` <-> `LUFS` / `EBU R128` / `ducking`).

### 4.1 Mandatory Files to Inspect Before Recommending Any Candidate

For every candidate repository, the evaluator must read the actual text of:
- `SKILL.md` (frontmatter + full body + routing table)
- `README.md`, `SECURITY.md`, `CHANGELOG.md`, and `LICENSE`
- `references/*.md` and `examples/*`
- `scripts/*.py` / `scripts/*.sh` (checking for shell injection, network calls, credential reads, or destructive writes)
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `package.json`, `requirements.txt`, and `.mcp.json` / `server.json`
- `tests/` and `evals/evals.json`
- Open GitHub Issues and Pull Requests (to catch known precision or security bugs before adoption)

### 4.2 Tool-First and Skill-First Decision Matrix (Cases A–D)

| Case | Condition | Mandatory Execution Sequence |
|---|---|---|
| **CASE A** | **Required Tool already exists in repo/environment** (e.g., `ffmpeg`, `explainer_engine/episode/timing.py`, `explainer_engine/production/assemble.py`) | 1. Inspect actual local tool capabilities, CLI flags, and schema version.<br>2. Search for the best Skill that teaches Claude how to orchestrate that exact tool.<br>3. Check if an official/community plugin bundles the Tool + Skill.<br>4. Verify compatibility with Explainer Engine contracts ([CONTRACTS.md](https://www.google.com/search?q=../CONTRACTS.md), [EPISODE\_FIRST.md](https://www.google.com/search?q=../EPISODE_FIRST.md)) before adoption. |
| **CASE B** | **New capability is required** | 1. Search across all 10 content dimensions for existing Skills explaining the workflow.<br>2. Search for real executable Tools and MCP servers implementing the capability.<br>3. Search for existing plugins and end-to-end workflows.<br>4. Prefer integrating proven, MIT/Apache-2.0 licensed components over writing from scratch. |
| **CASE C** | **No suitable external Skill exists** | 1. Evaluate adapting the closest high-quality open-source Skill (preserving license attribution and provenance).<br>2. If adaptation is insufficient, author a project-specific Skill under `.claude/skills/<name>/SKILL.md` following [Agent Skills Specification (`agentskills.io/specification`)](https://agentskills.io/specification). |
| **CASE D** | **No suitable external Tool exists** | 1. Search official vendor documentation, MCP registries, SDKs, and CLI applications.<br>2. Document a comparative trade-off table of existing alternatives explaining why each fails project requirements.<br>3. Propose a minimal, reusable repository tool under `explainer_engine/` ([ORCHESTRATION.md](https://www.google.com/search?q=../ORCHESTRATION.md)) with unit tests. |

### 4.3 Required Discovery Sources & Trust Tiers

| Trust Tier | Source Category | Canonical References | Verification Requirement |
|---|---|---|---|
| **Tier 1 — Official Anthropic & Open Spec** | Claude Code official docs, official plugin repository, and Agent Skills open specification | [`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills), [`code.claude.com/docs/en/sub-agents`](https://code.claude.com/docs/en/sub-agents), [`code.claude.com/docs/en/hooks`](https://code.claude.com/docs/en/hooks), [`code.claude.com/docs/en/plugins/install`](https://code.claude.com/docs/en/plugins/install), [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official), [`agentskills.io/specification`](https://agentskills.io/specification) | Verify exact Claude Code version requirements (e.g., `v2.1.277+`, `v2.1.296+`) and frontmatter schema |
| **Tier 2 — Official Vendor & Tool Ecosystems** | Vendor-maintained CLIs, SDKs, and MCP servers | [`vercel-labs/skills`](https://github.com/vercel-labs/skills) (`npx skills` / `skills.sh`), official Blender Lab MCP (Blender 5.1+), ElevenLabs / Modal / RunPod / Hyperstack official docs | Verify billing semantics, read-only vs. mutating endpoints, and telemetry flags (`DISABLE_TELEMETRY=1`) |
| **Tier 3 — Vetted Community Repositories** | Open-source Skills, Plugins, and MCP servers on GitHub | [`wuwangzhang1216/DirectorSKILL`](https://github.com/wuwangzhang1216/DirectorSKILL), [`RobLe3/cc-blender-skill`](https://github.com/RobLe3/cc-blender-skill), [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill), [`ahujasid/mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender) | Full line-by-line audit of `SKILL.md`, `scripts/`, `SECURITY.md`, open issues, and license; pin by full Git commit SHA and `computedHash` |
| **Tier 4 — Unverified / Aggregator Listings** | Third-party directories, social posts, star counts | Trendshift, Reddit, generic MCP directories | **Never trusted as evidence.** Used only to locate the upstream Git repository for a Tier 3 content audit |

---

## 5. Deep Content Evaluation of the 7 Initial Candidates & Competing Alternatives

Each of the 7 initial candidates named in the architectural brief was inspected by reading its actual repository structure, `SKILL.md` / manifest contents, scripts, references, license, commit history, and open issues, and compared against competing alternatives:

### 5.1 Candidate Content Inspection Matrix

| Candidate | Source URL & Latest Verified State | Actual Inspected Contents (`SKILL.md`, Scripts, Manifests, Evals) | License & Dependencies | Technical & Security Findings | Project Fit & Recommended State |
|---|---|---|---|---|---|
| **1. DirectorSKILL** (`cinematic-director`) | [`wuwangzhang1216/DirectorSKILL`](https://github.com/wuwangzhang1216/DirectorSKILL) (`v2.0.0`, commit `c65ae0d`, 379 stars) | [`README.md`](https://github.com/wuwangzhang1216/DirectorSKILL/blob/main/README.md), `SKILL.md` (13-step pipeline, Modes `A–J` routing table), 13 craft/generation/production files in `references/` (`failure-modes.md` `F1–F19`, `ai-video-tool-adapters.md` shapes `S1–S4`), 20 bilingual EN/ZH director lenses ([`09_wong_kar_wai.md`](https://github.com/wuwangzhang1216/DirectorSKILL/blob/main/references/director_styles/09_wong_kar_wai.md), [`10_nolan.md`](https://github.com/wuwangzhang1216/DirectorSKILL/blob/main/references/director_styles/10_nolan.md)), 8 templates in `assets/`, `evals/evals.json` | **MIT**; pure Markdown (`0` scripts, `0` MCP servers, `$0` cost) | Safe (no executable code). **Conflict with repo rules if used raw:** its 20 director lenses name real film directors (Kubrick, Nolan, Wong Kar-wai), whereas Explainer Engine's `world/look_v2.json` (`no_names`, [UNIVERSAL\_RULE\_BASE.md](https://www.google.com/search?q=../UNIVERSAL_RULE_BASE.md)) forbids naming external directors/studios in prompts, and `videolane/` ([VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md)) + `production_script.schema.json` define our own shot schema. However, its **routing-table progressive disclosure**, **`F1–F19` failure triage tree**, and **`S1–S4` prompt shapes** are high-value architectural patterns. | `SECURITY / LICENSE REVIEWED` -> **Adapt patterns into `.claude/skills/shot-visuals/` & `videolane/`** (do not install raw 20-director overlay pack) |
| **2. cc-blender-skill** | [`RobLe3/cc-blender-skill`](https://github.com/RobLe3/cc-blender-skill) (`v1.4.0`, 33 commits, 19 tags, 165 stars) | [`plugin/README.md`](https://github.com/RobLe3/cc-blender-skill/blob/main/plugin/README.md), `plugin/manifest.json`, 30 chain-loadable skills under `plugin/skills/` (`text-to-blender`, `blender-skill-harmonizer`, `quality-refinement-autoloop`, [`blender-export/SKILL.md`](https://github.com/roble3/cc-blender-skill/blob/main/plugin/skills/blender-export/SKILL.md), [`mcp-backends.md`](https://github.com/RobLe3/cc-blender-skill/blob/main/plugin/skills/text-to-blender/references/mcp-backends.md)), `scripts/multires_bake_export.py`, `scripts/collision_preflight.py`, `src/wireframe_analyzer.py`, 200+ trigger evals | **MIT** ([`LICENSE`](https://github.com/RobLe3/cc-blender-skill/blob/main/LICENSE)); requires Blender 5.1+ (Official MCP) or 4.0+ (`ahujasid`), Python 3.9+, `opencv-python`, `numpy`, `scipy`, `Pillow` | High technical quality (dual MCP backend support, level-0 multires baking, collision preflight, Haiku-tester/Opus-patcher validation loop). **Security & Route Gate:** `execute_blender_code` executes arbitrary Python inside Blender; in Explainer Engine v4.3 (`config/retired_era.json`), the Blender scene/J5 route is **retired inside v4.3 episodes** (`episode/retired.refuse`). | `SECURITY / LICENSE REVIEWED` -> **Hold as optional reference for legacy / free PC benchmark work only; do NOT enable in v4.3 episodes** |
| **3. blender-mcp-skill (`zq940222`)** | `https://github.com/zq940222/blender-mcp-skill` | Repository URL returned HTTP 404 / inaccessible; zero public commits, zero `SKILL.md` files, and zero indexed references across GitHub and skill registries | **Unverified** (inaccessible / non-existent public repository) | Fails provenance and content inspection gate. Note that official Blender Lab MCP adaptation is already provided and verified inside [`RobLe3/cc-blender-skill` v1.4.0 (`mcp-backends.md`)](https://github.com/RobLe3/cc-blender-skill/blob/main/plugin/skills/text-to-blender/references/mcp-backends.md). | **REJECTED (`UNVERIFIED SOURCE`)** — superseded by `RobLe3/cc-blender-skill` v1.4.0 `mcp-backends.md` |
| **4. ffmpeg-skill (`kajisho5`)** | [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill) (`v3.10.1`, commit `f1c97cb`, 590 commits, 202 tags, 7.5k stars) | [`SKILL.md`](https://github.com/kajisho5/ffmpeg-skill/blob/main/SKILL.md), [`README.md`](https://github.com/kajisho5/ffmpeg-skill/blob/main/README.md), [`SECURITY.md`](https://github.com/kajisho5/ffmpeg-skill/blob/main/SECURITY.md), `.claude-plugin/`, `scripts/` (42 Python 3.10+ stdlib tools: `probe.py`, `cut.py`, `join.py`, `silence.py`, `fit.py`, `caption.py`, `overlay.py`, `loudness.py`, `render.py`, `check.py`, `look.py`, `_contract.py`), `mcp/` (12 core / 42 full MCP tools), `references/`, `templates/`, `evals/`, `fuzz/` | **MIT** ([`LICENSE`](https://github.com/kajisho5/ffmpeg-skill/blob/main/LICENSE)); requires FFmpeg 6.1+ and Python 3.10+ stdlib (`$0` local execution, no API keys) | Strong engineering discipline: no shell string interpolation, SPEC `contract --json` derived from `argparse`, mandatory `probe.py -> --dry-run --json -> check.py -> look.py` workflow. **Critical Bug Found in Upstream Issues ([`#469` / `#510`](https://github.com/kajisho5/ffmpeg-skill/issues)):** `join.py` writes `xfade` offsets in milliseconds, which can round by 1 frame on long edits — incompatible with Explainer Engine's frame-exact 24fps `episode_timing` contract if used for master assembly! | `SECURITY / LICENSE REVIEWED` -> **Adopt `probe -> dry-run -> check -> contact-sheet look` patterns & diagnostic tools (`probe.py`, `check.py`, `look.py`), while keeping master 24fps assembly strictly in `explainer_engine/production/assemble.py`** |
| **5. claude-plugins-official** | [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official) (commit `b5b01ac`, 4,841 commits, 47.5k stars) | [`.claude-plugin/marketplace.json`](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json), [`plugin-structure/SKILL.md`](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/plugin-structure/SKILL.md), [`skill-creator/SKILL.md`](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/skill-creator/skills/skill-creator/SKILL.md), `plugins/hookify`, `plugins/pr-review-toolkit`, `plugins/security-guidance`, `plugins/claude-md-management` | **Apache-2.0**; official Anthropic marketplace | Authoritative reference for `.claude-plugin/plugin.json`, immutable plugin slugs, `strict: false` skill bundles with commit SHA pinning, and `skill-creator` / `plugin-dev` validation scripts (`validate-hook-schema.sh`). | `SECURITY / LICENSE REVIEWED` -> **Adopt as canonical Plugin & Skill authoring/validation reference** |
| **6. vercel-labs/skills** | [`vercel-labs/skills`](https://github.com/vercel-labs/skills) (`v1.5.25+`, 681 commits, 39.8k stars) | [`README.md`](https://github.com/vercel-labs/skills/blob/main/README.md), [`docs/commands.md`](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), [`skills/find-skills/SKILL.md`](https://github.com/vercel-labs/skills/blob/main/skills%2Ffind-skills%2FSKILL.md) | **MIT**; CLI requires Node.js 22.20+ | Provides `npx skills` CLI and the deterministic `skills-lock.json` (v2) `computedHash` specification (`path length content` SHA-256 over UTF-8 sorted files with CRLF->LF text normalization + pinned Git SHA). Sends anonymous telemetry unless `DISABLE_TELEMETRY=1` / `DO_NOT_TRACK=1` is set. | `SECURITY / LICENSE REVIEWED` -> **Adopt the `skills-lock.json` v2 `computedHash` algorithm in Python stdlib (`explainer_engine`) without requiring Node.js runtime in production** |
| **7. Agent Skills Specification** | [`agentskills.io/specification`](https://agentskills.io/specification) (Linux Foundation / Agentic AI Foundation) | Full specification page inspected: directory layout (`SKILL.md`, `scripts/`, `references/`, `assets/`), frontmatter schema (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`), and 3-tier progressive disclosure (`~100` tokens metadata, `< 5,000` tokens body, on-demand resources) | **Open Standard** (Linux Foundation) | 100% compatible with Claude Code native skills ([`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills)). Existing 21 `.claude/skills/*/SKILL.md` files in this repo already have valid `name` and `description` frontmatter; adding `license: Proprietary` / `MIT` and keeping bodies `< 500` lines aligns them completely. | **APPROVED STANDARD** (baseline format for all project Skills) |

### 5.2 Comparison of Competing Candidates by Domain

| Domain | Evaluated Candidates | Comparative Strengths & Weaknesses | Winner / Project Recommendation |
|---|---|---|---|
| **AI Film Direction & Shot Planning** | 1. **Existing Repo:** `.claude/skills/shot-visuals/SKILL.md` + `story-engine` + `explainer_engine/videolane/` ([VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md))<br>2. [`wuwangzhang1216/DirectorSKILL`](https://github.com/wuwangzhang1216/DirectorSKILL) (`cinematic-director` v2.0)<br>3. [`zhuyansen/awesome-claude-video-skills`](https://github.com/zhuyansen/awesome-claude-video-skills) | `DirectorSKILL` v2.0 has superior progressive-disclosure routing (Modes A–J), coded failure diagnosis (`F1–F19`), and model capability prompt shapes (`S1–S4`), whereas existing repo skills are tightly bound to `ProductionScriptV4`, `continuity_card/1`, and LTX-2.5 distilled rules ([VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md), [EPISODE\_FIRST.md](https://www.google.com/search?q=../EPISODE_FIRST.md)). | **Hybrid Internal + Selective Adaptation:** Keep `.claude/skills/shot-visuals/` and `videolane/` as authoritative; port `DirectorSKILL`'s `F1–F19` failure-diagnosis taxonomy and routing-table pattern into `shot-visuals/references/` (with MIT attribution, stripping named-director overlays that violate `no_names` in [UNIVERSAL\_RULE\_BASE.md](https://www.google.com/search?q=../UNIVERSAL_RULE_BASE.md)). |
| **Blender 3D & MCP Integration** | 1. **Existing Repo:** `explainer_engine/blender/*` (48 modules, headless `bpy` CLI)<br>2. [`RobLe3/cc-blender-skill`](https://github.com/RobLe3/cc-blender-skill) (v1.4.0, 30 skills, dual MCP)<br>3. `zq940222/blender-mcp-skill` (404 / unverified)<br>4. [`ahujasid/mcp-for-blender`](https://github.com/ahujasid/mcp-for-blender) (raw socket MCP server)<br>5. [`arjun988/blender-skills`](https://github.com/arjun988/blender-skills) (94 micro-skills)<br>6. [`kevinbadi/blender-skills`](https://github.com/kevinbadi/blender-skills) | `explainer_engine/blender/` is deterministic, headless, and tested by unit tests; `ahujasid/mcp-for-blender` provides only raw socket execution without workflow guardrails; `arjun988/blender-skills` (94 skills) creates excessive startup metadata token overhead (~9,400 tokens); `RobLe3/cc-blender-skill` v1.4.0 is well-structured, MIT-licensed, and supports both Official Blender 5.1 MCP and `ahujasid`. | **Keep `explainer_engine/blender/` as primary tool; rank `RobLe3/cc-blender-skill` #1 external candidate** (isolated for legacy / free PC benchmark tasks only; disabled in v4.3 episodes per [EPISODE\_FIRST.md](https://www.google.com/search?q=../EPISODE_FIRST.md)). Reject `zq940222` (404). |
| **FFmpeg Video/Audio Processing** | 1. **Existing Repo:** `explainer_engine/production/assemble.py` + `explainer_engine/audio/stems.py` + `tools/render_tools/{build_segments,mix}.py`<br>2. [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill) (v3.10.1, 42 stdlib tools + MCP)<br>3. [`ychoi-kr/claude-ffmpeg-skill`](https://github.com/ychoi-kr/claude-ffmpeg-skill) (shell presets)<br>4. [`n0an/ffmpeg-skill`](https://github.com/n0an/ffmpeg-skill) (recipe markdown)<br>5. [`digitalsamba/claude-code-video-toolkit`](https://github.com/digitalsamba/claude-code-video-toolkit) | `ychoi-kr` and `n0an` rely on raw shell recipes that encourage agent guessing; `kajisho5/ffmpeg-skill` enforces `probe.py -> --dry-run --json -> check.py -> look.py` with zero shell strings and Python stdlib, but its `join.py` uses millisecond `xfade` offsets (upstream issue `#469`) whereas our `assemble.py` + `timing.py` enforce 24fps frame-exact clock alignment (`episode_timing/1` & `/2`). | **Keep `assemble.py`, `stems.py`, `build_segments.py`, and `mix.py` as sole production writers**; rank [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill) #1 external reference for read-only media probing, delivery checking, and contact-sheet inspection patterns. |

---

## 6. Skill Evaluation Rubric & 9-Stage Lifecycle State Machine

### 6.1 Quantitative Evaluation Rubric (100-Point Scale + Hard Veto Gates)

Every candidate Skill, Plugin, MCP server, or Tool is scored across 11 dimensions before advancing past `TECHNICALLY EVALUATED`:

| # | Dimension | Weight | Pass Threshold & Evaluation Criteria |
|---|---|---|---|
| 1 | **Task Relevance & Functional Coverage** | 15 pts | Solves a documented v4.3 pipeline or developer workflow gap without duplicating existing `explainer_engine/` modules |
| 2 | **Internal Instruction & Workflow Quality** | 15 pts | Step-by-step deterministic procedure, explicit stop/ask gates, progressive disclosure (`SKILL.md < 500` lines), zero vague adjective soup |
| 3 | **Claude Code Native Compatibility** | 10 pts | Valid YAML frontmatter (`name`, `description`), works with `.claude/skills/`, subagent `skills` preloading, and `.claude/settings.json` hooks |
| 4 | **Tool / MCP Compatibility** | 10 pts | Clear separation between Skill instructions and executable Tool; maps cleanly to repository Python CLIs or vetted local MCP servers |
| 5 | **Maintenance & Reproducibility** | 10 pts | Active commit history, tagged releases, changelog, pinned commit SHA, and reproducible behavior |
| 6 | **Validation & Test Evidence** | 10 pts | Ships unit tests, `evals/evals.json`, or deterministic check scripts with honest failure documentation |
| 7 | **License & Provenance** | 10 pts | **HARD VETO GATE:** Must carry an explicit permissive license (`MIT`, `Apache-2.0`, `BSD`) or verified first-party ownership; unknown/unlicensed repos are blocked |
| 8 | **Security & Execution Permissions** | 10 pts | **HARD VETO GATE:** Zero unreviewed shell execution, zero credential exfiltration, zero unauthorized network calls, and full compliance with `.claude/settings.json` hooks |
| 9 | **Dependencies & Installation Complexity** | 5 pts | Prefers Python stdlib and existing repo binaries (`ffmpeg`, `python3`) over heavy new runtime stacks |
| 10 | **Financial Cost** | 0 pts (Veto) | **HARD VETO GATE:** Must be strictly **$0.00** to install, load, and validate locally; any tool capable of spending money must be fenced by `spend_caps.json` and `PreToolUse` hooks |
| 11 | **Context & Token Overhead** | 5 pts | Startup metadata `<= 120` tokens; activated `SKILL.md` body `< 5,000` tokens; MCP `tools/list` footprint `<= 15` core tools |

### 6.2 Mandatory 9-Stage Lifecycle State Machine

No discovered Skill, Plugin, or MCP server may skip states or auto-install:

~~~text
DISCOVERED
  -> CONTENT REVIEWED (10-dimension full-text inspection of SKILL.md, scripts, references, issues)
  -> TECHNICALLY EVALUATED (rubric scored + compared against competing alternatives & existing repo code)
  -> SECURITY / LICENSE REVIEWED (SPDX license verified, scripts audited, $0 cost & hook compliance proven)
  -> SANDBOX VALIDATED (deterministic local $0 positive/negative trigger & functional tests pass in isolated worktree/tmp)
  -> OWNER APPROVED (explicit creator sign-off recorded in DECISION_LOG.md / governance records)
  -> INSTALLED (committed to .claude/skills/ or registered with pinned commit SHA + computedHash)
  -> PRODUCTION VALIDATED (verified on an actual episode dry-run / gate check with 0 regressions)
  -> UPDATE / DEPRECATION REVIEW (periodic hash/upstream check; retired items receive dated legacy banner)
~~~

---

## 7. Central Registry Architecture (Skills, Plugins, MCP Servers & Executable Tools)

To maintain a single auditable inventory without introducing runtime database complexity, the central registry is designed as four linked, schema-validated tables documented in this specification (and optionally mirrored as a read-only JSON manifest `config/claude_ecosystem_registry.json` in a future Owner-approved implementation step):

### 7.1 Required Registry Fields & Provenance Hash (`computedHash`)

Every registry entry records:
1. `canonical_name` (kebab-case identifier matching directory/slug)
2. `kind` (`skill` | `plugin` | `mcp_server` | `executable_tool`)
3. `functional_domain` (`story` | `visual` | `videolane` | `audio` | `maps` | `blender_legacy` | `assembly` | `cloud_cost` | `qa_governance`)
4. `description_and_capabilities`
5. `source_repository` (canonical URL or `vano1919/explainer-engine` for first-party)
6. `exact_version_or_commit_sha` (40-char Git SHA or semantic tag + SHA)
7. `integrity_hash` (deterministic `computedHash` per [`vercel-labs/skills` v2 lock specification](https://github.com/vercel-labs/skills): UTF-8 sorted relative file paths, CRLF->LF text normalization, `SHA256(path + "\0" + decimal_byte_len + "\0" + content)`)
8. `license_and_attribution` (SPDX identifier + copyright notice path)
9. `required_tools` (linked `executable_tool` IDs)
10. `required_mcp_servers` (linked `mcp_server` IDs)
11. `claude_code_compatibility` (minimum Claude Code version, frontmatter extensions used, cloud vs. local session support)
12. `dependencies` (Python version, packages, system binaries)
13. `lifecycle_state` (one of the 9 states in Section 6.2)
14. `validation_evidence` (test file path, `docs_lint` / `test_agent_governance.py` status)
15. `owner_approval` (`DEC-*` ID or `Built-in repository baseline`)
16. `update_policy` (`pinned-manual-review` — never auto-updated)

### 7.2 Initial Linked Registry Snapshot (First-Party Baseline + Evaluated Candidates)

#### A. Project Skills Registry (Summary of 21 Active First-Party + 4 Evaluated External Candidates)

| Canonical Name | Domain | Source & Version/SHA | Integrity / Provenance | License | Required Tools / MCP | Lifecycle State | Owner Approval |
|---|---|---|---|---|---|---|---|
| `story-engine`, `dialogue-scenes`, `narration-script`, `science-grounding`, `crossover-episode`, `time-jump-episode` (6 skills) | `story` | `vano1919/explainer-engine` @ `eb80e443` (`a060cf0b`) | First-party tracked in Git (`.claude/skills/*`) | Repo Proprietary | `explainer_engine.scripting.*`, `explainer_engine.standards.rulebook` | `PRODUCTION VALIDATED` | Baseline ([DECISIONS\_AND\_OPEN\_QUESTIONS.md](https://www.google.com/search?q=../DECISIONS_AND_OPEN_QUESTIONS.md)) |
| `shot-visuals`, `visual-beats`, `animated-universe`, `animation-principles`, `cartography` (5 skills) | `visual` / `maps` | `vano1919/explainer-engine` @ `eb80e443` (`a060cf0b`) | First-party tracked in Git (`.claude/skills/*`) | Repo Proprietary | `explainer_engine.videolane.*`, `explainer_engine.maps.*`, `explainer_engine.production.*` | `PRODUCTION VALIDATED` | Baseline ([EPISODE\_FIRST.md](https://www.google.com/search?q=../EPISODE_FIRST.md), [VIDEO\_LANE.md](https://www.google.com/search?q=../VIDEO_LANE.md)) |
| `elevenlabs-voice`, `voice-search`, `editing-style`, `video-editing-architect`, `shorts-for-video` (5 skills) | `audio` / `assembly` | `vano1919/explainer-engine` @ `eb80e443` (`a060cf0b`) | First-party tracked in Git (`.claude/skills/*`) | Repo Proprietary | `explainer_engine.audio.*`, `explainer_engine.production.assemble`, `mcp__ElevenLabs__*` (guarded) | `PRODUCTION VALIDATED` | Baseline ([EPISODE\_FIRST.md](https://www.google.com/search?q=../EPISODE_FIRST.md)) |
| `cloud-cost-audit`, `cloud-provider-selection`, `hyperstack-operations`, `modal-operations`, `lora-training` (5 skills) | `cloud_cost` | `vano1919/explainer-engine` @ `eb80e443` (`a060cf0b`) | First-party tracked in Git (`.claude/skills/*`) | Repo Proprietary | `explainer_engine.cloud.*`, `explainer_engine.training.*` | `PRODUCTION VALIDATED` | Baseline ([CLOUD\_RUNBOOK.md](https://www.google.com/search?q=../CLOUD_RUNBOOK.md)) |
| `cinematic-director` (external candidate) | `visual` | [`wuwangzhang1216/DirectorSKILL`](https://github.com/wuwangzhang1216/DirectorSKILL) @ `c65ae0d` (`v2.0.0`) | External Git SHA `c65ae0d` | `MIT` | None (pure Markdown) | `SECURITY / LICENSE REVIEWED` (adapt `F1–F19` & routing table only; do not install raw) | Pending (`DEC-2026-11-17-02`) |
| `cc-blender-skill` (external candidate) | `blender_legacy` | [`RobLe3/cc-blender-skill`](https://github.com/RobLe3/cc-blender-skill) (`v1.4.0`) | External release tag `v1.4.0` | `MIT` | `blender >= 5.1` (or `4.0+`), Blender MCP server | `SECURITY / LICENSE REVIEWED` (hold for legacy / PC benchmark only; retired in v4.3) | Pending (`DEC-2026-11-17-02`) |
| `ffmpeg-skill` (external candidate) | `assembly` | [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill) @ `f1c97cb` (`v3.10.1`) | External Git SHA `f1c97cb` | `MIT` | `ffmpeg >= 6.1`, `ffprobe`, Python 3.10+ stdlib | `SECURITY / LICENSE REVIEWED` (adapt read-only probe/check/look patterns; keep 24fps assembly in `assemble.py`) | Pending (`DEC-2026-11-17-02`) |
| `blender-mcp-skill` (`zq940222`) | `blender_legacy` | `https://github.com/zq940222/blender-mcp-skill` | HTTP 404 / unverified | Unknown | Unknown | **REJECTED (`UNVERIFIED SOURCE`)** | Rejected |

#### B. MCP Server & Executable Tool Registry

| Canonical ID | Kind | Transport / Binary | Capabilities & Scope | Security & Cost Gate | Lifecycle State |
|---|---|---|---|---|---|
| `mcp__ElevenLabs` | `mcp_server` | Claude Connector / MCP | Voice library search (`creative_list_voices`, free) and TTS/SFX generation (`creative_generate_speech`, paid) | Guarded by `.claude/settings.json` `PreToolUse` -> `explainer_engine.standards.hook` (blocks pictures/video, enforces `generations_count=1`, `paid_assets` gate, `script_approval`, `editorial_gate`, and library lookup) | `PRODUCTION VALIDATED` |
| `hyperstack-docs-mcp` | `mcp_server` | HTTP MCP (`https://docs.hyperstack.cloud/mcp`) | Read-only documentation search for Hyperstack GPU VMs and APIs | Read-only ($0); documented in `.claude/rules/cloud-platforms.md` Section 5 | `SECURITY / LICENSE REVIEWED` |
| `hyperstack-console-mcp` | `mcp_server` | HTTP MCP (`https://console.hyperstack.cloud/ai/mcp`) | Privileged account control-plane MCP (can create/delete VMs) | **Restricted:** mutating calls forbidden without all preflight gates and explicit Owner approval (`.claude/rules/cloud-platforms.md`) | `SECURITY / LICENSE REVIEWED` (read-only inventory only) |
| `explainer-episode-runner` | `executable_tool` | `python -m explainer_engine.episode` | Canonical v4.3 G1–G10 episode pipeline runner (`run.py`, `timing.py`, `router.py`, `acceptance.py`) | Enforces `retired.refuse`, `spend_caps.json`, `load_clock`, and `clock_sha256` fingerprints | `PRODUCTION VALIDATED` |
| `explainer-cloud-managers` | `executable_tool` | `python -m explainer_engine.cloud.{runpod,paid_offer,providers}` | Guarded RunPod lifecycle manager and Modal `paid_offer/1` preflight checker | Enforced by `.claude/settings.json` `PreToolUse` (`Bash`) -> `explainer_engine.cloud.hooks` | `PRODUCTION VALIDATED` |
| `ffmpeg-local` | `executable_tool` | Local CLI (`ffmpeg`, `ffprobe`) invoked via `explainer_engine/production/assemble.py` & `tools/render_tools/` | Frame-exact 24fps segment building, EBU R128 stem mixing, and chunked MP4 assembly | Local CPU/GPU only ($0.00); clock alignment verified via `ET.load_clock()` | `PRODUCTION VALIDATED` |

---

## 8. Repeatable Zero-Cost Validation & Regression Strategy

Every new or updated Skill, Agent, Hook, Plugin, or Tool integration must pass a **7-layer deterministic, $0 local validation suite** before activation:

1. **Frontmatter & Structural Lint (`$0`, local Python):**
   - Verify `SKILL.md` frontmatter (`name` matches directory and `^[a-z0-9]+(-[a-z0-9]+)*$`, `description` non-empty `<= 1024` chars, body `< 500` lines / `< 5,000` tokens, no unclosed code fences, all relative links in `SKILL.md` resolve 1 level deep).
   - Verify `.claude/agents/*.md` against `config/model_routing.json` via `pytest tests/unit/test_agent_roles.py tests/unit/test_agent_governance.py tests/unit/test_t3_agent_skill_banners.py`.
2. **Documentation & ID Single-Home Lint (`$0`, local Python):**
   - Run `python -m explainer_engine.docs_lint` (`0 finding(s)` required) to ensure no rule ID is duplicated across `docs/` and `.claude/`.
3. **Deterministic Hook Denial & Allow Tests (`$0`, local `pytest`):**
   - Run `pytest tests/unit/test_governance_hooks.py tests/unit/test_money_path_fences.py` on synthetic `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, and `PreModelSwitch` JSON stdin payloads to prove every security and spend fence denies unauthorized calls (exit code `2` or `permissionDecision: deny`) and allows valid read-only calls (exit code `0`).
4. **Positive & Negative Trigger Evaluation (`$0` static rubric check; paid LLM evals gated on Owner approval):**
   - Each Skill maintains an `evals/evals.json` file with at least 10 positive trigger prompts (must match description keywords/intent) and 10 negative trigger prompts (near-miss domains that must NOT trigger the skill).
   - Local static keyword/intent overlap and token-budget checks run at **$0.00**; executing live multi-turn LLM benchmark runs via `skill-creator` is classified as a token-consuming run and requires explicit Owner approval.
5. **Tool-Call & Contract Verification (`$0`, local dry-run):**
   - Any script in `scripts/` or tool in `explainer_engine/` referenced by a Skill must support `--help` and `--dry-run` (or fixture-based `pytest`) and validate its outputs against `explainer_engine/core/contracts.py`.
6. **Context & Token Overhead Measurement (`$0`, local character/token counter):**
   - Measure total startup metadata across all `.claude/skills/*/SKILL.md` descriptions (target `< 2,500` tokens total) and all `.claude/agents/*.md` descriptions (hard ceiling `< 15,000` tokens per Claude Code startup warning limit; project target `< 3,000` tokens).
7. **Provenance & Integrity Lock Verification (`$0`, local SHA-256):**
   - Verify that every external or adapted Skill matches its recorded Git commit SHA and `computedHash`.

---

## 9. Security and $0 Cost Gates for the Claude Code Ecosystem

All Claude Code extensions operate under the project's binding **$0.00 default execution policy** and existing `.claude/settings.json` hook architecture:

1. **Zero Paid Calls Without Gates:** No Skill, Subagent, Plugin, or MCP server may initiate a paid LLM API call, paid image/video generation, paid ElevenLabs TTS/SFX call, or paid cloud GPU job (RunPod, Modal, Hyperstack) without passing all preflight gates ([ORCHESTRATION.md](https://www.google.com/search?q=../ORCHESTRATION.md), [CLOUD\_RUNBOOK.md](https://www.google.com/search?q=../CLOUD_RUNBOOK.md)), `config/spend_caps.json`, and explicit Owner approval.
2. **No Automatic Installation or Auto-Update:** `npx skills update`, `/plugin update`, or unpinned `git pull` inside `.claude/` are forbidden in automated flows. All third-party skills/plugins are copied (`--copy`) after review and pinned to an immutable commit SHA and `computedHash`.
3. **Hook & MCP Privilege Containment:**
   - Imported plugins must never register unrestricted `PreToolUse` / `PostToolUse` shell hooks or auto-start privileged control-plane MCP servers without a dedicated `.claude/settings.json` `PreToolUse` matcher (`mcp__<server>__.*` or `mcp__plugin_<plugin>_<server>__.*`) enforcing repository approval gates.
   - Note per [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents): plugin subagents ignore `hooks`, `mcpServers`, and `permissionMode` frontmatter fields; therefore, security-critical agents must reside in `.claude/agents/` under project hook governance rather than inside third-party plugins.
4. **Telemetry & Credential Hygiene:** Set `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1` whenever running third-party discovery CLIs (`npx skills`), and never pass `.env`, `vault.json`, or API keys to external skill scripts.
