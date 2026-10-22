"""The pod manager against a fake RunPod API (REST v2 shape): no network, no pod, no money."""
import json

import pytest

from explainer_engine.cloud import runpod as R
from explainer_engine.core.ledger import CapReached, Run


class FakeRunPod:
    """Pods in a dict, in RunPod's v2 shape (``status``, ``cost``, ``disk``, ``mounts``, ``runtime`` only while RUNNING);
    ``faults`` is a list of (method, path-prefix, what) consumed in order: what = an HTTP status, or "timeout" (no answer),
    or "timeout-after" (the request happened, the answer was lost). ``page_size`` splits ``GET /pods`` into pages."""

    def __init__(self, pods=(), stop_takes=0, page_size=1000):
        self.pods = {p["id"]: dict(p) for p in pods}
        self.calls, self.faults, self.stop_takes, self.n = [], [], stop_takes, 0
        self.billing, self.page_size, self.refuse_gpus, self.new_status = [], page_size, set(), "RUNNING"
        self.volumes, self.global_volumes, self.endpoints, self.other_billing = [], [], [], 0.0
        self.headers = {}  # response headers for the next answers (Retry-After)

    def __call__(self, method, url, body, headers, timeout):
        path = url.split("runpod.io", 1)[-1].replace("/v2", "", 1) if "runpod.io" in url else url
        self.calls.append((method, path))
        for i, (m, pre, what) in enumerate(self.faults):
            if m == method and path.startswith(pre):
                self.faults.pop(i)
                if what == "timeout":
                    raise TimeoutError("timed out")
                if what == "timeout-after":
                    self._handle(method, path, body)
                    raise TimeoutError("timed out")
                return what, "boom", dict(self.headers)
        return self._handle(method, path, body)

    def _handle(self, method, path, body):
        data = json.loads(body) if body else None
        if path == "/graphql":
            q = data["query"]
            if "myself" in q:
                return 200, json.dumps({"data": {"myself": {"clientBalance": 1.0}}})
            pid = q.split('"')[1]
            if "podStop" in q and pid in self.pods:
                self.pods[pid]["status"] = "EXITED"
            if "podTerminate" in q:
                self.pods.pop(pid, None)
            return 200, json.dumps({"data": {}})
        if path.startswith("/billing/pods"):
            return 200, json.dumps({"records": self.billing, "metadata": {}})
        if path.startswith("/billing?"):  # the aggregate: every resource of the account
            total = sum(float(r.get("totalAmount") or 0) for r in self.billing) + self.other_billing
            return 200, json.dumps({"records": [], "metadata": {"totals": {"totalAmount": total}, "recordCount": 0}})
        if path.startswith("/network-volumes?"):
            return 200, json.dumps({"networkVolumes": self.volumes, "pagination": {"nextCursor": None, "hasNextPage": False}})
        if path.startswith("/network-volumes/") and method == "DELETE":
            vid = path.split("/")[2]
            self.volumes = [v for v in self.volumes if v["id"] != vid]
            return 204, ""
        if path.startswith("/global-volumes?"):
            return 200, json.dumps({"globalVolumes": self.global_volumes, "pagination": {"nextCursor": None, "hasNextPage": False}})
        if path.startswith("/serverless?"):
            return 200, json.dumps({"endpoints": self.endpoints, "pagination": {"nextCursor": None, "hasNextPage": False}})
        if path.startswith("/pods?") or path == "/pods":
            if method == "POST":
                if data["gpu"]["id"] in self.refuse_gpus:
                    return 400, json.dumps({"error": "no capacity"})
                self.n += 1
                pid = f"p{self.n}"
                self.pods[pid] = pod(pid, data["name"], self.new_status, gpu=data["gpu"]["id"], volumeInGb=data["mounts"]["persistent"]["size"],
                                     containerDiskInGb=data["disk"])
                if self.new_status == "PROVISIONING":
                    self.pods[pid]["cost"] = 0.0
                return 201, json.dumps(self.pods[pid])
            rows = list(self.pods.values())
            start = int(path.split("cursor=")[1].split("&")[0]) if "cursor=" in path else 0
            page = rows[start:start + self.page_size]
            more = start + self.page_size < len(rows)
            return 200, json.dumps({"pods": page, "pagination": {"nextCursor": str(start + self.page_size) if more else None,
                                                                  "hasNextPage": more}})
        parts = path.split("/")  # "", "pods", id, [action|logs]
        pid = parts[2]
        if pid not in self.pods:
            return 404, "not found"
        if method == "GET":
            return 200, json.dumps(self.pods[pid])
        if method == "DELETE":
            del self.pods[pid]
            return 204, ""
        if parts[3] == "action":
            what = data["action"]
            if what == "stop":
                if self.stop_takes:
                    self.stop_takes -= 1
                else:
                    self.pods[pid]["status"] = "EXITED"
                    self.pods[pid]["runtime"] = None
                    self.pods[pid]["cost"] = 0.0
            elif what == "start":
                self.pods[pid]["status"] = "RUNNING"
                self.pods[pid]["cost"] = 0.89
            elif what == "terminate":
                del self.pods[pid]
            return 200, json.dumps(self.pods.get(pid) or {})
        return 400, "?"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    fake = FakeRunPod()
    api = R.Api("k", transport=fake, sleep=lambda s: None)
    return fake, api


