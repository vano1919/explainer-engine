"""The owner's requirements registry and its enforcement in the layer gate (owner, 2026-11-20 08:34 UTC: "what is the point of rules
if they are not followed?"; spec OWNER_REQUIREMENTS_SPEC_2026-11-20 section 3, docs/LAYER_GATE.md).

A fixture registry in a throw-away repo: one negative test per code (REQ-UNMAPPED, REQ-NOTEST, REQ-NOJUDGE, REQ-UNCOVERED,
REQ-CONFLICT-OPEN, REQ-SUPERSEDED-USED and the rest), one per registry-schema rule, and the flip test: adding an entry to a registry
turns a passing layer into BLOCK. $0, stdlib only."""
from __future__ import annotations

import copy
import json

import pytest

from _gov import ROOT
from explainer_engine.governance import layer_gate as LG
from explainer_engine.governance import owner_requirements as OR
from explainer_engine.qa import status as S
from test_layer_gate import good

REG = "explainer_engine/governance/owner_requirements.json"
MSG = "cmsg_01Hnu5zB86sjUj5GtTgaUkPW1oFAyBSLLgTCU7KMSLutpZ"


def entry(i: int, layers=("L9",), *, check=None, **extra) -> dict:
    e = {"id": f"REQ-{i:03d}", "words": "only the fire moves is not allowed", "date": "2026-11-20T08:33:54Z",
         "source": {"kind": "chat", "ref": MSG}, "layers": list(layers), "status": "active",
         "check": check or {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                            "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}}
    e.update(extra)
    return e


def registry(*entries) -> dict:
    return {"schema": "owner_requirements/1", "requirements": list(entries)}


def covered(*ids) -> list[dict]:
    return [{"id": i, "evidence": "the validator ran on the sample and the number is in the trial note"} for i in ids]


@pytest.fixture
def root(tmp_path):
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "OVERLAY.md").write_text("# overlay\nTask mode only: batches of 6\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").write_text("| D-131 | the v4.3 rebuild |\n| D-139 | x |\n", encoding="utf-8")
    (tmp_path / "docs" / "RUBRICS.md").write_text("# Rubrics\n\n## Faces intact\n\nthe judge looks at six frames\n", encoding="utf-8")
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "unit" / "test_living.py").write_text("def test_living_motion():\n    living_motion = True\n    assert living_motion\n\ndef test_living_motion_fails():\n    living_motion = True\n    assert living_motion\n", encoding="utf-8")
    (tmp_path / "explainer_engine" / "validators").mkdir(parents=True)
    (tmp_path / "explainer_engine" / "validators" / "living.py").write_text("def living_motion(path):\n    return {}\n", encoding="utf-8")
    return tmp_path


def put(root, reg) -> None:
    p = root / REG
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(reg), encoding="utf-8")


def rec_for(*ids) -> dict:
    r = good()
    r["requirements_covered"] = covered(*ids)
    return r


def codes(res) -> set[str]:
    return {e.split(":", 1)[0] for e in res.errors}


def run(rec, root):
    return LG.check_record(rec, root=root)


# ---- the gate: a registry entry binds its layers -------------------------------------------------------------------------------

def test_a_layer_with_every_bound_entry_covered_passes(root):
    put(root, registry(entry(1), entry(2, layers=("L10",))))
    res = run(rec_for("REQ-001"), root)
    assert res.status == S.PASS and res.errors == []


def test_no_registry_file_binds_nothing(root):
    assert run(good(), root).status == S.PASS


def test_adding_an_entry_flips_a_passing_layer_to_block(root):
    put(root, registry(entry(1)))
    rec = rec_for("REQ-001")
    assert run(rec, root).status == S.PASS
    put(root, registry(entry(1), entry(2, check={"kind": "judge", "who": "blind judge", "rubric": "docs/RUBRICS.md#faces-intact"})))
    res = run(rec, root)
    assert res.status == S.BLOCK and "REQ-UNCOVERED" in codes(res)           # the new entry reopens the layer it binds
    assert "REQ-002" in " ".join(res.errors)


def test_an_entry_of_another_layer_does_not_bind(root):
    put(root, registry(entry(1, layers=("L14",))))
    assert run(good(), root).status == S.PASS


