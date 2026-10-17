import base64
import json

import pytest

from explainer_engine.core.ledger import CapReached, Run
from explainer_engine.imagegen.gemini import GeminiClient, GeminiError

PNG = b"\x89PNG fake"


def fake(state="JOB_STATE_SUCCEEDED", bad=()):
    calls = []

    def post(method, url, body=None):
        calls.append((method, url))
        if method == "POST":
            keys = [r["metadata"]["key"] for r in body["batch"]["input_config"]["requests"]["requests"]]
            fake.keys = keys
            return {"name": "batches/abc"}
        rows = []
        for k in fake.keys:
            if k in bad:
                rows.append({"metadata": {"key": k}, "error": {"message": "blocked"}})
            else:
                rows.append({"metadata": {"key": k}, "response": {"candidates": [{"content": {"parts": [
                    {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(PNG).decode()}}]}}]}})
        return {"name": "batches/abc", "state": state, "dest": {"inlinedResponses": rows}}
    return post, calls


def client(tmp_path, post):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0}) if not (tmp_path / "run.json").exists() else Run.open(tmp_path / "run.json")
    c = GeminiClient(tmp_path / "g", cap_usd=6.0, run=run)
    c.batch_post = post
    return c, run


def test_batch_reserves_half_price_and_writes_pictures(tmp_path):
    post, calls = fake()
    c, run = client(tmp_path, post)
    name = c.submit_batch([{"name": "a", "prompt": "p", "refs": [b"x"]}, {"name": "b", "prompt": "q"}],
                          model="gemini-nano-banana-2.1", size="2K")
    assert run.spent("gemini_usd") == pytest.approx(2 * 0.0252 + 0.0011, abs=1e-4)
    res = c.collect_batch(name)
    assert res["done"] and (tmp_path / "g" / "a.png").read_bytes() == PNG and (tmp_path / "g" / "b.png").exists()


def test_failed_item_is_refunded_once(tmp_path):
    post, _ = fake(bad=("b",))
    c, run = client(tmp_path, post)
    name = c.submit_batch([{"name": "a", "prompt": "p"}, {"name": "b", "prompt": "q"}], model="gemini-3.1-flash-lite-image", size="1K")
    before = run.spent("gemini_usd")
    r1 = c.collect_batch(name)
    assert r1["items"]["b"] == "blocked" and run.spent("gemini_usd") == pytest.approx(before - 0.0168, abs=1e-4)
    c.collect_batch(name)  # settled: no second refund
    assert run.spent("gemini_usd") == pytest.approx(before - 0.0168, abs=1e-4)


def test_batch_refuses_past_the_80_percent_stop(tmp_path):
    post, _ = fake()
    c, run = client(tmp_path, post)
    run.reserve("gemini_usd", 4.79)
    with pytest.raises(CapReached):
        c.submit_batch([{"name": "a", "prompt": "p"}] * 2, model="gemini-nano-banana-2.1", size="2K")