def pod(pid="a", name="ee-x-until-9999999999", status="RUNNING", price=0.89, volumeInGb=150, containerDiskInGb=80,
        gpu="NVIDIA GeForce RTX 4090", ports=None, ip=None, util=None):
    """A pod as v2 answers it."""
    runtime = None
    if status == "RUNNING":
        runtime = {"uptime": 120, "gpus": [{"id": "GPU-1", "util": util or 0, "memoryUtil": 0}], "cpu": {"util": 1}, "memory": {"util": 1},
                   "ports": [{"private": int(k), "public": v, "type": "tcp", "ip": ip} for k, v in (ports or {}).items()]}
    return {"id": pid, "name": name, "status": status, "cost": price if status in ("RUNNING", "PROVISIONING", "STARTING") else 0.0,
            "disk": containerDiskInGb, "mounts": {"persistent": {"size": volumeInGb, "path": "/workspace"}},
            "gpu": {"id": gpu, "count": 1}, "startedAt": "2026-10-22T08:00:00Z", "runtime": runtime}


def test_norm_turns_a_v2_pod_into_the_flat_record():
    p = R.norm(pod(ports={"22": 40022, "8888": 48888}, ip="1.2.3.4", util=77))
    assert p["status"] == "RUNNING" and p["costPerHr"] == 0.89 and p["volumeInGb"] == 150 and p["containerDiskInGb"] == 80
    assert p["publicIp"] == "1.2.3.4" and p["portMappings"] == {"22": 40022, "8888": 48888} and p["util"] == 77 and p["uptime"] == 120
    q = R.norm(pod(status="EXITED"))
    assert q["costPerHr"] == 0.0 and q["portMappings"] is None and q["publicIp"] is None and q["util"] is None
    assert R.norm(p) is p and R.norm(None) is None  # flat records and None pass through


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


def test_pods_reads_every_page(env):
    fake, api = env
    fake.pods = {f"p{i}": pod(f"p{i}") for i in range(5)}
    fake.page_size = 2
    assert [p["id"] for p in api.pods()] == [f"p{i}" for i in range(5)]
    assert sum(1 for c in fake.calls if c[1].startswith("/pods?")) == 3


def test_create_is_never_posted_twice_when_the_answer_is_lost(env):
    fake, api = env
    body = R.create_body("ee-default-abc-until-9999999999")
    fake.faults = [("POST", "/pods", "timeout-after")]
    got = R.create(api, body, max_price=0.95, sleep=lambda s: None, gpus=R.GPUS["cheap"])
    assert got["id"] == "p1" and len(fake.pods) == 1
    assert [c for c in fake.calls if c[0] == "POST"] == [("POST", "/pods")]  # no second card tried after a lost answer


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


