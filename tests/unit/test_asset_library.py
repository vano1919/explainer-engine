"""The reusable asset library (D-70 stage C, WB-06..WB-10): records with provenance, hash, lineage and approval; duplicate
warnings never veto; a reusable paint plan's pictures become records; a plan names the library assets it leans on."""
import json

import pytest
from PIL import Image

from explainer_engine.assets import library as L
from explainer_engine.imagegen import plan as P
from explainer_engine.production import paint
from explainer_engine.world import bible as B


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "assets" / "refs").mkdir(parents=True)
    Image.new("RGB", (32, 18), (200, 40, 40)).save(tmp_path / "assets" / "refs" / "camp.png")
    Image.new("RGB", (32, 18), (40, 40, 200)).save(tmp_path / "assets" / "refs" / "valley.png")
    return tmp_path


def rec(repo, asset_id="reference.camp", name="camp", **kw):
    kw.setdefault("tags", ["camp", "fire", "night"])
    kw.setdefault("bible_version", "1.0")
    return L.make_record(asset_id, asset_id.split(".")[0], f"assets/refs/{name}.png", repo=repo, **kw)


def test_committed_library_verifies_clean():
    """Every record's file is present and unchanged, every parent exists, every bible version existed."""
    assert L.verify() == []
    lib = L.load()
    assert lib["schema"] == "asset_library/1" and len(lib["items"]) >= 9
    assert all(i["approval"]["status"] == "superseded" for i in lib["items"])  # look v1 sprites, kept for lineage only


def test_record_checks_id_kind_and_file(repo):
    r = rec(repo)
    assert (r["width"], r["height"]) == (32, 18) and r["file"] == "assets/refs/camp.png" and len(r["sha256"]) == 64
    assert r["tags"] == ["camp", "fire", "night"] and r["approval"]["status"] == "not_looked"
    with pytest.raises(ValueError, match="P-66"):
        rec(repo, "Camp Reference")
    with pytest.raises(ValueError, match="kind"):
        L.make_record("reference.camp", "sprite", "assets/refs/camp.png", repo=repo, tags=["x"], bible_version="1.0")
    with pytest.raises(ValueError, match="unknown kind"):
        L.make_record("thing.camp", "thing", "assets/refs/camp.png", repo=repo, tags=["x"], bible_version="1.0")
    with pytest.raises(FileNotFoundError):
        rec(repo, name="missing")


def test_duplicates_warn_and_never_veto(repo):
    path = repo / "lib.json"
    _, w = L.register(rec(repo), path=path)
    assert w == []
    same_bytes, w = L.register(rec(repo, "reference.camp.copy"), path=path)
    assert w == ["reference.camp has identical bytes"]
    twin = rec(repo, "reference.valley", "valley", made_with={"prompt": "a valley", "model": "m", "seed": 7})
    L.register(twin, path=path)
    again = rec(repo, "reference.valley.b", "valley", tags=["valley"], made_with={"prompt": "a valley", "model": "m", "seed": 7})
    again["sha256"] = "0" * 64  # different bytes, same recipe
    _, w = L.register(again, path=path)
    assert w == ["reference.valley has identical bytes"] or any("same prompt" in x for x in w)
    tagged = rec(repo, "reference.camp.night", "valley", tags=["camp", "night", "snow"])
    _, w = L.register(tagged, path=path)
    assert any("shares the tags camp, night" in x for x in w)
    assert len(L.load(path)["items"]) == 5
    with pytest.raises(ValueError, match="already"):
        L.register(rec(repo), path=path)
    L.register(rec(repo, description="again"), path=path, replace=True)
    assert L.get("reference.camp", path=path)["description"] == "again"


def test_find_hides_rejected_and_filters_by_kind_tags_and_version(repo):
    path = repo / "lib.json"
    L.register(rec(repo), path=path)
    L.register(rec(repo, "plate.valley", "valley", tags=["valley", "day"], bible_version="1.0"), path=path)
    assert [i["id"] for i in L.find(tags=["camp"], path=path)] == ["reference.camp"]
    assert [i["id"] for i in L.find(kind="plate", path=path)] == ["plate.valley"]
    assert L.find(tags=["camp", "day"], path=path) == []
    assert L.find(bible_version="0.9", path=path) == []
    L.approve("reference.camp", "ვანო", status="rejected", note="wrong era", path=path, at="2026-10-22T10:00:00")
    assert L.find(tags=["camp"], path=path) == [] and L.find(tags=["camp"], usable=False, path=path)[0]["approval"]["by"] == "ვანო"
    with pytest.raises(ValueError):
        L.approve("plate.valley", "", path=path)
    with pytest.raises(ValueError):
        L.approve("plate.valley", "ვანო", status="liked", path=path)


