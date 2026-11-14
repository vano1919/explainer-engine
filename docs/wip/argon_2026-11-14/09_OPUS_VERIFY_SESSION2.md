# Opus verification of Argon code task 1 (2026-11-14)
Applied Argon's full files on a clean worktree of 302c8dd (explainer-engine .venv, Windows).
- Diff is focused: run.py +116, directed25d.py +141/-, living_director.py 2 lines, motion_intent.py +60, BP-21 gains pre_accent_rate_min_per_s 0.018 (applied minimally; Argon's sourced_rules.json differed only by CRLF), 2 old tests adjusted, 1 new test file (7 tests).
- New tests: 7/7 FAIL on old code, 7/7 PASS on new code.
- Old focused suites (directed25d, living_director, motion_intent, c4a_review_fixes, v43_runner): 76/76 pass with the new code when run on their own.
- DEFECT 1 (test isolation): tests/unit/test_plan_steps_1_2.py replaces sys.modules entries with stub modules and restores them through monkeypatch._undo (private API). Run in one session with the old suites, 10 old tests then fail (e.g. "module explainer_engine.episode.events has no attribute spine_hash"). Fix: use monkeypatch.setitem(sys.modules, ...) / monkeypatch.setattr only, never a private undo list; better, stub at the call sites in run.py's namespace.
- DEFECT 2 (sandbox code in production): the main path is right (missing insert -> exact-length silence WAV -> VV.compose), but run.py also adds _compose_rehearsal_voice_fallback, used when VV.compose leaves no voice_track.wav. In production that silently replaces a failed compose with a hand-written splicer (16-bit mono, inserts appended after the whole read instead of at their timeline positions). It only exists to satisfy the stubbed test. Remove it; if voice_track.wav is missing after compose, raise ContractError.
- DEFECT 3: docs/SOURCED_RULES.md not regenerated -> tests/unit/test_sourced_rules.py::test_the_doc_table_matches_the_registry fails (run: python -m explainer_engine.standards.sourced_rules write).
- 74 test files touching the changed modules: 9 fail vs 8 on clean baseline; the only new one is DEFECT 3 (the other 8 fail on clean 302c8dd too: shorts_2k, sourced_rules cli, style_sheets x2, v43_ltx_jobs, variant_plan, videolane x2).

## After session 3 (Argon review + fixes), verified by Opus
- Reviewer confirmed all 3 defects and found 7 more (directed25d plate ghost at 1440p, per-frame depth flattening breaking frame purity and speed, "man"/"men" substring false positives, schema keys outside the task, failed/missing clip files in stage_sound, a T1 test passing for the wrong reason, a C4A test hiding the plate hole); fixed run.py, directed25d.py and two test files.
- New tests: 7/7 fail on old code, 7/7 pass on new. All 7 focused suites in ONE pytest session: 96 passed, 1 failed (test_sourced_rules::test_the_cli_check_and_render, fails on clean 302c8dd too).
- 74 test files touching the changed modules: 1362 passed, 8 failed, the same 8 that fail on clean 302c8dd. Zero regressions.
- NOT CHECKED: no real Truce clip rendered (CPU render of real shots is the next step); no eye review.
