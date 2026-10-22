"""production/mocap.py: a BVH clip is parsed, projected onto its sagittal plane and measured into gait numbers; the rig
reads the measured gaits from gaits.json."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from explainer_engine.production import bend_rig as R
from explainer_engine.production import mocap as M

HIER = """HIERARCHY
ROOT Hips
{
\tOFFSET 0 0 0
\tCHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation
\tJOINT LeftUpLeg
\t{
\t\tOFFSET 1 -1 0
\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\tJOINT LeftLeg
\t\t{
\t\t\tOFFSET 0 -5 0
\t\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\t\tJOINT LeftFoot
\t\t\t{
\t\t\t\tOFFSET 0 -5 0
\t\t\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\t\t\tJOINT LeftToeBase
\t\t\t\t{
\t\t\t\t\tOFFSET 0 -0.5 2
\t\t\t\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\t\t\t\tEnd Site
\t\t\t\t\t{
\t\t\t\t\t\tOFFSET 0 0 1
\t\t\t\t\t}
\t\t\t\t}
\t\t\t}
\t\t}
\t}
\tJOINT Spine1
\t{
\t\tOFFSET 0 4 0
\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\tJOINT Head
\t\t{
\t\t\tOFFSET 0 3 0
\t\t\tCHANNELS 3 Zrotation Yrotation Xrotation
\t\t\tEnd Site
\t\t\t{
\t\t\t\tOFFSET 0 1 0
\t\t\t}
\t\t}
\t}
}
MOTION
Frames: 2
Frame Time: 0.1
0 11 0 0 0 0  0 0 0  0 0 0  0 0 0  0 0 0  0 0 0  0 0 0
3 11 0 0 0 0  0 0 90  0 0 0  0 0 0  0 0 0  0 0 0  0 0 0
"""


def test_bvh_parse_and_forward_kinematics(tmp_path: Path):
    p = tmp_path / "t.bvh"
    p.write_text(HIER)
    clip = M.parse_bvh(p)
    assert [j.name for j in clip.joints] == ["Hips", "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase", "Spine1", "Head"]
    assert clip.frames.shape == (2, 24) and abs(clip.frame_time - 0.1) < 1e-9
    f0 = M.fk(clip, 0)
    assert np.allclose(f0["LeftFoot"], (1.0, 0.0, 0.0))
    assert np.allclose(f0["LeftToeBase_end"], (1.0, -0.5, 3.0))
    assert np.allclose(f0["Head_end"], (0.0, 19.0, 0.0))
    f1 = M.fk(clip, 1)       # the hip joint rotated 90 deg about X: the leg swings level (-z, the BVH convention)
    assert np.allclose(f1["LeftLeg"], (4.0, 10.0, -5.0), atol=1e-6)
    assert np.allclose(f1["Hips"], (3.0, 11.0, 0.0))


def _walk_clip(tmp_path: Path, frames: int = 360, period: float = 1.0, speed: float = 12.0) -> Path:
    """A synthetic walk along -z (the BVH forward of this skeleton): straight legs of length 10 swing at the hip; a
    planted foot keeps its ground point for half the cycle (the hip angle follows the gliding hips), then swings back."""
    dt = 1 / 120
    L = 10.0
    half = period / 2
    reach = speed * half / 2          # the plant is this far ahead of the hips at the strike, as far behind at the toe-off

    def angle(t, phase):
        u = ((t / period) + phase) % 1.0
        if u < 0.5:                   # stance: the foot stays at its plant point
            d = reach - speed * u * period
            return math.degrees(math.asin(max(-1.0, min(1.0, d / L))))
        w = (u - 0.5) / 0.5           # swing: from behind to ahead, smoothly
        a = math.degrees(math.asin(reach / L))
        return -a + 2 * a * (0.5 - 0.5 * math.cos(math.pi * w))

    rows = []
    for i in range(frames):
        t = i * dt
        row = [0.0, 11.0, -speed * t, 0, 0, 0]
        row += [0, 0, angle(t, 0.0)] + [0] * 9
        row += [0, 0, angle(t, 0.5)] + [0] * 9
        row += [0] * 6
        rows.append(" ".join(f"{v:.4f}" for v in row))
    hier = HIER.split("MOTION")[0]
    right = HIER.split("\tJOINT LeftUpLeg")[1].split("\tJOINT Spine1")[0]
    right = "\tJOINT RightUpLeg" + right.replace("Left", "Right").replace("OFFSET 1 -1 0", "OFFSET -1 -1 0")
    hier = hier.replace("\tJOINT Spine1", right + "\tJOINT Spine1")
    p = tmp_path / "walk.bvh"
    p.write_text(hier + f"MOTION\nFrames: {frames}\nFrame Time: {dt:.6f}\n" + "\n".join(rows) + "\n")
    return p


def test_measure_finds_the_cycles_of_a_synthetic_walk(tmp_path: Path):
    clip = M.parse_bvh(_walk_clip(tmp_path))
    m = M.measure(clip)
    assert m["cycles"] >= 1
    assert abs(m["cycle_s"] - 1.0) < 0.1
    assert abs(m["stride"] - 12.0 / 10.0) < 0.2          # 12 units per cycle over a 10-unit leg
    assert 0.35 < m["stance"][0] < 0.65
    assert abs(m["offset"] - 0.5) < 0.1                  # the right foot strikes half a cycle after the left
    assert 0.0 < m["hip"] < 1.2 and 0 <= m["elbow"] <= 180
    kw = M.to_gait_kwargs(m, leg_px=R.THIGH + R.SHIN, body_px=R.B)
    g = R.Gait(**kw)
    assert abs(g.stride - 1.2 * (R.THIGH + R.SHIN) / R.B) < 0.05
    assert len(g.arc) == 12


def test_the_rig_reads_the_measured_gaits_and_their_feet_never_slide():
    for name in ("walk", "run"):
        g = R.measured(name)
        assert 0.2 < g.stance[0] < 0.7 and g.stride > 0.5 and g.arc
        # a planted foot stays put over the stance
        xs = {gait_foot[0] for gait_foot in (R.gait_foot(g, 0, ph, 0.0, 1) for ph in np.linspace(0.02, g.stance[0] - 0.02, 20))
              if gait_foot[3]}
        assert len(xs) == 1, name
        # the swing arc lifts the ankle above both of its ends
        swing = [R.gait_foot(g, 0, ph, 0.0, 1)[1] for ph in np.linspace(g.stance[0] + 0.05, 0.95, 20)]
        assert min(swing) < R.ANK - 0.03 * R.B
