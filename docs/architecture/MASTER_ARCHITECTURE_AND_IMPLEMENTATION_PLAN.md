# Explainer Engine — Master Architecture & Implementation Plan

> **Owner:** Creator  
> **Document role:** Single master architecture, phase plan, and live execution-status register.  
> **Status:** IN PROGRESS — Phase 0 audit  
> **Audit baseline:** `o239-argon-impl` @ `a060cf0bb33a00974568d91c1dd30816de35da32` (2026-11-16 13:52:45 UTC)  
> **Created on branch:** `docs/phase-0-master-architecture-2026-11-16`  
> **Important:** This document is being populated in stages. A section is not considered audited merely because it appears in the target architecture. Evidence, confidence, limitations, and acceptance status must be recorded separately.

## Live Status — Phase 0

| ID | Work item | Status | Evidence / outcome |
|---|---|---|---|
| P0.0 | Freeze the audit baseline and scope | DONE | Read-only baseline recorded at `a060cf0`; no code, media, paid job, or existing PR changed |
| P0.1 | Repository, branch and PR inventory | DONE — initial pass | 2,546 Git tree entries; 102 branches; 17 open Draft PRs; active branch is 725 commits ahead of `main` |
| P0.2 | Architecture, module and contract audit | IN PROGRESS | Current v4.3 episode-first path and major package boundaries inspected; dependency and duplicate-path review remains |
| P0.3 | Latest Truce 1914 production, render and incident audit | IN PROGRESS | Shot plan, edit points, runbook and incident audit inspected; referenced Hugging Face media binaries have not yet been opened directly |
| P0.4 | Tests, CI, coding governance and release controls | DONE — repository-level pass | 367 unit-test files; latest PR Quality runs observed successful; active HEAD has no combined status checks; scheduled RunPod watchdog fails on missing secret in `main` |
| P0.5 | KEEP / IMPROVE / REPLACE / REMOVE / BUILD disposition | PENDING | Must follow completion of P0.2 and P0.3 |
| P0.6 | Target architecture and phased implementation roadmap | PENDING | Draft architecture is based on the creator's 81 decisions; reconcile against repository evidence before freezing |
| P0.7 | Final consistency review and Phase 0 report | PENDING | No implementation work is authorized by this audit document |

**Status protocol:** Update this table after each audit milestone. Use only `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `DONE`, or `DONE WITH LIMITATIONS`. A DONE status requires a recorded artifact, commit, test result, or source evidence. If the artifact cannot be accessed, mark the limitation instead of inferring its contents.

## Scope and safety of this audit

- Inspect the current repository and relevant historical branches/PRs; do not treat the old `main` branch as the sole current truth.
- Preserve current implementation, unmerged work, production assets, history, and owner-approved visual identity.
- Do not delete, rewrite, merge, close, force-push, or retarget any existing branch or PR during Phase 0.
- Do not run paid API calls, cloud GPU jobs, paid image/video generation, or publish anything.
- Do not change production code during Phase 0. Documentation in this single file is the only intended repository change.
- Clearly separate: verified repository facts, current implementation behaviour, previous-run reports, target decisions, assumptions, and recommendations.
- A target architecture decision does not automatically authorize replacing a current production route. A route changes only after evidence, impact analysis, tests, and owner approval where required.

## Audit baseline

The repository metadata reports `main` as the default branch. The active implementation baseline selected for this audit is `o239-argon-impl` at commit `a060cf0bb33a00974568d91c1dd30816de35da32`, not `main` at `073eb25cda135387c47dfc3aafb043cad0574ecc`. This choice is based on the creator's current working context and the newer committed work on `o239-argon-impl`; it does not assert that this branch is already the approved release branch.

Initial read-only inventory:
- Recursive tree: 2,546 entries, not truncated.
- Python files under `explainer_engine/`: 511.
- Python unit-test files under `tests/unit/`: 367.
- Remote branch refs returned: 102.
- Open PRs returned: 17; all are Draft.
- `o239-argon-impl` vs `main`: 725 commits ahead, 0 behind; compare reports 300 changed files (225 added, 74 modified, 1 removed).
- `main` branch metadata reports `protected: false`. The separate branch-protection endpoint returned 403 to the connected integration; ruleset details therefore remain unverified.
- The current active commit has no combined commit-status rows in the GitHub connector response. This is not proof that no local tests were run.

## Document map

1. [Owner decisions and immutable project constraints](#1-owner-decisions-and-project-constraints)
2. [Current repository architecture — evidence-based](#2-current-repository-architecture)
3. [Current production route and last Truce 1914 evidence](#3-current-production-route-and-truce-1914-evidence)
4. [Repository audit findings and disposition matrix](#4-repository-audit-findings-and-disposition)
5. [Target architecture](#5-target-architecture)
6. [Engineering governance and AI coding protocol](#6-engineering-governance-and-ai-coding-protocol)
7. [Production lifecycle](#7-production-lifecycle)
8. [Implementation roadmap and gates](#8-implementation-roadmap)
9. [Testing, quality, recovery, security and delivery](#9-cross-cutting-engineering-requirements)
10. [Risks, unresolved evidence and owner decision gates](#10-risks-and-open-items)
11. [Phase 0 execution log](#11-phase-0-execution-log)
12. [Source register](#12-source-register)

---

*This first checkpoint records the baseline and the status of the audit. The architecture and disposition sections will be filled only after the remaining repository and production evidence has been assessed.*
