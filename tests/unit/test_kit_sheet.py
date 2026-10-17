"""Kit's reference sheet (assets/characters/kit/kit_reference.svg): parts exist and only palette colours are used."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from explainer_engine.design import palette

SHEET = Path(__file__).resolve().parents[2] / "assets" / "characters" / "kit" / "kit_reference.svg"
EXPRESSIONS = ("neutral", "curious", "surprised", "smug", "confused", "delighted", "worried", "deadpan")
MOUTHS = ("rest", "mbp", "wide", "mid", "round", "fv")


def _ids() -> set[str]:
    return {el.get("id") for el in ET.parse(SHEET).iter() if el.get("id")}


def test_required_parts_exist():
    ids = _ids()
    required = {"kit_body", "kit_limbs", "lid_closed", "lid_open"}
    required |= {f"expr_{e}" for e in EXPRESSIONS} | {f"mouth_{m}" for m in MOUTHS}
    assert required <= ids, sorted(required - ids)


def test_every_colour_is_a_palette_token():
    tokens = {t["hex"].lower() for t in palette.load()["tokens"].values()}
    used = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", SHEET.read_text(encoding="utf-8"))}
    assert used <= tokens, sorted(used - tokens)


def test_every_use_points_at_a_defined_id():
    root = ET.parse(SHEET).getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    refs = {el.get("href", "")[1:] for el in root.iter() if el.tag.endswith("use")}
    assert refs <= ids, sorted(refs - ids)


def test_stroke_widths_follow_the_style_rule():
    css = SHEET.read_text(encoding="utf-8")
    assert "stroke-width:6" in css and "stroke-width:4" in css  # characters 6 px, props 4 px (style bible)
    assert "stroke-linecap:round" in css
