"""v4.3 plan P6: one Wan adapter, real clip QA instead of ``passed: True``, one retry then the 2.5D fallback, money checked
before every paid attempt, a ledger line per attempt. A fake backend makes the clips (good, frozen, short, wrong start,
crashing), so nothing paid or remote runs."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.aivideo import wan_adapter as WA
from explainer_engine.aivideo import wan_runner
from explainer_engine.core.errors import ConfigError
from explainer_engine.core.ledger import EpisodeTotal, Run
from explainer_engine.training.pods.wan import modal_wan_jobs as WJ

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
        monkeypatch.setenv("EXPLAINER_LEDGER_MIRROR", str(tmp_path / "mirror"))   # the episode total's durable folder (B5)
    write()
    return write


def _job(picture, **kw):
    return WA.WanJob(**dict(dict(shot_id="S9", start_picture=str(picture), motion_prompt="she runs", seconds=1.0, seed=7,
                                 width=W, height=H), **kw))


def _appr(tmp_path, plan_id="plan-1", cap=2.0, msg="cmsg_x"):
    """An approval bound to a plan file's sha256 (final audit B10)."""
    f = tmp_path / f"{plan_id}.json"
    if not f.exists():
        f.write_text(json.dumps({"plan": plan_id, "cap_usd": cap}))
    return WA.Approval(plan_id, cap, "creator", "2026-11-12T12:00Z", msg, str(f), WA._sha_file(f))


def _run(path, cap, episode="ep_t"):
    return Run.open(path, caps={"modal_usd": cap}, episode=episode)


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
    assert r["route"] == "video" and r["status"] != "FAIL" and r["fallback"] is None
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
    run = _run(tmp_path / "run.json", 2.5)
    ok = _appr(tmp_path, "plan-1", 2.0)
    with pytest.raises(ConfigError, match="OR-23"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", run=run)
    with pytest.raises(ConfigError, match="no run ledger"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok)
    tight = _appr(tmp_path, "plan-1", 1.5)
    with pytest.raises(ConfigError, match="nothing was sent"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=tight, run=run)
    assert be.calls == [] and run.spent("modal_usd") == 0.0
    WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok, run=run)
    assert WA.spent(tmp_path / "l.jsonl") == pytest.approx(1.0) and run.spent("modal_usd") == pytest.approx(1.0)
    assert "wan/plan-1/S9/try1" in Run.open(tmp_path / "run.json").data["reserved"]


def test_the_runs_80_percent_stop_and_the_creators_line_bind_the_plan(picture, tmp_path, caps):
    be = Fake(["good"], paid=True, speed=3600.0, rate=1.0)
    ok = _appr(tmp_path, "plan-1", 2.0)
    with pytest.raises(ConfigError, match="80 % stop"):    # 2 attempts x $1 > 80 % of a $2 run cap
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok,
                    run=_run(tmp_path / "a.json", 2.0))
    big = _appr(tmp_path, "plan-2", 5.0)
    with pytest.raises(ConfigError, match="above the creator's"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=big,
                    run=_run(tmp_path / "b.json", 2.5))
    assert be.calls == []


def test_no_modal_line_is_a_zero_budget_whatever_the_card_says(picture, tmp_path, caps):
    caps(modal=None)
    be = Fake(["good"], paid=True, speed=3600.0, rate=0.01)
    ok = _appr(tmp_path, "plan-1", 2.0)
    with pytest.raises(ConfigError, match="zero approved budget"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok,
                    run=_run(tmp_path / "run.json", 2.5))
    assert be.calls == []


