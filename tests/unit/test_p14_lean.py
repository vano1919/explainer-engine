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
SCH = {s["id"]: s for s in json.loads((DIR / "p14_schedule.json").read_text(encoding="utf-8"))["stages"]}
LEAN_IDS = ["S02-02.c1.ltx25.colour.s42", "S02-02.c1.ltx23.canny_full.s42", "S02-02.c1.ltx23.line_foremid.s42",
            "S02-02.c2.ltx25.colour.s42", "S03-02.ltx25.clay.s42"]


GPU_ENV = p14_pod.gpu_env   # the real one, for the vendor test (the fixture below stands it in everywhere else)


@pytest.fixture(autouse=True)
def _no_card(monkeypatch):
    """No test reads this machine's EGL vendors: Blender stays on the CPU unless a test gives the pod a card."""
    monkeypatch.setattr(p14_pod, "gpu_env", lambda base, work: (None, {"vendor_files": []}))


def _ltx(tmp_path, monkeypatch):
    monkeypatch.setenv("P14_MODELS", str(tmp_path / "models"))
    spec = importlib.util.spec_from_file_location("p14_ltx_lean", DIR / "p14_ltx.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# --- stage order ----------------------------------------------------------------------------------------------------------------

def test_the_stage_order_and_the_lanes():
    assert ST["order"] == ["A", "B", "C", "D", "E", "X", "G", "F"]
    # fix 2 (Fable thread 15:07 UTC): the GPU lane is the schedule's stages in the order RP-11 costs; B and E split per input
    assert p14_pod.LANES["gpu"] == ST["gpu_order"] == ["qwen1", "D", "B.duel", "B.battle", "E.duel", "X6.ltx", "E.battle",
                                                      "E.battle_line", "G", "X3", "X4", "F"]
    assert p14_pod.LANES["cpu"] == ST["cpu_order"] and p14_pod.NEEDS["B.battle"] == ["A.frame0.battle"]
    assert p14_pod.NEEDS["G"] == ["D"] and p14_pod.NEEDS["X3"] == p14_pod.NEEDS["X4"] == ["G"]
    every = [j["id"] for j in JOBS["jobs"]] + [j["id"] for j in EXTRA["jobs"]]
    split = [i for ids in ST["E_stages"].values() for i in ids]
    assert sorted(split) == sorted(every) and len(split) == len(set(split))   # each LTX job in exactly one stage


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
    assert {"E.duel", "X6.ltx", "E.battle", "E.battle_line"} <= set(run.calls)          # the LTX stages still ran
    assert rows["F"]["status"] == "ok" and (tmp_path / "out" / "step3" / "speeds.json").exists()
    assert rows["X4"]["status"] == "skipped" and rows["X3"]["status"] == "skipped" and "G" in rows["X3"]["reason"]
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


# --- the 14:44 UTC fix (pod ygg2ztmflr8pv2: the battle's line frame 0 held the card idle) ---------------------------------------

class SlowBattle(FakeRun):
    """A FakeRun whose battle line frame 0 never finishes in time (it 'times out'), while the duel's frame 0 is written; records the
    order the stages started in and whether qwen1 started while the battle frame 0 still ran."""

    def __init__(self, pod_dirs, **kw):
        super().__init__(**kw)
        self.lay_f0, self.qwen1_started, self.qwen1_during_battle = pod_dirs, threading.Event(), False

    def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
        name = Path(log_path).stem if log_path else "?"
        if name == "A.frame0.duel":
            f = self.lay_f0 / "duel" / "line" / "frames" / "frame_000000.png"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"png")
        if name == "A.frame0.battle":
            self.calls.append(name)
            self.qwen1_during_battle = self.qwen1_started.wait(10)   # the card is busy while Blender draws
            return "timeout", float(timeout)
        if name == "qwen1":
            self.qwen1_started.set()
        if name == "E.duel":
            self.e_env = env
        return super().__call__(cmd, timeout=timeout, env=env, log_path=log_path, deadline=deadline)


