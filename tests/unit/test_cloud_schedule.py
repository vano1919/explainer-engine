"""RP-11 (cloud/schedule.py): every combination of a pod's run is computed before the pod and the cheapest one taken
(the creator, 2026-11-06 14:48 UTC, after the step-3 pod's H100 sat idle behind a CPU Blender frame)."""
import json

import pytest
from test_cloud_stop_paths import env  # noqa: F401 - the fixture of the create tests

from explainer_engine.cloud import schedule as S

H100 = {"name": "H100 NVL", "cloud": "COMMUNITY", "price_h": 2.59, "gpu_speed": 1.0}
A100 = {"name": "A100 80GB", "cloud": "COMMUNITY", "price_h": 1.39, "gpu_speed": 0.6}


def step3_as_launched():
    """The step-3 pod of 2026-11-06 as its code ran: the whole Qwen process waited for both Blender first frames on the CPU,
    and the LTX clips waited for every Blender pass (timeouts 30 min per first frame, 90 min for the passes)."""
    return {"schema": S.SCHEMA, "setup_min": 4, "end_reserve_min": 10, "lanes": {"gpu": 1, "cpu": 1, "net": 1},
            "stages": [
                {"id": "weights", "needs": [], "on": {"net": {"expected_min": 6, "max_min": 15}}},
                {"id": "A.frame0", "needs": [], "on": {"cpu": {"expected_min": 5, "max_min": 60}}},
                {"id": "qwen1", "needs": ["weights", "A.frame0"], "on": {"gpu": {"expected_min": 15, "max_min": 40}}},
                {"id": "D", "needs": ["weights"], "on": {"gpu": {"expected_min": 5, "max_min": 15}}},
                {"id": "A", "needs": [], "on": {"cpu": {"expected_min": 40, "max_min": 90}}},
                {"id": "E", "needs": ["weights", "A"], "on": {"gpu": {"expected_min": 40, "max_min": 80}}}],
            "cards": [H100], "limits": {"max_usd": 8, "max_hours": 3.5, "max_idle_gpu_share": 0.15}}


def step3_fixed():
    """The same work with each stage waiting only for its own inputs and Blender allowed on the GPU."""
    spec = step3_as_launched()
    spec["stages"] = [
        {"id": "weights", "needs": [], "on": {"net": {"expected_min": 6, "max_min": 15}}},
        {"id": "A.frame0", "needs": [], "on": {"cpu": {"expected_min": 5, "max_min": 60}, "gpu": {"expected_min": 0.5, "max_min": 3}}},
        {"id": "C+X6", "needs": ["weights"], "on": {"gpu": {"expected_min": 8, "max_min": 20}}},
        {"id": "B", "needs": ["weights", "A.frame0"], "on": {"gpu": {"expected_min": 7, "max_min": 20}}},
        {"id": "D", "needs": ["weights"], "on": {"gpu": {"expected_min": 5, "max_min": 15}}},
        {"id": "A", "needs": [], "on": {"cpu": {"expected_min": 40, "max_min": 90}, "gpu": {"expected_min": 6, "max_min": 15}}},
        {"id": "E", "needs": ["weights", "A"], "on": {"gpu": {"expected_min": 40, "max_min": 80}}}]
    return spec


def test_the_launched_plan_is_refused_for_its_idle_gpu():
    spec = step3_as_launched()
    why = S.check(spec)
    assert any("idle" in w for w in why), why
    res = S.plan(spec)
    assert res["exhaustive"] and res["combinations"] == res["of_total"] > 0


def test_the_fixed_plan_passes_and_puts_blender_on_the_gpu():
    spec = step3_fixed()
    res = S.plan(spec)
    assert S.check(spec, res) == []
    best = res["best"]
    assert best["lanes"]["A"] == "gpu"   # the 40-min CPU pass would make E wait; a CPU first frame is fine while C+X6 run
    assert best["worst"]["usd"] <= 8 and best["worst"]["idle_share"] <= 0.15


def test_every_combination_is_tried_and_none_drops_or_reorders_against_inputs():
    spec = step3_fixed()
    seen = list(S.combinations(spec))
    gpu_flex = 2 * 2  # A.frame0 and A each on cpu or gpu
    assert len({json.dumps(l, sort_keys=True) for _, l, _ in seen}) == gpu_flex
    needs = {s["id"]: s["needs"] for s in spec["stages"]}
    for card, lane_of, order in seen:
        assert sorted(order) == sorted(k for k, v in lane_of.items() if v == "gpu")   # nothing dropped
        assert S._respects(order, {k: set(v) for k, v in needs.items()})               # inputs first
        r = S.simulate(spec, card, lane_of, order, "worst")
        assert set(r["start"]) == {s["id"] for s in spec["stages"]}                       # every stage runs


