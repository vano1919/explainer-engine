"""The creator's money ceilings live only in config/spend_caps.json (D-56, CN-10): no module writes a cap or a pod limit as a
number. A literal under a cap's name is a copy that goes stale when the creator changes the file."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAPS = json.loads((ROOT / "config" / "spend_caps.json").read_text(encoding="utf-8"))
NAMES = set(CAPS["per_episode"]) | {k for k, v in CAPS["runpod"].items() if isinstance(v, (int, float))} | {"per_run"}
ALLOWED = {"explainer_engine/core/spend_caps.py"}


def _numeric(node) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool)


def violations(source: str) -> list[tuple[int, str]]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value in NAMES and _numeric(v):
                    found.append((v.lineno, str(k.value)))
        elif isinstance(node, ast.keyword) and node.arg in NAMES and _numeric(node.value):
            found.append((node.value.lineno, node.arg))
    return found


def test_no_module_copies_a_cap_number():
    bad = []
    for p in sorted((ROOT / "explainer_engine").rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in ALLOWED:
            bad += [f"{rel}:{line} {name}" for line, name in violations(p.read_text(encoding="utf-8"))]
    assert bad == [], "caps are read from config/spend_caps.json (core/spend_caps.py), never written as numbers:\n" + "\n".join(bad)


def test_the_detector_catches_a_copied_cap():
    assert violations('Run.open(p, caps={"bfl_usd": 3.0})') == [(1, "bfl_usd")]
    assert violations("f(runpod_usd=29)") == [(1, "runpod_usd")]
    assert violations('x = {"runpod_usd": spend_caps.runpod()["x"]}') == []
