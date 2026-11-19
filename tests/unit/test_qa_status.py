"""W2 (final plan P-7): the one QA status vocabulary, NOT_RUN and REVIEW never counted as success, and the runner's
REVIEW -> CREATOR_APPROVAL path (GO_ON = (PASS,)) with an approval bound to the stage record's input hash."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import run as RUN
from explainer_engine.qa import gates as G
from explainer_engine.qa import status as ST

ROOT = Path(__file__).resolve().parents[2]
TOBA = ROOT / "episodes" / "ep_toba"


# --- the vocabulary ---------------------------------------------------------------------------------------------------

def test_the_vocabulary_is_exactly_five_statuses():
    assert ST.ALL == ("PASS", "REVIEW", "RETRY", "BLOCK", "NOT_RUN")


def test_only_pass_is_a_success():
    assert ST.is_success(ST.PASS)
    for s in (ST.REVIEW, ST.RETRY, ST.BLOCK, ST.NOT_RUN, "FAIL", "INCOMPLETE", None, "bogus"):
        assert not ST.is_success(s), s


def test_fail_is_the_legacy_spelling_of_block():
    assert ST.canon("FAIL") == ST.BLOCK and ST.is_block("FAIL") and ST.is_block(ST.BLOCK)
    assert G.BLOCK == G.FAIL and ST.canon("INCOMPLETE") == ST.NOT_RUN
    with pytest.raises(ValueError):
        ST.canon("MAYBE")


def test_rollup_worst_wins_and_empty_is_not_run_never_pass():
    assert ST.rollup([]) == ST.NOT_RUN
    assert ST.rollup([ST.PASS, ST.PASS]) == ST.PASS
    assert ST.rollup([ST.PASS, ST.REVIEW]) == ST.REVIEW
    assert ST.rollup([ST.REVIEW, ST.NOT_RUN]) == ST.NOT_RUN
    assert ST.rollup([ST.NOT_RUN, ST.RETRY]) == ST.RETRY
    assert ST.rollup([ST.RETRY, "FAIL", ST.PASS]) == ST.BLOCK
    assert ST.rollup([{"status": ST.PASS}, {"status": ST.NOT_RUN}]) == ST.NOT_RUN


def test_gate_rows_carry_retry_and_block_and_the_verdict_rolls_them_up():
    r = G.row("clip_ok", False, "motion artefact", level=G.RETRY)
    assert r["status"] == ST.RETRY
    b = G.row("clip_ok", False, "no retry left", level=ST.BLOCK)
    assert b["status"] == "FAIL" and ST.is_block(b["status"])      # the wire string of BLOCK is the legacy "FAIL"
    assert G.verdict([G.row("a", True, ""), r])["status"] == ST.RETRY
    assert G.verdict([r, b])["status"] == G.FAIL
    assert G.verdict([G.row("a", True, ""), G.row("b", None, "no tool")])["status"] != ST.PASS
    with pytest.raises(ValueError):
        G.row("x", False, "", level="MAYBE")


def test_not_run_and_review_rows_never_make_a_pass_verdict():
    for rows in ([G.row("a", None, "ffmpeg absent")], [G.row("a", False, "taste", level=G.REVIEW)],
                 [G.row("a", True, ""), G.row("b", None, "x")]):
        assert not ST.is_success(G.verdict(rows)["status"])


# --- the runner: GO_ON = (PASS,) and REVIEW -> CREATOR_APPROVAL ---------------------------------------------------------

def _episode(tmp_path: Path) -> Path:
    root = tmp_path / "ep_toba"
    (root / "story").mkdir(parents=True)
    shutil.copy(TOBA / "episode.json", root / "episode.json")
    shutil.copy(TOBA / "story" / "production_script.json", root / "story" / "production_script.json")
    return root


def _fake(status_by_stage: dict, not_run_in: str | None = None):
    def make(stage):
        def fn(ep, rehearsal):
            st = status_by_stage.get(stage, G.PASS)
            rows = [G.row(f"{stage}_gate", st == G.PASS, "fake", level=G.REVIEW if st == G.REVIEW else G.FAIL)]
            if not_run_in == stage:
                rows.append(G.row(f"{stage}_unmeasured", None, "NOT_RUN: ffmpeg is absent"))
            return rows, {"n": 1}
        return fn
    return {s: make(s) for s in RUN.STAGES}


@pytest.fixture(autouse=True)
def _governance_root(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "GOVERNANCE_ROOT", tmp_path / "gov")


MSG = "cmsg_01TestCreatorMessage"


def _approve(root: Path, stage: str, input_hash: str, *, record: bool = True, message_id: str = MSG):
    """A valid approval: the entry in approvals.json and, with ``record``, the creator's word in jobs/creator_ok.jsonl."""
    from explainer_engine.governance import records
    p = root / "qa" / "approvals.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = json.loads(p.read_text()) if p.is_file() else {"schema": "stage_approvals/1", "approvals": []}
    doc["approvals"].append({"stage": stage, "input_hash": input_hash, "approved_by": "creator", "approved_at": "2026-11-19T00:00:00Z",
                             "message_id": message_id, "words": "ok, go on"})
    p.write_text(json.dumps(doc), encoding="utf-8")
    if record:
        records.add("stage_approval", f"ep_toba:{stage}:{input_hash}", message_id, "ok, go on", root=RUN.GOVERNANCE_ROOT)


def test_go_on_is_pass_only():
    assert RUN.GO_ON == (G.PASS,)


