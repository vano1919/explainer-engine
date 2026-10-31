"""F7 (docs/CLOUD_RUNBOOK.md CR-12, CR-18, CR-06; T22/T24): a create whose answer was lost never POSTs twice, a pod script that
downloads must list its ``# needs:``, and the wrapper ends a pod ``FAILED rc=66`` before the GPU step when a needed file is
missing. On the fake RunPod HTTP of the P12d drills and the real ``pod_wrapper.sh`` under bash. No network, no pod, no money."""
import json
import re

import pytest
from test_cloud_stop_paths import FakeLive, _create, env  # noqa: F401 - env: the fixture of the create tests
from test_pod_wrapper import pod as wrapper  # noqa: F401 - the fixture running the real wrapper
from test_runpod import NEW_SH, pod

from explainer_engine.cloud import dryrun as D, hf_live, pins as P, runpod as R

PINS = P.load()
REST = "https://rest.runpod.io/v2"


def _posts(fake):
    return [c for c in fake.calls if c[0] == "POST" and c[1].startswith("/pods")]


def _die_after_the_post(monkeypatch, fake):
    """The session dies after RunPod took the POST and before it heard the answer: the live spec stays, with no pod id."""
    def create(api, body, **kw):
        body.pop(R.PREFLIGHT_KEY, None)
        fake("POST", REST + "/pods", json.dumps(body).encode(), {}, 1)
        raise KeyboardInterrupt("the session died")
    monkeypatch.setattr(R, "create", create)


def test_a_second_create_adopts_the_pod_of_a_lost_answer_by_its_name_and_never_posts_again(env, monkeypatch, capsys):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    live = FakeLive(age=60)
    real = R.create
    _die_after_the_post(monkeypatch, fake)
    with pytest.raises(KeyboardInterrupt):
        _create(api, tmp, NEW_SH, live=live)
    (name, spec), = live.specs().items()
    assert spec["pod"] is None and len(_posts(fake)) == 1 and fake.pods["p1"]["name"] == name   # the pod exists, the spec does not know it
    monkeypatch.setattr(R, "create", real)
    _create(api, tmp, NEW_SH, live=live)
    assert len(_posts(fake)) == 1                                                      # zero second POST
    assert live.specs()[name]["pod"] == "p1" and len(live.specs()) == 1                 # the pod id is in the spec of the first name
    assert "adopted p1" in capsys.readouterr().out and len(fake.pods) == 1


def test_a_stale_spec_of_a_pod_that_never_appeared_is_moved_and_the_create_goes_on(env, monkeypatch):
    fake, api, tmp = env
    monkeypatch.delenv("RUNPOD_POD_API_KEY", raising=False)
    live = FakeLive(age=60)
    dead = "ee-default-aaaaaa-until-1000"                                             # its lifetime ended long ago, no pod carries the name
    live._specs[dead] = {"name": dead, "pod": None, "job": "ee-default", "heartbeat": "datasets/o/r:run/out/beat.txt", "until": 1000}
    _create(api, tmp, NEW_SH, live=live)
    assert live.closed == [dead] and len(_posts(fake)) == 1 and len(fake.pods) == 1
    assert [s["pod"] for s in live.specs().values()] == ["p1"]


def test_a_listing_that_fails_after_a_lost_answer_refuses_instead_of_posting_blind(env):
    fake, api, tmp = env
    spec = {"name": "ee-x-until-9999999999", "pod": None, "job": "j", "heartbeat": "h", "until": 9999999999}
    live = FakeLive({spec["name"]: spec})
    fake.faults += [("GET", "/pods", "timeout")] * 10
    with pytest.raises(R.RunPodError, match="not POSTing again"):
        R.adopt_pending(api, live, job="j", heartbeat="h", now=1)
    assert _posts(fake) == [] and live.specs()[spec["name"]]["pod"] is None
    assert hf_live.pending({"a": spec, "b": {**spec, "pod": "x"}}, job="j") == {"a": spec}
    assert set(hf_live.SPEC_FIELDS) >= {"name", "pod", "job", "heartbeat", "until"}


# --- CR-18: the `# needs:` list ------------------------------------------------------------------------------------------------
DL = 'python3 - <<PY\nfrom huggingface_hub import hf_hub_download as d\nd("o/r", "w.bin")\nPY\n'


