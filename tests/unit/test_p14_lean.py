"""The lean step-3 pod (STEP3_POD_PLAN_LEAN_ka.md; the creator 2026-11-06 13:21 UTC, stage G 13:25 UTC, extras 13:33 UTC): the stage
order and lanes, the five-job LTX matrix in the plan's order, no upscale on the pod, a failed stage that never ends the pod, the
extras' jobs, the Qwen and cut-out lists, the J5 shots of the pilot window and the byte-stable code bundle. No GPU, no network."""
import gzip
import hashlib
import importlib.util
import io
import json
import tarfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.core import contracts as C
from explainer_engine.edit import ltx_jobs as LJ
from explainer_engine.qa import style_prompt
from explainer_engine.training.pods.p14 import lean, p14_j5, p14_pod, p14_qwen

DIR = Path(lean.__file__).resolve().parent
ST = json.loads((DIR / "p14_stages.json").read_text(encoding="utf-8"))
JOBS = json.loads((DIR / "ltx_jobs.json").read_text(encoding="utf-8"))
EXTRA = json.loads((DIR / "ltx_extra.json").read_text(encoding="utf-8"))
CFG = json.loads((DIR / "p14.json").read_text(encoding="utf-8"))
LEAN_IDS = ["S02-02.c1.ltx25.colour.s42", "S02-02.c1.ltx23.canny_full.s42", "S02-02.c1.ltx23.line_foremid.s42",
            "S02-02.c2.ltx25.colour.s42", "S03-02.ltx25.clay.s42"]


def _ltx(tmp_path, monkeypatch):
    monkeypatch.setenv("P14_MODELS", str(tmp_path / "models"))
    spec = importlib.util.spec_from_file_location("p14_ltx_lean", DIR / "p14_ltx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- stage order ----------------------------------------------------------------------------------------------------------------

def test_the_stage_order_and_the_lanes():
    assert ST["order"] == ["A", "B", "C", "D", "E", "X", "G", "F"]
    gpu = p14_pod.LANES["gpu"]
    assert gpu.index("B") < gpu.index("D") < gpu.index("E") < gpu.index("X1") < gpu.index("X2") < gpu.index("X5") < gpu.index("X3")
    assert gpu.index("X3") < gpu.index("X6.ltx") < gpu.index("X4") < gpu.index("F")
    assert p14_pod.LANES["cpu"] == ["A", "X6.move", "G"] and p14_pod.NEEDS["G"] == ["D"] and p14_pod.NEEDS["B"] == ["A.frame0"]
    assert ST["gpu_order"][:5] == ["B", "C", "X6.still", "D", "E"]


def test_the_five_lean_ltx_jobs_in_the_plan_s_order():
    assert [j["id"] for j in JOBS["jobs"]] == LEAN_IDS
    assert {j["seed"] for j in JOBS["jobs"]} == {42}
    c2 = JOBS["jobs"][3]
    assert c2["chain_from"] == {"job": "S02-02.c1.ltx25.colour.s42", "frames": 8}
    assert not [f for f in C.errors(JOBS) if f["severity"] == "FAIL"]
    assert all(j["output"].startswith("route_test_2026-11/step3/ltx/") for j in JOBS["jobs"])
    assert all(j["first_frame"]["path"].startswith("route_test_2026-11/step3/first_frames/") for j in JOBS["jobs"])
    assert LJ.build(json.loads(lean.ROUTE_SHOTS.read_text()), matrix=LJ.LEAN, out_root="step3") == JOBS   # regenerated, not hand-edited


def test_no_upscale_on_the_pod(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)
    assert CFG["upscale"]["enabled"] is False
    out, shell = tmp_path / "o", []

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    def runner(cmd, timeout, log, label):
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"clip")
        return 0, ""

    def sh(cmd, check=False):
        shell.append(cmd)
        Path(cmd[-1].replace("%d", "0")).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1].replace("%d", "0")).write_bytes(b"x")
        return SimpleNamespace(returncode=0)

    m.run(CFG, JOBS, out, time.time() + 3600, m.Log(out), runner=runner, fetch=fetch, download=lambda *a: [], sh=sh)
    assert not (out / "ltx_up").exists()
    assert not any("scale=2560:1440" in " ".join(map(str, c)) for c in shell)
    assert all("upscaled" not in json.loads(p.read_text()) for p in (out / "ltx").glob("S0*.json"))


