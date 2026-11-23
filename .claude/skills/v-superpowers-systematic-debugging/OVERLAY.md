# Overlay for `v-superpowers-systematic-debugging`: Root cause first (layer L33, every stage)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from obra/superpowers, page `systematic-debugging` (MIT, commit `22f0b463e7`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a media pipeline whose bugs show up as stage records,
gate rows and files on disk as often as stack traces. The upstream text is this folder's `SKILL.md`; the
technique pages beside it stay usable (table below).

## The law, and where it comes from here

No fix before the cause is known. This is the creator's own order of work (2026-10-17): study the process and the real
output first (open the files, measure, find the cause), then research, then ask what is his, then update rules and
tests, and only then produce. A guess that happens to work hides the next bug; a guess on a paid path costs money.

## Phase 1: read and reproduce

1. **Read the whole message.** The traceback, the gate row's detail, the validator's rule id and `where`. Our rows
   name the rule (PV-37, VL-06, MA-04...) and the item; that is usually most of the answer.
2. **Read the record, not your memory of it.** `python -m explainer_engine.episode status <episode>` lists the stages
   and their records (under the episode's `production/stages/`); open the record of the failing stage and its inputs.
3. **Look at the real output.** Probe the clip, listen to the stem, open the picture, read the JSON. "Look at the
   output before reporting it" is a production rule; it is also the first debugging step.
4. **Reproduce on the smallest input.** One shot, one segment, one fixture. Run one stage
   (`python -m explainer_engine.episode run <episode> --stage <name>`) or one test node, never the whole episode to
   see one bug.
5. **What changed?** `git log` and `git diff` on the files the stage reads, the inputs' hashes, the registry
   (`explainer_engine/standards/sourced_rules.json`), the config.

## Phase 2: trace back to the entry point

Follow the wrong value backwards: which function produced it, who called it with what, until you reach where it first
became wrong. Fix it there, not where it surfaced. Recent examples in `docs/PROGRESS.md`: a word filter that dropped a
real repeated line (cause in the filter's rule, not the clip), proposals overwritten per scene (cause in one atomic
write of only this call's list). `root-cause-tracing.md` has the method.

Compare with what works: another episode, another scene, the last good commit, the module's own tests. List every
difference, however small; the one you dismissed is often the one.

## Phase 3: one hypothesis at a time

Write it down: "X is the cause because Y". Change one thing, smallest possible, and measure. If it was wrong, undo it
before the next try. Do not stack fixes. If you do not understand something, say so and find out; do not pretend.

## Phase 4: fix with a test

1. A failing test that reproduces the bug (skill `v-superpowers-test-driven-development`).
2. One fix at the cause. No "while I am here" changes (invariant 8).
3. The test passes, the focused files pass, then the full suite once; re-run only failures while fixing.
4. A `docs/PROGRESS.md` entry: what broke, the cause (file and function), the general fix, the test that guards it.
   Where a stale doc or rule caused it, report the stale text and continue (ICW-01 precedence), never silently delete it.

## When to stop and ask

- **Three fixes failed on the same problem:** stop. The design is the suspect, not the fourth fix. OR-04 says the
  same for any item or phase: two tries at the assigned level, the third only escalated, then stop. Bring the evidence
  to the planning thread on the higher model (OR-24, OR-26).
- **The cause is a conflict with an approved decision or architecture:** stop at the boundary, report evidence and
  options, ask (invariant 12).
- **The fix needs a system choice nobody settled** (a model, a setting, a threshold, a rule's wording, any spend):
  put it to the creator (OR-22). Never decide it on an assumption, not even in auto mode.

## Paid and media failures

- A paid call whose result is uncertain is never retried blindly: reconcile the provider state, the job id, the
  ledger (`explainer_engine/core/ledger.py`) and the output store first. A duplicate submit can bill twice.
- A picture or clip that looks wrong is diagnosed with its own ladder: P-5 observe every asset, repair rungs R1-R4, at
  most two generative retries (skill `v-ltxv2-video`, skill `v-director-cinematic`). Code is suspected only when the
  plan and the output disagree in a way the plan cannot explain.
- An error class tells you the path: `explainer_engine/core/errors.py` separates contract, config, retryable and
  needs-review errors. A `ContractError` is a bug or a bad input, never something to retry.

## Red flags in your own head

"Quick fix now, investigate later." "Just try raising the threshold." "Skip the test, I checked it by eye." "It is
probably the provider." "One more fix" after two that failed. Each means: back to phase 1.

## References: when to open which

| File | Open when |
|---|---|
| `root-cause-tracing.md` | the bad value appears deep in a stage and you must walk the call chain back |
| `defense-in-depth.md` | the cause is fixed and you want the input checked at the boundary too (schema, validator, runner row) |
| `condition-based-waiting.md` | a test or watcher sleeps a fixed time and flakes; poll for the condition instead |
| `condition-based-waiting-example.ts` | the same idea in TypeScript, for reading only |
| `find-polluter.sh` | a test leaves files behind; the script is written for `npm test`, so copy its bisect idea with pytest node ids rather than running it |

## Not used from upstream

The "your human partner" signals section (our creator does not read code; his signals are rules), and the advice to
add retries or timeouts when no root cause is found: here an environmental cause is documented in PROGRESS and,
where money is involved, handled by the ledger and the cloud rules, not by a new retry loop.
