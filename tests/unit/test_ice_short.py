"""The hybrid model's test cartoon (production/ice_short.py): the 2.5D camera keeps the ground where it should and a
deeper object is drawn smaller and nearer the horizon."""
from __future__ import annotations

from explainer_engine.production import ice_short as I


def test_the_camera_keeps_the_depth_one_ground_on_its_line():
    for t in (0.0, 6.0, 12.5, 20.0, 29.9):
        cam = I.camera(t)
        _, y, _ = I.to_screen(cam[0], I.STAND_WORLD, 1.0, cam)
        assert abs(y - I.GROUND_SCREEN) < 1e-6


def test_a_deeper_object_is_smaller_and_nearer_the_horizon():
    cam = I.camera(10.0)
    x1, y1, k1 = I.to_screen(cam[0] + 300, I.STAND_WORLD, 1.0, cam)
    x2, y2, k2 = I.to_screen(cam[0] + 300, I.STAND_WORLD, 2.0, cam)
    _, horizon, _ = I.to_screen(cam[0], I.HORIZON_WORLD, 1e9, cam)
    assert abs(k2 - k1 / 2) < 1e-9
    assert horizon < y2 < y1
    assert abs((x2 - I.W / 2) - (x1 - I.W / 2) / 2) < 1e-6


def test_the_captions_never_overlap():
    for (t0, _, _), (t1, _, _) in zip(I.LINES, I.LINES[1:]):
        assert t0 < t1
