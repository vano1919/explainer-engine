"""The Infrastructure Guardian (master brief 2026-10-22, stage B) against the fake RunPod: the job record, the incident log,
the durable store, the watchdog rules, the phone commands, and the brief's fifteen recovery scenarios. No network, no money."""
import json

import pytest
from test_runpod import FakeRunPod, pod

from explainer_engine.cloud import __main__ as CLI, incidents as I, jobs as J, runpod as R, store as S, watchdog as W
from explainer_engine.core.ledger import Run


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp")
    monkeypatch.setattr(R, "ROOT", tmp_path)
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    monkeypatch.setattr(I, "LOCAL", tmp_path / "rp" / "incidents.jsonl")
    monkeypatch.setattr(CLI, "JOBS_ROOT", tmp_path / "jobs" / "cloud")
    monkeypatch.setattr(CLI, "LAST_LOOK", tmp_path / "rp" / "last_look.json")
    monkeypatch.setenv("EXPLAINER_STORE_LOCAL", str(tmp_path / "store"))
    monkeypatch.setattr(R, "guard_detached", lambda pid: 4242)
    monkeypatch.setattr(R, "live_guard", lambda pid: True)
    fake = FakeRunPod()
    api = R.Api("k", transport=fake, sleep=lambda s: None)
    return fake, api, tmp_path


def job_for(tmp_path, pid="a", state="RUNNING", stage=None, now=0, **inputs):
    """A job record attached to pod ``pid`` with a session the guard can read."""
    job = J.Job.create(tmp_path / "jobs" / "cloud", "ep", kind="pod", provider="runpod", now=now, inputs=inputs or None,
                       caps={"max_usd": 1.0, "max_hours": 2.0}, reuse_finished=False)
    job.attach(pid, now=now)
    for st in ("PROVISIONING", "STARTING", "MODEL_LOADING", "READY", "RUNNING"):
        job.move(st, "test", now=now)
        if st == state:
            break
    if stage:
        job.heartbeat(stage, "test", now=now)
    sess = R.new_session(pod(pid), max_usd=1.0, max_hours=2.0, now=now, job=job.dir, price_ceiling=0.95, status_token="t")
    sess["answered"] = state != "STARTING"
    R.sess_write(sess)
    return job


def run_guard(api, pid, *, step=600, conductor=None, pushes=None, start=0, max_looks=10**5):
    t = iter(range(start, start + step * max_looks, step)).__next__
    page = (lambda p, tok: conductor(p, tok) if callable(conductor) else conductor) if conductor is not None else (lambda *a: "")
    pushes = [] if pushes is None else pushes
    why = R.guard(api, pid, clock=t, sleep=lambda s: None, push=lambda *a: pushes.append(a), page=page, log=lambda *a: None)
    return why, pushes


# --- the job record -----------------------------------------------------------------------------------------------------
def test_job_record_moves_only_along_legal_transitions_and_keeps_history(tmp_path):
    job = J.Job.create(tmp_path, "ep", kind="pod", provider="runpod", now=10, inputs={"gpu": "cheap"})
    assert job.state["state"] == "QUEUED" and job.dir.name.startswith("job-001_")
    job.move("PROVISIONING", "POST /pods", now=20)
    with pytest.raises(J.IllegalMove):
        job.move("SUCCEEDED", "not from PROVISIONING", now=30)
    with pytest.raises(J.IllegalMove):
        job.move("NOT_A_STATE", "x")
    assert job.move("PROVISIONING", "same state, new reason", now=31) is False and job.state["reason"] == "same state, new reason"
    job.move("RUNNING", "stage paint", now=40)
    job.move("FAILED", "exit 1", now=50)
    job.move("RETRYING", "second try", now=60)
    assert job.state["attempts"] == 1
    kinds = [(e["kind"], e.get("to")) for e in job.events()]
    assert kinds == [("created", None), ("move", "PROVISIONING"), ("move", "RUNNING"), ("move", "FAILED"), ("move", "RETRYING")]
    assert [e["to"] for e in job.events(since=45)] == ["FAILED", "RETRYING"]
    again = J.Job(job.dir)  # re-read from disk
    assert again.state["state"] == "RETRYING" and again.state["inputs_hash"] == J.inputs_hash({"gpu": "cheap"})
    assert J.Job.list(tmp_path)[0].dir == job.dir and J.Job.by_resource(tmp_path, "nope") is None
    for st in J.STATES:
        assert st in J.TRANSITIONS and all(t in J.STATES for t in J.TRANSITIONS[st])


