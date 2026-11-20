"""Label-only Truce map shots: valid specs, no counter, no line, no unsourced place names."""
import json
from pathlib import Path

import pytest

from explainer_engine.maps.maplibre_spec import load_shot_spec, schedule

DIR = Path(__file__).resolve().parents[2] / "examples" / "maps" / "truce_labels"
SHOTS = ["S02_SH101", "S02_SH103", "S05_SH001"]
ALLOWED_TEXT = {
    "S02_SH101": {"August 1914"},
    "S02_SH103": {"Flanders: in places about 50 yards apart, elsewhere up to about 300"},
    "S05_SH001": {"Christmas 1914", "Unofficial truce, in patches"},
}


@pytest.mark.parametrize("shot", SHOTS)
def test_spec_valid_without_counter(shot):
    spec = load_shot_spec(DIR / f"{shot}.json")
    assert spec["counter"] is None
    assert schedule(spec, 10)["counter"] is None


@pytest.mark.parametrize("shot", SHOTS)
def test_no_line_and_only_sourced_text(shot):
    spec = json.loads((DIR / f"{shot}.json").read_text(encoding="utf-8"))
    assert json.loads((DIR / spec["line_geojson"]).read_text(encoding="utf-8"))["features"] == []
    texts = {c["text"] for c in spec["date_chip"]} | {t["name"] for t in spec["towns"]}
    assert texts == ALLOWED_TEXT[shot]


@pytest.mark.parametrize("shot", SHOTS)
def test_camera_is_one_of_the_five_moves(shot):
    spec = json.loads((DIR / f"{shot}.json").read_text(encoding="utf-8"))
    assert spec["camera"]["move"] == "zoom_in"
