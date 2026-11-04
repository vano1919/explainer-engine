# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/maps/geo.py`
# Target Module : explainer_engine/maps/geo.py
# Target Classes/Symbols : def dataset(), class _Polygon (methods: __init__), class _Line (methods: __init__), def _hit(), class View (methods: km_per_px, height_km, to_px, to_lonlat, bbox, at), def distance_km(), def _inside(), def in_polygons(), def is_water(), def point_in_ring(), def clip_polygon(), def clip_line()
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

"""Map geometry: the Natural Earth extract, one local projection per view, point-in-polygon and clipping. numpy only.

The projection is the local equirectangular one (x east = longitude * cos(latitude of the centre), y north = latitude), north up
(CRAFT-CART-06). A view is a centre, a width in kilometres and a pixel size: every pixel is a pure function of those numbers,
so a plate renders to the same bytes twice (CMP-09).
"""

from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA = Path(__file__).with_name("data") / "ne50m.json.gz"
R_KM = 6371.0088
KM_PER_DEG = R_KM * math.pi / 180.0


@lru_cache(maxsize=1)
def dataset() -> dict:
    """The four layers: ``land`` and ``lakes`` as polygons (rings of lon/lat, the first the outline), ``rivers`` and ``borders`` as lines."""
    raw = json.loads(gzip.decompress(DATA.read_bytes()).decode("utf-8"))
    out = {"schema": raw["schema"]}
    for layer in ("land", "lakes"):
        out[layer] = [_Polygon([np.asarray(r, dtype=np.float64) for r in poly]) for poly in raw[layer]]
    for layer in ("rivers", "borders"):
        out[layer] = [_Line(np.asarray(line, dtype=np.float64)) for line in raw[layer]]
    return out


# TODO [CLAUDE-CLASS-SYNC: _Polygon] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `_Polygon` (methods: __init__) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class _Polygon:
    __slots__ = ("rings", "bbox")

    def __init__(self, rings: list[np.ndarray]):
        self.rings = rings
        outer = rings[0]
        self.bbox = (float(outer[:, 0].min()), float(outer[:, 1].min()), float(outer[:, 0].max()), float(outer[:, 1].max()))


# TODO [CLAUDE-CLASS-SYNC: _Line] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `_Line` (methods: __init__) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class _Line:
    __slots__ = ("pts", "bbox")

    def __init__(self, pts: np.ndarray):
        self.pts = pts
        self.bbox = (float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max()))


def _hit(a: tuple, b: tuple) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


# TODO [CLAUDE-CLASS-SYNC: View] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `View` (methods: km_per_px, height_km, to_px, to_lonlat, bbox, at) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
@dataclass(frozen=True)
class View:
    """What a frame shows: the centre (lon, lat), the width in km, the pixel size. The height in km follows the aspect."""

    lon: float
    lat: float
    span_km: float
    width: int
    height: int

    @property
    def km_per_px(self) -> float:
        return self.span_km / self.width

    @property
    def height_km(self) -> float:
        return self.span_km * self.height / self.width

    def to_px(self, lon, lat) -> tuple[np.ndarray, np.ndarray]:
        lon, lat = np.asarray(lon, dtype=np.float64), np.asarray(lat, dtype=np.float64)
        kx = KM_PER_DEG * math.cos(math.radians(self.lat))
        x = ((lon - self.lon) * kx / self.span_km + 0.5) * self.width
        y = (0.5 - (lat - self.lat) * KM_PER_DEG / self.height_km) * self.height
        return x, y

    def to_lonlat(self, x, y) -> tuple[np.ndarray, np.ndarray]:
        x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
        kx = KM_PER_DEG * math.cos(math.radians(self.lat))
        return self.lon + (x / self.width - 0.5) * self.span_km / kx, self.lat + (0.5 - y / self.height) * self.height_km / KM_PER_DEG

    def bbox(self, margin: float = 0.0) -> tuple[float, float, float, float]:
        (x0, x1), (y0, y1) = (-margin * self.width, (1 + margin) * self.width), (-margin * self.height, (1 + margin) * self.height)
        lon0, lat1 = self.to_lonlat(x0, y0)
        lon1, lat0 = self.to_lonlat(x1, y1)
        return float(lon0), float(lat0), float(lon1), float(lat1)

    def at(self, lon: float, lat: float, span_km: float) -> "View":
        return View(lon, lat, span_km, self.width, self.height)


def distance_km(lon0, lat0, lon1, lat1) -> float:
    """Great-circle distance (haversine)."""
    p0, p1 = math.radians(lat0), math.radians(lat1)
    a = math.sin((p1 - p0) / 2) ** 2 + math.cos(p0) * math.cos(p1) * math.sin(math.radians(lon1 - lon0) / 2) ** 2
    return 2 * R_KM * math.asin(min(1.0, math.sqrt(a)))


def _inside(ring: np.ndarray, lon: float, lat: float) -> bool:
    x, y = ring[:, 0], ring[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    crosses = (y > lat) != (y1 > lat)
    with np.errstate(divide="ignore", invalid="ignore"):
        x_at = x + (lat - y) * (x1 - x) / (y1 - y)
    return bool(np.count_nonzero(crosses & (lon < x_at)) % 2)


def in_polygons(polygons: list, lon: float, lat: float) -> bool:
    for poly in polygons:
        b = poly.bbox
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3] and _inside(poly.rings[0], lon, lat):
            if not any(_inside(h, lon, lat) for h in poly.rings[1:]):
                return True
    return False


def is_water(lon: float, lat: float) -> bool:
    """Sea or a lake (a river is not water for a march: it is crossed at a ford or a bridge, MAP law 2 lists the crossing)."""
    ds = dataset()
    return (not in_polygons(ds["land"], lon, lat)) or in_polygons(ds["lakes"], lon, lat)


def point_in_ring(ring, lon: float, lat: float) -> bool:
    return _inside(np.asarray(ring, dtype=np.float64), lon, lat)


def clip_polygon(pts: list[tuple[float, float]], x0: float, y0: float, x1: float, y1: float) -> list[tuple[float, float]]:
    """Sutherland-Hodgman against the rectangle: a polygon with a vertex 100 000 px away stays drawable."""
    def edge(points, inside, cross):
        out = []
        for i, cur in enumerate(points):
            prev = points[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    for inside, cross in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                          (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        if not pts:
            return []
        pts = edge(pts, inside, cross)
    return pts


def clip_line(pts: list[tuple[float, float]], x0: float, y0: float, x1: float, y1: float) -> list[list[tuple[float, float]]]:
    """Liang-Barsky per segment; consecutive kept segments are joined into pieces."""
    pieces: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1 = 0.0, 1.0
        ok = True
        for p, q in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if p == 0:
                if q < 0:
                    ok = False
                    break
            else:
                t = q / p
                if p < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
        if not ok or t0 > t1:
            if cur:
                pieces.append(cur)
                cur = []
            continue
        pa, pb = (a[0] + t0 * dx, a[1] + t0 * dy), (a[0] + t1 * dx, a[1] + t1 * dy)
        if cur and cur[-1] != pa:
            pieces.append(cur)
            cur = []
        if not cur:
            cur = [pa]
        cur.append(pb)
        if t1 < 1.0:
            pieces.append(cur)
            cur = []
    if cur:
        pieces.append(cur)
    return pieces
