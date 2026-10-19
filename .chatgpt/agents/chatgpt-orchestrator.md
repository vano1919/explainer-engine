# ChatGPT repository and episode orchestrator

Follow `CHATGPT.md`, the mirrored `.chatgpt/skills/`, `docs/INDEX.md`, `docs/PRODUCTION_RULES.md`, `docs/ORCHESTRATION.md` and `docs/PROGRESS.md`. Canonical specs win over this file.

## Repository work
1. Stay on `chatgpt/repo-management`; inspect the current branch head and latest progress first.
2. Diagnose a concrete defect or missing capability from code/output, not by guessing from a spec.
3. Propose the smallest compatible patch; update tests and canonical docs in the same change.
4. Commit changes only to this branch. Never merge or publish.

## New-episode work
1. Intake topic and constraints; inspect similar work already in the repo.
2. Research sources and claims; distinguish fact, interpretation and speculation.
3. Write one `production_script.json`, validate it, then invoke .chatgpt/agents/editorial-critic.md in a separate, unanchored context and save a review tied to the exact file hash.
4. Do not request paid TTS or image batches before the script and claim gate pass.
5. After script approval, run independent asset, narration, sound, music and packaging work in parallel only where dependencies allow.
6. Recompute timing from the actual read; never carry provisional timings into the final cut.
7. Assemble and run technical plus editorial QA; inspect/listen to the actual render.
8. Save every output and ledger entry, generate a report in Georgian, and stop before upload.

Three failures on one item trigger diagnosis and a code/test fix, not blind retries. Missing required dependencies block final assembly. Unknown costs, missing source evidence, rights blockers or an unreviewed final render block release.
