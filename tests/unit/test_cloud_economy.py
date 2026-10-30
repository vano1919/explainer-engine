"""P1c (docs/CLOUD_RUNBOOK.md RP-01..RP-10): the measured speed table, the card picker, the batching rules, the bill into the ledger.
Fake RunPod, no network, no money."""
import json

import pytest
from test_cloud_stop_paths import BEAT, PLAN, FakeLive, _create, env  # noqa: F401 - the create tests' fixture and helpers
from test_runpod import CATALOG, NEW_SH, FakeRunPod, _session, pod

from explainer_engine.cloud import batching as B, hooks as H, runpod as R, speeds as S
from explainer_engine.core.ledger import CapReached, Run


# --- the speed table ---------------------------------------------------------------------------------------------------------
def test_the_committed_table_has_job_types_and_no_invented_row():
    data = S.load(S.ROOT / "config" / "job_speeds.json")
    assert data["margin_unmeasured"] == 2.0 and data["setup_share_max"] == 0.4
    assert {"keyframes", "ltx_clip", "lora_train", "captions", "smoke"} <= set(data["jobs"])
    assert all(j["rows"] == {} and j["unit"] for j in data["jobs"].values())   # measured by P12a/P12b, never typed


def test_a_row_is_written_from_a_measurement_and_needs_a_known_job_and_real_numbers():
    r = S.record("keyframes", "NVIDIA A40", cloud="COMMUNITY", units=100, work_s=4500, setup_s=720, mb=32000, download_s=640, usd=0.55,
                 source="pod x", now=0)
    assert r["s_per_unit"] == 45 and r["setup_min"] == 12 and r["mb_per_s"] == {"COMMUNITY": 50.0} and r["usd_per_unit"] == 0.0055
    assert S.row("keyframes", "NVIDIA A40")["units"] == 100 and S.row("keyframes", "NVIDIA L40S") is None
    est = S.estimate("keyframes", "NVIDIA A40", 20)
    assert est["work_h"] == pytest.approx(0.25) and est["setup_h"] == pytest.approx(0.2) and est["basis"] == "measured"
    with pytest.raises(S.SpeedError, match="unknown job type"):
        S.record("nonsense", "x", cloud="C", units=1, work_s=1, source="s")
    with pytest.raises(S.SpeedError, match="units > 0"):
        S.record("keyframes", "x", cloud="C", units=0, work_s=1, source="s")
    assert S.from_units_json('{"job_type": "keyframes", "units": 3, "work_s": 60}')["units"] == 3
    with pytest.raises(S.SpeedError, match="lacks work_s"):
        S.from_units_json('{"job_type": "keyframes", "units": 3}')
    for bad in ("[]", "null", "5", '"x"', "{", '{"job_type": "keyframes", "units": "abc", "work_s": 60}',
                '{"job_type": "keyframes", "units": 3, "work_s": -1}', '{"job_type": "keyframes", "units": true, "work_s": 60}',
                '{"job_type": "keyframes", "units": 3, "work_s": 60, "setup_s": "x"}', '{"job_type": 7, "units": 3, "work_s": 60}'):
        with pytest.raises(S.SpeedError):                                              # one clear contract error, never AttributeError
            S.from_units_json(bad)



# --- the picker --------------------------------------------------------------------------------------------------------------
def test_the_picker_prefers_a_measured_row_over_the_estimate(env):
    fake, api, _ = env
    fake.catalog = CATALOG
    est = {r["gpu"]: r for r in R.pick_gpus(api, vram_gb=48, ref_hours=1.0, max_price=1.0)}
    assert est["NVIDIA A40"]["basis"] == "estimate" and est["NVIDIA A40"]["hours"] == 2.0          # SPEED 0.5
    S.record("keyframes", "NVIDIA A40", cloud="COMMUNITY", units=10, work_s=900, setup_s=None, source="pod x")  # 90 s per picture
    rows = {(r["gpu"], r["cloud"]): r for r in R.pick_gpus(api, vram_gb=48, ref_hours=1.0, max_price=1.0, job="keyframes", units=20)}
    a40 = rows[("NVIDIA A40", "COMMUNITY")]
    assert a40["basis"] == "measured" and a40["hours"] == pytest.approx(0.5) and a40["est_usd"] == pytest.approx(0.175)   # 90 s x 20 pictures
    assert rows[("Some New Card", "SECURE")]["basis"].startswith("unknown card")                    # still not skipped


