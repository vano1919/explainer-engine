"""Unit tests for TODO-11: Stage 3 Wan 2.2 shotplan payload builder, WanLocalRunner retries, WAN_CONTROL escalation, and telemetry."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema

from explainer_engine.aivideo import shotplan, wan_runner
from explainer_engine.imagegen import routing
from tests.unit.test_schemas_v4 import _sample_v4_production_script

ROOT = Path(__file__).resolve().parents[2]
WAN_SCHEMA = json.loads((ROOT / "explainer_engine/schemas/wan_job.schema.json").read_text(encoding="utf-8"))
TELEMETRY_SCHEMA = json.loads((ROOT / "explainer_engine/schemas/render_telemetry.schema.json").read_text(encoding="utf-8"))


def test_build_wan_payload_constructs_valid_jobs_for_all_modes() -> None:
    doc = _sample_v4_production_script()
    flf_shot = doc["shots"][0]
    flf_job = shotplan.build_wan_payload(flf_shot, episode_id=doc["episode_id"])
    jsonschema.validate(flf_job, WAN_SCHEMA)
    assert flf_job["generation_mode"] == "WAN_FLF2V"
    assert flf_job["end_image_path"] == "02_keyframes/shots/S04_SH001_end.png"
    assert "api.ltx-cloud.internal" not in json.dumps(flf_job)

    # Single-frame WAN_I2V
    i2v_shot = copy.deepcopy(flf_shot)
    i2v_shot["shot_id"] = "S04_SH002"
    i2v_shot["generation_mode"] = "WAN_I2V"
    i2v_shot["keyframe_plan"]["needs_end_frame"] = False
    i2v_job = shotplan.build_wan_payload(i2v_shot, episode_id=doc["episode_id"])
    jsonschema.validate(i2v_job, WAN_SCHEMA)
    assert i2v_job["end_image_path"] is None

    # Deterministic 2.5D STILL_25D
    still_shot = copy.deepcopy(i2v_shot)
    still_shot["shot_id"] = "S04_SH003"
    still_shot["visual_type"] = "composed_illustration"
    still_shot["generation_mode"] = "STILL_25D"
    still_shot["video_prompt"]["parallax_preset"] = "dolly_in"
    still_job = shotplan.build_wan_payload(still_shot, episode_id=doc["episode_id"])
    jsonschema.validate(still_job, WAN_SCHEMA)
    assert still_job["model_tier"] == "depthflow_local_25d"


def test_wan_local_runner_retries_seeds_escalates_to_control_and_logs_telemetry(tmp_path: Path) -> None:
    doc = _sample_v4_production_script()
    router = routing.ShotRouter()
    kf_manifest = router.plan_stage2_keyframes(doc, job_dir=tmp_path)

    dispatched_payloads = []

    def fake_post(url: str, payload: dict) -> dict:
        assert url == "http://127.0.0.1:8188/prompt"
        dispatched_payloads.append(payload)
        return {"prompt_id": f"pid_{len(dispatched_payloads)}"}

    # Simulate WAN_FLF2V failing initial attempt + 2 retries due to action/camera error, then succeeding after WAN_CONTROL escalation
    def simulated_qa(job: dict, attempt: int) -> dict:
        if job["generation_mode"] != "WAN_CONTROL":
            return {
                "passed": False,
                "action_or_camera_error": True,
                "failure_reason": "Action trajectory drifted before escalation",
                "qa_metrics": {"duration_match": True, "frozen_frame_ratio": 0.0, "boundary_jump_score": 0.42},
            }
        return {
            "passed": True,
            "failure_reason": None,
            "qa_metrics": {"duration_match": True, "frozen_frame_ratio": 0.0, "boundary_jump_score": 0.03},
        }

    runner = wan_runner.WanLocalRunner(post_fn=fake_post, qa_eval_fn=simulated_qa)
    res = runner.run_episode_stage3(doc, kf_manifest, job_dir=tmp_path)

    # 3 attempts on WAN_FLF2V (1 initial + 2 seed retries) + 1 attempt on escalated WAN_CONTROL = 4 dispatches
    assert len(dispatched_payloads) == 4
    telemetry_lines = (tmp_path / "03_video" / "render_telemetry.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(telemetry_lines) == 4
    records = [json.loads(line) for line in telemetry_lines]
    for rec in records:
        jsonschema.validate(rec, TELEMETRY_SCHEMA)

    assert [r["status"] for r in records] == [
        "REJECTED_AUTO_QA",
        "REJECTED_AUTO_QA",
        "ESCALATED_TO_CONTROL",
        "ACCEPTED",
    ]
    assert records[3]["generation_mode"] == "WAN_CONTROL"
    assert res["manifest"]["jobs"][0]["generation_mode"] == "WAN_CONTROL"


def test_wan_runner_refuses_unapproved_keyframe(tmp_path: Path) -> None:
    doc = _sample_v4_production_script()
    job = shotplan.build_wan_payload(doc["shots"][0], episode_id=doc["episode_id"])
    runner = wan_runner.WanLocalRunner(dry_run=True)
    try:
        runner.run_shot_job(
            job,
            keyframe_status="FLAGGED_HUMAN_REVIEW",
            telemetry_path=tmp_path / "telemetry.jsonl",
            clips_dir=tmp_path / "clips",
        )
    except wan_runner.WanRunnerError as exc:
        assert "FLAGGED_HUMAN_REVIEW" in str(exc)
    else:
        raise AssertionError("Expected WanRunnerError for unapproved keyframe")
