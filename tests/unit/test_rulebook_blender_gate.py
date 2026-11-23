"""ICW-01 RW-20 (D-96): the Blender render pod is held to the episode rulebook's `paid_assets` gate.

ICW-01 pins the rule text; ICW-04 adds the code assertion (the pod script refuses to start without a passing gate)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_the_paid_assets_gate_row_names_the_blender_render_pod():
    text = (ROOT / "docs" / "EPISODE_STANDARDS.md").read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| `paid_assets` |"))
    assert "Blender render pod" in row and "D-96" in row and "ICW-04" in row


def test_the_production_rules_render_pod_gate_names_paid_assets():
    text = (ROOT / "docs" / "PRODUCTION_RULES.md").read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| 6 |"))
    assert "`paid_assets`" in row and "OR-23" in row and "10.4" in row
