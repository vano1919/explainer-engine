"""The scene join (W1, 2026-11-12): clips are trimmed by their measured speech (BP-190), each clip's own track fades at its ends
(BP-191) and drops between its lines, the bed is never set closer to the voice than BP-52 allows, and a free CC0 take becomes a
loop without a seam (BP-58)."""
from __future__ import annotations

import numpy as np
import pytest

from explainer_engine.audio import free_import as FI
from explainer_engine.audio import sfx_library as L
from explainer_engine.core.errors import ContractError
from explainer_engine.production import scene_join as J
from explainer_engine.standards import sourced_rules as SR


def test_a_pause_splits_into_tail_and_head():
    tail, head = J.split_pause(0.5)
    assert abs(tail + head - 0.5) < 1e-6 and SR.T("BP-190", "head_lead_s")[0] <= head <= SR.T("BP-190", "head_lead_s")[1]
    tail, head = J.split_pause(0.3)
    assert abs(tail + head - 0.3) < 1e-6 and head >= 0.08


def test_trims_follow_the_measured_speech():
    a, b = J.trims([(2.4, 3.8), (4.6, 6.24)], 10.04, head=0.2, tail=0.3)
    assert abs(a - 2.2) < 1 / 24 and abs(b - 6.54) < 1 / 24           # the hand join cut 0.3 s after the line, then 1.3 s of nothing
    a, b = J.trims([(2.4, 3.8)], 10.04, head=0.2, tail=0.3, lead_s=1.2)   # an establishing shot keeps a lead
    assert abs(a - 1.2) < 1 / 24
    assert J.trims([], 6.0, head=0.2, tail=0.3) == (0.0, 6.0)          # no speech: the whole clip (or the card's keep)
    assert J.trims([], 10.0, head=0.2, tail=0.3, keep=(0.0, 6.0)) == (0.0, 6.0)
    f = J.trims([(1.01, 2.0)], 5.0, head=0.2, tail=0.3)[0] * 24
    assert abs(f - round(f)) < 0.01                                   # on a frame


def test_a_clips_own_hiss_drops_between_its_lines():
    g = J.between_lines_gain(J.RATE * 4, [(0.5, 1.5), (2.5, 3.5)])
    assert g[int(1.0 * J.RATE)] > 0.99 and g[int(2.0 * J.RATE)] < 10 ** (J.BETWEEN_LINES_DB / 20) * 1.01


def test_the_bed_is_never_closer_than_bp52(tmp_path):
    assert J.BED_UNDER_MIN_LU == SR.T("BP-52", "bed_under_lu") == 15.0
    with pytest.raises(ContractError):
        J.join({"scene": "x", "place": "p", "bed": [], "clips": []}, tmp_path, clip_root=tmp_path, library_root=tmp_path,
               pause_s=0.5, bed_under_lu=14.0, label="x")


def test_the_join_reads_its_numbers_from_the_registry():
    assert J.CLIP_FADE_S == pytest.approx(np.mean(SR.T("BP-191", "clip_fade_s")))
    src = open(J.__file__, encoding="utf-8").read()
    reads = {rid for rid, _, _ in SR.threshold_reads(src)}
    assert {"BP-52", "BP-190", "BP-191"} <= reads


def test_a_free_take_loops_without_a_seam():
    rng = np.random.default_rng(1)
    t = np.arange(FI.RATE * 30) / FI.RATE
    x = (rng.standard_normal(len(t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t))).astype(np.float32)
    y = FI.make_loop(x, 24.0)
    assert len(y) / FI.RATE >= SR.T("BP-58", "loop_min_s")
    assert L.seam_step_db(y, FI.RATE) <= SR.T("BP-58", "seam_step_db_max")


def test_the_arranged_march_wraps_round_its_loop():
    rng = np.random.default_rng(2)
    step = (rng.standard_normal(int(0.2 * FI.RATE)) * np.exp(-np.arange(int(0.2 * FI.RATE)) / 900)).astype(np.float32)
    y = FI.arrange_march([step], [step * 0.5], seconds=4.0, seed=3, soldiers=8, steps_per_s=(1.6, 1.9), clinks_per_s=1.0)
    assert len(y) == 4 * FI.RATE
    assert np.sqrt(np.mean(y[:FI.RATE // 10] ** 2)) > 0          # the events that run past the end come back at the start
