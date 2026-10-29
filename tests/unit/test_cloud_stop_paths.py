"""P1a (docs/CLOUD_RUNBOOK.md): the guard on script pods, the registry-aware watchdog, the fail-closed hooks, the refusals of
``create`` and the workflow file, against the fake RunPod. No network, no pod, no money."""
import json
import re
from pathlib import Path

import pytest
from test_runpod import NEW_SH, FakeRunPod, pod

from explainer_engine.cloud import hf_live, hooks as H, jobs as J, runpod as R, watchdog as W
from explainer_engine.core.ledger import Run

BEAT = "datasets/o/r:run/out/beat.txt"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp")
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    monkeypatch.setattr(R, "guard_detached", lambda pid: 4242)
    monkeypatch.setattr(R, "live_guard", lambda pid: True)
    fake = FakeRunPod()
    return fake, R.Api("k", transport=fake, sleep=lambda s: None), tmp_path


def beat_text(now, progress="step 5/9", word="ALIVE", fail=0, unstored=0, rc=None):
    ts = "2026-10-29T18:00:00Z"
    return ("BOOT key=200 job=j pod=a price=0.5 deadline=99\n"
            f"{word}{'' if rc is None else f' rc={rc}'} {ts} progress={progress} upload_fail={fail} unstored={unstored}\n")


def script_job(tmp, pid="a", stall_s=None):
    job = J.Job.create(tmp / "jobs" / "cloud", "ep", kind="pod", provider="runpod", now=0, caps={"max_usd": 99, "max_hours": 99},
                       reuse_finished=False)
    job.attach(pid, now=0)
    job.move("PROVISIONING", "test", now=0)
    sess = R.new_session(pod(pid), max_usd=99, max_hours=99, now=0, job=job.dir, price_ceiling=0.95, heartbeat=BEAT, stall_s=stall_s)
    sess.update(until=10**9)
    R.sess_write(sess)
    return job


def run_script_guard(api, fake, monkeypatch, make_beat, *, hours, step=300, on_look_extra=None, pushes=None):
    """The guard over ``hours`` of simulated time; the pod is set to EXITED afterwards so the loop ends by itself."""
    state = {"now": 0}
    real = R.heartbeat_step
    monkeypatch.setattr(R, "heartbeat_step", lambda s, now, push=None: real(
        s, now, beat=lambda x: float(now - 30), text=lambda x: make_beat(now), push=push))

    def clock():
        state["now"] += step
        return state["now"]
    looks = []

    def on_look(p, action, why):
        looks.append((state["now"], action, why))
        if state["now"] >= hours * 3600:
            fake.pods["a"]["status"] = "EXITED"
    why = R.guard(api, "a", clock=clock, sleep=lambda s: None, push=lambda *a: (pushes if pushes is not None else []).append(a),
                  page=lambda *a: "", log=lambda *a: None, on_look=on_look)
    return why, looks


def test_c_a_healthy_script_pod_is_never_stopped_or_stalled_for_three_hours(env, monkeypatch):
    """The 2026-10-29 finding: the REST view of a script pod never changes, so jobs.stall fired and the guard stopped it at ~70 min."""
    fake, api, tmp = env
    fake.pods["a"] = pod()                       # RUNNING, no ports, GPU util 0: the LT-17 shape
    job = script_job(tmp)
    pushes = []
    why, looks = run_script_guard(api, fake, monkeypatch, lambda now: beat_text(now, progress=f"step {now // 300}/999"), hours=3, pushes=pushes)
    assert why.startswith("pod is EXITED") and R.sess_read("a").get("closed") is None   # the guard never stopped it
    moves = [e["to"] for e in J.Job(job.dir).events() if e["kind"] == "move"]
    assert "STALLED" not in moves and J.Job(job.dir).state["state"] in ("RUNNING", "FAILED")
    assert not any(p[0] in ("Pod job stalled", "Pod is silent") for p in pushes)


