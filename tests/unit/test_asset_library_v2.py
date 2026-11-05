"""asset_library/2 (D-110, roadmap 9.3 and 21.4-21.5, ICW-05): the 3D kinds in the one library, deps by hash, git or external
storage at 5 MB, the licence record of a third-party source, unknown commercial use blocking approval, skeleton search."""
import json

import pytest
from PIL import Image

from explainer_engine import assets_reuse as AR
from explainer_engine.assets import library as L
from explainer_engine.core import contracts as C


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "body.glb").write_bytes(b"glTF" + b"\x01" * 60)
    (tmp_path / "in" / "rig.blend").write_bytes(b"BLENDER" + b"\x02" * 60)
    (tmp_path / "in" / "walk.fbx").write_bytes(b"Kaydara FBX" + b"\x03" * 60)
    Image.new("RGB", (16, 16), (90, 60, 30)).save(tmp_path / "in" / "skin.png")
    return tmp_path


def lic(key="quaternius_ubc"):
    return L.licence_from_source(key, url="https://example.org/pack", version="1.0")


def model(repo, lib, asset_id="model.ubc_body_a", **kw):
    kw.setdefault("three_d", {"skeleton_id": "skeleton.ubc_humanoid_v1", "rig_profile": "ubc_humanoid", "poly_count": 13000})
    return L.make_record(asset_id, "model", "in/body.glb", repo=repo, tags=["hero", "body"], bible_version="1.5", licence=lic(),
                         made_with={"provider": "third_party"}, lib=lib, **kw)


def test_the_committed_library_is_v2_and_clean_under_cn19():
    lib = L.load()
    assert lib["schema"] == L.SCHEMA and C.errors(lib) == [] and L.verify() == []


def test_a_v1_document_upgrades_with_git_storage_and_commercial_use_by_definition():
    v1 = {"schema": "asset_library/1", "items": [json.loads(json.dumps(i)) for i in L.load()["items"]]}
    for it in v1["items"]:
        it.pop("deps"), it.pop("storage"), it["licence"].pop("commercial_use")
    v2 = L.upgrade(v1)
    assert v2["schema"] == "asset_library/2" and C.errors(v2) == []
    assert {i["licence"]["commercial_use"] for i in v2["items"]} == {"unknown"}  # Gemini terms never verified
    own = {"schema": "asset_library/1", "items": [dict(v1["items"][0], licence={"status": "own_drawn", "note": "drawn"})]}
    assert L.upgrade(own)["items"][0]["licence"]["commercial_use"] == "yes"
    assert L.upgrade(v2) is v2


def test_3d_kinds_need_their_block_and_the_up_axis_is_read_not_guessed(repo):
    lib = {"schema": L.SCHEMA, "items": []}
    r = model(repo, lib)
    assert r["three_d"]["format"] == "glb" and r["three_d"]["up_axis"] == "Y" and r["three_d"]["units"] == "m"
    with pytest.raises(ValueError, match="three_d"):
        L.make_record("rig.ubc", "rig", "in/rig.blend", repo=repo, tags=["rig"], bible_version="1.5", licence=lic())
    with pytest.raises(ValueError, match="up axis"):  # FBX does not fix its axis: the importer must say
        L.make_record("animation.walk", "animation", "in/walk.fbx", repo=repo, tags=["walk"], bible_version="1.5", licence=lic(),
                      three_d={"skeleton_id": "skeleton.ubc_humanoid_v1"})
    rig = L.make_record("rig.ubc", "rig", "in/rig.blend", repo=repo, tags=["rig"], bible_version="1.5", licence=lic(),
                        three_d={"skeleton_id": "skeleton.ubc_humanoid_v1", "rig_profile": "ubc_humanoid"})
    assert rig["three_d"]["up_axis"] == "Z"
    sc = L.make_record("scene_template.council_hall", "scene_template", "in/rig.blend", repo=repo, tags=["hall"],
                       bible_version="1.5", licence=lic("polyhaven"), three_d={})
    lib["items"] = [sc]
    L.validate(lib)  # an underscore kind is a valid id prefix


