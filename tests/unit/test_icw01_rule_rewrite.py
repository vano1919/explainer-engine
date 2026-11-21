"""ICW-01 acceptance (roadmap section 20): the rule texts no longer read as forbidding the Ink Chronicle work.

A grep for the image-generation era's words over CLAUDE.md, docs/*.md (research and archive excluded) and .claude/** returns only
lines inside a file that carries a dated legacy banner (or, since 2026-11-06, a route-scoped D-116 banner) near its top, lines that
say themselves that they are legacy or name D-116 (the route decision that made Qwen and LTX current again), or rows of the decision
log (its history)."""
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
    """A dated banner near the top: the 2026-11-05 legacy banner (ICW-01) or the 2026-11-06 route-scoped banner (D-116)."""
    return any(("2026-11-05" in l and "legacy" in l.lower()) or ("2026-11-06" in l and "Route-scoped since D-116" in l)
               for l in lines[:20])


def test_old_route_words_appear_only_under_a_dated_legacy_banner_or_marked_legacy():
    stale = []
    for path in _files():
        if path.name in HISTORY:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if _banner(lines):
            continue
        stale += [f"{path.relative_to(ROOT)}:{n}" for n, l in enumerate(lines, 1) if WORDS.search(l) and "legacy" not in l.lower()
                  and "D-116" not in l and "D-131" not in l
                  and "D-132" not in l and "D-137" not in l]   # a line that names the 2026-11-06 route decision
    # (D-116) or the v4.3 rebuild (D-131, 2026-11-12: 2.5D is a current route again) is current, not stale; since the Fable
    # audit 2026-11-13 (FA-17) also a line naming D-132 (LTX-2.5 distilled on the v4.3 Modal path) or D-137 (the video lane)
    assert not stale, stale


def test_claude_md_states_the_precedence_rule_and_the_new_identity():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    head = text[:text.index("## Commands")]
    assert "follows the decision log, reports the stale text" in head and "does not refuse" in head
    assert "2D hand-drawn" not in text
    # D-96 as amended and D-116 (2026-11-06): the role split replaces "rendered in Blender" as the identity
    assert "Qwen-Image-2.1 + xworld_v2 draws the look" in head and "LTX animates the J2/J4 shots" in head and "D-116" in head
    # invariant 1, D-113 as amended 2026-11-06: free Blender renders on the PC and CI; the Mac is out of every plan
    assert "The creator's PC only reviews and uploads." not in text and "M4 Pro Mac" not in text
    assert "the creator's PC (RX 5700" in text and "the Mac is out of every plan" in text
    assert "turnaround sheet" in text  # invariant 6, D-101


def test_the_decision_log_defines_d96_to_d116():
    text = (ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    for n in range(96, 117):
        assert f"| D-{n} |" in text, n
    for old, new in (("D-93", "D-97"), ("D-95", "D-99"), ("D-87", "D-112"), ("D-31", "D-113")):
        row = next(l for l in text.splitlines() if l.startswith(f"| {old} |"))
        assert new in row, (old, new)


def test_the_master_mold_guides_and_the_d95_override_are_archived():
    for name in ("CREATOR_OVERRIDE_NARRATION_VISUAL_SHOT_DURATIONS_2026-11-04.md", "CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md",
                 "CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md"):
        assert not (ROOT / "docs" / "wip" / name).exists(), name
        assert (ROOT / "docs" / "archive" / name).read_text(encoding="utf-8").startswith("> **HISTORICAL"), name


def test_the_2026_11_06_amendments_keep_the_history():
    """D-116 (the creator, 2026-11-06): the amended rows keep their 2026-11-04/05 text and add a dated clause; nothing is deleted."""
    rows = {l.split(" | ")[0][2:]: l for l in (ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8").splitlines()
            if l.startswith("| D-")}
    assert "Final VIDEO and STILL pixels come from real 3D geometry" in rows["D-96"] and "Amended 2026-11-06" in rows["D-96"]
    for d in ("D-97", "D-101", "D-105", "D-113"):
        assert "Amended 2026-11-06" in rows[d], d
    assert "J5" in rows["D-116"] and "J2" in rows["D-116"] and "J4" in rows["D-116"] and "decided by creator 2026-11-06" in rows["D-116"]
