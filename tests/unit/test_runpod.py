"""The pod manager against a fake RunPod API: no network, no pod, no money."""
import json

import pytest

from explainer_engine.cloud import runpod as R
from explainer_engine.core.ledger import CapReached, Run


class FakeRunPod:
    """Pods in a dict; ``faults`` is a list of (method, path-prefix, what) consumed in order: what = an HTTP status, or
    "timeout" (no answer), or "timeout-after" (the request happened, the answer was lost)."""

    def __init__(self, pods=(), stop_takes=0):
        self.pods = {p["id"]: dict(p) for p in pods}
        self.calls, self.faults, self.stop_takes, self.n = [], [], stop_takes, 0
        self.billing = []

    def __call__(self, method, url, body, headers, timeout):
        path = url.split("runpod.io", 1)[-1].replace("/v1", "", 1) if "runpod.io" in url else url
        self.calls.append((method, path))
        for i, (m, pre, what) in enumerate(self.faults):
            if m == method and path.startswith(pre):
                self.faults.pop(i)
                if what == "timeout":
                    raise TimeoutError("timed out")
                if what == "timeout-after":
                    self._handle(method, path, body)
                    raise TimeoutError("timed out")
                return what, "boom"
        return self._handle(method, path, body)

    def _handle(self, method, path, body):
        data = json.loads(body) if body else None
        if path == "/graphql":
            q = data["query"]
            if "myself" in q:
                return 200, json.dumps({"data": {"myself": {"clientBalance": 1.0}}})
            pid = q.split('"')[1]
            if "podStop" in q and pid in self.pods:
                self.pods[pid]["desiredStatus"] = "EXITED"
            if "podTerminate" in q:
                self.pods.pop(pid, None)
            return 200, json.dumps({"data": {}})
        if path.startswith("/billing/pods"):
            return 200, json.dumps(self.billing)
        if path.startswith("/pods?") or path == "/pods":
            if method == "POST":
                self.n += 1
                pid = f"p{self.n}"
                self.pods[pid] = {"id": pid, "name": data["name"], "desiredStatus": "RUNNING", "costPerHr": 0.89,
                                  "volumeInGb": data["volumeInGb"], "containerDiskInGb": data["containerDiskInGb"]}
                return 201, json.dumps(self.pods[pid])
            name = path.split("name=")[1] if "name=" in path else None
            return 200, json.dumps([p for p in self.pods.values() if name is None or p["name"] == name])
        parts = path.split("/")  # "", "pods", id, [action]
        pid = parts[2]
        if pid not in self.pods:
            return 404, "not found"
        if method == "GET":
            return 200, json.dumps(self.pods[pid])
        if method == "DELETE":
            del self.pods[pid]
            return 200, ""
        if parts[3] == "stop":
            if self.stop_takes:
                self.stop_takes -= 1
            else:
                self.pods[pid]["desiredStatus"] = "EXITED"
            return 200, ""
        if parts[3] == "start":
            self.pods[pid]["desiredStatus"] = "RUNNING"
            return 200, ""
        return 400, "?"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    fake = FakeRunPod()
    api = R.Api("k", transport=fake, sleep=lambda s: None)
    return fake, api


def pod(pid="a", name="ee-x-until-9999999999", status="RUNNING", price=0.89, **kw):
    return {"id": pid, "name": name, "desiredStatus": status, "costPerHr": price, "volumeInGb": 150,
            "containerDiskInGb": 80, **kw}


def test_reads_retry_on_429_and_5xx_and_lost_connections(env):
    fake, api = env
    fake.pods["a"] = pod()
    fake.faults = [("GET", "/pods/a", 429), ("GET", "/pods/a", 502), ("GET", "/pods/a", "timeout")]
    assert api.pod("a")["id"] == "a"
    assert len(fake.calls) == 4


