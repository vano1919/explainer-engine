"""The P12b measurement pod script (RP-01, 2026-11-01): it passes the free dry-run rules, installs with the same pinned lines as p12b.sh,
downloads the base model at the revision p12b.json pins, and does no GPU work. No network, no pod, no money."""
import json
import subprocess
from pathlib import Path

from explainer_engine.cloud import dryrun as D, pins, runpod as R

DIR = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"


def _text(name):
    return (DIR / name).read_text(encoding="utf-8")


def test_the_measure_script_passes_the_dryrun_rules_and_declares_heartbeat_and_stall():
    t = _text("p12b_measure.sh")
    assert subprocess.run(["bash", "-n", str(DIR / "p12b_measure.sh")]).returncode == 0
    assert R.is_wrapper_script(t) and R.lint_pod_script(t) == [] and D.static_problems(t, pins.load()) == []
    assert R.heartbeat_of_script(t) == "datasets/vano1919/tmr-artifacts:runs/p12b_measure/beat.txt"
    assert R.stall_minutes_of_script(t) == 10
    assert "beat.txt" not in "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#"))   # the wrapper owns it


def test_its_install_lines_and_model_pin_are_those_of_p12b():
    m, b = _text("p12b_measure.sh"), _text("p12b.sh")
    cfg = json.loads(_text("p12b.json"))
    for line in b.splitlines():
        if line.startswith(("pip install", "git clone")):
            assert line in m, line                                    # the measured install is the install P12b runs
    assert cfg["base"]["repo"] in m and cfg["base"]["revision"] in m
    assert "HF_XET_HIGH_PERFORMANCE=0" in m and "HF_XET_HIGH_PERFORMANCE=1" in m


def test_it_does_no_gpu_work_and_loads_no_model():
    code = "\n".join(ln for ln in _text("p12b_measure.sh").splitlines() if not ln.lstrip().startswith("#"))
    for banned in ("from_pretrained", "load_pipeline", "merge_lora", "p12b.py", "ltx", "Lightricks"):
        assert banned not in code, banned
