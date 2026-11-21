"""Unit tests for TODO-12: local_preflight.py and paid_preflight.py gating."""

from __future__ import annotations

from pathlib import Path

from explainer_engine.imagegen import routing
from explainer_engine.production import local_preflight, paid_preflight
from tests.unit.test_schemas_v4 import _sample_v4_production_script


def test_local_preflight_verifies_nodes_workflows_and_licences() -> None:
    fake_object_info = {
        "WanFunInpaintToVideo": {},
        "WanImageToVideo": {},
        "Wan22FunControlToVideo": {},
        "TextEncodeQwenImageEditPlus": {},
        "QwenMultiangleCameraNode": {},
        "DepthflowPresetDolly": {},
    }

    def fake_http_get(url: str) -> dict:
        if url.endswith("/system_stats"):
            return {"system": {"comfyui_version": "0.3.10"}}
        if url.endswith("/object_info"):
            return fake_object_info
        raise AssertionError(f"Unexpected URL {url}")

    rep = local_preflight.check_local_environment(live=True, http_get=fake_http_get)
    assert rep["ok"] is True
    assert rep["local_only"] is True
    assert rep["comfy_local_url"] == "http://127.0.0.1:8188"
    assert rep["missing_required_nodes"] == []
    assert any("verify_card" in w for w in rep["warnings"])


def test_local_preflight_detects_missing_required_comfy_node() -> None:
    def fake_http_get(url: str) -> dict:
        if url.endswith("/system_stats"):
            return {"system": {"comfyui_version": "0.3.10"}}
        return {"WanImageToVideo": {}}  # Missing WanFunInpaintToVideo etc.

    rep = local_preflight.check_local_environment(live=True, http_get=fake_http_get)
    assert rep["ok"] is False
    assert "WanFunInpaintToVideo" in rep["missing_required_nodes"]


def test_local_preflight_validates_keyframe_manifest(tmp_path: Path) -> None:
    doc = _sample_v4_production_script()
    router = routing.ShotRouter()
    manifest = router.plan_stage2_keyframes(doc, job_dir=tmp_path)
    assert local_preflight.check_keyframe_manifest(manifest) == []

    manifest["shots"][0]["approval_status"] = "FLAGGED_HUMAN_REVIEW"
    problems = local_preflight.check_keyframe_manifest(manifest)
    assert any("not approved" in p for p in problems)


def test_paid_preflight_is_blocked_by_default_unless_allow_paid_cloud() -> None:
    try:
        paid_preflight.check_cloud_allowed(allow_paid_cloud=False, env={"EXPLAINER_LOCAL_ONLY": "1"})
    except SystemExit as exc:
        assert "DEPRECATED / BLOCKED BY DEFAULT" in str(exc)
    else:
        raise AssertionError("Expected SystemExit when paid_preflight runs without --allow-paid-cloud")

    # Explicitly passing allow_paid_cloud=True succeeds
    paid_preflight.check_cloud_allowed(allow_paid_cloud=True, env={"EXPLAINER_LOCAL_ONLY": "1"})
