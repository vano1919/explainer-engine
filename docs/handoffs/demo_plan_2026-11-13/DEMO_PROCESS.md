# The demo run: process (plan of 2026-11-13)

Written by the planning thread (Fable) on the creator's order of 2026-11-13 14:02 UTC (message
`cmsg_01Hnu5zB86sjUj5GtTgaUkPW3jruJd721MjWDbZ6qBuPqh`). Planning only: nothing here was run, nothing paid.
Companions in this folder: `DEMO_JOURNAL.md` (the one living document), `BRIEFS.md` (the texts the coordinator hands to
each thread), `HANDOFF.md`, `SUMMARY_ka.md`.

Read against: PR #177 (`claude/project-thread-knwnla`, head `11f556b`) and its `HANDOFF_AFTER_OPUS.md`,
`docs/EPISODE_FIRST.md`, `docs/VIDEO_LANE.md`, `docs/SOUND_LIBRARY.md`, `docs/GEMINI_CONSISTENCY_RULES.md`, the two sound
guides (`docs/sound_guides/`), `config/picture_route.json`, `config/spend_caps.json`, `config/creator_open_questions.json`.
Rule ids below are cited, never restated in full: their homes are those documents.

## 1. The goal and the three laws of this run

**Goal.** One brand-new 2-3 minute episode made from zero (new story, pictures, voices, sound, edit) on the integrated
line, good enough that the creator may put it on YouTube, and at the same time a complete record of everything the line
got wrong, so that the code is updated once, afterwards, from that record.

**Law 1: no code is written during the run.** From the freeze (stage S0) to the creator's approval of the master, nobody
edits the system. Section 3 says exactly what "the system" is and what stays editable.

**Law 2: everything is written down as it happens.** Every failure, friction, workaround, measurement and creator note is
an entry in `DEMO_JOURNAL.md`, written before the workaround, with the code or file it touches.

**Law 3: rules change in one place only.** A rule may change during the run, on the creator's word. The change is written
only in section 2 of `DEMO_JOURNAL.md`. The repo's rule documents, the registry and the validators stay as they are until
the code update after the demo.

## 2. What the demo must contain (the creator's words, 2026-11-13)

| Part | Share of the running time | Route | What it must prove |
|---|---|---|---|
| A YouTube hook | the first seconds | any | BP-03 (first sentence is the hook), BP-04 (the 30-second contract) |
| One strong scene with dialogue and the narrator | 60 % | `video` (LTX on Modal) | VL-01..VL-13, RT-08, BP-187, BP-188, the D-138 answers (measured reads, voice text, face gate) |
| The map line | 10 % | `map_action` | RT-03, MA-01..MA-08, AV-01..AV-08 (every action has its audio decision) |
| Photos with full 2.5D motion | 30 % | `still_25d` | RT-06, L25-01..L25-06, BP-185 |

- Length 120-180 s. The shares are measured by duration (RT-04). The creator's standing word on lengths is "a frame of
  plus or minus 10 %, the story decides"; this plan reads that as: each share may sit within a tenth of its target
  (video 54-66 %). The script thread states the measured mix with the script.
- `run_scope` in the new `episode.json` is `full`, so the 60 % row is binding as on a real episode (Q7 of D-138).
- Everything the viewer sees or hears is English. The narrator is a voice only. No child hero.
- Overlays: none on the LTX shots; full on the map; accent only, strict, on the 2.5D stills. Every visible movement has an
  audio decision (`sfx`, `ui_cue`, `silent_by_design` with its reason, ...), inside the BP-81 cue budget.
- Sound follows guide v2: only authored sound is heard; library first; a missing take is never replaced by an unrelated one.
- Pictures follow `config/picture_route.json`: Gemini chat first (free), Gemini API batch as backup, BFL Klein as the
  backup of the backup, the last two only with a price and the creator's word.
- Out of scope unless the creator asks: Shorts, a paid thumbnail (he sets the thumbnail himself), a public upload.

## 3. The freeze: what "no code" means

