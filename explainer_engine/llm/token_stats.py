"""Measured output sizes of real API calls, so max_tokens is a number we measured and not a guess (creator 2026-11-01).

    python -m explainer_engine.llm.token_stats                 # table per (model, effort, job/request)
    python -m explainer_engine.llm.token_stats suggest fable high 20000   # a max_tokens for an expected answer size

``usage.output`` of a ledger line counts thinking AND answer tokens, so it is the number that fills max_tokens.
A call that stopped on ``max_tokens`` is a lower bound only (the real need was higher).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[2] / "jobs" / "llm_ledger" / "calls.jsonl"
HEADROOM = 1.5                  # house: measured maximum x 1.5 (a call that hit the cap counts x 2 as a lower bound)
FLOOR = {"low": 8000, "medium": 16000, "high": 32000, "xhigh": 64000, "max": 64000}


def load(path: Path = LEDGER) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def measured(rows: list[dict]) -> dict[tuple, dict]:
    """(model, effort, job, request id) -> {calls, max_out, capped}; one entry per request id, tool turns folded in."""
    start = {r["uid"]: r for r in rows if r.get("ev") == "start"}
    out: dict[tuple, dict] = collections.defaultdict(lambda: {"calls": 0, "max_out": 0, "capped": 0})
    for r in rows:
        if r.get("ev") != "done" or "usage" not in r:
            continue
        s = start.get(r["uid"], {})
        key = (str(r.get("model", s.get("model", "?"))), r.get("effort"), s.get("job"), s.get("id"))
        e = out[key]
        e["calls"] += 1
        e["max_out"] = max(e["max_out"], r["usage"].get("output", 0))
        e["capped"] += r.get("stop") == "max_tokens"
    return dict(out)


def suggest(effort: str, expected_answer: int, rows: list[dict] | None = None, model: str | None = None) -> int:
    """max_tokens for one turn: the floor of the effort, or the largest measured need of that effort x HEADROOM,
    or the expected answer x 3 (thinking is about twice the answer at high), whichever is largest. Never below the answer."""
    best = 0
    for (m, eff, _job, _id), e in measured(rows if rows is not None else load()).items():
        if eff == effort and (model is None or model in m):
            best = max(best, int(e["max_out"] * (2.0 if e["capped"] else HEADROOM)))
    return max(FLOOR.get(effort, 32000), best, expected_answer * 3)


def main(argv: list[str]) -> int:
    if argv[:1] == ["suggest"] and len(argv) >= 4:
        print(suggest(argv[2], int(argv[3]), model=argv[1]))
        return 0
    for (m, eff, job, rid), e in sorted(measured(load()).items(), key=lambda kv: -kv[1]["max_out"]):
        print(f"{m:18} {str(eff):6} {str(job):18} {str(rid)[:22]:22} max_out={e['max_out']:6} calls={e['calls']} capped={e['capped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
