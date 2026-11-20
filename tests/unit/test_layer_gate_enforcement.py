"""Spec section 7.2 with the owner's soft mode (his typed word 2026-11-20 09:11 UTC, cmsg_01Hnu5zB86sjUj5GtTgaUkPWMd8fDv9ExMX3zJq6nwZXau:
production stops only on a validator that failed): the episode runner and the trial scripts call ``layer_gate.require_layers``, which raises
only for a missing or invalid registry and lists every layer that is not final as a NOT_RUN note; ``send_gate.stage_check`` runs the owner's
validators on a stage's files and only a FAIL stops (the owner's recorded ``layer_waiver`` excuses one layer). There is one behaviour and no
flag. These tests run the real gate (``real_layer_gate``); every other unit test gets a gate that passes. $0."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from _gov import ROOT
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN
from explainer_engine.governance import layer_gate as LG
from explainer_engine.governance import records
from explainer_engine.governance import send_gate as SG
from test_send_gate import VALIDATOR
from test_owner_requirements import REG, entry, final, put, registry, rec_for, root  # noqa: F401 (root is a fixture)

MSG = "cmsg_01Hnu5zB86sjUj5GtTgaUkPW1oFAyBSLLgTCU7KMSLutpZ"
pytestmark = pytest.mark.usefixtures("real_layer_gate")


def write_layer(root, layer="L9", **kw):
    rec = final(rec_for("REQ-001"))
    rec.update(kw)
    (root / "docs" / "layers").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "layers" / f"{layer}.json").write_text(json.dumps(rec), encoding="utf-8")


def test_a_final_pass_record_lets_the_layer_through_silently(root):
    put(root, registry(entry(1)))
    write_layer(root)
    assert LG.require_layers(("L9",), root=root) == ["layer gate: fail_only"]


@pytest.mark.parametrize("what", ["no record", "draft record"])
def test_a_layer_without_a_final_record_is_listed_not_refused(root, what):
    put(root, registry(entry(1)))
    if what == "draft record":
        write_layer(root, state="draft")
    notes = LG.require_layers(("L9", "L10"), root=root)
    assert notes[0] == "layer gate: fail_only"
    assert any(n.startswith("NOT_RUN L9") for n in notes) and any(n.startswith("NOT_RUN L10") for n in notes)


def test_a_final_block_is_listed_too_the_layer_records_do_not_decide_whether_production_runs(root):
    put(root, registry(entry(1)))
    write_layer(root, state="final", requirements_covered=[])             # final, and the entry is not covered: BLOCK of the layer record
    notes = LG.require_layers(("L9",), root=root)
    assert any(n.startswith("NOT_RUN L9") and "REQ-UNCOVERED" in n for n in notes)


def test_a_missing_or_broken_registry_refuses_every_stage(root):
    with pytest.raises(ContractError, match="REG-MISSING"):
        LG.require_layers(("L9",), root=root)
    put(root, registry(entry(1, words="")))
    with pytest.raises(ContractError, match="REG-FIELDS"):
        LG.require_layers(("L9",), root=root)
    records.add("layer_waiver", "L9", MSG, "go on", root=root)            # a waiver never opens a broken registry
    with pytest.raises(ContractError, match="REG-FIELDS"):
        LG.require_layers(("L9",), root=root)


def test_a_waiver_is_a_note_for_one_layer(root):
    put(root, registry(entry(1)))
    records.add("layer_waiver", "L9", MSG, "go on with the pictures", root=root)
    notes = LG.require_layers(("L9", "L10"), root=root)
    assert any("L9 waived by the owner" in n and MSG in n for n in notes) and any(n.startswith("NOT_RUN L10") for n in notes)


@pytest.mark.parametrize("target", ["*", "L9,L10", "9", "L"])
def test_a_waiver_cannot_be_a_wildcard(root, target):
    with pytest.raises(ValueError):
        records.add("layer_waiver", target, MSG, "all of them", root=root)


def test_a_waiver_needs_his_message_id_and_a_quote(root):
    with pytest.raises(ValueError):
        records.add("layer_waiver", "L9", "", "words", root=root)
    with pytest.raises(ValueError):
        records.add("layer_waiver", "L9", MSG, "  ", root=root)


def test_every_runner_stage_has_its_layers_and_every_layer_is_known():
    assert set(LG.STAGE_LAYERS) == set(RUN.STAGES)
    for stage, layers in LG.STAGE_LAYERS.items():
        assert layers and all(layer in LG.GROUP_OF for layer in layers), stage


def test_the_runner_refuses_a_stage_when_there_is_no_registry(monkeypatch, tmp_path):
    ep = SimpleNamespace(root=tmp_path)
    monkeypatch.setattr(LG, "root_dir", lambda r=None: tmp_path)           # a repo with no registry and no records
    with pytest.raises(RUN.StageRefused, match="REG-MISSING"):
        RUN.run_stage(ep, "pictures")


def test_a_trial_script_refuses_before_it_reserves_or_writes_without_a_registry(monkeypatch, tmp_path):
    from explainer_engine.training.pods.ltx import scene_run as SR
    monkeypatch.setattr(LG, "root_dir", lambda r=None: tmp_path)
    out = tmp_path / "spec.json"
    with pytest.raises(SystemExit, match="refused"):
        SR.main(["job", str(tmp_path / "scene.json"), str(out)])
    assert not out.exists()
    with pytest.raises(SystemExit, match="refused"):
        SR.main(["reserve", str(tmp_path / "scene.json")])


def test_the_committed_repo_lists_its_layers_it_does_not_refuse():
    notes = LG.require_stage("pictures", root=ROOT)
    assert notes[0] == "layer gate: fail_only" and any(n.startswith("NOT_RUN") for n in notes)


# ---- the one behaviour: no strict mode, no flag, the owner's word only as an audit record --------------------------------------------

def test_there_is_no_mode_function_no_flag_and_the_record_takes_only_fail_only(root):
    assert not hasattr(LG, "gate_mode") and LG.MODE == "fail_only"
    params = LG.require_layers.__code__.co_varnames[:LG.require_layers.__code__.co_argcount + LG.require_layers.__code__.co_kwonlyargcount]
    assert params == ("layers", "root")
    for target in ("strict", "lenient", "off", "*", ""):
        with pytest.raises(ValueError):
            records.add("layer_gate_mode", target, MSG, "words", root=root)
    assert records.add("layer_gate_mode", "fail_only", MSG, "the owner's typed word", root=root)["target"] == "fail_only"


# ---- what stops production: a validator that FAILED on the stage's files -------------------------------------------------------------

@pytest.fixture
def vroot(root):
    (root / "explainer_engine" / "validators" / "living.py").write_text(VALIDATOR, encoding="utf-8")
    (root / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    assert True\n\ndef test_living_motion_fails():\n    assert True\n", encoding="utf-8")
    good, bad = root / "good.txt", root / "bad.txt"
    good.write_text("mmmm", encoding="utf-8")
    bad.write_text("m", encoding="utf-8")
    return root, good, bad


def test_a_failed_validator_stops_a_passing_one_does_not(vroot):
    root, good, bad = vroot
    put(root, registry(entry(1)))
    ok = SG.stage_check(("L9",), [good], root=root)
    assert ok["failed"] == [] and len(ok["passed"]) == 1
    no = SG.stage_check(("L9",), [good, bad], root=root)
    assert len(no["failed"]) == 1 and "REQ-001" in no["failed"][0] and no["failed"][0].startswith("L9 ")


def test_unmapped_judge_conflict_and_no_files_are_listed_never_a_stop(vroot):
    root, good, _ = vroot
    put(root, registry(entry(1), entry(2, check={"kind": "unmapped"})))
    rep = SG.stage_check(("L9",), [good], root=root)
    assert rep["failed"] == [] and any("REQ-002" in n and "unmapped" in n for n in rep["not_run"])
    assert SG.stage_check(("L9",), [], root=root) == {"failed": [], "passed": [], "not_run": ["no output file to measure"], "waived": []}
    other = root / "clip.mp4"
    other.write_bytes(b"x")
    assert SG.stage_check(("L9",), [other], root=root)["failed"] == []     # no validator of this file's kind: NOT_RUN


def test_the_send_to_the_owner_still_blocks_on_an_unmapped_entry(vroot):
    root, good, _ = vroot
    put(root, registry(entry(1), entry(2, check={"kind": "unmapped"})))
    assert SG.run("L9", [good], root=root)["status"] == SG.BLOCK            # only the runner's check is soft


def test_a_waiver_moves_a_failure_of_that_layer_to_waived(vroot):
    root, _, bad = vroot
    put(root, registry(entry(1)))
    records.add("layer_waiver", "L9", MSG, "I accept this failure", root=root)
    rep = SG.stage_check(("L9",), [bad], root=root)
    assert rep["failed"] == [] and len(rep["waived"]) == 1


def test_a_broken_validator_or_registry_in_the_check_is_a_failure(vroot):
    root, good, _ = vroot
    put(root, registry(entry(1, check={"kind": "validator", "ref": "explainer_engine.validators.living:boom",
                                         "test": "tests/unit/test_living.py::test_living_motion",
                                         "negative_test": "tests/unit/test_living.py::test_living_motion_fails"})))
    (root / "explainer_engine" / "validators" / "living.py").write_text(VALIDATOR.replace("boom.kinds = ()", "boom.kinds = ('.txt',)"), encoding="utf-8")
    assert SG.stage_check(("L9",), [good], root=root)["failed"]            # the validator raised: fail closed
    (root / "explainer_engine" / "governance" / "owner_requirements.json").unlink()
    assert SG.stage_check(("L9",), [good], root=root)["failed"]            # no registry: fail closed


def test_the_runner_records_a_failed_validator_as_a_failed_row_and_the_notes(monkeypatch, tmp_path):
    from explainer_engine.qa import gates as G
    ep = SimpleNamespace(root=tmp_path, manifest={"episode_id": "t"})
    monkeypatch.setattr(RUN.LG, "require_stage", lambda stage, **kw: ["layer gate: fail_only", "NOT_RUN L9: no record"])
    monkeypatch.setattr(RUN, "check_before", lambda ep, stage: False)
    monkeypatch.setattr(RUN.SS, "check_all", lambda root: [])
    monkeypatch.setattr(RUN.SS, "hook", lambda *a, **k: None)
    monkeypatch.setattr(RUN, "fingerprint", lambda ep, stage: "fp")
    monkeypatch.setattr(RUN, "record_path", lambda root, stage: tmp_path / f"{stage}.json")
    monkeypatch.setitem(RUN.STAGE_FUNCS, "script", lambda ep, rehearsal: ([G.row("a", True, "ok")], {"x": "x.txt"}))
    (tmp_path / "x.txt").write_text("m", encoding="utf-8")
    fail = {"failed": ["L1 REQ-001: 1 moving marks"], "passed": [], "not_run": ["L1 REQ-002: unmapped"], "waived": []}
    monkeypatch.setattr(RUN.SG, "stage_check", lambda layers, files, **kw: fail)
    rec = RUN.run_stage(ep, "script")
    assert rec["verdict"]["status"] == G.FAIL
    assert any(r["gate"] == "owner_requirements" and r["status"] == G.FAIL for r in rec["rows"])
    assert rec["layer_gate"]["mode"] == "fail_only" and rec["layer_gate"]["validators"]["not_run"] == ["L1 REQ-002: unmapped"]
    assert "NOT_RUN L9: no record" in rec["layer_gate"]["notes"]
    monkeypatch.setattr(RUN.SG, "stage_check", lambda layers, files, **kw: {"failed": [], "passed": [], "not_run": ["L1 REQ-002: unmapped"], "waived": []})
    rec = RUN.run_stage(ep, "script")
    assert rec["verdict"]["status"] == G.PASS and not any(r["gate"] == "owner_requirements" for r in rec["rows"])   # listed, not a stop
