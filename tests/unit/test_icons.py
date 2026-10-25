"""Drawn props from the text (design/icons.py, the creator 2026-10-21): vendored line icons drawn on as stickers."""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

from explainer_engine.design import icons as I
from explainer_engine.production import beats as B


def test_the_path_reader_draws_arcs_and_relative_moves():
    lines = I.path_polylines("M12 3a9 9 0 1 0 0.001 0z")  # a circle as one arc
    pts = lines[0]
    assert all(abs(math.dist(p, (12, 12)) - 9) < 0.2 for p in pts)
    assert I.path_polylines("M3 7l9 6l9 -6")[0][-1] == (21.0, 7.0)


def test_every_vendored_icon_draws_and_the_licence_is_kept():
    assert (I.SVG_DIR / "LICENSE").exists()
    for n in I.available():
        assert I.icon_polylines(n), n


def test_a_row_is_drawn_on_in_turn_and_holds_once_complete():
    def ink(t):  # dark stroke pixels on the paper discs
        a = np.asarray(I.strip("cash+rocket", 96, t)).astype(int)
        return int(((a[..., 3] > 200) & (a[..., :3].sum(axis=2) < 200)).sum())

    seen = [ink(t) for t in (0.2, 0.35, 0.6, 0.9, 2.0, 5.0)]
    assert seen == sorted(seen) and seen[0] < seen[-1] and seen[-2] == seen[-1]
    assert I.strip("cash+rocket", 96, 0.0) is None or not np.asarray(I.strip("cash+rocket", 96, 0.0))[..., 3].any()


def test_an_icon_prop_draws_its_row_and_caption_and_a_missing_icon_fails():
    frame = Image.new("RGB", (640, 360), (40, 40, 40))
    b = dict(kind="prop", thing="money", asset="icon:cash", text="FORTY BUCKS", pos=[0.5, 0.4], start=0.0, end=3.0,
             start_frame=0, end_frame=90, shot="SH1")
    out = np.asarray(B.draw(frame, [b], 60, 30, (0, 0, 640, 360), (640, 360), {}, [])).astype(int)
    assert (out.sum(axis=2) > 600).sum() > 2000  # the paper sticker and the caption tag are on screen
    assert B.icon_hold("icon:a+b+c") > B.HOLD["prop"]
    doc = {"schema": "production_script/3", "segments": [{"id": "S01", "lines": [{"text": "He has forty dollars.",
           "visual_beats": [{"at": "forty dollars", "kind": "prop", "thing": "money", "asset": "icon:no-such-icon",
                             "why": "the forty dollars he has"}]}]}], "cast": {}}
    assert any("VB-06" in f["rule"] and f["severity"] == "FAIL" for f in B.lint(doc))


def test_a_drawn_prop_ends_with_its_shot_and_a_symbol_may_cross_the_cut():
    from explainer_engine.production import script as S
    doc = {"schema": "production_script/3", "episode": {"id": "x"},
           "segments": [{"id": "S01", "lines": [{"text": "He has forty dollars and no time.", "visual_beats": [
               {"at": "forty dollars", "kind": "prop", "thing": "money", "asset": "icon:cash", "why": "his forty dollars"},
               {"at": "no time", "kind": "symbol", "symbol": "question", "why": "no time left"}]}], "shots": []}]}
    toks = S.tokens(doc)
    words = [{"w": t["w"], "s": 0.5 + i * 0.4, "e": 0.8 + i * 0.4} for i, t in enumerate(toks)]
    shots = [{"id": "T1", "picture": "p", "start": 0.0, "end": 2.0, "accents": []},
             {"id": "T2", "picture": "q", "start": 2.0, "end": 10.0, "accents": []}]
    out = B.resolve(doc, toks, words, lambda i: i, shots, 30, 10.0, [])
    prop = next(b for b in out if b["kind"] == "prop")
    assert prop["shot"] == "T1" and prop["end"] == 2.0  # FORTY BUCKS does not ride into the next scene
