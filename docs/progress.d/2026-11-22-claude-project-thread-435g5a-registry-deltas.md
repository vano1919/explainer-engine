## 2026-11-22 — Registry deltas: C04 append-only check and LAYER_COVERAGE count confirmed

**Done** — Added `test_c04_resolution_is_append_only_against_base_snapshot` in `tests/unit/test_owner_requirements_deltas.py`, with base snapshot fixture `tests/fixtures/owner_registry_base_c04.json` (the two entries OR-C04 and OR-A07 taken from commit `1e530833`, before the C04 resolution). The test checks that the OR-C04 flip from open to resolved passes `compare_with_base` with no findings.

**State** — `LAYER_COVERAGE.md` was regenerated with the repo generator (`governance requirements --coverage`) and matches it: 246 active entries, 7 open conflicts. No change to the file.

**Files** — `tests/unit/test_owner_requirements_deltas.py`; `tests/fixtures/owner_registry_base_c04.json`. Not changed: `docs/PROGRESS.md` (frozen log), `owner_requirements.json` (group B, waiting for the owner-signed DR route).

**Tests** — `test_c04_resolution_is_append_only_against_base_snapshot`: `compare_with_base` over the OR-C04 open→resolved flip returns no findings.

**Decisions** — Correction: the review's count of 245 was a hand calculation from an incomplete diff; 246 is the generator's count and stands. The earlier statement that `compare_with_base` was clean covers the state before the C04 resolution commit `6cbb2e7a`; the new test covers the resolution itself.

**Cost** — DeepSeek Flash, about 0.001 USD for the test.

**Next step** — Group B, after the DR route.

**Recovery** — `git revert` of the test commit removes the new check only.