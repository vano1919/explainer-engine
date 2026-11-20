"""Camera tests (G-04c camera add-on): spec validation, camera_state maths, render order. No browser, no network."""
import json
import sys
import types

import pytest

if "playwright" not in sys.modules:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        _m = types.ModuleType("playwright")
        _s = types.ModuleType("playwright.sync_api")
        _s.sync_playwright = lambda: None
        sys.modules["playwright"] = _m
        sys.modules["playwright.sync_api"] = _s

from explainer_engine.maps import maplibre_spec as MS
from explainer_engine.maps.hud_layout import boxes_overlap
from explainer_engine.maps.maplibre_lane import render as R
from test_maps_maplibre_lane import LINE, _fake_lane, _FakePW, make_spec  # noqa: E402

import subprocess

BASE = {
    "size": [1280, 704], "fps": 24, "seconds": 5.0, "center": [2.85, 50.8], "zoom": 9.5,
    "line_geojson": "a.geojson", "line_t": [0.4, 3.6],
    "counter": {"from": 0, "to": 100, "t0": 1.0, "t1": 4.0, "label": "X"},
    "date_chip": [], "towns": [], "font": "Inter", "footnote": "",
}
CAMS = {
    "truck": {"move": "truck", "center_from": [2.7, 50.8], "center_to": [3.0, 50.8]},
    "zoom_in": {"move": "zoom_in", "zoom_from": 8.0, "zoom_to": 10.0},
    "zoom_out": {"move": "zoom_out", "zoom_from": 10.0, "zoom_to": 8.0},
    "truck_zoom_in": {"move": "truck_zoom_in", "center_from": [2.7, 50.8], "center_to": [3.0, 50.9],
                      "zoom_from": 8.0, "zoom_to": 10.0},
    "truck_zoom_out": {"move": "truck_zoom_out", "center_from": [2.7, 50.8], "center_to": [3.0, 50.9],
                       "zoom_from": 10.0, "zoom_to": 8.0},
}


def spec_with(cam):
    return {**BASE, "camera": cam}


def test_exactly_five_allowed_moves():
    assert set(MS.ALLOWED_CAMERA_MOVES) == set(CAMS) and len(MS.ALLOWED_CAMERA_MOVES) == 5


@pytest.mark.parametrize("name", list(CAMS))
def test_each_move_validates(name):
    assert MS.validate_shot_spec(spec_with(CAMS[name])) == []


@pytest.mark.parametrize("bad", ["orbit", "rotate", "static", "pan", "", None, 3, "TRUCK"])
def test_other_moves_rejected(bad):
    assert MS.validate_shot_spec(spec_with({"move": bad}))


@pytest.mark.parametrize("key", ["bearing", "pitch", "rotation", "roll", "orbit"])
def test_rotation_keys_rejected(key):
    assert any(key in p for p in MS.validate_shot_spec(spec_with({**CAMS["truck"], key: 10})))


def test_camera_not_a_dict_and_none():
    assert MS.validate_shot_spec({**BASE, "camera": "truck"})
    assert MS.validate_shot_spec({**BASE, "camera": None}) == []


def test_truck_needs_two_different_centres():
    assert MS.validate_shot_spec(spec_with({"move": "truck", "center_from": [1, 1], "center_to": [1, 1]}))
    assert MS.validate_shot_spec(spec_with({"move": "truck", "center_from": [1, 1]}))


def test_zoom_direction_enforced():
    assert MS.validate_shot_spec(spec_with({"move": "zoom_in", "zoom_from": 10, "zoom_to": 8}))
    assert MS.validate_shot_spec(spec_with({"move": "zoom_out", "zoom_from": 8, "zoom_to": 10}))
    assert MS.validate_shot_spec(spec_with({"move": "zoom_in", "zoom_from": 8, "zoom_to": 8}))
    assert MS.validate_shot_spec(spec_with({"move": "zoom_in", "zoom_from": 8}))


def test_ease_must_be_smoothstep_and_nan_rejected():
    assert MS.validate_shot_spec(spec_with({**CAMS["zoom_in"], "ease": "linear"}))
    assert MS.validate_shot_spec(spec_with({**CAMS["zoom_in"], "zoom_to": float("nan")}))


def test_static_when_no_camera():
    for f in (0, 60, 119):
        assert MS.camera_state(BASE, f) == {"center": (2.85, 50.8), "zoom": 9.5}


@pytest.mark.parametrize("name", list(CAMS))
def test_endpoints_exact_and_nothing_outside_range(name):
    spec = spec_with(CAMS[name])
    n = MS.frame_count(spec)
    s0, s1 = MS.camera_state(spec, 0), MS.camera_state(spec, n - 1)
    cam = CAMS[name]
    if "center_from" in cam:
        assert s0["center"] == tuple(cam["center_from"]) and s1["center"] == pytest.approx(tuple(cam["center_to"]))
    else:
        assert s0["center"] == s1["center"] == (2.85, 50.8)
    if "zoom_from" in cam:
        assert s0["zoom"] == cam["zoom_from"] and s1["zoom"] == pytest.approx(cam["zoom_to"])
    else:
        assert s0["zoom"] == s1["zoom"] == 9.5


