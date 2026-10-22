# Documentation index

One canonical home per specification and per ID (D-23). Link to a document or an ID; never copy its content.

| Document | Canonical for | ID prefix |
|---|---|---|
| [PROJECT_BRIEF](PROJECT_BRIEF.md) | mission, constraints, positioning, scope | |
| [DECISIONS_AND_OPEN_QUESTIONS](DECISIONS_AND_OPEN_QUESTIONS.md) | every decision, open questions, approval gates | D- |
| [MARKET_RESEARCH](MARKET_RESEARCH.md) | seed-evidence register, verification log, topic comparison, vidIQ ledger | SE-, V- |
| [CREATIVE_STYLE_BIBLE](CREATIVE_STYLE_BIBLE.md) | tone, Kit, shape grammar, typography, hook framework | |
| [TITLE_THUMBNAIL_SYSTEM](TITLE_THUMBNAIL_SYSTEM.md) | title patterns, thumbnail spec, packaging QA | |
| [THUMBNAIL_RULES](THUMBNAIL_RULES.md) | click-worthy but honest thumbnails: rules with sources, what the `publish thumbnail` step checks; D-57 | TN- |
| [NARRATION_AND_LANGUAGE_GUIDE](NARRATION_AND_LANGUAGE_GUIDE.md) | voice, vocabulary, anti-patterns, pronunciation | |
| [SCRIPTING_SPEC](SCRIPTING_SPEC.md) | research-to-script gate, format structures, script rubric | |
| [VIDEO_PARAMETER_SPEC](VIDEO_PARAMETER_SPEC.md) | every parameter: default, range, evidence, validation | P- |
| [PRODUCTION_RULES](PRODUCTION_RULES.md) | the gates every video passes in order, the creator's standing orders, the feedback log, planning numbers by length | |
| [VISUAL_WORLD_ARCHITECTURE](VISUAL_WORLD_ARCHITECTURE.md) | how a topic's world and era are resolved and shown (era codex, look v2, anchored hybrid generation, grade, visual QA); proposal D-41 | |
| [WORLD_BIBLE](WORLD_BIBLE.md) | the versioned World Bible (`world/bible.json`) and the reusable asset library (`assets/library.json`): records, versions, approval, duplicate warnings; D-70 stage C | WB- |
| [PRODUCTION_SCRIPT](PRODUCTION_SCRIPT.md) | the one JSON per video (narration, voice, pictures and prompts, sounds, edit), its validation rules PV-01..PV-52 and the command line; D-43 | |
| [STORY_ENGINE](STORY_ENGINE.md) | the writers' room for dialogue what-if episodes: story (ST-), scenes and dialogue (SC-, DW-), performance (PF-), motion and accents (MO-), sound layers (AL-), voice casting from traits (VC-), Shorts styles (SS-), visual beats and their cues, expression sheets (VB-); D-48, D-54, D-55, D-58 | ST-, SC-, DW-, PF-, MO-, AL-, VC-, SS-, VB- |
| [ORCHESTRATION](ORCHESTRATION.md) | how an episode is run alone: phases, hard caps and stops (OR-), time-jump episode structure (SR-), Shorts (SH-) | OR-, SR-, SH- |
| [EDITING](EDITING.md) | editing rules: chunk seams, zoom continuity, one music at a time, transitions and look, speed (ED-) | ED- |
| [SOURCED_RULES](SOURCED_RULES.md) | the sourced production rules (BP-): every number a validator enforces, its sources (article, book, video), status (binding, hypothesis, house) and the code that enforces it; generated from `explainer_engine/standards/sourced_rules.json`; D-59 | BP- |
| [UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) | hook, arc, ABC shots, faces, mood (emotion, light, palette), durations, cuts, motion, transitions | UR- |
| [STORYBOARD_SCHEMA](STORYBOARD_SCHEMA.md) | storyboard contract, animation vocabulary, timing rules | |
| [ASSET_SYSTEM](ASSET_SYSTEM.md) | asset records, naming, licences, generation rules | |
| [AUDIO_SYSTEM](AUDIO_SYSTEM.md) | narration, mix, audio-event contract, licences | |
| [RENDERING_ARCHITECTURE](RENDERING_ARCHITECTURE.md) | current Python/FFmpeg assembler; historical Remotion proposal and renderer decision notes | |
| [PIPELINE_ARCHITECTURE](PIPELINE_ARCHITECTURE.md) | target stages, failure classes, config and job record; current entry points and unimplemented coordinator are marked at the top | |
| [QA_SPECIFICATION](QA_SPECIFICATION.md) | technical and editorial QA, review bundle | Q- |
| [PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md) | cadence, first cycle, candidates, metrics, learning loop | |
| [COST_AND_TIME_MODEL](COST_AND_TIME_MODEL.md) | budgets, estimates, spend ledger, hours | |
| [TOOL_STRATEGY](TOOL_STRATEGY.md) | which tool makes which asset, costs, kit test, RunPod money rules | |
| [TOOLING_RESEARCH](TOOLING_RESEARCH.md) | dated candidate models, providers, storage and watchdogs with sources (stage A of the 2026-10-22 brief); appendices in `research/TOOLING_*_2026-10-22.md` and `research/REPO_AUDIT_2026-10-22.md` | |
| [research/ANIMATION_UNIVERSE_2026-10-22](research/ANIMATION_UNIVERSE_2026-10-22.md) | the creator's 2026-10-22 brief: four candidate animated universes, their concept boards (`imagegen/universe_boards.py`), feasibility, asset-library plan, rig proof of concept; the direction is the creator's choice | |
| [ARCHITECTURE_PLAN_2026-10-22](ARCHITECTURE_PLAN_2026-10-22.md) | the master brief's stages A-H on the real code: Guardian, World Bible, asset library, provider adapters, pilots; the creator's open questions; D-70 | |
| [RISK_REGISTER](RISK_REGISTER.md) | risks and mitigations | R- |
| [RIGHTS_AND_FAIR_USE](RIGHTS_AND_FAIR_USE.md) | rights rules for crossover episodes of fictional worlds | RR- |
| [EPISODE_STANDARDS](EPISODE_STANDARDS.md) | the per-episode rulebook (`episode_rules.json`): legal, platform and creative rules of one video, risk statuses PASS/ADAPT/REVIEW/BLOCK, checkpoints and rechecks; D-51 | ES- |
| [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) | phases, tasks, acceptance, stop conditions | |
| [CLAUDE_EXECUTION_GUIDE](CLAUDE_EXECUTION_GUIDE.md) | phase gates, recovery, never-do list | |
| [REPO_REUSE_AUDIT](REPO_REUSE_AUDIT.md), [PROVENANCE](PROVENANCE.md) | what came from the TMR repository | |
| [PROGRESS](PROGRESS.md) | resumable progress log |
| [CHATGPT_WORKFLOW](CHATGPT_WORKFLOW.md) | ChatGPT-specific repository governance, editorial gate and parallel production workflow | |
| [PLAN_2026-10-15](PLAN_2026-10-15.md) | the approved plan, kept as history; the canonical documents above supersede it | |

Machine-readable sources of truth: `explainer_engine/design/palette.json` (colours), `assets/characters/kit/kit_reference.svg`
(character parts), `explainer_engine/schemas/` (contracts, from Phase 3),
`explainer_engine/standards/policy_baseline.json` (verified policy and law sources for episode rulebooks),
`explainer_engine/standards/sourced_rules.json` (the sourced production rules BP-, rendered into SOURCED_RULES.md).
