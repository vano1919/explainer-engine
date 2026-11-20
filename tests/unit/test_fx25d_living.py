"""2.5D living photo renderer with the 2D smoke (explainer_engine/fx25d/living.py): inputs are arguments, the plume stays off the person,
the other photos' plumes are untouched. Synthetic photo and depth only (the real shot S07_SH008 lives on HF)."""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.fx25d import living as LV
from explainer_engine.qa import plume_zones as PZ

FRAME = 72


def _pic():
    rs = np.random.RandomState(1)
    return np.clip(110 + 25 * rs.randn(180, 320, 3), 0, 255).astype(np.uint8)


def _depth():
    return np.full((180, 320), 6.5, np.float32)       # one flat plane behind the plume's nominal depth (4.5 m): nothing covers it


def _inventory(avoid: bool):
    inv = copy.deepcopy(LV.INV["S07_SH008"])
    inv["fires"] = []; inv["sway_cloth"] = []
    sm = inv["smoke"][0]; sm.update(lean=0.0, avoid=avoid)
    inv["persons"] = [[(850, 100), (944, 100), (944, 740), (850, 740)]]       # a person standing right next to the plume's source
    return inv


def _shot(avoid: bool):
    return LV.Shot("S07_SH008", 5.0417, False, False, pic=_pic(), depth=_depth(), inventory=_inventory(avoid))


def test_the_renderer_needs_its_inputs():
    with pytest.raises(ValueError):
        LV.Shot("S07_SH008", 1.0, False, False, pic=None, depth=_depth())
    with pytest.raises(ValueError):
        LV.Shot("S07_SH008", 1.0, False, False, pic=_pic(), depth=None)


def test_no_machine_paths_in_the_module():
    src = Path(LV.__file__).read_text(encoding="utf-8")
    assert "/tmp/" not in src and "/mnt/" not in src


def test_a_frame_is_a_pure_function_of_its_number():
    s = _shot(True)
    a = s.render(FRAME); b = s.render(FRAME)
    assert a.shape == (720, 1280, 3) and a.dtype == np.uint8 and np.array_equal(a, b)


def test_without_avoidance_the_plume_lies_on_the_person_and_with_it_it_does_not():
    on = _shot(False); on.render(FRAME)
    r_on = PZ.plume_in_person_share(on.plume_a, on.pmask_f)
    assert r_on["status"] == "FAIL" and r_on["value"] > 0.05, r_on          # the fault of run2e: smoke on the person
    off = _shot(True); off.render(FRAME)
    assert float(off.plume_a.sum()) > 0.0                                   # a plume remains: the share below is not 0/0
    r_off = PZ.plume_in_person_share(off.plume_a, off.pmask_f)
    assert r_off["status"] == "PASS" and r_off["value"] < 0.01, r_off
    assert PZ.plume_total_share(off.plume_a)["status"] == "PASS"


def test_only_the_s07_plumes_read_the_new_keys():
    for k in ("S07_SH008", "S07_SH006"):
        sm = LV.INV[k]["smoke"][0]
        assert sm["avoid"] is True and sm["lean"] > 0, k
    for k, inv in LV.INV.items():
        for sm in inv["smoke"]:
            if k not in ("S07_SH008", "S07_SH006"):
                assert "avoid" not in sm and "lean" not in sm, k


def test_a_plume_that_must_avoid_people_refuses_to_render_without_person_zones():
    inv = copy.deepcopy(LV.INV["S07_SH006"]); inv["persons"] = []
    with pytest.raises(ValueError):
        LV.Shot("S07_SH006", 1.0, False, False, pic=_pic(), depth=_depth(), inventory=inv)
    LV.Shot("S07_SH006", 1.0, False, False, pic=_pic(), depth=_depth(), inventory=inv, person_mask=np.full((90, 160), 255, np.uint8))


def test_an_extra_person_mask_is_measurement_only_when_no_plume_avoids_it():
    inv = _inventory(False); inv["persons"] = []
    extra = np.zeros((90, 160), np.uint8); extra[:, 60:100] = 255              # a person next to the source, given as an image
    a = LV.Shot("S07_SH008", 5.0417, False, False, pic=_pic(), depth=_depth(), inventory=copy.deepcopy(inv))
    b = LV.Shot("S07_SH008", 5.0417, False, False, pic=_pic(), depth=_depth(), inventory=copy.deepcopy(inv), person_mask=extra)
    assert not a.pmask.any() and b.pmask.any()
    assert np.array_equal(a.render(FRAME), b.render(FRAME))                    # the picture is untouched
    assert PZ.plume_in_person_share(a.plume_a, a.pmask_f if a.pmask.any() else None)["status"] == "NOT_RUN"
    assert PZ.plume_in_person_share(b.plume_a, b.pmask_f)["status"] in ("PASS", "FAIL")
