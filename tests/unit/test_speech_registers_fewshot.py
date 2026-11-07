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


def _pairs():
    text = (ROOT / ".claude" / "skills" / "narration-script" / "SKILL.md").read_text(encoding="utf-8")
    block = text.split("### Few-shot test pairs", 1)[1]
    good, bad = block.split("BAD (register lint must flag):")
    keep = lambda b: [ln.strip() for ln in b.splitlines() if ln.startswith("    ")]
    return keep(good), keep(bad)


def test_few_shot_pairs_run_through_the_register_lint():
    from explainer_engine.scripting import register_lint as RL
    good, bad = _pairs()
    assert good and bad
    for line in good:
        assert not [f for f in RL.findings(line) if f["severity"] == "FAIL"], line
    for line in bad:
        assert any(f["severity"] == "FAIL" for f in RL.findings(line)), line
