"""P0b (OR-29): a phase in review/done has its routing_log line; STATUS.md is rendered from phases.json and decision_queue.json."""
from __future__ import annotations

import copy
import json
import re

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
    row = next(r for r in rows if r["id"] == "P6")
    row["state"], row["pr"] = "done", "#9"
    errs = status.check_log(rows, LOG, config())
    assert any("P6" in e and "routing_log" in e for e in errs)
    line = {"kind": "phase", "phase": "P6", "level": "S2", "model": "claude-sonnet-5-5", "effort": "medium", "result": "report"}
    assert status.check_log(rows, LOG + [line], config()) == []


def test_a_review_phase_needs_a_pr():
    rows = copy.deepcopy(PHASES)
    next(r for r in rows if r["id"] == "P6")["state"] = "review"
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


MERGED = {"P0a": ["#32"], "P0b": ["#30"], "P0c": ["#35"], "P1a": ["#29"], "P1b": ["#46", "#49"], "P1c": ["#48"], "P2": ["#31"],
          "P3b": ["#36"], "P4b": ["#45", "#50"], "P5": ["#47"], "P3": ["#40"], "P4": ["#51"], "P12d": ["#44"]}


def test_merged_phases_are_marked_done_with_their_pr():
    """T3-1 (CP-03): the table says what main says (merge commits on main, docs/PROGRESS.md entries)."""
    by_id = {r["id"]: r for r in PHASES}
    for pid, prs in MERGED.items():
        assert by_id[pid]["state"] == "done", pid
        for pr in prs:
            assert f"{pr} merged" in by_id[pid]["pr"], (pid, pr)


def test_every_merged_phase_has_a_routing_log_row():
    logged = {r.get("phase") for r in LOG if r.get("kind") == "phase"}
    for p in PHASES:
        if re.search(r"#\d+ merged", str(p.get("pr") or "")):
            assert p["id"] in logged, p["id"]


def test_governance_check_fails_closed_on_merged_phase_without_log(tmp_path):
    from _gov import make_repo
    repo = make_repo(tmp_path / "r")
    assert status.check_all(repo) == []
    path = repo / "docs/blueprint/routing_log.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    kept = [r for r in rows if r.get("phase") != "P1a"]
    assert len(kept) == len(rows) - 1
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    errs = status.check_all(repo)
    assert any("P1a" in e and "routing_log" in e for e in errs), errs
