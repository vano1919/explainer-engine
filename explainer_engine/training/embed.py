"""Picture and text embeddings for the judge (CLIP ViT-B-32, CPU is enough for a few hundred pictures).

Needs ``torch`` + ``open_clip_torch`` (not in requirements.txt: install them where the judge runs, the pod or a cloud
session). Embeddings are cached per file hash in ``<cache>/<sha1>.npy`` so a re-judge costs nothing.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

MODEL = ("ViT-B-32", "laion2b_s34b_b79k")
_M = {}


def _model():
    if not _M:
        import open_clip
        import torch
        m, _, pre = open_clip.create_model_and_transforms(*MODEL)
        m.eval()
        _M.update(m=m, pre=pre, tok=open_clip.get_tokenizer(MODEL[0]), torch=torch)
    return _M


def images(paths, cache=None):
    out = []
    for p in map(Path, paths):
        key = hashlib.sha1(p.read_bytes()).hexdigest()
        cp = Path(cache) / f"{key}.npy" if cache else None
        if cp and cp.exists():
            out.append(np.load(cp))
            continue
        from PIL import Image
        M = _model()
        with Image.open(p) as im, M["torch"].no_grad():
            v = M["m"].encode_image(M["pre"](im.convert("RGB")).unsqueeze(0))[0].numpy()
        v = v / np.linalg.norm(v)
        if cp:
            cp.parent.mkdir(parents=True, exist_ok=True)
            np.save(cp, v)
        out.append(v)
    return np.array(out)


def texts(strings):
    M = _model()
    with M["torch"].no_grad():
        v = M["m"].encode_text(M["tok"](list(strings))).numpy()
    return v / np.linalg.norm(v, axis=-1, keepdims=True)
