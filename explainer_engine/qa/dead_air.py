"""Dead air while the narrator speaks (creator's card, 2026-11-20 20:58 UTC: "from the registry"): a stretch with nothing new on
screen that overlaps a narration line is REVIEW over BP-36 ``gap_review_s`` and FAIL over BP-36 ``gap_fail_s`` (the /3 line of
VB-01, ``production/beats.py``). A change is what ``edit/board.change_times`` counts. This reads the finished timeline
(``timed.json``: ``shots``, ``lines[{start, end, speaker}]``, ``duration``) so it also covers a flow that never runs the beats
check. No number is written here. Result ``{status, value, detail}``: PASS / REVIEW / FAIL, NOT_RUN when there is nothing to measure.

    python -m explainer_engine.qa.dead_air <timed.json>        # exit 1 on a FAIL, 2 on NOT_RUN
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from explainer_engine.edit import board
from explainer_engine.qa.first_shot import not_run
from explainer_engine.standards import sourced_rules as SR

GAP_REVIEW_S = float(SR.T("BP-36", "gap_review_s"))  # BP-36
GAP_FAIL_S = float(SR.T("BP-36", "gap_fail_s"))      # BP-36


def dead_air(shots: list[dict], lines: list[dict], duration: float, timed: dict | None = None) -> dict:
    """The longest change-free stretch that overlaps a narration line (a line without a ``speaker``)."""
    if not shots or not isinstance(duration, (int, float)) or duration <= 0:
        return not_run("no shots or no duration")
    narr = [ln for ln in lines if not ln.get("speaker") and ln.get("end", 0) > ln.get("start", 0)]
    if not narr:
        return not_run("no narration lines in the timeline")
    try:
        times = board.change_times(shots, float(duration), timed)
    except (KeyError, TypeError, ValueError):
        return not_run("the shots have no readable start times")
    longest, where = 0.0, (0.0, 0.0)
    for a, b in zip(times, times[1:]):
        if b - a > longest and any(ln["start"] < b and ln["end"] > a for ln in narr):
            longest, where = b - a, (a, b)
    detail_at = f"{where[0]:.1f}-{where[1]:.1f} s"
    if longest > GAP_FAIL_S:
        return {"status": "FAIL", "value": round(longest, 3),
                "detail": f"{longest:.1f} s with nothing new on screen while the narrator speaks ({detail_at}; FAIL over {GAP_FAIL_S:g} s, BP-36)"}
    if longest > GAP_REVIEW_S:
        return {"status": "REVIEW", "value": round(longest, 3),
                "detail": f"{longest:.1f} s with nothing new on screen while the narrator speaks ({detail_at}; REVIEW over {GAP_REVIEW_S:g} s, BP-36)"}
    return {"status": "PASS", "value": round(longest, 3),
            "detail": f"the longest change-free stretch under narration is {longest:.1f} s (at most {GAP_REVIEW_S:g}, BP-36)"}


def check_timed(timed: dict) -> dict:
    return dead_air(timed.get("shots") or [], timed.get("lines") or [], timed.get("duration", 0), timed)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print(__doc__)
        return 2
    r = check_timed(json.loads(Path(argv[0]).read_text(encoding="utf-8")))
    print(f"{r['status']:8} dead_air: {r['detail']}")
    return {"FAIL": 1, "NOT_RUN": 2}.get(r["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
