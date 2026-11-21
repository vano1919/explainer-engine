"""Minimal front-line GeoJSON from the public-domain West Point map "Western front 1914" (HF explainer-engine/sources/maps/Western_front_1914.jpg).

The thick red/blue line of that map (the stabilised front, end of 1914) was traced by eye as pixel points of the 1241x961 picture; the
picture is georeferenced by an affine least-squares fit on eight towns whose pixel position was read off the map and whose coordinates are
common knowledge (Wikipedia). The map is a conic projection, so the fit is APPROXIMATE: the residuals are written to the output
(``properties.fit_rms_km``). It is a minimal drawing aid for an animated front, not a surveyed front line and not a claim source.
usage: python -m explainer_engine.maps.trace_front_1914 out.geojson
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

# (pixel x, pixel y, lon, lat): town labels of the map
CONTROL = [(326, 24, 2.92, 51.23), (580, 140, 4.35, 50.85), (245, 615, 2.35, 48.86), (698, 535, 5.38, 49.16),
           (1065, 675, 7.75, 48.58), (1000, 880, 7.34, 47.75), (350, 112, 2.89, 50.85), (355, 395, 2.79, 49.70)]
# the front, north (Nieuport, coast) to south (Swiss border), pixel points on the thick/dashed line of the map
FRONT_PX = [(335, 40), (350, 70), (352, 100), (356, 120), (362, 150), (350, 185), (348, 215), (345, 265), (332, 330), (352, 395), (334, 440),
            (380, 455), (430, 470), (480, 495), (520, 520), (560, 530), (610, 535), (650, 530), (700, 520), (735, 522), (760, 545),
            (785, 590), (810, 605), (835, 598), (850, 620), (880, 650), (905, 675), (935, 700), (960, 730), (985, 775), (1005, 830),
            (1000, 880), (1003, 935)]


def fit():
    A = np.array([[x, y, 1.0] for x, y, _, _ in CONTROL]); lon = np.array([c[2] for c in CONTROL]); lat = np.array([c[3] for c in CONTROL])
    cl, *_ = np.linalg.lstsq(A, lon, rcond=None); ct, *_ = np.linalg.lstsq(A, lat, rcond=None)
    return cl, ct, A, lon, lat


def to_lonlat(px, cl, ct):
    return [(float(cl @ [x, y, 1.0]), float(ct @ [x, y, 1.0])) for x, y in px]


def rms_km(cl, ct, A, lon, lat):
    dlon = (A @ cl - lon) * 111.32 * math.cos(math.radians(49.5)); dlat = (A @ ct - lat) * 110.57
    return float(np.sqrt(np.mean(dlon ** 2 + dlat ** 2)))


def geojson():
    cl, ct, A, lon, lat = fit()
    pts = to_lonlat(FRONT_PX, cl, ct)
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[round(a, 4), round(b, 4)] for a, b in pts]},
            "properties": {"name": "Western Front, end of 1914 (approximate trace)", "source": "Western_front_1914.jpg, US Army / West Point, public domain",
                           "fit_rms_km": round(rms_km(cl, ct, A, lon, lat), 1), "status": "minimal drawing aid, not a surveyed line, no claim"}}]}


def main(argv=None) -> int:
    out = (argv or sys.argv[1:])[0]
    gj = geojson()
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(gj, fh, indent=1)
    print(out, "fit rms km:", gj["features"][0]["properties"]["fit_rms_km"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
