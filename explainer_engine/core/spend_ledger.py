"""Authoritative cross-process transactional spending ledger backed by SQLite.

Provides process-safe serialization (`BEGIN IMMEDIATE`), duplicate reservation prevention,
80% stop-rule enforcement, persistent OVERRUN blocking, and CI durable-storage checks
without relying on platform-specific POSIX-only fcntl locks.
"""
from __future__ import annotations

import contextlib
import datetime
import os
import sqlite3
from pathlib import Path
from typing import Any

from explainer_engine.core.spend_caps import OverCeiling

UTC = datetime.UTC
DEFAULT_STOP_FRACTION = 0.80


class LedgerPersistenceError(OverCeiling):
    """Raised when the spending ledger cannot be opened or persisted safely."""


class DuplicateReservationError(OverCeiling):
    """Raised when attempting to reserve an already-booked item_id."""


class ServiceOverrunBlockedError(OverCeiling):
    """Raised when a service is blocked due to a prior unreconciled spend overrun."""


def default_ledger_path() -> Path:
    """Resolve the persistent spending ledger path, failing closed in CI if durable storage is unset."""
    env_durable = os.environ.get("EE_DURABLE_LEDGER_PATH")
    if env_durable:
        return Path(env_durable).expanduser()
    if os.environ.get("CI", "").lower() in ("1", "true", "yes"):
        raise LedgerPersistenceError(
            "CI paid execution requires EE_DURABLE_LEDGER_PATH pointing to durable persistent storage"
        )
    env_local = os.environ.get("EE_SPEND_LEDGER")
    if env_local:
        return Path(env_local).expanduser()
    return Path.home() / ".explainer_engine" / "spend_ledger.sqlite3"


