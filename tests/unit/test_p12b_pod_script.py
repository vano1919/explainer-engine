"""T11: the combined P12 pod script (p12b.sh + p12b.py + p12c_ltx.py) passes the free dry-run rules, declares its heartbeat and stall; Qwen draws in process 1 and the LTX weights download in the background, the LTX stages run in process 2.
No network, no pod, no money (the Hub existence check of ``runpod dryrun`` is not done here)."""
import hashlib
import importlib.util
import json
import pytest
import re
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
    assert R.stall_minutes_of_script(t) == 25                      # p12b.json stall_minutes: the LTX audio stage is long
    assert json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))["stall_minutes"] == 25
    assert "beat.txt" not in "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#"))   # the wrapper owns it
    low = (t + py).lower()
    # process 1 draws with Qwen and only DOWNLOADS the LTX weights (a background thread); every LTX run is process 2 (p12c_ltx.py)
    assert "from_pretrained" in py and "a2vid" not in low and "ltx_pipelines" not in py
    assert 'cfg["ltx"]' in py and "hf_hub_download" in py and "start_ltx_download" in py
    assert t.index('python3 "$JOB/p12b.py"') < t.index('python3 "$JOB/p12c_ltx.py"')
    assert "stopped_after.txt" in t                                # process 2 starts only without the creator's soft stop
    assert "HF_HUB_ENABLE_HF_TRANSFER=1" in t and "HF_XET_HIGH_PERFORMANCE=1" in t
    assert "hosts" not in low and "host_" not in low and "q4" not in low                 # D-89: no host stage, no host block
    assert "import json" in py and "stages.txt" in py and "t.jsonl" in py
    assert "EE_DEADLINE" in py and "EE_OUT" in py and "sys.exit(main())" in py


def test_the_job_files_are_sha256_pinned_in_the_script_text_and_the_pins_are_filled_before_a_pod():
    """The pod fetches p12b.py, p12b.json and p12c_ltx.py from HF code/p12/ and checks them against the sha256 written in p12b.sh. Until
    the DRY gate (WP-1e) fills those lines they read PLACEHOLDER_SHA_*; a REAL sha in the script must be the committed file's."""
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    for f in ("p12b.py", "p12b.json", "p12c_ltx.py"):
        real = hashlib.sha256((DIR / f).read_bytes()).hexdigest()
        holder = "PLACEHOLDER_SHA_" + f.upper().replace(".", "_")
        assert real in t or holder in t, f
        assert not re.search(r"\b[0-9a-f]{64}\s+\"\$JOB/" + re.escape(f), t) or real in t, f


@pytest.mark.xfail(strict=True, reason="WP-1e: sha256 lines of p12b.sh, the clay and the AV takes of p12b.json are still PLACEHOLDER; remove "
                   "this marker when the DRY gate has filled them (strict: it fails the day they are all real, as a reminder)")
def test_the_pod_is_runnable_only_when_no_placeholder_is_left():
    text = "".join((DIR / f).read_text(encoding="utf-8") for f in ("p12b.sh", "p12b.json", "p12c_ltx.py"))
    assert "PLACEHOLDER" not in text


def test_the_projection_skips_optional_stages_when_time_is_short_and_keeps_the_essential_ones():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    st = cfg["stages"]
    assert [m.units_of(st[n]) for n in ("Q1", "Q2", "Q3")] == [24, 16, 24]
    assert [m.units_of(st[n]) for n in ("L1", "L3", "L2", "AV")] == [3, 3, 3, 2]       # one take per shot (D-93 / the creator)
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
    # the LTX stages still to come (process 2) are a fixed reserve: Q2 fits alone but not next to the 61 min LTX reserve
    ltx = float(cfg["ltx"]["reserve_min"]) * 60
    assert not m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve, deadline, reserve, ltx)
    assert m.stage_may_start("Q2", st, first, done, deadline - 960 - reserve - ltx, deadline, reserve, ltx)
    # LTX stages are never measured in process 1: no estimate, so an optional one (L3) never starts there; the order is the plan's
    assert m.estimate_s("L3", st, first) is None and not m.stage_may_start("L3", st, first, done, 0.0, deadline, reserve)
    assert m.ordered(st) == ["Q1", "Q2", "Q3", "L1", "L3", "L2", "AV"]
    assert m.ordered(st, "qwen_mva") == ["Q1", "Q2", "Q3"] and m.ordered(st, "ltx_i2v") == ["L1", "L3"]


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


