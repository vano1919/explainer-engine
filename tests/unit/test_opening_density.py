"""Opening density: nothing unchanged longer than BP-40's hook still limit inside BP-40's hook window."""

from __future__ import annotations

import json

import pytest

from explainer_engine.qa import opening_density as oc
from explainer_engine.standards import sourced_rules as SR


def shots(*starts, end=60.0):
    out = [{"start": s} for s in starts]
    for a, b in zip(out, out[1:] + [{"start": end}]):
        a["end"] = b["start"]
    return out


def test_numbers_come_from_the_registry():
    assert oc.OPENING_WINDOW_S == SR.T("BP-40", "hook_window_s") and oc.OPENING_MAX_STILL_S == SR.T("BP-40", "hook_max_still_s")


def test_opening_density_passes_when_something_changes_often_enough():
    step = oc.OPENING_MAX_STILL_S
    starts = [i * step for i in range(int(oc.OPENING_WINDOW_S // step) + 1)]          # a cut exactly every limit
    assert oc.opening_density(shots(*starts, end=60.0), 60.0)["status"] == "PASS"


def test_opening_density_fails_on_a_still_inside_the_window():
    limit = oc.OPENING_MAX_STILL_S
    r = oc.opening_density(shots(0.0, limit + 1, 20.0, 25.0, end=60.0), 60.0)
    assert r["status"] == "FAIL" and "BP-40" in r["detail"] and r["value"] > limit


def test_a_long_still_after_the_window_is_not_this_checks_business():
    w = oc.OPENING_WINDOW_S
    starts = [i * oc.OPENING_MAX_STILL_S for i in range(int(w // oc.OPENING_MAX_STILL_S) + 1)]
    assert oc.opening_density(shots(*starts, end=200.0), 200.0)["status"] == "PASS"   # the last shot runs far past the window


def test_a_video_shorter_than_the_window_is_judged_to_its_end():
    assert oc.opening_density(shots(0.0, end=20.0), 20.0)["status"] == "FAIL"
    assert oc.opening_density(shots(0.0, end=3.0), 3.0)["status"] == "PASS"


def test_bubbles_and_beats_count_as_changes():
    sh = shots(0.0, end=60.0)
    sh[0]["bubbles"] = [{"start": 4.0}, {"start": 8.0}, {"start": 12.0}, {"start": 16.0}, {"start": 20.0}, {"start": 24.0}, {"start": 28.0}]
    assert oc.opening_density(sh, 60.0)["status"] == "PASS"
    timed = {"visual_beats": [{"start": float(t)} for t in range(4, 30, 4)]}
    assert oc.opening_density(shots(0.0, end=60.0), 60.0, timed)["status"] == "PASS"


def test_not_run_without_shots_or_duration():
    assert oc.opening_density([], 60.0)["status"] == "NOT_RUN"
    assert oc.opening_density(shots(0.0), 0)["status"] == "NOT_RUN"
    assert oc.opening_density([{"id": "no start"}], 60.0)["status"] == "NOT_RUN"


def test_cli(tmp_path):
    f = tmp_path / "timed.json"
    f.write_text(json.dumps({"duration": 60.0, "shots": shots(*[i * 4.0 for i in range(8)], end=60.0)}), encoding="utf-8")
    assert oc.main([str(f)]) == 0
    f.write_text(json.dumps({"duration": 60.0, "shots": shots(0.0, 1.0, end=60.0)}), encoding="utf-8")
    assert oc.main([str(f)]) == 1
    f.write_text(json.dumps({"shots": []}), encoding="utf-8")
    assert oc.main([str(f)]) == 2
