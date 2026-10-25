"""production/physics2d.py: the sled, the ragdoll and the camera operator behave like bodies, not like eased keys."""
from __future__ import annotations

import math

import numpy as np

from explainer_engine.production import physics2d as P


def test_the_terrain_descends_with_a_positive_slope_and_is_continuous():
    t = P.Terrain([(100.0, 0.0), (200.0, 45.0), (300.0, 0.0)])
    assert t.h(50.0) == 0.0
    assert abs(t.h(200.0) - (-100.0)) < 1e-6
    assert abs(t.h(150.0) - (-50.0)) < 1e-6
    assert t.h(250.0) == t.h(300.0) == t.h(1e6)
    assert t.slope(150.0) == 45.0 and t.slope(250.0) == 0.0


def _still_hand(s: float, h: float):
    return lambda t: (s, h)


def test_a_released_sled_stays_on_flat_ground_and_slides_down_a_slope():
    flat = P.Terrain([(5000.0, 0.0)])
    sim = P.SledSim(flat, 160.0, 60.0, friction=0.05, s0=1000.0)
    res = sim.run(0.0, 2.0, _still_hand(1000.0, 60.0), release=0.0)
    assert abs(res.s[-1] - 1000.0) < 5.0
    assert not any(k in ("takeoff", "bump") for _, k, _ in res.events)

    slope = P.Terrain([(500.0, 12.0), (5000.0, 12.0)])
    sim = P.SledSim(slope, 160.0, 60.0, friction=0.05, s0=1000.0)
    res = sim.run(0.0, 2.0, _still_hand(1000.0, 60.0), release=0.0)
    # a = g (sin 12 - 0.05 cos 12) over 2 s, within the simulation's tolerance
    a = P.G * (math.sin(math.radians(12)) - 0.05 * math.cos(math.radians(12)))
    expect = 0.5 * a * 2.0 ** 2 * math.cos(math.radians(12))
    assert 0.85 * expect < res.s[-1] - 1000.0 < 1.05 * expect
    assert res.v[-1] > res.v[len(res.v) // 2] > 0.0


def test_a_dragged_sled_follows_the_hand_on_a_taut_rope_and_the_arm_takes_the_bob():
    flat = P.Terrain([(5000.0, 0.0)])
    rope = 200.0
    sim = P.SledSim(flat, 160.0, 60.0, friction=0.05, rope=rope, s0=1000.0)
    sim.sled.velocity = (180.0, 0.0)

    def hand(t):   # a walking hand: 180 px/s with a 12 px bob twice a second
        return (1000.0 + 80 + rope + 180.0 * t, 90.0 + 12.0 * math.sin(2 * math.pi * 2.0 * t))

    res = sim.run(0.0, 3.0, hand, release=10.0)
    assert abs(res.s[-1] - (1000.0 + 180.0 * 3.0)) < 40.0        # it came along
    assert np.nanmin(res.rope_slack) > -15.0                      # the rope never stretched
    assert res.v.max() < 180.0 * 1.6                               # the bob did not yank it to double speed


def test_the_sled_bumps_a_foot_in_its_way_once_and_stops_there():
    slope = P.Terrain([(500.0, 8.0), (5000.0, 8.0)])
    sim = P.SledSim(slope, 160.0, 60.0, friction=0.05, s0=1000.0)
    foot_s = 1400.0
    res = sim.run(0.0, 3.0, _still_hand(1000.0, 60.0), release=0.0,
                  foot=lambda t, front: (foot_s, slope.h(foot_s) + 18.0, 18.0))
    kinds = [k for _, k, _ in res.events]
    assert "bump" in kinds
    assert res.s[-1] + 80.0 <= foot_s + 5.0        # the front rests against the heel, never through it


def _skeleton() -> dict:
    hip = (1000.0, 180.0)
    return {
        "hip": hip, "neck": (1000.0, 290.0), "head": (1000.0, 350.0), "shoulder": (1000.0, 280.0),
        "hip_L": hip, "hip_R": hip, "knee_L": (1010.0, 95.0), "knee_R": (990.0, 95.0),
        "ankle_L": (1010.0, 10.0), "ankle_R": (990.0, 10.0),
        "elbow_L": (1020.0, 220.0), "elbow_R": (980.0, 220.0), "hand_L": (1035.0, 160.0), "hand_R": (965.0, 160.0),
    }


def test_the_ragdoll_keeps_its_bone_lengths_and_comes_to_rest_on_the_ground():
    terrain = P.Terrain([(5000.0, 0.0)])
    skel = _skeleton()
    rag = P.Ragdoll(skel, +1, terrain)
    res = rag.run(0.0, 3.0, velocity=(300.0, 0.0), spin=3.0, tone=lambda dt: max(0.0, 1 - dt / 0.3))
    for name, a, b, _ in P.LIMBS:
        want = math.dist(rag.pos0[a], rag.pos0[b])
        got = np.hypot(*(res.joints[a] - res.joints[b]).T)
        assert np.all(abs(got - want) < 6.0), name     # the solver's joint error at the impact, under 2 % of a hero
    kinds = [k for _, k, _ in res.events]
    assert "impact" in kinds and "rest" in kinds
    assert res.joints["head"][-1, 1] < 120.0          # it lies down, it does not stand up
    assert res.joints["head"][-1, 1] > -5.0           # and never through the floor


def test_the_operator_never_stops_dead_and_never_lurches():
    target = np.concatenate([np.linspace(0, 600, 480), np.full(480, 600.0)])
    out = P.Operator(omega=6.0).track(target)
    v = np.diff(out) * 240
    assert abs(v[0] - 300.0) < 30.0                   # starts at the subject's speed, no lurch
    assert np.all(np.abs(np.diff(v) * 240) < 6000.0)  # bounded acceleration
    assert abs(out[-1] - 600.0) < 2.0                 # settles on the target
    settle = v[480:]
    assert np.all(np.diff(np.abs(settle)[::24]) <= 1e-6)   # the speed only decays after the subject stops: no stop-start


def test_follow_through_lags_and_overshoots_then_settles():
    step = np.concatenate([np.zeros(24), np.full(480, 10.0)])
    out = P.follow_through(step, k=800.0, c=20.0)
    assert out[30] < 10.0
    assert out.max() > 10.0
    assert abs(out[-1] - 10.0) < 0.1
