"""Adversarial tests for ``governance/layer_gate`` (group 1 tester, skills team, 2026-11-20). $0, stdlib only, tests only.

Two kinds of test live here:

* guards: hostile input the gate already refuses correctly (wrong types in owner_seen, waiver, owner_check, NOT_RUN that must
  never pass, keep_ours with fewer than 3 really run candidates, a licence that must never block). They pass today and keep
  those behaviours from being weakened.
* defects: input the gate wrongly accepts or crashes on. Each is ``xfail(strict=True)`` with its finding number
  (``TEST_G1_2026-11-20.md``); the test fails today, and when the developer fixes the gate it turns into an unexpected pass,
  which fails the suite until the marker is removed. Nothing in ``explainer_engine`` was changed to make these pass.
"""
from __future__ import annotations

import json
import os

import pytest

from explainer_engine.core.errors import ContractError, NeedsReview
from explainer_engine.governance import layer_gate as LG
from explainer_engine.qa import status as S
from test_layer_gate import SHA, _cand, _other, _write_group1, check, codes, good, keep_good, sign, write


@pytest.fixture
def root(tmp_path):
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "OVERLAY.md").write_text("# overlay\nTask mode only: batches of 6\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").write_text("| D-131 | the v4.3 rebuild |\n| D-140 | x |\n", encoding="utf-8")
    reg = tmp_path / "explainer_engine" / "governance"      # a final record needs the owner's registry (REG-MISSING, T2.0): one entry of an unused layer
    reg.mkdir(parents=True)
    (reg / "owner_requirements.json").write_text(json.dumps({"schema": "owner_requirements/1", "requirements": [{
        "id": "REQ-901", "words": "x", "date": "2026-11-20T08:00:00Z", "source": {"kind": "chat", "ref": "cmsg_01AbCdEf"},
        "layers": ["L33"], "status": "active", "check": {"kind": "unmapped"}}]}), encoding="utf-8")
    return tmp_path


def _set(path, value):
    def apply(rec):
        node = rec
        for k in path[:-1]:
            node = node[k]
        node[path[-1]] = value
        return rec
    return apply


def _keep(rec):
    rec["decisions"][0].update(choice="keep_ours", beats=5, candidate_ids=[])
    return rec


# ======================================================================================================================
# GUARDS: the gate already refuses these; keep it that way
# ======================================================================================================================

# ---- owner_seen / owner_check / waiver of the wrong type --------------------------------------------------------------

@pytest.mark.parametrize("bad", [5, None, ["cmsg_01A"], {"id": "cmsg_01A"}, "", "cmsg_", "cmsg_ 01A", "CMSG_01A", "cmsg_01A\n", True],
                         ids=repr)
def test_final_owner_seen_of_the_wrong_type_is_a_block(root, bad):
    rec = sign(good())
    rec["owner_seen"] = bad
    res = check(rec, root)
    assert "LG-OWNER" in codes(res) and res.status == S.BLOCK


@pytest.mark.parametrize("bad", ["https://huggingface.co/x", {"url": "https://x.org"}, [None], [5], ["https://x.org"], [{"url": 5}],
                                 [{"url": "https://x.org", "sha256": "nothex"}], [{"sha256": 5}]], ids=repr)
def test_final_owner_check_of_the_wrong_shape_is_a_block(root, bad):
    rec = sign(good())
    rec["owner_check"] = bad
    res = check(rec, root)
    assert "LG-OWNER" in codes(res) and res.status == S.BLOCK


@pytest.mark.parametrize("bad", [5, ["cmsg_01A"], "", "cmsg_", "the owner agreed", True, {}], ids=repr)
def test_a_waiver_of_the_wrong_type_is_refused_and_does_not_waive(root, bad):
    rec = sign(good())
    rec["not_run_waiver"] = bad
    res = check(rec, root)
    assert "LG-OWNER" in codes(res) and res.waived is False


