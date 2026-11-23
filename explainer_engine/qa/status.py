"""The one QA status vocabulary (final plan P-7, W2): PASS, REVIEW, RETRY, BLOCK, NOT_RUN.

* ``PASS``    a measurement or a recorded check passed.
* ``REVIEW``  a person must look (a hypothesis rule missed, or a taste rule that code cannot judge). Never a success.
* ``RETRY``   a miss that the retry router may still fix (OB-2: at most 2 generative retries).
* ``BLOCK``   a miss with no retry left or not retryable; the chain stops.
* ``NOT_RUN`` nothing was measured. Never a success (the tool, the file or the input was absent).

``FAIL`` is the legacy spelling of ``BLOCK``: ``qa/gates.py`` still writes ``"FAIL"`` to records and reads old records, so every
existing caller and test keeps working; ``canon("FAIL") == BLOCK`` and ``is_block`` accepts both. ``INCOMPLETE`` is the legacy
verdict word for "something was not measured" and canonicalises to NOT_RUN. stdlib only.
"""
from __future__ import annotations

PASS, REVIEW, RETRY, BLOCK, NOT_RUN = "PASS", "REVIEW", "RETRY", "BLOCK", "NOT_RUN"
ALL = (PASS, REVIEW, RETRY, BLOCK, NOT_RUN)
LEGACY = {"FAIL": BLOCK, "INCOMPLETE": NOT_RUN}
# the order of severity for a roll-up: the worst status of a set wins
_ORDER = {PASS: 0, REVIEW: 1, NOT_RUN: 2, RETRY: 3, BLOCK: 4}


def canon(status) -> str:
    """The canonical status of a stored one (``FAIL`` -> BLOCK, ``INCOMPLETE`` -> NOT_RUN); anything else is refused."""
    s = LEGACY.get(status, status)
    if s not in ALL:
        raise ValueError(f"unknown QA status {status!r}: one of {', '.join(ALL)}")
    return s


def is_success(status) -> bool:
    """True only for PASS: REVIEW is not a pass, NOT_RUN is not a pass, a missing status is not a pass."""
    try:
        return canon(status) == PASS
    except ValueError:
        return False


def is_block(status) -> bool:
    try:
        return canon(status) == BLOCK
    except ValueError:
        return False


def rollup(rows) -> str:
    """The status of a set of gate rows (dicts with ``status``, or bare statuses). Worst wins in the order
    BLOCK > RETRY > NOT_RUN > REVIEW > PASS; an empty set is NOT_RUN (nothing was measured), never PASS."""
    worst = None
    for r in rows:
        s = canon(r["status"] if isinstance(r, dict) else r)
        if worst is None or _ORDER[s] > _ORDER[worst]:
            worst = s
    return worst or NOT_RUN
