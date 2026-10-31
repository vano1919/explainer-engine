"""P8 retry router, qa_report/1 writer and the pilot measures (OR-04, CN-13, BP-165, BP-168, OR-08)."""

from __future__ import annotations

import json

import pytest
from PIL import Image

import test_lifecycle as TL
from explainer_engine.core import contracts, ledger
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import EpisodeJob
from explainer_engine.qa import identity as ID
from explainer_engine.qa import keyframe_gate as KG
from explainer_engine.qa import retry_router as RR


def test_attempts_one_to_three_are_reseed_reweight_fallback_and_the_fourth_raises():
    assert [RR.action_for(n, "KEYFRAME_LTX") for n in (1, 2, 3)] == ["RESEED", "REWEIGHT_REFERENCES", "FALLBACK_STILL_HOLD"]
    assert [RR.action_for(n, "DIALOGUE_CU") for n in (1, 2, 3)] == ["RESEED", "REWEIGHT_REFERENCES", "FALLBACK_KEYFRAME_LTX"]
    assert RR.action_for(3, "ATMOS_BROLL") == "FALLBACK_STILL_HOLD"
    for lane, cite in (("HOST_COMMENTARY", "D-89"), ("DRAMA_BLOCKED_3D", "D-75")):   # refused lanes get no directive (D-89, A2)
        with pytest.raises(ContractError, match=cite):
            RR.action_for(3, lane)
    with pytest.raises(ContractError, match="CN-13"):
        RR.action_for(4, "KEYFRAME_LTX")
    assert RR.directive("s01", 3, "DIALOGUE_CU", fallback_failed=True) is None  # ESCALATE_TO_HUMAN is the report's status


def test_next_attempt_counts_in_attempts_json_and_writes_nothing_for_the_fourth(tmp_path):
    path = tmp_path / "s01" / "attempts.json"
    got = [RR.next_attempt(path, "s01", "DIALOGUE_CU", "hand") ["action"] for _ in range(3)]
    assert got == ["RESEED", "REWEIGHT_REFERENCES", "FALLBACK_KEYFRAME_LTX"]
    with pytest.raises(ContractError):
        RR.next_attempt(path, "s01", "DIALOGUE_CU")
    assert len(json.loads(path.read_text())) == 3
    assert RR.MAX_ATTEMPTS == KG.MAX_TRIES == 3


def test_still_hold_holds_the_approved_starting_keyframe(tmp_path):
    key = tmp_path / "start.png"
    Image.new("RGB", (64, 36), "navy").save(key)
    plan = RR.still_hold(key, 48, 24)
    assert plan["kind"] == "still_hold" and plan["frames"] == 48 and plan["seconds"] == 2.0
    assert plan["sha256"] == contracts.sha256_file(key)
    with pytest.raises(ContractError):
        RR.still_hold(tmp_path / "missing.png", 48, 24)


def test_a_report_with_a_failed_fail_check_cannot_be_pass(tmp_path):
    fail = {"check_id": "LT-51", "rule": "LT-51", "severity": "FAIL", "measured": "pop", "threshold": None, "passed": False}
    bad = {"schema": "qa_report/1", "job_id": "j", "stage": "clip", "status": "PASS", "checks": [fail], "retry_directive": None}
    with pytest.raises(ContractError, match="CN-13"):
        RR.write_report(tmp_path, bad)
    d = RR.directive("s01", 1, "KEYFRAME_LTX")
    report = RR.build_report("j", "clip", [fail], d)
    assert report["status"] == "REPAIR_APPLIED"
    path = RR.write_report(tmp_path, report)
    assert path == tmp_path / "qa" / "clip.qa_report.json" and json.loads(path.read_text())["retry_directive"]["action"] == "RESEED"
    assert RR.build_report("j", "clip", [fail], None)["status"] == "ESCALATE_TO_HUMAN"
    with pytest.raises(ContractError, match="CN-13"):  # a directive past the failure limit is refused by the contract too
        RR.write_report(tmp_path, {**report, "retry_directive": {"shot_id": "s01", "attempt": 4, "action": "RESEED"}})


def test_checks_come_from_the_existing_gates_and_a_review_row_warns():
    rows = RR.from_findings([{"rule": "LT-60", "status": "REVIEW", "msg": "palette"}, {"rule": "LT-60", "status": "PASS", "msg": "ok"},
                             {"rule": "CLIP-01", "status": "FAIL", "msg": "vfr"}])
    assert [r["check_id"] for r in rows] == ["LT-60", "LT-60#2", "CLIP-01"]
    assert [r["severity"] for r in rows] == ["REVIEW", "INFO", "FAIL"]
    assert RR.status_of(rows[:2]) == "WARN_REVIEW" and RR.status_of([rows[1]]) == "PASS"
    verdict = {"status": "FAIL", "fails": [{"code": "KG-03", "q": "two people?", "got": "1"}], "reviews": []}
    kg = RR.from_keyframe_verdict("s01", verdict)
    assert kg[0]["severity"] == "FAIL" and not kg[0]["passed"]
    ok = RR.build_report("j", "keyframe", RR.from_keyframe_verdict("s01", {"status": "PASS", "fails": [], "reviews": []}))
    assert ok["status"] == "PASS" and contracts.errors(ok) == []


def test_identity_and_lipsync_rows_validate_in_a_report(tmp_path):
    rows = [ID.identity_check("s01", {"min": 0.8, "mean": 0.8, "per_frame": [0.8]}), ID.lipsync_check("s01", {"offset_ms": 120.0})]
    report = RR.build_report("j", "clip", rows)
    assert report["status"] == "WARN_REVIEW"
    RR.write_report(tmp_path, report)


