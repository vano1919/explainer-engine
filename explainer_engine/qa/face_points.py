"""Face points measured on the painted pictures (the coordinator's QA note, 2026-10-20: the script's
``pictures.<id>.speakers`` are template guesses, e.g. s02_signing puts Belfort at [0.76, 0.42] while he is drawn near
[0.92, 0.3], so bubble tails point at the wrong hero and rings land on walls). Free and local: YuNet (OpenCV, opencv_zoo,
MIT) on each picture the script uses, from the same picture folders as ``production time``.

    python -m explainer_engine.qa.face_points <script.json> [--pics DIR ...] [--out face_points.json] [--apply]

1. Each picture with ``speakers`` is found (``assemble.find_picture``) and YuNet looks for faces (score >= FACE_SCORE_MIN).
2. Who is who: with OpenCV's SFace model (opencv_zoo, Apache-2.0, ``tools/yunet/face_recognition_sface_2021dec.onnx``)
   each face is compared with the hero's own painted faces (his face sheet and reference picture); a face named with
   confidence (ID_MIN, ID_MARGIN) is that hero's, whatever the declared order says (s02_signing declares O'Leary left of
   Musk; he is drawn in the middle). The remaining heroes are matched to the remaining faces in left-to-right order (the
   subset and pairing with the smallest summed distance), so a hero seen from behind (over the shoulder) has no face.
3. ``face_points.json``: per picture and hero the declared point, the measured face centre, the distance (shares of the
   width), and whether the match is confident (CONFIDENT_SCORE, one face per declared hero or the only face near him).
4. ``--apply`` rewrites only the confident ``speakers`` values in the script (nothing else).
5. ``check`` (run by ``qa/loop``): FP-OFF REVIEW for every declared point farther than OFF_MAX of the width from its
   matched face. Never FAIL: cartoon face detection is a heuristic and the numbers below are hypotheses.

The YuNet model: ``$EXPLAINER_YUNET`` or ``tools/yunet/face_detection_yunet_2023mar.onnx`` (qa/pixels). Without OpenCV or
the model the check returns nothing and says so.
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.core.store import write_json_atomic
from explainer_engine.production import assemble as A
from explainer_engine.production import script as S
from explainer_engine.qa import pixels as PX

# --- HYPOTHESIS (REVIEW only): invented for this check, to calibrate on our pictures ------------------------------------------
DETECT_W = 1600  # px: pictures are searched at this width
FACE_SCORE_MIN = 0.6  # YuNet score for a face candidate (painted caricatures score 0.85-0.95, side faces lower)
CONFIDENT_SCORE = 0.85  # a match rewrites the script only at this score or above ...
MATCH_MAX = 0.25  # ... and within this share of the width of the declared point (farther = another figure)
OFF_MAX = 0.08  # FP-OFF: a declared point farther than this share of the width from its matched face
MAX_CANDIDATES = 6  # the best-scoring faces tried per picture (painted crowds)
ID_MIN = 0.45  # SFace cosine to a hero's own painted faces: at least this names the face (measured on titans: the right hero
ID_MARGIN = 0.08  # 0.52-0.76, the next one 0.08-0.4 lower; the same hero looking down scored 0.29) ... and this above the next
SFACE = PX.YUNET.with_name("face_recognition_sface_2021dec.onnx")  # opencv_zoo SFace (Apache-2.0), optional


def _load(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    k = min(1.0, DETECT_W / im.width)
    return np.asarray(im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS))[:, :, ::-1].copy()


def detect(path: Path, model: Path, recognizer=None) -> list[dict]:
    """YuNet faces of one picture: [{x, y (face centre, shares), w, h (shares), score}] (+ ``_emb``, the SFace feature,
    when a recognizer is given)."""
    import cv2
    img = _load(path)
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h), FACE_SCORE_MIN, 0.3, 50)
    _, faces = det.detect(img)
    rows = sorted([] if faces is None else list(faces), key=lambda r: -float(r[14]))[:MAX_CANDIDATES]
    out = []
    for r in rows:
        f = {"x": round(float(r[0] + r[2] / 2) / w, 4), "y": round(float(r[1] + r[3] / 2) / h, 4),
             "w": round(float(r[2]) / w, 4), "h": round(float(r[3]) / h, 4), "score": round(float(r[14]), 3)}
        if recognizer is not None:
            f["_emb"] = recognizer.feature(recognizer.alignCrop(img, r))
        out.append(f)
    return out


def recognizer():
    """OpenCV's SFace (opencv_zoo) when its model is in tools/yunet, else None (then matching is by position only)."""
    cv2 = PX._cv2()
    p = Path(__import__("os").environ.get("EXPLAINER_SFACE") or SFACE)
    if cv2 is None or not p.is_file():
        return None
    return cv2.FaceRecognizerSF.create(str(p), "")


