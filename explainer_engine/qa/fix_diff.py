"""What a fix-edit changed outside its defect (the asset pod's end report, 2026-11-06 12:27 UTC: a "change nothing, fix: ..." edit
(scene_assets SA-09) was judged by eye; this measures it). numpy + PIL only, so the pod can run it next to the edit.

    python -m explainer_engine.qa.fix_diff <before.png> <after.png> --box x0,y0,x1,y1 [--out report.json] [--mask mask.png]

``--box`` is the defect's region in 0..1 of the picture (the fix-edit's "fix:" names it; several ``--box`` allowed). Per pixel the
change is the largest RGB difference after a 3x3 mean (resampling and codec noise stay under ``NOISE``); the report gives the share
of changed pixels inside and outside the defect boxes, the mean change outside, and the bounding box of the outside change, and the
mask image paints changed pixels red (outside) and green (inside). No threshold here decides anything (none is sourced, D-59): the
numbers go next to the picture for the person (or the keyframe gate's VLM questions) who accepts the edit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

NOISE = 12   # 0..255 after the 3x3 mean: re-encoding and the edit model's resampling noise (engineering value, not a rule)


def _load(path, size=None):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def _blur(a):
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    h, w = a.shape[:2]
    return sum(p[dy:dy + h, dx:dx + w] for dy in range(3) for dx in range(3)) / 9.0


def box_mask(shape, boxes) -> np.ndarray:
    h, w = shape[:2]
    m = np.zeros((h, w), bool)
    for x0, y0, x1, y1 in boxes:
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            raise ValueError(f"box {x0, y0, x1, y1} is not inside 0..1 with x0 < x1 and y0 < y1")
        m[int(y0 * h):int(np.ceil(y1 * h)), int(x0 * w):int(np.ceil(x1 * w))] = True
    return m


def diff(before, after, boxes, *, noise: int = NOISE) -> tuple[dict, np.ndarray, np.ndarray]:
    """(report, changed mask, inside mask) of two RGB float arrays of the same size."""
    if before.shape != after.shape:
        raise ValueError(f"sizes differ: {before.shape} vs {after.shape}")
    d = np.abs(_blur(after) - _blur(before)).max(axis=2)
    changed = d > noise
    inside = box_mask(before.shape, boxes)
    out = ~inside
    rep = {"schema": "fix_diff/1", "size": [int(before.shape[1]), int(before.shape[0])], "boxes": [list(b) for b in boxes],
           "noise": noise,
           "changed_inside_share": round(float(changed[inside].mean()) if inside.any() else 0.0, 4),
           "changed_outside_share": round(float(changed[out].mean()) if out.any() else 0.0, 4),
           "mean_change_outside": round(float(d[out].mean()) if out.any() else 0.0, 2),
           "outside_bbox": None}
    ys, xs = np.nonzero(changed & out)
    if len(xs):
        h, w = changed.shape
        rep["outside_bbox"] = [round(xs.min() / w, 3), round(ys.min() / h, 3), round((xs.max() + 1) / w, 3),
                               round((ys.max() + 1) / h, 3)]
    return rep, changed, inside


def mask_image(after, changed, inside) -> np.ndarray:
    img = (after * 0.35).astype(np.uint8)
    img[changed & ~inside] = (230, 40, 40)
    img[changed & inside] = (40, 200, 80)
    return img


def report(before_path, after_path, boxes, *, mask_path=None, noise: int = NOISE) -> dict:
    from PIL import Image
    a = _load(after_path)
    b = _load(before_path, size=(a.shape[1], a.shape[0]))
    rep, changed, inside = diff(b, a, boxes, noise=noise)
    rep.update(before=str(before_path), after=str(after_path))
    if mask_path:
        Image.fromarray(mask_image(a, changed, inside)).save(mask_path)
        rep["mask"] = str(mask_path)
    return rep


def _box(text):
    v = [float(x) for x in text.split(",")]
    if len(v) != 4:
        raise argparse.ArgumentTypeError("a box is x0,y0,x1,y1 in 0..1")
    return tuple(v)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="what a fix-edit changed outside its defect")
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("--box", type=_box, action="append", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--mask", type=Path)
    a = ap.parse_args(argv)
    rep = report(a.before, a.after, a.box, mask_path=a.mask)
    text = json.dumps(rep, indent=1)
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
