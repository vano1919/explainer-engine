"""Dead air under narration: BP-36's review and fail gaps, from the registry."""

from __future__ import annotations

import json

from explainer_engine.qa import dead_air as da
from explainer_engine.standards import sourced_rules as SR


def tl(starts, end=100.0, lines=None):
    shots = [{"start": s} for s in starts]
    for a, b in zip(shots, shots[1:] + [{"start": end}]):
        a["end"] = b["start"]
    return shots, (lines if lines is not None else [{"start": 0.0, "end": end}])


def test_numbers_come_from_the_registry():
    assert (da.GAP_REVIEW_S, da.GAP_FAIL_S) == (SR.T("BP-36", "gap_review_s"), SR.T("BP-36", "gap_fail_s"))


def test_pass_review_fail_bands():
    ok, bad = da.GAP_REVIEW_S, da.GAP_FAIL_S
    sh, ln = tl([0.0, ok, 2 * ok], end=2 * ok)
    assert da.dead_air(sh, ln, 2 * ok)["status"] == "PASS"                      # exactly the review gap passes
    sh, ln = tl([0.0, ok + 1, 2 * ok + 2], end=2 * ok + 2)
    r = da.dead_air(sh, ln, 2 * ok + 2)
    assert r["status"] == "REVIEW" and "BP-36" in r["detail"]
    sh, ln = tl([0.0, bad + 1], end=bad + 2)
    r = da.dead_air(sh, ln, bad + 2)
    assert r["status"] == "FAIL" and r["value"] > bad


def test_a_still_with_no_narration_over_it_is_not_dead_air():
    one = [{"start": 0.0, "end": 100.0}]
    assert da.dead_air(one, [{"start": 90.0, "end": 91.0}], 100.0)["status"] == "FAIL"     # the narrator speaks inside the still
    assert da.dead_air(one, [{"start": 100.0, "end": 100.0}], 100.0)["status"] == "NOT_RUN"  # an empty line is no narration


def test_dialogue_lines_are_not_narration():
    sh, _ = tl([0.0], end=100.0)
    assert da.dead_air(sh, [{"start": 0.0, "end": 100.0, "speaker": "A"}], 100.0)["status"] == "NOT_RUN"


def test_bubbles_break_up_a_still():
    sh, ln = tl([0.0], end=100.0)
    sh[0]["bubbles"] = [{"start": float(t)} for t in range(5, 100, 5)]
    assert da.dead_air(sh, ln, 100.0, {"shots": sh})["status"] == "PASS"


def test_not_run_cases():
    assert da.dead_air([], [{"start": 0, "end": 1}], 10)["status"] == "NOT_RUN"
    assert da.dead_air([{"start": 0.0, "end": 5.0}], [], 5)["status"] == "NOT_RUN"
    assert da.dead_air([{"start": 0.0, "end": 5.0}], [{"start": 0, "end": 1}], 0)["status"] == "NOT_RUN"
    assert da.dead_air([{"id": "x"}], [{"start": 0, "end": 1}], 5)["status"] == "NOT_RUN"


def test_cli(tmp_path):
    f = tmp_path / "timed.json"
    sh, ln = tl([0.0, 5.0], end=10.0)
    f.write_text(json.dumps({"duration": 10.0, "shots": sh, "lines": ln}), encoding="utf-8")
    assert da.main([str(f)]) == 0
    sh, ln = tl([0.0], end=100.0)
    f.write_text(json.dumps({"duration": 100.0, "shots": sh, "lines": ln}), encoding="utf-8")
    assert da.main([str(f)]) == 1
    f.write_text(json.dumps({"shots": []}), encoding="utf-8")
    assert da.main([str(f)]) == 2
