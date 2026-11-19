"""Owner-approved Python item 6: our own voices (plan, cache, cost guard). No test calls a real API: the client is a fake."""
import json
from pathlib import Path

import pytest

from explainer_engine.audio import our_voices as V
from explainer_engine.core import spend_caps

SPEC = Path(__file__).resolve().parents[2] / "episodes" / "ep_truce_1914" / "audio" / "our_voices_spec.json"


class FakeClient:
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def synthesize(self, job):
        if job["line_id"] == self.fail_on:
            raise RuntimeError("API error")
        self.calls.append(job["line_id"])
        return b"R" * (V.MIN_WAV_BYTES + 10)


def _jobs():
    return V.jobs(V.load_spec(SPEC))


def test_one_job_per_dialogue_line_with_the_specs_cache_keys():
    jobs = _jobs()
    assert len(jobs) == 39
    assert all(j["key_matches_spec"] for j in jobs)
    assert len({j["relpath"] for j in jobs}) == 39


def test_the_estimate_matches_the_spec_and_stays_under_the_stop():
    est = V.estimate(_jobs())
    assert est["credits"] == 1038 and est["lines"] == 39 and est["usd_estimate"] == pytest.approx(0.23, abs=0.01)
    assert est["credits"] <= spend_caps.casting_credits_max() * V.STOP_FRACTION


def test_without_the_owners_approval_nothing_is_generated(tmp_path):
    c = FakeClient()
    with pytest.raises(V.OwnerApprovalRequired):
        V.generate(_jobs(), c, tmp_path / "c", tmp_path / "l.json", approved=False)
    assert c.calls == [] and not (tmp_path / "c").exists()


def test_a_plan_above_the_eighty_percent_stop_is_refused(tmp_path):
    c = FakeClient()
    with pytest.raises(spend_caps.OverCeiling):
        V.generate(_jobs(), c, tmp_path / "c", tmp_path / "l.json", approved=True, ceiling=1200)
    assert c.calls == []


def test_generation_checkpoints_every_line_and_resumes_without_rebilling(tmp_path):
    jobs = _jobs()
    c = FakeClient(fail_on=jobs[5]["line_id"])
    with pytest.raises(RuntimeError):
        V.generate(jobs, c, tmp_path / "c", tmp_path / "l.json", approved=True)
    ledger = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert len(ledger["lines"]) == 5 and ledger["credits_spent"] == sum(j["credits"] for j in jobs[:5])
    c2 = FakeClient()
    out = V.generate(jobs, c2, tmp_path / "c", tmp_path / "l.json", approved=True)
    assert out["cached"] == 5 and out["generated"] == 34 and len(c2.calls) == 34
    assert V.dialogue_wav(jobs[0], tmp_path / "c") is not None


def test_a_too_short_read_is_refused_and_not_cached(tmp_path):
    class Short:
        def synthesize(self, job):
            return b"x"
    with pytest.raises(ValueError):
        V.generate(_jobs()[:1], Short(), tmp_path / "c", tmp_path / "l.json", approved=True)
    assert V.dialogue_wav(_jobs()[0], tmp_path / "c") is None