def test_the_card_works_while_the_battle_frame_0_is_drawn_and_b_goes_on_with_the_duel(tmp_path, monkeypatch):
    lay = tmp_path / "lay"
    run = SlowBattle(Path(str(lay) + "_f0"))
    pod = p14_pod.Pod(ST, tmp_path / "out", binary="blender", deadline=time.time() + 3600, run=run, layouts_work=lay,
                      assets=tmp_path / "assets")
    monkeypatch.setattr(p14_pod.Pod, "publish_layout", lambda self, scene: None)
    monkeypatch.setattr(p14_pod.Pod, "g_frames", lambda self, sid, d: None)
    monkeypatch.setattr(p14_j5, "run", lambda *a, **k: 0)
    pod.main()
    rows = pod.book.rows
    assert run.qwen1_during_battle                                    # C and X6.still did not wait for the battle frame 0
    assert run.calls.index("qwen1") < run.calls.index("B.duel") and run.calls.index("D") < run.calls.index("B.duel")
    assert run.calls.index("B.duel") < run.calls.index("A.frame0.battle") or run.qwen1_during_battle   # the duel did not wait
    assert rows["A.frame0.duel"]["status"] == "ok" and rows["A.frame0.battle"]["rc"] == "timeout"
    assert rows["A.frame0"]["scenes"] == ["duel"] and rows["A.frame0"]["missing"] == ["battle"]
    assert SCH["A.frame0.battle"]["on"]["cpu"]["max_min"] == 10 and SCH["A.frame0.duel"]["on"]["cpu"]["max_min"] == 2
    assert pod.book.rows["B.battle"]["status"] == "skipped" and "B.battle" not in run.calls   # B went on with the duel alone
    line = rows["A.battle.line"]
    assert line["status"] == "skipped" and "did not finish" in line["reason"] and "A.battle.line" not in run.calls
    assert run.calls.index("A.duel") < run.calls.index("E.duel")      # E.duel waited for its own clip only
    assert run.e_env["P14_JOBS"] == ",".join(ST["E_stages"]["E.duel"]) and run.e_env["P14_TAG"] == "E.duel"


def test_the_battle_line_runs_only_when_frame_0_s_time_fits_its_budget(tmp_path, monkeypatch):
    lay = tmp_path / "lay"
    secs = {"A.frame0.duel": 5.0, "A.frame0.battle": 30.0}

    class Run(FakeRun):
        def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
            name = Path(log_path).stem
            if name in secs:
                scene = name.split(".")[-1]
                f = Path(str(lay) + "_f0") / scene / "line" / "frames" / "frame_000000.png"
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"png")
                self.calls.append(name)
                return 0, secs[name]
            return super().__call__(cmd, timeout=timeout, env=env, log_path=log_path, deadline=deadline)

    monkeypatch.setattr(p14_pod.Pod, "publish_layout", lambda self, scene: None)
    budget = next(r for r in ST["A"]["renders"] if not r["core"])
    assert budget["frames"] == 282 and budget["passes"] == ["line"]   # the battle's two 145-frame clips, 8 shared
    line_s = SCH["A.battle.line"]["on"]["cpu"]["max_min"] * 60          # its budget is its max in the schedule
    for f0, ran in ((30.0, False), (line_s / budget["frames"] - 1, True)):
        secs["A.frame0.battle"] = f0
        run = Run()
        pod = p14_pod.Pod(ST, tmp_path / f"out{f0}", binary="b", deadline=time.time() + 3600, run=run, layouts_work=lay,
                          assets=tmp_path / "a")
        pod.stage_a()
        assert ("A.battle.line" in run.calls) is ran
        if not ran:
            assert f"over the {round(line_s)} s budget" in pod.book.rows["A.battle.line"]["reason"]


