# Prompt Inventory

Canonical inventory of active system/production prompts in `explainer-engine`, their owning modules, and their verification mechanisms.

| Prompt ID | Module / Location | Purpose | Model / Consumer | Verification |
| :--- | :--- | :--- | :--- | :--- |
| `PERCEPTUAL_QA_V2` | `explainer_engine/qa/perceptual_qa.py` (`MULTIMODAL_QA_PROMPT`) | 3-layer visual/audio/editorial perceptual QA (explicit melt/warp, freeze, synthetic audio, sync checks) | Gemini multimodal (`gemini-2.5-flash`, opt-in via `--gemini`) | Strict JSON boolean/enum schema validator (`validate_multimodal_response`) + unit tests with fake transport |
| `LTX_MOTION_PROMPT` | `explainer_engine/videolane/storyboard.py` & `explainer_engine/qa/ltx_prompt_lint.py` | Shot-level LTX-2.5 motion + spoken voice directive or explicit no-speech clause | Modal LTX-2.5 worker (`MODAL1`) | `ltx_prompt_lint`, `test_videolane.py`, and `prompt_eval.py` Golden Dataset |
| `LIVING_DIRECTOR_SPEC` | `explainer_engine/production/living_director.py` | 2.5D/still camera & atmospheric motion direction | Local FFmpeg / 2.5D pipeline | `camera_vocab.py` + `delivery_gate.py` |
| `MAPLIBRE_CARTOGRAPHY` | `explainer_engine/maps/maplibre_spec.py` | Label-free regional relief & front-line vector map shots | MapLibre / Playwright renderer | `maplibre_spec.py` schema + `camera_vocab.py` |
| `GOLDEN_PROMPT_SUITE` | `tests/fixtures/prompts/golden_dataset.json` | Offline regression benchmark for positive & rejected prompt patterns | `explainer_engine/qa/prompt_eval.py` | Deterministic offline pytest (`test_workstream_ijk_engineering_skills_prompts.py`) |

## Retired / Prohibited Prompt Routes

Prompts targeting `Unreal Engine`, `Qwen-LoRA`, or generic AI-slop quality boosters (`masterpiece, best quality, 8k`) are rejected by `explainer_engine/qa/prompt_eval.py` and `config/skill_registry.json` (`retired_skills`).
