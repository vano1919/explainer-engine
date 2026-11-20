"""Extra tests for the three small fixes found when running the corrected G-04b tests against Gemini's code (tester, 2026-11-20)."""
import json

import pytest

from explainer_engine.maps.maplibre_spec import ShotSpecError, load_shot_spec, schedule, validate_shot_spec


def _spec():
    return {
        "size": [1280, 704], "fps": 24, "seconds": 5.0, "center": [2.85, 50.8], "zoom": 9.5,
        "line_geojson": "a.geojson", "line_t": [0.4, 3.6],
        "counter": {"from": 0, "to": 100, "t0": 1.0, "t1": 4.0, "label": "X"},
        "date_chip": [{"t": 0.0, "text": "A"}, {"t": 2.2, "text": "B"}],
        "towns": [], "font": "preset", "footnote": "",
    }


def test_date_chip_order_in_the_spec_does_not_matter():
    spec = _spec()
    spec["date_chip"] = list(reversed(spec["date_chip"]))
    assert schedule(spec, 0)["date"] == "A"
    assert schedule(spec, 72)["date"] == "B"        # t = 3.0 s


@pytest.mark.parametrize("field,bad", [("fps", float("nan")), ("seconds", float("inf")), ("zoom", float("nan")),
                                       ("size", [float("inf"), 704])])
def test_non_finite_numbers_are_rejected(field, bad):
    spec = _spec()
    spec[field] = bad
    assert len(validate_shot_spec(spec)) >= 1


def test_load_wraps_undecodable_bytes_and_missing_file(tmp_path):
    p = tmp_path / "bin.json"
    p.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ShotSpecError):
        load_shot_spec(p)
    with pytest.raises(ShotSpecError):
        load_shot_spec(tmp_path / "missing.json")


def test_load_accepts_valid_file(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(_spec()), encoding="utf-8")
    assert load_shot_spec(p)["fps"] == 24
