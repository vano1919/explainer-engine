"""Local ComfyUI & Model Readiness Preflight (D-123, docs/LOCAL_COMFYUI_SETUP.md).

Replaces ``paid_preflight.py`` as the default preflight check:
- Enforces ``EXPLAINER_LOCAL_ONLY=1`` by default (zero paid cloud spend calls).
- Inspects ``.env`` variable names safely via ``vault.load_dotenv_keys()`` without printing or logging secret values.
- Checks local ComfyUI reachability (``GET /system_stats`` and ``GET /object_info``) when ``live=True``.
- Verifies required ComfyUI nodes and workflow JSON templates in ``config/local_models.json``.
- Audits model ``licence_status`` (emitting warnings if ``non_commercial_research`` or ``verify_card`` weights are
  selected for commercial runs).
- Verifies Stage 2 keyframe approval (``keyframe_manifest.json``) and 1-or-2 keyframe conformance before Stage 3.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

import jsonschema

from explainer_engine import vault

ROOT = Path(__file__).resolve().parents[2]
KEYFRAME_SCHEMA_PATH = ROOT / "explainer_engine" / "schemas" / "keyframe_manifest.schema.json"


def _fetch_json(url: str, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def check_local_environment(
    *,
    config_path: Path | str = vault.LOCAL_MODELS_CONFIG,
    env: Mapping[str, str] | None = None,
    live: bool = False,
    commercial_publish: bool = False,
    http_get: Callable[[str], dict] | None = None,
    require_weights_on_disk: bool = False,
) -> dict:
    """Validate local-only configuration, workflow templates, licence statuses, and optional live ComfyUI server."""
    problems: list[str] = []
    warnings: list[str] = []

    local_only = vault.is_local_only(env)
    if not local_only:
        warnings.append("EXPLAINER_LOCAL_ONLY is disabled (0); default pipeline expects EXPLAINER_LOCAL_ONLY=1")

    try:
        comfy_url = vault.get_comfyui_url(env)
    except vault.VaultError as exc:
        problems.append(str(exc))
        comfy_url = ""

    dotenv_keys = vault.load_dotenv_keys(env=env)
    cfg = vault.local_models_config(config_path)
    models_dir = vault.get_comfyui_models_dir(env)

    # 1. Verify workflow templates exist on disk
    active = cfg.get("active_defaults", {})
    models = cfg.get("models", {})
    for role, model_id in active.items():
        if model_id not in models:
            problems.append(f"active_defaults.{role} references unknown model {model_id!r}")
            continue
        entry = models[model_id]
        wf_rel = entry.get("workflow_json")
        if wf_rel and not (ROOT / wf_rel).exists():
            problems.append(f"Missing workflow template {wf_rel} for {model_id}")

        # Licence check
        lic_status = entry.get("licence_status", "unknown")
        if lic_status == "non_commercial_research":
            msg = f"Model {model_id} has licence_status='non_commercial_research' ({entry.get('licence')})"
            if commercial_publish:
                problems.append(f"COMMERCIAL BLOCK: {msg}")
            else:
                warnings.append(msg)
        elif lic_status == "verify_card":
            warnings.append(f"Model {model_id} has licence_status='verify_card' ({entry.get('licence')}); verify card before commercial redistribution")

        # Optional local weight file check
        if require_weights_on_disk:
            ckpt = entry.get("checkpoint_file")
            if ckpt and not (models_dir / ckpt).exists():
                problems.append(f"Missing local checkpoint file: {models_dir / ckpt}")
            for ckpt_item in entry.get("checkpoint_files", []):
                if not (models_dir / ckpt_item).exists():
                    problems.append(f"Missing local checkpoint file: {models_dir / ckpt_item}")

    # 2. Live ComfyUI endpoint & custom node check (when live=True or http_get is injected)
    comfy_stats = None
    missing_required_nodes: list[str] = []
    missing_optional_nodes: list[str] = []
    if (live or http_get is not None) and comfy_url:
        getter = http_get or _fetch_json
        try:
            comfy_stats = getter(f"{comfy_url}/system_stats")
            obj_info = getter(f"{comfy_url}/object_info")
            req_nodes = cfg.get("comfyui", {}).get("required_nodes", [])
            opt_nodes = cfg.get("comfyui", {}).get("optional_nodes", [])
            for node_name in req_nodes:
                if node_name not in obj_info:
                    missing_required_nodes.append(node_name)
                    problems.append(f"Missing required ComfyUI node: {node_name}")
            for node_name in opt_nodes:
                if node_name not in obj_info:
                    missing_optional_nodes.append(node_name)
                    warnings.append(f"Optional ComfyUI node {node_name} not found; Python fallback will be used if needed")
        except (OSError, urllib.error.URLError, ValueError) as exc:
            problems.append(f"Local ComfyUI unreachable at {comfy_url}: {exc}")

    return {
        "ok": len(problems) == 0,
        "local_only": local_only,
        "comfy_local_url": comfy_url,
        "models_dir": str(models_dir),
        "env_keys_present": dotenv_keys,
        "active_defaults": active,
        "comfy_system_stats": comfy_stats,
        "missing_required_nodes": missing_required_nodes,
        "missing_optional_nodes": missing_optional_nodes,
        "warnings": warnings,
        "problems": problems,
    }


def check_keyframe_manifest(manifest_or_path: dict | Path | str) -> list[str]:
    """Verify Stage 2 keyframe_manifest.json conformance (1-or-2 keyframes, all approved) before Stage 3."""
    doc = (
        json.loads(Path(manifest_or_path).read_text(encoding="utf-8"))
        if isinstance(manifest_or_path, (Path, str))
        else manifest_or_path
    )
    schema = json.loads(KEYFRAME_SCHEMA_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        problems.append(f"Schema validation failed: {exc.message}")
        return problems

    for shot in doc.get("shots", []):
        sid = shot["shot_id"]
        mode = shot["generation_mode"]
        status = shot["approval_status"]
        if status not in ("KEYFRAME_APPROVED", "REPAIRED_2D"):
            problems.append(f"{sid}: keyframe not approved (status={status!r})")
        if mode == "WAN_FLF2V" and not shot.get("end_frame_path"):
            problems.append(f"{sid}: WAN_FLF2V shot is missing end_frame_path")
        if mode != "WAN_FLF2V" and shot.get("end_frame_path") is not None:
            problems.append(f"{sid}: {mode} shot must not specify end_frame_path")
    return problems
