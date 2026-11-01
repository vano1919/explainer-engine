"""Paid tests in config/spend_caps.json (the creator, 2026-10-29 18:40 UTC: P12a, P12b, P12e within $5.90 in total) and their
ledgers (core/ledger.Run.open_test): the test's line is its cap, nothing else can spend in it, the 80 % stop holds."""

import json

import pytest

from explainer_engine.core import spend_caps
from explainer_engine.core.ledger import CapReached, LedgerConflict, Run, main


@pytest.fixture(autouse=True)
def mirror_dir(tmp_path, monkeypatch):
    """The durable folder a paid test's ledger needs (EXPLAINER_LEDGER_MIRROR); outside tmp_path's ledgers, like a volume."""
    d = tmp_path / "durable"
    monkeypatch.setenv("EXPLAINER_LEDGER_MIRROR", str(d))
    return d


def test_paid_tests_lines_are_the_creators_and_stay_inside_his_total():
    tests = spend_caps.load()["paid_tests"]
    assert tests["total_usd"] == 5.9
    names = ("p12a_smoke", "p12b_two_runs", "p12e_hosts", "p12b_measure")
    caps = {n: spend_caps.paid_test(n) for n in names}
    assert caps == {"p12a_smoke": {"runpod_usd": 0.5}, "p12b_two_runs": {"runpod_usd": 3.0}, "p12e_hosts": {"runpod_usd": 2.02},
                    "p12b_measure": {"runpod_usd": 0.38}}     # p12e dropped (D-89); 0.38 of its 2.40 went to the measurement pod (creator 2026-11-01)
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


def test_test_ledger_has_only_its_line_and_stops_at_80_percent(tmp_path, mirror_dir):
    run = Run.open_test(tmp_path / "run.json", "p12a_smoke")
    assert run.data["caps"]["runpod_usd"] == 0.5
    assert run.data["meta"] == {"test": "p12a_smoke", "mirror": str(mirror_dir / "p12a_smoke.json")}
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
    assert out["caps"]["runpod_usd"] == 2.02 and out["meta"]["test"] == "p12e_hosts"
    main(["report", str(tmp_path / "e.json")])
    assert json.loads(capsys.readouterr().out)["spent"] == {}
    with pytest.raises(SystemExit):
        main(["report", str(tmp_path / "missing.json")])
    assert not (tmp_path / "missing.json").exists()


def _test_caps(name):
    """The caps open_test sets: every per-episode service at 0, the test's own lines on top."""
    return {**{s: 0.0 for s in spend_caps.load()["per_episode"]}, **spend_caps.paid_test(name)}


def test_open_test_refuses_a_ledger_that_is_not_that_tests(tmp_path):
    """Same caps as open_test would set, but no meta test (an episode ledger) or another test's: refused, not adopted."""
    caps = _test_caps("p12a_smoke")
    Run.open(tmp_path / "plain.json", caps=caps)
    Run.open(tmp_path / "other.json", caps=caps, test="p12b_two_runs")
    for name in ("plain.json", "other.json"):
        with pytest.raises(ValueError, match="not the ledger of paid test"):
            Run.open_test(tmp_path / name, "p12a_smoke")
    assert "test" not in json.loads((tmp_path / "plain.json").read_text())["meta"]  # and left as it was


def test_a_test_ledger_with_a_cap_above_its_line_is_refused_on_open(tmp_path, mirror_dir):
    run = Run.open_test(tmp_path / "run.json", "p12a_smoke")
    for f in (run.path, mirror_dir / "p12a_smoke.json"):  # the cap raised by hand in both copies
        data = json.loads(f.read_text())
        data["caps"]["runpod_usd"] = 20.0
        f.write_text(json.dumps(data))
    with pytest.raises(spend_caps.OverCeiling, match="runpod_usd"):
        Run.open(tmp_path / "run.json")
    with pytest.raises(ValueError, match="already 20.0"):  # open_test refuses too: the ledger's cap is not the line any more
        Run.open_test(tmp_path / "run.json", "p12a_smoke")
    # a cap on a service the test has no line for is the same breach (check_caps fills it from the episode ceiling)
    data["caps"] = {"runpod_usd": 0.5}
    run.path.write_text(json.dumps(data))
    with pytest.raises(spend_caps.OverCeiling, match="gemini_usd"):
        Run.open(run.path)
    # lower caps than the line are allowed (a hand edit reconciles both copies: same bytes in the ledger and its mirror)
    data["caps"] = {**_test_caps("p12a_smoke"), "runpod_usd": 0.2}
    for f in (run.path, mirror_dir / "p12a_smoke.json"):
        f.write_text(json.dumps(data))
    assert Run.open(run.path).data["caps"]["runpod_usd"] == 0.2