def test_a_test_only_line_lets_no_episode_run_spend(picture, tmp_path, monkeypatch):
    """The creator's answer (final audit section 7.3): $1 a run for the ladder's tests; the episode line comes after L3."""
    f = tmp_path / "caps.json"
    f.write_text(json.dumps({"per_episode": {}, "modal": {"per_run_usd": 1.0}}))
    monkeypatch.setenv("EXPLAINER_SPEND_CAPS", str(f))
    monkeypatch.setenv("EXPLAINER_LEDGER_MIRROR", str(tmp_path / "mirror"))
    assert WA.service_ceiling("modal_usd") == 1.0
    be = Fake(["good"], paid=True, speed=36.0, rate=1.0)
    with pytest.raises(ConfigError, match="after rung L3"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=_appr(tmp_path, "plan-1", 1.0),
                    run=_run(tmp_path / "run.json", 1.0))
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
          "memory_gib": 64, "usd_per_h": 3.3872, "prices_date": "2026-11-07", "scaledown_window_s": 2,
          "pip_pins": {"transformers": "4.0.0", "accelerate": "1.0.0"},
          "caps": {"smoke_usd": 0.25, "run_usd": 1.0, "cold_start_s": 120},
          "native": {"fps": 24, "max_frames": 49, "sizes": [[320, 176]], "use": [320, 176]}, "offload": "none"}
PROOF = WJ.proof(LAUNCH)
LADDER = {"done": ["L0", "L1", "L2", "L3"], "red": None, "rungs": {r: dict(PROOF, ok=True) for r in ("L1", "L2", "L3")},
          "measured": {"gpu": "A100-80GB", "s_per_clip_s": 60.0, "setup_s": 30.0}}
GO_ANY = "cmsg_1:" + "0" * 12


def test_the_modal_backend_refuses_until_every_gate_holds(caps):
    m = WA.ModalWanBackend()
    bad = " ".join(m.refusals())
    for want in ("no launch file", "ladder is at L0", "no speed measured", "EE_MODAL_GO", "no Modal runner"):
        assert want in bad
    with pytest.raises(ConfigError, match="nothing was sent"):
        m.generate(WA.WanJob("S9", "x.png", "p", 1.0, 7), None)
    half = WA.ModalWanBackend(dict(LAUNCH, model_revision=None), dict(LADDER, done=["L0", "L1", "L2"]),
                              runner=lambda a: (0, ""), fetch=lambda j, o: None, env={"EE_MODAL_GO": GO_ANY})
    assert {r.split(":")[0] for r in half.refusals()} >= {"launch model_revision is not pinned",
                                                           "the OR-37 ladder is at L3, not L4"}
    with pytest.raises(ConfigError, match="measured on L4"):
        WA.ModalWanBackend(LAUNCH, dict(LADDER, measured=dict(LADDER["measured"], gpu="L4")))


def test_the_modal_backend_is_priced_from_modal_schedule_and_the_l3_speed(caps):
    from explainer_engine.cloud import modal_schedule as MS
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=lambda a: (0, ""), fetch=lambda j, o: None, env={"EE_MODAL_GO": GO_ANY})
    per_s = MS.GPUS["A100-80GB"]["usd_s"] + 8 * MS.CPU_CORE_S + 64 * MS.MEM_GIB_S
    est = m.estimate(WA.WanJob("S9", "x.png", "p", 2.0, 7))
    assert est["gpu_s"] == 120.0 and est["usd"] == pytest.approx(30 * per_s + 120 * per_s, abs=1e-3)
    assert m.refusals() == [] and m.prices_date == MS.PRICES_DATE


