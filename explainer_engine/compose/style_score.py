"""AC-14: the automatic style score. Six crops of a picture (line, texture, colour, little layout) are embedded with
DINOv2-small and compared with the creator's own style photos (HF lora_plan_2026-10-22/references_v3, 11 pictures): the mean
of the five nearest cosine similarities.

Measured on 2026-10-25 over 80 earlier pictures the creator had judged: AUC 0.96 between the approved look (eras, the v5
samples) and the pictures he called "the style is lost" (mean 0.63 against 0.42). Its weak side: snow. His photos have none,
so a correct snowy picture scores low (the v5 tundra sample: 0.33). Therefore the score is never read alone: a new picture
is compared with a CONTROL of the same place drawn with the approved prompt shape, and the verdict is REVIEW at most
(D-59: a measured hypothesis, one source type, not a binding threshold).

    python -m explainer_engine.compose.style_score <refs dir> <image> [--control <image>]

Needs torch + transformers (CPU is enough, ~1 s per picture); the pure scoring below is tested without them.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

MODEL = "facebook/dinov2-small"
K = 5
DROP_REVIEW = 0.10       # AC-14: more than this below the same-place control -> REVIEW (style probably drifting)
CROPS, SIDE = 6, 224


def crops(img, n: int = CROPS, seed: int = 1):
    im = img.convert("RGB").resize((1024, 576))
    r = random.Random(seed)
    return [im.crop((x, y, x + SIDE, y + SIDE)) for x, y in ((r.randint(0, 1024 - SIDE), r.randint(0, 576 - SIDE))
                                                             for _ in range(n))]


_model = None


def embed(img) -> np.ndarray:
    """Mean of the crops' normalised CLS embeddings (lazy import: the repo's tests never load torch)."""
    global _model
    import torch
    from transformers import AutoImageProcessor, AutoModel
    if _model is None:
        _model = (AutoModel.from_pretrained(MODEL).eval(), AutoImageProcessor.from_pretrained(MODEL))
    m, proc = _model
    with torch.no_grad():
        e = m(**proc(images=crops(img), return_tensors="pt")).last_hidden_state[:, 0]
        e = torch.nn.functional.normalize(e, dim=-1).mean(0).numpy()
    return e / np.linalg.norm(e)


def score(e: np.ndarray, refs: list[np.ndarray], k: int = K) -> float:
    e = e / np.linalg.norm(e)
    sims = sorted((float(e @ (r / np.linalg.norm(r))) for r in refs), reverse=True)
    return float(np.mean(sims[:k]))


def verdict(s: float, control: float | None) -> dict:
    """PASS or REVIEW, never FAIL (hypothesis tier). Without a control the score is only reported."""
    if control is None:
        return {"rule": "AC-14", "severity": "INFO", "score": round(s, 3), "detail": "no same-place control: score only"}
    drop = control - s
    sev = "REVIEW" if drop > DROP_REVIEW else "PASS"
    return {"rule": "AC-14", "severity": sev, "score": round(s, 3), "control": round(control, 3),
            "detail": f"{drop:+.2f} below the control" if drop > 0 else "at or above the control"}


def main(argv: list[str]) -> int:
    from PIL import Image
    refs = [embed(Image.open(p)) for p in sorted(Path(argv[0]).iterdir()) if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    s = score(embed(Image.open(argv[1])), refs)
    c = score(embed(Image.open(argv[argv.index("--control") + 1])), refs) if "--control" in argv else None
    print(verdict(s, c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
