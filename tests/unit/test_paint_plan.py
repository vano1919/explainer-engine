"""Paint plans (audit 2026-10-19, PP-01..PP-07): the provider is chosen per batch, the creator's yes is bound to the batch's hash,
every painted prompt is linted, no paid request is sent twice. No network: the Gemini client gets a fake ``post``."""
import base64
import json

import pytest

from explainer_engine.core.ledger import LedgerConflict, Run
from explainer_engine.imagegen import gemini as G
from explainer_engine.imagegen import plan as P
from explainer_engine.production import paint
from explainer_engine.production import validate as V
from explainer_engine.production import script as S
from test_editorial_gate import valid_doc, valid_review
from test_production_script import compiled, mini

PNG = b"\x89PNG fake"
MODEL, SIZE = "gemini-nano-banana-2.1", "2K"


def answer(*_):
    return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png",
                                                                   "data": base64.b64encode(PNG).decode()}}]}}]}


@pytest.fixture
def episode(tmp_path, monkeypatch):
    from PIL import Image
    doc = compiled()
    doc["episode"]["gemini_exception"] = {"decision": "D-44", "cap_usd": 6.0}
    for name in ("camp", "valley", "duo"):
        Image.new("RGB", (16, 9)).save(tmp_path / f"{name}.png")
    doc["editorial"] = valid_doc()["editorial"]  # the editorial gate (EG) passes: sources and a hash-bound review
    for seg in doc["segments"]:
        for ln in seg["lines"]:
            ln["kind"] = "transition"
    doc["segments"][0]["lines"][0].update(kind="fact", claims=["C1"])
    script = tmp_path / "production_script.json"
    S.save(doc, script)
    (tmp_path / "editorial_review.json").write_text(json.dumps(valid_review(script)))
    calls = []

    def post(self, model, body):
        calls.append(model)
        return answer()
    monkeypatch.setattr(G.GeminiClient, "_http", post)
    monkeypatch.setenv("EXPLAINER_IMAGE_CACHE", str(tmp_path / "cache"))
    return tmp_path, script, calls


def make_plan(tmp, script, **kw):
    args = ["plan", str(script), "--out", str(tmp / "pics"), "--id", "B1", "--provider", "gemini", "--model", MODEL,
            "--size", SIZE, "--purpose", "test pictures"] + kw.get("extra", [])
    assert paint.main(args) == 0
    return tmp / "pics" / "plans" / "B1.json"


def run_args(tmp, script, plan):
    return ["run", str(plan), str(script), "--run", str(tmp / "run.json"), "--out", str(tmp / "pics"), "--refs", str(tmp),
            "--workers", "1"]


def test_options_price_the_batch_at_every_provider():
    rows = P.options([{"id": "a", "prompt": "p", "refs": ["r.png"]}])
    names = {r["provider"] for r in rows}
    assert names == {"gemini", "pod", "local"}
    batch = [r for r in rows if r["model"] == MODEL and r["size"] == SIZE and r["batch"]][0]
    assert batch["usd"] == pytest.approx(G.BATCH_PRICES[MODEL][SIZE] + G.REFERENCE_USD)


def test_plan_needs_a_provider_and_has_no_default(episode, capsys):
    tmp, script, _ = episode
    with pytest.raises(SystemExit):
        paint.main(["plan", str(script), "--out", str(tmp / "pics"), "--id", "B1"])


def test_nothing_is_painted_without_the_creators_yes(episode, capsys):
    tmp, script, calls = episode
    Run.open(tmp / "run.json", caps={"gemini_usd": 6.0})
    plan = make_plan(tmp, script)
    assert paint.main(run_args(tmp, script, plan)) == 2
    assert calls == [] and "no approval" in capsys.readouterr().out


def test_approved_plan_paints_and_records_the_prompt_hash(episode):
    tmp, script, calls = episode
    Run.open(tmp / "run.json", caps={"gemini_usd": 6.0})
    plan = make_plan(tmp, script)
    assert paint.main(["approve", str(plan), "--run", str(tmp / "run.json"), "--by", "creator", "--ref", "cmsg_x"]) == 0
    assert paint.main(run_args(tmp, script, plan)) == 0
    assert calls == [MODEL] and (tmp / "pics" / "cold_hands.png").read_bytes() == PNG
    rec = Run.open(tmp / "run.json").data["items"]["pictures"]["cold_hands"]
    assert rec["plan"] == "B1" and rec["hash"] == P.item_hash(json.loads(plan.read_text())["items"][0])
    assert paint.main(run_args(tmp, script, plan)) == 0 and calls == [MODEL]  # a re-run skips it


def test_an_edited_plan_loses_its_approval(episode, capsys):
    tmp, script, calls = episode
    Run.open(tmp / "run.json", caps={"gemini_usd": 6.0})
    plan = make_plan(tmp, script)
    paint.main(["approve", str(plan), "--run", str(tmp / "run.json"), "--by", "creator", "--ref", "cmsg_x"])
    data = json.loads(plan.read_text())
    data["size"] = "4K"  # dearer than what was approved
    plan.write_text(json.dumps(data))
    assert paint.main(run_args(tmp, script, plan)) == 2 and calls == []
    assert "PP-02" in capsys.readouterr().out


