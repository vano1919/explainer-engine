"""The episode lifecycle (docs/CONTRACTS.md, CN-03..CN-06): only the next step, gates with approvals, named back paths."""

from __future__ import annotations

import json

import pytest

from explainer_engine.core import store
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import EpisodeJob, LIFECYCLE

SHA = "c" * 64
CREATOR = {"kind": "creator", "by": "ვანო", "ref": "cmsg_1", "at": "2026-10-29T18:00:00", "sha256": SHA}
MACHINE = {"kind": "machine", "by": "gate", "ref": "report.json", "at": "2026-10-29T18:00:00", "sha256": None}
PLANNER = {"kind": "planner", "by": "opus-thread", "ref": "cmsg_2", "at": "2026-10-29T18:00:00", "sha256": SHA}


@pytest.fixture
def job(tmp_path):
    (tmp_path / "run.json").write_text(json.dumps({"reserved": {"pod:abc": {"service": "runpod_usd", "amount": 1.0}}}), encoding="utf-8")
    (tmp_path / "dossier.md").write_text("research", encoding="utf-8")
    return EpisodeJob.create(tmp_path, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)


def step(job, to):
    kind = next(iter(store.GATES[to]))
    approval = {"creator": CREATOR, "machine": MACHINE}[kind if kind in ("creator", "machine") else "creator"]
    extra = {}
    if to == "RESEARCHED":
        extra["dossier"] = job.job_dir / "dossier.md"
    if to == "BUDGET_RESERVED":
        extra["reservation_id"] = "pod:abc"
    job.move(to, reason=f"to {to}", approval=approval, **extra)


def walk(job, upto):
    for to in LIFECYCLE[1:LIFECYCLE.index(upto) + 1]:
        step(job, to)


def snapshot(job):
    return (job.job_dir / store.MANIFEST).read_text(encoding="utf-8")


def test_the_full_forward_walk(job):
    walk(job, "PUBLISHED_PUBLIC")
    m = EpisodeJob.open(job.job_dir).manifest
    assert m["state"] == "PUBLISHED_PUBLIC" and [h["to"] for h in m["history"]] == list(LIFECYCLE)
    assert m["source_dossier_sha256"] and m["budget_reservation_id"] == "pod:abc"
    with pytest.raises(ContractError):
        job.abort("ABORTED_SPEND_CAP", reason="late")
    with pytest.raises(ContractError):
        job.back("repair", reason="late")


def test_a_skipped_step_is_refused_and_writes_nothing(job):
    before = snapshot(job)
    with pytest.raises(ContractError):
        job.move("SCRIPT_APPROVED", reason="skip", approval=CREATOR)
    assert snapshot(job) == before and job.state == "CREATED"


def test_a_gate_needs_its_approval_kind_and_a_creator_needs_a_ref(job):
    walk(job, "RESEARCHED")
    for bad in (None, MACHINE, {**CREATOR, "ref": ""}, {**CREATOR, "by": ""}, {**CREATOR, "sha256": None}):
        with pytest.raises(ContractError):
            job.move("VARIANT_CHOSEN", reason="x", approval=bad)
    job.move("VARIANT_CHOSEN", reason="x", approval=CREATOR)


def test_researched_fixes_the_dossier_once(job):
    walk(job, "VARIANT_CHOSEN")
    first = job.manifest["source_dossier_sha256"]
    assert first
    job.back("variant_changed", reason="another variant")  # back at RESEARCHED: the dossier stays the job's
    assert job.state == "RESEARCHED" and job.manifest["source_dossier_sha256"] == first
    with pytest.raises(ContractError):  # never create a manifest over an existing one
        EpisodeJob.create(job.job_dir, job_id="j", episode_slug="s", ledger="run.json", fps=24)
    with pytest.raises(ContractError):  # RESEARCHED is not the next step from RESEARCHED: another dossier is another job
        job.move("RESEARCHED", reason="again", approval=MACHINE, dossier=job.job_dir / "dossier.md")


