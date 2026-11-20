"""Opening density (creator's card, 2026-11-20 20:58 UTC: the opening is 30 s; BP-40, BP-48, BP-85): inside the first
``OPENING_WINDOW_S`` (BP-40 ``hook_window_s``) nothing may stay unchanged longer than ``OPENING_MAX_STILL_S`` (BP-40
``hook_max_still_s``). A change is what ``edit/board.change_times`` counts. The still-picture board enforces the same BP-40 line as
RHYTHM-3; this reads the finished timeline (``timed.json``), so it also covers a flow that never builds the board. No number is
written here. Result ``{status, value, detail}``: PASS / FAIL, NOT_RUN when there is nothing to measure.

    python -m explainer_engine.qa.opening_density <timed.json>        # exit 1 on a FAIL, 2 on NOT_RUN
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.edit import board
from explainer_engine.qa.first_shot import not_run
from explainer_engine.standards import sourced_rules as SR

OPENING_WINDOW_S = float(SR.T("BP-40", "hook_window_s"))         # BP-40
OPENING_MAX_STILL_S = float(SR.T("BP-40", "hook_max_still_s"))   # BP-40
EPS = 1e-6


def opening_density(shots: list[dict], duration: float, timed: dict | None = None) -> dict:
    """Nothing stays unchanged longer than ``OPENING_MAX_STILL_S`` inside the first ``OPENING_WINDOW_S`` (or the whole video if shorter)."""
    if not shots or not isinstance(duration, (int, float)) or duration <= 0:
        return not_run("no shots or no duration")
    try:
        times = board.change_times(shots, float(duration), timed)
    except (KeyError, TypeError, ValueError):
        return not_run("the shots have no readable start times")
    window = min(OPENING_WINDOW_S, float(duration))
    longest, where = 0.0, (0.0, 0.0)
    for a, b in zip(times, times[1:]):
        inside = max(0.0, min(b, window) - a)
        if inside > longest:
            longest, where = inside, (a, b)
    if longest > OPENING_MAX_STILL_S + EPS:
        return {"status": "FAIL", "value": round(longest, 3),
                "detail": f"nothing changes on screen from {where[0]:.1f} to {where[1]:.1f} s inside the first {window:g} s "
                          f"({longest:.1f} s > {OPENING_MAX_STILL_S:g}; BP-40)"}
    return {"status": "PASS", "value": round(longest, 3),
            "detail": f"the longest still in the first {window:g} s is {longest:.1f} s (at most {OPENING_MAX_STILL_S:g}, BP-40)"}


def check_timed(timed: dict) -> dict:
    return opening_density(timed.get("shots") or [], timed.get("duration", 0), timed)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    r = check_timed(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    print(f"{r['status']:8} opening_density: {r['detail']}")
    return {"FAIL": 1, "NOT_RUN": 2}.get(r["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