def test_smoothstep_ease_midpoint_and_slow_ends():
    spec = spec_with(CAMS["zoom_in"])  # 120 frames: u = f/119
    mid = MS.camera_state(spec, 119 // 2 + 0)["zoom"]
    assert 8.0 < mid < 10.0
    z = [MS.camera_state(spec, f)["zoom"] for f in range(120)]
    assert all(b >= a for a, b in zip(z, z[1:]))  # monotonic
    assert z[1] - z[0] < z[60] - z[59]  # eased start is slower than the middle
    assert z[119] - z[118] < z[60] - z[59]  # eased end too
    # symmetric about the middle
    assert z[0] + z[119] == pytest.approx(18.0) and z[30] + z[89] == pytest.approx(18.0)


def test_truck_keeps_zoom_and_zoom_keeps_centre():
    t = MS.camera_state(spec_with(CAMS["truck"]), 50)
    assert t["zoom"] == 9.5 and t["center"][0] != 2.85
    z = MS.camera_state(spec_with(CAMS["zoom_in"]), 50)
    assert z["center"] == (2.85, 50.8)


def test_camera_state_one_frame_and_does_not_mutate():
    spec = {**spec_with(CAMS["zoom_in"]), "fps": 1, "seconds": 1}
    before = json.dumps(spec)
    assert MS.camera_state(spec, 0)["zoom"] == 10.0  # single frame lands on the end state
    assert json.dumps(spec) == before


def test_no_rotation_in_state():
    assert set(MS.camera_state(spec_with(CAMS["truck_zoom_in"]), 10)) == {"center", "zoom"}


# ---------------------------------------------------------------- render
def _render(tmp_path, monkeypatch, cam):
    p, spec = make_spec(tmp_path, camera=cam)
    tiles = tmp_path / "tiles"
    (tiles / "vector").mkdir(parents=True)
    log = {}
    _fake_lane(tmp_path, monkeypatch)
    calls = []

    class Page:
        def goto(self, *a, **k):
            pass

        def evaluate(self, js, arg=None):
            if "initScene" in js:
                log["boot"] = arg
            elif "setCamera" in js:
                calls.append(("cam", arg))
            elif "setFrame" in js:
                calls.append(("frame", arg))

        def screenshot(self, path, type=None):
            open(path, "wb").write(b"p")

    class Ctx:
        def route(self, *a):
            pass

        def new_page(self):
            return Page()

    class Br:
        def new_context(self, **k):
            return Ctx()

        def close(self):
            pass

    class PW:
        chromium = types.SimpleNamespace(launch=lambda **k: Br())

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(R, "sync_playwright", lambda: PW())
    monkeypatch.setattr(R.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0))
    out = R.render_shot(str(p), str(tmp_path / "x.mp4"), str(tiles), str(tmp_path / "w"))
    return out, spec, log, calls


def test_render_sets_camera_before_frame_every_frame(tmp_path, monkeypatch):
    out, spec, log, calls = _render(tmp_path, monkeypatch, CAMS["truck_zoom_in"])
    assert out["frames"] == 120 and len(calls) == 240
    for i in range(120):
        assert calls[2 * i][0] == "cam" and calls[2 * i + 1] == ("frame", i)
    assert calls[0][1]["zoom"] == 8.0 and calls[-2][1]["zoom"] == pytest.approx(10.0)
    assert log["boot"]["camera0"] == {"center": [2.7, 50.8], "zoom": 8.0}


def test_render_without_camera_still_sends_constant_camera(tmp_path, monkeypatch):
    p, _ = make_spec(tmp_path)
    out, spec, log, calls = _render(tmp_path / "b" if (tmp_path / "b").mkdir() is None else tmp_path, monkeypatch, None)
    zs = {c[1]["zoom"] for c in calls if c[0] == "cam"}
    assert zs == {9.5}


def test_counter_slot_free_over_the_whole_camera_path(tmp_path, monkeypatch):
    _, spec, log, _ = _render(tmp_path, monkeypatch, CAMS["zoom_in"])
    cb = tuple(log["boot"]["hudLayout"]["counter_box"])
    coords = R._extract_line_coords(LINE)
    for f in range(0, 120, 7):
        cam = MS.camera_state(spec, f)
        moved = {**spec, "center": list(cam["center"]), "zoom": cam["zoom"]}
        assert not any(boxes_overlap(cb, b) for b in R._build_avoid_boxes(moved, coords, (1280, 704)))


def test_avoid_union_is_bigger_than_first_frame_alone(tmp_path):
    _, spec = make_spec(tmp_path, camera=CAMS["truck"])
    coords = R._extract_line_coords(LINE)
    one = R._build_avoid_boxes({**spec, "center": [2.7, 50.8]}, coords, (1280, 704))
    many = R._build_avoid_boxes_over_camera(spec, coords, (1280, 704))
    assert len(many) > len(one)


def test_page_has_set_camera_and_flat_moves_only():
    from pathlib import Path
    html = (Path(R.__file__).parent / "page.html").read_text(encoding="utf-8")
    assert "window.setCamera" in html and "window.initScene" in html
    assert "bearing: 0" in html and "pitch: 0" in html
    assert "camera0" in html
