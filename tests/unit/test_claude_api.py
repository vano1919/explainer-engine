"""The Claude API client (P0d, docs/LLM_API.md): routing, prices, caps, cache, batch, tool loop, refusals. A fake client, no network."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from explainer_engine.core.errors import ConfigError
from explainer_engine.core.ledger import CapReached
from explainer_engine.llm import claude_api as ca

ROOT = Path(__file__).resolve().parents[2]

ROUTING = {
    "models": {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5", "fable": "claude-fable-5-1"},
    "fable_story_stages": {"enabled": False},
    "classes": [
        {"id": "critical-review", "models": ["opus"], "efforts": ["high", "xhigh"]},
        {"id": "qa-judgement", "models": ["sonnet"], "efforts": ["medium"]},
        {"id": "simple-question", "models": ["haiku"], "efforts": ["low"]},
        {"id": "whole-project-plan", "models": ["fable"], "efforts": ["xhigh", "max"]},
        {"id": "script-story-stages", "models": ["fable"], "efforts": ["high"]},
        {"id": "multi-agent-analysis", "models": [], "efforts": []},
    ],
}
CAPS = {"claude_api": {"max_usd": 95.0, "jobs": {"J1": 10.0, "J1b": 8.0, "J4": 5.0, "T": 20.0}, "approval": {"ref": "cmsg_test"}}}


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    (tmp_path / "routing.json").write_text(json.dumps(ROUTING), encoding="utf-8")
    (tmp_path / "caps.json").write_text(json.dumps(CAPS), encoding="utf-8")
    monkeypatch.setenv("EXPLAINER_MODEL_ROUTING", str(tmp_path / "routing.json"))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(tmp_path / "caps.json"))
    monkeypatch.setenv("EXPLAINER_LLM_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("EXPLAINER_LLM_LEDGER", str(tmp_path / "ledger"))
    monkeypatch.delenv("EXPLAINER_LLM_PRICES", raising=False)
    monkeypatch.delenv("EE_ANTHROPIC_API_KEY", raising=False)  # a session that has the alias must not leak it into the tests
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    return tmp_path


def set_caps(tmp_path, **jobs):
    c = json.loads(json.dumps(CAPS))
    c["claude_api"]["jobs"].update(jobs.pop("jobs", {}))
    c["claude_api"].update(jobs)
    (tmp_path / "caps.json").write_text(json.dumps(c), encoding="utf-8")


def resp(text="ok", *, model="claude-opus-5-5", stop="end_turn", inp=1000, out=500, read=0, write=0, searches=0, content=None, details=None):
    usage = NS(input_tokens=inp, output_tokens=out, cache_read_input_tokens=read, cache_creation_input_tokens=write,
               server_tool_use=NS(web_search_requests=searches), iterations=None)
    blocks = content if content is not None else [NS(type="text", text=text)]
    return NS(content=blocks, stop_reason=stop, model=model, usage=usage, _request_id="req_1", stop_details=details)


class Err(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status_code = status


class Midway(Err):
    """A scripted answer that streams ``chunks`` and then breaks with this error (F2)."""

    def __init__(self, status, chunks):
        super().__init__(status)
        self.chunks = chunks


def delta(text):
    return NS(type="content_block_delta", delta=NS(type="text_delta", text=text))


class FakeStream:
    def __init__(self, item):
        self.item = item

    def __iter__(self):
        if isinstance(self.item, Midway):
            for c in self.item.chunks:
                yield NS(type="content_block_delta", delta=NS(type="thinking_delta", thinking=c[1])) if isinstance(c, tuple) else delta(c)
        if isinstance(self.item, Exception):
            raise self.item
        for b in self.item.content:
            t = getattr(b, "type", None)
            if t in ("text", "thinking"):
                yield NS(type="content_block_start", content_block=NS(type=t))
            if t == "text":
                yield delta(b.text)
            elif t == "thinking":
                yield NS(type="content_block_delta", delta=NS(type="thinking_delta", thinking=b.thinking))
                yield NS(type="content_block_delta", delta=NS(type="signature_delta", signature="sig"))

    def get_final_message(self):
        return self.item


class Spaces:
    """One messages namespace: scripted answers (a response, an exception, or a callable), every call recorded. Every call streams
    (the client's only path): ``stream`` yields the text blocks of the scripted response as text deltas."""

    def __init__(self, tag, script):
        self.tag, self.script, self.calls = tag, script, []
        self.batches = NS(create=self._bcreate, retrieve=self._bretrieve, results=self._bresults)
        self.batch_requests, self.batch_results = [], []

    def _take(self, kw):
        self.calls.append((self.tag, kw))
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        return item(kw) if callable(item) else item

    def _next(self, kw):
        item = self._take(kw)
        if isinstance(item, Exception):
            raise item
        return item

    def create(self, **kw):
        return self._next(kw)

    @contextmanager
    def stream(self, **kw):
        yield FakeStream(self._take(kw))

    def count_tokens(self, **kw):
        return NS(input_tokens=2000)

    def _bcreate(self, requests):
        self.batch_requests.append(requests)
        return NS(id="batch_1", processing_status="in_progress")

    def _bretrieve(self, bid):
        return NS(id=bid, processing_status="ended")

    def _bresults(self, bid):
        return iter(self.batch_results)


class Fake:
    def __init__(self, *script):
        script = list(script) or [resp()]
        self.messages = Spaces("direct", script)
        self.beta = NS(messages=Spaces("beta", script))

    @property
    def calls(self):
        return self.messages.calls + self.beta.messages.calls


def api(*script, **kw):
    return ca.ClaudeAPI(Fake(*script), sleep=lambda s: None, **kw)


def req(i="r1", **kw):
    base = dict(id=i, user="review this", task_class="critical-review", job="T", system=["rules"])
    base.update(kw)
    return ca.Request(**base)


# --- routing -----------------------------------------------------------------------------------------------------------
def test_route_defaults_and_narrowing():
    r = ca.route("critical-review")
    assert (r.model, r.effort) == ("claude-opus-5-5", "high")
    assert ca.route("critical-review", effort="xhigh").effort == "xhigh"
    assert ca.route("critical-review", model="claude-opus-5-5").alias == "opus"


def test_route_refuses_outside_the_class():
    with pytest.raises(ca.RoutingError):
        ca.route("critical-review", model="fable")
    with pytest.raises(ca.RoutingError):
        ca.route("critical-review", effort="max")
    with pytest.raises(ca.RoutingError):
        ca.route("nope")
    with pytest.raises(ca.RoutingError):
        ca.route("multi-agent-analysis")


def test_fable_story_stages_follow_the_p0b_flag(env):
    with pytest.raises(ca.RoutingError):
        ca.route("script-story-stages")
    routing = dict(ROUTING, fable_story_stages={"enabled": True})
    (env / "routing.json").write_text(json.dumps(routing), encoding="utf-8")
    assert ca.route("script-story-stages").model == "claude-fable-5-1"


def test_missing_routing_file_is_a_clear_error(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPLAINER_MODEL_ROUTING", str(tmp_path / "none.json"))
    with pytest.raises(ca.RoutingError, match="P0b"):
        ca.route("critical-review")


def test_real_routing_file_when_present_has_the_classes_the_jobs_use(monkeypatch):
    p = ROOT / "config" / "model_routing.json"
    assert p.exists(), "config/model_routing.json is the one home of model and effort (P0b)"
    monkeypatch.setenv("EXPLAINER_MODEL_ROUTING", str(p))
    for cls in ("critical-review", "qa-judgement", "whole-project-plan"):
        ca.route(cls)


# --- prices (F1, F2) ---------------------------------------------------------------------------------------------------
U = {"input": 0, "output": 0, "cache_read": 0, "write_5m": 0, "write_1h": 0, "searches": 0}


def test_cache_writes_and_reads_are_priced():
    m = "claude-opus-5-5"
    assert ca.usd_of(m, {**U, "input": 1_000_000}) == pytest.approx(4.0)
    assert ca.usd_of(m, {**U, "write_5m": 1_000_000}) == pytest.approx(5.0)
    assert ca.usd_of(m, {**U, "write_1h": 1_000_000}) == pytest.approx(8.0)
    assert ca.usd_of(m, {**U, "cache_read": 1_000_000}) == pytest.approx(0.20)
    assert ca.usd_of(m, {**U, "output": 1_000_000}) == pytest.approx(20.0)
    assert ca.usd_of("claude-fable-5-1", {**U, "write_5m": 1_000_000}) == pytest.approx(12.5)
    assert ca.usd_of("claude-fable-5-1", {**U, "write_1h": 1_000_000}) == pytest.approx(20.0)
    assert ca.usd_of("claude-sonnet-5-5", {**U, "write_5m": 1_000_000}) == pytest.approx(2.5)


def test_web_search_is_ten_dollars_per_thousand_and_not_batch_discounted():
    assert ca.usd_of("claude-opus-5-5", {**U, "searches": 100}) == pytest.approx(1.0)
    assert ca.usd_of("claude-opus-5-5", {**U, "searches": 100, "output": 1_000_000}, batch=True) == pytest.approx(1.0 + 10.0)


def test_batch_halves_tokens_and_haiku_long_prompt_tier():
    assert ca.usd_of("claude-opus-5-5", {**U, "input": 1_000_000}, batch=True) == pytest.approx(2.0)
    assert ca.usd_of("claude-haiku-5-5", {**U, "input": 100_000}) == pytest.approx(0.01)
    assert ca.usd_of("claude-haiku-5-5", {**U, "input": 200_000}) == pytest.approx(0.10)


def test_unknown_model_is_refused_not_guessed():
    with pytest.raises(ca.PriceMissing):
        ca.usd_of("claude-unknown-9", U)


def test_usage_reads_the_ttl_split_and_server_tool_use():
    u = NS(input_tokens=1, output_tokens=2, cache_read_input_tokens=3, cache_creation_input_tokens=10,
           cache_creation=NS(ephemeral_5m_input_tokens=4, ephemeral_1h_input_tokens=6), server_tool_use=NS(web_search_requests=2))
    assert ca.usage_of(NS(usage=u)) == {"input": 1, "output": 2, "cache_read": 3, "write_5m": 4, "write_1h": 6, "searches": 2}
    u2 = NS(input_tokens=1, output_tokens=2, cache_read_input_tokens=0, cache_creation_input_tokens=10, server_tool_use=None)
    assert ca.usage_of(NS(usage=u2), "1h")["write_1h"] == 10


# --- the request body (F5, F6) -----------------------------------------------------------------------------------------
def test_body_has_effort_cache_prefix_and_no_forbidden_parameter():
    p = ca.build_params(req(system=["stage page", "rules"]), ca.route("critical-review"))
    assert p["output_config"] == {"effort": "high"}
    assert "cache_control" not in p["system"][0] and p["system"][1]["cache_control"] == {"type": "ephemeral"}
    assert p["messages"] == [{"role": "user", "content": "review this"}]
    assert not set(ca.FORBIDDEN_PARAMS) & set(p) and p["thinking"] == {"type": "adaptive", "display": "summarized"}
    p2 = ca.build_params(req(schema={"type": "object"}, cache_ttl="1h"), ca.route("critical-review"))
    assert p2["output_config"]["format"] == {"type": "json_schema", "schema": {"type": "object"}}
    assert p2["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}


def test_body_keys_are_accepted_by_the_installed_sdk():
    inspect = pytest.importorskip("inspect")
    anthropic = pytest.importorskip("anthropic")
    from anthropic.resources.messages import Messages
    names = set(inspect.signature(Messages.create).parameters)
    p = ca.build_params(req(web_search_max_uses=3, tools_root="."), ca.route("critical-review"))
    assert set(p) <= names, set(p) - names
    assert anthropic


# --- secrets (F7) ------------------------------------------------------------------------------------------------------
def test_secret_patterns_follow_the_hygiene_test():
    hygiene = (ROOT / "tests" / "unit" / "test_repo_hygiene.py").read_text(encoding="utf-8")
    assert ca.SECRET_NAMES.pattern in hygiene


@pytest.mark.parametrize("text", ["key sk-ant-api03-abcdefghijkl", "ANTHROPIC_API_KEY=abc", "hf_" + "a" * 30, "ghp_" + "b" * 30,
                                  "-----BEGIN RSA PRIVATE KEY-----", "AKIA" + "A" * 16, "aws_secret_access_key = abcd",
                                  "RUNPOD_API_KEY=" + "x1" * 15, "Authorization: Bearer " + "a" * 30, "github_pat_" + "B" * 30,
                                  "sk_" + "a1" * 25, "sk-proj-" + "Z" * 30, "xoxb-1234567890-abcdef", 'YOUTUBE_TOKEN_B64="' + "Q" * 40 + '"'])
def test_a_secret_in_the_prompt_is_refused_before_any_call(text):
    a = api()
    with pytest.raises(ca.SecretInPrompt):
        a.complete(req(user=text))
    with pytest.raises(ca.SecretInPrompt):
        a.complete(req(system=[text]))
    assert a._client.calls == []


@pytest.mark.parametrize("path", ["tools/gemini/api_key.txt", ".env", "x/token_google.json", "a/id_ed25519", "c/secret_notes.md",
                                  "../tools/x", "a/../../tools/x", ".env.local", "id_rsa", "a/.netrc", "certs/server.key", "x/.git/config"])
def test_secret_paths_are_refused(path):
    with pytest.raises(ca.SecretInPrompt):
        ca.check_secret_path(path)


def test_job_file_with_a_secret_path_or_text_is_refused(tmp_path):
    (tmp_path / "ok.md").write_text("fine", encoding="utf-8")
    (tmp_path / "bad.md").write_text("ANTHROPIC_API_KEY=x", encoding="utf-8")
    job = {"job": "T", "task_class": "critical-review", "system_files": ["ok.md"], "requests": [{"id": "a", "user_file": "bad.md"}]}
    (tmp_path / "job.json").write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ca.SecretInPrompt):
        ca.load_job(tmp_path / "job.json")
    job["requests"] = [{"id": "a", "user_file": "tools/x.txt"}]
    (tmp_path / "job.json").write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ca.SecretInPrompt):
        ca.load_job(tmp_path / "job.json")


# --- one call: ledger, cache, caps -------------------------------------------------------------------------------------
def test_call_is_settled_logged_and_cached():
    a = api(resp("verdict", inp=1000, out=500, write=2000))
    r = a.complete(req())
    assert r.text == "verdict" and not r.cached
    expect = (1000 * 4 + 500 * 20 + 2000 * 5) / 1e6
    assert r.usd == pytest.approx(expect)
    assert a.ledger.total() == pytest.approx(expect)
    rows = a.ledger.rows()
    assert [x["ev"] for x in rows] == ["start", "done"] and rows[1]["usage"]["write_5m"] == 2000
    again = a.complete(req())
    assert again.cached and again.usd == 0 and again.text == "verdict"
    assert len(a._client.calls) == 1                       # nothing is paid twice
    assert a.ledger.total() == pytest.approx(expect)       # a cache hit is a line with usd 0
    assert a.ledger.rows()[-1]["cached"] is True


def test_a_changed_prompt_is_a_new_call():
    a = api()
    a.complete(req())
    a.complete(req(user="other text"))
    assert len(a._client.calls) == 2


def test_job_cap_stops_at_80_percent(env):
    set_caps(env, jobs={"T": 0.001})
    a = api()
    with pytest.raises(CapReached):
        a.complete(req())
    assert a._client.calls == []


def test_total_cap_stops_at_80_percent(env):
    set_caps(env, max_usd=0.2, jobs={"T": 0.2})
    a = api()
    with pytest.raises(CapReached):
        a.complete(req())                  # 16000 output tokens reserved = $0.32 passes 80 % of $0.2
    assert a._client.calls == []


def test_job_without_a_cap_line_is_refused(env):
    with pytest.raises(ConfigError):
        api().complete(req(job="J9"))


def test_job_cap_above_the_whole_credit_is_refused(env):
    set_caps(env, jobs={"T": 500.0})
    with pytest.raises(Exception, match="above"):
        api().complete(req())


def test_no_claude_api_line_means_no_spending(env):
    (env / "caps.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError):
        api().complete(req())


def test_real_client_needs_the_key_and_the_recorded_approval(env, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("EE_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ca.KeyAbsent):
        ca.ClaudeAPI().complete(req())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    set_caps(env, approval=None)
    with pytest.raises(ca.NotApproved):
        ca.ClaudeAPI().complete(req())


def test_real_spend_caps_file_holds_the_or24_caps():
    c = json.loads((ROOT / "config" / "spend_caps.json").read_text(encoding="utf-8"))["claude_api"]
    assert c["max_usd"] == 95.0 and sum(c["jobs"].values()) == pytest.approx(c["max_usd"])
    # 2026-10-30: plan v2 got its own $28 line from J1b's unspent part, all of J6, J4 and the reserve (ვანო's card answer, docs/PROGRESS.md)
    assert c["jobs"]["J1"] == 10.0 and c["jobs"]["J1b"] == 5.02 and c["jobs"]["J6"] == 0.0 and c["jobs"]["plan_v2"] == 18.0
    # 2026-10-30 20:46 UTC (ვანო's card, all lines): the night run's four lines, paid from plan_v2, J3, J4, J5 and the reserve
    assert [c["jobs"][k] for k in ("final_review", "change_plan", "fix_desk", "result_check")] == [8.0, 8.0, 8.0, 10.0]
    assert c["jobs"]["J1b"] >= 5.016946 and c["approval"]["ref"]   # J1b keeps its cover for the lost scope A run


def test_a_call_without_a_result_line_stops_the_next_one():
    a = api()
    a.ledger.append({"ev": "start", "uid": "lost1", "job": "T", "id": "x"})
    with pytest.raises(ca.LedgerGap):
        a.complete(req())
    assert a._client.calls == []
    a.ledger.append({"ev": "done", "uid": "lost1", "job": "T", "id": "x", "usd": 0.5})
    a.complete(req())
    assert a.ledger.total() == pytest.approx(0.5 + (1000 * 4 + 500 * 20) / 1e6)


def test_uncharged_error_voids_the_start_line_and_refunds():
    a = api(Err(400))
    with pytest.raises(Err):
        a.complete(req())
    assert [x["ev"] for x in a.ledger.rows()] == ["start", "void"]
    assert a.run_for("T").spent(ca.SERVICE) == 0
    a.ledger.check_gap()


# --- refusals, truncation, overload, Fable -----------------------------------------------------------------------------
def test_refusal_is_reported_paid_and_not_cached():
    a = api(resp("", stop="refusal", details=NS(category="cyber", explanation="no")))
    with pytest.raises(ca.Refused) as e:
        a.complete(req())
    assert e.value.category == "cyber"
    assert a.ledger.total() > 0 and a.cache.get(ca.cache_key(ca.build_params(req(), ca.route("critical-review")))) is None


def test_truncated_answer_is_paid_but_not_cached():
    a = api(resp("cut", stop="max_tokens"))
    with pytest.raises(ca.OutputTruncated):
        a.complete(req())
    assert a.ledger.total() > 0
    assert not a.cache.dir.exists() or not list(a.cache.dir.glob("*.json"))


def test_overload_waits_then_succeeds_and_gives_up_after_fifteen_minutes():
    a = api(Err(529), Err(429), resp("late"))
    assert a.complete(req()).text == "late"
    t = {"now": 0.0}
    waits = []

    def sleep(s):
        waits.append(s)
        t["now"] += s

    b = ca.ClaudeAPI(Fake(Err(529)), sleep=sleep, clock=lambda: t["now"])
    with pytest.raises(ca.Overloaded):
        b.complete(req(user="a different request"))
    assert 600 < sum(waits) <= ca.OVERLOAD_WAIT_S
    assert b.ledger.open_calls() == []


def test_long_output_is_streamed():
    a = api()
    a.complete(req(max_tokens=64000))
    calls = a._client.calls
    assert len(calls) == 1 and calls[0][1]["max_tokens"] == 64000
    a.complete(req("short", user="another", max_tokens=1000))     # F1: every call streams now, not only the long ones
    assert len(a._client.calls) == 2 and sorted((ledger_streams(a))) == ["ok", "ok"]


def test_fable_400_falls_to_opus_xhigh_and_says_so():
    a = api(Err(400), resp("by opus", model="claude-opus-5-5"))
    q = req(task_class="whole-project-plan", model="fable", effort="xhigh", fallback_to=("opus", "xhigh"), max_tokens=32000)   # the xhigh floor
    r = a.complete(q)
    assert r.text == "by opus" and r.fell_back_to == "claude-opus-5-5"
    first, second = a._client.calls
    assert first[1]["model"] == "claude-fable-5-1" and second[1]["model"] == "claude-opus-5-5"
    assert second[1]["output_config"]["effort"] == "xhigh"
    done = [x for x in a.ledger.rows() if x["ev"] == "done"][-1]
    assert done["fell_back_from"] == "claude-fable-5-1"


def test_fable_400_without_a_declared_fallback_is_not_silent():
    a = api(Err(400))
    with pytest.raises(Err):
        a.complete(req(task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=32000))


# --- fallbacks (F3, F4) ------------------------------------------------------------------------------------------------
def test_direct_calls_send_fallbacks_default_where_the_model_has_them():
    a = api()
    a.complete(req())                                   # opus
    a.complete(req(i="s", task_class="qa-judgement"))   # sonnet
    a.complete(req(i="h", task_class="simple-question"))  # haiku: none
    by = {kw["model"]: (tag, kw.get("fallbacks"), kw.get("betas")) for tag, kw in a._client.calls}
    assert by["claude-opus-5-5"] == ("beta", "default", [ca.FALLBACK_BETA])
    assert by["claude-sonnet-5-5"] == ("beta", "default", [ca.FALLBACK_BETA])
    assert by["claude-haiku-5-5"] == ("direct", None, None)


def test_batch_never_carries_fallbacks_and_a_refused_item_is_rerun_once_direct():
    a = api(resp("direct rerun"))
    reqs = [req(f"q{i}", task_class="qa-judgement") for i in range(ca.BATCH_MIN)]
    reqs = [ca.Request(**{**q.__dict__, "user": f"text {i}"}) for i, q in enumerate(reqs)]
    ok = lambda i: NS(custom_id=f"q{i}", result=NS(type="succeeded", message=resp(f"a{i}", model="claude-sonnet-5-5", inp=1000, out=100)))  # noqa: E731
    refused = NS(custom_id="q3", result=NS(type="succeeded", message=resp("", model="claude-sonnet-5-5", stop="refusal")))
    a._client.messages.batch_results = [refused] + [ok(i) for i in range(ca.BATCH_MIN) if i != 3]
    out = a.run_job(reqs)
    sent = a._client.messages.batch_requests
    assert len(sent) == 1 and len(sent[0]) == ca.BATCH_MIN
    assert all("fallbacks" not in r["params"] and "betas" not in r["params"] for r in sent[0])
    assert out["q3"].text == "direct rerun"                  # re-run once, direct, with fallbacks; not reworded
    direct = a._client.calls
    assert len(direct) == 1 and direct[0][0] == "beta" and direct[0][1]["fallbacks"] == "default"
    assert direct[0][1]["messages"][0]["content"] == "text 3"
    assert out["q0"].text == "a0" and out["q0"].usd == pytest.approx((1000 * 2 + 100 * 10) / 1e6 * 0.5)
    a.ledger.check_gap()


def test_batch_resume_does_not_submit_twice():
    a = api()
    reqs = [ca.Request(id=f"q{i}", user=f"t{i}", task_class="qa-judgement", job="T") for i in range(ca.BATCH_MIN)]
    a._client.messages.batch_results = [NS(custom_id=f"q{i}", result=NS(type="succeeded", message=resp("x", model="claude-sonnet-5-5")))
                                        for i in range(ca.BATCH_MIN)]
    a.run_job(reqs)
    b = ca.ClaudeAPI(a._client, sleep=lambda s: None, cache=ca.ResponseCache(a.cache.dir / "other"))
    b.run_job(reqs)
    assert len(a._client.messages.batch_requests) == 1


def test_small_jobs_go_direct_in_order():
    a = api()
    out = a.run_job([req(f"r{i}", user=f"u{i}") for i in range(3)])
    assert list(out) == ["r0", "r1", "r2"] and a._client.messages.batch_requests == []


# --- the read-only repo tool loop --------------------------------------------------------------------------------------
def tool_turn(name, args, tid="tu1", **usage):
    return resp(content=[NS(type="tool_use", name=name, input=args, id=tid)], stop="tool_use", **usage)


def warm_turns(n, path="."):
    """n tool turns whose usage looks like a loop that caches its history: the read grows, little is fresh."""
    return [tool_turn("list_dir", {"path": path}, f"w{i}", inp=100, read=20000 + 2000 * i, write=2000) for i in range(n)]


def test_tool_loop_reads_files_and_reserves_every_turn(tmp_path):
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "a.py").write_text("x = 1\ny = 2\n", encoding="utf-8")
    a = api(tool_turn("read_file", {"path": "a.py", "start": 1, "end": 2}), resp("VERDICT: ok"))
    r = a.complete(req(tools_root=str(tmp_path / "repo"), cache_salt="sha1"))
    assert r.text == "VERDICT: ok" and r.turns == 2
    second = a._client.calls[1][1]["messages"]
    assert second[-1]["content"][0]["content"] == "1: x = 1\n2: y = 2"
    assert [x["ev"] for x in a.ledger.rows()] == ["start", "done", "start", "done"]
    assert r.usd == pytest.approx(2 * (1000 * 4 + 500 * 20) / 1e6)


def test_tools_are_read_only_and_cannot_leave_the_checkout(tmp_path):
    assert {t["name"] for t in ca.REPO_TOOLS} == {"list_dir", "read_file", "grep"}
    root = tmp_path / "repo"
    (root / "tools").mkdir(parents=True)
    (root / "tools" / "k.txt").write_text("hello", encoding="utf-8")
    (root / ".env").write_text("ANTHROPIC_API_KEY=abc", encoding="utf-8")
    (root / "n.txt").write_text("key sk-ant-api03-abcdefghijkl\nplain", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("no", encoding="utf-8")
    assert "error" in ca.run_repo_tool(root, "read_file", {"path": "../outside.txt", "start": 1, "end": 2})
    assert "error" in ca.run_repo_tool(root, "read_file", {"path": ".env", "start": 1, "end": 2})
    assert "error" in ca.run_repo_tool(root, "read_file", {"path": "tools/k.txt", "start": 1, "end": 2})
    shown = ca.run_repo_tool(root, "read_file", {"path": "n.txt", "start": 1, "end": 2})
    assert "sk-ant" not in shown and "[REDACTED-SECRET-LIKE]" in shown and "2: plain" in shown
    assert "tools" not in ca.run_repo_tool(root, "list_dir", {"path": "."}) and ".env" not in ca.run_repo_tool(root, "list_dir", {"path": "."})
    assert ca.run_repo_tool(root, "grep", {"pattern": "plain", "path": "."}) == "n.txt:2: plain"
    assert ca.run_repo_tool(root, "grep", {"pattern": "sk-ant", "path": "."}) == "(no match)"
    assert ca.run_repo_tool(root, "write_file", {"path": "x"}).startswith("error")


def test_tool_loop_stops_at_max_turns(tmp_path):
    a = api(*warm_turns(3))
    with pytest.raises(ca.OutputTruncated):
        a.complete(req(tools_root=str(tmp_path), max_turns=3))
    assert len(a._client.calls) == 3


# --- web search (F2) and estimate --------------------------------------------------------------------------------------
def test_web_search_requests_are_counted_in_the_ledger():
    a = api(resp("found", searches=4))
    r = a.complete(req(web_search_max_uses=5))
    assert r.usd == pytest.approx((1000 * 4 + 500 * 20) / 1e6 + 4 * 10 / 1000)
    assert a._client.calls[0][1]["tools"][0]["type"] == "web_search_20260209"


def test_estimate_spends_nothing_and_reports_the_cap():
    e = ca.estimate([req("a"), req("b", user="x" * 30000)])
    assert e["worst_total_usd"] > 0 and e["job_cap"] == 20.0 and e["stop_at_job"] == 16.0
    assert all(not row["exact"] for row in e["requests"]) and e["ledger_total"] == 0


def test_estimate_marks_cached_requests_free():
    a = api()
    a.complete(req("a"))
    e = ca.estimate([req("a")], api=a)
    assert e["requests"][0]["cached"] and e["requests"][0]["worst_usd"] == 0 and e["requests"][0]["exact"]


def test_cli_status_never_prints_the_key(capsys, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "super-secret-value")
    assert ca.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "super-secret-value" not in out and '"key_present": true' in out


# --- review of PR #34: symlinks, wider patterns, fallback prices --------------------------------------------------------
def test_grep_and_list_do_not_follow_links_out_of_the_checkout(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "aws.txt"
    outside.write_text("aws_secret_access_key = abcdEFGH1234\nRUNPOD_API_KEY=" + "x1" * 15 + "\nplain line\n", encoding="utf-8")
    (root / "env_real").write_text("TOKEN=" + "a" * 30 + "\nplain line\n", encoding="utf-8")
    (root / "link_out.txt").symlink_to(outside)
    (root / "link_env").symlink_to(root / "env_real")
    (root / ".env.local").write_text("plain line\n", encoding="utf-8")
    (root / "outdir").symlink_to(tmp_path, target_is_directory=True)
    (root / "ok.txt").write_text("plain line\n", encoding="utf-8")
    got = ca.run_repo_tool(root, "grep", {"pattern": ".", "path": "."})
    assert "aws_secret" not in got and "RUNPOD" not in got and "TOKEN=" not in got
    assert "ok.txt:1: plain line" in got and "link_out" not in got and ".env.local" not in got and "outdir" not in got
    listing = ca.run_repo_tool(root, "list_dir", {"path": "."})
    assert "link_out.txt" not in listing and "link_env" not in listing and ".env.local" not in listing and "outdir" not in listing
    for path in ("link_out.txt", ".env.local", "outdir/aws.txt"):
        assert ca.run_repo_tool(root, "read_file", {"path": path, "start": 1, "end": 5}).startswith("error")
    inside = ca.run_repo_tool(root, "read_file", {"path": "link_env", "start": 1, "end": 5})   # a link INSIDE the root is read, redacted
    assert "a" * 30 not in inside and "[REDACTED-SECRET-LIKE]" in inside
    assert ca.run_repo_tool(root, "grep", {"pattern": ".", "path": "outdir"}).startswith("error")


def test_job_file_path_with_dotdot_tools_is_refused(tmp_path):
    job = {"job": "T", "task_class": "critical-review", "requests": [{"id": "a", "user_file": "../tools/x.txt"}]}
    (tmp_path / "job.json").write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ca.SecretInPrompt):
        ca.load_job(tmp_path / "job.json")


def test_fallback_targets_have_price_lines():
    pr = ca.prices()["models"]
    for m in ("claude-opus-4-8", "claude-opus-5", "claude-sonnet-5"):
        assert ca.usd_of(m, {**U, "input": 1_000_000}) == pytest.approx(pr[m]["in"])


def iteration(model, inp, out, typ="message"):
    return NS(type=typ, model=model, input_tokens=inp, output_tokens=out, cache_read_input_tokens=0, cache_creation_input_tokens=0,
              server_tool_use=None)


def test_fallback_answer_is_priced_with_every_iteration_at_its_own_model():
    r = resp("by fallback", model="claude-opus-4-8", inp=1000, out=500)
    r.usage.iterations = [iteration("claude-opus-5-5", 1000, 20, "refusal"), iteration("claude-opus-4-8", 1000, 500, "fallback_message")]
    a = api(r)
    res = a.complete(req())
    expect = (1000 * 4 + 20 * 20) / 1e6 + (1000 * 5 + 500 * 25) / 1e6
    assert res.usd == pytest.approx(expect)
    done = [x for x in a.ledger.rows() if x["ev"] == "done"][-1]
    assert done["fallback_ran"] is True and [i["model"] for i in done["iterations"]] == ["claude-opus-5-5", "claude-opus-4-8"]


def test_a_model_without_a_price_still_gets_a_done_line_at_the_reserved_amount():
    a = api(resp("answer", model="claude-mystery-9"))
    res = a.complete(req())
    assert res.text == "answer" and res.usd > 0
    rows = a.ledger.rows()
    assert [x["ev"] for x in rows] == ["start", "done"] and "price missing" in rows[1]["note"]
    assert rows[1]["usd"] == pytest.approx(rows[0]["reserved"], abs=1e-5)
    a.ledger.check_gap()


def test_tool_loop_caches_the_first_message(tmp_path):
    a = api(tool_turn("list_dir", {"path": "."}), resp("done"))
    (tmp_path / "x.txt").write_text("a", encoding="utf-8")
    a.complete(req(tools_root=str(tmp_path)))
    first = a._client.calls[0][1]["messages"][0]["content"][0]
    assert first["text"] == "review this" and first["cache_control"] == {"type": "ephemeral"}


def test_void_defaults_to_the_reserved_amount(capsys):
    a = ca.ClaudeAPI(Fake())
    a.ledger.append({"ev": "start", "uid": "lost2", "job": "T", "id": "x", "reserved": 0.42})
    assert ca.main(["void", "lost2"]) == 0
    assert a.ledger.total() == pytest.approx(0.42) and a.ledger.open_calls() == []
    assert ca.main(["void", "nope"]) == 1


def test_run_refuses_a_job_whose_worst_case_passes_the_stop(env, capsys):
    set_caps(env, jobs={"T": 0.1})
    write_proof()
    job = {"job": "T", "task_class": "critical-review", "requests": [{"id": "a", "user": "hi"}]}
    (env / "job.json").write_text(json.dumps(job), encoding="utf-8")
    assert ca.main(["run", str(env / "job.json")]) == 3
    assert "refused" in capsys.readouterr().out


def test_batch_rerun_that_truncates_does_not_lose_the_other_results():
    a = api(resp("cut", model="claude-sonnet-5-5", stop="max_tokens"))
    reqs = [ca.Request(id=f"q{i}", user=f"t{i}", task_class="qa-judgement", job="T") for i in range(ca.BATCH_MIN)]
    refused = NS(custom_id="q0", result=NS(type="succeeded", message=resp("", model="claude-sonnet-5-5", stop="refusal")))
    a._client.messages.batch_results = [refused] + [NS(custom_id=f"q{i}", result=NS(type="succeeded", message=resp("x", model="claude-sonnet-5-5")))
                                                    for i in range(1, ca.BATCH_MIN)]
    out = a.run_job(reqs)
    assert isinstance(out["q0"], ca.OutputTruncated) and out["q1"].text == "x" and len(out) == ca.BATCH_MIN
    assert list((ca.ledger_dir()).glob("batch-T-*.json"))


def test_the_key_can_come_from_the_alias_name(env, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("EE_ANTHROPIC_API_KEY", raising=False)
    assert ca.api_key() is None
    monkeypatch.setenv("EE_ANTHROPIC_API_KEY", "alias-key-not-real")
    assert ca.api_key() == "alias-key-not-real"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "main-key-not-real")
    assert ca.api_key() == "main-key-not-real"


# --- the loop's cache breakpoint, partial saves and the loop estimate (J1b scope A, 2026-10-30) -------------------------------
def test_tool_loop_moves_the_cache_breakpoint_to_the_last_block_every_turn(tmp_path):
    a = api(tool_turn("list_dir", {"path": "."}, "t1"), tool_turn("list_dir", {"path": "."}, "t2"), resp("done"))
    a.complete(req(tools_root=str(tmp_path)))
    calls = [c[1]["messages"] for c in a._client.calls]

    def marks(msgs):                                                    # (message index) of every dict block carrying a breakpoint
        return [i for i, m in enumerate(msgs) if isinstance(m["content"], list) for b in m["content"] if isinstance(b, dict) and "cache_control" in b]
    assert [marks(m) for m in calls] == [[0], [0, 2], [0, 2, 4]]        # the first message's own, last turn's breakpoint and the newest block: 3 + the system prefix = the API's four
    four = a._client.calls[2][1]
    assert len(marks(calls[2])) + len(four["system"]) <= 4


def test_a_stopped_tool_loop_leaves_its_partial_transcript_on_disk(env, tmp_path):
    (tmp_path / "x.txt").write_text("a", encoding="utf-8")
    a = api(tool_turn("read_file", {"path": "x.txt", "start": 1, "end": 1}, "t1"), tool_turn("list_dir", {"path": "."}, "t2"))
    with pytest.raises(ca.OutputTruncated) as ei:
        a.complete(req("J", tools_root=str(tmp_path), max_turns=2))
    part = ca.ledger_dir() / "partial_T_J.json"
    assert part.exists() and str(part) in "".join(getattr(ei.value, "__notes__", []))
    d = json.loads(part.read_text(encoding="utf-8"))
    assert d["turns"] == 2 and d["usd_so_far"] > 0 and "OutputTruncated" in d["stopped_by"]
    assert [b["type"] for m in d["messages"] for b in m["blocks"]] == ["tool_use", "tool_result", "tool_use", "tool_result"]
    assert d["messages"][1]["blocks"][0]["content"] == "1: a"


def test_a_cap_stop_in_the_middle_of_a_loop_keeps_the_turns_so_far(env, tmp_path):
    set_caps(env, jobs={"T": 0.5})                                      # a turn reserves ~0.33 and settles at ~0.014: the stop is 0.4
    a = api()

    def other_spend(kw):                                                # F5 now asks for a wrap-up turn before the cap bites; money
        a.run_for("T").reserve(ca.SERVICE, 0.37, "other")               # that appears at once (another process) still can't be reserved
        return warm_turns(1)[0]
    a._client.messages.script[:] = [warm_turns(1)[0], other_spend, warm_turns(1)[0]]
    with pytest.raises(CapReached):
        a.complete(req("K", tools_root=str(tmp_path), max_turns=30))
    d = json.loads((ca.ledger_dir() / "partial_T_K.json").read_text(encoding="utf-8"))
    assert 1 < d["turns"] < 30 and "CapReached" in d["stopped_by"] and d["messages"]


def test_estimate_says_a_tool_loop_is_priced_for_its_first_turn_only_and_prices_the_loop(env, tmp_path):
    set_caps(env, jobs={"T": 5.0})
    q = req(tools_root=str(tmp_path), max_turns=10)
    row = ca.estimate([q])["requests"][0]
    assert "FIRST turn only" in row["loop"]["warning"] and row["loop"]["turns"] == 10
    row3 = ca.estimate([q], turns=3)["requests"][0]
    assert row3["loop"]["turns"] == 3 and 0 < row3["loop"]["usd_if_cached"] < row["loop"]["usd_if_cached"]
    assert "loop" not in ca.estimate([req()])["requests"][0]
    # cached re-reads are cheaper than re-sending the history fresh: 10 turns of 30k context
    assert ca.loop_usd("claude-opus-5-5", 30000, 10, 6000, 600) < 10 * ca.usd_of("claude-opus-5-5", {"input": 60000, "output": 600, "cache_read": 0,
                                                                                    "write_5m": 0, "write_1h": 0, "searches": 0})


# --- follow-up to the review of the cache fix: estimate bounds, the loop in worst_total, two breakpoints ----------------------------
def test_with_breakpoint_keeps_last_turns_breakpoint_so_many_parallel_results_still_hit_the_cache():
    many = [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "x"} for i in range(14)]    # more than ~20 blocks in one turn
    msgs = [{"role": "user", "content": [{"type": "text", "text": "q", "cache_control": {"type": "ephemeral"}}]},
            {"role": "assistant", "content": [NS(type="text", text="a")]},
            {"role": "user", "content": many},
            {"role": "assistant", "content": [NS(type="text", text="b")]},
            {"role": "user", "content": [dict(b) for b in many]}]
    out = ca._with_breakpoint(msgs)
    assert [i for i, m in enumerate(out) if isinstance(m["content"][-1], dict) and "cache_control" in m["content"][-1]] == [0, 2, 4]
    assert "cache_control" not in msgs[4]["content"][-1] and "cache_control" not in msgs[2]["content"][-1]    # the input is not mutated
    assert ca._with_breakpoint(msgs[:1])[0]["content"][-1]["cache_control"] == {"type": "ephemeral"}


def test_loop_usd_orders_cached_below_uncached_below_miss_and_bills_the_previous_output_as_a_write():
    m, kw = "claude-opus-5-5", dict(first_tokens=30000, turns=20, new_per_turn=6000, out_per_turn=600)
    cached, unc, miss = (ca.loop_usd(m, **kw, mode=x) for x in ("cached", "uncached", "miss"))
    assert cached < unc < miss
    assert ca.loop_usd(m, **kw, mode="cached") > ca.loop_usd(m, **{**kw, "out_per_turn": 0}, mode="cached")
    zero = {"input": 0, "output": 0, "cache_read": 0, "write_5m": 0, "write_1h": 0, "searches": 0}
    turn2 = ca.usd_of(m, {**zero, "cache_read": 30000, "write_5m": 6600, "output": 600})      # turn 2: the tool result AND turn 1's output are writes
    assert ca.loop_usd(m, 30000, 2, 6000, 600, mode="cached") == pytest.approx(ca.usd_of(m, {**zero, "write_5m": 30000, "output": 600}) + turn2)
    with pytest.raises(ValueError):
        ca.loop_usd(m, 1, 1, 1, 1, mode="nope")


def test_estimate_shows_the_three_loop_figures_and_counts_the_loop_in_worst_total(env, tmp_path):
    set_caps(env, jobs={"T": 5.0})
    q = req(tools_root=str(tmp_path), max_turns=12, user="x" * 200_000, max_tokens=1000)     # ~50k tokens: the loop outweighs one turn
    row = ca.estimate([q])["requests"][0]
    lp = row["loop"]
    assert lp["usd_if_cached"] < lp["usd_if_uncached"] < lp["usd_if_miss"] and "costs more than uncached" in lp["warning"]
    assert row["worst_usd"] == lp["usd_if_cached"] and lp["bound"] == "cached"            # no longer turn 1 only
    safe = ca.estimate([q], loop_bound="uncached")["requests"][0]
    assert safe["worst_usd"] == safe["loop"]["usd_if_uncached"] > row["worst_usd"]
    assert ca.estimate([q], loop_bound="miss")["requests"][0]["worst_usd"] == lp["usd_if_miss"]
    assert ca.estimate([req()])["requests"][0].get("loop") is None


def test_run_refuses_a_loop_job_by_the_chosen_loop_bound(env, tmp_path, capsys):
    job = {"job": "T", "task_class": "critical-review", "max_turns": 40, "tools_root": str(tmp_path), "max_tokens": 1000,
           "requests": [{"id": "a", "user": "x" * 200_000}]}
    (env / "job.json").write_text(json.dumps(job), encoding="utf-8")
    write_proof()
    est = {m: ca.estimate(ca.load_job(env / "job.json"), loop_bound=m)["worst_total_usd"] for m in ("cached", "uncached")}
    set_caps(env, jobs={"T": round((est["cached"] + est["uncached"]) / 2 / 0.8, 2)})   # its 80 % stop sits between the two figures
    assert ca.estimate(ca.load_job(env / "job.json"))["fits_job_cap"]                  # the default bound: the expected, cached case
    assert ca.main(["run", str(env / "job.json"), "--loop-bound", "uncached"]) == 3 and "refused" in capsys.readouterr().out


# --- the runtime cache guard (the `cached` loop bound must check itself) ---------------------------------------------------------
def test_a_loop_whose_history_is_cached_runs_on_past_turn_3(tmp_path):
    a = api(*warm_turns(4), resp("done", inp=100, read=30000, write=2000))
    r = a.complete(req(tools_root=str(tmp_path), max_turns=8))
    assert r.text == "done" and r.turns == 5


def test_a_loop_whose_cache_read_is_stuck_at_the_prefix_stops_at_turn_3_with_the_partial_on_disk(env, tmp_path):
    (tmp_path / "x.txt").write_text("a", encoding="utf-8")
    prefix = 22746                                                      # what the J1b scope A ledger showed on every turn
    broken = [tool_turn("list_dir", {"path": "."}, f"b{i}", inp=1000 + 2000 * i, read=prefix, write=0) for i in range(10)]
    a = api(*broken)
    with pytest.raises(ca.CacheCold, match=r"turn 3.*cache read stayed at 22746") as ei:
        a.complete(req("C", tools_root=str(tmp_path), max_turns=20))
    assert len(a._client.calls) == 3                                    # stopped within three turns, not at the line
    part = ca.ledger_dir() / "partial_T_C.json"
    assert part.exists() and str(part) in "".join(getattr(ei.value, "__notes__", []))
    assert json.loads(part.read_text(encoding="utf-8"))["turns"] == 3


def answer_part(path):
    """What a stream file holds after its ``[answer]`` line (the file starts with a header line and may hold a ``[thinking]`` part)."""
    t = Path(path).read_text(encoding="utf-8")
    return t.split("[answer]\n", 1)[1] if "[answer]\n" in t else ""


def ledger_streams(a):
    """The answer part of every stream file of the ledger folder."""
    return [answer_part(p) for p in (ca.ledger_dir() / "stream").glob("*.txt")]


def test_the_guard_names_the_measured_share_when_most_of_the_prompt_is_fresh_input():
    assert ca.cache_guard(2, {"input": 90000, "cache_read": 1000, "write_5m": 0, "write_1h": 0}, 0) is None        # too early to judge
    why = ca.cache_guard(3, {"input": 40000, "cache_read": 20000, "write_5m": 0, "write_1h": 0}, 0)
    assert "33%" in why and "60%" in why
    assert ca.cache_guard(5, {"input": 100, "cache_read": 30000, "write_5m": 2000, "write_1h": 0}, 28000) is None
    assert ca.cache_guard(5, {"input": 100, "cache_read": 0, "write_5m": 0, "write_1h": 0}, 0) is None            # a tiny turn with nothing fresh


# --- paid output saved step by step (P0d audit F1-F11, OR-33) ------------------------------------------------------------------
def multi(*chunks, **kw):
    return resp(content=[NS(type="text", text=c) for c in chunks], **kw)


def start_rows(a):
    return [x for x in a.ledger.rows() if x["ev"] == "start"]


def test_f1_every_call_streams_its_text_to_a_file_before_any_bookkeeping(monkeypatch):
    a = api(multi("The verdict ", "is: ", "fine."))
    real = a.ledger.append

    def failing(row):                                    # the answer is on disk even when the ledger line after it fails
        if row["ev"] == "done":
            raise OSError("disk")
        real(row)
    monkeypatch.setattr(a.ledger, "append", failing)
    with pytest.raises(OSError):
        a.complete(req())
    start = start_rows(a)[0]
    assert Path(start["stream"]) == ca.ledger_dir() / "stream" / f"{start['uid']}.txt"
    assert answer_part(start["stream"]) == "The verdict is: fine."


def test_f1_the_stream_file_stays_after_a_good_call():
    a = api(multi("alpha", "beta"))
    r = a.complete(req())
    assert r.text == "alphabeta" and ledger_streams(a) == ["alphabeta"]


def test_f2_an_error_after_text_is_not_retried_not_voided_and_booked_at_the_reservation():
    a = api(Midway(529, ["half an ", "answer"]), resp("never asked"))
    with pytest.raises(ca.StreamBroken) as ei:
        a.complete(req())
    assert len(a._client.calls) == 1                                           # no second, paid call
    assert ei.value.text == "half an answer" and answer_part(ei.value.path) == "half an answer"
    start, done = a.ledger.rows()
    assert [x["ev"] for x in a.ledger.rows()] == ["start", "done"] and done["usd"] == start["reserved"]
    assert "stream broke after 14 chars" in done["note"] and "reserved amount booked" in done["note"]
    assert a.run_for("T").spent(ca.SERVICE) == pytest.approx(start["reserved"])
    a.ledger.check_gap()


def test_f2_an_error_before_any_text_still_retries_and_voids_as_before():
    a = api(Midway(529, []), resp("late"))
    assert a.complete(req()).text == "late" and len(a._client.calls) == 2
    b = api(Err(400))
    with pytest.raises(Err):
        b.complete(req(user="a different request"))
    assert [x["ev"] for x in b.ledger.rows()][-2:] == ["start", "void"]


def test_f3_a_truncated_answer_carries_its_paid_text():
    a = api(multi("the cut ", "text", stop="max_tokens"))
    with pytest.raises(ca.OutputTruncated) as ei:
        a.complete(req())
    assert ei.value.text == "the cut text" and ei.value.result.text == "the cut text" and ei.value.result.usd > 0


def test_f3_batch_truncation_keeps_the_text_too():
    a = api()
    reqs = [ca.Request(id=f"q{i}", user=f"t{i}", task_class="qa-judgement", job="T") for i in range(ca.BATCH_MIN)]
    cut = NS(custom_id="q0", result=NS(type="succeeded", message=resp("cut batch text", model="claude-sonnet-5-5", stop="max_tokens")))
    a._client.messages.batch_results = [cut] + [NS(custom_id=f"q{i}", result=NS(type="succeeded", message=resp("x", model="claude-sonnet-5-5")))
                                                for i in range(1, ca.BATCH_MIN)]
    assert a.run_job(reqs)["q0"].text == "cut batch text"


def patched_main(monkeypatch, a):
    monkeypatch.setattr(ca, "ClaudeAPI", lambda: a)


def write_proof():
    """The stream-proof gate (OR-33) is open: the tests of `main run` that are not about the gate start from here."""
    ca.proof_path().parent.mkdir(parents=True, exist_ok=True)
    ca.proof_path().write_text(json.dumps({"uid": "test"}), encoding="utf-8")


def job_file(env, requests, **spec):
    write_proof()
    job = {"job": "T", "task_class": "critical-review", "max_tokens": 1000, "requests": requests, **spec}
    (env / "job.json").write_text(json.dumps(job), encoding="utf-8")
    return str(env / "job.json")


def test_f3_main_writes_the_truncated_text_and_says_so(env, monkeypatch, capsys):
    a, a2 = api(multi("kept ", "words", stop="max_tokens")), api(multi("{\"k\": 1", stop="max_tokens"))
    patched_main(monkeypatch, a)
    out = env / "out"
    assert ca.main(["run", job_file(env, [{"id": "a", "user": "hi"}]), "--out", str(out)]) == 2
    assert (out / "a.truncated.md").read_text(encoding="utf-8") == "kept words" and not (out / "a.md").exists()
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["a"]["truncated"] is True
    # with a schema the kept text goes to .truncated.json
    patched_main(monkeypatch, a2)
    ca.main(["run", job_file(env, [{"id": "b", "user": "hi2"}], schema={"type": "object"}), "--out", str(out)])
    assert (out / "b.truncated.json").read_text(encoding="utf-8") == '{"k": 1'


def test_f4_the_loop_checkpoints_after_every_turn_and_a_keyboard_interrupt_saves_too(tmp_path):
    seen = {}

    def interrupted(kw):
        seen["partial"] = json.loads((ca.ledger_dir() / "partial_T_K.json").read_text(encoding="utf-8"))   # what a SIGKILL here would leave
        raise KeyboardInterrupt
    a = api(warm_turns(1)[0], warm_turns(2)[1], interrupted)
    with pytest.raises(KeyboardInterrupt) as ei:
        a.complete(req("K", tools_root=str(tmp_path), max_turns=9))
    assert seen["partial"]["turns"] == 2 and "checkpoint after turn 2" in seen["partial"]["stopped_by"]
    assert [b["type"] for m in seen["partial"]["messages"] for b in m["blocks"]] == ["tool_use", "tool_result"] * 2
    final = json.loads((ca.ledger_dir() / "partial_T_K.json").read_text(encoding="utf-8"))
    assert "KeyboardInterrupt" in final["stopped_by"] and "partial transcript" in "".join(ei.value.__notes__)
    assert len(a.ledger.open_calls()) == 1                                        # the killed call stays open: nobody knows its price


def test_f4_sigterm_in_main_is_a_keyboard_interrupt_and_the_handler_is_restored(env, monkeypatch, tmp_path):
    import os
    import signal

    def killed(kw):
        os.kill(os.getpid(), signal.SIGTERM)
        return warm_turns(1)[0]
    a = api(warm_turns(1)[0], killed)
    patched_main(monkeypatch, a)
    before = signal.getsignal(signal.SIGTERM)
    job = job_file(env, [{"id": "K", "user": "hi"}], tools_root=str(tmp_path))
    with pytest.raises(KeyboardInterrupt):
        ca.main(["run", job, "--out", str(env / "o")])
    assert signal.getsignal(signal.SIGTERM) == before
    assert "KeyboardInterrupt" in json.loads((ca.ledger_dir() / "partial_T_K.json").read_text(encoding="utf-8"))["stopped_by"]


def sent_blocks(call):
    return call[1]["messages"][-1]["content"]


def test_f5_the_last_allowed_turn_is_a_wrap_up_turn(tmp_path):
    a = api(warm_turns(1)[0], warm_turns(2)[1], resp("the answer"))
    r = a.complete(req(tools_root=str(tmp_path), max_turns=3))
    c1, c2, c3 = a._client.calls
    assert all(b["type"] == "tool_result" for b in sent_blocks(c2))                      # turn 2 is an ordinary turn
    last = sent_blocks(c3)
    assert [b["type"] for b in last] == ["tool_result", "text"] and last[-1]["text"] == ca.WRAP_UP_TEXT
    assert last[-1]["cache_control"] == {"type": "ephemeral"}                            # the breakpoint lands on the wrap-up block
    assert c3[1]["tools"] == c1[1]["tools"]                                              # the tools list (the cache prefix) is unchanged
    assert r.text == "the answer" and r.turns == 3


def test_f5_too_little_room_makes_the_next_turn_a_wrap_up_turn(env, tmp_path):
    set_caps(env, jobs={"T": 0.8})                                       # stop 0.64: after turn 1 the room is under two worst-case turns
    a = api(warm_turns(1)[0], resp("wrapped up"))
    r = a.complete(req(tools_root=str(tmp_path), max_turns=24))
    assert r.text == "wrapped up" and r.turns == 2
    assert sent_blocks(a._client.calls[1])[-1]["text"] == ca.WRAP_UP_TEXT


def test_f5_a_wrap_up_turn_that_still_calls_tools_stops_with_the_partial(tmp_path):
    a = api(*warm_turns(3))
    with pytest.raises(ca.OutputTruncated, match="wrap-up turn still called tools"):
        a.complete(req("W", tools_root=str(tmp_path), max_turns=3))
    assert len(a._client.calls) == 3
    assert json.loads((ca.ledger_dir() / "partial_T_W.json").read_text(encoding="utf-8"))["turns"] == 3


def test_f5_wrap_up_reason_is_unit_testable_and_never_on_turn_1(env, tmp_path):
    a = api()
    q = req(tools_root=str(tmp_path), max_turns=5)
    r = ca.route("critical-review")
    params = ca.build_params(q, r)
    msgs = [*params["messages"], {"role": "assistant", "content": []}, {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "c"}]}]
    assert a.wrap_up_reason(q, r, params, msgs, 1) is None and a.wrap_up_reason(q, r, params, msgs, 2) is None
    assert "last of 5" in a.wrap_up_reason(q, r, params, msgs, 5)
    set_caps(env, jobs={"T": 0.1})
    assert "two worst-case turns" in a.wrap_up_reason(q, r, params, msgs, 2)


def test_f6_a_cache_cold_stop_keeps_the_turn_that_was_just_paid(env, tmp_path):
    prefix = 22746
    a = api(*[tool_turn("list_dir", {"path": "."}, f"b{i}", inp=1000 + 2000 * i, read=prefix) for i in range(10)])
    with pytest.raises(ca.CacheCold):
        a.complete(req("C", tools_root=str(tmp_path), max_turns=20))
    d = json.loads((ca.ledger_dir() / "partial_T_C.json").read_text(encoding="utf-8"))
    assert d["turns"] == 3 and [m["role"] for m in d["messages"]] == ["assistant", "user", "assistant", "user", "assistant"]


def test_f7_run_job_hands_over_each_result_and_a_failing_request_stops_the_rest_as_not_run(env):
    set_caps(env, jobs={"T": 0.5})
    a = api()

    def spends(kw):                                                       # another process spends the job's room during request r0
        a.run_for("T").reserve(ca.SERVICE, 0.38, "other")
        return resp("first")
    a._client.messages.script[:] = [spends, resp("never")]
    seen = []
    out = a.run_job([req(f"r{i}", user=f"u{i}", max_tokens=100) for i in range(3)], on_result=lambda q, res: seen.append((q.id, res)))
    assert [i for i, _ in seen] == ["r0", "r1", "r2"] and list(out) == ["r0", "r1", "r2"]
    assert out["r0"].text == "first" and isinstance(out["r1"], CapReached)
    assert isinstance(out["r2"], ca.LLMError) and str(out["r2"]).startswith("not_run: job stopped after r1")
    seen.clear()
    a.run_job([req("r0", user="u0", max_tokens=100)], on_result=lambda q, res: seen.append((q.id, res.cached)))   # cache hits are handed over too
    assert seen == [("r0", True)]


def test_f7_main_writes_each_file_at_once_and_reports_the_not_run_rest(env, monkeypatch):
    set_caps(env, jobs={"T": 0.5})
    a = api()
    a._client.messages.script[:] = [lambda kw: (a.run_for("T").reserve(ca.SERVICE, 0.38, "other"), resp("first one"))[1]]
    patched_main(monkeypatch, a)
    out = env / "out"
    assert ca.main(["run", job_file(env, [{"id": "a", "user": "x"}, {"id": "b", "user": "y"}, {"id": "c", "user": "z"}], max_tokens=100),
                    "--out", str(out)]) == 2
    assert (out / "a.md").read_text(encoding="utf-8") == "first one" and not (out / "b.md").exists()
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["a"]["ok"] and not s["b"]["ok"] and "not_run" in s["c"]["error"] and "_ledger_total_usd" in s


def test_f8_a_batch_rerun_after_a_crash_does_not_book_or_pay_an_item_twice():
    a = api(resp("direct rerun"))
    reqs = [ca.Request(id=f"q{i}", user=f"t{i}", task_class="qa-judgement", job="T") for i in range(ca.BATCH_MIN)]
    refused = NS(custom_id="q0", result=NS(type="succeeded", message=resp("", model="claude-sonnet-5-5", stop="refusal")))
    a._client.messages.batch_results = [refused] + [NS(custom_id=f"q{i}", result=NS(type="succeeded", message=resp("x", model="claude-sonnet-5-5")))
                                                    for i in range(1, ca.BATCH_MIN)]
    first = a.run_job(reqs)
    before = (a.ledger.total(), len(a.ledger.rows()), len(a._client.calls))
    again = ca.ClaudeAPI(a._client, sleep=lambda s: None, cache=ResponseCacheFresh(a))       # a crashed rerun: same ledger, cache lost
    out = again.run_job(reqs)
    assert (a.ledger.total(), len(a.ledger.rows()), len(a._client.calls)) == before          # no second done line, no second direct call
    assert all(isinstance(v, ca.LLMError) and "already collected" in str(v) for v in out.values()) and len(out) == ca.BATCH_MIN
    assert first["q0"].text == "direct rerun"
    same_cache = ca.ClaudeAPI(a._client, sleep=lambda s: None, cache=a.cache)                # with the cache the items are served from it
    got = same_cache.run_job(reqs)
    assert all(r.cached for r in got.values()) and got["q1"].text == "x" and a.ledger.total() == before[0]


def ResponseCacheFresh(a):
    return ca.ResponseCache(a.cache.dir.parent / "fresh_cache")


def test_f9_a_full_cache_miss_stops_the_loop_at_turn_3(tmp_path):
    miss = [tool_turn("list_dir", {"path": "."}, f"m{i}", inp=100, read=0, write=20000 + 2000 * i) for i in range(10)]
    a = api(*miss)
    with pytest.raises(ca.CacheCold, match=r"turn 3.*only 0% of the previous turn's prompt was read from cache"):
        a.complete(req(tools_root=str(tmp_path), max_turns=20))
    assert len(a._client.calls) == 3
    assert ca.cache_guard(4, {"input": 100, "cache_read": 9000, "write_5m": 10000, "write_1h": 0}, 8000, 19000) is not None  # 47 % of 19k
    assert ca.cache_guard(4, {"input": 100, "cache_read": 11000, "write_5m": 9000, "write_1h": 0}, 8000, 19000) is None


def test_f9_one_big_tool_result_is_not_taken_for_a_miss():
    # the whole previous prompt was read; this turn only added a large (capped) tool result, so most of THIS prompt is a write
    assert ca.cache_guard(3, {"input": 100, "cache_read": 15000, "write_5m": 20000, "write_1h": 0}, 9000, 15000) is None


def test_f10_the_last_turn_is_priced_at_max_tokens_and_the_estimate_says_so(env, tmp_path):
    m, kw = "claude-opus-5-5", dict(first_tokens=30000, turns=6, new_per_turn=2000, out_per_turn=600)
    assert ca.loop_usd(m, **kw, final_out=16000) - ca.loop_usd(m, **kw) == pytest.approx((16000 - 600) * 20 / 1e6)
    set_caps(env, jobs={"T": 5.0})
    small = ca.estimate([req(tools_root=str(tmp_path), max_turns=6, max_tokens=1000)])["requests"][0]["loop"]
    big = ca.estimate([req(tools_root=str(tmp_path), max_turns=6, max_tokens=30000)])["requests"][0]["loop"]
    assert big["usd_if_cached"] - small["usd_if_cached"] == pytest.approx((30000 - 1000) * 20 / 1e6, abs=1e-3)
    assert "max_tokens" in big["warning"] and str(ca.MAX_TOOL_CHARS_PER_TURN) in big["warning"]


def test_f10_tool_results_of_one_turn_are_capped_together(tmp_path):
    (tmp_path / "big.txt").write_text("\n".join("x" * 70 for _ in range(400)), encoding="utf-8")     # ~28k characters a read
    reads = [NS(type="tool_use", name="read_file", input={"path": "big.txt", "start": 1, "end": 400}, id=f"p{i}") for i in range(3)]
    a = api(resp(content=reads, stop="tool_use"), resp("done"))
    a.complete(req(tools_root=str(tmp_path)))
    got = [b["content"] for b in sent_blocks(a._client.calls[1])]
    assert got[0].startswith("1: xxx") and got[1].startswith("1: xxx") and got[2] == "error: per-turn tool output limit reached; ask for less at once"
    assert sum(len(x) for x in got[:2]) <= ca.MAX_TOOL_CHARS_PER_TURN


def test_f11_the_sdk_does_not_retry_on_its_own():
    a = api(resp("one"))
    opts = []
    a._client.with_options = lambda **o: (opts.append(o), a._client)[1]
    a.complete(req())
    assert opts == [{"max_retries": 0}]


# --- line redaction in the stream file, the 1h TTL option, the stream-proof gate (OR-33) ----------------------------------------
KEY = "sk-ant-api03-abcdefghijklmnop"


def test_a_key_shaped_string_split_across_deltas_never_reaches_the_stream_file():
    a = api(multi("the key is sk-ant-api0", "3-abcdefghijklmnop and more\nsecond line"))
    r = a.complete(req())
    f = Path(start_rows(a)[0]["stream"]).read_text(encoding="utf-8")
    assert "sk-ant" not in f and "[REDACTED-SECRET-LIKE]" in f and f.endswith("second line")
    assert KEY in r.text                                              # the answer in memory is untouched (n and text are unredacted)


def test_complete_lines_are_on_disk_before_close_so_a_kill_loses_only_the_unfinished_line():
    sink = ca.StreamSink(ca.ledger_dir() / "stream" / "x.txt")
    sink.write("line one\nline two\nunfin")
    assert sink.path.read_text(encoding="utf-8") == "[answer]\nline one\nline two\n" and sink.n == 23
    sink.write("ished " + KEY)
    assert sink.path.read_text(encoding="utf-8") == "[answer]\nline one\nline two\n"      # the tail waits
    sink.close()
    assert sink.path.read_text(encoding="utf-8").endswith("unfinished [REDACTED-SECRET-LIKE]") and KEY in sink.text


def test_the_truncated_file_is_redacted_too(env, monkeypatch):
    patched_main(monkeypatch, api(multi("cut " + KEY, stop="max_tokens")))
    out = env / "out"
    ca.main(["run", job_file(env, [{"id": "a", "user": "hi"}]), "--out", str(out)])
    assert "sk-ant" not in (out / "a.truncated.md").read_text(encoding="utf-8")


def test_a_one_hour_tool_loop_needs_a_measured_turn_gap_over_five_minutes(env, tmp_path):
    job = {"job": "T", "task_class": "critical-review", "tools_root": str(tmp_path), "cache_ttl": "1h", "requests": [{"id": "a", "user": "hi"}]}
    f = env / "job.json"
    f.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ConfigError, match="measured_turn_gap_s"):
        ca.load_job(f)
    f.write_text(json.dumps({**job, "measured_turn_gap_s": 300}), encoding="utf-8")
    with pytest.raises(ConfigError):
        ca.load_job(f)
    f.write_text(json.dumps({**job, "measured_turn_gap_s": 420}), encoding="utf-8")
    assert ca.load_job(f)[0].cache_ttl == "1h"
    f.write_text(json.dumps({**job, "cache_ttl": "5m"}), encoding="utf-8")
    assert ca.load_job(f)[0].cache_ttl == "5m"


