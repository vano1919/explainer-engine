"""T11: the P12b pod script (p12b.sh + p12b.py) passes the free dry-run rules, declares its heartbeat and stall; Qwen draws, the video weights only download in the background.
No network, no pod, no money (the Hub existence check of ``runpod dryrun`` is not done here)."""
import hashlib
import importlib.util
import json
import pytest
import subprocess
from pathlib import Path

from explainer_engine.cloud import dryrun as D, pins, runpod as R

DIR = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p12"


def _load():
    spec = importlib.util.spec_from_file_location("p12b_pod", DIR / "p12b.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_p12b_script_passes_the_dryrun_rules_declares_heartbeat_and_stall_and_draws_only_with_qwen():
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    py = (DIR / "p12b.py").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(DIR / "p12b.sh")]).returncode == 0
    assert R.is_wrapper_script(t) and R.lint_pod_script(t) == [] and D.static_problems(t, pins.load()) == []
    assert R.heartbeat_of_script(t) == "datasets/vano1919/tmr-artifacts:runs/p12b/beat.txt"
    assert R.stall_minutes_of_script(t) == 15
    assert "beat.txt" not in "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#"))   # the wrapper owns it
    low = (t + py).lower()
    # creator 2026-10-31 (RP-01 Path A): the video model's weights download in the background; nothing else of a video model runs here
    assert "a2vid" not in low and "Layout" not in t + py and "from_pretrained" in py and "ltx" not in py.lower()
    assert 'cfg["video"]' in py and "snapshot_download(v[\"repo\"]" in py and "start_video_download" in py
    assert "HF_HUB_ENABLE_HF_TRANSFER=1" in t and "HF_XET_HIGH_PERFORMANCE=1" in t
    assert "hosts" not in low and "host_" not in low and "q4" not in low                 # D-89: no host stage, no host block
    assert "import json" in py and "stages.txt" in py and "t.jsonl" in py
    assert "EE_DEADLINE" in py and "EE_OUT" in py and "sys.exit(main())" in py
    # the job files the pod fetches are the ones committed here: their sha256 is pinned in the script text
    for f in ("p12b.py", "p12b.json"):
        assert hashlib.sha256((DIR / f).read_bytes()).hexdigest() in t, f


def test_the_projection_skips_q3_when_time_is_short_and_keeps_q1_and_q4_always():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    st = cfg["stages"]
    assert [m.units_of(st[n]) for n in ("Q1", "Q2", "Q3")] == [24, 16, 24]
    reserve = cfg["end_reserve_min"] * 60
    first = {"Q1": 60.0}                                    # seconds of the first unit of each stage
    done = {"Q1"}
    deadline = 100_000.0
    # Q2: 16 x 60 s = 960 s; Q3: 24 x 60 s = 1440 s
    assert m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve, deadline, reserve)
    assert not m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve + 1, deadline, reserve)
    assert m.stage_may_start("Q3", st, first, done, deadline - 1440 - reserve, deadline, reserve)
    assert not m.stage_may_start("Q3", st, first, done, deadline - 1000 - reserve, deadline, reserve)   # Q2 still fits, Q3 does not
    assert m.stage_may_start("Q2", st, first, done, deadline - 1000 - reserve, deadline, reserve)
    # the essential stages start even with no time left; an optional stage without a measured first unit never starts
    assert m.stage_may_start("Q1", st, {}, set(), deadline + 999, deadline, reserve)
    assert not m.stage_may_start("Q3", st, {}, set(), 0.0, deadline, reserve)
    # an optional stage also has to leave room for the essential stages still to run
    assert not m.stage_may_start("Q2", st, first, set(), deadline - 960 - reserve, deadline, reserve)
    assert m.ordered(st) == ["Q1", "Q2", "Q3"]


def test_the_outputs_follow_the_plan_paths_and_the_azimuth_degrees_go_round_in_30_steps():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    assert [m.az_deg(cfg, a) for a in ("front view", "right side view", "back view", "left side view")] == [0, 90, 180, 270]
    assert str(m.mva_out(cfg, "o", "napoleon", "back view", 0.8)) == "o/mva/napoleon/180_s0.8.png"
    assert not hasattr(m, "host_out") and not hasattr(m, "host_reference")   # D-89


