"""Draft map style preset from 3-6 reference frames of an episode film (our own approved film_look frames, never film frames).

The owner picks the film before every video, so every episode needs a new preset. This tool measures the frames (palette by
k-means in CIE L*a*b*, contrast, noise, edge fall-off, colour cast) and proposes the map / line / hud / finish colours and the
palette_check. The result is a DRAFT: `"draft": true`, `font` empty (a person chooses it), every field's origin named in
`proposal_notes` (measured / derived / fixed). `render.load_style_preset` refuses a draft, so nothing uses it automatically; a
person reviews it, sets the font and removes `draft`.

CLI: python -m explainer_engine.maps.maplibre_lane.preset_from_frames <name> <frame> [<frame> ...] [--grid ROWSxCOLS] [--out FILE]
     [--compare styles/1917_film.json]
With `--grid 3x2` a single contact sheet is cut into its frames first (rows x columns).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.maps.hud_layout import OKABE_ITO, check_palette

MIN_FRAMES, MAX_FRAMES = 3, 6
CLUSTERS = 8
SAMPLES_PER_FRAME = 4000
KMEANS_ITERATIONS = 12
MIN_CLUSTER_WEIGHT = 0.03
RGB = tuple[int, int, int]

_D65 = np.array([0.95047, 1.0, 1.08883])
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])


# ------------------------------------------------------------------ colour maths
def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB 0..255 (N,3) -> CIE L*a*b* (D65)."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = (lin @ _M.T) / _D65
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], axis=1)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """CIE L*a*b* (N,3) -> sRGB 0..255, clipped."""
    lab = np.asarray(lab, dtype=np.float64)
    fy = (lab[:, 0] + 16) / 116
    fx, fz = fy + lab[:, 1] / 500, fy - lab[:, 2] / 200
    f = np.stack([fx, fy, fz], axis=1)
    xyz = np.where(f ** 3 > 216 / 24389, f ** 3, (116 * f - 16) / (24389 / 27)) * _D65
    lin = np.clip(xyz @ np.linalg.inv(_M).T, 0.0, 1.0)
    c = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return np.clip(np.rint(c * 255), 0, 255)


def _hex(rgb: Any) -> str:
    r, g, b = (int(v) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _lab_hex(lab: Any) -> str:
    return _hex(lab_to_rgb(np.array([lab]))[0])


def _hex_lab(value: str) -> np.ndarray:
    v = value.lstrip("#")
    return rgb_to_lab(np.array([[int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)]]))[0]


def _lerp(a: np.ndarray, b: np.ndarray, t: float) -> np.ndarray:
    return a + (b - a) * t


def _chroma(lab: np.ndarray) -> float:
    return float(np.hypot(lab[1], lab[2]))


def _with_lightness(lab: np.ndarray, lightness: float) -> np.ndarray:
    return np.array([lightness, lab[1], lab[2]])


def delta_e(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """CIE76 colour difference."""
    return float(np.linalg.norm(np.asarray(lab1) - np.asarray(lab2)))


# ------------------------------------------------------------------ measuring
def load_frames(paths: list[str | Path], grid: tuple[int, int] | None = None) -> list[Image.Image]:
    """Open the frames; with `grid` (rows, cols) one contact sheet is cut into its cells."""
    images = [Image.open(p).convert("RGB") for p in paths]
    if grid is not None:
        if len(images) != 1:
            raise ValueError("--grid cuts ONE contact sheet; give exactly one image")
        rows, cols = grid
        sheet = images[0]
        w, h = sheet.width // cols, sheet.height // rows
        images = [sheet.crop((c * w, r * h, (c + 1) * w, (r + 1) * h)) for r in range(rows) for c in range(cols)]
    if not MIN_FRAMES <= len(images) <= MAX_FRAMES:
        raise ValueError(f"{MIN_FRAMES}-{MAX_FRAMES} reference frames are needed, got {len(images)}")
    return images


def _sample_pixels(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.resize((256, int(256 * img.height / img.width))), dtype=np.uint8).reshape(-1, 3)
    step = max(1, len(arr) // SAMPLES_PER_FRAME)
    return arr[::step][:SAMPLES_PER_FRAME]


def kmeans_lab(points: np.ndarray, k: int = CLUSTERS, iterations: int = KMEANS_ITERATIONS) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic k-means++ in Lab: returns (centres (k,3), weights (k,))."""
    rng = np.random.RandomState(0)
    centres = [points[rng.randint(len(points))]]
    for _ in range(k - 1):
        d2 = np.min(((points[:, None, :] - np.array(centres)[None]) ** 2).sum(axis=2), axis=1)
        total = d2.sum()
        centres.append(points[rng.choice(len(points), p=d2 / total)] if total > 0 else points[rng.randint(len(points))])
    centres_arr = np.array(centres)
    for _ in range(iterations):
        labels = np.argmin(((points[:, None, :] - centres_arr[None]) ** 2).sum(axis=2), axis=1)
        for i in range(k):
            members = points[labels == i]
            if len(members):
                centres_arr[i] = members.mean(axis=0)
    labels = np.argmin(((points[:, None, :] - centres_arr[None]) ** 2).sum(axis=2), axis=1)
    weights = np.bincount(labels, minlength=k) / len(points)
    order = np.argsort(-weights)
    return centres_arr[order], weights[order]


