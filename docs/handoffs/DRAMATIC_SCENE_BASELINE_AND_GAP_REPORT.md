# Explainer Engine v4.2 — Dramatic Scene Storytelling & Cold-Open Integration Baseline & Gap Report

**Date:** 2026-11-11  
**Baseline Archive:** `explainer_engine_v4_2_canonical_reconciled.zip` (`7,067,094` bytes, `1,351` files)  
**Verified Baseline SHA-256:** `bb39dd6fd49ee8e95664bbd45223b92ae979fc0b09754c4584d51b08aef481ff`  
**Controlling Handoff:** `EXPLAINER_ENGINE_DRAMATIC_SCENE_HOOK_INTEGRATION_ARGON_PROMPT_2026-11-11.md`

## 1. Step 0 — Source of Truth Verification & Snapshot Comparison

1. **Drive Artifacts Verified:**
   - `explainer_engine_v4_2_canonical_reconciled.zip` (`SHA-256: bb39dd6fd49ee8e95664bbd45223b92ae979fc0b09754c4584d51b08aef481ff`, `7,067,094` bytes, `1,351` files).
   - `Explainer_Engine_V4_2_Master_Colab_Pipeline.ipynb` (`29,874` bytes, 10 executable cells covering Gates G0–G9).
2. **Comparison Between GitHub `main` (`production_script/3` + `film_shots/1..3`) and Canonical Drive v4.2 (`schema_version: "4.0.0"`):**
   - The repository contains **both** the rich legacy `/3` Story Engine modules (`docs/STORY_ENGINE.md`, `docs/research/DOCUDRAMA_REFERENCE_LIBRARY.md`, `.claude/skills/story-engine/SKILL.md`, `.claude/skills/dialogue-scenes/SKILL.md`, `.claude/agents/story-architect.md`, `.claude/agents/scene-writer.md`, `.claude/agents/beat-writer.md`, `.claude/agents/edit-planner.md`, `.claude/agents/script-critic.md`, `explainer_engine/scripting/story_lint.py`, `explainer_engine/scripting/scene_lint.py`, `explainer_engine/scripting/film_shots.py`, `explainer_engine/production/editorial_gate.py`) **and** the v4.0/v4.2 12-minute docudrama pipeline (`schemas/production_script.schema.json`, `orchestration/cohesive_film_engine.py`, `orchestration/rule_enforcer.py`, `qa/viewer_critic.py`).
   - **Root-Cause Disconnect Identified:** When `schema_version == "4.0.0"` was introduced, `story_lint.lint(doc)` and `scene_lint.lint(doc)` were branched early (`if doc.get('schema_version') == '4.0.0': return lint_v4(doc)`). While `lint()` on `/3` enforced `ST-14` (narrator setup -> exchange -> consequence), `ST-21` (no double exposition), `SC-01..SC-06` (scene header, opposing wants, value charge turn, valid addressee in `present`, multi-line exchange with `>= 2` speakers, enter late/leave early), `lint_v4(doc)` only checked speaker existence and lip-sync flags!
   - Similarly, in `explainer_engine/scripting/film_shots.py`, `teaser_of` reuses a later payoff clip (`KP-41`), but hardcodes a centered trim (`start = round(max(0.0, (of["seconds"] - shot["seconds"]) / 2), 2)`) and lacked an optional explicit `teaser_trim: [start_seconds, end_seconds]` field, while v4.0 `ShotSpec` in `production_script.schema.json` lacked `teaser_of` and `teaser_trim` altogether.

## 2. Step 1 — Current Story Generation & Validation Call-Path Trace

