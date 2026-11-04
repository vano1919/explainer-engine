# Claude handoff: Gemini Master Mold package (2026-11-04)

**Branch:** `claude/master-mold-ready-2026-11-04`
**Base:** `planning/master-mold-integration-2026-11-02` at `bb0da660582ac0868825d88592276d7d43c234d5`
**Source archive:** `explainer-engine_CLAUDE_TODO_MASTER_MOLD_READY_2026-11-04.zip`
**Archive SHA-256:** `AA5433AACFA9FB5964705E25397164DDC73E1059A2EE5FAF4AC0BEFFD58CF674`

## Read first

1. [Synchronized TODO execution guide](CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md)
2. [Gemini full-repository audit brief](GEMINI_ARGON_MASTER_MOLD_FULL_REPOSITORY_AUDIT_2026-11-03.md)
3. [Master Mold integration roadmap](MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md)
4. [Canonical decision log](../DECISIONS_AND_OPEN_QUESTIONS.md) and the latest entries in [PROGRESS](../PROGRESS.md)

The execution guide and audit brief are source material to inspect, not authority to execute. The audit brief explicitly requests a read-only audit. The guide's claims, recommendations, proposed code changes, test names, and creator-decision labels all require independent verification. This handoff does not authorize implementation, spend, pods, publishing, or changes to creator-owned decisions.

## What was imported

- The ZIP's roadmap, Gemini audit brief, and synchronized execution guide.
- The 301 Python files carrying `[CLAUDE-MASTER-MOLD-SYNC]` TODO material: 259 existing modules and 42 new stubs. A comparison after removing the inserted module/class TODO comments found no executable-body differences in the 259 existing modules; four `__init__.py` differences were whitespace-only. Treat every TODO as an unverified proposal.
- The archive's verified-shot digest was not replaced; its SHA-256 already matched the branch copy (`F745C487EB0BEB4792D4900D803BC998B8795D3D51416ACF9B9B9DFA1F418B33`).

The imported package is only a selected part of a 1,353-entry repository snapshot. Do not overlay the archive wholesale or infer that unimported snapshot differences are approved changes.

## Discrepancies to verify before acting

- The execution guide lists baseline hashes `5013a55aa910820db16be2e59f9045a79573b219` and `bb0da662273ebcd18120c9eb8e2524df87efca2e`. The pinned project references available here are PR #119 code baseline `5013a55aca5a17a3734150f61a5eb172abcbe3b8` and planning branch base `bb0da660582ac0868825d88592276d7d43c234d5`. Re-establish the correct comparison for every finding; do not reuse the guide's line numbers as current.
- The guide and roadmap label `CD-01..CD-06` as locked creator decisions. They are not recorded as such in the canonical decision log. In particular, that log has no `D-96` entry, and `PROGRESS.md` explicitly keeps `CD-05` open pending measurement and separate approval. Do not treat any proposed value or option as the creator's word.
- The guide's claimed tests are not all present. The paths `tests/test_continuity_and_jump_cut_laws.py`, `tests/test_word_clock_and_prop_face_grounding.py`, and `tests/test_cpfm_cost_protocol.py` were absent from the source archive. Check the actual branch and test inventory before reporting any test as existing or passing.
- The guide says every top-level class has a class TODO; the archive has 88 class TODO annotations, so that completeness claim is unverified.
- Its seven "critical synchronization mismatches" are claims to check against actual code, schemas, tests, and current documentation. Do not apply the prescribed fixes until each mismatch and its acceptance criteria are independently established.

## Deliberately not imported

- `config/job_speeds.json`: the ZIP adds A100/A40 rows attributed only to `"pod x"`. Their provenance and measurements are not established; preserve the branch's existing values until verified and any required creator decision is recorded.
- `jobs/` and `tools/runpod/` runtime logs/session state.
- The remaining repository snapshot changes, including configuration, settings, agents, skills, and unrelated documents. Review each separately if needed; none is approved merely by appearing in the ZIP.

## Suggested next work

1. Begin with the audit brief's read-only scope. Reconfirm the branch base and inspect each claimed discrepancy on this branch; distinguish verified defects, proposals, missing evidence, and creator decisions.
2. Check the 42 stubs and every TODO against existing modules, schemas, gates, tests, and downstream callers. Preserve existing behavior; do not implement a batch from the guide alone.
3. Update canonical decisions or request the creator's answer wherever a choice is not already recorded. Keep the existing `CD-05`/D-67 approval boundaries intact.
4. Only after the audit and required approvals, propose a small, dependency-ordered free change set with focused tests and a `PROGRESS.md` entry. No paid API or pod action is authorized here; any pod still needs the itemized OR-23 plan and approval, and paid tests remain subject to OR-34.