def references(doc: dict, dirs: list[Path], model: Path, rec) -> dict[str, list]:
    """Each hero's own painted faces (his face sheet's close-ups and his reference picture): the SFace features of the
    best face in each."""
    out: dict[str, list] = {}
    for who, c in doc.get("cast", {}).items():
        files = []
        sheet = (c.get("face_sheet") or {}).get("id")
        for d in dirs:
            if sheet:
                files += sorted(Path(d).glob(f"{sheet}_*.png"))
        ref = (c.get("reference") or {}).get("picture")
        if ref:
            files += [Path(d) / f"{ref}.png" for d in dirs if (Path(d) / f"{ref}.png").exists()]
        feats = []
        for f in files:
            faces = detect(f, model, rec)
            if faces:
                feats.append(faces[0]["_emb"])
        if feats:
            out[who] = feats
    return out


def identify(faces: list[dict], refs: dict[str, list], rec, heroes: list[str]) -> dict:
    """{hero: face} for the faces SFace names with confidence: best hero at ID_MIN or more and ID_MARGIN above the next
    (any hero of the cast, so a face of another cast member is never taken for a declared one); each hero keeps his best."""
    import cv2
    best: dict = {}
    for f in faces:
        if "_emb" not in f:
            continue
        sims = sorted(((max(rec.match(f["_emb"], r, cv2.FaceRecognizerSF_FR_COSINE) for r in rs), h)
                       for h, rs in refs.items()), reverse=True)
        f["id"] = [[h, round(float(v), 3)] for v, h in sims[:3]]
        if not sims:
            continue
        v, h = sims[0]
        second = sims[1][0] if len(sims) > 1 else 0.0
        if h in heroes and v >= ID_MIN and v - second >= ID_MARGIN and v > best.get(h, (None, -1))[1]:
            best[h] = (f, v)
    return {h: f for h, (f, _) in best.items()}


def _dist(p, f, aspect: float = 16 / 9) -> float:
    """Distance in shares of the picture's width (a y share is 1/aspect of a width share)."""
    return math.hypot(p[0] - f["x"], (p[1] - f["y"]) / aspect)


def match(speakers: dict, faces: list[dict], aspect: float = 16 / 9) -> dict:
    """{hero: face} for the declared heroes, keeping left-to-right order: of every subset of heroes and of faces of the same
    size (both sorted by x, paired in order), the pairing with the smallest summed distance; then pairs farther than
    MATCH_MAX dropped (that face is another figure)."""
    heroes = sorted(speakers, key=lambda w: speakers[w][0])
    fs = sorted(faces, key=lambda f: f["x"])
    n = min(len(heroes), len(fs))
    best, cost = {}, math.inf
    for k in range(n, 0, -1):
        for hs in itertools.combinations(heroes, k):
            for ff in itertools.combinations(fs, k):
                c = sum(_dist(speakers[h], f, aspect) for h, f in zip(hs, ff))
                if c < cost - 1e-9:
                    best, cost = dict(zip(hs, ff)), c
        if best:
            break  # the most heroes matched wins; fewer only when no face is left
    return {h: f for h, f in best.items() if _dist(speakers[h], f, aspect) <= MATCH_MAX}


