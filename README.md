# explainer-engine

Episode-first production pipeline (`v4.3`) for historical documentary-drama and What-If videos:
evidence-grounded research → approved script & film direction → flexible visual routes (`map_action`, `still_25d`, `video`) → narration/sound/music → FFmpeg assembly → 3-layer technical, perceptual & editorial QA → creator approval.
Nothing is ever spent or uploaded publicly without the creator's explicit approval.

## Canonical Entrypoints (v4.3)

- **Episode pipeline runner (draft production runner):** `python -m explainer_engine.episode run <episode> --to qa`
- **Episode status:** `python -m explainer_engine.episode status <episode>`
- **Visual routes (duration-measured, flexible per scene):**
  - `map_action` — Python/MapLibre cartography (`explainer_engine/maps/`, `explainer_engine/production/map_clip.py`)
  - `still_25d` — Gemini reference images + deterministic 2.5D layered rendering (`explainer_engine/imagegen/`, `explainer_engine/fx25d/living.py`)
  - `video` — LTX-2.5 on Modal (`MODAL1`) with explicit 64-char SHA-256 owner approval, transactional SQLite ledger reservation, and strict clip ingestion (`explainer_engine/videolane/`, `explainer_engine/training/pods/ltx/modal_ltx_jobs.py`)
- **Blender spatial previs (grey-box only):** `explainer_engine/lab/scene_spec.py` & `explainer_engine/lab/scene_render.py`
- **3-Layer Perceptual QA (deterministic by default; opt-in `--gemini`):**
  `python -m explainer_engine.qa.perceptual_qa --video <clip.mp4> --out-dir <qa_dir>`
- **Local-first Modal preflight (`$0.00` check-only):**
  `python scripts/run_modal_ltx_smoke_and_qa.py --check-only`

## Spending, Approvals & Security Controls

- **Authoritative spend caps:** `config/spend_caps.json` (never raise caps without explicit owner instruction; unverified legacy `orchestration_envelopes` are disabled by default).
- **Owner approvals:** `config/owner_approvals.json` (empty by default; validated fail-closed via `explainer_engine/core/approvals.py` bound to a full 64-char SHA-256 manifest).
- **Transactional spend ledger:** `explainer_engine/core/spend_ledger.py` (SQLite `BEGIN IMMEDIATE` + WAL, 80% stop rule, duplicate refusal, persistent `OVERRUN` service block; CI fails closed unless `EE_DURABLE_LEDGER_PATH` is configured).
- **API key hygiene:** Gemini multimodal QA uses the `x-goog-api-key` header (never `?key=` in URLs) and redacts keys from errors/logs; Modal runners verify pre-provisioned secrets via `modal.Secret.from_name(..., required_keys=["HF_TOKEN"])`.

## Provider Status & Known Gaps

| Area | Status | Notes |
| :--- | :--- | :--- |
| Deterministic technical QA & delivery gate | Active | Tested locally with FFmpeg-generated media (`>= 8` temporal frames, `check_no_melt`, stereo audio) |
| Gemini multimodal perceptual QA | Opt-in (`--gemini`) | Tested offline with fake transport; live API requires `GEMINI_API_KEY` + spend-cap reservation |
| Modal LTX-2.5 (`MODAL1`) | Gated | `--check-only` runs full L0 suite locally (`$0.00`); live GPU smoke/main requires owner approval + durable ledger |
| Gemini interactive image generation | Human gate | Verifies on-disk image decode, dimensions, and SHA-256; unattended chat bridge not implemented |
| Legacy routes (Unreal, Qwen-LoRA, RunPod, Kokoro) | Retired | Preserved only in `config/retired_era.json` / archived records; refused in active workflows |

## Key Documentation & Governance

- Working rules and current production policies: `CLAUDE.md`
- Stage crosswalk (Episode Runner ↔ Skill Registry ↔ Skill Index): `docs/architecture/STAGE_CROSSWALK.md`
- Active prompt inventory & offline evaluation: `docs/architecture/PROMPT_INVENTORY.md`
- Portable cross-agent skills: `.agents/skills/*/SKILL.md` (`python -m explainer_engine.governance.agent_skills_lint`)
- Episode-first v4.3 contract: `docs/EPISODE_FIRST.md`
- Canonical documentation index: `docs/INDEX.md`
- Sourced production rules (`BP-*`): `docs/SOURCED_RULES.md` (`explainer_engine/standards/sourced_rules.json`)
- Retired-era compatibility catalog: `config/retired_era.json`

## Setup & Validation (macOS / Linux / Windows)

Requires **Python 3.11+** and **FFmpeg / FFprobe** on `PATH` (on Apple Silicon macOS, ensure `/opt/homebrew/bin` is on `PATH`).

```bash
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -e ".[dev]"
```

Run validation gates (all `$0.00`, zero paid calls):

```bash
python -m explainer_engine.docs_lint
python -m explainer_engine.governance.agent_skills_lint
ruff check explainer_engine/core/approvals.py explainer_engine/core/spend_ledger.py explainer_engine/core/camera_vocab.py explainer_engine/qa/perceptual_qa.py explainer_engine/qa/prompt_eval.py
basedpyright
python -m pytest -q -m "not system and not media"
```
