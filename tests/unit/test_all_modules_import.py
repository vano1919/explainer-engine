"""Dynamic import smoke test ensuring every active Python module under explainer_engine/ imports cleanly."""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG_ROOT = REPO_ROOT / "explainer_engine"

# Optional third-party packages that may not be installed in a minimal CPU environment.
# Internal explainer_engine.* imports are NEVER allowed to be missing.
OPTIONAL_THIRD_PARTY = frozenset(
    {
        "anthropic",
        "bmesh",
        "bpy",
        "cv2",
        "diffusers",
        "fal_client",
        "faster_whisper",
        "huggingface_hub",
        "imagehash",
        "kokoro_onnx",
        "modal",
        "onnxruntime",
        "playwright",
        "runpod",
        "scenedetect",
        "scipy",
        "skimage",
        "soundfile",
        "torch",
        "transformers",
    }
)

# Modules intentionally retired (raising SystemExit("RETIRED...")) or standalone CLI scripts
# that execute side effects at module top-level rather than serving as importable libraries.
EXPLICITLY_EXCLUDED_MODULES = frozenset(
    {
        "explainer_engine.aivideo.pod.fixhub",
        "explainer_engine.aivideo.pod.launch",
        "explainer_engine.aivideo.pod.launch_clips",
        "explainer_engine.aivideo.pod.montage",
        "explainer_engine.aivideo.pod.watchdog",
        "explainer_engine.blender.j5_minute_ambience",
        "explainer_engine.blender.j5_minute_post",
        "explainer_engine.training.pods.p15.sa_test_qwen",
    }
)


def _discover_modules() -> list[str]:
    mods: list[str] = []
    for py in sorted(PKG_ROOT.rglob("*.py")):
        if "__pycache__" in py.parts or py.name == "__main__.py":
            continue
        rel = py.relative_to(REPO_ROOT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        mod_name = ".".join(parts)
        if mod_name and mod_name not in EXPLICITLY_EXCLUDED_MODULES:
            mods.append(mod_name)
    return mods


@pytest.mark.parametrize("module_name", _discover_modules())
def test_module_imports_cleanly(module_name: str):
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        top = (exc.name or "").split(".", 1)[0]
        if top in OPTIONAL_THIRD_PARTY:
            pytest.skip(f"Optional third-party dependency {top!r} not installed in this environment")
        raise
