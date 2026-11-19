"""Make the scene layers of an episode's still_25d pictures, free, on CPU (``understand.understand`` for every shot).

``python -m explainer_engine.production.layers_run models``           fetch the free models into ``$EXPLAINER_MODELS_DIR``
``python -m explainer_engine.production.layers_run build <episode> --shots S01_SH004,S02_SH005``

``episode/run.py`` only reads a ``<picture>.layers/`` cache (``understand.load``); nothing in the runner made one, so a still
shot had no direction and G7 stopped at ``director_not_used: no direction``. This is the command that makes the cache, for the
picture the runner will use (the master in ``production/pictures.json``), from the shot's spec in ``planning/layer_specs.json``
(``{"shots": {id: {"q": {object id: phrase}, "lights": [{id, kind, point, radius}]}}}``): Grounding-DINO finds each phrase, its
box centre is the SAM point (``understand.understand`` does the rest: depth, masks, BiRefNet edges, the clean plate).

A phrase the detector does not find is a row in the result, never a silent skip; a picture with no spec is a row too.
Needs torch and transformers (CPU build is enough) and the models; without them it says what is missing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from explainer_engine.core.errors import ConfigError

SPECS_REL = "planning/layer_specs.json"
PICTURES_REL = "production/pictures.json"
MAX_BOX_AREA = 0.6            # a detection that covers most of the picture is the background, not an object
PER_PHRASE = 2                # the two most confident boxes of a phrase (the second gets the id ``<id>_2``)
# models understand.py reads from $EXPLAINER_MODELS_DIR/<owner>__<name>/ and the files each needs (None = all)
MODEL_FILES = {"da_v2_small": ["onnx/model.onnx", "*.json"], "lama": ["lama_fp32.onnx"], "sam21": None, "birefnet": None}


def fetch_models(keys=None, download=None) -> dict:
    """Download the free models (public repos) into the models folder; the folder names are ``understand.repo_dir``."""
    from explainer_engine.production import understand as U
    if download is None:
        from huggingface_hub import snapshot_download as download
    out = {}
    for k in keys or MODEL_FILES:
        if k not in MODEL_FILES:
            raise ConfigError(f"unknown model {k!r}: one of {', '.join(MODEL_FILES)}")
        t0 = time.time()
        dest = U.repo_dir(k)
        download(U.REPOS[k], local_dir=str(dest), allow_patterns=MODEL_FILES[k])
        out[k] = {"repo": U.REPOS[k], "dir": str(dest), "seconds": round(time.time() - t0, 1)}
    return out


def load_specs(root: Path) -> dict:
    p = Path(root) / SPECS_REL
    if not p.is_file():
        raise ConfigError(f"{p} is missing: one spec per still shot (objects to find, light sources)")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "layer_specs/1" or not isinstance(doc.get("shots"), dict):
        raise ConfigError(f"{p} is not a layer_specs/1 file")
    return doc["shots"]


def picture_of(root: Path, shot_id: str) -> Path:
    """The start picture the runner uses (its master once promoted), from ``production/pictures.json``."""
    p = Path(root) / PICTURES_REL
    if not p.is_file():
        raise ConfigError(f"{p} is missing: run the pictures stage (G5) first, the layers belong to the picture it pins")
    rec = (json.loads(p.read_text(encoding="utf-8")).get("pictures") or {}).get(f"{shot_id}_start")
    if not rec:
        raise ConfigError(f"{shot_id}_start is not in {PICTURES_REL}")
    pic = Path(root) / rec["file"]
    if not pic.is_file():
        raise ConfigError(f"{pic} is not on disk")
    return pic


def seen_from_spec(rgb: np.ndarray, spec: dict, detect) -> tuple[dict, list[dict]]:
    """The ``seen`` block of ``understand`` and a row for every phrase (found or not)."""
    objs, rows = [], []
    for oid, phrase in (spec.get("q") or {}).items():
        hits = [h for h in detect(rgb, [phrase]) if (h["bbox"][2] - h["bbox"][0]) * (h["bbox"][3] - h["bbox"][1]) < MAX_BOX_AREA]
        hits.sort(key=lambda h: -h["confidence"])
        rows.append({"object": oid, "phrase": phrase, "found": len(hits[:PER_PHRASE]),
                     "confidence": [round(float(h["confidence"]), 3) for h in hits[:PER_PHRASE]]})
        for k, h in enumerate(hits[:PER_PHRASE]):
            objs.append({"id": oid if k == 0 else f"{oid}_{k + 1}", "what": phrase, "points": [h["centroid"]], "box": h["bbox"],
                         "layer": True, "names": [oid.split("_")[0]]})
    lights = [{"id": li["id"], "kind": li["kind"], "point": list(li["point"]), "radius": li["radius"]}
              for li in spec.get("lights") or []]
    return {"what": " ".join((spec.get("q") or {}).values()), "objects": objs, "lights": lights, "living": []}, rows


def build(root: Path, shot_ids: list[str], understand=None, detect=None, force: bool = False) -> list[dict]:
    """One result row per shot: ``{shot, status, picture, phrases, seconds}`` (status ``made``, ``no_spec`` or ``error``)."""
    from PIL import Image
    root = Path(root)
    specs = load_specs(root)
    if understand is None:
        from explainer_engine.production import understand as U
        understand = U.understand
    if detect is None:
        from explainer_engine.production import perceive_picture as PP
        detect = PP.run_grounding_dino_tiny
    out = []
    for sid in shot_ids:
        if sid not in specs:
            out.append({"shot": sid, "status": "no_spec", "why": f"no entry in {SPECS_REL}"})
            continue
        pic = picture_of(root, sid)
        t0 = time.time()
        rgb = np.asarray(Image.open(pic).convert("RGB"))
        seen, rows = seen_from_spec(rgb, specs[sid], detect)
        if specs[sid].get("q") and not seen["objects"]:
            out.append({"shot": sid, "status": "error", "picture": str(pic.relative_to(root)), "phrases": rows,
                        "why": "the detector found none of the phrases (is transformers installed, are the weights there?)"})
            continue
        man = understand(pic, seen, force=force)
        out.append({"shot": sid, "status": "made", "picture": str(pic.relative_to(root)), "phrases": rows,
                    "objects": len(seen["objects"]), "lights": len(seen["lights"]), "picture_sha256": man.get("picture_sha256"),
                    "seconds": round(time.time() - t0, 1)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("models")
    m.add_argument("--only", action="append")
    b = sub.add_parser("build")
    b.add_argument("episode", type=Path)
    b.add_argument("--shots", required=True, help="comma-separated shot ids")
    b.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "models":
        print(json.dumps(fetch_models(a.only), indent=1))
        return 0
    rows = build(a.episode, [s.strip() for s in a.shots.split(",") if s.strip()], force=a.force)
    print(json.dumps(rows, indent=1))
    return 0 if all(r["status"] == "made" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
