"""HUD OCR check: expected text from the schedule; a one-character counter ("0") is checked as ink, not by OCR (G-04c finding)."""
from __future__ import annotations
import numpy as np
from explainer_engine.maps.maplibre_lane import hud_ocr as H

SPEC = {
    "size": [2560, 1440], "fps": 24, "seconds": 6, "center": [7, 50], "zoom": 5, "line_geojson": "l.geojson", "line_t": [0.4, 5.2],
    "counter": {"from": 0, "to": 420000, "t0": 0.4, "t1": 5.2, "label": "soldiers marched"},
    "date_chip": [{"t": 0.0, "text": "August 1914"}], "towns": [{"name": "Paris", "lonlat": [2.35, 48.86], "t": 0.0}],
    "font": "preset", "footnote": "x",
}
INK = (31, 74, 102)


def _frame(with_glyph: bool) -> np.ndarray:
    img = np.full((1440, 2560, 3), 220, dtype=np.uint8)
    if with_glyph:
        img[75:120, 85:110] = INK  # a 45 px tall glyph in the counter colour
    return img


def test_expected_items_follow_the_schedule():
    items = H.expected_items(SPEC, 0)
    assert items == {"counter": "0", "label": "soldiersmarched", "date": "august1914", "town:Paris": "paris"}
    assert H.expected_items(SPEC, 143)["counter"] == "420000"


def test_single_glyph_counter_is_checked_as_ink():
    ocr = lambda img: ["SOLDIERS MARCHED", "August 1914", "Paris"]  # reads everything but the lone "0"
    good = H.check_frame(_frame(True), SPEC, 0, ocr, INK)
    assert all(v["found"] for v in good.values()) and good["counter"]["method"] == "ink"
    empty = H.check_frame(_frame(False), SPEC, 0, ocr, INK)
    assert empty["counter"]["found"] is False  # a missing counter still fails


def test_multi_digit_counter_must_be_read_by_ocr():
    ocr = lambda img: ["SOLDIERS MARCHED", "August 1914", "Paris"]
    res = H.check_frame(_frame(True), SPEC, 143, ocr, INK)
    assert res["counter"] == {"expected": "420000", "found": False, "method": "ocr"}
    res = H.check_frame(_frame(True), SPEC, 143, lambda img: ["420,000", "SOLDIERS MARCHED"], INK)
    assert res["counter"]["found"] is True


def test_too_small_glyph_is_not_ink():
    img = np.full((1440, 2560, 3), 220, dtype=np.uint8)
    img[75:85, 85:200] = INK  # 10 px tall: below 2 % of the frame height
    assert H.ink_glyph_present(img, INK) is False