def test_c_a_frozen_progress_under_fresh_beats_stalls_then_ends(env, monkeypatch):
    fake, api, tmp = env
    fake.pods["a"] = pod()
    job = script_job(tmp, stall_s=1800)
    pushes = []
    why, looks = run_script_guard(api, fake, monkeypatch, lambda now: beat_text(now), hours=6, pushes=pushes)
    assert "progress stood still for 60 min" in why and fake.pods["a"]["status"] == "EXITED"
    stop_at = [t for t, a, w in looks if a == "stop"][0]
    assert 3600 <= stop_at <= 3600 + 2 * 900          # twice the limit, plus the 'first beat' offset
    assert any(p[0] == "Pod job stalled" for p in pushes)
    assert J.Job(job.dir).state["state"] in ("STOPPED", "STALLED")


def test_c_frozen_progress_with_failing_uploads_is_not_stopped_but_pushed(env, monkeypatch):
    fake, api, tmp = env
    fake.pods["a"] = pod()
    script_job(tmp, stall_s=600)
    pushes = []
    why, looks = run_script_guard(api, fake, monkeypatch, lambda now: beat_text(now, fail=7, unstored=4), hours=2, pushes=pushes)
    assert why.startswith("pod is EXITED")                              # CR-10: no stop for failing uploads while files are unstored
    assert any(p[0] == "Pod uploads are failing" and p[2] == "urgent" for p in pushes)


def test_c_a_script_that_writes_no_progress_is_judged_by_its_beats_alone(env, monkeypatch):
    fake, api, tmp = env
    fake.pods["a"] = pod()
    script_job(tmp, stall_s=600)
    why, _ = run_script_guard(api, fake, monkeypatch, lambda now: beat_text(now, progress=""), hours=3)
    assert why.startswith("pod is EXITED")


def test_c_failed_upload_and_bad_host_put_the_job_into_recovery(env, monkeypatch):
    fake, api, tmp = env
    fake.pods["a"] = pod()
    job = script_job(tmp)
    pushes = []
    why, _ = run_script_guard(api, fake, monkeypatch, lambda now: beat_text(now, word="FAILED_UPLOAD", rc=0, fail=9, unstored=2), hours=1,
                              pushes=pushes)
    assert "FAILED_UPLOAD" in why and fake.pods["a"]["status"] == "EXITED"
    assert J.Job(job.dir).state["state"] == "RECOVERY_REQUIRED" and any(p[0] == "Pod job needs a hand" for p in pushes)


def test_the_key_probe_other_than_200_is_pushed_once(env):
    pushes = []
    sess = R.new_session(pod("k"), max_usd=1.0, max_hours=2.0, now=0, heartbeat=BEAT)
    text = lambda s: beat_text(0).replace("key=200", "key=401")  # noqa: E731
    assert R.heartbeat_step(sess, 600, beat=lambda s: 500.0, text=text, push=lambda *a: pushes.append(a)) == "alive"
    assert sess["key"] == "401" and pushes[0][0] == "Pod cannot stop itself"


# --- the watchdog with the registry (CR-12) -----------------------------------------------------------------------------------
class FakeLive:
    def __init__(self, specs=None, age=None):
        self._specs, self.age, self.closed, self.dropped, self.ran = dict(specs or {}), age, [], [], []

    def write_spec(self, spec):
        self._specs[spec["name"]] = spec

    def specs(self):
        return dict(self._specs)

    def close_spec(self, name):
        self.closed.append(name)
        self._specs.pop(name, None)

    def drop_spec(self, name):
        self.dropped.append(name)
        self._specs.pop(name, None)

    def mark_run(self, now=None):
        self.ran.append(now)

    def watchdog_age(self, now=None):
        return self.age


def spec_for(name, pid, **kw):
    return {"name": name, "pod": pid, "job": "j", "heartbeat": BEAT, "created": 1000.0, "price": 0.34, "disk_per_h": 0.05, "max_usd": 3.0,
            "max_hours": 4.0, "until": 10**10, **kw}