def test_deps_are_hashed_from_the_library_and_cn19_catches_a_stale_one(repo):
    path = repo / "lib.json"
    tex = L.make_record("texture.skin", "texture", "in/skin.png", repo=repo, tags=["skin"], bible_version="1.5", licence=lic("ambientcg"))
    L.register(tex, path=path)
    body = model(repo, L.load(path), deps=["texture.skin"])
    assert body["deps"] == [{"asset_id": "texture.skin", "sha256": tex["sha256"]}]
    L.register(body, path=path)
    lib = L.load(path)
    L.get("model.ubc_body_a", lib=lib)["deps"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="CN-19.*re-link"):
        L.validate(lib)
    assert any("re-link" in p for p in L.verify(lib=lib, repo=repo, versions=["1.5"]))


def test_a_third_party_licence_records_its_page_version_and_date(repo):
    r = model(repo, None)
    assert r["licence"]["status"] == "cc0" and r["licence"]["commercial_use"] == "yes"
    assert r["licence"]["source_url"] == "https://example.org/pack" and r["licence"]["inspected_on"] == "2026-11-05"
    assert "check this pack's own page" in r["licence"]["note"]
    lib = {"schema": L.SCHEMA, "items": [r]}
    r["licence"]["revision_or_version"] = None
    with pytest.raises(ValueError, match="revision_or_version"):
        L.validate(lib)
    with pytest.raises(KeyError, match="no licence row"):
        L.licence_from_source("somewhere")
    assert L.licence_from_source("hunyuan3d_2_1", version="2.1")["commercial_use"] == "no"


def test_every_source_row_fits_the_schema_enums():
    schema = json.loads(L.SCHEMA_PATH.read_text(encoding="utf-8"))
    lic = schema["$defs"]["v2"]["properties"]["items"]["items"]["properties"]["licence"]["properties"]
    for key, row in L.sources().items():
        assert row["status"] in lic["status"]["enum"] and row["commercial_use"] in lic["commercial_use"]["enum"], key
        assert row["source_url"].startswith("https://") and row["evidence"], key


def test_unknown_commercial_use_blocks_approval_until_the_approver_answers(repo):
    path = repo / "lib.json"
    r = L.make_record("texture.paper", "texture", "in/skin.png", repo=repo, tags=["paper"], bible_version="1.5")
    assert r["licence"]["commercial_use"] == "unknown"
    L.register(r, path=path)
    with pytest.raises(ValueError, match="commercial use is unknown"):
        L.approve("texture.paper", "ვანო", path=path)
    assert L.approve("texture.paper", "ვანო", status="rejected", path=path)["approval"]["status"] == "rejected"  # no answer needed
    rec = L.approve("texture.paper", "ვანო", commercial_use="yes", path=path, at="2026-11-05T13:00:00")
    assert rec["approval"]["status"] == "approved" and rec["licence"]["commercial_use"] == "yes"
    assert "commercial use yes per ვანო (2026-11-05T13:00:00)" in rec["licence"]["note"]


def test_storage_is_git_up_to_5_mb_and_external_in_the_cache_above(repo, monkeypatch):
    path = repo / "lib.json"
    small, _ = L.ingest(repo / "in" / "skin.png", "texture.skin", "texture", path=path, repo=repo, tags=["skin"],
                        bible_version="1.5", licence=lic("ambientcg"))
    assert small["storage"] == {"location": "git", "external_path": None} and small["file"] == "assets/3d/texture/skin.png"
    monkeypatch.setattr(L, "GIT_MAX_BYTES", 32)
    big, _ = L.ingest(repo / "in" / "body.glb", "model.ubc_body_a", "model", path=path, repo=repo, tags=["body"],
                      bible_version="1.5", licence=lic(), three_d={"skeleton_id": "skeleton.ubc_humanoid_v1"})
    assert big["file"] == f"tools/assets_cache/{big['sha256']}/body.glb"
    assert big["storage"] == {"location": "external", "external_path": "assets/3d/model/model.ubc_body_a/body.glb"}
    assert (repo / "in" / "body.glb").exists()  # the source is never moved
    found = L.verify(path=path, repo=repo, versions=["1.5"])
    assert any("texture.skin" in p and "stored externally" in p for p in found)  # its bytes > the patched 32: flagged
    (repo / big["file"]).unlink()
    assert not any("model.ubc_body_a" in p for p in L.verify(path=path, repo=repo, versions=["1.5"]))  # in the vault


