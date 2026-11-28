"""3D Scene Pre-Visualization & Multi-Angle Set Blocking (Headless Blender Python)."""
from explainer_engine.scene3d.blender_set_blocker import (
    ROMAN_SET_PRESETS,
    CameraAngleSpec,
    build_blender_set_script,
    plan_set_cameras,
    render_blender_set_angles,
    validate_set_rig_manifest,
)

__all__ = [
    "ROMAN_SET_PRESETS",
    "CameraAngleSpec",
    "build_blender_set_script",
    "plan_set_cameras",
    "render_blender_set_angles",
    "validate_set_rig_manifest",
]
