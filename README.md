# explainer-engine

Episode-first production pipeline (`v4.3`) for historical documentary-drama videos:
evidence-grounded research → approved script & film direction → three visual routes (`map_action`, `still_25d`, `video`) → ElevenLabs narration/sound/music → FFmpeg chunk assembly → technical & multimodal perceptual QA → creator approval.
Nothing is ever uploaded publicly without the creator's explicit approval.

## Canonical Entrypoints (v4.3)

- **Episode pipeline runner (canonical):** `python -m explainer_engine.episode run <episode> --to qa`
- **Episode status:** `python -m explainer_engine.episode status <episode>`
- **Visual routes (duration-measured, flexible per scene):**
  - `map_action` — Python/MapLibre cartography (`explainer_engine/maps/`, `explainer_engine/production/map_clip.py`)
  - `still_25d` — Gemini turn-pack images + deterministic 2.5D layered rendering (`explainer_engine/imagegen/`, `explainer_engine/production/layers25d.py`)
  - `video` — LTX-2.5 on Modal (`MODAL1`) with explicit approval, ledger reservation, and clip ingestion (`explainer_engine/videolane/`, `explainer_engine/training/pods/ltx/modal_ltx_jobs.py`)
- **Blender spatial previs (grey-box only):** `explainer_engine/lab/scene_spec.py` & `explainer_engine/lab/scene_render.py`
- **Perceptual QA (video + audio):** `python -m explainer_engine.qa.perceptual_qa --video <clip.mp4> --out <report.json> --gemini`

## Key Documentation & Governance

- Working rules and current production policies: `CLAUDE.md`
- Episode-first v4.3 contract: `docs/EPISODE_FIRST.md`
- Canonical documentation index: `docs/INDEX.md`
- Sourced production rules (`BP-*`): `docs/SOURCED_RULES.md` (`explainer_engine/standards/sourced_rules.json`)
- Retired-era compatibility catalog (legacy Qwen / Blender J5 / Wan / RunPod preserved for pre-2026-11-12 episodes only): `config/retired_era.json`
- Spend caps & independent budgets: `config/spend_caps.json`
- Implementation history & audit trail: `docs/PROGRESS.md`

## Setup & Validation

- Install dependencies in a Python 3.11+ virtual environment: `pip install -r requirements.txt`
- Run docs lint & unit tests:
  ```bash
  python -m explainer_engine.docs_lint
  python -m pytest -q -m "not system and not media"
  ```
