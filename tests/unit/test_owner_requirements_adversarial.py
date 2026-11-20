"""Tester (skills team STEP 2): adversarial tests of the owner requirements registry, its CI job and its hooks (owner, 2026-11-20
08:37 UTC: "words are not enough, Claude still skips").

Question per test: can a thread that wants to be "done" get past the machine without the owner's word?

* guards: behaviour that holds today and must keep holding (they pass);
* defects: ``xfail(strict=True)`` named R1.. with the reason; they fail today, turn the suite red when the developer fixes one, and the
  marker is removed in the same commit (``--runxfail`` shows each failing for the stated reason).

$0, stdlib only, throw-away repos (the fixtures of ``test_owner_requirements``)."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from _gov import ROOT
from explainer_engine.governance import ci_check as CI
from explainer_engine.governance import layer_gate as LG
from explainer_engine.governance import owner_requirements as OR
from explainer_engine.qa import status as S
from test_owner_requirements import MSG, REG, codes, covered, entry, put, rec_for, registry, root, run  # noqa: F401


def errs_of(e, root):
    return OR._check_errs(e, root)


def judge(rubric, who="blind judge"):
    return {"kind": "judge", "who": who, "rubric": rubric}


# ============================ guards: the checks of one entry ============================

@pytest.mark.parametrize("field,code", [("test", "REQ-NOTEST"), ("negative_test", "REQ-NONEGATIVE")])
@pytest.mark.parametrize("value", [None, "", "  ", 5, ["tests/unit/test_living.py::test_living_motion"], "tests/unit/test_living.py",
                                   "tests/unit/test_living.py::test_missing", "tests/unit/test_nofile.py::test_living_motion",
                                   "tests/unit/test_living.py::test_living_motion extra", "::test_living_motion"])
def test_a_validator_needs_both_its_tests_to_exist(root, field, value, code):
    e = entry(1)
    e["check"][field] = value
    assert code in " ".join(errs_of(e, root))


@pytest.mark.parametrize("ref", [None, "", "explainer_engine.validators.living", "living_motion", "explainer_engine.validators.living:",
                                 "explainer_engine.validators.living:missing", "explainer_engine.validators.nofile:living_motion", 5])
def test_a_validator_ref_must_name_a_real_function(root, ref):
    e = entry(1)
    e["check"]["ref"] = ref
    assert "REQ-NOVALIDATOR" in " ".join(errs_of(e, root))


def test_a_bad_send_ref_is_refused_but_an_absent_one_is_fine(root):
    e = entry(1)
    assert errs_of(e, root) == []
    e["check"]["send_ref"] = "explainer_engine.validators.living:missing"
    assert "REQ-NOVALIDATOR" in " ".join(errs_of(e, root))


@pytest.mark.parametrize("rubric", ["", None, "  ", "docs/NOPE.md#faces-intact", "docs/RUBRICS.md#no-such-heading"])
def test_a_judge_needs_an_existing_rubric_heading(root, rubric):
    assert "REQ-NOJUDGE" in " ".join(errs_of(entry(1, check=judge(rubric)), root))


@pytest.mark.parametrize("who", [None, "", "   ", 5])
def test_a_judge_needs_a_who(root, who):
    assert "REQ-NOJUDGE" in " ".join(errs_of(entry(1, check=judge("docs/RUBRICS.md#faces-intact", who)), root))


@pytest.mark.parametrize("check", [None, {}, {"kind": "unmapped"}, {"kind": "judge"}, {"kind": "validator"}, "validator", 5, [],
                                   {"kind": "VALIDATOR"}, {"kind": "validator ", "ref": "x:y"}])
def test_an_entry_with_a_malformed_check_never_counts_as_checked(root, check):
    e = entry(1)
    if check is None:
        del e["check"]
    else:
        e["check"] = check
    assert errs_of(e, root), check


# ============================ guards: the registry file and the base-branch comparison ============================

def test_deleting_the_registry_or_emptying_it_is_reg_missing(root):
    assert "REG-MISSING" in " ".join(OR.missing(None))
    assert "REG-MISSING" in " ".join(OR.missing([]))
    put(root, registry())
    entries, errs = OR.load(root)
    assert entries == [] and OR.missing(entries)


@pytest.mark.parametrize("text", ["", "null", "[]", "{}", "{not json", '{"schema": "owner_requirements/1"}',
                                  '{"schema": "owner_requirements/9", "requirements": []}',
                                  '{"schema": "owner_requirements/1", "requirements": {}}',
                                  '{"schema": "owner_requirements/1", "requirements": [], "process_requirements": 5}'])
def test_a_broken_registry_file_is_a_reg_error_not_a_pass(root, text):
    (root / REG).parent.mkdir(parents=True, exist_ok=True)
    (root / REG).write_text(text, encoding="utf-8")
    entries, errs = OR.load(root)
    assert errs or not entries
    fails, _ = CI.problems(root, run_tests=False)
    assert fails, text


def test_ci_check_fails_when_one_entry_is_not_a_dict_and_survives_it(root):
    reg = registry(entry(1))
    reg["requirements"].append("REQ-002")
    reg["requirements"].append(None)
    reg["requirements"].append(5)
    put(root, reg)
    fails, _ = CI.problems(root, run_tests=False)
    assert any("REG-FIELDS" in f for f in fails)


@pytest.mark.parametrize("bad_id", ["", "req-001", "REQ-1", "REQ-001 ", "OR-v01", "../x", None, 7, "REQ-001\n"])
def test_a_malformed_entry_id_is_refused(root, bad_id):
    e = entry(1)
    e["id"] = bad_id
    assert any("REG-FIELDS" in x for x in OR.check_registry([e], root)), bad_id


def test_a_duplicate_id_is_refused(root):
    assert any("REG-DUP" in x for x in OR.check_registry([entry(1), entry(1)], root))


def test_removing_an_entry_against_the_base_is_reg_removed():
    base = [entry(1), entry(2)]
    assert any("REG-REMOVED" in x and "REQ-002" in x for x in OR.compare_with_base(base, [entry(1)]))
    assert any("REG-REMOVED" in x for x in OR.compare_with_base(base, None))
    assert any("REG-REMOVED" in x for x in OR.compare_with_base(base, []))


@pytest.mark.parametrize("field,new", [("words", "a softer wording"), ("words", ""), ("words", None), ("words_verbatim", True), ("words_verbatim", False)])
def test_changing_the_owners_words_against_the_base_is_refused(field, new):
    base = [entry(1, words_verbatim=not new if isinstance(new, bool) else True)]
    now = copy.deepcopy(base)
    now[0][field] = new
    assert any("REG-WORDS-CHANGED" in x for x in OR.compare_with_base(base, now))


def test_adding_an_entry_against_the_base_is_allowed():
    assert OR.compare_with_base([entry(1)], [entry(1), entry(2)]) == []


def test_a_superseded_entry_may_not_point_at_an_older_or_missing_or_itself(root):
    old = entry(1, status="superseded", superseded_by="REQ-002")
    for newer in (entry(2, date="2026-11-19T08:00:00Z"),):
        assert any("REG-SUPERSEDED" in x for x in OR.check_registry([old, newer], root))
    assert any("REG-SUPERSEDED" in x for x in OR.check_registry([entry(1, status="superseded", superseded_by="REQ-009")], root))
    assert any("REG-SUPERSEDED" in x for x in OR.check_registry([entry(1, status="superseded", superseded_by="REQ-001")], root))
    assert any("REG-SUPERSEDED" in x for x in OR.check_registry([entry(1, superseded_by="REQ-002"), entry(2)], root))


def test_a_resolved_conflict_needs_a_cmsg_id_and_an_open_one_blocks_its_layer(root):
    base = {"id": "REQ-050", "kind": "conflict", "summary": "two rules disagree", "conflicts": ["REQ-001", "GC-18"], "date": "2026-11-20T08:40:00Z",
            "source": {"kind": "chat", "ref": MSG}, "layers": ["L9"], "status": "resolved"}
    assert any("REG-CONFLICT" in x for x in OR.check_registry([entry(1), base], root))
    base["resolved_by"] = "not-an-id"
    assert any("REG-CONFLICT" in x for x in OR.check_registry([entry(1), base], root))
    put(root, registry(entry(1), dict(base, status="open")))
    assert "REQ-CONFLICT-OPEN" in codes(run(rec_for("REQ-001"), root))


def test_a_new_entry_reopens_a_passing_layer_and_removing_its_test_file_blocks_it_again(root):
    put(root, registry(entry(1)))
    rec = rec_for("REQ-001")
    assert run(rec, root).status == S.PASS
    (root / "tests" / "unit" / "test_living.py").unlink()
    res = run(rec, root)
    assert res.status == S.BLOCK and {"REQ-NOTEST", "REQ-NONEGATIVE"} <= codes(res)
    (root / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    pass\n\ndef test_living_motion_fails():\n    pass\n", encoding="utf-8")
    assert run(rec, root).status == S.BLOCK                                 # R4 fixed: a test that never names the validator proves nothing
    (root / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    living_motion = 1\n\ndef test_living_motion_fails():\n    living_motion = 0\n", encoding="utf-8")
    assert run(rec, root).status == S.PASS


def test_a_registry_entry_removed_from_the_file_can_not_open_a_final_layer(root):
    put(root, registry(entry(1)))
    rec = rec_for("REQ-001")
    rec["state"] = "final"
    put(root, registry())
    assert "REG-MISSING" in codes(run(rec, root))


# ============================ guards: the CI job and its workflow ============================

WORKFLOW = ROOT / ".github" / "workflows" / "owner-requirements.yml"


def test_the_workflow_exists_and_its_job_is_named_owner_requirements():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^\s{2}owner-requirements:\s*$", text, re.M) and re.search(r"^\s{4}name: owner-requirements\s*$", text, re.M)


@pytest.mark.parametrize("pattern,why", [
    (r"^\s*paths(-ignore)?:", "a path filter skips the job, and a skipped required check counts as passing"),
    (r"^\s*branches-ignore:", "a branch filter skips the job"),
    (r"continue-on-error", "the job must be able to fail"),
    (r"--no-tests", "the named tests must run in the job"),
    (r"\|\|\s*true", "a swallowed failure"),
    (r"^\s{4}if:", "a condition on the job itself skips it"),
    (r"\bexit 0\b", "a forced success"),
])
def test_the_workflow_has_no_way_to_skip_or_swallow_the_check(pattern, why):
    assert not re.search(pattern, WORKFLOW.read_text(encoding="utf-8"), re.M), why


def test_the_workflow_runs_on_every_pull_request_and_compares_with_the_base():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"^\s{2}pull_request:\s*$", text, re.M)
    assert '--base "origin/${{ github.base_ref }}"' in text
    assert "governance check" in text and "governance.ci_check" in text


def test_the_workflow_installs_requirements_so_the_named_tests_do_not_fail_on_a_missing_module():
    assert "pip install -r requirements.txt" in WORKFLOW.read_text(encoding="utf-8")


# ============================ defects ============================

def _base_and_now_with(change):
    base = [entry(1), entry(2, layers=("L10",))]
    now = copy.deepcopy(base)
    change(now)
    return base, now


def test_R1_superseding_an_owner_entry_needs_the_owners_recorded_word(root):
    def change(now):
        now[0]["status"] = "superseded"
        now[0]["superseded_by"] = "REQ-003"
        now.append(entry(3, date="2026-11-20T10:00:00Z", source={"kind": "doc", "ref": "whatever"}, layers=["L33"]))
    base, now = _base_and_now_with(change)
    assert OR.check_registry(now, root) == []                                 # schema-valid today
    assert OR.compare_with_base(base, now), "the old entry is gone from every layer and nothing in CI noticed"


def test_R2_shrinking_the_layers_of_an_entry_is_refused():
    base, now = _base_and_now_with(lambda n: n[1].update(layers=["L33"]))
    assert OR.compare_with_base(base, now)


@pytest.mark.parametrize("field,new", [("date", "2026-01-01T00:00:00Z"), ("source", {"kind": "doc", "ref": "anything"}), ("kind", "process")])
def test_R2_provenance_fields_are_append_only_too(field, new):
    base, now = _base_and_now_with(lambda n: n[0].update({field: new}))
    assert OR.compare_with_base(base, now)


def test_R3_removing_a_process_requirement_is_reg_removed(tmp_path, monkeypatch):
    base_doc = registry(entry(1))
    base_doc["process_requirements"] = [entry(7, layers=[], check={"kind": "unmapped"})]
    now_doc = copy.deepcopy(base_doc)
    now_doc["process_requirements"] = []

    class R:
        returncode = 0
        stdout = json.dumps(base_doc)

    monkeypatch.setattr(CI.subprocess, "run", lambda *a, **k: R())
    prior = CI.base_entries("origin/main", tmp_path)
    cur = [e for e in now_doc["requirements"]] + [dict(e, kind="process") for e in now_doc["process_requirements"]]
    assert any("REG-REMOVED" in x and "REQ-007" in x for x in OR.compare_with_base(prior, cur))


def test_R4_a_test_that_never_calls_the_validator_does_not_count(root):
    (root / "tests" / "unit" / "test_living.py").write_text(
        "def test_living_motion():\n    pass\n\ndef test_living_motion_fails():\n    assert True\n", encoding="utf-8")
    assert errs_of(entry(1), root), "neither test mentions living_motion"


def test_R4_the_negative_test_is_a_different_test_from_the_compliant_one(root):
    e = entry(1)
    e["check"]["negative_test"] = e["check"]["test"]
    assert errs_of(e, root)


def test_R5_a_judge_rubric_must_name_a_heading(root):
    (root / "README.md").write_text("# readme\n", encoding="utf-8")
    assert errs_of(entry(1, check=judge("README.md")), root)


def test_R5_a_judge_rubric_stays_inside_the_repo(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "rubric.md"
    outside.write_text("# x\n", encoding="utf-8")
    rel = "../" * 8 + str(outside).lstrip("/") + "#x"
    assert errs_of(entry(1, check=judge(rel)), root)


@pytest.mark.parametrize("ref", ["explainer_engine..validators.living:living_motion", ".explainer_engine.validators.living:living_motion"])
def test_a_validator_ref_with_an_empty_module_part_is_refused(root, ref):
    e = entry(1)
    e["check"]["ref"] = ref
    assert errs_of(e, root)


@pytest.mark.xfail(strict=True, reason="R7: the hook protection list names quality.yml but not the owner-requirements workflow, the registry, the gate or the hook config: "
                                       "a Write/Edit on them is not refused")
@pytest.mark.parametrize("path", [".github/workflows/owner-requirements.yml", "explainer_engine/governance/owner_requirements.json",
                                  "explainer_engine/governance/layer_gate.py", "explainer_engine/governance/send_gate.py",
                                  "explainer_engine/governance/ci_check.py", ".claude/settings.json"])
def test_R7_the_enforcement_files_themselves_are_protected(path):
    from explainer_engine.governance import hooks, load
    cfg = load()
    assert path in cfg["protected_files"], path
