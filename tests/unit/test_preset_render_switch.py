"""MAP_PRESET switch: unset means unchanged output; a set preset changes the frame."""

import hashlib
import os
from pathlib import Path

import pytest

from explainer_engine.maps import render as R
from explainer_engine.maps import render_presets as P
from explainer_engine.maps import timeline as T


def _frame_hash():
    spec, spine = R.build_toba_gis_map_spec("preset_switch", width=480, height=270, total_frames=48)
    tl, clock = T.build(spec, spine, trigger_word_index=0, duration_frames=48)
    return hashlib.sha256(R.render_frame(spec, tl, clock, 24).convert("RGB").tobytes()).hexdigest()


def test_unset_preset_gives_unit_scales(monkeypatch):
    monkeypatch.delenv("MAP_PRESET", raising=False)
    assert P.line_scale() == 1.0 and P.label_scale() == 1.0


@pytest.mark.skipif(not Path("tools/maps/SR_HR.tif").exists(), reason="SR_HR raster not in CI (gitignored)")
def test_balanced_is_identity_and_bold_changes_the_frame(monkeypatch):
    monkeypatch.delenv("MAP_PRESET", raising=False)
    base = _frame_hash()
    monkeypatch.setenv("MAP_PRESET", "balanced")
    assert P.line_scale() == 1.0 and P.label_scale() == 1.0
    assert _frame_hash() == base
    monkeypatch.setenv("MAP_PRESET", "bold")
    assert P.line_scale() > 1.0 and P.label_scale() > 1.0
    assert _frame_hash() != base
    monkeypatch.delenv("MAP_PRESET", raising=False)
