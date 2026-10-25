"""The cut-out rig proof of concept (docs/research/ANIMATION_UNIVERSE_2026-10-22.md section 8): eased cycles, follow-through,
squash and stretch, closed-form physics, mouths from word timings, a puppet whose frame is a pure function of its number."""
import json
import math
import shutil

import numpy as np
import pytest
from PIL import Image

from explainer_engine.production import rig as R


def test_ease_is_slow_in_slow_out():
    assert R.ease(0) == 0 and R.ease(1) == 1 and R.ease(0.5) == 0.5
    assert R.ease(0.1) < 0.1 and R.ease(0.9) > 0.9 and R.ease(-1) == 0 and R.ease(2) == 1


def test_cycles_loop_or_hold_and_travel():
    for name, c in R.CYCLES.items():
        assert c["keys"][0][0] == 0.0 and c["keys"][-1][0] == 1.0, name
        assert all(t0 < t1 for (t0, _), (t1, _) in zip(c["keys"], c["keys"][1:])), name
    walk0, walk1 = R.pose_at("walk", 0.0), R.pose_at("walk", 1.0)
    assert walk0 == pytest.approx(walk1)  # a loop closes on itself
    assert R.pose_at("walk", 0.25)["leg_l"] != walk0["leg_l"]
    assert R.pose_at("point", 5.0) == pytest.approx(dict(R.CYCLES["point"]["keys"][-1][1]))  # holds the last key
    assert R.travel("walk", 2.0) == pytest.approx(2 * R.CYCLES["walk"]["dx"])
    assert R.travel("point", 9.0) == 0.0 and R.travel("fall", 9.0) == R.CYCLES["fall"]["dx"]


def test_squash_preserves_area_and_clamps():
    for vy in (-3.0, -0.5, 0.0, 0.4, 5.0):
        sx, sy = R.squash(vy)
        assert sx * sy == pytest.approx(1.0)
    assert R.squash(5.0)[1] == pytest.approx(1 - 0.22)   # landing fast: squashed, clamped
    assert R.squash(-5.0)[1] == pytest.approx(1 + 0.22)  # flying up: stretched
    assert R.squash(0.0) == (1.0, 1.0)


def test_spring_lags_then_settles_and_replays_identically():
    tg = np.array([0.0] * 10 + [30.0] * 200, dtype=np.float32)
    s = R.Spring(stiffness=60.0, damping=7.0)
    out = s.series(tg, 1 / 24)
    assert out[10] < 5.0                       # it has not caught up at the step
    assert np.max(out) > 30.0                  # overshoot = follow-through
    assert abs(out[-1] - 30.0) < 0.5           # settled
    assert np.array_equal(out, s.series(tg, 1 / 24))


def test_drop_falls_bounces_lower_each_time_and_rests():
    y0, floor = 100.0, 500.0
    assert R.drop_y(0.0, y0, floor) == y0
    t_fall = math.sqrt(2 * 400 / 2200)
    assert R.drop_y(t_fall * 0.5, y0, floor) < floor and R.drop_y(t_fall * 0.5, y0, floor) > y0
    assert R.drop_y(t_fall, y0, floor) == pytest.approx(floor, abs=1e-6)
    peaks = []
    t = t_fall
    v = math.sqrt(2 * 2200 * 400) * 0.45
    while v >= 40.0:
        peaks.append(floor - R.drop_y(t + v / 2200, y0, floor))
        t += 2 * v / 2200
        v *= 0.45
    assert len(peaks) >= 2 and all(a > b > 0 for a, b in zip(peaks, peaks[1:]))
    assert R.drop_y(60.0, y0, floor) == floor
    assert all(R.drop_y(x / 10, y0, floor) <= floor + 1e-6 for x in range(0, 300))


