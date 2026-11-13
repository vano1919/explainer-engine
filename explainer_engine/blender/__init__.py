"""The Blender render lanes of the Ink Chronicle (D-96, roadmap section 11): the pinned binary (``project``), the render profiles
(``profiles``), the headless adapter with the frame-recovery protocol of roadmap 10.4 (``render``) and the cost estimate from
measured rows (``cost``), the library assets of a shot with their import settings (``assets``) and the mouths and rig checks
(``rigs``: Rhubarb cues to shape-key tracks). Only ``bpy/render_shot.py`` imports ``bpy``; it runs inside Blender, never in this interpreter."""


# D-123 (2026-11-09): Mandatory 3D Blender scene-building and grease-pencil layout passes are deprecated and removed from default execution.
# Only `explainer_engine.blender.assemble_25d` is retained as an optional local deterministic 2.5D plane renderer alongside DepthFlow.
ACTIVE_25D_FALLBACK = "explainer_engine.blender.assemble_25d"
DEPRECATED_3D_BY_DEFAULT = True
DEPRECATED_3D_MODULES = (
    "assets",
    "benchmark_shots",
    "camera_setups",
    "character_benchmark",
    "characters",
    "cost",
    "crowd",
    "crowd_proof",
    "kit_pieces",
    "layout_passes",
    "pilot_envs",
    "pilot_stills",
    "profiles",
    "project",
    "render",
    "rigs",
    "scene_builder",
    "stoneage_qwen_jobs",
    "stoneage_test_layouts",
    "style_sheets",
    "turnaround",
    "world_kits",
)
