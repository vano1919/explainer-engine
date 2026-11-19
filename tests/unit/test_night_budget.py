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
