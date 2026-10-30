"""T4 (plan_v2 wave 2): the creator's 2026-10-30 word on hosts (A1 NO, D-89), the dialogue voice (A3 option A, D-90) and the
craft conflicts (D-91) is written down in the one home of each, and the pages that describe the dialogue route say the same."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _row(doc: str, start: str) -> str:
    return next(line for line in doc.splitlines() if line.startswith(start))


def _card(cid: str) -> dict:
    cards = json.loads(_read("docs/blueprint/decision_queue.json"))["cards"]
    return next(c for c in cards if c["id"] == cid)


def test_d89_hosts_are_no_and_the_card_says_so():
    row = _row(_read("docs/DECISIONS_AND_OPEN_QUESTIONS.md"), "| D-89 |")
    assert "2026-10-30" in row and "card A1" in row and "p12e_hosts" in row and "unspent" in row
    a = _card("A1")["answer"]
    assert a["label"] == "არა" and a["at"].startswith("2026-10-30") and a["by"] == "ვანო"
    caps = json.loads(_read("config/spend_caps.json"))
    assert "p12e_hosts" in caps["paid_tests"]  # the line stays; nothing is spent on it


def test_d90_dialogue_is_read_first_and_conditions_the_clip():
    decisions = _read("docs/DECISIONS_AND_OPEN_QUESTIONS.md")
    row = _row(decisions, "| D-90 |")
    assert "2026-10-30" in row and "cmsg_01Hnu5zB86sjUj5GtTgaUkPWFv6dvb6QVwMfnJ6ic89ksh" in row and "supersedes" in row
    assert "Not built yet" in row  # no page claims what the code does not do
    assert "D-90" in _row(decisions, "| D-88 |")
    assert "D-90" in _row(_read("docs/SCRIPT_ENGINE.md"), "| Dialogue audio |")
    assert "LTX native audio, the voice described in words" not in _row(_read("docs/SCRIPT_ENGINE.md"), "| Dialogue audio |").split("|")[2]
    assert "D-90" in _read("docs/AUDIO_SYSTEM.md").split("sd-matrix:end")[1][:600]
    caster = _read(".claude/agents/voice-caster.md")
    assert "D-90" in caster and "read first" in caster
    assert "write `casting.ltx_voice_text(hero)` as the voice" not in caster
    a = _card("A3")["answer"]
    assert a["by"] == "ვანო" and a["at"].startswith("2026-10-30") and "D-90" in a["reason"]


def test_d91_the_craft_conflicts_are_decided_and_no_row_is_left_pending():
    assert "| D-91 |" in _read("docs/DECISIONS_AND_OPEN_QUESTIONS.md")
    cur = _read("docs/CRAFT_CURRICULUM.md")
    assert "creator decision pending" not in cur and "D-91" in cur