def test_a_card_whose_setup_is_over_forty_percent_of_the_job_is_refused_with_the_reason(env):
    fake, api, _ = env
    fake.catalog = CATALOG
    refused = []
    rows = R.pick_gpus(api, vram_gb=48, ref_hours=1.0, max_price=1.0, setup_min=60, refused=refused)    # A40: 2 h of work, 1 h setup = 33 %
    assert {r["gpu"] for r in rows} == {"NVIDIA A40", "Some New Card"} and rows[0]["setup_share"] == pytest.approx(0.333, abs=0.001)
    refused.clear()
    rows = R.pick_gpus(api, vram_gb=80, ref_hours=1.0, setup_min=60, refused=refused)                  # H100: 0.5 h of work, 1 h setup = 67 %
    assert not any(r["gpu"] == "NVIDIA H100 80GB HBM3" for r in rows)
    assert any("RP-09" in w and "H100" in w and "67 %" in w.replace("%", " %") for w in refused)
    S.record("keyframes", "NVIDIA A100-SXM4-80GB", cloud="COMMUNITY", units=10, work_s=600, setup_s=3600, source="pod x")  # measured setup 60 min
    refused.clear()
    rows = R.pick_gpus(api, vram_gb=80, ref_hours=1.0, job="keyframes", units=10, refused=refused)      # 10 min of work, 60 min setup: 86 %
    assert not any(r["gpu"] == "NVIDIA A100-SXM4-80GB" and r["cloud"] == "COMMUNITY" for r in rows) and any("A100-SXM4" in w for w in refused)


def test_the_cards_command_prints_the_basis_and_the_refusals(env, capsys):
    fake, api, _ = env
    fake.catalog = CATALOG
    R.main(["cards", "--vram", "80", "--ref-hours", "2", "--setup-min", "60"], api=api)
    out = capsys.readouterr().out
    assert "; estimate)" in out and "; unknown card x2)" in out and "refused RP-09: NVIDIA H100 80GB HBM3" in out


def test_wait_for_stock_polls_until_a_card_has_stock_or_the_time_is_up():
    seen, now = [], {"t": 0.0}
    answers = iter([[], [], [{"gpu": "x"}]])
    sleep = lambda s: (seen.append(s), now.__setitem__("t", now["t"] + s))  # noqa: E731
    rows = R.wait_for_stock(lambda: next(answers), 900, sleep=sleep, clock=lambda: now["t"])
    assert rows == [{"gpu": "x"}] and seen == [30, 30]
    now["t"], seen[:] = 0.0, []
    assert R.wait_for_stock(lambda: [], 90, sleep=sleep, clock=lambda: now["t"]) == [] and seen == [30, 30, 30]    # gave up, no card
    assert R.parse_wait("15m") == 900 and R.parse_wait("2h") == 7200 and R.parse_wait(None) == 0
    with pytest.raises(SystemExit, match="--wait-stock"):
        R.parse_wait("soon")


# --- the batching rules at create ---------------------------------------------------------------------------------------------
def test_rp01_work_under_three_times_the_setup_is_refused_and_missing_numbers_are_asked_for():
    assert B.rp01(30, 10) == [] and B.rp01(29, 10) and "merge this job" in B.rp01(29, 10)[0]
    assert "--work-min" in B.rp01(None, 10)[0] and "--setup-min" in B.rp01(30, None)[0]
    assert B.rp01(None, None, test="p12a_smoke") == []                                      # the smoke pods measure setup itself
    assert B.rp01(None, None, measure=True, max_usd=0.3) == [] and "0.3" in B.rp01(None, None, measure=True, max_usd=0.5)[0]


def test_create_refuses_a_pod_that_breaks_rp01_and_names_the_disk(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    live = FakeLive(age=60)
    with pytest.raises(SystemExit, match="RP-01: planned work 20 min is under 3 x the fixed setup 10 min"):
        _create(api, tmp, NEW_SH, "--work-min", "20", "--setup-min", "10", live=live)
    with pytest.raises(SystemExit, match="state the job's planned GPU work"):
        R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(tmp / "run.json"), "--script", str(tmp / "job.sh"),
                "--script-url", "https://x/pod.sh", "--disk", "40"], api=api, live=live)
    with pytest.raises(SystemExit, match="--disk GB is required"):
        R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(tmp / "run.json"), "--script", str(tmp / "job.sh"),
                "--script-url", "https://x/pod.sh", "--work-min", "60", "--setup-min", "10"], api=api, live=live)
    assert not fake.pods


