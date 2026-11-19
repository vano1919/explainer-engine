"""production/layers_run: the command that makes the scene layers the runner only reads (fakes for the models)."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ConfigError
from explainer_engine.production import layers_run as L

ROOT = Path(__file__).resolve().parents[2]


def _episode(tmp_path, specs):
    (tmp_path / "planning").mkdir()
    (tmp_path / "planning" / "layer_specs.json").write_text(json.dumps({"schema": "layer_specs/1", "shots": specs}))
    pic = tmp_path / "assets" / "generated" / "masters" / "S01_SH004_start.png"
    pic.parent.mkdir(parents=True)
    Image.fromarray(np.zeros((90, 160, 3), np.uint8)).save(pic)
    (tmp_path / "production").mkdir()
    (tmp_path / "production" / "pictures.json").write_text(json.dumps({"pictures": {"S01_SH004_start": {
        "file": "assets/generated/masters/S01_SH004_start.png"}}}))
    return tmp_path


def _hit(conf, box):
    return {"confidence": conf, "bbox": box, "centroid": [(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]}


def test_a_found_phrase_becomes_a_sam_point_and_the_light_is_kept(tmp_path):
    root = _episode(tmp_path, {"S01_SH004": {"q": {"wire": "barbed wire"}, "lights": [
        {"id": "sun", "kind": "sun", "point": [0.5, 0.27], "radius": 0.03}]}})
    got = {}

    def understand(pic, seen, force=False):
        got["seen"], got["pic"] = seen, pic
        return {"picture_sha256": "abc"}

    detect = lambda rgb, qs: [_hit(0.4, [0.1, 0.1, 0.3, 0.3]), _hit(0.9, [0.5, 0.5, 0.7, 0.7]), _hit(0.8, [0, 0, 1, 1])]
    rows = L.build(root, ["S01_SH004"], understand=understand, detect=detect)
    assert rows[0]["status"] == "made" and rows[0]["picture_sha256"] == "abc"
    ids = [o["id"] for o in got["seen"]["objects"]]
    assert ids == ["wire", "wire_2"]                       # the whole-picture box is dropped, the best two kept, best first
    assert got["seen"]["objects"][0]["points"] == [[0.6, 0.6]]
    assert got["seen"]["lights"][0]["id"] == "sun" and got["pic"].name == "S01_SH004_start.png"


def test_a_detector_that_finds_nothing_is_an_error_row_not_a_silent_pass(tmp_path):
    root = _episode(tmp_path, {"S01_SH004": {"q": {"wire": "barbed wire"}, "lights": []}})
    rows = L.build(root, ["S01_SH004"], understand=lambda *a, **k: pytest.fail("must not run"), detect=lambda r, q: [])
    assert rows[0]["status"] == "error" and rows[0]["phrases"][0]["found"] == 0


def test_a_shot_without_a_spec_is_a_row(tmp_path):
    root = _episode(tmp_path, {})
    assert L.build(root, ["S01_SH004"], understand=None, detect=None)[0]["status"] == "no_spec"


def test_missing_pictures_record_or_specs_file_say_what_to_do_first(tmp_path):
    with pytest.raises(ConfigError, match="layer_specs"):
        L.load_specs(tmp_path)
    (tmp_path / "planning").mkdir()
    (tmp_path / "planning" / "layer_specs.json").write_text(json.dumps({"schema": "layer_specs/1", "shots": {"A": {}}}))
    with pytest.raises(ConfigError, match="pictures stage"):
        L.picture_of(tmp_path, "A")


def test_fetch_models_names_the_folders_understand_reads(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPLAINER_MODELS_DIR", str(tmp_path))
    calls = []
    out = L.fetch_models(["lama", "sam21"], download=lambda repo, local_dir, allow_patterns: calls.append((repo, local_dir, allow_patterns)))
    assert calls[0] == ("Carve/LaMa-ONNX", str(tmp_path / "Carve__LaMa-ONNX"), ["lama_fp32.onnx"])
    assert calls[1][2] is None and set(out) == {"lama", "sam21"}
    with pytest.raises(ConfigError):
        L.fetch_models(["nope"], download=lambda **k: None)


def test_the_truce_specs_cover_the_five_stills_of_the_first_minute():
    specs = L.load_specs(ROOT / "episodes" / "ep_truce_1914")
    assert {"S01_SH001", "S01_SH004", "S01_SH005", "S02_SH004", "S02_SH005"} <= set(specs)
    assert all(li["kind"] in ("fire", "candle", "glow", "sun") for s in specs.values() for li in s["lights"])
