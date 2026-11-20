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


def test_an_operator_task_line_with_six_pictures_passes_in_both_forms(tmp_path):
    for k, line in enumerate(("MODE: task", "chat mode **Task** (input box read 'Describe a task')", "> **MODE: Task**")):
        r = V.gemini_task_report(_f(tmp_path, line + "\n" + _batch(6), f"p{k}.txt"))
        assert r["status"] == "PASS" and r["value"] == 6, line
    assert V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _t0("Task"), "t.txt"))["status"] == "PASS"
    assert V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _batch(4), "s.txt"))["status"] == "PASS"   # a shorter batch is fine


def test_gemini_task_report_fails_outside_task_mode_and_over_six(tmp_path):                       # the negative test of OR-V35
    r = V.gemini_task_report(_f(tmp_path, "MODE: chat\n" + _batch(6)))
    assert r["status"] == "FAIL" and "Task mode" in r["detail"]
    r = V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _batch(7), "b.txt"))
    assert r["status"] == "FAIL" and r["value"] == 7
    assert V.gemini_task_report(_f(tmp_path, _t0("Chat"), "c.txt"))["status"] == "FAIL"             # the chat's own words can fail, never pass


def test_without_an_operator_mode_line_the_mode_is_not_measured(tmp_path):
    r = V.gemini_task_report(_f(tmp_path, _batch(6)))
    assert r["status"] == "NOT_RUN" and r["value"] == 6 and "mode is not measured" in r["detail"]
    assert V.gemini_task_report(_f(tmp_path, _t0("Task"), "t.txt"))["status"] == "NOT_RUN"           # the chat cannot vouch for its own mode


def test_a_report_that_does_not_parse_raises_so_the_send_gate_blocks(tmp_path):
    with pytest.raises(Exception):
        V.gemini_task_report(_f(tmp_path, "hello"))
    assert V.gemini_task_report.kinds == (".txt", ".md")


# ---- BP-214 / OR-V36: faces intact (IoU floor from sourced_rules) --------------------------------------------------------------------

def _boxes(*bs):
    return lambda path: list(bs[0 if str(path).startswith("b") else 1])


def _shift(box, dx=0.0, dy=0.0, k=1.0):
    cx, cy = (box[0] + box[2]) / 2 + dx, (box[1] + box[3]) / 2 + dy
    w, h = (box[2] - box[0]) * k, (box[3] - box[1]) * k
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


FACE = (0.40, 0.20, 0.50, 0.38)


def test_the_same_face_after_an_upscale_passes_with_its_lowest_iou():
    r = V.faces_intact_pair("b", "a", detect=_boxes([FACE], [_shift(FACE, 0.002)]))
    assert r["status"] == "PASS" and r["value"] >= V.FACE_IOU_MIN and "not binding" in r["detail"]


def test_a_moved_a_warped_and_a_missing_or_extra_face_fail(tmp_path):                                # the calibration set of bad fixtures
    for label, after in (("moved", [_shift(FACE, 0.03)]), ("warped", [_shift(FACE, k=1.3)]), ("lost", []),
                         ("extra", [FACE, (0.1, 0.1, 0.2, 0.3)])):
        r = V.faces_intact_pair("b", "a", detect=_boxes([FACE], after))
        assert r["status"] == "FAIL", label


def test_two_faces_are_matched_one_to_one():
    f2 = (0.70, 0.25, 0.80, 0.43)
    assert V.faces_intact_pair("b", "a", detect=_boxes([FACE, f2], [f2, FACE]))["status"] == "PASS"
    assert V.faces_intact_pair("b", "a", detect=_boxes([FACE, f2], [FACE, _shift(f2, 0.05)]))["status"] == "FAIL"


def test_no_face_and_no_opencv_are_not_run_never_a_pass():
    assert V.faces_intact_pair("b", "a", detect=_boxes([], []))["status"] == "NOT_RUN"
    def boom(path):
        raise RuntimeError("OpenCV or the YuNet model is missing")
    r = V.faces_intact_pair("b", "a", detect=boom)
    assert r["status"] == "NOT_RUN" and "not measured" in r["detail"]


def test_the_default_detector_says_not_run_when_opencv_or_the_model_is_missing(tmp_path, monkeypatch):
    from explainer_engine.qa import pixels as PX
    monkeypatch.setattr(PX, "yunet_path", lambda: None)
    img = tmp_path / "x.png"
    Image.new("RGB", (64, 64), (9, 9, 9)).save(img)
    assert V.faces_intact_pair(img, img)["status"] == "NOT_RUN"


def test_the_pair_file_adapter(tmp_path, monkeypatch):
    for n in ("a.png", "b.png"):
        Image.new("RGB", (64, 64), (9, 9, 9)).save(tmp_path / n)
    monkeypatch.setattr(V, "yunet_boxes", lambda p: [FACE] if p.name == "a.png" else [_shift(FACE, 0.05)])
    pair = tmp_path / "s.faces.json"
    pair.write_text(json.dumps({"before": "a.png", "after": "b.png"}), encoding="utf-8")
    assert V.faces_intact(pair)["status"] == "FAIL" and V.faces_intact.kinds == (".json",)
    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    assert V.faces_intact(other)["status"] == "NOT_RUN"
    pair.write_text(json.dumps({"before": "a.png", "after": "gone.png"}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        V.faces_intact(pair)


def test_the_floor_is_read_from_sourced_rules():
    from explainer_engine.standards import sourced_rules as SR
    assert V.FACE_IOU_MIN == SR.T("BP-214", "face_iou_min") == 0.85 and SR.rule("BP-214")["status"] == "hypothesis"
