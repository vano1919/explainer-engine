# Demo journal: the one living document of the demo run

**Live copy:** `/mnt/project-files/explainer-engine/demo_run_<date>/DEMO_JOURNAL.md` (created by stage S0 from this file).
A snapshot goes into `docs/handoffs/demo_run_<date>/` at the end of every stage. The process is `DEMO_PROCESS.md`.

| Field | Value |
|---|---|
| Episode id | `ep_truce_1914` (S2, story thread, 2026-11-13) |
| `FREEZE_SHA` | **provisional `8ae21ec`** (code under the frozen script commit `8da40d6`, PR #180; S0 2026-11-13 16:50 UTC). PR #177 is not merged and moved on to `1406ce2` (L3 worker fixes), PR #179 (CH-07 `cloud/paid_offer`) is stacked on it: the freeze is set again on the merged `systemic/next-video` before any paid stage (FL-009) |
| Baseline tests | 4141 passed, 20 skipped, 1 xfailed (677 s) at `8da40d6` (MS-005) |
| Current stage and thread | S0 done 16:50 UTC and S3 started (pictures thread, `claude/project-thread-bf505m`); continuity cards written; start frames blocked on T0 and the style anchors (FL-010, CQ-008) |
| Counts | KN 15 · FL 21 · DV 3 · RC 3 · SF 4 · NT 4 · CQ 11 · MS 8 · CU 0 |

## 0. How to write here

1. **One writer:** the thread of the running stage. The watchdog and the critic never write here.
2. **Log first.** An entry is written within minutes of the event and before any workaround.
3. **Append only.** New entries go at the end of their section with the next number. Nothing is deleted; a wrong entry
   gets `status: withdrawn` and one line why. Status fields and links are updated in place.
4. **Short entries, full evidence.** At most about 15 lines an entry. Tracebacks, records, commands and screenshots go
   into `evidence/<entry id>/` beside this file and are named in the entry.
5. **`touches` is opened, never guessed.** Name a file or function only after opening it or reading it in a traceback
   (Blueprint Lock 5). Otherwise write `unlocated` and what was searched. At most about ten minutes of looking; the
   close stage locates the rest.
6. **The shared folder is a network mount:** read the file again just before writing, and read it once more about ten
   seconds after, to see that the write landed.
7. **Stage-end checkpoint** (the stage is not finished without it):
   - every entry of the stage has severity, cause class, `touches` and a status;
   - section 2 (rules in force) and section 7 (impact index) are current;
   - the freeze check output is in the stage handoff;
   - the stage's MS entry holds its minutes and money;
   - the counts in the table above are updated, and the snapshot is committed.

**Entry kinds**

| Prefix | What | Section |
|---|---|---|
| KN | known before the start (seeded from the audit and handoffs) | 1 |
| RC | rule change | 2 |
| FL | failure, problem or friction | 3 |
| DV | deviation from the production path (a rehearsal, a manual step, a waiver) | 4 |
| SF | script fix request to the script thread | 5 |
| NT | the creator's note, word for word | 5 |
| CQ | a question to the creator and his answer | 5 |
| MS | a measurement: minutes, money, counts, speeds | 6 |
| CU | code-update package (written in S9) | 8 |

**Severity:** `BLOCKER` (the stage stopped) · `DEGRADED` (worked around; quality or the production path suffered) ·
`FRICTION` (cost time or a manual step) · `COSMETIC`.

**Cause class:** `CODE-BUG` · `MISSING-FEATURE` · `RULE-WRONG` (a rule blocks good work or lets bad work pass) ·
`RULE-MISSING` · `DOC-WRONG` (a guide, skill or agent page says what the code rejects) · `DATA` (our own script or prompt
mistake) · `PROVIDER` · `ENV` · `PROCESS` (handoff, model split, this plan). The first five always end in a CU package.
The others end in one only when a guard or a check should have caught them.

## 1. Known before the start (KN)

Seeded 2026-11-13 by the planning thread from the files named in each line. S0 opens each source again and sets the
status to `confirmed`, `changed` (with what changed) or `closed`.

| Id | What is known | Source read | Touches | Status |
|---|---|---|---|---|
| KN-01 | The P5 worker edits are not started: the hand-over frame search on the worker side, the worker-side retry, the stale docstring. After any worker edit the L0-L4 ladder runs again. | `HANDOFF_AFTER_OPUS.md`, "Still open" 2 and 3 | `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` | changed: P5 edits done on PR #177 (`6e144f8`, `8cd8be8`, L0-L3 green at `1406ce2`), but not in the episode's base `8ae21ec` (FL-009) |
| KN-02 | The script approval stamp binds only `production_script/3`; a v4 script's OR-17 approval cannot be stamped by the tool. In this run it is a CQ entry with the script's sha256 and his message id. | `HANDOFF_AFTER_OPUS.md`, "Still open" 1 | `scripting/script_approval` | open |
| KN-03 | No real takes for `map_pin_set`, `map_line_strain`, `map_line_snap` and a flag-like `cloth_flap`; the other map and data classes have one or two takes (BP-57 asks three). Such events become `review_required` and the render is not shippable. | guide v2, section 7.1 | `assets/audio/library/manifest.json`, `episode/sound_plan` | open |
| KN-04 | 73 library items are vault-only: their working copies are not in the container and their QC is NOT_RUN. | guide v2, section 7.2; `docs/SOUND_LIBRARY.md` | the library | open |
| KN-05 | Nobody has listened: every event says `human: not_listened`. A machine PASS is never the creator's approval. | guide v2, section 7.7 | `episode/av_report` | open |
| KN-06 | Two FA-11 checks are coarse: BP-55 counts only visual events as beats, and one emphasis a line is counted per shot. | `HANDOFF_AFTER_OPUS.md`, "Still open" 5 | `episode/cue_sheet` | open |
| KN-07 | LTX money: `modal_ltx` has `per_run_usd` 1.5 and no episode line; the Wan `modal` line is unset. The demo scene needs the creator's line before S5. | `config/spend_caps.json` on `11f556b` | `config/spend_caps.json` | confirmed 16:45 UTC: `modal_ltx.per_run_usd` 1.5, no episode line |
| KN-08 | No automatic repair loop: G10 writes repair lines with their class; running them is a person's step. The face and costume identity across a cut is not a VL-12 gate. | `docs/VIDEO_LANE.md`, "Not done here" | `videolane/master_qa` | open |
| KN-09 | Switch Q1: BP-56 is REVIEW and flips to FAIL "after the Toba sample". The demo does not flip it unless the creator says so. | `config/creator_open_questions.json`, D-138 | `episode/cue_sheet.bp56_level` | open |
| KN-10 | Switch Q3: a paid scene is refused while the face is NOT MEASURED. It needs YuNet and SFace in the gitignored `tools/yunet` and the heroes' reference pictures. | `HANDOFF_AFTER_OPUS.md`, Q3 row | `videolane/identity` | confirmed: no `tools/yunet` in the container |
| KN-11 | Switch Q4: every video shot is sized from a measured read; the clip-line takes are a paid ElevenLabs step. | `HANDOFF_AFTER_OPUS.md`, Q4 row and "Still open" 0 | `videolane/line_reads`, `videolane/scene` | open |
| KN-12 | The LTX build takes one picture at frame 0, 1280x704 at 24 fps, at most 10 s; no end frame, extend or retake. A line starts about 0.75 s into its clip; mouths are weak close up. | `docs/VIDEO_LANE.md`, "What our generator can and cannot do" | the worker | open |
| KN-13 | `episodes/` holds only `ep_toba`. Whether a scaffold command for a new episode exists is not known; S0 finds out. The chat picture route needs the creator's PC session or his own pasting (GC-15). | `git ls-tree` of `11f556b`; `docs/GEMINI_CONSISTENCY_RULES.md` | `episode/`, `imagegen/turn_pack`, `gemini_task/` | changed: `episodes/ep_truce_1914` exists (S2 built it by its builder, no scaffold command); the picture route needs T0 first (FL-010) |
| KN-14 | One test depends on an outside server (itch.io answered 522 in CI): `test_pilot_stills::test_a_named_battle_camera_reaches_the_crowd_plan`. | PR #177 body | `tests/unit/test_pilot_stills.py` | open |
| KN-15 | This is the first paid end-to-end run of the integrated line. Only real clips show: whether LTX holds faces and costumes, whether the voice text keeps a voice across clips, the clip sound under the narrator, the hand-overs and seams, the cue density by ear, the real cost and time per clip. | `HANDOFF_AFTER_OPUS.md`, "What only the sample proves" | the video lane | open |

## 2. Rules in force for this run that differ from the repo (RC)

**This section is the only place a rule changes during the run** (Law 3). A thread that starts a stage reads the table
first: it is the whole difference between the repo's rules and today's law.

| Id | Rule (home) | Change in one line | Approved (date, message id) | Status |
|---|---|---|---|---|
| RC-001 | Q7 video share (`episode/run._video_share_row`, D-131/D-138) | Variant B of ep_truce_1914 may sit under 60 % video (measured 32.4 %), for the A/B comparison only; version A keeps 60 % | ვანო 2026-11-13 15:08 UTC, card `cmsg_01Hnu5zB86sjUj5GtTgaUkPW5udZfvGUREE4XYMQnfev1X` answer ა | APPROVED |
| RC-002 | GC-20 T0 gate (`gemini_task/batch._preconditions`, `config/gemini_t0_record.json`) | Pictures of ep_truce_1914 (anchors, R1) may be made before T0 is PASS, on picture route level 2 (Gemini API batch, 2K) | ვანო 2026-11-13 16:50 UTC, card `cmsg_01Hnu5zB86sjUj5GtTgaUkPWKfyQxUuUGhDtLX72PBMkfB` answer ა | APPROVED |
| RC-003 | GC-26 script review gate (`gemini_task/batch._preconditions`) | The same pictures may be made before Gemini's review of the video script is PASS; RN-03 (voice first) stays: scene frames wait for S4 | ვანო 2026-11-13 16:50 UTC, card `cmsg_01Hnu5zB86sjUj5GtTgaUkPWKfyQxUuUGhDtLX72PBMkfB` answer ა | APPROVED |

### RC-001 · APPROVED · severity
rule: Q7 (home: `config/creator_open_questions.json`, D-138) — today: "the 60 % video gate is REVIEW on a sample and FAIL on a full episode"
change: for variant B of ep_truce_1914 only, the video share may be under 60 % (the A/B comparison the creator asked for)
why: the creator's request 15:01 and 15:04 UTC (NT-001): build ChatGPT's reduced-LTX cut from A's material and compare for real
source (D-59): house (the creator, 2026-11-13)
approved: card answer ა "კი", 15:08 UTC, `cmsg_01Hnu5zB86sjUj5GtTgaUkPW5udZfvGUREE4XYMQnfev1X`
in this run: B lives at `episodes/ep_truce_1914/variants/B/production_script.json`; its G1 run (in a scratch copy) shows the expected FAILs `video_share_against_target` (32.4 %) and `CF-VISUAL-MIX-BOUNDS` (47.6 % of shots) and nothing else; G4 is refused on that FAIL (DV-002)
conflicts: CF-VISUAL-MIX-BOUNDS (shot-count mix bounds, `orchestration/cohesive_film_engine.py`)
to code: nothing unless B wins the comparison
status: APPROVED

Status path: `PROPOSED` → `APPROVED` → `APPLIED-BY-HAND` → `CODED (PR #)`. Only the creator approves. One card per
change. A change that blocks work is asked at once; the others at the stage's end.

**Entry template**

```
### RC-000 · PROPOSED · <new | wording | threshold | severity | retire>
rule: <id> (home: <doc path>) — today: "<the one sentence as the home says it>"
change: <the new sentence>
why: <FL-.. / NT-.. / measurement MS-..>
source (D-59): house (the creator, <date>, <message id>) | binding (<two source types>) | hypothesis (REVIEW only)
approved: <the creator's words>, <UTC time>, <message id>
in this run: <who applies it by hand and how; which gate still shows the old verdict → DV-..>
conflicts: <other rule ids it touches, or none>
to code: registry row · rule home · validator <file> · test · skills and agent pages that restate it
status: PROPOSED
```

## 3. Failures, problems and friction (FL)

**Entry template**

```
### FL-000 · <SEVERITY> · <CAUSE CLASS> · <stage> · open
when: <UTC> · thread: <name, model>
what failed: <one sentence, observable>
expected: <what the rule or doc says should happen: rule id and home>
evidence: <command and exit code, record file, traceback tail> → evidence/FL-000/
touches: <path:function, opened yes> | unlocated (<what was searched>)
cause: <what is known> · confidence: confirmed | likely | guess
impact on the demo: <what the viewer or the schedule loses>
workaround: rung <2-5> — <what was done> (DV-.. / SF-..) | none (stopped)
cost: <minutes>, <money or credits lost>
proposed fix: <one or two sentences> · test: <what a focused test should assert>
links: <RC-.., CU-.., KN-..>
```

### FL-001 · FRICTION · PROCESS · S2 · open
when: 2026-11-13 15:30 UTC · thread: story thread (S2), Opus high
what failed: S2 started before S0: no live journal, no FREEZE_SHA, no baseline, no "new episode needs" list
expected: DEMO_PROCESS.md S0 steps 1-3 run first (the journal is created by S0)
evidence: `ls /mnt/project-files/explainer-engine/demo_run_*` empty at 15:30 UTC
touches: unlocated (process, not code)
cause: the Truce demo replaced the 2-3 min demo and its story stage started at once · confidence: confirmed
impact on the demo: none on the script; S0's checks are still owed before any paid stage
workaround: rung 2 — S2 created this journal from the template and logged its own entries; S0 fills its fields later
cost: 2 minutes
proposed fix: none in code; the coordinator runs S0 before S3
links: KN-13

### FL-002 · DEGRADED · MISSING-FEATURE · S2 · open
when: 2026-11-13 15:40 UTC · thread: story thread
what failed: the sound classes have no rifle or pistol shot, spade digging, paper or letter rustle, choir or singing, match strike, clapping
expected: every visible event gets its own sound (AV contract D-135); an unknown class raises ContractError (`sound_plan.shot_events`)
evidence: `explainer_engine/episode/sound_plan.py` EVENT_CLASSES (read 2026-11-13)
touches: `explainer_engine/episode/sound_plan.py:EVENT_CLASSES`, opened yes; the library manifest
cause: the class list grew from earlier eras (ancient battles, volcano) · confidence: confirmed
impact on the demo: the shots, the digging, the singing and the clapping come only from the LTX clip's own sound (Q2 quiet layer); on 2.5D stills (variant B) they are silent unless A's clip audio is lifted (DV-001)
workaround: rung 3 — shots in clips: `sound_events` source `clip_audio`, class `impact` as the nearest label; the rest silent_by_design or clip sound
cost: 10 minutes
proposed fix: add classes gunshot_rifle, gunshot_pistol, dig_spade, paper_rustle, choir_sing, applause_small, match_strike with library takes · test: sound_plan accepts them and the source search finds a take
links: KN-03

### FL-003 · FRICTION · RULE-WRONG · S2 · open
when: 2026-11-13 15:45 UTC · thread: story thread
what failed: two mix gates measure the same mix on different bases: Q7 by duration (D-131) and CF-VISUAL-MIX-BOUNDS by shot count; CF-SHOT-DURATION-BOUNDS caps a shot at 10 s while the schema allows 12 s
expected: one canonical home for one number (docs_lint's rule)
evidence: `orchestration/cohesive_film_engine.py` lines 158-260, opened; `episode/run._video_share_row`, opened
touches: `explainer_engine/orchestration/cohesive_film_engine.py`, opened yes
cause: the cohesive-film engine predates D-131 · confidence: confirmed
impact on the demo: a map shot of 12 s had to be split; on version A both pass, on B both FAIL (RC-001)
workaround: rung 2 — wrote to both
cost: 10 minutes
proposed fix: CF-VISUAL-MIX-BOUNDS reads the router's duration mix (R.mix_report); the 10 s shot cap moves to one home · test: a script with long stills and short clips gets the same verdict from both rows
links: RC-001

### FL-004 · FRICTION · RULE-WRONG · S2 · open
when: 2026-11-13 15:50 UTC · thread: story thread
what failed: SC-05 and VL-08 pull against each other: a silent reaction shot (a silent_beat line) splits SC-05's dialogue run into "isolated" one-line runs, while VL-08 asks for a reaction every three lines; VL-08 also counts across a time cut and narrated shots
expected: a reaction inside an exchange is good editing (ED-14)
evidence: G1 rows of 15:47 UTC (SC-05 S03_L008, S06_L010; VL-08 S04_SH012, S05_SH014)
touches: `explainer_engine/scripting/scene_lint.py` (SC-05 run logic), `explainer_engine/videolane/plan.py:findings` (VL-08 run), opened yes
cause: SC-05 counts any non-character line as a break · confidence: confirmed
impact on the demo: two new lines were written (Harris S02, Friedrich S03 "Good, English! More!"; S06 "Then take one of mine.") and two silent inserts were added (hands, spades): all good for the story, but forced
workaround: rung 2 — DATA fixes in the script
cost: 15 minutes
proposed fix: SC-05 skips silent_beat lines when it measures a run; VL-08 resets on a time_cut and on a narrated shot · test: an exchange with a silent reaction in the middle passes both
links: none

### FL-005 · COSMETIC · RULE-WRONG · S2 · open
when: 2026-11-13 15:47 UTC · thread: story thread
what failed: YT-01-HOOK is a fixed word list ("?", "why", "seconds", "secret", "blood", ...): "Christmas morning, 1914. This man is about to walk toward the German guns." failed
expected: a concrete dramatic hook passes
evidence: `scripting/story_lint.py` lines 566-577, opened
touches: `explainer_engine/scripting/story_lint.py`, opened yes
cause: a keyword list instead of a hook-form check · confidence: confirmed
impact on the demo: the hook became "In a few seconds, this man will walk toward the German guns." (stronger anyway)
workaround: rung 2 — wording
cost: 3 minutes
proposed fix: use `scripting/narration_lint.hook_form` instead of the word list · test: the two hook lines above both pass

### FL-006 · COSMETIC · RULE-WRONG · S2 · open
when: 2026-11-13 15:47 UTC · thread: story thread
what failed: SC-04 calls "It's Thomas, actually." (a man correcting a nickname) a third-person self-reference
evidence: G1 15:47 UTC; `scripting/scene_lint.py`
touches: `explainer_engine/scripting/scene_lint.py`, opened yes (SC-04 block)
workaround: rung 2 — the nicknames carry it: "Saxon. Fritz, to my friends. Merry Christmas, Tommy." / "We're all Tommies to you. It's really my name." (the lint also refused "Saxon. Friedrich." from Friedrich himself)
proposed fix: allow the speaker's own name after "it's" / "I'm" / "my name is" · test: those three forms pass

### FL-007 · FRICTION · RULE-WRONG · S2 · open
when: 2026-11-13 15:47 UTC · thread: story thread
what failed: KP-V4-NO-DUPLICATE-PROMPT and PV-NO-CROP-PADDING refuse two map shots that use the same relief plate
expected: a map plate is drawn once and the Python layer moves on it (RT-03)
touches: the KP/PV prompt lints (`scripting/shot_prompt_lint.py`), opened yes
workaround: rung 2 — each map shot names a slightly different plate view
proposed fix: skip map_action shots in the duplicate-prompt lints · test: two map shots on one plate pass

### FL-008 · FRICTION · DOC-WRONG · S2 · open
when: 2026-11-13 15:35 UTC · thread: story thread
what failed: the look's never-words (`photo`, `photograph`, `realistic`, ...) and the era rule (no `lantern`) collide with a 1914 story whose key prop is a family photograph; no guide says how to name it
expected: the story-architect and shot-visuals pages warn about never-words in props
touches: `config/visual_style_presets.json` (crossworld_main_style_v1), `imagegen/turn_pack.never_hits`, opened yes
workaround: rung 2 — every picture prompt says "sepia portrait card" and "oil lamp"; the narration still says "photograph" (not a picture prompt)
proposed fix: a line in skill `shot-visuals`: props that are never-words get a stated substitute · test: governance test names the substitute list

### FL-009 · FRICTION · PROCESS · S0 · open
when: 2026-11-13 16:45 UTC · thread: pictures thread (S0, S3), Opus
what failed: S0's start condition (PR #177 merged into `systemic/next-video`) does not hold; the episode branch sits on `8ae21ec`, while #177 moved on to `1406ce2` and #179 (CH-07) is stacked on it
expected: DEMO_PROCESS.md S0: FREEZE_SHA is the merged `systemic/next-video`
evidence: `git log origin/claude/project-thread-knwnla` (head `1406ce2`), `git log origin/systemic/next-video` (older); `explainer_engine/cloud/paid_offer.py` exists only on `claude/project-thread-wxcp6k`
touches: unlocated (process, not code)
cause: the Truce demo started before the merge · confidence: confirmed
impact on the demo: none for the free S3 work; S4/S5 cannot apply CH-07 from this base (no `cloud.paid_offer` here) and would run the pre-L3 LTX worker
workaround: rung 2 — provisional freeze `8ae21ec` for free work; the freeze is set again on the merged branch before any paid stage
proposed fix: none in code; merge #177 and #179 before S4
links: KN-01, KN-07

### FL-010 · BLOCKER · PROCESS · S3 · open
when: 2026-11-13 16:40 UTC · thread: pictures thread
what failed: no start frame can be made on the production path today: the Task route refuses every batch until T0 is PASS (`gemini_task batch ... 1` → "the Gemini Task route is off until T0 is recorded as PASS (GC-20); T0 is NOT_RUN"); T0 was never recorded (no `config/gemini_t0_record.json` on any branch); Gemini Task mode's usage limit is used up until 2026-11-14 ~05:19 Georgia time (memory of the A3 thread); the API backup (`gemini_task/api_backup.py`) only reads messages this package writes, so level 2 is blocked by the same gate; the scene pictures also need approved style anchors A-F (`config/gemini_task.json` `style_pack`: all `candidate`; the queue counts 82 items `needs_approval`)
expected: picture route level 1, then level 2 (`config/picture_route.json`)
evidence: `python -m explainer_engine.gemini_task queue episodes/ep_truce_1914` (t0 NOT_RUN, blocked 82); `batch` refusal above → evidence in this entry
touches: `explainer_engine/gemini_task/batch.py` (T0 gate), `explainer_engine/gemini_task/queue.py` (needs_approval), opened yes
cause: the T0 retest (Hydrogen) was planned for 11-14 after the limit; nobody approved anchors · confidence: confirmed
impact on the demo: S3 start frames wait for T0 and the anchor pick (CQ-008)
workaround: none (stopped at rung 5: card to the creator)
links: FL-013, CQ-008

### FL-011 · COSMETIC · RULE-WRONG · S3 · open
what failed: two checks of one rule disagree: `imagegen/turn_pack export` passed the German-trench place prompt with "a hanging lantern"; `gemini_task queue` refused it (GC-22)
touches: `explainer_engine/imagegen/turn_pack.py` (never-word check), `explainer_engine/gemini_task/prompts.py` (era rule), opened yes
workaround: rung 2 — SF-002 (applied by the script thread, `8da40d6`)
proposed fix: one era-rule check used by both routes · test: a "lantern" prompt fails in both

### FL-012 · DEGRADED · MISSING-FEATURE · S3 · open
what failed: the Task queue makes no prop references: the H1 R2 list names nine props (letter, portrait card, two buttons, candle tree, two rifles, spade, flag), the queue has only 3 portraits, 3 places and 3 full bodies
expected: GC-02 "people ..., then the place, then props"
evidence: `shot_queue.json` reference roles: style 79, scene master 55, heroes and places only
touches: `explainer_engine/gemini_task/queue.py` (`_refs_for_shot`), opened yes
impact on the demo: props are drawn from words only; the buttons and the portrait card may differ between shots
workaround: none needed to start; G10 identity rows and the contact sheet watch them
proposed fix: prop anchors in R2 and attached after the place · test: a shot with a prop id attaches its anchor

### FL-013 · FRICTION · PROCESS · S3 · open
what failed: the T0 record (`gemini_task t0-record` → `config/gemini_t0_record.json`) and an anchor approval (`approve-anchor` → `config/gemini_task.json`) write under `config/`, which the freeze forbids except a money line or a creator switch
expected: DEMO_PROCESS.md section 3
touches: `explainer_engine/gemini_task/gate.py`, `explainer_engine/gemini_task/__main__.py`, opened yes (CLI help)
workaround: treated as a creator switch: written only on his recorded word, listed in the freeze check
proposed fix: the freeze table names these two files as creator records

### FL-014 · FRICTION · DOC-WRONG · S3 · open
what failed: `scripting/continuity.cards_from_v4` (the stage page's first draft) writes Toba's light ("the low sun through the ash veil", "hearth"), depth `mid` and facing `camera` by default, one costume `default`, no props, and generic change causes
touches: `explainer_engine/scripting/continuity.py:cards_from_v4`, opened yes
workaround: rung 2 — the S3 builder (`demo_truce_1914/builder/build_continuity_cards.py`) lays place, light, costume variants, props, crowd counts and causes on the draft; 0 FAIL, 0 REVIEW
proposed fix: light and weather from the shot's own `lighting_and_time`, costume variants from `costume_continuity_notes` · test: a dusk shot of a non-Toba episode gets dusk and its own source

### FL-015 · DEGRADED · MISSING-FEATURE · S3 · open
what failed: the Task queue's prompts do not read the continuity cards or the heroes' `costume_continuity_notes`: from S06_SH010 on, no prompt says Thomas's top brass button or Friedrich's greatcoat button is missing; the registry text "tunic with brass buttons" is copied as it is (GC-04)
touches: `explainer_engine/gemini_task/queue.py` (prompt assembly), opened yes
impact on the demo: the button exchange (the episode's keepsake) may not show on the later shots; small at medium size
workaround: none yet; a one-clause prompt addition is a script fix (SF), offered to the creator in the stage message
proposed fix: the queue adds the card's costume variant after the registry text · test: a shot after a costume change carries the variant

### FL-016 · DEGRADED · RULE-WRONG · S5 · open
when: 2026-11-13 16:43 UTC · thread: Fable review of #177 (script check), relayed to the story thread
what failed: one LTX launch is one scene (CH-03) under a 508 s function timeout (`caps.run_usd` 0.97); from L3 (about 53 s setup, about 24 s per 2 s clip) about 30 clip-seconds fit. ep_truce_1914 A has S05 19 clips / 89.5 s, S06 12 / 49.2 s, S04 8 / 41.0 s, S02 6 / 42.6 s, so these four would end PARTIAL (an estimate, not measured)
expected: the launch fits the longest scene, or the runner splits a scene over launches
touches: `training/pods/ltx/launch.json` (protected), `cloud/cheapest.py` CH-03, opened no (the reviewer's reading)
workaround: rung 2 (data, no code): A's 57 clips are planned as 9 launch parts of at most 9 clips / about 34 clip-seconds, each cut on a scene_change or time_cut shot (HANDOFF_H1, "LTX launch parts"; the LTX worker thread confirmed 38.6 s per clip at L3, 16:47 UTC). A higher run cap stays the other way: ვანო's word, ladder L1-L3 again; it goes into the OR-23 plan
proposed fix: the scene runner splits a scene into launch-sized parts with the hand-over frame · test: a 90 clip-second scene plans as 3 launches

### FL-017 · COSMETIC · RULE-WRONG · S4 · open
when: 2026-11-13 16:43 UTC · thread: Fable review (script check)
what failed: S03_SH001 is 10.0 s against the model's 10.06 s (VL-06); a slower measured read makes `videolane/scene.build` raise
expected: a margin in the script stage
touches: `videolane/plan` VL-06, opened no
workaround: if the read is longer, split the narration over S03_SH001 and the next shot, or trim the shot to the clip and let the line run over the cut (a script change goes to ვანო first)
proposed fix: story stage keeps clips at or under 9.5 s on the estimated clock · test: a 9.8 s estimated clip gets a REVIEW

### FL-018 · DEGRADED · MISSING-FEATURE · S4 · open
when: 2026-11-13 16:43 UTC · thread: Fable review (script check)
what failed: Q4 is forced: all 39 clip lines need a measured take in `audio/line_reads.json` (paid ElevenLabs) before a scene file builds; the two sung lines (S03_SH003 German, S03_SH008 English) will not match a spoken TTS length
expected: a way to measure a sung line (a sung take, or a fixed sung length)
touches: `videolane/voice`, `config/creator_open_questions.json` Q4, opened no
workaround: a card to ვანო: the sung lines take their estimated 4.0 s, or a sung ElevenLabs take (priced first)
proposed fix: `line_reads` accepts `sung: true` with a declared length · test: a sung line passes with a declared length

### FL-019 · BLOCKING · MISSING-FEATURE · S5 · open
when: 2026-11-13 16:43 UTC · thread: Fable review (script check)
what failed: Q3: a paid scene is refused while the face is NOT MEASURED; the cloud container has no `tools/yunet` (KN-10)
expected: the face model is fetched in S0 readiness
touches: Q3 identity gate, `tools/yunet`, opened no
workaround: fetch YuNet (free) before S5; check the HF / OpenCV zoo path first
proposed fix: S0 checklist names it · test: readiness fails without the model file

### FL-020 · FRICTION · DOC-WRONG · S3 · open
when: 2026-11-13 16:55 UTC · thread: pictures thread
what failed: DEMO_PROCESS.md puts S3 (pictures) before S4 (reads), but the Task package refuses a scene batch until the read is timed ("the read is not timed yet; voice comes first (build item 6, RN-03)"), and every batch, R1 included, until Gemini's review of the video script is PASS (GC-26, never run)
expected: the demo process order matches the code's order
touches: `explainer_engine/gemini_task/batch.py:_preconditions`, opened yes
cause: the demo plan was written from the docs, not from the Task package's preconditions · confidence: confirmed
impact on the demo: scene start frames come after S4 on the production path; R1/R2 need the GC-26 review or the creator's waiver (CQ-011)
workaround: rung 5 — card CQ-011
proposed fix: DEMO_PROCESS order S3a references → S4 reads → S3b scenes; the review step named in S2 · test: none (process)
links: FL-010, CQ-011

### FL-021 · DEGRADED · RULE-WRONG · S3 · open
when: 2026-11-13 17:00 UTC · thread: pictures thread
what failed: the era line names "oil lamps" and the prompt check passes (no "lantern" word), but Gemini draws glass hurricane lanterns as the oil lamp: in ref_char_sgt_harris_portrait, ref_char_friedrich_brandt_portrait, ref_loc_german_trench_place and anchor1914_C. Thomas's portrait wears a stiff peaked cap, not the registry's soft service cap with ear flaps
expected: GC-22 preset era rule (no lantern); GC-04 the hero's registry text drawn as written
evidence: contact sheet https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/demo_truce_1914/pictures/S3_R1/contact_sheet.jpg (looked at by the thread)
touches: `explainer_engine/gemini_task/prompts.py` (era rule), the preset's era line, opened yes
cause: "oil lamp" reads as a hanging lantern to the model · confidence: likely
impact on the demo: hurricane lanterns are period-correct in 1914; the rule is a house rule. Creator's call: keep, or redo with one correction sentence (GC-25)
workaround: none yet; card to the creator
proposed fix: the era line says "small open oil lamps and candles" or the check looks at the picture, not only the words · test: none (needs a picture judge)
links: FL-011, DV-003

## 4. Deviations from the production path (DV)

Everything the master carries that the production path did not make. The message that shows the master to the creator
lists the open DV entries.

| Id | Stage | What was done outside the path | Why (FL) | Commands saved | Affects the master | Waived by the creator (message id) |
|---|---|---|---|---|---|---|
| DV-001 | S7 (variant B only) | A's clip audio of the signal shots (S07_SH006, S07_SH007) lifted under B's 2.5D stills | FL-002 | planned, not done | B's sound at 4:58-5:08 | not yet |
| DV-002 | S2 | Variant B's G1 runs in a scratch copy of the episode folder; its G4 is refused on the approved Q7 FAIL (RC-001), so B's sound plan is A's plan with the same beds | RC-001 | `episode run <copy> --stage script` | none on A | RC-001 |
| DV-003 | S3 | Anchors + R1 made through `gemini_task/api_backup` from a hand-built PICTURE-block message (the Task `batch` refuses before T0/GC-26); prompts verbatim from `shot_queue.json` and `anchors_1914_draft.md`; intake by `gemini_task intake` gates | RC-002, RC-003 | done 17:00 UTC (MS-008) | none expected (same prompts, same refs) | yes, cap $0.60 |

## 5. Requests, notes and questions

### 5a. Script fix requests (SF)

Sent to the script thread in one batch per stage. A change of approved spoken words goes to the creator as a card that
shows only the changed lines.

| Id | From stage | Shot or line | What must change and why (FL / MS) | Words change | Answered (script sha256 after) |
|---|---|---|---|---|---|
| SF-001 | creator (NT-002) | S01_L005, S05_L002, S05_L003, S07_L005, S08_L002 (narrator only) | five factual qualifiers: parts of the Western Front; the 100,000 is an estimate nobody counted; football as a kickabout (C-17); the Boxing Day shots are the Houplines incident (C-21); small truces did happen in 1915 (C-23). Claim rows C-01, C-03, C-21, C-23 reworded to match; S01_SH005 8.0 s, S07_SH005 6.75 s from the longer lines | yes, narrator only; shown to ვანო before/after in the thread | 2026-11-13 ~16:40 UTC; A `d14f7c7d...3f2806`, B `e89b5adf...074a07`; A G1-G4 PASS no REVIEW, B G1 FAIL only RC-001 |
| SF-002 | S3 (pictures thread) | `world_bible.locations.loc_german_trench.fixed_environment_prompt` | "hanging lantern" refused by GC-22 (era rule); FL-008's substitute "oil lamp" | no (prompt only) | 2026-11-13 ~16:35 UTC; A `25636aba...6de24c` |
| SF-003 | S3 (pictures thread) | S06_SH001 `character_ids` | the prompt shows Thomas and Friedrich but the list was empty, so no hero anchors (GC-02); now [char_thomas_hale, char_friedrich_brandt] | no | same |
| SF-004 | creator (NT-003) | S02_L007, S05_L003, S08_L002 (narrator); S07_SH005, S07_SH006 (action) | the Pope's appeal failed, no official truce (not "they refused"; 28 words max YT-03 and the 10 s shot cap dropped "the warring governments"); football "accounts describe men kicking a ball around"; commanders "moved to prevent it"; Houplines in Stockwell's order: three shots, flag, salute; the German salutes back, gets down, then two shots. Claim C-25 reworded | yes, narrator only; S07_L007 silent action text | same; B `0ce9795a...9efbc4`; A G1-G4 PASS no REVIEW, B G1 FAIL only RC-001 |

### 5b. The creator's notes (NT)

His words, exactly, with the message id. Each ends as a rule change, a code package or `no action` with the reason
(OR-09: a creator note becomes a rule with a test).

| Id | When, message id | His words | About (shot, sound, story) | Becomes |
|---|---|---|---|---|
| NT-001 | 2026-11-13 15:04 UTC, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWFcyjCKA7uQJsTkd692MkxS` | "რეალურად ორმაგდება? ეგ ჯერ არ ვიცით მოდი დაწერე ჯერ სენი ვერსის სკრიპტი მერე დაწერე ჩატჯიპიტისი სადაც გაუთვალისწინებ თუ რა ვიდეო მასალა გექნება იმას ააგებ და მხოლოდ იშვიათ გამონაკლისებში ფააკეთებ დამატებით ლტხს სადაც უბრალიდ გარდაუვალია ასე ხარჯი კი არ გაორმაგდება არამედ გარკვეული პროცენტით იზრდება" | the A/B plan | RC-001; variant B built only from A's material |
| NT-002 | 2026-11-13 16:13 UTC, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWFCqRPmUmvb4PzH7h1aEZDY` | "keep the current A/B experiment unchanged and proceed with production in this order. Version A: Keep Claude's original route — 57 LTX clips. This is the cinematic quality baseline and is currently my preferred version. Version B: Keep the reduced route — 40 LTX clips, using only A's existing clips and start frames. Do not generate additional LTX clips for B. Do not merge the two approaches or introduce a Version C before we have rendered and compared A and B. [...] B must remain a genuine low-LTX comparison, not an improved hybrid version. Before paid production, address these factual wording issues in both versions [five items]. Do not change the approved story structure or dialogue without showing me the proposed changes first. Next objective: produce A, derive B from A's assets, and compare the actual result for cinematic quality, emotional impact, pacing, character consistency, and real cost. No paid work beyond the approved caps without my approval." | the A/B plan, the narration facts, the production order | SF-001 (applied); CQ-007 (OR-17 approval); the production order in HANDOFF_H1; B stays frozen as built (no C, no hybrid) |
| NT-003 | 2026-11-13 16:24 UTC, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWGK3dPACZAx9mwS5gMQAXKT` | "ეს ვერსია წინაზე უკეთესია. ხუთივე ფაქტობრივი შესწორება სწორი მიმართულებით წავიდა. სიუჟეტის სტრუქტურას, პერსონაჟებსა და დიალოგებს აღარ შევცვლიდი. 6:05 ქრონომეტრაჟიც მისაღებია." Four notes: S02_SH008 "The appeal failed. No official Christmas truce was agreed."; S07_SH006 Stockwell's order (three shots, flag, salutes, both back down, then the German's two shots); S08_SH002 "Their commanders moved to prevent it from happening again. A few small truces still occurred in 1915, but nothing on that scale."; S05_SH003 "In a few places, accounts describe men kicking a ball around." "ჩემი გადაწყვეტილება: ეს უკვე წარმოებისთვის მზად მყოფი Story/Script ვერსიაა, ზემოთ ჩამოთვლილი მცირე შესწორებების შემდეგ." Order: S0, A, B from A only, real comparison; paid only with a separately approved cap | the script freeze | SF-004 (applied); the script is frozen at A `25636aba...6de24c` |
| NT-004 | 2026-11-13 16:46-16:48 UTC, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWV5wD59xnB2aFzCf55toB82`, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWV8CrzPDJoerrWD9a5KXCtM`, `cmsg_01Hnu5zB86sjUj5GtTgaUkPWFdDSqmXxNBcTk3hG2qQ7BE` | "ყველაფერს ვაკეთებთ იმაღლესი ხარისხით ჯემინაის აპითი. თანხა დამითვალე რა ფვჭირდება და რამდენი თანხა" / "მეორე რო გვაქ 1 კ 2კ თუ რაღაც?" / "2 კ ჯობია უბრაკიდ მაინტერესებდა სხვაობა რამდენი იყი" | pictures: picture route level 2 (Gemini API batch, nano-banana-2.1), everything at 2K | priced: 94 pictures $2.74, max $3.29 with a 20 % redo reserve, cap $3.50 proposed; the rule breaks asked in CQ-011 |

### 5c. Questions to the creator (CQ)

| Id | Stage | Question (the card) | His answer, time, message id | Acts on |
|---|---|---|---|---|
| CQ-001 | S1/S2 | Approve story v1? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWAb5hzrfbPkFhTUS8JXNiZQ`) | withdrawn 15:00 UTC after ChatGPT's review; v2 written | story v2 |
| CQ-002 | S2 | Stille Nacht in German? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPW5rhTLzrHdZ68u4SyChZm2Y`) | open; the script follows the recommended ა (German verse, English answer) | S03_L003 |
| CQ-003 | S2 | Where to say the heroes are invented? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWUU51Wd8BsyG7oyTs7MMwLw`) | open; the packaging follows the recommended ა (description only) | PACKAGING.md |
| CQ-004 | S2 | Approve story v2? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWLzxUHmmZ1Qgk6xADkeaZRG`) | taken as approved by his 15:04 UTC message (NT-001: "write your version's script first"); card closed 15:04 | the script |
| CQ-005 | S2 | Test both LTX ways on one scene? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWAVhNnHhgM7grtUkaxnUvFi`) | withdrawn 15:04 UTC: replaced by NT-001 (two whole versions, B from A's material) | RC-001 |
| CQ-006 | S2 | B under 60 % LTX: break Q7 for the comparison? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPW5udZfvGUREE4XYMQnfev1X`) | ა "კი", 15:08 UTC | RC-001 |
| CQ-007 | S2 | OR-17: approve script A for production? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWBd2wajM4s1jMPTyK1DHWZq`) | approved in words 16:13 UTC (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWFCqRPmUmvb4PzH7h1aEZDY`), on the condition of SF-001, applied; card closed. Re-confirmed 16:24 UTC (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWGK3dPACZAx9mwS5gMQAXKT`, NT-003) after SF-004; FROZEN at A sha256 `25636aba731607b94911060da011eab0993ac6b728793acf4b39805fe66de24c` and B sha256 `0ce9795a7290429c81ee11a2f126dad830367feed6848856da2d95cb139efbc4` | S3 onward |
| CQ-008 | S3 | How and when to make the pictures: T0 tomorrow on the Task route, the plain chat today, or wait? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWHsJHengUbe4HbZ1d7i88iw`, recommended ა: T0 after the Task limit resets) | withdrawn 16:47 UTC: replaced by NT-004 (level 2 API) and CQ-011 | FL-010 |
| CQ-009 | S3 | Style anchors of the scene pictures: new 1914 anchors or the Stone-Age T0 pictures of 11-12? (`cmsg_01Hnu5zB86sjUj5GtTgaUkPW7GY6Qm56ACPTod55Tz7hik`, recommended ა: new 1914 anchors) | open | FL-010 |
| CQ-010 | S3 | Gemini API or app; API breaks GC-20 (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWLksmNXtvyrjV5yRS9Jfg6k`) | withdrawn 16:55 UTC: it named one rule break, the code shows three (FL-020); replaced by CQ-011 | - |
| CQ-011 | S3 | Break GC-20 (T0) and GC-26 (script review) for this run only, API 2K: ა anchors + R1 now (≈$0.40), scenes after S4; ბ also break RN-03, all 94 now (≤$3.29); გ no, the app tomorrow (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWKfyQxUuUGhDtLX72PBMkfB`, recommended ა) | answered ა 16:50 UTC (anchors + R1 via API 2K now; scenes after S4) | FL-010, FL-020 |

## 6. Measurements (MS)

Real numbers only, each with where it was read. They replace estimates in the cost model after the run.

| Id | Stage | What was measured | Value | Read from |
|---|---|---|---|---|
| MS-001 | S2 | Version A, estimated clock (G1 `outputs.mix`, before the read) | after the critic's two rounds and SF-001..SF-004: 367.0 s; video 220.5 s (60.1 %), still_25d 114.5 s (31.2 %), map 32.0 s (8.7 %); 84 shots, 57 LTX clips (39 with a hero line); narrator 504 / dialogue 193 words (72 % / 28 %); script sha256 25636aba...6de24c; G1-G4 PASS, no REVIEW (before SF-001: 357.0 s, 61.0 %, sha 9d3c18a9...51b7a0) | `episodes/ep_truce_1914/production/stages/script.json` |
| MS-003 | S2 | Critic (script-critic, 2 rounds) | round 1 mean 3.77 (title gate below 4), 8 fixes applied; round 2 mean 3.92, "ship after the one wording fix" (applied); still slowest 0:59-1:22 | this thread |
| MS-004 | S2 | LTX cost estimate (not measured) | A 57 clips ≈ $6.8-16; B alone 40 ≈ $4.8-11; B after A $0 new LTX. Basis: H100 $5.0937/h, CLI ~82 s a clip; battle run 4 clips $1.1 | `training/pods/ltx/launch.json`; `A_vs_B_2026-11-13.md` |
| MS-002 | S2 | Variant B, same clock | 367.0 s; video 115.75 s (31.5 %), still_25d 219.25 s (59.7 %), map 32.0 s (8.7 %); 84 shots, 40 LTX clips, all 40 are clips of A (0 new clips, 0 new pictures); sha256 0ce9795a...9efbc4 (before SF-001: 1015b11f...602e) → see `variants/B` | scratch G1 record of B; `variants/B/production_script.json` |
| MS-005 | S0 | Baseline test suite at `8da40d6` (code `8ae21ec`), cloud container, Python 3.13 | 4141 passed, 20 skipped, 1 xfailed (677 s) | `python -m pytest -q` (log in the S3 handoff) |
| MS-006 | S3 | Task queue of A (free) | 84 shots → 9 references (R1 3 portraits + 3 places, R2 3 full bodies), 79 pictures (style anchors E 38, A 18, C 11, D 7, F 4, B 1), 31 batches of 6, 4 days at the measured limit; 0 prompt FAIL after SF-002 | `episodes/ep_truce_1914/planning/gemini_task/shot_queue.json` |
| MS-007 | S3 | Continuity cards of A (free) | 16 scene files (S01-S07, one per place run), 70 cards, 0 FAIL, 0 REVIEW | `episodes/ep_truce_1914/planning/continuity/report.json` |
| MS-008 | S3 | Gemini API batch, nano-banana-2.1 2K: 6 1914 anchors + R1 (3 portraits, 3 places) | 12 of 12 back, 2752x1536, batch `36v3u67gbxt3ytjru9q2sjjmllf7op26333x` SUCCEEDED in under 7 min; cost $0.3156 reserved = settled (cap $0.60); 13 files on HF, SHA256 match 13/13 | https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/demo_truce_1914/pictures/S3_R1 |

Each stage's closing MS row: thread minutes, money and credits spent against the cap, items made, items retried.

## 7. Impact index: which code each entry touches

Updated at every stage end. One row per file or module; S9 turns the rows into packages.

| File or module | Entries | What is wrong there, in a few words | Package |
|---|---|---|---|
| _none yet_ | | | |

`unlocated` entries are listed here under "unlocated" until S9 finds their home.

## 8. The code-update plan (written in S9, nothing before)

Order of work: (1) the registry and the rule homes; (2) schemas; (3) code, a focused test with every package;
(4) skills and agent pages; (5) the regression: the demo episode runs G1-G10 again, free, from its stored assets, and
finishes with no DV entry still needed.

**Package template**

```
### CU-00 · <title>
closes: <FL-.., RC-.., NT-.., KN-..>
files: <paths, each opened>
change: <what the code or rule must do afterwards, in plain sentences>
test: <the focused test and what it asserts>
docs: <rule home, PROGRESS entry, decision id if a decision moved>
level and model: <S0-S4> · <Sonnet | Opus> (project rule 7)
needs first: <CU-.. or nothing>
paid re-test: no | yes (<what, estimated price>)
risk: <what could break>
```

**Coverage check before the plan goes to the creator:** every FL of the first five cause classes, every APPROVED RC and
every NT has a package or a written `no action`; every package names its test.