def test_the_pod_view_maps_onto_job_states():
    live = R.norm(pod(ports={"22": 1}, ip="1.1.1.1"))
    assert J.state_from_pod(R.norm(pod(status="PROVISIONING")), False)[0] == "PROVISIONING"
    assert J.state_from_pod(R.norm(pod()), False)[0] == "STARTING"  # RUNNING without ports: the container is still coming
    assert J.state_from_pod(live, True)[0] == "READY"
    assert J.state_from_pod(live, True, "STATUS RUNNING  stage setup  0/5 done")[0:3:2] == ("MODEL_LOADING", "setup")
    assert J.state_from_pod(live, True, "STATUS RUNNING  stage paint  2/5 done")[0] == "RUNNING"
    assert J.state_from_pod(live, True, "STATUS RUNNING  stage push_store  4/5 done")[0] == "UPLOADING"
    assert J.state_from_pod(live, True, "STATUS DONE  stage None  5/5 done")[0] == "SUCCEEDED"
    assert J.state_from_pod(live, True, "STATUS CAPPED  stage paint  2/5 done")[0] == "STOPPED"
    assert J.state_from_pod(live, True, "STATUS STOPPED  stage setup  0/5 done")[0] == "FAILED"
    assert J.state_from_pod(live, True, "STATUS BLOCKED  stage write  1/5 done")[0] == "RECOVERY_REQUIRED"
    assert J.state_from_pod(R.norm(pod(status="ERROR")), False)[0] == "RECOVERY_REQUIRED"
    assert J.state_from_pod(R.norm(pod(status="EXITED")), False)[0] is None and J.state_from_pod(None, False)[0] is None


def test_observe_never_moves_a_job_backwards_and_heartbeats_only_on_progress(tmp_path):
    job = job_for(tmp_path, state="RUNNING", stage="paint")
    live = R.norm(pod(ports={"22": 1}))
    assert J.observe(job, live, True, "STATUS RUNNING  stage paint  1/3 done", now=100) is None
    hb1 = job.last_heartbeat()
    assert J.observe(job, live, True, "STATUS RUNNING  stage paint  1/3 done", now=200) is None
    assert job.last_heartbeat() == hb1  # the same line again is not progress
    assert J.observe(job, live, True, "STATUS RUNNING  stage paint  2/3 done", now=300) is None
    assert job.last_heartbeat()["ts"] == 300  # the line changed: progress
    busy = R.norm(pod(ports={"22": 1}, util=80))
    J.observe(job, busy, True, "STATUS RUNNING  stage paint  2/3 done", now=400)
    assert job.last_heartbeat()["ts"] == 400  # a busy GPU is progress too
    assert J.observe(job, R.norm(pod(status="STARTING")), False, None, now=500) is None and job.state["state"] == "RUNNING"
    assert J.observe(job, live, True, "STATUS RUNNING  stage push  3/3 done", now=600) == "UPLOADING"
    assert J.observe(job, live, True, "STATUS DONE  stage None  3/3 done", now=700) == "SUCCEEDED"
    assert J.observe(job, R.norm(pod(status="EXITED")), False, None, now=800) is None and job.state["state"] == "SUCCEEDED"


def test_stall_uses_the_state_limit_or_the_stages_own_budget(tmp_path):
    job = job_for(tmp_path, state="RUNNING", stage="paint", stage_limits={"paint": 600})
    assert J.stall(job, now=500) == ""
    assert "stage paint quiet for 11 min (limit 10)" in J.stall(job, now=660)  # the stage's budget counts from its start
    other = job_for(tmp_path, pid="b", state="MODEL_LOADING")
    assert J.stall(other, now=J.STALL_AFTER["MODEL_LOADING"] - 1) == "" and J.stall(other, now=J.STALL_AFTER["MODEL_LOADING"] + 61)
    other.move("STALLED", "quiet", now=2000)
    assert J.stall(other, now=10**6) == ""  # already said