def test_d_the_watchdog_stops_a_pod_whose_beat_says_done_without_any_session(env):
    fake, api, tmp = env
    name = "ee-x-until-9999999999"
    fake.pods = {"a": pod("a", name), "b": pod("b", "ee-y-until-9999999999")}
    live = FakeLive({name: spec_for(name, "a"), "ee-y-until-9999999999": spec_for("ee-y-until-9999999999", "b")})
    texts = {BEAT: beat_text(0, word="DONE", rc=0)}
    pushes = []
    res = W.run(api, now=2000, apply=True, push=lambda *a: pushes.append(a) or True, log=lambda *a: None, live=live,
                text=lambda spec: texts[spec] if "x" not in spec else texts[spec])
    # both specs share the one beat file in this fake, so both pods end; the point is the rule fires from the registry alone
    assert fake.pods["a"]["status"] == "EXITED" and "DONE" in str(res["stopped"])
    assert live.ran == [2000] and not list((tmp / "rp").glob("sessions/*.json"))


def test_d_the_money_estimate_from_the_record_stops_a_pod_and_alerts_failing_uploads(env):
    fake, api, tmp = env
    name = "ee-x-until-9999999999"
    fake.pods = {"a": pod("a", name, price=1.69)}
    live = FakeLive({name: spec_for(name, "a", max_usd=3.0, created=0.0)})
    res = W.run(api, now=2 * 3600, apply=True, push=lambda *a: True, log=lambda *a: None, live=live,
                text=lambda s: beat_text(0, fail=7, unstored=3))
    assert fake.pods["a"]["status"] == "EXITED" and "reached the approved $3.0" in res["stopped"][0]
    assert any("7 uploads in a row failed" in a and "a person must look" in a for a in res["alerts"])


def test_d_a_pod_without_a_record_keeps_the_lifetime_rule_and_a_gone_pod_closes_its_record(env):
    fake, api, tmp = env
    fake.pods = {"old": pod("old", "ee-x-until-100"), "ok": pod("ok", "ee-z-until-9999999999")}
    gone = "ee-g-until-9999999999"
    live = FakeLive({gone: spec_for(gone, "gone-pod")})
    res = W.run(api, now=1000, apply=True, push=lambda *a: True, log=lambda *a: None, live=live, text=lambda s: "")
    assert fake.pods["old"]["status"] == "EXITED" and fake.pods["ok"]["status"] == "RUNNING"
    assert live.closed == [gone] and live.ran


def test_d_no_hf_token_with_a_live_pod_is_an_alert_not_silence(env):
    fake, api, tmp = env
    fake.pods = {"ok": pod("ok", "ee-z-until-9999999999")}
    res = W.run(api, now=1000, apply=True, push=lambda *a: True, log=lambda *a: None, live=None)
    assert any("no HF_TOKEN" in a for a in res["alerts"])
    fake.pods = {}
    assert not any("no HF_TOKEN" in a for a in W.run(api, now=1000, apply=True, push=lambda *a: True, log=lambda *a: None, live=None)["alerts"])


def test_d_the_summary_and_the_exit_code_do_not_hide_a_lost_push(env, monkeypatch, tmp_path):
    fake, api, tmp = env
    fake.pods = {"old": pod("old", "ee-x-until-100")}
    monkeypatch.setattr(W.R, "notify", lambda *a: False)
    out = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(out))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert W.main(["--apply"], api=api) == 1 and "Stopped" in out.read_text()
    d = {"stopped": [], "failed": [], "alerts": [], "info": [], "push_ok": False}
    assert "did not arrive" in W.summary(d)


