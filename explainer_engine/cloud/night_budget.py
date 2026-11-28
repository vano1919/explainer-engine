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
    """Return the durable night ledger path; in CI fails closed unless EE_DURABLE_LEDGER_PATH is set."""
    durable = os.environ.get("EE_DURABLE_LEDGER_PATH")
    if durable:
        return Path(durable).expanduser()
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return spend_ledger.default_ledger_path()
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
    """Resolve the strictest applicable authorized cumulative Modal cap from config/spend_caps.json."""
    cfg = spend_caps.load()
    caps: list[float] = []
    modal_cfg = cfg.get("modal") or {}
    if isinstance(modal_cfg.get("night_total_usd"), (int, float)) and not isinstance(
        modal_cfg.get("night_total_usd"), bool
    ):
        caps.append(float(modal_cfg["night_total_usd"]))
    ltx_cfg = cfg.get("modal_ltx") or {}
    ep_cap = ltx_cfg.get("per_episode_usd")
    run_cap = ltx_cfg.get("per_run_usd")
    if isinstance(ep_cap, (int, float)) and not isinstance(ep_cap, bool) and ep_cap > 0:
        caps.append(float(ep_cap))
    elif isinstance(run_cap, (int, float)) and not isinstance(run_cap, bool) and run_cap > 0:
        caps.append(float(run_cap))
    if not caps:
        raise NightCapExceeded("No authorized Modal spending cap configured in config/spend_caps.json (zero budget)")
    return min(caps)


def _per_run_modal_cap() -> float | None:
    cfg = spend_caps.load()
    ltx_cfg = cfg.get("modal_ltx") or {}
    run_cap = ltx_cfg.get("per_run_usd")
    if isinstance(run_cap, (int, float)) and not isinstance(run_cap, bool) and run_cap > 0:
        return float(run_cap)
    return None


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
    per_run = _per_run_modal_cap()
    if per_run is not None and float(usd) > per_run + 1e-9:
        raise NightCapExceeded(f"Single modal_ltx launch ${float(usd):.4f} exceeds per_run_usd ${per_run:.2f}")
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
