# ChatGPT repository workflow

## Purpose
This is the working contract for managing the repository through ChatGPT while preserving the existing Claude workflow.

## Branch isolation
- Base: `systemic/next-video` at source commit `a1821958c4195953e52261bfb42d9b3351d6aa45`.
- ChatGPT branch: `chatgpt/repo-management`.
- The original base branch is not modified by this work. ChatGPT-specific instructions live in `CHATGPT.md` and `.chatgpt/`.
- No automatic merge or default-branch change is authorized.

## Canonical reading order
1. `CHATGPT.md` — copied Claude invariants plus ChatGPT-specific controls.
2. `docs/INDEX.md` — canonical specification locations.
3. Last entries of `docs/PROGRESS.md` — recent implementation and test evidence.
4. Task-specific implementation, tests and the canonical spec it implements.
5. `.chatgpt/skills/` for cloned domain instructions; `.chatgpt/rules/` for ChatGPT-specific additions.

## Current implementation to reconcile
The current renderer in `explainer_engine/production/assemble.py` is the Python/NumPy/PIL/FFmpeg assembler. Older `docs/RENDERING_ARCHITECTURE.md` still describes Remotion as primary and the implementation plan still describes early phases. Do not blindly follow stale prose. Reconcile these docs against actual code, measured renders and current `PROGRESS.md`; do not replace the working renderer by default.

## New script quality gate
The existing rubric in `docs/SCRIPTING_SPEC.md` is now represented by an executable gate for new scripts.

A new script must have an `editorial` object with `version: 1`, `sources[]` and `claims[]`. Each source records ID, URL, title, publisher, access date, grade and supporting passage. Each claim records ID, text, type, source IDs, confidence and uncertainty wording. Every narration line has `kind`. Lines classified as fact, analysis or speculation must reference claim IDs; factual lines cannot refer to unknown or unsupported claims.

Save `editorial_review.json` beside the script. It includes:
- `schema: editorial_review/1` (a `production_script/3` requires `editorial_review/2` with its `integrated`
  production-coherence section — contract in `docs/SCRIPTING_SPEC.md` section 5.2, D-60)
- `script_sha256`: SHA-256 of the exact bytes of `production_script.json`
- `reviewer_role: independent_critic` and `independent: true`
- `scores`: every rubric criterion with a 1–5 score and a concrete evidence note
- `critical_blockers` and `required_revisions`

Run the structural validator, then:
```powershell
.venv\Scripts\python -m explainer_engine.production.editorial_gate examples/<episode>/production_script.json --review examples/<episode>/editorial_review.json
```
Any failure blocks paid narration and asset creation. Editing the script invalidates the old review hash.

## Parallel production
After approval, schedule independent preparation tasks in parallel while keeping dependencies explicit:
- actual voice read → measured word timings → final cut timing;
- storyboard/shot plan → image prompts and asset list;
- sound-event plan → required SFX/ambience assets;
- music plan → licensed/procedural music preparation;
- packaging draft can start from the approved promise/title and finalize after the cut.

Final assembly waits for the actual read, real timings and all required assets. Preserve resumable per-item outputs and an authoritative job ledger. Final QA includes machine checks plus human listening/visual inspection.

## Implementation priorities
1. Enforce source/claim mapping and independent review for new production scripts.
2. Reconcile stale renderer and phase-status documentation from current code.
3. Implement a dependency-aware coordinator for parallel tasks, retries, persistence and resumable jobs after auditing current command paths and failure recovery.
4. Keep strategy changes, budget caps and publishing under creator control. Do not repeat questions already answered in the repository.
