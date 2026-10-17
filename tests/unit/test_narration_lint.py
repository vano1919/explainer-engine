"""Narration lint (skill narration-script): the defects the creator heard in the first reads are caught."""

from __future__ import annotations

from pathlib import Path

from explainer_engine.scripting import narration_lint as L

ROOT = Path(__file__).resolve().parents[2]
GOOD = ("[curious] Could they survive the Stone AGE? No tools. [dramatically] But night is coming.\n"
        "Hmm. Who takes charge? Franklin does, naturally. But a rule won't keep anyone warm.\n"
        "Oh. A lens. One bright point on the grass. And tomorrow? Tomorrow, they need a pot.\n")


def rules(text, severity=None):
    return [f["rule"] for f in L.lint(text) if severity is None or f["severity"] == severity]


def test_a_good_script_has_no_findings():
    assert L.lint(GOOD) == []


def test_the_hook_must_be_a_question_and_a_wh_hook_falls():
    assert "N-01" in rules("No tools. But night is coming.\n", "FAIL")
    assert "N-01" in rules(GOOD.replace("Could they survive the Stone AGE?", "What happens to them in the Stone Age?"))


def test_ellipses_caps_and_long_sentences():
    assert "N-03" in rules(GOOD.replace("No tools.", "No... tools... at all... here."), "FAIL")
    assert "N-04" in rules(GOOD.replace("No tools.", "NO tools AT all."), "FAIL")
    long = " ".join(["word"] * 25) + "."
    assert "N-05" in rules(GOOD.replace("No tools.", long))


def test_closed_beats_missing_questions_and_no_interjections():
    closed = GOOD.replace("But a rule won't keep anyone warm.", "The rule works well.")
    assert "N-02" in rules(closed)
    flat = "Could they survive? " + " ".join(["They walk."] * 80) + " But then it rains.\n"
    assert "N-06" in rules(flat) and "N-07" in rules(flat)


def test_sounds_mid_sentence_and_stage_directions():
    assert "N-08" in rules(GOOD.replace("One bright point", "One hmm bright point"))
    assert "N-09" in rules(GOOD.replace("[dramatically]", "[pacing]"), "FAIL")


def test_the_committed_day1_v4_text_passes():
    text = (ROOT / "examples/stone_age/day1_v4/narration_tts.txt").read_text(encoding="utf-8")
    assert [f for f in L.lint(text) if f["severity"] == "FAIL"] == []
