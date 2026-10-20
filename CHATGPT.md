# CLAUDE.md — explainer-engine

A solo creator's 2D hand-drawn explainer channel ("worlds collide": history, science and money meeting other
eras, public-domain worlds only, D-25) and its production
pipeline: topic → research dossier + claim map → script → **creator approval** → schema-validated storyboard →
assets → Kokoro narration + timings → Remotion scene renders (muted) → Python mix → Shorts → thumbnail + metadata →
technical + editorial QA → review bundle → **creator approval** → manual upload. Cloud-first (D-31). Start from `docs/INDEX.md`: every specification and every ID (D-, SE-, V-, P-, R-, Q-) has ONE canonical home —
link to it, never copy it (`python -m explainer_engine.docs_lint` enforces this). `docs/PLAN_2026-10-15.md` is history.

## Commands

```powershell
.\setup.ps1                                   # once: .venv (Python 3.12/3.13) + packages
.venv\Scripts\python -m pytest -q             # all tests
.venv\Scripts\python -m explainer_engine.docs_lint        # docs: one home per ID, links, fixtures
.venv\Scripts\python -m explainer_engine.design.palette   # palette contrast table + rule check
```

## Invariants (do not violate; stop and ask if a task seems to require it)

1. Production is cloud-first (D-31): the cloud session + RunPod pods, RunPod hard cap $3, TMR's money-control rules
   (approved price and time cap per pod, `rp.py guard`, sweep at start and end, delete at the end). The creator's PC
   only reviews and uploads.
2. Budget caps are ceilings, not targets: Gemini ≤ $10 total, vidIQ ≤ 200 credits. Estimate and log before every paid
   call (`docs/COST_AND_TIME_MODEL.md` ledger); at 80 % of a cap stop and ask. Leave nothing paid running.
3. No long-form pipeline before the 60–90 s prototype passes its acceptance criteria (plan F).
4. No public upload, ever, without a recorded creator approval. No upload code in Phases 1–8.
5. No unsupported claims, fabricated research, invented metrics, or copied protected IP. Every factual sentence maps
   to a claim with a source; say exactly what was and was not verified.
6. The original character/visual identity stays stable (part-based rig, reference sheet; never redraw from scratch).
7. Versioned schema contracts are authoritative; never bypass or weaken validation to make a render pass.
8. No destructive command, broad deletion, credential exposure, or unrelated refactor without approval. Cleanup
   deletes only job directories via `core/jobs.clean_jobs`.
9. Do not change the approved strategy or architecture without new evidence and a minimal-change proposal.
10. Never remove or weaken a test or acceptance criterion to make a phase pass.
11. Every meaningful change: a focused test + an entry in `docs/PROGRESS.md` (and the decision log if a decision moved).
12. A material conflict found during implementation: stop at the boundary, report evidence and options, ask.

**Autonomous runs:** `docs/ORCHESTRATION.md` and the `orchestrator` agent (`.claude/agents/orchestrator.md`): gated phases, hard caps in `core/ledger.py`, nothing lost on a stop, nothing public. Skills `science-grounding`, `time-jump-episode`, `shorts-for-video`, `editing-style` (rules `docs/EDITING.md`), `video-editing-architect` (general technique database and QA list), `elevenlabs-voice` (first-take reads, credit saving).

**How we work (creator, 2026-10-17):** a change request goes in this order: (1) study the process and the real output (open files, measure, find the cause); (2) research when the topic needs it and write the findings into a skill; (3) ask the creator the questions that are truly his to answer; (4) update rules, skills, agents and tests; (5) only then produce. Never produce before steps 1-4. Creator notes become rules with a test (OR-09).

**Production rules (binding for every video, creator 2026-10-16):** start from `docs/PRODUCTION_RULES.md` and run
`python -m explainer_engine.production_gate <episode folder>` to see the gates (script, test read, shot plan, style bridge,
sprites, pictures, full read, render, QA). Skills: `narration-script` (how the narrator sounds), `shot-visuals` (what the pictures
show). Entertainment first, facts second; stakes and named heroes in every frame; one drawn world; limits computed from
measured speeds; every paid step estimated and approved first; look at the output before reporting it; reply in Georgian.

Also binding: crossover episodes of other people's fictional worlds follow docs/RIGHTS_AND_FAIR_USE.md (no third-party
media, our own art only, short analysed quotes, small recap, credited fan theories) and pass `rights/ip_check.py`.
Gemini only for reusable channel-identity assets (the mascot, thumbnail design elements), never for one
topic's pictures (creator's rule, 2026-10-11), except where the creator records an exception for an episode (D-44: Episode 1, new spend cap US$6 in `core/ledger.py`). Disclosure is decided per video by the checklist (realistic content
only, YouTube Help 14328491); channel audience "not made for kids".

## Layout

```
explainer_engine/core/    store.py (JobStore, atomic writes, stage registry), jobs.py (job naming, cleanup),
                          errors.py (Contract/Config/Retryable/NeedsReview), labels.py (evidence labels)
explainer_engine/audio/   timings.py (phoneme timings -> words), visemes.py (mouth opening/shape, blinks),
                          envelope.py (loudness mouth fallback)
explainer_engine/design/  palette.json (the only place hex colours live), palette.py (contrast + rules)
explainer_engine/docs_lint.py   documentation consistency (D-23)
explainer_engine/rights/  ip_check.py: rights check of an episode's rights manifest (RR rules, D-26); any FAIL blocks
explainer_engine/research/ fan_brief.py: fan research brief, audience balance, template phrases (crossover episodes)
explainer_engine/schemas/ versioned JSON Schemas (rights_manifest, fan_brief; the rest arrive in Phase 3)
.claude/skills/crossover-episode/   procedure for crossover episodes (fan research -> scenario -> script -> rights)
assets/characters/kit/    kit_reference.svg (character parts; poses and rig come in Phase 4)
tests/unit/               fast tests; test_repo_hygiene.py guards media/keys, tmr_engine imports, provenance
docs/                     INDEX.md and the canonical specifications; PROGRESS.md (read the last entry first)
jobs/                     job output (gitignored): jobs/<slug>/job-NNN_<date>/{state.json, artifacts/...}
```

