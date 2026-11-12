"""Model Lifecycle & Deprecation Guard (D-130).

Blocks retired or shut-down Google Gemini / Imagen / Veo and legacy Qwen endpoints
before any paid API request or worker job is launched, and provides canonical active
model identifiers verified against official vendor lifecycle documentation.
"""
from __future__ import annotations

from typing import Dict, Tuple


class RetiredModelBlockedError(RuntimeError):
    """Raised when code attempts to invoke a retired or shut-down model endpoint."""


# Officially retired / shut-down models that must NEVER be invoked at runtime
RETIRED_MODELS_REGISTRY: Dict[str, Dict[str, str]] = {
    "imagen-3.0-generate-002": {
        "shutdown_date": "2025-11-10",
        "replacement": "gemini-3-pro-image",
        "reason": "Shut down per Google AI Studio Deprecations (2025-11-10).",
    },
    "imagen-3.0-generate-001": {
        "shutdown_date": "2025-11-10",
        "replacement": "gemini-3-pro-image",
        "reason": "Shut down per Google AI Studio Deprecations (2025-11-10).",
    },
    "imagen-4.0-generate-001": {
        "shutdown_date": "2026-08-17",
        "replacement": "gemini-3-pro-image",
        "reason": "Shut down per Google AI Studio Imagen Docs (2026-08-17).",
    },
    "imagen-4.0-ultra-generate-001": {
        "shutdown_date": "2026-08-17",
        "replacement": "gemini-3-pro-image",
        "reason": "Shut down per Google AI Studio Imagen Docs (2026-08-17).",
    },
    "imagen-4.0-fast-generate-001": {
        "shutdown_date": "2026-08-17",
        "replacement": "gemini-3.1-flash-image",
        "reason": "Shut down per Google AI Studio Imagen Docs (2026-08-17).",
    },
    "gemini-2.0-flash-preview-image-generation": {
        "shutdown_date": "2025-11-14",
        "replacement": "gemini-3.1-flash-image",
        "reason": "Shut down per Google AI Studio Deprecations (2025-11-14).",
    },
    "gemini-3-pro-image-preview": {
        "shutdown_date": "2026-06-25",
        "replacement": "gemini-3-pro-image",
        "reason": "Preview shut down (2026-06-25); use GA model gemini-3-pro-image.",
    },
    "gemini-3.1-flash-image-preview": {
        "shutdown_date": "2026-06-25",
        "replacement": "gemini-3.1-flash-image",
        "reason": "Preview shut down (2026-06-25); use GA model gemini-3.1-flash-image.",
    },
    "veo-2.0-generate-001": {
        "shutdown_date": "2026-06-30",
        "replacement": "gemini-omni-1.2-flash",
        "reason": "Shut down per Google Gemini API Veo 2.0 Docs (2026-06-30).",
    },
    "veo-3.1-generate-preview": {
        "shutdown_date": "2026-10-22",
        "replacement": "gemini-omni-1.2-flash",
        "reason": "Shut down per Google Gemini API Veo 3.1 Docs (2026-10-22).",
    },
    "veo-3.1-fast-generate-preview": {
        "shutdown_date": "2026-10-22",
        "replacement": "gemini-omni-1.2-flash",
        "reason": "Shut down per Google Gemini API Veo 3.1 Docs (2026-10-22).",
    },
    "veo-3.1-lite-generate-preview": {
        "shutdown_date": "2026-10-22",
        "replacement": "gemini-omni-1.2-flash",
        "reason": "Shut down per Google Gemini API Veo 3.1 Docs (2026-10-22).",
    },
    "Qwen/Qwen-Image-2512": {
        "shutdown_date": "2026-10-26",
        "replacement": "gemini-3-pro-image",
        "reason": "Retired in repo (KG-16 / D-124).",
    },
    "fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA": {
        "shutdown_date": "2026-11-05",
        "replacement": "gemini-3-pro-image",
        "reason": "Retired in repo (D-96 / D-124).",
    },
}

# Active canonical models for Explainer Engine v4.2
ACTIVE_CANONICAL_MODELS: Dict[str, str] = {
    "g1_g2_reasoning_argon": "gemini-4-argon",
    "g2_viewer_critic": "gemini-4-argon",
    "g3_g4_compiler_flash": "gemini-3.8-flash",
    "g5_keyframe_primary": "gemini-3-pro-image",
    "g5_keyframe_banana": "gemini-nano-banana-2.1",
    "g5_keyframe_fast": "gemini-3.1-flash-image",
    "g6_narrator_tts": "eleven_v4",
    "g6_narrator_tts_fallback": "eleven_multilingual_v2",
    "g7_google_video_api": "gemini-omni-1.2-flash",
    "g7_wan_i2v_api": "fal-ai/wan-i2v",
    "g7_wan_flf2v_api": "fal-ai/wan-flf2v",
}

ALLOWED_ACTIVE_MODEL_IDS: Tuple[str, ...] = (
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-pro-image",
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-2.5-flash-image",
    "gemini-omni-1.2-flash",
    "eleven_v4",
    "eleven_multilingual_v2",
    "eleven_text_to_sound_v2",
    "eleven_music_v2_5",
    "fal-ai/wan-i2v",
    "fal-ai/wan-flf2v",
    "wan2.2_i2v_14b_fp8.safetensors",
    "wan2.2_flf2v_14b_fp8.safetensors",
    "wan2.2_fun_control_14b_fp8.safetensors",
)


def assert_active_model(model_id: str) -> str:
    """Validate that `model_id` is not retired or shut down. Returns `model_id` if active."""
    cleaned = str(model_id or "").strip()
    if not cleaned:
        raise RetiredModelBlockedError("Empty model_id passed to assert_active_model().")
    if cleaned in RETIRED_MODELS_REGISTRY:
        info = RETIRED_MODELS_REGISTRY[cleaned]
        raise RetiredModelBlockedError(
            f"BLOCKED RETIRED MODEL {cleaned!r} (shut down {info['shutdown_date']}): "
            f"{info['reason']} Use active replacement {info['replacement']!r}."
        )
    return cleaned


def resolve_or_migrate_model(model_id: str) -> str:
    """Return active replacement if `model_id` is in `RETIRED_MODELS_REGISTRY`, else validate and return."""
    cleaned = str(model_id or "").strip()
    if cleaned in RETIRED_MODELS_REGISTRY:
        return RETIRED_MODELS_REGISTRY[cleaned]["replacement"]
    return assert_active_model(cleaned)
