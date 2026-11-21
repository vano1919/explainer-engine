"""The DeepSeek worker (explainer_engine/llm/deepseek_api.py, skill deepseek-worker): money, stream saving, edit safety, the fix loop."""
import datetime
import json
import urllib.error

import pytest

from explainer_engine.llm import deepseek_api as ds

UTC = datetime.timezone.utc
OFF_PEAK = datetime.datetime(2026, 11, 21, 12, 0, tzinfo=UTC)      # a Saturday
PEAK = datetime.datetime(2026, 11, 20, 7, 0, tzinfo=UTC)           # a Friday, 07:00 UTC


def sse(text, usage=None, model="deepseek-flash", finish="stop", pieces=2):
    step = max(1, len(text) // pieces)
    lines = [": keep-alive\n", "\n"]
    for i in range(0, len(text), step):
        lines.append("data: " + json.dumps({"model": model, "choices": [{"delta": {"content": text[i:i + step]}}]}) + "\n")
    lines.append("data: " + json.dumps({"model": model, "choices": [{"delta": {}, "finish_reason": finish}]}) + "\n")
    if usage is not None:
        lines.append("data: " + json.dumps({"model": model, "choices": [], "usage": usage}) + "\n")
    return lines + ["data: [DONE]\n"]


def block(path, search, replace):
    return f"### FILE: {path}\n{ds.M_SEARCH}\n{search}{ds.M_SPLIT}\n{replace}{ds.M_REPLACE}\n"


def worker(tmp_path, answers, *, cap=5.0, max_usd=1.0, now=OFF_PEAK, usage=None):
    sent = []
    usage = usage or {"prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 1000, "completion_tokens": 500}

    def transport(url, headers, body):
        sent.append(body)
        a = answers[len(sent) - 1]
        if isinstance(a, Exception):
            raise a
        return iter(a if isinstance(a, list) else sse(a, usage))

    w = ds.Worker(job="t", max_usd=max_usd, cfg=ds.config(), cap={"max_usd": cap, "period": "week"}, ledger=tmp_path / "ledger.jsonl",
                  transport=transport, now=lambda: now, sleep=lambda s: None, key="k")
    return w, sent


def test_config_prices_and_peak_hours():
    cfg = ds.config()
    assert cfg["models"]["flash"]["id"] == "deepseek-flash" and cfg["models"]["pro"]["id"] == "deepseek-v4-pro"
    assert ds.is_peak(PEAK, cfg) and not ds.is_peak(OFF_PEAK, cfg)
    assert not ds.is_peak(datetime.datetime(2026, 11, 20, 4, 30, tzinfo=UTC), cfg)       # between the two windows
    u = {"prompt_cache_hit_tokens": 1_000_000, "prompt_cache_miss_tokens": 1_000_000, "completion_tokens": 1_000_000}
    assert ds.usd_of("flash", u, PEAK, cfg) == pytest.approx(0.006 + 0.30 + 1.20)
    assert ds.usd_of("flash", u, OFF_PEAK, cfg) == pytest.approx((0.006 + 0.30 + 1.20) / 2)
    assert ds.usd_of("pro", u, PEAK, cfg) == pytest.approx(0.044 + 1.32 + 3.96)


def test_no_cap_line_means_no_call(tmp_path, monkeypatch):
    monkeypatch.setattr(ds.spend_caps, "load", lambda: {})
    w, sent = worker(tmp_path, ["x"])
    w.cap = None
    with pytest.raises(ds.NotApproved):
        w.complete([{"role": "user", "content": "hi"}])
    assert not sent


def test_stream_is_saved_as_it_arrives_and_logged(tmp_path):
    w, sent = worker(tmp_path, ["hello world"])
    sink = tmp_path / "o" / "a.md"
    assert w.complete([{"role": "user", "content": "hi"}], sink=sink) == "hello world"
    assert sink.read_text() == "hello world" and sent[0]["stream"] and sent[0]["thinking"] == {"type": "enabled"}
    (e,) = w.entries()
    assert e["usd"] == pytest.approx((1000 * 0.30 + 500 * 1.20) / 1e6 / 2) and not e["uncertain"]
    assert w.spent() == pytest.approx(e["usd"])


def test_broken_stream_keeps_the_partial_and_charges_the_estimate(tmp_path):
    w, _ = worker(tmp_path, [sse("half an ans", usage=None)[:-2]])      # no finish, no usage line
    sink = tmp_path / "a.md"
    with pytest.raises(ds.StreamBroken):
        w.complete([{"role": "user", "content": "hi"}], sink=sink)
    assert sink.read_text() == "half an ans"
    (e,) = w.entries()
    assert e["uncertain"] and e["usd"] > 0


def test_cap_job_limit_and_secret_refusals(tmp_path):
    w, sent = worker(tmp_path, ["x"], cap=0.01)
    with pytest.raises(ds.CapReached):
        w.complete([{"role": "user", "content": "hi"}])
    w, sent2 = worker(tmp_path, ["x"], max_usd=0.001)
    with pytest.raises(ds.CapReached):
        w.complete([{"role": "user", "content": "hi"}])
    w, sent3 = worker(tmp_path, ["x"])
    with pytest.raises(ds.EngineError):
        w.complete([{"role": "user", "content": "key hf_" + "a" * 30}])
    assert not sent and not sent2 and not sent3


def test_retry_on_429_then_answer(tmp_path):
    err = urllib.error.HTTPError("u", 429, "busy", {}, None)
    w, sent = worker(tmp_path, [err, "ok"])
    assert w.complete([{"role": "user", "content": "hi"}]) == "ok" and len(sent) == 2


def test_code_loop_fixes_after_a_red_test_and_last_round_is_pro(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("def f():\n    return 1\n")
    bad = block("pkg/m.py", "    return 1\n", "    return 3\n")
    good = block("pkg/m.py", "    return 1\n", "    return 2\n") + block("tests/test_m.py", "", "def test_f():\n    assert True\n")
    w, sent = worker(tmp_path, [bad, good])
    seen = []

    def runner(cmd, root, timeout):
        seen.append((root / "pkg" / "m.py").read_text())
        return ("return 2" in seen[-1]), "AssertionError: 3 != 2"

    res = ds.code(w, "make f return 2", ["pkg/m.py"], root=tmp_path, test="pytest", rounds=2, out=tmp_path / "out", test_runner=runner)
    assert res["status"] == "PASS" and res["rounds"] == 2 and res["models"] == ["flash", "pro"]
    assert res["files"] == ["pkg/m.py", "tests/test_m.py"] and res["tested"]
    assert (tmp_path / "pkg" / "m.py").read_text() == "def f():\n    return 2\n" and (tmp_path / "tests" / "test_m.py").exists()
    assert "AssertionError" in sent[1]["messages"][-1]["content"] and sent[1]["model"] == "deepseek-v4-pro"
    diff = (tmp_path / "out" / "patch.diff").read_text()
    assert "+    return 2" in diff and "/dev/null" in diff
    assert res["usd"] == pytest.approx(w.spent(), abs=1e-4) and len(w.entries()) == 2


def test_code_failure_leaves_the_tree_untouched(tmp_path):
    (tmp_path / "m.py").write_text("x = 1\n")
    ans = block("m.py", "x = 1\n", "x = 2\n") + block("new.py", "", "y = 1\n")
    w, _ = worker(tmp_path, [ans, ans])
    res = ds.code(w, "b", ["m.py"], root=tmp_path, test="t", rounds=2, out=tmp_path / "out", test_runner=lambda *a: (False, "red"))
    assert res["status"] == "FAIL" and res["rounds"] == 2 and res["last_failure"] == "red"
    assert (tmp_path / "m.py").read_text() == "x = 1\n" and not (tmp_path / "new.py").exists()


def test_edit_safety_rules(tmp_path):
    cfg = ds.config()
    (tmp_path / "a.py").write_text("a = 1\nb = 1\n" + "# keep\n" * 100)
    (tmp_path / "other.py").write_text("z = 1\n")

    def errs(edits, allowed=("a.py",)):
        return ds.plan_edits(edits, tmp_path, set(allowed), cfg)[1]

    assert errs([]) and "no edit block" in errs([])[0]
    assert "may not be edited" in errs([("config/spend_caps.json", "", "{}")])[0]              # money
    assert "may not be edited" in errs([(".claude/settings.json", "", "{}")])[0]               # hooks
    assert "may not be edited" in errs([("../x.py", "", "x")])[0]
    assert "was not sent" in errs([("other.py", "z = 1\n", "z = 2\n")])[0]                     # only the sent files
    assert "whole file" in errs([("a.py", "", "a = 2\n")])[0]                                  # no rewrite of an existing file
    assert "exactly once" in errs([("a.py", " = 1\n", " = 2\n")])[0]                           # ambiguous SEARCH
    assert "shrinks" in errs([("a.py", "b = 1\n" + "# keep\n" * 100, "b = 1\n")])[0]            # no stubbed module
    new, none = ds.plan_edits([("a.py", "a = 1\n", "a = 2\n"), ("a.py", "b = 1\n", "b = 2\n")], tmp_path, {"a.py"}, cfg)
    assert not none and new["a.py"].startswith("a = 2\nb = 2\n")


def test_review_returns_a_short_verdict(tmp_path):
    w, sent = worker(tmp_path, [json.dumps({"verdict": "FIX", "findings": [{"file": "a.py", "line": 3, "severity": "high",
                                                                             "problem": "p", "fix": "f"}] * 9})])
    res = ds.review(w, "brief", "+x = 1\n", out=tmp_path / "out")
    assert res["verdict"] == "FIX" and len(res["findings"]) == 5 and sent[0]["response_format"] == {"type": "json_object"}
    assert sent[0]["model"] == "deepseek-v4-pro"


def test_cli_dry_run_and_refusal_without_cap(tmp_path, capsys, monkeypatch):
    brief = tmp_path / "b.md"
    brief.write_text("do it")
    assert ds.main(["code", "--brief", str(brief), "--max-usd", "0.1", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["worst_usd_per_round"] > 0
    monkeypatch.setattr(ds.spend_caps, "load", lambda: {})
    monkeypatch.setenv("EXPLAINER_DEEPSEEK_LEDGER", str(tmp_path / "l.jsonl"))
    assert ds.main(["text", "--brief", str(brief), "--max-usd", "0.1", "--out", str(tmp_path / "o.md")]) == 2
    assert "NotApproved" in capsys.readouterr().out
