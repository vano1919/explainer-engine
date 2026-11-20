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
    return tmp_path


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
    ("candidate without licence", mutate(["candidates", 0, "licence"], ""), "MS2-CAND-FIELD"),
    ("monetised flag missing", mutate(["candidates", 0, "monetised_ok"], delete=True), "MS2-CAND-FIELD"),
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
    ("adopting a candidate whose licence refuses a monetised channel",
     lambda r: r["candidates"][1].update(monetised_ok=False, licence="CC-BY-NC") or r, "MS4-LICENCE"),
    ("idea_only for a candidate that is allowed", mutate(["decisions", 0, "choice"], "idea_only"), "MS4-LICENCE"),
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


def test_keep_ours_passes_when_a_run_trial_beats_every_candidate(root):
    rec = good()
    rec["decisions"][0].update(choice="keep_ours", candidate_ids=[], beats=["C1", "C2", "C3"], evidence=["TR1"])
    assert check(rec, root).status == S.PASS


def test_idea_only_for_a_candidate_without_a_monetised_licence(root):
    rec = good()
    rec["candidates"][1].update(monetised_ok=False, licence="none")
    rec["decisions"][0].update(choice="idea_only", candidate_ids=["C2"])
    assert check(rec, root).status == S.PASS


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
    rec = good()
    rec["state"] = "final"
    assert "LG-SIGN" in codes(check(rec, root))
    rec["signed_by"], rec["signed_at"] = "team lead", "2026-11-20"
    assert check(rec, root).status == S.PASS


def test_require_pass_refuses_a_draft_a_block_and_a_not_run(root):
    rec = good()
    write(root, rec)
    with pytest.raises(ContractError, match="draft"):
        LG.require_pass("L9", root=root)
    rec["state"], rec["signed_by"], rec["signed_at"] = "final", "team lead", "2026-11-20"
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
    final.update(layer="L10", state="final", signed_by="team lead", signed_at="2026-11-20")
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


# ---- the committed records ---------------------------------------------------------------------------------------------------

def test_every_final_record_in_the_repo_is_not_a_block():
    """A committed record that claims to be final must keep MS-1 .. MS-5 (drafts are reported only)."""
    assert LG.problems(LG.check_all(root=ROOT)) == []
