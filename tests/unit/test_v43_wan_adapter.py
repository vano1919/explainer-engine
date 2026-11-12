"""v4.3 plan P6: one Wan adapter, real clip QA instead of ``passed: True``, one retry then the 2.5D fallback, money checked
before every paid attempt, a ledger line per attempt. A fake backend makes the clips (good, frozen, short, wrong start,
crashing), so nothing paid or remote runs."""
from __future__ import annotations

import json
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.aivideo import wan_adapter as WA
from explainer_engine.aivideo import wan_runner
from explainer_engine.core.errors import ConfigError
from explainer_engine.core.ledger import Run

W, H, FPS = 320, 180, 24


@pytest.fixture()
def picture(tmp_path):
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:270, 0:480]
    img = np.zeros((270, 480, 3), np.uint8)
    img[..., 0] = (xx * 255 // 480).astype(np.uint8)
    img[..., 1] = (yy * 255 // 270).astype(np.uint8)
    img[..., 2] = 90
    img[(xx - 300) ** 2 + (yy - 140) ** 2 < 50 ** 2] = [220, 180, 140]
    img = np.clip(img.astype(int) + rng.integers(0, 30, img.shape), 0, 255).astype(np.uint8)
    p = tmp_path / "start.png"
    Image.fromarray(img).save(p)
    return p


def _write(frames, out):
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
                             str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(out)],
                            stdin=subprocess.PIPE)
    for fr in frames:
        proc.stdin.write(np.ascontiguousarray(fr).tobytes())
    proc.stdin.close()
    proc.wait()


