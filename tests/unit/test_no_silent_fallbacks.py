"""Silent-fallback guards (P2)."""

from explainer_engine.production.build_shot import validate_spec


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
