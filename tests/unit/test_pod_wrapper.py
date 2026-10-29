"""CR-01..06, CR-15: the real ``pod_wrapper.sh`` under bash with stubbed curl, nvidia-smi and uploader. No network, no pod, no
money. Each run takes a few seconds (the loop and polling intervals are shortened through the wrapper's env)."""
import os
import stat
import subprocess
import time

import pytest

from explainer_engine.cloud import runpod as R

CURL = """#!/bin/bash
echo "$*" >> "$STUB_DIR/curl.log"
out=""; w=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift;; -w) w=$2; shift;; http*) url=$1;; esac; shift; done
case "$url" in
  */action) echo stop >> "$STUB_DIR/stops"; [ "$STUB_STOP_FAILS" = 1 ] && exit 22; exit 0;;
  */graphql) echo gqlstop >> "$STUB_DIR/stops"; exit 0;;
  */v2/pods/*) [ -n "$out" ] && echo '{"cost": 0.74}' > "$out"; [ -n "$w" ] && printf '%s' "${STUB_KEY_CODE:-200}"; exit 0;;
  *) [ -n "$out" ] && { cp "$STUB_SCRIPT" "$out" 2>/dev/null || exit 22; }; exit 0;;
esac
"""
UPLOAD = """#!/bin/bash
n=$(cat "$STUB_DIR/up_n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$STUB_DIR/up_n"
if [ "$STUB_UPLOAD_FAIL" = always ] || { [ -n "$STUB_UPLOAD_FAIL" ] && [ "$n" -le "$STUB_UPLOAD_FAIL" ]; }; then exit 1; fi
mkdir -p "$STUB_DIR/hf"; cp -r "$EE_OUT"/. "$STUB_DIR/hf"/; exit 0
"""
UPLOAD_BEAT = """#!/bin/bash
cp "$EE_OUT/beat.txt" "$STUB_DIR/hf_beat.txt"; cat "$EE_OUT/beat.txt" >> "$STUB_DIR/beat_history"; exit 0
"""
SMI_FAIL = "#!/bin/bash\nexit 9\n"


def _running(pid):
    try:
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0] != "Z"   # a zombie is dead
    except OSError:
        return False


def _exe(path, text):
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def pod(tmp_path):
    stub = tmp_path / "stub"
    stub.mkdir()
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    _exe(bin_ / "curl", CURL)
    _exe(stub / "upload.sh", UPLOAD)
    _exe(stub / "upload_beat.sh", UPLOAD_BEAT)
    out = tmp_path / "out"

    def run(script, *, timeout=60, smi=None, **env):
        (stub / "job.sh").write_text(script)
        if smi:
            _exe(bin_ / "nvidia-smi", smi)
        e = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "STUB_DIR": str(stub), "STUB_SCRIPT": str(stub / "job.sh"),
             "EE_OUT": str(out), "EE_STATE": str(tmp_path / "st"), "EE_SCRIPT": str(tmp_path / "pod.sh"),
             "RUNPOD_API_KEY": "k", "RUNPOD_POD_ID": "pp", "EE_PASS_S": "1", "EE_POLL_S": "0.1", "EE_RETRY_S": "0.1",
             "EE_STOP_RETRY_S": "0.1", "EE_MAX_STOPS": "2", "EE_KILL_WAIT_S": "2", "EE_UPLOAD_GRACE_S": "1", "EE_CAP_GRACE_S": "1",
             "EE_UPLOAD_CMD": str(stub / "upload.sh"), "EE_UPLOAD_BEAT_CMD": str(stub / "upload_beat.sh"), "EE_SCRIPT_URL": "https://x/pod.sh",
             "HF_TOKEN": "t", "EE_CREATED": str(int(time.time())), "EE_LIFETIME_S": "3600", "EE_MAX_USD": "5", "EE_PRICE": "0.34",
             "EE_DISK_H": "0.05", "EE_JOB": "job-1"}
        e.update({k: str(v) for k, v in env.items()})
        p = subprocess.run(["bash", str(R.WRAPPER)], env=e, capture_output=True, text=True, timeout=timeout)
        beat = (out / "beat.txt").read_text() if (out / "beat.txt").exists() else ""
        stops = (stub / "stops").read_text().split() if (stub / "stops").exists() else []
        return p, R.parse_beat(beat), stops, stub
    run.out = out
    return run


