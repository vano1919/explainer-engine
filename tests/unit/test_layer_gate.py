"""MS-6 (skills team plan, 2026-11-20): ``governance/layer_gate`` refuses a layer record that skips a mandatory step.

One negative test per missing part of MS-1 .. MS-5, plus the NOT_RUN rule (a trial that was not run is never a pass), the
draft/final split, the CLI exit codes and a guard over the committed ``docs/layers`` records. $0, stdlib only."""
from __future__ import annotations

import copy
import json

import pytest

from _gov import ROOT
from explainer_engine.core.errors import ContractError, NeedsReview
from explainer_engine.governance import layer_gate as LG
from explainer_engine.qa import status as S

SHA = "a" * 64
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _cand(i: int, sq: str = "SQ1", *, ok: bool = True) -> dict:
    return {"id": f"C{i}", "sub_question": sq, "kind": "repo", "url": f"https://github.com/someone/repo{i}", "author": "someone",
            "stars": 100 * i, "commit": COMMIT, "licence": "MIT" if ok else "none", "monetised_ok": ok,
            "licence_source": f"https://github.com/someone/repo{i}/blob/{COMMIT}/LICENSE" if ok else "none",
            "teaches": "a structure for prompts", "fit": 4}


def good() -> dict:
    """A record that satisfies MS-1 .. MS-5 for one sub-question."""
    return {
        "schema": "layer_record/1", "layer": "L9", "name": "Gemini picture prompts", "group": 1, "state": "draft",
        "sub_questions": [{"id": "SQ1", "text": "how to name the film in the prompt"}],
        "requirements": [
            {"id": "R1", "text": "Task mode only, batches of 6", "source": {"kind": "message", "ref": "cmsg_01AbCdEf"}},
            {"id": "R2", "text": "name the film, no style description", "source": {"kind": "decision", "ref": "D-131"}},
        ],
        "tool_capabilities": [
            {"id": "T1", "tool": "Gemini chat", "capability": "reference images", "use": "used", "reason": "keeps the place steady"},
            {"id": "T2", "tool": "Gemini chat", "capability": "text in pictures", "use": "not_used", "reason": "no on-screen text"},
        ],
        "candidates": [_cand(1), _cand(2), _cand(3)],
        "trials": [{"id": "TR1", "sub_question": "SQ1", "status": "RUN", "looked_at_by": "team lead",
                    "observation": "B keeps the sky; A drifts in shot 4",
                    "links": [{"ref": "https://huggingface.co/x/y.jpg", "kind": "file", "sha256": SHA, "seen": "six frames, same square"}]}],
        "decisions": [{"sub_question": "SQ1", "choice": "enrich", "candidate_ids": ["C2"], "reason": "best structure",
                       "evidence": ["TR1"]}],
        "mapping": [
            {"requirement": "R1", "target": {"kind": "skill_line", "ref": "skill/OVERLAY.md:2"}},
            {"requirement": "R2", "target": {"kind": "sourced_rule", "ref": "BP-06"}},
            {"requirement": "T1", "target": {"kind": "skill_line", "ref": "skill/OVERLAY.md:1"}},
        ],
    }


@pytest.fixture
def root(tmp_path):
    (tmp_path / "skill").mkdir()
    (tmp_path / "skill" / "OVERLAY.md").write_text("# overlay\nTask mode only: batches of 6\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md").write_text("| D-131 | the v4.3 rebuild |\n| D-140 | x |\n", encoding="utf-8")
    reg = tmp_path / "explainer_engine" / "governance"      # a final record needs the owner's registry (REG-MISSING): one entry of a layer these tests do not use
    reg.mkdir(parents=True)
    (reg / "owner_requirements.json").write_text(json.dumps({"schema": "owner_requirements/1", "requirements": [{
        "id": "REQ-901", "words": "x", "date": "2026-11-20T08:00:00Z", "source": {"kind": "chat", "ref": "cmsg_01AbCdEf"},
        "layers": ["L33"], "status": "active", "check": {"kind": "unmapped"}}]}), encoding="utf-8")
    return tmp_path


def sign(rec, **extra):
    """Make a record final: the lead's signature and the MS-7 owner check."""
    rec.update(state="final", signed_by="team lead", signed_at="2026-11-20",
               owner_check=[{"url": "https://huggingface.co/datasets/x/y/blob/main/page.html", "sha256": SHA}], owner_seen="pending")
    rec.update(extra)
    return rec


def codes(res) -> set[str]:
    return {e.split(":", 1)[0] for e in res.errors}


def check(rec, root):
    return LG.check_record(rec, root=root)


def test_a_complete_record_passes(root):
    res = check(good(), root)
    assert res.status == S.PASS and res.errors == [] and S.is_success(res.status)


# ---- one negative test per missing part --------------------------------------------------------------------------------------

def mutate(path, value=LG, *, delete=False):
    def apply(rec):
        node = rec
        for k in path[:-1]:
            node = node[k]
        if delete:
            del node[path[-1]]
        else:
            node[path[-1]] = value
        return rec
    return apply