def test_hf_live_writes_reads_and_lists_through_the_commit_api(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    files, calls = {}, []

    def transport(method, url, data, headers):
        calls.append((method, url))
        assert headers["Authorization"] == "Bearer t"
        if method == "POST" and url.endswith("/commit/main"):
            for line in data.decode().splitlines():
                row = json.loads(line)
                if row["key"] == "file":
                    import base64
                    files[row["value"]["path"]] = base64.b64decode(row["value"]["content"]).decode()
                if row["key"] == "deletedFile":
                    files.pop(row["value"]["path"], None)
            return 200, "{}"
        if "/tree/main/" in url:
            folder = url.split("/tree/main/", 1)[1].replace("%2F", "/")
            return 200, json.dumps([{"type": "file", "path": p} for p in files if p.startswith(folder + "/")])
        path = url.split("/resolve/main/", 1)[1].replace("%2F", "/")
        return (200, files[path]) if path in files else (404, "")
    lv = hf_live.Live("t", transport=transport)
    lv.write_spec(spec_for("n1", "p1"))
    assert lv.specs()["n1"]["pod"] == "p1" and lv.watchdog_age() is None
    lv.mark_run(500.0)
    assert lv.watchdog_age(800.0) == 300.0
    lv.close_spec("n1")
    assert "runpod/closed/n1.json" in files and "runpod/live/n1.json" not in files
    with pytest.raises(hf_live.LiveError):
        hf_live.Live("")


# --- create refusals (CR-07) -------------------------------------------------------------------------------------------------
def _create(api, tmp, script, *extra, live=None):
    ledger = tmp / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    sf = tmp / "job.sh"
    sf.write_text(script)
    return R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(ledger), "--script", str(sf),
                   "--script-url", "https://huggingface.co/x/pod.sh", *extra], api=api, live=live)


def test_create_cli_refuses_a_script_pod_nothing_outside_the_session_can_stop(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="no stop path outside this session"):
        _create(api, tmp, NEW_SH, live=FakeLive(age=None))
    with pytest.raises(SystemExit, match="no stop path outside this session"):
        _create(api, tmp, NEW_SH, live=FakeLive(age=7200))
    with pytest.raises(SystemExit, match="no heartbeat"):
        _create(api, tmp, NEW_SH.replace("# heartbeat: datasets/o/r:run/out/beat.txt\n", ""), live=FakeLive(age=60))
    with pytest.raises(SystemExit, match="disagree"):
        _create(api, tmp, NEW_SH, "--heartbeat", "datasets/o/r:other/beat.txt", live=FakeLive(age=60))
    assert not fake.pods


def test_a_pre_p1a_script_is_judged_by_its_old_rules_but_never_runs_under_the_wrapper(env):
    fake, api, tmp = env
    legacy = "( while true; do sleep 240; date > out/beat.txt; up; done ) &\npython train.py\n" + "python -m explainer_engine.vault check-uploaded out --to r\n"
    assert not R.is_wrapper_script(legacy) and R.lint_pod_script(legacy) == [] and R.is_wrapper_script(NEW_SH)
    why = R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="cheap", now=10**6, script=legacy, heartbeat=BEAT, pod_key=True)
    assert len(why) == 1 and "pre-P1a protocol" in why[0]


