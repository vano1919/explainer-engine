import pytest

from explainer_engine.core.ledger import CapReached, Run


def test_reserve_stops_at_80_percent_and_keeps_state(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 1.0})
    run.reserve("gemini_usd", 0.5, item="a")
    run.reserve("gemini_usd", 0.3, item="b")
    with pytest.raises(CapReached):
        run.reserve("gemini_usd", 0.05, item="c")
    again = Run.open(tmp_path / "run.json")
    assert again.spent("gemini_usd") == pytest.approx(0.8)


def test_no_cap_no_spend(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 1.0})
    with pytest.raises(CapReached):
        run.reserve("elevenlabs_credits", 10)


def test_paid_items_are_not_bought_twice_after_a_stop(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 1.0})
    run.done("pictures", "p1", file="p1.png")
    again = Run.open(tmp_path / "run.json")
    assert again.pending("pictures", ["p1", "p2"]) == ["p2"]


def test_three_failures_stop_an_item_and_a_cap_cannot_be_raised_silently(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 1.0})
    assert run.fail("p1", "x") and run.fail("p1", "y")
    assert not run.fail("p1", "z")
    with pytest.raises(ValueError):
        Run.open(tmp_path / "run.json", caps={"gemini_usd": 9.0})


def test_gemini_client_reserves_in_the_ledger_and_refunds_a_refused_call(tmp_path):
    from explainer_engine.imagegen.gemini import GeminiClient, GeminiError
    run = Run.open(tmp_path / "run.json", caps={"gemini_usd": 1.0})

    def refuse(model, body):
        raise GeminiError("blocked")

    c = GeminiClient(tmp_path / "g", key="k", cap_usd=100.0, post=refuse, run=run)
    with pytest.raises(GeminiError):
        c.generate("a", "p", model="gemini-nano-banana-2.1", size="2K")
    assert run.spent("gemini_usd") == 0.0
    run.reserve("gemini_usd", 0.79)
    c2 = GeminiClient(tmp_path / "g", key="k", cap_usd=100.0, post=refuse, run=run)
    with pytest.raises(CapReached):
        c2.generate("b", "p2", model="gemini-nano-banana-2.1", size="2K")


def test_the_qa_loop_allowance_is_a_ceiling_inside_the_elevenlabs_cap(tmp_path, monkeypatch):
    # the creator, 2026-10-20: the QA loop may spend at most 2,000 ElevenLabs credits per run on its own, only on re-reads of
    # script lines it changed; the run's own cap (and its 80 % stop) still applies
    import json

    from explainer_engine.core import spend_caps
    from explainer_engine.core.ledger import AllowanceReached
    real = spend_caps.load()
    assert real["allowances"]["qa_loop"] == {**real["allowances"]["qa_loop"], "service": "elevenlabs_credits", "per_run": 2000}
    run = Run.open(tmp_path / "run.json", caps={"elevenlabs_credits": 23000})
    run.reserve_allowance("qa_loop", 1500, "reread_1", lines=["S02 L4"])
    run.reserve_allowance("qa_loop", 500, "reread_2", lines=["S02 L5"])
    with pytest.raises(AllowanceReached):
        run.reserve_allowance("qa_loop", 1, "reread_3", lines=["S02 L6"])
    assert run.allowance_used("qa_loop") == 2000 and run.spent("elevenlabs_credits") == 2000
    with pytest.raises(ValueError):  # only for named changed lines
        Run.open(tmp_path / "other.json", caps={"elevenlabs_credits": 23000}).reserve_allowance("qa_loop", 10, "x", lines=[])
    # inside the cap: a run whose cap is nearly spent refuses even under the allowance, and nothing is recorded
    tight = Run.open(tmp_path / "tight.json", caps={"elevenlabs_credits": 1000})
    tight.reserve("elevenlabs_credits", 700, item="narration")
    with pytest.raises(CapReached):
        tight.reserve_allowance("qa_loop", 200, "reread", lines=["S01 L1"])
    assert tight.allowance_used("qa_loop") == 0 and tight.spent("elevenlabs_credits") == 700
    # no allowance in the file: no spending on its own
    caps = tmp_path / "caps.json"
    caps.write_text(json.dumps({k: v for k, v in real.items() if k != "allowances"}))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(caps))
    with pytest.raises(spend_caps.OverCeiling):
        Run.open(tmp_path / "none.json", caps={"elevenlabs_credits": 1000}).reserve_allowance("qa_loop", 1, "x", lines=["a"])