class FakeModal:
    """A fake Modal + HF: ``modal run`` reads the job spec and 'makes' the clip in the run's HF folder unless the step says
    otherwise; ``fetch`` writes the clip (and the worker's measured.json) only when that folder holds it."""

    def __init__(self, steps=("ok",), body_s=100.0):
        self.steps, self.calls, self.hf, self.specs, self.body_s = list(steps), [], set(), [], body_s

    def runner(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["modal", "run"]:
            spec = json.loads(Path(argv[argv.index("--job") + 1]).read_text())
            self.specs.append(spec)
            step = self.steps.pop(0) if self.steps else "ok"
            key = (spec["run_id"], spec["shot_id"], spec["seed"])
            if step == "lost":            # the launcher dies, the detached app goes on and finishes the clip
                self.hf.add(key)
                raise TimeoutError("the connection dropped")
            if step == "lost_nothing":
                raise TimeoutError("the connection dropped")
            if step == "wan_failed":
                return 4, f"ap-Zz0123456789ab ... result {{\"state\": \"FAILED\"}}\n{WJ.WAN_FAILED}"
            if step == "infra":
                return 1, "ap-Zz0123456789ab ... grpc error"
            self.hf.add(key)
            return 0, "View run at https://modal.com/apps/x/ap-AbCdEfGhIjKl12 ..."
        if argv[:3] == ["modal", "app", "list"]:
            return 0, json.dumps([{"App ID": "ap-Zz0123456789ab", "Description": "ee-wan", "State": "running"}])
        return 0, ""

    def fetch(self, job, out):
        if (job.extra["run_id"], job.shot_id, job.seed) not in self.hf:
            raise FileNotFoundError("404")
        Fake(["good"]).generate(job, out)
        Path(out).with_suffix(".measured.json").write_text(json.dumps({"state": "DONE", "body_s": self.body_s}))


def _modal_job(picture, **kw):
    return _job(picture, extra={"start_sha256": WA._sha_file(picture)}, **kw)


def _go(appr):
    return {"EE_MODAL_GO": f"{appr.message_id}:{appr.plan_sha256[:12]}"}


def test_the_wired_modal_backend_launches_detached_fetches_reserves_and_settles(picture, tmp_path, caps):
    fm, appr = FakeModal(body_s=100.0), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    run = _run(tmp_path / "run.json", 2.5)
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    assert r["route"] == "video" and r["attempts"][0]["backend_info"]["app_id"] == "ap-AbCdEfGhIjKl12"
    assert fm.calls[0][:4] == ["modal", "run", "--detach", f"{WA.WORKER}::main"]
    spec = fm.specs[0]   # the run id, the plan and the launch travel with the job (A4, B9, B10)
    assert spec["run_id"] == WJ.run_id(appr.plan_sha256, LAUNCH) and spec["plan_sha256"] == appr.plan_sha256
    assert spec["launch_sha"] == WJ.launch_sha(LAUNCH) and spec["extra"]["start_sha256"] == WA._sha_file(picture)
    billed = (100.0 + 120) * m.usd_per_hour / 3600   # B6: the container's seconds + the launch's cold start
    money = r["attempts"][0]["money"]
    assert money["billed_usd"] == pytest.approx(billed, abs=1e-4) and money["estimate_usd"] == r["estimate_usd_per_attempt"]
    assert run.spent("modal_usd") == pytest.approx(billed, abs=1e-4) and run.settled_total("modal_usd") == pytest.approx(billed, abs=1e-4)
    assert EpisodeTotal("ep_t", "modal_usd", 6.0).total() == pytest.approx(billed, abs=1e-4)   # B5


def test_a_clip_already_in_the_runs_folder_is_not_launched_again(picture, tmp_path, caps):
    fm, appr = FakeModal(), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    fm.hf.add((WJ.run_id(appr.plan_sha256, LAUNCH), "S9", 7))
    run = _run(tmp_path / "run.json", 2.5)
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    assert r["route"] == "video" and r["attempts"][0]["backend_info"]["reused"] is True
    assert not any(c[:2] == ["modal", "run"] for c in fm.calls) and run.spent("modal_usd") == 0.0


def test_a_lost_answer_is_reconciled_never_launched_twice(picture, tmp_path, caps):
    fm, appr = FakeModal(["lost"]), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=_run(tmp_path / "run.json", 2.5),
                    approval=appr)
    assert sum(c[:2] == ["modal", "run"] for c in fm.calls) == 1 and ["modal", "app", "stop", "ap-Zz0123456789ab"] in fm.calls
    assert r["route"] == "video" and r["attempts"][0]["backend_info"]["reconciled"] is True