def test_a_waiver_on_a_draft_does_not_open_the_next_group(root):
    _write_group1(root, final_layers={"L9", "L10", "L11"})
    draft = good()
    draft.update(layer="L16", not_run_waiver="cmsg_01OwnerWord")
    draft["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no GPU"}
    draft["decisions"][0]["evidence"] = []
    write(root, draft, "L16")
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L16"):
        LG.require_pass("L12", root=root)


def test_group_ten_waits_while_only_group_one_is_final(root):
    _write_group1(root, final_layers=set(LG.GROUPS[1]))
    write(root, _other("L31", 10), "L31")
    with pytest.raises(NeedsReview, match="group 10"):
        LG.require_pass("L31", root=root)


@pytest.mark.parametrize("state", ["Final", " final", "FINAL", "final ", True, None, ["final"], "signed"], ids=repr)
def test_a_state_that_is_not_exactly_draft_or_final_is_a_block_and_never_ready(root, state):
    rec = sign(good())
    rec["state"] = state
    res = check(rec, root)
    assert "LG-SCHEMA" in codes(res) and res.status == S.BLOCK
    write(root, rec, "L9")
    with pytest.raises(ContractError):
        LG.require_pass("L9", root=root)


def test_a_blank_signature_is_not_a_signature(root):
    rec = sign(good())
    rec["signed_by"] = "   "
    assert "LG-SIGN" in codes(check(rec, root))
    rec["signed_by"], rec["signed_at"] = "team lead", ""
    assert "LG-SIGN" in codes(check(rec, root))


# ---- NOT_RUN is never a pass ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["PASS", "pass", "run", "Run", "OK", "DONE", "", None, True, 1, ["RUN"]], ids=repr)
def test_a_trial_status_that_is_not_exactly_run_or_not_run_never_passes(root, status):
    rec = good()
    rec["trials"][0]["status"] = status
    res = check(rec, root)
    assert "MS3-TRIAL-FIELD" in codes(res) and res.status == S.BLOCK and not S.is_success(res.status)


def test_one_not_run_sub_question_among_passing_ones_makes_the_layer_not_run(root):
    rec = good()
    rec["sub_questions"].append({"id": "SQ2", "text": "second"})
    rec["candidates"] += [_cand(4, "SQ2"), _cand(5, "SQ2"), _cand(6, "SQ2")]
    rec["trials"].append({"id": "TR2", "sub_question": "SQ2", "status": "NOT_RUN", "not_run_reason": "needs the owner's Chrome"})
    rec["decisions"].append({"sub_question": "SQ2", "choice": "adopt", "candidate_ids": ["C4"], "reason": "provisional", "evidence": []})
    res = check(rec, root)
    assert res.errors == [] and res.status == S.NOT_RUN and not S.is_success(res.status)
    assert [n.split(":")[0] for n in res.not_run] == ["SQ2"]


def test_a_final_not_run_record_is_not_ready_and_require_pass_refuses_it(root):
    rec = sign(good())
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no GPU"}
    rec["decisions"][0]["evidence"] = []
    write(root, rec, "L9")
    with pytest.raises(NeedsReview, match="NOT_RUN"):
        LG.require_pass("L9", root=root)
    assert LG.problems(LG.check_all(root=root)) == []       # reported, not a failure: but also never a pass


@pytest.mark.parametrize("config_ok", [False])
def test_a_badly_configured_run_is_not_run_even_with_every_link_present(root, config_ok):
    rec = good()
    rec["trials"][0]["config_ok"] = config_ok
    res = check(rec, root)
    assert res.errors == [] and res.status == S.NOT_RUN


# ---- keep_ours with fewer than 3 really run candidates --------------------------------------------------------------

