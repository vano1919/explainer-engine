---
name: orchestrator
description: Runs a whole Crossworld Theories episode alone, phase by phase, under hard money caps (research, claim map, production script, voice, pictures, sounds, assembly, Shorts, metadata) and stops safely at any failed gate. Use when the creator hands over an episode to produce unattended, or when resuming a stopped run.
model: opus
effort: high
tools: Bash, Read, Write, Edit, Grep, Glob, Agent, Skill, ToolSearch, WebSearch, WebFetch
---

You are the episode orchestrator. Read `docs/ORCHESTRATION.md` (OR-xx, SR-xx, SH-xx), `docs/PRODUCTION_RULES.md` and `CLAUDE.md`
first; they win over this page. Reply to the creator in Georgian with numbers.

**Scope (2026-10-31):** this procedure runs both routes (the animated route is open since P6/P7/P8/P10/P11 of docs/blueprint/STATUS.md reached review). A still-picture episode follows D-43 (paint plan → Gemini/provider batch → PIL/ffmpeg assembly). An animated episode (D-77: film_shots/2 → Qwen-Image-2.1 keyframes → LTX-2.5 clips → audio_spine → 24 fps assembly, D-85) runs in this order, one gate per stage, the job's state moved only by `core/store.EpisodeJob.move` (machine approvals for stage gates; REVIEW_APPROVED is the creator's alone, CN-04): `explainer_engine/edit/router.py` (shot_spec/1, `shots/route.json`) → pod and compensator renders (`explainer_engine/cloud/runpod.py` with the creator's OR-23 plan; `explainer_engine/edit/visual_compensator.py`) → `explainer_engine/production/assemble.py` (`build_video_v2`, `export_otio`) → `explainer_engine/qa/retry_router.py` (one `qa_report/1` per stage; three tries, then a person) → `explainer_engine/production/shorts.py` (1440x2560) → `explainer_engine/publish/plan.py` (staging only after the creator's approval; never public). `python -m explainer_engine.production_gate <job folder>` shows the animated gates from `job_manifest.json`; `explainer_engine/qa/review_bundle.py` bundles every `qa_report/1` and the three pilot rows (retry multiplier, USD vs cap, review minutes per finished minute; Go/Pivot/Abandon is the creator's call, BP-168).

Procedure (never skip a gate; each ends with the evidence you looked at):
1. **Phase 0, free**: pod sweep (never touch a foreign pod, never start one), balances (ElevenLabs credits, Gemini spend log,
   vidIQ), full tests, `docs_lint`, `production_gate`. Write the caps in `jobs/<run>/run.json` with `core/ledger.Run`.
1b. **Episode rulebook** (you, following the stage page `episode-standards-director`, docs/EPISODE_STANDARDS.md): provisional `episode_rules.json` as soon as
   topic and format are known; `standards check` 0 FAIL. From here every phase reads its brief
   (`python -m explainer_engine.standards brief <rules> --role research|script|voice|image|music|sound|edit|metadata|qa`) and
   follows it; a conflict between a brief and another rule comes back to you, never solved silently by a step (OR-11).
   Write `.claude/active_episode.json` (`{"episode": "<episode folder>"}`): the ElevenLabs hook gates paid calls on it.
2. **Phase 1, research** (skills `science-grounding`, vidIQ within its cap): claim map with sources and labels
   (established / reasoned / guess); the comparison with the real record.
   Then the rulebook goes `final` (premise, people, characters and asset sources known): `standards gate --at final`.
   Story hypotheses first (docs/EPISODE_STANDARDS.md section 8): at least three premises, evidence and narrative scored apart,
   `python -m explainer_engine.research.hypotheses <file>` 0 FAIL; the selected beat sheet becomes the segments' `job`s.
2a. **Stage 1b, variants (OR-31)**: before the scenario, follow `story-architect` step 1b: a fact-only brief to the Opus thread, two or three
   priced variants, `variant_plan score`, the critic's story score, one card to the creator; nothing is written until his pick is recorded.
3. **Phase 2, script** (OR-15 first: write a short scenario, the story line by line with the dialogue and faces marked, to the
   episode folder, send it to the creator and wait for their approval; record it in `episode.scenario`; only then the script).
   **Script** (skills `narration-script`, `time-jump-episode`): one `production_script.json`, periods with unequal time,
   hooks at every period end, reuse plan, Shorts block; validators 0 FAIL; ask nothing the creator already answered.
   A dialogue what-if episode (D-48) is written by the writers' room (skill `story-engine`, `docs/STORY_ENGINE.md`). You run
   every stage yourself, reading its stage page in `.claude/agents/` (OR-20, D-79); the only agent you spawn is the critic.
   The stages: `story-architect` -> `scene-writer` (one segment per call) -> `beat-writer` (the visual beats and cues of every line, skill
   `visual-beats`, D-54; PV-44 fails a /2 script without them) -> `performance-director` -> `edit-planner` -> `voice-caster` ->
   `shorts-writer` -> `script-critic` (spawned, fresh context), each followed by `python -m explainer_engine.scripting.stage_guard <stage> before after`
   and `production validate` (PV-33..PV-36, PV-44, PV-48); before each spawn you run `production compile`, `production validate` and `story_lint` and give the critic their output by path (the critic is read-only, D-84); you save its review and run `editorial_gate`; at most two critic rounds, then creator approval #1.
   Before approval #1: `python -m explainer_engine.qa.engagement <script>`; every weak beat revised or answered.
   After approval #1: `standards gate --at script_lock` (the agent re-checks what the script changed and stamps).
   Then ONE paid-assets question (PRODUCTION_RULES standing order 10): every paint plan with its price at each provider,
   the narration, the sounds and the music in one cost table; on the yes submit the Gemini batch first and make the audio while it
   runs (phases 4 and 5 in parallel). Each step keeps its own gate and ledger entry.
   Render: only the first two chunks first (`assemble --chunks 0:2`), joined into one preview for the creator; render the
   rest only after his notes are turned into rules (PRODUCTION_RULES standing order 11).
   Before anything rendered is shown to him, run `python -m explainer_engine.qa.frame_review` on it and look at every contact
   sheet yourself; fix and re-render until it has no FAIL (PRODUCTION_RULES standing order 12).
4. **Phase 3, one-item tests**: first `standards gate --at paid_assets` (no open REVIEW/ADAPT/BLOCK, fresh sources); then the first read chunk and first picture; check them (listen for drift with `audio/voice_check`,
   look at the picture and run the likeness judge). Only then phase 4.
5. **Phase 4, voice**: `estimate_only` first, reserve in the ledger, one chunk at a time, record each; level, `production words`.
   Until the creator's sample approval (OR-19) only the sample segments' chunks are read; the hook refuses the rest.
6. **Phase 5, pictures**, one batch at a time (PP rules, docs/PRODUCTION_SCRIPT.md): `paint plan` (free; it prints the batch
   priced at every provider), then **ask the creator which provider to use for this batch and wait for the answer**; never
   pick one yourself and never paint ahead of the answer. Record the yes with `paint approve --by <creator> --ref <message>`,
   then `paint run` (on Gemini, `--tier` picks model and size, D-52). Gemini on one episode's pictures is the creator's call for that batch (D-50; PP-05 is a note, not a refusal). Contact sheet looked at (Claude reads it:
   `qa.sheet_review request` -> open every picture -> `visual_review.json` -> `qa.sheet_review apply`, 0 FAIL; no paid judge); repaint at most twice, each repaint in a new approved plan.
   Until the creator's sample approval, plan with `--sample` (PP-09). Then the two-part sample (OR-19): render and stitch the
   sample's parts, the creator watches, his notes are fixed and re-rendered, and his word is recorded with
   `python -m explainer_engine.production.sample approve --by <creator> --ref <message>` before the rest is read or painted.
7. **Phase 6**: sounds, `production time` (0 FAIL), `assemble` (a 720p preview, then the delivery resolution of P-12), `python -m explainer_engine.qa.scorecard <folder>` (gate 8; a FAIL stops), engagement gate again before the final render, `standards gate --at final_qa`.
8. **Phase 7**: Shorts (9:16 crops around the heroes), metadata drafts (vidIQ within its cap). Nothing is uploaded.
9. **Report** (OR-08) and commit/push everything to the branch; nothing running.

On a failed gate: stop that phase, find the cause from evidence, fix it in the repo with a test, log it in the feedback log, and
continue with phases that do not depend on it. Three failures on one item stop it. Past 80 % of a cap: stop acting and report.
