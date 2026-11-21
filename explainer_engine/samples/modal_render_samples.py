"""Paid-run wrapper for sample renders (OR-33): every output and ledger line is written before the next job starts.

A rerun skips jobs whose output file already exists and is non-empty. Stops at 80 % of the cap and after 3 failed jobs.
Modal is imported only inside ``modal_app()``, never at import time.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

MAX_FAILURES = 3
STOP_FRACTION = 0.8


def load_jobs(path) -> list[dict]:
    """Read a JSON list of {"name", "argv", "out"}; reject missing keys and non-string argv items."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("jobs file must be a JSON list")
    jobs = []
    for entry in data:
        for key in ("name", "argv", "out"):
            if key not in entry:
                raise ValueError(f"job missing key {key!r}")
        if not isinstance(entry["argv"], list) or not all(isinstance(item, str) for item in entry["argv"]):
            raise ValueError("argv must be a list of strings")
        jobs.append(entry)
    return jobs


def _has_output(out) -> bool:
    p = Path(out)
    return p.is_file() and p.stat().st_size > 0


def write_ledger_line(path, record: dict) -> None:
    """Append one JSON line and push it to disk before returning."""
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def run_one(job: dict, runner=subprocess.run) -> dict:
    """Run one job without a shell; ok only when the exit code is 0 and the output file exists and is non-empty."""
    proc = runner(job["argv"], capture_output=True, text=True, check=False, shell=False)
    code = proc.returncode
    return {"name": job["name"], "returncode": code, "out_exists": _has_output(job["out"]), "ok": code == 0 and _has_output(job["out"])}


def run_all(jobs, ledger_path, runner=subprocess.run, max_usd: float = 8.0, cost_per_job_usd: float = 0.0) -> list[dict]:
    """Run jobs in order, saving each result before the next. Skips finished jobs; stops at 80 % of max_usd or after 3 failures."""
    results: list[dict] = []
    spent = 0.0
    failures = 0
    for job in jobs:
        if _has_output(job["out"]):
            record = {"name": job["name"], "status": "skipped"}
            write_ledger_line(ledger_path, record)
            results.append(record)
            continue
        if spent >= STOP_FRACTION * max_usd:
            record = {"name": job["name"], "status": "stopped_at_80pct", "spent_usd": round(spent, 4)}
            write_ledger_line(ledger_path, record)
            results.append(record)
            break
        result = run_one(job, runner=runner)
        spent += cost_per_job_usd
        result["spent_usd"] = round(spent, 4)
        result["status"] = "ok" if result["ok"] else "failed"
        write_ledger_line(ledger_path, result)
        results.append(result)
        if not result["ok"]:
            failures += 1
            if failures >= MAX_FAILURES:
                break
    return results


def modal_app():
    """Build the Modal app. Called only by the paid launcher, never at import time."""
    import modal  # lazy import on purpose

    return modal.App("explainer-samples")
