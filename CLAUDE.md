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

**Autonomous runs:** `docs/ORCHESTRATION.md` and the `orchestrator` agent (`.claude/agents/orchestrator.md`): gated phases, hard caps in `core/ledger.py`, nothing lost on a stop, nothing public. Skills `science-grounding`, `time-jump-episode`, `shorts-for-video`.

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