class Fake(WA.Backend):
    """Writes a clip from the start picture; ``plan`` lists what each attempt makes."""
    name = "fake"
    service = "modal_usd"

    def __init__(self, plan, paid=False, speed=2.0, rate=1.0):
        self.plan, self.calls, self.paid = list(plan), [], paid
        self.measured_s_per_clip_s, self.usd_per_hour = speed, rate

    def generate(self, job, out):
        kind = self.plan[min(len(self.calls), len(self.plan) - 1)]
        self.calls.append((kind, job.seed))
        if kind == "crash":
            raise RuntimeError("CUDA out of memory")
        src = np.asarray(Image.open(job.start_picture).convert("RGB").resize((int(W * 1.1), int(H * 1.1))))
        if kind == "wrong_start":
            src = src[::-1, ::-1]
        n = job.frames - (8 if kind == "short" else 0)
        frames = []
        for f in range(n):
            o = (src.shape[1] - W) // 2 + (0 if kind == "frozen" else int(round(f * 0.6)) - 7)
            frames.append(src[(src.shape[0] - H) // 2:(src.shape[0] - H) // 2 + H, o:o + W])
        _write(frames, out)


@pytest.fixture()
def caps(tmp_path, monkeypatch):
    """A spend-caps file with a Modal line (the real file has none: a zero approved budget)."""
    def write(modal=(3.0, 6.0)):
        doc = {"per_episode": {}}
        if modal:
            doc["modal"] = {"per_run_usd": modal[0], "per_episode_usd": modal[1]}
        f = tmp_path / "caps.json"
        f.write_text(json.dumps(doc))
        monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(f))
    write()
    return write


def _job(picture, **kw):
    return WA.WanJob(**dict(dict(shot_id="S9", start_picture=str(picture), motion_prompt="she runs", seconds=1.0, seed=7,
                                 width=W, height=H), **kw))


def _status(rows, gate):
    return next(r["status"] for r in rows if r["gate"] == gate)


def test_a_good_clip_passes_its_qa(picture, tmp_path):
    Fake(["good"]).generate(_job(picture), tmp_path / "c.mp4")
    rows = WA.qa_clip(tmp_path / "c.mp4", _job(picture))
    assert {r["gate"]: r["status"] for r in rows if r["status"] == "FAIL"} == {}
    assert _status(rows, "first_frame_is_the_picture") == "PASS" and _status(rows, "enough_frames") == "PASS"


@pytest.mark.parametrize("kind, gate, want", [
    ("frozen", "not_a_still", "FAIL"),
    ("frozen", "no_frozen_run", "REVIEW"),
    ("short", "enough_frames", "FAIL"),
    ("wrong_start", "first_frame_is_the_picture", "REVIEW"),
])
def test_bad_clips_are_caught(picture, tmp_path, kind, gate, want):
    Fake([kind]).generate(_job(picture), tmp_path / "c.mp4")
    assert _status(WA.qa_clip(tmp_path / "c.mp4", _job(picture)), gate) == want


def test_a_missing_clip_fails_to_decode(picture, tmp_path):
    rows = WA.qa_clip(tmp_path / "none.mp4", _job(picture))
    assert rows[0]["gate"] == "clip_decodes" and rows[0]["status"] == "FAIL"


def test_a_fail_is_retried_once_with_a_new_seed_then_kept(picture, tmp_path):
    be = Fake(["short", "good"])
    r = WA.run_shot(_job(picture), be, tmp_path / "out", tmp_path / "ledger.jsonl")
    assert [c[1] for c in be.calls] == [7, 7 + WA.SEED_STEP]
    assert r["route"] == "wan" and r["status"] != "FAIL" and r["fallback"] is None
    lines = [json.loads(x) for x in (tmp_path / "ledger.jsonl").read_text().splitlines()]
    assert [(x["attempt"], x["event"]) for x in lines] == [(1, "submit"), (1, "done"), (2, "submit"), (2, "done")]
    assert lines[3]["sha256"] and (tmp_path / "out" / "S9.mp4").is_file()


def test_two_fails_fall_back_to_the_layered_25d_and_the_report_says_so(picture, tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    be = Fake(["crash", "frozen"])
    shot = {"shot_id": "S9", "fallback_motion_imitation": [{"effect": "push"}, {"effect": "mist"},
                                                           {"effect": "subject_sway"}]}
    r = WA.run_shot(_job(picture), be, tmp_path / "out", tmp_path / "ledger.jsonl", shot=shot)
    assert len(be.calls) == WA.MAX_ATTEMPTS
    assert r["route"] == "still_25d" and r["fallback"]["motion_imitation"] == shot["fallback_motion_imitation"]
    assert "CUDA" in r["attempts"][0]["gates"]["gates"][0]["detail"] and (tmp_path / "out" / "S9.mp4").is_file()


def test_a_paid_backend_needs_the_plan_the_run_and_fits_under_both_caps(picture, tmp_path, caps):
    be = Fake(["good"], paid=True, speed=3600.0, rate=1.0)    # one clip second = one GPU hour = $1
    run = Run.open(tmp_path / "run.json", caps={"modal_usd": 2.5})
    ok = WA.Approval("plan-1", 2.0, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="OR-23"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", run=run)
    with pytest.raises(ConfigError, match="no run ledger"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok)
    tight = WA.Approval("plan-1", 1.5, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="nothing was sent"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=tight, run=run)
    assert be.calls == [] and run.spent("modal_usd") == 0.0
    WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok, run=run)
    assert WA.spent(tmp_path / "l.jsonl") == pytest.approx(1.0) and run.spent("modal_usd") == pytest.approx(1.0)
    assert "wan/plan-1/S9/try1" in Run.open(tmp_path / "run.json").data["reserved"]


def test_the_runs_80_percent_stop_and_the_creators_line_bind_the_plan(picture, tmp_path, caps):
    be = Fake(["good"], paid=True, speed=3600.0, rate=1.0)
    ok = WA.Approval("plan-1", 2.0, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="80 % stop"):    # 2 attempts x $1 > 80 % of a $2 run cap
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok,
                    run=Run.open(tmp_path / "a.json", caps={"modal_usd": 2.0}))
    big = WA.Approval("plan-2", 5.0, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="above the creator's"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=big,
                    run=Run.open(tmp_path / "b.json", caps={"modal_usd": 2.5}))
    assert be.calls == []


def test_no_modal_line_is_a_zero_budget_whatever_the_card_says(picture, tmp_path, caps):
    caps(modal=None)
    be = Fake(["good"], paid=True, speed=3600.0, rate=0.01)
    ok = WA.Approval("plan-1", 2.0, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="zero approved budget"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok,
                    run=Run.open(tmp_path / "run.json", caps={"modal_usd": 2.5}))
    assert be.calls == []


def test_the_real_spend_caps_file_has_no_modal_line_yet():
    """The creator has not set a Modal line: until he does, the Modal backend refuses every paid call."""
    with pytest.raises(Exception, match="zero approved budget"):
        WA.service_ceiling("modal_usd")


def test_no_measured_speed_no_price(picture):
    be = Fake(["good"], speed=None)
    with pytest.raises(ConfigError, match="no measured speed"):
        be.estimate(_job(picture))


LAUNCH = {"app_name": "ee-wan", "model_repo": "org/wan", "model_revision": "a" * 40, "model_files": {"m.safetensors": "b" * 64},
          "pipeline": "SomePipeline", "hf_out": "route_test/wan_out", "settings": {"steps": 30}, "gpu": "A100-80GB", "cpu": 8,
          "memory_gib": 64, "usd_per_h": 3.3872, "prices_date": "2026-11-07",
          "caps": {"smoke_usd": 0.25, "run_usd": 1.0, "cold_start_s": 120}}
LADDER = {"done": ["L0", "L1", "L2", "L3"], "red": None,
          "measured": {"gpu": "A100-80GB", "s_per_clip_s": 60.0, "setup_s": 30.0}}


def test_the_modal_backend_refuses_until_every_gate_holds(caps):
    m = WA.ModalWanBackend()
    bad = " ".join(m.refusals())
    for want in ("no launch file", "ladder is at L0", "no speed measured", "EE_MODAL_GO", "no Modal runner"):
        assert want in bad
    with pytest.raises(ConfigError, match="nothing was sent"):
        m.generate(WA.WanJob("S9", "x.png", "p", 1.0, 7), None)
    half = WA.ModalWanBackend(dict(LAUNCH, model_revision=None), dict(LADDER, done=["L0", "L1", "L2"]),
                              runner=lambda a: (0, ""), fetch=lambda j, o: None, env={"EE_MODAL_GO": "cmsg_1"})
    assert {r.split(":")[0] for r in half.refusals()} >= {"launch model_revision is not pinned",
                                                           "the OR-37 ladder is at L3, not L4"}
    with pytest.raises(ConfigError, match="measured on L4"):
        WA.ModalWanBackend(LAUNCH, dict(LADDER, measured=dict(LADDER["measured"], gpu="L4")))


def test_the_modal_backend_is_priced_from_modal_schedule_and_the_l3_speed(caps):
    from explainer_engine.cloud import modal_schedule as MS
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=lambda a: (0, ""), fetch=lambda j, o: None, env={"EE_MODAL_GO": "cmsg_1"})
    per_s = MS.GPUS["A100-80GB"]["usd_s"] + 8 * MS.CPU_CORE_S + 64 * MS.MEM_GIB_S
    est = m.estimate(WA.WanJob("S9", "x.png", "p", 2.0, 7))
    assert est["gpu_s"] == 120.0 and est["usd"] == pytest.approx(30 * per_s + 120 * per_s, abs=1e-3)
    assert m.refusals() == [] and m.prices_date == MS.PRICES_DATE


