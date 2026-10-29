"""Paid tests in config/spend_caps.json (the creator, 2026-10-29 18:40 UTC: P12a, P12b, P12e within $5.90 in total) and their
ledgers (core/ledger.Run.open_test): the test's line is its cap, nothing else can spend in it, the 80 % stop holds."""

import json

import pytest

from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import CapReached, Run, main


def test_paid_tests_lines_are_the_creators_and_stay_inside_his_total():
    tests = spend_caps.load()["paid_tests"]
    assert tests["total_usd"] == 5.9
    caps = {n: spend_caps.paid_test(n) for n in ("p12a_smoke", "p12b_two_runs", "p12e_hosts")}
    assert caps == {"p12a_smoke": {"runpod_usd": 0.5}, "p12b_two_runs": {"runpod_usd": 3.0}, "p12e_hosts": {"runpod_usd": 2.4}}
    assert sum(c["runpod_usd"] for c in caps.values()) <= tests["total_usd"] + 1e-9
    # every pod of a test fits the account's per-pod line
    assert all(c["runpod_usd"] * 0.8 <= spend_caps.runpod()["per_pod_usd"] for c in caps.values())


def test_unknown_test_and_a_section_over_its_total_are_refused(tmp_path, monkeypatch):
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.paid_test("p99_nothing")
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.paid_test("_doc")
    real = spend_caps.load()
    over = {**real, "paid_tests": {**real["paid_tests"], "p12z": {"runpod_usd": 1.0}}}
    f = tmp_path / "caps.json"
    f.write_text(json.dumps(over))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(f))
    with pytest.raises(spend_caps.OverCeiling):
        spend_caps.paid_test("p12a_smoke")


def test_test_ledger_has_only_its_line_and_stops_at_80_percent(tmp_path):
    run = Run.open_test(tmp_path / "run.json", "p12a_smoke")
    assert run.data["caps"]["runpod_usd"] == 0.5 and run.data["meta"] == {"test": "p12a_smoke"}
    assert all(v == 0.0 for k, v in run.data["caps"].items() if k != "runpod_usd")
    with pytest.raises(CapReached):  # nothing else can spend in a test ledger
        run.reserve("gemini_usd", 0.01, item="pic")
    for pod, usd in (("A", 0.07), ("B", 0.07), ("C", 0.10), ("D", 0.05), ("E", 0.09)):
        run.reserve("runpod_usd", usd, item=f"pod:{pod}")
    with pytest.raises(CapReached):  # 0.38 + 0.03 passes 80 % of 0.50
        run.reserve("runpod_usd", 0.03, item="pod:F")
    # reopening the same test's ledger keeps it; a plain Run.open (runpod create --ledger) keeps its cap too
    assert Run.open_test(tmp_path / "run.json", "p12a_smoke").spent("runpod_usd") == pytest.approx(0.38)
    assert Run.open(tmp_path / "run.json").data["caps"]["runpod_usd"] == 0.5


def test_open_test_refuses_another_runs_ledger(tmp_path):
    Run.open(tmp_path / "episode.json", caps={"runpod_usd": 10.0})
    with pytest.raises(ValueError):
        Run.open_test(tmp_path / "episode.json", "p12a_smoke")
    Run.open_test(tmp_path / "b.json", "p12b_two_runs")
    with pytest.raises(ValueError):
        Run.open_test(tmp_path / "b.json", "p12e_hosts")


def test_cli_open_test_and_report(tmp_path, capsys):
    main(["open-test", str(tmp_path / "e.json"), "p12e_hosts"])
    out = json.loads(capsys.readouterr().out)
    assert out["caps"]["runpod_usd"] == 2.4 and out["meta"]["test"] == "p12e_hosts"
    main(["report", str(tmp_path / "e.json")])
    assert json.loads(capsys.readouterr().out)["spent"] == {}
    with pytest.raises(SystemExit):
        main(["report", str(tmp_path / "missing.json")])
    assert not (tmp_path / "missing.json").exists()
