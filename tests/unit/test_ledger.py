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
