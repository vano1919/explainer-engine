# Demo journal: the one living document of the demo run

**Live copy:** `/mnt/project-files/explainer-engine/demo_run_<date>/DEMO_JOURNAL.md` (created by stage S0 from this file).
A snapshot goes into `docs/handoffs/demo_run_<date>/` at the end of every stage. The process is `DEMO_PROCESS.md`.

| Field | Value |
|---|---|
| Episode id | _set in S2_ |
| `FREEZE_SHA` | _set in S0_ |
| Baseline tests | _set in S0 (passed / skipped / failed)_ |
| Current stage and thread | _S0, Demo readiness_ |
| Counts | KN 15 · FL 0 · DV 0 · RC 0 · SF 0 · NT 0 · CQ 0 · MS 0 · CU 0 |

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
| KN-01 | The P5 worker edits are not started: the hand-over frame search on the worker side, the worker-side retry, the stale docstring. After any worker edit the L0-L4 ladder runs again. | `HANDOFF_AFTER_OPUS.md`, "Still open" 2 and 3 | `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` | open, decide before S0 |
| KN-02 | The script approval stamp binds only `production_script/3`; a v4 script's OR-17 approval cannot be stamped by the tool. In this run it is a CQ entry with the script's sha256 and his message id. | `HANDOFF_AFTER_OPUS.md`, "Still open" 1 | `scripting/script_approval` | open |
| KN-03 | No real takes for `map_pin_set`, `map_line_strain`, `map_line_snap` and a flag-like `cloth_flap`; the other map and data classes have one or two takes (BP-57 asks three). Such events become `review_required` and the render is not shippable. | guide v2, section 7.1 | `assets/audio/library/manifest.json`, `episode/sound_plan` | open |
| KN-04 | 73 library items are vault-only: their working copies are not in the container and their QC is NOT_RUN. | guide v2, section 7.2; `docs/SOUND_LIBRARY.md` | the library | open |
| KN-05 | Nobody has listened: every event says `human: not_listened`. A machine PASS is never the creator's approval. | guide v2, section 7.7 | `episode/av_report` | open |
| KN-06 | Two FA-11 checks are coarse: BP-55 counts only visual events as beats, and one emphasis a line is counted per shot. | `HANDOFF_AFTER_OPUS.md`, "Still open" 5 | `episode/cue_sheet` | open |
| KN-07 | LTX money: `modal_ltx` has `per_run_usd` 1.5 and no episode line; the Wan `modal` line is unset. The demo scene needs the creator's line before S5. | `config/spend_caps.json` on `11f556b` | `config/spend_caps.json` | open |
| KN-08 | No automatic repair loop: G10 writes repair lines with their class; running them is a person's step. The face and costume identity across a cut is not a VL-12 gate. | `docs/VIDEO_LANE.md`, "Not done here" | `videolane/master_qa` | open |
| KN-09 | Switch Q1: BP-56 is REVIEW and flips to FAIL "after the Toba sample". The demo does not flip it unless the creator says so. | `config/creator_open_questions.json`, D-138 | `episode/cue_sheet.bp56_level` | open |
| KN-10 | Switch Q3: a paid scene is refused while the face is NOT MEASURED. It needs YuNet and SFace in the gitignored `tools/yunet` and the heroes' reference pictures. | `HANDOFF_AFTER_OPUS.md`, Q3 row | `videolane/identity` | open |
| KN-11 | Switch Q4: every video shot is sized from a measured read; the clip-line takes are a paid ElevenLabs step. | `HANDOFF_AFTER_OPUS.md`, Q4 row and "Still open" 0 | `videolane/line_reads`, `videolane/scene` | open |
| KN-12 | The LTX build takes one picture at frame 0, 1280x704 at 24 fps, at most 10 s; no end frame, extend or retake. A line starts about 0.75 s into its clip; mouths are weak close up. | `docs/VIDEO_LANE.md`, "What our generator can and cannot do" | the worker | open |
| KN-13 | `episodes/` holds only `ep_toba`. Whether a scaffold command for a new episode exists is not known; S0 finds out. The chat picture route needs the creator's PC session or his own pasting (GC-15). | `git ls-tree` of `11f556b`; `docs/GEMINI_CONSISTENCY_RULES.md` | `episode/`, `imagegen/turn_pack`, `gemini_task/` | open |
| KN-14 | One test depends on an outside server (itch.io answered 522 in CI): `test_pilot_stills::test_a_named_battle_camera_reaches_the_crowd_plan`. | PR #177 body | `tests/unit/test_pilot_stills.py` | open |
| KN-15 | This is the first paid end-to-end run of the integrated line. Only real clips show: whether LTX holds faces and costumes, whether the voice text keeps a voice across clips, the clip sound under the narrator, the hand-overs and seams, the cue density by ear, the real cost and time per clip. | `HANDOFF_AFTER_OPUS.md`, "What only the sample proves" | the video lane | open |

## 2. Rules in force for this run that differ from the repo (RC)

**This section is the only place a rule changes during the run** (Law 3). A thread that starts a stage reads the table
first: it is the whole difference between the repo's rules and today's law.

| Id | Rule (home) | Change in one line | Approved (date, message id) | Status |
|---|---|---|---|---|
| _none yet_ | | | | |

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

_No entries yet._

## 4. Deviations from the production path (DV)

Everything the master carries that the production path did not make. The message that shows the master to the creator
lists the open DV entries.

| Id | Stage | What was done outside the path | Why (FL) | Commands saved | Affects the master | Waived by the creator (message id) |
|---|---|---|---|---|---|---|
| _none yet_ | | | | | | |

## 5. Requests, notes and questions

### 5a. Script fix requests (SF)

Sent to the script thread in one batch per stage. A change of approved spoken words goes to the creator as a card that
shows only the changed lines.

| Id | From stage | Shot or line | What must change and why (FL / MS) | Words change | Answered (script sha256 after) |
|---|---|---|---|---|---|
| _none yet_ | | | | | |

### 5b. The creator's notes (NT)

His words, exactly, with the message id. Each ends as a rule change, a code package or `no action` with the reason
(OR-09: a creator note becomes a rule with a test).

| Id | When, message id | His words | About (shot, sound, story) | Becomes |
|---|---|---|---|---|
| _none yet_ | | | | |

### 5c. Questions to the creator (CQ)

| Id | Stage | Question (the card) | His answer, time, message id | Acts on |
|---|---|---|---|---|
| _none yet_ | | | | |

## 6. Measurements (MS)

Real numbers only, each with where it was read. They replace estimates in the cost model after the run.

| Id | Stage | What was measured | Value | Read from |
|---|---|---|---|---|
| _none yet_ | | | | |

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
