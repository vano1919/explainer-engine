# Overlay for `v-superpowers-subagent-driven-development`: Running a plan through workers (layer L33, every stage)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from obra/superpowers, page `subagent-driven-development` (MIT, commit `22f0b463e7`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for this project's split of roles: the creator decides,
the Opus thread plans, the working session implements, workers do one slice each. The upstream text is this folder's `SKILL.md`; its prompt templates and `references/` stay usable (table below); its `scripts/` are not run
here as they stand (see the workspace note).

## When this fits

Fits: a plan already agreed (by the Opus planning thread, OR-24, OR-26, and where needed the creator), with tasks that
touch separate files: ten skill folders, five validators, one schema per stage. RW-50 itself runs this way: one brief
file, each worker given its own folders, the main session committing.

Does not fit: tightly coupled work (one module refactor), a plan nobody agreed, or anything that spends money. A paid
run is never a worker task; it waits for the OR-23 plan, the OR-34 audit, CH-07's paid offer where it applies, and the
creator's word.

## Roles and models

- **Creator:** every system decision a plan does not settle (rule one, OR-22): model, setting, threshold, rule wording,
  data, spend. Also in auto mode.
- **Opus planning thread:** writes the plan and answers hard technical questions before the work (OR-26).
- **Coordinator (this session):** splits, briefs, reviews, merges, commits when asked. Only the orchestrator and the
  LoRA coordinator agents may spawn (`tests/unit/test_agent_governance.py`); critics are read-only.
- **Workers:** one task each, on the model and effort `config/model_routing.json` gives that task class (OR-29). Pick
  the class, not a favourite model; say the model explicitly when dispatching. The file changes only on the creator's
  word.

## Setup

1. Read the plan once; note its constraints and the decisions it cites. If it conflicts with the decision log, the
   decision log wins; report the stale text (ICW-01 precedence) and do not dispatch on the stale part.
2. Run a conflict scan before task 1 (`references/preflight.md`): two tasks writing one file, a task that needs another's
   output, a task that would need a paid step or a creator decision. Resolve by reordering or by asking.
3. Keep a ledger file: which task, which worker, what it touched, result, review verdict. Context compaction forgets;
   the ledger and `git log` do not.
4. **Workspace:** upstream's `scripts/sdd-workspace` creates `.superpowers/sdd/` inside the repository, which this
   repo does not ignore. Keep briefs, reports and the ledger in the session's scratchpad directory instead, and point
   workers at absolute paths there.

## The brief (one file per task or per batch)

Everything a worker needs, nothing it does not, written to a file it reads first:
- the goal in one paragraph and the exact files or folders it owns; "do not touch anything else";
- facts it must use (module paths, CLI commands, rule ids) and where they are defined, so it links instead of copying
  (one home per ID, `python -m explainer_engine.docs_lint`);
- the tests it must run and pass, and which failures are expected because other workers own them;
- hard limits: no paid calls, no git write commands, no edits to byte-pinned vendored files, no change to
  `config/spend_caps.json` or `config/model_routing.json`;
- the report it returns: per task the result, the measured numbers, what it could not verify.

Small same-shape edits across many files go to one worker as one batch (`references/batching.md`).

## The loop

1. Dispatch with the brief path. Keep working on the next brief while it runs; do not poll in tight loops.
2. Read the report as a lead (skill `v-superpowers-verification-before-completion`): check the diff, re-run its tests.
3. Review against the brief: did it stay in its files, does each named module or skill exist, is the PROGRESS entry
   there for a meaningful change (invariant 11), was any test weakened (invariant 10).
4. Findings go back to the same worker or a fresh one with the finding as its brief (`references/fix-loop.md`). Two
   rounds without convergence: escalate per OR-04, then stop and report.
5. Record the result in the ledger; next task.

## Stop and ask, never rule

Upstream tells the controller to make rulings and keep going. Here that is narrowed: a coordinator may settle
mechanics (order, batching, which test file to run), but a gap in the plan that touches a system decision goes to
the creator, and a material conflict with the approved architecture stops at the boundary with evidence and options
(invariant 12). Also stop for anything destructive, anything public (invariant 4), and any spend.

## Final review

After the last task: the whole suite once (`python -m pytest -q`), the docs linter, `python -m explainer_engine.governance check`,
`python tools/vendor_skill.py verify` when vendored skills were touched, and one broad review of the branch diff on a
strong model (`references/final-review.md`). Then the commit, by the coordinator, with the repository identity and the
session attribution, only when asked.

## References: when to open which

| File | Open when |
|---|---|
| `implementer-prompt.md` | drafting a worker brief; adapt the structure, replace its git steps with ours |
| `task-reviewer-prompt.md` | reviewing a worker's diff against its brief |
| `re-review-prompt.md` | re-checking after a fix round |
| `references/preflight.md` | the conflict scan before task 1 |
| `references/batching.md` | many small same-shape edits |
| `references/fix-loop.md` | before every fix round |
| `references/handling-reports.md` | a report is unclear, partial or claims more than it shows |
| `references/cannot-verify.md` | a reviewer cannot check a requirement from the diff alone |
| `references/final-review.md` | the end-of-plan review |
| `references/resuming.md` | picking up after a context loss |
| `scripts/task-brief`, `scripts/review-package`, `scripts/sdd-repo` | read for the idea (extract a task to a file, package a diff); run only with an output path in the scratchpad |

## Not used from upstream

Continuous execution with rulings on open questions (OR-22 overrides it), cheapest-model selection by the controller's
judgement (OR-29 and the routing file decide), workers that commit their own work, worktree creation as a default,
deleting the workspace at the end, and the hand-off to a finishing-branch skill we did not vendor.
