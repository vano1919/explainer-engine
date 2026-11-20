"""Spec section 4: ``governance/send_gate`` measures a candidate against the validators of the layer's registered requirements before the
owner sees it. A fixture registry with a fixture validator that fails on a bad file and passes on a good one. $0."""
from __future__ import annotations

import json

import pytest

from explainer_engine.governance import send_gate as SG
from test_owner_requirements import REG, entry, put, registry, root  # noqa: F401 (root is a fixture)

MSG = "cmsg_01Hnu5zB86sjUj5GtTgaUkPW1oFAyBSLLgTCU7KMSLutpZ"
VALIDATOR = '''
def living_motion(path):
    text = path.read_text()
    moving = text.count("m")
    return {"status": "PASS" if moving >= 3 else "FAIL", "value": float(moving), "detail": f"{moving} moving marks"}
living_motion.kinds = (".txt",)

def boom(path):
    raise RuntimeError("the validator itself broke")
boom.kinds = ()

def plan_turns(queue, size=6):
    return []
'''


@pytest.fixture
def env(root):
    (root / "explainer_engine" / "validators" / "living.py").write_text(VALIDATOR, encoding="utf-8")
    (root / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    living_motion = True\n    assert living_motion\n\ndef test_living_motion_fails():\n    living_motion = True\n    assert living_motion\n\ndef test_boom():\n    boom = True\n    assert boom\n\ndef test_plan_turns():\n    plan_turns = True\n    assert plan_turns\n\ndef test_plan_turns_fails():\n    plan_turns = True\n    assert plan_turns\n", encoding="utf-8")
    good = root / "good.txt"
    good.write_text("mmmm", encoding="utf-8")
    bad = root / "bad.txt"
    bad.write_text("m", encoding="utf-8")
    put(root, registry(entry(1, measures="moving marks")))
    return root, good, bad


def rows(rep):
    return {r["id"]: r for r in rep["rows"]}


def test_a_compliant_file_passes_with_its_number(env):
    root, good, _ = env
    rep = SG.run("L9", [good], root=root)
    assert rep["status"] == "PASS" and rows(rep)["REQ-001"]["value"] == 4.0
    assert "PASS" in SG.render(rep) and "4.0" in SG.render(rep)


def test_a_file_that_violates_the_requirement_fails_and_exits_non_zero(env, capsys, monkeypatch):
    root, _, bad = env
    rep = SG.run("L9", [bad], root=root)
    assert rep["status"] == "FAIL" and rows(rep)["REQ-001"]["status"] == "FAIL"
    monkeypatch.setattr(SG, "root_dir", lambda r=None: root)
    assert SG.main(["L9", str(bad)]) == 1
    assert "FAIL" in capsys.readouterr().out


def test_one_failing_file_among_good_ones_fails_the_send(env):
    root, good, bad = env
    assert SG.run("L9", [good, bad], root=root)["status"] == "FAIL"


def test_the_cli_exit_code_is_zero_for_a_pass(env, monkeypatch):
    root, good, _ = env
    monkeypatch.setattr(SG, "root_dir", lambda r=None: root)
    assert SG.main(["L9", str(good)]) == 0


def test_an_unmapped_entry_blocks_the_send(env):
    root, good, _ = env
    put(root, registry(entry(1), entry(2, check={"kind": "unmapped"})))
    rep = SG.run("L9", [good], root=root)
    assert rep["status"] == "BLOCK" and rows(rep)["REQ-002"]["status"] == "BLOCK"


def test_a_judge_step_is_shown_as_not_run_and_does_not_fail(env):
    root, good, _ = env
    put(root, registry(entry(1, check={"kind": "judge", "who": "blind judge", "rubric": "docs/RUBRICS.md#faces-intact"})))
    rep = SG.run("L9", [good], root=root)
    assert rep["status"] == "NOT_RUN" and rows(rep)["REQ-001"]["status"] == "NOT_RUN" and "blind judge" in rows(rep)["REQ-001"]["detail"]


def test_a_file_of_another_kind_is_not_measured_by_the_validator(env):
    root, _, _ = env
    other = root / "clip.mp4"
    other.write_bytes(b"\x00\x01")
    rep = SG.run("L9", [other], root=root)
    assert rep["status"] == "NOT_RUN" and "no file of kind .txt" in rows(rep)["REQ-001"]["detail"]


@pytest.mark.parametrize("how", ["no file", "empty registry", "missing registry", "wrong layer", "open conflict", "broken validator", "raises"])
def test_everything_that_cannot_be_measured_blocks(env, how):
    root, good, _ = env
    files = [good]
    layer = "L9"
    if how == "no file":
        files = [root / "nope.txt"]
    elif how == "empty registry":
        put(root, registry())
    elif how == "missing registry":
        (root / REG).unlink()
    elif how == "wrong layer":
        layer = "L99"
    elif how == "open conflict":
        c = {"id": "REQ-003", "kind": "conflict", "status": "open", "conflicts": ["REQ-001", "REQ-002"], "layers": ["L9"], "summary": "x",
             "date": "2026-11-20T08:20:00Z", "source": {"kind": "chat", "ref": MSG}}
        put(root, registry(entry(1), entry(2), c))
    elif how == "broken validator":
        put(root, registry(entry(1, check={"kind": "validator", "ref": "explainer_engine.validators.living:nope",
                                           "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"})))
    elif how == "raises":
        put(root, registry(entry(1, check={"kind": "validator", "ref": "explainer_engine.validators.living:boom",
                                           "test": "tests/unit/test_living.py::test_boom", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"})))
    rep = SG.run(layer, files, root=root)
    assert rep["status"] == "BLOCK", rep


def test_the_label_for_a_failing_candidate_needs_the_owners_message_id(env):
    root, _, bad = env
    with pytest.raises(ValueError):
        SG.run("L9", [bad], root=root, owner_asked="please")
    with pytest.raises(ValueError):
        SG.run("L9", [root / "good.txt"], root=root, owner_asked=MSG)       # nothing failed: nothing to label
    rep = SG.run("L9", [bad], root=root, owner_asked=MSG)
    assert rep["status"] == "FAIL" and rep["label"]["text"] == "fails REQ-001"
    assert "fails REQ-001" in SG.render(rep)


def test_a_passing_record_lets_that_file_go_and_a_failing_one_does_not(env):
    root, good, bad = env
    SG.run("L9", [good, bad][:1], root=root)
    SG.run("L9", [bad], root=root)
    assert SG.passing_record(good, root=root) is not None
    assert SG.passing_record(bad, root=root) is None
    SG.run("L9", [bad], root=root, owner_asked=MSG)
    assert SG.passing_record(bad, root=root)["label"]["owner_asked"] == MSG        # labelled with the owner's word: may go
    good.write_text("mmmmm", encoding="utf-8")                                       # a changed file is a different file
    assert SG.passing_record(good, root=root) is None


def test_every_run_is_recorded_with_the_hash_of_each_file(env):
    root, good, _ = env
    SG.run("L9", [good], root=root)
    line = json.loads((root / SG.RECORDS).read_text().splitlines()[-1])
    assert line["layer"] == "L9" and line["files"][0]["sha256"] == SG.sha256(good) and line["status"] == "PASS"


def test_a_pipeline_function_without_kinds_is_not_run_and_an_adapter_in_send_ref_is_used(env):
    root, good, bad = env
    pipe = dict(entry(1)["check"], ref="explainer_engine.validators.living:plan_turns", test="tests/unit/test_living.py::test_plan_turns",
                negative_test="tests/unit/test_living.py::test_plan_turns_fails")
    put(root, registry(entry(1, check=pipe)))
    rep = SG.run("L9", [good], root=root)
    assert rep["status"] == "NOT_RUN" and "no send adapter" in rows(rep)["REQ-001"]["detail"]
    put(root, registry(entry(1, check=dict(pipe, send_ref="explainer_engine.validators.living:living_motion"))))
    assert SG.run("L9", [good], root=root)["status"] == "PASS"
    assert SG.run("L9", [bad], root=root)["status"] == "FAIL"
    put(root, registry(entry(1, check=dict(pipe, send_ref="explainer_engine.validators.living:nope"))))
    assert SG.run("L9", [good], root=root)["status"] == "BLOCK"                       # a send_ref that does not exist blocks
