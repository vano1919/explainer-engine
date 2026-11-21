# Handoff: the demo run plan (2026-11-13)

From the planning thread (Fable), for the coordinator. Planning only: no code, nothing run, nothing paid.

## What was done

Three documents, in `/mnt/project-files/explainer-engine/demo_plan_2026-11-13/` and in the repo under
`docs/handoffs/demo_plan_2026-11-13/` (branch `claude/project-thread-guupn1`, a draft PR into `systemic/next-video`,
documents only):

| File | What it is |
|---|---|
| `DEMO_PROCESS.md` | the stage-by-stage process: the three laws, what the demo must contain, the freeze, the blocker ladder, threads and models, stages S0-S9, the paid gates, the reporting rhythm, the pre-start decisions, "done" |
| `DEMO_JOURNAL.md` | the one living document, ready to copy: writing rules, entry kinds and templates (failure, rule change, deviation, script fix, creator note, question, measurement), the impact index, the code-update plan; seeded with 15 known issues (KN-01..KN-15) |
| `BRIEFS.md` | the common block and one short brief per thread (A readiness, B story and script, C assets, W watchdog, D assembly and upload, E close) |
| `SUMMARY_ka.md` | the short Georgian summary for the creator |

## What it was read against

PR #177 at head `11f556b` (open, draft, CI "unstable" at 14:05 UTC on 2026-11-13), `HANDOFF_AFTER_OPUS.md`,
`docs/EPISODE_FIRST.md`, `docs/VIDEO_LANE.md`, `docs/SOUND_LIBRARY.md`, `docs/GEMINI_CONSISTENCY_RULES.md`, both sound
guides, `config/picture_route.json`, `config/spend_caps.json`, `config/creator_open_questions.json`,
`explainer-engine/agents/WATCHDOG_GUIDE.md`. Every path the plan names was checked on that head.

Not verified, and left to stage S0 on purpose: whether a scaffold command for a new episode exists; which files a new
episode needs before G1 (rulebook, rights manifest, claim map, registry row); which paid paths have a test that proves
step-by-step saving; the live state of the accounts and of the chat picture route.

## The main design choices

1. **Six threads in a row, as the creator split the models:** A readiness (Sonnet high), B story and script (Opus
   high), C assets (Sonnet high), D assembly and upload (Sonnet high), E close (Opus high recommended), and the Haiku
   low watchdog beside every paid run.
2. **The freeze is checkable:** S0 records `FREEZE_SHA`; every stage ends with `git diff --name-only` against it, and
   only episode data, the demo handoff folder, sound pick lists and the creator's own money or switch lines may appear.
3. **A blocker never forces code:** the ladder goes from "log first" through a data fix, an existing switch or
   `--rehearsal`, a manual free step (logged as a deviation), to a card for the creator. A refused paid launch is
   never worked around.
4. **Rules change in one table** (journal section 2), one card per change, only the creator approves; the repo's rule
   documents stay untouched until the code update.
5. **The script thread stays open:** production threads never change words, story or prompts; they send script fix
   requests in one batch per stage.
6. **The close stage ends in packages**, each with its files, test, docs, level and model; the last package re-runs the
   demo episode free and must need no deviation.

## Next step: the entry for the coordinator

1. Put the three pre-start decisions of `DEMO_PROCESS.md` section 8 to the creator as cards. The first one matters
   most: the P5 worker edits and the ladder are not done (KN-01), and once the freeze starts they cannot be done.
2. When PR #177 is merged and those are answered, open thread A with the common block and block A of `BRIEFS.md`.
3. Then B, C, D, E in order, each with the handoff file of the stage before it.

## Open risks the plan cannot remove

- This is the first paid end-to-end run of a very large integration. Blockers are likely; the ladder decides what
  happens, and the journal is the product either way.
- 60 % of 2-3 minutes on LTX at one line per clip is a dozen clips or more, the largest LTX run so far. Its price is
  known only after the ladder's speed measurement.
- The map and data sound classes are thin (KN-03); the script should use the classes that have takes, or the gaps are
  filled before assembly.
- The chat picture route depends on the creator's PC session or his own pasting (KN-13).
