"""Helpers every validator shares: severity from the registry, threshold reads that never invent a number, critic rows."""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR


def level(rule_id: str) -> str:
    """The severity a miss of this rule may have: REVIEW for a hypothesis, a rule whose registry severity is REVIEW, and a BP id
    the registry lacks (a missing id is a hypothesis, D-59); FAIL (= BLOCK) only for a binding or house rule with severity FAIL."""
    try:
        r = SR.rule(rule_id)
    except KeyError:
        return G.REVIEW
    return G.FAIL if r["status"] != "hypothesis" and r.get("severity", "REVIEW") == "FAIL" else G.REVIEW


def T(rule_id: str, key: str):
    """``sourced_rules.T`` that returns None when the rule or the key is missing (the caller then returns REVIEW, never a made-up
    number)."""
    try:
        return SR.T(rule_id, key)
    except KeyError:
        return None


def missing_threshold(gate: str, rule_id: str, key: str) -> dict:
    return G.row(gate, False, f"{rule_id}.{key} is not in standards/sourced_rules.json: a missing number is a hypothesis, "
                              f"so a person looks", level=G.REVIEW)


def check(gate: str, ok: bool | None, rule_id: str, detail: str, measured=None) -> dict:
    """A measured row whose miss has the registry's severity for ``rule_id``; ``ok`` None is NOT_RUN."""
    return G.row(gate, ok, detail, measured, level=level(rule_id))


def critic(gate: str, rule_id: str, missing: list[str], detail: str, measured=None) -> dict:
    """A rule of kind ``critic``: code can only see that the fields a critic needs are there. Always REVIEW, never PASS
    (a taste call is a person's: REVIEW -> CREATOR_APPROVAL). ``missing`` lists the absent fields (named in the detail)."""
    why = f"fields missing: {', '.join(missing)}; " if missing else "fields present; "
    return G.row(gate, False, f"{why}{detail}; a critic or the creator judges it ({rule_id})",
                 {"missing": missing, **({} if measured is None else {"measured": measured})}, level=G.REVIEW)
