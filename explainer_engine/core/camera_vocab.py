"""Single source of truth for allowed camera movement vocabulary across production, maps, and delivery QA."""
from __future__ import annotations

from explainer_engine.core.errors import ContractError

ALLOWED_CAMERA_MOVES: tuple[str, ...] = (
    "truck",
    "zoom_in",
    "zoom_out",
    "truck_zoom_in",
    "truck_zoom_out",
)

FORBIDDEN_CAMERA_KEYS: tuple[str, ...] = (
    "bearing",
    "pitch",
    "rotation",
    "roll",
    "orbit",
)

_LEGACY_ALIASES: dict[str, str] = {
    "pan": "truck",
    "pan_crop_2d": "truck",
    "dolly_in": "zoom_in",
    "push": "zoom_in",
    "push_in": "zoom_in",
    "dolly_out": "zoom_out",
    "pull": "zoom_out",
    "pull_out": "zoom_out",
}


def validate_camera_move(move: str) -> str:
    """Validate that ``move`` is one of the 5 canonical camera operations."""
    if not isinstance(move, str) or move not in ALLOWED_CAMERA_MOVES:
        raise ContractError(
            f"Unsupported camera move {move!r}; must be one of {ALLOWED_CAMERA_MOVES}"
        )
    return move


def normalize_camera_move(move: str) -> str:
    """Map legacy editorial aliases into the 5 canonical camera operations, failing on unknown values."""
    if not isinstance(move, str):
        raise ContractError(f"Camera move must be a string, got {type(move).__name__}")
    key = move.strip().lower()
    if key in ALLOWED_CAMERA_MOVES:
        return key
    if key in _LEGACY_ALIASES:
        return _LEGACY_ALIASES[key]
    raise ContractError(
        f"Unsupported camera move {move!r}; must be one of {ALLOWED_CAMERA_MOVES}"
    )
