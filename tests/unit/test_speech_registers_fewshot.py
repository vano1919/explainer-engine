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


def test_revision_rules_are_in_the_skill():
    text = (ROOT / ".claude" / "skills" / "narration-script" / "SKILL.md").read_text(encoding="utf-8")
    block = text.split("### Six revision rules", 1)[1].split("### Few-shot test pairs", 1)[0]
    for key in ("not X, but Y", "anachronistic", "echo", "stock similes", "overlap must answer", "moral",
                "physical cause", "left of the colon"):
        assert key.lower() in block.lower(), key


def test_register_lint_reads_only_the_spoken_lines_of_a_markdown_script():
    from explainer_engine.scripting import register_lint as RL
    md = ("# Title — draft\nNotation: [OVERLAP] -- here\n\n## S01\nNARRATOR (Odom): He lands in snow.\n"
          "MARCUS [OVERLAP: -0.45s]: Out of what?\n\n## Measured\nWords 9 — a note — another — more\n")
    text = RL.script_text(md)
    assert "—" not in text and "Measured" not in text and "NARRATOR" not in text
    assert "He lands in snow." in text and "Out of what?" in text


def test_register_checks_short_form_and_narrator_only_text():
    import copy
    from explainer_engine.production import script as S
    from explainer_engine.scripting import speech as SP
    base = {"schema": "production_script/3", "episode": {"id": "x", "title": "X pilot", "short_form": True},
            "cast": {"m": {"names": ["m"], "card": "a courier", "speech": {
                "basis": "personality", "style": "wry, fast, short turns", "words": ["look", "okay", "man"],
                "max_contractions": 0.02, "mlu_range": [3, 5]}}},
            "segments": [{"id": "S01", "lines": [
                {"text": "The rain falls hard tonight."},
                {"text": "I can't do it, and I won't. We don't know why it's so loud, do we?", "speaker": "m", "to": "room"}]}]}
    found = SP.check(base)
    assert sorted(x["detail"].split()[2] for x in found if x["severity"] == "REVIEW")  # both register checks fire
    assert any("contractions" in x["detail"] for x in found) and any("average" in x["detail"] for x in found)
    ok = copy.deepcopy(base)
    ok["cast"]["m"]["speech"].update(max_contractions=0.5, mlu_range=[3, 30])
    assert not [x for x in SP.check(ok) if "contractions" in x["detail"] or "average" in x["detail"]]
    assert "can't" not in S.narrator_tts_text(base) and "rain" in S.narrator_tts_text(base)
    plain = {"segments": [{"lines": [{"text": "Only narration."}]}]}
    assert S.narrator_tts_text(plain) == S.tts_text(plain)
