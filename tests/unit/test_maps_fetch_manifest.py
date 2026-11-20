"""fetch_tiles: a second fetch into the same folder adds to manifest.json instead of overwriting it (G-04c finding)."""
from __future__ import annotations
import json
from explainer_engine.maps.maplibre_lane import fetch_tiles as F


def _fake(monkeypatch):
    monkeypatch.setattr(F, "_download_tile", lambda url, dest, timeout=30.0: (3, "sha"))
    monkeypatch.setattr(F, "resolve_vector_template", lambda timeout=30.0: "https://x/{z}/{x}/{y}.pbf")


def test_second_fetch_keeps_earlier_tiles_and_widens_bbox(tmp_path, monkeypatch):
    _fake(monkeypatch)
    F.fetch_tiles((0.0, 0.0, 1.0, 1.0), tmp_path, min_zoom=3, max_zoom=3, dem_max_zoom=3, delay_sec=0)
    first = json.loads((tmp_path / "manifest.json").read_text())
    F.fetch_tiles((10.0, 10.0, 11.0, 11.0), tmp_path, min_zoom=4, max_zoom=4, dem_max_zoom=4, delay_sec=0)
    second = json.loads((tmp_path / "manifest.json").read_text())
    assert second["tile_count"] > first["tile_count"]
    assert {t["z"] for t in second["tiles"]} == {3, 4}
    assert second["bbox"] == [0.0, 0.0, 11.0, 11.0]
    assert (second["min_zoom"], second["max_zoom"]) == (3, 4)


def test_same_tile_is_not_listed_twice(tmp_path, monkeypatch):
    _fake(monkeypatch)
    for _ in range(2):
        F.fetch_tiles((0.0, 0.0, 1.0, 1.0), tmp_path, min_zoom=3, max_zoom=3, dem_max_zoom=3, delay_sec=0)
    tiles = json.loads((tmp_path / "manifest.json").read_text())["tiles"]
    keys = [(t["kind"], t["z"], t["x"], t["y"]) for t in tiles]
    assert len(keys) == len(set(keys))


def test_foreign_manifest_is_replaced_not_merged(tmp_path, monkeypatch):
    _fake(monkeypatch)
    (tmp_path / "manifest.json").write_text('{"schema": "other", "tiles": [1]}')
    F.fetch_tiles((0.0, 0.0, 1.0, 1.0), tmp_path, min_zoom=3, max_zoom=3, dem_max_zoom=3, delay_sec=0)
    assert json.loads((tmp_path / "manifest.json").read_text())["schema"] == "explainer_engine.offline_tiles.v1"