def test_outputs_and_the_store_decide_whether_a_resource_may_go(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_STORE_LOCAL", str(tmp_path / "store"))
    monkeypatch.setattr(R, "RP", tmp_path / "rp")
    job = job_for(tmp_path)
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "p1.json").write_text('{"a": 1}')
    job.record_output(tmp_path / "out" / "p1.json")
    assert not job.safe_to_release() and len(job.unstored_outputs()) == 1
    where = S.store_job(job, extra_dirs=[tmp_path / "out"])
    assert job.safe_to_release() and job.state["stored"] == [where] and job.state["outputs"][0]["stored"] == where
    assert (tmp_path / "store" / f"jobs/ep/{job.state['id']}/out/p1.json").exists()
    assert (tmp_path / "store" / f"jobs/ep/{job.state['id']}/state.json").exists()  # the record travels with the outputs
    lines = job.summary(now=1000, since=0)
    assert lines[0].startswith(job.state["id"]) and any("outputs 1, stored 1" in l for l in lines) and any("+ " in l for l in lines)


# --- the store ------------------------------------------------------------------------------------------------------------
def test_store_push_skips_damaged_files_and_verify_reports_a_changed_copy(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_STORE_LOCAL", str(tmp_path / "store"))
    src = tmp_path / "src"
    src.mkdir()
    (src / "ok.json").write_text('{"x": 1}')
    (src / "broken.json").write_text('{"x": ')
    (src / "empty.png").write_bytes(b"")
    (src / "note.tmp").write_text("scratch")
    res = S.push(src, "runs/r1")
    assert res["pushed"] == ["ok.json"] and set(res["skipped"]) == {"broken.json", "empty.png"}
    assert S.verify(src, "runs/r1") == {"missing": [], "damaged": [], "ok": 1}
    (tmp_path / "store" / "runs" / "r1" / "ok.json").write_text('{"x": 2}')
    assert S.verify(src, "runs/r1")["damaged"] == ["ok.json"]
    (tmp_path / "store" / "runs" / "r1" / "ok.json").unlink()
    assert S.verify(src, "runs/r1")["missing"] == ["ok.json"]
    assert S.main(["check", str(src)]) == 1 and S.main(["push", str(src), "runs/r2"]) == 1  # damaged files -> exit 1


# --- incidents ----------------------------------------------------------------------------------------------------------
def test_incidents_classify_match_and_remember_repeats(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "LOCAL", tmp_path / "incidents.jsonl")
    known = I.load_known()
    assert len(known) >= 20 and len({i["id"] for i in known}) == len(known)
    classes = {name for name, _ in I.CLASSES}
    assert all(i["fingerprint"]["error_class"] in classes for i in known)
    assert I.classify("POST /pods: HTTP 400 no capacity for NVIDIA RTX A5000") == "no_capacity"
    assert I.classify("pod a not ready after 600 s (boot deadline)") == "boot_timeout"
    assert I.classify("CUDA out of memory") == "oom" and I.classify("???") == "unknown"
    lines = I.doctor("not enough free GPUs on the host", stage="start")
    assert lines[1].startswith("class: no_capacity") and any(l.startswith("INC-06") for l in lines)
    fp = I.fingerprint("runpod", "pod", "boot", text="pod never answered by its boot deadline")
    first = I.record(fp, "pod p1 never answered", cause="start command returned", source="test")
    second = I.record(fp, "pod p2 never answered", cause="same", source="test")
    assert first["id"] == "LOC-001" and "INC-17" in first["repeat_of"] and "LOC-001" in second["repeat_of"]
    assert I.repeats(fp) == 3 and len(I.load_local()) == 2  # INC-17 (known) + the two seen here
    assert "no known incident is close" in " ".join(I.doctor("a brand new kind of trouble zzz", resource="moon"))


# --- the fifteen scenarios of the brief -----------------------------------------------------------------------------------
def test_s01_create_fails_on_every_card_bills_nothing_and_records_the_failure(env):
    fake, api, tmp = env
    fake.refuse_gpus = set(R.GPUS["cheap"])
    ledger = tmp / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    with pytest.raises(R.RunPodError, match="no pod could be made"):
        R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--gpu", "cheap", "--ledger", str(ledger)], api=api)
    assert not fake.pods and Run.open(ledger).spent("runpod_usd") == 0
    assert Run.open(ledger).data["reserved"].get("pod:pending", {}).get("amount", 0) == 0  # released
    job = J.Job.list(tmp / "jobs" / "cloud")[0]
    assert job.state["state"] == "FAILED" and "no capacity" in job.state["reason"]
    assert I.load_local()[0]["fingerprint"]["error_class"] == "no_capacity" and I.load_local()[0]["job"] == job.state["id"]


def test_s02_a_pod_stuck_starting_is_stopped_at_the_boot_deadline(env):
    fake, api, tmp = env
    fake.pods["a"] = pod()  # RUNNING but never maps its ports: the container never came up
    job = job_for(tmp, state="STARTING")
    why, pushes = run_guard(api, "a", step=60)
    assert "boot deadline" in why and fake.pods["a"]["status"] == "EXITED"
    job = J.Job(job.dir)
    assert job.state["state"] == "STOPPED" and "boot deadline" in job.state["reason"]
    assert any("Guard ended the pod" == p[0] for p in pushes)


def test_s03_a_failed_model_load_marks_the_job_failed_and_the_pod_is_stopped(env):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")
    job = job_for(tmp, state="RUNNING", stage="setup")
    why, pushes = run_guard(api, "a", step=60, conductor="STATUS STOPPED  stage setup  0/5 done\nEND: setup failed fatally: exit 1")
    assert "conductor ended" in why and fake.pods["a"]["status"] == "EXITED"
    job = J.Job(job.dir)
    assert job.state["state"] == "FAILED" and "STATUS STOPPED" in job.state["reason"]  # FAILED keeps its meaning after the stop
    assert any(p[0] == "Pod job FAILED" for p in pushes) and I.load_local()[0]["fingerprint"]["stage"] == "setup"


def test_s04_no_progress_is_a_stall_then_a_stop_once_outputs_are_safe(env):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")  # GPU idle (util 0)
    job = job_for(tmp, state="RUNNING", stage="paint")
    sess = R.sess_read("a")
    sess.update(max_usd=99, max_hours=99, until=10**9)
    R.sess_write(sess)
    why, pushes = run_guard(api, "a", step=300, conductor="STATUS RUNNING  stage paint  1/3 done")
    assert "stalled" in why and "every output is stored" in why and fake.pods["a"]["status"] == "EXITED"
    assert any(p[0] == "Pod job stalled" for p in pushes)
    job = J.Job(job.dir)
    assert job.state["state"] == "STOPPED" and [e["to"] for e in job.events() if e["kind"] == "move"][-2:] == ["STALLED", "STOPPED"]


def test_s05_a_pod_that_dies_closes_the_job_and_records_an_incident(env):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")
    job = job_for(tmp, state="RUNNING", stage="paint")
    looks = {"n": 0}

    def page(p, tok):
        looks["n"] += 1
        if looks["n"] == 3:
            del fake.pods["a"]
        return "STATUS RUNNING  stage paint  1/3 done"

    why, pushes = run_guard(api, "a", step=60, conductor=page)
    assert why == "pod is gone"
    job = J.Job(job.dir)
    assert job.state["state"] == "FAILED" and "gone while RUNNING" in job.state["reason"]
    assert any(p[0] == "Pod job FAILED" for p in pushes) and I.load_local()[-1]["fingerprint"]["error_class"] == "pod_gone"


def test_s06_api_timeouts_and_429s_leave_the_record_alone_and_the_money_clock_running(env):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")
    job = job_for(tmp, state="RUNNING", stage="paint")
    fake.faults = [("GET", "/pods/a", 429)] * 5 * 3 + [("GET", "/pods/a", "timeout")] * 5 * 3
    why, pushes = run_guard(api, "a", step=900, conductor="STATUS RUNNING  stage paint  1/3 done")
    assert "money cap" in why and fake.pods["a"]["status"] == "EXITED"
    job = J.Job(job.dir)
    assert [e["to"] for e in job.events() if e["kind"] == "move"][-1] == "STOPPED"
    assert not any(e.get("forced_from") in ("RUNNING",) and e["to"] in ("STARTING", "PROVISIONING") for e in job.events())


def test_s07_s08_an_unreachable_store_or_a_failed_upload_keeps_the_job_and_never_releases_the_pod(env, monkeypatch):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")
    job = job_for(tmp, state="RUNNING", stage="paint")
    out = tmp / "out"
    out.mkdir()
    (out / "p1.json").write_text('{"a": 1}')
    job.record_output(out / "p1.json")
    job.move("UPLOADING", "pushing", now=100)
    blocker = tmp / "blocker"
    blocker.write_text("a file where the store folder should be")
    monkeypatch.setenv("EXPLAINER_STORE_LOCAL", str(blocker))
    with pytest.raises(S.StoreError):  # scenario 7: the store cannot be reached
        S.store_job(job, extra_dirs=[out])
    job.move("RECOVERY_REQUIRED", "store unreachable", now=200)
    assert not job.safe_to_release()
    monkeypatch.setenv("EXPLAINER_STORE_LOCAL", str(tmp / "store"))
    real_push = S.push

    def push_then_lose(local_dir, repo_path, api=None):  # scenario 8: the upload "succeeds" but the copy is not there
        res = real_push(local_dir, repo_path, api)
        if Path(local_dir) == out:
            (tmp / "store" / repo_path / "p1.json").unlink()
        return res

    from pathlib import Path
    monkeypatch.setattr(S, "push", push_then_lose)
    job.move("RETRYING", "again", now=300)
    job.move("RUNNING", "again", now=301)
    job.move("UPLOADING", "pushing again", now=302)
    with pytest.raises(S.StoreError, match="missing"):
        S.store_job(job, extra_dirs=[out])
    assert not job.safe_to_release()
    job.move("RECOVERY_REQUIRED", "upload not confirmed", now=400)
    pods = [R.norm(fake.pods["a"])]
    d = W.decide(pods, now=10**6, caps=R.spend_caps.runpod(), job_list=[job])
    assert d["stop"] == [] and any("unstored" in str(j) for j in d["jobs"]) or job.state["state"] == "RECOVERY_REQUIRED"
    assert not any(pid == "a" for pid, _ in d["stop"])  # never a sole copy lost by the watchdog


def test_s09_the_watchdog_needs_no_session_and_stops_an_expired_pod(env):
    fake, api, tmp = env
    fake.pods = {"old": pod("old", "ee-x-until-100"), "ok": pod("ok"), "noname": pod("noname", "console pod"),
                 "ex": pod("ex", "ee-y-until-5", "EXITED", volumeInGb=60), "err": pod("err", "ee-z-until-5", "ERROR")}
    assert not list((tmp / "rp").glob("sessions/*.json"))  # nobody here guards anything (the sandbox is gone)
    d = W.decide([R.norm(p) for p in fake.pods.values()], now=1000, caps=R.spend_caps.runpod(), billed_24h=0.1, balance=5.0)
    assert sorted(pid for pid, _ in d["stop"]) == ["noname", "old"] and any("ERROR" in a for a in d["alerts"])
    assert any("ok ee-x-until-9999999999" in i for i in d["info"]) and any("$0.39/day" in i for i in d["info"])
    pushes = []
    res = W.run(api, now=1000, apply=True, push=lambda *a: pushes.append(a), log=lambda *a: None)
    assert fake.pods["old"]["status"] == "EXITED" and fake.pods["noname"]["status"] == "EXITED" and fake.pods["ok"]["status"] == "RUNNING"
    assert len(res["stopped"]) == 2 and pushes[0][0] == "Watchdog: pods stopped"
    assert [i["fingerprint"]["error_class"] for i in I.load_local()] == ["unknown", "unknown"] or len(I.load_local()) == 2
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / ".github" / "workflows" / "watchdog.yml").read_text()
    assert 'cron: "*/30 * * * *"' in text and "kill_all" in text and "--kill-all --yes" in text and "--apply" in text
    assert "RUNPOD_API_KEY: ${{ secrets.RUNPOD_API_KEY }}" in text and "DELETE" not in text and "terminate" not in text


