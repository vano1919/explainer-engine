"""The J5 dialogue collage (``blender/j5_collage.py``, step 1 of the 2026-11-06 test): the shot list obeys the 180-degree rule and the
framing it claims, and the card grade lights the side that faces the fire. No Blender here (that runs in the cloud container)."""
import numpy as np

from explainer_engine.blender import j5_collage as J


def test_two_shot_puts_h2_left_of_h1_and_all_cameras_stay_on_one_side_of_the_axis():
    for name, shot in J.SHOTS.items():
        pos = {c["id"]: c["pos"] for c in shot["cards"]}
        assert shot["cam"][1] < min(p[1] for p in pos.values()), name      # the camera is on the -y side of the H2-H1 line (180 degree rule)
    s1 = {c["id"]: J.project(J.SHOTS["S1_two_shot"]["cam"], J.SHOTS["S1_two_shot"]["aim"], J.SHOTS["S1_two_shot"]["lens"],
                             (c["pos"][0], c["pos"][1], 1.5))[0] for c in J.SHOTS["S1_two_shot"]["cards"]}
    assert s1["H2"] < 0 < s1["H1"]                                          # screen left / right
    for name in ("S2_ots_h2_to_h1", "S3_ots_h1_to_h2"):                      # both over-the-shoulder shots keep H2 left of H1 on screen
        sh = J.SHOTS[name]
        xs = {c["id"]: J.project(sh["cam"], sh["aim"], sh["lens"], (c["pos"][0], c["pos"][1], 1.5))[0] for c in sh["cards"]}
        assert xs["H2"] < xs["H1"], name


def test_h1_bust_bottom_stays_out_of_every_frame():
    """The H1 sheets end at the belt: the bottom of his card (z = HERO z0) must be below the frame's bottom edge in each shot."""
    z0 = J.HERO["H1"]["z0"]
    for name, shot in J.SHOTS.items():
        for c in shot["cards"]:
            if c["id"] != "H1":
                continue
            _, y, dist = J.project(shot["cam"], shot["aim"], shot["lens"], (c["pos"][0], c["pos"][1], z0))
            assert y <= -0.95, (name, y)                                     # the card's bottom edge is at or below the frame's


def test_grade_lights_the_side_toward_the_fire_and_keeps_alpha():
    rgba = np.zeros((200, 100, 4), np.float32)
    rgba[20:190, 20:80, :3] = 0.5
    rgba[20:190, 20:80, 3] = 1.0
    left, right = J.grade_card(rgba, -1.0), J.grade_card(rgba, +1.0)
    assert np.allclose(left[..., 3], rgba[..., 3])
    lum = lambda a, cols: a[60:140, cols, :3].mean()                         # noqa: E731
    assert lum(left, slice(22, 38)) > lum(left, slice(62, 78))              # fire on the left: the left edge is brighter
    assert lum(right, slice(62, 78)) > lum(right, slice(22, 38))
    warm = right[60:140, 62:78, :3].mean((0, 1))
    assert warm[0] > warm[2]                                                # the lit side is warm
    assert J.grade_card(rgba, 1.0, dark=0.5)[100, 50, :3].max() < right[100, 50, :3].max()


def test_grain_layer_is_one_shared_deterministic_texture():
    a, b = J.grain_layer((64, 96), 7, scale=1.0), J.grain_layer((64, 96), 7, scale=1.0)
    assert np.array_equal(a, b) and a.std() > 0