def test_the_one_hour_loop_figure_is_never_below_the_five_minute_one(env, tmp_path):
    set_caps(env, jobs={"T": 50.0})
    five = ca.estimate([req(tools_root=str(tmp_path), max_turns=10, cache_ttl="5m")])["requests"][0]["loop"]
    hour = ca.estimate([req(tools_root=str(tmp_path), max_turns=10, cache_ttl="1h")])["requests"][0]["loop"]
    for k in ("usd_if_cached", "usd_if_uncached", "usd_if_miss"):
        assert hour[k] >= five[k], k
    assert hour["usd_if_cached"] > five["usd_if_cached"] and hour["usd_if_miss"] > five["usd_if_miss"]


def tiny_job(env, **kw):
    job = {"job": "T", "task_class": "simple-question", "max_tokens": 100, "requests": [{"id": "p", "user": "say ok"}], **kw}
    (env / "tiny.json").write_text(json.dumps(job), encoding="utf-8")
    return str(env / "tiny.json")


def test_run_refuses_a_normal_job_while_the_stream_proof_is_missing(env, monkeypatch, capsys):
    patched_main(monkeypatch, api())
    normal = env / "job.json"
    normal.write_text(json.dumps({"job": "T", "task_class": "critical-review", "max_tokens": 1000, "requests": [{"id": "a", "user": "hi"}]}),
                      encoding="utf-8")
    assert ca.main(["run", str(normal), "--out", str(env / "o")]) == 4 and "stream-proof" in capsys.readouterr().out
    for bad in ({"max_tokens": 1000}, {"requests": [{"id": "a", "user": "x"}, {"id": "b", "user": "y"}]}):
        assert ca.main(["run", tiny_job(env, **bad), "--out", str(env / "o")]) == 4
    assert ca.main(["run", tiny_job(env, tools_root=str(env)), "--out", str(env / "o")]) == 4
    assert patched_main and not ca.proof_path().exists()


