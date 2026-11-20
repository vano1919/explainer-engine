"""Tests for explainer_engine/maps/maplibre_spec.py (G-04b).

Drafted by Gemini Hydrogen (raw copy kept next to this folder), corrected by the tester (Sonnet) 2026-11-20.

Conventions these tests PIN (the brief does not spell them out; the code chat must follow them):
- validate_shot_spec returns a list of problem strings and never raises; a non-dict gives a one-item list; every
  missing required key gets its own problem that contains the key name; independent defects are all reported.
- Types: size = two positive ints, fps and seconds = numbers > 0, center = two numbers, zoom = number,
  line_geojson and font = non-empty str, line_t = two numbers with t0 < t1, counter = dict with from/to/t0/t1 numbers
  (t0 < t1) and label str, date_chip = list of {t: number, text: str}, towns = list of {name: str, lonlat: two numbers,
  t: number}, footnote = str. A bool is never a number. The validator does NOT check that line_geojson exists.
- load_shot_spec accepts str or Path, raises ShotSpecError for malformed JSON and for an invalid spec.
- schedule: an item is "reached" when t >= its time (inclusive): towns_visible keeps spec order; date is the text of
  the last chip with t <= now; counter and line_u are clamped outside their windows; counter is an int. The
  counter's easing curve is NOT pinned (brief silent): only its ends, int type and non-decreasing are tested.
- offline_tile_url returns "file://<absolute dir>/{z}/{x}/{y}.pbf" ("vector") or ".png" ("dem"), ValueError otherwise.
- strip_labels: drops every layer whose type is "symbol" (text and icon), keeps all else, deep copy, no mutation.
"""
import ast
import copy
import inspect
import json
from pathlib import Path

import pytest

import explainer_engine.maps.maplibre_spec as spec_module
from explainer_engine.maps.maplibre_spec import (
    ShotSpecError,
    ease_smoothstep,
    frame_count,
    load_shot_spec,
    offline_tile_url,
    schedule,
    strip_labels,
    validate_shot_spec,
)

REQUIRED_KEYS = [
    "size", "fps", "seconds", "center", "zoom", "line_geojson", "line_t",
    "counter", "date_chip", "towns", "footnote",
]  # font is no longer required: it comes from the film preset (G-06)


def _valid_spec() -> dict:
    return {
        "size": [1280, 704],
        "fps": 24,
        "seconds": 5.0,
        "center": [2.85, 50.80],
        "zoom": 9.5,
        "line_geojson": "assets/front_line.geojson",
        "line_t": [0.4, 3.6],
        "counter": {"from": 0, "to": 100000, "t0": 1.0, "t1": 4.0, "label": "Men at the front (estimate)"},
        "date_chip": [
            {"t": 0.0, "text": "NOV 1914"},
            {"t": 2.2, "text": "DEC 1914"},
        ],
        "towns": [
            {"name": "Nieuport", "lonlat": [2.75, 51.13], "t": 0.5},
            {"name": "Ypres", "lonlat": [2.885, 50.851], "t": 2.0},
            {"name": "Armentieres", "lonlat": [2.881, 50.688], "t": 3.5},
        ],
        "font": "preset",
        "footnote": "Front line illustrative",
    }


