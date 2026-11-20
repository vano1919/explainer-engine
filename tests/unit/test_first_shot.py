"""First shot floor (the owner's OR-E01 card), from the registry's BP-85 number."""

from __future__ import annotations

import json

import pytest

from explainer_engine.qa import first_shot as oc
from explainer_engine.standards import sourced_rules as SR


def shots(*starts, end=60.0):
    out = [{"start": s} for s in starts]
    for a, b in zip(out, out[1:] + [{"start": end}]):
        a["end"] = b["start"]
    return out


def test_number_comes_from_the_registry():
    assert oc.FIRST_SHOT_MIN_S == SR.T("BP-85", "c_shot_s")[0]


def test_first_shot_floor():
    floor = oc.FIRST_SHOT_MIN_S
    assert oc.first_shot(shots(0.0, floor))["status"] == "PASS"                         # exactly the floor passes
    assert oc.first_shot(shots(0.0, floor + 3))["status"] == "PASS"
    r = oc.first_shot(shots(0.0, floor - 0.1))
    assert r["status"] == "FAIL" and abs(r["value"] - (floor - 0.1)) < 1e-9 and "flash" in r["detail"]


def test_first_shot_not_run_cases():
    assert oc.first_shot([])["status"] == "NOT_RUN"
    assert oc.first_shot([{"start": 0.0}])["status"] == "NOT_RUN"
    assert oc.first_shot([{"start": "x", "end": 1}])["status"] == "NOT_RUN"


def test_cli(tmp_path):
    f = tmp_path / "timed.json"
    f.write_text(json.dumps({"shots": shots(0.0, 3.0)}), encoding="utf-8")
    assert oc.main([str(f)]) == 0
    f.write_text(json.dumps({"shots": shots(0.0, 1.0)}), encoding="utf-8")
    assert oc.main([str(f)]) == 1
    f.write_text(json.dumps({"shots": []}), encoding="utf-8")
    assert oc.main([str(f)]) == 2
