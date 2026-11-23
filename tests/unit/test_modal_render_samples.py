"""OR-33 protection for sample renders: outputs and ledger lines land on disk before the next job; reruns skip finished jobs."""

import builtins
import json
import sys
from pathlib import Path

import pytest

from explainer_engine.samples import modal_render_samples as m


def _fake_runner(out_map, fail=(), raise_on=None, seen=None):
    def runner(argv, **kwargs):
        name = argv[-1]
        if seen is not None:
            seen.append(name)
        if raise_on == name:
            raise KeyboardInterrupt("interrupted")
        if name not in fail:
            Path(out_map[name]).write_bytes(b"x" * 10)
        class P:
            returncode = 1 if name in fail else 0
        return P()
    return runner


def test_load_jobs_rejects_missing_key_and_bad_argv(tmp_path):
    bad_key = tmp_path / "a.json"
    bad_key.write_text(json.dumps([{"name": "x", "argv": ["a"]}]), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_jobs(bad_key)
    bad_argv = tmp_path / "b.json"
    bad_argv.write_text(json.dumps([{"name": "x", "argv": ["a", 1], "out": "o"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_jobs(bad_argv)


def test_run_one_ok_only_with_output_file(tmp_path):
    out = tmp_path / "o.mp4"
    job = {"name": "j", "argv": ["x", str(out)], "out": str(out)}
    assert m.run_one(job, runner=_fake_runner({str(out): str(out)}))["ok"] is True
    missing = {"name": "j", "argv": ["x", "nope"], "out": str(tmp_path / "none.mp4")}
    assert m.run_one(missing, runner=_fake_runner({}, fail=("nope",)))["ok"] is False


def test_each_result_is_on_disk_before_the_next_job_runs(tmp_path):
    outs = {n: str(tmp_path / f"{n}.mp4") for n in ("a", "b")}
    jobs = [{"name": n, "argv": ["r", n], "out": outs[n]} for n in ("a", "b")]
    ledger = tmp_path / "ledger.jsonl"
    seen_lines = []

    def runner(argv, **kwargs):
        if argv[-1] == "b":
            seen_lines.append(len(ledger.read_text(encoding="utf-8").splitlines()))
        return _fake_runner(outs)(argv, **kwargs)

    m.run_all(jobs, ledger, runner=runner)
    assert seen_lines == [1]  # job a's ledger line existed when job b started


def test_interruption_keeps_finished_output_and_rerun_skips_it(tmp_path):
    outs = {n: str(tmp_path / f"{n}.mp4") for n in ("a", "b")}
    jobs = [{"name": n, "argv": ["r", n], "out": outs[n]} for n in ("a", "b")]
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(KeyboardInterrupt):
        m.run_all(jobs, ledger, runner=_fake_runner(outs, raise_on="b"))
    assert Path(outs["a"]).exists()
    seen = []
    m.run_all(jobs, ledger, runner=_fake_runner(outs, seen=seen))
    assert seen == ["b"]


def test_stops_at_80_percent_of_cap(tmp_path):
    outs = {n: str(tmp_path / f"{n}.mp4") for n in ("a", "b", "c")}
    jobs = [{"name": n, "argv": ["r", n], "out": outs[n]} for n in ("a", "b", "c")]
    ledger = tmp_path / "ledger.jsonl"
    res = m.run_all(jobs, ledger, runner=_fake_runner(outs), max_usd=1.0, cost_per_job_usd=0.5)
    assert res[-1]["status"] == "stopped_at_80pct"
    assert not Path(outs["c"]).exists()


def test_stops_after_three_failures(tmp_path):
    outs = {n: str(tmp_path / f"{n}.mp4") for n in ("a", "b", "c", "d")}
    jobs = [{"name": n, "argv": ["r", n], "out": outs[n]} for n in ("a", "b", "c", "d")]
    ledger = tmp_path / "ledger.jsonl"
    res = m.run_all(jobs, ledger, runner=_fake_runner(outs, fail=("a", "b", "c", "d")))
    assert len(res) == 3


def test_importing_does_not_touch_modal(monkeypatch):
    monkeypatch.setitem(sys.modules, "modal", None)  # any import of modal now fails
    import importlib
    importlib.reload(m)  # import must still succeed
    with pytest.raises(ImportError):
        m.modal_app()