def test_dryrun_refuses_a_downloading_script_without_a_needs_list_and_accepts_one_that_checks_it():
    base = "# heartbeat: datasets/o/r:run/out/beat.txt\n[ \"${DRY:-0}\" = 1 ] && exit 0\n"
    bare = D.needs_problems(base + DL)
    assert len(bare) == 1 and "# needs:" in bare[0]
    assert any(p.startswith("needs:") for p in D.run(base + DL, exists=lambda r, k: (True, ""), pins=PINS)["problems"])
    listed_not_checked = D.needs_problems("# needs: /w/w.bin 10\n" + DL)
    assert len(listed_not_checked) == 1 and "ee_needs_check" in listed_not_checked[0]
    assert D.needs_problems("# needs: /w/w.bin 10\n" + DL + "ee_needs_check\n") == []
    assert D.needs_problems("# needs: none (the download is the test)\n" + DL) == []
    assert D.needs_problems("echo hi > $EE_OUT/progress.txt\n") == []                    # nothing downloaded: nothing to need
    assert D.needs_of("# needs: $JOB/a.py 14916\n# needs: /x/y\n# needs: none\n") == [("$JOB/a.py", 14916), ("/x/y", 1)]


def test_the_committed_p12_scripts_carry_their_needs_and_pass():
    from pathlib import Path
    pods = Path(R.__file__).resolve().parents[1] / "training" / "pods" / "p12"
    t = (pods / "p12b.sh").read_text(encoding="utf-8")
    assert D.needs_problems(t) == [] and D.static_problems(t, PINS) == []
    # p12a_A.sh is pinned by sha to the plan's dry-run record (test_p12a_scripts): it is not edited here; a new dry run of it would ask
    # for `# needs: none`, which is for the creator's plan to decide (reported in PROGRESS)
    assert [p for p, _ in D.needs_of((pods / "p12b.sh").read_text(encoding="utf-8"))] == ["$JOB/p12b.py", "$JOB/p12b.json"]


# --- the wrapper -------------------------------------------------------------------------------------------------------------
SCRIPT = """# needs: $WANT_DIR/weights.bin 5
echo "step 1/2" > $EE_OUT/progress.txt
ee_needs_check
echo GPU_STEP_REACHED >> $EE_OUT/t.txt
"""


def test_the_wrapper_ends_failed_before_the_gpu_step_when_a_needed_file_is_missing(wrapper, tmp_path):
    want = tmp_path / "w"
    want.mkdir()
    p, b, stops, _ = wrapper(SCRIPT, WANT_DIR=want)
    assert b["word"] == "FAILED" and b["rc"] == 66 and stops
    assert "NEEDS_MISSING" in p.stdout and "weights.bin" in p.stdout
    assert not (wrapper.out / "t.txt").exists()                                          # the marker line after the check never ran
    (want / "weights.bin").write_text("123")                                            # present but too small
    p, b, _, _ = wrapper(SCRIPT, WANT_DIR=want)
    assert b["word"] == "FAILED" and b["rc"] == 66


def test_the_wrapper_lets_the_script_go_on_when_the_files_are_there_and_keeps_the_cuda_probe(wrapper, tmp_path):
    want = tmp_path / "w"
    want.mkdir()
    (want / "weights.bin").write_text("12345678")
    p, b, _, _ = wrapper(SCRIPT, WANT_DIR=want)
    assert b["word"] == "DONE" and (wrapper.out / "t.txt").read_text().strip() == "GPU_STEP_REACHED"
    text = R.WRAPPER.read_text()
    assert text.index("timeout 120 python3 -c \"import torch; x = torch.ones(8, device='cuda')") < text.index("ee_needs_check()")   # CR-06 first
    from test_pod_wrapper import SMI_FAIL
    (wrapper.out / "t.txt").unlink()
    p, b, _, _ = wrapper(SCRIPT, smi=SMI_FAIL, WANT_DIR=want)                          # a bad host still ends BAD_HOST before the script
    assert b["word"] == "BAD_HOST" and not (wrapper.out / "t.txt").exists()


def test_the_runbook_names_the_two_new_drill_rows_with_these_tests():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / "docs" / "CLOUD_RUNBOOK.md").read_text()
    rows = [ln for ln in text.split("## Drills", 1)[1].splitlines() if ln.startswith("| ") and re.match(r"\| 6[ab] ", ln)]
    assert len(rows) == 2
    here = Path(__file__).read_text()
    for ln in rows:
        names = re.findall(r"`(test_\w+?)`", ln)
        assert names and all(f"def {n}" in here for n in names), ln
