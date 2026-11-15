"""Cartographic style rules, thresholds, and theater reference cities for map rendering (S9, D-59)."""
from __future__ import annotations

SAFE_MARGIN_MIN_FRAC = 0.04
SAFE_MARGIN_X_FRAC = 0.045
SAFE_MARGIN_TOP_FRAC = 0.050
SAFE_MARGIN_BOTTOM_FRAC = 66.0 / 1080.0

HUD_CARD_X_FRAC = 0.048
HUD_CARD_Y_FRAC = 0.068

MAX_LABELS_PER_FRAME = 6
MACRO_LABEL_MIN_SPAN_KM = 220.0

MICRO_RELIEF_UPSAMPLE_MIN = 3.0
RASTER_KM_PER_PX = 111.32 / 60.0

CARRY_OVER_GHOST_ALPHA = 0.22

SECTOR_WIDTH_MIN_FRAC = 0.06
SECTOR_WIDTH_MAX_FRAC = 0.14
HIGHLIGHT_AREA_MAX_FRAC = 0.03
DEFAULT_HIGHLIGHT_KM = 8.0
DEFAULT_PULSE_KM = 6.0

BORDER_1914_MAX_PX_1080 = 2.0
BORDER_1914_DASH_ON = 5.0
BORDER_1914_DASH_OFF = 3.5

# Key reference cities per historical theater for macro views (sorted by priority 1..N)
THEATER_REFERENCE_CITIES: dict[str, dict] = {
    "western_front": {
        "bbox": (-2.0, 46.0, 10.5, 53.0),
        "cities": [
            {"id": "paris", "name": "Paris", "lon": 2.35, "lat": 48.86, "prefer": "W", "priority": 1},
            {"id": "brussels", "name": "Brussels", "lon": 4.35, "lat": 50.85, "prefer": "NW", "priority": 2},
            {"id": "aachen", "name": "Aachen", "lon": 6.08, "lat": 50.78, "prefer": "E", "priority": 3},
            {"id": "ypres", "name": "Ypres", "lon": 2.885, "lat": 50.851, "prefer": "W", "priority": 4},
            {"id": "liege", "name": "Liège", "lon": 5.57, "lat": 50.63, "prefer": "SE", "priority": 5},
            {"id": "verdun", "name": "Verdun", "lon": 5.38, "lat": 49.16, "prefer": "E", "priority": 6},
        ],
    },
}

NARRATION_PLACE_ALIASES: dict[str, str] = {
    "north sea": "nieuport",
    "switzerland": "swiss_border",
    "swiss": "swiss_border",
    "marne": "marne",
}

PLACE_LABEL_PREFER: dict[str, str] = {
    "paris": "W",
    "brussels": "NW",
    "aachen": "E",
    "liege": "SE",
    "marne": "SE",
    "nieuport": "E",
    "swiss_border": "E",
    "verdun": "E",
    "ypres": "E",
    "wulverghem": "W",
    "ploegsteert": "W",
    "frelinghien": "E",
    "armentieres": "SE",
    "fleurbaix": "W",
    "la_bassee": "E",
}