def _write(tmp_path: Path, spec, name="shot.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p


# ---------------------------------------------------------------- Must NOT: network, playwright

def test_module_imports_no_network_or_playwright():
    tree = ast.parse(inspect.getsource(spec_module))
    forbidden = {"playwright", "requests", "urllib", "http", "socket", "httpx", "aiohttp"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots = {(node.module or "").split(".")[0]}
        else:
            continue
        assert not (roots & forbidden), f"forbidden import {roots & forbidden}"


# ---------------------------------------------------------------- validate_shot_spec

class TestValidateShotSpec:
    def test_valid_spec_returns_no_problems(self):
        problems = validate_shot_spec(_valid_spec())
        assert problems == []

    def test_problems_are_a_list_of_strings(self):
        spec = _valid_spec()
        del spec["fps"]
        problems = validate_shot_spec(spec)
        assert isinstance(problems, list) and all(isinstance(p, str) and p for p in problems)

    def test_validator_does_not_mutate_the_spec(self):
        spec = _valid_spec()
        snapshot = copy.deepcopy(spec)
        validate_shot_spec(spec)
        assert spec == snapshot

    @pytest.mark.parametrize("bad", [None, [], "spec", 42])
    def test_non_dict_spec_reports_problem(self, bad):
        problems = validate_shot_spec(bad)
        assert isinstance(problems, list) and len(problems) >= 1

    @pytest.mark.parametrize("missing_key", REQUIRED_KEYS)
    def test_missing_required_key_reports_problem(self, missing_key):
        spec = _valid_spec()
        del spec[missing_key]
        problems = validate_shot_spec(spec)
        assert len(problems) >= 1
        assert any(missing_key in p for p in problems)

    def test_every_missing_key_is_reported(self):
        spec = _valid_spec()
        del spec["fps"]
        del spec["footnote"]
        problems = validate_shot_spec(spec)
        assert any("fps" in p for p in problems) and any("footnote" in p for p in problems)

    def test_independent_defects_are_all_reported(self):
        spec = _valid_spec()
        spec["fps"] = 0
        spec["zoom"] = "high"
        assert len(validate_shot_spec(spec)) >= 2

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            ("size", "1280x704"),
            ("size", [1280]),
            ("size", [1280, 704, 3]),
            ("size", [-1280, 704]),
            ("size", [0, 704]),
            ("size", [1280.5, 704]),
            ("size", [True, 704]),
            ("fps", "24"),
            ("fps", 0),
            ("fps", -24),
            ("fps", True),
            ("seconds", "5"),
            ("seconds", 0),
            ("seconds", -2.5),
            ("seconds", False),
            ("center", "2.85,50.8"),
            ("center", [2.85]),
            ("center", [2.85, 50.8, 0]),
            ("center", ["2.85", 50.8]),
            ("zoom", "9.5"),
            ("zoom", True),
            ("line_geojson", 123),
            ("line_geojson", ""),
            ("line_t", "0.4-3.6"),
            ("line_t", [0.4]),
            ("line_t", [3.6, 0.4]),
            ("line_t", [1.0, 1.0]),
            ("line_t", ["0.4", 3.6]),
            ("counter", "0..100000"),
            ("counter", {"from": 0, "to": 100}),
            ("counter", {"from": "0", "to": 100, "t0": 1.0, "t1": 4.0, "label": "X"}),
            ("counter", {"from": 0, "to": "100", "t0": 1.0, "t1": 4.0, "label": "X"}),
            ("counter", {"from": 0, "to": 100, "t0": 4.0, "t1": 1.0, "label": "X"}),
            ("counter", {"from": 0, "to": 100, "t0": 1.0, "t1": 4.0, "label": 123}),
            ("counter", {"from": 0, "to": 100, "t1": 4.0, "label": "X"}),
            ("date_chip", "12 August"),
            ("date_chip", [{"t": "0.0", "text": "Aug"}]),
            ("date_chip", [{"t": 0.0, "text": 1808}]),
            ("date_chip", [{"text": "Aug"}]),
            ("date_chip", [{"t": 0.0}]),
            ("towns", "Ypres"),
            ("towns", [{"name": 123, "lonlat": [2.8, 50.8], "t": 1.0}]),
            ("towns", [{"name": "Ypres", "lonlat": [2.8], "t": 1.0}]),
            ("towns", [{"name": "Ypres", "lonlat": [2.8, 50.8], "t": "1.0"}]),
            ("towns", [{"name": "Ypres", "t": 1.0}]),
            ("font", 123),
            ("font", ""),
            ("footnote", 999),
        ],
    )
    def test_wrong_type_or_invalid_value_reports_problem(self, field, bad_value):
        spec = _valid_spec()
        spec[field] = bad_value
        problems = validate_shot_spec(spec)
        assert len(problems) >= 1

    @pytest.mark.parametrize(
        "field,ok_value",
        [
            ("size", (1920, 1080)),
            ("fps", 30.0),
            ("seconds", 3),
            ("zoom", 7),
            ("center", (2, 50)),
            ("counter", {"from": 0, "to": 100, "t0": 0, "t1": 1, "label": ""}),
            ("footnote", ""),
        ],
    )
    def test_reasonable_variants_are_accepted(self, field, ok_value):
        spec = _valid_spec()
        spec[field] = ok_value
        assert validate_shot_spec(spec) == []