def test_create_cli_makes_a_script_pod_with_the_wrapper_the_env_and_a_live_record(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    seen = []
    real = R.create
    monkeypatch.setattr(R, "create", lambda api, body, **kw: seen.append((body, kw)) or real(api, body, **kw))
    live = FakeLive(age=600)
    _create(api, tmp, NEW_SH + "# stall-minutes: 45\n", "--volume", "0", live=live)       # (b) is OR: the fresh watchdog is enough
    body, kw = seen[0]
    env_ = body["env"]
    assert body["cmd"] == R.script_cmd() and env_["EE_SCRIPT_URL"] == "https://huggingface.co/x/pod.sh"
    assert env_["EE_HF_REPO"] == "o/r" and env_["EE_HF_PREFIX"] == "run/out" and env_["EE_MAX_USD"] == "0.5" and env_["EE_LIFETIME_S"] == "3600"
    assert float(env_["EE_PRICE"]) == 0.95 and kw["gpus"][0][2] == 0.95                          # the pool card's ceiling price
    name = fake.pods["p1"]["name"]
    spec = live.specs()[name]
    assert spec["pod"] == "p1" and spec["heartbeat"] == BEAT and spec["max_usd"] == 0.5 and spec["until"] == R.until_of(name)
    sess = R.sess_read("p1")
    assert sess["heartbeat"] == BEAT and sess["stall_s"] == 45 * 60


def test_create_cli_drops_the_record_when_no_pod_could_be_made(env, monkeypatch):
    fake, api, tmp = env
    fake.refuse_gpus = set(R.GPUS["default"])
    live = FakeLive(age=60)
    with pytest.raises(R.RunPodError):
        _create(api, tmp, NEW_SH, live=live)
    assert live.dropped and not live.specs()


def test_create_per_card_price_reaches_the_dead_man(env):
    fake, api, tmp = env
    seen = []
    orig = fake._handle

    def spy(method, path, body):
        if method == "POST" and path.startswith("/pods"):
            seen.append(json.loads(body)["env"]["EE_PRICE"])
        return orig(method, path, body)
    fake._handle = spy
    body = R.create_body("ee-x-until-9999999999", "NVIDIA A40", script_url="https://x/p.sh", lifetime_s=3600, heartbeat=BEAT, max_usd=2.0,
                         price=0.35)
    R.create(api, body, max_price=3.0, gpus=[("NVIDIA A40", "COMMUNITY", 0.35)])
    assert seen == ["0.35"]
    with pytest.raises(R.RunPodError, match="heartbeat"):
        R.create_body("n", script_url="https://x/p.sh")


# --- hooks (CR-13) ------------------------------------------------------------------------------------------------------------
def test_f_the_stop_hook_fails_closed_only_when_a_live_pod_is_known(env, monkeypatch, capsys):
    fake, api, tmp = env
    monkeypatch.setattr(H, "_check", lambda: None)                      # no key
    assert H.stop({}) == 0                                               # nothing known live: never lock the session
    sess = R.new_session(pod("a"), max_usd=1.0, max_hours=2.0, heartbeat=BEAT)
    sess.update(until=10**10)
    R.sess_write(sess)
    assert H.known_live() == [("a", "ee-x-until-9999999999")]
    assert H.stop({}) == 2 and "a ee-x" in capsys.readouterr().err        # no key + a live session
    assert H.stop({"stop_hook_active": True}) == 0
    monkeypatch.setattr(H, "_check", lambda: {"problems": [], "info": ["RunPod not reachable: boom"], "unreadable": True})
    assert H.stop({}) == 2                                               # API error + a live session
    sess["closed"] = 1.0
    R.sess_write(sess)
    assert H.stop({}) == 0 and H.known_live() == []                      # closed sessions do not count
    sess.update(closed=None, until=1.0)
    R.sess_write(sess)
    assert H.known_live() == []                                          # a session past its lifetime does not count either


def test_f_the_bash_hook_allows_only_read_only_and_stopping_tmr_commands(env):
    for cmd in ("python cloud/rp.py create --yes", "python3 cloud/rp.py start", "python cloud/rp.py adopt abc", "python cloud/rp.py",
                "python -c \"import rp; rp.main(['create'])\"", "python -c 'from cloud import rp; rp.main()'",
                "cd tmr && python ./cloud/rp.py guard abc", "python cloud/rp.py create"):
        assert H.pre_bash({"tool_input": {"command": cmd}}) == 2, cmd
    for cmd in ("python cloud/rp.py sweep", "python3 cloud/rp.py status abc", "python cloud/rp.py stop abc", "python cloud/rp.py cost abc",
                "cat cloud/rp.py", "grep -n create cloud/rp.py", "git diff cloud/rp.py", "python -m explainer_engine.cloud.runpod check"):
        assert H.pre_bash({"tool_input": {"command": cmd}}) == 0, cmd


# --- the workflow (g), the notify record (CR-14), CR-15, CR-16 -------------------------------------------------------------------
def test_g_the_watchdog_workflow_hides_nothing():
    text = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "watchdog.yml").read_text()
    body = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "|| true" not in body and "|| echo" not in body and "exit 0" not in body and "continue-on-error" not in body
    assert 'cron: "*/10 * * * *"' in body and "timeout-minutes: 20" in body
    assert "RUNPOD_API_KEY: ${{ secrets.RUNPOD_API_KEY }}" in body and "HF_TOKEN: ${{ secrets.HF_TOKEN }}" in body
    assert "exit 1" in body and "--kill-all --yes" in body and "--apply" in body
    assert "DELETE" not in body and "terminate" not in body
    import yaml
    doc = yaml.safe_load(text)
    assert doc["jobs"]["watch"]["timeout-minutes"] == 20