def test_the_wrapper_is_valid_bash_and_names_no_v1_route():
    assert subprocess.run(["bash", "-n", str(R.WRAPPER)]).returncode == 0
    text = R.WRAPPER.read_text()
    assert "rest.runpod.io" not in text and "/v1/" not in text and "DELETE" not in text and "terminate" not in text  # CR-15
    assert "api.runpod.io/v2/pods/$RUNPOD_POD_ID/action" in text and "podStop" in text


def test_a_script_that_finishes_ends_with_done_uploaded_and_the_pod_stopped(pod):
    p, b, stops, stub = pod('echo "step 3/9" > $EE_OUT/progress.txt\necho result > $EE_OUT/r.txt\n')
    assert b["word"] == "DONE" and b["rc"] == 0 and b["upload_fail"] == 0
    assert b["boot"]["key"] == "200" and b["boot"]["job"] == "job-1" and b["boot"]["pod"] == "pp"
    assert float(b["boot"]["price"]) == 0.74            # the probed cost is higher than the price in the body (CR-03)
    assert (stub / "hf" / "r.txt").read_text() == "result\n" and stops == ["stop", "stop"]
    assert b["progress"] == "step 3/9"


def test_a_script_that_crashes_writes_failed_without_its_help_and_the_guard_stops_the_pod(pod):
    """P1a criterion (a): the dead EXIT trap of 2026-10-29 is replaced by the wrapper's end sequence."""
    from test_runpod import FakeRunPod, pod as fake_pod
    p, b, stops, _ = pod("echo partial > $EE_OUT/r.txt\nexit 3\n")
    assert b["word"] == "FAILED" and b["rc"] == 3 and stops
    text = (pod.out / "beat.txt").read_text()
    sess = R.new_session(fake_pod("a"), max_usd=1.0, max_hours=2.0, now=0, heartbeat="datasets/o/r:run/out/beat.txt")
    assert R.heartbeat_step(sess, 600, beat=lambda s: 500.0, text=lambda s: text) == "done"
    assert sess["job_ended"].startswith("FAILED rc=3")
    fake = FakeRunPod()
    fake.pods["a"] = fake_pod("a")
    api = R.Api("k", transport=fake, sleep=lambda s: None)
    t = iter(range(0, 10**7, 60)).__next__
    real = R.heartbeat_step
    R.heartbeat_step = lambda s, now, push=None: real(s, now, beat=lambda x: 250.0, text=lambda x: text)
    try:
        why = R.guard(api, "a", clock=t, sleep=lambda s: None, push=lambda *a: None, page=lambda *a: "", log=lambda *a: None)
    finally:
        R.heartbeat_step = real
    assert "FAILED rc=3" in why and fake.pods["a"]["status"] == "EXITED"


def test_failed_uploads_are_counted_retried_for_the_grace_and_end_as_failed_upload(pod):
    """P1a criterion (b), wrapper half: the pod says so instead of swallowing it, and still stops."""
    p, b, stops, stub = pod("echo x > $EE_OUT/r.txt\nsleep 3.5\n", STUB_UPLOAD_FAIL="always")
    assert b["word"] == "FAILED_UPLOAD" and b["rc"] == 0 and b["upload_fail"] >= 3 and b["unstored"] >= 1
    history = (stub / "beat_history").read_text()
    fails = [int(x) for x in __import__("re").findall(r"upload_fail=(\d+)", history)]
    assert max(fails) >= 2 and fails == sorted(fails)    # the count rose in the beats the pod kept sending
    assert stops                                            # a pod that cannot upload still stops (the guard decides about recovery)


