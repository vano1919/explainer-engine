# ChatGPT operating files

This directory is the ChatGPT-specific working layer for `explainer-engine`.

- `../CHATGPT.md` is the main entry point and contains the full current `CLAUDE.md` rules plus ChatGPT-specific operating rules.
- `agents/` and `skills/` contain exact blob copies of every file under `.claude/` from source commit `a1821958c4195953e52261bfb42d9b3351d6aa45`.
- `rules/` contains additional ChatGPT rules for repository maintenance and production quality.
- `agents/chatgpt-orchestrator.md` describes the required end-to-end repository workflow.

The copied files are snapshots, not a runtime bridge to Claude. Keep the two assistant instruction trees separate. When Claude's instructions change, compare the source tree and copied tree, record the source commit, and intentionally sync relevant updates. Do not modify `.claude/` just to customize ChatGPT.

Use this branch for ChatGPT-owned changes: `chatgpt/repo-management`. Do not merge this branch or change the default branch unless the creator approves it.
