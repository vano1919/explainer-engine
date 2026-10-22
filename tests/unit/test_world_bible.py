"""The World Bible (D-70 stage C, WB-01..WB-05): one versioned record of the visual world, pinned parts, recorded approval."""
import json

import jsonschema
import pytest

from explainer_engine.imagegen import plan as P
from explainer_engine.world import bible as B, resolver

SPEC = {"topic": "Newton at the Space Race", "host": {"era": "space_race_1960s", "place": "Houston", "when": "1969"},
        "visitors": [{"era": "renaissance_baroque", "people": ["newton"]}], "day_arc": []}


def parts(tmp_path):
    """Three stand-in part files and a bible that pins them (the committed one pins the real files)."""
    files = {}
    for name in ("look", "eras", "palette"):
        p = tmp_path / f"{name}.json"
        p.write_text(json.dumps({"name": name, "v": 1}), encoding="utf-8")
        files[name] = p
    b = json.loads(B.PATH.read_text(encoding="utf-8"))
    b["parts"] = {n: {"file": f.name, "sha256": B.sha256(f)} for n, f in files.items()}
    return files, b


def test_committed_bible_is_valid_and_matches_its_parts():
    """WB-02: look_v2.json, eras.json and palette.json changed? Then `python -m explainer_engine.world.bible bump --reason ...`."""
    assert B.check() == []
    assert B.load()["schema"] == "world_bible/1"


def test_cite_and_text():
    b = B.load()
    assert B.cite(b) == {"version": b["version"], "status": b["status"]}
    assert B.text(b) == f"world bible v{b['version']} ({b['status']})"
    assert B.versions(b)[-1] == b["version"]


def test_schema_refuses_an_unknown_field_and_a_bad_version():
    b = B.load()
    with pytest.raises(jsonschema.ValidationError):
        B.validate({**b, "mood": "dark"})
    with pytest.raises(jsonschema.ValidationError):
        B.validate({**b, "version": "v2"})


def test_an_edited_part_is_drift_until_the_version_is_bumped(tmp_path):
    files, b = parts(tmp_path)
    assert B.check(b, parts=files) == []
    files["eras"].write_text(json.dumps({"name": "eras", "v": 2}), encoding="utf-8")
    found = B.check(b, parts=files)
    assert len(found) == 1 and "eras" in found[0] and "bump" in found[0]
    new = B.bump("a new era entry", bible=b, parts=files, date="2026-10-23")
    assert new["version"] == "1.1" and new["status"] == "draft" and new["approved_by"] is None
    assert new["parts"]["eras"]["sha256"] == B.sha256(files["eras"])
    assert [e["version"] for e in new["changelog"]] == ["1.0", "1.1"] and new["changelog"][-1]["reason"] == "a new era entry"
    assert B.check(new, parts=files) == []
    assert B.bump("grammar change", major=True, bible=new, parts=files)["version"] == "2.0"
    with pytest.raises(ValueError):
        B.bump("   ", bible=new, parts=files)


def test_approval_needs_a_name_and_parts_that_match(tmp_path):
    files, b = parts(tmp_path)
    with pytest.raises(ValueError):
        B.approve("", bible=b, parts=files)
    files["look"].write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        B.approve("ვანო", bible=b, parts=files)
    fresh = B.bump("look edit", bible=b, parts=files)
    ok = B.approve("ვანო", note="first look test passed", bible=fresh, parts=files, at="2026-10-23T10:00:00")
    assert ok["status"] == "approved" and ok["approved_by"] == "ვანო" and ok["changelog"][-1]["approved_by"] == "ვანო"
    assert B.check(ok, parts=files) == []
    broken = {**ok, "approved_by": None}
    assert any("WB-03" in x for x in B.check(broken, parts=files))


def test_an_anchor_must_be_a_library_asset(tmp_path):
    files, b = parts(tmp_path)
    b["anchors"] = ["anchor.space_wide"]
    assert B.check(b, parts=files, library={"items": []}) == ["anchor anchor.space_wide is not in the asset library"]
    assert B.check(b, parts=files, library={"items": [{"id": "anchor.space_wide"}]}) == []


def test_bump_and_approve_write_the_file(tmp_path):
    files, b = parts(tmp_path)
    path = tmp_path / "bible.json"
    path.write_text(json.dumps(b), encoding="utf-8")
    B.bump("written", parts=files, path=path, bible=None) if False else None  # the CLI path: load from disk
    out = B.bump("written", bible=json.loads(path.read_text(encoding="utf-8")), parts=files, path=path)
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == out["version"] == "1.1"
    B.approve("ვანო", bible=json.loads(path.read_text(encoding="utf-8")), parts=files, path=path)
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "approved"


def test_world_and_paint_plan_cite_the_bible_version():
    """WB-04: every world.json and every paint plan says which bible version it was made under."""
    w = resolver.resolve(SPEC)
    assert w["bible"] == B.cite()
    plan = P.make("p1", "ep", [{"id": "w_0001", "prompt": "a wide shot", "refs": []}], provider="gemini",
                  model="gemini-nano-banana-2.1", size="2K")
    assert plan["bible"] == B.cite()
    assert P.plan_hash(plan) == plan["hash"]  # the citation is a record, not part of the approved hash


def test_cli_show_and_check(capsys):
    assert B.main(["show"]) == 0
    assert B.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "world bible v" in out and "0 finding(s)" in out
