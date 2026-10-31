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
import os
import threading
import time
from pathlib import Path

from explainer_engine.core import spend_caps
from explainer_engine.core.errors import NeedsReview
from explainer_engine.core.spend_caps import check_caps
from explainer_engine.core.store import write_json_atomic, write_text_atomic

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
        test = (data.get("meta") or {}).get("test")
        if test:  # a paid test's ledger may hold lower caps than its line, never higher
            line = spend_caps.paid_test(test)
            for service, cap in data["caps"].items():
                if cap > line.get(service, 0.0) + 1e-9:
                    raise spend_caps.OverCeiling(f"{service} cap {cap} in {path} is above the line {line.get(service, 0.0)} of "
                                                 f"paid test {test!r} (config/spend_caps.json)")
        run = cls(path, data)
        run.save()
        return run

    @classmethod
    def open_test(cls, path: Path | str, name: str) -> "Run":
        """The ledger of one paid test (config/spend_caps.json ``paid_tests.<name>``): the test's lines as its caps, every other
        service at 0, meta ``test``. Without it a new path gets the episode's ceilings (``check_caps``), far above the test's
        word. An existing ledger of another run or test is refused.

        The cap is per test, not per file: every save of the ledger also writes ``$EXPLAINER_LEDGER_MIRROR/<name>.json`` (a
        durable folder). A new path, or a path lost with its container, is restored from that mirror, so what a test has spent
        is never counted from 0 again; a save of a ledger that differs from its mirror stops with LedgerConflict."""
        caps = {**{s: 0.0 for s in spend_caps.load().get("per_episode", {})}, **spend_caps.paid_test(name)}  # refuses a bad name
        folder = os.environ.get("EXPLAINER_LEDGER_MIRROR")
        if not folder:
            raise ValueError("a paid test's ledger needs a durable mirror so a lost container or a second path cannot restart it "
                             "from 0: set EXPLAINER_LEDGER_MIRROR to a folder that outlives the container")
        path, mirror = Path(path), Path(folder) / f"{name}.json"
        if not path.exists() and mirror.exists():
            write_text_atomic(path, mirror.read_text(encoding="utf-8"))  # same bytes, so ledger and mirror agree
        if path.exists():
            meta = json.loads(path.read_text(encoding="utf-8")).get("meta", {})
            if meta.get("test") != name:
                raise ValueError(f"{path} is not the ledger of paid test {name!r} (its meta test is {meta.get('test')!r})")
        return cls.open(path, caps=caps, test=name, mirror=str(mirror))

    def _stamp(self):
        try:
            return self.path.read_bytes()
        except FileNotFoundError:
            return None

    def save(self) -> None:
        with self.lock:
            if self._stamp() != self._seen:
                raise LedgerConflict(f"{self.path} was changed by another process; stop and re-open the run")
            mirror = (self.data.get("meta") or {}).get("mirror")
            if mirror:  # a paid test's durable copy (open_test): every process that saves the ledger updates it
                if Path(mirror).exists() and Path(mirror).read_bytes() != self._seen:  # another path spent after this one was read
                    raise LedgerConflict(f"ledger {self.path} and its mirror {mirror} differ; reconcile by hand")
            write_json_atomic(self.path, self.data)
            if mirror:
                write_json_atomic(Path(mirror), self.data)
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

    def settled_total(self, service: str) -> float:
        """What providers really billed (items replaced by ``settle``)."""
        return round(sum(r["amount"] for r in self.data["reserved"].values() if r.get("service") == service and r.get("settled")), 6)

    def reserved_open(self, service: str) -> float:
        """What is still only a reservation (the provider's bill has not replaced it yet). The 80 % stop counts both: a bill
        replaces its reservation in ``spent`` as soon as ``settle`` runs, so the stop reads real money where it exists."""
        return round(sum(r["amount"] for r in self.data["reserved"].values() if r.get("service") == service and not r.get("settled")), 6)

    def report(self) -> dict:
        services = sorted({r.get("service") for r in self.data["reserved"].values() if r.get("service")})
        return {"caps": self.data["caps"], "spent": {k: round(v, 4) for k, v in self.data["spent"].items()},
                "settled": {s: self.settled_total(s) for s in services}, "reserved_open": {s: self.reserved_open(s) for s in services},
                "phases": {k: v["status"] for k, v in self.data["phases"].items()},
                "items": {k: len(v) for k, v in self.data["items"].items()},
                "failures": {k: len(v) for k, v in self.data["failures"].items()}}


