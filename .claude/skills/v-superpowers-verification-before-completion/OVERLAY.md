# Overlay for `v-superpowers-verification-before-completion`: Evidence before "done" (layer L33, every stage)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from obra/superpowers, page `verification-before-completion` (MIT, commit `22f0b463e7`). Rewritten 2026-11-20
under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a pipeline where "done" may mean a green test
suite, a gate row, a rendered chunk or a file in the vault. The upstream text is this folder's `SKILL.md`;
there are no upstream reference files.

## The rule

No claim of completion without fresh evidence from this turn. Our system already says it in its own words: every gate
measures or says NOT_RUN (D-131); look at the output before reporting it; never say "done" or "saved" unless the
output exists in the vault and its hash matches (cloud rules, section 8). This page is the checklist that makes those
rules automatic for code work too.

## The gate, every time

1. **Name the claim** in one line ("the tests pass", "G6 passes on ep_truce_1914", "the clip is in the vault").
2. **Name the command that proves it** (table below).
3. **Run it now, whole.** Not a cached result from earlier in the session, not a subset dressed as the whole.
4. **Read the output**: exit code, counts of FAIL and REVIEW, NOT_RUN rows, warnings.
5. **Say what it showed**, with the numbers. If it fell short, say that instead, and what is left.

## What proves what here

| Claim | Proof |
|---|---|
| tests pass | `python -m pytest -q` exit 0 with its count (a focused file passing proves only that file) |
| docs are consistent | `python -m explainer_engine.docs_lint` clean |
| governance is consistent | `python -m explainer_engine.governance check` |
| vendored skills untouched | `python tools/vendor_skill.py verify` reports 0 problems |
| a skill rewrite counts | `python -m explainer_engine.governance.skill_rewrite` row at or above the line |
| a script is valid | `python -m explainer_engine.production validate <script>` with 0 FAIL, REVIEW items listed |
| an episode stage passed | `python -m explainer_engine.episode run <episode> --stage <name>` and its record: PASS rows, and every NOT_RUN named |
| the episode is accepted | G10's measured acceptance report, read row by row, not its headline |
| rights are clear | `python -m explainer_engine.rights.ip_check <manifest>` exit 0, every REVIEW answered |
| packaging is ready | `python -m explainer_engine.qa.publish_check <publish.json> --episode <folder>` |
| a paid output is saved | the file in the HF vault and its SHA256 matching the local or reported hash (OR-33) |
| nothing is billing | the provider check at the end of the run, per the cloud rules |
| a bug is fixed | the reproducing test failed before the fix and passes after it |

## Reports from others are leads, not proof

A subagent, a worker thread, the Opus planning thread or an API review that says "all green" has told you what it
believes. Check the diff (`git diff`, `git status`), re-run the named tests, open the file. A worker brief that says
"failures outside your folders are expected" still needs you to read the failures and confirm they really are outside.

## Words to watch in your own reply

"Should pass", "looks fine", "probably saved", "done" before running anything, "all tests pass" after running one
file, "verified" for a claim-map row you did not open (invariant 5: say exactly what was and was not verified). Each
one means: run the proof or soften the sentence.

## Honest partial results

It is fine to report "12 of 14 pass; the two failures are in `tests/unit/test_x.py` and name only folders another
worker owns" or "G7 NOT_RUN: no Modal budget line" (Modal has a zero budget until `config/spend_caps.json` has its
line). It is not fine to round that up to "done". A NOT_RUN is a result, never a PASS.

## Before a commit or PR

- Commits happen only when the creator or the main session asks; workers do not run git write commands.
- The full suite was run in this turn, the docs linter is clean, the PROGRESS entry exists for a meaningful change
  (invariant 11), and no test was weakened (invariant 10).
- The commit uses the repository's identity (`git -c user.name=vano1919 ...`, CLAUDE.md conventions) and the session's
  attribution lines.
- No secret, media file or credential is staged (`tests/unit/test_repo_hygiene.py` guards this).

## Usage limits

At 95 % of the five-hour or weekly limit the unfinished work is backed up (project files and a WIP commit on the work
branch, OR-30). A backup is not completion: the report says what is unfinished.

## Not used from upstream

The "your human partner" trust framing and the personal-failure anecdotes. The gate itself is upstream's idea kept
whole; the commands are ours.
