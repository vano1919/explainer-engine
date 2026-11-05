"""ICW-01 acceptance (roadmap section 20): the rule texts no longer read as forbidding the Ink Chronicle work.

A grep for the image-generation era's words over CLAUDE.md, docs/*.md (research and archive excluded) and .claude/** returns only
lines inside a file that carries a dated legacy banner near its top, lines that say themselves that they are legacy, or rows of the
decision log (its history)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = re.compile(r"LTX|Qwen|2\.5D|hand-drawn|sprite|keyframe", re.I)
HISTORY = {"DECISIONS_AND_OPEN_QUESTIONS.md", "PLAN_2026-10-15.md"}


def _files():
    yield ROOT / "CLAUDE.md"
    yield from sorted((ROOT / "docs").glob("*.md"))
    yield from sorted((ROOT / ".claude").rglob("*.md"))


def _banner(lines):
    return any("2026-11-05" in l and "legacy" in l.lower() for l in lines[:20])


def test_old_route_words_appear_only_under_a_dated_legacy_banner_or_marked_legacy():
    stale = []
    for path in _files():
        if path.name in HISTORY:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if _banner(lines):
            continue
        stale += [f"{path.relative_to(ROOT)}:{n}" for n, l in enumerate(lines, 1) if WORDS.search(l) and "legacy" not in l.lower()]
    assert not stale, stale


def test_claude_md_states_the_precedence_rule_and_the_new_identity():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    head = text[:text.index("## Commands")]
    assert "follows the decision log, reports the stale text" in head and "does not refuse" in head
    assert "2D hand-drawn" not in text and "rendered in Blender" in head
    assert "The creator's PC only reviews and uploads." not in text and "M4 Pro Mac" in text  # invariant 1, D-113
    assert "turnaround sheet" in text  # invariant 6, D-101


def test_the_decision_log_defines_d96_to_d113():
    text = (ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    for n in range(96, 114):
        assert f"| D-{n} |" in text, n
    for old, new in (("D-93", "D-97"), ("D-95", "D-99"), ("D-87", "D-112"), ("D-31", "D-113")):
        row = next(l for l in text.splitlines() if l.startswith(f"| {old} |"))
        assert new in row, (old, new)


def test_the_master_mold_guides_and_the_d95_override_are_archived():
    for name in ("CREATOR_OVERRIDE_NARRATION_VISUAL_SHOT_DURATIONS_2026-11-04.md", "CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md",
                 "CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md"):
        assert not (ROOT / "docs" / "wip" / name).exists(), name
        assert (ROOT / "docs" / "archive" / name).read_text(encoding="utf-8").startswith("> **HISTORICAL"), name
