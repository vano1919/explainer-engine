"""LT-75 test scoring: a frame equal to the truth scores best; the table orders variants by composite."""
import numpy as np

from explainer_engine.training.pods import xworld_v1_score as sc


def test_identical_frame_beats_a_different_one():
    rng = np.random.default_rng(1)
    truth = (rng.random((72, 128, 3)) * 255).astype(np.uint8)
    other = np.full_like(truth, 200)
    same = sc.frame_metrics(truth, truth, 1.0)
    diff = sc.frame_metrics(other, truth, 0.6)
    assert same["palette"] == 0 and same["change"] == 0 and same["composite"] > diff["composite"]


def test_table_is_ordered_by_composite():
    rows = [{"variant": "D", "lora": "A", "clip": .9, "palette": .1, "ink": 1, "change": .1, "drift": .1, "composite": .7},
            {"variant": "T", "lora": "A", "clip": .8, "palette": .1, "ink": 1, "change": .1, "drift": .1, "composite": .6},
            {"variant": "D0", "lora": None, "clip": .7, "palette": .2, "ink": 1, "change": .2, "drift": .2, "composite": .3}]
    t = sc.summarise(rows)
    assert list(t) == ["D/A", "T/A", "D0/base"] and t["D/A"]["n"] == 1