def test_p12b_applies_the_gate_up_correction_after_every_merge_and_unmerge():
    import ast
    tree = ast.parse((DIR / "p12b.py").read_text(encoding="utf-8"))
    assert any(isinstance(n, ast.FunctionDef) and n.name == "gate_up" for n in ast.walk(tree))
    calls = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            nm = n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
            if nm in ("merge_lora", "unmerge_lora", "gate_up"):
                calls.append((n.lineno, nm))
    names = [x[1] for x in sorted(calls)]
    assert names.count("merge_lora") == 2 and names.count("unmerge_lora") == 1
    for i, nm in enumerate(names):
        if nm in ("merge_lora", "unmerge_lora"):
            assert names[i + 1] == "gate_up", (nm, names)


def test_gate_up_splits_the_fused_delta_into_gate_layer_and_proj_and_unmerge_restores(tmp_path):
    torch = pytest.importorskip("torch")
    st = pytest.importorskip("safetensors.torch")
    m = _load()
    r, half, din = 2, 3, 4
    down, up = torch.randn(r, din), torch.randn(2 * half, r)
    p = tmp_path / "l.safetensors"
    pre = "transformer.transformer_blocks.0.img_mlp.gate_up."
    st.save_file({pre + "lora_A.weight": down, pre + "lora_B.weight": up, pre + "alpha": torch.tensor(1.0)}, str(p))
    ff = torch.nn.Module()
    ff.gate_layer, ff.proj = torch.nn.Linear(din, half, bias=False), torch.nn.Linear(din, half, bias=False)
    root = torch.nn.Module()
    root.transformer_blocks = torch.nn.ModuleList([torch.nn.Module()])
    root.transformer_blocks[0].img_mlp = ff
    g0, p0 = ff.gate_layer.weight.detach().clone(), ff.proj.weight.detach().clone()
    gu = m.GateUp(root)
    delta = (up @ down) * (1.0 / r) * 0.5
    assert gu.gate_up(str(p), 0.5) == 1
    assert torch.allclose(ff.gate_layer.weight, g0 + delta[:half], atol=1e-6)
    assert torch.allclose(ff.proj.weight, p0 + delta[half:], atol=1e-6)
    gu.gate_up(str(p), -0.5)
    assert torch.allclose(ff.gate_layer.weight, g0, atol=1e-5) and torch.allclose(ff.proj.weight, p0, atol=1e-5)


def test_p12b_declares_needs_none_because_the_code_files_are_sha256_pinned_and_the_weights_are_not_listed():
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    assert D.needs_of(t) == [] and "# needs: none" in t   # no hard-coded sizes that break on every edit of p12b.py / p12b.json


def test_the_style_lora_is_merged_at_the_json_weight_0_7_not_a_literal(tmp_path):
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    assert m.style_weight(cfg) == 0.7
    import ast
    tree = ast.parse((DIR / "p12b.py").read_text(encoding="utf-8"))
    merges = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "merge_lora"]
    style = next(n for n in merges if n.args[1].id == "style")
    assert not isinstance(style.args[2], ast.Constant)      # the weight is a variable that comes from p12b.json


def test_the_video_download_runs_in_a_background_thread_and_a_failure_does_not_stop_qwen(tmp_path, monkeypatch):
    import sys
    import types
    m = _load()
    calls = []
    hub = types.ModuleType("huggingface_hub")
    def boom(repo, **kw):
        calls.append((repo, kw["revision"]))
        raise OSError("offline")
    hub.snapshot_download = boom
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    log = m.Log(tmp_path / "out")
    th = m.start_video_download(log, cfg)
    th.join(5)
    assert calls == [("Lightricks/LTX-Video-0.9.8-13B-distilled", "7c64400e1861cc0d7b98d570a1926d5408ec60cd")] and not th.is_alive()
    evs = [json.loads(x)["ev"] for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert evs == ["video_download_start", "video_download_failed"]