def test_the_wired_modal_backend_launches_detached_fetches_and_reserves(picture, tmp_path, caps):
    calls = []

    def runner(argv):
        calls.append(argv)
        return 0, "View run at https://modal.com/apps/x/ap-AbCdEfGhIjKl12 ..."

    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=runner, fetch=lambda j, o: Fake(["good"]).generate(j, o),
                           env={"EE_MODAL_GO": "cmsg_1"})
    run = Run.open(tmp_path / "run.json", caps={"modal_usd": 2.5})
    r = WA.run_shot(_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run,
                    approval=WA.Approval("plan-1", 2.0, "creator", "2026-11-12T12:00Z", "cmsg_x"))
    assert r["route"] == "wan" and r["attempts"][0]["backend_info"]["app_id"] == "ap-AbCdEfGhIjKl12"
    assert calls[0][:4] == ["modal", "run", "--detach", f"{WA.WORKER}::main"]
    assert run.spent("modal_usd") == pytest.approx(r["estimate_usd_per_attempt"])


def test_a_failed_modal_launch_stops_its_app_by_id(picture, tmp_path, caps):
    calls = []

    def runner(argv):
        calls.append(argv)
        if argv[:2] == ["modal", "run"]:
            return 1, "ap-Zz0123456789ab started, then CUDA error"
        if argv[:3] == ["modal", "app", "list"]:
            return 0, json.dumps([{"App ID": "ap-Zz0123456789ab", "Description": "ee-wan", "State": "running"}])
        return 0, ""

    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=runner, fetch=lambda j, o: None, env={"EE_MODAL_GO": "cmsg_1"})
    with pytest.raises(RuntimeError, match="was stopped"):
        m.generate(_job(picture), tmp_path / "c.mp4")
    assert ["modal", "app", "stop", "ap-Zz0123456789ab"] in calls


def test_the_local_runner_no_longer_passes_without_a_clip():
    v = wan_runner.WanLocalRunner._default_qa_eval({"shot_id": "x"}, 1)
    assert v["passed"] is False and "wan_adapter" in v["failure_reason"]


def test_the_default_fallback_is_alive_by_bp185():
    from explainer_engine.production import layers25d as L25
    p = L25.plan({"shot_id": "S9", "target_duration_seconds": 1.0, "motion_imitation": WA.DEFAULT_FALLBACK}, FPS)
    assert len(set(p["families"]) & {"atmosphere", "light", "surface", "subject"}) >= 2