The readiness stage records `FREEZE_SHA`, the commit of `systemic/next-video` after PR #177 is merged. From then on:

| Frozen (nobody edits) | Editable (it is the episode, not the system) |
|---|---|
| `explainer_engine/**` (the LTX worker and launch files under `training/pods/` included), `tests/**`, every schema | `episodes/<demo_id>/**` (manifest, script, planning, continuity cards, records, QA) |
| `.claude/**` (skills, agents, hooks, settings) | `docs/handoffs/demo_run_<date>/**` (journal snapshots, stage handoffs) |
| `docs/*.md` rule homes, `explainer_engine/standards/sourced_rules.json` | `docs/episodes.json` (the new episode's row, if a gate asks for it) |
| `config/**` except the two rows on the right | `assets/audio/` pick lists, import reports and `library/manifest.json`, only through `audio/free_import` (a new take is data) |
| `CLAUDE.md` | `config/spend_caps.json`: a money line, only on the creator's recorded word (the governance hook applies) |
| | `config/creator_open_questions.json`: a switch value, only on the creator's recorded word |

Every stage ends with the freeze check: `git diff --name-only <FREEZE_SHA>..HEAD` must list only paths of the right-hand
column. Its output is pasted into the stage's handoff. A path outside the list is a BLOCKER entry and is reverted before
the stage closes.

Also not allowed, because it is code by another name: running a changed copy of a repo module from the scratchpad,
monkeypatching, calling a paid provider directly around a refusal, editing a test or a threshold to get a pass. Reading
and inspecting with throwaway commands is fine.

`docs/PROGRESS.md` gets no entries during the run (nothing in the system changes); the journal replaces it until the code
update, which writes the PROGRESS and decision-log entries.

## 4. When something blocks: the ladder

The thread walks down this ladder and stops at the first rung that works. Rung 1 is never skipped.

1. **Log first.** A journal entry (FL) with the evidence, before anything else is tried.
2. **Fix the episode's data** so it satisfies the rule as the rule is meant (lengths, anchors, a class from the list, a file
   name, a seed). A change of the spoken words, the story, a dialogue line or a prompt beyond the GC-25 redo sentence is not
   the production thread's: it becomes a script fix request (SF) to the script thread, sent in one batch per stage.
3. **Use what the system already offers:** a documented CLI flag, a creator switch (with his word), or `--rehearsal` on a
   free stage. A rehearsal marks every later record, and the QA of a rehearsal FAILs by design (RN-02), so the master then
   ships only with the creator's explicit waiver. Each use is a deviation entry (DV).
4. **A manual free step outside the production path** (for example one ffmpeg command by hand), with the exact commands
   saved under `evidence/`. It is a DV entry, and whatever is shown to the creator says which DV it carries.
5. **Stop and ask the creator** with one card: change the story or shot to avoid the fault; drop the element; allow one
   blocker hotfix in a separate code thread (his exception to Law 1, logged as its own entry); or pause the demo.

Paid steps have no rungs 3 and 4: a refused paid launch is never worked around. It is logged and goes to rung 2 or 5.

## 5. Threads, models and stages

The creator's split (2026-11-13 14:02 UTC): story, dialogue and picture prompts on Opus high; assembly, render, tests and
upload on Sonnet high; the spend watchdog on Haiku low. Stages run one after another, never in parallel (project rule 7a);
the watchdog is the one thread that runs beside a paid run (rule 11). Every thread writes its handoff file and the next
thread gets only that file, the journal and its brief.

| Thread | Model | Stages | Paid |
|---|---|---|---|
| A. Demo readiness | Sonnet high | S0 | no |
| B. Demo story and script | Opus high | S1, S2 (and SF batches later) | no |
| C. Demo assets | Sonnet high | S3, S4, S5 | yes |
| W. Demo spend watchdog | Haiku low | beside every paid run of S3-S6 | no (read-only) |
| D. Demo assembly and upload | Sonnet high | S6, S7, S8 | SFX gaps only |
| E. Demo close | Opus high (recommended; the creator decides then) | S9 | no |

### S0. Readiness and freeze (thread A, free)

