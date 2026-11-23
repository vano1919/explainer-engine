"""Night spending ledger for Modal GPU launches backed by cross-process SQLite transactions."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from explainer_engine.core import spend_caps, spend_ledger


class NightCapExceeded(spend_caps.OverCeiling):
    """Raised when a Modal launch would exceed the strictest applicable budget ceiling or overrun block."""


def default_night_ledger_path() -> Path:
    """Return the configurable persistent night ledger path (no hard-coded /mnt/project-files default)."""
    env_p = os.environ.get("EE_NIGHT_LEDGER")
    if env_p:
        return Path(env_p).expanduser()
    return Path.home() / ".explainer_engine" / "night_ledger.sqlite3"


def _resolve_sqlite_path(path: str | Path | None) -> Path:
    if path is None:
        return default_night_ledger_path()
    p = Path(path)
    if p.suffix.lower() == ".json":
        return p.with_suffix(".sqlite3")
    return p


def _strictest_modal_cap() -> float:
    """Resolve the strictest applicable authorized Modal cap from config/spend_caps.json."""
    cfg = spend_caps.load()
    caps: list[float] = []
    modal_cfg = cfg.get("modal") or {}
    if isinstance(modal_cfg.get("night_total_usd"), (int, float)) and not isinstance(
        modal_cfg.get("night_total_usd"), bool
    ):
        caps.append(float(modal_cfg["night_total_usd"]))
    ltx_cfg = cfg.get("modal_ltx") or {}
    if isinstance(ltx_cfg.get("per_run_usd"), (int, float)) and not isinstance(
        ltx_cfg.get("per_run_usd"), bool
    ):
        caps.append(float(ltx_cfg["per_run_usd"]))
    if not caps:
        raise NightCapExceeded("No authorized Modal spending cap configured in config/spend_caps.json (zero budget)")
    return min(caps)


def _mirror_json(json_path: Path, row: dict[str, Any]) -> None:
    if json_path.suffix.lower() != ".json":
        return
    json_path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.is_file() else {"items": {}}
    data.setdefault("items", {})[row["item_id"]] = row
    tmp = json_path.with_suffix(f".json.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)


def reserve(path: str | Path | None, item: str, usd: float, why: str = "") -> dict[str, Any]:
    """Atomically reserve ``usd`` for ``item`` under the strictest applicable Modal cap."""
    db_path = _resolve_sqlite_path(path)
    cap_usd = _strictest_modal_cap()
    try:
        row = spend_ledger.reserve(
            "modal_ltx",
            item,
            float(usd),
            cap_usd=cap_usd,
            stop_fraction=0.80,
            why=why,
            ledger_path=db_path,
        )
    except spend_caps.OverCeiling as exc:
        raise NightCapExceeded(str(exc)) from None
    if path is not None and Path(path).suffix.lower() == ".json":
        _mirror_json(Path(path), row)
    return row


def settle(path: str | Path | None, item: str, usd: float) -> dict[str, Any]:
    """Atomically settle ``item`` with actual wall-clock USD; marks OVERRUN loudly if exceeded."""
    db_path = _resolve_sqlite_path(path)
    try:
        row = spend_ledger.settle("modal_ltx", item, float(usd), ledger_path=db_path)
    except spend_caps.OverCeiling as exc:
        raise NightCapExceeded(str(exc)) from None
    if path is not None and Path(path).suffix.lower() == ".json":
        _mirror_json(Path(path), row)
    return row