def test_ltx_jobs_that_read_the_battle_line_wait_at_the_end_of_the_queue(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)
    lay, flag = tmp_path / "layouts", tmp_path / "pending.json"
    for name in ("battle/colour/battle_c1_colour.mp4", "battle/colour/battle_c2_colour.mp4", "battle/depth/battle_c1_depth.mp4",
                 "duel/clay/duel_c1_clay.mp4"):
        (lay / name).parent.mkdir(parents=True, exist_ok=True)
        (lay / name).write_bytes(b"x")
    flag.write_text(json.dumps({"prefixes": [f"{LJ.HF_ROOT}/layouts/"]}))
    monkeypatch.setenv("P14_LOCAL_ROOTS", json.dumps([[f"{LJ.HF_ROOT}/layouts", str(lay)]]))
    monkeypatch.setenv("P14_PENDING", str(flag))
    order = []

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    def runner(cmd, timeout, log, label):
        order.append(label)
        if len(order) == 6:   # the last job that does not need the line: stage A ends, the line clip lands
            (lay / "battle/line").mkdir(parents=True, exist_ok=True)
            (lay / "battle/line/battle_c1_line.mp4").write_bytes(b"x")
            flag.unlink()
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"clip")
        return 0, ""

    def sh(cmd, check=False):
        Path(cmd[-1].replace("%d", "0")).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1].replace("%d", "0")).write_bytes(b"x")
        return SimpleNamespace(returncode=0)

    out = tmp_path / "o"
    m.run_all(CFG, JOBS, out, time.time() + 3600, m.Log(out), runner=runner, fetch=fetch, download=lambda *a: [], sh=sh,
              sleep=lambda s: pytest.fail("nothing to wait for: the line clip landed before the queue ran dry"))
    line = ["S02-02.c1.ltx23.line_foremid.s42", "X2.S02-02.c1.ltx25.line_inv.s42"]
    assert order[-2:] == line and len(order) == len(JOBS["jobs"]) + len(EXTRA["jobs"])
    assert order.index("X1.S03-02.ltx25.i2v.s42") < order.index(line[0])     # the extras did not wait behind the line
    core = json.loads((out / "ltx" / "speeds.json").read_text())
    extra = json.loads((out / "ltx" / "speeds_extra.json").read_text())
    assert [r["job"] for r in core["rows"]] == [j for j in LEAN_IDS if j != line[0]] + [line[0]]
    assert len(extra["rows"]) == len(EXTRA["jobs"]) and all(r["status"] == "ok" for r in core["rows"] + extra["rows"])


def test_a_timed_out_stage_kills_its_whole_process_group(tmp_path):
    import os
    pidf = tmp_path / "pid"
    t0 = time.time()
    rc, _ = p14_pod.run_proc(["bash", "-c", f"sleep 60 & echo $! > {pidf}; wait"], timeout=1.5, log_path=tmp_path / "l.log")
    assert rc == "timeout" and time.time() - t0 < 30
    pid = int(pidf.read_text())
    time.sleep(0.3)
    try:
        os.kill(pid, 0)
        with open(f"/proc/{pid}/stat") as f:
            gone = f.read().split()[2] == "Z"
    except (ProcessLookupError, FileNotFoundError):
        gone = True
    assert gone                                                       # the grandchild (Blender's stand-in) died with it


def test_the_blender_log_tails_land_in_the_uploaded_logs(tmp_path):
    src, dst = tmp_path / "blender.log", tmp_path / "logs" / "A.battle.line.blender_tail.txt"
    src.write_text("".join(f"line {i}\n" for i in range(500)))
    with p14_pod.Tailer([(src, dst)], every=0.05):
        time.sleep(0.2)
        assert dst.exists()
    got = dst.read_text().splitlines()
    assert len(got) == p14_pod.TAIL_LINES and got[-1] == "line 499"


# --- Blender on the card (the creator 2026-11-06 14:49 UTC) and the BiRefNet dtype (pod ygg2ztmflr8pv2, D failed 12/12) ----------

