"""Strict owner approval verification bound to 64-character SHA-256 operation manifests."""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import ContractError

DEFAULT_APPROVALS_PATH = Path(__file__).resolve().parents[2] / "config" / "owner_approvals.json"
APPROVAL_ID_RE = re.compile(r"^cmsg_[A-Za-z0-9_-]{8,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UTC = datetime.UTC


class ApprovalError(ContractError):
    """Raised when a paid operation lacks a valid, matching, unexpired owner approval."""


def canonical_manifest_sha256(manifest: dict[str, Any]) -> str:
    """Return the deterministic 64-character SHA-256 digest of a canonical operation manifest."""
    if not isinstance(manifest, dict) or not manifest:
        raise ApprovalError("Operation manifest must be a non-empty JSON object")
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_approvals(path: Path | None = None) -> dict[str, Any]:
    p = path or DEFAULT_APPROVALS_PATH
    if not p.is_file():
        raise ApprovalError(f"Owner approval registry not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != "owner_approvals/1":
        raise ApprovalError("Invalid owner_approvals.json schema_version")
    approvals = data.get("approvals")
    if not isinstance(approvals, dict):
        raise ApprovalError("owner_approvals.json 'approvals' must be a JSON object")
    return approvals


def verify_approval(
    approval_id: str | None,
    *,
    provider: str,
    operation_mode: str,
    manifest_sha256: str,
    requested_usd: float,
    registry_path: Path | None = None,
    now_utc: datetime.datetime | None = None,
) -> dict[str, Any]:
    """Fail-closed validation of an explicit owner approval bound to a 64-char manifest SHA-256."""
    if not approval_id or not isinstance(approval_id, str):
        raise ApprovalError("Missing owner approval_id; paid operation refused")
    if not APPROVAL_ID_RE.fullmatch(approval_id):
        raise ApprovalError(f"Invalid approval_id format: {approval_id!r}")
    if not SHA256_RE.fullmatch(manifest_sha256):
        raise ApprovalError("Approval binding requires a full 64-character lowercase SHA-256 manifest hash")
    if isinstance(requested_usd, bool) or not isinstance(requested_usd, (int, float)) or not math.isfinite(requested_usd):
        raise ApprovalError(f"requested_usd must be a finite number, got {requested_usd!r}")
    if requested_usd < 0:
        raise ApprovalError("requested_usd cannot be negative")

    approvals = load_approvals(registry_path)
    rec = approvals.get(approval_id)
    if not isinstance(rec, dict):
        raise ApprovalError(f"Unknown approval_id {approval_id!r}; not present in owner_approvals.json")

    if rec.get("provider") != provider:
        raise ApprovalError(
            f"Approval {approval_id!r} is bound to provider {rec.get('provider')!r}, not {provider!r}"
        )
    if rec.get("operation_mode") != operation_mode:
        raise ApprovalError(
            f"Approval {approval_id!r} is bound to mode {rec.get('operation_mode')!r}, not {operation_mode!r}"
        )

    bound_sha = str(rec.get("manifest_sha256", ""))
    if not SHA256_RE.fullmatch(bound_sha) or bound_sha != manifest_sha256:
        raise ApprovalError(
            f"Approval {approval_id!r} manifest_sha256 does not match the exact operation manifest"
        )

    max_usd = rec.get("max_usd")
    if not isinstance(max_usd, (int, float)) or isinstance(max_usd, bool) or not math.isfinite(max_usd) or max_usd <= 0:
        raise ApprovalError(f"Approval {approval_id!r} has invalid max_usd")
    if requested_usd > float(max_usd) + 1e-9:
        raise ApprovalError(
            f"Requested ${requested_usd:.4f} exceeds approval {approval_id!r} max_usd ${float(max_usd):.4f}"
        )

    exp_raw = rec.get("expires_at")
    if not isinstance(exp_raw, str) or not exp_raw.strip():
        raise ApprovalError(f"Approval {approval_id!r} is missing expires_at")
    try:
        exp = datetime.datetime.fromisoformat(exp_raw)
    except ValueError as exc:
        raise ApprovalError(f"Approval {approval_id!r} has invalid expires_at timestamp") from exc
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=UTC)
    now = now_utc or datetime.datetime.now(UTC)
    if now > exp:
        raise ApprovalError(f"Approval {approval_id!r} expired at {exp.isoformat()}")

    evidence = rec.get("owner_evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ApprovalError(f"Approval {approval_id!r} is missing owner_evidence")

    return dict(rec, approval_id=approval_id)


def compute_approval_hmac(proof: dict[str, Any], *, signing_key: str) -> str:
    """Compute a deterministic HMAC-SHA256 over the canonical security fields of an approval proof."""
    if not signing_key or len(signing_key) < 16:
        raise ApprovalError("signing_key must be at least 16 characters")
    canonical = {
        "approval_id": proof.get("approval_id"),
        "provider": proof.get("provider"),
        "operation_mode": proof.get("operation_mode"),
        "manifest_sha256": proof.get("manifest_sha256"),
        "max_usd": round(float(proof.get("max_usd", 0.0)), 6),
        "expires_at": proof.get("expires_at"),
        "owner_evidence": proof.get("owner_evidence"),
        "operation_id": proof.get("operation_id"),
    }
    msg = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hmac.new(signing_key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def sign_approval_proof(proof: dict[str, Any], *, signing_key: str, operation_id: str) -> dict[str, Any]:
    """Attach a unique operation_id and HMAC-SHA256 signature for remote worker verification."""
    if not operation_id or not isinstance(operation_id, str):
        raise ApprovalError("operation_id must be a non-empty string")
    signed = dict(proof, operation_id=operation_id)
    signed["approval_hmac"] = compute_approval_hmac(signed, signing_key=signing_key)
    return signed


def verify_approval_hmac(proof: dict[str, Any], *, signing_key: str) -> bool:
    """Constant-time verification of an approval proof's HMAC-SHA256 signature."""
    provided = str(proof.get("approval_hmac") or "").strip().lower()
    if not SHA256_RE.fullmatch(provided):
        return False
    expected = compute_approval_hmac(proof, signing_key=signing_key)
    return hmac.compare_digest(provided, expected)


def _connect_replay_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0, isolation_level=None)
    conn.execute("PRAGMA busy_timeout=15000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consumed_operations (
            operation_id TEXT PRIMARY KEY,
            approval_id TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            consumed_at TEXT NOT NULL
        )
        """
    )
    return conn


def is_operation_consumed(operation_id: str, *, db_path: Path) -> bool:
    """Return True if operation_id has already been consumed in the persistent replay ledger."""
    if not operation_id or not isinstance(operation_id, str):
        raise ApprovalError("operation_id must be a non-empty string")
    if not db_path.is_file():
        return False
    conn = _connect_replay_db(db_path)
    try:
        row = conn.execute("SELECT 1 FROM consumed_operations WHERE operation_id = ?", (operation_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def record_consumed_operation(
    operation_id: str,
    *,
    approval_id: str,
    manifest_sha256: str,
    db_path: Path,
) -> None:
    """Atomically record a single-use operation_id; raises ApprovalError on replay."""
    if not operation_id or not isinstance(operation_id, str):
        raise ApprovalError("operation_id must be a non-empty string")
    conn = _connect_replay_db(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO consumed_operations (operation_id, approval_id, manifest_sha256, consumed_at) VALUES (?, ?, ?, ?)",
                (operation_id, approval_id, manifest_sha256, datetime.datetime.now(UTC).isoformat()),
            )
            conn.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            conn.execute("ROLLBACK")
            raise ApprovalError(f"Replay detected: operation_id {operation_id!r} was already consumed") from exc
    finally:
        conn.close()
