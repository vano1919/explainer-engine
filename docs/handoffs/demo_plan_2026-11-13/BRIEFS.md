# Briefs for the demo threads

For the coordinator. Each thread gets the common block, its own block and the handoff file of the stage before it.
Stages run one after another (project rule 7a). Fill the `<...>` fields from the previous handoff. The process is
`DEMO_PROCESS.md`, the living document is `DEMO_JOURNAL.md` (both in
`/mnt/project-files/explainer-engine/demo_plan_2026-11-13/`).

## Common block (goes into every brief)

```
You work on the demo run: one new 2-3 minute episode made from zero on the integrated line (after PR #177).
Read first, in this order: /mnt/project-files/explainer-engine/demo_plan_2026-11-13/DEMO_PROCESS.md, then section 0
and section 2 of the live journal /mnt/project-files/explainer-engine/demo_run_<date>/DEMO_JOURNAL.md, then the handoff
file named below.

Three laws of this run:
1. No code is written. Frozen: explainer_engine/ (the LTX worker included), tests/, schemas, .claude/, docs/*.md,
   config/ (except a money line or a creator switch on his recorded word), CLAUDE.md. Editable: episodes/<demo_id>/, the demo handoff
   folder, docs/episodes.json, sound pick lists through audio/free_import. End your stage with the freeze check
   (git diff --name-only <FREEZE_SHA>..HEAD) and paste its output into your handoff.
2. Log first. Every failure, friction, workaround, measurement and creator note is a journal entry written before the
   workaround, with the code or file it touches (opened, never guessed; otherwise "unlocated").
3. A rule changes only in section 2 of the journal, on the creator's word (one card per change). Never edit a rule
   document, the registry or a validator.

When something blocks, use the ladder of DEMO_PROCESS.md section 4. A refused paid launch is never worked around.
You are the only writer of the journal while your stage runs. End with the stage checkpoint (journal section 0, point 7),
your handoff file, and one short Georgian message to the creator: the result with its HF links, the counts of new
failures, rule changes and deviations, the top problems, and what you need from him.
Reply to the creator in Georgian, short. Everything the viewer sees or hears is English.
```

## Thread A. Demo readiness (Sonnet high) — stage S0

```
Goal: prove the line is ready for a new episode and freeze the code, before any story is written. Free work only.
Start condition: PR #177 is merged into systemic/next-video, and the creator has answered the pre-start cards
(DEMO_PROCESS.md section 8).
Do: S0 of DEMO_PROCESS.md, all six points: record FREEZE_SHA; run the whole test suite once as the baseline; create the
live journal from the template and confirm every KN entry by opening its source; dry-run the runner on an empty new
episode folder and list what a new episode needs before G1; write the paid-path matrix (for each paid path: the test
that proves step-by-step saving, and the cap line); read the account and tool states without spending anything.
Do not: fix anything, write a script, start anything paid.
Result: handoff H0 in /mnt/project-files/explainer-engine/demo_run_<date>/H0_readiness.md and the live journal.
```

## Thread B. Demo story and script (Opus high) — stages S1 and S2

```
Goal: the creator picks one of three short stories, then gets one finished script for everything and approves it.
Handoff in: H0_readiness.md.
The demo must contain (by duration, each share within a tenth of its target): a YouTube hook in the first sentence;
one strong scene with character dialogue and the narrator on the video route (LTX), 60 %; the map line on the
map_action route, 10 %; photos with full 2.5D motion on the still_25d route, 30 %. Length 120-180 s. run_scope "full".
LTX limits to write for: one line per clip, at most 10 s a clip, no speaking close-up, every line ends inside its clip.
No overlays on LTX shots. The narrator is a voice only. No child hero.

S1: propose three stories, each complete enough that choosing one is the approval of the short story (project rule 0):
premise, hook line, the scene (who wants what, the turn), where the map and the stills fall, the heroes, a rough count
of LTX clips. One card with a recommendation. Wait for the pick.
S2: write the episode yourself, not through the Claude API (project rule 15): research and claim map, episode.json, the
production script on the v4.3 contracts (words, voice cards and voice text, edit plans, map actions and 2.5D motion
with event ids and audio decisions, authored sound events, picture prompts, continuity cards, the reference list for
rounds R1 and R2), plus title, description, tags and the thumbnail idea in words. Follow skill story-engine and the
sound guide v2 (docs/sound_guides/). Run the free gates G1-G4 until no FAIL is left. One spawned critic, at most two
rounds. Then the creator reads the script and approves it; record his approval with the script's sha256 (journal CQ).
Nothing paid.
Result: handoff H1_script.md (episode id, branch and head sha, script sha256, measured mix, clip count, open REVIEW
rows, the picture list by round, the read list). Stay open afterwards for script fix requests.
```

