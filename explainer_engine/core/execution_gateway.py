"""Deterministic Python Execution Gateway & Persistent Production State Machine.

Prevents Claude Opus or any orchestrator from silently skipping mandatory stages,
bypassing approval/spend controls, or claiming PASS without machine-verifiable
on-disk artifacts and SHA-256 provenance hashes.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from explainer_engine.core import approvals, spend_ledger
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

UTC = datetime.UTC
STATE_SCHEMA = "production_state/1"

ORDERED_STAGES: tuple[str, ...] = (
    "script",
    "sound_plan",
    "pictures",
    "voice",
    "clips",
    "sound",
    "assemble",
    "post_assembly_spotting",
    "qa",
    "delivery",
)

STAGE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "script": (),
    "sound_plan": ("script",),
    "pictures": ("script",),
    "voice": ("script",),
    "clips": ("pictures", "voice"),
    "sound": ("sound_plan", "voice"),
    "assemble": ("clips", "sound"),
    "post_assembly_spotting": ("assemble",),
    "qa": ("assemble", "post_assembly_spotting"),
    "delivery": ("qa",),
}

PASSING_STATES = frozenset({"PASS", "REVIEW"})


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Expected artifact file does not exist on disk: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _downstream_stages(stage: str) -> list[str]:
    if stage not in ORDERED_STAGES:
        raise ContractError(f"Unknown production stage: {stage!r}")
    idx = ORDERED_STAGES.index(stage)
    affected: set[str] = set()
    changed = True
    while changed:
        changed = False
        for candidate in ORDERED_STAGES[idx + 1 :]:
            deps = STAGE_DEPENDENCIES.get(candidate, ())
            if candidate not in affected and (stage in deps or any(d in affected for d in deps)):
                affected.add(candidate)
                changed = True
    return [s for s in ORDERED_STAGES if s in affected]


class ProductionStateMachine:
    """Persistent, resumable, SHA-256-verified production state machine for an episode."""

    def __init__(self, state_path: Path, *, episode_id: str = "unknown") -> None:
        self.state_path = Path(state_path)
        self.episode_id = episode_id
        if self.state_path.is_file():
            self.data: dict[str, Any] = json.loads(self.state_path.read_text(encoding="utf-8"))
        else:
            self.data = {
                "schema_version": STATE_SCHEMA,
                "episode_id": episode_id,
                "created_at": datetime.datetime.now(UTC).isoformat(),
                "updated_at": datetime.datetime.now(UTC).isoformat(),
                "stages": {},
                "audit_log": [],
            }
            self.save()

    def save(self) -> None:
        self.data["updated_at"] = datetime.datetime.now(UTC).isoformat()
        write_json_atomic(self.state_path, self.data)

    def can_start_stage(self, stage: str) -> tuple[bool, list[str]]:
        if stage not in ORDERED_STAGES:
            raise ContractError(f"Unknown production stage: {stage!r}")
        blockers: list[str] = []
        stages = self.data.get("stages") or {}
        for dep in STAGE_DEPENDENCIES.get(stage, ()):
            rec = stages.get(dep)
            if not isinstance(rec, dict):
                blockers.append(f"Prerequisite stage {dep!r} has not been completed")
                continue
            st = str(rec.get("status", "")).upper()
            if st not in PASSING_STATES:
                blockers.append(f"Prerequisite stage {dep!r} has non-passing status {st!r}")
                continue
            # Verify on-disk outputs of prerequisite still match recorded hashes
            for out_path, expected_sha in (rec.get("output_hashes") or {}).items():
                p = Path(out_path)
                if not p.is_file():
                    blockers.append(f"Prerequisite {dep!r} output missing on disk: {out_path}")
                elif sha256_file(p) != expected_sha:
                    blockers.append(f"Prerequisite {dep!r} output modified since completion: {out_path}")
        return len(blockers) == 0, blockers

    def record_stage_completion(
        self,
        stage: str,
        *,
        status: str,
        output_paths: list[Path | str],
        input_fingerprints: dict[str, str] | None = None,
        config: dict[str, Any] | None = None,
        provider_or_model: str = "local_python",
        cost_usd: float = 0.0,
        approval_id: str | None = None,
        qa_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Verify prerequisites and on-disk outputs, record stage, and invalidate downstream if changed."""
        if stage not in ORDERED_STAGES:
            raise ContractError(f"Unknown production stage: {stage!r}")
        norm_status = status.upper()
        if norm_status not in ("PASS", "REVIEW", "FAIL"):
            raise ContractError(f"Invalid stage completion status: {status!r}")

        ok, blockers = self.can_start_stage(stage)
        if not ok:
            raise ContractError(f"Stage {stage!r} cannot be recorded: {'; '.join(blockers)}")

        if norm_status in PASSING_STATES and not output_paths:
            raise ContractError(f"Stage {stage!r} cannot be marked {norm_status} without verifiable on-disk output_paths")

        output_hashes: dict[str, str] = {}
        for raw_p in output_paths:
            p = Path(raw_p)
            output_hashes[str(p)] = sha256_file(p)

        prev = (self.data.get("stages") or {}).get(stage)
        changed_outputs = prev is not None and prev.get("output_hashes") != output_hashes

        record = {
            "stage": stage,
            "status": norm_status,
            "completed_at": datetime.datetime.now(UTC).isoformat(),
            "input_fingerprints": dict(input_fingerprints or {}),
            "output_hashes": output_hashes,
            "config": dict(config or {}),
            "provider_or_model": provider_or_model,
            "cost_usd": round(float(cost_usd), 6),
            "approval_id": approval_id,
            "qa_summary": dict(qa_summary or {}),
        }
        self.data.setdefault("stages", {})[stage] = record

        invalidated: list[str] = []
        if changed_outputs or norm_status == "FAIL":
            for ds in _downstream_stages(stage):
                if ds in self.data["stages"]:
                    self.data["stages"][ds]["status"] = "INVALIDATED"
                    self.data["stages"][ds]["invalidated_by"] = stage
                    invalidated.append(ds)

        self.data.setdefault("audit_log", []).append(
            {
                "ts": record["completed_at"],
                "stage": stage,
                "status": norm_status,
                "cost_usd": record["cost_usd"],
                "invalidated_downstream": invalidated,
            }
        )
        self.save()
        return {"record": record, "invalidated_downstream": invalidated}

    def authorize_paid_action(
        self,
        *,
        approval_id: str | None,
        provider: str,
        operation_mode: str,
        manifest: dict[str, Any],
        estimated_usd: float,
        cap_usd: float,
        item_id: str,
        registry_path: Path | None = None,
        ledger_path: Path | None = None,
    ) -> dict[str, Any]:
        """Centralized fail-closed gateway enforcing owner approval + SQLite spend reservation."""
        manifest_sha = approvals.canonical_manifest_sha256(manifest)
        proof = approvals.verify_approval(
            approval_id,
            provider=provider,
            operation_mode=operation_mode,
            manifest_sha256=manifest_sha,
            requested_usd=estimated_usd,
            registry_path=registry_path,
        )
        reservation = spend_ledger.reserve(
            provider,
            item_id,
            estimated_usd,
            cap_usd=cap_usd,
            why=f"{operation_mode} ({self.episode_id})",
            ledger_path=ledger_path,
        )
        return {"approval_proof": proof, "reservation": reservation, "manifest_sha256": manifest_sha}

    def status_summary(self) -> dict[str, Any]:
        stages = self.data.get("stages") or {}
        return {
            "episode_id": self.data.get("episode_id"),
            "schema_version": self.data.get("schema_version"),
            "stages": {s: (stages.get(s) or {}).get("status", "PENDING") for s in ORDERED_STAGES},
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.core.execution_gateway")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_st = sub.add_parser("status", help="Show persistent production state summary")
    p_st.add_argument("state_path", type=Path)
    p_ck = sub.add_parser("can-start", help="Check whether a stage can start")
    p_ck.add_argument("state_path", type=Path)
    p_ck.add_argument("stage", choices=ORDERED_STAGES)
    args = ap.parse_args(argv)
    sm = ProductionStateMachine(args.state_path)
    if args.cmd == "status":
        print(json.dumps(sm.status_summary(), indent=2))
        return 0
    ok, blockers = sm.can_start_stage(args.stage)
    print(json.dumps({"stage": args.stage, "can_start": ok, "blockers": blockers}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