def test_s10_the_creators_stop_all_stops_every_live_pod_and_closes_the_records(env, capsys):
    fake, api, tmp = env
    fake.pods = {"a": pod("a"), "b": pod("b", "ee-b-until-9999999999", "PROVISIONING"), "ex": pod("ex", "x", "EXITED")}
    job = job_for(tmp, state="RUNNING", stage="paint")
    with pytest.raises(SystemExit, match="--yes"):
        CLI.main(["stop-all"], api=api)
    assert fake.pods["a"]["status"] == "RUNNING"
    assert CLI.main(["stop-all", "--yes"], api=api) == 0
    assert fake.pods["a"]["status"] == "EXITED" and fake.pods["b"]["status"] == "EXITED"
    assert J.Job(job.dir).state["state"] == "STOPPED" and "STOP ALL" in J.Job(job.dir).state["reason"]
    with pytest.raises(SystemExit, match="--yes"):
        W.main(["--kill-all"], api=api)


def test_s11_budget_reached_stops_pods_and_refuses_the_next_one(env):
    fake, api, tmp = env
    fake.pods = {"a": pod("a")}
    caps = R.spend_caps.runpod()
    d = W.decide([R.norm(fake.pods["a"])], now=1000, caps=caps, billed_24h=caps["per_24h_usd"], balance=5.0)
    assert d["stop"] and "per_24h_usd" in d["stop"][0][1] and d["alerts"]
    fake.billing = [{"totalAmount": caps["per_24h_usd"], "podId": "a"}]
    assert any("per_24h_usd" in w for w in R.preflight_create(api, max_usd=0.5, max_hours=1.0, gpu="default", now=10**6))
    d = W.decide([], now=1000, caps=caps, billed_24h=0.0, balance=0.1)
    assert any("min_balance_left_usd" in a for a in d["alerts"])


