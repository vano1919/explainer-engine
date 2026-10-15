"""Job storage, job naming/cleanup, errors and evidence labels.
Adapted from vano1919/tmr-video-script-engine@d88ba8f: tests/unit/test_housekeeping.py (+ new store tests)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from explainer_engine.core import errors, labels
from explainer_engine.core.jobs import clean_jobs, job_seq, next_job_dir
from explainer_engine.core.store import JobStore, Stage, write_json_atomic

STAGES = [Stage(1, "intake", "topic intake"), Stage(2, "dossier", "research dossier"), Stage(3, "script", "script")]


def _make_job(root, slug, seq, extra=None):
    job = root / slug / f"job-{seq:03d}_2026-10-15_00{seq:02d}"
    (job / "artifacts").mkdir(parents=True)
    for name in extra or []:
        (job / name).write_text("x", encoding="utf-8")
    return job


def test_next_job_dir_numbers_and_records_origin(tmp_path):
    first = next_job_dir(tmp_path, "onion", now=datetime(2026, 10, 15, 0, 12))
    assert first.name == "job-001_2026-10-15_0012"
    (first / "artifacts").mkdir(parents=True)
    second = next_job_dir(tmp_path, "onion", resume_from=first, redo_from=5, now=datetime(2026, 10, 15, 1, 0))
    assert second.name == "job-002_2026-10-15_0100_from-001-redo5"
    assert job_seq(second) == 2


def test_clean_keeps_newest_and_protected(tmp_path):
    jobs = [_make_job(tmp_path, "onion", n) for n in range(1, 8)]
    _make_job(tmp_path, "other", 1)
    (jobs[0] / "KEEP").write_text("", encoding="utf-8")
    (jobs[1] / "final.mp4").write_text("", encoding="utf-8")
    (jobs[2] / "state.json").write_text(json.dumps({"status": "NEEDS_REVIEW"}), encoding="utf-8")
    removed = clean_jobs(tmp_path, "onion", keep=2, current=jobs[6], channel_dir=tmp_path / "channel")
    assert sorted(p.name[:7] for p in removed) == ["job-004", "job-005"]
    assert all(jobs[k].exists() for k in (0, 1, 2, 5, 6))
    assert (tmp_path / "other").exists()


def test_clean_dry_run_deletes_nothing(tmp_path):
    jobs = [_make_job(tmp_path, "onion", n) for n in range(1, 5)]
    removed = clean_jobs(tmp_path, "onion", keep=1, dry_run=True, channel_dir=tmp_path / "channel")
    assert len(removed) == 3 and all(j.exists() for j in jobs)


def test_store_saves_atomically_and_tracks_state(tmp_path):
    store = JobStore(tmp_path / "job-001", STAGES)
    store.set_state("RUNNING", current_stage=1)
    store.save(1, {"topic": "onions"})
    assert store.load(1) == {"topic": "onions"}
    assert store.read_state()["completed_stages"] == [1]
    assert not list(tmp_path.rglob("*.tmp"))  # nothing torn or left behind


def test_resume_uses_only_a_contiguous_prefix(tmp_path):
    store = JobStore(tmp_path / "job-001", STAGES)
    store.save(1, {}, quiet=True)
    store.save(3, {}, quiet=True)  # stage 2 missing: 3 must not be reused
    assert store.completed_prefix() == [1]


def test_store_rejects_bad_status_and_duplicate_stages(tmp_path):
    with pytest.raises(ValueError):
        JobStore(tmp_path, STAGES + [Stage(1, "again", "dup")])
    with pytest.raises(ValueError):
        JobStore(tmp_path, STAGES).set_state("DONE")
    with pytest.raises(KeyError):
        JobStore(tmp_path, STAGES).save(9, {})


def test_write_json_atomic_creates_parents(tmp_path):
    path = write_json_atomic(tmp_path / "a" / "b.json", {"x": "ä"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"x": "ä"}


def test_validation_error_lists_findings():
    err = errors.ValidationError([{"check": "schema", "detail": "missing scene_id"}])
    assert "schema: missing scene_id" in str(err) and isinstance(err, errors.EngineError)
    assert str(errors.PipelineFailure("render", "scene S3 failed")) == "[render] scene S3 failed"


def test_labels_wrap_and_unwrap():
    node = {"fps": labels.v(30, "engineering_default"), "lufs": labels.v(-14, "hypothesis", "playback normalisation")}
    assert labels.plain_tree(node) == {"fps": 30, "lufs": -14}
    with pytest.raises(ValueError):
        labels.v(1, "established")  # TMR's label; not in this project's vocabulary
