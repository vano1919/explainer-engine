"""BP-54 on the cue placement: episode1's timed.json carries sfx 0.050 s before their words (the old build's lead); the current
timing code defaults to 0 and holds a scripted offset inside the sourced window, read from the registry."""
from explainer_engine.production import timing
from explainer_engine.standards import sourced_rules as SR


def test_default_offset_is_on_the_word():
    assert timing.SFX_OFFSET == 0.0


def test_the_window_is_read_from_bp54_and_excludes_the_old_50_ms_lead():
    assert timing.SFX_EARLY_MAX == SR.T("BP-54", "early_max_ms") / 1000
    assert timing.SFX_LATE_MAX == SR.T("BP-54", "late_max_ms") / 1000
    assert 0.050 > timing.SFX_EARLY_MAX  # the old lead sat past the limit; a scripted -0.05 s is now clamped to the limit
    assert min(max(-0.050, -timing.SFX_EARLY_MAX), timing.SFX_LATE_MAX) == -timing.SFX_EARLY_MAX
