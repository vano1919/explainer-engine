"""Unit tests for canonical SkillOrchestrator and Skill registry traceability."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator


def test_registry_has_no_hardcoded_10_30_60_quota_and_retires_legacy():
    orch = SkillOrchestrator()
    policy = orch.registry["policy"]
    assert policy["flexible_visual_composition"] is True
    assert policy["enforced_10_30_60_quota"] is False
    assert "qwen_lora_pipeline" in policy["retired_technologies"]
    assert "unreal_engine" in policy["retired_technologies"]


def test_audit_correspondence_passes_against_repo():
    orch = SkillOrchestrator()
    report = orch.audit_correspondence()
    assert report["missing_skill_dirs"] == [], report["missing_skill_dirs"]
    assert report["missing_python_modules"] == [], report["missing_python_modules"]
    assert report["ok"] is True
    assert report["active_skills_count"] >= 15
    assert report["python_modules_count"] >= 15


def test_retired_skill_activation_is_refused():
    orch = SkillOrchestrator()
    with pytest.raises(ContractError):
        orch.assert_not_retired("lora-training")


def test_conditional_stages_respect_context_without_forcing_all_lanes():
    orch = SkillOrchestrator()
    plan = orch.select_plan(
        requested_stages=["S10_qa_and_delivery", "S4_blender_previs", "S6_ltx_video", "S7_maps_and_25d"],
        context={"needs_blender_previs": True, "needs_ltx_video": False, "needs_maps_or_25d": False},
        available_artifacts={"topic_brief", "episode_film_preset"},
    )
    selected_ids = [s.stage_id for s in plan.stages]
    assert "S4_blender_previs" in selected_ids
    assert "S6_ltx_video" in plan.skipped_conditional
    assert "S7_maps_and_25d" in plan.skipped_conditional
    assert plan.ready is True


def test_missing_inputs_block_plan_and_execution_ledger_persists(tmp_path: Path):
    orch = SkillOrchestrator()
    blocked = orch.select_plan(requested_stages=["S3_film_direction"], available_artifacts=set())
    assert blocked.ready is False
    assert "S1_research" in blocked.blocked_missing_inputs

    ledger = tmp_path / "skill_execution_record.json"
    entry = orch.record_execution(
        ledger,
        stage_id="S3_film_direction",
        skills_used=["film-direction", "visual-beats"],
        inputs=["approved_script"],
        outputs=["shot_plan"],
        status="PASS",
        notes="validated",
    )
    assert entry["status"] == "PASS"
    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(data["executions"]) == 1
