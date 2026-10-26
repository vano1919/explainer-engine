"""Checkpoint choice for xworld_v1 from its training samples (D-80, LT-75 step 1; the night plan's agreed method).

The six fixed-seed samples per saved step (LT-77) are scored with CLIP (``training.embed``, free, local):
* ``held``  the held-out samples (0, 1 and the edit 3) against the REAL frames they describe (closer = better);
* ``style`` the two new subjects (4, 5) against the mean of 60 training frames (the look carried to a new subject);
* ``bleed`` the no-trigger sample (2) against the same mean (how much the look leaks without the trigger; reported only).
Rank = held + style; the two best steps go to the prompt-type test, never two neighbours (at least 500 steps apart),
so the test also shows whether more training helps. Claude looks at the sheets before ``picks.json`` is written.

    python -m explainer_engine.training.pods.xworld_v1_pick <dataset dir> <samples dir> <out json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

HELD = {0: (0, 0), 1: (1, 0), 3: (0, 1)}  # sample index -> (held-out chain, frame) it describes (xworld_v1_build.samples)


def rank(scores, gap=500):
    """scores {step: {held, style, ...}} -> the two best steps by held + style, at least ``gap`` steps apart."""
    order = sorted(scores, key=lambda s: -(scores[s]["held"] + scores[s]["style"]))
    best = order[0]
    second = next((s for s in order[1:] if abs(s - best) >= gap), order[1] if len(order) > 1 else best)
    return [best, second]


def score(dataset, samples):
    from explainer_engine.training import embed
    dataset, samples = Path(dataset), Path(samples)
    m = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    chains = [c for c in m["hold_out"]["chains"] if len(c) >= 6]
    train = [dataset / x["img"] for x in m["train"]["single"][::max(1, len(m["train"]["single"]) // 60)]][:60]
    cache = samples / "_emb"
    centre = embed.images(train, cache).mean(0); centre /= np.linalg.norm(centre)
    truth = {k: embed.images([dataset / chains[c][f]], cache)[0] for k, (c, f) in HELD.items()}
    by_step = {}
    for p in samples.glob("*.jpg"):
        mm = re.search(r"__0*(\d+)_(\d)\.jpg$", p.name)
        if mm:
            by_step.setdefault(int(mm.group(1)), {})[int(mm.group(2))] = p
    out = {}
    for step, ims in sorted(by_step.items()):
        if step == 0 or len(ims) < 6:
            continue
        v = {k: embed.images([ims[k]], cache)[0] for k in ims}
        out[step] = {"held": round(float(np.mean([v[k] @ truth[k] for k in HELD])), 4),
                     "style": round(float(np.mean([v[k] @ centre for k in (4, 5)])), 4),
                     "bleed": round(float(v[2] @ centre), 4)}
    return out


if __name__ == "__main__":
    s = score(sys.argv[1], sys.argv[2])
    res = {"scores": s, "picks": rank(s)}
    Path(sys.argv[3]).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
