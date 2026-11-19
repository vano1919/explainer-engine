"""The night total (creator, 2026-11-19 22:25 UTC): one outer ceiling over every paid step."""
import json

import pytest

from explainer_engine.cloud import night_budget as N


def test_the_night_total_is_the_creators_ten_dollars():
    assert N.total_usd() == 10.0


def test_reservations_stop_at_the_total_a_repeat_is_refused_and_settlement_replaces_the_reservation(tmp_path):
    p = tmp_path / "night.json"
    with pytest.raises(N.NightCapExceeded, match="open the night ledger first"):
        N.reserve(p, "x", 1.0)
    N.open_ledger(p)
    N.reserve(p, "ltx_smoke", 0.5)
    N.reserve(p, "ltx_main", 3.5)
    with pytest.raises(N.NightCapExceeded, match="would pay twice"):
        N.reserve(p, "ltx_main", 3.5)
    with pytest.raises(N.NightCapExceeded, match="left of the night"):
        N.reserve(p, "upscale", 6.5)                                                           # 4.0 committed, 6.5 more is above 10
    d = N.settle(p, "ltx_smoke", 0.31)
    assert d["items"]["ltx_smoke"]["state"] == "settled" and N.committed(d) == pytest.approx(3.81)
    N.reserve(p, "upscale", 6.0)                                                               # what the smoke did not spend is free again
    with pytest.raises(N.NightCapExceeded, match="never rises"):
        N.open_ledger(p, 11)
    with pytest.raises(N.NightCapExceeded, match="would pass the night"):
        N.settle(p, "upscale", 7.0)


def test_the_cli_refuses_with_exit_one(tmp_path, capsys):
    p = str(tmp_path / "n.json")
    assert N.main(["open", p]) == 0 and N.main(["reserve", p, "a", "9"]) == 0
    assert N.main(["reserve", p, "b", "2"]) == 1
    assert "NIGHT LEDGER REFUSED" in capsys.readouterr().err
    assert json.loads(open(p).read())["items"].keys() == {"a"}


def test_the_ltx_launcher_reserves_the_hard_bill_before_the_gpu_call_and_refuses_past_the_total(tmp_path, monkeypatch):
    from explainer_engine.core import spend_caps
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    p = tmp_path / "night.json"
    N.open_ledger(p)
    hard = L.hard_bill_usd(L.LAUNCH, L.TIMEOUTS[1])
    assert 3.0 < hard < 3.5                                                                    # timeout + cold start at the H100 price, under the cap
    L.night_reserve("ltx_main_x", hard, "test", path=p)
    with pytest.raises(SystemExit, match="night total"):
        L.night_reserve("ltx_main_x", hard, "test", path=p)                                     # a repeat would pay twice
    L.night_reserve("ltx_smoke_x", 0.5, "test", path=p)
    with pytest.raises(SystemExit, match="night total.*left of the night"):
        L.night_reserve("upscale_x", 7.0, "test", path=p)                                       # 3.2 + 0.5 committed, 7.0 more passes 10
    L.night_settle("ltx_main_x", 1.9, path=p)
    assert N.committed(json.loads(p.read_text())) == pytest.approx(2.4, abs=0.01)
    with pytest.raises(SystemExit, match="open the night ledger first"):
        L.night_reserve("y", 1.0, path=tmp_path / "missing.json")                              # no ledger file: refused, never skipped
    monkeypatch.setattr(spend_caps, "modal", lambda episode=False: {"per_run_usd": 3.5})       # no night line: the rule does not apply
    L.night_reserve("z", 99.0, path=tmp_path / "missing.json")


def test_both_paid_entrypoints_call_the_night_ledger_before_the_function_and_settle_after():
    import inspect
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    src = inspect.getsource(L)
    for call in ("ltx_smoke.remote(", "ltx_main.remote("):
        assert 0 < src.index("night_reserve(") < src.index(call), call
    smoke, main = src.split("def smoke(")[1].split("def main(")[0], src.split("def main(")[-1]
    assert smoke.index("night_reserve(") < smoke.index("ltx_smoke.remote(") < smoke.index("night_settle(")
    assert main.index("night_reserve(") < main.index("claim_launch(spec)") < main.index("ltx_main.remote(") < main.index("night_settle(")


def test_a_chained_clip_with_an_end_picture_is_refused_like_the_top_job(monkeypatch):
    from explainer_engine.core import spend_caps
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    monkeypatch.setattr(spend_caps, "modal_ltx", lambda episode=False: {"per_run_usd": 5.0})
    job = {"shot_id": "c1", "seconds": 8.0, "seed": 1, "motion_prompt": "x",
           "chain": [{"shot_id": "c2", "seconds": 8.0, "seed": 2, "motion_prompt": "y", "end_picture": "e.png"}]}
    with pytest.raises(SystemExit, match="c2: an end picture, but only the keyframes kind"):
        L.preflight(L.LAUNCH, job)