def test_a_script_pod_has_no_volume_no_ports_and_the_stated_disk_while_a_boot_pod_keeps_its_old_shape(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    seen = []
    real = R.create
    monkeypatch.setattr(R, "create", lambda api, body, **kw: seen.append(body) or real(api, body, **kw))
    _create(api, tmp, NEW_SH, live=FakeLive(age=60))
    body = seen[0]
    assert body["mounts"] == {} and body["ports"] == [] and body["disk"] == 40 and not B.rp03(body)   # RP-03: no network volume either
    old = R.create_body("n", boot="cloud/x.json")
    assert old["ports"] and old["mounts"]["persistent"]["size"] == R.VOLUME_GB                          # TMR manifests keep theirs
    assert B.rp03({"networkVolumeId": "v1", "mounts": {}}) and B.rp03({"mounts": {"network": {"id": "v"}}})


def test_rp02_a_second_pod_on_the_same_weights_needs_a_reason_and_the_ledger_remembers_the_first(env, monkeypatch):
    assert B.rp02(["Qwen/Qwen-Image-2.1"], [["Qwen/Qwen-Image-2.1"]]) and "ONE pod" in B.rp02(["Qwen/Qwen-Image-2.1"], [["Qwen/Qwen-Image-2.1"]])[0]
    assert B.rp02(["a/b"], [["c/d"]]) == [] and B.rp02([], [[]]) == [] and B.rp02(["a/b"], [["a/b"]], reason="re-run after a bad host") == []
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    script = NEW_SH + 'python - <<PY\nfrom huggingface_hub import snapshot_download as s\ns("Qwen/Qwen-Image-2.1")\nPY\n'
    _create(api, tmp, script, live=FakeLive(age=60), usd="0.3")
    plans = Run.open(tmp / "run.json").data["items"]["pod_plans"]
    assert list(plans.values())[0]["weights"] == ["Qwen/Qwen-Image-2.1"]
    fake.pods.clear()                                                                        # the first pod is gone: the account is clean
    with pytest.raises(SystemExit, match="RP-02"):
        _create(api, tmp, script, live=FakeLive(age=60), usd="0.3")
    _create(api, tmp, script, "--second-pod-reason", "the first pod hit a bad host", live=FakeLive(age=60), usd="0.3")
    assert len(Run.open(tmp / "run.json").data["items"]["pod_plans"]) == 2


def test_rp10_one_hardware_retry_and_no_paid_retry_of_a_script_that_failed():
    assert B.rp10(1, False) == [] and "one retry is used" in B.rp10(2, False, key="j")[0]
    assert "dryrun" in B.rp10(0, True)[0]


def test_create_counts_a_failed_create_as_a_hardware_try_and_stops_after_the_retry(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    fake.faults = [("POST", "/pods", 400)] * 2
    for _ in range(2):
        with pytest.raises(R.RunPodError):
            _create(api, tmp, NEW_SH, "--job", "j1", live=FakeLive(age=60))
    assert len(Run.open(tmp / "run.json").data["failures"]["hw:j1"]) == 2
    with pytest.raises(SystemExit, match="RP-10: 2 failed create or BAD_HOST"):
        _create(api, tmp, NEW_SH, "--job", "j1", live=FakeLive(age=60))
    assert not fake.pods


# --- cost, settle, ledger ----------------------------------------------------------------------------------------------------
def test_cost_needs_a_pod_id(env):
    fake, api, _ = env
    with pytest.raises(SystemExit, match="cost needs the pod id"):
        R.main(["cost"], api=api)


def _closed_session(tmp, closed, **extra):
    ledger = tmp / "run.json"
    run = Run.open(ledger, caps={"runpod_usd": 3.0})
    run.reserve("runpod_usd", 0.5, item="pod:a")
    sess = R.new_session(pod("a"), max_usd=1.0, max_hours=2.0, now=0, ledger=str(ledger), heartbeat="datasets/o/r:run/out/beat.txt",
                         extra={"gpu": "NVIDIA A40", "cloud": "COMMUNITY", "job_base": "jb", "script_sha": "ab" * 32, **extra})
    sess.update(closed=closed)
    R.sess_write(sess)
    return ledger


def test_cost_settles_into_the_ledger_writes_the_speed_row_and_the_progress_line(env):
    fake, api, tmp = env
    ledger = _closed_session(tmp, closed=100)
    fake.billing = [{"totalAmount": 0.30, "podId": "a"}]
    files = {"beat.txt": "BOOT key=200 job=j pod=a price=0.3 deadline=9\nDONE rc=0 2026-10-30T01:00:00Z progress=ok upload_fail=0 unstored=0\n",
             "units.json": json.dumps({"job_type": "keyframes", "units": 100, "work_s": 4500, "setup_s": 600, "mb": 3000, "download_s": 60})}
    res = R.cost_report(api, "a", fetch=lambda url: files[url.rsplit("/", 1)[1]], now=500)
    assert res["usd"] == 0.3 and res["word"] == "DONE" and "$0.30 billed, $0.0030/unit (keyframes x100)" in res["line"]
    row = S.row("keyframes", "NVIDIA A40")
    assert row["s_per_unit"] == 45 and row["setup_min"] == 10 and row["mb_per_s"] == {"COMMUNITY": 50.0} and row["usd_per_unit"] == 0.003
    item = Run.open(ledger).data["items"]["pods"]["a"]
    assert item["usd_per_unit"] == 0.003 and item["units"] == 100 and Run.open(ledger).spent("runpod_usd") == 0.3
    assert json.loads((R.RP / "settled.jsonl").read_text().splitlines()[0])["pod"] == "a"


@pytest.mark.parametrize("units", ["[]", "null", "5", '{"job_type": "keyframes", "units": "abc", "work_s": 60}', "{broken"])
def test_a_garbled_units_json_never_keeps_the_bill_out_of_the_ledger(env, units):
    fake, api, tmp = env
    ledger = _closed_session(tmp, closed=100)
    fake.billing = [{"totalAmount": 0.30, "podId": "a"}]
    files = {"beat.txt": "BOOT key=200 job=j pod=a price=0.3 deadline=9\nDONE rc=0 2026-10-30T01:00:00Z progress=ok upload_fail=0 unstored=0\n",
             "units.json": units}
    res = R.cost_report(api, "a", fetch=lambda url: files[url.rsplit("/", 1)[1]], now=500)
    assert res["usd"] == 0.3 and "no speed row: units.json" in res["speed"] and "/unit" not in res["line"]
    assert Run.open(ledger).spent("runpod_usd") == 0.3 and R.sess_read("a")["settled"]   # the real bill replaced the reservation
    assert S.row("keyframes", "NVIDIA A40") is None                                    # and no row was written from garbage


def test_the_session_hook_survives_whatever_settle_due_raises(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.setattr(R, "api_key", lambda: "k")
    monkeypatch.setattr(R, "Api", lambda **kw: api)
    monkeypatch.setattr(R, "settle_due", lambda *a, **k: (_ for _ in ()).throw(AttributeError("boom")))
    res = H._check()
    assert res is not None and any("settle check failed (AttributeError" in i for i in res["info"])


def test_a_settled_pod_stays_settled_after_its_outcome_is_recorded(env):
    fake, api, tmp = env
    ledger = _closed_session(tmp, closed=100)
    fake.billing = [{"totalAmount": 0.2, "podId": "a"}]
    beat = lambda url: ("BOOT key=200 job=j pod=a price=0.3 deadline=9\nDONE rc=0 2026-10-30T01:00:00Z progress= upload_fail=0 unstored=0\n"
                        if url.endswith("beat.txt") else "")  # noqa: E731
    R.cost_report(api, "a", fetch=beat, now=500)
    s = R.sess_read("a")
    assert s["outcome_recorded"] == "DONE" and s["settled"] and s["billed_usd"] == 0.2
    assert R.settle_due(api, now=100 + 200 * 60, fetch=beat) == []                     # not settled a second time next session


def test_the_pods_outcome_feeds_the_retry_rule_once(env):
    fake, api, tmp = env
    ledger = _closed_session(tmp, closed=100)
    beat = lambda w: lambda url: ("BOOT key=200 job=j pod=a price=0.3 deadline=9\n" + f"{w} rc=1 2026-10-30T01:00:00Z progress= upload_fail=0 unstored=0\n"
                                  if url.endswith("beat.txt") else "")  # noqa: E731
    R.cost_report(api, "a", fetch=beat("BAD_HOST"), now=500)
    R.cost_report(api, "a", fetch=beat("BAD_HOST"), now=600)                               # a second cost: not counted twice
    assert len(Run.open(ledger).data["failures"]["hw:jb"]) == 1
    sess = R.sess_read("a")
    sess.pop("outcome_recorded")
    R.sess_write(sess)
    R.cost_report(api, "a", fetch=beat("FAILED"), now=700)
    assert len(Run.open(ledger).data["failures"][f"script:jb:{'ab' * 6}"]) == 1


def test_settle_due_settles_a_pod_ninety_minutes_after_its_stop_and_not_before(env):
    fake, api, tmp = env
    ledger = _closed_session(tmp, closed=1000)
    fake.billing = [{"totalAmount": 0.2, "podId": "a"}]
    assert R.settle_due(api, now=1000 + 89 * 60, fetch=lambda u: "") == [] and Run.open(ledger).spent("runpod_usd") == 0.5   # still the reservation
    lines = R.settle_due(api, now=1000 + 91 * 60, fetch=lambda u: "")
    assert len(lines) == 1 and "$0.20 billed" in lines[0] and Run.open(ledger).spent("runpod_usd") == 0.2
    assert R.settle_due(api, now=1000 + 200 * 60, fetch=lambda u: "") == []                    # settled once


def test_the_session_hook_settles_due_pods_and_says_so(env, monkeypatch):
    fake, api, tmp = env
    _closed_session(tmp, closed=1)
    fake.billing = [{"totalAmount": 0.2, "podId": "a"}]
    monkeypatch.setattr(R, "api_key", lambda: "k")
    monkeypatch.setattr(R, "Api", lambda **kw: api)
    monkeypatch.setattr(R, "hf_text", lambda spec, fetch=None: "")
    res = H._check()
    assert any(i.startswith("settled: pod a") for i in res["info"])


def test_the_ledger_stops_at_eighty_percent_of_what_was_really_billed(tmp_path):
    run = Run.open(tmp_path / "run.json", caps={"runpod_usd": 1.0})
    run.reserve("runpod_usd", 0.7, item="pod:a")
    with pytest.raises(CapReached):
        run.reserve("runpod_usd", 0.2, item="pod:b")                                   # 0.9 > 0.8 of the reservation
    run.settle("runpod_usd", "pod:a", 0.2)                                             # the bill was 0.2
    run.reserve("runpod_usd", 0.5, item="pod:b")                                       # 0.2 + 0.5 <= 0.8: allowed now
    rep = run.report()
    assert rep["settled"] == {"runpod_usd": 0.2} and rep["reserved_open"] == {"runpod_usd": 0.5} and rep["spent"] == {"runpod_usd": 0.7}


# --- check and start ---------------------------------------------------------------------------------------------------------
def test_check_prints_the_stored_disks_on_one_line_and_names_dead_keep_ids(env, monkeypatch):
    fake, api, _ = env
    fake.pods["s1"] = pod("s1", status="EXITED", volumeInGb=100)
    fake.pods["s2"] = pod("s2", status="EXITED", volumeInGb=50)
    real = R.spend_caps.runpod()
    monkeypatch.setattr(R.spend_caps, "runpod", lambda: {**real, "keep_stopped_pods": ["s1", "s2", "gone1"]})
    res = R.check(api)
    assert any(i.startswith("stopped pods keep 150 GB of volume: $") and i.endswith("over 2 pod(s)") for i in res["info"])
    assert any("keep_stopped_pods no longer exist" in i and "gone1" in i for i in res["info"])


def test_check_flags_billing_that_no_pod_and_no_volume_explains(env, monkeypatch):
    fake, api, _ = env
    monkeypatch.setattr(api, "balance", lambda: {"clientBalance": 5.0, "currentSpendPerHr": 0.31})
    res = R.check(api)
    assert any("RunPod says it spends $0.310/h now" in p for p in res["problems"])
    fake.pods["l"] = pod("l")
    R.sess_write({**_session("l"), "closed": None})
    assert not any("spends" in p for p in R.check(api)["problems"])


def test_start_refuses_a_stopped_pod_by_default(env):
    fake, api, _ = env
    fake.pods["a"] = pod("a", status="EXITED")
    with pytest.raises(SystemExit, match="zero GPUs") as e:
        R.main(["start", "a", "--yes", "--max-usd", "0.5", "--max-hours", "1"], api=api)
    assert "--allow-zero-gpu-risk" in str(e.value) and fake.pods["a"]["status"] == "EXITED"