NEGATIVE = [
    # schema and identity
    ("schema", mutate(["schema"], "layer_record/0"), "LG-SCHEMA"),
    ("no layer", mutate(["layer"], delete=True), "LG-SCHEMA"),
    ("bad state", mutate(["state"], "done"), "LG-SCHEMA"),
    ("no sub-questions", mutate(["sub_questions"], []), "MS2-SUBQ"),
    # MS-1 requirements
    ("no requirements", mutate(["requirements"], []), "MS1-REQ-NONE"),
    ("requirement without source", mutate(["requirements", 0, "source"], delete=True), "MS1-REQ-SOURCE"),
    ("requirement source kind", mutate(["requirements", 0, "source", "kind"], "hearsay"), "MS1-REQ-SOURCE"),
    ("requirement message id", mutate(["requirements", 0, "source", "ref"], "my chat"), "MS1-REQ-SOURCE"),
    ("requirement decision id not in the log", mutate(["requirements", 1, "source", "ref"], "D-999"), "MS1-REQ-SOURCE"),
    ("requirement without text", mutate(["requirements", 0, "text"], ""), "MS1-REQ-FIELD"),
    # MS-1 tool capabilities
    ("no capabilities", mutate(["tool_capabilities"], []), "MS1-CAP-NONE"),
    ("capability use", mutate(["tool_capabilities", 0, "use"], "maybe"), "MS1-CAP-FIELD"),
    ("not-used capability without a reason", mutate(["tool_capabilities", 1, "reason"], " "), "MS1-CAP-FIELD"),
    ("used capability without a reason", mutate(["tool_capabilities", 0, "reason"], ""), "MS1-CAP-FIELD"),
    # MS-2 candidates
    ("two candidates only", lambda r: r.update(candidates=r["candidates"][:2]) or r, "MS2-CAND-MIN"),
    ("candidate without url", mutate(["candidates", 0, "url"], delete=True), "MS2-CAND-FIELD"),
    ("candidate url not https", mutate(["candidates", 0, "url"], "git@github.com:a/b"), "MS2-CAND-FIELD"),
    ("candidate without author", mutate(["candidates", 0, "author"], ""), "MS2-CAND-FIELD"),
    ("repo without stars", mutate(["candidates", 0, "stars"], None), "MS2-CAND-FIELD"),
    ("repo without commit", mutate(["candidates", 0, "commit"], delete=True), "MS2-CAND-FIELD"),
    ("commit not a hash", mutate(["candidates", 0, "commit"], "main"), "MS2-CAND-FIELD"),
    ("monetised flag not a bool", mutate(["candidates", 0, "monetised_ok"], "yes"), "MS2-CAND-FIELD"),
    ("candidate fit out of range", mutate(["candidates", 0, "fit"], 9), "MS2-CAND-FIELD"),
    ("candidate for an unknown sub-question", mutate(["candidates", 0, "sub_question"], "SQ9"), "MS2-CAND-FIELD"),
    ("duplicate candidate id", mutate(["candidates", 1, "id"], "C1"), "LG-DUP"),
    ("doc candidate without retrieved date", lambda r: r["candidates"][0].update(kind="doc", commit=None, stars=None) or r,
     "MS2-CAND-FIELD"),
    # MS-3 trials
    ("no trial for the sub-question", mutate(["trials"], []), "MS3-TRIAL-NONE"),
    ("trial status", mutate(["trials", 0, "status"], "PASS"), "MS3-TRIAL-FIELD"),
    ("trial not looked at", mutate(["trials", 0, "looked_at_by"], ""), "MS3-TRIAL-FIELD"),
    ("trial without observation", mutate(["trials", 0, "observation"], ""), "MS3-TRIAL-FIELD"),
    ("trial without links", mutate(["trials", 0, "links"], []), "MS3-TRIAL-FIELD"),
    ("link without a seen line", mutate(["trials", 0, "links", 0, "seen"], ""), "MS3-TRIAL-FIELD"),
    ("file link without sha256", mutate(["trials", 0, "links", 0, "sha256"], delete=True), "MS3-TRIAL-FIELD"),
    ("link sha256 not hex", mutate(["trials", 0, "links", 0, "sha256"], "xyz"), "MS3-TRIAL-FIELD"),
    # MS-4 decisions
    ("no decision", mutate(["decisions"], []), "MS4-DEC-MISSING"),
    ("two decisions for one sub-question", lambda r: r["decisions"].append(copy.deepcopy(r["decisions"][0])) or r, "MS4-DEC-FIELD"),
    ("decision choice", mutate(["decisions", 0, "choice"], "whatever"), "MS4-DEC-FIELD"),
    ("decision without reason", mutate(["decisions", 0, "reason"], ""), "MS4-DEC-FIELD"),
    ("adopting a candidate that names nothing", mutate(["decisions", 0, "candidate_ids"], []), "MS4-DEC-FIELD"),
    ("adopting an unknown candidate", mutate(["decisions", 0, "candidate_ids"], ["C77"]), "MS4-DEC-FIELD"),
    ("evidence names no trial", mutate(["decisions", 0, "evidence"], ["TR9"]), "MS4-DEC-FIELD"),
    ("keep_ours without evidence", lambda r: r["decisions"][0].update(choice="keep_ours", candidate_ids=[], evidence=[], beats=["C1", "C2", "C3"]) or r,
     "MS4-KEEP-EVIDENCE"),
    ("keep_ours that does not beat every candidate",
     lambda r: r["decisions"][0].update(choice="keep_ours", candidate_ids=[], beats=["C1", "C2"]) or r, "MS4-KEEP-EVIDENCE"),
    # MS-5 mapping
    ("no mapping", mutate(["mapping"], []), "MS5-MAP-MISSING"),
    ("a requirement is not mapped", lambda r: (r["mapping"].pop(1), r)[1], "MS5-MAP-MISSING"),
    ("a used capability is not mapped", lambda r: (r["mapping"].pop(2), r)[1], "MS5-MAP-MISSING"),
    ("mapping names an unknown requirement", mutate(["mapping", 0, "requirement"], "R9"), "MS5-MAP-TARGET"),
    ("mapping target kind", mutate(["mapping", 0, "target", "kind"], "vibes"), "MS5-MAP-TARGET"),
    ("skill line without a line number", mutate(["mapping", 0, "target", "ref"], "skill/OVERLAY.md"), "MS5-MAP-TARGET"),
    ("skill line of a missing file", mutate(["mapping", 0, "target", "ref"], "skill/NOPE.md:1"), "MS5-MAP-TARGET"),
    ("skill line past the end of the file", mutate(["mapping", 0, "target", "ref"], "skill/OVERLAY.md:99"), "MS5-MAP-TARGET"),
    ("skill line outside the repo", mutate(["mapping", 0, "target", "ref"], "../x.md:1"), "MS5-MAP-TARGET"),
    ("validator rule that does not exist", mutate(["mapping", 0, "target"], {"kind": "validator", "ref": "VAL-NOPE-99"}),
     "MS5-MAP-TARGET"),
    ("sourced rule that does not exist", mutate(["mapping", 1, "target", "ref"], "BP-99999"), "MS5-MAP-TARGET"),
]


