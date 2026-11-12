"""Gates that measure (v4.3 plan P2, EP-03): every gate row says PASS or FAIL from a measurement, or NOT_RUN with the reason no
measurement exists yet. No gate is a literal ``True``; a report with any NOT_RUN is not a pass (it is ``INCOMPLETE``).
A gate on a hypothesis or an engineering default fails as REVIEW, never FAIL (D-59): pass ``level="REVIEW"``
(``sourced_rules.level(rule_id)`` gives the level a rule allows).

A row: ``{"gate": <name>, "status": "PASS"|"FAIL"|"REVIEW"|"NOT_RUN", "measured": <what was measured or None>,
"detail": <text>}``.
"""
from __future__ import annotations

PASS, FAIL, REVIEW, NOT_RUN = "PASS", "FAIL", "REVIEW", "NOT_RUN"


def row(gate: str, ok: bool | None, detail: str, measured=None, level: str = FAIL) -> dict:
    """``ok`` None means nothing was measured: NOT_RUN (``detail`` says why). ``level`` is what a miss is: FAIL or REVIEW."""
    if level not in (FAIL, REVIEW):
        raise ValueError(f"gate {gate}: level must be FAIL or REVIEW, not {level!r}")
    if ok is None:
        return {"gate": gate, "status": NOT_RUN, "measured": None, "detail": detail}
    if not isinstance(ok, bool):
        raise TypeError(f"gate {gate}: the outcome must be a bool from a measurement or None, not {type(ok).__name__}")
    return {"gate": gate, "status": PASS if ok else level, "measured": measured, "detail": detail}


def verdict(rows: list[dict]) -> dict:
    """PASS only when every gate PASSed; FAIL when any FAILed; else INCOMPLETE (something was not measured); else REVIEW
    (a hypothesis gate missed: a person looks)."""
    failed = [r["gate"] for r in rows if r["status"] == FAIL]
    not_run = [r["gate"] for r in rows if r["status"] == NOT_RUN]
    review = [r["gate"] for r in rows if r["status"] == REVIEW]
    status = FAIL if failed else (NOT_RUN if not rows else ("INCOMPLETE" if not_run else (REVIEW if review else PASS)))
    return {"status": status, "failed": failed, "not_run": not_run, "review": review, "gates": rows}
