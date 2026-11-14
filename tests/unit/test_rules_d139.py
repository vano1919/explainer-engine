"""D-139 (the creator, 2026-11-14): the video-chain rules are written where the next thread reads them.

VL-14 anchors and chains planned in the script, VL-15 a link gate on every pair, VL-16 the hand-over frame picked by
the main person's face and pose stillness and then upscaled; VL-05 points to VL-16; CT-09 says a continuation and an
upscale are not drawn bases. The code of these rules comes in the roadmap's P2/P3; this test keeps the words.
"""
from __future__ import annotations

from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs"


def _row(doc: str, ident: str) -> str:
    for line in (DOCS / doc).read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| {ident} |"):
            return line
    raise AssertionError(f"{ident} has no row in {doc}")


def test_vl14_plans_anchors_and_chains_and_the_director_sees_video_photos():
    row = _row("VIDEO_LANE.md", "VL-14")
    for words in ("anchor", "continuation", "how many shots", "video included", "No length cap", "D-139"):
        assert words in row, words


def test_vl15_gates_every_pair_before_the_next_paid_wave():
    row = _row("VIDEO_LANE.md", "VL-15")
    for words in ("every pair", "before the next paid run", "PASS", "REDO", "REANCHOR", "STOP", "CT-08"):
        assert words in row, words


def test_vl16_picks_by_face_and_pose_stillness_then_upscales():
    row = _row("VIDEO_LANE.md", "VL-16")
    for words in ("face and pose", "never the whole frame", "pick: director", "upscaled", "2K anchor photo", "BP-187"):
        assert words in row, words
    assert "VL-16" in _row("VIDEO_LANE.md", "VL-05")


def test_ct09_is_clarified_not_weakened():
    row = _row("SHOT_CONTINUITY.md", "CT-09")
    assert "D-139" in row and "never with the clip frame as an image input" in row
    assert "`MAX_CHAIN` is 0" in row  # the rule itself stays


def test_d139_is_in_the_decision_log():
    row = _row("DECISIONS_AND_OPEN_QUESTIONS.md", "D-139")
    assert "RULES_RECONCILIATION_JOURNAL.md" in row and "decided by creator 2026-11-14" in row


def test_or22_is_scoped_so_the_director_decides_per_shot_creative_choices():
    orch = (DOCS / "ORCHESTRATION.md").read_text(encoding="utf-8")
    row = next(line for line in orch.splitlines() if line.startswith("| OR-22 |"))
    assert "Scoped 2026-11-14 by D-139" in row and "goal or the money" in row
    d139 = _row("DECISIONS_AND_OPEN_QUESTIONS.md", "D-139")
    assert "director decides each shot's weather and effects" in d139
