"""Planning stub: keyframe and shot-preview support for the Blender pipeline.

TODO [INK-CHRONICLE-PLANNING — NOT IMPLEMENTED]
Do not assume Qwen-Image-2.1 is the canonical final keyframe generator or carry forward the old
LoRA pin / next-pose / LTX frame-bucket requirements. Opus must decide whether this module remains
a separate keyframe planner, becomes a Blender preview/pose-planning adapter, or is removed after
dependency analysis. Blender scene state, reusable rig/animation assets and deterministic render
profiles must remain the source of final visual continuity.
See docs/architecture/INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04.md.
"""
from __future__ import annotations
