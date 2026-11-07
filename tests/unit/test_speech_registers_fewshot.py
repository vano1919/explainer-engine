"""DW-11 registers (creator 2026-11-07): the rule and its few-shot examples stay in the docs and the skill."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dw11_names_registers_and_points_to_the_skill():
    text = (ROOT / "docs" / "STORY_ENGINE.md").read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("| DW-11"))
    assert "Registers" in row and "narration-script" in row


def test_skill_has_few_shot_for_each_register():
    text = (ROOT / ".claude" / "skills" / "narration-script" / "SKILL.md").read_text(encoding="utf-8")
    section = text.split("## Speech registers", 1)[1]
    for who in ("Narrator", "Rustic elder", "City wiseguy", "Child", "Noble"):
        assert f"- {who}" in section
    assert "Bad (" in section
