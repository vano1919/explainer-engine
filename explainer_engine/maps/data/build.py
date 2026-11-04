# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/maps/data/build.py`
# Target Module : explainer_engine/maps/data/build.py
# Target Classes/Symbols : def _ring(), def _polygons(), def _lines(), def extract(), def build(), def main()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""Build ``ne50m.json.gz``, the one vector source of every map (Natural Earth 1:50m, public domain, naturalearthdata.com).

The extract keeps four layers (land, lakes, rivers, land borders) and no names: a plate has no letters (CMP-01). Coordinates
are rounded to 2 decimals (~1 km), which is finer than a 50 m view needs. The source files are pinned by sha256 in
``SOURCES.json``; a changed upstream file stops the build instead of changing every plate silently.

    python -m explainer_engine.maps.data.build [--from-dir <folder with the 4 geojson files>] [--check]
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from explainer_engine.core.store import replace_file, write_text_atomic

HERE = Path(__file__).resolve().parent
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
LAYERS = {  # layer -> (source file, geometry kind)
    "land": ("ne_50m_land", "polygon"),
    "lakes": ("ne_50m_lakes", "polygon"),
    "rivers": ("ne_50m_rivers_lake_centerlines", "line"),
    "borders": ("ne_50m_admin_0_boundary_lines_land", "line"),
}
DECIMALS = 2
OUT = HERE / "ne50m.json.gz"
SOURCES = HERE / "SOURCES.json"


def _ring(coords) -> list[list[float]]:
    return [[round(x, DECIMALS), round(y, DECIMALS)] for x, y, *_ in coords]


def _polygons(geom: dict) -> list[list[list[list[float]]]]:
    """A geometry as a list of polygons, each a list of rings (the first is the outline, the rest are holes)."""
    if geom["type"] == "Polygon":
        return [[_ring(r) for r in geom["coordinates"]]]
    if geom["type"] == "MultiPolygon":
        return [[_ring(r) for r in poly] for poly in geom["coordinates"]]
    return []


def _lines(geom: dict) -> list[list[list[float]]]:
    if geom["type"] == "LineString":
        return [_ring(geom["coordinates"])]
    if geom["type"] == "MultiLineString":
        return [_ring(line) for line in geom["coordinates"]]
    return []


def extract(raw: dict[str, bytes]) -> dict:
    out: dict = {"schema": "ne50m/1", "decimals": DECIMALS}
    for layer, (stem, kind) in LAYERS.items():
        items = []
        for feature in json.loads(raw[stem])["features"]:
            geom = feature["geometry"]
            if geom:
                items += _polygons(geom) if kind == "polygon" else _lines(geom)
        out[layer] = items
    return out


def build(from_dir: Path | None = None, check: bool = False) -> int:
    pins = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else {"files": {}}
    raw: dict[str, bytes] = {}
    for stem, _kind in LAYERS.values():
        if from_dir is not None:
            data = (Path(from_dir) / f"{stem}.geojson").read_bytes()
        else:
            data = urllib.request.urlopen(BASE + f"{stem}.geojson", timeout=120).read()
        digest = hashlib.sha256(data).hexdigest()
        want = pins["files"].get(stem, {}).get("sha256")
        if want and want != digest:
            print(f"{stem}: sha256 {digest} is not the pinned {want}; stop and review the upstream change")
            return 1
        pins["files"][stem] = {"url": BASE + f"{stem}.geojson", "sha256": digest, "bytes": len(data)}
        raw[stem] = data
    doc = extract(raw)
    payload = gzip.compress(json.dumps(doc, separators=(",", ":")).encode("utf-8"), 9, mtime=0)
    if check:
        same = OUT.exists() and OUT.read_bytes() == payload
        print("ne50m.json.gz is current" if same else "ne50m.json.gz differs from a fresh build")
        return 0 if same else 1
    tmp = OUT.with_name(OUT.name + ".tmp")
    tmp.write_bytes(payload)
    replace_file(tmp, OUT)
    pins.update({"about": "Natural Earth 1:50m vector layers (public domain; made with Natural Earth, naturalearthdata.com). "
                          "The extract keeps no names and rounds to 2 decimals.",
                 "output": {"file": OUT.name, "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}})
    write_text_atomic(SOURCES, json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.name}: {len(payload)} bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from_dir = Path(argv[argv.index("--from-dir") + 1]) if "--from-dir" in argv else None
    return build(from_dir, check="--check" in argv)


if __name__ == "__main__":
    raise SystemExit(main())
