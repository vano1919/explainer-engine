"""The one home of the LoRA dataset rules (docs/LORA_TRAINING.md LT-01): ``training/lora_rules.json``. stdlib only, so
``scripting/`` and ``qa/`` import it cheaply.

``trigger()`` is the style trigger every caption and every style-LoRA prompt starts with (D-80: Qwen-Image-2.1 + the xworld
LoRA; the same word ``training/pods/xworld_v2_data.TRIGGER`` captioned the dataset with). It is read by
``training/audit.py``, ``qa/style_prompt.py`` (so ``compose/episode_look.py``), ``scripting/film_shots.py`` and the
examples that build film_shots cards."""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).with_name("lora_rules.json")


def load() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def trigger() -> str:
    return load()["dataset"]["trigger"]