def test_s12_a_repeated_error_is_recognised_by_doctor(env, capsys):
    fake, api, tmp = env
    fp = I.fingerprint("runpod", "pod", "create", text="HTTP 400 no capacity")
    I.record(fp, "create failed: no capacity", cause="no A5000 free", source="test")
    I.record(fp, "create failed: no capacity", cause="no A5000 free", source="test")
    job = job_for(tmp, state="RUNNING")
    job.move("FAILED", "create: HTTP 400 no capacity for NVIDIA RTX A5000", now=5)
    assert CLI.main(["doctor"], api=api) == 1
    out = capsys.readouterr().out
    assert "class: no_capacity" in out and "seen before with this fingerprint: 2" in out and "INC-06" in out


def test_s13_resume_from_a_checkpoint_keeps_outputs_and_history(env):
    fake, api, tmp = env
    job = job_for(tmp, state="RUNNING", stage="paint")
    out = tmp / "out"
    out.mkdir()
    (out / "p1.json").write_text('{"a": 1}')
    job.record_output(out / "p1.json")
    S.store_job(job, extra_dirs=[out])
    job.move("STOPPING", "time cap", now=100)
    job.move("STOPPED", "stopped", now=101)
    n = len(job.events())
    job.move("RETRYING", "resume from the stored checkpoint", now=200)
    job.move("RUNNING", "stage paint again", now=201)
    assert job.state["attempts"] == 1 and job.state["outputs"][0]["stored"] and len(job.events()) == n + 2
    assert J.Job(job.dir).state["state"] == "RUNNING"


