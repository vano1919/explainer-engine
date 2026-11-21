"""A fix-edit's change outside its defect box is measured (asset pod end report, 2026-11-06): inside vs outside share, the outside
bounding box and a red/green mask image."""
import numpy as np
import pytest
from PIL import Image

from explainer_engine.qa import fix_diff as FD


def _pic(path, arr):
    Image.fromarray(arr.astype(np.uint8)).save(path)
    return path


def test_a_clean_fix_changes_only_its_box_and_a_dirty_one_is_located(tmp_path):
    base = np.full((100, 200, 3), 120, np.uint8)
    clean = base.copy()
    clean[20:40, 20:60] = 250                                    # the fixed hand, inside the box
    dirty = clean.copy()
    dirty[70:90, 150:190] = 10                                   # the edit also repainted a soldier elsewhere
    b = _pic(tmp_path / "b.png", base)
    box = (0.05, 0.1, 0.35, 0.5)
    rep = FD.report(b, _pic(tmp_path / "c.png", clean), [box])
    assert rep["changed_inside_share"] > 0.3 and rep["changed_outside_share"] == 0 and rep["outside_bbox"] is None
    rep = FD.report(b, _pic(tmp_path / "d.png", dirty), [box], mask_path=tmp_path / "m.png")
    assert rep["changed_outside_share"] > 0.03
    x0, y0, x1, y1 = rep["outside_bbox"]
    assert 0.7 <= x0 <= 0.76 and 0.66 <= y0 <= 0.7 and x1 >= 0.95 and y1 >= 0.9
    m = np.asarray(Image.open(tmp_path / "m.png"))
    assert tuple(m[80, 170]) == (230, 40, 40) and tuple(m[30, 40]) == (40, 200, 80)


def test_codec_noise_is_not_a_change_and_bad_boxes_are_refused(tmp_path):
    rng = np.random.default_rng(1)
    base = np.full((60, 80, 3), 100, np.float32)
    noisy = base + rng.integers(-6, 7, base.shape)
    rep, _, _ = FD.diff(base, noisy, [(0.1, 0.1, 0.2, 0.2)])
    assert rep["changed_outside_share"] == 0
    with pytest.raises(ValueError):
        FD.box_mask((10, 10), [(0.5, 0.5, 0.4, 0.9)])
    with pytest.raises(ValueError):
        FD.diff(base, base[:50], [(0.1, 0.1, 0.2, 0.2)])