def measure_frames(images: list[Image.Image]) -> dict[str, Any]:
    """Palette and global statistics of the frames (each frame counts equally)."""
    pooled = np.concatenate([_sample_pixels(im) for im in images])
    lab = rgb_to_lab(pooled)
    centres, weights = kmeans_lab(lab)
    noise, centre_l, edge_l = [], [], []
    for im in images:
        gray = im.convert("L").resize((512, int(512 * im.height / im.width)))
        arr = np.asarray(gray, dtype=np.float64)
        blur = np.asarray(gray.filter(ImageFilter.GaussianBlur(2)), dtype=np.float64)
        mid = (arr > 40) & (arr < 215)
        noise.append(float(np.std((arr - blur)[mid])) if mid.any() else 0.0)
        h, w = arr.shape
        centre_l.append(float(arr[h // 4: 3 * h // 4, w // 4: 3 * w // 4].mean()))
        ring = np.ones_like(arr, dtype=bool)
        ring[h // 8: 7 * h // 8, w // 8: 7 * w // 8] = False
        edge_l.append(float(arr[ring].mean()))
    return {
        "centres": centres, "weights": weights, "mean_lab": lab.mean(axis=0), "lightness_std": float(lab[:, 0].std()),
        "noise_std": float(np.mean(noise)), "vignette_drop": float(np.mean(centre_l) - np.mean(edge_l)) / 255.0,
    }


# ------------------------------------------------------------------ proposing
def _pick(centres: np.ndarray, weights: np.ndarray, key, pool=None) -> np.ndarray:
    idx = [i for i in range(len(centres)) if weights[i] >= MIN_CLUSTER_WEIGHT and (pool is None or pool(centres[i]))]
    if not idx:
        idx = list(range(len(centres)))
    return centres[min(idx, key=lambda i: key(centres[i]))]


def propose_preset(name: str, stats: dict[str, Any]) -> dict[str, Any]:
    """Build the draft preset dict from `measure_frames` output."""
    centres, weights = stats["centres"], stats["weights"]
    ink = _with_lightness(_pick(centres, weights, key=lambda c: c[0]), 0)
    ink[0] = min(float(_pick(centres, weights, key=lambda c: c[0])[0]), 28.0)
    paper = _pick(centres, weights, key=lambda c: -c[0])
    paper = np.array([float(np.clip(paper[0], 78.0, 90.0)), paper[1] * 0.6, paper[2] * 0.6])
    white = np.array([97.0, 0.0, 0.0])
    water = _pick(centres, weights, key=lambda c: c[2], pool=lambda c: 40 <= c[0] <= 75)
    water = np.array([68.0, water[1] * 0.5, water[2] * 0.5])
    accent = _pick(centres, weights, key=lambda c: -_chroma(c), pool=lambda c: 25 <= c[0] <= 65 and c[1] > 3 and _chroma(c) >= 18)
    accent_source = "measured warm cluster"
    if not (25 <= accent[0] <= 65 and accent[1] > 3 and _chroma(accent) >= 18):
        accent = rgb_to_lab(np.array([OKABE_ITO["vermillion"]], dtype=float))[0]
        accent_source = "no warm saturated cluster in the frames: Okabe-Ito vermillion (fixed, colour-blind safe)"
    cool = _pick(centres, weights, key=lambda c: c[2], pool=lambda c: c[0] <= 45)
    cool = _with_lightness(cool, 30.0)
    ink_hex, paper_hex = _lab_hex(ink), _lab_hex(paper)
    ex = float(np.clip(0.25 + stats["lightness_std"] / 100.0, 0.25, 0.5))
    mean = stats["mean_lab"]
    cast = np.array([55.0, mean[1], mean[2]])
    preset = {
        "name": name,
        "draft": True,
        "note": "DRAFT proposed from reference frames; review, choose the font, then remove 'draft'. Never used automatically.",
        "font": "",
        "map": {
            "background": paper_hex,
            "water": _lab_hex(water),
            "waterway": {"color": _lab_hex(_lerp(water, ink, 0.2)), "width": 1.3},
            "landcover": {"color": _lab_hex(_lerp(paper, ink, 0.12)), "opacity": 0.5},
            "boundary": {"color": _lab_hex(_lerp(ink, paper, 0.15)), "width": 1.3, "dash": [3, 2]},
            "roads": {"color": _lab_hex(_lerp(paper, ink, 0.3)), "width": 1.0},
            "hillshade": {"exaggeration": round(ex, 2), "shadow": _lab_hex(_lerp(ink, paper, 0.1)),
                          "highlight": _lab_hex(_lerp(paper, white, 0.5))},
        },
        "line": {"stroke": _lab_hex(accent), "stroke_width": 2.8, "casing": _lab_hex(_lerp(paper, white, 0.6)),
                 "casing_width": 5.2, "casing_opacity": 0.85},
        "hud": {
            "counter_bg": "rgba(%d,%d,%d,0.95)" % tuple(int(v) for v in lab_to_rgb(np.array([_lerp(paper, white, 0.2)]))[0]),
            "counter_border": ink_hex, "counter_value": _lab_hex(cool), "counter_label": ink_hex,
            "chip_bg": ink_hex, "chip_fg": _lab_hex(_lerp(paper, white, 0.4)),
            "dot": ink_hex, "dot_border": _lab_hex(_lerp(paper, white, 0.4)),
            "town_bg": "rgba(%d,%d,%d,0.92)" % tuple(int(v) for v in lab_to_rgb(np.array([_lerp(paper, white, 0.2)]))[0]),
            "town_border": "rgba(%d,%d,%d,0.5)" % tuple(int(v) for v in lab_to_rgb(np.array([ink]))[0]),
            "town_text": ink_hex, "footnote_text": ink_hex,
            "footnote_bg": "rgba(%d,%d,%d,0.85)" % tuple(int(v) for v in lab_to_rgb(np.array([_lerp(paper, white, 0.2)]))[0]),
        },
        "finish": {
            "grain": {"opacity": round(float(np.clip(stats["noise_std"] / 10.0, 0.0, 0.3)), 2), "size": 300},
            "vignette": round(float(np.clip(stats["vignette_drop"], 0.0, 0.6)), 2),
            "tint": {"color": _lab_hex(cast), "opacity": round(float(np.clip(_chroma(cast) / 200.0, 0.0, 0.15)), 2)},
        },
        "palette_check": {"foreground": ["line.stroke", "hud.counter_value"], "background": "map.background"},
    }
    _repair_palette(preset)
    preset["proposal_notes"] = {
        "measured": ["palette (k-means, 8 clusters in Lab, equal weight per frame)", "finish.grain.opacity (noise of mid tones / 10)",
                     "finish.vignette (centre minus edge lightness)", "finish.tint (mean colour cast)"],
        "line_stroke_source": accent_source,
        "derived": ["map.* and hud.* colours: ink = darkest cluster (L<=28), paper = lightest (L 78-90, chroma x0.6), water = bluest "
                    "mid cluster (chroma x0.5, L 68), line.stroke = most saturated warm mid-dark cluster (else vermillion), counter_value = bluest dark cluster at L 30; "
                    "blends of ink/paper for land cover, roads, borders, waterways",
                    "map.hillshade.exaggeration = 0.25 + lightness spread / 100 (0.25-0.5)"],
        "fixed": ["line widths, boundary dash, land cover opacity, grain size 300 (not measured)",
                  "font: empty on purpose, a person chooses it"],
        "palette_repair": preset.pop("_repair_log", []),
    }
    return preset


def _palette_problems(preset: dict[str, Any]) -> list[str]:
    def get(dotted: str) -> RGB:
        node: Any = preset
        for part in dotted.split("."):
            node = node[part]
        v = node.lstrip("#")
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)

    check = preset["palette_check"]
    return check_palette({n: get(n) for n in check["foreground"]}, get(check["background"]))


def _repair_palette(preset: dict[str, Any]) -> None:
    """If the palette check fails, search the smallest lightness change of line.stroke / hud.counter_value that passes."""
    log: list[str] = []
    problems = _palette_problems(preset)
    if problems:
        log.append("before repair: " + "; ".join(problems))
        s0, c0 = _hex_lab(preset["line"]["stroke"]), _hex_lab(preset["hud"]["counter_value"])
        best = None
        for ds in range(0, 41, 2):
            for dc in range(-24, 25, 2):
                preset["line"]["stroke"] = _lab_hex(_with_lightness(s0, max(5.0, s0[0] - ds)))
                preset["hud"]["counter_value"] = _lab_hex(_with_lightness(c0, float(np.clip(c0[0] + dc, 5, 70))))
                if not _palette_problems(preset) and (best is None or ds + abs(dc) < best[0]):
                    best = (ds + abs(dc), ds, dc)
        if best:
            _, ds, dc = best
            preset["line"]["stroke"] = _lab_hex(_with_lightness(s0, max(5.0, s0[0] - ds)))
            preset["hud"]["counter_value"] = _lab_hex(_with_lightness(c0, float(np.clip(c0[0] + dc, 5, 70))))
            log.append(f"repaired: line.stroke L -{ds}, hud.counter_value L {dc:+d}")
        else:
            preset["line"]["stroke"], preset["hud"]["counter_value"] = _lab_hex(s0), _lab_hex(c0)
            log.append("NOT repairable by lightness alone: a person must choose these two colours")
    preset["_repair_log"] = log


# ------------------------------------------------------------------ comparing
def _flat(node: Any, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_flat(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = node
    return out


def compare_presets(draft: dict[str, Any], reference: dict[str, Any]) -> list[dict[str, Any]]:
    """Per shared colour field: CIE76 delta E; per shared number field: the difference."""
    a, b = _flat(draft), _flat(reference)
    rows = []
    for key in sorted(set(a) & set(b)):
        if key in ("name", "note", "font", "draft") or key.startswith("proposal_notes"):
            continue
        va, vb = a[key], b[key]
        if isinstance(va, str) and va.startswith("#") and isinstance(vb, str) and vb.startswith("#"):
            rows.append({"field": key, "draft": va, "reference": vb, "delta_e": round(delta_e(_hex_lab(va), _hex_lab(vb)), 1)})
        elif isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            rows.append({"field": key, "draft": va, "reference": vb, "difference": round(float(va) - float(vb), 3)})
    return rows


def build_draft(name: str, images: list[Image.Image]) -> dict[str, Any]:
    if not MIN_FRAMES <= len(images) <= MAX_FRAMES:
        raise ValueError(f"{MIN_FRAMES}-{MAX_FRAMES} reference frames are needed, got {len(images)}")
    return propose_preset(name, measure_frames(images))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Draft map style preset from 3-6 reference frames (never used automatically).")
    ap.add_argument("name")
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--grid", help="ROWSxCOLS: cut one contact sheet into its frames")
    ap.add_argument("--out")
    ap.add_argument("--compare", help="a finished preset to compare with (delta E per colour)")
    args = ap.parse_args(argv)
    grid = tuple(int(v) for v in args.grid.lower().split("x")) if args.grid else None
    draft = build_draft(args.name, load_frames(args.frames, grid))  # type: ignore[arg-type]
    text = json.dumps(draft, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.compare:
        ref = json.loads(Path(args.compare).read_text(encoding="utf-8"))
        for row in compare_presets(draft, ref):
            print(json.dumps(row), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
