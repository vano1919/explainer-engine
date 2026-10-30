"""Documentation lint (D-23): the canonical-home rule is enforced, not hoped for."""

from __future__ import annotations

from explainer_engine import docs_lint


def test_the_documentation_set_is_consistent():
    assert docs_lint.check() == []


def test_every_decision_has_exactly_one_home():
    defs = docs_lint.definitions()
    decisions = [k for k in defs if k.startswith("D-")]
    assert len(decisions) >= 23
    assert all(defs[k] == ["DECISIONS_AND_OPEN_QUESTIONS.md"] for k in decisions)


def test_the_lint_catches_a_duplicate_definition_and_a_dangling_id(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "INDEX.md").write_text("[a](A.md) [d](DECISIONS_AND_OPEN_QUESTIONS.md)", encoding="utf-8")
    (docs / "DECISIONS_AND_OPEN_QUESTIONS.md").write_text("| D-01 | x |\n", encoding="utf-8")
    (docs / "A.md").write_text("| D-01 | copy |\nsee D-09 and [gone](missing.md) #FF0000\n```json\n{bad}\n```\n", encoding="utf-8")
    monkeypatch.setattr(docs_lint, "DOCS", docs)
    kinds = {f["check"] for f in docs_lint.check()}
    assert {"canonical_home", "undefined_id", "broken_link", "hex_in_docs", "bad_json"} <= kinds


# ---- T4 CP-11 (plan_v2 wave 2): the documents that described 2512 / Edit-2511 / wldnk as "in use" say it is history ------------------------

import re as _re
from pathlib import Path as _Path

_DOCS = _Path(__file__).resolve().parents[2] / "docs"
_RETIRED = _re.compile(r"2512|Edit-2511|wldnk|nextpose,")
_MARK = _re.compile(r"banned|retired|suspended|History", _re.I)


def _live_retired_mentions(name: str) -> list[str]:
    """Lines that name a retired model, LoRA or trigger outside a History block and without a banned/retired/suspended mark."""
    bad, in_history = [], False
    for n, line in enumerate((_DOCS / name).read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("#"):
            in_history = "History" in line
        if _RETIRED.search(line) and not in_history and not _MARK.search(line):
            bad.append(f"{name}:{n}: {line[:90]}")
    return bad


def test_cp11_retired_models_are_history_in_the_d80_documents():
    found = []
    for name in ("SCRIPT_ENGINE.md", "KEYFRAME_GATE.md", "SHOT_PROMPTS.md"):
        found += _live_retired_mentions(name)
    assert found == []
    engine = (_DOCS / "SCRIPT_ENGINE.md").read_text(encoding="utf-8")
    stage6 = next(l for l in engine.splitlines() if l.startswith("| 6 | Pictures |"))
    assert "Qwen-Image-2.1" in stage6 and "LT-79" in stage6 and "continuity_card/1" in stage6


def test_cp11_ur22_ur25_and_tool_strategy_are_scoped_to_their_route():
    ur = (_DOCS / "UNIVERSAL_RULE_BASE.md").read_text(encoding="utf-8").splitlines()
    for rid in ("| UR-22 |", "| UR-25 |"):
        assert "D-43 still-picture route" in next(l for l in ur if l.startswith(rid))
    ts = (_DOCS / "TOOL_STRATEGY.md").read_text(encoding="utf-8")
    assert "every picture is painted by Gemini on the batch tier" not in ts and "D-50" in ts and "D-80" in ts
    spec = (_DOCS / "VIDEO_PARAMETER_SPEC.md").read_text(encoding="utf-8")
    assert "still-picture route's" in spec and "BP-167" in spec
