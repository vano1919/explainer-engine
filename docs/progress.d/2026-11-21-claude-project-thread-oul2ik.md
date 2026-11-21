## 2026-11-21 — Progress rule and stop hook point to fragments
- Done (owner's card 06:45 UTC, "Update both"): CLAUDE.md invariant 11 and the layout line now require a `docs/progress.d` fragment checked by `progress_fragments check`; the stop hook (`governance/hooks.py`, `_progress_logged`) accepts the phase name in any fragment, or in the frozen `docs/PROGRESS.md` for old phases.
- Tests: `tests/unit/test_governance_hooks.py::test_stop_checks_the_active_phase_checklist` now proves a fragment satisfies the hook.
