"""Palette under the AgX grade (ICW-05b round 2; the creator 2026-11-05: frame quality and the colour palette come first).

AgX "Medium High Contrast" is a film-like view transform: it compresses and desaturates what the toon materials emit, so a palette
hex given straight to an emission shader does not come out as that hex. Measured on Blender 5.2.3 (its own OCIO config, the same
numbers a render gives): mean CIE76 dE 13 over the palette tokens, up to 27 (uncertain_amber), against 0.2 under "Standard".

``match`` inverts the grade once per colour: it finds the scene-linear emission value whose AgX display value is the hex (Gauss-
Newton in log space from several starts, the best kept), and records what is left (``delta_e``) where AgX cannot reach a
saturated colour at all. The table ``agx_palette_match.json`` is generated, never edited by hand; it is stamped with the palette's
sha256 and the OCIO config's, so a palette change makes it stale (the style engine then refuses to build a matched graph).

    python -m explainer_engine.blender.grade match --config <blender>/5.2/datafiles/colormanagement/config.ocio
    python -m explainer_engine.blender.grade show

``match`` needs PyOpenColorIO (``pip install opencolorio``, a build-time tool only); ``show`` and the style engine read the table.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

HERE = Path(__file__).resolve().parent
TABLE = HERE / "agx_palette_match.json"
PALETTE = HERE.parent / "design" / "palette.json"
SCHEMA = "agx_palette_match/1"
VIEW, LOOK = "AgX", "AgX - Medium High Contrast"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _srgb(hex_color: str) -> list[float]:
    h = hex_color.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lab(srgb: list[float]) -> tuple[float, float, float]:
    """CIE L*a*b* (D65) of a display sRGB triple in 0..1."""
    r, g, b = (_linear(min(max(c, 0.0), 1.0)) for c in srgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def delta_e(a: list[float], b: list[float]) -> float:
    """CIE76 dE between two display sRGB triples (about 2 is the smallest difference most viewers see side by side)."""
    return sum((p - q) ** 2 for p, q in zip(lab(a), lab(b))) ** 0.5


def processor(config: Path):
    """The CPU processor of Blender's display pipeline: Linear Rec.709 -> sRGB display through the AgX view and the look."""
    import PyOpenColorIO as ocio
    cfg = ocio.Config.CreateFromFile(str(config))
    p = ocio.LegacyViewingPipeline()
    p.setDisplayViewTransform(ocio.DisplayViewTransform(src="Linear Rec.709", display="sRGB", view=VIEW))
    p.setLooksOverrideEnabled(True)
    p.setLooksOverride(LOOK)
    return p.getProcessor(cfg).getDefaultCPUProcessor()


def invert(forward, target: list[float], *, lo: float = 1e-4, hi: float = 64.0) -> tuple[list[float], list[float]]:
    """The emission value (scene linear, each channel in lo..hi) whose display value is closest to ``target`` (sRGB 0..1)."""
    import numpy as np
    f = lambda x: np.array(forward([float(v) for v in np.exp(x)]))  # noqa: E731
    t = np.array(target)
    starts = [[_linear(c) for c in target], [0.18, 0.18, 0.18], [1.0, 1.0, 1.0], [c * 2 for c in target]]
    best = None
    for s in starts:
        x = np.log(np.clip(np.array(s, dtype=float), lo, hi))
        for _ in range(80):
            y = f(x)
            e = delta_e(list(y), target)
            if best is None or e < best[0]:  # the best point on any path (a clipped step can walk away from it)
                best = (e, [round(float(v), 6) for v in np.exp(x)], [float(v) for v in y])
            r = y - t
            if np.abs(r).max() < 2e-5:
                break
            jac = np.zeros((3, 3))
            for k in range(3):
                d = x.copy()
                d[k] += 1e-4
                jac[:, k] = (f(d) - y) / 1e-4
            step = np.linalg.lstsq(jac, -r, rcond=None)[0]
            x = np.clip(x + np.clip(step, -1, 1), np.log(lo), np.log(hi))
    return best[1], best[2]


def build(config: Path, extra: dict[str, str] | None = None, *, blender_version: str = "5.2.3") -> dict:
    """The match table for every palette token plus ``extra`` (name -> hex, scene colours the palette does not have yet)."""
    forward = processor(config).applyRGB
    tokens = {k: v["hex"] for k, v in json.loads(PALETTE.read_text(encoding="utf-8"))["tokens"].items() if k != "chroma_key"}
    by_hex: dict[str, list[str]] = {}
    for name, h in {**tokens, **(extra or {})}.items():
        by_hex.setdefault(h.upper(), []).append(name)
    colours = {}
    for h, names in sorted(by_hex.items()):
        target = _srgb(h)
        raw = list(forward([_linear(c) for c in target]))
        lin, got = invert(forward, target)
        colours[h] = {"names": sorted(names), "linear": lin, "delta_e": round(delta_e(got, target), 2),
                      "raw_delta_e": round(delta_e(raw, target), 2), "in_palette": any(n in tokens for n in names)}
    return {"schema": SCHEMA, "view_transform": VIEW, "look": LOOK, "blender_version": blender_version,
            "config_sha256": _sha(config), "palette_sha256": _sha(PALETTE), "colours": colours}


def load(path: Path | None = None) -> dict:
    return json.loads(Path(path or TABLE).read_text(encoding="utf-8"))


def stale(doc: dict | None = None) -> bool:
    """True when the palette changed since the table was made (regenerate with ``match``)."""
    doc = doc if doc is not None else load()
    return doc["palette_sha256"] != _sha(PALETTE)


def matched(hex_color: str, doc: dict | None = None) -> tuple[float, float, float]:
    """The emission value for ``hex_color`` under AgX MHC. Refuses a stale table or a colour the table does not hold."""
    doc = doc if doc is not None else load()
    if stale(doc):
        raise ValueError("agx_palette_match.json is stale: palette.json changed (python -m explainer_engine.blender.grade match)")
    rec = doc["colours"].get(hex_color.upper())
    if rec is None:
        raise KeyError(f"{hex_color} has no AgX match (add it to the palette or the scene colours, then regenerate)")
    return tuple(rec["linear"])


def summary(doc: dict | None = None) -> dict:
    doc = doc if doc is not None else load()
    rows = [r for r in doc["colours"].values() if r["in_palette"]]
    mean = lambda k: round(sum(r[k] for r in rows) / len(rows), 2)  # noqa: E731
    return {"palette_tokens": len(rows), "mean_delta_e_raw": mean("raw_delta_e"), "mean_delta_e_matched": mean("delta_e"),
            "unreachable": sorted(n for r in doc["colours"].values() if r["delta_e"] > 2.0 for n in r["names"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.grade", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("match")
    m.add_argument("--config", required=True, help="Blender's colormanagement/config.ocio")
    m.add_argument("--blender-version", default="5.2.3")
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "match":
        from explainer_engine.blender import style_sheets as SS
        doc = build(Path(a.config), SS.SCENE_COLOURS, blender_version=a.blender_version)
        write_json_atomic(TABLE, doc)
        print(TABLE)
    print(json.dumps(summary(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
