"""The letterless map plate: one per region, drawn from the Natural Earth vectors + optional real shaded relief, cached by the hash of its spec.

A plate is land, coast, lakes, rivers and borders in palette colours (with Natural Earth's shaded relief raster on the land when
`shaded_relief=True`, ``maps/relief.py``; v4.3 P4 removed the synthetic DEM with its hand-placed Toba and Waterloo terrain,
finding F6) and nothing else. The colours can follow the episode's map look (``look``: palette token names, EP-02). It has no letters (CMP-01): this module never calls ``Canvas.text`` and its spec has no text field, so the
guarantee holds by construction, and ``tests/unit/test_maps.py`` fails if the renderer ever draws one. Labels, units and arrows
are drawn over the plate by ``maps/render.py`` at the frame the viewer sees.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.standards import sourced_rules as SR

LAYERS = ("land", "lakes", "rivers", "borders")
STYLE = {"sea_mix": 0.55, "coast_px": 0.0022, "river_px": 0.0030, "border_px": 0.0016}  # strokes are shares of the frame height
LOOK_KEYS = ("sea", "land", "coast", "river", "border", "lake")
RELIEF_FLAT = 0.82   # Natural Earth SR_HR's grey on flat ground (measured on the Indian Ocean basin's plains, 2026-11-12)


def spec_hash(view: geo.View, layers=LAYERS, shaded_relief: bool = False, look: dict | None = None) -> str:
    """The cache key: the view, the layers, the style and the data it was drawn from."""
    sources = json.loads((Path(geo.__file__).with_name("data") / "SOURCES.json").read_text(encoding="utf-8"))
    body = {
        "view": [view.lon, view.lat, view.span_km, view.width, view.height],
        "layers": list(layers),
        "style": STYLE,
        "data": sources["output"]["sha256"],
    }
    if shaded_relief:
        from explainer_engine.maps import relief
        body["shaded_relief"] = relief.SOURCE_ZIP_SHA256
    if look:
        body["look"] = {k: look[k] for k in sorted(look)}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def colours(look: dict | None = None) -> dict[str, tuple[int, int, int]]:
    """The plate's colours: palette blends, or the episode map look's palette tokens (``look[key]`` names a token)."""
    paper, ink, blue, grey = D.rgb("paper"), D.rgb("ink"), D.rgb("support_blue"), D.rgb("grey_mid")
    base = {
        "sea": D.blend(blue, paper, STYLE["sea_mix"]),
        "land": D.blend(paper, D.rgb("kit_card"), 0.14),
        "coast": ink,
        "river": D.blend(blue, paper, 0.25),
        "border": D.blend(grey, ink, 0.25),
        "lake": D.blend(blue, paper, STYLE["sea_mix"]),
    }
    for k in LOOK_KEYS:
        if look and look.get(k):
            base[k] = D.rgb(look[k])
    return base


def relief_rgb(view: geo.View, col: dict, look: dict | None = None, path=None) -> np.ndarray:
    """Land lit by the real relief, the sea flat (a hint of the raster's sea floor), seeded grain if the look asks for it."""
    from explainer_engine.maps import relief
    look = look or {}
    shade = relief.sample(view, path)
    mask = land_mask(view, ss=1)
    k = float(look.get("relief_strength", 1.0))
    gain = np.clip(1.0 + k * 1.6 * (shade / RELIEF_FLAT - 1.0), 0.45, 1.3)[..., None]
    land = np.asarray(col["land"], np.float32) * gain
    sea = np.asarray(col["sea"], np.float32) * (0.97 + 0.03 * shade)[..., None]
    out = np.where(mask[..., None], land, sea)
    grain = float(look.get("grain", 0.0))
    if grain > 0:
        rng = D.seeded("grain", view.lon, view.lat, view.span_km, view.width, view.height)
        out = out * (1.0 + grain * rng.standard_normal(out.shape[:2]).astype(np.float32))[..., None]
    return np.clip(out + 0.5, 0, 255).astype(np.uint8)


def draw_base(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
    look: dict | None = None,
) -> D.Canvas:
    """Land, lakes, rivers and borders over the sea (land lit by the real relief when `shaded_relief=True`), as a supersampled
    canvas (no letters). ``cache_dir`` is kept for callers; relief needs no per-view cache."""
    ds, col = geo.dataset(), colours(look)
    c = D.Canvas(view.width, view.height, col["sea"], ss)
    lon0, lat0, lon1, lat1 = view.bbox(0.02)
    box = (lon0, lat0, lon1, lat1)
    rect = (-2.0, -2.0, view.width + 2.0, view.height + 2.0)
    unit = view.height

    if shaded_relief:
        big = geo.View(view.lon, view.lat, view.span_km, view.width * ss, view.height * ss)
        c.replace(Image.fromarray(relief_rgb(big, col, look), mode="RGB").convert("RGBA"))

    if "land" in layers:
        if not shaded_relief:
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


def render_plate(
    view: geo.View,
    layers=LAYERS,
    ss: int = D.SS,
    shaded_relief: bool = False,
    cache_dir: Path | str | None = None,
    look: dict | None = None,
) -> Image.Image:
    return draw_base(view, layers, ss, shaded_relief=shaded_relief, cache_dir=cache_dir, look=look).image().convert("RGB")


def plate_path(view: geo.View, directory: Path | str, layers=LAYERS, shaded_relief: bool = False, look: dict | None = None) -> Path:
    prefix = "relief-plate" if shaded_relief else "plate"
    return Path(directory) / f"{prefix}-{spec_hash(view, layers, shaded_relief=shaded_relief, look=look)[:16]}.png"


def save_plate(view: geo.View, directory: Path | str, layers=LAYERS, shaded_relief: bool = False, look: dict | None = None) -> Path:
    """The plate in the cache folder; a hit is not drawn again (the file name is the hash of what it shows)."""
    path = plate_path(view, directory, layers, shaded_relief=shaded_relief, look=look)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        D.write_bytes_atomic(path, D.png_bytes(render_plate(view, layers, shaded_relief=shaded_relief, cache_dir=directory, look=look)))
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
    return {
        "schema": "map_plate_certificate/1",
        "sha256": hashlib.sha256(Path(plate_png).read_bytes()).hexdigest(),
        "ocr_engine": ocr_engine,
        "ocr_chars": int(ocr_chars),
        "geometry_iou": round(float(geometry_iou), 4),
    }


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
    D.write_bytes_atomic(argv[1], D.png_bytes(render_plate(view, shaded_relief=bool(s.get("shaded_relief", False)))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