def test_a_second_path_for_the_same_test_continues_from_what_was_spent(tmp_path):
    a = Run.open_test(tmp_path / "a" / "run.json", "p12a_smoke")
    for pod, usd in (("A", 0.07), ("B", 0.07), ("C", 0.10), ("D", 0.05), ("E", 0.09)):
        a.reserve("runpod_usd", usd, item=f"pod:{pod}")
    b = Run.open_test(tmp_path / "b" / "run.json", "p12a_smoke")  # a new path, not a new allowance
    assert b.spent("runpod_usd") == pytest.approx(0.38) and set(b.data["reserved"]) == set(a.data["reserved"])
    with pytest.raises(CapReached):
        b.reserve("runpod_usd", 0.03, item="pod:F")
    b.reserve("runpod_usd", 0.02, item="pod:G")
    assert Run.open_test(tmp_path / "c" / "run.json", "p12a_smoke").spent("runpod_usd") == pytest.approx(0.40)
    # another test has its own mirror and its own line
    assert Run.open_test(tmp_path / "d" / "run.json", "p12b_two_runs").spent("runpod_usd") == 0


def test_a_lost_container_restores_the_ledger_from_the_mirror(tmp_path):
    path = tmp_path / "jobs" / "run.json"
    run = Run.open_test(path, "p12a_smoke")
    run.reserve("runpod_usd", 0.30, item="pod:A")
    run.settle("runpod_usd", "pod:A", 0.12)  # a later save from another call still updates the mirror
    path.unlink()
    path.parent.rmdir()  # the container (and its jobs folder) is gone
    back = Run.open_test(path, "p12a_smoke")
    assert path.exists() and back.spent("runpod_usd") == pytest.approx(0.12)
    assert back.data["reserved"]["pod:A"] == {"service": "runpod_usd", "amount": 0.12, "settled": True}
    with pytest.raises(CapReached):  # 0.12 + 0.29 passes 80 % of 0.50
        back.reserve("runpod_usd", 0.29, item="pod:B")


def test_a_ledger_and_a_mirror_that_differ_stop_with_a_conflict(tmp_path, mirror_dir):
    path = tmp_path / "run.json"
    run = Run.open_test(path, "p12a_smoke")
    run.reserve("runpod_usd", 0.10, item="pod:A")
    mirror = mirror_dir / "p12a_smoke.json"
    data = json.loads(mirror.read_text())
    data["spent"]["runpod_usd"] = 0.25  # the mirror is ahead (or the ledger was edited back)
    mirror.write_text(json.dumps(data, indent=2))
    with pytest.raises(LedgerConflict, match="reconcile by hand"):
        Run.open_test(path, "p12a_smoke")


def test_a_stale_path_cannot_overwrite_what_another_path_spent(tmp_path, mirror_dir):
    a = Run.open_test(tmp_path / "a" / "run.json", "p12a_smoke")
    for pod, usd in (("A", 0.07), ("B", 0.07), ("C", 0.10), ("D", 0.05), ("E", 0.09)):
        a.reserve("runpod_usd", usd, item=f"pod:{pod}")
    b = Run.open_test(tmp_path / "b" / "run.json", "p12a_smoke")  # restored from the mirror, then spends on its own path
    b.reserve("runpod_usd", 0.02, item="pod:G")
    mirror = mirror_dir / "p12a_smoke.json"
    assert json.loads(mirror.read_text())["spent"]["runpod_usd"] == pytest.approx(0.40)
    # a plain Run.open of the stale path (runpod create --ledger) saves, and its save must not erase b's 0.02 from the mirror
    with pytest.raises(LedgerConflict, match="reconcile by hand"):
        Run.open(tmp_path / "a" / "run.json")
    # nor can the stale object that is still in memory
    with pytest.raises(LedgerConflict):
        a.reserve("runpod_usd", 0.01, item="pod:Z")
    assert json.loads(mirror.read_text())["spent"]["runpod_usd"] == pytest.approx(0.40)


def test_a_paid_tests_ledger_needs_the_durable_mirror(tmp_path, monkeypatch):
    for value in (None, ""):
        if value is None:
            monkeypatch.delenv("EXPLAINER_LEDGER_MIRROR")
        else:
            monkeypatch.setenv("EXPLAINER_LEDGER_MIRROR", value)
        with pytest.raises(ValueError, match="durable mirror"):
            Run.open_test(tmp_path / "run.json", "p12a_smoke")
        assert not (tmp_path / "run.json").exists()
        with pytest.raises(ValueError, match="durable mirror"):  # the CLI path too
            main(["open-test", str(tmp_path / "run.json"), "p12a_smoke"])


def test_report_reads_a_ledger_without_writing_it(tmp_path, capsys, mirror_dir):
    path = tmp_path / "run.json"
    run = Run.open_test(path, "p12a_smoke")
    run.reserve("runpod_usd", 0.07, item="pod:A")
    before, mirror_before = path.read_bytes(), (mirror_dir / "p12a_smoke.json").read_bytes()
    main(["report", str(path)])
    out = json.loads(capsys.readouterr().out)
    assert out["spent"] == {"runpod_usd": 0.07} and out["meta"]["test"] == "p12a_smoke"
    assert path.read_bytes() == before and (mirror_dir / "p12a_smoke.json").read_bytes() == mirror_before
    # an old ledger made before the ceilings grew: reported as it is, not filled in and saved
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"created": "2026-10-01T00:00:00", "caps": {"runpod_usd": 5.0}, "spent": {}, "reserved": {},
                               "phases": {}, "items": {}, "failures": {}, "meta": {}}, indent=2))
    before = old.read_bytes()
    main(["report", str(old)])
    assert json.loads(capsys.readouterr().out)["caps"] == {"runpod_usd": 5.0}
    assert old.read_bytes() == before