def test_a_fixture_job_walks_assets_to_qa_passed_on_fake_reports(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"reserved": {"pod:abc": {"service": "runpod_usd", "amount": 1.0}}}), encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    job = EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    TL.walk(job, "ASSETS")
    for stage, to in (("keyframe", None), ("clip", None), ("assembled", "ASSEMBLED")):
        RR.write_report(tmp_path, RR.build_report("job-001", stage, RR.from_keyframe_verdict("s01", {"status": "PASS", "fails": [], "reviews": []})))
        if to:
            job.move(to, reason="assembled", approval=TL.MACHINE)
    report = json.loads((tmp_path / "qa" / "assembled.qa_report.json").read_text())
    assert report["status"] == "PASS"
    job.move("QA_PASSED", reason="qa_report/1 PASS", approval=TL.MACHINE)
    assert job.state == "QA_PASSED"


# --- the pilot measures (ledger) ----------------------------------------------------------------------------------------
def _run(tmp_path):
    return ledger.Run.open(tmp_path / "run.json", caps={"runpod_usd": 3.0})


def test_18_renders_for_12_accepted_shots_is_a_multiplier_of_1_5(tmp_path):
    assert ledger.retry_multiplier(18, 12) == 1.5 and ledger.retry_multiplier(5, 0) is None
    files = []
    for i in range(12):  # 12 shots, 6 of them rendered twice -> 18 attempt rows
        log = ledger.Attempts(tmp_path / f"s{i:02d}" / "attempts.json", at_level=3, escalated=0)
        for _ in range(2 if i < 6 else 1):
            log.add("render")
        files.append(log.path)
    assert ledger.count_renders(files) == 18


def test_zero_logged_retries_is_a_multiplier_of_one(tmp_path):
    """The router logs retries only: first renders are accepted shots, so renders = accepted + logged retries."""
    assert ledger.retry_multiplier(12, 12) == 1.0 and ledger.retry_multiplier(3, 4) == 0.75
    assert ledger.renders_made(12, []) == 12
    log = ledger.Attempts(tmp_path / "s00" / "attempts.json", at_level=3, escalated=0)
    log.add("retry")
    assert ledger.renders_made(12, [log.path]) == 13
    run = _run(tmp_path)
    ledger.main(["report", str(run.path), "--attempts", str(tmp_path / "none"), "--accepted", "12"])
    assert ledger.pilot_measures(run, tmp_path, renders=ledger.renders_made(12, []), accepted=12)["retry_multiplier"] == 1.0


def test_review_minutes_unknown_without_the_file_and_summed_with_it(tmp_path):
    run = _run(tmp_path)
    m = ledger.pilot_measures(run, tmp_path, renders=18, accepted=12, finished_minutes=2.0)
    assert m["review_minutes"] is None and m["review_minutes_per_finished_minute"] is None
    rows = ledger.morning_rows(m)
    assert "unknown" in rows[2] and rows[0].endswith("x1.5") and len(rows) == 4
    ledger.add_review_minutes(tmp_path, 6, "keyframes")
    ledger.add_review_minutes(tmp_path, 2.5, "clips")
    assert (tmp_path / "review_minutes.jsonl").read_text().count("\n") == 2
    m = ledger.pilot_measures(run, tmp_path, renders=18, accepted=12, finished_minutes=2.0)
    assert m["review_minutes_per_finished_minute"] == 4.25
    with pytest.raises(ValueError):
        ledger.add_review_minutes(tmp_path, 0)


@pytest.mark.parametrize("mult,rev,forecast,verdict", [
    (1.5, 3.0, 5.0, "GO"), (2.0, 4.0, 12.0, "GO"), (2.5, 3.0, 5.0, "PIVOT"), (3.0, 3.0, 5.0, "PIVOT"), (3.2, 1.0, 1.0, "ABANDON"),
    (1.5, 4.5, 5.0, "PIVOT"), (1.5, 3.0, 12.5, "PIVOT"), (1.5, None, 5.0, "UNKNOWN"), (None, 3.0, 5.0, "UNKNOWN")])
def test_go_pivot_abandon_uses_the_creators_thresholds_from_bp_168(mult, rev, forecast, verdict):
    m = {"retry_multiplier": mult, "forecast_usd": forecast, "review_minutes_per_finished_minute": rev}
    v = ledger.pilot_verdict(m)
    assert v["verdict"] == verdict and v["severity"] == "REVIEW"


def test_the_cli_adds_review_minutes_and_prints_the_pilot_rows(tmp_path, capsys):
    _run(tmp_path)
    ledger.main(["review-minutes", "add", str(tmp_path), "7", "first", "review"])
    ledger.main(["report", str(tmp_path / "run.json"), "--accepted", "12", "--finished-minutes", "1"])
    out = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert out["pilot"]["review_minutes_per_finished_minute"] == 7.0 and out["pilot"]["retry_multiplier"] is None
    assert any("unknown" in r for r in out["pilot_rows"])


def test_only_rows_tagged_render_count_as_renders_untagged_legacy_rows_still_do(tmp_path):
    log = ledger.Attempts(tmp_path / "s00" / "attempts.json", at_level=3, escalated=1)
    RR.next_attempt(log.path, "s00", "STATIC_DIAGRAM", "bad seed")           # tagged by the router
    log.add("hand note", kind="note")                                                    # not a render
    log.add("opus look", escalated=True, kind="escalation")                              # not a render
    log.add("old row")                                                                   # legacy, untagged: counted (compatibility)
    assert [r.get("kind") for r in log.rows()] == ["render", "note", "escalation", None]
    assert ledger.count_renders([log.path]) == 2
