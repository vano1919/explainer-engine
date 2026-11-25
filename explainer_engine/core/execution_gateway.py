"""Deterministic Python Execution Gateway & Persistent Production State Machine.

Authoritative state machine integrated into ``episode/run.py`` and
``orchestration/skill_orchestrator.py`` so no runner or orchestrator can skip
mandatory stages, proceed on stale/corrupted outputs, recover unsafely after
interruption, or bypass approval/spend controls.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import uuid
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

# Episode runner (episode/run.py) linear dependency graph where post_assembly_spotting is optional/inline
EPISODE_RUNNER_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "script": (),
    "sound_plan": ("script",),
    "pictures": ("sound_plan",),
    "voice": ("pictures",),
    "clips": ("voice",),
    "sound": ("clips",),
    "assemble": ("sound",),
    "post_assembly_spotting": ("assemble",),
    "qa": ("assemble",),
    "delivery": ("qa",),
}

PASSING_STATES = frozenset({"PASS", "REVIEW"})
RECORDABLE_STATES = frozenset({"PASS", "REVIEW", "FAIL", "NOT_RUN"})


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Expected artifact file does not exist on disk: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _downstream_stages(
    stage: str,
    ordered_stages: tuple[str, ...] = ORDERED_STAGES,
    stage_dependencies: dict[str, tuple[str, ...]] = STAGE_DEPENDENCIES,
) -> list[str]:
    if stage not in ordered_stages:
        raise ContractError(f"Unknown production stage: {stage!r}")
    affected: set[str] = set()
    changed = True
    while changed:
        changed = False
        for candidate in ordered_stages:
            if candidate == stage or candidate in affected:
                continue
            deps = stage_dependencies.get(candidate, ())
            if stage in deps or any(d in affected for d in deps):
                affected.add(candidate)
                changed = True
    return [s for s in ordered_stages if s in affected]


class ProductionStateMachine:
    """Persistent, resumable, SHA-256-verified production state machine for an episode."""

    def __init__(
        self,
        state_path: Path,
        *,
        episode_id: str = "unknown",
        ordered_stages: tuple[str, ...] | None = None,
        stage_dependencies: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self.state_path = Path(state_path)
        self.episode_id = episode_id
        self.ordered_stages: tuple[str, ...] = tuple(ordered_stages) if ordered_stages is not None else ORDERED_STAGES
        self.stage_dependencies: dict[str, tuple[str, ...]] = (
            dict(stage_dependencies) if stage_dependencies is not None else dict(STAGE_DEPENDENCIES)
        )
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

    def _validate_stage_name(self, stage: str) -> None:
        if stage not in self.ordered_stages:
            raise ContractError(f"Unknown production stage: {stage!r}")

    def verify_stage_outputs(self, stage: str) -> tuple[bool, list[str]]:
        """Verify a completed stage's own status and on-disk SHA-256 output integrity."""
        self._validate_stage_name(stage)
        stages = self.data.get("stages") or {}
        rec = stages.get(stage)
        if not isinstance(rec, dict):
            return False, [f"Stage {stage!r} has not been recorded"]
        st = str(rec.get("status", "")).upper()
        if st not in PASSING_STATES:
            return False, [f"Stage {stage!r} has non-passing status {st!r}"]
        output_hashes = rec.get("output_hashes") or {}
        if not output_hashes:
            return False, [f"Stage {stage!r} has no recorded verifiable output hashes"]
        errors: list[str] = []
        for out_path, expected_sha in output_hashes.items():
            p = Path(out_path)
            if not p.is_file():
                errors.append(f"Stage {stage!r} output missing on disk: {out_path}")
            elif sha256_file(p) != expected_sha:
                errors.append(f"Stage {stage!r} output corrupted or modified on disk: {out_path}")
        return len(errors) == 0, errors

    def can_start_stage(self, stage: str, *, allow_rehearsal: bool = False) -> tuple[bool, list[str]]:
        self._validate_stage_name(stage)
        blockers: list[str] = []
        stages = self.data.get("stages") or {}
        for dep in self.stage_dependencies.get(stage, ()):
            rec = stages.get(dep)
            if not isinstance(rec, dict):
                blockers.append(f"Prerequisite stage {dep!r} has not been completed")
                continue
            st = str(rec.get("status", "")).upper()
            if st == "RUNNING":
                blockers.append(f"Prerequisite stage {dep!r} is still RUNNING (interrupted/incomplete); rerun it first")
                continue
            if st == "INVALIDATED":
                blockers.append(f"Prerequisite stage {dep!r} was INVALIDATED; rerun it first")
                continue
            if st not in PASSING_STATES and not allow_rehearsal:
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

    def is_stage_fresh(
        self,
        stage: str,
        *,
        input_fingerprints: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> tuple[bool, list[str]]:
        """Check whether a stage is complete, matches current inputs/config, and has intact on-disk outputs."""
        self._validate_stage_name(stage)
        reasons: list[str] = []
        ok_deps, dep_blockers = self.can_start_stage(stage)
        if not ok_deps:
            reasons.extend(dep_blockers)
        ok_out, out_errors = self.verify_stage_outputs(stage)
        if not ok_out:
            reasons.extend(out_errors)
        rec = (self.data.get("stages") or {}).get(stage)
        if isinstance(rec, dict):
            if input_fingerprints is not None and (rec.get("input_fingerprints") or {}) != dict(input_fingerprints):
                reasons.append(f"Stage {stage!r} input fingerprints changed since completion")
            if config is not None and (rec.get("config") or {}) != dict(config):
                reasons.append(f"Stage {stage!r} config changed since completion")
        return len(reasons) == 0, reasons

    def invalidate_stage(self, stage: str, *, reason: str) -> list[str]:
        """Mark ``stage`` and all downstream stages INVALIDATED and persist safely."""
        self._validate_stage_name(stage)
        stages = self.data.setdefault("stages", {})
        invalidated: list[str] = []
        for target in [stage, *_downstream_stages(stage, self.ordered_stages, self.stage_dependencies)]:
            if target in stages:
                stages[target]["status"] = "INVALIDATED"
                stages[target]["invalidated_by"] = stage
                stages[target]["invalidated_reason"] = reason
                invalidated.append(target)
        self.data.setdefault("audit_log", []).append(
            {
                "ts": datetime.datetime.now(UTC).isoformat(),
                "event": "invalidated",
                "stage": stage,
                "reason": reason,
                "invalidated": invalidated,
            }
        )
        self.save()
        return invalidated

    def mark_stage_started(
        self,
        stage: str,
        *,
        input_fingerprints: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        allow_rehearsal: bool = False,
    ) -> dict[str, Any]:
        """Persist RUNNING state before stage execution so crash/interruption is safely detected."""
        self._validate_stage_name(stage)
        ok, blockers = self.can_start_stage(stage, allow_rehearsal=allow_rehearsal)
        if not ok:
            raise ContractError(f"Stage {stage!r} cannot start: {'; '.join(blockers)}")
        prev = (self.data.get("stages") or {}).get(stage)
        started_at = datetime.datetime.now(UTC).isoformat()
        rec: dict[str, Any] = {
            "stage": stage,
            "status": "RUNNING",
            "started_at": started_at,
            "input_fingerprints": dict(input_fingerprints or {}),
            "config": dict(config or {}),
            "output_hashes": dict((prev or {}).get("output_hashes") or {}),
        }
        self.data.setdefault("stages", {})[stage] = rec
        self.data.setdefault("audit_log", []).append(
            {"ts": started_at, "event": "started", "stage": stage, "status": "RUNNING"}
        )
        self.save()
        return rec

    def record_stage_completion(
        self,
        stage: str,
        *,
        status: str,
        output_paths: list[Path | str],
        input_fingerprints: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        provider_or_model: str = "local_python",
        cost_usd: float = 0.0,
        approval_id: str | None = None,
        qa_summary: dict[str, Any] | None = None,
        rehearsal: bool = False,
        allow_rehearsal: bool = False,
    ) -> dict[str, Any]:
        """Verify prerequisites and on-disk outputs, record stage, and invalidate downstream if changed."""
        self._validate_stage_name(stage)
        norm_status = status.upper()
        if norm_status not in RECORDABLE_STATES:
            raise ContractError(f"Invalid stage completion status: {status!r}")

        ok, blockers = self.can_start_stage(stage, allow_rehearsal=allow_rehearsal)
        if not ok:
            raise ContractError(f"Stage {stage!r} cannot be recorded: {'; '.join(blockers)}")

        if norm_status == "PASS" and not output_paths:
            raise ContractError(f"Stage {stage!r} cannot be marked {norm_status} without verifiable on-disk output_paths")

        output_hashes: dict[str, str] = {}
        for raw_p in output_paths:
            p = Path(raw_p)
            output_hashes[p.as_posix()] = sha256_file(p)

        prev = (self.data.get("stages") or {}).get(stage)
        new_inputs = dict(input_fingerprints or {})
        new_cfg = dict(config or {})
        changed = prev is not None and (
            prev.get("output_hashes") != output_hashes
            or prev.get("input_fingerprints") != new_inputs
            or prev.get("config") != new_cfg
        )

        record = {
            "stage": stage,
            "status": norm_status,
            "completed_at": datetime.datetime.now(UTC).isoformat(),
            "input_fingerprints": new_inputs,
            "output_hashes": output_hashes,
            "config": new_cfg,
            "provider_or_model": provider_or_model,
            "cost_usd": round(float(cost_usd), 6),
            "approval_id": approval_id,
            "rehearsal": bool(rehearsal),
            "qa_summary": dict(qa_summary or {}),
        }
        self.data.setdefault("stages", {})[stage] = record

        invalidated: list[str] = []
        if changed or norm_status in ("FAIL", "NOT_RUN"):
            for ds in _downstream_stages(stage, self.ordered_stages, self.stage_dependencies):
                if ds in self.data["stages"]:
                    self.data["stages"][ds]["status"] = "INVALIDATED"
                    self.data["stages"][ds]["invalidated_by"] = stage
                    invalidated.append(ds)

        self.data.setdefault("audit_log", []).append(
            {
                "ts": record["completed_at"],
                "event": "completed",
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
        operation_id = f"op_{uuid.uuid4().hex}"
        hmac_key = (os.environ.get("OWNER_APPROVAL_SIGNING_KEY") or os.environ.get("EE_APPROVAL_HMAC_KEY") or "").strip()
        if hmac_key:
            proof = approvals.sign_approval_proof(proof, signing_key=hmac_key, operation_id=operation_id)
        else:
            proof = dict(proof, operation_id=operation_id)
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
            "stages": {s: (stages.get(s) or {}).get("status", "PENDING") for s in self.ordered_stages},
        }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.core.execution_gateway")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_st = sub.add_parser("status", help="Show persistent production state summary")
    p_st.add_argument("state_path", type=Path)
    p_ck = sub.add_parser("can-start", help="Check whether a stage can start")
    p_ck.add_argument("state_path", type=Path)
    p_ck.add_argument("stage", choices=ORDERED_STAGES)
    p_vf = sub.add_parser("verify", help="Verify a completed stage's own output hashes and prerequisites")
    p_vf.add_argument("state_path", type=Path)
    p_vf.add_argument("stage", choices=ORDERED_STAGES)
    args = ap.parse_args(argv)
    sm = ProductionStateMachine(args.state_path)
    if args.cmd == "status":
        print(json.dumps(sm.status_summary(), indent=2))
        return 0
    if args.cmd == "verify":
        ok_p, p_errs = sm.can_start_stage(args.stage)
        ok_o, o_errs = sm.verify_stage_outputs(args.stage)
        ok = ok_p and ok_o
        print(json.dumps({"stage": args.stage, "verified": ok, "errors": p_errs + o_errs}, indent=2))
        return 0 if ok else 1
    ok, blockers = sm.can_start_stage(args.stage)
    print(json.dumps({"stage": args.stage, "can_start": ok, "blockers": blockers}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
