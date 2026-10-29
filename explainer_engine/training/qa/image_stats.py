"""Free picture statistics for the automatic round QA (AUTO_QA_PLAN_2026-10-26 sections A and B, ვანო 2026-10-26).

Noise (the high-frequency energy of a picture, its Laplacian variance, the share of busy 16 px blocks) and colour
(Hasler-Suesstrunk colourfulness 2003, HSV saturation p95, share of clipped colour channels). numpy and PIL only, so it
runs on a pod and in the container. A value alone means little (a cartoon texture is not noise): the verdict compares a
shot with shot 0 of its own row and with the same shot of round 0 (`ratio`), never with a fixed threshold.

    python -m explainer_engine.training.qa.image_stats <picture folder> [<out.json>]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SIDE = 512  # long side the picture is measured at: the numbers do not depend on the render size
BLOCK = 16
BUSY_STD = 12.0  # a 16 px block whose grey std is above this counts as busy (0..255 scale)


def load(path, side=SIDE):
    """The picture as float RGB 0..255, long side scaled to ``side`` (Lanczos)."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        k = side / max(im.size)
        if k < 1:
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        return np.asarray(im, dtype=np.float64)


def _grey(rgb):
    return rgb @ np.array([0.299, 0.587, 0.114])


def laplacian_var(rgb):
    g = _grey(rgb)
    lap = g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:] - 4 * g[1:-1, 1:-1]
    return float(lap.var())


def busy_share(rgb, block=BLOCK, std=BUSY_STD):
    g = _grey(rgb)
    h, w = (g.shape[0] // block) * block, (g.shape[1] // block) * block
    b = g[:h, :w].reshape(h // block, block, w // block, block).std(axis=(1, 3))
    return float((b > std).mean())


def colourfulness(rgb):
    rg = rgb[..., 0] - rgb[..., 1]
    yb = 0.5 * (rgb[..., 0] + rgb[..., 1]) - rgb[..., 2]
    return float(np.hypot(rg.std(), yb.std()) + 0.3 * np.hypot(rg.mean(), yb.mean()))


def saturation_p95(rgb):
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-9), 0.0)
    return float(np.percentile(s, 95))


def clipped_share(rgb):
    """Share of pixels with a colour channel at 0 or 255 (blown or crushed)."""
    return float(((rgb <= 0) | (rgb >= 255)).any(axis=-1).mean())


def stats(path):
    rgb = load(path)
    return {"lap_var": laplacian_var(rgb), "busy": busy_share(rgb), "colourful": colourfulness(rgb),
            "sat_p95": saturation_p95(rgb), "clip": clipped_share(rgb)}


def ratio(a, b):
    """Every statistic of ``a`` divided by the one of ``b`` (the reference): 1.0 = the same, 2.0 = twice as much."""
    return {k: (a[k] / b[k] if b[k] else float("inf") if a[k] else 1.0) for k in a}


def folder(path):
    return {p.stem: stats(p) for p in sorted(Path(path).glob("*.png"))}


if __name__ == "__main__":
    out = folder(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(len(out), "pictures")
