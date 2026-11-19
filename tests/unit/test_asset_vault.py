"""W3: the asset vault keeps one untouched original per picture/clip with a hash and a record. No network, no media."""
from __future__ import annotations

import csv
import json
import os

import pytest
from PIL import Image

from explainer_engine import vault as D73
from explainer_engine.core.errors import ContractError
from explainer_engine.imagegen import turn_pack as T
from explainer_engine.imagegen import vault as AV

EP = "ep_t"


def _file(p, data=b"bytes-one"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def _ing(tmp_path, src, **kw):
    return AV.ingest(src, EP, kw.pop("shot", "S01_SH001"), kw.pop("kind", "image_start"), "gemini_chat_image", None,
                     "a prompt", ["ref.png"], 7, {"k": 1}, 0.0, root=tmp_path, **kw)


def test_ingest_is_byte_identical_read_only_and_recorded(tmp_path):
    src = _file(tmp_path / "in" / "a.png", bytes(range(256)) * 50)
    rec = _ing(tmp_path, src)
    dest = tmp_path / rec["path"]
    assert dest.read_bytes() == src.read_bytes() and rec["sha256"] == AV.sha256_file(src)
    assert rec["path"] == f"assets/originals/{EP}/S01_SH001_image_start_v1.png" and rec["version"] == 1 and rec["parent"] is None
    assert dest.stat().st_mode & 0o222 == 0
    assert AV.get(rec["asset_id"], EP, tmp_path) == rec and AV.latest(EP, "S01_SH001", "image_start", tmp_path) == rec
    assert rec["prompt_hash"] == AV.prompt_hash("a prompt") and rec["observation_record_id"] is None
    assert AV.verify(EP, root=tmp_path) == []


def test_reingest_of_identical_bytes_returns_the_same_record(tmp_path):
    src = _file(tmp_path / "in" / "a.png")
    a, b = _ing(tmp_path, src), _ing(tmp_path, _file(tmp_path / "other" / "copy.png"))
    assert a == b and len(AV.load(EP, tmp_path)) == 1


def test_new_bytes_are_the_next_version_with_a_parent_chain(tmp_path):
    a = _ing(tmp_path, _file(tmp_path / "in" / "a.png", b"one"))
    b = _ing(tmp_path, _file(tmp_path / "in" / "b.png", b"two"))
    c = _ing(tmp_path, _file(tmp_path / "in" / "c.png", b"three"))
    assert (b["version"], b["parent"]) == (2, a["asset_id"]) and (c["version"], c["parent"]) == (3, b["asset_id"])
    assert (tmp_path / a["path"]).read_bytes() == b"one"          # the first original is untouched
    assert AV.latest(EP, "S01_SH001", "image_start", tmp_path)["asset_id"] == c["asset_id"]


def test_an_existing_original_is_never_overwritten(tmp_path):
    src = _file(tmp_path / "in" / "a.png", b"one")
    _file(tmp_path / f"assets/originals/{EP}/S01_SH001_image_start_v1.png", b"precious")
    with pytest.raises(ContractError, match="never overwritten"):
        _ing(tmp_path, src)
    assert (tmp_path / f"assets/originals/{EP}/S01_SH001_image_start_v1.png").read_bytes() == b"precious"


def test_verify_reports_a_changed_or_missing_original(tmp_path):
    rec = _ing(tmp_path, _file(tmp_path / "in" / "a.png"))
    dest = tmp_path / rec["path"]
    os.chmod(dest, 0o644)
    dest.write_bytes(b"tampered")
    assert any(p.startswith("CHANGED") for p in AV.verify(EP, root=tmp_path))
    dest.unlink()
    assert any(p.startswith("MISSING") for p in AV.verify(EP, root=tmp_path))


def test_verify_checks_the_hf_copy_with_the_d73_lfs_hash(tmp_path):
    rec = _ing(tmp_path, _file(tmp_path / "in" / "a.png"))
    # the same record also on HF: a stubbed D-73 listing (what vault.remote_files returns), no network
    p = AV.records_path(EP, tmp_path)
    row = dict(rec, hf_path="x/a.png")
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    listing = {"x/a.png": {"size": rec["size"], "sha256": rec["sha256"], "blob": "b"}}
    assert AV.verify(EP, root=tmp_path, files=listing) == []
    assert AV.verify(EP, root=tmp_path, files={"x/a.png": dict(listing["x/a.png"], sha256="0" * 64)})[0].startswith("DIFFERS ON HF")
    assert AV.verify(EP, root=tmp_path, files={})[0].startswith("NOT ON HF")


def test_remote_listing_goes_through_the_d73_functions(monkeypatch):
    seen = {}
    monkeypatch.setattr(D73, "remote_files", lambda repo, prefix="", **kw: seen.update(repo=repo, prefix=prefix) or {})
    AV.remote_listing("p/")
    assert seen == {"repo": D73.config()["primary"], "prefix": "p/"}


def test_migration_records_hf_assets_without_bytes_and_lists_the_missing(tmp_path):
    inv = tmp_path / "inv.csv"
    base = "https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/"
    cols = ["asset_id", "category", "subtype", "path", "hf_location", "route", "source_kind"]
    rows = [["pic:S01_SH001_start", "start_photo", "png", "a.png", base + "pics/a.png", "still_25d", "gemini_chat_image"],
            ["ltx_raw:S01_SH002", "ltx_clip", "raw", "r.mp4", base + "raw/r.mp4", "video", "ltx"],
            ["ltx_cut:S01_SH002", "ltx_clip", "cut", "c.mp4", "", "video", "ltx"],
            ["clip:S01_SH001", "rendered_clip", "still_25d", "k.mp4", "", "still_25d", "directed25d"]]
    with open(inv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    files = {"pics/a.png": {"size": 5, "sha256": "a" * 64, "blob": "x"}, "raw/r.mp4": {"size": 9, "sha256": "b" * 64, "blob": "y"}}
    out = AV.migrate_inventory(EP, inv, files, root=tmp_path)
    assert len(out["recorded"]) == 2 and [m["asset_id"] for m in out["missing"]] == ["ltx_cut:S01_SH002", "clip:S01_SH001"]
    again = AV.migrate_inventory(EP, inv, files, root=tmp_path)
    assert again["recorded"] == [] and len(again["already"]) == 2
    assert {r["type"] for r in AV.load(EP, tmp_path)} == {"image_start", "clip_raw"}
    assert AV.verify(EP, root=tmp_path, files=files) == []


def test_turn_pack_promote_ingests_the_chat_picture_and_its_master(tmp_path):
    import numpy as np
    root = tmp_path / "episodes" / EP
    (root / "assets" / "generated").mkdir(parents=True)
    pic = root / "assets/generated/images/S1_SH1_start.png"
    pic.parent.mkdir(parents=True)
    Image.fromarray(np.random.default_rng(1).integers(0, 255, (788, 1400, 3), dtype=np.uint8)).save(pic)
    man = {"episode_id": EP, "image_native_min_long_side": 1376, "image_min_long_side": 2752}
    (root / "episode.json").write_text(json.dumps(man))
    (root / "story").mkdir()
    (root / "story" / "production_script.json").write_text(json.dumps({"schema_version": "4.0.0", "episode_id": EP}))
    T._append(root, {"id": "S1_SH1_start", "file": str(pic.relative_to(root)), "sha256": T.sha256(pic), "status": "accepted",
                     "grade": "draft", "gates": [], "at": T.now()})

    def double(src, dst):
        with Image.open(src) as im:
            im.resize((im.size[0] * 2, im.size[1] * 2)).save(dst)

    T.promote(root, upscaler=double)
    rows = AV.load(EP, tmp_path)
    assert {r["type"] for r in rows} == {"image_start", "master_start"}
    pic_rec = next(r for r in rows if r["type"] == "image_start")
    assert pic_rec["sha256"] == T.sha256(pic) and AV.verify(EP, root=tmp_path) == []
