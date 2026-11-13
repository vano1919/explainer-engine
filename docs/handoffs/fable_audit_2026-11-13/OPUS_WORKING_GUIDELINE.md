# Working guideline for the Opus high thread (after the Fable audit, 2026-11-13)

Read `FABLE_AUDIT_REPORT.md` (same folder) first: the findings FA-01..FA-18, the proposals P1..P9 and the creator's questions
Q1..Q7 are defined there and only cited here. This file says what to do, in which order, and when each step is done.

Goal: one integration branch off `systemic/next-video` that holds the sound line, the AV line, the video lane, the Gemini
picture line and the picture route, with the five blocking faults fixed and the script-writing stage taught the new contracts,
so that the Toba script passes G1 honestly and the next step is the priced sample.

## Rules for this work

- Free work only. No ElevenLabs, Gemini, Modal or LTX call. A paid step needs the OR-23 plan and the creator's word.
- The worker `training/pods/ltx/modal_ltx_jobs.py` and `launch.json` are not edited before phase P5; any change to them means
  the ladder runs again before paid LTX.
- Protected files of D-133 (cheapest-run gate) and `config/spend_caps.json`, `config/model_routing.json` stay untouched.
- Never weaken or delete a test (invariant 10). A test that asserted the old behaviour is rewritten to assert the new rule, with
  the rule id in its docstring.
- Every step: a focused test, a `docs/PROGRESS.md` entry, the decision log when a decision moves (invariant 11). New rule rows
  need their sources (D-59) or the creator's dated house call; where neither exists the row is `hypothesis` and REVIEW.
- Real merge commits, no squash and no rebase of the merged branches: containment must stay provable with
  `git merge-base --is-ancestor`.
- The creator's open questions (report section 5) are not answered by the thread. Until he answers, use the stated defaults.
- Routine steps are marked (routine); the coordinator may give those to a Sonnet thread.

## P0. Integration branch (mechanical)

