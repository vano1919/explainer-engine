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


def test_important_decisions_go_to_a_higher_model_thread_and_its_confirmation_starts_the_pod():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(l for l in orch.splitlines() if l.startswith("| OR-24 |"))
    for item in ("higher model", "Opus", "get_session", "without", "reasoning", "OPEN", "confirms the pod plan", "spend_caps.json",
                 "top-up"):
        assert item in row, item
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "OR-24" in claude and claude.index("OR-24") < claude.index("## Commands")


def test_evaluations_are_direct_and_plans_are_full_scale():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(l for l in orch.splitlines() if l.startswith("| OR-25 |"))
    for item in ("direct", "full scale", "starts from the goal", "every path", "known training methods"):
        assert item in row, item
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "OR-25" in claude and claude.index("OR-25") < claude.index("## Commands")


def test_or26_opus_plans_sonnet_works_is_a_rule_and_in_claude_md():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    row = next(l for l in orch.splitlines() if l.startswith("| OR-26 |"))
    assert "Opus plans, Sonnet works" in row
    assert "OR-26" in claude and claude.index("OR-26") < claude.index("## Commands")


def test_or28_halt_and_ask_names_its_triggers_and_the_block_format():
    orch = (ROOT / "docs" / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(l for l in orch.splitlines() if l.startswith("| OR-28 |"))
    for item in ("[STOP — CREATOR CONFIRMATION REQUIRED]", "config/spend_caps.json", "deleting unmerged work", "90 %",
                 "a creative or architectural choice the rules do not settle", "UD-01"):
        assert item in row, item
    assert "| OR-29 |" in orch and "| OR-30 |" in orch
