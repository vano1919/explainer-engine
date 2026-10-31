"""P10/P11 dry run: a fixture animated job walks CREATED -> ASSEMBLED -> QA_PASSED on fakes, no network (OR-01, OR-05, CN-03/04)."""

from __future__ import annotations

import json
import socket

import pytest
from PIL import Image

import test_lifecycle as TL
from explainer_engine import production_gate as G
from explainer_engine.core import ledger
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import EpisodeJob
from explainer_engine.qa import retry_router as RR
from explainer_engine.qa import review_bundle as RB


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("the dry run touched the network")
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def machine(ref):
    return {**TL.MACHINE, "ref": ref}


@pytest.fixture
def job(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"reserved": {"pod:abc": {"service": "runpod_usd", "amount": 1.0}}}), encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    return EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)


def fake_shots(job_dir):
    """Rendered shots as the pod would leave them: a keyframe and a clip stand-in per shot (no GPU, no model)."""
    d = job_dir / "shots"
    d.mkdir()
    for sid in ("s01", "s02"):
        Image.new("RGB", (64, 36), (120, 90, 60)).save(d / f"{sid}.png")
        (d / f"{sid}.mp4").write_bytes(b"fake clip " + sid.encode())
    return d


def write_reports(job_dir, stages=RR.STAGES):
    ok = [{"check_id": "x", "rule": "KG", "severity": "FAIL", "measured": 1.0, "threshold": 0.8, "passed": True}]
    return [RR.write_report(job_dir, RR.build_report("job-001", st, ok)) for st in stages]


def test_the_animated_job_walks_to_qa_passed_on_machine_approvals(job):
    TL.walk(job, "SAMPLE_APPROVED")  # the person's gates up to the sample are the lifecycle fixture's, not this test's subject
    shots = fake_shots(job.job_dir)
    for to in ("AUDIO_TIMED", "ASSETS", "ASSEMBLED"):
        job.move(to, reason=f"fake {to}", approval=machine(f"{to}.json"))
    assert job.state == "ASSEMBLED" and len(list(shots.glob("*.mp4"))) == 2
    write_reports(job.job_dir)
    job.move("QA_PASSED", reason="all qa_report/1 pass", approval=machine("qa/assembled.qa_report.json"))
    m = EpisodeJob.open(job.job_dir).manifest
    assert m["state"] == "QA_PASSED" and m["fps"] == 24
    assert {h["approval"]["kind"] for h in m["history"] if h["to"] in ("AUDIO_TIMED", "ASSETS", "ASSEMBLED", "QA_PASSED")} == {"machine"}


def test_review_approved_is_refused_without_a_creator_approval(job):
    TL.walk(job, "QA_PASSED")
    before = TL.snapshot(job)
    for bad in (None, machine("bundle"), {**TL.PLANNER, "kind": "planner"}):
        with pytest.raises(ContractError):
            job.move("REVIEW_APPROVED", reason="no creator", approval=bad)
    assert TL.snapshot(job) == before and job.state == "QA_PASSED"
    for to in ("STAGED_UNLISTED", "PUBLISHED_PUBLIC"):  # no way round the gate to staging or public (invariant 4)
        with pytest.raises(ContractError):
            job.move(to, reason="skip", approval=machine("x"))


def test_the_animated_gates_read_job_manifest(job):
    rows = {r["gate"]: r for r in G.gates(job.job_dir)}
    assert rows["RESEARCHED"]["status"] == "WAIT" and "machine" in rows["RESEARCHED"]["detail"]
    assert rows["REVIEW_APPROVED"]["status"] == "WAIT" and "creator" in rows["REVIEW_APPROVED"]["detail"]
    TL.walk(job, "QA_PASSED")
    write_reports(job.job_dir)
    rows = {r["gate"]: r for r in G.gates(job.job_dir)}
    assert rows["QA_PASSED"]["status"] == "PASS" and rows["REVIEW_APPROVED"]["status"] == "WAIT"
    assert [rows[f"qa:{s}"]["status"] for s in RR.STAGES] == ["PASS"] * 3
    bad = RR.build_report("job-001", "clip", [{"check_id": "x", "rule": "KG", "severity": "FAIL", "measured": 0, "threshold": 1,
                                               "passed": False}])
    assert bad["status"] == "ESCALATE_TO_HUMAN"
    RR.write_report(job.job_dir, bad)
    assert {r["gate"]: r for r in G.gates(job.job_dir)}["qa:clip"]["status"] == "BLOCKED"
    assert G.main([str(job.job_dir)]) == 1


def test_a_terminal_job_blocks_every_gate(job):
    job.abort("ABORTED_SPEND_CAP", reason="cap")
    assert {r["status"] for r in G.gates(job.job_dir)} == {"BLOCKED"}


def test_the_review_bundle_names_every_qa_report_and_the_three_pilot_rows(job, tmp_path):
    reports = write_reports(job.job_dir)
    run = ledger.Run.open(tmp_path / "pilot_run.json", {"runpod_usd": 2.5})
    measures = ledger.pilot_measures(run, job.job_dir, renders=5, accepted=3, finished_minutes=1.0)
    bundle = tmp_path / "review_bundle"
    bundle.mkdir()
    (bundle / "final.mp4").write_bytes(b"video")
    added = RB.add_qa(bundle, job.job_dir, measures)
    manifest = json.loads(RB.write(bundle).read_text(encoding="utf-8"))
    listed = {r["path"] for r in manifest["files"]}
    assert {f"qa/{p.name}" for p in reports} <= listed and set(added) <= listed and len(added) == 4
    rows = (bundle / "pilot_rows.md").read_text(encoding="utf-8")
    for needle in ("retry multiplier", "settled USD vs cap", "review minutes per finished minute", "pilot verdict (REVIEW)"):
        assert needle in rows
    assert RB.check(bundle / RB.MANIFEST) == []
    (bundle / "qa" / reports[0].name).write_text("{}", encoding="utf-8")  # a report changed after the manifest: refused
    assert RB.check(bundle / RB.MANIFEST)