| Stage | Input | Output / Owned Fields | Implementation Path | Active Caller | Gate / Test | Verified Status |
|---|---|---|---|---|---|---|
| Stage 1: Story Architect | Research dossier, `claim_map.json` | `drama` (`question`, `promise`, `loops`, `setups`), `segments[].drama`, `segments[].scene` | `.claude/agents/story-architect.md`, `explainer_engine/scripting/variant_plan.py` | `stage_guard start architect` / v4 script generator | `story_lint.py` (`ST-01..ST-24`, `lint_v4`) | `PARTIALLY VERIFIED` (`/3` checks full `drama`/`scene`; v4 `lint_v4` skipped scene-necessity & hand-off checks) |
| Stage 2: Scene Writer | Story skeleton, `scene` header, `cast.<id>.speech` | `segments[].lines` (`/3`) or `audio_lines` (`v4.0`) with `speaker`, `to`/`addressee_id`, `intent` | `.claude/agents/scene-writer.md`, `.claude/skills/dialogue-scenes/SKILL.md` | `stage_guard start writer` | `scene_lint.py` (`SC-01..SC-12`, `lint_v4`) | `PARTIALLY VERIFIED` (`lint_v4` did not check `SC-01..SC-06` or isolated 1-line shouts on v4 scripts) |
| Stage 3: Beat Writer | Approved `lines` / `audio_lines` | `visual_beats` on lines | `.claude/agents/beat-writer.md`, `explainer_engine/production/beats.py` | `production/validate.py` (`VB-01..VB-11`) | `validate.py` | `VERIFIED` on `/3` |
| Stage 4: Edit & Shot Planner | Timed script, `scene` header | `shots` (`film_shots/1..3` or v4 `shots[]`), `teaser_of` | `.claude/agents/edit-planner.md`, `explainer_engine/scripting/film_shots.py` | `film_shots.compose` / `film_shots.check` / `shot_prompt_lint.check_v4_script` | `KP-01..KP-49`, `CF-NO-JUMP-CUT` | `PARTIALLY VERIFIED` (`film_shots.py` hardcoded centered trim on `teaser_of`; v4 `ShotSpec` lacked `teaser_of` & `teaser_trim`) |
| Stage 5: Deterministic Linters | `production_script.json`, `film_shots.json` | Structured `FAIL` / `REVIEW` findings | `story_lint.py`, `scene_lint.py`, `shot_prompt_lint.py`, `cohesive_film_engine.py` | `orchestration/rule_enforcer.py` (`run_all_gate_audits`) | `test_d124_gemini_architecture.py`, `test_v4_2_reconciliation_and_viewer_critic.py` | `VERIFIED` (executes in `run_all_gate_audits`) |
| Stage 6: Independent Critic | Full script (`editorial_review/2` or clean-room `viewer_review_packet/1`) | `editorial_review.json` / `viewer_critic_report/1` | `.claude/agents/script-critic.md`, `production/editorial_gate.py`, `qa/viewer_critic.py` | `editorial_gate.check` / `evaluate_script_with_viewer_critic` | `test_v4_2_reconciliation_and_viewer_critic.py` | `PARTIALLY VERIFIED` (`viewer_critic.py` needs explicit cold-open payoff & isolated-line interruption checks) |

## 3. Step 2 — Reproduction of Current Failure Patterns in Existing Scripts

Direct inspection of `jobs/ep_waterloo_12min/production_script.json` and `jobs/ep_toba_74000bce_12min/ep_toba_74000bce_12min_production_script.json` reproduces the exact storytelling defects described in Part I:

1. **Defect Reproduction #1 — Isolated One-Line Generic Character Interruption & Impossible Addressee (`jobs/ep_waterloo_12min/production_script.json`):**
   - In Segment `S01` (`S01_L001`–`S01_L008`), the narrator speaks two short lines (`S01_L001`–`S01_L002`), and then `S01_L003` inserts a single isolated character line:
     - `speaker_id`: `"char_gerard_1815"`, `addressee_id`: `"char_wellington_1815"` (historically and physically impossible—Gérard is a French general at Wavre 15 miles away from Wellington!).
     - `text`: `"Bring up the heavy cuirassiers now; their center wavers and Bülow's vanguard is still miles behind the river!"`
   - Nobody replies to Gérard; no decision or turn occurs; and in `S01_L004` the narrator immediately resumes general exposition.
   - Worse still, in `S02_L002`, `"char_rothschild_1815"` (in London!) addresses `"char_napoleon_1815"` with the **exact same boilerplate sentence** (`"Bring up the heavy cuirassiers now..."`), and in `S02_L006` `"char_wellington_1815"` addresses `"char_rothschild_1815"` while referring to himself in the third person (`"...before Wellington reinforces the ridge!"`).