def _ltx_jobs(cfg):
    """Fetch order (audit #14): the shared files, the Layout LoRA, and the AV files last (only with real takes)."""
    lt, ll = cfg["ltx"], cfg["ltx"]["layout_lora"]
    jobs = [(lt["repo"], f, lt["revision"]) for f in lt["files"]] + [(ll["repo"], ll["file"], ll["revision"])]
    if all("PLACEHOLDER" not in str(v[k]) for v in lt["av"]["takes"].values() for k in ("sha256", "voice_id")):
        jobs += [(lt["repo"], f, lt["revision"]) for f in lt["av_files"]]
    return jobs


def _real_takes(cfg):
    for v in cfg["ltx"]["av"]["takes"].values():
        v["sha256"], v["voice_id"] = "a" * 64, "voice"
    return cfg


def test_the_ltx_download_runs_in_a_background_thread_and_a_failure_does_not_stop_qwen(tmp_path, monkeypatch):
    import sys
    import types
    m = _load()
    calls = []
    hub = types.ModuleType("huggingface_hub")

    def boom(repo, filename, **kw):
        calls.append((repo, filename, kw["revision"]))
        raise OSError("offline")
    hub.hf_hub_download = boom
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    cfg = _real_takes(json.loads((DIR / "p12b.json").read_text(encoding="utf-8")))
    log = m.Log(tmp_path / "out")
    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: types.SimpleNamespace(free=200 * 2 ** 30))   # the guard is tested below
    th = m.start_ltx_download(log, cfg)
    th.join(5)
    assert not th.is_alive()
    assert calls == _ltx_jobs(cfg) and len(calls) == 8                      # every file at its pinned revision, a failure goes on to the next
    evs = [json.loads(x)["ev"] for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert evs == ["ltx_download_start"] + ["ltx_download_failed"] * 8 + ["ltx_download_end"]


def test_a_403_on_a_gated_file_is_logged_as_gated_and_the_next_file_is_still_tried(tmp_path, monkeypatch):
    import sys
    import types
    m = _load()
    hub = types.ModuleType("huggingface_hub")
    seen = []

    def gated(repo, filename, **kw):
        seen.append(filename)
        err = OSError("403 gated")
        err.response = types.SimpleNamespace(status_code=403)
        raise err
    hub.hf_hub_download = gated
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: types.SimpleNamespace(free=200 * 2 ** 30))
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    m.start_ltx_download(m.Log(tmp_path / "out"), _real_takes(cfg)).join(5)
    evs = [json.loads(x) for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert len(seen) == 8 and sum(e["ev"] == "gated_403" for e in evs) == 8
    assert {e["repo"] for e in evs if e["ev"] == "gated_403"} == {"Lightricks/LTX-2.5", "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render"}


def test_the_ltx_download_is_skipped_when_the_free_disk_is_below_ltx_plus_margin(tmp_path, monkeypatch):
    import types
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    need = (cfg["ltx"]["expected_gb"] + cfg["ltx"]["margin_gb"]) * 2 ** 30
    assert m.ltx_download_fits(need, cfg) and not m.ltx_download_fits(need - 1, cfg)
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: types.SimpleNamespace(free=need - 1))
    log = m.Log(tmp_path / "out")
    assert m.start_ltx_download(log, cfg) is None                         # no thread, no download; the wait loop guards None
    evs = [json.loads(x) for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert [e["ev"] for e in evs] == ["ltx_download_skipped"] and evs[0]["why"] == "disk"
    assert "ltx is not None and ltx.is_alive()" in (DIR / "p12b.py").read_text(encoding="utf-8")


# audit 2026-11-01 (#10, #13): the stall rule must see change during installs and the model load; the creator may stop after M
def test_p12b_sh_writes_progress_from_the_first_second_and_stops_the_writer_before_the_real_work():
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    writer, first_install, killed = t.index("while sleep 60"), t.index("pip install"), t.index('kill "$PROG0"')
    assert writer < first_install < killed < t.index('python3 "$JOB/p12b.py"')
    assert killed < t.index('if [ "${DRY:-0}" = "1" ]')                  # a DRY run ends without a writer left behind


def test_the_ticker_rewrites_progress_while_a_block_runs_and_stops_after_it(tmp_path):
    import time
    m = _load()
    log = m.Log(tmp_path)
    with m.ticker(log, "loading the model", every=0.05):
        time.sleep(0.3)
        mid = (tmp_path / "progress.txt").read_text(encoding="utf-8")
    assert "loading the model" in mid and mid.rstrip().endswith(" s")      # the first line has no seconds: a tick has rewritten it
    after = (tmp_path / "progress.txt").read_text(encoding="utf-8")
    time.sleep(0.2)
    assert (tmp_path / "progress.txt").read_text(encoding="utf-8") == after


def test_the_creator_can_stop_right_after_stage_m(tmp_path, monkeypatch):
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(m, "creator_stop_after", lambda cfg, log, timeout_s=20: "M")
    log = m.Log(tmp_path)
    assert m.stop_here(cfg, log, tmp_path, "M") is True
    assert (tmp_path / "control" / "stopped_after.txt").read_text(encoding="utf-8") == "M\n"
    assert m.stop_here(cfg, log, tmp_path, "Q1") is False
    assert "stop_here(cfg, log, out, \"M\")" in (DIR / "p12b.py").read_text(encoding="utf-8")


# audit 2026-11-01 #9: the drop order is Q3, then L3, then Q2: a stage may start only when the optional stages dropped LATER still fit
def test_q3_starts_only_when_l3_still_fits_behind_it_and_q2_does_not_wait_for_l3():
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    st, lt = cfg["stages"], cfg["ltx"]
    reserve, ltx = cfg["end_reserve_min"] * 60, float(lt["reserve_min"]) * 60
    l3 = float(lt["optional_reserve_min"]["L3"]) * 60
    optional = {k: float(v) * 60 for k, v in lt["optional_reserve_min"].items()}
    assert m.after_reserve(cfg, "Q3", optional) == l3 and m.after_reserve(cfg, "Q2", optional) == 0.0
    assert m.after_reserve(cfg, "Q1", optional) == 0.0 and "L3" not in lt["reserve_parts_min"]    # L3 is optional: not in the essential reserve
    first, done, deadline = {"Q1": 60.0}, {"Q1", "Q2"}, 100_000.0
    q3 = 24 * 60.0
    at_limit = deadline - q3 - reserve - ltx                      # Q3 + the essential LTX stages fit exactly, L3 does not
    assert m.stage_may_start("Q3", st, first, done, at_limit - l3, deadline, reserve, ltx + m.after_reserve(cfg, "Q3", optional))
    assert not m.stage_may_start("Q3", st, first, done, at_limit - l3 + 1, deadline, reserve, ltx + m.after_reserve(cfg, "Q3", optional))
    assert m.stage_may_start("Q3", st, first, done, at_limit, deadline, reserve, ltx)               # the old projection let Q3 starve L3
    # Q2 is dropped last: only the essential LTX stages hold it back
    first2, q2 = {"Q1": 60.0}, 16 * 60.0
    assert m.stage_may_start("Q2", st, first2, {"Q1"}, deadline - q2 - reserve - ltx, deadline, reserve, ltx + m.after_reserve(cfg, "Q2", optional))


def test_p12b_sh_has_one_ltx_install_line_pinned_to_cloud_pins():
    """The old measurement pod script (p12b_measure.sh, deleted 2026-11-01: the measurement is stage M) used to tie p12b.sh's installs to a
    second copy; the one new line, the LTX-2 clone, is tied to config/cloud_pins.json here."""
    t = (DIR / "p12b.sh").read_text(encoding="utf-8")
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    sha = pins.load()["git"]["Lightricks/LTX-2"]["sha"]
    lines = [ln for ln in t.splitlines() if ln.startswith(("pip install", "git clone")) and "Lightricks/LTX-2" in ln]
    assert len(lines) == 1 and sha in lines[0] and cfg["ltx"]["code"]["sha"] == sha
    assert not (DIR / "p12b_measure.sh").exists()


# audit 2026-11-01 #14: no 51 GB AV download without real takes, the Layout LoRA before them, no new unit inside the end reserve
def test_the_av_files_are_fetched_last_and_only_when_the_takes_are_real(tmp_path, monkeypatch):
    import sys
    import types
    m = _load()
    cfg = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    lt = cfg["ltx"]
    if not m.av_takes_real(cfg):                                           # the checked-in state until WP-1e
        jobs = m.ltx_download_jobs(cfg)
        assert len(jobs) == len(lt["files"]) + 1 and jobs[-1][1] == lt["layout_lora"]["file"]
        assert not {f for _, f, _ in jobs} & set(lt["av_files"])
    real = m.ltx_download_jobs(_real_takes(cfg))
    assert [f for _, f, _ in real[-len(lt["av_files"]):]] == lt["av_files"]
    assert real[len(lt["files"])][1] == lt["layout_lora"]["file"]          # the Layout LoRA precedes the AV files
    cfg2 = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    cfg2["ltx"]["av"]["takes"]["av2"]["sha256"] = "PLACEHOLDER_SHA"
    _real_takes(cfg2)["ltx"]["av"]["takes"]["av2"]["voice_id"] = "PLACEHOLDER"
    assert not m.av_takes_real(cfg2)                                       # one placeholder is enough to skip
    hub = types.ModuleType("huggingface_hub")
    hub.hf_hub_download = lambda repo, filename, **kw: str(tmp_path / filename)
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)
    monkeypatch.setattr(m, "MODELS", tmp_path / "models")
    monkeypatch.setattr(m.shutil, "disk_usage", lambda p: types.SimpleNamespace(free=200 * 2 ** 30))
    cfg3 = json.loads((DIR / "p12b.json").read_text(encoding="utf-8"))
    cfg3["ltx"]["av"]["takes"]["av1"]["voice_id"] = "PLACEHOLDER"
    m.start_ltx_download(m.Log(tmp_path / "out"), cfg3).join(5)
    evs = [json.loads(x) for x in (tmp_path / "out" / "t.jsonl").read_text().splitlines()]
    assert any(e["ev"] == "ltx_download_av_skipped" for e in evs)
    assert next(e for e in evs if e["ev"] == "ltx_download_start")["files"] == len(lt["files"]) + 1


def test_no_new_unit_starts_inside_the_end_reserve_even_for_an_essential_stage():
    m = _load()
    assert m.unit_may_start(100.0, 1000.0, 600.0) and not m.unit_may_start(400.0, 1000.0, 600.0)
    src = (DIR / "p12b.py").read_text(encoding="utf-8")
    assert "unit_may_start(time.time(), deadline, reserve)" in src
    ltx = (DIR / "p12c_ltx.py").read_text(encoding="utf-8")
    assert "p12b.unit_may_start(time.time(), deadline, reserve)" in ltx and "inside the end reserve" in ltx