## Thread C. Demo assets (Sonnet high) — stages S3, S4, S5

```
Goal: every picture, read and LTX clip of the approved script, made through the production path, each on HF.
Handoff in: H1_script.md. Start your branch from the head sha it names.
S3 pictures: paint plan; Gemini chat first (free). A fallback batch (Gemini API, then BFL) only after a card with the
count, the price from config/picture_route.json, the cap and the creator's choice. Rounds R1, his look, R2, then the
scene pictures; intake gates; contact sheet on HF; look at it yourself before reporting.
S4 reads (paid): price the narration and one take of every clip-spoken line in credits, ask with one card, then run with
the watchdog beside you, saving each take as it arrives. Measure the line reads and run the voice stage (G6).
S5 LTX (paid): storyboard sheet and identity rows; scene file; the OR-23 plan item by item with two orders and their
prices (a pilot of two clips first, recommended; or the whole scene in one launch). His GO, the watchdog first, then the
run inside the cap. Clips go to HF as they are made. A failing clip follows RT-07. Ingest every clip.
Paid rules: an estimate from a measured rate, a hard cap in code, proven step-by-step saving (H0 matrix), his yes on a
card, the watchdog confirmed. Stop and ask at 80 % of a cap. Leave nothing running.
Do not change spoken words, story or prompts (beyond the GC-25 redo sentence): send script fix requests to thread B in
one batch per stage.
Result: handoff H2_assets.md (every asset with its HF link and record, ledger totals, retries, journal counts).
```

## Thread W. Demo spend watchdog (Haiku low) — beside every paid run

```
Use the prompt /mnt/project-files/explainer-engine/agents/paid-run-watchdog.md and fill its RUN block from the approved
plan of the run: cap, ledger path, ledger_filter (the run's own job ids), progress files, the job-end signal, planned
burn, max hours. Tier by the run's cap as WATCHDOG_GUIDE.md says. Read-only: never spend, stop, delete or edit, and
never write in the demo journal. First message: confirm you read the ledger and see the filtered spent. Then silence
while all is fine; WARN, ALERT or STOP lines otherwise; one line at the end. A new RUN block arrives for each next run.
```

## Thread D. Demo assembly and upload (Sonnet high) — stages S6, S7, S8

```
Goal: the master, measured and seen, on HF; after the creator's approval, staged unlisted on YouTube.
Handoff in: H2_assets.md. Start your branch from the head sha it names.
S6: the runner from clips to assemble (G7-G9). A render over ten minutes is a tracked background task in chunks.
Sound gaps: the library, then a free pick list through audio/free_import, then a priced ElevenLabs list with a card
and the watchdog. Read sound_coverage.md, mix_check.json and the event report.
S7: the qa stage (G10); every FAIL row is a journal entry with its repair class. Watch the master yourself. Upload the
master, the QA report and the contact sheet to HF. One message to the creator: the links, the deviations the master
carries, the open FAIL and REVIEW rows. Write his notes into the journal word for word. Free repairs directly; a paid
repair only with a price and a card.
S8: only after his recorded approval: qa/publish_check, then the unlisted staging through publish/. Never public.
Result: handoff H3_master.md (HF links, the YouTube link if staged, the open entries by severity, the freeze check).
```

## Thread E. Demo close (Opus high recommended; the creator decides) — stage S9

```
Goal: turn the journal into the code-update plan. No code, nothing paid.
Handoff in: H3_master.md and the whole journal.
Do: give every entry its final status; locate every "unlocated" entry by opening the code; fill the impact index;
write the CU packages of journal section 8 in the stated order, each with its files, its focused test, its docs, a
level and model, and whether a paid re-test is needed; run the coverage check. The last package is the regression: the
demo episode runs G1-G10 again, free, from its stored assets, with no deviation left.
Result: the plan in the journal's section 8, a Georgian summary for the creator with the package list, and his go.
```
