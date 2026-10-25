"""Rule one (OR-22, creator 2026-10-26): no system decision on an assumption; OR-23: a detailed plan before every pod.
Both are written where every session reads them."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_rule_one_and_the_pod_plan_are_in_orchestration_and_claude_md():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    assert "| OR-22 | **Rule one: no system decision on an assumption**" in orch
    assert "| OR-23 | **A detailed plan before every pod**" in orch
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude.index("OR-22") < claude.index("## Commands")  # read first
    assert "also in auto mode" in claude and "OR-23" in claude


def test_the_pod_plan_names_every_item():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(l for l in orch.splitlines() if l.startswith("| OR-23 |"))
    for item in ("base model", "checkpoint", "captions", "learning rate", "seeds", "price per hour", "time cap",
                 "money cap", "ledger", "stops the pod", "A general summary"):
        assert item in row, item
