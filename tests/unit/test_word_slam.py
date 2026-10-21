"""BP-97 / PV-58 (D-66, creator 2026-10-21): a slammed word owns the frame (the picture dims behind it) and stays rare."""

from __future__ import annotations

import numpy as np
from PIL import Image

from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import accents as ACC
from explainer_engine.production import validate as V


def test_the_picture_dims_behind_a_slam_and_comes_back_after():
    frame = Image.new("RGB", (320, 180), (200, 200, 200))
    acc = [{"kind": "slam_text", "start": 0.0, "start_frame": 0, "strength": 0.6, "text": "BROKE", "pos": [0.5, 0.5]}]
    during = np.asarray(ACC.draw(frame, acc, 15, 30, 0, 300, None, BUB.SHOUT_FONT)).astype(int)
    assert during[5, 5].mean() < 200 * (1 - ACC.SLAM_DIM) + 8  # a corner far from the word is dimmed
    after = np.asarray(ACC.draw(frame, acc, 280, 30, 0, 300, None, BUB.SHOUT_FONT)).astype(int)
    assert after[5, 5].mean() == 200


def _doc(*slams):
    return {"segments": [{"id": sid, "shots": [{"accents": [{"kind": "slam_text", "at": w, "text": w}]} for w in words]}
                         for sid, words in slams]}


def test_a_slam_is_short_one_a_scene_and_never_repeated():
    assert V.word_slams(_doc(("S01", ["PAPERWORK"]), ("S02", ["FOREVER"]))) == []
    assert any("2 word slams" in w for _, w in V.word_slams(_doc(("S01", ["A", "B"]))))
    assert any("again" in w for _, w in V.word_slams(_doc(("S01", ["BROKE"]), ("S02", ["broke"]))))
    assert any("words" in w for _, w in V.word_slams(_doc(("S01", ["ONE TWO THREE FOUR"]))))