def test_notify_records_every_push_and_check_names_a_lost_one(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    assert R.notify("t", "x") is False
    rows = [json.loads(ln) for ln in (R.RP / "notify.jsonl").read_text().splitlines()]
    assert rows[0]["ok"] is False and rows[0]["topic"] is False
    fake.pods["a"] = pod("a")
    sess = R.new_session(pod("a"), max_usd=1.0, max_hours=2.0)
    res = R.check(api)
    assert any("no NTFY_TOPIC" in p for p in res["problems"])
    monkeypatch.setenv("NTFY_TOPIC", "t")
    monkeypatch.setattr(R.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    assert R.notify("Pod status", "x") is False
    assert any("did not arrive" in p for p in R.check(api)["problems"])


def test_cr15_no_generated_command_names_the_retiring_v1_route(env):
    cmds = [R.script_cmd()[2], R.boot_cmd("cloud/x.json", "main")[2], R.self_stop_sh()]
    for c in cmds:
        assert "rest.runpod.io" not in c and not re.search(r"/v1/", c), c[:60]


def test_cr16_the_unit_tests_never_touch_the_real_tools_dir():
    real = R.ROOT / "tools" / "runpod"
    assert R.RP != real and "rp_default" in str(R.RP) or "rp" in str(R.RP)
    R.notify("isolated", "x")
    assert not (real / "notify.jsonl").exists() or "isolated" not in (real / "notify.jsonl").read_text()


# --- P12a drill flags -------------------------------------------------------------------------------------------------------
def _create_p12a(api, tmp, monkeypatch, test, *extra):
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    ledger = tmp / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0}, **({"test": test} if test else {}))
    sf = tmp / "job.sh"
    sf.write_text(NEW_SH)
    seen = []
    real = R.create
    monkeypatch.setattr(R, "create", lambda api, body, **kw: seen.append(body) or real(api, body, **kw))
    R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--ledger", str(ledger), "--script", str(sf),
            "--script-url", "https://huggingface.co/x/pod.sh", *extra], api=api, live=FakeLive(age=60))
    return seen


def test_drill_is_refused_unless_the_ledger_says_p12a_smoke(env, monkeypatch):
    fake, api, tmp = env
    for test in (None, "other"):
        with pytest.raises(SystemExit, match="p12a_smoke"):
            _create_p12a(api, tmp, monkeypatch, test, "--drill", "drop_key")
    with pytest.raises(SystemExit, match="not one of"):
        _create_p12a(api, tmp, monkeypatch, "p12a_smoke", "--drill", "explode")
    assert not fake.pods


@pytest.mark.parametrize("drill", ["no_self_stop", "drop_key", "upload_fail"])
def test_drill_and_scaled_constants_reach_the_pod_env(env, monkeypatch, drill):
    fake, api, tmp = env
    body = _create_p12a(api, tmp, monkeypatch, "p12a_smoke", "--drill", drill, "--pass-s", "120", "--upload-grace-s", "300",
                        "--cap-grace-s", "120")[0]
    e = body["env"]
    assert e["EE_DRILL"] == drill and e["EE_PASS_S"] == "120" and e["EE_UPLOAD_GRACE_S"] == "300" and e["EE_CAP_GRACE_S"] == "120"


def test_a_normal_create_carries_no_drill_and_no_scaled_constants(env, monkeypatch):
    fake, api, tmp = env
    e = _create_p12a(api, tmp, monkeypatch, None)[0]["env"]
    assert not {"EE_DRILL", "EE_PASS_S", "EE_UPLOAD_GRACE_S", "EE_CAP_GRACE_S"} & set(e)
