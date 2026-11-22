## 2026-11-22 — PC-10 third-party media gate fails closed without a manifest

**Done:** commit `175974b` makes PC-10 FAIL when the library manifest is missing or unreadable (before it passed silently). The change is in `explainer_engine/qa/publish_check.py`.

**State:** focused tests pass.

**Files:** `explainer_engine/qa/publish_check.py`; `tests/unit/test_third_party_media.py`. Only these two changed in commit `175974b`.

**Tests:** 10 tests in `tests/unit/test_third_party_media.py` pass, including 4 new cases: missing manifest, corrupt JSON, manifest without items, id absent from a readable manifest stays REVIEW.

**Decisions:** PR 201 also contains `sources.py`, `test_sound_design_system.py`, `docs/QA_SPECIFICATION.md` (one PC-10 row), and the slice 1.4 files. Those files are outside the slice 1.4 allowlist; the allowlist change is the creator's decision (requested by card).

**Cost:** 0 USD for the commit itself (DeepSeek Flash, about 0.002 USD).

**Next step:** creator decides the allowlist for `sources.py` and `publish_check.py`.

**Recovery:** `git revert 175974b` restores the old silent pass.