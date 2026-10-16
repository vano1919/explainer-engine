"""The run ledger (docs/ORCHESTRATION.md OR-02..OR-04): caps in code, reservations before paid calls, paid items recorded
as they are made so a stop loses nothing. One JSON file per run (``run.json``), written atomically. stdlib only.

    run = Run.open(path, caps={"gemini_usd": 6.0, "elevenlabs_credits": 25000})
    if run.pending("pictures", ids):                  # ids not yet recorded
        run.reserve("gemini_usd", 0.0504, item="pic_01")   # raises CapReached past 80 % of the cap
        ... paid call, file written ...
        run.done("pictures", "pic_01", file="pic_01.png", cost={"gemini_usd": 0.0504})
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

STOP_FRACTION = 0.8
MAX_FAILURES = 3


class CapReached(RuntimeError):
    """A reservation would pass 80 % of a cap: stop this phase, report, wait for the creator."""


class Run:
    def __init__(self, path: Path, data: dict):
        self.path = Path(path)
        self.data = data

    @classmethod
    def open(cls, path: Path | str, caps: dict[str, float] | None = None, **meta) -> "Run":
        path = Path(path)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if caps:
                for k, v in caps.items():
                    if k in data["caps"] and data["caps"][k] != v:
                        raise ValueError(f"cap {k} is already {data['caps'][k]} in this run; a cap is raised only by editing "
                                         f"run.json after the creator says so")
                    data["caps"].setdefault(k, v)
        else:
            data = {"created": time.strftime("%Y-%m-%dT%H:%M:%S"), "caps": dict(caps or {}), "spent": {}, "reserved": {},
                    "phases": {}, "items": {}, "failures": {}, "meta": meta}
        run = cls(path, data)
        run.save()
        return run

    def save(self) -> None:
        write_json_atomic(self.path, self.data)

    # --- money -------------------------------------------------------------------------------------------------------
    def spent(self, service: str) -> float:
        return round(self.data["spent"].get(service, 0.0), 6)

    def reserve(self, service: str, amount: float, item: str = "") -> None:
        """Record the charge BEFORE the paid call. Refuses past 80 % of the cap, and when the service has no cap."""
        cap = self.data["caps"].get(service)
        if cap is None:
            raise CapReached(f"{service} has no cap in this run; set it before spending")
        if amount < 0:
            raise ValueError("a reservation is not negative")
        if self.spent(service) + amount > cap * STOP_FRACTION + 1e-9:
            raise CapReached(f"{service}: {self.spent(service) + amount:.4f} would pass {int(STOP_FRACTION * 100)} % of the "
                             f"cap {cap}; stop and ask the creator")
        self.data["spent"][service] = self.spent(service) + amount
        self.data["reserved"][item or f"{service}#{len(self.data['reserved'])}"] = {"service": service, "amount": amount}
        self.save()

    def refund(self, service: str, amount: float) -> None:
        """A charge that provably did not happen (the provider refused before generating)."""
        self.data["spent"][service] = max(0.0, self.spent(service) - amount)
        self.save()

    # --- items and phases --------------------------------------------------------------------------------------------
    def done(self, kind: str, item: str, **info) -> None:
        self.data["items"].setdefault(kind, {})[item] = info
        self.save()

    def pending(self, kind: str, ids: list[str]) -> list[str]:
        have = self.data["items"].get(kind, {})
        return [i for i in ids if i not in have]

    def fail(self, key: str, cause: str) -> bool:
        """Count a failure; True while another try is allowed (OR-04: three failures stop the item)."""
        rows = self.data["failures"].setdefault(key, [])
        rows.append({"at": time.strftime("%H:%M:%S"), "cause": cause[:400]})
        self.save()
        return len(rows) < MAX_FAILURES

    def phase(self, name: str, status: str, note: str = "") -> None:
        if status not in ("RUNNING", "PASSED", "FAILED", "STOPPED"):
            raise ValueError(status)
        self.data["phases"][name] = {"status": status, "note": note, "at": time.strftime("%H:%M:%S")}
        self.save()

    def passed(self, name: str) -> bool:
        return self.data["phases"].get(name, {}).get("status") == "PASSED"

    def report(self) -> dict:
        return {"caps": self.data["caps"], "spent": {k: round(v, 4) for k, v in self.data["spent"].items()},
                "phases": {k: v["status"] for k, v in self.data["phases"].items()},
                "items": {k: len(v) for k, v in self.data["items"].items()},
                "failures": {k: len(v) for k, v in self.data["failures"].items()}}