def test_a_lost_answer_without_a_clip_stops_there_and_keeps_the_money_reserved(picture, tmp_path, caps):
    fm, appr = FakeModal(["lost_nothing"]), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    run = _run(tmp_path / "run.json", 2.5)
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    assert r["status"] == "FAIL" and r["stopped"] == "infrastructure" and r["fallback"] is None and len(r["attempts"]) == 1
    assert sum(c[:2] == ["modal", "run"] for c in fm.calls) == 1        # no new seed after an uncertain launch (A4)
    assert run.spent("modal_usd") == pytest.approx(r["estimate_usd_per_attempt"])   # the reservation stays open
    assert ["modal", "app", "stop", "ap-Zz0123456789ab"] in fm.calls


def test_a_failed_modal_launch_stops_its_app_and_is_not_retried(picture, tmp_path, caps):
    fm, appr = FakeModal(["infra"]), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=_run(tmp_path / "run.json", 2.5),
                    approval=appr)
    assert r["stopped"] == "infrastructure" and "was stopped" in r["attempts"][0]["gates"]["gates"][0]["detail"]
    assert ["modal", "app", "stop", "ap-Zz0123456789ab"] in fm.calls and sum(c[:2] == ["modal", "run"] for c in fm.calls) == 1


def test_a_clip_the_model_failed_gets_the_one_retry_with_a_new_seed(picture, tmp_path, caps):
    fm, appr = FakeModal(["wan_failed", "ok"]), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    r = WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=_run(tmp_path / "run.json", 2.5),
                    approval=appr)
    assert [s["seed"] for s in fm.specs] == [7, 7 + WA.SEED_STEP] and r["route"] == "video" and r["status"] != "FAIL"


def test_the_yes_binds_the_plan_and_the_picture_binds_its_pin(picture, tmp_path, caps):
    fm, appr = FakeModal(), _appr(tmp_path)
    run = _run(tmp_path / "run.json", 2.5)
    other = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env={"EE_MODAL_GO": "cmsg_x:" + "f" * 12})
    with pytest.raises(ConfigError, match="not this plan's yes"):
        WA.run_shot(_modal_job(picture), other, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    with pytest.raises(ConfigError, match="no start_sha256"):
        WA.run_shot(_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    with pytest.raises(ConfigError, match="not the one production/pictures.json pinned"):
        WA.run_shot(_job(picture, extra={"start_sha256": "0" * 64}), m, tmp_path / "o", tmp_path / "l.jsonl", run=run,
                    approval=appr)
    Path(appr.plan_path).write_text("{}")        # the plan changed after the yes
    with pytest.raises(ConfigError, match="not the file the creator said yes to"):
        WA.run_shot(_modal_job(picture), m, tmp_path / "o", tmp_path / "l.jsonl", run=run, approval=appr)
    assert not any(c[:2] == ["modal", "run"] for c in fm.calls) and run.spent("modal_usd") == 0.0


def test_the_episode_line_holds_across_separate_runs(picture, tmp_path, caps):
    caps(modal=(3.0, 2.0))     # $3 a run, $2 an episode: 80 % = $1.60 for all the episode's runs together
    be = Fake(["good"], paid=True, speed=1800.0, rate=1.0)    # $0.50 an attempt, two attempts reserved per shot
    WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=_appr(tmp_path, "plan-1", 2.0),
                run=_run(tmp_path / "a.json", 2.5))
    WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=_appr(tmp_path, "plan-2", 2.0),
                run=_run(tmp_path / "b.json", 2.5))
    with pytest.raises(ConfigError, match="episode"):    # $1.00 of $1.60 used: two more attempts at $0.50 do not fit
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=_appr(tmp_path, "plan-3", 2.0),
                    run=_run(tmp_path / "c.json", 2.5))
    assert len(be.calls) == 2
    with pytest.raises(ConfigError, match="names no episode"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=_appr(tmp_path, "plan-4", 2.0),
                    run=Run.open(tmp_path / "d.json", caps={"modal_usd": 2.5}))


def test_a_ladder_proved_on_another_launch_file_is_refused(caps):
    changed = dict(LAUNCH, settings={"steps": 40})
    m = WA.ModalWanBackend(changed, LADDER, runner=lambda a: (0, ""), fetch=lambda j, o: None, env={"EE_MODAL_GO": GO_ANY})
    assert any("proved on another launch file" in r for r in m.refusals())


