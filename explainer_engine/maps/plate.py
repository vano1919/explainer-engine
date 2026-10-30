"""The letterless map plate: one per region, drawn from the Natural Earth vectors, cached by the hash of its spec.

A plate is land, coast, lakes, rivers and borders in palette colours and nothing else. It has no letters (CMP-01): this module
never calls ``Canvas.text`` and its spec has no text field, so the guarantee holds by construction, and
``tests/unit/test_maps.py`` fails if the renderer ever draws one. Labels, units and arrows are drawn over the plate by
``maps/render.py`` at the frame the viewer sees. The same module draws a view of any size and span (the "plate" of a region is the
view that frames its whole box), so a close-up is as crisp as a theatre map; a painted plate that replaces it (P12e) is only
used with its certificate (BP-153, ``certificate``).

    python -m explainer_engine.maps.plate <spec.json> <out.png>      # a plate spec: {"lon","lat","span_km","width","height"}
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.standards import sourced_rules as SR

LAYERS = ("land", "lakes", "rivers", "borders")
STYLE = {"sea_mix": 0.55, "coast_px": 0.0022, "river_px": 0.0030, "border_px": 0.0016}  # strokes are shares of the frame height


def spec_hash(view: geo.View, layers=LAYERS) -> str:
    """The cache key: the view, the layers, the style and the data it was drawn from."""
    sources = json.loads((Path(geo.__file__).with_name("data") / "SOURCES.json").read_text(encoding="utf-8"))
    body = {"view": [view.lon, view.lat, view.span_km, view.width, view.height], "layers": list(layers), "style": STYLE,
            "data": sources["output"]["sha256"]}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def colours() -> dict[str, tuple[int, int, int]]:
    paper, ink, blue, grey = D.rgb("paper"), D.rgb("ink"), D.rgb("support_blue"), D.rgb("grey_mid")
    return {"sea": D.blend(blue, paper, STYLE["sea_mix"]), "land": D.blend(paper, D.rgb("kit_card"), 0.14), "coast": ink,
            "river": D.blend(blue, paper, 0.25), "border": D.blend(grey, ink, 0.25), "lake": D.blend(blue, paper, STYLE["sea_mix"])}


def draw_base(view: geo.View, layers=LAYERS, ss: int = D.SS) -> D.Canvas:
    """Land, lakes, rivers and borders over the sea, as a supersampled canvas (no letters)."""
    ds, col = geo.dataset(), colours()
    c = D.Canvas(view.width, view.height, col["sea"], ss)
    lon0, lat0, lon1, lat1 = view.bbox(0.02)
    box = (lon0, lat0, lon1, lat1)
    rect = (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    unit = view.height
    if "land" in layers:
        for poly in ds["land"]:
            if not geo._hit(poly.bbox, box):
                continue
            for i, ring in enumerate(poly.rings):
                x, y = view.to_px(ring[:, 0], ring[:, 1])
                pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
                if len(pts) < 3:
                    continue
                if i == 0:
                    c.polygon(pts, fill=(*col["land"], 255))
                else:
                    c.polygon(pts, fill=(*col["sea"], 255))
        for poly in ds["land"]:
            if not geo._hit(poly.bbox, box):
                continue
            for ring in poly.rings:
                x, y = view.to_px(ring[:, 0], ring[:, 1])
                for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                    c.line(piece, (*col["coast"], 255), max(1.0, STYLE["coast_px"] * unit))
    if "lakes" in layers:
        for poly in ds["lakes"]:
            if not geo._hit(poly.bbox, box):
                continue
            x, y = view.to_px(poly.rings[0][:, 0], poly.rings[0][:, 1])
            pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
            if len(pts) >= 3:
                c.polygon(pts, fill=(*col["lake"], 255))
    for layer, key, width, dash in (("borders", "border", STYLE["border_px"], (6.0, 4.0)), ("rivers", "river", STYLE["river_px"], None)):
        if layer not in layers:
            continue
        for line in ds[layer]:
            if not geo._hit(line.bbox, box):
                continue
            x, y = view.to_px(line.pts[:, 0], line.pts[:, 1])
            for piece in geo.clip_line(list(zip(x.tolist(), y.tolist())), *rect):
                c.line(piece, (*col[key], 255), max(1.0, width * unit), dash=dash)
    return c


def render_plate(view: geo.View, layers=LAYERS, ss: int = D.SS) -> Image.Image:
    return draw_base(view, layers, ss).image().convert("RGB")


def plate_path(view: geo.View, directory: Path | str, layers=LAYERS) -> Path:
    return Path(directory) / f"plate-{spec_hash(view, layers)[:16]}.png"


def save_plate(view: geo.View, directory: Path | str, layers=LAYERS) -> Path:
    """The plate in the cache folder; a hit is not drawn again (the file name is the hash of what it shows)."""
    path = plate_path(view, directory, layers)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        D.write_bytes_atomic(path, D.png_bytes(render_plate(view, layers)))
    return path


def land_mask(view: geo.View, ss: int = 1) -> np.ndarray:
    """Land as a boolean mask of the view (sea and lakes are False): what a painted plate is compared with."""
    c = D.Canvas(view.width, view.height, (0, 0, 0), ss)
    ds, rect = geo.dataset(), (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    box = view.bbox(0.02)
    for poly in ds["land"]:
        if geo._hit(poly.bbox, box):
            for i, ring in enumerate(poly.rings):
                x, y = view.to_px(ring[:, 0], ring[:, 1])
                pts = geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect)
                c.polygon(pts, fill=(255, 255, 255, 255) if i == 0 else (0, 0, 0, 255))
    for poly in ds["lakes"]:
        if geo._hit(poly.bbox, box):
            x, y = view.to_px(poly.rings[0][:, 0], poly.rings[0][:, 1])
            c.polygon(geo.clip_polygon(list(zip(x.tolist(), y.tolist())), *rect), fill=(0, 0, 0, 255))
    return np.asarray(c.image().convert("L")) > 127


def iou(a: np.ndarray, b: np.ndarray) -> float:
    union = np.count_nonzero(a | b)
    return 1.0 if union == 0 else float(np.count_nonzero(a & b) / union)


def certificate(plate_png: Path | str, ocr_chars: int, geometry_iou: float, ocr_engine: str) -> dict:
    """The record that must sit next to a painted plate (BP-153). The caller runs the OCR and the comparison; this only writes
    what they found, bound to the file's sha256 so a repainted plate needs a new one."""
    return {"schema": "map_plate_certificate/1", "sha256": hashlib.sha256(Path(plate_png).read_bytes()).hexdigest(),
            "ocr_engine": ocr_engine, "ocr_chars": int(ocr_chars), "geometry_iou": round(float(geometry_iou), 4)}


