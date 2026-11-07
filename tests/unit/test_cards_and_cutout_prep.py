"""AS-12 (house-style cards) and DL-03 (clean cut-out edge), D-121."""
import pytest
from PIL import Image

from explainer_engine.production import cards, cutout_prep


def test_cards_use_the_palette_paper_and_the_hand_font():
    for spec in ({"kind": "phone", "battery": 14, "status": "No service"}, {"kind": "stat", "lines": ["8,000,000 people", "fire: 0"]}):
        im = cards.card(spec, (640, 352))
        assert im.size == (640, 352)
        assert max(abs(a - b) for a, b in zip(im.getpixel((320, 20)), cards._rgb("paper"))) < 40   # paper ground, not a flat UI fill
    assert cards.FONT.name == "ComicNeue-Bold.ttf" and cards.FONT.is_file()
    with pytest.raises(ValueError):
        cards.card({"kind": "ui"})


def test_trim_edge_clears_the_border_and_erodes_the_matte():
    im = Image.new("RGBA", (40, 40), (255, 255, 255, 255))          # a figure whose matte touches the image's top edge
    for x in range(40):
        for y in range(10, 40):
            im.putpixel((x, y), (200, 50, 50, 255))
    out = cutout_prep.trim_edge(im, 2)
    assert all(out.getpixel((x, 0))[3] == 0 for x in range(40))    # no top-edge line (v1 00:39, 00:44, 01:01)
    assert out.getpixel((20, 25))[3] == 255
    with pytest.raises(ValueError):
        cutout_prep.trim_edge(im, 0)
