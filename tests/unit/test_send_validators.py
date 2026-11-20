"""``qa/send_validators.living_motion`` (R-LIVING, G-LIVE-1 and G-LIVE-3): FAILS a known violation fixture ("only the fire moves": a still
photo with one small flame), PASSES a compliant one (a still camera with moving smoke), says NOT_RUN for a moving camera. Synthetic clips
encoded with ffmpeg; no network, $0."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.qa import liveliness as LV
from explainer_engine.qa import send_validators as V

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
W, H, FPS = 480, 270, 24


def clip(path, frames):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path)],
                       input=b"".join(f.astype(np.uint8).tobytes() for f in frames), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[-300:]
    return path


def background():
    rng = np.random.default_rng(1)
    return np.clip(np.kron(rng.integers(40, 200, (27, 48)), np.ones((10, 10))), 0, 255).astype(np.float32)


def seconds(n):
    return int(n * FPS)


def smoke_clip(path, n=3.0, area=(slice(40, 230), slice(60, 400))):
    """A still camera, a textured picture, a big region of turbulent change (smoke, snow, sky)."""
    rng = np.random.default_rng(2)
    bg = background()
    frames = []
    for _ in range(seconds(n)):
        f = bg.copy()
        f[area] = np.clip(f[area] + rng.normal(0, 40, f[area].shape), 0, 255)
        frames.append(f)
    return clip(path, frames)


def fire_only_clip(path, n=3.0):
    """The violation: a still photograph in which only one small flame (1 % of the frame) flickers."""
    rng = np.random.default_rng(3)
    bg = background()
    frames = []
    for _ in range(seconds(n)):
        f = bg.copy()
        f[200:220, 230:250] = rng.integers(150, 255, (20, 20))
        frames.append(f)
    return clip(path, frames)


def camera_move_clip(path, n=3.0):
    bg = np.tile(background(), (1, 2))
    return clip(path, [bg[:, 4 * i % 400:4 * i % 400 + W] for i in range(seconds(n))])


def test_a_still_camera_with_moving_smoke_passes_with_its_number(tmp_path):
    r = V.living_motion(smoke_clip(tmp_path / "ok.mp4"))
    assert r["status"] == "PASS" and r["value"] >= LV.FROZEN_CHANGE, r
    assert "zones not measured" in r["detail"] and "camera still" in r["detail"]


def test_only_the_fire_moves_fails(tmp_path):
    r = V.living_motion(fire_only_clip(tmp_path / "bad.mp4"))
    assert r["status"] == "FAIL" and r["value"] < LV.FROZEN_CHANGE, r
    assert "G-LIVE-1" in r["detail"]


def test_a_moving_camera_is_not_run_not_passed(tmp_path):
    r = V.living_motion(camera_move_clip(tmp_path / "pan.mp4"))
    assert r["status"] == "NOT_RUN" and "camera moves" in r["detail"], r


def test_a_zone_that_barely_moves_fails_and_one_that_moves_passes(tmp_path):
    p = smoke_clip(tmp_path / "z.mp4")
    for name, box, want in (("smoke", (60, 40, 400, 230), "PASS"), ("sky", (0, 0, 480, 30), "FAIL")):
        m = np.zeros((H, W), np.uint8)
        x0, y0, x1, y1 = box
        m[y0:y1, x0:x1] = 255
        Image.fromarray(m).save(tmp_path / f"{name}.png")
        (tmp_path / "z.zones.json").write_text(json.dumps({"zones": [{"name": name, "mask": f"{name}.png"}]}), encoding="utf-8")
        r = V.living_motion(p)
        assert r["status"] == want, (name, r)
        if want == "FAIL":
            assert "G-LIVE-3" in r["detail"]
        else:
            assert f"{name} " in r["detail"]


def test_a_clip_shorter_than_a_second_is_not_run(tmp_path):
    r = V.living_motion(smoke_clip(tmp_path / "s.mp4", n=0.5))
    assert r["status"] == "NOT_RUN"


def test_a_file_that_is_no_video_raises_so_the_send_gate_blocks(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(RuntimeError):
        V.living_motion(bad)


def test_the_pure_numpy_frozen_windows_agree_with_the_threshold():
    still = [np.zeros((270, 480), np.float32)] * 30
    assert LV.frozen_windows_grey(still, 8)["frozen"] > 0
    moving = [np.full((270, 480), 40.0 * ((i // 8) % 2), np.float32) for i in range(30)]
    assert LV.frozen_windows_grey(moving, 8)["frozen"] == 0


def test_the_phase_shift_sees_a_translation():
    a = background()
    assert V.phase_shift(a, a) < 0.5 and V.phase_shift(a, np.roll(a, 6, axis=1)) > 4


def test_the_validator_declares_its_kinds_for_the_send_gate():
    assert ".mp4" in V.living_motion.kinds


def test_the_command_line_prints_a_line_per_clip_and_exits_1_on_a_fail(tmp_path, capsys):
    ok, bad = smoke_clip(tmp_path / "ok.mp4"), fire_only_clip(tmp_path / "bad.mp4")
    assert V.main(["living_motion", str(ok)]) == 0
    assert "PASS" in capsys.readouterr().out
    assert V.main(["living_motion", str(ok), str(bad)]) == 1
    out = capsys.readouterr().out
    assert "PASS" in out and "FAIL" in out and "G-LIVE-1" in out
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"x")
    assert V.main(["living_motion", str(junk)]) == 2


# ---- rule 19 (OR-V35): Gemini photos only in Task mode, 6 per batch ---------------------------------------------------------------

def _batch(n, batch="3"):
    lines = [f"BATCH REPORT {batch}"] + [f"{k} | p{k:02d} | MADE | refs: 1 | prompt: AS GIVEN | note: -" for k in range(1, n + 1)]
    return "\n".join(lines + [f"MADE {n} of {n}"])


def _t0(mode, n=6, model="Gemini 3.8 Flash"):
    return f"T0 REPORT abcdef12\nMODEL: {model} | MODE: {mode}\nDRIVE READ: OK \"v1\"\nDRIVE WRITE: OK x\n{_batch(n, '0')}\nLIMIT: not reached"


def _f(tmp_path, text, name="a.txt"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_a_t0_report_in_task_mode_with_six_pictures_passes(tmp_path):
    r = V.gemini_task_report(_f(tmp_path, _t0("Task")))
    assert r["status"] == "PASS" and r["value"] == 6


def test_gemini_task_report_fails_outside_task_mode_and_over_six(tmp_path):                       # the negative test of OR-V35
    r = V.gemini_task_report(_f(tmp_path, _t0("Chat")))
    assert r["status"] == "FAIL" and "Task mode" in r["detail"]
    r = V.gemini_task_report(_f(tmp_path, _batch(7), "b.txt"))
    assert r["status"] == "FAIL" and r["value"] == 7


def test_a_batch_report_counts_but_its_mode_is_not_measured(tmp_path):
    r = V.gemini_task_report(_f(tmp_path, _batch(6)))
    assert r["status"] == "NOT_RUN" and r["value"] == 6 and "no MODE line" in r["detail"]
    assert V.gemini_task_report(_f(tmp_path, _batch(4), "c.txt"))["status"] == "NOT_RUN"           # a shorter batch is not a failure


def test_a_report_that_does_not_parse_raises_so_the_send_gate_blocks(tmp_path):
    with pytest.raises(Exception):
        V.gemini_task_report(_f(tmp_path, "hello"))
    assert V.gemini_task_report.kinds == (".txt", ".md")