def test_budget_needs_a_reservation_the_ledger_holds_and_accepts_a_planner(job):
    walk(job, "STORYBOARDED")
    for rid in (None, "pod:missing"):
        with pytest.raises(ContractError):
            job.move("BUDGET_RESERVED", reason="x", approval=CREATOR, reservation_id=rid)
    with pytest.raises(ContractError):
        job.move("BUDGET_RESERVED", reason="x", approval=MACHINE, reservation_id="pod:abc")
    job.move("BUDGET_RESERVED", reason="OR-24", approval=PLANNER, reservation_id="pod:abc")
    assert job.manifest["budget_reservation_id"] == "pod:abc"


def test_every_named_back_path_once_and_a_wrong_one_is_refused(job):
    walk(job, "REVIEW_APPROVED")
    with pytest.raises(ContractError):
        job.back("plan_changed", reason="wrong state")  # leaves BUDGET_RESERVED only
    with pytest.raises(ContractError):
        job.back("made_up", reason="x")
    with pytest.raises(ContractError):
        job.back("post_review_fix", reason="x")  # the creator's word is needed after approval #2
    job.back("post_review_fix", reason="fix", approval=CREATOR)
    assert job.state == "ASSETS"
    for path, (sources, to) in store.BACK_PATHS.items():
        if path == "post_review_fix":
            continue
        fresh = EpisodeJob.create(job.job_dir / path, job_id=path, episode_slug="n", ledger="../run.json", fps=24)
        (job.job_dir / path / "dossier.md").write_text("d", encoding="utf-8")
        for to_state in LIFECYCLE[1:LIFECYCLE.index(sources[0]) + 1]:
            kind = next(iter(store.GATES[to_state]))
            extra = {"dossier": job.job_dir / path / "dossier.md"} if to_state == "RESEARCHED" else {}
            if to_state == "BUDGET_RESERVED":
                extra["reservation_id"] = "pod:abc"
            fresh.move(to_state, reason="w", approval={"creator": CREATOR}.get(kind, MACHINE) if kind != "planner" else CREATOR, **extra)
        fresh.back(path, reason="named path")
        assert fresh.state == to and fresh.manifest["history"][-1]["path"] == path


def test_going_back_past_the_budget_clears_it_and_the_approvals_beyond(job):
    walk(job, "SAMPLE_APPROVED")
    job.back("words_changed", reason="a word changed (OR-17)")
    assert job.state == "SCENARIO_APPROVED" and job.manifest["budget_reservation_id"] is None
    assert set(job.manifest["approvals"]) <= set(LIFECYCLE[:LIFECYCLE.index("SCENARIO_APPROVED") + 1])


def test_abort_and_reopen(job):
    walk(job, "STORYBOARDED")
    job.abort("ABORTED_SPEND_CAP", reason="80 % of runpod_usd")
    assert job.state == "ABORTED_SPEND_CAP" and job.manifest["reopen_to"] == "STORYBOARDED"
    with pytest.raises(ContractError):
        job.move("BUDGET_RESERVED", reason="x", approval=CREATOR, reservation_id="pod:abc")
    with pytest.raises(ContractError):
        job.reopen(reason="x", approval=MACHINE)
    job.reopen(reason="the creator raised the cap", approval=CREATOR)
    assert job.state == "STORYBOARDED" and job.manifest["reopen_to"] is None


def test_published_public_is_the_creators_click(job):
    walk(job, "STAGED_UNLISTED")
    with pytest.raises(ContractError):
        job.move("PUBLISHED_PUBLIC", reason="auto", approval=MACHINE)
    job.move("PUBLISHED_PUBLIC", reason="Studio click", approval=CREATOR)