# ---------------------------------------------------------------- load_shot_spec

class TestLoadShotSpec:
    def test_loads_valid_json_spec(self, tmp_path):
        spec = _valid_spec()
        loaded = load_shot_spec(_write(tmp_path, spec))
        assert loaded == spec

    def test_accepts_str_path(self, tmp_path):
        spec = _valid_spec()
        assert load_shot_spec(str(_write(tmp_path, spec))) == spec

    def test_does_not_require_the_geojson_to_exist(self, tmp_path):
        spec = _valid_spec()
        spec["line_geojson"] = "no/such/dir/line.geojson"
        assert load_shot_spec(_write(tmp_path, spec))["line_geojson"] == "no/such/dir/line.geojson"

    def test_raises_shot_spec_error_on_invalid_spec(self, tmp_path):
        bad = _valid_spec()
        del bad["fps"]
        with pytest.raises(ShotSpecError):
            load_shot_spec(_write(tmp_path, bad))

    def test_raises_shot_spec_error_on_malformed_json(self, tmp_path):
        p = tmp_path / "corrupt.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(ShotSpecError):
            load_shot_spec(p)

    def test_shot_spec_error_is_an_exception(self):
        assert issubclass(ShotSpecError, Exception)


# ---------------------------------------------------------------- ease_smoothstep

class TestEaseSmoothstep:
    def test_boundary_and_midpoint_values(self):
        assert ease_smoothstep(0.0) == pytest.approx(0.0)
        assert ease_smoothstep(0.5) == pytest.approx(0.5)
        assert ease_smoothstep(1.0) == pytest.approx(1.0)

    def test_clamps_outside_unit_interval(self):
        for u in (-0.5, -100.0):
            assert ease_smoothstep(u) == pytest.approx(0.0)
        for u in (1.5, 100.0):
            assert ease_smoothstep(u) == pytest.approx(1.0)

    def test_cubic_hermite_polynomial_values(self):
        for u in (0.1, 0.25, 0.35, 0.75, 0.9):
            assert ease_smoothstep(u) == pytest.approx(u * u * (3.0 - 2.0 * u))

    def test_monotonically_nondecreasing(self):
        samples = [ease_smoothstep(i / 100.0) for i in range(-10, 111)]
        assert all(b >= a for a, b in zip(samples, samples[1:]))


# ---------------------------------------------------------------- frame_count and schedule