def test_a_superseded_entry_binds_nothing_but_may_not_be_cited(root):
    put(root, registry(entry(1, status="superseded", superseded_by="REQ-002"), entry(2, date="2026-11-20T09:00:00Z")))
    assert run(rec_for("REQ-002"), root).status == S.PASS
    res = run(rec_for("REQ-002", "REQ-001"), root)
    assert "REQ-SUPERSEDED-USED" in codes(res) and res.status == S.BLOCK


def test_a_citation_of_an_id_that_is_not_in_the_registry(root):
    put(root, registry(entry(1)))
    assert "REQ-UNKNOWN" in codes(run(rec_for("REQ-001", "REQ-099"), root))


@pytest.mark.parametrize("name,rows", [
    ("not a list", "REQ-001"),
    ("row without evidence", [{"id": "REQ-001"}]),
    ("empty evidence", [{"id": "REQ-001", "evidence": "  "}]),
    ("row without id", [{"evidence": "a number"}]),
    ("the same id twice", [{"id": "REQ-001", "evidence": "a"}, {"id": "REQ-001", "evidence": "b"}]),
])
def test_requirements_covered_rows_are_well_formed(root, name, rows):
    put(root, registry(entry(1)))
    rec = good()
    rec["requirements_covered"] = rows
    assert "REQ-COVER-FIELD" in codes(run(rec, root)), name


def test_a_layer_record_without_the_field_is_uncovered_not_a_crash(root):
    put(root, registry(entry(1)))
    assert "REQ-UNCOVERED" in codes(run(good(), root))


# ---- the six codes of the check of a covered entry ---------------------------------------------------------------------------

def test_an_unmapped_entry_blocks(root):
    put(root, registry(entry(1, check={"kind": "unmapped"})))
    res = run(rec_for("REQ-001"), root)
    assert "REQ-UNMAPPED" in codes(res) and res.status == S.BLOCK


def test_an_entry_without_a_check_is_unmapped(root):
    e = entry(1)
    del e["check"]
    put(root, registry(e))
    assert "REQ-UNMAPPED" in codes(run(rec_for("REQ-001"), root))


@pytest.mark.parametrize("name,check", [
    ("no test field", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion"}),
    ("the test file is missing", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                                  "test": "tests/unit/test_nowhere.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("the test function is missing", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                                      "test": "tests/unit/test_living.py::test_other", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("the test has no ::name", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                                "test": "tests/unit/test_living.py", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
])
def test_a_validator_without_an_existing_test_blocks(root, name, check):
    put(root, registry(entry(1, check=check)))
    res = run(rec_for("REQ-001"), root)
    assert "REQ-NOTEST" in codes(res) and res.status == S.BLOCK, name


@pytest.mark.parametrize("name,check", [
    ("no negative test", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                          "test": "tests/unit/test_living.py::test_living_motion"}),
    ("the negative test file is missing", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                                           "test": "tests/unit/test_living.py::test_living_motion",
                                           "negative_test": "tests/unit/test_nowhere.py::test_living_motion_fails"}),
    ("the negative test function is missing", {"kind": "validator", "ref": "explainer_engine.validators.living:living_motion",
                                               "test": "tests/unit/test_living.py::test_living_motion",
                                               "negative_test": "tests/unit/test_living.py::test_no_such"}),
])
def test_a_validator_without_a_negative_test_blocks(root, name, check):
    put(root, registry(entry(1, check=check)))
    res = run(rec_for("REQ-001"), root)
    assert "REQ-NONEGATIVE" in codes(res) and res.status == S.BLOCK, name


