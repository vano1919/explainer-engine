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
import threading
import time
from pathlib import Path

from explainer_engine.core import spend_caps
from explainer_engine.core.spend_caps import check_caps
from explainer_engine.core.store import write_json_atomic

STOP_FRACTION = 0.8
MAX_FAILURES = 3


class CapReached(RuntimeError):
    """A reservation would pass 80 % of a cap: stop this phase, report, wait for the creator."""


class AllowanceReached(CapReached):
    """A reservation under a tool's allowance (config/spend_caps.json ``allowances``) would pass it: the tool stops and asks."""


class LedgerConflict(RuntimeError):
    """``run.json`` changed on disk since this process read or wrote it: another process uses the same run. Writing now
    would erase its reservations, so this process stops (audit 2026-10-19 H3)."""


class Run:
    def __init__(self, path: Path, data: dict):
        self.path = Path(path)
        self.data = data
        self.lock = threading.RLock()  # paint workers share one ledger
        self._seen = self._stamp()

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
        data["caps"] = check_caps(data["caps"])  # the creator's ceilings (config/spend_caps.json, D-56)
        run = cls(path, data)
        run.save()
        return run

    def _stamp(self):
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def save(self) -> None:
        with self.lock:
            if self._stamp() != self._seen:
                raise LedgerConflict(f"{self.path} was changed by another process; stop and re-open the run")
            write_json_atomic(self.path, self.data)
            self._seen = self._stamp()

    # --- approvals (a paid batch runs only with the creator's yes on exactly that batch) -------------------------------
    def approve(self, plan_id: str, plan_hash: str, *, by: str, ref: str, provider: str, usd: float) -> None:
        """Record the creator's approval of one paint plan. ``ref`` points at the creator's own message (thread message id
        or date and words); the approval binds the plan's hash, so a changed plan needs a new yes."""
        if not by or not ref:
            raise ValueError("an approval needs who approved (by) and where they said it (ref)")
        with self.lock:
            self.data.setdefault("approvals", {})[plan_id] = {
                "hash": plan_hash, "by": by, "ref": ref, "provider": provider, "usd": round(usd, 4),
                "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            self.save()

    def approved(self, plan_id: str, plan_hash: str) -> bool:
        return (self.data.get("approvals", {}).get(plan_id) or {}).get("hash") == plan_hash

    # --- money -------------------------------------------------------------------------------------------------------
    def spent(self, service: str) -> float:
        return round(self.data["spent"].get(service, 0.0), 6)

    def reserve(self, service: str, amount: float, item: str = "") -> None:
        """Record the charge BEFORE the paid call. Refuses past 80 % of the cap, and when the service has no cap."""
        with self.lock:
            self._reserve(service, amount, item)

    def _reserve(self, service: str, amount: float, item: str) -> None:
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

    def reserve_allowance(self, name: str, amount: float, item: str, *, lines: list[str]) -> None:
        """A charge a tool makes on its own under its allowance (``allowances.<name>`` in config/spend_caps.json, e.g. the QA
        loop's re-reads of the script lines it changed, at most 2,000 ElevenLabs credits per run, the creator 2026-10-20).
        Refuses (AllowanceReached) when the allowance's total for this run would pass ``per_run``, and when ``lines`` (what
        the money is for) is empty; the reservation then goes through ``reserve``, so the service's own cap and its 80 %
        stop still apply: the allowance is a ceiling inside the cap, never a raise of it."""
        a = spend_caps.allowance(name)
        if not lines:
            raise ValueError(f"allowance {name}: name the changed lines the charge is for")
        with self.lock:
            used = self.data.setdefault("allowances", {}).setdefault(name, {"service": a["service"], "used": 0.0, "items": {}})
            if used["used"] + amount > float(a["per_run"]) + 1e-9:
                raise AllowanceReached(f"allowance {name}: {used['used'] + amount:g} {a['service']} would pass its "
                                       f"{a['per_run']:g} per run (config/spend_caps.json); stop and ask the creator")
            self._reserve(a["service"], amount, item)  # the cap and its 80 % stop; raises before anything is recorded
            used["used"] += amount
            used["items"][item] = {"amount": amount, "lines": list(lines), "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            self.save()

    def allowance_used(self, name: str) -> float:
        return round((self.data.get("allowances", {}).get(name) or {}).get("used", 0.0), 6)

    def refund(self, service: str, amount: float) -> None:
        """A charge that provably did not happen (the provider refused before generating)."""
        with self.lock:
            self.data["spent"][service] = max(0.0, self.spent(service) - amount)
            self.save()

    def settle(self, service: str, item: str, actual: float) -> float:
        """Replace an item's reservation with what the provider really billed (a pod's RunPod billing). Money already spent
        is recorded even past a cap; returns the change to ``spent``."""
        with self.lock:
            row = self.data["reserved"].get(item) or {"service": service, "amount": 0.0}
            delta = actual - row["amount"]
            self.data["spent"][service] = max(0.0, self.spent(service) + delta)
            self.data["reserved"][item] = {"service": service, "amount": actual, "settled": True}
            self.save()
            return delta

    def rename_reservation(self, old: str, new: str) -> None:
        with self.lock:
            if old in self.data["reserved"]:
                self.data["reserved"][new] = self.data["reserved"].pop(old)
                self.save()

    # --- items and phases --------------------------------------------------------------------------------------------
    def done(self, kind: str, item: str, **info) -> None:
        with self.lock:
            self._done(kind, item, info)

    def _done(self, kind: str, item: str, info: dict) -> None:
        self.data["items"].setdefault(kind, {})[item] = info
        self.save()

    def pending(self, kind: str, ids: list[str]) -> list[str]:
        have = self.data["items"].get(kind, {})
        return [i for i in ids if i not in have]

    def fail(self, key: str, cause: str) -> bool:
        """Count a failure; True while another try is allowed (OR-04: three failures stop the item)."""
        with self.lock:
            return self._fail(key, cause)

    def _fail(self, key: str, cause: str) -> bool:
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