def test_a_tiny_proof_job_passes_the_gate_and_the_proof_is_written_once(env, monkeypatch, capsys):
    a = api(resp("ok", model="claude-haiku-5-5", inp=100, out=5))
    patched_main(monkeypatch, a)
    assert ca.main(["status"]) == 0 and '"stream_proof": false' in capsys.readouterr().out
    assert ca.main(["run", tiny_job(env), "--out", str(env / "o")]) == 0
    assert "this is the stream-proof call" in capsys.readouterr().out
    proof = json.loads(ca.proof_path().read_text(encoding="utf-8"))
    assert proof["chars"] == 2 and proof["model"] == "claude-haiku-5-5" and proof["request_id"] == "req_1" and proof["uid"] and proof["at"]
    ca.main(["status"])
    assert '"stream_proof": true' in capsys.readouterr().out
    ca.proof_path().write_text(json.dumps({"uid": "first"}), encoding="utf-8")
    a.complete(req(task_class="simple-question", user="again"))
    assert json.loads(ca.proof_path().read_text(encoding="utf-8")) == {"uid": "first"}          # never rewritten


def test_a_stream_file_that_does_not_equal_the_answer_leaves_no_proof(monkeypatch):
    a = api(multi("the whole answer"))
    monkeypatch.setattr(ca.StreamSink, "write", lambda self, text: (setattr(self, "n", self.n + len(text)), self.parts.append(text)))
    a.complete(req())                                                  # nothing reached the file: no proof
    assert not ca.proof_path().exists()