def test_the_egl_vendor_for_the_card_is_nvidia_s_only(tmp_path):
    d = tmp_path / "egl"
    d.mkdir()
    (d / "50_mesa.json").write_text("{}")
    env, seen = GPU_ENV({"CUDA_VISIBLE_DEVICES": "", "X": "1"}, tmp_path / "w", dirs=(str(d),), ldconfig=lambda: "")
    assert env is None and seen["vendor_files"] == [str(d / "50_mesa.json")]          # Mesa alone: Blender stays on the CPU
    lib = "\tlibEGL_nvidia.so.0 (libc6,x86-64) => /usr/lib/x86_64-linux-gnu/libEGL_nvidia.so.0\n"
    env, seen = GPU_ENV({"CUDA_VISIBLE_DEVICES": ""}, tmp_path / "w", dirs=(str(d),), ldconfig=lambda: lib)
    written = tmp_path / "w" / "10_nvidia.json"
    assert env["__EGL_VENDOR_LIBRARY_FILENAMES"] == str(written) and "CUDA_VISIBLE_DEVICES" not in env
    assert json.loads(written.read_text())["ICD"]["library_path"] == "libEGL_nvidia.so.0"
    (d / "10_nvidia.json").write_text("{}")
    env, seen = GPU_ENV({}, tmp_path / "w2", dirs=(str(d),), ldconfig=lambda: "")
    assert env["__EGL_VENDOR_LIBRARY_FILENAMES"] == str(d / "10_nvidia.json")       # never the Mesa file: it cannot shadow
    assert p14_pod.cpu_env({})["__EGL_VENDOR_LIBRARY_FILENAMES"].endswith("50_mesa.json")


@pytest.mark.parametrize("renderer,on_card", [("NVIDIA H100 NVL/PCIe/SSE2", True), ("llvmpipe (LLVM 15.0.7, 256 bits)", False)])
def test_the_preflight_frame_decides_card_or_cpu_and_only_a_and_g_follow_it(tmp_path, monkeypatch, renderer, on_card):
    lay = tmp_path / "lay"
    gpu = {"__EGL_VENDOR_LIBRARY_FILENAMES": "/x/10_nvidia.json", "MARK": "gpu"}
    monkeypatch.setattr(p14_pod, "gpu_env", lambda base, work: (dict(base, **gpu), {"used": "/x/10_nvidia.json"}))
    monkeypatch.setattr(p14_pod.Pod, "publish_layout", lambda self, scene: None)
    monkeypatch.setattr(p14_pod.Pod, "g_frames", lambda self, sid, d: None)
    g_env = {}
    monkeypatch.setattr(p14_j5, "run", lambda *a, **k: g_env.update(k.get("env") or {}) or 0)

    class Run(FakeRun):
        envs = {}

        def __call__(self, cmd, *, timeout=None, env=None, log_path=None, deadline=None):
            name = Path(log_path).stem
            self.envs[name] = env
            if name in ("A.preflight", "A.frame0.duel"):
                d = Path(str(lay) + "_f0") / "duel" / "line"
                (d / "frames").mkdir(parents=True, exist_ok=True)
                (d / "frames" / "frame_000000.png").write_bytes(b"png")
                (d / "progress.jsonl").write_text(json.dumps({"index": 0, "file": "frame_000000.png", "seconds": 0.9}) + "\n")
                gl = renderer if name == "A.preflight" else "llvmpipe"
                (d / "bpy_report.json").write_text(json.dumps({"gl": {"vendor": gl.split()[0], "renderer": gl}}))
                assert name != "A.preflight" or timeout == p14_pod.PREFLIGHT_S == 120
            return super().__call__(cmd, timeout=timeout, env=env, log_path=log_path, deadline=deadline)

    run = Run()
    pod = p14_pod.Pod(ST, tmp_path / "out", binary="b", deadline=time.time() + 3600, run=run, layouts_work=lay, assets=tmp_path / "a")
    pod.main()
    pre = pod.book.rows["A.preflight"]
    assert pre["chosen"] == ("gpu" if on_card else "cpu") and pre["budget_s"] == 120 and "s_per_frame" in pre
    assert ("A.frame0.duel" in run.calls) is not on_card                 # a frame drawn on the card is kept, not drawn twice
    assert pod.book.rows["A.frame0.duel"]["status"] == "ok"
    want = "gpu" if on_card else None
    assert run.envs["A.battle"].get("MARK") == want and run.envs["A.frame0.battle"].get("MARK") == want
    assert pre["s_per_frame"] == 0.9                                    # the frame's own seconds, not the scene build
    if on_card:
        assert g_env.get("MARK") == "gpu" and pod.book.rows["G"]["cut_at_min"] == SCH["G"]["on"]["gpu"]["max_min"]
    else:                                                                # G renders free on CI or the PC, X3 and X4 with it
        assert run.envs["A.battle"]["CUDA_VISIBLE_DEVICES"] == "" and not g_env
        assert pod.book.rows["G"]["status"] == "skipped" and "D-114" in pod.book.rows["G"]["reason"]
        assert pod.book.rows["X3"]["status"] == "skipped" and pod.book.rows["X4"]["status"] == "skipped"
    assert run.envs["qwen1"].get("MARK") is None and "__EGL_VENDOR_LIBRARY_FILENAMES" not in run.envs["E.duel"]   # Qwen/LTX untouched


