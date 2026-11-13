"""Unit tests for TODO-09: Stage 2 Qwen keyframe routing, 1-or-2 keyframe rule, and 2D repair retries."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema

from explainer_engine.imagegen import plan, routing
from tests.unit.test_schemas_v4 import _sample_v4_production_script

ROOT = Path(__file__).resolve().parents[2]
KF_SCHEMA = json.loads((ROOT / "explainer_engine/schemas/keyframe_manifest.schema.json").read_text(encoding="utf-8"))
SR_SCHEMA = json.loads((ROOT / "explainer_engine/schemas/shot_route.schema.json").read_text(encoding="utf-8"))


def test_shot_router_plans_stage2_keyframes_and_enforces_end_frame_rule(tmp_path: Path) -> None:
    doc = _sample_v4_production_script()
    # Add a WAN_I2V shot (needs_end_frame=False) alongside S04_SH001 (WAN_FLF2V, needs_end_frame=True)
    shot2 = copy.deepcopy(doc["shots"][0])
    shot2["shot_id"] = "S04_SH002"
    shot2["generation_mode"] = "WAN_I2V"
    shot2["keyframe_plan"]["needs_end_frame"] = False
    shot2["keyframe_plan"]["end_frame_reason"] = None
    shot2["image_prompt"]["end_frame_prompt"] = None
    doc["shots"].append(shot2)
    doc["segments"][0]["target_duration_seconds"] = 10.0

    router = routing.ShotRouter(model_id="qwen_image_edit_2511")
    manifest = router.plan_stage2_keyframes(doc, job_dir=tmp_path)
    jsonschema.validate(manifest, KF_SCHEMA)

    shots_by_id = {s["shot_id"]: s for s in manifest["shots"]}
    assert shots_by_id["S04_SH001"]["needs_end_frame"] is True
    assert shots_by_id["S04_SH001"]["end_frame_path"] == "02_keyframes/shots/S04_SH001_end.png"
    assert shots_by_id["S04_SH002"]["needs_end_frame"] is False
    assert shots_by_id["S04_SH002"]["end_frame_path"] is None

    route_doc = json.loads((tmp_path / "02_keyframes" / "shot_route.json").read_text(encoding="utf-8"))
    jsonschema.validate(route_doc, SR_SCHEMA)

    # Verify ComfyUI graph compilation contains zero cloud endpoints and substitutes Qwen parameters
    graph = router.build_comfy_prompt(doc["shots"][0], doc["world_bible"], frame_role="start", seed=777)
    serialized = json.dumps(graph)
    assert "qwen-api.internal" not in serialized
    assert "{{" not in serialized
    assert graph["5"]["inputs"]["horizontal_azimuth_deg"] == 315


def test_shot_router_2d_repair_retries_up_to_three_times(tmp_path: Path) -> None:
    doc = _sample_v4_production_script()
    router = routing.ShotRouter(model_id="qwen_image_2_1_xworld_v2")

    # Succeeds on 3rd try (attempt index 2 -> 2 repair attempts)
    calls = []

    def pass_on_third(shot: dict, role: str, seed: int) -> bool:
        calls.append(seed)
        return len(calls) >= 3

    manifest = router.plan_stage2_keyframes(doc, job_dir=tmp_path / "repaired", qa_check_fn=pass_on_third)
    rec = manifest["shots"][0]
    assert rec["approval_status"] == "REPAIRED_2D"
    assert rec["repair_attempts"] == 2

    # Fails all 4 tries (initial + 3 repair retries) -> FLAGGED_HUMAN_REVIEW
    manifest_fail = router.plan_stage2_keyframes(doc, job_dir=tmp_path / "flagged", qa_check_fn=lambda *_: False)
    rec_fail = manifest_fail["shots"][0]
    assert rec_fail["approval_status"] == "FLAGGED_HUMAN_REVIEW"
    assert rec_fail["repair_attempts"] == 3


def test_local_comfyui_provider_is_free_in_imagegen_plan() -> None:
    p = plan.make(
        "B_LOCAL",
        "ep_waterloo_napoleon_victory",
        [{"id": "S04_SH001_start", "prompt": "Ink Chronicle start frame", "refs": []}],
        provider="local_comfyui",
        model="qwen_image_edit_2511",
        size="1280x720",
    )
    assert p["estimate_usd"] == 0.0