def test_a_client_error_is_not_retried_and_404_means_gone(env):
    fake, api = env
    assert api.pod("nope") is None
    fake.pods["a"] = pod()
    fake.faults = [("GET", "/pods/a", 401)]
    with pytest.raises(R.RunPodError, match="401"):
        api.pod("a")
    assert len(fake.calls) == 2


def test_create_is_never_posted_twice_when_the_answer_is_lost(env):
    fake, api = env
    body = R.create_body("ee-default-abc-until-9999999999")
    fake.faults = [("POST", "/pods", "timeout-after")]
    got = R.create(api, body, max_price=0.95, sleep=lambda s: None)
    assert got["id"] == "p1" and len(fake.pods) == 1
    assert [c for c in fake.calls if c[0] == "POST"] == [("POST", "/pods")]


def test_create_after_a_lost_request_that_never_happened_bills_nothing(env):
    fake, api = env
    fake.faults = [("POST", "/pods", "timeout")]
    with pytest.raises(R.RunPodError, match="nothing is billing"):
        R.create(api, R.create_body("ee-x-until-9999999999"), max_price=0.95, sleep=lambda s: None)
    assert not fake.pods and [c for c in fake.calls if c[0] == "POST"] == [("POST", "/pods")]


def test_create_reposts_only_after_a_429(env):
    fake, api = env
    fake.faults = [("POST", "/pods", 429)]
    assert R.create(api, R.create_body("ee-x-until-9999999999"), max_price=0.95, sleep=lambda s: None)["id"] == "p1"
    assert len(fake.pods) == 1


def test_a_card_over_the_ceiling_is_deleted_at_once(env):
    fake, api = env
    with pytest.raises(R.RunPodError, match="over the"):
        R.create(api, R.create_body("ee-x-until-9999999999"), max_price=0.5)
    assert not fake.pods


def test_stop_is_idempotent_and_verified(env):
    fake, api = env
    fake.pods["a"] = pod()
    assert R.stop(api, "a") == "EXITED"
    n = len(fake.calls)
    assert R.stop(api, "a") == "EXITED" and ("POST", "/pods/a/stop") not in fake.calls[n:]  # already stopped: no call
    assert R.stop(api, "gone") == "GONE"


def test_a_stop_that_does_not_take_falls_back_to_graphql(env):
    fake, api = env
    fake.pods["a"] = pod()
    fake.stop_takes = 10**6  # REST answers 200 but the pod keeps running
    clock = iter(range(0, 10**6, 50)).__next__
    assert R.stop(api, "a", timeout=100, clock=clock, sleep=lambda s: None) == "EXITED"
    assert ("POST", "/graphql") in fake.calls


def test_stop_raises_when_nothing_stops_the_pod(env, monkeypatch):
    fake, api = env
    fake.pods["a"] = pod()
    fake.stop_takes = 10**6
    monkeypatch.setattr(api, "graphql", lambda q: {})
    clock = iter(range(0, 10**6, 50)).__next__
    with pytest.raises(R.RunPodError, match="still running"):
        R.stop(api, "a", timeout=100, clock=clock, sleep=lambda s: None)


def test_sweep_stops_expired_lists_stopped_disks_and_survives_a_failure(env):
    fake, api = env
    fake.pods = {"ok": pod("ok"), "old": pod("old", "ee-x-until-100"), "noname": pod("noname", "my pod"),
                 "ex": pod("ex", "ee-x-until-100", "EXITED", volumeInGb=60)}
    fake.faults = [("POST", "/pods/old/stop", 400)]
    rows = R.sweep(api, now=1000)
    assert fake.pods["noname"]["desiredStatus"] == "EXITED" and fake.pods["ok"]["desiredStatus"] == "RUNNING"
    assert len(rows["stopped"]) == 2  # old (graphql after the REST 400) and noname
    assert rows["exited"] == ["ex ee-x-until-100: disk 60 GB = $0.39/day"] and "ex" in fake.pods  # never deleted unasked
    rows = R.sweep(api, now=1000, delete_exited=True)
    assert "ex" not in fake.pods and rows["deleted"]