def measure(doc: dict, dirs: list[Path], model: Path | None = None) -> dict:
    """face_points.json: per picture with speakers, each hero's declared point, the matched face and the distance."""
    model = model or PX.yunet_path()
    pics, _ = S.pictures(doc)
    out = {"model": str(model) if model else None, "pictures": {}, "missing": [], "off_max": OFF_MAX}
    if model is None or PX._cv2() is None:
        out["skipped"] = "OpenCV or the YuNet model is missing: no face points measured"
        return out
    rec = recognizer()
    refs = references(doc, dirs, model, rec) if rec is not None else {}
    out["identity"] = {"model": "SFace" if rec is not None else None, "heroes_with_references": sorted(refs)}
    for pid, p in sorted(pics.items()):
        speakers = p.get("speakers") or {}
        if not speakers:
            continue
        path = A.find_picture(pid, pics, dirs)
        if path is None:
            out["missing"].append(pid)
            continue
        faces = detect(path, model, rec if refs else None)
        with Image.open(path) as im:
            aspect = im.width / im.height
        named = identify(faces, refs, rec, list(speakers)) if refs else {}
        rest = [f for f in faces if not any(f is g for g in named.values())
                and not (f.get("id") and f["id"][0][1] >= ID_MIN and f["id"][0][0] not in speakers)]
        m = dict(named, **match({h: v for h, v in speakers.items() if h not in named}, rest, aspect))
        rows = {}
        for who, pt in speakers.items():
            f = m.get(who)
            if f is None:
                rows[who] = {"declared": pt, "face": None, "note": "no face matched (seen from behind, off picture, or missed)"}
                continue
            d = _dist(pt, f, aspect)
            others = [g for g in faces if g is not f and _dist(pt, g, aspect) <= MATCH_MAX]
            by = "identity" if who in named else "position"
            if who in named:
                confident = True
            elif who in refs:
                confident = False  # SFace knows him and did not name this face: position alone does not rewrite
            else:
                confident = f["score"] >= CONFIDENT_SCORE and (len(faces) >= len(speakers) or not others)
            rows[who] = {"declared": pt, "face": [f["x"], f["y"]], "box": [f["w"], f["h"]], "score": f["score"],
                         "distance": round(d, 4), "off": d > OFF_MAX, "confident": confident, "matched_by": by}
        for f in faces:
            f.pop("_emb", None)
        out["pictures"][pid] = {"file": str(path), "uses": p.get("uses", []), "faces": faces, "heroes": rows}
    rows = [r for pic in out["pictures"].values() for r in pic["heroes"].values()]
    out["counts"] = {"points": len(rows), "matched": sum(1 for r in rows if r.get("face")),
                     "off": sum(1 for r in rows if r.get("off")), "confident": sum(1 for r in rows if r.get("confident")),
                     "off_confident": sum(1 for r in rows if r.get("off") and r.get("confident")),
                     "pictures": len(out["pictures"])}
    return out


