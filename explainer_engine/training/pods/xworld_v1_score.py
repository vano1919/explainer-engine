"""LT-75 scoring of the xworld_v1 prompt-type test (D-80): every drawn frame against the REAL frame of the same place in
its held-out scene, free and local after the pod.

Per frame: CLIP image similarity (``training.embed``), the set's palette distance (LT-60, ``video_qa._palette``), the
line weight as ink ratio (LT-61) and the grey-level difference to the real frame (``judge.edit_pair_metrics``: ``change``
over the frame, ``drift`` on the outer band = set and camera, LT-41/42 read against the truth instead of the control).
Per variant x checkpoint the means, and one composite so the table has an order:
    composite = clip - palette - 0.5 x |ln ink| - change
(higher is better; each term is 0..1 or near it). Claude confirms the order on the sheets; ვანო decides (LT-75).

    python -m explainer_engine.training.pods.xworld_v1_score <dataset dir> <test out dir> <out json>
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np


def frame_metrics(drawn, truth, clip):
    """drawn, truth: RGB uint8 arrays of one size; clip: their CLIP similarity."""
    from explainer_engine.training import judge, video_qa
    ink = [float((video_qa._gray(f) < video_qa.Q.get("ink_max", 50)).mean()) for f in (truth, drawn)]
    m = {"clip": round(float(clip), 4), "palette": video_qa._dist(video_qa._palette(truth), video_qa._palette(drawn)),
         "ink": round(ink[1] / max(ink[0], 1e-6), 3), **judge.edit_pair_metrics(truth, drawn)}
    m["composite"] = round(m["clip"] - m["palette"] - 0.5 * abs(math.log(max(m["ink"], 1e-3))) - m["change"], 4)
    return m


def summarise(rows):
    """rows [{variant, lora, k, ...metrics}] -> {"<variant>/<lora>": means + n}, best composite first."""
    groups = {}
    for r in rows:
        groups.setdefault(f"{r['variant']}/{r['lora'] or 'base'}", []).append(r)
    keys = ("clip", "palette", "ink", "change", "drift", "composite")
    out = {g: {**{k: round(float(np.mean([r[k] for r in rs])), 4) for k in keys}, "n": len(rs)} for g, rs in groups.items()}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["composite"]))


def score(dataset, outd):
    from PIL import Image
    from explainer_engine.training import embed
    dataset, outd = Path(dataset), Path(outd)
    jobs = json.loads((outd / "jobs.json").read_text(encoding="utf-8"))
    rows, cache = [], outd / "_emb"
    for j in jobs:
        p = outd / f"{j['name']}.png"
        if not p.exists():
            continue
        tp = dataset / j["truth"]
        with Image.open(tp) as t:
            size = t.size
            truth = np.asarray(t.convert("RGB"))
        with Image.open(p) as d:
            drawn = np.asarray(d.convert("RGB").resize(size))
        e = embed.images([p, tp], cache)
        rows.append({k: j[k] for k in ("name", "chain", "k", "variant", "lora")} | frame_metrics(drawn, truth, e[0] @ e[1]))
    return {"frames": rows, "table": summarise(rows)}


if __name__ == "__main__":
    res = score(sys.argv[1], sys.argv[2])
    Path(sys.argv[3]).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["table"], indent=1))
