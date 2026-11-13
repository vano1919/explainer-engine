"""The API backup of the Gemini chat reads the message's picture blocks word for word and prices them before sending."""

import base64
import json

import pytest

from explainer_engine.gemini_task import api_backup as AB
from explainer_engine.imagegen import gemini as G

MSG = """head
-----BEGIN PICTURES-----
PICTURE 1 of 2 | id t0_A | save as t0_A.jpg
REFERENCES, in this order: 1 = style.png (style)
PROMPT: First prompt, exactly as written.

PICTURE 2 of 2 | id t0_B | save as t0_B.jpg
REFERENCES, in this order: 1 = style.png (style), 2 = hero.png (hero)
PROMPT: Second prompt: with a colon.
-----END PICTURES-----
tail PROMPT: not a picture"""


def test_blocks_keep_the_prompt_word_for_word_and_the_reference_order():
    b = AB.picture_blocks(MSG)
    assert [x["id"] for x in b] == ["t0_A", "t0_B"]
    assert b[1]["prompt"] == "Second prompt: with a colon."
    assert b[1]["refs"] == ["style.png", "hero.png"]
    with pytest.raises(G.GeminiError):
        AB.picture_blocks("-----BEGIN PICTURES-----\nPICTURE 1 of 1 | id x\n-----END PICTURES-----")


def test_submit_prices_sends_the_same_text_and_collect_writes_each_picture(tmp_path, monkeypatch):
    (tmp_path / "refs").mkdir()
    (tmp_path / "refs" / "style.png").write_bytes(b"\x89PNGstyle")
    (tmp_path / "refs" / "hero.png").write_bytes(b"\x89PNGhero")
    msg = tmp_path / "m.md"
    msg.write_text(MSG, encoding="utf-8")
    its = AB.items(msg, [tmp_path / "refs"])
    assert AB.estimate(its) == round(2 * G.BATCH_PRICES[AB.DEFAULT_MODEL]["2K"] + 3 * G.REFERENCE_USD, 4)
    sent = {}

    def fake(method, url, body=None):
        if method == "POST":
            sent["body"] = body
            return {"name": "batches/b1"}
        pic = base64.b64encode(b"\xff\xd8jpg").decode()
        rows = [{"metadata": {"key": k}, "response": {"candidates": [{"content": {"parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": pic}}]}}]}} for k in ("t0_A", "t0_B")]
        return {"done": True, "response": {"inlinedResponses": {"inlinedResponses": rows}}}

    c = G.GeminiClient(tmp_path / "out", cap_usd=1.0, cache_dir=tmp_path / "cache")
    c.batch_post = fake
    c.submit_batch([{k: i[k] for k in ("name", "prompt", "refs")} for i in its], model=AB.DEFAULT_MODEL, size="2K")
    reqs = sent["body"]["batch"]["input_config"]["requests"]["requests"]
    assert [r["request"]["contents"][0]["parts"][0]["text"] for r in reqs] == [i["prompt"] for i in its]
    assert len(reqs[1]["request"]["contents"][0]["parts"]) == 3
    out = c.collect_batch("batches/b1")
    assert all((tmp_path / "out" / f"{k}.png").read_bytes() == b"\xff\xd8jpg" for k in ("t0_A", "t0_B"))
    assert out["done"] and set(out["items"]) == {"t0_A", "t0_B"}


def test_the_cap_refuses_before_anything_is_sent(tmp_path):
    c = G.GeminiClient(tmp_path, cap_usd=0.01, cache_dir=tmp_path / "c")
    c.batch_post = lambda *a, **k: pytest.fail("sent past the cap")
    with pytest.raises(G.GeminiError, match="80 %"):
        c.submit_batch([{"name": "x", "prompt": "p", "refs": []}], model=AB.DEFAULT_MODEL, size="2K")