def test_create_tries_the_next_card_of_the_pool_after_a_clear_refusal(env):
    fake, api = env
    fake.refuse_gpus = set(R.GPUS["cheap"][:2])  # no capacity for the first two cards
    got = R.create(api, R.create_body("ee-x-until-9999999999", "cheap"), max_price=0.95, gpus=R.GPUS["cheap"])
    assert got["gpu"] == R.GPUS["cheap"][2] and len(fake.pods) == 1
    assert sum(1 for c in fake.calls if c == ("POST", "/pods")) == 3
    fake.refuse_gpus = set(R.GPUS["cheap"])
    with pytest.raises(R.RunPodError, match="no pod could be made"):
        R.create(api, R.create_body("ee-y-until-9999999999", "cheap"), max_price=0.95, gpus=R.GPUS["cheap"])
    assert len(fake.pods) == 1


def test_a_card_over_the_ceiling_is_deleted_at_once(env):
    fake, api = env
    with pytest.raises(R.RunPodError, match="over the"):
        R.create(api, R.create_body("ee-x-until-9999999999"), max_price=0.5)
    assert not fake.pods


def test_the_v2_create_body_names_one_card_and_the_volume_mount():
    body = R.create_body("ee-x-until-9", "cheap", volume=60, min_ram=24)
    assert body["gpu"] == {"id": R.GPUS["cheap"][0], "count": 1, "allowedCudaVersions": R.CUDA_VERSIONS, "minRamPerGpu": 24}
    assert body["mounts"] == {"persistent": {"size": 60, "path": "/workspace"}} and body["disk"] == R.CONTAINER_GB
    assert body["cloud"] == "SECURE" and "22/tcp" in body["ports"] and "cmd" not in body
    for old in ("gpuTypeIds", "volumeInGb", "containerDiskInGb", "dockerStartCmd", "interruptible"):
        assert old not in body  # v1 fields


def test_stop_is_idempotent_and_verified(env):
    fake, api = env
    fake.pods["a"] = pod()
    assert R.stop(api, "a") == "EXITED"
    n = len(fake.calls)
    assert R.stop(api, "a") == "EXITED" and ("POST", "/pods/a/action") not in fake.calls[n:]  # already stopped: no call
    assert R.stop(api, "gone") == "GONE"
    fake.pods["e"] = pod("e", status="ERROR")
    assert R.stop(api, "e") == "ERROR"  # nothing runs; the creator decides about its disk


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


def test_delete_counts_a_204_and_a_404_as_done(env):
    fake, api = env
    fake.pods["a"] = pod()
    assert R.delete(api, "a") == "GONE" and "a" not in fake.pods
    assert R.delete(api, "a") == "GONE"


def test_sweep_stops_expired_lists_stopped_disks_and_survives_a_failure(env):
    fake, api = env
    fake.pods = {"ok": pod("ok"), "old": pod("old", "ee-x-until-100"), "noname": pod("noname", "my pod"),
                 "ex": pod("ex", "ee-x-until-100", "EXITED", volumeInGb=60), "err": pod("err", "ee-x-until-100", "ERROR", volumeInGb=10)}
    fake.faults = [("POST", "/pods/old/action", 400)]
    rows = R.sweep(api, now=1000)
    assert fake.pods["noname"]["status"] == "EXITED" and fake.pods["ok"]["status"] == "RUNNING"
    assert len(rows["stopped"]) == 2  # old (graphql after the REST 400) and noname
    assert rows["exited"] == ["ex ee-x-until-100: disk 60 GB = $0.39/day", "err ee-x-until-100: disk 10 GB = $0.07/day (ERROR state)"]
    assert "ex" in fake.pods  # never deleted unasked
    rows = R.sweep(api, now=1000, delete_exited=True)
    assert "ex" not in fake.pods and "err" not in fake.pods and len(rows["deleted"]) == 4  # the two just stopped as well


def test_the_cli_refuses_without_the_creators_word(env):
    fake, api = env
    fake.pods["a"] = pod()
    for argv in (["create", "--max-usd", "1", "--max-hours", "1"], ["create", "--yes"], ["delete", "a"],
                 ["sweep", "--delete"], ["start", "a", "--yes"]):
        with pytest.raises(SystemExit):
            R.main(argv, api=api)
    assert fake.pods["a"]["status"] == "RUNNING" and len(fake.pods) == 1