class TestFrameCountAndSchedule:
    def test_frame_count_is_round_fps_times_seconds(self):
        assert frame_count(_valid_spec()) == 120          # wave-1 shot: 5 s at 24 fps
        s = _valid_spec()
        s["seconds"] = 2.52                                # 60.48 -> 60
        assert frame_count(s) == round(24 * 2.52) == 60
        s["seconds"] = 2.54                                # 60.96 -> 61 (rounds up, not floor)
        assert frame_count(s) == 61
        s["fps"], s["seconds"] = 30, 2.0
        assert frame_count(s) == 60

    def test_schedule_frame_zero_initial_state(self):
        state = schedule(_valid_spec(), 0)
        assert set(state.keys()) >= {"t", "line_u", "counter", "date", "towns_visible"}
        assert state["t"] == pytest.approx(0.0)
        assert state["line_u"] == 0.0
        assert state["counter"] == 0 and type(state["counter"]) is int
        assert state["date"] == "NOV 1914"
        assert state["towns_visible"] == []

    def test_schedule_t_is_frame_over_fps(self):
        spec = _valid_spec()
        spec["fps"] = 30
        assert schedule(spec, 45)["t"] == pytest.approx(1.5)
        assert schedule(spec, 3)["t"] == pytest.approx(0.1)

    def test_schedule_line_smoothstep_progression(self):
        spec = _valid_spec()  # line_t = [0.4, 3.6], fps = 24

        # frame 9 -> t = 0.375 s, before the line starts
        assert schedule(spec, 9)["line_u"] == pytest.approx(0.0)

        # frame 12 -> t = 0.5 s, shortly after the start
        s12 = schedule(spec, 12)
        assert s12["t"] == pytest.approx(0.5)
        assert s12["line_u"] == pytest.approx(ease_smoothstep((0.5 - 0.4) / (3.6 - 0.4)))
        assert 0.0 < s12["line_u"] < 0.05

        # frame 48 -> t = 2.0 s = midpoint of [0.4, 3.6]
        assert schedule(spec, 48)["line_u"] == pytest.approx(0.5)

        # frame 72 -> t = 3.0 s, three quarters of the way in time (smoothstep(0.8125))
        assert schedule(spec, 72)["line_u"] == pytest.approx(ease_smoothstep((3.0 - 0.4) / 3.2))

        # frame 87 -> t = 3.625 s, after the end; stays at 1.0
        assert schedule(spec, 87)["line_u"] == pytest.approx(1.0)
        assert schedule(spec, 119)["line_u"] == pytest.approx(1.0)

    def test_schedule_line_u_is_nondecreasing_and_within_unit_interval(self):
        spec = _valid_spec()
        us = [schedule(spec, f)["line_u"] for f in range(frame_count(spec))]
        assert all(0.0 <= u <= 1.0 for u in us)
        assert all(b >= a for a, b in zip(us, us[1:]))
        assert us[0] == 0.0 and us[-1] == 1.0

    def test_schedule_counter_integers_and_nondecreasing(self):
        spec = _valid_spec()  # counter 0 -> 100000 from 1.0 s to 4.0 s
        counts = []
        for f in range(frame_count(spec)):
            c = schedule(spec, f)["counter"]
            assert type(c) is int
            counts.append(c)
        assert counts[0] == 0
        assert counts[23] == 0                              # t = 0.958 s, before the window
        assert counts[24] == 0                              # t = 1.0 s
        assert 0 < counts[60] < 100000                      # t = 2.5 s, inside the window
        assert counts[96] == 100000                         # t = 4.0 s
        assert counts[-1] == 100000
        assert all(b >= a for a, b in zip(counts, counts[1:]))

    def test_schedule_counter_uses_from_and_to(self):
        spec = _valid_spec()
        spec["counter"] = {"from": 500, "to": 2500, "t0": 1.0, "t1": 4.0, "label": "X"}
        assert schedule(spec, 0)["counter"] == 500
        assert schedule(spec, 96)["counter"] == 2500
        assert schedule(spec, 119)["counter"] == 2500
        assert 500 < schedule(spec, 60)["counter"] < 2500

    def test_schedule_date_chip_switches_at_threshold(self):
        spec = _valid_spec()  # switches at t = 2.2 s
        assert schedule(spec, 52)["date"] == "NOV 1914"       # t = 2.1667 s
        assert schedule(spec, 53)["date"] == "DEC 1914"       # t = 2.2083 s
        assert schedule(spec, 119)["date"] == "DEC 1914"

    def test_schedule_date_chip_with_three_steps(self):
        spec = _valid_spec()
        spec["date_chip"] = [{"t": 0.0, "text": "A"}, {"t": 1.0, "text": "B"}, {"t": 3.0, "text": "C"}]
        assert [schedule(spec, f)["date"] for f in (0, 23, 24, 71, 72, 119)] == ["A", "A", "B", "B", "C", "C"]

    def test_schedule_towns_appear_at_their_timestamps(self):
        spec = _valid_spec()  # towns at t = 0.5 (frame 12), 2.0 (frame 48), 3.5 (frame 84)
        assert schedule(spec, 11)["towns_visible"] == []
        assert schedule(spec, 12)["towns_visible"] == ["Nieuport"]
        assert schedule(spec, 47)["towns_visible"] == ["Nieuport"]
        assert schedule(spec, 48)["towns_visible"] == ["Nieuport", "Ypres"]
        assert schedule(spec, 83)["towns_visible"] == ["Nieuport", "Ypres"]
        assert schedule(spec, 84)["towns_visible"] == ["Nieuport", "Ypres", "Armentieres"]
        assert schedule(spec, 119)["towns_visible"] == ["Nieuport", "Ypres", "Armentieres"]

    def test_schedule_does_not_mutate_the_spec(self):
        spec = _valid_spec()
        snapshot = copy.deepcopy(spec)
        for f in (0, 12, 60, 119):
            schedule(spec, f)
        assert spec == snapshot