def test_a_stream_file_that_holds_something_else_leaves_no_proof(monkeypatch):
    b = api(multi("short answer"))
    monkeypatch.setattr(ca, "redact", lambda t: ("different", 0))     # the file would hold something else than redact(answer)
    monkeypatch.setattr(ca.StreamSink, "close", lambda self: (self._out("tampered"), None)[1])
    b.complete(req(user="second"))
    assert not ca.proof_path().exists()


# --- thinking is streamed and saved, the max_tokens floor per effort, max needs a reason (F12-F16, the $3.45 thinking-only loss) -----
def thought(summary, text=None, **kw):
    blocks = [NS(type="thinking", thinking=summary)] + ([NS(type="text", text=text)] if text else [])
    return resp(content=blocks, **kw)


def test_f12_every_request_asks_for_adaptive_summarized_thinking_and_never_a_budget():
    for c in ("critical-review", "qa-judgement", "simple-question"):
        p = ca.build_params(req(task_class=c), ca.route(c))
        assert p["thinking"] == {"type": "adaptive", "display": "summarized"} and "budget_tokens" not in json.dumps(p)
    assert "thinking" in ca.build_params(req(tools_root="."), ca.route("critical-review"))


def test_f13_a_thinking_only_max_tokens_stop_leaves_the_file_and_names_the_cause():
    a = api(thought("I weighed the plan.\nNo answer yet.", stop="max_tokens", inp=1000, out=16000))
    with pytest.raises(ca.OutputTruncated, match=r"thinking used the whole max_tokens 16000 \(output tokens 16000\), no answer text; raise max_tokens") as ei:
        a.complete(req())
    f = Path(start_rows(a)[0]["stream"]).read_text(encoding="utf-8")
    assert f.startswith("--- r1#") and "effort=high max_tokens=16000 ---\n[thinking]\nI weighed the plan.\nNo answer yet." in f and "[answer]" not in f
    assert ei.value.thinking == "I weighed the plan.\nNo answer yet." and ei.value.text == ""


