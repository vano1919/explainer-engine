"""All attempts at the retry cap, sorted by defects, never chosen (OR-Q03)."""

from __future__ import annotations

import copy

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.qa import attempt_ranking as ar


def chk(cid, sev, passed=False):
    return {"check_id": cid, "rule": cid, "severity": sev, "measured": "x", "threshold": None, "passed": passed}


def att(n, *checks):
    return {"attempt": n, "checks": list(checks)}


def test_fewer_failures_first_then_fewer_reviews():
    rows = ar.rank_attempts([
        att(1, chk("A", "FAIL"), chk("B", "FAIL")),
        att(2, chk("A", "FAIL"), chk("R1", "REVIEW"), chk("R2", "REVIEW")),
        att(3, chk("A", "FAIL")),
    ])
    assert [r["attempt"] for r in rows] == [3, 2, 1]
    assert [(r["fails"], r["reviews"]) for r in rows] == [(1, 0), (1, 2), (2, 0)]
    assert [r["rank"] for r in rows] == [1, 2, 3]


def test_one_failure_outweighs_many_reviews():
    rows = ar.rank_attempts([att(1, chk("F", "FAIL")), att(2, *[chk(f"R{i}", "REVIEW") for i in range(9)])])
    assert [r["attempt"] for r in rows] == [2, 1]


def test_passed_rows_and_info_are_not_defects():
    rows = ar.rank_attempts([att(1, chk("F", "FAIL", passed=True), chk("I", "INFO"), chk("R", "REVIEW", passed=True))])
    assert rows[0]["fails"] == 0 and rows[0]["reviews"] == 0 and rows[0]["defects"] == []


def test_equal_counts_share_a_rank_and_order_by_attempt_number():
    rows = ar.rank_attempts([att(3, chk("F", "FAIL")), att(1, chk("G", "FAIL")), att(2)])
    assert [r["attempt"] for r in rows] == [2, 1, 3]
    assert [r["rank"] for r in rows] == [1, 2, 2]


def test_it_returns_every_attempt_and_picks_none():
    attempts = [att(1, chk("F", "FAIL")), att(2, chk("F", "FAIL"), chk("G", "FAIL")), att(3, chk("R", "REVIEW"))]
    rows = ar.rank_attempts(attempts)
    assert sorted(r["attempt"] for r in rows) == [1, 2, 3]
    assert not ({"best", "chosen", "selected", "winner"} & set().union(*(r.keys() for r in rows)))
    assert ar.rank_attempts([]) == []


def test_inputs_are_not_changed():
    attempts = [att(2, chk("F", "FAIL")), att(1)]
    before = copy.deepcopy(attempts)
    ar.rank_attempts(attempts)
    assert attempts == before


@pytest.mark.parametrize("bad", [
    {"attempt": 0, "checks": []}, {"attempt": "1", "checks": []}, {"attempt": True, "checks": []},
    {"attempt": 1}, {"attempt": 1, "checks": [{"severity": "FAIL"}]},
    {"attempt": 1, "checks": [{"severity": "BAD", "passed": False}]}, "x",
])
def test_malformed_entries_raise(bad):
    with pytest.raises(ContractError):
        ar.rank_attempts([bad])


def test_repeated_attempt_number_raises():
    with pytest.raises(ContractError):
        ar.rank_attempts([att(1), att(1)])


def test_creator_text_lists_all_and_says_it_is_a_sort():
    rows = ar.rank_attempts([att(1, chk("F1", "FAIL")), att(2, *[chk(f"R{i}", "REVIEW") for i in range(7)])])
    text = ar.format_for_creator("S07_SH008", rows)
    assert "S07_SH008" in text and "All 2 attempts" in text and "a sort, not a choice" in text
    assert "attempt 1" in text and "attempt 2" in text and "(+2 more)" in text
