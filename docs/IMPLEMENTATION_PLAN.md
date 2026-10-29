# Implementation plan

> **SUPERSEDED (2026-10-29, P0a): history, not the live plan.** The live plan is `docs/PROGRESS.md` and the blueprint plan (project files `blueprint_2026-10-29/`); the stage table below is a target design.

## Status override — checked 2026-10-18

The phase status below is the original implementation plan and is stale as a live status tracker. The branch has progressed through the D-43 production script, the Python/FFmpeg assembler, sound and visual checks, episode orchestration, the script source/claim gate, and ChatGPT branch tooling; see the end of `docs/PROGRESS.md` for measured events. Use `docs/INDEX.md` for current canonical specifications.

Treat remaining rows below as a checklist to reconcile against the code, not as evidence that a phase is untouched or completed. Before claiming a capability, inspect its actual implementation and tests. A full dependency-aware end-to-end coordinator and a full test run after the new editorial gate are still outstanding.

Dependency-aware phases. Every phase: inspect the relevant files, state the minimal change, implement it, run focused
tests, then the full suite, inspect output artifacts, record failures, update [PROGRESS](PROGRESS.md) (and the decision
log if a decision moved), and report each acceptance criterion as pass, fail or not tested. Phases are not merged unless a
documented dependency requires it. Status: Phase 1 done (24 tests), Phase 2 in review.

| # | Objective | Creates / changes | Inputs -> outputs, contracts | Tests and acceptance | Failure modes -> recovery | Definition of done | Stop conditions |
|---|---|---|---|---|---|---|---|
| 1 | Inventory and safeguards | scaffold, copied modules with provenance, `.gitignore`, guard tests | TMR modules -> copies | 24 tests; no media/keys tracked; no `tmr_engine` import | copied test fails for a non-coupling reason -> report | pushed, progress logged | TMR behaviour unclear |
| 2 | Decision and specification pack | `docs/*`, `palette.json` + checker, `kit_reference.svg`, docs lint | plan -> canonical docs | palette contrast test; sheet tests; docs lint | contradiction between docs -> fix the canonical one | creator reviews strategy and Kit | creator rejects the direction |
| 3 | Contracts first | `explainer_engine/schemas/*.schema.json`, `contracts.py`, fixtures | docs -> schemas for config, assets, storyboard, audio events, manifests, timing, job state | each schema: >= 1 valid and >= 3 invalid fixtures (type, enum, dangling ref, time overlap); rejects bad references and timestamps | a schema cannot express a rule -> a referential check in `contracts.py` | all schemas versioned and tested | a spec rule cannot be made testable |
| 4 | Deterministic scene proof + renderer benchmark | `render/` Remotion project, `render_bridge.py`, Kit component (3 actions), 20 s scene, benchmark script | storyboard fixture -> scene MP4 | same props -> identical frame hash; benchmark table (concurrency 2-5, RAM, disk) recorded | slow render -> tune concurrency; miss the gate -> skia fallback proposal | D-10 confirmed or changed with evidence | gate missed or licence changed |
| 5 | Narration and audio | `tts.py`, `alignment.py`, `audio_events.py`, `mix.py`, loudness gate, listening pack | script -> clips, words file, audio.wav | anchor resolution, ducking depth, LUFS on synthetic signals; real-model test of the timed path; blind A/B recorded | timed path missing -> estimated words + loudness mouth | one TTS route chosen with evidence | all Kokoro voices rejected -> propose a paid voice |
| 6 | Prototype pipeline | `job.py`, S01-S16 minimal, onion package, review bundle, QA, skills and hooks as justified | episode.yaml -> final package | full onion run; acceptance criteria 1-9 below; kill and resume test | a criterion fails -> fix that stage, rerun it | acceptance report filled with measured values; creator review | 5 iterations on one issue |
| 7 | Packaging and Shorts | thumbnail composition and export, metadata, vertical storyboard validator | package -> thumbnail, metadata, Short | 168x94 legibility; Short safe-area test; standalone checklist | | one Short passes | |
| 8 | Long-form scale-up | incremental tests 2, 4, 7 min | episode -> long video | same gates at 7 min; render < 2 h | RAM above 12 GB -> chunking change first | measured memory and disk profile | |
| 9 | Analytics and iteration | `analytics.py` (CSV import, snapshots), loop docs | Studio export -> records | fixture import tests | | baseline recorded | |
| 10 | Hardening | setup script (Node check, `npm ci`), lockfiles, recovery drills, licence register, security check, final report, updated execution guide | | fresh-clone setup documented on Windows; suite green | | final implementation report | |

## Prototype acceptance criteria (Phase 6; each reported pass / fail / not tested)
1. Every contract file validates; invalid fixtures are rejected with specific errors.
2. Output 1920x1080, 30 fps constant, 60-90 s, no missing scene or asset (manifest equals render log).
3. Scenes start within +/- 1 frame of their anchors; the knife SFX within 1 frame of its word (the target of [BP-54](SOURCED_RULES.md)); mouth timing correlates
   with the phonemes (lead 0-2 frames).
4. Integrated loudness and true peak inside [BP-50](SOURCED_RULES.md), no clipping, music under the voice by
   [BP-52](SOURCED_RULES.md) (LU on the stems), no unintended silence over 1.5 s.
5. No black or frozen picture over 1 s unless declared.
6. Captions: <= 2 lines, <= 42 characters, no overlaps, inside the safe area, timed to words +/- 100 ms.
7. Peak RAM < 10 GB; render wall time, disk and spend logged.
8. Every factual sentence maps to a verified source; the amber badge covers the weak tip or the tip is cut.
9. Creator approval of Kit, voice, pacing, humour and thumbnail, recorded in `acceptance_report.md`.
A failed criterion triggers a focused fix of that stage and a rerun; no 8-12 minute video until 1-9 pass.

## Prototype package (Phase 6 outputs, `examples/onion/`)
Topic and why it is representative and low-risk (P1, one mechanism, primary literature, strong visual metaphors, no health,
financial or political risk); the mini research dossier with claim-level mapping (candidates C1-C5 listed in
[PLAN_2026-10-15](PLAN_2026-10-15.md) section F are all unverified until Phase 6); working title and packaging options;
the full narration; a storyboard fixture of about seven scenes in contract v1; the asset list (reused, new, generated,
manual, third-party); the character consistency plan (the Kit sheet); the audio timeline with licences; the render
specification; captions and the vertical concept; the thumbnail concept; the QA tests and checklist; resource and cost
capture; the acceptance report template.
