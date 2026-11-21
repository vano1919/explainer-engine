## 2026-11-21 — DeepSeek worker: Claude plans and checks, DeepSeek writes

- **Done:** the creator's new way of working (2026-11-21, project thread) as a mandatory skill, `.claude/skills/deepseek-worker/SKILL.md`, a pointer
  in `CLAUDE.md`, and the tool `explainer_engine/llm/deepseek_api.py` (`code`: brief + files -> applied, tested edits and `patch.diff`, failures fed
  back without a Claude turn, last round on Pro; `review`; `text`; `spent`; `balance`; `--dry-run`).
- **Facts:** `config/deepseek.json` holds the model names, the list prices and peak hours read on the official pricing page on 2026-11-21, the limits
  and the paths the worker may never edit.
- **State:** nothing paid was run. A real call is refused until `config/spend_caps.json` has a `deepseek_api` line (the creator's word) and the key
  is in the environment. The cost table of the plan is an estimate, not a measurement.
- **Tests:** `tests/unit/test_deepseek_api.py` (11): prices and peak hours, refusal without a cap line, stream saved as it arrives, a broken stream
  keeps the partial answer and charges the estimate, ceiling / job limit / secret refusals, retry on 429, the fix loop with Pro in the last round,
  a failed job leaves the tree untouched, edit safety (never-paths, unsent files, whole-file rewrite, ambiguous search, shrink), review verdict, CLI.
- **Decisions waiting for the creator:** the `deepseek_api` ceiling; whether Gemini stays out of the per-task loop as the skill proposes; project
  instruction 15 (scripts written by the thread's Claude) against his new word that script drafts move to DeepSeek.
- **Next step:** five real backlog tasks under a $5 hard limit, then the measured numbers replace the estimate.
