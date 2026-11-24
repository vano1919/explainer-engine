"""Deterministic Claude Opus governance hook helpers enforcing the Python Execution Gateway.

Prevents direct ungoverned paid-provider CLI bypasses and verifies machine-checkable
``production_state/1`` stage completion before allowing stop/handoff claims.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from explainer_engine.core.execution_gateway import ProductionStateMachine

FORBIDDEN_UNGOVERNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("direct_modal_secret_overwrite", re.compile(r"\bmodal\s+secret\s+create\b.*--force", re.I)),
    ("direct_modal_run_bypass", re.compile(r"\bmodal\s+run\b.*modal_(?:ltx|layout)_jobs\.py", re.I)),
    ("gemini_url_key_leak", re.compile(r"generativelanguage\.googleapis\.com[^\s\"']*[?&]key=", re.I)),
    ("destructive_git_reset", re.compile(r"\bgit\s+reset\s+--hard\b", re.I)),
)


def check_shell_command_for_gateway_bypass(command: str) -> list[str]:
    """Return governance violations if a shell command attempts an ungoverned paid or destructive bypass."""
    violations: list[str] = []
    for code, pat in FORBIDDEN_UNGOVERNED_PATTERNS:
        if pat.search(command):
            violations.append(f"GATEWAY-DENY[{code}]: command bypasses governed Python execution gateway")
    return violations


def verify_production_state_gate(state_path: Path, *, required_stages: tuple[str, ...] = ("script", "qa")) -> dict[str, Any]:
    """Verify at stop/handoff time that required stages have verifiable PASS/REVIEW state and intact hashes."""
    if not state_path.is_file():
        return {"ok": False, "errors": [f"Missing production state file: {state_path}"]}
    sm = ProductionStateMachine(state_path)
    errors: list[str] = []
    stages = sm.data.get("stages") or {}
    for st in required_stages:
        rec = stages.get(st)
        if not isinstance(rec, dict):
            errors.append(f"Mandatory stage {st!r} has not been recorded in {state_path.name}")
            continue
        status = str(rec.get("status", "")).upper()
        if status not in ("PASS", "REVIEW"):
            errors.append(f"Mandatory stage {st!r} is {status!r} (must be PASS or REVIEW)")
            continue
        ok, blockers = sm.can_start_stage(st)
        if not ok:
            errors.extend(blockers)
    return {"ok": len(errors) == 0, "errors": errors, "summary": sm.status_summary()}


def check_hook_payload(event: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a Claude Code PreToolUse Bash event payload cleanly."""
    tool_input = event.get("tool_input") or {}
    cmd = str(tool_input.get("command") or "")
    violations = check_shell_command_for_gateway_bypass(cmd)
    if violations:
        return {"decision": "deny", "reason": "; ".join(violations)}
    return {"decision": "allow", "reason": "ok"}


if __name__ == "__main__":
    import sys

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    res = check_hook_payload(payload)
    print(json.dumps(res))
    sys.exit(0 if res["decision"] == "allow" else 2)