def test_a_failing_pass_does_not_stop_the_job_and_recovers(pod):
    p, b, stops, stub = pod("echo x > $EE_OUT/r.txt\nsleep 3\n", STUB_UPLOAD_FAIL="2")
    assert b["word"] == "DONE" and b["upload_fail"] == 0 and (stub / "hf" / "r.txt").exists()


def test_the_money_deadline_caps_the_script_after_a_graceful_term_and_uploads_first(pod):
    """P1a criterion (e), wrapper half: SIGTERM to the process group, then the end sequence with the short grace."""
    p, b, stops, stub = pod("echo started > $EE_OUT/r.txt\nsleep 120 &\necho $! > $STUB_DIR/child\nwait\n", EE_LIFETIME_S="4", EE_CAP_GRACE_S="1")
    assert b["word"] == "CAPPED" and (stub / "hf" / "r.txt").exists() and stops
    child = int((stub / "child").read_text())
    time.sleep(0.3)
    assert not _running(child)                              # the whole group went, not only the script's shell


def test_the_wrapper_deadline_equals_deadline_of(pod):
    created = int(time.time())
    for life, usd, price in ((7200, 3.0, 0.34), (600, 3.0, 1.69), (3600, 0.5, 2.59)):
        p, b, _, _ = pod("exit 0\n", EE_CREATED=created, EE_LIFETIME_S=life, EE_MAX_USD=usd, EE_PRICE=price, EE_CAP_GRACE_S=300,
                         STUB_KEY_CODE="403")
        want = R.deadline_of(created, life, usd, price, 0.05, grace=300)
        assert int(b["boot"]["deadline"]) == want, (life, usd, price)


def test_a_bad_host_never_runs_the_script_and_says_so(pod):
    p, b, stops, stub = pod("echo ran > $STUB_DIR/ran\n", smi=SMI_FAIL, EE_REQUIRE_GPU_CHECK="1")
    assert b["word"] == "BAD_HOST" and b["rc"] == 9 and not (stub / "ran").exists() and stops


@pytest.mark.parametrize("code,key", [("401", "401"), ("000", "000")])
def test_the_key_probe_is_written_to_line_one(pod, code, key):
    p, b, stops, _ = pod("exit 0\n", STUB_KEY_CODE=code)
    assert b["boot"]["key"] == key and float(b["boot"]["price"]) == 0.34 and b["word"] == "DONE"


def test_no_key_in_the_pod_is_none_and_the_stop_says_it_could_not(pod):
    p, b, stops, _ = pod("exit 0\n", RUNPOD_API_KEY="", STUB_STOP_FAILS="1")
    assert b["boot"]["key"] == "none" and b["word"] == "DONE"
    assert "no key could stop this pod" in p.stdout + p.stderr or stops.count("gqlstop") >= 1


def test_a_script_that_cannot_be_downloaded_ends_failed(pod, tmp_path):
    p, b, stops, stub = pod("exit 0\n", STUB_SCRIPT=str(tmp_path / "missing.sh"))
    assert b["word"] == "FAILED" and b["rc"] == 22 and stops


def test_parse_beat_reads_every_word_and_the_old_forms():
    assert R.parse_beat("DONE 2026-10-24T17:00Z")["word"] == "DONE"
    assert R.parse_beat("FAILED rc=1")["rc"] == 1
    assert R.parse_beat("BAD_HOST cuda check rc=124 driver 550")["word"] == "BAD_HOST"
    assert R.parse_beat("11:52:18")["word"] is None
    full = ("BOOT key=200 job=j pod=p price=0.5 deadline=100\n"
            "FAILED_UPLOAD rc=0 2026-10-29T18:00:00Z progress=step 4/9 upload_fail=7 unstored=3\n")
    b = R.parse_beat(full)
    assert b["word"] == "FAILED_UPLOAD" and b["progress"] == "step 4/9" and b["upload_fail"] == 7 and b["unstored"] == 3
    assert b["boot"] == {"key": "200", "job": "j", "pod": "p", "price": "0.5", "deadline": "100"}
    assert R.parse_beat("ALIVE 2026-10-29T18:00:00Z progress= upload_fail=0 unstored=0")["word"] == "ALIVE"
