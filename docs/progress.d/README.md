# Progress fragments

Since 2026-11-20 a change is logged as ONE new file here, not as a new entry at the end of `docs/PROGRESS.md` (every parallel branch appended at the
same spot, so each merged PR made the next one conflict). `docs/PROGRESS.md` keeps its old content, frozen.

- File name: `<YYYY-MM-DD>-<branch-slug>.md`, lowercase, e.g. `2026-11-20-claude-lipsync.md`.
- First line `## <YYYY-MM-DD> — <title>` (same date as the file name), then the entry exactly as before: done, state, files, tests, decisions,
  cost, next step, recovery. The rule is unchanged (CLAUDE.md invariant 11); only the place moved.
- Check: `python -m explainer_engine.progress_fragments check`; all fragments in order: `... assemble`.
- Rules PRG-01..PRG-06 and the tests: `explainer_engine/progress_fragments.py`, `tests/unit/test_progress_fragments.py`.
