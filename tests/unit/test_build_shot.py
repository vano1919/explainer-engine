"""production/build_shot.py: spec checks, the five camera moves, the film's finish, the plume gate. Tiny synthetic renders (2 frames)."""
from __future__ import annotations

import json
import shutil

import numpy as np
import pytest
from PIL import Image

from explainer_engine.fx25d import living as LV
from explainer_engine.production import build_shot as BS

FILM = {"schema": "episode_film/1", "film_id": "t_film", "film_name": "T", "era": "WWI", "picture": {"era_look": "a", "grade_words": "b"},
        "map": {"style_preset": "truce_cold", "font": "Liberation Serif"}, "counter": {"style_preset": "truce_cold"},
        "colour": {"targets": "x=#000000"}, "subtitles": {"font": "Inter", "colour": "#ffffff", "position": "bottom_center"},
        "direction": {"notes": ["n"]}, "narration": {"notes": ["n"]}}


def _setup(tmp_path, **spec_over):
    rs = np.random.RandomState(0)
    Image.fromarray(np.clip(120 + 30 * rs.randn(180, 320, 3), 0, 255).astype(np.uint8)).save(tmp_path / "p.png")
    (tmp_path / "film.json").write_text(json.dumps(FILM))
    spec = {"id": "T1", "photo": "p.png", "film_file": "film.json", "seconds": 0.1, "camera": {"move": "truck_zoom_in"}}
    spec.update(spec_over)
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    return tmp_path / "spec.json"


@pytest.fixture(autouse=True)
def fake_depth(monkeypatch, tmp_path):
    def fake(photo, cache_dir, near, far, session=None):
        p = tmp_path / "depth.npy"
        np.save(p, np.full((36, 64), 8.0, np.float32))
        return p
    monkeypatch.setattr(BS, "ensure_depth", fake)


def test_five_moves_only():
    for mv in LV.MOVES:
        assert LV.check_camera({"move": mv})["move"] == mv
    for bad in ("orbit", "static", "pan"):
        with pytest.raises(ValueError):
            LV.check_camera({"move": bad})
    with pytest.raises(ValueError):
        LV.check_camera({"move": "truck", "bearing": 10})


def test_camera_moves_have_the_right_sign(tmp_path):
    def cam(move, **kw):
        s = LV.Shot("x", 2.0, False, False, pic=np.full((180, 320, 3), 100, np.uint8), depth=np.full((36, 64), 8.0, np.float32),
                    inventory=BS.inventory({}), camera=dict(move=move, **kw))
        return s.cam(0.0), s.cam(2.0 - 1 / 24)
    (l0, p0), (l1, p1) = cam("truck")
    assert p0 == p1 == 0 and l1 > l0
    assert cam("truck", dir=-1)[1][0] < cam("truck", dir=-1)[0][0]
    (l0, p0), (l1, p1) = cam("zoom_in")
    assert l0 == l1 == 0 and p1 > p0
    (l0, p0), (l1, p1) = cam("zoom_out")
    assert p1 < p0
    (l0, p0), (l1, p1) = cam("truck_zoom_out")
    assert l1 > l0 and p1 < p0


def test_spec_problems_are_listed():
    probs = BS.validate_spec({"id": "x", "camera": {"move": "orbit"}, "living": {"lava": 1}})
    assert any("photo" in p for p in probs) and any("orbit" in p for p in probs) and any("lava" in p for p in probs)


def test_builds_a_clip_with_the_films_finish(tmp_path):
    spec = _setup(tmp_path)
    log = BS.build_shot(spec, tmp_path / "o.mp4")
    assert (tmp_path / "o.mp4").stat().st_size > 1000 and log["frames"] == 2
    assert log["style_preset"] == "truce_cold" and log["film_id"] == "t_film" and "Liberation Serif" in log["font"]
    assert "ASSUMED" in log["depth"]["metric"]
    assert json.loads((tmp_path / "o.render_log.json").read_text())["camera"]["move"] == "truck_zoom_in"


def test_finish_matches_the_preset_numbers():
    img = np.full((8, 8, 3), 0.5, np.float32)
    out = BS.apply_finish(img, {"tint": {"color": "#ffffff", "opacity": 0.5}, "grain": {"opacity": 0.0, "size": 300}, "vignette": 0.0}, 0)
    assert np.allclose(out, 0.5)                              # white multiply tint changes nothing
    out = BS.apply_finish(img, {"tint": {"color": "#000000", "opacity": 0.5}, "grain": {"opacity": 0.0, "size": 300}, "vignette": 0.0}, 0)
    assert np.allclose(out, 0.25)                             # black tint at 50 %
    a = BS.apply_finish(img, {"tint": {"color": "#ffffff", "opacity": 0.0}, "grain": {"opacity": 0.3, "size": 300}, "vignette": 0.0}, 3)
    b = BS.apply_finish(img, {"tint": {"color": "#ffffff", "opacity": 0.0}, "grain": {"opacity": 0.3, "size": 300}, "vignette": 0.0}, 3)
    c = BS.apply_finish(img, {"tint": {"color": "#ffffff", "opacity": 0.0}, "grain": {"opacity": 0.3, "size": 300}, "vignette": 0.0}, 4)
    assert np.array_equal(a, b) and not np.array_equal(a, c) and a.std() > 0


def test_a_film_without_a_preset_is_refused(tmp_path):
    bad = dict(FILM, map={"font": "X"}); bad["counter"] = {}
    (tmp_path / "f.json").write_text(json.dumps(bad))
    with pytest.raises(Exception):
        BS.film_finish(tmp_path / "f.json")


def test_avoiding_plume_without_person_zones_refuses(tmp_path):
    smoke = [{"src": [600, 600], "spread": 0.2, "a": 3.0, "w": 40, "h": 300, "depth": 4.5, "soft": True, "v2": True, "peak": 0.6, "hole": 0.85, "lean": 60, "avoid": True}]
    spec = _setup(tmp_path, living={"smoke": smoke})
    with pytest.raises(ValueError):
        BS.build_shot(spec, tmp_path / "o.mp4")


def test_map_spec_goes_to_the_map_lane(tmp_path, monkeypatch):
    from explainer_engine.production import build_map_shot
    called = {}
    monkeypatch.setattr(build_map_shot, "build", lambda s, o, w=None, t=None: called.setdefault("ok", (str(s), str(o))) and {"id": "m"})
    (tmp_path / "m.json").write_text(json.dumps({"kind": "map"}))
    BS.build_shot(tmp_path / "m.json", tmp_path / "m.mp4")
    assert "ok" in called
