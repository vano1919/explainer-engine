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


def test_the_hook_takes_one_of_four_forms_never_a_greeting_and_a_wh_hook_falls():
    """BP-03 (supersedes the yes/no-only N-01): a cold-open line is a hook; a greeting FAILs; a long plain sentence is REVIEW."""
    assert "N-01" not in rules("No tools. But night is coming.\n")  # a cold-open line
    assert "N-01" in rules("Welcome back to the channel. But night is coming.\n", "FAIL")
    assert "N-01" in rules("Today we look at the Stone Age. But night is coming.\n", "FAIL")
    plain = "The geniuses walked slowly across the wide grey valley toward the distant hills under a low sky. But night falls.\n"
    assert "N-01" in rules(plain, "REVIEW") and "N-01" not in rules(plain, "FAIL")
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


def test_named_game_and_agency_acronyms_are_not_stress_marks():
    """Syndicate Wars: 'LCN and BAWSAQ', 'GTA', 'IRS' are names, not two stressed words (2026-10-17)."""
    line = "Fans say there are two exchanges, LCN and BAWSAQ, in GTA V."
    assert "N-04" not in rules(GOOD + line + "\n")
    assert "N-04" in rules(GOOD + "Fans say it is REALLY and TRULY odd.\n", "FAIL")
