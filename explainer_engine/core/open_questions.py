"""The creator's open questions as switches (Fable audit 2026-11-13, Q1..Q7): ``config/creator_open_questions.json`` holds
each switch's value, Fable's default until the creator answers. Code reads a switch with ``value("Q1")``; an unknown
value refuses (a typo never silently picks a behaviour)."""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.core.errors import ConfigError

PATH = Path(__file__).resolve().parents[2] / "config" / "creator_open_questions.json"


def load(path: Path | str = PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def value(qid: str, path: Path | str = PATH) -> str:
    q = load(path)["questions"].get(qid)
    if q is None:
        raise ConfigError(f"{qid} is not an open question of config/creator_open_questions.json")
    if q["value"] not in q["choices"]:
        raise ConfigError(f"{qid} ({q['switch']}) = {q['value']!r} is not one of {q['choices']}")
    return q["value"]