@pytest.mark.parametrize("name,fn,code", NEGATIVE, ids=[n[0] for n in NEGATIVE])
def test_every_missing_part_is_refused(root, name, fn, code):
    res = check(fn(good()), root)
    assert code in codes(res), res.errors
    assert res.status == S.BLOCK and not S.is_success(res.status)


def test_few_candidates_allowed_for_one_sub_question_only_with_a_reason(root):
    rec = good()
    rec["sub_questions"].append({"id": "SQ2", "text": "the second question"})
    rec["candidates"] += [_cand(4, "SQ2"), _cand(5, "SQ2")]
    rec["trials"].append({"id": "TR2", "sub_question": "SQ2", "status": "NOT_RUN", "not_run_reason": "no GPU today"})
    rec["decisions"].append({"sub_question": "SQ2", "choice": "adopt", "candidate_ids": ["C4"], "reason": "only two exist",
                             "evidence": []})
    assert "MS2-CAND-MIN" in codes(check(rec, root))
    rec["sub_questions"][1]["few_candidates_reason"] = "only two public repos do this at all"
    assert "MS2-CAND-MIN" not in codes(check(rec, root))


# ---- NOT_RUN is never a pass --------------------------------------------------------------------------------------------------

def test_a_trial_that_was_not_run_makes_the_layer_not_run_never_pass(root):
    rec = good()
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "the owner's Chrome was not reachable"}
    rec["decisions"][0]["evidence"] = []
    res = check(rec, root)
    assert res.errors == [] and res.status == S.NOT_RUN and not S.is_success(res.status)
    assert any("SQ1" in n for n in res.not_run)


def test_not_run_trial_needs_its_reason(root):
    rec = good()
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN"}
    assert "MS3-TRIAL-FIELD" in codes(check(rec, root))


def test_keep_ours_cannot_rest_on_a_trial_that_was_not_run(root):
    rec = good()
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no GPU"}
    rec["decisions"][0].update(choice="keep_ours", candidate_ids=[], beats=["C1", "C2", "C3"], evidence=["TR1"])
    assert "MS4-KEEP-EVIDENCE" in codes(check(rec, root))


def test_the_old_keep_ours_record_is_now_refused(root):
    """T1.0's keep_ours (one run trial, beats everyone) lacks (a), (b), (c), (d) and (e) of the owner's MS-4 rule."""
    rec = good()
    rec["decisions"][0].update(choice="keep_ours", candidate_ids=[], beats=["C1", "C2", "C3"], evidence=["TR1"])
    res = check(rec, root)
    assert res.status == S.BLOCK
    assert {"MS4-KEEP-REQ", "MS4-KEEP-RUN3", "MS4-KEEP-SOTA", "MS4-KEEP-JUDGE", "MS4-KEEP-OWNER"} <= codes(res)