Starts only when PR #177 is merged into `systemic/next-video` and the creator has answered the pre-start decisions of
section 8.

1. Record `FREEZE_SHA`. Run the whole test suite once and record the counts as the baseline (journal MS entry).
2. Create the live journal from `DEMO_JOURNAL.md` at `/mnt/project-files/explainer-engine/demo_run_<date>/`. Confirm or
   close every seeded KN entry by opening the file it names.
3. Dry-run the new-episode path on an empty scaffold with the runner (`python -m explainer_engine.episode run|status`):
   which files a NEW episode needs before G1 (manifest, look, places, rulebook, rights manifest, claim map, episodes
   registry row). Every surprise is an FL entry now, before the script thread meets it.
4. The paid-path matrix (rule 10): for each paid path the demo may use (ElevenLabs narration, clip-line takes, ElevenLabs
   SFX, the LTX worker on Modal, Gemini API batch, BFL) name the test that proves step-by-step saving and the cap line
   that bounds it. A path without both is marked "may not run" in the journal.
5. Tool and account state, read-only: Modal balance, ElevenLabs credits left, the HF token, the face tools of Q3
   (`tools/yunet`), the Gemini chat route on the creator's PC (GC-15, GC-20), `cloud.runpod check` (nothing billing).
6. Handoff `H0`: freeze sha, baseline, the "new episode needs" list, the paid-path matrix, open KN entries.

### S1. Three stories, one choice (thread B, free; project rule 0, OR-15)

1. Three short stories for the demo, each complete enough that choosing one is the rule-0 approval: the premise in the
   channel's "worlds collide" frame, the hook line, the one strong scene (who wants what from whom, the turn), where the
   map line and the 2.5D stills fall, the heroes, and a rough count of LTX clips (it drives the cost).
2. Each story is checked against section 2 and the LTX limits (one line per clip, at most 10 s, no speaking close-up,
   the line ends inside its clip) before it is shown.
3. One card to the creator: the three stories, one recommended. His pick, with the message id, is a CQ entry.

### S2. The one script for everything (thread B, free; project rules 1 and 15, OR-17)

1. A small research dossier and claim map for the chosen story (invariant 5; skill `science-grounding`).
2. `episodes/<demo_id>/`: `episode.json` (look, places, `run_scope: full`) and `story/production_script.json` on the
   v4.3 contracts, written by the thread itself, stage by stage as skill `story-engine` orders: words and dialogue;
   voice cards and the one voice text per speaker (Q5); `edit_plan` on every video shot; map `actions` and 2.5D
   `motion_imitation` with `event_id` and `audio` (`av_contract: "av_events/1"`); authored `sound_events`; the place
   beds; picture prompts and continuity cards; the reference list for rounds R1 and R2 (GC-23).
3. The packaging texts while the story is fresh: title, description, tags (`qa/publish_check` rules), and the thumbnail
   idea in words for the creator.
4. Free gates: the runner's `script` and `sound_plan` stages (G1-G4) until no FAIL is left; every REVIEW row is read and
   either fixed or carried into the handoff with its reason. The one spawned critic (`script-critic`), at most two rounds.
5. The creator reads the finished script and approves it (OR-17). The approval is recorded as a CQ entry with the
   script's sha256 and his message id (KN-02: the stamp tool binds only `production_script/3`).
6. Handoff `H1`: episode id, branch and head sha, script sha256, the measured mix, clip count, open REVIEW rows, the
   picture list by round, the read list (narration plus every clip-spoken line).

Thread B stays open, parked. Later script fix requests reach it as one message per stage; a change of approved spoken
words goes back to the creator as a card that shows only the changed lines.

### S3. Pictures (thread C; free on the main route)

1. The paint plan: every picture with its route level. Level 1 (Gemini chat) needs no price. A fallback batch on level 2
   or 3 is a card first: the count, the price from `config/picture_route.json`, the cap line, his choice of provider
   (project rule 2).
