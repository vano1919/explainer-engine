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


def test_the_turn_passes_through_a_front_drawing_with_uncrossed_legs():
    sc = R.scene()
    ta, tb = sc.turn
    fronts = [R.pose_at(ta + k * (tb - ta) / 20) for k in range(21)]
    fronts = [p for p in fronts if p.front]
    assert len(fronts) >= 6
    for p in fronts:
        j = R.skeleton(p)
        left = min(R.SIDES, key=lambda s: j["hip_" + s][0])
        right = R.SIDES[1 - R.SIDES.index(left)]
        assert j["ankle_" + left][0] < j["ankle_" + right][0]
    assert R.pose_at(tb + 0.01).facing == -1 and R.pose_at(ta - 0.01).facing == 1


def test_the_walk_rolls_heel_to_toe():
    pitches = [R.gait_foot(R.WALK, 0, k / 200, 0.0, 1)[2] for k in range(200)]
    assert min(pitches) < -10 and max(pitches) > 20  # toe up at the strike, heel up at the toe-off


def _sheet(tmp_path):
    """A synthetic painted sheet: one picture with a flat colour per part, bones drawn inside each patch."""
    import json
    from PIL import Image, ImageDraw
    src = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(src)
    cols = {"torso": (200, 40, 40), "upper_arm": (40, 200, 40), "fore_arm": (40, 40, 200), "thigh": (200, 200, 40),
            "shin": (40, 200, 200)}
    parts = {}
    for k, (name, c) in enumerate(cols.items()):
        x = 20 + k * 75
        d.rectangle([x, 50, x + 60, 350], fill=c + (255,))
        parts[name] = {"p0": [x + 30, 330], "p1": [x + 30, 70], "r": [28, 26]}
    parts["torso"]["rig_r"] = [0.088, 0.080]
    src.save(tmp_path / "sheet.png")
    head = Image.new("RGBA", (80, 120), (0, 0, 0, 0))
    ImageDraw.Draw(head).ellipse([5, 5, 75, 95], fill=(238, 186, 146, 255))
    head.save(tmp_path / "head_happy.png")
    (tmp_path / "parts.json").write_text(json.dumps({"source": "sheet.png", "parts": parts, "foot_rgb": [1, 2, 3]}))
    return str(tmp_path)


def test_a_painted_part_lands_on_the_rig_bone_and_keeps_its_paint(tmp_path):
    folder = _sheet(tmp_path)
    sheet = R.load_sheet(folder)
    assert sheet.base["torso"] == (200, 40, 40) and sheet.foot == (1, 2, 3)
    # the shin's painted half-width scales with the bone; the torso's is the rig's own
    r_shin = sheet.radii("shin", (0.0, 0.0), (130.0, 0.0))
    assert abs(r_shin[0] - 28 * 130 / 260) < 1e-9
    assert sheet.radii("torso", (0.0, 0.0), (113.0, 0.0)) == (0.088 * R.B, 0.080 * R.B)
    # the picture's bone midpoint lands on the rig bone's midpoint, whichever way the hero faces
    for f in (1, -1):
        tex = sheet.warp("fore_arm", (100.0, 300.0), (220.0, 180.0), f, (400, 400))
        assert tex.getpixel((160, 240))[:3] == (40, 40, 200)
        assert tex.getpixel((20, 20))[3] == 0


def test_a_sheet_character_is_drawn_from_its_paint(tmp_path):
    folder = _sheet(tmp_path)
    p = R.pose_at(2.5)
    img, _ = R.draw_character(p, folder)
    a = np.asarray(img)
    opaque = a[a[:, :, 3] > 200][:, :3].astype(int)
    assert len(opaque) > 1000
    reds = ((opaque[:, 0] > 150) & (opaque[:, 1] < 90) & (opaque[:, 2] < 90)).sum()   # the torso's paint
    assert reds > 500
    assert not np.any(np.all(opaque == R.JACKET, axis=1))  # nothing of the code-drawn jacket
    front, _ = R.draw_character(R.pose_at(sum(R.scene().turn) / 2), folder)
    assert np.asarray(front)[:, :, 3].max() == 255


def test_three_quarter_moves_the_far_side_back_and_keeps_the_bones():
    p = R.pose_at(2.5)
    side = R.skeleton(p)
    p.view = "three_quarter"
    tq = R.skeleton(p)
    near = R.near_side(p.facing)
    far = R.SIDES[1 - R.SIDES.index(near)]
    # the near hip moves back, the far one forward, and the far side sits a little higher (further away)
    assert (tq["hip_" + near][0] - side["hip_" + near][0]) * p.facing < 0
    assert (tq["hip_" + far][0] - side["hip_" + far][0]) * p.facing > 0
    assert tq["hip_" + far][1] < tq["hip_" + near][1]
    for s in R.SIDES:
        assert abs(math.dist(tq["hip_" + s], tq["knee_" + s]) - R.THIGH) < 1e-6
        assert abs(math.dist(tq["knee_" + s], tq["ankle_" + s]) - R.SHIN) < 1e-6


def test_a_build_swaps_the_bones_only_while_it_is_used():
    short = R.Build(thigh=0.135, shin=0.135, torso=0.38)
    before = (R.THIGH, R.SHIN, R.STAND)
    with R.use_build(short):
        assert abs(R.THIGH - 0.135 * R.B) < 1e-9 and abs(R.STAND - short.stand) < 1e-9
        g = short.gait(R.WALK)
        assert abs(g.stride - R.WALK.stride * 0.27 / 0.42) < 1e-9
    assert (R.THIGH, R.SHIN, R.STAND) == before


def _cut_sheet(tmp_path):
    import json
    from PIL import Image, ImageDraw
    src = Image.new("RGBA", (200, 400), (0, 0, 0, 0))
    ImageDraw.Draw(src).rectangle([90, 100, 110, 300], fill=(10, 200, 10, 255))
    src.save(tmp_path / "turn.png")
    parts = {"thigh": {"p0": [100, 100], "p1": [100, 300], "r": [12, 12]}}
    (tmp_path / "parts_side.json").write_text(json.dumps({"mode": "cut", "source": "turn.png", "height": 400,
                                                          "parts": parts}))
    return R.Sheet(str(tmp_path), "parts_side.json")


def test_a_cut_part_follows_its_bone_and_keeps_the_figure_width(tmp_path):
    sheet = _cut_sheet(tmp_path)
    assert sheet.mode == "cut"
    for f in (1, -1):
        layer = np.asarray(sheet.place("thigh", (100.0, 50.0), (300.0, 50.0), f, (400, 120)))
        on = np.argwhere(layer[:, :, 3] > 128)
        # the painted bone lies along the rig bone (horizontal here), its length stretched to the bone's
        assert 95 <= on[:, 1].min() <= 106 and 294 <= on[:, 1].max() <= 305
        # across, the paint keeps the figure's scale: 21 source px wide -> 21 * B / height layer px
        width = on[:, 0].max() - on[:, 0].min() + 1
        assert abs(width - 21 * sheet.k * R.SS) <= 3
        assert abs(on[:, 0].mean() - 50) < 2
