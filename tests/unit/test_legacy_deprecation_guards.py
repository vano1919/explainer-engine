"""Unit tests for TODO-14: Legacy 3D Blender module deprecation and manual-only CI workflows."""

from __future__ import annotations

from pathlib import Path

import yaml

from explainer_engine import blender

ROOT = Path(__file__).resolve().parents[2]


def test_blender_3d_modules_marked_deprecated_and_assemble_25d_kept() -> None:
    assert blender.DEPRECATED_3D_BY_DEFAULT is True
    assert blender.ACTIVE_25D_FALLBACK == "explainer_engine.blender.assemble_25d"
    assert "scene_builder" in blender.DEPRECATED_3D_MODULES
    assert "layout_passes" in blender.DEPRECATED_3D_MODULES
    assert "world_kits" in blender.DEPRECATED_3D_MODULES
    assert "assemble_25d" not in blender.DEPRECATED_3D_MODULES
    assert (ROOT / "explainer_engine" / "blender" / "assemble_25d.py").exists()


def test_legacy_blender_ci_workflows_are_manual_workflow_dispatch_only() -> None:
    for wf_name in ("blender-smoke.yml", "crowd-proof.yml", "world-kits.yml"):
        wf_path = ROOT / ".github" / "workflows" / wf_name
        raw = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        # PyYAML parses `on:` key as boolean True or string "on"
        on_block = raw.get("on") if "on" in raw else raw.get(True)
        assert isinstance(on_block, dict), f"{wf_name} on: block should be a dict"
        assert set(on_block.keys()) == {"workflow_dispatch"}, (
            f"{wf_name} must only trigger on manual workflow_dispatch, got {list(on_block.keys())}"
        )
