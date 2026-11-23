"""File-locked night spending ledger for Modal GPU launches (and independent MODAL1 envelope enforcement)."""
from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

from explainer_engine.core import spend_caps

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]


class NightCapExceeded(spend_caps.OverCeiling):
    """Raised when a Modal launch would exceed the configured night total or independent envelope."""


@contextlib.contextmanager
def _lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lp = path.with_suffix(path.suffix + ".lock")
    with lp.open("a+", encoding="utf-8") as f:
        if fcntl is not None:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path) -> dict:
    if not path.is_file():
        return {"items": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"items": {}}
    data.setdefault("items", {})
    return data


def _booked_usd(data: dict) -> float:
    total = 0.0
    for row in (data.get("items") or {}).values():
        if not isinstance(row, dict):
            continue
        if row.get("state") == "SETTLED":
            total += float(row.get("actual_usd", 0.0))
        else:
            total += float(row.get("reserved_usd", 0.0))
    return round(total, 6)


def reserve(path: str | Path, item: str, usd: float, why: str = "") -> dict:
    """Reserve ``usd`` for ``item`` against both modal.night_total_usd (if set) and MODAL1 envelope."""
    p = Path(path)
    amount = round(max(0.0, float(usd)), 6)
    cfg = spend_caps.load()
    night_cap = (cfg.get("modal") or {}).get("night_total_usd")

    # Enforce independent MODAL1 orchestration envelope when configured
    env_services = (cfg.get("orchestration_envelopes") or {}).get("services") or {}
    if "modal_modal1" in env_services:
        try:
            spend_caps.envelope_reserve("modal_modal1", item, amount)
        except spend_caps.OverCeiling as exc:
            raise NightCapExceeded(str(exc)) from None

    with _lock(p):
        data = _load(p)
        if item in data["items"]:
            raise NightCapExceeded(f"item {item!r} is already booked in {p}")
        booked = _booked_usd(data)
        if isinstance(night_cap, (int, float)) and not isinstance(night_cap, bool):
            if booked + amount > float(night_cap) + 1e-9:
                raise NightCapExceeded(
                    f"booked ${booked:.4f} + request ${amount:.4f} exceeds modal.night_total_usd ${float(night_cap):.2f}"
                )
        row = {
            "item": item,
            "reserved_usd": amount,
            "actual_usd": 0.0,
            "state": "RESERVED",
            "why": why,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data["items"][item] = row
        _atomic_write(p, data)
        return row


def settle(path: str | Path, item: str, usd: float) -> dict:
    """Settle ``item`` with actual wall-clock ``usd`` in both the night ledger and MODAL1 envelope."""
    p = Path(path)
    actual = round(max(0.0, float(usd)), 6)
    cfg = spend_caps.load()
    env_services = (cfg.get("orchestration_envelopes") or {}).get("services") or {}
    if "modal_modal1" in env_services:
        try:
            spend_caps.envelope_settle("modal_modal1", item, actual)
        except spend_caps.OverCeiling:
            pass

    with _lock(p):
        data = _load(p)
        row = data["items"].get(item)
        if not isinstance(row, dict):
            raise NightCapExceeded(f"no reservation for {item!r} in {p}")
        row["actual_usd"] = actual
        row["state"] = "SETTLED"
        row["settled_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _atomic_write(p, data)
        return row
