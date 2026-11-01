"""D-92: the creator's 2026-11-01 answers are pinned to the code that already carries them."""
from pathlib import Path

from explainer_engine.core import delivery
from explainer_engine.qa import retry_router as RR
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_d92_numbers_match_the_code():
    assert delivery.fps() == 24
    assert delivery.shorts_frame() == (1440, 2560)
    assert SR.T("BP-01", "wpm_target") == 170


def test_d92_compose_does_not_return_as_fallback():
    assert RR.action_for(3, "ATMOS_BROLL") == "FALLBACK_STILL_HOLD"


def test_d92_is_in_the_decision_log():
    text = (ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").read_text(encoding="utf-8")
    row = next(l for l in text.splitlines() if l.startswith("| D-92 "))
    for needle in ("24 fps", "170 wpm", "1440x2560", "at most 3 seeds", "ElevenLabs", "auto_delete_due"):
        assert needle in row
