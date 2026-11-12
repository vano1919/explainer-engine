"""Unit tests for TODO-02: local-only mode, ComfyUI URL/path getters, .env safety, and model registries."""

from __future__ import annotations

import json
from pathlib import Path

from explainer_engine import governance, vault

ROOT = Path(__file__).resolve().parents[2]


def test_is_local_only_defaults_to_true_and_parses_overrides() -> None:
    assert vault.is_local_only({}) is True
    assert vault.is_local_only({"EXPLAINER_LOCAL_ONLY": "1"}) is True
    assert vault.is_local_only({"EXPLAINER_LOCAL_ONLY": "true"}) is True
    assert vault.is_local_only({"EXPLAINER_LOCAL_ONLY": "0"}) is False
    assert vault.is_local_only({"EXPLAINER_LOCAL_ONLY": "false"}) is False


def test_comfyui_url_defaults_to_localhost_and_blocks_remote_urls() -> None:
    assert vault.get_comfyui_url({}) == "http://127.0.0.1:8188"
    assert vault.get_comfyui_url({"COMFY_SERVER_ADDRESS": "localhost:8189"}) == "http://localhost:8189"
    assert vault.get_comfyui_url({"COMFYUI_API_ENDPOINT": "http://127.0.0.1:8188/"}) == "http://127.0.0.1:8188"

    for blocked_url in (
        "https://api.ltx-cloud.internal/v1/jobs",
        "https://qwen-api.internal/v2/generate",
        "https://cloud-run.internal/preflight/verify",
        "https://api.runpod.io/v2/endpoint",
        "https://fal.run/fal-ai/wan",
    ):
        try:
            vault.get_comfyui_url({"COMFYUI_API_ENDPOINT": blocked_url, "EXPLAINER_LOCAL_ONLY": "1"})
        except vault.VaultError as exc:
            assert "EXPLAINER_LOCAL_ONLY=1 blocks non-localhost endpoint" in str(exc)
        else:
            raise AssertionError(f"Expected VaultError for non-localhost URL {blocked_url}")

    # Opt-in cloud override allows remote URL when EXPLAINER_LOCAL_ONLY=0
    assert (
        vault.get_comfyui_url({"COMFYUI_API_ENDPOINT": "https://example.com/comfy", "EXPLAINER_LOCAL_ONLY": "0"})
        == "https://example.com/comfy"
    )


def test_load_dotenv_keys_never_exposes_secret_values(tmp_path: Path) -> None:
    secret_value = "hf_SUPER_SECRET_DO_NOT_LEAK_999"
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        f"HF_TOKEN={secret_value}\n"
        "EXPLAINER_LOCAL_ONLY=1\n"
        "COMFY_SERVER_ADDRESS=127.0.0.1:8188\n"
        "EMPTY_VAR=\n",
        encoding="utf-8",
    )
    key_map = vault.load_dotenv_keys(dotenv_file, env={})
    assert key_map["HF_TOKEN"] is True
    assert key_map["EXPLAINER_LOCAL_ONLY"] is True
    assert key_map["COMFY_SERVER_ADDRESS"] is True
    assert key_map["COMFY_API_KEY"] is False
    serialized = json.dumps(key_map)
    assert secret_value not in serialized
    assert all(isinstance(v, bool) for v in key_map.values())


def test_local_models_and_model_routing_configs_have_zero_cloud_endpoints() -> None:
    local_cfg = vault.local_models_config()
    assert local_cfg["local_only_default"] is True
    assert local_cfg["comfyui"]["default_url"] == "http://127.0.0.1:8188"
    assert local_cfg["active_defaults"]["stage3_video_inp_model"] == "wan22_fun_5b_inp"
    assert local_cfg["active_defaults"]["stage3_video_control_model"] == "wan22_fun_5b_control"
    assert local_cfg["active_defaults"]["stage3_parallax_engine"] == "depthflow_local_25d"

    for model_id, entry in local_cfg["models"].items():
        assert entry["licence_status"] in ("commercial_ok", "verify_card", "non_commercial_research"), model_id

    routing_text = (ROOT / "config" / "model_routing.json").read_text(encoding="utf-8")
    for banned_host in ("ltx-cloud.internal", "qwen-api.internal", "cloud-run.internal"):
        assert banned_host not in routing_text

    routing_cfg = governance.load(ROOT)
    assert routing_cfg["local_media_routing"]["local_only_default"] is True
    assert routing_cfg["local_media_routing"]["default_provider"] == "local_comfyui"
