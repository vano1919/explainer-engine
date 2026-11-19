"""episode/hf_inputs: fetch the listed inputs, hash-checked, never outside the episode folder, no network in the test."""
import hashlib
import json
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import hf_inputs as H


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _manifest(root: Path, files: list[dict]):
    (root / "planning").mkdir(parents=True, exist_ok=True)
    (root / H.DEFAULT_MANIFEST).write_text(json.dumps({"schema": H.SCHEMA, "repo": "r/x", "repo_type": "dataset", "files": files}))


class Fake:
    def __init__(self, content: dict):
        self.content, self.calls = content, []

    def __call__(self, repo, hf_path, repo_type, local_dir):
        self.calls.append(hf_path)
        p = Path(local_dir) / hf_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.content[hf_path])
        return p


def test_fetch_copies_keeps_and_refuses_a_wrong_hash(tmp_path):
    good, bad = b"picture bytes", b"another file"
    _manifest(tmp_path, [{"dest": "assets/a.png", "hf_path": "p/a.png", "sha256": _sha(good)},
                         {"dest": "audio/b.wav", "hf_path": "p/b.wav", "sha256": _sha(b"expected")}])
    dl = Fake({"p/a.png": good, "p/b.wav": bad})
    res = H.fetch(tmp_path, download=dl)
    assert res["fetched"] == ["assets/a.png"] and res["kept"] == []
    assert [r["dest"] for r in res["refused"]] == ["audio/b.wav"] and not (tmp_path / "audio/b.wav").exists()
    assert (tmp_path / "assets/a.png").read_bytes() == good
    res2 = H.fetch(tmp_path, download=dl)                 # the good file is kept, not fetched again
    assert res2["kept"] == ["assets/a.png"] and dl.calls.count("p/a.png") == 1


def test_fetch_only_a_prefix_and_never_outside_the_episode(tmp_path):
    _manifest(tmp_path, [{"dest": "audio/x", "hf_path": "p/x", "sha256": _sha(b"x")},
                         {"dest": "assets/y", "hf_path": "p/y", "sha256": _sha(b"y")}])
    dl = Fake({"p/x": b"x", "p/y": b"y"})
    assert H.fetch(tmp_path, only=["audio/"], download=dl)["fetched"] == ["audio/x"]
    _manifest(tmp_path, [{"dest": "../escape", "hf_path": "p/x", "sha256": _sha(b"x")}])
    with pytest.raises(ContractError):
        H.fetch(tmp_path, download=dl)


def test_add_records_the_hash_and_replaces_a_row(tmp_path):
    dl = Fake({"p/x": b"one"})
    row = H.add(tmp_path, "audio/x", "p/x", download=dl)
    assert row["sha256"] == _sha(b"one")
    dl2 = Fake({"p/x": b"two"})
    H.add(tmp_path, "audio/x", "p/x", download=dl2)
    rows = json.loads((tmp_path / H.DEFAULT_MANIFEST).read_text())["files"]
    assert len(rows) == 1 and rows[0]["sha256"] == _sha(b"two")


def test_the_truce_manifest_is_wellformed_and_names_the_60_second_inputs():
    root = Path(__file__).resolve().parents[2] / "episodes" / "ep_truce_1914"
    doc = H.load_manifest(root)
    dests = [f["dest"] for f in doc["files"]]
    for sid in ("S01_SH001", "S01_SH002", "S01_SH003", "S01_SH004", "S01_SH005", "S02_SH004", "S02_SH005"):
        assert f"assets/generated/images/{sid}_start.png" in dests
    assert {"audio/clock/narration.wav", "audio/clock/timing.json", "audio/clock/narration.scribe.json"} <= set(dests)
    assert all(len(f["sha256"]) == 64 for f in doc["files"])