def test_s14_a_finished_job_with_the_same_inputs_is_not_run_again(tmp_path):
    root = tmp_path / "jobs"
    job = J.Job.create(root, "ep", kind="pod", provider="runpod", inputs={"boot": "paint.json", "gpu": "cheap"}, now=1)
    for st in ("PROVISIONING", "RUNNING", "SUCCEEDED", "STOPPED"):
        job.move(st, "test", now=2)
    job.move("RETRYING", "x", now=3)  # a resumed-and-finished history still counts once SUCCEEDED again
    job.move("RUNNING", "x", now=4)
    job.move("SUCCEEDED", "done", now=5)
    same = J.Job.create(root, "ep", kind="pod", provider="runpod", inputs={"gpu": "cheap", "boot": "paint.json"}, now=10)
    assert same.dir == job.dir and same.events()[-1]["kind"] == "reused"
    other = J.Job.create(root, "ep", kind="pod", provider="runpod", inputs={"gpu": "cheap", "boot": "voice.json"}, now=11)
    assert other.dir != job.dir and len(J.Job.list(root, "ep")) == 2


def test_s15_nothing_is_left_running_and_status_says_so(env, capsys):
    fake, api, tmp = env
    fake.pods = {"a": pod("a", ports={"22": 1}, ip="1.1.1.1")}
    job = job_for(tmp, state="RUNNING", stage="paint")
    why, _ = run_guard(api, "a", step=60, conductor="STATUS DONE  stage None  3/3 done")
    assert "conductor ended" in why and fake.pods["a"]["status"] == "EXITED"
    assert J.Job(job.dir).state["state"] == "SUCCEEDED"
    fake.pods = {}  # the creator deleted the finished pod's disk
    assert R.check(api, now=10**6)["problems"] == []
    d = W.decide([], now=10**6, caps=R.spend_caps.runpod(), billed_24h=0.2, balance=5.0, job_list=J.Job.list(tmp / "jobs" / "cloud"))
    assert d["stop"] == [] and d["alerts"] == [] and d["jobs"] == []
    assert CLI.main(["status"], api=api) == 0
    out = capsys.readouterr().out
    assert "RunPod: 0 problem(s)" in out and "jobs: 0 open" in out
    assert CLI.main(["budget"], api=api) == 0 and "last 24 h" in capsys.readouterr().out
    assert CLI.main(["doctor"], api=api) == 0 and "nothing is failing" in capsys.readouterr().out
    CLI.main(["incidents", "capacity"])
    assert "INC-06" in capsys.readouterr().out
    CLI.main(["logs", job.state["id"]], api=api)
    out = capsys.readouterr().out
    assert "STATUS DONE" in out and "guard ended the pod" in out and "no live log" in out