def _connect(path: Path) -> sqlite3.Connection:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=15000")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                item_id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                reserved_usd REAL NOT NULL,
                actual_usd REAL NOT NULL DEFAULT 0.0,
                cap_usd REAL NOT NULL,
                state TEXT NOT NULL,
                why TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                settled_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_blocks (
                service TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                blocked_at TEXT NOT NULL
            )
            """
        )
        return conn
    except (OSError, sqlite3.Error) as exc:
        raise LedgerPersistenceError(f"Cannot initialize spending ledger at {path}: {exc}") from exc


def _now_iso() -> str:
    return datetime.datetime.now(UTC).isoformat()


def reserve(
    service: str,
    item_id: str,
    estimate_usd: float,
    *,
    cap_usd: float,
    stop_fraction: float = DEFAULT_STOP_FRACTION,
    why: str = "",
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Atomically reserve ``estimate_usd`` for ``item_id`` under ``cap_usd * stop_fraction``."""
    if not service or not item_id:
        raise OverCeiling("service and item_id must be non-empty")
    if estimate_usd < 0 or cap_usd <= 0:
        raise OverCeiling(f"Invalid spending parameters: estimate={estimate_usd}, cap={cap_usd}")
    if not (0 < stop_fraction <= 1.0):
        raise OverCeiling(f"Invalid stop_fraction: {stop_fraction}")

    path = ledger_path or default_ledger_path()
    conn = _connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        blocked = conn.execute(
            "SELECT reason FROM service_blocks WHERE service = ?", (service,)
        ).fetchone()
        if blocked is not None:
            conn.execute("ROLLBACK")
            raise ServiceOverrunBlockedError(
                f"Service {service!r} is blocked pending reconciliation: {blocked['reason']}"
            )

        existing = conn.execute(
            "SELECT state FROM reservations WHERE item_id = ?", (item_id,)
        ).fetchone()
        if existing is not None:
            conn.execute("ROLLBACK")
            raise DuplicateReservationError(
                f"Reservation {item_id!r} already exists with state={existing['state']!r}"
            )

        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN state IN ('SETTLED', 'OVERRUN') THEN actual_usd ELSE 0.0 END), 0.0) AS spent,
                COALESCE(SUM(CASE WHEN state = 'RESERVED' THEN reserved_usd ELSE 0.0 END), 0.0) AS reserved
            FROM reservations
            WHERE service = ?
            """,
            (service,),
        ).fetchone()
        spent = float(row["spent"])
        reserved = float(row["reserved"])
        effective_ceiling = round(float(cap_usd) * float(stop_fraction), 6)
        if spent + reserved + float(estimate_usd) > effective_ceiling + 1e-9:
            conn.execute("ROLLBACK")
            raise OverCeiling(
                f"{service}: spent ${spent:.4f} + reserved ${reserved:.4f} + request ${estimate_usd:.4f} "
                f"exceeds effective ceiling ${effective_ceiling:.4f} "
                f"({int(stop_fraction * 100)}% of ${cap_usd:.2f})"
            )

        now = _now_iso()
        est = round(float(estimate_usd), 6)
        conn.execute(
            """
            INSERT INTO reservations (item_id, service, reserved_usd, actual_usd, cap_usd, state, why, created_at)
            VALUES (?, ?, ?, 0.0, ?, 'RESERVED', ?, ?)
            """,
            (item_id, service, est, round(float(cap_usd), 6), why, now),
        )
        conn.execute("COMMIT")
        return {
            "item_id": item_id,
            "service": service,
            "reserved_usd": est,
            "actual_usd": 0.0,
            "cap_usd": round(float(cap_usd), 6),
            "state": "RESERVED",
            "why": why,
            "created_at": now,
        }
    except OverCeiling:
        raise
    except sqlite3.Error as exc:
        with contextlib.suppress(sqlite3.Error):
            conn.execute("ROLLBACK")
        raise LedgerPersistenceError(f"Ledger reservation failed for {service}/{item_id}: {exc}") from exc
    finally:
        conn.close()


def settle(
    service: str,
    item_id: str,
    actual_usd: float,
    *,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Atomically settle ``item_id``. Persists actual spend and blocks service on OVERRUN."""
    if actual_usd < 0:
        raise OverCeiling("actual_usd cannot be negative")
    path = ledger_path or default_ledger_path()
    conn = _connect(path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        rec = conn.execute(
            "SELECT reserved_usd, cap_usd, state FROM reservations WHERE item_id = ? AND service = ?",
            (item_id, service),
        ).fetchone()
        if rec is None or rec["state"] != "RESERVED":
            conn.execute("ROLLBACK")
            raise OverCeiling(f"No open RESERVED entry for {service}/{item_id}")

        actual = round(float(actual_usd), 6)
        reserved = float(rec["reserved_usd"])
        cap = float(rec["cap_usd"])
        other_spent = float(
            conn.execute(
                """
                SELECT COALESCE(SUM(actual_usd), 0.0) AS s
                FROM reservations
                WHERE service = ? AND state IN ('SETTLED', 'OVERRUN') AND item_id != ?
                """,
                (service, item_id),
            ).fetchone()["s"]
        )
        is_overrun = (actual > reserved + 1e-9) or (other_spent + actual > cap + 1e-9)
        new_state = "OVERRUN" if is_overrun else "SETTLED"
        now = _now_iso()
        conn.execute(
            "UPDATE reservations SET actual_usd = ?, state = ?, settled_at = ? WHERE item_id = ?",
            (actual, new_state, now, item_id),
        )
        if is_overrun:
            reason = (
                f"item {item_id!r} actual ${actual:.4f} exceeded reservation ${reserved:.4f} "
                f"or cap ${cap:.4f} (cumulative ${other_spent + actual:.4f})"
            )
            conn.execute(
                "INSERT OR REPLACE INTO service_blocks (service, reason, blocked_at) VALUES (?, ?, ?)",
                (service, reason, now),
            )
        conn.execute("COMMIT")
        return {
            "item_id": item_id,
            "service": service,
            "reserved_usd": reserved,
            "actual_usd": actual,
            "cap_usd": cap,
            "state": new_state,
            "settled_at": now,
        }
    except OverCeiling:
        raise
    except sqlite3.Error as exc:
        with contextlib.suppress(sqlite3.Error):
            conn.execute("ROLLBACK")
        raise LedgerPersistenceError(f"Ledger settlement failed for {service}/{item_id}: {exc}") from exc
    finally:
        conn.close()


def service_status(service: str, *, ledger_path: Path | None = None) -> dict[str, Any]:
    """Inspect current spent, reserved, and overrun-block state for a service."""
    path = ledger_path or default_ledger_path()
    conn = _connect(path)
    try:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN state IN ('SETTLED', 'OVERRUN') THEN actual_usd ELSE 0.0 END), 0.0) AS spent,
                COALESCE(SUM(CASE WHEN state = 'RESERVED' THEN reserved_usd ELSE 0.0 END), 0.0) AS reserved,
                COALESCE(SUM(CASE WHEN state = 'OVERRUN' THEN 1 ELSE 0 END), 0) AS overruns
            FROM reservations
            WHERE service = ?
            """,
            (service,),
        ).fetchone()
        blocked = conn.execute(
            "SELECT reason, blocked_at FROM service_blocks WHERE service = ?", (service,)
        ).fetchone()
        return {
            "service": service,
            "spent_usd": round(float(row["spent"]), 6),
            "reserved_usd": round(float(row["reserved"]), 6),
            "overrun_count": int(row["overruns"]),
            "blocked": blocked is not None,
            "block_reason": blocked["reason"] if blocked is not None else None,
        }
    finally:
        conn.close()
