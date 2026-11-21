"""fx25d/depth_metres.py: relative inverse depth -> assumed metres, monotone, cached by picture content. No model needed (a fake session)."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from explainer_engine.fx25d import depth_metres as DM


class FakeSession:
    calls = 0

    class _In:
        name = "pixel_values"

    def get_inputs(self):
        return [self._In()]

    def run(self, _o, feed):
        FakeSession.calls += 1
        x = feed["pixel_values"]
        h, w = x.shape[2:]
        ramp = np.tile(np.linspace(0, 10, w, dtype=np.float32), (h, 1))   # left far, right near
        return [ramp[None]]


def _photo(tmp_path, colour=90):
    p = tmp_path / "p.png"
    Image.new("RGB", (320, 180), (colour, 60, 30)).save(p)
    return p


def test_metres_are_monotone_and_inside_the_range():
    rel = np.linspace(0, 1, 1000, dtype=np.float32).reshape(10, 100)
    d = DM.relative_to_metres(rel, 2.0, 50.0)
    assert d.min() == pytest.approx(2.0, rel=1e-3) and d.max() == pytest.approx(50.0, rel=1e-3)
    assert (np.diff(d, axis=1) <= 1e-6).all()          # nearer (larger relative) -> fewer metres


def test_bad_range_is_refused():
    with pytest.raises(ValueError):
        DM.relative_to_metres(np.zeros((2, 2)), 10.0, 5.0)


def test_ensure_depth_writes_and_reuses_the_cache(tmp_path):
    FakeSession.calls = 0
    p = _photo(tmp_path)
    out = DM.ensure_depth(p, tmp_path / "c", session=FakeSession())
    assert out.exists() and np.load(out).shape == (360, 640) and np.load(out).dtype == np.float32
    again = DM.ensure_depth(p, tmp_path / "c", session=FakeSession())
    assert again == out and FakeSession.calls == 1


def test_cache_key_follows_the_picture_and_the_range(tmp_path):
    a = DM.cache_path(_photo(tmp_path, 90), tmp_path, 2.5, 60.0)
    b = DM.cache_path(_photo(tmp_path, 91), tmp_path, 2.5, 60.0)
    c = DM.cache_path(_photo(tmp_path, 90), tmp_path, 3.0, 60.0)
    assert len({a, b, c}) == 3


def test_missing_model_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "none"))
    with pytest.raises(FileNotFoundError):
        DM.ensure_depth(_photo(tmp_path), tmp_path / "c")