def certificate_findings(plate_png: Path | str, cert: dict | None) -> list[dict]:
    """BP-153: no certificate, a certificate of another file, letters found, or land that moved are findings (REVIEW)."""
    lvl, out = SR.level("BP-153"), []

    def add(detail: str) -> None:
        out.append({"rule": "CMP-01", "severity": lvl, "where": str(plate_png), "detail": detail})

    if not cert:
        return [{"rule": "CMP-01", "severity": lvl, "where": str(plate_png), "detail": "a painted plate needs its certificate (BP-153)"}]
    if cert.get("sha256") != hashlib.sha256(Path(plate_png).read_bytes()).hexdigest():
        add("the certificate is for another file: repaint means recertify")
    if cert.get("ocr_chars", 1) > SR.T("BP-153", "ocr_chars_max"):
        add(f"the OCR found {cert.get('ocr_chars')} letters on the plate: a plate has none")
    if cert.get("geometry_iou", 0.0) < SR.T("BP-153", "restyle_geometry_iou_min"):
        add(f"the painted land overlaps the vector land by {cert.get('geometry_iou')}: the restyle moved geometry")
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        print(__doc__)
        return 2
    s = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    view = geo.View(s["lon"], s["lat"], s["span_km"], s["width"], s["height"])
    D.write_bytes_atomic(argv[1], D.png_bytes(render_plate(view)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
