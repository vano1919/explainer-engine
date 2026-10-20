# ChatGPT repository-maintenance rules

## Before any edit
1. Confirm repository `vano1919/explainer-engine`, current branch `chatgpt/repo-management`, and branch head.
2. Read `CHATGPT.md`, `docs/INDEX.md`, the end of `docs/PROGRESS.md`, and the relevant source, tests and canonical specs.
3. Check whether a similar helper, schema, fixture or skill already exists. Extend it before adding a competing abstraction.
4. Record the current behavior and the smallest justified change.

## During edits
- Keep Claude's original instruction tree unchanged; ChatGPT instructions live in `CHATGPT.md` and `.chatgpt/`.
- Every production behavior change needs a focused regression test, then the full test run where an execution environment is available.
- Keep schemas strict. Do not weaken validation or turn FAIL into REVIEW to make old fixtures pass; migrate fixtures or isolate legacy behavior explicitly.
- Preserve resumability, atomic writes, run-ledger accounting, checksums and hard spending caps.
- Do not introduce a provider, paid service, runtime dependency or renderer unless the task requires it and the trade-off is recorded.
- Avoid concurrent writes to the same file. Fetch fresh SHAs before updates. Use a single tree+commit when several files must change atomically.

## Before reporting
- Inspect the committed diff, not only the intended patch.
- Verify new paths and key file contents from the branch.
- Report commit SHA, branch, files changed, tests run, tests not run and remaining blockers.
- Never claim a render, API call, balance check, test or human listening review happened without concrete evidence.
