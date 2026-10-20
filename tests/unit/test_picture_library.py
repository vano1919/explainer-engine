"""The reusable picture library (D-61): register, find by tags, prompt matches (PP-08), fetch, validate."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from explainer_engine.imagegen import picture_library as PL

ROOT = Path(__file__).resolve().parents[2] / "assets" / "pictures" / "library"


def _png(path: Path, size=(8, 6), colour=(40, 90, 120)):
    Image.new("RGB", size, colour).save(path)
    return path


def _add(tmp_path, name="camp_fire", tags=("fire", "night", "camp"), kind="prop", take=1):
    src = _png(tmp_path / f"src_{name}_{take}.png")
    return PL.add(tmp_path / "lib", file=src, name=name, take=take, kind=kind, tags=list(tags),
                  source={"kind": "gemini", "model": "m", "prompt": "a camp fire at night", "cost_usd_estimate": 0.04},
                  licence={"status": "generated_terms_unverified", "note": "test"})


def test_add_find_and_fetch(tmp_path):
    entry = _add(tmp_path)
    lib = tmp_path / "lib"
    assert entry["id"] == "camp_fire__v1" and (lib / entry["file"]).exists()
    assert [i["id"] for i in PL.find(lib, tags=["fire", "night"])] == ["camp_fire__v1"]
    assert PL.find(lib, tags=["fire", "ocean"]) == []
    assert PL.find(lib, kind="background") == []
    dest = PL.fetch(lib, "camp_fire__v1", tmp_path / "ep", as_name="w_0101.png")
    assert dest.name == "w_0101.png" and dest.read_bytes() == (lib / entry["file"]).read_bytes()
    with pytest.raises(KeyError):
        PL.fetch(lib, "nope__v1", tmp_path / "ep")


def test_find_for_prompt_matches_tag_words(tmp_path):
    _add(tmp_path)
    _add(tmp_path, name="desert_dune", tags=("desert", "sand", "day"))
    lib = tmp_path / "lib"
    hits = PL.find_for_prompt("a small camp fire burning in the night, wide shot", lib)
    assert [h["id"] for h in hits] == ["camp_fire__v1"]
    assert PL.find_for_prompt("a boardroom argument over money", lib) == []


def test_rejected_pictures_are_hidden(tmp_path):
    _add(tmp_path)
    lib = tmp_path / "lib"
    man = PL.load_manifest(lib)
    man["items"][0]["review"]["human"] = "rejected"
    from explainer_engine.core.store import write_json_atomic
    write_json_atomic(lib / "manifest.json", man)
    assert PL.find(lib, tags=["fire"]) == []
    assert PL.find(lib, tags=["fire"], usable=False)


def test_validate_catches_changes_and_strays(tmp_path):
    entry = _add(tmp_path)
    lib = tmp_path / "lib"
    assert PL.validate(lib) == []
    _png(lib / entry["file"], colour=(1, 2, 3))  # changed after registration
    assert any("changed" in p for p in PL.validate(lib))
    _png(lib / "prop" / "stray__v9.png")
    assert any("not in the manifest" in p for p in PL.validate(lib))


def test_committed_manifest_is_valid():
    assert PL.validate(ROOT, check_files=False) == []
