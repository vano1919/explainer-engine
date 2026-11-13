"""Unit tests for TODO-13: 4-stage local pipeline CLI and production_gate e2e dry-run."""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine import production_gate
from explainer_engine.production import __main__ as prod_cli
from tests.unit.test_schemas_v4 import _sample_v4_production_script


def test_production_cli_check_local_and_all_four_stages_dryrun(tmp_path: Path) -> None:
    # 1. --check-local offline preflight
    rc_check = prod_cli.main(["--check-local"])
    assert rc_check == 0

    # 2. Write a sample v4.0 script and run all 4 stages in --dry-run mode
    script_file = tmp_path / "input_script.json"
    script_file.write_text(json.dumps(_sample_v4_production_script(), indent=2), encoding="utf-8")
    job_dir = tmp_path / "job_waterloo"

    for stage in ("1", "2", "3", "4"):
        rc = prod_cli.main(["--script", str(script_file), "--stage", stage, "--dry-run", "--out", str(job_dir)])
        assert rc == 0, f"Stage {stage} failed"

    assert (job_dir / "01_script" / "production_script.json").exists()
    assert (job_dir / "01_script" / "research_dossier.md").exists()
    assert (job_dir / "02_keyframes" / "keyframe_manifest.json").exists()
    assert (job_dir / "03_video" / "wan_jobs_manifest.json").exists()
    assert (job_dir / "03_video" / "render_telemetry.jsonl").exists()
    assert (job_dir / "04_assembly" / "audio" / "audio_spine_manifest.json").exists()
    assert (job_dir / "04_assembly" / "timeline" / "episode_master_24fps.mp4").exists()
    assert (job_dir / "04_assembly" / "qa_report.json").exists()

    gates = production_gate.gates(job_dir)
    assert [g["status"] for g in gates] == ["PASS", "PASS", "PASS", "PASS"]
