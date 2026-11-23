"""Access to the map render presets and bridge styles used by map quality options."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

_QUALITY_DIR = Path(__file__).resolve().parent / "quality_options"
_MAP_PRESETS_PATH = _QUALITY_DIR / "map_presets.json"
_BRIDGE_STYLES_PATH = _QUALITY_DIR / "bridge_styles.json"
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

_LINE_PCT_KEYS = {"primary": "primary_line_pct", "secondary": "secondary_line_pct"}


def _load_list(path: Path, key: str) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data[key]


def get_map_preset(name: str) -> dict:
    """Return the map preset called ``name`` or raise ValueError if it is unknown."""
    for preset in _load_list(_MAP_PRESETS_PATH, "presets"):
        if preset["name"] == name:
            return preset
    raise ValueError(f"Unknown map preset: {name!r}")


def get_bridge_style(name: str) -> dict:
    """Return the bridge style called ``name`` or raise ValueError if it is unknown."""
    for style in _load_list(_BRIDGE_STYLES_PATH, "styles"):
        if style["name"] == name:
            return style
    raise ValueError(f"Unknown bridge style: {name!r}")


def active_map_preset() -> dict:
    """Return the preset selected by MAP_PRESET (defaulting to ``balanced``)."""
    return get_map_preset(os.environ.get("MAP_PRESET", "balanced"))


def line_px(preset: dict, frame_height_px: int, kind: str) -> float:
    """Line width in pixels for ``kind`` ("primary" or "secondary") at the given frame height."""
    if frame_height_px <= 0:
        raise ValueError(f"frame_height_px must be positive, got {frame_height_px!r}")
    if kind not in _LINE_PCT_KEYS:
        raise ValueError(f"Unknown line kind: {kind!r}")
    return preset[_LINE_PCT_KEYS[kind]] / 100.0 * frame_height_px


def label_px(preset: dict, frame_height_px: int) -> float:
    """Label cap height in pixels at the given frame height."""
    return preset["label_cap_pct"] / 100.0 * frame_height_px


def colours(preset: dict) -> tuple[str, str]:
    """Return the (label_fill, label_halo) hex colour pair for ``preset``."""
    fill = preset["label_fill"]
    halo = preset["label_halo"]
    for value in (fill, halo):
        if not isinstance(value, str) or not _HEX_RE.match(value):
            raise ValueError(f"Invalid hex colour: {value!r}")
    return fill, halo


def _scales() -> tuple[float, float]:
    """(line, label) multipliers relative to the balanced preset; (1.0, 1.0) when MAP_PRESET is unset, so renders are unchanged."""
    import os
    if os.environ.get("MAP_PRESET") in (None, ""):
        return 1.0, 1.0
    base = get_map_preset("balanced")
    chosen = active_map_preset()
    return chosen["primary_line_pct"] / base["primary_line_pct"], chosen["label_cap_pct"] / base["label_cap_pct"]


def line_scale() -> float:
    """Width multiplier for map lines (1.0 unless MAP_PRESET is set)."""
    return _scales()[0]


def label_scale() -> float:
    """Text size multiplier for map labels (1.0 unless MAP_PRESET is set)."""
    return _scales()[1]
