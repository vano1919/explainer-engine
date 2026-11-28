"""Reverse-engineered commercial AI filmmaking studio orchestration."""
from explainer_engine.studio.elements_vault import ElementsVault, StudioElement
from explainer_engine.studio.popcorn_storyboard import build_popcorn_2x2_prompt, slice_and_upscale_2x2_sheet
from explainer_engine.studio.scenebuilder import (
    SceneShotCard,
    build_ltx25_multishot_prompt,
    plan_dramatic_scene_sequence,
)

__all__ = [
    "ElementsVault",
    "StudioElement",
    "build_popcorn_2x2_prompt",
    "slice_and_upscale_2x2_sheet",
    "SceneShotCard",
    "build_ltx25_multishot_prompt",
    "plan_dramatic_scene_sequence",
]
