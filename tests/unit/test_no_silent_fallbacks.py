"""Silent-fallback guards (P2)."""

import pytest

from explainer_engine.edit import visual_compensator as VC
from explainer_engine.production.build_shot import validate_spec
from tests.unit import _comp


@pytest.fixture()
def map_item(tmp_path):
    base = tmp_path / "comp_job"
    manifest = _comp.build(base)
    return base, next(r for r in VC.items_of(manifest, base) if VC._module(r["spec"]["archetype_id"]) == "map")


def test_a_map_shot_is_not_rendered_by_the_old_pil_path(map_item, monkeypatch):
    monkeypatch.delenv(VC.LEGACY_MAP_ENV, raising=False)
    base, row = map_item
    it = row["item"]
    with pytest.raises(ValueError, match="maplibre"):
        VC.render_item_frame(row["spec"], row["spine"], it["trigger_word_index"], it["duration_frames"], 1, 1, base)


def test_the_owner_can_still_ask_for_the_old_pil_map_path(map_item, monkeypatch):
    monkeypatch.delenv(VC.LEGACY_MAP_ENV, raising=False)
    base, row = map_item
    it = row["item"]
    args = (row["spec"], row["spine"], it["trigger_word_index"], it["duration_frames"])
    im = VC.render_item_frame(*args, 1, 1, base, allow_legacy_map=True)
    assert im.size == (row["spec"]["width"], row["spec"]["height"])


def test_map_spec_without_camera_is_a_problem():
    problems = validate_spec({"kind": "map", "film_file": "episode_film.json"})
    assert any("camera" in p for p in problems)


def test_map_spec_without_film_file_is_a_problem():
    problems = validate_spec({"kind": "map", "camera": {"move": "zoom_in"}})
    assert any("film_file" in p for p in problems)


def test_map_spec_with_orbit_or_static_camera_is_a_problem():
    for move in ("orbit", "static"):
        problems = validate_spec({"kind": "map", "camera": {"move": move}, "film_file": "episode_film.json"})
        assert any("camera" in p for p in problems)


def test_photo_spec_without_camera_is_a_problem():
    spec = {
        "id": "S01_SH001", "kind": "photo", "photo": "S01_SH001.jpeg",
        "film_file": "episode_film.json", "seconds": 6.0,
    }
    problems = validate_spec(spec)
    assert any("camera" in p for p in problems)


def test_valid_map_spec_has_no_problem():
    assert validate_spec({"kind": "map", "camera": {"move": "zoom_in"}, "film_file": "episode_film.json"}) == []
