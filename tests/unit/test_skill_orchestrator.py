"""Unit tests for canonical operational SkillOrchestrator, triggers, gap blocking, and episode wiring."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.episode.router import select_ltx_worker
from explainer_engine.episode.run import stage_previs_blender
from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator


def test_registry_has_no_hardcoded_10_30_60_quota_and_retires_legacy():
    orch = SkillOrchestrator()
    policy = orch.registry["policy"]
    assert policy["flexible_visual_composition"] is True
    assert policy["enforced_10_30_60_quota"] is False
    assert "qwen_lora_pipeline" in policy["retired_technologies"]
    assert "unreal_engine" in policy["retired_technologies"]


def test_audit_correspondence_fails_closed_on_unresolved_gaps_unless_waived():
    orch = SkillOrchestrator()
    strict = orch.audit_correspondence(allow_gaps=False)
    assert strict["missing_skill_dirs"] == []
    assert strict["missing_python_modules"] == []
    assert strict["documented_gaps"], "registry has documented gaps that must fail closed"
    assert strict["ok"] is False

    waived = orch.audit_correspondence(allow_gaps=True)
    assert waived["ok"] is True
    assert waived["active_skills_count"] >= 15
    assert "S4_blender_previs" in waived["registered_executors"]


def test_retired_skill_activation_is_refused():
    orch = SkillOrchestrator()
    with pytest.raises(ContractError):
        orch.assert_not_retired("lora-training")


def test_trigger_selection_and_gap_blocking():
    orch = SkillOrchestrator()
    plan = orch.select_by_triggers(
        ["camera_blocking"],
        available_artifacts={"topic_brief", "episode_film_preset"},
        allow_gaps=False,
    )
    ids = [s.stage_id for s in plan.stages]
    assert "S4_blender_previs" in ids
    # S2_story_and_script has an open gap so strict plan must fail closed
    assert plan.ready is False
    assert "S2_story_and_script" in plan.blocked_implementation_gaps

    waived = orch.select_by_triggers(
        ["camera_blocking"],
        available_artifacts={"topic_brief", "episode_film_preset"},
        allow_gaps=True,
    )
    assert waived.ready is True


def test_real_stage_execution_for_blender_previs_and_ltx_routing(tmp_path: Path):
    orch = SkillOrchestrator()
    ledger = tmp_path / "skill_execution_record.json"

    t0_spec = Path("explainer_engine/lab/specs/t0/t0_a1.json")
    r_prev = orch.run_stage("S4_blender_previs", {"scene_spec_path": str(t0_spec)}, ledger_path=ledger)
    assert r_prev["status"] == "VALIDATED"
    assert r_prev["outputs"] == []

    r_ltx = orch.run_stage("S6_ltx_video", {"shot": {"use_ic_lora": True}}, ledger_path=ledger)
    assert r_ltx["worker"]["account"] == "MODAL1"
    assert r_ltx["status"] == "PLANNED"
    assert r_ltx["outputs"] == []
    assert r_ltx["worker"]["worker_module"] == "explainer_engine.training.pods.ltx.modal_layout_jobs"

    r_std = select_ltx_worker({"shot_id": "s1"})
    assert r_std["worker_module"] == "explainer_engine.training.pods.ltx.modal_ltx_jobs"

    ep_prev = stage_previs_blender(tmp_path, t0_spec)
    assert ep_prev["status"] == "PASS"

    data = json.loads(ledger.read_text(encoding="utf-8"))
    assert len(data["executions"]) == 2
