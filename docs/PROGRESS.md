# Progress log

Append one entry per phase boundary: completed work, state, files changed, test results, decisions, blockers,
cost (estimate/actual), next step, recovery instructions.

## 2026-10-15 — Plan approved (Mode A)
- Approved plan: `docs/PLAN_2026-10-15.md`. Creator decisions: D-13 (Claude Code sessions draft research and scripts),
  D-21 (separate repository), repo name `explainer-engine`.
- Spend: Gemini $0.00 of $10; vidIQ 0 of 200 credits (account balance read 2026-10-15: 395, call cost 0).

## 2026-10-15 — Phase 1: new repo, inventory & safeguards (in progress)
- Blocker: creating `vano1919/explainer-engine` through the GitHub integration returned 403 ("Resource not accessible
  by integration"). The scaffold was built and committed in a local repository; it is pushed once the creator creates
  the empty repository and it is attached to the session.
- Done: scaffold (`explainer_engine/core`, `explainer_engine/audio`, `tests/unit`, `docs/`), `.gitignore` (jobs, media,
  models, keys), `requirements.txt` (numpy, jsonschema, pyyaml, pytest), `pytest.ini`, `setup.ps1`, `CLAUDE.md`;
  copied modules with provenance (`docs/PROVENANCE.md`); `docs/REPO_REUSE_AUDIT.md`.
- Tests (Linux sandbox, Python 3.13, fresh venv): `python -m pytest -q` → 24 passed. The guard test was checked
  against a planted `from tmr_engine import x` (it failed as intended). Not tested: `setup.ps1` on Windows.
- Not done in Phase 1 by design: Kokoro, Node/Remotion, schemas (Phases 3–5).
- Next: Phase 2, the decision and specification pack (split the plan into the canonical docs), Kit reference sheet
  draft, palette contrast check.
- Recovery: the local clone is a plain git repository; `git push -u origin main` after `git remote add origin ...`.

## 2026-10-15 — Phase 1 pushed
- `vano1919/explainer-engine` created by the creator; commit `a41e47b` pushed to `main` (the repo was empty, so no PR).
  Remote clone checked: 25 files, 24 tests pass.

## 2026-10-15 — Phase 2: decision and specification pack (branch `phase-2-spec-pack`, draft PR)
- Done: 19 canonical documents + `docs/INDEX.md`; `explainer_engine/design/palette.json` + `palette.py` (contrast and
  rules); `assets/characters/kit/kit_reference.svg` (draft v0: body, limbs, two lid states, 8 expressions, 6 speech
  mouths); `explainer_engine/docs_lint.py` (one home per ID, links, JSON fixtures, no hex in docs).
- Measured (palette): ink on paper 14.7:1; every accent colour is 1.5-3.7:1 against paper, below the 3:1 graphics need,
  so accents are fills with an ink stroke and `false_red` text is large-only (D-22). The plan's colour table had not
  stated this; it is now a tested rule.
- Decisions added: D-07 (hook framework, was cited but undefined), D-08 (export targets), D-09 (language), D-22
  (accent rule), D-23 (canonical homes).
- Tests: `python -m pytest -q` -> 36 passed; `python -m explainer_engine.docs_lint` -> 0 findings (verified to fail on a
  planted dangling ID, duplicate definition and broken link). The Kit sheet was rendered with headless Chromium and
  inspected by eye; its first render had clipped labels and box-shaped eyelids, fixed before commit.
- Deviation from the plan (G.2): `.claude/rules/`, skills and hooks are not written in Phase 2. The path-scoping and
  hook syntax for the installed Claude Code version were not verified, and the directive says to verify first and add
  only what a workflow justifies. They are scheduled with Phases 3, 4 and 6 (`docs/CLAUDE_EXECUTION_GUIDE.md`).
- Not verified: the official YouTube thumbnail size limit and chapter minimum (marked "re-verify" in P-17, P-19; checked
  in Phase 7); Fredoka and Inter licence files (recorded in Phase 4).
- Awaiting the creator: review of strategy, identity and Kit's look (approval gate 1 in the decision log; Q2: final name).
- Next: Phase 3, contracts first (JSON Schemas for config, assets, storyboard, audio events, manifests, timing, job
  state, with valid and invalid fixtures).

## 2026-10-15 — Creator feedback on Phase 2 and niche research
- Creator feedback: Kit / the visual direction was disliked; asked why this topic and what it rested on.
- Honest finding written to docs/MARKET_RESEARCH.md B.7: the original topic pick was a reasoned guess under the
  creator's constraints, not measured demand; the supplied report covers Shorts, not 5-11 minute explainers.
- vidIQ research (creator approved ~60 credits): 60 spent (6 outlier searches, 6 keyword researches; 5 credits wasted on
  an unusable generic seed). Account 445 -> 385. Project cap 200: 60 used.
- Result: finance (SE-34) and what-if/space (SE-35) have the widest small-channel breakout evidence; everyday mechanisms
  (SE-29) has real breakouts at our length, mostly about vehicles; stories (SE-33) are kids / third-party IP.
- Decisions: D-01 reopened and then resolved for now by **D-24** (creator: test both arms before choosing); D-04 Kit
  draft v0 rejected, new direction hand-drawn / doodle style (creator, 2026-10-15).
- Next: doodle style samples for the creator's reaction (`assets/style_samples/`), then redesign of the mascot and
  palette (D-04) before Phase 4; Phase 3 (contracts) does not depend on the visual style.
