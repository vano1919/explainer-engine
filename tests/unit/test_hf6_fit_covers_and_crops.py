"""HF-6 (Truce 1914 assembly, FL-412, TD-307): ``assemble._fit`` scales to cover and centre-crops; it never stretches."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.production import assemble as ASM


def _circle_frame(w=1280, h=704, r=200) -> np.ndarray:
    im = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(im).ellipse((w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r), fill=(255, 255, 255))
    return np.asarray(im)


def test_a_1280x704_frame_comes_out_1920x1080_with_the_circle_still_round():
    out = ASM._fit(_circle_frame(), (1920, 1080))
    assert out.shape == (1080, 1920, 3)
    mask = out[..., 0] > 128
    ys, xs = np.nonzero(mask)
    assert abs((xs.max() - xs.min()) - (ys.max() - ys.min())) <= 1            # width equals height within one pixel


def test_the_crop_is_centred_and_loses_only_the_sides():
    f = np.zeros((704, 1280, 3), np.uint8)
    f[:, :40] = (255, 0, 0)      # the left edge
    f[:, -40:] = (0, 0, 255)     # the right edge
    f[:, 640:644] = (0, 255, 0)  # the centre line
    out = ASM._fit(f, (1920, 1080))
    assert out[540, 960 - 2:960 + 4, 1].max() == 255                         # the centre stays at the centre
    assert out[540, 0, 0] < 255 or out[540, 0, 2] < 255                      # part of the edge strips is cropped away


def test_the_same_aspect_gives_the_pixels_a_plain_resize_gave():
    f = np.random.default_rng(1).integers(0, 255, (180, 320, 3), dtype=np.uint8)
    assert np.array_equal(ASM._fit(f, (640, 360)), np.asarray(Image.fromarray(f).resize((640, 360), Image.LANCZOS)))
    assert ASM._fit(f, (320, 180)) is f


def test_a_taller_source_is_cropped_top_and_bottom():
    f = np.zeros((400, 200, 3), np.uint8)
    f[:20] = 255
    f[-20:] = 255
    out = ASM._fit(f, (200, 100))
    assert out.shape == (100, 200, 3) and out[0].max() < 255 and out[-1].max() < 255   # both strips cropped away