def test_review_without_an_approval_stops_and_is_recorded_as_awaiting(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert [r["stage"] for r in recs] == ["script", "sound_plan"]
    assert recs[1]["awaiting"] == "CREATOR_APPROVAL"
    with pytest.raises(RUN.StageRefused, match="awaiting: CREATOR_APPROVAL"):
        RUN.run_stage(RUN.Episode(root), "pictures")


def test_review_with_an_approval_of_a_different_hash_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "qa")
    _approve(root, "sound_plan", "0" * 64)
    with pytest.raises(RUN.StageRefused, match="CREATOR_APPROVAL"):
        RUN.run_stage(RUN.Episode(root), "pictures")


def test_review_with_the_matching_hash_continues_and_a_changed_input_withdraws_it(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    _approve(root, "sound_plan", recs[1]["fingerprint"])
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert recs[-1]["stage"] == "qa" and recs[-1]["verdict"]["status"] == G.PASS and not recs[-1]["rehearsal"]
    # the input changes: the old record is stale, its approval is bound to the old hash and counts for nothing
    (root / "episode.json").write_text(json.dumps(dict(json.loads((root / "episode.json").read_text()), note="changed")))
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert recs[1]["awaiting"] == "CREATOR_APPROVAL" and recs[-1]["stage"] == "sound_plan"


def test_an_entry_without_the_creators_recorded_word_does_not_count(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    _approve(root, "sound_plan", recs[1]["fingerprint"], record=False)      # a session wrote the file by hand
    with pytest.raises(RUN.StageRefused, match="CREATOR_APPROVAL"):
        RUN.run_stage(RUN.Episode(root), "pictures")


def test_an_entry_without_message_id_or_words_or_with_another_approver_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    base = {"stage": "sound_plan", "input_hash": recs[1]["fingerprint"], "approved_by": "creator", "approved_at": "t",
            "message_id": MSG, "words": "ok"}
    for bad in ({k: v for k, v in base.items() if k != "message_id"}, {**base, "message_id": "not-a-chat-id"},
                {**base, "approved_by": "claude"}, {**base, "words": ""}):
        (root / "qa").mkdir(exist_ok=True)
        (root / "qa" / "approvals.json").write_text(json.dumps({"schema": "stage_approvals/1", "approvals": [bad]}))
        with pytest.raises(ContractError):
            RUN.run_stage(RUN.Episode(root), "pictures")


def test_the_approve_command_is_refused_unless_review_fresh_and_has_the_word(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "qa")
    ok = ["approve", str(root), "sound_plan", "--message-id", MSG, "--words", "yes, continue"]
    assert RUN.main(["approve", str(root), "script", "--message-id", MSG, "--words", "x"]) == 2      # PASS, not REVIEW
    assert RUN.main(["approve", str(root), "sound_plan", "--message-id", "oops", "--words", "x"]) == 2
    assert RUN.main(["approve", str(root), "sound_plan", "--message-id", MSG, "--words", "  "]) == 2
    assert not (root / "qa" / "approvals.json").exists()
    assert RUN.main(ok) == 0
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert recs[-1]["stage"] == "qa" and recs[-1]["verdict"]["status"] == G.PASS
    entry = json.loads((root / "qa" / "approvals.json").read_text())["approvals"][0]
    assert entry["input_hash"] == recs[1]["fingerprint"] and entry["message_id"] == MSG and entry["approved_by"] == "creator"


def test_the_approve_command_refuses_a_stale_record(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "qa")
    (root / "episode.json").write_text(json.dumps(dict(json.loads((root / "episode.json").read_text()), note="changed")))
    assert RUN.main(["approve", str(root), "sound_plan", "--message-id", MSG, "--words", "yes"]) == 2


def test_a_rehearsal_still_goes_past_an_unapproved_review_and_never_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    recs = RUN.run_to(RUN.Episode(_episode(tmp_path), rehearsal=True), "qa")
    assert recs[-1]["stage"] == "qa" and recs[-1]["rehearsal"] and recs[-1]["verdict"]["status"] == G.FAIL


def test_a_malformed_approvals_file_is_refused_not_guessed(tmp_path, monkeypatch):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({"sound_plan": G.REVIEW}))
    root = _episode(tmp_path)
    RUN.run_to(RUN.Episode(root), "qa")
    (root / "qa").mkdir()
    (root / "qa" / "approvals.json").write_text(json.dumps({"schema": "stage_approvals/1", "approvals": [{"stage": "sound_plan"}]}))
    with pytest.raises(ContractError):
        RUN.run_stage(RUN.Episode(root), "pictures")


def test_not_run_never_reports_success_is_stored_and_printed(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RUN, "STAGE_FUNCS", _fake({}, not_run_in="sound_plan"))
    root = _episode(tmp_path)
    recs = RUN.run_to(RUN.Episode(root), "qa")
    assert [r["stage"] for r in recs] == ["script", "sound_plan"]            # NOT_RUN stops the chain
    rec = recs[1]
    assert rec["verdict"]["status"] != G.PASS and not ST.is_success(rec["verdict"]["status"])
    assert rec["not_run"] == ["sound_plan_unmeasured"]
    assert RUN.main(["status", str(root)]) == 0
    assert "NOT_RUN  sound_plan_unmeasured" in capsys.readouterr().out
    assert RUN.main(["run", str(root), "--stage", "sound_plan"]) == 1        # exit code: not a success
