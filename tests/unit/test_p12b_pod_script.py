"""T11: the P12b pod script (p12b.sh + p12b.py) passes the free dry-run rules, declares its heartbeat and stall, and is Qwen only.
No network, no pod, no money (the Hub existence check of ``runpod dryrun`` is not done here)."""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

from explainer_engine.cloud import dryrun as D, pins, runpod as R

DIR = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"


def _load():
    spec = importlib.util.spec_from_file_location("p12b_pod", DIR / "p12b.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_p12b_script_passes_the_dryrun_rules_declares_heartbeat_and_stall_and_is_qwen_only():
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    py = (DIR / "p12b.py").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(DIR / "p12b.sh")]).returncode == 0
    assert R.is_wrapper_script(t) and R.lint_pod_script(t) == [] and D.static_problems(t, pins.load()) == []
    assert R.heartbeat_of_script(t) == "datasets/vano1919/tmr-artifacts:runs/p12b/beat.txt"
    assert R.stall_minutes_of_script(t) == 15
    assert "beat.txt" not in "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#"))   # the wrapper owns it
    low = (t + py).lower()
    assert "ltx" not in low and "a2vid" not in low and "Layout" not in t + py
    assert "import json" in py and "stages.txt" in py and "t.jsonl" in py
    assert "EE_DEADLINE" in py and "EE_OUT" in py and "sys.exit(main())" in py
    # the job files the pod fetches are the ones committed here: their sha256 is pinned in the script text
    for f in ("p12b.py", "p12b.json"):
        assert hashlib.sha256((DIR / f).read_bytes()).hexdigest() in t, f


def test_the_projection_skips_q3_when_time_is_short_and_keeps_q1_and_q4_always():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    st = cfg["stages"]
    assert [m.units_of(st[n]) for n in ("Q1", "Q4", "Q2", "Q3")] == [24, 8, 16, 24]
    reserve = cfg["end_reserve_min"] * 60
    first = {"Q1": 60.0, "Q4": 40.0}                        # seconds of the first unit of each stage
    done = {"Q1", "Q4"}
    deadline = 100_000.0
    # Q2: 16 x 60 s = 960 s; Q3: 24 x 60 s = 1440 s
    assert m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve, deadline, reserve)
    assert not m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve + 1, deadline, reserve)
    assert m.stage_may_start("Q3", st, first, done, deadline - 1440 - reserve, deadline, reserve)
    assert not m.stage_may_start("Q3", st, first, done, deadline - 1000 - reserve, deadline, reserve)   # Q2 still fits, Q3 does not
    assert m.stage_may_start("Q2", st, first, done, deadline - 1000 - reserve, deadline, reserve)
    # the essential stages start even with no time left; an optional stage without a measured first unit never starts
    assert m.stage_may_start("Q1", st, {}, set(), deadline + 999, deadline, reserve)
    assert m.stage_may_start("Q4", st, first, {"Q1"}, deadline + 999, deadline, reserve)
    assert not m.stage_may_start("Q3", st, {}, set(), 0.0, deadline, reserve)
    # an optional stage also has to leave room for the essential stages still to run
    assert not m.stage_may_start("Q2", st, first, {"Q1"}, deadline - 960 - reserve, deadline, reserve)
    assert m.ordered(st) == ["Q1", "Q4", "Q2", "Q3"]


def test_the_outputs_follow_the_plan_paths_and_the_azimuth_degrees_go_round_in_30_steps():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    assert [m.az_deg(cfg, a) for a in ("front view", "right side view", "back view", "left side view")] == [0, 90, 180, 270]
    assert str(m.mva_out(cfg, "o", "napoleon", "back view", 0.8)) == "o/mva/napoleon/180_s0.8.png"
    assert str(m.host_out("o", "analyst", 11)) == "o/hosts/analyst_seed11.png"
