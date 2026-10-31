"""F0: one fps source for sync windows and one Shorts frame derived from the master (D-85, BP-54, BP-167)."""
import ast
from pathlib import Path

import pytest

from explainer_engine.core import delivery
from explainer_engine.standards import sourced_rules as SR

ROOT = Path(__file__).resolve().parents[2]


def test_frame_ms_follows_fps():
    assert delivery.frame_ms(24) == pytest.approx(41.6667, abs=1e-3)
    assert delivery.frame_ms(30) == pytest.approx(33.3333, abs=1e-3)
    assert delivery.frame_ms() == pytest.approx(1000 / delivery.fps())
    with pytest.raises(ValueError):
        delivery.frame_ms(0)


def test_shorts_frame_is_master_rotated():
    assert delivery.shorts_frame() == (1440, 2560)
    w, h = delivery.size()
    assert delivery.shorts_frame() == (h, w)


def test_bp54_row_is_frames_not_milliseconds():
    th = SR.rule("BP-54")["thresholds"]
    assert th["frames"] == 1 and "frame_ms" not in th


def test_bp54_modules_hold_no_literal_33():
    mods = [e.split(":")[0] for e in SR.rule("BP-54")["enforced_by"]]
    assert "explainer_engine/core/delivery.py" in mods
    for m in mods:
        tree = ast.parse((ROOT / m).read_text(encoding="utf-8"))
        nums = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                and not isinstance(n.value, bool)]
        assert 33 not in nums and 33.3 not in nums, m
    src = (ROOT / "explainer_engine/audio/sound_director.py").read_text(encoding="utf-8")
    assert "delivery.frame_ms" in src and '"frame_ms"' not in src