# ---- licence is information only (the owner, 2026-11-20 08:10 UTC, cmsg_01Hnu5zB86sjUj5GtTgaUkPW4g2aaMZ4SAJQUbEgZGWoPM) ----------

def test_a_candidate_may_leave_every_licence_field_out(root):
    rec = good()
    for c in rec["candidates"]:
        for k in ("licence", "licence_source", "monetised_ok"):
            c.pop(k)
    assert check(rec, root).status == S.PASS


def test_a_licence_never_excludes_a_candidate(root):
    rec = good()
    rec["candidates"][1].update(licence="CC-BY-NC-SA", licence_source="none", monetised_ok=False)
    res = check(rec, root)                       # enrich of a non-commercial candidate: allowed
    assert res.status == S.PASS and "MS4-LICENCE" not in codes(res)
    rec["candidates"][0].update(licence_source="none", monetised_ok=True)
    assert check(rec, root).status == S.PASS     # "none" no longer forces anything
    rec["decisions"][0]["choice"] = "idea_only"  # idea_only stays a choice, for any candidate
    assert check(rec, root).status == S.PASS


def test_a_monetised_flag_that_is_present_must_still_be_a_bool(root):
    rec = good()
    rec["candidates"][0]["monetised_ok"] = "yes"
    assert "MS2-CAND-FIELD" in codes(check(rec, root))


# ---- mapping targets ----------------------------------------------------------------------------------------------------------

def test_a_validator_target_is_checked_against_the_registry(root):
    from explainer_engine import validators
    rid = sorted(validators.rule_index())[0]
    rec = good()
    rec["mapping"][0]["target"] = {"kind": "validator", "ref": rid}
    assert check(rec, root).status == S.PASS


def test_a_planned_validator_is_allowed_unless_strict(root):
    rec = good()
    rec["mapping"][0]["target"] = {"kind": "validator_planned", "ref": "VAL-PRO-01", "wave": 2}
    res = check(rec, root)
    assert res.status == S.PASS and any("VAL-PRO-01" in n for n in res.planned)
    strict = LG.check_record(rec, root=root, strict=True)
    assert "MS5-MAP-TARGET" in codes(strict) and strict.status == S.BLOCK


def test_a_planned_validator_needs_its_wave(root):
    rec = good()
    rec["mapping"][0]["target"] = {"kind": "validator_planned", "ref": "VAL-PRO-01"}
    assert "MS5-MAP-TARGET" in codes(check(rec, root))


# ---- files, draft and final, the require step ---------------------------------------------------------------------------------

def write(root, rec, layer="L9"):
    d = root / "docs" / "layers"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{layer}.json").write_text(json.dumps(rec), encoding="utf-8")


def test_a_missing_record_is_a_block(root):
    res = LG.check_layer("L9", root=root)
    assert res.status == S.BLOCK and "LG-SCHEMA" in codes(res)


def test_the_file_name_must_match_the_layer(root):
    write(root, good(), layer="L10")
    assert "LG-SCHEMA" in codes(LG.check_layer("L10", root=root))


def test_a_file_that_is_not_json_is_a_block(root):
    d = root / "docs" / "layers"
    d.mkdir(parents=True)
    (d / "L9.json").write_text("{not json", encoding="utf-8")
    assert "LG-SCHEMA" in codes(LG.check_layer("L9", root=root))


def test_final_needs_the_leads_signature(root):
    rec = sign(good())
    del rec["signed_by"]
    assert "LG-SIGN" in codes(check(rec, root))
    rec["signed_by"] = "team lead"
    assert check(rec, root).status == S.PASS


def test_require_pass_refuses_a_draft_a_block_and_a_not_run(root):
    rec = good()
    write(root, rec)
    with pytest.raises(ContractError, match="draft"):
        LG.require_pass("L9", root=root)
    sign(rec)
    write(root, rec)
    LG.require_pass("L9", root=root)                                 # a signed, complete record passes
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no GPU"}
    rec["decisions"][0]["evidence"] = []
    write(root, rec)
    with pytest.raises(NeedsReview, match="NOT_RUN"):
        LG.require_pass("L9", root=root)
    rec["requirements"] = []
    write(root, rec)
    with pytest.raises(ContractError, match="MS1-REQ-NONE"):
        LG.require_pass("L9", root=root)


def test_check_all_fails_for_a_final_block_but_not_for_a_draft(root):
    draft = good()
    draft["requirements"] = []
    write(root, draft, "L9")
    final = good()
    final.update(layer="L10")
    sign(final)
    write(root, final, "L10")
    results = LG.check_all(root=root)
    assert {r.layer: r.status for r in results} == {"L9": S.BLOCK, "L10": S.PASS}
    assert LG.problems(results) == []                                # the broken one is a draft: reported, not failing
    final["requirements"] = []
    write(root, final, "L10")
    assert any("L10" in p and "MS1-REQ-NONE" in p for p in LG.problems(LG.check_all(root=root)))


def test_check_all_without_a_layers_folder_is_empty(root):
    assert LG.check_all(root=root) == []