def test_create_cli_reserves_in_the_ledger_writes_a_session_and_names_the_lifetime(env, tmp_path, monkeypatch):
    fake, api = env
    monkeypatch.setattr(R, "guard_detached", lambda pid: 4242)
    monkeypatch.setattr(R, "live_guard", lambda pid: True)
    ledger = tmp_path / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "0.75", "--boot", "cloud/x.json", "--ledger", str(ledger)], api=api)
    sess = R.sess_read("p1")
    assert sess["max_usd"] == 0.5 and sess["status_token"] and sess["until"] == R.until_of(fake.pods["p1"]["name"])
    assert sess["price"] == 0.89 and sess["pod_shape"] == {"volumeInGb": 150, "containerDiskInGb": 80}
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


def test_a_provisioning_pod_without_a_price_runs_its_money_clock_on_the_ceiling(env, tmp_path, monkeypatch):
    fake, api = env
    monkeypatch.setattr(R, "guard_detached", lambda pid: 4242)
    fake.new_status = "PROVISIONING"  # v2 answers 201 PROVISIONING with cost 0 and no runtime
    ledger = tmp_path / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(ledger)], api=api)
    sess = R.sess_read("p1")
    assert sess["price"] == R.MAX_PRICE["default"]  # never $0/h
    assert R.guard_check(sess, R.norm(fake.pods["p1"]), sess["started"] + 60)[0] == "ok"  # PROVISIONING is guarded, not "end"
    fake.pods["p1"].update(status="RUNNING", cost=0.74)
    pushes, looks = [], []
    t = iter(range(int(sess["started"]), int(sess["started"]) + 10**7, 600)).__next__
    R.guard(api, "p1", clock=t, sleep=lambda s: None, push=lambda *a: pushes.append(a), page=lambda *a: "", log=lambda *a: None,
            on_look=lambda p, a, w: looks.append(a))
    assert R.sess_read("p1")["price"] == 0.74 and looks[-1] == "stop"  # the real price replaced the ceiling


def test_a_failed_boot_stops_the_pod_and_pid1_stays_alive():
    cmd = R.boot_cmd("cloud/stages_pictures.json", "main")[2]
    assert cmd.startswith("set -o pipefail;") and '"action":"stop"' in cmd and "/v2/pods/$RUNPOD_POD_ID/action" in cmd
    assert "-X DELETE" not in cmd and "terminate" not in cmd
    assert cmd.rstrip().endswith("tail -f /dev/null")


def _session(pid="a", **kw):
    p = pod(pid)
    sess = R.new_session(p, max_usd=1.0, max_hours=2.0, now=0, **kw)
    sess["answered"] = True
    return R.sess_write(sess)


def test_guard_check_caps_lifetime_boot_conductor_and_error(env):
    sess = _session()
    running = R.norm(pod())
    assert R.guard_check(sess, None, 10)[0] == "end"
    assert R.guard_check(sess, R.norm(pod(status="EXITED")), 10)[0] == "end"
    assert R.guard_check(sess, R.norm(pod(status="ERROR")), 10) == ("stop", "the pod is in ERROR: stopping it; the creator decides about its disk")
    assert R.guard_check(sess, running, 60)[0] == "ok"
    assert "money cap" in R.guard_check(sess, running, 3600 * 1.1)[1]  # 0.89 + disk ~0.03 $/h
    assert "time cap" in R.guard_check({**sess, "max_usd": 99}, running, 7300)[1]
    assert "lifetime" in R.guard_check({**sess, "until": 100}, running, 101)[1]
    assert "boot" in R.guard_check({**sess, "answered": False}, running, 601)[1]
    assert R.guard_check({**sess, "ended": 50}, running, 100, "STATUS DONE")[0] == "ok"
    assert "conductor" in R.guard_check({**sess, "ended": 50}, running, 200, "STATUS DONE")[1]


def test_the_money_clock_counts_compute_and_disk():
    sess = _session()
    assert R.spent_estimate(sess, 3600, R.norm(pod())) == pytest.approx(0.89 + 230 * 0.10 / 730, abs=1e-4)
    assert R.disk_per_hour(pod(volumeInGb=60), running=False) * 24 == pytest.approx(0.3945, abs=1e-3)


def test_guard_stops_at_the_cap_keeps_the_disk_and_says_what_it_costs(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()
    pushes = []
    t = iter(range(0, 10**7, 600)).__next__
    why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: pushes.append(a), page=lambda *a: "", log=lambda *a: None)
    assert "money cap" in why and fake.pods["a"]["status"] == "EXITED"
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
    assert "money cap" in why and fake.pods["a"]["status"] == "EXITED"
    assert any(p[0] == "Guard is blind" for p in pushes)


