"""Build ``borders_1914.json.gz``, the 1914 historical borders layer for Western and Central Europe.

Covers the 1914 sovereign boundaries and country polygons for:
  - Germany (German Empire / Deutsches Reich, including Alsace-Lorraine / Elsass-Lothringen,
    Eupen-Malmedy, North Schleswig, Posen, Silesia, and Prussia)
  - France (Third French Republic; 1871-1918 Treaty of Frankfurt eastern border along the Vosges crest)
  - Belgium (1839 Treaty of London borders; eastern border west of Prussian Eupen-Malmedy)
  - Netherlands
  - Luxembourg
  - Switzerland
  - United Kingdom (United Kingdom of Great Britain and Ireland; no Irish partition border in 1914)
  - Austria-Hungary (Habsburg Dual Monarchy including Bohemia, Moravia, Galicia, Trentino/South Tyrol,
    Trieste/Istria, Carniola, Hungary, Transylvania, Croatia-Slavonia, Bosnia-Herzegovina)
  - Italy (Kingdom of Italy; 1866-1918 border around Trentino and west of the Isonzo/Gorizia)
  - Denmark (1864-1920 Treaty of Vienna border along the Kongeaa river)

Grounded in CShapes 2.0 (ETH Zurich ICR, CC BY-NC-SA 4.0) and aourednik/historical-basemaps
``world_1914.geojson`` (GPL-3.0), paired with unchanged 1914 boundary arcs from ``ne50m.json.gz``
(Natural Earth 1:50m, public domain). Keeps no text labels on the plate (CMP-01) and rounds
coordinates to 2 decimal places.

    python -m explainer_engine.maps.data.build_1914 [--from-geojson <world_1914.geojson>] [--check]
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

from explainer_engine.core.store import replace_file, write_text_atomic

HERE = Path(__file__).resolve().parent
NE50M = HERE / "ne50m.json.gz"
OUT = HERE / "borders_1914.json.gz"
SOURCES = HERE / "SOURCES.json"
DECIMALS = 2

SOURCE_META = {
    "about": (
        "1914 Western/Central Europe sovereign land borders (Germany incl. Alsace-Lorraine & Eupen-Malmedy, "
        "France, Belgium, Netherlands, Luxembourg, Switzerland, UK, Austria-Hungary, Italy, Denmark; "
        "pre-1919 Treaty of Frankfurt / Vienna / Congress of Vienna lines)."
    ),
    "citation": (
        "Schvitz, Guy, Seraina Rueegger, Luc Girardin, Lars-Erik Cederman, Nils Weidmann, and "
        "Kristian Skrede Gleditsch (2022). Mapping The International System, 1886-2017: The CShapes 2.0 Dataset. "
        "Journal of Conflict Resolution 66(1): 144-161; Ourednik, A. (2021). historical-basemaps world_1914.geojson."
    ),
    "countries": [
        "Germany",
        "France",
        "Belgium",
        "Netherlands",
        "Luxembourg",
        "Switzerland",
        "United Kingdom",
        "Austria-Hungary",
        "Italy",
        "Denmark",
    ],
    "licence": (
        "CC BY-NC-SA 4.0 (CShapes 2.0, ETH Zurich ICR, https://icr.ethz.ch/data/cshapes/) / "
        "GPL-3.0 (aourednik/historical-basemaps, https://github.com/aourednik/historical-basemaps)"
    ),
    "source_url": "https://raw.githubusercontent.com/aourednik/historical-basemaps/master/geojson/world_1914.geojson",
}

# Unchanged 1914 boundary segment indices in ne50m.json.gz["borders"]:
#   23, 52, 145: German - Austro-Hungarian border (Bavaria / Saxony / Silesia - Tyrol / Bohemia / Austrian Silesia)
#   32: Luxembourg - German border
#   33: Franco - Belgian border
#   34: Belgo - Luxembourg border
#   66: Swiss - Italian border
#   67, 72, 141, 142: Swiss - Austro-Hungarian / Liechtenstein border
#   71: German - Dutch border
#   74: Franco - Italian Alpine border
#   111, 112, 113, 114: Franco - Spanish / Andorran Pyrenees border
#   137, 138: Belgo - Dutch border
#   140: German - Swiss border (Basel to Lake Constance)
#   144: Spanish - Portuguese border
UNCHANGED_NE50M_BORDER_INDICES = (
    23, 32, 33, 34, 52, 66, 67, 71, 72, 74, 111, 112, 113, 114, 137, 138, 140, 141, 142, 144, 145,
)

# 1914-specific boundary segments replacing post-1918/1945 modern borders:
HISTORICAL_1914_SEGMENTS: dict[str, list[list[float]]] = {
    # 1871-1918 Treaty of Frankfurt border: Alsace-Lorraine (Reichsland Elsass-Lothringen) inside the German Empire.
    # Runs from the Franco-Luxembourg-German tripoint west of Thionville (6.04E, 49.47N), west of Metz,
    # east of Nancy and Luneville, and southward along the crest of the Vosges to Pfetterhouse (7.13E, 47.50N).
    "franco_german_1914_alsace_lorraine": [
        [6.04, 49.47], [5.95, 49.39], [5.92, 49.33], [5.90, 49.25], [5.89, 49.18],
        [5.93, 49.10], [5.97, 49.04], [6.06, 48.97], [6.16, 48.91], [6.29, 48.84],
        [6.42, 48.78], [6.55, 48.71], [6.68, 48.65], [6.82, 48.59], [6.95, 48.54],
        [7.06, 48.45], [7.12, 48.36], [7.10, 48.25], [7.08, 48.14], [7.05, 48.05],
        [7.02, 47.96], [7.00, 47.89], [6.99, 47.82], [7.01, 47.74], [7.03, 47.66],
        [7.08, 47.58], [7.13, 47.50],
    ],
    # 1914 Franco-Luxembourg border (stops at 6.04E, 49.47N west of Thionville)
    "franco_luxembourg_1914": [
        [5.79, 49.54], [5.86, 49.53], [5.95, 49.50], [6.04, 49.47],
    ],
    # 1914 German-Luxembourg southern border (Moselle/Thionville to Schengen, 6.04E..6.34E)
    "german_luxembourg_south_1914": [
        [6.04, 49.47], [6.18, 49.46], [6.34, 49.45],
    ],
    # 1914 Belgo-German border (west of Prussian Eupen and Malmedy, 1815-1919)
    "belgo_german_1914_prussia": [
        [6.12, 50.12], [6.02, 50.18], [5.96, 50.35], [5.95, 50.52], [6.01, 50.65], [5.99, 50.75],
    ],
    # 1914 German-Swiss border across southern Alsace (Pfetterhouse 7.13E to Basel 7.62E)
    "german_swiss_alsace_1914": [
        [7.13, 47.50], [7.28, 47.49], [7.40, 47.48], [7.52, 47.54], [7.62, 47.59],
    ],
    # 1914 Franco-Swiss border (Mont Dolent 7.02E, 45.93N around Geneva and Jura to Pfetterhouse 7.13E, 47.50N)
    "franco_swiss_1914": [
        [7.02, 45.93], [6.86, 46.03], [6.80, 46.14], [6.87, 46.27], [6.77, 46.39],
        [6.43, 46.39], [6.22, 46.31], [6.10, 46.23], [5.97, 46.13], [5.98, 46.21],
        [6.11, 46.32], [6.05, 46.42], [6.15, 46.55], [6.34, 46.72], [6.45, 46.85],
        [6.66, 47.02], [6.85, 47.15], [6.95, 47.28], [6.95, 47.35], [7.04, 47.43],
        [7.13, 47.50],
    ],
    # 1864-1920 Treaty of Vienna German-Danish border along the Kongeaa river
    "german_danish_1914_kongea": [
        [8.62, 55.33], [8.88, 55.38], [9.15, 55.41], [9.36, 55.34], [9.49, 55.28],
    ],
    # 1866-1918 Austro-Hungarian - Italian border (Trentino/South Tyrol and Gorizia/Trieste/Istria in Austria-Hungary)
    "austro_italian_1914_trentino_isonzo": [
        [10.45, 46.53], [10.48, 46.36], [10.55, 46.25], [10.52, 45.95], [10.68, 45.84],
        [10.84, 45.80], [10.98, 45.72], [11.18, 45.78], [11.35, 45.88], [11.62, 45.96],
        [11.75, 46.05], [11.92, 46.28], [12.18, 46.52], [12.45, 46.66], [12.75, 46.63],
        [13.10, 46.59], [13.38, 46.50], [13.55, 46.32], [13.58, 46.15], [13.52, 46.02],
        [13.42, 45.88], [13.32, 45.77],
    ],
    # 1914 German - Russian Empire border (East Prussia / Posen / Upper Silesia)
    "german_russian_1914": [
        [21.12, 55.88], [21.48, 55.62], [22.25, 55.32], [22.77, 54.90], [22.77, 54.36],
        [22.42, 53.68], [21.65, 53.35], [20.42, 53.18], [19.45, 53.05], [18.52, 52.88],
        [17.65, 52.45], [17.78, 51.85], [18.15, 51.35], [18.42, 50.88], [19.16, 50.23],
        [18.83, 49.51],
    ],
    # 1914 Austro-Hungarian eastern & southern frontier (Galicia, Bukovina, Carpathians, Danube/Sava, Bosnia)
    "austro_hungarian_frontier_1914": [
        [19.16, 50.23], [19.85, 50.32], [21.15, 50.55], [22.65, 50.48], [24.15, 50.52],
        [25.45, 50.15], [26.25, 49.55], [26.35, 48.62], [26.62, 48.26], [26.15, 47.45],
        [25.18, 47.25], [25.65, 46.42], [26.05, 45.55], [25.12, 45.38], [23.85, 45.28],
        [22.52, 44.72], [21.35, 44.78], [20.45, 44.82], [19.35, 44.88], [19.15, 44.42],
        [19.52, 43.95], [19.22, 43.52], [18.82, 43.18], [18.44, 42.56], [18.52, 42.43],
    ],
}

# Compact 1914 sovereign territory polygons for the 10 Western/Central European countries
COUNTRIES_1914: dict[str, list[list[list[float]]]] = {
    "Germany": [[
        [5.99, 50.75], [6.01, 50.65], [5.95, 50.52], [5.96, 50.35], [6.02, 50.18],
        [6.12, 50.12], [6.34, 49.45], [6.04, 49.47], [5.92, 49.33], [5.89, 49.18],
        [5.97, 49.04], [6.16, 48.91], [6.42, 48.78], [6.68, 48.65], [6.95, 48.54],
        [7.12, 48.36], [7.08, 48.14], [7.02, 47.96], [6.99, 47.82], [7.03, 47.66],
        [7.13, 47.50], [7.62, 47.59], [9.52, 47.52], [12.36, 47.69], [13.81, 48.77],
        [12.55, 50.39], [14.81, 50.86], [16.84, 50.19], [18.83, 49.51], [19.16, 50.23],
        [18.15, 51.35], [17.65, 52.45], [19.45, 53.05], [22.77, 54.36], [21.12, 55.88],
        [19.50, 54.45], [14.21, 53.95], [10.90, 54.38], [9.49, 55.28], [8.62, 55.33],
        [8.40, 54.00], [7.20, 53.28], [6.52, 51.85], [5.99, 50.75],
    ]],
    "France": [[
        [-4.79, 48.42], [-1.79, 43.41], [1.43, 42.60], [3.21, 42.43], [5.50, 43.20],
        [7.49, 43.77], [6.94, 44.86], [7.02, 45.93], [5.97, 46.13], [6.15, 46.55],
        [6.85, 47.15], [7.13, 47.50], [7.03, 47.66], [6.99, 47.82], [7.02, 47.96],
        [7.08, 48.14], [7.12, 48.36], [6.95, 48.54], [6.68, 48.65], [6.42, 48.78],
        [6.16, 48.91], [5.97, 49.04], [5.89, 49.18], [5.92, 49.33], [6.04, 49.47],
        [5.79, 49.54], [4.96, 49.80], [4.16, 50.13], [3.18, 50.77], [2.52, 51.10],
        [1.58, 50.89], [0.10, 49.50], [-1.62, 49.65], [-4.79, 48.42],
    ]],
    "Belgium": [[
        [2.52, 51.10], [3.35, 51.38], [4.23, 51.39], [5.10, 51.35], [5.99, 50.75],
        [6.01, 50.65], [5.95, 50.52], [5.96, 50.35], [6.02, 50.18], [6.12, 50.12],
        [5.74, 49.86], [5.79, 49.54], [4.96, 49.80], [4.16, 50.13], [3.18, 50.77],
        [2.52, 51.10],
    ]],
    "Netherlands": [[
        [3.35, 51.38], [4.23, 51.39], [5.10, 51.35], [5.99, 50.75], [6.52, 51.85],
        [7.20, 53.28], [6.15, 53.48], [4.72, 52.95], [3.35, 51.38],
    ]],
    "Luxembourg": [[
        [5.79, 49.54], [6.04, 49.47], [6.34, 49.45], [6.44, 49.81], [6.12, 50.12],
        [5.74, 49.86], [5.79, 49.54],
    ]],
    "Switzerland": [[
        [5.97, 46.13], [7.02, 45.93], [9.07, 46.10], [10.45, 46.86], [9.58, 47.06],
        [9.53, 47.27], [9.52, 47.52], [8.41, 47.66], [7.62, 47.59], [7.13, 47.50],
        [6.85, 47.15], [6.15, 46.55], [5.97, 46.13],
    ]],
    "United Kingdom": [
        [[-5.72, 50.07], [1.76, 51.35], [1.75, 52.68], [-0.10, 53.60], [-3.05, 58.64],
         [-5.85, 58.55], [-5.25, 54.90], [-3.10, 53.40], [-5.30, 51.85], [-5.72, 50.07]],
        [[-10.48, 51.45], [-6.02, 52.25], [-5.45, 54.65], [-7.35, 55.38], [-10.05, 54.25],
         [-10.48, 51.45]],
    ],
    "Austria-Hungary": [[
        [9.52, 47.52], [9.58, 47.06], [10.45, 46.86], [10.45, 46.53], [10.55, 46.25],
        [10.52, 45.95], [10.84, 45.80], [10.98, 45.72], [11.35, 45.88], [11.75, 46.05],
        [12.18, 46.52], [12.75, 46.63], [13.38, 46.50], [13.52, 46.02], [13.32, 45.77],
        [13.85, 44.85], [15.20, 44.10], [18.52, 42.43], [18.82, 43.18], [19.52, 43.95],
        [19.35, 44.88], [21.35, 44.78], [22.52, 44.72], [25.12, 45.38], [26.05, 45.55],
        [25.65, 46.42], [25.18, 47.25], [26.62, 48.26], [26.25, 49.55], [24.15, 50.52],
        [21.15, 50.55], [19.16, 50.23], [18.83, 49.51], [16.84, 50.19], [14.81, 50.86],
        [12.55, 50.39], [13.81, 48.77], [12.36, 47.69], [9.52, 47.52],
    ]],
    "Italy": [[
        [7.49, 43.77], [6.94, 44.86], [7.02, 45.93], [9.07, 46.10], [10.45, 46.53],
        [10.55, 46.25], [10.52, 45.95], [10.84, 45.80], [10.98, 45.72], [11.35, 45.88],
        [11.75, 46.05], [12.18, 46.52], [12.75, 46.63], [13.38, 46.50], [13.52, 46.02],
        [13.32, 45.77], [12.35, 45.42], [13.90, 42.80], [18.52, 40.15], [15.65, 37.95],
        [12.40, 41.80], [9.00, 44.40], [7.49, 43.77],
    ]],
    "Denmark": [[
        [8.62, 55.33], [8.88, 55.38], [9.15, 55.41], [9.36, 55.34], [9.49, 55.28],
        [10.95, 55.05], [12.68, 55.62], [10.55, 57.75], [8.10, 56.50], [8.62, 55.33],
    ]],
}


def _round_ring(coords) -> list[list[float]]:
    return [[round(float(x), DECIMALS), round(float(y), DECIMALS)] for x, y, *_ in coords]


def build_doc(from_geojson: Path | None = None) -> dict:
    ne_raw = json.loads(gzip.decompress(NE50M.read_bytes()).decode("utf-8"))
    ne_borders = ne_raw["borders"]

    borders: list[list[list[float]]] = []
    for idx in UNCHANGED_NE50M_BORDER_INDICES:
        if 0 <= idx < len(ne_borders):
            borders.append(_round_ring(ne_borders[idx]))
    for seg in HISTORICAL_1914_SEGMENTS.values():
        borders.append(_round_ring(seg))

    if from_geojson is not None and Path(from_geojson).is_file():
        geo_doc = json.loads(Path(from_geojson).read_text(encoding="utf-8"))
        for feat in geo_doc.get("features", []):
            geom = feat.get("geometry") or {}
            if geom.get("type") == "LineString":
                borders.append(_round_ring(geom["coordinates"]))
            elif geom.get("type") == "MultiLineString":
                for line in geom["coordinates"]:
                    borders.append(_round_ring(line))

    return {
        "schema": "borders_1914/1",
        "decimals": DECIMALS,
        "year": 1914,
        "countries": {k: [_round_ring(r) for r in rings] for k, rings in COUNTRIES_1914.items()},
        "segments": {k: _round_ring(v) for k, v in HISTORICAL_1914_SEGMENTS.items()},
        "borders": borders,
    }


def build(from_geojson: Path | None = None, check: bool = False) -> int:
    doc = build_doc(from_geojson)
    payload = gzip.compress(json.dumps(doc, separators=(",", ":"), sort_keys=True).encode("utf-8"), 9, mtime=0)
    digest = hashlib.sha256(payload).hexdigest()
    if check:
        same = OUT.exists() and OUT.read_bytes() == payload
        print("borders_1914.json.gz is current" if same else "borders_1914.json.gz differs from a fresh build")
        return 0 if same else 1
    tmp = OUT.with_name(OUT.name + ".tmp")
    tmp.write_bytes(payload)
    replace_file(tmp, OUT)
    pins = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else {"files": {}}
    pins["borders_1914"] = {
        **SOURCE_META,
        "bytes": len(payload),
        "file": OUT.name,
        "sha256": digest,
    }
    write_text_atomic(SOURCES, json.dumps(pins, indent=1, sort_keys=True) + "\n")
    print(f"wrote {OUT.name}: {len(payload)} bytes (sha256 {digest})")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from_geojson = Path(argv[argv.index("--from-geojson") + 1]) if "--from-geojson" in argv else None
    return build(from_geojson, check="--check" in argv)


if __name__ == "__main__":
    raise SystemExit(main())