def test_f13_a_call_with_no_text_at_all_still_leaves_a_stream_file():
    a = api(thought("", stop="max_tokens"))
    with pytest.raises(ca.OutputTruncated):
        a.complete(req())
    assert Path(start_rows(a)[0]["stream"]).read_text(encoding="utf-8").startswith("--- ")


def test_f13_main_writes_the_thinking_file_redacted(env, monkeypatch):
    patched_main(monkeypatch, api(thought("plan with " + KEY, stop="max_tokens")))
    out = env / "out"
    ca.main(["run", job_file(env, [{"id": "a", "user": "hi"}]), "--out", str(out)])
    t = (out / "a.thinking.md").read_text(encoding="utf-8")
    assert "plan with" in t and "sk-ant" not in t and not (out / "a.truncated.md").exists()


def test_f13_an_error_after_thinking_only_output_is_not_retried_and_is_booked():
    a = api(Midway(529, [("thinking", "pondering")]), resp("never"))
    with pytest.raises(ca.StreamBroken):
        a.complete(req())
    assert len(a._client.calls) == 1
    start, done = a.ledger.rows()
    assert done["usd"] == start["reserved"] and "stream broke after 9 chars" in done["note"]


def test_f13_a_partial_transcript_keeps_the_thinking_blocks(tmp_path):
    turn = resp(content=[NS(type="thinking", thinking="I will list the folder."), NS(type="tool_use", name="list_dir", input={"path": "."}, id="t1")],
                stop="tool_use", inp=100, read=20000, write=2000)
    a = api(turn, turn)
    with pytest.raises(ca.OutputTruncated):
        a.complete(req("TH", tools_root=str(tmp_path), max_turns=2))
    d = json.loads((ca.ledger_dir() / "partial_T_TH.json").read_text(encoding="utf-8"))
    assert {"type": "thinking", "thinking": "I will list the folder."} in d["messages"][0]["blocks"]


