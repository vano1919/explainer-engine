"""D-120 (the creator, 2026-11-07 18:08 UTC): one place, one picture; no rendered reference. The rule families LV/RF/HI/DL live in
docs/SCENE_REUSE_RULES.md only, the decision is logged, and the Blender-to-Qwen rows it replaced are marked superseded."""
import re
from pathlib import Path

from explainer_engine import docs_lint

DOCS = Path(__file__).resolve().parents[2] / "docs"


def test_families_have_one_home_and_every_row_is_defined():
    for fam in ("LV", "RF", "HI", "DL"):
        assert docs_lint.HOMES[fam] == "SCENE_REUSE_RULES.md"
    text = (DOCS / "SCENE_REUSE_RULES.md").read_text(encoding="utf-8")
    rows = set(re.findall(r"^\| ((?:LV|RF|HI|DL)-\d\d) \|", text, re.M))
    want = {f"LV-0{i}" for i in range(1, 9)} | {f"RF-0{i}" for i in range(1, 6)} | {f"HI-0{i}" for i in range(1, 9)} \
        | {f"DL-{i:02d}" for i in range(1, 11)}
    assert rows == want


def test_core_rule_words_and_the_creator_message():
    text = (DOCS / "SCENE_REUSE_RULES.md").read_text(encoding="utf-8")
    assert "cmsg_01Hnu5zB86sjUj5GtTgaUkPWWGFzRWxBehT3gJoao5ggGZ" in text
    lv01 = next(l for l in text.splitlines() if l.startswith("| LV-01 |"))
    assert "blurred" in lv01 and "consecutive" in lv01 and "FAIL" in lv01
    rf01 = next(l for l in text.splitlines() if l.startswith("| RF-01 |"))
    assert "Blender" in rf01 and "FAIL" in rf01


def test_decision_logged_and_old_rows_superseded():
    assert re.search(r"^\| D-120 \|", (DOCS / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8"), re.M)
    kp = (DOCS / "SHOT_PROMPTS.md").read_text(encoding="utf-8")
    for row in ("KP-54", "KP-56", "KP-57", "KP-58"):
        line = next(l for l in kp.splitlines() if l.startswith(f"| {row} |"))
        assert "superseded 2026-11-07 by D-120" in line
