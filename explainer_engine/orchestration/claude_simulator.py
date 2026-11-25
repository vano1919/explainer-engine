"""Claude-Simulator Harness: executes production actions through real `.claude/settings.json` governance hooks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class ClaudeSimulator:
    """Runs Bash/Write/Stop steps through the live configured `gateway_hook` commands from `.claude/settings.json`."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.settings_path = self.repo_root / ".claude" / "settings.json"
        self.settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.audit_events: list[dict[str, Any]] = []

    def _run_hook(self, mode: str, payload: dict[str, Any]) -> tuple[int, str, str]:
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(self.repo_root)
        env["PYTHONPATH"] = str(self.repo_root)
        proc = subprocess.run(
            [sys.executable, "-m", "explainer_engine.governance.gateway_hook", mode],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(self.repo_root),
            env=env,
            check=False,
        )
        self.audit_events.append(
            {
                "hook_mode": mode,
                "returncode": proc.returncode,
                "allowed": proc.returncode == 0,
                "stderr": proc.stderr.strip()[:200],
            }
        )
        return proc.returncode, proc.stdout, proc.stderr

    def check_bash(self, command: str) -> bool:
        rc, _, err = self._run_hook("pre-bash-guard", {"tool_name": "Bash", "tool_input": {"command": command}})
        if rc != 0:
            raise PermissionError(f"Claude-Simulator pre-bash-guard blocked command: {err.strip()}")
        return True

    def check_write(self, file_path: Path) -> bool:
        rc, _, err = self._run_hook("pre-write-guard", {"tool_name": "Write", "tool_input": {"file_path": str(file_path)}})
        if rc != 0:
            raise PermissionError(f"Claude-Simulator pre-write-guard blocked write: {err.strip()}")
        return True

    def check_stop(self, production_state_path: Path, required_stages: list[str]) -> bool:
        rc, _, err = self._run_hook(
            "stop-guard",
            {"production_state_path": str(production_state_path), "required_stages": required_stages},
        )
        if rc != 0:
            raise PermissionError(f"Claude-Simulator stop-guard blocked completion: {err.strip()}")
        return True

    def save_audit(self, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(
                {
                    "schema_version": "claude_simulator_audit/1",
                    "settings_loaded": str(self.settings_path),
                    "total_hook_checks": len(self.audit_events),
                    "all_passed": all(e["allowed"] for e in self.audit_events),
                    "events": self.audit_events,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return out_path
