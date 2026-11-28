"""Modern Broadcast Documentary Design System (Typography, GSAP 3.13, MapLibre, Three.js, SVG Tokens).

Replaces legacy PIL rectangles and 1990s Linux bitmap/Liberation defaults with a curated,
100% open-license (SIL OFL / MIT / BSD / Apache 2.0) broadcast motion-design library matching
Netflix *Life on Our Planet*, BBC *Planet Earth*, Vox, and Johnny Harris aesthetics.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DS_FONTS_DIR = ROOT / "assets" / "design_system" / "fonts"
DS_VENDOR_DIR = ROOT / "assets" / "design_system" / "vendor"
FALLBACK_FONTS_DIR = ROOT / "assets" / "fonts"

FONT_REGISTRY: dict[str, dict[str, str]] = {
    "Cormorant Garamond": {
        "file": "CormorantGaramond-Regular.ttf",
        "italic_file": "CormorantGaramond-Italic.ttf",
        "role": "prestige_documentary_serif",
        "license": "SIL OFL 1.1",
    },
    "Cinzel": {
        "file": "Cinzel-Variable.ttf",
        "role": "epic_display_caps",
        "license": "SIL OFL 1.1",
    },
    "Plus Jakarta Sans": {
        "file": "PlusJakartaSans-Variable.ttf",
        "role": "modern_editorial_sans",
        "license": "SIL OFL 1.1",
    },
    "Space Grotesk": {
        "file": "SpaceGrotesk-Variable.ttf",
        "role": "geometric_display_sans",
        "license": "SIL OFL 1.1",
    },
    "IBM Plex Mono": {
        "file": "IBMPlexMono-Medium.ttf",
        "regular_file": "IBMPlexMono-Regular.ttf",
        "semibold_file": "IBMPlexMono-SemiBold.ttf",
        "role": "cartographic_telemetry_mono",
        "license": "SIL OFL 1.1",
    },
    "JetBrains Mono": {
        "file": "JetBrainsMono-Variable.ttf",
        "role": "data_counter_mono",
        "license": "SIL OFL 1.1",
    },
    "Oswald": {
        "file": "Oswald-Variable.ttf",
        "role": "youtube_thumbnail_impact",
        "license": "SIL OFL 1.1",
    },
    "Bebas Neue": {
        "file": "BebasNeue-Regular.ttf",
        "role": "bold_condensed_hook",
        "license": "SIL OFL 1.1",
    },
    "Inter": {
        "file": "Inter.ttf",
        "role": "clean_ui_sans",
        "license": "SIL OFL 1.1",
    },
}

PALEO_ICE_AGE_THEME: dict[str, Any] = {
    "name": "paleo_ice_age_life_on_our_planet",
    "bg_obsidian": "rgba(9, 13, 19, 0.72)",
    "bg_obsidian_deep": "rgba(6, 9, 14, 0.84)",
    "border_specular": "rgba(232, 240, 248, 0.22)",
    "accent_amber": "#E39B43",
    "accent_amber_glow": "rgba(227, 155, 67, 0.45)",
    "accent_glacial": "#7CC4E8",
    "accent_glacial_glow": "rgba(124, 196, 232, 0.42)",
    "accent_crimson": "#D4523B",
    "text_primary": "#F5F7FA",
    "text_secondary": "#C5D1DE",
    "text_muted": "#8FA1B5",
    "font_display": "'Cinzel', 'Cormorant Garamond', Georgia, serif",
    "font_editorial": "'Cormorant Garamond', Georgia, serif",
    "font_sans": "'Plus Jakarta Sans', 'Inter', system-ui, sans-serif",
    "font_mono": "'IBM Plex Mono', 'JetBrains Mono', monospace",
    "font_impact": "'Oswald', 'Bebas Neue', sans-serif",
}


def resolve_font_file(family: str, variant: str = "file") -> Path:
    """Resolve a curated SIL OFL font file on disk."""
    meta = FONT_REGISTRY.get(family)
    if not meta:
        raise FileNotFoundError(f"Unknown design system font family: {family!r}")
    fname = meta.get(variant) or meta["file"]
    for base in (DS_FONTS_DIR, FALLBACK_FONTS_DIR):
        p = base / fname
        if p.is_file():
            return p
    raise FileNotFoundError(f"Design system font missing on disk: {fname} (family={family})")


def resolve_vendor_js(filename: str) -> Path:
    """Resolve a locally vendored JS/CSS library (GSAP, MapLibre, Turf, Three, Lucide)."""
    p = DS_VENDOR_DIR / filename
    if not p.is_file():
        raise FileNotFoundError(f"Design system vendor asset missing: {p}")
    return p


def build_font_face_css(families: list[str] | None = None, *, embed_data_uri: bool = False) -> str:
    """Generate CSS ``@font-face`` rules for headless Chromium rendering."""
    chosen = families or list(FONT_REGISTRY.keys())
    blocks: list[str] = []
    for fam in chosen:
        meta = FONT_REGISTRY.get(fam)
        if not meta:
            continue
        for key, style_val, weight_val in (
            ("file", "normal", "100 900"),
            ("italic_file", "italic", "100 900"),
            ("regular_file", "normal", "400"),
            ("semibold_file", "normal", "600"),
        ):
            if key not in meta:
                continue
            try:
                fpath = resolve_font_file(fam, variant=key)
            except FileNotFoundError:
                continue
            if embed_data_uri:
                b64 = base64.b64encode(fpath.read_bytes()).decode("ascii")
                src = f"url('data:font/ttf;base64,{b64}') format('truetype')"
            else:
                src = f"url('{fpath.as_uri()}') format('truetype')"
            blocks.append(
                f"@font-face {{ font-family: '{fam}'; src: {src}; font-style: {style_val}; font-weight: {weight_val}; font-display: block; }}"
            )
    return "\n".join(blocks)


def verify_design_system_assets() -> dict[str, Any]:
    """Audit presence of all required modern typography and JS/WebGL libraries."""
    missing_fonts: list[str] = []
    present_fonts: list[str] = []
    for fam in FONT_REGISTRY:
        try:
            resolve_font_file(fam)
            present_fonts.append(fam)
        except FileNotFoundError:
            missing_fonts.append(fam)

    required_vendors = [
        "gsap.min.js",
        "SplitText.min.js",
        "DrawSVGPlugin.min.js",
        "CustomEase.min.js",
        "maplibre-gl.js",
        "maplibre-gl.css",
        "turf.min.js",
        "three.min.js",
        "lucide.min.js",
    ]
    missing_vendors = [v for v in required_vendors if not (DS_VENDOR_DIR / v).is_file()]
    return {
        "status": "PASS" if (not missing_fonts and not missing_vendors) else "FAIL",
        "present_fonts": present_fonts,
        "missing_fonts": missing_fonts,
        "missing_vendors": missing_vendors,
    }
