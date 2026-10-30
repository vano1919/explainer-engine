"""P12d (docs/CLOUD_RUNBOOK.md, "Drills"): every "what if" of the pod protocol played once on fake HTTP, with the real
``pod_wrapper.sh`` (under bash, stubbed curl/uploader) writing the beat the watchdog and the guard then read. No pod, no network,
no money. The live half of each scenario rides on P12a's pod (``create --drill``, CR-17)."""
import time

import pytest
from test_cloud_stop_paths import FakeLive, spec_for
from test_pod_wrapper import pod as wrapper  # noqa: F401 - the fixture running the real wrapper
from test_runpod import FakeRunPod, pod

from explainer_engine.cloud import runpod as R, watchdog as W

NAME = "ee-drill-until-9999999999"
HB = "datasets/o/r:run/out/beat.txt"


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "RP", tmp_path / "rp")                      # no session file exists: the session is dead
    monkeypatch.setattr(R.time, "sleep", lambda s: None)
    fake = FakeRunPod()
    fake.pods["pp"] = pod("pp", NAME)                                  # the pod the wrapper believes it is (RUNPOD_POD_ID=pp)
    return fake, R.Api("k", transport=fake, sleep=lambda s: None), tmp_path


def _watchdog(api, text, *, now=None, specs=None, pushes=None):
    now = time.time() if now is None else now
    live = FakeLive(specs if specs is not None else {NAME: spec_for(NAME, "pp", created=now - 600, heartbeat=HB)})
    return W.run(api, now=now, apply=True, push=lambda *a: (pushes if pushes is not None else []).append(a) or True,
                 log=lambda *a: None, live=live, text=text)


def _beat_of(wrapper_run):
    return (wrapper_run.out / "beat.txt").read_text()


def test_drill_1_the_session_dies_and_the_pod_does_not_stop_itself_the_watchdog_stops_it(world, wrapper):
    fake, api, tmp = world
    p, b, stops, stub = wrapper("echo result > $EE_OUT/r.txt\n", EE_DRILL="no_self_stop")
    assert b["word"] == "DONE" and not stops and (stub / "hf" / "r.txt").exists()      # uploaded, ended, and never called stop
    assert not (tmp / "rp" / "sessions").exists()                                       # there is no guard and no session file
    res = _watchdog(api, lambda spec: _beat_of(wrapper))
    assert fake.pods["pp"]["status"] == "EXITED" and "DONE" in res["stopped"][0]


def test_drill_2_the_cap_is_reached_outputs_go_up_first_and_the_watchdog_ends_what_the_pod_left(world, wrapper):
    fake, api, tmp = world
    p, b, stops, stub = wrapper("echo started > $EE_OUT/r.txt\nsleep 120\n", EE_DRILL="no_self_stop", EE_LIFETIME_S="4",
                                EE_CAP_GRACE_S="1")
    assert b["word"] == "CAPPED" and (stub / "hf" / "r.txt").exists() and not stops    # uploaded before the cap, no self stop
    res = _watchdog(api, lambda spec: _beat_of(wrapper))
    assert fake.pods["pp"]["status"] == "EXITED" and "CAPPED" in res["stopped"][0]


def test_drill_2b_the_pod_is_silent_and_the_money_estimate_of_the_record_stops_it(world):
    fake, api, tmp = world
    fake.pods["pp"] = pod("pp", NAME, price=1.69)
    now = 10 * 3600
    spec = spec_for(NAME, "pp", created=0.0, max_usd=3.0)

    def no_beat(spec):
        raise OSError("HF has no beat.txt for this pod")
    res = _watchdog(api, no_beat, now=now, specs={NAME: spec})
    assert fake.pods["pp"]["status"] == "EXITED" and "reached the approved $3.0" in res["stopped"][0]


def test_drill_3_the_folder_upload_fails_the_beat_says_so_and_a_person_is_told(world, wrapper):
    fake, api, tmp = world
    p, b, stops, stub = wrapper("echo x > $EE_OUT/r.txt\nsleep 3.5\n", EE_DRILL="upload_fail")
    assert b["word"] == "FAILED_UPLOAD" and b["upload_fail"] >= 3 and b["unstored"] >= 1 and not (stub / "hf" / "r.txt").exists()
    text = _beat_of(wrapper)
    sess = R.new_session(pod("pp", NAME), max_usd=1.0, max_hours=2.0, now=0, heartbeat=HB)
    assert R.heartbeat_step(sess, 600, beat=lambda s: 500.0, text=lambda s: text) == "done"
    assert sess["job_ended"].startswith("FAILED_UPLOAD") and sess["job_ended_unstored"] >= 1      # the guard: RECOVERY_REQUIRED
    pushes = []
    res = _watchdog(api, lambda spec: text, pushes=pushes)
    assert any("may not be on HF" in a for a in res["alerts"]) and fake.pods["pp"]["status"] == "EXITED"
    assert pushes and "needs a hand" not in pushes[0][0]                                           # stopped and pushed, not silent


def test_drill_4_only_the_watchdog_is_left_no_session_no_beat_and_the_lifetime_has_passed(world):
    fake, api, tmp = world
    fake.pods["old"] = pod("old", "ee-old-until-100")                                              # no record, no session, no beat
    res = _watchdog(api, lambda spec: "", now=1000, specs={})
    assert fake.pods["old"]["status"] == "EXITED" and fake.pods["pp"]["status"] == "RUNNING"       # only the expired one
    assert "old" in res["stopped"][0]


def test_drill_5_the_pod_has_no_key_it_says_so_nobody_inside_stops_it_and_the_watchdog_does(world, wrapper):
    fake, api, tmp = world
    p, b, stops, stub = wrapper("echo x > $EE_OUT/r.txt\n", EE_DRILL="drop_key")
    assert b["boot"]["key"] == "none" and b["word"] == "DONE" and not stops                        # no stop call without a key
    text = _beat_of(wrapper)
    sess = R.new_session(pod("pp", NAME), max_usd=1.0, max_hours=2.0, now=0, heartbeat=HB)
    pushes = []
    R.heartbeat_step(sess, 600, beat=lambda s: 500.0, text=lambda s: text, push=lambda *a: pushes.append(a))
    assert pushes and pushes[0][0] == "Pod cannot stop itself" and sess["key"] == "none"           # the guard knows from the first beat
    res = _watchdog(api, lambda spec: text)
    assert fake.pods["pp"]["status"] == "EXITED" and "DONE" in res["stopped"][0]


def test_the_runbook_drill_table_names_five_scenarios_and_a_test_for_each():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "docs" / "CLOUD_RUNBOOK.md").read_text()
    rows = [ln for ln in text.split("## Drills", 1)[1].splitlines() if ln.startswith("| ") and ln.split("|")[1].strip().isdigit()]
    assert len(rows) == 5
    here = Path(__file__).read_text()
    for ln in rows:
        for name in __import__("re").findall(r"`(test_drill_\w+?)\.\.\.`", ln):
            assert f"def {name}" in here, name
