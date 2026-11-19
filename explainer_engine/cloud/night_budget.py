"""The creator's night total (2026-11-19 22:25 UTC): one ledger file holds every paid step of the night, and each step reads it
before it reserves.

The creator approved ``modal.night_total_usd`` (``config/spend_caps.json``, message cmsg_01Hnu5zB86sjUj5GtTgaUkPWV6nm3Y6UKXYD2j2e8WKeiw)
for ALL paid work tonight, combined across runs. The per-run lines (``core/ledger.Run``, the worker's own caps) stay; this file is the
second, outer ceiling: a reservation is refused when the reserved-or-spent total plus the new amount passes the night total, and a
settlement replaces the reservation by the measured cost. stdlib plus ``core/store`` (atomic writes).

    python -m explainer_engine.cloud.night_budget open   <ledger>
    python -m explainer_engine.cloud.night_budget reserve <ledger> <item> <usd> [--why TEXT]
    python -m explainer_engine.cloud.night_budget settle  <ledger> <item> <usd>
    python -m explainer_engine.cloud.night_budget show    <ledger>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SCHEMA = "night_ledger/1"


class NightCapExceeded(Exception):
    pass


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def total_usd() -> float:
    from explainer_engine.core import spend_caps
    v = spend_caps.modal().get("night_total_usd")
    if not (isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0):
        raise NightCapExceeded("no modal.night_total_usd in config/spend_caps.json: the night has no approved total")
    return float(v)


def _load(path) -> dict:
    p = Path(path)
    if not p.is_file():
        raise NightCapExceeded(f"{p} does not exist: open the night ledger first")
    d = json.loads(p.read_text(encoding="utf-8"))
    if d.get("schema") != SCHEMA:
        raise NightCapExceeded(f"{p} is not a {SCHEMA} file")
    return d


def _save(path, d: dict):
    from explainer_engine.core.store import write_json_atomic
    write_json_atomic(Path(path), d)


def committed(d: dict) -> float:
    return round(sum(float(i["usd"]) for i in d["items"].values()), 6)


def open_ledger(path, total: float | None = None) -> dict:
    p = Path(path)
    total = total_usd() if total is None else float(total)
    if p.is_file():
        d = _load(p)
        if abs(d["total_usd"] - total) > 1e-9:
            raise NightCapExceeded(f"{p} was opened with ${d['total_usd']:g}, the budget file says ${total:g}: the total never rises in this file")
        return d
    d = {"schema": SCHEMA, "total_usd": total, "opened": _now(), "items": {}}
    _save(p, d)
    return d


def reserve(path, item: str, usd: float, why: str = "") -> dict:
    """Refused (nothing written) when the committed total plus ``usd`` is above the night total, or the item exists already."""
    d = _load(path)
    if usd <= 0:
        raise NightCapExceeded("a reservation needs a positive amount")
    if item in d["items"]:
        raise NightCapExceeded(f"{item} is in the night ledger already ({d['items'][item]}): a repeat would pay twice")
    left = d["total_usd"] - committed(d)
    if usd > left + 1e-9:
        raise NightCapExceeded(f"{item}: ${usd:g} is more than the ${left:.2f} left of the night's ${d['total_usd']:g}")
    d["items"][item] = {"state": "reserved", "usd": round(usd, 4), "at": _now(), "why": why}
    _save(path, d)
    return d


def settle(path, item: str, usd: float) -> dict:
    """The measured cost replaces the reservation (it may not pass the total either)."""
    d = _load(path)
    it = d["items"].get(item)
    if not it:
        raise NightCapExceeded(f"{item} was never reserved")
    others = committed(d) - float(it["usd"])
    if others + usd > d["total_usd"] + 1e-9:
        raise NightCapExceeded(f"{item}: settling ${usd:g} would pass the night's ${d['total_usd']:g}; stop everything and tell the owner")
    d["items"][item] = dict(it, state="settled", usd=round(usd, 4), reserved_usd=it.get("reserved_usd", it["usd"]), settled_at=_now())
    _save(path, d)
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.cloud.night_budget", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("open", "show"):
        sub.add_parser(name).add_argument("ledger")
    r = sub.add_parser("reserve")
    r.add_argument("ledger"), r.add_argument("item"), r.add_argument("usd", type=float), r.add_argument("--why", default="")
    s = sub.add_parser("settle")
    s.add_argument("ledger"), s.add_argument("item"), s.add_argument("usd", type=float)
    a = ap.parse_args(argv)
    try:
        d = (open_ledger(a.ledger) if a.cmd == "open" else _load(a.ledger) if a.cmd == "show" else
             reserve(a.ledger, a.item, a.usd, a.why) if a.cmd == "reserve" else settle(a.ledger, a.item, a.usd))
    except NightCapExceeded as exc:
        print(f"NIGHT LEDGER REFUSED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(dict(d, committed_usd=committed(d), left_usd=round(d["total_usd"] - committed(d), 4)), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
