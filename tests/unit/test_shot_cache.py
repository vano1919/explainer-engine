"""The shot cache (docs/CONTRACTS.md, CN-07): one changed byte in anything a render depends on is a new key, nothing else is."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from explainer_engine.core import shot_cache as SC
from explainer_engine.core.errors import ContractError

ROOT = Path(__file__).resolve().parents[2]
SPEC = json.loads((ROOT / "tests" / "fixtures" / "contracts" / "shot_spec" / "valid.json").read_text(encoding="utf-8"))
H = [c * 64 for c in "0123456789abcdef"]


def variant(**change):
    s = copy.deepcopy(SPEC)
    for k, v in change.items():
        s[k] = v
    return s


@pytest.mark.parametrize("field,value", [
    ("prompt", "a tent at dusk"), ("negative", "blur"), ("seed", 8), ("width", 1280), ("height", 704), ("frames", 121), ("fps", 25),
    ("audio_slice_sha256", H[3]), ("blocking_sha256", H[4]), ("recipe", "ltx_i2v/2"), ("params", {"steps": 9, "cfg": 1.0}),
    ("model", {"id": "ltx-2.5", "sha256": H[5], "revision": None}), ("loras", []), ("lane", "DIALOGUE_CU"),
    ("loras", [{"id": "xworld_v2", "sha256": H[6], "weight": 0.8}]), ("loras", [{"id": "xworld_v2", "sha256": H[1], "weight": 0.7}]),
    ("refs", [{"role": "keyframe", "path": "k/s1.png", "sha256": H[7]}]), ("refs", []),
])
def test_every_field_of_the_spec_changes_the_key(field, value):
    assert SC.key(variant(**{field: value})) != SC.key(SPEC)


def test_who_asked_and_where_files_lie_do_not_change_the_key():
    moved = variant(refs=[{"role": "keyframe", "path": "elsewhere/a.png", "sha256": SPEC["refs"][0]["sha256"]}], job_id="job-999", shot_id="s77")
    assert SC.key(moved) == SC.key(SPEC)


def test_the_order_of_references_and_loras_does_not_matter():
    two = variant(refs=[{"role": "a", "path": "p", "sha256": H[1]}, {"role": "b", "path": "q", "sha256": H[2]}],
                  loras=[{"id": "x", "sha256": H[1], "weight": 1.0}, {"id": "y", "sha256": H[2], "weight": 0.5}])
    swapped = copy.deepcopy(two)
    swapped["refs"].reverse()
    swapped["loras"].reverse()
    assert SC.key(two) == SC.key(swapped)


def test_float_noise_below_six_decimals_is_not_a_new_key():
    a = variant(loras=[{"id": "x", "sha256": H[1], "weight": 0.8}])
    b = variant(loras=[{"id": "x", "sha256": H[1], "weight": 0.8 + 1e-9}])
    assert SC.key(a) == SC.key(b)


def test_a_spec_that_breaks_its_contract_has_no_key():
    with pytest.raises(ContractError):
        SC.key(variant(model={"id": "ltx", "sha256": None, "revision": None}))


def test_twelve_shots_editing_one_rerenders_only_that_one(tmp_path):
    cache = SC.ShotCache(tmp_path / "cache")
    specs = [variant(shot_id=f"s{i:02d}", seed=i) for i in range(1, 13)]
    out = tmp_path / "out.mp4"
    out.write_bytes(b"clip")
    for s in specs:
        assert cache.get(s) is None
        cache.put(s, {"clip": out}, job_id="job-001")
    assert all(cache.get(s) for s in specs)
    specs[4] = variant(shot_id="s05", seed=5, prompt="a different tent")  # shot 05 is edited
    assert [cache.get(s) is not None for s in specs] == [True] * 4 + [False] + [True] * 7


def test_a_damaged_output_is_a_miss_never_a_wrong_picture(tmp_path):
    cache = SC.ShotCache(tmp_path / "cache")
    out = tmp_path / "out.mp4"
    out.write_bytes(b"clip")
    entry = cache.put(SPEC, {"clip": out}, job_id="job-001")
    hit = cache.get(SPEC)
    assert hit and Path(hit["dir"], hit["outputs"]["clip"]["path"]).read_bytes() == b"clip"
    Path(entry["dir"], entry["outputs"]["clip"]["path"]).write_bytes(b"torn")
    assert cache.get(SPEC) is None


def test_the_cache_root_follows_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_SHOT_CACHE", str(tmp_path / "env"))
    assert SC.ShotCache().root == tmp_path / "env"
