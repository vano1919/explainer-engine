"""The J5 dialogue test's moving background (``blender/j5_background.py``): the pieces that make a frame a pure function of its time.
No Blender, no ffmpeg here."""
import numpy as np

from explainer_engine.blender import j5_background as B


def test_flicker_is_bounded_deterministic_and_alive():
    ts = np.arange(0, 12, 1 / 24)
    a = np.array([B.flicker(t) for t in ts])
    assert np.array_equal(a, np.array([B.flicker(t) for t in ts]))
    assert a.min() >= -1 and a.max() <= 1
    assert a.std() > 0.15                                  # it really moves
    assert abs(a.mean()) < 0.3                              # and does not drift to one side


def test_tile_noise_tiles_and_scroll_wraps():
    n = B.tile_noise(64, 3)
    assert n.shape == (64, 64) and 0 <= n.min() and n.max() <= 1
    w = B.scroll(n, 0, 0, 64, 64, 1.0)
    assert np.allclose(w, n, atol=1e-5)
    shifted = B.scroll(n, 64, 64, 64, 64, 1.0)              # a whole tile later is the same window
    assert np.allclose(shifted, n, atol=1e-5)


def test_affine_keeps_the_pivot_fixed():
    M = B.affine(1.3, 1.3, (100.0, 200.0), (0.0, 0.0))
    p = M @ np.array([100.0, 200.0, 1.0])
    assert np.allclose(p, [100.0, 200.0])
    q = B.affine(1.0, 1.0, (0, 0), (5.0, -3.0)) @ np.array([10.0, 10.0, 1.0])
    assert np.allclose(q, [15.0, 7.0])


def test_flame_mask_finds_a_flame_coloured_blob_inside_the_fire_box_only():
    a1 = np.zeros((1024, 2048, 3), np.uint8)
    a1[560:640, 980:1040] = (250, 140, 30)                  # in the box
    a1[100:160, 100:160] = (250, 140, 30)                   # outside it: a lamp, the moon
    m = B.flame_mask(a1)
    assert m[600, 1010] > 0.9 and m[130, 130] == 0


def test_ambience_is_stereo_finite_and_has_no_voice_band_peak_clipping():
    amb = B.ambience(2.0, sr=16000)
    assert amb.shape == (32000, 2) and np.isfinite(amb).all()
    assert np.abs(amb).max() <= 0.5 + 1e-6
    assert amb[:100].std() < amb[8000:8100].std()           # fades in
