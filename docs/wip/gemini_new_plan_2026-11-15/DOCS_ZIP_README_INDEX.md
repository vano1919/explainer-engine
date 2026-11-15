# 04_DOCS — index (Truce 1914, first full film pass 1, 2026-11-15)

Read in this order. Everything here is text; the videos and pictures are the separate attachments 01-08.

## 1_film_plan_pass1/ — the plan and logs that produced the pass-1 film (the film you are judging)
- `SHOT_PLAN.md` — human-readable shot plan, all 84 shots: line, picture, camera, living effects, sound per shot, music per segment, known renderer defects. START HERE.
- `shot_plan.json` — the same as data (84 shots: shot id, segment, route video / still_25d / map_action, slot start and length on the film clock, lines, mood, picture URL, current clip URL, camera, effects, sound).
- `CORRECTIONS_LOG.md` — every correction so far (part A: specific defects and fixes; part B: every shot's director brief before and after the rewrite). `CORRECTIONS_LOG_render_copy.md` is the earlier copy kept by the render side.
- `edit_points.json` — clip in/out trims; `picture_overrides.json`; `ltx_whisper_small_en_2026-11-15.json` — what Whisper heard in every LTX clip.
- `inputs_manifest.json` — every input used: 79 pictures, 56 LTX clips, 72 voice reads, clock, sound library (URLs are private; the pictures and clips themselves are attached as 01-08).
- `audio_gaps.json` — sounds the plan asked for that the library did not have, and the substitutes used.
- `GALLERY.md`, `gallery_table.json` — the shot gallery (photo + clip per shot).

## 2_script/ — the episode script (this is what the new plan must also rewrite)
- `production_script.json` — the full production script (story, segments, lines, beats, prompts, edit plan).
- `claim_map.md`, `research_dossier.md` — the facts and their sources (keep every fact sourced).
- `sound_plan.json`, `av_events.json` — the older sound plan and AV events of this episode.

## 3_journals/ — what went wrong and why
- `INCIDENT_JOURNAL_2026-11-14.md` — the shared incident journal of all threads (time, shot/file, what happened, cause, what was done, what remains).
- `INCIDENT_JOURNAL_part_clips_lane.md` — incidents of the clips lane.
- `INCIDENT_JOURNAL_argon_loop.md` — incidents and code causes found in your (Argon/Gemini) earlier code sessions.
- `INCIDENT_AUDIT_2026-11-15.md` — audit of 76 incidents (34 fixed with a regression guard, the rest open).
- `RULES_RECONCILIATION_JOURNAL.md`, `LIVING_PHOTO_RULES_2026-11-14.md` — rule changes and the living-photo (2.5D) rules.

## 4_previous_plan_argon/ — the PREVIOUS plan (no longer wanted as a plan; read it for what exists and what failed)
- `01..37_*` — your earlier sessions: prompts, replies, plan (`04_PLAN.md`, `32_/35_ARGON_TASK2_PLAN_R1/R2.md`), code tasks and changes, Opus and ChatGPT reviews, maps work, director design.
- `project_files_latest_tasks_2026-11-15/` — the last task prompts of 2026-11-15 (task 1 logic fixes, task 2 improvements, task 3 system check).
- `s7_regenerated_directions/` — example director outputs.

## 5_sound/
- `SOUND_INTEGRATION_GUIDE.md` (+ `_v2`) — how sound is meant to be layered.
- `SOUND_LIBRARY_FILE_LIST.md` — every free sound file we already own (names, sizes; the audio itself is not attached).
- `sound_library_2026-11-15_additions_manifest.json` — the 63 Mixkit additions + Kevin MacLeod "Silent Night" with licences.

## 6_render_tools/ — the small scripts the pass-1 assembly ran on the Mac (mix, segment build, direction, edits).

The full code of the repo is the separate attachment `09_REPO_TEXT_branch_o239rq_40c860f.zip` (text files only; skills in `.claude/skills/`, agents in `.claude/agents/`, code in `explainer_engine/`).
