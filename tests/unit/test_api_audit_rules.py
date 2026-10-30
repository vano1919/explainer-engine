"""OR-34 (Fable's full-repo audit is the last gate before a paid test) and OR-35 (API instead of threads where quality holds), creator
2026-10-30: written where every session reads them."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCH = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")


def row(oid):
    return next(l for l in ORCH.splitlines() if l.startswith(f"| {oid} |"))


def test_or34_the_full_repo_audit_is_the_last_gate_before_a_paid_test():
    r = row("OR-34")
    assert r.startswith("| OR-34 | **Fable's full-repo audit is the last gate before a paid test**")
    for item in ("Before ANY paid test", "whole repo", "Claude API", "old era", "new approaches", "necessary or recommended"):
        assert item in r, item
    assert "OR-34" in CLAUDE and CLAUDE.index("OR-34") < CLAUDE.index("## Commands") and CLAUDE.index("OR-26") < CLAUDE.index("OR-34")


def test_or35_api_instead_of_threads_where_quality_holds():
    r = row("OR-35")
    assert r.startswith("| OR-35 | **API instead of threads where quality holds**")
    for item in ("cross-reviews", "audits", "research", "script variants", "llm/claude_api.py", "Threads keep code writing and merging"):
        assert item in r, item
    assert "OR-35" in CLAUDE and CLAUDE.index("OR-35") < CLAUDE.index("## Commands")


def test_the_rows_follow_or33_in_order():
    ids = [l.split("|")[1].strip() for l in ORCH.splitlines() if l.startswith("| OR-3")]
    assert ids[-3:] == ["OR-33", "OR-34", "OR-35"] or ids.index("OR-34") == ids.index("OR-33") + 1