class Attempts:
    """Code attempts per phase (OR-04, P0b): attempts 1-2 run at the assigned level, the 3rd only escalated (or on its plan), a
    4th stops the item with NeedsReview. File ``jobs/<phase>/attempts.json``."""

    def __init__(self, path: Path | str, at_level: int = 2, escalated: int = 1) -> None:
        self.path, self.at_level, self.escalated = Path(path), at_level, escalated

    def rows(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else []

    def add(self, cause: str = "", *, escalated: bool = False) -> dict:
        rows = self.rows()
        plain = sum(1 for r in rows if not r["escalated"])
        esc = sum(1 for r in rows if r["escalated"])
        if escalated and esc >= self.escalated:
            raise NeedsReview(f"{self.path.parent.name}: {len(rows)} attempts used ({plain} at the assigned level, {esc} escalated); "
                              "write the cause from evidence and ask the creator (OR-04)")
        if not escalated and plain >= self.at_level:
            raise NeedsReview(f"{self.path.parent.name}: attempts 1-{self.at_level} at the assigned level are used; "
                              "the next one runs only escalated (Opus or its plan), then the item stops (OR-04)")
        row = {"n": len(rows) + 1, "escalated": escalated, "cause": cause[:400], "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        write_json_atomic(self.path, rows + [row])
        return row

# --- the pilot measures (P8, the creator 2026-10-31, BP-168): printed in the OR-08 report at REVIEW severity -------------------
REVIEW_MINUTES = "review_minutes.jsonl"   # jobs/<run>/review_minutes.jsonl: one creator-typed line per review


def retry_multiplier(renders: int, accepted: int) -> float | None:
    """Renders divided by accepted shots (an accepted shot is one in ``core/shot_cache``); None until a shot is accepted."""
    return round(renders / accepted, 3) if accepted > 0 and renders >= accepted else None


def count_renders(attempt_files) -> int:
    """Renders made: one row per attempt in each shot's ``attempts.json`` (the QA retry router adds a row per attempt)."""
    return sum(len(Attempts(p).rows()) for p in attempt_files)


def add_review_minutes(job_dir: Path | str, minutes: float, note: str = "", *, by: str = "creator") -> dict:
    """Append the creator's own typed review time (minutes) to ``<job_dir>/review_minutes.jsonl``."""
    if minutes <= 0:
        raise ValueError("review minutes are positive")
    row = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "minutes": float(minutes), "by": by, "note": note[:400]}
    path = Path(job_dir) / REVIEW_MINUTES
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def review_minutes_total(job_dir: Path | str) -> float | None:
    """The sum of the typed minutes; None when the file does not exist (never a guess)."""
    path = Path(job_dir) / REVIEW_MINUTES
    if not path.exists():
        return None
    return round(sum(json.loads(line)["minutes"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()), 3)


def pilot_measures(run: "Run", job_dir: Path | str, *, renders: int | None = None, accepted: int | None = None,
                   finished_minutes: float | None = None) -> dict:
    """The three measures: retry multiplier, USD settled / forecast against the cap, review minutes per finished minute.
    Anything not known stays None."""
    usd = [k for k in run.data["caps"] if k.endswith("_usd")]
    settled = round(sum(run.settled_total(k) for k in usd), 4)
    forecast = round(sum(run.settled_total(k) + run.reserved_open(k) for k in usd), 4)
    total = review_minutes_total(job_dir)
    per_min = round(total / finished_minutes, 3) if total is not None and finished_minutes else None
    return {"retry_multiplier": None if renders is None or accepted is None else retry_multiplier(renders, accepted),
            "settled_usd": settled, "forecast_usd": forecast, "cap_usd": round(sum(run.data["caps"][k] for k in usd), 4),
            "review_minutes": total, "finished_minutes": finished_minutes, "review_minutes_per_finished_minute": per_min}


def pilot_verdict(m: dict) -> dict:
    """Go / Pivot / Abandon (BP-168, house 2026-10-31), a REVIEW-level recommendation for the creator: ABANDON above the
    pivot multiplier; GO when the multiplier, the forecast and the review time are all known and within their GO limits;
    PIVOT otherwise within the pivot multiplier; UNKNOWN while the multiplier is unknown."""
    from explainer_engine.standards import sourced_rules as SR
    mult = m["retry_multiplier"]
    if mult is None:
        return {"verdict": "UNKNOWN", "severity": "REVIEW", "why": "no retry multiplier yet (no accepted shot or no attempts)"}
    if mult > SR.T("BP-168", "pivot_retry_max"):
        return {"verdict": "ABANDON", "severity": "REVIEW", "why": f"retries x{mult} > x{SR.T('BP-168', 'pivot_retry_max')}"}
    rev = m["review_minutes_per_finished_minute"]
    over = []
    if mult > SR.T("BP-168", "go_retry_max"):
        over.append(f"retries x{mult} > x{SR.T('BP-168', 'go_retry_max')}")
    if m["forecast_usd"] > SR.T("BP-168", "go_forecast_usd_max"):
        over.append(f"forecast ${m['forecast_usd']} > ${SR.T('BP-168', 'go_forecast_usd_max')}")
    if rev is not None and rev > SR.T("BP-168", "go_review_min_per_min_max"):
        over.append(f"review {rev} min/min > {SR.T('BP-168', 'go_review_min_per_min_max')}")
    if over:
        return {"verdict": "PIVOT", "severity": "REVIEW", "why": "; ".join(over)}
    if rev is None:
        return {"verdict": "UNKNOWN", "severity": "REVIEW", "why": "review minutes per finished minute are unknown"}
    return {"verdict": "GO", "severity": "REVIEW", "why": "all three measures within the GO limits"}


def morning_rows(m: dict) -> list[str]:
    """The three OR-08 report rows (+ the verdict); an unknown measure prints 'unknown'."""
    def f(x, fmt):
        return "unknown" if x is None else fmt.format(x)
    v = pilot_verdict(m)
    return [f"retry multiplier (renders / accepted): {f(m['retry_multiplier'], 'x{}')}",
            f"settled USD vs cap: ${m['settled_usd']:.2f} settled, ${m['forecast_usd']:.2f} forecast, cap ${m['cap_usd']:.2f}",
            f"review minutes per finished minute: {f(m['review_minutes_per_finished_minute'], '{}')}",
            f"pilot verdict (REVIEW): {v['verdict']} - {v['why']}"]


def main(argv=None) -> None:
    """python -m explainer_engine.core.ledger open-test <run.json> <test>   (a paid test's ledger, before its first create)
       python -m explainer_engine.core.ledger report <run.json> [--attempts DIR] [--accepted N] [--finished-minutes M]
       python -m explainer_engine.core.ledger review-minutes add <job_dir> <minutes> [note...]"""
    import sys
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) == 3 and a[0] == "open-test":
        run = Run.open_test(a[1], a[2])
    elif len(a) >= 2 and a[0] == "report":
        if not Path(a[1]).exists():
            raise SystemExit(f"no ledger at {a[1]}")
        run = Run(Path(a[1]), json.loads(Path(a[1]).read_text(encoding="utf-8")))  # read-only: Run.open would save
        opt = {k: a[i + 1] for i, k in enumerate(a) if k.startswith("--") and i + 1 < len(a)}
        files = sorted(Path(opt["--attempts"]).rglob("attempts.json")) if "--attempts" in opt else []
        m = pilot_measures(run, run.path.parent, renders=count_renders(files) if files else None,
                           accepted=int(opt["--accepted"]) if "--accepted" in opt else None,
                           finished_minutes=float(opt["--finished-minutes"]) if "--finished-minutes" in opt else None)
        print(json.dumps({"path": str(run.path), "meta": run.data.get("meta", {}), **run.report(), "pilot": m,
                          "pilot_rows": morning_rows(m)}, ensure_ascii=False, indent=1))
        return
    elif len(a) >= 4 and a[:2] == ["review-minutes", "add"]:
        print(json.dumps(add_review_minutes(a[2], float(a[3]), " ".join(a[4:])), ensure_ascii=False))
        return
    else:
        raise SystemExit(main.__doc__)
    print(json.dumps({"path": str(run.path), "meta": run.data.get("meta", {}), **run.report()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
