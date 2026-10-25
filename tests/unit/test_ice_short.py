"""The hybrid model's test cartoon (production/ice_short.py): the 2.5D projection keeps the ground where the camera puts
it, a deeper object is drawn smaller and nearer the horizon, the lane bends away, and the shot list is a montage."""
from __future__ import annotations

from explainer_engine.production import ice_short as I


def test_the_projection_puts_the_depth_one_ground_where_the_camera_frames_it():
    for cam in ((0.0, I.STAND_WORLD, 1.0), (900.0, 600.0, 1.4), (-300.0, 700.0, 0.6)):
        cx, cy, z = cam
        _, y, k = I.to_screen(cx, I.STAND_WORLD, 1.0, cam)
        assert abs(y - ((I.STAND_WORLD - cy) * z + I.H / 2)) < 1e-6
        assert abs(k - z) < 1e-9


def test_a_deeper_object_is_smaller_and_nearer_the_horizon():
    cam = (500.0, 650.0, 1.0)
    x1, y1, k1 = I.to_screen(cam[0] + 300, I.STAND_WORLD, 1.0, cam)
    x2, y2, k2 = I.to_screen(cam[0] + 300, I.STAND_WORLD, 2.0, cam)
    _, horizon, _ = I.to_screen(cam[0], I.HORIZON_WORLD, 1e9, cam)
    assert abs(k2 - k1 / 2) < 1e-9
    assert horizon < y2 < y1
    assert abs((x2 - I.W / 2) - (x1 - I.W / 2) / 2) < 1e-6


def test_frame_for_inverts_the_projection():
    point = (1234.0, 800.0, 20.0)      # x, away, elevation
    for z, sx, sy in ((1.0, 960.0, 700.0), (1.6, 500.0, 420.0), (0.55, 1400.0, 900.0)):
        cam = I.frame_for((point[0], point[1], I.STAND_WORLD - point[2]), z, sx, sy)
        x, y, _ = I.world_screen(point[0], point[1], point[2], 0.0, cam)
        assert abs(x - sx) < 1e-6 and abs(y - sy) < 1e-6


def test_the_lane_bends_away_from_the_camera_after_the_turn():
    x0, a0 = I.LANE.at(0.0)
    x1, a1 = I.LANE.at(I.LANE.s_turn)
    x2, a2 = I.LANE.at(I.LANE.s_turn + 3000.0)
    assert a0 == a1 == 0.0 and x1 > x0
    assert a2 > 500.0 and x2 > x1
    assert abs(I.LANE.s_of_x(x1) - I.LANE.s_turn) < 1e-6


def test_the_terrain_has_a_lip_then_a_slope_and_the_sled_lane_descends():
    s_lip = I.TERRAIN.sections[0][0]
    assert I.TERRAIN.h(s_lip - 1) == 0.0
    assert I.TERRAIN.h(s_lip + 500) < I.TERRAIN.h(s_lip) and I.TERRAIN.h(8000.0) < I.TERRAIN.h(3000.0)


def test_the_captions_never_overlap():
    for (t0, _, _), (t1, _, _) in zip(I.LINES, I.LINES[1:]):
        assert t0 < t1