def test_the_birefnet_input_takes_the_dtype_of_the_weights():
    from explainer_engine.edit import cutout as CUT

    class X:
        def to(self, device=None, dtype=None):
            return ("moved", device, dtype)

    class Model:
        def parameters(self):
            return iter([SimpleNamespace(dtype="float16")])

    assert CUT.model_input(Model(), X(), "cuda") == ("moved", "cuda", "float16")


def test_a_job_waits_for_g_s_frame_and_runs_when_g_settles_it_or_is_skipped_at_the_reserve(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)
    step3, flag = tmp_path / "step3", tmp_path / "pending.json"
    x3 = f"{LJ.HF_ROOT}/step3/first_frames/S01-02.j5.png"
    flag.write_text(json.dumps({"prefixes": [x3]}))
    monkeypatch.setenv("P14_LOCAL_ROOTS", json.dumps([[f"{LJ.HF_ROOT}/step3", str(step3)]]))
    monkeypatch.setenv("P14_PENDING", str(flag))
    monkeypatch.setenv("P14_EXTRAS", "0")
    doc = dict(EXTRA, schema="ltx_job/1", jobs=[j for j in EXTRA["jobs"] if j["id"].startswith(("X1.", "X3."))])
    order, sleeps = [], []

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    def runner(cmd, timeout, log, label):
        order.append(label)
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"clip")
        return 0, ""

    def sleep(s):   # G draws S01-02 while E waits: the frame lands and the promise is dropped
        sleeps.append(s)
        (step3 / "first_frames").mkdir(parents=True, exist_ok=True)
        (step3 / "first_frames" / "S01-02.j5.png").write_bytes(b"png")
        flag.unlink()

    out = tmp_path / "o"
    m.run_all(CFG, doc, out, time.time() + 3600, m.Log(out), runner=runner, fetch=fetch, download=lambda *a: [], sleep=sleep)
    assert order == ["X1.S03-02.ltx25.i2v.s42", "X3.S01-02.ltx25.i2v.s42"] and len(sleeps) == 1
    flag.write_text(json.dumps({"prefixes": [x3]}))
    (step3 / "first_frames" / "S01-02.j5.png").unlink()
    order.clear()
    rows = m.run_all(CFG, doc, out, time.time() + CFG["end_reserve_min"] * 60 - 1, m.Log(out), runner=runner, fetch=fetch,
                     download=lambda *a: [], sleep=lambda s: pytest.fail("no waiting inside the end reserve"))
    assert order == [] and {r["job"]: r.get("reason") for r in rows}["X3.S01-02.ltx25.i2v.s42"] == "inside the end reserve"


def test_the_schedule_file_is_the_stage_graph_and_is_regenerated_not_hand_edited():
    from explainer_engine.cloud import schedule as S
    sch = json.loads((DIR / "p14_schedule.json").read_text(encoding="utf-8"))
    assert sch == json.loads(json.dumps(lean.schedule())) and S.validate(sch) == []
    ids = [s["id"] for s in sch["stages"]]
    assert set(ids) == {s for lane in p14_pod.LANES.values() for s in lane}            # the pod's stages, every one
    for s in sch["stages"]:
        for lane, v in s["on"].items():
            assert v["max_min"] <= max(3.5 * v["expected_min"], 2), (s["id"], lane)   # maxes ~3x the expected (2 min floor)
    assert {k for k in SCH["A.battle"]["on"]} == {"cpu", "gpu"} and list(SCH["G"]["on"]) == ["gpu"]
    assert "A.frame0.battle" not in SCH["B.duel"]["needs"] and "A.battle.line" not in SCH["E.battle"]["needs"]


