"""Tests of the limit code (0C.2) in ``explainer_engine/llm/claude_api.py``: the emergency stop, the per-call hard limit and the
80 % warning line. No network, no real ledger: the caps are patched, the ledger and the cache live in ``tmp_path``."""

from __future__ import annotations

import pytest

from explainer_engine.llm import claude_api
from explainer_engine.llm.claude_api import CapReached, ClaudeAPI, EmergencyStop

JOB = "limits-test"


def caps_dict(job_cap: float = 1.0, max_usd: float = 10.0) -> dict:
    return {"max_usd": max_usd, "jobs": {JOB: job_cap}, "approval": {"ref": "OR-24 test", "by": "test"}}


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_LLM_LEDGER", str(tmp_path / "ledger"))
    monkeypatch.setenv("EXPLAINER_LLM_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("EXPLAINER_EMERGENCY_STOP", str(tmp_path / "EMERGENCY_STOP"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("EE_ANTHROPIC_API_KEY", raising=False)
    return tmp_path


@pytest.fixture()
def caps(monkeypatch):
    def set_caps(job_cap: float = 1.0, max_usd: float = 10.0) -> dict:
        c = caps_dict(job_cap, max_usd)
        monkeypatch.setattr(claude_api, "caps", lambda: c)
        return c
    return set_caps


@pytest.fixture()
def api(env, caps):
    caps()
    return ClaudeAPI()


def test_emergency_stop_refuses_before_anything_is_sent(env, caps):
    caps(job_cap=1.0, max_usd=10.0)
    api = ClaudeAPI()
    stop = env / "EMERGENCY_STOP"
    assert claude_api.emergency_stop_path() == stop
    stop.write_text("stop\n", encoding="utf-8")
    with pytest.raises(EmergencyStop):
        api._reserve(JOB, "some item", 0.01)
    assert api.ledger.rows() == []
    assert not (env / "ledger" / f"job_{JOB}.json").exists()


def test_per_call_worst_case_above_the_job_cap_is_refused(env, caps):
    caps(job_cap=1.0, max_usd=10.0)
    api = ClaudeAPI()
    with pytest.raises(CapReached) as e:
        api._reserve(JOB, "one big call", 0.5, per_call=2.0)
    assert "worst case" in str(e.value)
    assert api.ledger.rows() == []
    assert not (env / "ledger" / f"job_{JOB}.json").exists()


def test_per_call_under_the_job_cap_is_reserved(env, caps):
    caps(job_cap=1.0, max_usd=10.0)
    api = ClaudeAPI()
    api._reserve(JOB, "small call", 0.01, per_call=0.2)
    assert api.run_for(JOB).spent(claude_api.SERVICE) == pytest.approx(0.01)


def test_no_warn_line_below_eighty_percent(env, caps):
    caps(job_cap=1.0, max_usd=10.0)
    api = ClaudeAPI()
    api.ledger.append({"ev": "done", "uid": "u1", "job": JOB, "id": "q", "model": "m", "usd": 0.5})
    api._warn_near_limits(JOB)
    assert [r for r in api.ledger.rows() if r["ev"] == "warn"] == []


def test_one_warn_line_at_eighty_percent_of_the_job_cap(env, caps):
    caps(job_cap=1.0, max_usd=10.0)
    api = ClaudeAPI()
    api.ledger.append({"ev": "done", "uid": "u1", "job": JOB, "id": "q", "model": "m", "usd": 0.85})
    api._warn_near_limits(JOB)
    warns = [r for r in api.ledger.rows() if r["ev"] == "warn"]
    assert [(r["job"], r["scope"]) for r in warns] == [(JOB, "job")]
    assert warns[0]["spent"] == pytest.approx(0.85)
    assert warns[0]["limit"] == pytest.approx(1.0)
    api._warn_near_limits(JOB)
    assert len([r for r in api.ledger.rows() if r["ev"] == "warn" and r["scope"] == "job"]) == 1