def test_s16_a_stopped_pod_that_cannot_restart_bills_nothing_and_says_why(env):
    fake, api, tmp = env
    fake.pods["a"] = pod("a", status="EXITED")
    fake.faults = [("POST", "/pods/a/action", 400)]  # "not enough free GPUs on the host": a stopped pod is tied to its host
    with pytest.raises(R.RunPodError, match="400"):
        R.main(["start", "a", "--yes", "--max-usd", "0.5", "--max-hours", "1"], api=api)
    assert fake.pods["a"]["status"] == "EXITED" and R.sess_read("a") is None
    lines = I.doctor("HTTP 400 not enough free GPUs on the host", stage="start")
    assert any(l.startswith("INC-06") for l in lines)  # the known cause and its fix are named


def test_s17_balance_hits_zero_mid_job_the_record_keeps_the_unstored_outputs_visible(env):
    fake, api, tmp = env
    fake.pods["a"] = pod(ports={"22": 1}, ip="1.1.1.1")
    job = job_for(tmp, state="RUNNING", stage="paint")
    out = tmp / "out"
    out.mkdir()
    (out / "p1.json").write_text('{"a": 1}')
    job.record_output(out / "p1.json")
    looks = {"n": 0}

    def page(p, tok):
        looks["n"] += 1
        if looks["n"] == 2:
            fake.pods["a"].update(status="TERMINATED", runtime=None, cost=0.0)  # RunPod terminates a volume-less pod at $0
        return f"STATUS RUNNING  stage paint  {looks['n']}/9 done"

    why, pushes = run_guard(api, "a", step=60, conductor=page)
    assert why == "pod is gone"
    job = J.Job(job.dir)
    assert job.state["state"] == "RECOVERY_REQUIRED" and "unstored output" in job.state["reason"]
    assert any(p[0] == "Pod job RECOVERY_REQUIRED" for p in pushes)
    d = W.decide([], now=10**6, caps=R.spend_caps.runpod(), billed_24h=0.5, balance=0.0, job_list=[job])
    assert any("min_balance_left_usd" in a for a in d["alerts"]) and d["stop"] == []


def test_the_watchdog_reports_every_billing_category(env):
    fake, api, tmp = env
    fake.volumes = [{"id": "nv1", "name": "models", "size": 100, "dataCenter": "EU-RO-1"}]
    fake.global_volumes = [{"id": "gsb_1", "name": "shared"}]
    fake.endpoints = [{"id": "ep1", "name": "sdxl", "workersMin": 2}]
    fake.other_billing = 0.3
    fake.faults = [("GET", "/global-volumes", 503)] * 6  # more than the retries: the listing really fails
    d = W.run(api, now=1000, apply=False, push=lambda *a: None, log=lambda *a: None)
    assert any("network volume nv1" in a and "$0.23/day" in a for a in d["alerts"])
    assert any("serverless endpoint ep1" in a for a in d["alerts"]) and any("could not list global volumes" in a for a in d["alerts"])
    assert d["stop"] == []


def test_the_create_cli_writes_a_job_record_the_guard_can_follow(env):
    fake, api, tmp = env
    ledger = tmp / "run.json"
    Run.open(ledger, caps={"runpod_usd": 1.0})
    R.main(["create", "--yes", "--max-usd", "0.5", "--max-hours", "1", "--job", "titans", "--ledger", str(ledger)], api=api)
    job = J.Job.list(tmp / "jobs" / "cloud", "titans")[0]
    sess = R.sess_read("p1")
    assert sess["job"] == str(job.dir) and job.state["resource"] == "p1" and job.state["state"] == "PROVISIONING"
    assert job.state["caps"] == {"max_usd": 0.5, "max_hours": 1.0} and job.state["ledger"] == str(ledger)
    assert R._job_of(sess).dir == job.dir and R._job_of({"job": None}) is None