def test_mouth_from_word_timings():
    words = [{"text": "moon", "start": 1.0, "end": 1.4}, {"text": "bridge", "start": 2.0, "end": 2.6}]
    assert R.mouth_at(words, 0.5) == "rest" and R.mouth_at(words, 1.7) == "rest"
    shapes = {R.mouth_at(words, 1.0 + i * 0.05) for i in range(8)}
    assert "rest" in shapes and "open_o" in shapes          # m closes, oo opens round
    assert "open_e" in {R.mouth_at(words, 2.0 + i * 0.05) for i in range(12)}  # the i of bridge
    assert all(R.mouth_at(words, t) in R.MOUTHS for t in np.arange(0, 3, 0.01))


def test_world_children_follow_parent_rotation_and_flip():
    pup = R.demo_puppet()
    w0 = pup.world({}, (500.0, 400.0), (1.0, 1.0))
    assert w0["torso"] == (0.0, (500.0, 400.0))
    head0 = w0["head"][1]
    assert head0[1] < 400.0                                     # the head sits above the torso pivot (hips)
    w1 = pup.world({"torso": 90.0}, (500.0, 400.0), (1.0, 1.0))
    assert w1["head"][0] == pytest.approx(90.0)                 # angles add down the tree
    assert w1["head"][1][0] > 500.0 and abs(w1["head"][1][1] - 400.0) < 2  # turned clockwise: the head is to the right
    assert w1["hand_r"][0] == pytest.approx(90.0)                # no arm pose: the hand turns with the torso only
    w2 = pup.world({"torso": 90.0, "arm_r": -30.0}, (500.0, 400.0), (1.0, 1.0))
    assert w2["hand_r"][0] == pytest.approx(60.0)
    wf = pup.world({"arm_r": -90.0}, (500.0, 400.0), (1.0, 1.0), flip=True)
    assert wf["arm_r"][0] == pytest.approx(90.0)                # a flip mirrors every angle


def test_draw_is_deterministic_and_changes_with_pose_and_mouth():
    pup = R.demo_puppet()
    bg = Image.new("RGB", (400, 400), (10, 20, 30))
    a = pup.draw(bg, R.pose_at("idle", 0.0), (200, 330), (0.5, 0.5))
    b = pup.draw(bg, R.pose_at("idle", 0.0), (200, 330), (0.5, 0.5))
    assert a.tobytes() == b.tobytes() and a.mode == "RGB" and a.size == (400, 400)
    c = pup.draw(bg, R.pose_at("walk", 0.25), (200, 330), (0.5, 0.5))
    d = pup.draw(bg, R.pose_at("idle", 0.0), (200, 330), (0.5, 0.5), mouth="open_o")
    assert a.tobytes() != c.tobytes() and a.tobytes() != d.tobytes()
    assert a.getpixel((200, 395)) == (10, 20, 30)  # nothing drawn below the feet


def test_demo_frame_is_a_pure_function_of_the_frame_number():
    size, fps = (320, 180), 12
    pup, layers, script = R.demo_puppet(), R.demo_layers(size), R.demo_script(20)
    series = pup.pieces["scarf"].secondary.series(R.scarf_targets(fps, 20, script), 1 / fps)
    f1 = R.demo_frame(30, fps, size, pup, layers, script, series)
    f2 = R.demo_frame(30, fps, size, pup, layers, script, series)
    f3 = R.demo_frame(100, fps, size, pup, layers, script, series)
    assert f1.tobytes() == f2.tobytes() and f1.tobytes() != f3.tobytes() and f1.size == size
    assert R.demo_script(20)[-1][1] == 20 and [c for _, _, c in script] == ["walk", "idle", "point", "idle", "react", "idle"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_demo_writes_an_mp4_and_a_sheet(tmp_path):
    rep = R.demo(tmp_path, seconds=2.0, fps=6, size=(320, 180), sheet_every=1.0)
    assert rep["ffmpeg_rc"] == 0 and rep["frames"] == 12
    assert (tmp_path / "rig_poc.mp4").stat().st_size > 1000 and (tmp_path / "rig_poc_sheet.jpg").exists()
    assert json.loads((tmp_path / "rig_poc.json").read_text())["cycles"][0] == "walk"
    assert R.main(["demo", "--out", str(tmp_path / "b"), "--seconds", "1", "--fps", "4", "--size", "160x90"]) == 0
