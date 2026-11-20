"""All attempts of a shot that hit the retry cap, ordered by their defects, for the creator to choose from
(creator 2026-11-20 20:42 UTC, card "both", OR-Q03: when the cap is spent the attempts are sorted automatically by defect count
and severity; the final choice is his eye, so this code returns a list and never picks one).

Input: one entry per attempt, ``{"attempt": 1-based int, "checks": [qa_report/1 check rows]}`` (the ``checks`` of that attempt's
``qa_report``; ``shot_id`` is optional). A defect is a check with ``passed`` false: a FAIL row counts as a failure, a REVIEW row as
a review item, INFO rows are not defects. Order: fewest failures first, then fewest review items, then the lower attempt number
(only to make the order stable). No weights and no thresholds: severity is the order of the two keys, nothing else.

    rows = rank_attempts(attempts)         # [{rank, attempt, fails, reviews, defects: [check_id, ...]}], best-looking first
    print(format_for_creator("S07_SH008", rows))
"""

from __future__ import annotations

from explainer_engine.core.errors import ContractError

SEVERITIES = ("FAIL", "REVIEW", "INFO")


def _count(entry: dict) -> dict:
    if not isinstance(entry, dict) or not isinstance(entry.get("attempt"), int) or isinstance(entry.get("attempt"), bool) \
            or entry["attempt"] < 1 or not isinstance(entry.get("checks"), list):
        raise ContractError(f"an attempt entry needs an 'attempt' number from 1 and a 'checks' list, got {entry!r}")
    fails, reviews, defects = 0, 0, []
    for c in entry["checks"]:
        if not isinstance(c, dict) or c.get("severity") not in SEVERITIES or not isinstance(c.get("passed"), bool):
            raise ContractError(f"attempt {entry['attempt']}: a check row needs severity FAIL/REVIEW/INFO and a boolean 'passed': {c!r}")
        if c["passed"] or c["severity"] == "INFO":
            continue
        defects.append(str(c.get("check_id", c.get("rule", "?"))))
        if c["severity"] == "FAIL":
            fails += 1
        else:
            reviews += 1
    return {"attempt": entry["attempt"], "fails": fails, "reviews": reviews, "defects": defects}


def rank_attempts(attempts: list[dict]) -> list[dict]:
    """Every attempt, fewest failures then fewest review items first; ``rank`` is the 1-based position in that order.
    Equal counts get the same rank. Raises ContractError for a malformed entry or a repeated attempt number; inputs are not
    changed. An empty list gives an empty list."""
    rows = [_count(a) for a in attempts]
    numbers = [r["attempt"] for r in rows]
    if len(set(numbers)) != len(numbers):
        raise ContractError(f"attempt numbers repeat: {sorted(numbers)}")
    rows.sort(key=lambda r: (r["fails"], r["reviews"], r["attempt"]))
    prev, rank = None, 0
    for pos, r in enumerate(rows, 1):
        key = (r["fails"], r["reviews"])
        if key != prev:
            rank, prev = pos, key
        r["rank"] = rank
    return rows


def format_for_creator(shot_id: str, rows: list[dict]) -> str:
    """The lines shown to the creator: the order is a sort by defects, not a verdict; he looks and chooses."""
    out = [f"{shot_id}: the retry cap is spent. All {len(rows)} attempts, fewest defects first (a sort, not a choice; "
           "you pick by eye):"]
    for r in rows:
        shown = ", ".join(r["defects"][:5]) + (f" (+{len(r['defects']) - 5} more)" if len(r["defects"]) > 5 else "")
        out.append(f"  #{r['rank']} attempt {r['attempt']}: {r['fails']} FAIL, {r['reviews']} REVIEW" + (f": {shown}" if shown else ""))
    return "\n".join(out)
