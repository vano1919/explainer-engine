"""FA-11 (Fable audit 2026-11-13): BP-81 counts the WORST minute (a long sheet no longer dilutes a crowded one) and the AV
timeline has one dialogue window per line, never one window from the first line to the last."""
from __future__ import annotations

from explainer_engine.episode import av_report as AVR
from explainer_engine.episode import cue_sheet as CS
from explainer_engine.standards import sourced_rules as SR


def test_a_crowded_minute_inside_a_long_sheet_is_found():
    fail_at = float(SR.T("BP-81", "per_min_fail"))
    n = int(fail_at) + 2                                        # one minute with more cues than BP-81's FAIL line
    rows = [{"start_s": 10.0 + k * 3.0, "end_s": 10.5 + k * 3.0, "decision": "ui_cue", "layer": "foley", "class": "ov_pop",
             "event_id": f"e{k}", "purpose": "clarify"} for k in range(n)]
    sheet = {"duration_s": 600.0, "rows": rows, "missing": []}   # ten minutes: the average is under 2 a minute
    out = CS.av_rows(rows, {"shots": []}, sheet)
    row = next(r for r in out if r["gate"] == "cue_density")
    assert row["status"] != "PASS" and row["measured"] == n and "whole sheet" in row["detail"]


def test_dialogue_windows_are_per_line():
    tl = AVR.timeline({"beds": []}, [{"duration_sec": 30.0}], None, {"L1": (1.0, 3.0), "L2": (20.0, 22.0)})
    assert tl["dialogue"] == [[1.0, 3.0], [20.0, 22.0]]