def test_f13_the_proof_is_written_when_the_answer_matches_even_with_thinking_before_it(env, monkeypatch):
    a = api(thought("a long think", "ok", model="claude-haiku-5-5", inp=100, out=5))
    patched_main(monkeypatch, a)
    assert ca.main(["run", tiny_job(env), "--out", str(env / "o")]) == 0
    assert json.loads(ca.proof_path().read_text(encoding="utf-8"))["chars"] == 2


def test_f15_effort_max_at_40000_tokens_is_refused_before_any_call_or_reservation():
    q = req(task_class="whole-project-plan", model="fable", effort="max", max_tokens=40000, max_effort_reason="audit")
    a = api()
    with pytest.raises(ConfigError, match="max_tokens >= 64000"):
        a.complete(q)
    assert a._client.calls == [] and a.ledger.rows() == [] and a.run_for("T").spent(ca.SERVICE) == 0
    assert a.complete(ca.Request(**{**q.__dict__, "max_tokens": 64000})).text == "ok"
    assert a.complete(req(i="x", task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=32000)).text == "ok"
    with pytest.raises(ConfigError, match="max_tokens >= 32000"):
        a.complete(req(i="y", task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=31999))


def test_f15_estimate_reports_the_floor_and_run_refuses_with_3(env, capsys):
    q = req(task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=16000)
    assert ca.estimate([q])["requests"][0]["max_tokens_floor_ok"] is False
    assert ca.estimate([req()])["requests"][0]["max_tokens_floor_ok"] is True
    write_proof()
    job = {"job": "T", "task_class": "whole-project-plan", "model": "fable", "effort": "xhigh", "max_tokens": 16000,
           "requests": [{"id": "a", "user": "hi"}, {"id": "b", "user": "ho"}]}
    (env / "job.json").write_text(json.dumps(job), encoding="utf-8")
    assert ca.main(["run", str(env / "job.json")]) == 3 and "floor" in capsys.readouterr().out