def test_cli_exit_codes(root, capsys, monkeypatch):
    from explainer_engine.governance import __main__ as cli
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    (root / "config").mkdir()
    (root / "config" / "model_routing.json").write_text((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"), encoding="utf-8")
    write(root, good())
    assert cli.main(["layers", "--layer", "L9"]) == 0
    assert "L9: PASS" in capsys.readouterr().out
    bad = good()
    bad["requirements"] = []
    write(root, bad)
    assert cli.main(["layers", "--layer", "L9"]) == 1
    assert "MS1-REQ-NONE" in capsys.readouterr().out
    nr = good()
    nr["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "no GPU"}
    nr["decisions"][0]["evidence"] = []
    write(root, nr)
    assert cli.main(["layers", "--layer", "L9"]) == 2



# ---- MS-7 owner check (final records) -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("name,fn,code", [
    ("no owner_check", lambda r: r.pop("owner_check") and r, "LG-OWNER"),
    ("empty owner_check", lambda r: r.update(owner_check=[]) or r, "LG-OWNER"),
    ("owner_check entry with neither url nor sha256", lambda r: r.update(owner_check=[{"note": "x"}]) or r, "LG-OWNER"),
    ("owner_check url not https", lambda r: r.update(owner_check=[{"url": "ftp://x"}]) or r, "LG-OWNER"),
    ("owner_check sha256 not hex", lambda r: r.update(owner_check=[{"sha256": "zz"}]) or r, "LG-OWNER"),
    ("no owner_seen", lambda r: r.pop("owner_seen") and r, "LG-OWNER"),
    ("owner_seen is neither a message id nor pending", lambda r: r.update(owner_seen="yes") or r, "LG-OWNER"),
], ids=lambda v: v if isinstance(v, str) and " " in v else None)
def test_a_final_record_needs_the_owner_check(root, name, fn, code):
    res = check(fn(sign(good())), root)
    assert code in codes(res) and res.status == S.BLOCK


def test_a_draft_does_not_need_the_owner_check(root):
    assert check(good(), root).status == S.PASS


def test_owner_check_by_url_or_by_sha256_alone_is_enough(root):
    rec = sign(good())
    rec["owner_check"] = [{"url": "https://huggingface.co/x"}, {"sha256": SHA}]
    assert check(rec, root).errors == []


def test_pending_owner_seen_is_reported_never_silent(root, capsys, monkeypatch):
    from explainer_engine.governance import __main__ as cli
    rec = sign(good())
    res = check(rec, root)
    assert res.status == S.PASS and any("owner_seen" in n for n in res.pending)
    rec["owner_seen"] = "cmsg_01AbCd"
    assert check(rec, root).pending == []
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    (root / "config").mkdir()
    (root / "config" / "model_routing.json").write_text((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"), encoding="utf-8")
    write(root, sign(good()))
    assert cli.main(["layers", "--layer", "L9"]) == 0
    assert "pending" in capsys.readouterr().out


def test_a_not_used_capability_without_a_reason_blocks(root):
    rec = good()
    del rec["tool_capabilities"][1]["reason"]
    res = check(rec, root)
    assert "MS1-CAP-FIELD" in codes(res) and res.status == S.BLOCK


# ---- group order (team plan section 3) ----------------------------------------------------------------------------------------

def _write_group1(root, *, final_layers):
    for layer in LG.GROUPS[1]:
        rec = good()
        rec["layer"] = layer
        if layer in final_layers:
            sign(rec)
        write(root, rec, layer)


def _other(layer, group):
    rec = sign(good())
    rec.update(layer=layer, group=group)
    return rec


def test_the_groups_cover_the_33_layers_once():
    flat = [l for g in LG.GROUPS.values() for l in g]
    assert sorted(flat, key=lambda x: int(x[1:])) == [f"L{i}" for i in range(1, 34)] and len(set(flat)) == 33
    assert sorted(LG.GROUPS) == list(range(1, 11))


def test_a_record_must_sit_in_its_layers_group(root):
    rec = good()
    rec["group"] = 2
    assert "LG-SCHEMA" in codes(check(rec, root))


def test_require_pass_waits_while_a_lower_group_is_not_final(root):
    _write_group1(root, final_layers={"L9", "L10", "L11"})          # L16 stays a draft
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L16"):
        LG.require_pass("L12", root=root)
    rec = sign(good())
    rec["layer"] = "L16"
    write(root, rec, "L16")
    LG.require_pass("L12", root=root)


def test_a_lower_group_layer_without_a_record_also_holds_the_next_group_back(root):
    _write_group1(root, final_layers={"L9", "L10", "L11", "L16"})
    (root / "docs" / "layers" / "L11.json").unlink()
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L11"):
        LG.require_pass("L12", root=root)


def test_a_final_block_does_not_open_the_next_group(root):
    _write_group1(root, final_layers={"L9", "L10", "L11", "L16"})
    broken = sign(good())
    broken.update(layer="L9", requirements=[])
    write(root, broken, "L9")
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L9"):
        LG.require_pass("L12", root=root)


def test_group_one_has_no_lower_group_to_wait_for(root):
    _write_group1(root, final_layers={"L9"})
    LG.require_pass("L9", root=root)


def test_group_report_says_per_group_whether_it_is_open(root, capsys, monkeypatch):
    from explainer_engine.governance import __main__ as cli
    _write_group1(root, final_layers={"L9", "L10", "L11"})
    write(root, _other("L12", 2), "L12")
    rows = {r["group"]: r for r in LG.group_report(root=root)}
    assert rows[1]["open"] == ["L16"] and rows[1]["ready"] is False
    assert rows[2]["waiting_on"] == [1] and "L16" in rows[2]["waiting_layers"]
    assert rows[3]["waiting_on"] == [1, 2]
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    (root / "config").mkdir()
    (root / "config" / "model_routing.json").write_text((ROOT / "config" / "model_routing.json").read_text(encoding="utf-8"), encoding="utf-8")
    cli.main(["layers"])
    out = capsys.readouterr().out
    assert "group 1:" in out and "L16" in out and "group 2: waiting on group 1" in out


def test_the_layers_folder_has_its_readme():
    text = (ROOT / "docs" / "layers" / "README.md").read_text(encoding="utf-8")
    assert "LAYER_GATE.md" in text



# ---- keep_ours: the owner's rule (a)..(e), 2026-11-20 08:07 UTC (REOPEN_S10_AND_MS4, section 6) ------------------------------

def _file(ref="https://huggingface.co/datasets/x/y/blob/main/f.json"):
    return {"ref": ref, "sha256": SHA}


def keep_good() -> dict:
    """A record whose sub-question may say keep_ours: all of (a)-(e) hold."""
    rec = good()
    for r in rec["requirements"]:
        r["ours_meets"] = True
    c = rec["candidates"]
    c.append(_cand(4))
    c[3]["stars"] = 50                                           # a fourth candidate that was not run
    for row in c[:3]:
        row.update(configured_per=f"https://docs.example.org/{row['id']}", config_log=_file())
    c[2]["stars"] = 900                                          # the most-starred one, run
    c[1]["state_of_the_art"] = True
    rec["trials"][0].update(candidate_ids=["C1", "C2", "C3"], config_ok=True)
    rec["decisions"][0] = {
        "sub_question": "SQ1", "choice": "keep_ours", "candidate_ids": [], "reason": "ours scored highest, blind",
        "evidence": ["TR1"], "beats": ["C1", "C2", "C3", "C4"], "ours_author": "developer thread",
        "blind_judge": {"judge": "fresh reviewer", "wrote_our_code": False, "labels_sealed": _file(),
                        "labels_sealed_before_scoring": True, "scores": _file(), "method": "rubric 1-5, sealed random labels"}}
    rec["owner_seen"] = "cmsg_01OwnerSawIt"
    return rec


def _dec(r):
    return r["decisions"][0]


KEEP_NEGATIVE = [
    # (a) ours meets every requirement, no open complaint
    ("ours_meets false", lambda r: r["requirements"][0].update(ours_meets=False) or r, "MS4-KEEP-REQ"),
    ("ours_meets missing", lambda r: r["requirements"][1].pop("ours_meets") and r, "MS4-KEEP-REQ"),
    ("an open complaint", lambda r: r["requirements"][0].update(complaint={"open": True}) or r, "MS4-KEEP-REQ"),
    ("a complaint without fix_seen", lambda r: r["requirements"][0].update(complaint={"open": False}) or r, "MS4-KEEP-REQ"),
    ("a complaint whose fix_seen is not a message id",
     lambda r: r["requirements"][0].update(complaint={"open": False, "fix_seen": "yes"}) or r, "MS4-KEEP-REQ"),
    # (b) three strong candidates were run
    ("two candidates run", lambda r: r["trials"][0].update(candidate_ids=["C2", "C3"]) or r, "MS4-KEEP-RUN3"),
    ("the same candidate named three times", lambda r: r["trials"][0].update(candidate_ids=["C3", "C3", "C3"]) or r, "MS4-KEEP-RUN3"),
    ("the trial names no candidates", lambda r: r["trials"][0].pop("candidate_ids") and r, "MS4-KEEP-RUN3"),
    ("the trial was not run", lambda r: r["trials"][0].update(status="NOT_RUN", not_run_reason="no cpu", candidate_ids=[]) or r, "MS4-KEEP-RUN3"),
    ("the trial config was bad", lambda r: r["trials"][0].update(config_ok=False) or r, "MS4-KEEP-RUN3"),
    ("most-starred candidate was not run", lambda r: r["candidates"][3].update(stars=5000) or r, "MS4-KEEP-TOP"),
    ("a doc candidate marked top was not run",
     lambda r: r["candidates"][3].update(kind="doc", stars=None, commit=None, retrieved="2026-11-20", top=True) or r, "MS4-KEEP-TOP"),
    ("no candidate is state of the art", lambda r: r["candidates"][1].pop("state_of_the_art") and r, "MS4-KEEP-SOTA"),
    ("the state of the art candidate was not run",
     lambda r: (r["candidates"][1].pop("state_of_the_art"), r["candidates"][3].update(state_of_the_art=True), r)[2], "MS4-KEEP-SOTA"),
    # (c) each configured per its own docs, with a log
    ("no configured_per", lambda r: r["candidates"][0].pop("configured_per") and r, "MS4-KEEP-CONFIG"),
    ("configured_per not https", lambda r: r["candidates"][0].update(configured_per="the readme") or r, "MS4-KEEP-CONFIG"),
    ("no config_log", lambda r: r["candidates"][1].pop("config_log") and r, "MS4-KEEP-CONFIG"),
    ("config_log without sha256", lambda r: r["candidates"][2].update(config_log={"ref": "https://x.org/log"}) or r, "MS4-KEEP-CONFIG"),
    # (d) a blind judge who did not write our code
    ("no ours_author", lambda r: _dec(r).pop("ours_author") and r, "MS4-KEEP-JUDGE"),
    ("no blind_judge", lambda r: _dec(r).pop("blind_judge") and r, "MS4-KEEP-JUDGE"),
    ("the judge wrote our code", lambda r: _dec(r)["blind_judge"].update(wrote_our_code=True) or r, "MS4-KEEP-JUDGE"),
    ("wrote_our_code missing", lambda r: (_dec(r)["blind_judge"].pop("wrote_our_code"), r)[1], "MS4-KEEP-JUDGE"),
    ("the judge is the author", lambda r: _dec(r)["blind_judge"].update(judge=" Developer Thread ") or r, "MS4-KEEP-JUDGE"),
    ("labels not sealed before scoring", lambda r: _dec(r)["blind_judge"].update(labels_sealed_before_scoring=False) or r, "MS4-KEEP-JUDGE"),
    ("no sealed labels file", lambda r: _dec(r)["blind_judge"].pop("labels_sealed") and r, "MS4-KEEP-JUDGE"),
    ("sealed labels without sha256", lambda r: _dec(r)["blind_judge"].update(labels_sealed={"ref": "https://x.org/k"}) or r, "MS4-KEEP-JUDGE"),
    ("no scores file", lambda r: _dec(r)["blind_judge"].pop("scores") and r, "MS4-KEEP-JUDGE"),
    ("scores sha256 not hex", lambda r: _dec(r)["blind_judge"].update(scores={"ref": "https://x.org/s", "sha256": "zz"}) or r, "MS4-KEEP-JUDGE"),
    ("no method", lambda r: _dec(r)["blind_judge"].update(method=" ") or r, "MS4-KEEP-JUDGE"),
    # (e) the owner saw the side-by-side
    ("owner_seen pending", lambda r: r.update(owner_seen="pending") or r, "MS4-KEEP-OWNER"),
    ("owner_seen missing", lambda r: r.pop("owner_seen") and r, "MS4-KEEP-OWNER"),
    ("owner_seen not a message id", lambda r: r.update(owner_seen="he agreed") or r, "MS4-KEEP-OWNER"),
]


def test_a_keep_ours_record_that_meets_a_to_e_passes(root):
    res = check(keep_good(), root)
    assert res.errors == [] and res.status == S.PASS


@pytest.mark.parametrize("name,fn,code", KEEP_NEGATIVE, ids=[n[0] for n in KEEP_NEGATIVE])
def test_keep_ours_is_refused_unless_all_of_a_to_e_hold(root, name, fn, code):
    res = check(fn(keep_good()), root)
    assert code in codes(res), res.errors
    assert res.status == S.BLOCK


def test_every_keep_code_has_a_negative_test():
    needed = {"MS4-KEEP-REQ", "MS4-KEEP-RUN3", "MS4-KEEP-TOP", "MS4-KEEP-SOTA", "MS4-KEEP-CONFIG", "MS4-KEEP-JUDGE", "MS4-KEEP-OWNER"}
    assert needed == {c for _, _, c in KEEP_NEGATIVE}


def test_the_keep_rules_do_not_touch_adopt_and_enrich(root):
    rec = good()                                   # enrich, ours_meets absent, owner_seen absent, no judge: still PASS
    assert check(rec, root).status == S.PASS
    rec["owner_seen"] = "pending"
    assert check(rec, root).status == S.PASS


def test_a_bad_config_trial_counts_as_not_run_for_the_layer_status(root):
    rec = good()
    rec["trials"][0].update(candidate_ids=["C1"], config_ok=False)
    rec["decisions"][0]["evidence"] = []
    res = check(rec, root)
    assert res.status == S.NOT_RUN and res.errors == []


def test_trial_candidate_ids_must_name_candidates_of_the_sub_question(root):
    rec = good()
    rec["trials"][0]["candidate_ids"] = ["C77"]
    assert "MS3-TRIAL-FIELD" in codes(check(rec, root))
    rec["trials"][0].update(candidate_ids=["C1"], config_ok="yes")
    assert "MS3-TRIAL-FIELD" in codes(check(rec, root))


def test_the_doc_has_the_five_rules_and_an_example_that_matches_the_gate(root):
    text = (ROOT / "docs" / "LAYER_GATE.md").read_text(encoding="utf-8")
    for token in ("MS4-KEEP-REQ", "MS4-KEEP-RUN3", "MS4-KEEP-TOP", "MS4-KEEP-SOTA", "MS4-KEEP-CONFIG", "MS4-KEEP-JUDGE",
                  "MS4-KEEP-OWNER", "not_run_waiver"):
        assert token in text
    block = text.split("```json", 1)[1].split("```", 1)[0]
    example = json.loads(block)
    assert example["choice"] == "keep_ours" and example["blind_judge"]["wrote_our_code"] is False
    assert set(keep_good()["decisions"][0]) == set(example)


# ---- group order: a final NOT_RUN opens the next group only with the owner's waiver --------------------------------------------

def _not_run_final(layer="L16"):
    rec = sign(good())
    rec.update(layer=layer)
    rec["trials"][0] = {"id": "TR1", "sub_question": "SQ1", "status": "NOT_RUN", "not_run_reason": "needs the owner's Chrome"}
    rec["decisions"][0]["evidence"] = []
    return rec


def test_a_final_not_run_does_not_open_the_next_group_without_a_waiver(root):
    _write_group1(root, final_layers={"L9", "L10", "L11"})
    write(root, _not_run_final("L16"), "L16")
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L16"):
        LG.require_pass("L12", root=root)
    assert {r["group"]: r["ready"] for r in LG.group_report(root=root)}[1] is False


def test_a_not_run_waiver_with_the_owners_message_id_opens_it(root):
    _write_group1(root, final_layers={"L9", "L10", "L11"})
    rec = _not_run_final("L16")
    rec["not_run_waiver"] = "cmsg_01OwnerWord"
    write(root, rec, "L16")
    write(root, _other("L12", 2), "L12")
    LG.require_pass("L12", root=root)
    assert {r["group"]: r["ready"] for r in LG.group_report(root=root)}[1] is True


def test_a_waiver_must_be_a_message_id_and_never_opens_a_block(root):
    rec = _not_run_final("L16")
    rec["not_run_waiver"] = "he said fine"
    assert "LG-OWNER" in codes(check(rec, root))
    _write_group1(root, final_layers={"L9", "L10", "L11"})
    blocked = sign(good())
    blocked.update(layer="L16", requirements=[], not_run_waiver="cmsg_01OwnerWord")
    write(root, blocked, "L16")
    write(root, _other("L12", 2), "L12")
    with pytest.raises(NeedsReview, match="L16"):
        LG.require_pass("L12", root=root)


# ---- the committed records ---------------------------------------------------------------------------------------------------

def test_every_final_record_in_the_repo_is_not_a_block():
    """A committed record that claims to be final must keep MS-1 .. MS-5 (drafts are reported only)."""
    assert LG.problems(LG.check_all(root=ROOT)) == []


# ---- mutmut survivors of the tester (2026-11-20 09:10): strict, the fixed complaint, the error text ----------------------------------

def test_a_fixed_complaint_with_the_owners_message_id_lets_keep_ours_pass(root):
    rec = keep_good()
    rec["requirements"][0]["complaint"] = {"open": False, "fix_seen": "cmsg_01OwnerSawTheFix"}
    res = check(rec, root)
    assert "MS4-KEEP-REQ" not in codes(res) and res.status == S.PASS
    rec["requirements"][0]["complaint"] = {"open": True, "fix_seen": "cmsg_01OwnerSawTheFix"}      # fixed only when open is exactly false
    assert "MS4-KEEP-REQ" in codes(check(rec, root))
    rec["requirements"][0]["complaint"] = {"open": False, "fix_seen": None}
    assert "MS4-KEEP-REQ" in codes(check(rec, root))


def test_a_keep_ours_error_names_its_sub_question_and_requirement(root):
    rec = keep_good()
    rec["requirements"][0].update(ours_meets=False)
    errs = [e for e in check(rec, root).errors if e.startswith("MS4-KEEP-REQ")]
    assert errs and "decision for SQ1" in errs[0] and rec["requirements"][0]["id"] in errs[0]


def test_require_pass_and_check_all_take_strict_and_refuse_a_planned_validator(root):
    rec = good()
    rec["mapping"][0]["target"] = {"kind": "validator_planned", "ref": "VAL-PRO-01", "wave": 2}
    sign(rec)
    write(root, rec)
    LG.require_pass("L9", root=root)                                       # not strict: a planned validator is allowed
    LG.require_pass("L9", root=root, strict=False)
    with pytest.raises(ContractError, match="MS5-MAP-TARGET"):
        LG.require_pass("L9", root=root, strict=True)
    assert {r.layer: r.status for r in LG.check_all(root=root)} == {"L9": S.PASS}
    assert {r.layer: r.status for r in LG.check_all(root=root, strict=True)} == {"L9": S.BLOCK}
    assert LG.check_layer("L9", root=root, strict=True).status == S.BLOCK
