"""The screenplay spine (Blueprint P3, ZI-10): compiled from the approved script and its shot cards, never written by hand;
the three promises are locked by the creator's script approval (PV-53); claim ids of the Napoleon draft ("C02", "I01") parse."""

from __future__ import annotations

import copy
import json

import pytest

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production.__main__ import main as production_main
from explainer_engine.scripting import claims, script_approval
from explainer_engine.standards import sourced_rules as SR

from test_story_engine import storied

PROMISES = ["Napoleon against a blizzard", "Why the khan lets him win", "From the first march to the last"]
CLAIM_MAP = """| id | claim | label | source |
|---|---|---|---|
| C-01 | The glasses were made of rock crystal. | E | https://example.org/crystal |
| C-02 | The first night was cold. | R | our reasoning |
"""


def setup(tmp_path, promises=PROMISES, profile="A"):
    doc = storied()
    doc["drama"]["packaging_promises"] = list(promises) if promises else None
    if not promises:
        del doc["drama"]["packaging_promises"]
    doc["drama"]["profile_id"] = profile
    doc["segments"][0]["lines"][0]["claims"] = ["C-01"]
    doc["segments"][1]["lines"][1]["claims"] = ["C-02"]
    (tmp_path / "production_script.json").write_text(json.dumps(doc), encoding="utf-8")
    (tmp_path / "claim_map.md").write_text(CLAIM_MAP, encoding="utf-8")
    shots = {"schema": "film_shots/1", "shots": [{"id": "a", "scene": doc["segments"][0]["id"], "seconds": 4},
                                                 {"id": "b", "scene": doc["segments"][0]["id"], "seconds": 3},
                                                 {"id": "c", "scene": doc["segments"][1]["id"], "seconds": 5}]}
    (tmp_path / "film_shots.json").write_text(json.dumps(shots), encoding="utf-8")
    return doc


def spine(tmp_path):
    return C.compile_spine(tmp_path / "production_script.json", tmp_path / "film_shots.json")


def test_a_small_script_compiles_to_a_valid_spine_with_windows_connectors_and_claims(tmp_path):
    doc = setup(tmp_path)
    sp = spine(tmp_path)
    assert not [f for f in contracts.errors(sp, tmp_path) if f["severity"] == "FAIL"]
    assert sp["packaging_promises"] == PROMISES and sp["structure_profile_id"] == "A" and sp["episode_slug"] == doc["episode"]["id"]
    first, second = sp["segments"]
    assert (first["est_duration_sec"], first["clock_window_sec"], first["causal_connector"]) == (7.0, [0.0, 7.0], "OPEN")
    assert (second["est_duration_sec"], second["clock_window_sec"], second["causal_connector"]) == (5.0, [7.0, 12.0], "BUT")
    assert first["lines"][0]["speaker"] == "narrator" and first["lines"][0]["claim_ids"] == ["C-01"]
    assert {c["claim_id"]: (c["status"], c["source_ref"]) for c in sp["claims"]} == {
        "C-01": ("FACT", "https://example.org/crystal"), "C-02": ("ALTERNATE", "our reasoning")}


def test_a_missing_segment_a_stray_scene_or_a_missing_claim_is_a_contract_error(tmp_path):
    doc = setup(tmp_path)
    shots = json.loads((tmp_path / "film_shots.json").read_text(encoding="utf-8"))
    (tmp_path / "film_shots.json").write_text(json.dumps({**shots, "shots": shots["shots"][:2]}), encoding="utf-8")
    with pytest.raises(ContractError, match="no shot cards"):
        spine(tmp_path)
    (tmp_path / "film_shots.json").write_text(json.dumps({**shots, "shots": shots["shots"] + [{"id": "z", "scene": "S99", "seconds": 1}]}),
                                              encoding="utf-8")
    with pytest.raises(ContractError, match="the script does not have"):
        spine(tmp_path)
    (tmp_path / "film_shots.json").write_text(json.dumps(shots), encoding="utf-8")
    (tmp_path / "claim_map.md").write_text(CLAIM_MAP.replace("| C-02 |", "| C-09 |"), encoding="utf-8")
    with pytest.raises(ContractError, match="C-02"):
        spine(tmp_path)


def test_missing_promises_or_profile_are_a_contract_error(tmp_path):
    setup(tmp_path, promises=None)
    with pytest.raises(ContractError, match="stage 1b"):
        spine(tmp_path)
    setup(tmp_path)
    d = json.loads((tmp_path / "production_script.json").read_text(encoding="utf-8"))
    del d["drama"]["profile_id"]
    (tmp_path / "production_script.json").write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ContractError, match="profile"):
        spine(tmp_path)