def test_f16_max_effort_on_a_single_shot_needs_a_stated_reason():
    kw = dict(task_class="whole-project-plan", model="fable", effort="max", max_tokens=64000)
    a = api()
    for bad in ("", "   "):
        with pytest.raises(ConfigError, match="max_effort_reason"):
            a.complete(req(max_effort_reason=bad, **kw))
    assert a._client.calls == [] and a.ledger.rows() == []
    assert a.complete(req(max_effort_reason="one-off whole-project audit", **kw)).text == "ok"
    assert a.complete(req(i="x", task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=32000)).text == "ok"   # xhigh: no reason
    assert ca.estimate([req(**kw)])["requests"][0]["max_effort_reason_ok"] is False
    assert ca.estimate([req(max_effort_reason="why", **kw)])["requests"][0]["max_effort_reason_ok"] is True


def test_f16_the_reason_comes_from_the_job_file_and_run_refuses_without_it(env, capsys):
    write_proof()
    job = {"job": "T", "task_class": "whole-project-plan", "model": "fable", "effort": "max", "max_tokens": 64000, "requests": [{"id": "a", "user": "hi"}]}
    (env / "job.json").write_text(json.dumps(job), encoding="utf-8")
    assert ca.main(["run", str(env / "job.json")]) == 3 and "max_effort_reason" in capsys.readouterr().out
    (env / "job.json").write_text(json.dumps({**job, "max_effort_reason": "one-off"}), encoding="utf-8")
    assert ca.load_job(env / "job.json")[0].max_effort_reason == "one-off"