def test_artifacts_do_not_cross_jobs_or_dossiers(tmp_path):
    a = tmp_path / "jobs" / "nap" / "job-001"
    b = tmp_path / "jobs" / "nap" / "job-002"
    for d in (a, b):
        d.mkdir(parents=True)
        (d / "run.json").write_text("{}", encoding="utf-8")
        (d / "dossier.md").write_text("d", encoding="utf-8")
    ja = EpisodeJob.create(a, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    (b / "cover.png").write_bytes(b"cover of job B")
    with pytest.raises(ContractError):
        ja.record_artifact("cover", b / "cover.png")
    (a / "cover.png").write_bytes(b"cover of job A")
    ja.record_artifact("cover", "cover.png")
    ja.check_artifact("cover")
    (a / "cover.png").write_bytes(b"changed")
    with pytest.raises(ContractError):
        ja.check_artifact("cover")
    (a / "cover.png").write_bytes(b"cover of job A")
    ja.check_artifact("cover")
    ja.move("RESEARCHED", reason="x", approval=MACHINE, dossier=a / "dossier.md")  # the dossier hash moves: the cover predates it
    with pytest.raises(ContractError):
        ja.check_artifact("cover")


def test_a_creator_gate_binds_the_sha256_of_what_was_approved(job):
    walk(job, "RESEARCHED")
    with pytest.raises(ContractError, match="binds the sha256"):
        job.move("VARIANT_CHOSEN", reason="x", approval={**CREATOR, "sha256": None})
    job.move("VARIANT_CHOSEN", reason="x", approval=CREATOR)
    assert job.manifest["approvals"]["VARIANT_CHOSEN"]["sha256"] == SHA


def test_an_existing_episode_is_adopted_through_its_state_gate(tmp_path):
    job = EpisodeJob.adopt(tmp_path / "titans", state="SCRIPT_APPROVED", reason="Titans, approved 2026-10-20", approval=CREATOR,
                           dossier_sha256=SHA, job_id="titans", episode_slug="titans", ledger="run.json", fps=24)
    m = EpisodeJob.open(tmp_path / "titans").manifest
    assert m["history"][0]["path"] == "adopted" and m["state"] == "SCRIPT_APPROVED"
    assert m["approvals"]["SCRIPT_APPROVED"]["sha256"] == SHA and m["source_dossier_sha256"] == SHA


def test_adopting_is_no_way_round_the_gates(tmp_path):
    base = dict(job_id="a", episode_slug="a", ledger="r", fps=24)
    cases = [
        ("PUBLISHED_PUBLIC", MACHINE, "machine"),            # CN-06: only the creator's click
        ("REVIEW_APPROVED", None, "no approval"),            # CN-04: approval #2 needs the creator
        ("SCRIPT_APPROVED", {**CREATOR, "sha256": None}, "unbound"),  # CN-04: bound to the words
        ("ABORTED_SPEND_CAP", CREATOR, "terminal"),          # nothing could reopen it
        ("NOPE", CREATOR, "unknown"),
    ]
    for n, (state, approval, why) in enumerate(cases):
        with pytest.raises(ContractError):
            EpisodeJob.adopt(tmp_path / str(n), state=state, reason=why, approval=approval, dossier_sha256=SHA, **base)
        assert not (tmp_path / str(n) / store.MANIFEST).exists(), why
    with pytest.raises(ContractError, match="dossier"):  # CN-05: past CREATED the dossier is named
        EpisodeJob.adopt(tmp_path / "x", state="SCRIPT_APPROVED", reason="x", approval=CREATOR, **base)
    EpisodeJob.adopt(tmp_path / "ok", state="CREATED", reason="new", approval=None, **base)


def test_a_cached_render_and_the_asset_library_may_be_recorded_but_not_a_stray_assets_folder(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setenv("EXPLAINER_SHOT_CACHE", str(cache))
    jd = tmp_path / "jobs" / "nap" / "job-001"
    jd.mkdir(parents=True)
    job = EpisodeJob.create(jd, job_id="job-001", episode_slug="nap", ledger="run.json", fps=24)
    (cache / "ab" / "abc").mkdir(parents=True)
    (cache / "ab" / "abc" / "clip.mp4").write_bytes(b"clip")
    job.record_artifact("clip_s1", cache / "ab" / "abc" / "clip.mp4")
    stray = tmp_path / "somewhere" / "assets" / "x.png"  # a path that merely contains "assets" is not the library
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"x")
    with pytest.raises(ContractError):
        job.record_artifact("stray", stray)
