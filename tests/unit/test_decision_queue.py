"""P0b (OR-29): every decision card has an owner; Claude never answers a creator-owned card without his delegation."""
from __future__ import annotations

import copy
import json

from _gov import ROOT
from explainer_engine.governance import status

CARDS = status.cards(ROOT)


def card(**kw):
    base = {"id": "X1", "question": "q", "options": [["a", "b"]], "reason": "r", "owner": "creator"}
    return base | kw


def test_the_shipped_cards_pass():
    assert status.check_cards(CARDS) == []
    assert len(CARDS) == 35 and all(c["owner"] in ("creator", "claude") for c in CARDS)


def test_a_card_without_an_owner_or_with_a_wrong_one_fails():
    assert status.check_cards([card(owner="")])
    assert status.check_cards([card(owner="coordinator")])


def test_claude_answering_a_creator_card_is_a_failure():
    """The v1 plan's A5 answer: owner creator, answered `by: claude`, no delegation. It must fail."""
    bad = card(id="A5", answer={"index": 1, "label": "D-81", "by": "claude", "at": "2026-10-29T09:00Z", "reason": "my pick"})
    assert any("without his delegation" in e for e in status.check_cards([bad]))
    delegated = copy.deepcopy(bad)
    delegated["answer"]["delegated_by"] = "ვანო"
    assert status.check_cards([delegated]) == []
    his = card(answer={"index": 0, "label": "კი", "by": "ვანო", "at": "x", "reason": "y"})
    assert status.check_cards([his]) == []
    assert status.check_cards([card(answer={"by": "ვანო", "pending": True})]) == []


def test_a_claude_card_needs_a_reason_and_from_s3_a_reviewer():
    ok = card(owner="claude", answer={"index": 0, "label": "x", "by": "claude", "reason": "r"})
    assert status.check_cards([ok]) == []
    assert status.check_cards([card(owner="claude", answer={"index": 0, "by": "claude"})])
    s3 = card(owner="claude", level="S3", answer={"index": 0, "by": "claude", "reason": "r"})
    assert any("reviewed_by" in e for e in status.check_cards([s3]))
    assert status.check_cards([s3 | {"reviewed_by": "Opus thread"}]) == []


def test_duplicate_ids_fail():
    assert status.check_cards([card(), card()])


def test_every_ud_gate_has_a_row_and_a_card_with_the_same_owner():
    docs = (ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    rows = {}
    for line in docs.splitlines():
        if line.startswith("| UD-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0]] = (cells[2], cells[3])
    assert sorted(rows) == [f"UD-{n:02d}" for n in range(1, 11)]
    by_id = {c["id"]: c for c in CARDS}
    for ud, (owner, card_id) in rows.items():
        assert by_id[card_id]["owner"] == owner and by_id[card_id]["ud"] == ud
    assert {c["ud"] for c in CARDS if "ud" in c} == set(rows)


def test_the_licence_card_is_closed_for_performance():
    c11 = next(c for c in CARDS if c["id"] == "C11")
    assert "პერფორმანს" in c11["answer"]["label"] or "პერფორმანს" in c11["answer"]["reason"]
