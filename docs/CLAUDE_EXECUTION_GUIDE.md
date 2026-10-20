# Claude execution guide

For any Claude Code session working in this repository. Read `CLAUDE.md` (the invariants), [INDEX](INDEX.md), the current
phase in [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) and the last entry of [PROGRESS](PROGRESS.md) before changing
anything.

## Per-phase procedure
1. Inspect the files the phase touches and the tests that cover them. 2. State the intended minimal change. 3. Implement
it. 4. Run the focused tests, then the full suite (`.venv\Scripts\python -m pytest -q`). 5. Inspect produced artifacts
(open the rendered file or report, do not trust a green test alone). 6. Record failures and deviations. 7. Update
PROGRESS (completed work, state, files, test results, decisions, blockers, cost estimate/actual, next step, recovery).
8. Report each acceptance criterion as pass, fail or not tested.

## Recovery (a failed or interrupted job)
Read `jobs/<slug>/job-NNN/state.json` (status, completed stages, error, retries). A RUNNING job whose log is stale is
treated as interrupted. Resume re-runs from the first missing stage; `--redo-from N` re-runs from stage N. Cached clips and
scenes are reused by their keys. Never delete a job directory by hand: protected jobs (KEEP, final render, review bundle,
NEEDS_REVIEW, active) are deliberate, and `core/jobs.clean_jobs` is the only cleanup. Disk full: delete only `tmp/` of
finished jobs first and report.

## Guardrail design (written when first needed; verified against the installed Claude Code version before use)
- Rules (`.claude/rules/`, path-scoped only if the installed version supports it): schemas and fixtures (never weaken a
  schema to pass), renderer (finite vocabulary, determinism, pinned dependencies), research and factuality (claims need
  sources, uncertainty labels, no invented metrics). Added with Phase 3 and Phase 4, each stating what it governs.
- Skills (three): new episode (intake to approval #1), render and QA (render, report, bundle), resume a job. Added with
  Phase 6 when the workflows exist; not before.
- Hooks (deterministic): after edits under `explainer_engine/schemas/` run the contract tests; before `git commit` block
  `jobs/`, media files and key files. Added with Phase 3 after checking the hook syntax for the installed version.
- Subagents: none standing. An isolated second fact-check read of a script is allowed; it reports, never edits, and cannot
  override an approved decision.

## Pod runs: size the limits, keep the work (2026-10-16)
- A stage limit never comes from a smaller job. Compute it: units x measured seconds per unit x margin (default 1.25), with the
  speed from TMR `cloud/job_speeds.json` (update the row after each run: card, date, seconds) and a 3-unit preflight for a
  job type that has no row. Quote units, limit, $/h and the money and time caps in the approval request.
- Whatever a stage makes is pushed even when the stage fails or times out (`optional` stage or a push in the same command);
  `lint_manifest.py` (rules `picture_budget`, `fatal_before_push`) runs before every pod start and must print nothing.
- The rule is a method, not a constant: when a card, resolution or step count changes, re-measure and edit the row; do not
  widen a limit by guesswork and do not shrink one without a measurement. Origin: the lost 35-picture run (R-29,
  PROGRESS 2026-10-16).

## Never
Skip the creator gates; publish, or upload other than the unlisted/private staging of D-57 after the creator's OK; exceed a budget cap or call a paid service without the ledger entry; invent
sources, metrics, measurements, tests or tool capabilities; claim a task is complete from code changes alone; weaken or
remove a test or acceptance criterion; bypass the schema; change the strategy, identity, hardware baseline, budget,
publication rule, schema or renderer silently; delete broadly or expose credentials; add a dependency, hook, agent or
abstraction without a specific stated benefit; use another channel's protected characters, footage or titles. If tool,
repository or source access is missing, say so and document the limitation.
