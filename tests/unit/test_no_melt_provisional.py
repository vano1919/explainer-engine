import pytest

from explainer_engine.qa import no_melt_provisional as nm


def test_frame_motion_boundary():
    assert nm.check_frame_motion(nm.T9_RESIDUAL_MOTION_PCT_MAX) == []
    problems = nm.check_frame_motion(nm.T9_RESIDUAL_MOTION_PCT_MAX + 0.0001)
    assert len(problems) == 1
    assert "T9" in problems[0]


def test_shot_motion_boundary():
    assert nm.check_shot_motion(nm.T10_RESIDUAL_DISPLACEMENT_PCT_MAX) == []
    problems = nm.check_shot_motion(nm.T10_RESIDUAL_DISPLACEMENT_PCT_MAX + 0.0001)
    assert len(problems) == 1
    assert "T10" in problems[0]


@pytest.mark.parametrize("effect", ["clouds", "fire", "smoke", "light", "Smoke "])
def test_effect_allowed_accepts_allowlist(effect):
    assert nm.effect_allowed(effect) is True


@pytest.mark.parametrize("effect", ["water", ""])
def test_effect_allowed_rejects_others(effect):
    assert nm.effect_allowed(effect) is False


def test_no_melt_problems_flag_off(monkeypatch):
    monkeypatch.delenv("EXPLAINER_QUALITY_PROVISIONAL", raising=False)
    items = [
        {"effect": "water", "frame_pct": 0.06, "shot_pct": 0.3},
        {"effect": "clouds", "frame_pct": 0.06, "shot_pct": 0.3},
    ]
    assert nm.no_melt_problems(items) == []


def test_no_melt_problems_flag_on(monkeypatch):
    monkeypatch.setenv("EXPLAINER_QUALITY_PROVISIONAL", "1")
    items = [
        {"effect": "water", "frame_pct": 0.06, "shot_pct": 0.3},
        {"effect": "clouds", "frame_pct": 0.06, "shot_pct": 0.3},
        {"effect": "fire", "frame_pct": 0.04, "shot_pct": 0.1},
    ]
    problems = nm.no_melt_problems(items)
    assert len(problems) == 5
    assert any("water" in p for p in problems)
    assert any("T9" in p for p in problems)
    assert any("T10" in p for p in problems)
