"""Cross-check that the five allowed map camera moves agree across modules.
Guards the delivery gate and the shot-spec validator against drifting apart."""
from explainer_engine.maps import maplibre_spec
from explainer_engine.qa import delivery_gate

# maplibre_spec.py exposes validate_shot_spec(), so the orbit/static rejection assertions below are used.

EXPECTED_MOVES = {"truck", "zoom_in", "zoom_out", "truck_zoom_in", "truck_zoom_out"}


def _base_spec(camera):
    """Minimal otherwise-valid shot spec whose only variable is the camera block."""
    return {
        "size": [1920, 1080],
        "fps": 30,
        "seconds": 10,
        "center": [-120.0, 38.0],
        "zoom": 5.0,
        "line_geojson": "line.geojson",
        "line_t": [0.0, 5.0],
        "counter": None,
        "date_chip": [],
        "towns": [],
        "footnote": "",
        "camera": camera,
    }


def test_delivery_gate_camera_moves_are_exactly_the_five():
    moves = delivery_gate.ALLOWED_CAMERA_MOVES
    assert len(moves) == 5
    assert len(set(moves)) == 5
    assert set(moves) == EXPECTED_MOVES


def test_maplibre_spec_camera_moves_are_exactly_the_five():
    moves = maplibre_spec.ALLOWED_CAMERA_MOVES
    assert len(moves) == 5
    assert len(set(moves)) == 5
    assert set(moves) == EXPECTED_MOVES


def test_camera_moves_agree_between_modules():
    assert set(delivery_gate.ALLOWED_CAMERA_MOVES) == set(maplibre_spec.ALLOWED_CAMERA_MOVES)


def test_maplibre_spec_rejects_orbit_move():
    problems = maplibre_spec.validate_shot_spec(_base_spec({"move": "orbit"}))
    assert any("orbit" in problem for problem in problems)


def test_maplibre_spec_rejects_static_move():
    problems = maplibre_spec.validate_shot_spec(_base_spec({"move": "static"}))
    assert any("static" in problem for problem in problems)
