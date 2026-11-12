"""Unit tests for TODO-15: Phase 1 compatibility and ablation runner dry-run."""

from __future__ import annotations

from pathlib import Path

from scripts import run_phase1_ablations


def test_phase1_ablation_runner_dryrun_writes_report(tmp_path: Path) -> None:
    out_file = tmp_path / "phase1_ablation_report.json"
    rep = run_phase1_ablations.run_ablations(dry_run=True, out_path=out_file)
    assert out_file.exists()
    assert rep["execution_mode"] == "dry_run_graph_verification"
    assert set(rep["tests"].keys()) == {"T-ABL-01", "T-ABL-02", "T-ABL-03", "T-ABL-04"}
    assert rep["tests"]["T-ABL-02"]["enabled_by_default"] is False
    assert rep["tests"]["T-ABL-02"]["stack_with_multiangle_allowed"] is False
    assert len(rep["tests"]["T-ABL-03"]["variants_verified"]) == 4