def test_the_cheapest_card_is_taken_when_it_fits():
    spec = step3_fixed()
    spec["cards"] = [H100, A100]
    best = S.plan(spec)["best"]
    exp_h = S.simulate(spec, H100, best["lanes"], best["gpu_order"])["usd"]
    assert best["card"] == ("A100 80GB" if best["expected"]["usd"] < exp_h else "H100 NVL")
    spec["limits"]["max_hours"] = 0.1
    res = S.plan(spec)
    assert res["fitting"] == 0 and any("no combination fits" in w for w in S.check(spec, res))


def test_the_pods_own_order_is_held_to_the_cheapest():
    spec = step3_fixed()
    res = S.plan(spec)
    good = S.committed(spec, "H100 NVL", res["best"]["gpu_order"], res["best"]["lanes"])
    assert S.check(spec, res, good) == []
    bad = S.committed(spec, "H100 NVL", ["E", "D", "B", "C+X6"], {"A": "cpu", "A.frame0": "cpu"})
    assert any("own order" in w for w in S.check(spec, res, bad))


def test_a_wait_is_counted_as_idle_gpu():
    spec = {"schema": S.SCHEMA, "setup_min": 0, "end_reserve_min": 0, "lanes": {"gpu": 1, "cpu": 1},
            "stages": [{"id": "cpu1", "needs": [], "on": {"cpu": {"expected_min": 30, "max_min": 30}}},
                       {"id": "g1", "needs": ["cpu1"], "on": {"gpu": {"expected_min": 10, "max_min": 10}}}],
            "cards": [{"name": "x", "price_h": 6.0}]}
    r = S.simulate(spec, spec["cards"][0], {"cpu1": "cpu", "g1": "gpu"}, ["g1"])
    assert r["gpu_idle_min"] == 30 and r["span_min"] == 40 and r["usd"] == 4.0


@pytest.mark.parametrize("broken, word", [
    ({"stages": []}, "no stages"),
    ({"cards": []}, "no cards"),
    ({"stages": [{"id": "a", "needs": ["b"], "on": {"gpu": {"expected_min": 1, "max_min": 1}}},
                 {"id": "b", "needs": ["a"], "on": {"gpu": {"expected_min": 1, "max_min": 1}}}]}, "cycle"),
    ({"stages": [{"id": "a", "needs": [], "on": {"gpu": {"expected_min": 1}}}]}, "max_min"),
])
def test_validate_refuses_an_incomplete_plan(broken, word):
    spec = step3_fixed()
    spec.update(broken)
    assert any(word in p for p in S.validate(spec))


def test_cli_check_exit_codes(tmp_path, capsys):
    p = tmp_path / "s.json"
    p.write_text(json.dumps(step3_as_launched()), encoding="utf-8")
    assert S.main(["check", str(p)]) == 1
    p.write_text(json.dumps(step3_fixed()), encoding="utf-8")
    assert S.main(["check", str(p), "--out", str(tmp_path / "plan.json")]) == 0
    assert json.loads((tmp_path / "plan.json").read_text())["best"]["card"] == "H100 NVL"
    assert "combinations tried" in capsys.readouterr().out


def test_rp11_needs_a_schedule_and_reads_the_creates_own_caps(tmp_path):
    assert "required" in S.rp11(None)[0]
    assert S.rp11(None, measure=True) == [] and S.rp11(None, test="p12a_smoke") == []
    p = tmp_path / "s.json"
    p.write_text(json.dumps(step3_fixed()), encoding="utf-8")
    assert S.rp11(str(p), max_usd=8, max_hours=3.5) == []
    assert any("no combination fits" in w for w in S.rp11(str(p), max_usd=1.0, max_hours=3.5))   # the create's cap wins
    p.write_text("{}", encoding="utf-8")
    assert "schema" in S.rp11(str(p))[0]


def test_create_refuses_a_script_pod_without_its_schedule(env, monkeypatch):
    from test_cloud_stop_paths import FakeLive, NEW_SH, PLAN
    from explainer_engine.cloud import runpod as R
    from explainer_engine.core.ledger import Run
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    Run.open(tmp / "run.json", caps={"runpod_usd": 1.0})
    (tmp / "job.sh").write_text(NEW_SH)
    plan = [x for i, x in enumerate(PLAN) if x != "--schedule" and (i == 0 or PLAN[i - 1] != "--schedule")]
    with pytest.raises(SystemExit, match="RP-11: --schedule"):
        R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(tmp / "run.json"), "--script",
                str(tmp / "job.sh"), "--script-url", "https://huggingface.co/x/pod.sh", *plan], api=api, live=FakeLive(age=60))
    assert not fake.pods