def test_a_guard_restarted_after_a_container_restart_keeps_the_session_clock(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()  # started at t=0; the guard process (and the session's container) restarted much later
    t = iter([4000] + list(range(4000, 10**7, 30))).__next__
    why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: None, page=lambda *a: "", log=lambda *a: None)
    assert "money cap" in why  # 4000 s at ~$0.92/h > $1: the clock did not restart with the process


def test_a_guard_stops_a_pod_that_went_into_error(env):
    fake, api = env
    fake.pods["a"] = pod()
    _session()
    fake.pods["a"]["status"] = "ERROR"
    fake.pods["a"]["runtime"] = None
    pushes = []
    why = R.guard(api, "a", clock=iter(range(0, 10**6, 30)).__next__, sleep=lambda s: None, push=lambda *a: pushes.append(a),
                  page=lambda *a: "", log=lambda *a: None)
    assert "ERROR" in why and R.sess_read("a")["close_status"] == "ERROR" and pushes


def test_end_pod_that_never_succeeds_says_so_instead_of_crashing(env, monkeypatch):
    fake, api = env
    fake.pods["a"] = pod()

    def never(api, pid, **kw):
        raise R.RunPodError(f"pod {pid} is still running after stop")

    monkeypatch.setattr(R, "stop", never)
    sess = _session()
    pushes = []
    st = R.end_pod(api, sess, "money cap", push=lambda *a: pushes.append(a), sleep=lambda s: None, attempts=3)
    assert st == "UNSTOPPED" and R.sess_read("a")["close_status"] == "UNSTOPPED"
    assert pushes[-1][0].startswith("GUARD GAVE UP") and pushes[-1][2] == "urgent"


def test_wait_ready_needs_ports_and_times_out(env):
    fake, api = env
    fake.pods["a"] = pod()
    clock = iter(range(0, 10**6, 100)).__next__
    with pytest.raises(TimeoutError):
        R.wait_ready(api, "a", timeout=300, clock=clock, sleep=lambda s: None)
    fake.pods["a"] = pod(ports={"22": 40022}, ip="1.2.3.4")
    assert R.wait_ready(api, "a", timeout=300, clock=clock, sleep=lambda s: None)["publicIp"] == "1.2.3.4"


def test_pod_session_stops_the_pod_on_an_error(env):
    fake, api = env
    fake.pods["a"] = pod()
    with pytest.raises(ValueError):
        with R.PodSession(api, "a"):
            raise ValueError("painter crashed")
    assert fake.pods["a"]["status"] == "EXITED"


def test_cost_settles_the_reservation_with_the_billed_amount(env, tmp_path):
    fake, api = env
    ledger = tmp_path / "run.json"
    run = Run.open(ledger, caps={"runpod_usd": 3.0})
    run.reserve("runpod_usd", 0.5, item="pod:a")
    R.sess_write({**_session(), "ledger": str(ledger)})
    fake.billing = [{"totalAmount": 0.12, "gpuAmount": 0.1, "diskAmount": 0.02, "podId": "a", "startTime": "2026-10-22T08:00:00Z"},
                    {"totalAmount": 0.08, "gpuAmount": 0.07, "diskAmount": 0.01, "podId": "a", "startTime": "2026-10-22T09:00:00Z"}]
    assert R.settle(api, "a") == (0.2, 2)
    run = Run.open(ledger)
    assert run.spent("runpod_usd") == 0.2 and run.data["items"]["pods"]["a"]["billed_buckets"] == 2
    fake.billing.append({"totalAmount": 0.01, "podId": "a"})  # the newest hour grew: settle again
    R.settle(api, "a")
    assert Run.open(ledger).spent("runpod_usd") == 0.21
    assert any("podId=a" in c[1] and "bucketSize=hour" in c[1] for c in fake.calls)