## Conventions and gotchas

- Code copied from `vano1919/tmr-video-script-engine` carries a provenance header and a row in `docs/PROVENANCE.md`;
  never import `tmr_engine`.
- Write JSON/text through `core/store.write_json_atomic` / `write_text_atomic`: on Windows `os.replace` fails
  ("Access is denied") while another process reads the target; `replace_file` retries.
- Secrets live only in gitignored `tools/` or env vars; never log or commit them.
- No linter/formatter/CI: match the existing style by hand; line length ~120.
- Commit with `git -c user.name=vano1919 -c user.email=122537395+vano1919@users.noreply.github.com`.
- The Bash tool collapses `\\` inside heredocs: write Python edit scripts with backslashes to a file first.

## ChatGPT operating layer — extends the copied Claude rules

The complete Claude instruction file is copied above. Every file that existed under `.claude/` at source commit `a1821958c4195953e52261bfb42d9b3351d6aa45` is mirrored under `.chatgpt/`. These are snapshots, not a live sync. The original `CLAUDE.md` and `.claude/` remain untouched.

### Current-state precedence

1. Read `docs/INDEX.md` and the last entries of `docs/PROGRESS.md` before work.
2. Canonical specification documents indexed in `docs/INDEX.md` own requirements and IDs.
3. Actual code and recent measured outputs outrank stale architecture summaries. In particular, `explainer_engine/production/assemble.py` currently uses Python/NumPy/PIL/FFmpeg; do not assert that the runtime is Remotion merely because an older architecture document says so.
4. When code, a spec and the progress log disagree, report the exact conflict and reconcile the canonical doc as part of the change. Do not silently invent which implementation exists.

### Repository-change protocol

- ChatGPT-owned work goes only on `chatgpt/repo-management` unless the creator explicitly chooses another branch. Never write to `main` or `systemic/next-video`.
- Before editing, inspect the actual branch and relevant files. Identify current behavior, proposed change, interface impact, compatibility risk and tests.
- Preserve existing architecture and working code unless evidence justifies a targeted change. No broad refactor, renderer replacement or dependency addition by default.
- Keep changes focused. Modify implementation, tests, canonical docs and `docs/PROGRESS.md` together. Never weaken an existing test or acceptance rule to make a change pass.
- After editing, inspect the committed diff and fetch the committed files back from GitHub. Separate tests actually executed from tests merely added or planned. Never claim a test passed without running it.
- Fetch fresh file SHAs before updates. Do not force-update the branch or merge it without explicit approval.

### Script quality is a production gate

A production script is not approved because its JSON validates or because its authoring model says it is good. Use the dedicated editorial critic instructions in .chatgpt/agents/editorial-critic.md and .chatgpt/skills/editorial-critic/SKILL.md in a separate review context; the script author must not sign off on its own draft. Before paid reads or asset creation:

1. Run the existing production-script validator.
2. Require `editorial.version = 1`, a source register, a claim register, and a `kind` on every narration line. Every factual line must reference claim IDs; each claim must resolve to source IDs and recorded passages.
3. Produce an independent critic report tied to the exact script SHA-256. The reviewer must cite concrete locations or short excerpts for every score.
4. Run `python -m explainer_engine.production.editorial_gate <production_script.json> --review <editorial_review.json>`. Any failure blocks the next paid stage. If the script changes, its hash changes and its review must be regenerated.
5. Preserve the existing rubric gates: factual reliability, source coverage and title/thumbnail alignment each at least 4/5; no other criterion below 3/5; mean at least 3.8/5; no unresolved critical blockers.
6. Automated scores are triage, not proof of truth. High-risk and disputed claims still require source inspection and a second read where specified.

### Production execution

- Use one canonical `production_script.json` for narration, picture subjects/prompts, sounds, music, story order and editing cues. Do not create a second unlinked shot list.
- After script approval, schedule dependency-independent work in parallel: narration/read timing, asset generation, sound preparation, music preparation, graphics and packaging drafts. Final timing, assembly and rendering wait for actual read timings and required assets.
- Estimate and record every paid call before calling; use approved per-run caps and stop at the established 80% threshold. A cap is not permission to spend without the required approval.
- Save and record each item as soon as it is produced. Resume from completed outputs rather than buying or generating them again. Required missing dependencies block final assembly.
- The final video needs both technical QA and content QA. A green code test is not visual acceptance: inspect representative frames and transitions, listen to narration and mixes, verify story state at cut points, and report unresolved review items.
- Keep publishing manual. No upload or public action without separate creator approval.

### Response and decision discipline

- Reply to the creator in Georgian by default.
- Distinguish verified facts, code observations, inference, recommendations and decisions.
- For significant architectural changes, compare CURRENT → PROPOSED → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION before implementation, unless the creator has already approved that specific change.
- Ask only for decisions that genuinely belong to the creator. Do not ask again for choices already recorded in the repo.