def test_the_cli_refuses_without_the_creators_word(env):
    fake, api = env
    fake.pods["a"] = pod()
    for argv in (["create", "--max-usd", "1", "--max-hours", "1"], ["create", "--yes"], ["delete", "a"],
                 ["sweep", "--delete"], ["start", "a", "--yes"]):
        with pytest.raises(SystemExit):
            R.main(argv, api=api)
    assert fake.pods["a"]["desiredStatus"] == "RUNNING" and len(fake.pods) == 1


def test_create_cli_reserves_in_the_ledger_writes_a_session_and_names_the_lifetime(env, tmp_path, monkeypatch):
    fake, api = env
    monkeypatch.setattr(R, "guard_detached", lambda pid: 4242)
    monkeypatch.setattr(R, "live_guard", lambda pid: True)
    ledger = tmp_path / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "0.75", "--boot", "cloud/x.json", "--ledger", str(ledger)], api=api)
    sess = R.sess_read("p1")
    assert sess["max_usd"] == 0.5 and sess["status_token"] and sess["until"] == R.until_of(fake.pods["p1"]["name"])
    assert Run.open(ledger).data["reserved"]["pod:p1"]["amount"] == 0.5
    body_cmd = fake.pods["p1"]["name"]
    assert R.until_of(body_cmd) and not R.expired(body_cmd)
    with pytest.raises(SystemExit, match="per_pod_usd"):  # the creator's ceiling, config/spend_caps.json
        R.main(["create", "--yes", "--max-usd", "2.0", "--max-hours", "1", "--ledger", str(ledger)], api=api)
    with pytest.raises(CapReached):  # 0.5 + 0.4 passes 80 % of the episode's $1
        R.main(["create", "--yes", "--max-usd", "0.4", "--max-hours", "1", "--ledger", str(ledger)], api=api)
    with pytest.raises(SystemExit, match="--ledger"):
        R.main(["create", "--yes", "--max-usd", "0.1", "--max-hours", "1"], api=api)
    assert len(fake.pods) == 1


def test_a_failed_boot_stops_the_pod_and_pid1_stays_alive():
    cmd = R.boot_cmd("cloud/stages_pictures.json", "main")[2]
    assert cmd.startswith("set -o pipefail;") and "/stop" in cmd and "-X DELETE" not in cmd
    assert cmd.rstrip().endswith("tail -f /dev/null")


def _session(pid="a", **kw):
    p = pod(pid)
    sess = R.new_session(p, max_usd=1.0, max_hours=2.0, now=0, **kw)
    sess["answered"] = True
    return R.sess_write(sess)


def test_guard_check_caps_lifetime_boot_and_conductor(env):
    sess = _session()
    running = pod()
    assert R.guard_check(sess, None, 10)[0] == "end"
    assert R.guard_check(sess, pod(status="EXITED"), 10)[0] == "end"
    assert R.guard_check(sess, running, 60)[0] == "ok"
    assert "money cap" in R.guard_check(sess, running, 3600 * 1.1)[1]  # 0.89 + disk ~0.03 $/h
    assert "time cap" in R.guard_check({**sess, "max_usd": 99}, running, 7300)[1]
    assert "lifetime" in R.guard_check({**sess, "until": 100}, running, 101)[1]
    assert "boot" in R.guard_check({**sess, "answered": False}, running, 601)[1]
    assert R.guard_check({**sess, "ended": 50}, running, 100, "STATUS DONE")[0] == "ok"
    assert "conductor" in R.guard_check({**sess, "ended": 50}, running, 200, "STATUS DONE")[1]


def test_the_money_clock_counts_compute_and_disk():
    sess = _session()
    assert R.spent_estimate(sess, 3600, pod()) == pytest.approx(0.89 + 230 * 0.10 / 730, abs=1e-4)
    assert R.disk_per_hour(pod(volumeInGb=60), running=False) * 24 == pytest.approx(0.3945, abs=1e-3)


