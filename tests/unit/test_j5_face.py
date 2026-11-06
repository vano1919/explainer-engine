"""Faces of the J5 dialogue test (``blender/j5_face.py``): blinks, brows, the mouth that follows Rhubarb's cues. No Blender, no ffmpeg."""
import numpy as np
from PIL import Image

from explainer_engine.blender import j5_background as B
from explainer_engine.blender import j5_collage as J
from explainer_engine.blender import j5_face as F


def _face():
    skin = np.array([0.8, 0.55, 0.4], np.float32)
    return {"k": 2.0, "eyes": [{"x": 60.0, "y": 50.0, "w": 24.0, "h": 16.0, "skin": skin, "lash": F.LASH}],
            "brows": [(60.0, 30.0, 20.0, 10.0)],
            "mouth": {"x": 60.0, "y": 110.0, "w": 50.0, "line": 6.0, "jaw": 12.0, "interior": F.INTERIOR, "tongue": F.TONGUE,
                      "teeth_c": F.TEETH, "teeth": True, "chin": 130.0, "lash": F.LASH}}


def _layer():
    pm = np.zeros((160, 120, 4), np.float32)
    pm[..., 3] = 1.0
    pm[..., :3] = np.array([0.8, 0.55, 0.4], np.float32)
    pm[45:55, 50:70, :3] = (0.95, 0.95, 0.95)               # the eye's white
    return pm


def test_blink_is_a_short_down_up_curve_and_deterministic():
    b = F.blink_times("S1:H2", 0.0, 3.0)
    assert b == F.blink_times("S1:H2", 0.0, 3.0) and b and 0.8 <= b[0] <= 1.6
    assert F.closure(b[0] - 0.01, b) == 0.0 and F.closure(b[0] + F.BLINK_S + 0.01, b) == 0.0
    peak = max(F.closure(b[0] + u * F.BLINK_S, b) for u in np.linspace(0, 1, 40))
    assert peak > 0.97                                       # it really shuts
    assert F.closure(b[0] + 0.35 * F.BLINK_S, b) > F.closure(b[0] + 0.9 * F.BLINK_S, b)   # down faster than up


def test_mouth_state_follows_the_cues_eases_and_is_shut_outside_the_line():
    line = {"start": 2.0, "cues": [{"start": 0.0, "end": 0.2, "value": "X"}, {"start": 0.2, "end": 0.5, "value": "D"},
                                   {"start": 0.5, "end": 0.8, "value": "A"}]}
    assert F.mouth_state(1.0, line) == (0.0, 1.0) and F.mouth_state(5.0, line) == (0.0, 1.0)
    assert F.mouth_state(2.45, line)[0] == F.SHAPES["D"][0]      # open on D
    assert 0.0 < F.mouth_state(2.21, line)[0] < F.SHAPES["D"][0]  # eased in, not a jump
    assert F.mouth_state(2.75, line)[0] < 0.1                     # closed on A
    assert F.mouth_state(2.0, None) == (0.0, 1.0)


def test_jaw_moves_only_below_the_mouth_line_and_a_raised_brow_moves_up():
    f = _face()
    gy, gx = np.mgrid[0:160, 0:120].astype(np.float32)
    dx, dy = F.displacement(f, gx, gy, 0.0, 1.0, 0.0)
    assert dy[60, 60] == 0 and dy[100, 60] == 0              # above and at the mouth line: nothing
    assert dy[128, 60] > 8                                   # the chin drops by almost the full jaw
    assert dy[158, 60] < 0.5                                  # a chin's height below it (neck, collar): nothing moves
    assert dy[128, 5] < 0.6 * dy[128, 60]                     # and the jaw's pull fades sideways
    _, up = F.displacement(f, gx, gy, 0.0, 0.0, 1.0)
    assert up[30, 60] < -3 and abs(up[128, 60]) < 1e-6             # brow lifts, chin stays
    _, down = F.displacement(f, gx, gy, 0.0, 0.0, -1.0)
    assert down[30, 60] > 3


def test_paint_closes_the_eye_opens_the_mouth_and_leaves_a_still_face_alone():
    f = _face()
    still = _layer()
    out = still.copy()
    F.paint(out, f, (0, 0, 120, 160), 0.0, 0.0, 0.0, 1.0)
    assert np.array_equal(out, still)                        # nothing to draw: not one pixel changes
    out = still.copy()
    F.paint(out, f, (0, 0, 120, 160), 0.0, 1.0, 0.0, 1.0)
    assert np.allclose(out[50, 60, :3], f["eyes"][0]["skin"], atol=0.15) or out[50, 60, :3].max() < 0.8   # the white is covered
    assert out[50, 60, :3].min() < 0.9 and abs(out[50, 60, 0] - 0.95) > 0.05
    out = still.copy()
    F.paint(out, f, (0, 0, 120, 160), 0.0, 0.0, 1.0, 1.0)
    assert out[110 + 6, 60, :3].max() < 0.7 and out[116, 60, 0] > out[116, 60, 2] + 0.1   # an opening where the mouth is, warm inside (no black hole)
    assert out[116, 60, :3].min() > 0.05
    assert np.array_equal(out[10, 10], still[10, 10])        # far away: untouched


def test_mapper_puts_the_feet_where_the_camera_sees_them(tmp_path):
    a = np.zeros((200, 100, 4), np.uint8)
    a[20:180, 30:70] = (200, 150, 120, 255)
    Image.fromarray(a).save(tmp_path / "X.cut.png")
    shot = J.SHOTS["S1_two_shot"]
    c = {"id": "H2", "img": "X", "pos": (-0.7, 3.8)}
    m = B.ShotAssets._mapper(shot, c, tmp_path, 2560, 1440)
    ndcx, ndcy, _ = J.project(shot["cam"], shot["aim"], shot["lens"], (c["pos"][0], c["pos"][1], J.HERO["H2"]["z0"]))
    fx, fy = m(50.0, 179.0)                                   # the middle of the figure's bottom edge (one pixel eroded) = the feet
    assert abs(fx - (ndcx + 1) / 2 * 2560) < 2 and abs(fy - (1 - ndcy) / 2 * 1440) < 2
    assert m(50.0, 21.0)[1] < fy                              # the head is above the feet
    h_px = fy - m(50.0, 21.0)[1]
    assert abs(h_px - 1.65 * 60 / 36 * 2560 / 3.8) < 6        # and the figure is 1.65 m tall at 3.8 m


def test_nothing_that_moves_a_head_or_brow_jumps_between_frames():
    from pathlib import Path
    cues = [{"start": 0.0, "end": 0.2, "value": "X"}, {"start": 0.2, "end": 0.5, "value": "D"}, {"start": 0.5, "end": 0.9, "value": "A"}]
    lines = [{"hero": "H1", "start": 1.0, "cues": cues}, {"hero": "H2", "start": 3.0, "cues": cues}]
    T = np.arange(0, 6, 1 / 24)
    for hero in ("H1", "H2"):
        d = [F.drive(lines, hero, t, 0.7, B.EXPR) for t in T]
        for key, limit in (("brow", 0.2), ("bob", 0.25), ("spk", 0.25), ("lis", 0.25)):
            v = np.array([x[key] for x in d])
            assert np.abs(np.diff(v)).max() < limit, (hero, key)       # speaker and listener roles fade, they never switch in one frame
    assert F.drive(lines, "H1", 0.0, 0.7, B.EXPR)["spk"] == 0 and F.drive(lines, "H1", 1.3, 0.7, B.EXPR)["spk"] > 0.95
