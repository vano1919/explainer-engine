"""Tier 3 writer (llm/opus_code.py): the DeepSeek worker's loop with the Claude API as the model call; no network, a fake api."""
from __future__ import annotations

import json

import pytest

from explainer_engine.llm import claude_api as CA
from explainer_engine.llm import deepseek_api as DS
from explainer_engine.llm import opus_code as OC

ROUTING = {"models": {"opus": "claude-opus-5-5"}, "classes": [{"id": "opus-code", "models": ["opus"], "efforts": ["medium"]}]}


class FakeApi:
    def __init__(self, answers, usd=0.5):
        self.answers, self.usd, self.requests = list(answers), usd, []

    def complete(self, req):
        self.requests.append(req)
        return CA.Result(id=req.id, text=self.answers.pop(0), model="claude-opus-5-5", effort="medium", usd=self.usd)


def blocks(path, old, new):
    return f"### FILE: {path}\n{DS.M_SEARCH}\n{old}\n{DS.M_SPLIT}\n{new}\n{DS.M_REPLACE}\n"


def worker(api, max_usd=5.0):
    return OC.ClaudeWorker(max_usd=max_usd, api=api, routing_cfg=ROUTING)


@pytest.fixture(autouse=True)
def _routing(monkeypatch):
    monkeypatch.setattr(CA, "routing", lambda: ROUTING)


def test_the_loop_applies_a_tested_edit_and_counts_the_money(tmp_path):
    (tmp_path / "m.py").write_text("X = 1\n", encoding="utf-8")
    api = FakeApi([blocks("m.py", "X = 1", "X = 2")])
    res = DS.code(worker(api), "make X two", ["m.py"], root=tmp_path, model="opus", out=tmp_path / "out",
                  test_runner=lambda cmd, root, t: ("X = 2" in (root / "m.py").read_text(encoding="utf-8"), ""), test="t")
    assert res["status"] == "PASS" and res["usd"] == 0.5 and (tmp_path / "m.py").read_text(encoding="utf-8") == "X = 2\n"
    req = api.requests[0]
    assert req.task_class == "opus-code" and req.job == "opus_code" and "make X two" in req.user and "=== FILE: m.py ===" in req.user


def test_a_red_round_is_sent_back_and_leaves_no_trace(tmp_path):
    (tmp_path / "m.py").write_text("X = 1\n", encoding="utf-8")
    api = FakeApi([blocks("m.py", "X = 1", "X = 9"), blocks("m.py", "X = 1", "X = 2")])
    ok = iter([False, True])
    res = DS.code(worker(api), "b", ["m.py"], root=tmp_path, model="opus", out=tmp_path / "out", test="t",
                  test_runner=lambda cmd, root, t: (next(ok), "boom"))
    assert res["status"] == "PASS" and res["rounds"] == 2 and (tmp_path / "m.py").read_text(encoding="utf-8") == "X = 2\n"
    assert "YOUR PREVIOUS ANSWER" in api.requests[1].user and "boom" in api.requests[1].user


def test_the_jobs_own_limit_stops_the_next_call_before_it_is_made(tmp_path):
    (tmp_path / "m.py").write_text("X = 1\n", encoding="utf-8")
    api = FakeApi([blocks("m.py", "X = 1", "X = 9")] * 3, usd=0.5)
    w = worker(api, max_usd=0.5)
    with pytest.raises(OC.OpusCodeError, match="--max-usd"):
        DS.code(w, "b", ["m.py"], root=tmp_path, model="opus", out=tmp_path / "out", test="t",
                test_runner=lambda cmd, root, t: (False, "red"))
    assert len(api.requests) <= 1


def test_a_task_class_that_is_not_in_the_routing_is_refused_never_guessed(tmp_path):
    w = OC.ClaudeWorker(max_usd=1.0, api=FakeApi(["x"]), task_class="no-such-class", routing_cfg=ROUTING)
    with pytest.raises(CA.RoutingError):
        w.complete([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])


def test_a_paid_call_needs_a_card_ref_and_a_key(tmp_path, monkeypatch, capsys):
    brief = tmp_path / "b.md"
    brief.write_text("do it", encoding="utf-8")
    for n in CA.KEY_ENV_NAMES:
        monkeypatch.delenv(n, raising=False)
    assert OC.main(["code", "--brief", str(brief), "--max-usd", "1"]) == 2
    assert "--card-ref" in capsys.readouterr().out
    assert OC.main(["code", "--brief", str(brief), "--max-usd", "1", "--card-ref", "cmsg_x"]) == 2
    assert "KeyAbsent" in capsys.readouterr().out


def test_the_dry_run_prints_an_estimate_and_sends_nothing(tmp_path, monkeypatch, capsys):
    brief = tmp_path / "b.md"
    brief.write_text("do it", encoding="utf-8")
    monkeypatch.setenv("EE_ANTHROPIC_API_KEY", "k" * 12)
    assert OC.main(["code", "--brief", str(brief), "--max-usd", "1", "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["model"] == "claude-opus-5-5" and out["effort"] == "medium" and out["worst_usd_per_round"] > 0 and out["key_present"]