KEEP_RUN3 = {
    "two distinct candidates": lambda r: r["trials"][0].update(candidate_ids=["C1", "C3"]) or r,
    "one candidate named five times": lambda r: r["trials"][0].update(candidate_ids=["C3"] * 5) or r,
    "the third run belongs to another sub-question": lambda r: r["candidates"][0].update(sub_question="SQ9") or r,
    "the third run is in a NOT_RUN trial": lambda r: (
        r["trials"][0].update(candidate_ids=["C2", "C3"]),
        r["trials"].append({"id": "TR2", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no cpu", "candidate_ids": ["C1"]}),
        r)[2],
    "the third run was badly configured": lambda r: (
        r["trials"][0].update(candidate_ids=["C2", "C3"]),
        r["trials"].append({"id": "TR2", "sub_question": "SQ1", "status": "RUN", "looked_at_by": "x", "observation": "y", "config_ok": False,
                            "candidate_ids": ["C1"], "links": [{"ref": "https://x.org/a", "kind": "page", "seen": "z"}]}),
        r)[2],
    "candidate_ids is a string": lambda r: r["trials"][0].update(candidate_ids="C1C2C3") or r,
    "candidate_ids is null": lambda r: r["trials"][0].update(candidate_ids=None) or r,
    "candidate_ids unknown ids": lambda r: r["trials"][0].update(candidate_ids=["C1", "C2", "C99"]) or r,
}


@pytest.mark.parametrize("name", list(KEEP_RUN3), ids=list(KEEP_RUN3))
def test_keep_ours_with_fewer_than_three_really_run_candidates_is_a_block(root, name):
    res = check(KEEP_RUN3[name](keep_good()), root)
    assert "MS4-KEEP-RUN3" in codes(res), res.errors
    assert res.status == S.BLOCK and not S.is_success(res.status)


def test_three_candidates_run_in_separate_trials_do_count(root):
    """The union over trials is what counts (control: the gate is strict, not broken)."""
    rec = keep_good()
    rec["trials"][0].update(candidate_ids=["C1"])
    for i, cid in ((2, "C2"), (3, "C3")):
        rec["trials"].append({"id": f"TR{i}", "sub_question": "SQ1", "status": "RUN", "looked_at_by": "x", "observation": "y",
                              "candidate_ids": [cid], "links": [{"ref": "https://x.org/a", "kind": "page", "seen": "z"}]})
    assert "MS4-KEEP-RUN3" not in codes(check(rec, root))


@pytest.mark.parametrize("bad", [5, None, ["cmsg_01A"], "", "cmsg_", "pending", "the owner saw it", True], ids=repr)
def test_keep_ours_owner_seen_of_the_wrong_type_is_refused(root, bad):
    rec = keep_good()
    rec["owner_seen"] = bad
    assert "MS4-KEEP-OWNER" in codes(check(rec, root))


@pytest.mark.parametrize("meets", [1, "true", "yes", None, 0, [True]], ids=repr)
def test_keep_ours_needs_a_real_true_for_every_requirement(root, meets):
    rec = keep_good()
    rec["requirements"][0]["ours_meets"] = meets
    assert "MS4-KEEP-REQ" in codes(check(rec, root))


@pytest.mark.parametrize("complaint", [False, 0, "", [], {}, {"open": None, "fix_seen": "cmsg_01A"}, {"open": 0, "fix_seen": "cmsg_01A"},
                                       {"open": False, "fix_seen": 5}, {"open": False, "fix_seen": ["cmsg_01A"]}], ids=repr)
def test_keep_ours_an_unclosed_or_malformed_complaint_is_refused(root, complaint):
    rec = keep_good()
    rec["requirements"][0]["complaint"] = complaint
    assert "MS4-KEEP-REQ" in codes(check(rec, root))


@pytest.mark.parametrize("judge", ["fresh reviewer", 5, [], None, True], ids=repr)
def test_keep_ours_a_blind_judge_that_is_not_an_object_is_refused(root, judge):
    rec = keep_good()
    rec["decisions"][0]["blind_judge"] = judge
    assert "MS4-KEEP-JUDGE" in codes(check(rec, root))


def test_keep_ours_judge_is_the_author_under_case_and_space_changes(root):
    rec = keep_good()
    rec["decisions"][0]["blind_judge"]["judge"] = "  DEVELOPER THREAD\t"
    assert "MS4-KEEP-JUDGE" in codes(check(rec, root))


# ---- the licence is information only (owner, 2026-11-20 08:10 UTC) --------------------------------------------------

def test_a_final_record_without_any_licence_field_passes(root):
    rec = sign(good())
    for c in rec["candidates"]:
        for k in ("licence", "licence_source", "monetised_ok"):
            c.pop(k, None)
    assert check(rec, root).status == S.PASS


@pytest.mark.parametrize("junk", [5, [], {}, None, "", "unknown", "all rights reserved", "CC-BY-NC-ND-4.0", True], ids=repr)
def test_a_licence_text_of_any_kind_never_blocks(root, junk):
    rec = sign(good())
    rec["candidates"][0]["licence"] = junk
    rec["candidates"][1]["licence_source"] = junk
    assert check(rec, root).status == S.PASS


def test_a_non_commercial_candidate_can_be_adopted_enriched_or_kept_in_a_keep_ours_record(root):
    for choice in ("adopt", "enrich", "idea_only"):
        rec = good()
        rec["candidates"][1].update(licence="CC-BY-NC-SA-4.0", licence_source="none", monetised_ok=False)
        rec["decisions"][0]["choice"] = choice
        assert check(rec, root).status == S.PASS, choice
    rec = keep_good()
    for c in rec["candidates"]:
        c.update(licence="proprietary", licence_source="none", monetised_ok=False)
    assert check(rec, root).status == S.PASS


def test_no_gate_code_mentions_the_licence(root):
    """MS4-LICENCE was dropped (D-141): no error code and no source line may bring a licence check back."""
    src = (LG.__file__ and open(LG.__file__, encoding="utf-8").read())
    assert "MS4-LICENCE" not in src and "licence_source ==" not in src and "monetised_ok is False" not in src
    for fn in (good, keep_good):
        rec = fn()
        for c in rec["candidates"]:
            c.update(licence="none", licence_source="none", monetised_ok=False)
        assert not any("LICEN" in e.upper() for e in check(rec, root).errors)


# ---- mapping targets that try to point outside or at nothing ------------------------------------------------------------

@pytest.mark.parametrize("ref", ["skill/OVERLAY.md:0", "skill/OVERLAY.md:-1", "skill/OVERLAY.md:1:2", "skill:1", "skill/:1", ":1",
                                 "/etc/passwd:1", "../x:1", "skill/../../etc/passwd:1", "skill/OVERLAY.md:one", "skill/OVERLAY.md: 1"],
                         ids=repr)
def test_a_skill_line_that_points_nowhere_inside_the_repo_is_refused(root, ref):
    rec = good()
    rec["mapping"][0]["target"]["ref"] = ref
    assert "MS5-MAP-TARGET" in codes(check(rec, root))


def test_a_symlink_that_leaves_the_repo_is_refused(root, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "secret.md"
    outside.write_text("line one\n", encoding="utf-8")
    link = root / "skill" / "LINK.md"
    try:
        os.symlink(outside, link)
    except OSError:
        pytest.skip("no symlinks here")
    rec = good()
    rec["mapping"][0]["target"]["ref"] = "skill/LINK.md:1"
    assert "MS5-MAP-TARGET" in codes(check(rec, root))


def test_a_blank_line_is_not_a_mapping_target(root):
    (root / "skill" / "OVERLAY.md").write_text("# overlay\n\n   \nreal line\n", encoding="utf-8")
    for ref, ok in (("skill/OVERLAY.md:2", False), ("skill/OVERLAY.md:3", False), ("skill/OVERLAY.md:4", True)):
        rec = good()
        rec["mapping"][0]["target"]["ref"] = ref
        assert ("MS5-MAP-TARGET" not in codes(check(rec, root))) is ok, ref


# ---- files that are not records -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw", [b"", b"null", b"[]", b"5", b'"L9"', b"\xef\xbb\xbf{}", b"{}", b"\xff\xfe\x00", b'{"layer": "L9"}'], ids=repr)
def test_a_layer_file_that_is_not_a_record_is_a_block_not_an_exception(root, raw):
    d = root / "docs" / "layers"
    d.mkdir(parents=True)
    (d / "L9.json").write_bytes(raw)
    res = LG.check_layer("L9", root=root)
    assert res.status == S.BLOCK and res.errors


def test_a_directory_named_like_a_record_is_a_missing_record(root):
    (root / "docs" / "layers" / "L9.json").mkdir(parents=True)
    assert "LG-SCHEMA" in codes(LG.check_layer("L9", root=root))


@pytest.mark.parametrize("field", ["stars", "fit"])
def test_a_bool_is_not_a_number_for_stars_or_fit(root, field):
    rec = good()
    rec["candidates"][0][field] = True
    assert "MS2-CAND-FIELD" in codes(check(rec, root))


def test_few_candidates_reason_must_be_real_text(root):
    for reason in ("   ", 5, None, ["x"]):
        rec = good()
        rec["sub_questions"].append({"id": "SQ2", "text": "second", "few_candidates_reason": reason})
        rec["candidates"] += [_cand(4, "SQ2"), _cand(5, "SQ2")]
        rec["trials"].append({"id": "TR2", "sub_question": "SQ2", "status": "NOT_RUN", "not_run_reason": "x"})
        rec["decisions"].append({"sub_question": "SQ2", "choice": "adopt", "candidate_ids": ["C4"], "reason": "r", "evidence": []})
        assert "MS2-CAND-MIN" in codes(check(rec, root)), reason


def test_evidence_that_is_a_bare_string_does_not_crash_and_is_a_block(root):
    rec = good()
    rec["decisions"][0]["evidence"] = "TR1"
    res = check(rec, root)
    assert res.status == S.BLOCK


# ======================================================================================================================
# DEFECTS: the gate is wrong today. xfail(strict) = fails now, must pass after the fix, then drop the marker.
# ======================================================================================================================

# F1: a field of the wrong type crashes the gate with a TypeError instead of returning BLOCK ---------------------------------

CRASH = {
    "layer is a list": _set(["layer"], ["L9"]),
    "decision.sub_question is a list": _set(["decisions", 0, "sub_question"], ["SQ1"]),
    "decision.evidence is an int": _set(["decisions", 0, "evidence"], 5),
    "decision.candidate_ids holds a list": _set(["decisions", 0, "candidate_ids"], [["C2"]]),
    "decision.beats is an int (keep_ours)": _keep,
    "trial.sub_question is a list": _set(["trials", 0, "sub_question"], ["SQ1"]),
    "trial.candidate_ids holds a dict": _set(["trials", 0, "candidate_ids"], [{}]),
    "candidate.sub_question is a list": _set(["candidates", 0, "sub_question"], ["SQ1"]),
    "mapping.requirement is a list": _set(["mapping", 0, "requirement"], ["R1"]),
}


@pytest.mark.parametrize("name", list(CRASH), ids=list(CRASH))
def test_F1_a_field_of_the_wrong_type_is_a_block_never_an_exception(root, name):
    res = check(CRASH[name](good()), root)
    assert res.status == S.BLOCK and res.errors


def test_F1_one_malformed_record_does_not_hide_the_others(root):
    bad = sign(good())
    bad["decisions"][0]["evidence"] = 5
    write(root, bad, "L9")
    other = sign(good())
    other.update(layer="L10")
    write(root, other, "L10")
    results = {r.layer: r.status for r in LG.check_all(root=root)}
    assert results == {"L9": S.BLOCK, "L10": S.PASS}


# F2: a layer id outside the 33 is accepted and skips the group order ---------------------------------------------------------

@pytest.mark.parametrize("layer", ["L99", "L0", "L34", "X1"])
def test_F2_a_layer_outside_the_33_is_a_block(root, layer):
    rec = sign(good())
    rec.update(layer=layer, group=10)
    assert check(rec, root).status == S.BLOCK
    write(root, rec, layer)
    with pytest.raises((ContractError, NeedsReview)):
        LG.require_pass(layer, root=root)


# F3: three candidates with one url count as three public candidates ----------------------------------------------------------

def test_F3_the_same_url_three_times_is_not_three_candidates(root):
    rec = good()
    for c in rec["candidates"]:
        c["url"] = "https://github.com/someone/repo1"
    assert check(rec, root).status == S.BLOCK


def test_F3_keep_ours_cannot_count_one_repo_three_times(root):
    rec = keep_good()
    for c in rec["candidates"]:
        c["url"] = "https://github.com/someone/repo3"
    assert check(rec, root).status == S.BLOCK


# F4: a bool is accepted as a number in two more places (group, wave) ---------------------------------------------------------

def test_F4_a_bool_is_not_a_group(root):
    rec = good()
    rec["group"] = True
    assert "LG-SCHEMA" in codes(check(rec, root))


def test_F4_a_bool_is_not_a_wave(root):
    rec = good()
    rec["mapping"][0]["target"] = {"kind": "validator_planned", "ref": "VAL-X", "wave": True}
    assert "MS5-MAP-TARGET" in codes(check(rec, root))


# F5 (decided by the lead 2026-11-20 09:43: option b): a candidate the record itself marks state_of_the_art, that no
# trial ran and no NOT_RUN row names, lets the layer say PASS. The analyst's L16 draft is exactly this (SeedVR, CodeFormer). ---

def test_F5_an_unrun_state_of_the_art_candidate_keeps_the_layer_not_run(root):
    rec = good()
    rec["candidates"][0]["state_of_the_art"] = True          # C1 is marked best-in-class by the record itself
    rec["trials"][0]["candidate_ids"] = ["C2", "C3"]          # and the only RUN trial says it ran the other two
    res = check(rec, root)
    assert res.status == S.NOT_RUN, res.status
    assert any("state_of_the_art candidate C1" in n for n in res.not_run)


def test_F5_a_not_run_row_that_names_the_candidate_with_a_reason_lets_it_stand(root):
    rec = good()
    rec["candidates"][0]["state_of_the_art"] = True
    rec["trials"][0]["candidate_ids"] = ["C2", "C3"]
    rec["trials"].append({"id": "T9", "sub_question": rec["trials"][0]["sub_question"], "status": "NOT_RUN", "candidate_ids": ["C1"],
                          "not_run_reason": "needs a priced GPU run: asked in the owner thread 2026-11-20"})
    res = check(rec, root)
    assert res.status == S.PASS, (res.status, res.errors, res.not_run)


def test_F5_a_not_run_row_without_a_reason_does_not(root):
    rec = good()
    rec["candidates"][0]["state_of_the_art"] = True
    rec["trials"][0]["candidate_ids"] = ["C2", "C3"]
    rec["trials"].append({"id": "T9", "sub_question": rec["trials"][0]["sub_question"], "status": "NOT_RUN", "candidate_ids": ["C1"]})
    res = check(rec, root)
    assert res.status in (S.BLOCK, S.NOT_RUN)


def test_F5_a_run_trial_that_names_it_counts(root):
    rec = good()
    rec["candidates"][0]["state_of_the_art"] = True
    rec["trials"][0]["candidate_ids"] = ["C1", "C2", "C3"]
    assert check(rec, root).status == S.PASS


# F6 (low): formal checks that accept impossible values ----------------------------------------------------------------------

def test_F6_a_doc_candidate_needs_a_real_date(root):
    rec = good()
    rec["candidates"][0].update(kind="doc", retrieved="2026-99-99", commit=None, stars=None)
    assert "MS2-CAND-FIELD" in codes(check(rec, root))


def test_F6_a_candidate_url_needs_a_host(root):
    rec = good()
    rec["candidates"][0]["url"] = "https://"
    assert "MS2-CAND-FIELD" in codes(check(rec, root))


def test_F6_a_link_kind_must_be_file_or_page(root):
    rec = good()
    rec["trials"][0]["links"][0] = {"kind": "trust-me", "ref": "somewhere", "seen": "yes"}
    assert "MS3-TRIAL-FIELD" in codes(check(rec, root))


# the SHA constant is imported for parity with the sibling file; keep the import used
assert len(SHA) == 64 and json.dumps({})