def test_a_declared_and_then_cannot_be_a_connector(tmp_path):
    setup(tmp_path)
    d = json.loads((tmp_path / "production_script.json").read_text(encoding="utf-8"))
    d["segments"][1]["drama"]["turn"] = "and then"
    (tmp_path / "production_script.json").write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ContractError, match="start, but or therefore"):
        spine(tmp_path)


def test_a_changed_input_makes_the_spine_stale_cn02(tmp_path):
    setup(tmp_path)
    sp = spine(tmp_path)
    assert not contracts.derived_findings(sp, tmp_path)
    shots = json.loads((tmp_path / "film_shots.json").read_text(encoding="utf-8"))
    shots["shots"][0]["seconds"] = 9
    (tmp_path / "film_shots.json").write_text(json.dumps(shots), encoding="utf-8")
    assert [f["rule"] for f in contracts.derived_findings(sp, tmp_path)] == ["CN-02"]


def test_the_cli_writes_the_spine_next_to_the_other_outputs(tmp_path, capsys):
    setup(tmp_path)
    out = tmp_path / "out"
    production_main(["compile", str(tmp_path / "production_script.json"), "--out", str(out), "--film-shots", str(tmp_path / "film_shots.json")])
    target = out / "screenplay_spine.json"
    sp = json.loads(target.read_text(encoding="utf-8"))
    assert sp["derived_from"]["film_shots"]["path"] == "../film_shots.json"
    assert not [f for f in contracts.errors(sp, out) if f["severity"] == "FAIL"]


def test_the_schema_takes_the_two_optional_drama_fields_and_nothing_else_changed():
    d = storied()
    assert not S.schema_errors(d)
    d["drama"]["packaging_promises"] = PROMISES
    d["drama"]["profile_id"] = "D"
    assert not S.schema_errors(d)
    for bad in ({"packaging_promises": PROMISES[:2]}, {"packaging_promises": PROMISES + ["x"]}, {"profile_id": "E"}):
        e = copy.deepcopy(d)
        e["drama"].update(bad)
        assert S.schema_errors(e)


def approved(doc):
    d = copy.deepcopy(doc)
    d["episode"]["script_approval"] = {"approved_by": "creator", "approved_at": "2026-10-30", "sha256": script_approval.words_sha256(d)}
    if script_approval.promises_sha256(d):
        d["episode"]["script_approval"]["promises_sha256"] = script_approval.promises_sha256(d)
    return d


def test_the_promises_are_locked_by_the_script_approval(tmp_path):
    doc = setup(tmp_path)
    doc["schema"] = script_approval.BINDING
    ok = approved(doc)
    assert script_approval.check(ok) == [] and not S.schema_errors(ok)
    changed = copy.deepcopy(ok)
    changed["drama"]["packaging_promises"][0] = "Something the creator never saw"
    found = script_approval.check(changed)
    assert [f["where"] for f in found] == ["drama.packaging_promises"] and found[0]["severity"] == "FAIL"
    dropped = copy.deepcopy(ok)
    del dropped["drama"]["packaging_promises"]
    assert [f["where"] for f in script_approval.check(dropped)] == ["drama.packaging_promises"]
    plain = copy.deepcopy(doc)
    del plain["drama"]["packaging_promises"]
    assert script_approval.check(approved(plain)) == []  # a script with no promises is approved as before


def test_approve_records_the_promises_hash_when_there_are_promises(tmp_path):
    doc = setup(tmp_path)
    doc["schema"] = script_approval.BINDING
    path = tmp_path / "production_script.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    rec = script_approval.approve(path, "creator", "2026-10-30")
    assert rec["promises_sha256"] == script_approval.promises_sha256(doc)
    assert script_approval.check(json.loads(path.read_text(encoding="utf-8"))) == []


def test_claim_ids_of_the_napoleon_draft_parse_next_to_the_old_ones():
    cmap = claims.parse_map("| id | claim | label | source |\n|---|---|---|---|\n| C-01 | a | E | https://x.org |\n"
                            "| C02 | b | E | https://y.org |\n| I01 | c | I | our invention |\n| x | no | E | no |\n")
    assert sorted(cmap) == ["C-01", "C02", "I01"] and cmap["I01"]["label"] == "I"
    assert SR.T("BP-135", "angles") == 3