def test_rp11_passes_with_the_pod_s_own_order():
    """The check runpod create asks (cloud/schedule.py, RP-11), on the file and with the order the pod's GPU lane commits to."""
    from explainer_engine.cloud import schedule as S
    sch = S.load(DIR / "p14_schedule.json")
    res = S.plan(sch)
    own = S.committed(sch, "H100 NVL", ST["gpu_order"])
    assert S.check(sch, res, own) == [], S.report(sch, res)
    assert own["worst"]["usd"] <= sch["limits"]["max_usd"] and own["worst"]["pod_min"] <= sch["limits"]["max_hours"] * 60
    assert own["worst"]["idle_share"] <= sch["limits"]["max_idle_gpu_share"]


def test_every_timeout_in_the_code_is_the_schedule_s_max(tmp_path):
    pod = p14_pod.Pod(ST, tmp_path / "out", binary="b", deadline=time.time() + 3600, run=FakeRun(), layouts_work=tmp_path / "l",
                      assets=tmp_path / "a")
    for sid in ("weights", "weights_qwen", "qwen1", "D", "B.duel", "E.battle", "G", "X4"):
        lane = next(iter(SCH[sid]["on"]))
        assert pod.max_s(sid) == SCH[sid]["on"][lane]["max_min"] * 60
    assert pod.blender_max_s("A.battle") == SCH["A.battle"]["on"]["cpu"]["max_min"] * 60
    pod.blender_on = "gpu"
    assert pod.blender_max_s("A.battle") == SCH["A.battle"]["on"]["gpu"]["max_min"] * 60
    assert CFG["clip_timeout_s"] == 600 and SCH["E.battle"]["on"]["gpu"]["max_min"] == 10 * len(ST["E_stages"]["E.battle"])


def test_an_e_stage_runs_only_its_own_jobs_into_its_own_speeds_files(tmp_path, monkeypatch):
    m = _ltx(tmp_path, monkeypatch)
    order = []

    def fetch(cfg, path, want, work):
        p = Path(work) / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
        return p, "0" * 64

    def runner(cmd, timeout, log, label):
        order.append(label)
        assert timeout == 600
        Path(cmd[cmd.index("--output-path") + 1]).write_bytes(b"clip")
        return 0, ""

    def sh(cmd, check=False):
        Path(cmd[-1].replace("%d", "0")).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1].replace("%d", "0")).write_bytes(b"x")
        return SimpleNamespace(returncode=0)

    want = ST["E_stages"]["E.battle"]
    out = tmp_path / "o"
    doc = dict(JOBS, jobs=[j for j in JOBS["jobs"] if j["id"] in want])
    m.run_all(CFG, doc, out, time.time() + 3600, m.Log(out), runner=runner, fetch=fetch, download=lambda *a: [], sh=sh,
              want=want, tag="E.battle")
    assert order == want                                              # c1 colour, canny, c2 (chained on c1), then X5
    core = json.loads((out / "ltx" / "speeds.E.battle.json").read_text())
    extra = json.loads((out / "ltx" / "speeds_extra.E.battle.json").read_text())
    assert [r["job"] for r in core["rows"]] == want[:3] and [r["job"] for r in extra["rows"]] == want[3:]
    assert not (out / "ltx" / "speeds.json").exists()


def test_b_runs_per_scene():
    cfg = p14_qwen.load_cfg()
    assert [j["name"] for j in p14_qwen.jobs(cfg, ["B"], "duel")] == ["B_S03-02_duel"]
    assert [j["name"] for j in p14_qwen.jobs(cfg, ["B"], "battle")] == ["B_S02-02.c1_battle"]
    assert len(p14_qwen.jobs(cfg, ["B"])) == 2
