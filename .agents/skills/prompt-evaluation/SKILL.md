---
name: prompt-evaluation
description: Audit active production prompts and run offline deterministic regression checks against the Golden Test Dataset.
---
# Prompt Evaluation

## Inventory & Dataset
- Prompt inventory: `docs/architecture/PROMPT_INVENTORY.md`
- Golden dataset: `tests/fixtures/prompts/golden_dataset.json`
- Offline evaluator: `explainer_engine.qa.prompt_eval`

## Checks
1. Reject retired routes (`Unreal Engine`, `Qwen-LoRA`) and generic AI-slop boosters (`masterpiece, best quality, 8k`).
2. Enforce canonical camera moves from `explainer_engine.core.camera_vocab`.
3. Verify LTX prompts contain either a spoken voice directive (`says in ...`) or an explicit no-speech clause.
4. Run offline with zero paid API calls: `pytest -q tests/unit/test_workstream_ijk_engineering_skills_prompts.py`.
