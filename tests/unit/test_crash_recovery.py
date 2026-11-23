"""Integration test proving crash-safe checkpoint recovery with zero duplicate stage/paid invocations."""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.orchestration.skill_orchestrator import SkillOrchestrator


def test_orchestrator_crash_recovery_resumes_without_duplicate_calls(tmp_path: Path):
    orch = SkillOrchestrator()
    calls: list[str] = []
    should_fail = {"S6_ltx_video": True}

    def make_handler(sid: str):
        def _run(payload: dict) -> dict:
            calls.append(sid)
            if should_fail.get(sid):
                return {"status": "FAIL", "notes": "simulated mid-run crash"}
            return {"status": "PASS", "outputs": []}
        return _run

    for sid in ("S1_research", "S2_story_and_script", "S3_film_direction", "S5_gemini_images", "S6_ltx_video"):
        orch.register_executor(sid, make_handler(sid))

    plan = orch.select_plan(
        requested_stages=["S6_ltx_video"],
        context={"needs_gemini_images": True, "needs_ltx_video": True},
        available_artifacts={"topic_brief", "episode_film_preset"},
        allow_gaps=True,
    )
    cp = tmp_path / "checkpoint.json"
    ledger = tmp_path / "ledger.json"

    # First run: fails at S6_ltx_video after completing S1..S5
    r1 = orch.run_plan(plan, {}, ledger_path=ledger, checkpoint_path=cp, allow_gaps=True)
    assert r1["status"] == "FAIL"
    assert r1["failed_stage"] == "S6_ltx_video"
    assert set(r1["completed_stages"]) == {"S1_research", "S2_story_and_script", "S3_film_direction", "S5_gemini_images"}
    assert calls == ["S1_research", "S2_story_and_script", "S3_film_direction", "S5_gemini_images", "S6_ltx_video"]

    # Second run (resume): S1..S5 are NOT re-executed; only S6_ltx_video runs once more and succeeds
    should_fail["S6_ltx_video"] = False
    r2 = orch.run_plan(plan, {}, ledger_path=ledger, checkpoint_path=cp, allow_gaps=True)
    assert r2["status"] == "PASS"
    assert calls.count("S1_research") == 1
    assert calls.count("S5_gemini_images") == 1
    assert calls.count("S6_ltx_video") == 2
    saved = json.loads(cp.read_text(encoding="utf-8"))
    assert "S6_ltx_video" in saved["completed_stages"]
