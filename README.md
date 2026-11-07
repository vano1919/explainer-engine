# explainer-engine

Production pipeline for the Ink Chronicle explainer channel: evidence-grounded research → script → storyboard →
Qwen scene assets → Blender 3D/2.5D production → LTX J2/J4 motion → FFmpeg → QA → review bundle.
Nothing is ever uploaded publicly without the creator's approval.

- Setup (Windows): `.\setup.ps1`, then `.venv\Scripts\python -m pytest -q`.
- Current specifications: `docs/INDEX.md`; implementation history and test evidence: `docs/PROGRESS.md`.
- Working rules for Claude Code: `CLAUDE.md`.
- `CHATGPT.md` and `docs/CHATGPT_WORKFLOW.md` are history (superseded by `CLAUDE.md`); the `.chatgpt/` copy of `.claude/` was deleted (D2, 2026-10-29).
- Current production commands: `python -m explainer_engine.production` and `python -m explainer_engine.production_gate <episode-folder>`. The target `python -m explainer_engine run ...` coordinator is not implemented yet.

- Cloud provider research and Claude execution policy: `.claude/rules/cloud-platforms.md`, `docs/providers/HYPERSTACK_README.md`, `docs/providers/MODAL_README.md`, and `docs/providers/CLOUD_COST_MODEL_2026-11-07.md`.
- Provider integration status: RunPod is the only cloud provider currently wired to the project manager. Hyperstack and Modal are research candidates; do not deploy through their MCP/CLI until a provider adapter and its gates are implemented.