2. **Defect Reproduction #2 — Single-Turn Interruption & Narrator Restating Character Action (`jobs/ep_toba_74000bce_12min/ep_toba_74000bce_12min_production_script.json`):**
   - In Segment `S01` (`S01_L004`–`S01_L008`), Sena speaks (`S01_L004`–`S01_L005`), then the narrator interrupts the exchange mid-scene (`S01_L006`) before Kael's single reply (`S01_L007: "The eastern mountains are quiet. Nothing burns there."`), and then `S01_L008` (Narrator) immediately restates Kael's line (`"Kael was right about the local peaks..."`).
   - Additionally, the opening shots (`S01_SH001`, `S01_SH002`) in both v4 scripts do not use `teaser_of` + `teaser_trim` to preview later dramatic payoff scenes (such as the Toba super-eruption detonation in `S02`, the Shinfa waterhole clash in `S05`, or the Ash River standoff with Thar in `S09`).

## 4. Justified Minimal Implementation Plan (Steps 3–14)

1. **`explainer_engine/schemas/film_shots.schema.json` & `explainer_engine/scripting/film_shots.py`:**
   - Add optional `"teaser_trim": [start_seconds, end_seconds]` to `film_shots.schema.json` and `film_shots.py` (`compose` and `episode_check` rule `KP-41`), validating that `0 <= start < end <= payoff.seconds` and `round(end - start, 2) <= shot.seconds`, while preserving the existing centered-trim fallback when `teaser_trim` is omitted.
2. **`explainer_engine/schemas/production_script.schema.json` (`ProductionScriptV4`):**
   - Add optional `teaser_of`, `teaser_trim`, and `shot_role` (`teaser` | `establishing` | `dialogue_ots` | `close_up_turn` | `listener_reaction` | `insert_cutaway` | `action_cutaway` | `scene_exit` | `narration_visual`) on `ShotSpec`, and optional `segment_mode` (`narration_led` | `played_scene` | `visual_action`) and `scene` header (`place`, `time`, `present`, `why_now`, `pov`, `want`, `obstacle_want`, `value`, `open_charge`, `close_charge`, `turn`, `exit`, `surface_topic`, `real_subject`) on `SegmentSpec`.
3. **`explainer_engine/scripting/scene_lint.py` & `explainer_engine/scripting/story_lint.py`:**
   - Extend `scene_lint.lint_v4` and `story_lint.lint_v4` so that v4 scripts enforce:
     - **Cold-Open Teaser Payoff Integrity (`KP-41` / `YT-V4-TEASER-PAYOFF`):** Teaser shots (`teaser_of`) must reference a real later shot (`payoff_idx > teaser_idx`), have valid `teaser_trim` bounds within the payoff shot's duration, and require zero new video generation.
     - **Played-Scene Integrity vs. Narration-Led Freedom (`SC-V4-SCENE-EXCHANGE` & `SC-V4-SCENE-HEADER`):** Segments without character dialogue (`narration_led`) require zero dialogue (no artificial dialogue quota!). Whenever a segment *does* include character dialogue (`played_scene`), it must not be an isolated 1-line slogan/interruption: it requires a genuine exchange (`>= 2` character turns or a complete `scene` contract with `open_charge != close_charge` and `want != obstacle_want`), valid co-present addressees (`SC-V4-ADDRESSEE`), narrator setup before the exchange and narrator consequence after (`ST-14`), and zero duplicate character lines or narrator double-exposition (`ST-21`).
4. **Update `jobs/ep_waterloo_12min/production_script.json` & `jobs/ep_toba_74000bce_12min/ep_toba_74000bce_12min_production_script.json`:**
   - Upgrade both canonical v4 scripts so their openings feature real `teaser_of` + `teaser_trim` previews of later dramatic climax/reversal shots followed by an intriguing narrator hook, convert isolated 1-line character interruptions in `ep_waterloo_12min` (and `ep_toba_74000bce_12min`) into either pure narration-led segments (where narration is stronger) or complete played dramatic scenes (`NARRATOR SETUP -> PLAYED SCENE WITH OPPOSING WANTS & TURN -> NARRATOR CONSEQUENCE`) with full multi-shot coverage (`establishing` -> `dialogue_ots` -> `listener_reaction` -> `insert_cutaway` -> `scene_exit`).
5. **Update `.claude/` Agents/Skills & `explainer_engine/qa/viewer_critic.py`:**
   - Update `.claude/agents/story-architect.md`, `.claude/agents/scene-writer.md`, `.claude/agents/script-critic.md`, `.claude/skills/dialogue-scenes/SKILL.md`, and `explainer_engine/qa/viewer_critic.py` to evaluate the Cold Open teaser payoff, Narration-to-Scene hand-off, Dialogue necessity, and Cinematic Scene Coverage.