2. Round R1 (portraits and places), the creator's look, then round R2 (full bodies) (GC-23). Then the scene pictures:
   the 2.5D stills, the video shots' start, coverage and insert pictures.
3. Intake gates on every file (GC-12, GC-13); the redo list at the end, once (GC-25). The contact sheet goes to HF and
   the thread looks at it before it reports.
4. The runner's `pictures` stage (G5).

### S4. The reads (thread C; paid, ElevenLabs)

1. Estimate in credits: the narration and one take of every clip-spoken line (Q4 forces a measured read for every video
   shot). Skill `elevenlabs-voice` first. Library-first record where a voice or take already exists (OR-18).
2. One card: the estimate, the cap in credits, the voices. On his yes: the watchdog thread confirms it reads the ledger,
   then the run, saving each take as it arrives.
3. Measure (`videolane.line_reads`), run the `voice` stage (G6). A line that no longer fits its clip is an SF request,
   not a re-read by guess.

### S5. The LTX scene (thread C; paid, Modal)

1. The storyboard sheet (VL-10) and the identity rows (Q3: the face must be measured before a paid scene). The thread and
   the creator look at the sheet.
2. The scene file (`videolane.scene.build`), then the OR-23 plan item by item: purpose, worker and pinned weights, every
   setting, clips and seconds, outputs and HF paths, GPU and price from the measured speed, time and money caps, stop
   condition, what he will see, what follows. The plan offers two orders with their prices: (a) a pilot of the first two
   clips, his look, then the rest (recommended: faces, voices and hand-overs are proven only on real clips); (b) the whole
   scene in one launch (cheapest by RT-08).
3. His GO on the card. The watchdog thread starts first. Then the ladder rungs that the worker's state requires
   (KN-01), each billed rung on his word.
4. Every clip goes to HF as it is made. A failing clip follows RT-07 (`videolane/failure.decide`): accept, one retry
   with a new seed inside the cap, the 2.5D fallback, or stop.
5. Ingest (`videolane.ingest`, VL-07). Handoff `H2`: clips with their HF links and records, the ledger totals, what was
   retried, the journal counts.

### S6. Assembly (thread D; free, except sound gaps)

1. The runner from `clips` to `assemble` (G7-G9): the map shots, the 2.5D shots, the video cuts, the cue sheet and stems,
   the chunked assembly (RULE-R1: a long render is a tracked background task, in chunks).
2. Sound gaps in the order of guide v1 section 5: the library; a free pick list through `audio/free_import`; then a
   priced ElevenLabs SFX list, a card, the watchdog, the run.
3. Read `sound_coverage.md`, `mix_check.json` and the event report before anything is shown.

### S7. QA and the creator's look (thread D, free)

1. The `qa` stage (G10). Every FAIL row gets its FL entry and its repair class (VL-12: A free, B free after a change,
   C paid).
2. The thread watches the master itself (contact sheet, the cuts, the mix numbers) and writes what it saw.
3. The master, the QA report and the contact sheet go to HF. One message to the creator with the exact links, the
   deviations the master carries (DV list) and the open FAIL or REVIEW rows. His notes are NT entries, word for word.
4. A repair round only inside the ladder: free repairs (class A, B) directly; a paid one (class C) with a price and a card.

### S8. YouTube staging (thread D; only after his recorded approval)

Unlisted staging through `publish/` (D-57) with the title and description of S2, after `qa/publish_check`. Going public
and the thumbnail are his clicks in Studio. The link goes into the journal and the reply.

### S9. Close: from the journal to the code-update plan (thread E, free)

1. Every entry gets its final status; every FL and RC that needs code points to a CU package (journal section 8).
2. The packages are ordered: registry and rule homes; schemas; code with a focused test each; skills and agent pages;
   then the regression: the demo episode runs G1-G10 again, free, from its stored assets, and must finish with no DV.
3. The creator sees the package list with a level and a model per package (project rule 7) and says go. The code threads
   that follow are not part of this plan.

## 6. The paid gates

