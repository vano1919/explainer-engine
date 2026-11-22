"""The creator's money ceilings from ``config/spend_caps.json`` (D-56): one file, read by the run ledger and the pod manager.
A run ledger may hold lower caps than the file, never higher; ``$EXPLAINER_SPEND_CAPS`` points at another file (tests)."""

from __future__ import annotations

import json
import os
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "spend_caps.json"


class OverCeiling(ValueError):
    """A cap or a pod asks for more than the creator's ceiling."""


def load() -> dict:
    p = Path(os.environ.get("EXPLAINER_SPEND_CAPS") or PATH)
    return json.loads(p.read_text(encoding="utf-8"))


def episode_ceiling(service: str) -> float | None:
    return load().get("per_episode", {}).get(service)


def allowance(name: str) -> dict:
    """A tool's own spending allowance (``allowances.<name>``: service, per_run): a ceiling inside the run's cap of that
    service, spent without asking first (the QA loop's re-reads, the creator 2026-10-20). Missing = no allowance."""
    a = load().get("allowances", {}).get(name)
    if not isinstance(a, dict) or "service" not in a or "per_run" not in a:
        raise OverCeiling(f"no allowance {name!r} in config/spend_caps.json: spending needs the creator's yes")
    return a


def paid_test(name: str) -> dict[str, float]:
    """One paid test's caps (``paid_tests.<name>``, the ``*_usd`` lines: service -> ceiling). Refuses a test that is not in the
    file and a section whose tests together pass ``total_usd``."""
    tests = load().get("paid_tests", {})
    t = tests.get(name) if not name.startswith("_") else None
    if not isinstance(t, dict):
        raise OverCeiling(f"no paid test {name!r} in config/spend_caps.json: a paid test needs the creator's yes and its line")
    total = sum(float(v) for row in tests.values() if isinstance(row, dict) for k, v in row.items() if k.endswith("_usd"))
    if total > float(tests.get("total_usd", 0)) + 1e-9:
        raise OverCeiling(f"paid tests add up to {total:g} USD, above their total_usd {tests.get('total_usd')} (config/spend_caps.json)")
    return {k: float(v) for k, v in t.items() if k.endswith("_usd")}


def casting_credits_max() -> float:
    """The ElevenLabs credits one casting session may spend (``casting.casting_credits_max``, the creator 2026-10-30)."""
    v = load().get("casting", {}).get("casting_credits_max")
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no casting_credits_max in config/spend_caps.json: casting spends nothing without the creator's number")
    return float(v)


def gemini_api() -> dict:
    """The Gemini API line (``gemini_api``: max_usd per calendar month). Missing or not a positive number = refused."""
    g = load().get("gemini_api")
    v = g.get("max_usd") if isinstance(g, dict) else None
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
        raise OverCeiling("no gemini_api max_usd in config/spend_caps.json: the Gemini API spends nothing without the creator's line")
    return g


def overnight(name: str) -> dict:
    """One night's ceiling (``overnight.<name>``: max_usd and its lines). A night whose lines together pass its max_usd, or
    a night not in the file, is refused: the lines of every paid service of the night add up to one number (the creator
    2026-11-22: $20 in total)."""
    nights = load().get("overnight", {})
    n = nights.get(name) if not name.startswith("_") else None
    if not isinstance(n, dict) or not isinstance(n.get("max_usd"), (int, float)) or isinstance(n.get("max_usd"), bool):
        raise OverCeiling(f"no overnight {name!r} with a max_usd in config/spend_caps.json: a night spends nothing without its line")
    total = 0.0
    for row in (n.get("lines") or {}).values():
        if isinstance(row, dict):
            total += sum(float(v) for k, v in row.items() if k.endswith("_usd"))
    if total > float(n["max_usd"]) + 1e-9:
        raise OverCeiling(f"overnight {name!r} lines add up to {total:g} USD, above its max_usd {n['max_usd']} (config/spend_caps.json)")
    return n


OVERNIGHT = "overnight_2026_11_23"   # the night the paid runners are counted against (config/spend_caps.json overnight)


def _overnight_dir() -> Path:
    return Path(os.environ.get("EXPLAINER_OVERNIGHT_DIR") or Path(__file__).resolve().parents[2] / "jobs" / "overnight")


def overnight_spent(name: str = OVERNIGHT) -> float:
    """Everything the night has booked so far, in every service: reservations plus their corrections (each row adds a USD
    amount; a reservation with no correction stays booked, the safe side)."""
    f = _overnight_dir() / f"{name}.jsonl"
    if not f.exists():
        return 0.0
    return round(sum(float(json.loads(x)["usd"]) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()), 6)


def _overnight_append(name: str, row: dict) -> None:
    d = _overnight_dir()
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{name}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def overnight_reserve(service: str, uid: str, estimate: float, name: str = OVERNIGHT) -> None:
    """Refuse a paid call unless the night's booked spend plus this call's estimate stays within the night's max_usd
    (the creator 2026-11-22: $20 in total, every service). On success the estimate is booked under uid."""
    n = overnight(name)
    spent = overnight_spent(name)
    if spent + estimate > float(n["max_usd"]) + 1e-9:
        raise OverCeiling(f"{service}: the night has ${spent:.4f} booked and this call estimates ${estimate:.4f}, which would pass "
                          f"its ${float(n['max_usd']):g} ceiling (config/spend_caps.json overnight); stop and ask the creator")
    _overnight_append(name, {"service": service, "uid": uid, "usd": round(estimate, 6), "kind": "reserve"})


def overnight_settle(service: str, uid: str, actual: float, reserved: float, name: str = OVERNIGHT) -> None:
    """Replace uid's reservation by the actual USD: a correction row of actual - reserved (0 when the call was not charged)."""
    _overnight_append(name, {"service": service, "uid": uid, "usd": round(actual - reserved, 6), "kind": "settle"})


def runpod() -> dict:
    return load()["runpod"]


def check_caps(caps: dict) -> dict:
    """Fill a run's missing caps from the file and refuse any cap above it."""
    out = dict(caps)
    for service, ceiling in load().get("per_episode", {}).items():
        if service not in out:
            out[service] = ceiling
        elif out[service] > ceiling + 1e-9:
            raise OverCeiling(f"{service} cap {out[service]} is above the creator's ceiling {ceiling} (config/spend_caps.json)")
    return out
