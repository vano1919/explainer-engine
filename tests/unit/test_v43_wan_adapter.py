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


def test_a_paid_backend_needs_the_plan_and_fits_under_its_cap(picture, tmp_path):
    be = Fake(["good"], paid=True, speed=3600.0, rate=1.0)    # one clip second = one GPU hour = $1
    with pytest.raises(ConfigError, match="OR-23"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl")
    tight = WA.Approval("plan-1", 1.5, "creator", "2026-11-12T12:00Z", "cmsg_x")
    with pytest.raises(ConfigError, match="nothing was sent"):
        WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=tight)
    assert be.calls == []
    ok = WA.Approval("plan-1", 2.0, "creator", "2026-11-12T12:00Z", "cmsg_x")
    WA.run_shot(_job(picture), be, tmp_path / "o", tmp_path / "l.jsonl", approval=ok)
    assert WA.spent(tmp_path / "l.jsonl") == pytest.approx(1.0)


def test_no_measured_speed_no_price_and_modal_refuses(picture):
    be = Fake(["good"], speed=None)
    with pytest.raises(ConfigError, match="no measured speed"):
        be.estimate(_job(picture))
    modal = WA.ModalWanBackend()
    modal.measured_s_per_clip_s = 10.0
    with pytest.raises(ConfigError, match="not wired"):
        modal.generate(_job(picture), None)


def test_the_local_runner_no_longer_passes_without_a_clip():
    v = wan_runner.WanLocalRunner._default_qa_eval({"shot_id": "x"}, 1)
    assert v["passed"] is False and "wan_adapter" in v["failure_reason"]


def test_the_default_fallback_is_alive_by_bp185():
    from explainer_engine.production import layers25d as L25
    p = L25.plan({"shot_id": "S9", "target_duration_seconds": 1.0, "motion_imitation": WA.DEFAULT_FALLBACK}, FPS)
    assert len(set(p["families"]) & {"atmosphere", "light", "surface", "subject"}) >= 2
