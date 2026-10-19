"""PV-45 / OR-15: the creator approves a short scenario before the script is written."""

import json
from pathlib import Path

from explainer_engine.scripting import scenario as SC

ROOT = Path(__file__).resolve().parents[2]


def doc(schema="production_script/2", rec=None):
    d = {"schema": schema, "episode": {"id": "x", "title": "X episode"}}
    if rec is not None:
        d["episode"]["scenario"] = rec
    return d


def test_a_new_script_without_an_approved_scenario_fails_and_an_old_one_reviews():
    assert [f["severity"] for f in SC.check(doc())] == ["FAIL"]
    assert [f["severity"] for f in SC.check(doc("production_script/1"))] == ["REVIEW"]


def test_an_approved_scenario_passes_and_an_edit_after_the_approval_fails(tmp_path):
    f = tmp_path / "scenario.md"
    f.write_text("S01: the hook\n", encoding="utf-8")
    rec = {"file": "scenario.md", "approved_by": "creator", "approved_at": "2026-10-19", "sha256": SC.sha256(f)}
    assert SC.check(doc(rec=rec), tmp_path) == []
    f.write_text("S01: another hook\n", encoding="utf-8")
    assert "changed after the approval" in SC.check(doc(rec=rec), tmp_path)[0]["detail"]
    (tmp_path / "scenario.md").unlink()
    assert "missing" in SC.check(doc(rec=rec), tmp_path)[0]["detail"]


def test_the_schema_knows_the_scenario_record():
    s = json.loads((ROOT / "explainer_engine/schemas/production_script.schema.json").read_text(encoding="utf-8"))
    assert set(s["properties"]["episode"]["properties"]["scenario"]["properties"]) == {"file", "approved_by", "approved_at", "sha256"}