def test_lineage_and_verify(repo):
    path = repo / "lib.json"
    L.register(rec(repo), path=path)
    child = L.derive("reference.camp", "sprite.camp_fire", "sprite", "assets/refs/valley.png", path=path, repo=repo)
    assert child["lineage"]["parent"] == "reference.camp" and child["tags"] == ["camp", "fire", "night"] and child["bible_version"] == "1.0"
    L.register(child, path=path)
    assert [c["id"] for c in L.children("reference.camp", path=path)] == ["sprite.camp_fire"]
    assert L.verify(path=path, repo=repo, versions=["1.0"]) == []
    lib = L.load(path)
    lib["items"][0]["lineage"]["parent"] = "reference.ghost"
    lib["items"][1]["bible_version"] = "3.0"
    lib["items"][1]["approval"] = {"status": "approved", "by": None, "at": None, "note": ""}
    Image.new("RGB", (8, 8)).save(repo / "assets" / "refs" / "valley.png")
    found = L.verify(lib=lib, repo=repo, versions=["1.0", "1.1"])
    assert sorted(x.split(":")[1].strip()[:12] for x in found) == sorted(["parent refer", "bible versio", "approved wit", "file assets/"])
    assert L.verify(lib={"schema": "asset_library/1", "items": [{"id": "x"}]}, repo=repo, versions=["1.0"])[0].startswith("library:")


def test_ids_for_files_maps_by_bytes(repo):
    path = repo / "lib.json"
    L.register(rec(repo), path=path)
    other = repo / "elsewhere.png"
    other.write_bytes((repo / "assets" / "refs" / "camp.png").read_bytes())
    assert L.ids_for_files([other, repo / "assets" / "refs" / "valley.png", repo / "none.png"], path=path) == {"elsewhere.png": "reference.camp"}


def test_reusable_plan_outputs_become_records_with_the_plans_provenance(repo):
    path = repo / "lib.json"
    L.register(rec(repo), path=path)
    out = repo / "pics"
    out.mkdir()
    Image.new("RGB", (16, 9)).save(out / "f_einstein.png")
    Image.new("RGB", (16, 9), (1, 2, 3)).save(out / "f_newton.png")
    items = [{"id": "f_einstein", "prompt": "Einstein amazed, close-up", "refs": ["camp.png"]},
             {"id": "f_newton", "prompt": "Newton, close-up", "refs": ["unknown.png"]}]
    plan = P.make("F1", "Day-1", items, provider="gemini", model="gemini-nano-banana-2.1", size="2K", purpose="face sheets", reusable=True)
    plan["assets"] = {"camp.png": "reference.camp"}
    assert L.record_painted(P.make("E1", "Day-1", items, provider="gemini", model="gemini-nano-banana-2.1", size="2K"), out, ["f_einstein"], path=path) == []
    recs = L.record_painted(plan, out, ["f_einstein", "f_newton", "f_missing"], path=path, files_dir=repo / "assets" / "lib", repo=repo)
    assert [r["id"] for r in recs] == ["picture.day_1_f_einstein", "picture.day_1_f_newton"]
    e = recs[0]
    assert e["made_with"]["refs"] == ["reference.camp"] and e["made_with"]["prompt"] == "Einstein amazed, close-up"
    assert e["made_with"]["provider"] == "gemini" and e["bible_version"] == B.cite()["version"] and e["origin"]["source"] == "paint plan F1"
    assert recs[1]["made_with"]["unresolved_refs"] == ["unknown.png"]
    assert (repo / "assets" / "lib" / "picture" / "picture.day_1_f_einstein.png").exists()
    assert L.verify(path=path, repo=repo, versions=B.versions()) == []
    assert all(i["approval"]["status"] == "not_looked" for i in L.find(kind="picture", path=path))


def test_paint_plan_names_the_library_assets_among_its_references(repo, monkeypatch):
    path = repo / "lib.json"
    L.register(rec(repo), path=path)
    monkeypatch.setattr(L, "PATH", path)
    items = [{"id": "w_0001", "prompt": "p", "refs": ["camp.png", "valley.png"]}, {"id": "w_0002", "prompt": "p", "refs": ["hero"]}]
    doc = {"library": {"hero": {"file": "valley.png"}}}
    assert paint.reference_assets(items, doc, [repo / "assets" / "refs"]) == {"camp.png": "reference.camp"}
    assert paint.reference_assets(items, doc, [repo / "nowhere"]) == {}


def test_cli_add_find_approve_verify(repo, capsys):
    path = str(repo / "lib.json")
    assert L.main(["--path", path, "--repo", str(repo), "add", "assets/refs/camp.png", "--id", "reference.camp", "--kind", "reference",
                   "--tags", "camp,fire", "--provider", "gemini", "--model", "m", "--cost-usd", "0.05"]) == 0
    assert L.main(["--path", path, "--repo", str(repo), "add", str(repo / "assets/refs/camp.png"), "--id", "anchor.camp", "--kind", "anchor",
                   "--tags", "camp,fire", "--bible", "1.0"]) == 0
    out = capsys.readouterr().out
    assert "WARNING possible duplicate: reference.camp has identical bytes" in out
    assert L.main(["--path", path, "find", "--tags", "camp"]) == 0 and "2 asset(s)" in capsys.readouterr().out
    assert L.main(["--path", path, "approve", "anchor.camp", "--by", "ვანო", "--reject"]) == 0
    assert L.main(["--path", path, "find", "--tags", "camp"]) == 0 and "1 asset(s)" in capsys.readouterr().out
    assert L.main(["--path", path, "--repo", str(repo), "verify"]) == 0
    assert L.get("reference.camp", path=repo / "lib.json")["made_with"]["cost_usd"] == 0.05
