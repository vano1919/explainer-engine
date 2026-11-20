"""Spec section 7.3: the CI job ``owner-requirements`` fails on a missing registry, an unmapped entry, a validator without its tests, a
removed id or changed owner words against the base branch, and a failing named test; the workflow file is committed and runs it. $0."""
from __future__ import annotations

import json
import subprocess

import pytest

from _gov import ROOT
from explainer_engine.governance import ci_check as CI
from test_owner_requirements import REG, entry, put, registry, root  # noqa: F401 (root is a fixture)


@pytest.fixture
def env(root):
    (root / "tests" / "unit" / "test_living.py").write_text(
        "def test_living_motion():\n    assert True\n\ndef test_living_motion_fails():\n    assert True\n", encoding="utf-8")
    put(root, registry(entry(1)))
    return root


def codes(fails):
    return {f.split(":", 1)[0].replace("FAIL ", "") for f in fails}


def test_a_complete_registry_passes_without_the_tests_step(env):
    fails, notes = CI.problems(env, run_tests=False)
    assert fails == [] and notes == []


@pytest.mark.parametrize("how,code", [("missing", "REG-MISSING"), ("empty", "REG-MISSING"), ("unmapped", "REQ-UNMAPPED"),
                                      ("no test", "REQ-NOTEST"), ("no negative test", "REQ-NONEGATIVE"),
                                      ("no validator", "REQ-NOVALIDATOR"), ("no rubric", "REQ-NOJUDGE"), ("bad schema", "REG-FIELDS")])
def test_each_failure_of_the_registry_fails_the_job(env, how, code):
    reg = {"missing": None, "empty": registry(), "unmapped": registry(entry(1, check={"kind": "unmapped"})),
           "no test": registry(entry(1, check=dict(entry(1)["check"], test="tests/unit/test_living.py::nope"))),
           "no negative test": registry(entry(1, check={k: v for k, v in entry(1)["check"].items() if k != "negative_test"})),
           "no validator": registry(entry(1, check=dict(entry(1)["check"], ref="explainer_engine.validators.living:nope"))),
           "no rubric": registry(entry(1, check={"kind": "judge", "who": "blind judge", "rubric": "docs/NOPE.md"})),
           "bad schema": registry(entry(1, words=""))}[how]
    if reg is None:
        (env / REG).unlink()
    else:
        put(env, reg)
    fails, _ = CI.problems(env, run_tests=False)
    assert code in codes(fails), fails


def test_a_process_requirement_needs_its_check_and_tests_like_any_other(env):
    data = registry(entry(1))
    data["process_requirements"] = [dict(entry(2, id="OR-G01", layers=[]), check={"kind": "unmapped"})]
    put(env, data)
    fails, _ = CI.problems(env, run_tests=False)
    assert any(f.startswith("REQ-UNMAPPED: OR-G01") for f in fails)
    data["process_requirements"] = [entry(2, id="OR-G01", layers=[])]
    put(env, data)
    assert CI.problems(env, run_tests=False)[0] == []


def test_an_open_conflict_is_a_note_not_a_failure(env):
    MSG = "cmsg_01AbCd"
    c = {"id": "REQ-003", "kind": "conflict", "status": "open", "conflicts": ["REQ-001", "REQ-002"], "layers": ["L9"], "summary": "x",
         "date": "2026-11-20T08:20:00Z", "source": {"kind": "chat", "ref": MSG}}
    put(env, registry(entry(1), entry(2), c))
    fails, notes = CI.problems(env, run_tests=False)
    assert fails == [] and "open conflict REQ-003" in notes[0]


def test_a_failing_named_test_fails_the_job(env):
    (env / "tests" / "unit" / "test_living.py").write_text(
        "def test_living_motion():\n    assert False\n\ndef test_living_motion_fails():\n    assert True\n", encoding="utf-8")
    fails, _ = CI.problems(env)
    assert any(f.startswith("REQ-TESTFAIL") for f in fails)


def test_a_passing_named_test_does_not(env):
    assert CI.problems(env)[0] == []


def git(root, *args):
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args], check=True, capture_output=True)


def test_the_registry_is_append_only_against_the_base_branch(env):
    git(env, "init", "-q", "-b", "base")
    put(env, registry(entry(1), entry(2, words="the second word")))
    git(env, "add", "-A")
    git(env, "commit", "-q", "-m", "base")
    git(env, "checkout", "-q", "-b", "work")
    put(env, registry(entry(1), entry(2, words="the second word"), entry(3)))                       # growing is fine
    assert CI.problems(env, base="base", run_tests=False)[0] == []
    put(env, registry(entry(1)))                                                                      # an id removed
    assert "REG-REMOVED" in codes(CI.problems(env, base="base", run_tests=False)[0])
    put(env, registry(entry(1), entry(2, words="a softer word")))                                     # his words edited
    assert "REG-WORDS-CHANGED" in codes(CI.problems(env, base="base", run_tests=False)[0])
    put(env, registry(entry(1), dict(entry(2, words="the second word"), status="superseded", superseded_by="REQ-003"), entry(3)))
    assert CI.problems(env, base="base", run_tests=False)[0] == []                                    # retiring is the allowed way


def test_a_base_without_a_registry_is_only_a_note(env):
    git(env, "init", "-q", "-b", "base")
    (env / "x.txt").write_text("x")
    git(env, "add", "x.txt")
    git(env, "commit", "-q", "-m", "base")
    fails, notes = CI.problems(env, base="base", run_tests=False)
    assert fails == [] and "no registry yet" in notes[0]


def test_main_exit_codes(env, monkeypatch, capsys):
    monkeypatch.setattr(CI, "root_dir", lambda r=None: env)
    assert CI.main(["--no-tests"]) == 0 and "owner-requirements: ok" in capsys.readouterr().out
    (env / REG).unlink()
    assert CI.main(["--no-tests"]) == 1 and "REG-MISSING" in capsys.readouterr().out


def test_the_workflow_runs_the_check_against_the_base_branch_and_the_steps_file_names_the_job():
    wf = (ROOT / ".github" / "workflows" / "owner-requirements.yml").read_text(encoding="utf-8")
    assert "owner-requirements:" in wf and "name: owner-requirements" in wf and "governance.ci_check" in wf
    assert "github.base_ref" in wf and "fetch-depth: 0" in wf and "pull_request" in wf and "governance check" in wf
    steps = (ROOT / "docs" / "OWNER_REQUIREMENTS_CI_STEPS.md").read_text(encoding="utf-8")
    assert "owner-requirements" in steps and "Require status checks to pass" in steps