@pytest.mark.parametrize("name,check", [
    ("no ref", {"kind": "validator", "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("an empty ref", {"kind": "validator", "ref": "", "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("not module:function", {"kind": "validator", "ref": "living_motion", "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("the module does not exist", {"kind": "validator", "ref": "explainer_engine.validators.nope:living_motion",
                                   "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
    ("the function does not exist", {"kind": "validator", "ref": "explainer_engine.validators.living:other",
                                     "test": "tests/unit/test_living.py::test_living_motion", "negative_test": "tests/unit/test_living.py::test_living_motion_fails"}),
])
def test_a_validator_that_does_not_exist_blocks(root, name, check):
    put(root, registry(entry(1, check=check)))
    res = run(rec_for("REQ-001"), root)
    assert "REQ-NOVALIDATOR" in codes(res) and res.status == S.BLOCK, name


@pytest.mark.parametrize("name,check", [
    ("no who", {"kind": "judge", "rubric": "docs/RUBRICS.md#faces-intact"}),
    ("no rubric", {"kind": "judge", "who": "blind judge"}),
    ("the rubric file is missing", {"kind": "judge", "who": "blind judge", "rubric": "docs/NOPE.md#x"}),
    ("the rubric anchor is missing", {"kind": "judge", "who": "blind judge", "rubric": "docs/RUBRICS.md#no-such-heading"}),
    ("an empty who", {"kind": "judge", "who": " ", "rubric": "docs/RUBRICS.md#faces-intact"}),
])
def test_a_judge_without_who_and_an_existing_rubric_blocks(root, name, check):
    put(root, registry(entry(1, check=check)))
    res = run(rec_for("REQ-001"), root)
    assert "REQ-NOJUDGE" in codes(res) and res.status == S.BLOCK, name


def test_a_judge_with_a_rubric_that_exists_passes(root):
    put(root, registry(entry(1, check={"kind": "judge", "who": "owner at MS-7", "rubric": "docs/RUBRICS.md#faces-intact"}),
                       entry(2, check={"kind": "judge", "who": "Gemini eye", "rubric": "docs/RUBRICS.md#faces-intact"})))
    assert run(rec_for("REQ-001", "REQ-002"), root).status == S.PASS


def test_an_open_conflict_blocks_the_layers_it_binds(root):
    c = {"id": "REQ-003", "kind": "conflict", "status": "open", "conflicts": ["REQ-001", "REQ-002"], "layers": ["L9"],
         "summary": "rule 20 (name the film) against GC-18 (never the word photograph)", "date": "2026-11-20T08:20:00Z",
         "source": {"kind": "chat", "ref": MSG}}
    put(root, registry(entry(1), entry(2), c))
    res = run(rec_for("REQ-001", "REQ-002"), root)
    assert "REQ-CONFLICT-OPEN" in codes(res) and res.status == S.BLOCK
    other = good()
    other["layer"], other["group"] = "L14", 2
    assert "REQ-CONFLICT-OPEN" not in codes(run(other, root))               # a layer it does not bind is not stopped


def test_a_resolved_conflict_no_longer_blocks(root):
    c = {"id": "REQ-003", "kind": "conflict", "status": "resolved", "resolved_by": MSG, "conflicts": ["REQ-001", "REQ-002"],
         "layers": ["L9"], "summary": "test both", "date": "2026-11-20T08:20:00Z", "source": {"kind": "chat", "ref": MSG}}
    put(root, registry(entry(1), entry(2), c))
    assert run(rec_for("REQ-001", "REQ-002"), root).status == S.PASS


# ---- the registry schema -----------------------------------------------------------------------------------------------------

def bad(**kv):
    return lambda e: e.update(kv) or e


def drop(key):
    return lambda e: (e.pop(key), e)[1]


SCHEMA_NEGATIVE = [
    ("empty words", bad(words=" "), "REG-FIELDS"),
    ("no words", drop("words"), "REG-FIELDS"),
    ("no date", drop("date"), "REG-FIELDS"),
    ("a date that is no date", bad(date="yesterday"), "REG-FIELDS"),
    ("no source", drop("source"), "REG-FIELDS"),
    ("a source kind that is not allowed", bad(source={"kind": "hearsay", "ref": "x"}), "REG-FIELDS"),
    ("a chat ref that is no message id", bad(source={"kind": "chat", "ref": "my chat"}), "REG-FIELDS"),
    ("a decision ref that is not in the log", bad(source={"kind": "decision_log", "ref": "D-777"}), "REG-FIELDS"),
    ("an empty source ref", bad(source={"kind": "memory", "ref": ""}), "REG-FIELDS"),
    ("a status that is not allowed", bad(status="maybe"), "REG-FIELDS"),
    ("an id that is no REQ-nnn", bad(id="R-1"), "REG-FIELDS"),
    ("no layers", bad(layers=[]), "REG-LAYER"),
    ("a layer outside L1..L33", bad(layers=["L34"]), "REG-LAYER"),
    ("a layer that is no layer", bad(layers=["frames"]), "REG-LAYER"),
    ("superseded without a newer id", bad(status="superseded"), "REG-SUPERSEDED"),
    ("superseded by itself", bad(status="superseded", superseded_by="REQ-001"), "REG-SUPERSEDED"),
    ("superseded by an id that is not there", bad(status="superseded", superseded_by="REQ-099"), "REG-SUPERSEDED"),
    ("superseded_by on an active entry", bad(superseded_by="REQ-002"), "REG-SUPERSEDED"),
    ("a check kind that is not allowed", bad(check={"kind": "vibes"}), "REG-FIELDS"),
]


@pytest.mark.parametrize("name,fn,code", SCHEMA_NEGATIVE, ids=[n[0] for n in SCHEMA_NEGATIVE])
def test_the_registry_schema_refuses(root, name, fn, code):
    put(root, registry(fn(entry(1)), entry(2, date="2026-11-20T09:00:00Z")))
    res = run(rec_for(), root)
    assert code in codes(res) and res.status == S.BLOCK, res.errors


def test_the_schema_checks_do_not_fire_on_a_good_registry(root):
    e2 = entry(2, status="superseded", superseded_by="REQ-003", words="x")
    put(root, registry(entry(1, source={"kind": "decision_log", "ref": "D-139"}), e2, entry(3, date="2026-11-20T09:00:00Z")))
    assert OR.check_registry(OR.load(root)[0], root) == []


def test_duplicate_ids_and_a_wrong_schema_marker(root):
    put(root, registry(entry(1), entry(1)))
    assert "REG-DUP" in codes(run(rec_for(), root))
    put(root, {"schema": "owner_requirements/0", "requirements": [entry(1)]})
    assert "REG-SCHEMA" in codes(run(rec_for(), root))
    (root / REG).write_text("{not json", encoding="utf-8")
    assert "REG-SCHEMA" in codes(run(rec_for(), root))
    put(root, {"schema": "owner_requirements/1"})
    assert "REG-SCHEMA" in codes(run(rec_for(), root))


def test_a_conflict_entry_needs_two_existing_ids_and_a_resolver_once_resolved(root):
    c = {"id": "REQ-003", "kind": "conflict", "status": "open", "conflicts": ["REQ-001"], "layers": ["L9"], "summary": "x",
         "date": "2026-11-20T08:20:00Z", "source": {"kind": "chat", "ref": MSG}}
    put(root, registry(entry(1), entry(2), c))
    assert "REG-CONFLICT" in codes(run(rec_for("REQ-001", "REQ-002"), root))
    c = dict(c, conflicts=["REQ-001", "REQ-099"])
    put(root, registry(entry(1), entry(2), c))
    assert "REG-CONFLICT" in codes(run(rec_for("REQ-001", "REQ-002"), root))
    c = dict(c, conflicts=["REQ-001", "REQ-002"], status="resolved")
    put(root, registry(entry(1), entry(2), c))
    assert "REG-CONFLICT" in codes(run(rec_for("REQ-001", "REQ-002"), root))      # resolved without resolved_by
    c = dict(c, summary=" ")
    put(root, registry(entry(1), entry(2), c))
    assert "REG-FIELDS" in codes(run(rec_for("REQ-001", "REQ-002"), root))


def test_a_registry_error_blocks_every_layer_not_only_the_bound_ones(root):
    put(root, registry(entry(1, layers=["L14"], words="")))
    assert run(rec_for(), root).status == S.BLOCK


# ---- the CLI and the repo guard -----------------------------------------------------------------------------------------------

def test_the_committed_registry_is_schema_valid_and_every_final_layer_covers_it():
    reg, errs = OR.load(ROOT)
    assert errs == []
    if reg is not None:
        assert OR.check_registry(reg, ROOT) == []
    for r in LG.check_all(root=ROOT):
        if r.state == "final":
            assert r.status != S.BLOCK, r.errors


def test_the_report_lists_unmapped_entries_per_layer(root):
    put(root, registry(entry(1, check={"kind": "unmapped"}), entry(2, layers=("L9", "L10")), entry(3, layers=("L10",))))
    rep = OR.report(root)
    assert rep["total"] == 3 and rep["unmapped"] == ["REQ-001"]
    assert rep["per_layer"]["L9"] == {"active": 2, "unmapped": 1} and rep["per_layer"]["L10"] == {"active": 2, "unmapped": 0}
    assert OR.report(root.parent / "empty")["total"] == 0


def test_cli_requirements_prints_the_report_and_exit_code(root, capsys, monkeypatch):
    from explainer_engine.governance import __main__ as M
    monkeypatch.setattr(M, "root_dir", lambda *a: root)
    put(root, registry(entry(1, check={"kind": "unmapped"}), entry(2)))
    assert M.main(["requirements"]) == 1                      # an unmapped entry: the report exits 1
    out = capsys.readouterr().out
    assert "REQ-001" in out and "unmapped" in out and "L9" in out
    put(root, registry(entry(2)))
    assert M.main(["requirements"]) == 0
    assert M.main(["requirements", "--layer", "L9"]) == 0


def test_the_group_ids_the_extra_fields_and_the_utc_date_form_are_accepted(root):
    a = entry(1, id="OR-V01", date="2026-11-19 22:08 UTC", measures="optical flow inside the fire mask above a threshold")
    b = entry(2, id="OR-V02", parent="OR-V01", words_verbatim=True, date="2026-11-20 08:34 UTC")
    put(root, registry(a, b))
    assert OR.check_registry(OR.load(root)[0], root) == []
    assert run(rec_for("OR-V01", "OR-V02"), root).status == S.PASS


@pytest.mark.parametrize("kv", [{"parent": "OR-V99"}, {"parent": "OR-V02"}, {"measures": " "}, {"id": "OR-v02"}])
def test_the_extra_fields_are_checked(root, kv):
    put(root, registry(entry(1, id="OR-V01"), entry(2, **{"id": "OR-V02", **kv})))
    assert "REG-FIELDS" in codes(run(rec_for(), root))


# ---- the registry may not be deleted or emptied (REG-MISSING) and may only grow (CI against the base branch) ---------------------

def final(rec):
    rec.update(state="final", signed_by="team lead", signed_at="2026-11-20", owner_seen="pending",
               owner_check=[{"url": "https://huggingface.co/datasets/x/y/blob/main/p.html", "sha256": "a" * 64}])
    return rec


def test_a_final_record_needs_the_registry_to_exist_and_hold_entries(root):
    put(root, registry(entry(1)))
    ok = final(rec_for("REQ-001"))
    assert run(ok, root).status == S.PASS
    (root / REG).unlink()                                                    # delete the file: every final layer BLOCKs
    res = run(ok, root)
    assert "REG-MISSING" in codes(res) and res.status == S.BLOCK
    put(root, registry())                                                    # empty it: same
    assert "REG-MISSING" in codes(run(ok, root))
    put(root, {"schema": "owner_requirements/1", "requirements": []})
    assert "REG-MISSING" in codes(run(ok, root))


def test_a_draft_without_a_registry_is_only_reported(root):
    assert "REG-MISSING" not in codes(run(good(), root))


def test_require_pass_refuses_when_the_registry_is_gone(root):
    import shutil
    (root / "docs" / "layers").mkdir(parents=True, exist_ok=True)
    put(root, registry(entry(1)))
    (root / "docs" / "layers" / "L9.json").write_text(json.dumps(final(rec_for("REQ-001"))), encoding="utf-8")
    assert LG.require_pass("L9", root=root).status == S.PASS
    shutil.rmtree(root / "explainer_engine" / "governance")
    with pytest.raises(LG.ContractError, match="REG-MISSING"):
        LG.require_pass("L9", root=root)


def test_the_base_comparison_refuses_a_removed_id_and_changed_words(root):
    base = [entry(1), entry(2, words="the owner's second word")]
    assert OR.compare_with_base(base, base + [entry(3)]) == []
    assert any(e.startswith("REG-REMOVED") for e in OR.compare_with_base(base, [entry(1)]))
    changed = [entry(1), entry(2, words="a softer word")]
    assert any(e.startswith("REG-WORDS-CHANGED") for e in OR.compare_with_base(base, changed))
    gone = [entry(1), dict(entry(2, words="the owner's second word"), status="superseded", superseded_by="REQ-003"), entry(3)]
    assert OR.compare_with_base(base, gone) == []                              # retiring is allowed, deleting and rewording are not
    assert OR.compare_with_base(None, base) == [] and any(e.startswith("REG-REMOVED") for e in OR.compare_with_base(base, None))


# ---- the analyst's registry v2: child ids, process requirements, conflicts naming outside rules ------------------------------------

def test_child_ids_decision_lists_and_flags_of_the_analysts_file_load_clean(root):
    kid = entry(2, id="OR-V09a", parent="OR-V09", words_verbatim=True, words_partial=False, words_origin="memory_quote",
                source={"kind": "decision_log", "ref": "D-131 / D-139, BP-105"})
    put(root, registry(entry(1, id="OR-V09"), kid))
    assert OR.check_registry(OR.load(root)[0], root) == []
    put(root, registry(entry(1, id="OR-V09"), dict(kid, source={"kind": "decision_log", "ref": "D-131 / D-777"})))
    assert "REG-FIELDS" in codes(run(rec_for(), root))                                   # one of the listed ids is not in the log
    put(root, registry(entry(1, id="OR-V09"), dict(kid, words_verbatim="yes")))
    assert "REG-FIELDS" in codes(run(rec_for(), root))                                   # the flag is a boolean


def test_a_conflict_may_name_rules_outside_the_registry_but_a_registry_id_must_exist(root):
    c = {"id": "OR-C01", "kind": "conflict", "status": "open", "title": "GC-18 against rule 20", "words": "", "layers": ["L9"],
         "conflicts": ["OR-V02", "OR-V01", "GC-18"], "date": "2026-11-20T00:00:00Z", "source": {"kind": "doc", "ref": "docs/x.md#GC-18"}}
    put(root, registry(entry(1, id="OR-V01", layers=["L14"]), entry(2, id="OR-V02", layers=["L14"]), c))
    assert OR.check_registry(OR.load(root)[0], root) == []                               # an empty words field is by design for a conflict
    c2 = dict(c, conflicts=["OR-V99", "GC-18"])
    put(root, registry(entry(1, id="OR-V01", layers=["L14"]), c2))
    assert "REG-CONFLICT" in codes(run(rec_for(), root))
    c3 = dict(c, conflicts=["GC-18", "RR-03"], status="open")
    put(root, registry(entry(1, id="OR-V01", layers=["L14"]), c3))
    assert OR.check_registry(OR.load(root)[0], root) == []                               # two outside rules are enough to name a conflict


def test_process_requirements_bind_no_layer_but_are_in_the_registry_and_the_report(root):
    data = registry(entry(1))
    data["process_requirements"] = [dict(entry(2, id="OR-G01", layers=[]), check={"kind": "unmapped"})]
    put(root, data)
    ents, errs = OR.load(root)
    assert errs == [] and [e["id"] for e in ents if OR.is_process(e)] == ["OR-G01"]
    assert OR.check_registry(ents, root) == []
    assert run(rec_for("REQ-001"), root).status == S.PASS                                # the layer gate never reads a process requirement
    rep = OR.report(root)
    assert rep["process"] == ["OR-G01"] and "OR-G01" in rep["unmapped"]
    data["process_requirements"][0]["layers"] = ["L9"]
    put(root, data)
    assert "REG-LAYER" in codes(run(rec_for("REQ-001"), root))                           # a process requirement that names a layer is a mistake
    data["process_requirements"][0]["layers"] = ["L33"]                                    # the dev-process layer is the one exception
    put(root, data)
    assert OR.check_registry(OR.load(root)[0], root) == [] and [e["id"] for e in OR.bound(OR.load(root)[0], "L33")] == ["OR-G01"]
    data["process_requirements"][0]["layers"] = ["L33", "L9"]
    put(root, data)
    assert "REG-LAYER" in codes(run(rec_for("REQ-001"), root))
    data["process_requirements"] = "no"
    put(root, data)
    assert "REG-SCHEMA" in codes(run(rec_for("REQ-001"), root))


def test_the_coverage_table_counts_validator_judge_and_unmapped_per_layer(root):
    put(root, registry(entry(1), entry(2, check={"kind": "unmapped"}),
                       entry(3, check={"kind": "judge", "who": "fresh reviewer", "rubric": "skill/OVERLAY.md#x"})))
    md = OR.coverage_md(root)
    assert "| L9 | 3 | 1 | 1 | 1 |" in md and "3 active entries" in md