def test_guard_stops_at_the_cap_keeps_the_disk_and_says_what_it_costs(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()
    pushes = []
    t = iter(range(0, 10**7, 600)).__next__
    why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: pushes.append(a), page=lambda *a: "", log=lambda *a: None)
    assert "money cap" in why and fake.pods["a"]["desiredStatus"] == "EXITED"
    assert any("/day until deleted" in p[1] for p in pushes)
    assert R.sess_read("a")["close_status"] == "EXITED"


def test_guard_deletes_only_with_the_creators_on_cap_delete(env):
    fake, api = env
    fake.pods["a"] = pod()
    R.sess_write({**_session(), "on_cap": "delete"})
    t = iter(range(0, 10**7, 600)).__next__
    R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: None, page=lambda *a: "", log=lambda *a: None)
    assert "a" not in fake.pods


def test_a_blind_guard_keeps_its_money_clock_and_still_stops(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()
    fake.faults = [("GET", "/pods/a", 503)] * 5 * 6  # five looks without an answer (each look retries 4 times)
    pushes = []
    t = iter(range(0, 10**7, 900)).__next__
    why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: pushes.append(a), page=lambda *a: "", log=lambda *a: None)
    assert "money cap" in why and fake.pods["a"]["desiredStatus"] == "EXITED"
    assert any(p[0] == "Guard is blind" for p in pushes)


def test_a_guard_restarted_after_a_container_restart_keeps_the_session_clock(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()  # started at t=0; the guard process (and the session's container) restarted much later
    t = iter([4000] + list(range(4000, 10**7, 30))).__next__
    why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: None, page=lambda *a: "", log=lambda *a: None)
    assert "money cap" in why  # 4000 s at ~$0.92/h > $1: the clock did not restart with the process


def test_wait_ready_needs_ports_and_times_out(env):
    fake, api = env
    fake.pods["a"] = pod()
    clock = iter(range(0, 10**6, 100)).__next__
    with pytest.raises(TimeoutError):
        R.wait_ready(api, "a", timeout=300, clock=clock, sleep=lambda s: None)
    fake.pods["a"].update(publicIp="1.2.3.4", portMappings={"22": 40022})
    assert R.wait_ready(api, "a", timeout=300, clock=clock, sleep=lambda s: None)["publicIp"] == "1.2.3.4"


def test_pod_session_stops_the_pod_on_an_error(env):
    fake, api = env
    fake.pods["a"] = pod()
    with pytest.raises(ValueError):
        with R.PodSession(api, "a"):
            raise ValueError("painter crashed")
    assert fake.pods["a"]["desiredStatus"] == "EXITED"


def test_cost_settles_the_reservation_with_the_billed_amount(env, tmp_path):
    fake, api = env
    ledger = tmp_path / "run.json"
    run = Run.open(ledger, caps={"runpod_usd": 3.0})
    run.reserve("runpod_usd", 0.5, item="pod:a")
    R.sess_write({**_session(), "ledger": str(ledger)})
    fake.billing = [{"amount": 0.12, "timeBilledMs": 480000, "podId": "a"}, {"amount": 0.08, "timeBilledMs": 300000, "podId": "a"}]
    assert R.settle(api, "a") == (0.2, 780)
    run = Run.open(ledger)
    assert run.spent("runpod_usd") == 0.2 and run.data["items"]["pods"]["a"]["billed_s"] == 780
    fake.billing.append({"amount": 0.01, "timeBilledMs": 1000, "podId": "a"})  # the newest hour grew: settle again
    R.settle(api, "a")
    assert Run.open(ledger).spent("runpod_usd") == 0.21


