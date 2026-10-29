"""P0b (OR-29): a phase in review/done has its routing_log line; STATUS.md is rendered from phases.json and decision_queue.json."""
from __future__ import annotations

import copy

from _gov import ROOT, config
from explainer_engine.governance import status

PHASES, LOG = status.phases(ROOT), status.log(ROOT)


def test_the_shipped_files_are_consistent():
    assert status.check_all(ROOT) == []


def test_phase_table_has_the_24_phases_with_known_dependencies():
    assert len(PHASES) == 24
    assert status.check_phases(PHASES) == []


def test_a_done_phase_without_a_log_line_fails():
    rows = copy.deepcopy(PHASES)
    row = next(r for r in rows if r["id"] == "P0c")
    row["state"], row["pr"] = "done", "#9"
    errs = status.check_log(rows, LOG, config())
    assert any("P0c" in e and "routing_log" in e for e in errs)
    line = {"kind": "phase", "phase": "P0c", "level": "S2", "model": "claude-sonnet-5-5", "effort": "medium", "result": "report"}
    assert status.check_log(rows, LOG + [line], config()) == []


def test_a_review_phase_needs_a_pr():
    rows = copy.deepcopy(PHASES)
    next(r for r in rows if r["id"] == "P0c")["state"] = "review"
    assert any("without a PR" in e for e in status.check_phases(rows))


def test_log_lines_are_validated():
    bad = [{"kind": "phase", "phase": "P1", "level": "S9", "model": "m", "effort": "high", "result": "r"},
           {"kind": "phase", "level": "S2", "model": "m", "effort": "high", "result": "r"},
           {"kind": "other"}, {"kind": "switch"}]
    errs = status.check_log([], bad, config())
    assert len(errs) >= 4


def test_status_md_is_generated_and_a_stale_table_fails(tmp_path):
    text = (ROOT / "docs/blueprint/STATUS.md").read_text(encoding="utf-8")
    assert status.render_status(ROOT) == text
    assert status.render_phases(PHASES).count("\n") == 25  # header, rule and 24 rows
    stale = text.replace("| P0c |", "| P0c-stale |")
    assert stale != text and status.render_status(ROOT) != stale


def test_dependencies_must_exist():
    rows = copy.deepcopy(PHASES)
    rows[0]["depends_on"] = ["P99"]
    assert any("unknown P99" in e for e in status.check_phases(rows))
