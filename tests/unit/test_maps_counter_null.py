"""A shot without a sourced number sets "counter": null: it validates, schedules no value and expects no counter text."""
import copy

from explainer_engine.maps.maplibre_lane.hud_ocr import expected_items
from explainer_engine.maps.maplibre_spec import schedule, validate_shot_spec

from tests.unit.test_maps_maplibre_spec import _valid_spec


def _no_counter():
    spec = copy.deepcopy(_valid_spec())
    spec["counter"] = None
    return spec


def test_null_counter_is_valid():
    assert validate_shot_spec(_no_counter()) == []


def test_forgotten_counter_key_is_still_reported():
    spec = _no_counter()
    del spec["counter"]
    assert any("counter" in p for p in validate_shot_spec(spec))


def test_schedule_has_no_counter_value():
    assert schedule(_no_counter(), 10)["counter"] is None


def test_ocr_expects_no_counter_text():
    items = expected_items(_no_counter(), 10)
    assert "counter" not in items and "label" not in items


def test_other_non_dict_counter_is_refused():
    spec = _no_counter()
    spec["counter"] = 5
    assert any("counter" in p for p in validate_shot_spec(spec))
