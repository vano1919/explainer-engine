from explainer_engine.maps import quality_provisional as qp


def test_enabled_defaults_off(monkeypatch):
    monkeypatch.delenv("EXPLAINER_QUALITY_PROVISIONAL", raising=False)
    assert qp.enabled() is False


def test_enabled_on(monkeypatch):
    monkeypatch.setenv("EXPLAINER_QUALITY_PROVISIONAL", "1")
    assert qp.enabled() is True


def test_primary_line_width_passes_at_boundary():
    assert qp.check_line_width("primary", 0.5) == []


def test_primary_line_width_fails_just_below_boundary():
    problems = qp.check_line_width("primary", 0.49)
    assert len(problems) == 1
    assert "0.5%" in problems[0]


def test_secondary_line_width_passes_at_boundary():
    assert qp.check_line_width("secondary", 0.25) == []


def test_secondary_line_width_fails_just_below_boundary():
    problems = qp.check_line_width("secondary", 0.24)
    assert len(problems) == 1
    assert "0.25%" in problems[0]


def test_label_passes_at_boundaries():
    assert qp.check_label(2.5, 4.5) == []


def test_label_fails_just_below_boundaries():
    problems = qp.check_label(2.49, 4.49)
    assert len(problems) == 2


def test_green_passes_at_boundaries():
    assert qp.check_green(80, 35) == []
    assert qp.check_green(160, 35) == []


def test_green_fails_just_outside_hue_range():
    assert qp.check_green(79, 35) != []
    assert qp.check_green(161, 35) != []


def test_green_fails_just_below_saturation():
    problems = qp.check_green(120, 34)
    assert len(problems) == 1


def test_quality_problems_returns_nothing_when_flag_off(monkeypatch):
    monkeypatch.delenv("EXPLAINER_QUALITY_PROVISIONAL", raising=False)
    items = [
        {"type": "line", "kind": "primary", "width_pct": 0.1},
        {"type": "label", "cap_height_pct": 1.0, "contrast_ratio": 1.0},
        {"type": "green", "hue_deg": 0, "saturation_pct": 0},
    ]
    assert qp.quality_problems(items) == []


def test_quality_problems_returns_problems_when_flag_on(monkeypatch):
    monkeypatch.setenv("EXPLAINER_QUALITY_PROVISIONAL", "1")
    items = [
        {"type": "line", "kind": "primary", "width_pct": 0.1},
        {"type": "label", "cap_height_pct": 1.0, "contrast_ratio": 1.0},
        {"type": "green", "hue_deg": 10, "saturation_pct": 10},
    ]
    problems = qp.quality_problems(items)
    assert len(problems) >= 3