Nothing paid starts without all five: an estimate from a measured rate; a hard cap that the code enforces
(`config/spend_caps.json`, the run's ledger, the 80 % stop); proven step-by-step saving for that path (S0 matrix); the
creator's yes on a card that names the price; and the watchdog thread confirming it reads the run's ledger.

| Gate | Stage | What is bought | Price basis | Cap |
|---|---|---|---|---|
| PG-1 | S3 | fallback pictures only (level 2 or 3) | `config/picture_route.json` per picture | `per_episode.gemini_usd`, `per_episode.bfl_usd` |
| PG-2 | S4 | narration and clip-line takes | characters of the approved script, as skill `elevenlabs-voice` counts them | his number in credits, inside the 100k standing cap |
| PG-3 | S5 | LTX clips on Modal | the measured speed of the ladder's L3 and `cloud/modal_schedule` | `modal_ltx` in `config/spend_caps.json` (today `per_run_usd` 1.5 and no episode line: KN-07) |
| PG-4 | S6 | missing sound takes | a list priced in credits | his number in credits |

- The watchdog follows `explainer-engine/agents/WATCHDOG_GUIDE.md` (project files): Haiku low, read-only, one RUN block
  per paid run, the tier by the run's cap, `ledger_filter` set to the run's own job ids. One watchdog thread serves the
  demo's paid runs one after another. It reports in chat; it never writes in the journal.
- A question from a paid stage is a card in its thread, and the coordinator shows the same question in the main chat
  (project rule 13). His answer travels by message id (rule 14).
- At the end of every paid stage: nothing left running (`cloud.runpod check`, the Modal app list), the ledger total in
  the journal (MS entry), and every new file's HF link in the reply (rules 4 and 16).

## 7. Documentation and reporting rhythm

- **At the event:** the entry is written within minutes, before the workaround. Evidence (tracebacks, records, commands)
  goes into `evidence/<entry id>/` beside the journal; the entry itself stays short.
- **At the end of each stage:** the checkpoint of journal section 0 (every new entry has its `touches` and severity; the
  impact index is current; the freeze check output is in the handoff; costs and minutes are measured), then a snapshot
  of the journal into `docs/handoffs/demo_run_<date>/` on the thread's branch, then the stage handoff.
- **To the creator:** one short Georgian message per stage end: the result with its links, the count of new failures,
  rule changes and deviations, the top problems in a line each, and what is needed from him. A BLOCKER is reported at
  once. Nothing else is sent.
- **Usage limits (project rules 8 and 12):** the journal and the stage records are the backup; at 95 % the thread writes
  its state into its handoff file and commits before anything else.

## 8. Decisions to settle before S0 (for the creator, as cards from the coordinator)

1. **The worker before the freeze (KN-01).** The P5 worker edits (hand-over frame search on the worker, the worker-side
   retry, the stale docstring) and the ladder after them are not done. Once the freeze starts they cannot be done.
   Recommended: finish P5 and the ladder as the last step of the integration, before S0. The alternative is a demo scene
   that avoids continuations (coverage and insert cuts only) and has no worker-side retry.
2. **The LTX money line (KN-07).** The demo's scene is the largest LTX run so far (60 % of 2-3 minutes at one line per
   clip and at most 10 s a clip is a dozen clips or more). `modal_ltx` has only a per-run line of $1.5. He names the
   demo's line once the S5 plan has the measured price; S0 only confirms the state.
3. **The close thread's model.** Recommended Opus high for S9; the creator may prefer to run it on Fable himself.

Not a question, stated so nobody assumes otherwise: the Q1 switch (BP-56 to FAIL "after the Toba sample") is not flipped
by the demo unless he says so (KN-09).

## 9. Done means

- The master is on HF with its exact link, with the QA report and contact sheet; the creator has approved it or listed
  his notes; if approved, it is staged unlisted on YouTube.
- The journal has no entry without a status, no failure without its `touches`, no rule change without his message id,
  and a code-update plan whose packages cover every open entry.
- No code changed between `FREEZE_SHA` and the approval (the freeze check of the last stage), or every exception is a
  logged hotfix he allowed.
- Nothing paid is running; the ledger totals are in the journal.
