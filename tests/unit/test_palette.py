"""The palette's own rules (explainer_engine/design/palette.json): contrast measured, not asserted in prose."""

from __future__ import annotations

import copy

from explainer_engine.design import palette


def test_the_shipped_palette_is_consistent():
    assert palette.check() == []


def test_contrast_matches_known_values():
    assert abs(palette.contrast("#000000", "#FFFFFF") - 21.0) < 0.01
    assert palette.contrast("#FFFFFF", "#FFFFFF") == 1.0


def test_every_ink_text_pair_reaches_aa():
    pal = palette.load()
    hexes = {n: t["hex"] for n, t in pal["tokens"].items()}
    for pair in pal["text_pairs"]:
        assert palette.contrast(hexes[pair["text"]], hexes[pair["on"]]) >= palette.TEXT_MIN, pair


def test_accents_alone_do_not_reach_graphic_contrast_on_paper_except_none_claimed():
    pal = palette.load()
    hexes = {n: t["hex"] for n, t in pal["tokens"].items()}
    weak = [n for n in pal["fill_only"] if palette.contrast(hexes[n], hexes["paper"]) < palette.GRAPHIC_MIN]
    assert {"answer_coral", "mechanism_teal", "true_green", "uncertain_amber"} <= set(weak)  # why they need an ink stroke


def test_a_bad_pair_is_reported():
    pal = copy.deepcopy(palette.load())
    pal["text_pairs"].append({"text": "uncertain_amber", "on": "paper"})
    findings = palette.check(pal)
    assert any(f["check"] == "text_contrast" and "uncertain_amber on paper" in f["detail"] for f in findings)
    pal2 = copy.deepcopy(palette.load())
    pal2["tokens"]["ink"]["hex"] = "1F2430"
    assert any(f["check"] == "hex_format" for f in palette.check(pal2))
