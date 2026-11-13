"""ICW-05 style bridge (roadmap 9.1, section 11): HELPER frames take the Blender look's tokens (palette ink/paper, BP-173 weight
scaled to the frame, the paper overlay at the same opacity) and the pass is deterministic."""
import hashlib

import numpy as np
import pytest
from PIL import Image

from explainer_engine.blender import style as S
from explainer_engine.edit import style_bridge as B


def paper_tex(w=64, h=64):
    rng = np.random.default_rng(7)  # a test fixture of a paper scan, not the bridge's grain
    a = (200 + rng.integers(0, 30, size=(h, w))).astype(np.uint8)
    return Image.fromarray(a, "L").convert("RGB")


def frame(w=320, h=180, rgba=False):
    im = Image.new("RGBA" if rgba else "RGB", (w, h), B._rgb(S.palette()["paper"]) + ((255,) if rgba else ()))
    im.paste(B._rgb(S.palette()["ink"]) + ((255,) if rgba else ()), (40, 40, 120, 140))
    return im


def test_tokens_come_from_the_palette_and_the_style_tokens():
    t = B.BridgeTokens.from_style(S.StyleTokens())
    pal = S.palette()
    assert t.ink == B._rgb(pal["ink"]) and t.paper == B._rgb(pal["paper"])
    assert t.paper_opacity == 0.12 and t.line_px_1440 == 2.25
    assert t.colour("faction_a") == B._rgb(pal["faction_a"])
    with pytest.raises(KeyError):
        t.colour("chroma_key")


def test_line_weight_scales_with_the_frame_height():
    t = B.BridgeTokens.from_style(S.variant("C"))
    assert t.line_px(1440) == 3.0 and t.line_px(1080) == 2.25 and t.line_px(720) == 1.5


def test_finish_is_deterministic_and_keeps_size_mode_and_alpha():
    t = B.BridgeTokens.from_style()
    a = B.finish(frame(), t, paper=paper_tex())
    b = B.finish(frame(), t, paper=paper_tex())
    assert hashlib.sha256(a.tobytes()).digest() == hashlib.sha256(b.tobytes()).digest()
    assert a.size == (320, 180) and a.mode == "RGB"
    ra = B.finish(frame(rgba=True), t, paper=paper_tex())
    assert ra.mode == "RGBA" and ra.getchannel("A").getextrema() == (255, 255)


def test_finish_changes_pixels_by_at_most_the_opacity_and_not_without_paper():
    t = B.BridgeTokens.from_style()
    src = frame()
    assert B.finish(src, t).tobytes() == src.tobytes()
    out = np.asarray(B.finish(src, t, paper=paper_tex()), dtype=np.int16)
    diff = np.abs(out - np.asarray(src, dtype=np.int16))
    assert diff.max() > 0
    assert diff.max() <= round(255 * t.paper_opacity) + 1


def test_overlay_matches_blender_overlay_formula():
    base = np.array([[0.2, 0.8]], dtype=np.float32)[..., None].repeat(3, axis=2)
    top = np.array([[0.5, 0.5]], dtype=np.float32)
    assert np.allclose(B.overlay(base, top, 1.0), base)  # 0.5 grain is neutral
    top = np.array([[1.0, 0.0]], dtype=np.float32)
    out = B.overlay(base, top, 1.0)
    assert np.allclose(out[0, 0], 0.4) and np.allclose(out[0, 1], 0.6)


def test_grain_is_stretched_and_cropped_to_the_aspect():
    g = B.grain(paper_tex(100, 50), 32, 18)
    assert g.shape == (18, 32) and g.min() == 0.0 and g.max() == 1.0
    flat = B.grain(Image.new("L", (10, 10), 128), 8, 8)
    assert np.allclose(flat, 0.5)


def test_off_palette_share_flags_foreign_colours():
    t = B.BridgeTokens.from_style()
    assert B.off_palette_share(frame(), t) == 0.0
    im = Image.new("RGB", (64, 64), (0, 255, 0))
    assert B.off_palette_share(im, t) == 1.0