def test_create_is_refused_past_the_24h_billing_the_balance_or_with_a_stray_disk(env):
    fake, api = env
    ok = dict(max_usd=0.5, max_hours=1.0, gpu="default", now=10**6)
    assert R.preflight_create(api, **ok) == []
    assert any("max_hours_per_pod" in w for w in R.preflight_create(api, **{**ok, "max_hours": 3}))
    fake.billing = [{"amount": 1.2, "podId": "old"}]  # stopped disks count: RunPod bills them per pod
    assert any("per_24h_usd" in w for w in R.preflight_create(api, **ok))
    fake.billing = []
    fake.pods["ex"] = pod("ex", "x", "EXITED", volumeInGb=60)
    assert any("clean up first: ex" in w for w in R.preflight_create(api, **ok))
    assert R.preflight_create(api, **ok, ignore="ex") == []  # starting that very pod again


def test_check_flags_stopped_disks_unless_the_creator_keeps_them(env, tmp_path, monkeypatch):
    fake, api = env
    fake.pods = {"ex": pod("ex", "x", "EXITED", volumeInGb=60), "run": pod("run", "ee-x-until-100")}
    res = R.check(api, now=1000)
    assert len(res["problems"]) == 2 and "$0.39/day" in res["problems"][0]
    caps = json.loads(R.spend_caps.PATH.read_text())
    caps["runpod"]["keep_stopped_pods"] = ["ex"]
    (tmp_path / "caps.json").write_text(json.dumps(caps))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(tmp_path / "caps.json"))
    assert len(R.check(api, now=1000)["problems"]) == 1


def test_the_ledger_refuses_a_cap_above_the_creators_ceiling_and_fills_missing_ones(tmp_path):
    from explainer_engine.core.spend_caps import OverCeiling
    with pytest.raises(OverCeiling):
        Run.open(tmp_path / "a.json", caps={"runpod_usd": 50.0})
    assert Run.open(tmp_path / "b.json", caps={"gemini_usd": 2.0}).data["caps"] == {"gemini_usd": 2.0, "runpod_usd": 3.0}


def test_hooks_block_bypasses_and_a_turn_that_leaves_a_stray(env, monkeypatch, capsys):
    from explainer_engine.cloud import hooks as H
    fake, api = env
    for cmd in ("python cloud/rp.py create --yes --gpu big", "bash -c 'cd tmr && python cloud/rp.py start'",
                'curl -X POST https://rest.runpod.io/v1/pods -d @b.json', 'curl https://rest.runpod.io/v1/pods -X POST',
                "curl -X POST https://rest.runpod.io/v1/pods/abc/start"):
        assert H.pre_bash({"tool_input": {"command": cmd}}) == 2, cmd
    for cmd in ("python -m explainer_engine.cloud.runpod create --yes --max-usd 0.5", "curl -X POST https://rest.runpod.io/v1/pods/abc/stop",
                "python cloud/rp.py sweep", "pytest -q tests/unit/test_runpod.py"):
        assert H.pre_bash({"tool_input": {"command": cmd}}) == 0, cmd
    monkeypatch.setattr(H, "_check", lambda: R.check(api, now=1000))
    assert H.stop({}) == 0
    fake.pods["ex"] = pod("ex", "x", "EXITED")
    assert H.stop({}) == 2 and "ex x STOPPED" in capsys.readouterr().err
    assert H.stop({"stop_hook_active": True}) == 0  # never a loop
    H.session_start()
    assert "PROBLEM ex" in capsys.readouterr().out


def test_the_money_hooks_are_wired_into_the_session_settings(monkeypatch):
    from explainer_engine.cloud import hooks as H
    settings = json.loads((R.ROOT / ".claude" / "settings.json").read_text())["hooks"]
    commands = json.dumps(settings)
    for what in ("session-start", "stop", "pre-bash"):
        assert f"explainer_engine.cloud.hooks {what}" in commands
    assert "SessionStart" in settings and "Stop" in settings
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    monkeypatch.setattr(R, "RP", R.ROOT / "no-such-dir")
    assert H._check() is None and H.stop({}) == 0  # no key: report nothing, never block