def test_create_is_refused_past_the_24h_billing_the_balance_or_with_a_stray_disk(env):
    fake, api = env
    ok = dict(max_usd=0.5, max_hours=1.0, gpu="default", now=10**6)
    assert R.preflight_create(api, **ok) == []
    assert any("max_hours_per_pod" in w for w in R.preflight_create(api, **{**ok, "max_hours": 3}))
    fake.billing = [{"totalAmount": 1.2, "podId": "old"}]  # stopped disks count: RunPod bills them per pod
    assert any("per_24h_usd" in w for w in R.preflight_create(api, **ok))
    fake.billing = []
    fake.pods["ex"] = pod("ex", "x", "EXITED", volumeInGb=60)
    assert any("clean up first: ex" in w for w in R.preflight_create(api, **ok))
    assert R.preflight_create(api, **ok, ignore="ex") == []  # starting that very pod again


def test_check_flags_stopped_disks_unless_the_creator_keeps_them(env, tmp_path, monkeypatch):
    fake, api = env
    fake.pods = {"ex": pod("ex", "x", "EXITED", volumeInGb=60), "run": pod("run", "ee-x-until-100"), "err": pod("err", "e", "ERROR")}
    res = R.check(api, now=1000)
    assert len(res["problems"]) == 3 and "$0.39/day" in res["problems"][0] and "in ERROR" in res["problems"][2]
    caps = json.loads(R.spend_caps.PATH.read_text())
    caps["runpod"]["keep_stopped_pods"] = ["ex", "err"]
    (tmp_path / "caps.json").write_text(json.dumps(caps))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(tmp_path / "caps.json"))
    assert len(R.check(api, now=1000)["problems"]) == 1


def test_check_sees_network_volumes_global_volumes_and_idle_serverless_workers(env, tmp_path, monkeypatch):
    fake, api = env
    fake.volumes = [{"id": "nv1", "name": "models", "size": 100, "dataCenter": "EU-RO-1"}]
    fake.global_volumes = [{"id": "gsb_1", "name": "shared"}]
    fake.endpoints = [{"id": "ep1", "name": "sdxl", "workersMin": 1, "workersMax": 3}, {"id": "ep2", "name": "ok", "workersMin": 0}]
    res = R.check(api, now=1000)
    assert any("nv1 models network volume 100 GB bills $0.23/day" in p for p in res["problems"])
    assert any("gsb_1 shared global volume exists" in p for p in res["problems"])
    assert any("ep1 sdxl serverless endpoint keeps 1 worker" in p for p in res["problems"]) and len(res["problems"]) == 3
    fake.faults = [("GET", "/network-volumes", 404)]  # a listing that cannot be read is a PROBLEM, never silence
    assert any("network volumes could not be listed" in p for p in R.check(api, now=1000)["problems"])
    caps = json.loads(R.spend_caps.PATH.read_text())
    caps["runpod"]["keep_network_volumes"] = ["nv1", "gsb_1"]
    (tmp_path / "caps.json").write_text(json.dumps(caps))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(tmp_path / "caps.json"))
    assert len(R.check(api, now=1000)["problems"]) == 1  # only the serverless workers
    with pytest.raises(SystemExit, match="--yes"):
        R.main(["delete-volume", "nv1"], api=api)
    R.main(["delete-volume", "nv1", "--yes"], api=api)
    assert fake.volumes == []


def test_the_24h_ceiling_counts_every_resource_not_only_pods(env):
    fake, api = env
    fake.other_billing = 1.4  # serverless + storage billed while no pod existed
    assert api.billing(None, 10**6 - 86400)[0] == 0 and api.billing_total(10**6 - 86400)[0] == 1.4
    assert any("per_24h_usd" in w for w in R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="default", now=10**6))
    assert any("billed in the last 24 h $1.40" in i for i in R.check(api, now=10**6)["info"])


def test_a_429_with_retry_after_is_waited_out_and_a_402_stops_the_card_loop(env):
    fake, api = env
    fake.pods["a"] = pod()
    waits = []
    api.sleep = waits.append
    fake.headers = {"Retry-After": "7"}
    fake.faults = [("GET", "/pods/a", 429)]
    assert api.pod("a")["id"] == "a" and waits == [7]
    fake.refuse_gpus = set(R.GPUS["cheap"])
    fake.faults = [("POST", "/pods", 402)]
    with pytest.raises(R.RunPodError, match="every card"):
        R.create(api, R.create_body("ee-x-until-9999999999", "cheap"), max_price=0.95, gpus=R.GPUS["cheap"])
    assert sum(1 for c in fake.calls if c == ("POST", "/pods")) == 1  # no balance: the other cards are not tried


