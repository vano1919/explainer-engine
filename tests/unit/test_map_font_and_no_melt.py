import json
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STYLES_DIR = _REPO_ROOT / "explainer_engine" / "maps" / "maplibre_lane" / "styles"
_DRAW_PY = _REPO_ROOT / "explainer_engine" / "maps" / "draw.py"
_LIBERATION_FONT = Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")


def _first_family(font) -> str:
    if isinstance(font, (list, tuple)):
        font = font[0] if font else ""
    if not isinstance(font, str):
        return ""
    return font.split(",")[0].strip().strip("'\"")


def _iter_font_values(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "font":
                yield value
            yield from _iter_font_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_font_values(item)


def test_map_styles_use_liberation_serif_first_family():
    # "neutral" is the generic, non-film style (Inter, no film preset). The owner rule covers the film presets only.
    style_files = sorted(p for p in _STYLES_DIR.glob("*.json") if p.stem != "neutral")
    assert style_files, f"no style JSON files found in {_STYLES_DIR}"
    for path in style_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        fonts = list(_iter_font_values(data))
        assert fonts, f"{path.name} has no 'font' value"
        assert _first_family(fonts[0]) == "Liberation Serif", path.name


def test_liberation_serif_font_installed():
    if not _LIBERATION_FONT.exists():
        pytest.skip("LiberationSerif-Regular.ttf is not installed on this machine")
    assert _LIBERATION_FONT.is_file()


def _map_font_expression(text: str) -> str:
    match = re.search(r"^\s*MAP_FONT\b[^\n=]*=\s*(.+)$", text, re.MULTILINE)
    assert match is not None, "MAP_FONT assignment not found in maps/draw.py"
    return match.group(1)


@pytest.mark.xfail(
    strict=True,
    reason="raster map renderer maps/draw.py uses assets/fonts/Inter.ttf (MAP_FONT); the owner's Liberation Serif rule is not yet applied there",
)
def test_draw_py_uses_liberation_serif_font():
    text = _DRAW_PY.read_text(encoding="utf-8")
    expression = _map_font_expression(text)
    assert "LiberationSerif" in expression or "Liberation" in expression