# --- continue on failure --------------------------------------------------------------------------------------------------------

def test_two_failed_generations_in_a_row_stop_the_ltx_stage_and_a_bad_control_skips_only_its_job(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    def sh(cmd, check=False):
        if "edgedetect" in " ".join(map(str, cmd)):
            raise RuntimeError("ffmpeg died")
        Path(cmd[-1].replace("%d", "0")).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1].replace("%d", "0")).write_bytes(b"x")
        return SimpleNamespace(returncode=0)

    out = tmp_path / "o"
    rows = m.run(CFG, JOBS, out, time.time() + 3600, m.Log(out), runner=lambda *a: (1, "oom"), fetch=fetch,
                 download=lambda *a: [], sh=sh)
    st = {r["job"]: r for r in rows}
    assert st[LEAN_IDS[0]]["status"] == "failed"
    assert st[LEAN_IDS[1]]["status"] == "skipped" and "deriving canny" in st[LEAN_IDS[1]]["reason"]   # the canny failed: only its job
    assert st[LEAN_IDS[2]]["status"] in ("failed", "skipped")
    gemma = all(j["text_encoder"]["sha256"] for j in JOBS["jobs"] if j["base"] == "ltx23")
    if gemma:
        assert st[LEAN_IDS[2]]["status"] == "failed"
        assert "in a row" in st[LEAN_IDS[4]]["reason"]


class FakeRun:
    """Stands in for run_proc: every stage process 'runs' at once; ``fail`` names the stage logs that return 1."""

    def __init__(self, fail=()):
        self.fail, self.calls = set(fail), []

    def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
        name = Path(log_path).stem if log_path else "?"
        self.calls.append(name)
        return (1 if name in self.fail else 0), 0.1


def test_a_failed_stage_never_ends_the_pod(tmp_path, monkeypatch):
    run = FakeRun(fail={"D", "qwen1"})
    pod = p14_pod.Pod(ST, tmp_path / "out", binary="blender", deadline=time.time() + 3600, run=run,
                      layouts_work=tmp_path / "lay", assets=tmp_path / "assets")
    monkeypatch.setattr(p14_pod.Pod, "publish_layout", lambda self, scene: None)
    monkeypatch.setattr(p14_pod.Pod, "g_frames", lambda self, sid, d: None)
    from explainer_engine.training.pods.p14 import p14_j5 as J
    monkeypatch.setattr(J, "run", lambda *a, **k: pytest.fail("G must not run without D's cut-outs"))
    pod.main()
    rows = pod.book.rows
    assert rows["D"]["status"] == "failed"
    assert rows["G"]["status"] == "skipped" and "D" in rows["G"]["reason"]
    assert rows["E"]["status"] in ("running", "ok", "failed") and "E" in run.calls      # the LTX stage still ran
    assert rows["F"]["status"] == "ok" and (tmp_path / "out" / "step3" / "speeds.json").exists()
    assert rows["X4"]["status"] == "skipped"
    st = json.loads((tmp_path / "out" / "step3" / "stages.json").read_text())
    assert st["schema"] == "p14_stages_run/1"


def test_nothing_starts_inside_the_end_reserve(tmp_path):
    run = FakeRun()
    pod = p14_pod.Pod(ST, tmp_path / "out", binary="b", deadline=time.time() + 60, run=run, layouts_work=tmp_path / "l",
                      assets=tmp_path / "a")
    assert pod.stage("D", ["x"]) is False and pod.book.rows["D"]["reason"] == "inside the end reserve" and "D" not in run.calls


# --- the extras -----------------------------------------------------------------------------------------------------------------