def test_the_pod_gets_only_a_restricted_key_and_only_when_one_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "RP", tmp_path)
    for var in ("RUNPOD_POD_API_KEY", "NTFY_TOPIC", "HF_TOKEN", "GITHUB_TOKEN", "GITHUB_TOKEN_RO", "RUNPOD_PUBLIC_KEY", "HEARTBEAT_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("RUNPOD_API_KEY", "the-account-key")
    assert "RUNPOD_API_KEY" not in R.pod_env("t")  # the account key never goes into a pod
    monkeypatch.setenv("RUNPOD_POD_API_KEY", "pods-write-only")
    assert R.pod_env("t")["RUNPOD_API_KEY"] == "pods-write-only"


def test_logs_reads_server_sent_events(env):
    fake, api = env

    class Stream:
        def __init__(self):
            self.lines = [b"id: 1\n", b'data: {"ts":"2026-10-22T08:00:00Z","source":"container","line":"booting"}\n', b"\n",
                          b"id: 2\n", b"data: not json\n", b""]

        def readline(self):
            return self.lines.pop(0) if self.lines else b""

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    seen = {}

    def opener(req, timeout):
        seen["url"], seen["accept"] = req.full_url, req.get_header("Accept")
        return Stream()

    rows = api.logs("a", tail=50, seconds=1, opener=opener)
    assert rows == [("2026-10-22T08:00:00Z", "container", "booting"), ("", "", "not json")]
    assert seen["url"].endswith("/pods/a/logs?tail=50") and seen["accept"] == "text/event-stream"


def test_the_ledger_refuses_a_cap_above_the_creators_ceiling_and_fills_missing_ones(tmp_path):
    from explainer_engine.core.spend_caps import OverCeiling
    with pytest.raises(OverCeiling):
        Run.open(tmp_path / "a.json", caps={"runpod_usd": 50.0})
    assert Run.open(tmp_path / "b.json", caps={"gemini_usd": 2.0}).data["caps"] == {"gemini_usd": 2.0, "runpod_usd": 3.0, "bfl_usd": 3.0, "fal_usd": 9.0}


def test_hooks_block_bypasses_and_a_turn_that_leaves_a_stray(env, monkeypatch, capsys):
    from explainer_engine.cloud import hooks as H
    fake, api = env
    for cmd in ("python cloud/rp.py create --yes --gpu big", "bash -c 'cd tmr && python cloud/rp.py start'",
                'curl -X POST https://rest.runpod.io/v1/pods -d @b.json', 'curl https://rest.runpod.io/v1/pods -X POST',
                "curl -X POST https://rest.runpod.io/v1/pods/abc/start",
                'curl -X POST https://api.runpod.io/v2/pods -d @b.json', 'curl https://api.runpod.io/v2/pods -X POST',
                """curl -X POST https://api.runpod.io/v2/pods/abc/action -d '{"action":"start"}'""",
                """curl -d '{"action": "restart"}' -X POST https://api.runpod.io/v2/pods/abc/action""",
                "python -c 'import runpod; runpod.create_pod(\"x\", \"img\", \"NVIDIA RTX A5000\")'",
                "runpodctl create pod --gpuType 'NVIDIA RTX A5000'", "runpodctl start pod abc --bid 0.3",
                "curl -X PATCH https://api.runpod.io/v2/pods/abc -d '{\"disk\": 20}'", "curl https://api.runpod.io/v2/pods/abc -X PATCH -d @b.json"):
        assert H.pre_bash({"tool_input": {"command": cmd}}) == 2, cmd
    for cmd in ("python -m explainer_engine.cloud.runpod create --yes --max-usd 0.5", "curl -X POST https://rest.runpod.io/v1/pods/abc/stop",
                """curl -X POST https://api.runpod.io/v2/pods/abc/action -d '{"action":"stop"}'""",
                "curl https://api.runpod.io/v2/pods/abc", "python cloud/rp.py sweep", "pytest -q tests/unit/test_runpod.py",
                "runpodctl get pod", "runpodctl stop pod abc"):
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
