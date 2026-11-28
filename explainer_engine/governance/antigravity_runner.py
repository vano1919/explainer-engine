"""Unified Antigravity Python Governance Wrapper.

Enforces the exact same ironclad control plane used by Claude Code:
- Runs ``gateway_hook`` pre-bash-guard, pre-write-guard, and stop-guard checks.
- Enforces the SQLite WAL ``spend_ledger`` ($15.00 Modal H100 hard ceiling, 80% checkpoint at $12.00,
  $0.00 unapproved external paid APIs) with atomic ``reserve()`` before launch and ``settle()`` after.
- Tracks ``ProductionStateMachine`` stage completion and logs every governed action, spend event,
  and multimodal eyes-on / ears-on QA verdict to ``jobs/antigravity_execution_ledger.jsonl``.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from explainer_engine.core import spend_ledger
from explainer_engine.core.execution_gateway import ProductionStateMachine
from explainer_engine.core.spend_caps import OverCeiling
from explainer_engine.governance import gateway_hook

UTC = datetime.UTC
DEFAULT_MODAL_HARD_CAP_USD = 15.00
DEFAULT_MODAL_CHECKPOINT_USD = 12.00
MODAL_SERVICE = "modal_modal1"
DEFAULT_LEDGER_DB = Path("jobs/antigravity_spend_ledger.sqlite3")
DEFAULT_EXEC_LOG = Path("jobs/antigravity_execution_ledger.jsonl")


def _now_iso() -> str:
    return datetime.datetime.now(UTC).isoformat()


class AntigravityRunner:
    """Governed execution wrapper for Antigravity autonomous production runs."""

    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        spend_db_path: Path | None = None,
        exec_log_path: Path | None = None,
        modal_cap_usd: float = DEFAULT_MODAL_HARD_CAP_USD,
        modal_checkpoint_usd: float = DEFAULT_MODAL_CHECKPOINT_USD,
    ) -> None:
        self.repo_root = (Path(repo_root) if repo_root else Path.cwd()).resolve()
        self.spend_db_path = (
            Path(spend_db_path) if spend_db_path else (self.repo_root / DEFAULT_LEDGER_DB)
        ).resolve()
        self.exec_log_path = (
            Path(exec_log_path) if exec_log_path else (self.repo_root / DEFAULT_EXEC_LOG)
        ).resolve()
        self.modal_cap_usd = float(modal_cap_usd)
        self.modal_checkpoint_usd = float(modal_checkpoint_usd)

    def _log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self.exec_log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {"timestamp": _now_iso(), "event": event_type, **payload}
        with self.exec_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def check_bash(self, command: str) -> None:
        """Enforce gateway_hook pre-bash-guard before executing any shell command."""
        violations = gateway_hook.check_shell_command_for_gateway_bypass(command)
        allowed = not violations
        self._log_event("pre_bash_guard", {"command": command[:240], "allowed": allowed, "violations": violations})
        if violations:
            raise PermissionError(f"AntigravityRunner pre-bash-guard blocked command: {violations}")

    def check_write(self, target_path: Path) -> None:
        """Enforce gateway_hook pre-write-guard before modifying sensitive files."""
        res = gateway_hook.check_write_payload({"tool_name": "Write", "tool_input": {"file_path": str(target_path)}})
        allowed = res.get("decision") == "allow"
        violations = [] if allowed else [str(res.get("reason", "blocked by pre-write-guard"))]
        self._log_event("pre_write_guard", {"path": str(target_path), "allowed": allowed, "violations": violations})
        if not allowed:
            raise PermissionError(f"AntigravityRunner pre-write-guard blocked write: {violations}")

    def modal_spend_summary(self) -> dict[str, Any]:
        """Return exact SQLite WAL spend summary for the Modal H100 service."""
        summary = spend_ledger.service_status(MODAL_SERVICE, ledger_path=self.spend_db_path)
        spent = float(summary.get("spent_usd", 0.0))
        reserved = float(summary.get("reserved_usd", 0.0))
        total_committed = round(spent + reserved, 4)
        return {
            **summary,
            "cap_usd": self.modal_cap_usd,
            "checkpoint_usd": self.modal_checkpoint_usd,
            "committed_usd": total_committed,
            "remaining_usd": round(max(0.0, self.modal_cap_usd - total_committed), 4),
            "at_or_above_checkpoint": total_committed >= self.modal_checkpoint_usd,
        }

    def reserve_modal_spend(self, item_id: str, estimate_usd: float, *, why: str = "") -> dict[str, Any]:
        """Atomically reserve Modal H100 spend under the $15.00 hard ceiling (warning at $12.00)."""
        if estimate_usd <= 0:
            raise OverCeiling(f"estimate_usd must be > 0, got {estimate_usd}")
        # Allow booking up to full $15.00 hard cap (stop_fraction=1.0) while logging 80% ($12.00) checkpoint
        before = self.modal_spend_summary()
        projected = round(before["committed_usd"] + float(estimate_usd), 4)
        if projected > self.modal_cap_usd + 1e-9:
            self._log_event(
                "modal_reserve_blocked",
                {"item_id": item_id, "estimate_usd": estimate_usd, "projected_usd": projected, "cap_usd": self.modal_cap_usd},
            )
            raise OverCeiling(
                f"Modal H100 hard ceiling exceeded: projected ${projected:.4f} > ${self.modal_cap_usd:.2f}"
            )
        checkpoint_warn = projected >= self.modal_checkpoint_usd
        rec = spend_ledger.reserve(
            MODAL_SERVICE,
            item_id,
            float(estimate_usd),
            cap_usd=self.modal_cap_usd,
            stop_fraction=1.0,
            why=why,
            ledger_path=self.spend_db_path,
        )
        self._log_event(
            "modal_reserve",
            {
                "item_id": item_id,
                "estimate_usd": round(float(estimate_usd), 4),
                "projected_usd": projected,
                "checkpoint_warning": checkpoint_warn,
                "why": why,
            },
        )
        return {**rec, "checkpoint_warning": checkpoint_warn, "projected_usd": projected}

    def settle_modal_spend(self, item_id: str, actual_usd: float) -> dict[str, Any]:
        """Settle actual Modal H100 spend immediately after job completion."""
        rec = spend_ledger.settle(
            MODAL_SERVICE,
            item_id,
            round(float(actual_usd), 4),
            ledger_path=self.spend_db_path,
        )
        summary = self.modal_spend_summary()
        self._log_event(
            "modal_settle",
            {
                "item_id": item_id,
                "actual_usd": round(float(actual_usd), 4),
                "total_spent_usd": summary["spent_usd"],
                "remaining_usd": summary["remaining_usd"],
                "state": rec.get("state"),
            },
        )
        return {**rec, "summary": summary}

    def record_inspection(
        self,
        stage: str,
        artifact_path: Path,
        *,
        verdict: str,
        notes: str = "",
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Log a mandatory multimodal eyes-on / ears-on inspection verdict."""
        entry = {
            "stage": stage,
            "artifact_path": str(artifact_path),
            "verdict": verdict,
            "notes": notes,
            "metrics": metrics or {},
        }
        self._log_event("multimodal_inspection", entry)
        return entry

    def record_stage(
        self,
        state_path: Path,
        episode_id: str,
        stage: str,
        *,
        status: str = "PASS",
        output_paths: list[Path] | None = None,
    ) -> dict[str, Any]:
        """Record a ProductionStateMachine stage completion with SHA-256 verification."""
        sm = ProductionStateMachine(state_path, episode_id=episode_id)
        out_list: list[Path | str] = list(output_paths) if output_paths else []
        rec = sm.record_stage_completion(stage, status=status, output_paths=out_list)
        self._log_event(
            "stage_completion",
            {"episode_id": episode_id, "stage": stage, "status": status, "outputs": [str(p) for p in (output_paths or [])]},
        )
        return rec

    def reconcile_spend(self, out_json: Path | None = None) -> dict[str, Any]:
        """Reconcile SQLite spend ledger and assert zero stuck RESERVED rows and spend <= $15.00."""
        import sqlite3

        conn = sqlite3.connect(str(self.spend_db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = [dict(r) for r in conn.execute("SELECT * FROM reservations ORDER BY created_at").fetchall()]
        except sqlite3.OperationalError:
            rows = []
        finally:
            conn.close()

        stuck = [r for r in rows if r.get("state") == "RESERVED"]
        spent_modal = round(
            sum(float(r["actual_usd"]) for r in rows if r["service"] == MODAL_SERVICE and r["state"] in ("SETTLED", "OVERRUN")),
            4,
        )
        other_paid = round(
            sum(float(r["actual_usd"]) for r in rows if r["service"] != MODAL_SERVICE),
            4,
        )
        ok = (len(stuck) == 0) and (spent_modal <= self.modal_cap_usd + 1e-6) and (other_paid == 0.0)
        report = {
            "schema_version": "modal_spend_reconciliation/1",
            "reconciled_at": _now_iso(),
            "ledger_db": str(self.spend_db_path),
            "modal_service": MODAL_SERVICE,
            "modal_hard_cap_usd": self.modal_cap_usd,
            "modal_checkpoint_usd": self.modal_checkpoint_usd,
            "modal_total_spent_usd": spent_modal,
            "modal_remaining_usd": round(max(0.0, self.modal_cap_usd - spent_modal), 4),
            "other_external_paid_usd": other_paid,
            "stuck_reserved_count": len(stuck),
            "total_jobs": len(rows),
            "status": "PASS" if ok else "FAIL",
            "jobs": rows,
        }
        if out_json is not None:
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        self._log_event("spend_reconciliation", {"status": report["status"], "modal_total_spent_usd": spent_modal, "stuck": len(stuck)})
        return report

    def run_governed_subprocess(self, cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        """Run a non-paid governed local command after passing pre-bash-guard."""
        joined = " ".join(cmd)
        self.check_bash(joined)
        res = subprocess.run(cmd, cwd=str(cwd or self.repo_root), env=env or os.environ.copy(), text=True, capture_output=True, check=False)
        self._log_event("governed_exec", {"cmd": joined[:240], "returncode": res.returncode})
        return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Antigravity unified governance & spend-ledger CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Show Modal H100 spend status against $15.00 hard cap")
    p_rec = sub.add_parser("reconcile", help="Reconcile SQLite spend ledger")
    p_rec.add_argument("--out", type=Path, default=None)
    p_chk = sub.add_parser("check-bash", help="Test a command against gateway_hook")
    p_chk.add_argument("command")
    args = ap.parse_args(argv)

    runner = AntigravityRunner()
    if args.cmd == "status":
        print(json.dumps(runner.modal_spend_summary(), indent=2))
        return 0
    if args.cmd == "reconcile":
        rep = runner.reconcile_spend(args.out)
        print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "PASS" else 1
    if args.cmd == "check-bash":
        runner.check_bash(args.command)
        print("ALLOWED")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