def test_the_extras_follow_the_core_in_the_card_s_order_and_stay_pinned(tmp_path, monkeypatch):
    ids = [j["id"].split(".")[0] for j in EXTRA["jobs"]]
    assert ids == ["X1", "X2", "X5", "X3", "X6"] and EXTRA["code"] == JOBS["code"]
    by = {j["id"].split(".")[0]: j for j in EXTRA["jobs"]}
    assert all(j["question"] for j in EXTRA["jobs"])
    for k in ("X1", "X3", "X6"):
        assert by[k]["pipeline"] == "distilled" and by[k]["lora"] is None and by[k]["conditioning"] == [] and by[k]["frames"] == 121
    assert by["X2"]["lora"]["sha256"] and [c["pass"] for c in by["X2"]["conditioning"]] == ["line"]
    assert by["X2"]["conditioning"][0]["derive"] == "invert" and by["X2"]["model"]["key"] == JOBS["jobs"][0]["model"]["key"]
    assert (by["X5"]["width"], by["X5"]["height"]) == (2560, 1472) and by["X5"]["width"] % 64 == 0 and by["X5"]["height"] % 64 == 0
    assert all(j["model"]["sha256"] and j["text_encoder"] is None or j["text_encoder"]["sha256"] for j in EXTRA["jobs"])
    m = _ltx(tmp_path, monkeypatch)
    cmd = m.command(by["X1"], CFG, {"controls": [], "images": [("/f.png", 0)], "mask": None, "out": "/o.mp4"})
    assert cmd[2] == "ltx_pipelines.distilled" and "--lora" not in cmd and "--video-conditioning" not in cmd
    assert "--transformer-path" in cmd and "--spatial-upsampler-path" in cmd
    vf = m.derive_cmd(CFG, "scale_2k", "a", "b")
    assert vf[vf.index("-vf") + 1] == "scale=2598:1472:flags=lanczos,crop=2560:1472"
    assert CFG["extra_jobs_file"] == "ltx_extra.json"


def test_the_pod_s_own_inputs_are_read_before_the_vault(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)
    f = tmp_path / "out" / "layouts" / "battle" / "colour" / "battle_c1_colour.mp4"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"clip")
    monkeypatch.setenv("P14_LOCAL_ROOTS", json.dumps([["route_test_2026-11/layouts", str(tmp_path / "out" / "layouts")]]))
    p, sha = m.fetch_input(CFG, "route_test_2026-11/layouts/battle/colour/battle_c1_colour.mp4", None, tmp_path / "w")
    assert p == f and sha == hashlib.sha256(b"clip").hexdigest()
    p, why = m.fetch_input(CFG, "route_test_2026-11/layouts/battle/colour/battle_c1_colour.mp4", "1" * 64, tmp_path / "w")
    assert p is None and "not the pinned" in why


# --- Qwen, cut-outs -------------------------------------------------------------------------------------------------------------

def test_the_qwen_pictures_and_their_prompt_bands():
    js = p14_qwen.jobs(ST, ["B", "C", "X6"])
    assert [j["stage"] for j in js].count("B") == 2 and [j["stage"] for j in js].count("C") == 2
    for j in js:
        n = len(j["prompt"].split())
        assert j["size"] == [1280, 720]
        if j["stage"] == "B":
            assert 40 <= n <= 90 and j["refs"][0][0] == "layout" and j["refs"][0][1]["pass"] == "line" and j["kind"] == "edit"
        if j["stage"] == "C":
            assert 130 <= n <= style_prompt.MAX_WORDS and style_prompt.check(j["prompt"]) == []
    assert {j["clip"] for j in js if j["stage"] == "B"} == {"S02-02.c1", "S03-02"}   # the first frames of the core LTX jobs


def test_line_match_and_the_first_frame():
    lay = Image.new("L", (320, 180), 255)
    ImageDraw.Draw(lay).rectangle((60, 40, 260, 140), outline=0, width=2)
    same = Image.merge("RGB", [lay] * 3)
    blank = Image.new("RGB", (320, 180), (200, 200, 200))
    assert p14_qwen.line_match(lay, same)["kept"] > 0.95
    assert p14_qwen.line_match(lay, blank)["kept"] == 0.0
    ff = p14_qwen.first_frame(Image.new("RGB", (1280, 720)), (1920, 1088))
    assert ff.size == (1920, 1088)


def test_the_twelve_cutouts_are_the_pass_sheets():
    pics = ST["D"]["pictures"]
    assert len(pics) == 12 and len({(p["hero"], p["angle"]) for p in pics}) == 12
    assert any(p["name"] == "E_B_H2_left34" for p in pics) and not any(p["name"] == "B_H2_left34" for p in pics)
    assert all(len(p["sha256"]) == 64 for p in pics)


