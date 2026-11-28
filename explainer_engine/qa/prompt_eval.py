"""Offline deterministic prompt evaluator against the Golden Test Dataset."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from explainer_engine.core.camera_vocab import ALLOWED_CAMERA_MOVES

BANNED_ROUTE_TERMS = (
    re.compile(r"\bunreal\s+engine\b", re.I),
    re.compile(r"\bqwen[\s_-]*lora\b", re.I),
    re.compile(r"\bmasterpiece,\s*best quality,\s*8k\b", re.I),
)

BANNED_CAMERA_TERMS = (
    re.compile(r"\b360[\s-]*orbit\b", re.I),
    re.compile(r"\bdutch\s+roll\b", re.I),
)


def evaluate_prompt_case(case: dict[str, Any]) -> dict[str, Any]:
    """Deterministically evaluate a single prompt case (offline, zero API spend)."""
    issues: list[str] = []
    prompt = str(case.get("prompt", "")).strip()
    kind = str(case.get("kind", "ltx_video"))
    camera_move = case.get("camera_move")

    if len(prompt) < 25:
        issues.append("PROMPT_TOO_SHORT")
    for pat in BANNED_ROUTE_TERMS:
        if pat.search(prompt):
            issues.append(f"BANNED_ROUTE_OR_SLOP:{pat.pattern}")
    for pat in BANNED_CAMERA_TERMS:
        if pat.search(prompt):
            issues.append(f"BANNED_CAMERA_TERM:{pat.pattern}")

    if camera_move is not None and camera_move not in ALLOWED_CAMERA_MOVES:
        issues.append(f"INVALID_CAMERA_MOVE:{camera_move}")

    if kind == "ltx_video":
        if case.get("has_spoken_dialogue"):
            if "says in " not in prompt and "speaks in " not in prompt:
                issues.append("MISSING_SPOKEN_VOICE_DIRECTIVE")
        elif "no speech" not in prompt.lower() and "silent" not in prompt.lower() and "no dialogue" not in prompt.lower():
            issues.append("MISSING_NO_SPEECH_CLAUSE")

    passed = len(issues) == 0
    return {
        "case_id": case.get("case_id", "unknown"),
        "expected_pass": bool(case.get("expected_pass", True)),
        "actual_pass": passed,
        "matched_expectation": passed == bool(case.get("expected_pass", True)),
        "issues": issues,
    }


def evaluate_golden_dataset(dataset_path: Path) -> dict[str, Any]:
    """Run offline evaluation over every case in a golden_dataset.json file."""
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = data.get("cases") or []
    results = [evaluate_prompt_case(c) for c in cases]
    all_matched = all(r["matched_expectation"] for r in results) and len(results) > 0
    return {
        "schema_version": data.get("schema_version"),
        "total": len(results),
        "matched": sum(1 for r in results if r["matched_expectation"]),
        "ok": all_matched,
        "results": results,
    }