1. Branch off `origin/systemic/next-video` (`6b5a1b5`).
2. `git merge --no-ff origin/claude/project-thread-98b6wy` (brings #163, #169, #171, #174). No conflict: the base is an
   ancestor.
3. `git merge --no-ff origin/claude/project-thread-lncsi3` (brings #172, #175 and the sixteen older heads). Six conflicts:
   - `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/EPISODE_FIRST.md`, `docs/PROGRESS.md`, `docs/SOURCED_RULES.md`: keep both
     sides, video-lane numbering wins (D-133 cheapest run, D-135 AV, D-136 W1 sound, D-137 video lane).
   - `explainer_engine/schemas/production_script.schema.json`: keep both `motion_profile` (AV) and `edit_plan` (video lane).
   - `explainer_engine/episode/run.py`, two hunks. In `stage_clips` the cache key takes both sides:
     ```python
     evs = av_events.get(sid, {}).get("events", [])
     renderer = MA.RENDERER_VERSION if is_map else L25.RENDERER_VERSION
     files = [start, end] + ([_sha(ep.root / "production" / "video" / f"{sid}.json")] if route == "video" else [])
     key = _clip_key(sh, files, ep, spines.get(sid), evs, renderer)
     ```
     In `stage_sound` keep the AV return block and add `"voice_track": "audio/voice_track.json" if voice_rep else None`.
   - `standards/sourced_rules.json` merges by itself; run `tests/unit/test_sourced_rules.py` right after.
4. FA-08: rename the AV side's "D-133 = W1 sound" to D-136 in `audio/stems.py` (four places), `tests/unit/test_v43_sound_plan.py`,
   `docs/EPISODE_FIRST.md` SP-02, `docs/SOUND_LIBRARY.md`, and the AV PROGRESS entries. `grep -rn "D-133"` must then show only the
   cheapest-run decision.
5. `git merge --no-ff origin/claude/project-thread-1hrknf` (A line: #165, #166, #168, #170). Conflict: `docs/PROGRESS.md`, keep
   both.
6. `git merge --no-ff origin/claude/project-thread-96iqtm` (#167, commit `db59807`, GC-21). Conflict:
   `docs/GEMINI_CONSISTENCY_RULES.md`, keep the GC-21 row beside the newer rows.
7. `git merge --no-ff origin/claude/project-thread-eczgwr` (#173, `config/picture_route.json`). Conflict: `docs/PROGRESS.md`,
   keep both.
8. Run `python -m pytest -q` and `python -m explainer_engine.docs_lint`. Report section 8 lists what fails on this tree before
   any fix; nothing beyond that list may fail.

Done when: the seven merges are in, the suite result equals the list in the report or better, and one PROGRESS entry names the
merged PRs.

## P1. Blocking fixes (in this order)

### 1.1 FA-01: the G1 fit row reads the LTX model
`episode/run.py stage_script`: the `video_shots_fit_the_model` row uses the LTX launch (`training/pods/ltx/launch.json`,
`native.max_frames`) and `videolane/plan.clip_seconds` (so a spoken shot is judged by onset + line + tail + handle, VL-06, and a
narrated shot by its length + handles). `gemini_task/timing.py` reads the same launch. The Wan fit code stays for the legacy
route and its tests.
Test: a 9 s video shot passes, an 11 s one FAILs and names the LTX limit; the Toba script no longer reports Wan.

### 1.2 FA-04: the Gemini queue speaks `video` (routine)
`gemini_task/queue.py`: `BUCKET` and the target map use `video`; a legacy `wan` is read through `router.LEGACY_ROUTES`, never
written. `texts/drive_pack/04_VIDEO_SCRIPT_RULES.md`: `wan` becomes `video`; add the two rules the video lane needs: a
`continuation` shot asks for no start picture (its first frame is the previous clip's hand-over frame), a `coverage` shot takes
the scene master as its first reference. The text test of the drive pack covers both sentences.
Test: the queue of the Toba script builds with 55 video rows; a continuation shot has no picture row.

### 1.3 FA-05: schema and guides agree
`production_script.schema.json`, all optional: on a shot `intentional_silence` (object: `reason`, required) and `sound_design`
as the guide describes it; on a segment `mood` (enum of the moods `sound_plan` knows) and `music`; on a sound event `class` and
`at_word` (1.4). Open `sound_plan.py` first and take the names it already reads; do not invent a second spelling. Then correct
guide v1 section 3 and guide v2 section 3e to the schema, and copy the corrected guides to
`/mnt/project-files/sound_library_2026-11-13/` and `/mnt/project-files/av_system_2026-11-13/`.
Test: a fixture script written exactly by guide v2 validates; `INTENTIONAL_SILENCE` is reached by it.

### 1.4 FA-06: anchors follow the read (P1)
- `sound_events[].at_word`: `{line_id, word (index or text), offset_s}`; exactly one of `at_s` / `at_word`. `events.visual_events`
  resolves it on the measured spine it already receives (planned spine before the read).
- `actions` and `motion_imitation`: accept `from_frac` / `to_frac` / `at_frac` (0..1 of the shot) beside the frame fields; the
  resolver turns them into frames of the timed shot.
- G1: in a script with `av_contract`, an absolute `at_s` / `at_frame` on a shot that has a read line is REVIEW with the list
  (FAIL only on the creator's word).
- G6: right after the retime run the resolver over every shot; an anchor outside its retimed shot FAILs here, at the read
  stage, with every broken anchor in one list. A segment the resolver must shorten is a REVIEW row naming the lost frames.
Tests: the pilot retimed at 0.5 and 0.33 gives the G6 list, no exception at G7 or G8; a word-anchored event lands on its word at
every speed; a fraction-anchored camera segment keeps its share.

### 1.5 FA-02: the LTX prompt composer (P3)
`videolane/scene.build`: `row["motion_prompt"]` is composed, never copied:
`<motion_prompt>` + for a clip-spoken shot `<Name> says in <voice description>: "<line text>"` + a sound clause from the shot's
authored sound + for a narrated shot a fixed "Nobody speaks." clause. The voice description comes from the cast in the script;
open the cast part of the schema and `audio/casting.py` first, and if no description field exists add one optional string per
cast member (the voice-caster page fills it). The composed text and its parts are written into the scene record so the audit
can see what LTX was told. `KP-V4-DIALOGUE-LEAK` keeps guarding the script; the composer is the one place a line may meet a
prompt, and a test says so.
Tests: Toba scene build, the nine spoken rows contain their line and a voice description, the 46 narrated rows contain the
no-speech clause; the script itself still passes the leak lint.
Not proven until the first paid sample: that LTX speaks the composed line in the described voice. Say so in PROGRESS.

### 1.6 FA-07: the hand-over never cuts speech (P8, free half)
`videolane/ingest.edit_points`: when `handover_s` is before the last speech end + BP-187's tail, raise a ContractError that
names the shot, the speech end and the hand-over time (class C, regenerate) instead of cutting. Add `videolane/ingest.py` to
BP-187's `enforced_by`.
Test: the measured case of the report (speech to 4.6 s, hand-over at 4.375 s) raises; a hand-over at 5.2 s passes.
The worker half (search the hand-over frame only after the expected speech end) goes to P5.

Done when (P1): G1 on the Toba script shows no false row; what remains red there is the script itself (P3).

## P2. The writers' room learns the contracts

No page under `.claude/` knows the new fields (FA-03, FA-17). `tests/unit/test_agent_governance.py` checks every module, path
and skill a page names: open before citing.

| Page | Change |
|---|---|
| `agents/edit-planner.md` | owner of `edit_plan` per video shot (continuation / coverage / insert, handles, `speech_onset_s`), of `av_contract: "av_events/1"`, of `actions` / `motion_imitation` with fraction or word anchors; the Ink Chronicle lanes move under a legacy banner |
| `agents/beat-writer.md`, skill `visual-beats` | owner of `sound_events`: authored, word-anchored, one audio decision per visible event (the six kinds of AV-01..08); a word alone never earns a sound; links to sound guide v2 |
| `agents/scene-writer.md`, skill `dialogue-scenes` | one line per clip, the line ends inside the clip (BP-187), a line longer than one LTX clip is split in the script; scene = segment + place (the video lane's unit) |
| `agents/story-architect.md` | the place of every scene is named once and carries the bed (FA-09); the era comes from the manifest |
| `agents/voice-caster.md` | a voice description per speaking cast member for the LTX prompt (1.5) |
| `agents/shot-continuity-writer.md` | continuity cards for every scene that has video shots; they feed the identity gate (P4.2) |
| `agents/script-critic.md` | checks: no absolute anchors, every video shot has `edit_plan`, every visible event has an audio decision |
| skills `shot-visuals`, `dialogue-scenes`, `editing-style` | route `wan` becomes `video`; link to VL-01..13 and AV-01..08 by id, no copied numbers |
| every page that still describes the D-116 route (report FA-17 lists them) | read each Blender / Ink Chronicle / Qwen / LTX mention; what describes today's route is corrected, what is history gets the dated legacy banner |
| skill `story-engine` | the stage table names the new owners of the fields above |
| `scripting/stage_guard.py` | the field ownership above, so one stage cannot write another's fields |
| `docs/STORY_ENGINE.md`, `docs/PRODUCTION_SCRIPT.md` | the same ownership table, ids linked to their homes |

`CLAUDE.md` (both headers), `.claude/rules/cloud-platforms.md`, `GEMINI.md`, `docs/SCENE_REUSE_RULES.md` LX-04,
`docs/VIDEO_GENERATION_WAN.md`, `config/retired_era.json` (FA-16: remove `training/video_qa.py` from the retired list, name the
real LTX path `videolane/scene` + the worker), `tests/unit/test_icw01_rule_rewrite` (accept D-132 and D-137 as the LTX
decision): one text pass, each change listed in PROGRESS as a stale text corrected (ICW-01). `CLAUDE.md` is the creator's
standing instruction file: change only the route facts (60 % `video` = LTX-2.5 distilled on Modal, D-132; the lane D-137; the
AV contract D-135), nothing else.

Done when: `grep -rni "\bwan\b" .claude/skills .claude/agents` shows only legacy banners and the retired LoRA page; every
writer page that owns a new field names it; governance and docs_lint are green.

## P3. The Toba script meets the contract (free; the words do not change)

The edit-planner and beat-writer stages are re-run on the frozen words of `episodes/ep_toba`:
`edit_plan` on the 55 video shots (scenes by segment + place; 28 of 51 scenes hold video), `av_contract`, authored
`sound_events` with word anchors, an audio decision for every visible event, a place bed per scene, continuity cards for the
scenes with video. Then `python -m explainer_engine.episode run episodes/ep_toba --to script` (rehearsal).
The words stay frozen, but the script file changes: check `scripting/script_approval.py` for what its hash covers. If the
approval covers the changed fields, stop and tell the coordinator that the creator's approval (OR-17) must be renewed before
anything paid; do not re-stamp it.
Done when: G1 is green or shows only REVIEW rows that are the creator's (Q1, Q3, Q7).

## P4. Quality fixes

1. **FA-09 / P2.** Bed per place: `sound_plan` takes the bed from the scene's authored place bed; `sfx_planner`'s substring
   match becomes a candidate only (same pattern as D-135 for effects), with the three measured sentences of the report as
   tests. Era: `sound_plan.build` reads the manifest's `historical_period.era_id`; a missing era FAILs at G4 instead of
   becoming `napoleonic_1815`. Mood: the authored segment `mood`; the regex result is a candidate; the automatic riser appears
   in the event report as a derived event with its reason.
2. **FA-14 / P4, identity before money.** A new row at the storyboard gate (VL-10) and again in `videolane/master_qa` (G10):
   face match per hero with `qa/face_points.py` (SFace against the hero references), hero-box palette with
   `training/video_qa.shot_identity`, and the continuity-card questions answered on a contact sheet through
   `qa/sheet_review.py` (free). Level: REVIEW until the creator answers Q3. Fixture: two frames of one hero with a changed
   helmet colour must be flagged by the palette row or the sheet question.
3. **FA-10.** `picture_event` sound events go through `events.visual_events`; `layers25d`'s private fallback is removed;
   `av_report.event_report` lists them. Test: the eruption event of the pilot appears in the report with its audio decision.
4. **FA-11 / P7.** BP-81 on the worst 60 s window (the whole-sheet number stays as information); dialogue windows per line;
   `FRAME_MS` from the episode fps. The thresholds stay the registry's.
5. **FA-12.** `cue_sheet.py` reads BP-56's level the way BP-55 does (`_sev`), which gives the registry's REVIEW; Q1 decides the
   final level.
6. **FA-13 / P6, clip sound of narrated shots.** Build the path, default off: the narrated clips' own audio as a `clip_audio`
   layer in the effects stem (not the voice stem), ducked by the narrator like any effect; 30 ms fades at every read piece and
   clip edge in `videolane/voice.py` (BP-188); the voice track stays voice only. Then the free A/B for Q2 from the clips that
   already exist in `/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12/ltx_scene_live/` (check what is there first; if no
   narrated clip exists, say so and leave Q2 to the sample).
7. **FA-15 / P5, the read first.** `clip_seconds` sizes a narrated shot from the measured shot length when `audio/timing.json`
   exists, from the plan otherwise, and the scene plan row says which (`basis`). The runner does not force the order (Q4).
8. **FA-16.** RT-07 for the video route: what happens when a scene run fails a shot (retry count, 2.5D fallback) is written in
   one place and tested; today only the rehearsal branch of `stage_clips` knows it.
9. **FA-18.** `sound_plan`'s module globals move into the build call.

## P5. Before any paid step (not this thread's to start)

- One worker change set, if still wanted: the hand-over search after the expected speech end (P8). Then the ladder L0..L4 again,
  because the worker sha changes.
- The OR-23 plan for the Toba sample with the price, the cap, the watchdog and the cheapest combination (D-133), put to the
  creator in the main chat.
- What only the sample proves: P3 (LTX speaks the composed line), P9 (voice per speaker), P6 (clip sound under the narrator),
  the identity rows on real clips.

## After the integration PR is merged into `systemic/next-video`

Report section 6 lists every pull request. The thread closes #174, #175, #171, #169, #163, #172, #170, #168, #167, #166, #165,
#173 and the sixteen older contained heads, each with one comment naming the integration PR (the creator said on 2026-11-13
that the active branches can be closed once this work is done; confirm containment with `git merge-base --is-ancestor <head>
origin/systemic/next-video` before each close). #164, #120 and #112 wait for Q6. No branch is deleted without his word.

## What to hand back

One reply to the creator, in Georgian, short: what was merged, which findings are fixed, which tests prove it, what is still
red and why, and the questions that are his. One handoff file beside this one (`HANDOFF_AFTER_OPUS.md`) for the sample thread.
