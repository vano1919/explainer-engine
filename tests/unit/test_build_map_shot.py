"""build_shot's map lane: kind=map is handed to the maplibre lane with the tile dir; the traced 1914 front is sane and its spec is valid."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from explainer_engine.maps import maplibre_spec as MS
from explainer_engine.maps import trace_front_1914 as TR
from explainer_engine.production import build_map_shot as BM

EX = Path(__file__).resolve().parents[2] / "examples" / "maps" / "truce_front_1914"


def test_tiles_are_required(tmp_path, monkeypatch):
    monkeypatch.delenv("EXPLAINER_MAP_TILES", raising=False)
    with pytest.raises(ValueError):
        BM.build(tmp_path / "s.json", tmp_path / "o.mp4")


def test_the_lane_gets_spec_tiles_and_a_workdir(tmp_path, monkeypatch):
    from explainer_engine.maps.maplibre_lane import render
    seen = {}
    monkeypatch.setattr(render, "render_shot", lambda spec, out, tiles, work: seen.update(spec=spec, tiles=tiles, work=work) or {"frames": 3})
    log = BM.build(tmp_path / "s.json", tmp_path / "o.mp4", tile_dir=tmp_path / "t")
    assert seen["tiles"].endswith("t") and Path(seen["spec"]).name == "s.json" and log["render"] == {"frames": 3}
    assert (tmp_path / "o.render_log.json").exists() and not Path(seen["work"]).exists()      # temp workdir is cleaned


def test_traced_front_is_sane():
    gj = TR.geojson()
    props = gj["features"][0]["properties"]
    coords = gj["features"][0]["geometry"]["coordinates"]
    assert props["fit_rms_km"] < 15 and "no claim" in props["status"]
    assert 2.5 < coords[0][0] < 3.2 and 51.0 < coords[0][1] < 51.4        # Nieuport on the coast
    assert 7.0 < coords[-1][0] < 7.8 and 47.3 < coords[-1][1] < 47.8      # Swiss border
    assert [c[1] for c in coords][0] > [c[1] for c in coords][-1]          # north to south
    assert json.loads((EX / "front.geojson").read_text())["features"][0]["geometry"]["coordinates"] == coords


def test_the_example_map_spec_is_valid_and_uses_a_listed_move():
    spec = json.loads((EX / "spec.json").read_text())
    assert spec["camera"]["move"] in MS.ALLOWED_CAMERA_MOVES
    probs = MS.validate_shot_spec({k: v for k, v in spec.items() if k != "kind"})
    assert probs == [], probs
