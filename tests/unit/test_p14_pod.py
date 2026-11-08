"""Guide step 3 (D-116): the route-test LTX part of the lean pod (p14_ltx.py + p14.json + ltx_jobs.json, run by p14.sh through
p14_pod.py) passes the free dry-run rules, builds every ic_lora command from the flags table, derives the controls, chains clip B
from clip A, skips what is not pinned and upscales a clip with finish/upscale's chain only when p14.json turns it on (the lean plan
turns it off). No network, no pod, no money. The lean pod's own stages: test_p14_lean.py."""
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from explainer_engine.cloud import dryrun as D, pins, runpod as R
from explainer_engine.finish import upscale as U

DIR = Path(__file__).resolve().parents[2] / "explainer_engine" / "training" / "pods" / "p14"
CFG = json.loads((DIR / "p14.json").read_text(encoding="utf-8"))
JOBS = json.loads((DIR / "ltx_jobs.json").read_text(encoding="utf-8"))


def _load(tmp_path, monkeypatch):
    monkeypatch.setenv("P14_MODELS", str(tmp_path / "models"))
    spec = importlib.util.spec_from_file_location("p14_ltx", DIR / "p14_ltx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_script_passes_the_dryrun_rules_and_declares_heartbeat_stall_and_needs():
    t = (DIR / "p14.sh").read_text(encoding="utf-8")
    assert subprocess.run(["bash", "-n", str(DIR / "p14.sh")]).returncode == 0
    assert R.is_wrapper_script(t) and R.lint_pod_script(t) == [] and D.static_problems(t, pins.load()) == []
    assert D.needs_problems(t) == [] and D.placeholder_problems(t, DIR) == []
    assert R.heartbeat_of_script(t) == "datasets/vano1919/tmr-artifacts:route_test_2026-11/beat.txt"
    assert R.stall_minutes_of_script(t) == 30
    assert "ee_needs_check" in t and "explainer_engine.training.pods.p14.p14_pod" in t and "DRY" in t
    body = "\n".join(ln for ln in t.splitlines() if not ln.lstrip().startswith("#")).lower()
    assert "runpod create" not in body and "beat.txt" not in body      # the pod never starts a pod; the wrapper owns the beat
    rec = D.run(t, offline=True, folder=DIR)   # the offline dry run: only the "repos not looked at" line is left (never a pass)
    assert rec["problems"] == ["the Hugging Face repos were not checked (--offline): a dry run that did not look is not a pass"]


def test_the_code_bundle_is_sha256_pinned_in_the_script():
    t = (DIR / "p14.sh").read_text(encoding="utf-8")
    lines = [ln for ln in t.splitlines() if "ee_src.tar.gz\" > \"$JOB/sha.txt\"" in ln]
    assert len(lines) == 1 and re.search(r"\b[0-9a-f]{64}\b", lines[0]) and "sha256sum -c" in t


def test_d120_refuses_legacy_j2_and_any_clay_conditioning_before_pod_work(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="D-120"):
        m.require_d120_compliance(JOBS)
    j4_only = {**JOBS, "jobs": [j for j in JOBS["jobs"] if j.get("route") == "J4"]}
    assert j4_only["jobs"]
    m.require_d120_compliance(j4_only)
    bad = {**j4_only, "jobs": [{**j4_only["jobs"][0], "conditioning": [{"pass": "clay"}]}]}
    with pytest.raises(SystemExit, match="D-120"):
        m.require_d120_compliance(bad)


def test_p14_checks_d120_before_prefetch_and_generation():
    source = (DIR / "p14_ltx.py").read_text(encoding="utf-8")
    main = source[source.index("def main():"):source.index("def run_all(")]
    prefetch = source[source.index("def prefetch():"):source.index("def main():")]
    assert main.index("require_d120_compliance(jobs_doc)") < main.index("run_all(cfg, jobs_doc")
    assert prefetch.index("require_d120_compliance(jobs_doc)") < prefetch.index("download_base(cfg")


def test_the_upscale_filter_is_finish_upscale_s_route_test_chain_and_off_on_the_lean_pod():
    assert CFG["upscale"]["enabled"] is False     # the lean plan: no upscale on the pod (free on the PC, only the picked clip)
    assert CFG["upscale"]["vf"] == U.video_filter(1920, 1088, **U.ROUTE_TEST)
    assert "crop=1920:1080" in CFG["upscale"]["vf"] and "cas=" in CFG["upscale"]["vf"] and "noise=" in CFG["upscale"]["vf"]
    assert JOBS["code"]["sha"] == CFG["code"]["sha"] and {j["width"] for j in JOBS["jobs"]} == {1920}


def test_commands_use_only_the_flags_table_and_the_right_weight_layout(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    by = {j["id"]: j for j in JOBS["jobs"]}
    paths = {"controls": [("/in/a.mp4", 0.7), ("/in/d.mp4", 0.7)], "images": [("/in/f.png", 0)], "mask": None, "out": "/o.mp4"}
    c23 = m.command(by["S02-02.c1.ltx23.line_foremid.s42"], CFG, paths)
    flags = {x for x in c23 if str(x).startswith("--")}
    assert flags <= set(m.FLAGS.values())
    assert "--distilled-checkpoint-path" in c23 and "--gemma-root" in c23 and "--transformer-path" not in c23
    assert c23.count("--video-conditioning") == 2 and "--stage-2-ic-lora" in c23
    c25 = m.command(by["S03-02.ltx25.clay.s42"], CFG, {**paths, "controls": [("/in/c.mp4", 1.0)]})
    assert "--transformer-path" in c25 and "--video-vae-path" in c25 and "--distilled-checkpoint-path" not in c25
    assert "--stage-2-ic-lora" not in c25 and c25[c25.index("--num-frames") + 1] == "121"
    i = c25.index("--image")
    assert c25[i + 1:i + 4] == ["/in/f.png", "0", "1.0"]


def test_the_derived_controls_and_the_chain_frames(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    assert m.derive_cmd(CFG, "invert", "a", "b")[m.derive_cmd(CFG, "invert", "a", "b").index("-vf") + 1] == "negate"
    canny = m.derive_cmd(CFG, "canny", "a", "b")
    assert canny[canny.index("-vf") + 1] == CFG["controls"]["canny_vf"]
    ch = m.chain_cmd("prev.mp4", 8, 145, "f_%d.png")
    assert "select='gte(n\\,137)'" in ch


def test_a_whole_run_with_fakes_skips_the_unpinned_base_chains_b_from_a_and_records_speeds(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    out, ran, shell = tmp_path / "out", [], []

    def runner(cmd, timeout, log, label):
        ran.append(label)
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"clip " + label.encode())
        return 0, ""

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(path.encode())
        return p, hashlib.sha256(path.encode()).hexdigest()

    def sh(cmd, check=False):
        shell.append(cmd)
        Path(cmd[-1].replace("%d", "0")).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1].replace("%d", "0")).write_bytes(b"x")
        return SimpleNamespace(returncode=0)

    import time
    on = {**CFG, "upscale": {**CFG["upscale"], "enabled": True}}   # the upscale path itself, turned on for this test only
    rows = m.run(on, JOBS, out, time.time() + 3600, m.Log(out), runner=runner, fetch=fetch,
                 download=lambda cfg, base, log: [], sh=sh)
    status = {r["job"]: r["status"] for r in rows}
    gemma_pinned = all(j["text_encoder"]["sha256"] for j in JOBS["jobs"] if j["base"] == "ltx23")
    for j in JOBS["jobs"]:
        assert status[j["id"]] == ("ok" if j["base"] == "ltx25" or gemma_pinned else "skipped"), j["id"]
    assert "S02-02.c2.ltx25.colour.s42" in ran and ran.index("S02-02.c1.ltx25.colour.s42") < ran.index("S02-02.c2.ltx25.colour.s42")
    side = json.loads((out / "ltx" / "S02-02.c2.ltx25.colour.s42.json").read_text())
    assert side["cmd"].count("--image") == 8 and side["upscaled"]["path"] == "ltx_up/S02-02.c2.ltx25.colour.s42.mp4"
    sp = json.loads((out / "ltx" / "speeds.json").read_text())
    assert sp["ok"] == len(ran) and sp["failure_rate"] == 0.0
    assert any(c[c.index("-vf") + 1] == CFG["upscale"]["vf"] for c in shell if "-vf" in c)


def test_nothing_starts_inside_the_end_reserve_and_a_failed_clip_a_skips_its_chain(tmp_path, monkeypatch):
    m = _load(tmp_path, monkeypatch)
    assert not m.may_start(1000, 1000 + 599, 600) and m.may_start(1000, 1000 + 601, 600)
    jobs = {**JOBS, "jobs": [j for j in JOBS["jobs"] if j["base"] == "ltx25" and j["shot_id"] == "S02-02"]}

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    import time
    out = tmp_path / "o"
    rows = m.run(CFG, jobs, out, time.time() + 3600, m.Log(out), runner=lambda *a: (1, "oom"), fetch=fetch,
                 download=lambda *a: [], sh=lambda *a, **k: SimpleNamespace(returncode=0))
    st = {r["job"]: r for r in rows}
    assert st["S02-02.c1.ltx25.colour.s42"]["status"] == "failed"
    assert st["S02-02.c2.ltx25.colour.s42"]["status"] == "skipped" and "did not finish" in st["S02-02.c2.ltx25.colour.s42"]["reason"]