def sheets(measured: dict, out: Path, cols: int = 3, width: int = 560) -> list[str]:
    """Contact sheets to look at: each picture with its declared points (red dot) joined to the matched face (green box)."""
    from PIL import ImageDraw
    tiles = []
    for pid, pic in measured.get("pictures", {}).items():
        with Image.open(pic["file"]) as im:
            t = im.convert("RGB").resize((width, round(width * im.height / im.width)))
        d = ImageDraw.Draw(t)
        W, H = t.size
        for f in pic["faces"]:
            d.rectangle([(f["x"] - f["w"] / 2) * W, (f["y"] - f["h"] / 2) * H, (f["x"] + f["w"] / 2) * W,
                         (f["y"] + f["h"] / 2) * H], outline=(60, 220, 60), width=2)
        for who, r in pic["heroes"].items():
            x, y = r["declared"][0] * W, r["declared"][1] * H
            col = (230, 40, 40) if r.get("off") else (240, 200, 40)
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=col)
            if r.get("face"):
                d.line([x, y, r["face"][0] * W, r["face"][1] * H], fill=col, width=2)
            d.text((x + 7, y - 6), who, fill=col)
        d.rectangle([0, 0, W, 16], fill=(20, 20, 20))
        d.text((4, 2), pid, fill="white")
        tiles.append(t)
    out.mkdir(parents=True, exist_ok=True)
    names = []
    per = cols * 4
    for n in range(0, len(tiles), per):
        part = tiles[n:n + per]
        th = max(t.height for t in part)
        sheet = Image.new("RGB", (cols * (width + 4), ((len(part) + cols - 1) // cols) * (th + 4)), (24, 24, 24))
        for i, t in enumerate(part):
            sheet.paste(t, ((i % cols) * (width + 4), (i // cols) * (th + 4)))
        name = out / f"face_points_{n // per + 1:02d}.jpg"
        sheet.save(name, quality=85)
        names.append(str(name))
    return names


def check(doc: dict, dirs: list[Path], measured: dict | None = None) -> list[dict]:
    """FP-OFF (REVIEW): a declared speaker point farther than OFF_MAX of the width from its matched face."""
    m = measured or measure(doc, dirs)
    out = []
    for pid, pic in m.get("pictures", {}).items():
        for who, r in pic["heroes"].items():
            if r.get("off"):
                out.append({"rule": "FP-OFF", "severity": "REVIEW", "where": f"{pid} {who}", "source": "face_points",
                            "detail": f"{who}'s point {r['declared']} is {r['distance']:.2f} of the width from the face found "
                                      f"at {r['face']} (YuNet {r['score']}, {'confident' if r['confident'] else 'not confident'}"
                                      f"): bubble tails and rings use this point (shots {', '.join(pic['uses'][:6])})"})
    return out


def apply(doc: dict, measured: dict) -> list[dict]:
    """Rewrite only the confident, off points in the script's picture definitions; returns what changed."""
    changed = []
    want = {(pid, who): r["face"] for pid, pic in measured.get("pictures", {}).items()
            for who, r in pic["heroes"].items() if r.get("off") and r.get("confident")}
    for p in [doc.get("library", {}).get(k) for k in doc.get("library", {})] + \
             [s["picture"] for seg in doc["segments"] for s in seg["shots"] if isinstance(s["picture"], dict)]:
        pid = p.get("id") if p else None
        for who in list((p or {}).get("speakers") or {}):
            new = want.get((pid, who))
            if new is not None:
                old = p["speakers"][who]
                p["speakers"][who] = [round(new[0], 3), round(new[1], 3)]
                changed.append({"picture": pid, "who": who, "old": old, "new": p["speakers"][who]})
    return changed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.qa.face_points", description=__doc__.split("\n")[0])
    p.add_argument("script")
    p.add_argument("--pics", action="append")
    p.add_argument("--out", type=Path)
    p.add_argument("--apply", action="store_true", help="rewrite the confident off points in the script")
    p.add_argument("--sheets", type=Path, help="write contact sheets (declared point -> matched face) to this folder")
    a = p.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    dirs = [Path(x) for x in a.pics or []] + [path.parent / x for x in doc.get("picture_dirs", [])]
    m = measure(doc, dirs)
    out = a.out or path.with_name("face_points.json")
    if a.sheets and m.get("pictures"):
        m["sheets"] = sheets(m, a.sheets)
    if a.apply:
        m["applied"] = apply(doc, m)
        S.save(doc, path)
    write_json_atomic(out, m)
    if m.get("skipped"):
        print(m["skipped"])
        return 0
    c = m["counts"]
    print(f"face points: {c['pictures']} pictures, {c['points']} declared points, {c['matched']} matched to a face, "
          f"{c['off']} off by more than {OFF_MAX} of the width ({c['off_confident']} confident); missing pictures: "
          f"{len(m['missing'])}")
    for f in check(doc, dirs, m):
        print(f"  REVIEW FP-OFF {f['where']}: {f['detail'][:150]}")
    if a.apply:
        print(f"  applied {len(m['applied'])} confident point(s) to {path}")
    print(f"  {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
