"""T3-6 (CP-16, CP-19): decided questions are marked decided, the retired Kit leaves the live QA question, fps is D-85."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _lines(p):
    return (ROOT / p).read_text(encoding="utf-8").splitlines()


def test_q2_q4_are_marked_decided_and_kit_leaves_live_qa():
    dec = _lines("docs/DECISIONS_AND_OPEN_QUESTIONS.md")
    for q in ("Q2", "Q3", "Q4"):
        line = next(ln for ln in dec if ln.lstrip("- ").startswith(q + " "))
        assert ("decided" in line) or ("superseded" in line), q
    assert "Kit" not in next(ln for ln in _lines("docs/QA_SPECIFICATION.md") if "| Q-E11 |" in ln)


def test_kit_paragraphs_are_banded_as_history():
    sb = _lines("docs/STORYBOARD_SCHEMA.md")
    for ln in sb:
        if "(Kit)" in ln or "Kit actions only" in ln:
            assert "(history, D-04 rejected 2026-10-15)" in ln, ln
    bible = _lines("docs/CREATIVE_STYLE_BIBLE.md")
    assert "(history, D-04 rejected 2026-10-15)" in next(ln for ln in bible if ln.startswith("## Kit"))


def test_craft_curriculum_fps_conflict_is_decided_by_d85():
    txt = (ROOT / "docs/CRAFT_CURRICULUM.md").read_text(encoding="utf-8")
    fps_rows = [ln for ln in txt.splitlines() if "fps" in ln.lower() and "|" in ln]
    assert any("D-85" in ln for ln in fps_rows) or "fps row is decided by D-85" in txt