# ---------------------------------------------------------------- strip_labels

class TestStripLabels:
    @staticmethod
    def _style():
        return {
            "version": 8,
            "name": "HistoricalBase",
            "sources": {"terrain": {"type": "raster"}},
            "layers": [
                {"id": "background", "type": "background", "paint": {"background-color": "#f4efe6"}},
                {"id": "place-labels", "type": "symbol", "layout": {"text-field": "{name}"}},
                {"id": "rivers", "type": "line", "source": "terrain"},
                {"id": "road-shields", "type": "symbol", "layout": {"icon-image": "shield"}},
                {"id": "hills", "type": "hillshade", "source": "terrain"},
            ],
        }

    def test_removes_symbol_layers_and_preserves_others(self):
        style = self._style()
        snapshot = copy.deepcopy(style)

        cleaned = strip_labels(style)

        assert style == snapshot                       # input never mutated
        assert len(style["layers"]) == 5
        assert cleaned is not style
        assert cleaned["layers"] is not style["layers"]
        assert [layer["id"] for layer in cleaned["layers"]] == ["background", "rivers", "hills"]
        assert all(layer["type"] != "symbol" for layer in cleaned["layers"])
        # everything else is carried over unchanged
        assert cleaned["version"] == 8 and cleaned["name"] == "HistoricalBase"
        assert cleaned["sources"] == style["sources"]
        assert cleaned["layers"][0] == style["layers"][0]

    def test_result_is_a_deep_copy(self):
        style = self._style()
        cleaned = strip_labels(style)
        cleaned["sources"]["terrain"]["type"] = "vector"
        cleaned["layers"][0]["paint"]["background-color"] = "#000000"
        assert style["sources"]["terrain"]["type"] == "raster"
        assert style["layers"][0]["paint"]["background-color"] == "#f4efe6"

    def test_style_without_symbol_layers_is_returned_as_an_equal_copy(self):
        style = self._style()
        style["layers"] = [layer for layer in style["layers"] if layer["type"] != "symbol"]
        cleaned = strip_labels(style)
        assert cleaned == style and cleaned is not style

    def test_style_with_only_symbol_layers_ends_with_no_layers(self):
        style = self._style()
        style["layers"] = [layer for layer in style["layers"] if layer["type"] == "symbol"]
        assert strip_labels(style)["layers"] == []


# ---------------------------------------------------------------- offline_tile_url

PBF_TAIL = "/{z}/{x}/{y}.pbf"
PNG_TAIL = "/{z}/{x}/{y}.png"


def _middle(url: str, tail: str) -> Path:
    assert url.startswith("file://")
    assert url.endswith(tail)
    return Path(url[len("file://"):-len(tail)])


class TestOfflineTileUrl:
    def test_vector_url_is_absolute_pbf_template(self, tmp_path):
        tile_dir = tmp_path / "tiles" / "vector"
        tile_dir.mkdir(parents=True)
        mid = _middle(offline_tile_url(str(tile_dir), "vector"), PBF_TAIL)
        assert mid.is_absolute()
        assert mid.resolve() == tile_dir.resolve()

    def test_dem_url_is_absolute_png_template_and_relative_dir_is_made_absolute(self, tmp_path, monkeypatch):
        dem_dir = tmp_path / "tiles" / "dem"
        dem_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        mid = _middle(offline_tile_url("tiles/dem", "dem"), PNG_TAIL)
        assert mid.is_absolute()
        assert mid.resolve() == dem_dir.resolve()

    def test_kinds_differ_only_in_extension(self, tmp_path):
        v = offline_tile_url(str(tmp_path), "vector")
        d = offline_tile_url(str(tmp_path), "dem")
        assert v.endswith(".pbf") and d.endswith(".png")
        assert v[: -len(".pbf")] == d[: -len(".png")]

    def test_no_network_scheme_and_placeholders_kept_literal(self, tmp_path):
        url = offline_tile_url(str(tmp_path), "vector")
        assert not url.startswith(("http://", "https://"))
        assert "{z}" in url and "{x}" in url and "{y}" in url

    def test_invalid_kind_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError):
            offline_tile_url(str(tmp_path), "raster")
