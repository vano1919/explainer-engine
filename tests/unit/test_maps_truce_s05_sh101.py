"""The sourced Truce counter shot: estimate label, no unsourced geometry, valid spec."""
import json
from pathlib import Path

from explainer_engine.maps.maplibre_spec import load_shot_spec

DIR = Path(__file__).resolve().parents[2] / "examples" / "maps" / "truce_S05_SH101"


def test_spec_is_valid_and_uses_the_film_file():
    spec = load_shot_spec(DIR / "spec.json")
    assert spec["film_file"] == "episode_film.json" and spec["font"] == "preset"
    assert spec["camera"]["move"] == "zoom_in"


def test_counter_is_the_c03_estimate_and_visible_to_the_end():
    spec = json.loads((DIR / "spec.json").read_text(encoding="utf-8"))
    c = spec["counter"]
    assert c["to"] == 100000 and c["from"] == 0
    assert "estimate" in c["label"].lower()
    assert 0 <= c["t0"] < c["t1"] <= spec["seconds"]


def test_no_unsourced_geometry():
    spec = json.loads((DIR / "spec.json").read_text(encoding="utf-8"))
    assert spec["towns"] == []
    assert json.loads((DIR / spec["line_geojson"]).read_text(encoding="utf-8"))["features"] == []