# --- stage G ----------------------------------------------------------------------------------------------------------------------

def _card(path: Path, colour):
    im = Image.new("RGBA", (400, 1000), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((90, 100, 310, 990), 60, fill=colour + (255,))
    im.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_j5_window_plans_every_shot_with_handles(tmp_path):
    from explainer_engine.blender import assemble_25d as A
    st = json.loads(json.dumps(ST))
    out = tmp_path / "step3"
    (out / "cutout").mkdir(parents=True)
    (out / "backdrops").mkdir()
    rows = []
    for p in st["D"]["pictures"]:
        sha = _card(out / "cutout" / f"{p['name']}.png", (150, 40, 40))
        rows.append({"name": p["name"], "status": "ok", "sha256": sha})
    (out / "cutout" / "report.json").write_text(json.dumps({"pictures": rows}))
    for sc, ref in st["G"]["backdrops"].items():
        b = out / "backdrops" / f"{ref['name']}.png"
        Image.new("RGB", (2048, 1024), (90, 120, 160)).save(b)
        ref["sha256"] = hashlib.sha256(b.read_bytes()).hexdigest()
    doc = p14_j5.scene_assets(st, out / "cutout", out / "backdrops")
    C.validate(doc)
    shots = p14_j5.shots(st)
    assert [s["id"] for s in shots] == ["S01-01", "S01-02", "S01-03", "S01-04", "S01-05", "S01-06", "S02-04", "S03-01", "S03-03"]
    for s in shots:
        body = A.plan(doc, s, base=out, width=2560, height=1440)
        assert body["frames"] == round(st["G"]["seconds"][s["id"]] * 24) + 2 * st["G"]["handles_frames"]
        assert (body["width"], body["height"]) == (2560, 1440)


def test_the_pilot_window_s_j5_shots_are_the_ones_g_renders():
    from explainer_engine.production import pilot
    rs = json.loads(lean.ROUTE_SHOTS.read_text())
    j5 = [s["id"] for s in pilot.select(rs, seconds=60) if s["route"] == "J5"]
    assert j5 == [s["id"] for s in ST["G"]["shots"]]


def test_g_stops_at_its_deadline(tmp_path):
    class P:
        def __init__(self, *a, **k):
            self.returncode = None

        def poll(self):
            return self.returncode

        def kill(self):
            self.returncode = -9

        def wait(self):
            return self.returncode

    body = {"frames": 120, "shot_id": "S", "fps": 24}
    r = p14_j5.render_shot(body, tmp_path / "S", ["blender"], "5.2.3", deadline=time.time() - 1, nice=10, popen=P)
    assert r["rc"] == -9 and r["frames"] == 0 and r["stopped_at_deadline"]


# --- the code bundle --------------------------------------------------------------------------------------------------------------

def test_the_bundle_is_byte_stable_and_leaves_the_script_out(tmp_path, monkeypatch):
    monkeypatch.setattr(lean, "BUNDLE_DIRS", ("explainer_engine/training/pods/p14", "config"))
    a, b = lean.bundle(tmp_path / "a.tgz"), lean.bundle(tmp_path / "b.tgz")
    assert a == b
    with tarfile.open(tmp_path / "a.tgz") as t:
        names = t.getnames()
        assert "explainer_engine/training/pods/p14/p14_pod.py" in names and "explainer_engine/training/pods/p14/p14.sh" not in names
        assert {m.mtime for m in t.getmembers()} == {0} and {m.mode for m in t.getmembers()} == {0o644}


def test_pin_writes_the_one_sha_line(tmp_path):
    sh = tmp_path / "p.sh"
    sh.write_text("x\nprintf '%s  %s\\n' " + lean.PLACE + " \"$JOB/ee_src.tar.gz\" > \"$JOB/sha.txt\"\ny\n")
    lean.pin("a" * 64, sh)
    assert ("a" * 64) in sh.read_text() and lean.PLACE not in sh.read_text()
    lean.pin("b" * 64, sh)
    assert ("b" * 64) in sh.read_text() and ("a" * 64) not in sh.read_text()