def test_the_pictures_stage_pin_is_read_from_pictures_json(tmp_path):
    (tmp_path / "production").mkdir()
    (tmp_path / "production" / "pictures.json").write_text(json.dumps({"pictures": {"S9_start": {"sha256": "a" * 64}}}))
    assert WA.start_sha_from_pictures(tmp_path, "S9") == "a" * 64
    with pytest.raises(Exception, match="no start picture pinned"):
        WA.start_sha_from_pictures(tmp_path, "S8")


def test_the_local_runner_no_longer_passes_without_a_clip():
    v = wan_runner.WanLocalRunner._default_qa_eval({"shot_id": "x"}, 1)
    assert v["passed"] is False and "wan_adapter" in v["failure_reason"]


def test_the_default_fallback_is_alive_by_bp185():
    from explainer_engine.production import layers25d as L25
    p = L25.plan({"shot_id": "S9", "target_duration_seconds": 1.0, "motion_imitation": WA.DEFAULT_FALLBACK}, FPS)
    assert len(set(p["families"]) & {"atmosphere", "light", "surface", "subject"}) >= 2


def test_a_native_clip_is_conformed_to_the_timelines_rate_and_size(tmp_path):
    """Final audit A2: the model's 16 fps clip becomes the timeline's 24 fps at its size, the same length, no new pixels."""
    import cv2
    src, dst = tmp_path / "S1.native.mp4", tmp_path / "S1.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "160x96", "-r", "16",
                             "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(src)], stdin=subprocess.PIPE)
    for f in range(17):
        fr = np.zeros((96, 160, 3), np.uint8)
        fr[:, f * 8:f * 8 + 20] = 200
        proc.stdin.write(fr.tobytes())
    proc.stdin.close()
    proc.wait()
    info = WA.conform(src, dst, fps=24, width=W, height=H)
    cap = cv2.VideoCapture(str(dst))
    fps, w, h, n = (cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                    int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    cap.release()
    assert info["conformed"] is True and info["native"] == [16, 160, 96]
    assert round(fps) == 24 and (w, h) == (W, H) and abs(n - round(17 / 16 * 24)) <= 1
    again = WA.conform(dst, tmp_path / "copy.mp4", fps=24, width=W, height=H)   # already the timeline's: copied
    assert again["conformed"] is False and (tmp_path / "copy.mp4").read_bytes() == dst.read_bytes()


def test_g1_names_every_wan_shot_longer_than_one_clip_of_the_model():
    launch = dict(LAUNCH, native={"fps": 16, "max_frames": 81, "sizes": [[1280, 720]], "use": [1280, 720]})
    shots = [{"shot_id": "A", "route": "video", "target_duration_seconds": 4.0},
             {"shot_id": "B", "route": "video", "target_duration_seconds": 7.8},
             {"shot_id": "C", "route": "still_25d", "target_duration_seconds": 9.0}]
    row, = WA.fit_rows(shots, launch)
    assert row["status"] == "FAIL" and row["measured"] == ["B: 7.8 s"] and "split the shot" in row["detail"]
    assert WA.fit_rows(shots[:1], launch)[0]["status"] == "PASS"
    assert WA.fit_rows(shots, dict(LAUNCH, native=None))[0]["status"] == "NOT_RUN"


def test_a_shot_longer_than_the_models_clip_is_never_sent(picture, tmp_path, caps):
    fm, appr = FakeModal(), _appr(tmp_path)
    m = WA.ModalWanBackend(LAUNCH, LADDER, runner=fm.runner, fetch=fm.fetch, env=_go(appr))
    job = _modal_job(picture, seconds=3.0)   # the test launch holds 49 frames at 24 fps
    job.extra.update(plan_sha256=appr.plan_sha256, message_id=appr.message_id)
    with pytest.raises(ConfigError, match="split the shot"):
        m.generate(job, tmp_path / "S9.mp4")
    assert fm.calls == []
