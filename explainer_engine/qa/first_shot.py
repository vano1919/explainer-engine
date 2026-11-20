"""The first shot is not a flash (creator's card, 2026-11-20 20:58 UTC, label OR-E01): the first shot lasts at least the C-shot
minimum of BP-85 (``c_shot_s[0]``). No number is written here. Reads a timed production script (``timed.json``:
``shots[{start, end}]``). Result ``{status, value, detail}``: PASS / FAIL, NOT_RUN when there is nothing to measure.

    python -m explainer_engine.qa.first_shot <timed.json>        # exit 1 on a FAIL, 2 on NOT_RUN
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

FIRST_SHOT_MIN_S = float(SR.T("BP-85", "c_shot_s")[0])  # BP-85
EPS = 1e-6


def not_run(why: str) -> dict:
    return {"status": "NOT_RUN", "value": None, "detail": f"not run: {why}"}


def first_shot(shots: list[dict]) -> dict:
    """The first shot lasts at least ``FIRST_SHOT_MIN_S`` (a shot is ``{start, end}`` in seconds)."""
    if not shots:
        return not_run("no shots")
    try:
        length = float(shots[0]["end"]) - float(shots[0]["start"])
    except (KeyError, TypeError, ValueError):
        return not_run("the first shot has no readable start and end")
    if length + EPS < FIRST_SHOT_MIN_S:
        return {"status": "FAIL", "value": round(length, 3),
                "detail": f"the first shot lasts {length:.2f} s, under {FIRST_SHOT_MIN_S:g} s (BP-85): the first cut is a flash"}
    return {"status": "PASS", "value": round(length, 3), "detail": f"the first shot lasts {length:.2f} s (at least {FIRST_SHOT_MIN_S:g} s, BP-85)"}


def check_timed(timed: dict) -> dict:
    return first_shot(timed.get("shots") or [])


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    r = check_timed(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    print(f"{r['status']:8} first_shot: {r['detail']}")
    return {"FAIL": 1, "NOT_RUN": 2}.get(r["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