def test_gemini_for_episode_pictures_needs_a_recorded_exception():
    doc = mini()
    items = [{"id": "cold_hands", "prompt": "p", "refs": []}]
    plan = P.make("B1", "mini", items, provider="gemini", model=MODEL, size=SIZE, purpose="x")
    assert "PP-05" in {f["rule"] for f in P.check(plan) if f["severity"] == "FAIL"}
    doc["episode"]["gemini_exception"] = {"decision": "D-44", "cap_usd": 6.0}
    assert "PP-05" not in {f["rule"] for f in P.check(plan, compiled_of(doc))}
    assert "PP-05" not in {f["rule"] for f in P.check(P.make("B2", "mini", items, provider="gemini", model=MODEL, size=SIZE,
                                                            purpose="mascot", reusable=True))}


def test_too_many_references_for_the_provider():
    items = [{"id": "a", "prompt": "p", "refs": [f"r{i}.png" for i in range(5)]}]
    plan = P.make("B1", "mini", items, provider="pod", purpose="x")
    assert "PP-03" in {f["rule"] for f in P.check(plan)}


def test_reference_edit_prompts_are_linted_for_child_cues():
    doc = mini()
    doc["segments"][0]["shots"][1]["picture"] = {"id": "cold_hands", "engine": "pod_ref", "refs": ["valley"],
                                                 "subject": "tiny figures huddle in the rising wind at dusk"}
    found = V.check_script(compiled_of(doc))
    fails = [f for f in found if f["rule"] == "PV-11" and f["severity"] == "FAIL"]
    assert fails and "UR-24" in fails[0]["detail"]
    soft = [f for f in found if f["rule"] == "PV-11" and f["severity"] == "REVIEW" and f["where"] == "cold_hands"]
    assert soft and "reference edit" in soft[0]["detail"]


def compiled_of(doc):
    from explainer_engine.production import compile as C
    return C.compile_doc(doc)


# --- the Gemini client: no paid request twice ------------------------------------------------------------------------

def test_a_timed_out_paid_request_is_not_retried_and_keeps_its_reservation(tmp_path, monkeypatch):
    import urllib.request
    sent = []

    def urlopen(req, timeout):
        sent.append(req)
        raise TimeoutError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    c = G.GeminiClient(tmp_path / "g", key="k", cap_usd=6.0, run=run)
    with pytest.raises(G.ChargeUncertain):
        c.generate("a", "prompt", model=MODEL, size=SIZE)
    assert len(sent) == 1 and run.spent("gemini_usd") == pytest.approx(G.PRICES[MODEL][SIZE])


def test_the_judge_is_reserved_in_the_ledger(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    c = G.GeminiClient(tmp_path / "g", cap_usd=6.0, run=run,
                       post=lambda m, b: {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
    c.judge(PNG, "q")
    assert run.spent("gemini_usd") == pytest.approx(G.JUDGE_USD)


def test_open_batch_items_are_never_sent_again(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    c = G.GeminiClient(tmp_path / "g", cap_usd=6.0, run=run)
    c.batch_post = lambda method, url, body=None: {"name": "batches/one"}
    c.submit_batch([{"name": "a", "prompt": "p"}], model=MODEL, size=SIZE)
    assert G.open_batches(tmp_path / "g") == {"a": "batches_one.json"}


def test_a_lost_batch_submit_blocks_a_resend(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    c = G.GeminiClient(tmp_path / "g", cap_usd=6.0, run=run)

    def lost(method, url, body=None):
        raise TimeoutError("timed out")
    c.batch_post = lost
    with pytest.raises(G.ChargeUncertain):
        c.submit_batch([{"name": "a", "prompt": "p"}], model=MODEL, size=SIZE)
    assert "a" in G.open_batches(tmp_path / "g") and run.spent("gemini_usd") > 0


def test_collected_batch_pictures_fill_the_shared_cache(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    c = G.GeminiClient(tmp_path / "g", cap_usd=6.0, run=run, cache_dir=tmp_path / "cache")
    rows = [{"metadata": {"key": "a"}, "response": answer()}]
    c.batch_post = lambda method, url, body=None: ({"name": "batches/one"} if method == "POST" else
                                                   {"state": "JOB_STATE_SUCCEEDED", "dest": {"inlinedResponses": rows}})
    c.collect_batch(c.submit_batch([{"name": "a", "prompt": "p"}], model=MODEL, size=SIZE))
    assert G.open_batches(tmp_path / "g") == {}
    key = G.cache_key("p", MODEL, SIZE, "16:9", [])
    assert (tmp_path / "cache" / f"{key}.png").read_bytes() == PNG


def test_two_processes_on_one_ledger_stop_instead_of_erasing(tmp_path):
    a = Run.open(tmp_path / "run.json", caps={"gemini_usd": 6.0})
    b = Run.open(tmp_path / "run.json")
    a.reserve("gemini_usd", 0.1, item="x")
    with pytest.raises(LedgerConflict):
        b.reserve("gemini_usd", 0.1, item="y")
