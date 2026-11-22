from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"


def test_plan_scope_rules_doc_exists():
    path = DOCS / "PLAN_SCOPE_RULES.md"
    assert path.is_file(), f"Expected documentation file at {path}"


def test_index_mentions_plan_scope_rules():
    path = DOCS / "INDEX.md"
    assert path.is_file(), f"Expected documentation index at {path}"
    text = path.read_text(encoding="utf-8")
    assert "PLAN_SCOPE_RULES" in text, f"Expected {path} to reference PLAN_SCOPE_RULES"


def test_plan_scope_rules_contains_required_coverage():
    path = DOCS / "PLAN_SCOPE_RULES.md"
    assert path.is_file(), f"Expected documentation file at {path}"
    text = path.read_text(encoding="utf-8")
    assert "Requirements coverage" in text, f"Expected 'Requirements coverage' in {path}"
    for item in ("SC-1", "SC-2", "SC-3", "SC-4"):
        assert item in text, f"Expected {item} in {path}"