# --- review of PR #64 ----------------------------------------------------------------------------------------------------------
def test_a_key_in_a_thinking_block_never_reaches_the_partial_file(tmp_path):
    turn = resp(content=[NS(type="thinking", thinking="my key is " + KEY), NS(type="tool_use", name="list_dir", input={"path": "."}, id="t1")],
                stop="tool_use", inp=100, read=20000, write=2000)
    a = api(turn, turn)
    with pytest.raises(ca.OutputTruncated):
        a.complete(req("TK", tools_root=str(tmp_path), max_turns=2))
    raw = (ca.ledger_dir() / "partial_T_TK.json").read_text(encoding="utf-8")
    assert "sk-ant" not in raw and "[REDACTED-SECRET-LIKE]" in raw


def test_the_batch_path_checks_the_floor_before_creating_the_batch_or_reserving():
    a = api()
    reqs = [ca.Request(id=f"q{i}", user=f"t{i}", task_class="whole-project-plan", model="fable", effort="max", max_tokens=40000, job="T",
                       max_effort_reason="x") for i in range(ca.BATCH_MIN)]
    with pytest.raises(ConfigError, match="max_tokens >= 64000"):
        a.run_job(reqs)
    assert a._client.messages.batch_requests == [] and a.ledger.rows() == [] and a.run_for("T").spent(ca.SERVICE) == 0


def test_the_unfinished_last_piece_is_redacted_in_the_file_on_close():
    sink = ca.StreamSink(ca.ledger_dir() / "stream" / "tail.txt", "--- h ---")
    sink.write("first line\nlast piece without newline " + KEY)
    sink.close()
    t = sink.path.read_text(encoding="utf-8")
    assert "sk-ant" not in t and t.endswith("last piece without newline [REDACTED-SECRET-LIKE]") and KEY in sink.text


def test_the_fable_400_fallback_route_is_floor_checked_before_its_attempt_is_reserved():
    a = api(Err(400), resp("by opus"))
    q = req(task_class="whole-project-plan", model="fable", effort="xhigh", max_tokens=32000, fallback_to=("opus", "max"), max_effort_reason="x")
    with pytest.raises(ConfigError, match="max_tokens >= 64000"):          # fallback at max needs 64000 (and a reason)
        a.complete(q)
    assert len(a._client.calls) == 1 and [x["ev"] for x in a.ledger.rows()] == ["start", "void"]
    assert a.run_for("T").spent(ca.SERVICE) == 0


def test_a_line_may_not_be_lower_than_what_it_already_spent():
    c = {"jobs": {"J1b": 5.02, "plan_v2": 28.0, "J6": 0.0}}
    assert ca.lines_below_spent(c, {"J1b": 5.016946, "plan_v2": 3.0}) == {}
    assert ca.lines_below_spent(c, {"J1b": 5.5}) == {"J1b": 0.48}
    assert ca.lines_below_spent(c, {"J9": 0.01}) == {"J9": 0.01}   # a job without a line has spent against nothing