def test_fetch_takes_the_vault_copy_only_at_the_registered_hash(repo, monkeypatch):
    path = repo / "lib.json"
    monkeypatch.setattr(L, "GIT_MAX_BYTES", 32)
    big, _ = L.ingest(repo / "in" / "body.glb", "model.ubc_body_a", "model", path=path, repo=repo, tags=["body"],
                      bible_version="1.5", licence=lic(), three_d={})
    good = (repo / big["file"]).read_bytes()
    (repo / big["file"]).unlink()
    seen = []

    def download(url, tok, target, body=good):
        seen.append(url)
        target.write_bytes(body)

    got = L.fetch("model.ubc_body_a", path=path, repo=repo, download=download, tok="", primary="datasets/vano1919/tmr-artifacts")
    assert got.read_bytes() == good
    assert seen == ["https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/assets/3d/model/model.ubc_body_a/body.glb"]
    got.unlink()
    with pytest.raises(ValueError, match="another sha256"):
        L.fetch("model.ubc_body_a", path=path, repo=repo, download=lambda u, t, p: p.write_bytes(b"bad"), tok="",
                primary="datasets/vano1919/tmr-artifacts")
    assert not got.exists() and not list(got.parent.glob("*.part"))


def test_find_by_skeleton_and_reuse_lookup_for_3d_kinds(repo, tmp_path):
    path = repo / "lib.json"
    for aid, sk, f in (("animation.walk_ubc", "skeleton.ubc_humanoid_v1", "in/walk.fbx"),
                       ("animation.walk_mixamo", "skeleton.mixamo_v1", "in/rig.blend")):
        L.register(L.make_record(aid, "animation", f, repo=repo, tags=["walk"], bible_version="1.5", licence=lic("quaternius_ual"),
                                 three_d={"skeleton_id": sk, "format": "fbx", "up_axis": "Y"}), path=path)
    assert [r["id"] for r in L.find(kind="animation", skeleton_id="skeleton.ubc_humanoid_v1", path=path)] == ["animation.walk_ubc"]
    assert len(AR.lookup("animation", ["walk"], library_path=path)) == 2
    assert [m["id"] for m in AR.lookup("animation", ["walk"], library_path=path, skeleton_id="skeleton.mixamo_v1")] == ["animation.walk_mixamo"]
    ep = tmp_path / "ep"
    ep.mkdir()
    AR.record(ep, kind="animation", tags=["walk"], matches=AR.lookup("animation", ["walk"], library_path=path), decision="reuse")
    assert AR.has_lookup(ep, "animation") and AR.paid_justified(ep, "animation")


def test_cli_import_find_and_upgrade(repo, capsys):
    path = str(repo / "lib.json")
    base = ["--path", path, "--repo", str(repo)]
    assert L.main(base + ["import", str(repo / "in" / "walk.fbx"), "--id", "animation.walk", "--kind", "animation", "--tags", "walk",
                          "--bible", "1.5", "--source", "quaternius_ual", "--version", "1.0", "--up-axis", "Y",
                          "--skeleton", "skeleton.ubc_humanoid_v1"]) == 0
    assert "storage git" in capsys.readouterr().out
    assert L.main(base + ["find", "--kind", "animation", "--skeleton", "skeleton.ubc_humanoid_v1"]) == 0
    assert "1 asset(s)" in capsys.readouterr().out
    rec = L.get("animation.walk", path=repo / "lib.json")
    assert rec["licence"]["revision_or_version"] == "1.0" and rec["made_with"]["provider"] == "third_party"
    (repo / "v1.json").write_text(json.dumps({"schema": "asset_library/1", "items": []}))
    assert L.main(["--path", str(repo / "v1.json"), "upgrade"]) == 0
    assert json.loads((repo / "v1.json").read_text())["schema"] == "asset_library/2"
