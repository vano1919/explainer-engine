"""The bending rig of the hybrid model's proof of concept (production/bend_rig.py): joints bend without changing length,
planted feet never slide, sound comes from the poses, frames are pure functions of time."""
from __future__ import annotations

import math

import numpy as np

from explainer_engine.production import bend_rig as R


def test_ik_keeps_both_bones_and_reaches_a_reachable_target():
    root = (100.0, 100.0)
    for target in ((130.0, 230.0), (60.0, 210.0), (100.0, 160.0)):
        joint, end = R.ik2(root, target, 80.0, 70.0, 1)
        assert abs(math.dist(root, joint) - 80.0) < 1e-6
        assert abs(math.dist(joint, end) - 70.0) < 1e-6
        assert math.dist(end, target) < 1e-6


def test_ik_on_an_unreachable_target_straightens_without_stretching():
    joint, end = R.ik2((0.0, 0.0), (0.0, 500.0), 80.0, 70.0, 1)
    assert abs(math.dist((0.0, 0.0), joint) - 80.0) < 1e-6 and abs(math.dist(joint, end) - 70.0) < 1e-6
    assert end[1] > 149.0


def test_the_knee_bends_toward_the_facing_and_the_elbow_away():
    knee, _ = R.ik2((0.0, 0.0), (0.0, 120.0), 80.0, 70.0, 1)
    assert knee[0] > 0
    knee_l, _ = R.ik2((0.0, 0.0), (0.0, 120.0), 80.0, 70.0, -1)
    assert knee_l[0] < 0


def test_a_planted_foot_holds_one_world_position_in_every_gait():
    for g in (R.WALK, R.RUN, R.LIMP):
        prev = None
        for k in range(600):
            ph = k * 0.004
            feet = {s: R.gait_foot(g, i, ph, 0.0, 1) for i, s in enumerate(R.SIDES)}
            if prev:
                for s in R.SIDES:
                    if feet[s][3] and prev[s][3]:
                        assert abs(feet[s][0] - prev[s][0]) < 1e-9 and feet[s][1] == R.ANK
            prev = feet


def test_hips_never_pull_a_planted_leg_past_its_reach():
    feet = {"L": (0.0, R.ANK, 0.0, True), "R": (0.3 * R.B, R.ANK, 0.0, True)}
    hip = R.reach_clamp((0.15 * R.B, 0.0), feet)
    for s in R.SIDES:
        assert math.dist(hip, feet[s][:2]) <= R.REACH + 1e-6


def test_the_demo_shot_passes_its_motion_checks():
    report = R.check(24)
    assert report["verdict"] == "PASS", report["findings"][:5]


def test_every_footfall_is_an_event_and_nothing_sounds_after_the_end():
    sc = R.scene()
    ev = R.events(24)
    steps = [e for e in ev if e["kind"] == "step"]
    assert len(steps) > 12
    assert {e["kind"] for e in ev} >= {"takeoff", "land", "impact"}
    assert all(0 < e["t"] < sc.duration for e in ev)
    # no step while the hero lies in the snow
    lie0, lie1 = sc.wound_at, sc.wound_at + 1.4
    assert not [e for e in steps if lie0 < e["t"] < lie1]


def test_the_wound_appears_at_the_impact_and_stays():
    sc = R.scene()
    assert not R.pose_at(sc.wound_at - 0.05).wound
    assert R.pose_at(sc.wound_at + 0.01).wound and R.pose_at(sc.duration - 0.1).wound


def test_the_limp_is_slower_on_the_injured_foot():
    sc = R.scene()
    limp = sc.segments[-1][3]
    t0 = sc.segments[-1][0] + 1.0
    on, off = [], []
    for k in range(240):
        t = t0 + k / 120.0
        v = (limp.x(t + 1 / 240.0) - limp.x(t)) * 240.0
        (on if limp.raw_feet(t)[R.INJURED][3] else off).append(abs(v))
    assert np.mean(on) < 0.75 * np.mean(off)


def test_a_frame_is_a_pure_function_of_its_time():
    a = np.asarray(R.render_frame(6.1))
    b = np.asarray(R.render_frame(6.1))
    assert a.shape == (R.FRAME_H, R.FRAME_W, 3) and np.array_equal(a, b)
    assert not np.array_equal(a, np.asarray(R.render_frame(6.2)))
