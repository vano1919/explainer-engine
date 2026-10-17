# explainer-engine

Production pipeline for an original 2D cartoon explainer channel: evidence-grounded research → script →
storyboard → narration → animation → QA → review bundle. Nothing is ever uploaded without the creator's approval.

- Setup (Windows): `.\setup.ps1`, then `.venv\Scripts\python -m pytest -q`.
- Current specifications: `docs/INDEX.md`; implementation history and test evidence: `docs/PROGRESS.md`.
- Working rules for Claude Code: `CLAUDE.md`.
- Working rules for ChatGPT: `CHATGPT.md` and `.chatgpt/`.
- ChatGPT work branch: `chatgpt/repo-management`; no automatic merge.
- Current production commands: `python -m explainer_engine.production` and `python -m explainer_engine.production_gate <episode-folder>`. The target `python -m explainer_engine run ...` coordinator is not implemented yet.
