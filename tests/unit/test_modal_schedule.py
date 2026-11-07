"""Modal run plan: the cheapest passing (hardware, split) per step, offline, with a fake price table."""
import pytest

from explainer_engine.cloud import modal_schedule as m

FAKE = {
    "slow": {"usd_s": 0.001, "vram_gb": 80, "arch": "x", "speed": 1.0},
    "fast": {"usd_s": 0.003, "vram_gb": 80, "arch": "x", "speed": 4.0},   # cheaper per unit of work
    "small": {"usd_s": 0.0001, "vram_gb": 16, "arch": "x", "speed": 0.1},
}


def spec(**kw):
    s = {"schema": m.SCHEMA, "job": "t", "limits": {"max_usd": 50, "max_hours": 10}, "credit_usd": 30,
         "steps": [{"id": "g", "kind": "gpu", "work": 600, "min_vram_gb": 40, "max_split": 4, "overhead_s": 30,
                    "measured": False},
                   {"id": "c", "kind": "cpu", "work": 4000, "max_split": 20, "overhead_s": 20, "needs": ["g"],
                    "measured": False}]}
    s.update(kw)
    return s


def test_vram_filters_cards():
    res = m.plan(spec(), gpus=FAKE)
    assert all(hw != "small" for hw, _ in [res["pick"]["choice"]["g"]])


def test_cheapest_hardware_is_by_cost_per_work_not_price():
    res = m.plan(spec(), gpus=FAKE)
    assert res["pick"]["choice"]["g"][0] == "fast"      # 0.003/4 < 0.001/1 per work second


def test_cpu_cost_is_independent_of_split_but_wall_shrinks():
    st = spec()["steps"][1]
    rate = m._rate_cpu(2, st)
    one = m._opt(st, "cpu2", 1, rate, 2.0, 1.5, 3)
    many = m._opt(st, "cpu2", 20, rate, 2.0, 1.5, 3)
    assert many["wall_s"] < one["wall_s"] / 5
    # only the container start overhead is paid again per container
    assert many["cost"] - one["cost"] == pytest.approx(19 * 20 * rate)


def test_worst_case_adds_slack_and_retries():
    st = spec()["steps"][0]
    o = m.step_options(st, {"slow": FAKE["slow"]}, 1.5, 3)[0]
    assert o["worst_cost"] > o["cost"] * 1.5


def test_caps_exclude_and_report_over_cap():
    res = m.plan(spec(limits={"max_usd": 0.01, "max_hours": 10}), gpus=FAKE)
    assert res["pick"] is None and res["over_cap_best"]["over_usd"] > 0
    assert "NOTHING PASSES" in m.report(res)


def test_credit_covers_small_runs():
    res = m.plan(spec(), gpus=FAKE)
    assert res["pick"]["charge"] == 0.0
    res = m.plan(spec(credit_usd=0.0), gpus=FAKE)
    assert res["pick"]["charge"] == pytest.approx(res["pick"]["cost"])


def test_critical_path_runs_independent_steps_concurrently():
    s = spec()
    s["steps"].append({"id": "g2", "kind": "gpu", "work": 600, "min_vram_gb": 40, "max_split": 1, "overhead_s": 30,
                       "measured": False})
    res = m.plan(s, gpus=FAKE)
    p = res["fastest"]
    walls = {k: m.step_options(st, FAKE, 1.5, 3) for k, st in ((x["id"], x) for x in s["steps"])}
    assert p["wall_s"] < sum(min(o["wall_s"] for o in v) for v in walls.values())


def test_gpu_concurrency_limit(monkeypatch):
    s = spec()
    s["steps"][0]["max_split"] = 64
    monkeypatch.setattr(m, "GPU_CONCURRENCY", 3)
    res = m.plan(s, gpus=FAKE)
    assert res["pick"]["choice"]["g"][1] <= 3


def test_validate_requires_measured_flag_and_known_needs():
    bad = spec()
    del bad["steps"][0]["measured"]
    bad["steps"][1]["needs"] = ["nope"]
    errs = m.validate(bad)
    assert any("measured" in e for e in errs) and any("unknown" in e for e in errs)
    with pytest.raises(m.ModalScheduleError):
        m.plan(bad, gpus=FAKE)


def test_builtin_jobs_plan_and_film_frames():
    for job in ("p15d", "film21", "film24"):
        sp = m.job_spec(job)
        assert not m.validate(sp)
        res = m.plan({**sp, "limits": {"max_usd": 9, "max_hours": 5}})
        assert res["pick"] and res["pick"]["charge"] == 0.0
    j21, j24 = m.job_spec("film21"), m.job_spec("film24")
    a21 = next(s for s in j21["steps"] if s["id"] == "assemble_25d")["work"]
    a24 = next(s for s in j24["steps"] if s["id"] == "assemble_25d")["work"]
    assert a24 / a21 == pytest.approx((576 - 121) / (517 - 121))


def test_price_table_matches_page_numbers():
    assert m.GPUS["A100-80GB"]["usd_s"] == 0.000694 and m.GPUS["H100"]["usd_s"] == 0.001097
    assert m.CPU_CORE_S == 0.0000131 and m.MEM_GIB_S == 0.00000222
