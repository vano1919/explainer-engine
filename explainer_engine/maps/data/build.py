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
