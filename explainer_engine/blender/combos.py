"""The overnight matrix's Q1 combinations (``combo_profiles.json``, schema combo_profiles/1): which WP-Q1 look and render
profile a combination uses, and the light preset an era brings. Pure data; ``style_sheets.spec_for`` makes the shot from it."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from explainer_engine.blender import style as S

PATH = Path(__file__).resolve().parent / "combo_profiles.json"
SCHEMA = "combo_profiles/1"
CHARACTERS = ("toon", "native")


def load(path: Path | None = None) -> dict:
    doc = json.loads(Path(path or PATH).read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"{path or PATH} is not a {SCHEMA} document")
    presets = S.light_presets()
    for era, e in doc["eras"].items():
        if e["light_preset"] not in presets:
            raise ValueError(f"era {era}: unknown light preset {e['light_preset']!r}")
    for cid, c in doc["combos"].items():
        t = S.look_tokens(c["look"])   # raises on an unknown look
        native = bool(t.art.native_classes)
        if c["characters"] not in CHARACTERS or native != (c["characters"] == "native"):
            raise ValueError(f"{cid}: characters {c['characters']!r} does not match look {c['look']} (native_classes {t.art.native_classes})")
        if t.art.pn_converge and not any(x["id"] == "perfectly_normal" for x in c.get("extensions", [])):
            raise ValueError(f"{cid}: Perfectly Normal faces without the extension's provenance row")
    if doc["default"] not in doc["combos"]:
        raise ValueError(f"default combination {doc['default']!r} is not listed")
    return doc


def tokens(cid: str, era: str, *, doc: dict | None = None) -> S.StyleTokens:
    """The combination's look tokens with the era's light preset (one world tint and one light per era)."""
    doc = doc or load()
    t = S.look_tokens(doc["combos"][cid]["look"])
    return replace(t, art=replace(t.art, light_preset=doc["eras"][era]["light_preset"]))
