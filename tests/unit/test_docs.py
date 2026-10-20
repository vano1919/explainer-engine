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
