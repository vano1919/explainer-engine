"""Load provisional quality option files from this directory."""

from __future__ import annotations

import json
import os
from pathlib import Path

_OPTIONS = ("strict", "medium", "light")
_DIR = Path(__file__).resolve().parent


def _check_option(option: str) -> str:
    if option not in _OPTIONS:
        raise ValueError(f"unknown quality option: {option!r}")
    return option


def load_thresholds(option: str) -> dict:
    """Read thresholds_<option>.json; raise ValueError for an unknown option."""
    option = _check_option(option)
    path = _DIR / f"thresholds_{option}.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def active_option() -> str:
    """Read QUALITY_OPTION, defaulting to "medium"; raise ValueError for an unknown value."""
    return _check_option(os.environ.get("QUALITY_OPTION", "medium"))


def load_presets() -> list[dict]:
    path = _DIR / "map_presets.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)["presets"]


def load_bridge_styles() -> list[dict]:
    path = _DIR / "bridge_styles.json"
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)["styles"]
