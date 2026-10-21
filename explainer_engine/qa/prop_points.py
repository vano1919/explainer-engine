"""Prop points found on the painted pictures (the creator's CC-03, 2026-10-20: "props appear only because a rule demands
them"). The beat-writer writes a ring's or a label's ``pos`` without seeing the picture; on titans 59 of 82 rings and labels
whose phrase names no hero were such guesses (template values like [0.5, 0.72]) and circled empty wall or floor ('wooden
bench', 'price tags', 'stack of white envelopes'). A ring on nothing is worse than no ring (RX-12, BP-93). Free and local:
an open-vocabulary detector (OWLv2, ``google/owlv2-base-patch16-ensemble``, Apache-2.0, through ``transformers`` on the CPU)
looks for the beat's phrase in the picture its shot shows.

    python -m explainer_engine.qa.prop_points <script.json> [--words words.json | --timed timed.json] [--pics DIR ...]
                                              [--out prop_points.json] [--sheets DIR] [--apply]

1. The beats are timed as ``production time`` times them (``timing.time_script`` on the read's ``words.json``, else the
   estimated read; ``--timed`` reuses a timing): each timed beat names its ``shot`` and ``picture``.
2. A prop beat is a ``highlight`` or ``label`` whose phrase (a label: or its tag) names no hero of the cast. Rings and labels
   naming a hero are not measured here: they snap to the hero's face point (``beats.fit_to_views``, ``qa/face_points``).
3. Per picture one detector pass with every prop phrase of that picture (leading small words dropped: "this bench" ->
   "bench"; a verb phrase also as its thing: "reads the screen" -> "screen"). A box scoring SCORE_MIN or more is a find.
   Decision per beat: ``keep`` (its pos already lies in a found box, or a label names the place the whole picture shows),
   ``move`` (pos = the centre of the best found box), ``drop`` (nothing found, or a ring whose only find is the whole
   picture: the beat is proposed for removal).
4. ``prop_points.json`` and, with ``--sheets``, contact sheets: old pos (red dot) -> found box (green) per beat.
5. ``--apply`` rewrites ``pos`` of the moves and removes the dropped beats from the script (nothing else), written as
   ``json.dumps(indent=2, ensure_ascii=False)`` so the diff stays small.
6. ``check`` (run by ``qa/loop``): PB-OFF REVIEW for a prop beat whose pos lies farther than OFF_MAX of the width from its
   found box, PB-NONE REVIEW for a prop beat whose phrase is found nowhere in its picture. Never FAIL: an open-vocabulary
   detector on painted pictures is a heuristic and the numbers below are hypotheses.

Without ``torch`` / ``transformers`` or the model (``$EXPLAINER_OWL_MODEL`` names another one or a local folder) the tool
measures nothing and says so.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from PIL import Image

from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.production import assemble as A
from explainer_engine.production import beats as BEATS
from explainer_engine.production import script as S

MODEL = "google/owlv2-base-patch16-ensemble"  # OWLv2 (Minderer et al. 2023), Apache-2.0; OWL-ViT works through the same API
KINDS = ("highlight", "label")
# --- HYPOTHESIS (REVIEW only): invented for this check, tuned by eye on the titans pictures (2026-10-20) -----------------------
SCORE_MIN = 0.23  # OWLv2 score for a find: on the titans sheets the right object scored 0.23 (a monitor, an open mouth) to
#                   0.85 (a hot dog); abstract phrases ('inside their heads', 'last line', 'price tags', 'heat test') under 0.18
SCORE_FLOOR = 0.05  # boxes below this are not kept at all (the sheets still show the best one under SCORE_MIN)
SCENE_AREA = 0.3  # a found box covering this share of the picture or more is the place itself (a hallway, a parking lot):
#                   a label naming the place keeps its pos; a ring cannot circle a whole picture, so it is dropped
OFF_MAX = 0.05  # PB-OFF: a pos farther than this share of the width from its found box (the ring's radius is ~0.07)
MAX_BOXES = 20  # boxes kept per phrase (a pos inside any find stays: 'the man beside them' is one of ten men)
_DET = {"the", "a", "an", "this", "that", "these", "those", "his", "her", "their", "its", "our", "my", "your"}
_LEAD = {"with", "the", "a", "an", "this", "that", "these", "those", "his", "her", "their", "its", "our", "my", "your", "one", "some",
         "every", "each", "inside", "into", "on", "at", "of", "in"}


def query(phrase: str) -> str:
    """The detector's text for a beat's phrase: leading small words dropped ("inside their heads" -> "heads")."""
    words = re.findall(r"[A-Za-z0-9$'%-]+", phrase or "")
    while len(words) > 1 and words[0].lower() in _LEAD:
        words = words[1:]
    return " ".join(words).lower()


def queries(phrase: str) -> list[str]:
    """The detector's texts for a phrase, the preferred first: for a verb or place phrase the thing after its last article
    or possessive ("reads the screen" -> "screen", "a man in a grey suit" -> "grey suit"), then the whole query. The
    detector knows things better than actions: on titans "reads the screen" scored 0.33 on a far monitor seen through a
    window, "screen" found the teller's own; "taps his card" found the card reader where "card" found nothing."""
    q = query(phrase)
    words = q.split()
    cut = max((i for i, w in enumerate(words) if w in _DET), default=-1)
    return [" ".join(words[cut + 1:]), q] if 0 <= cut < len(words) - 1 else [q]


def hero_named(b: dict, cast: dict) -> list[str]:
    named = BEATS.named_heroes(b.get("at", ""), cast)
    if not named and b.get("kind") == "label":
        named = BEATS.named_heroes(b.get("text", ""), cast)
    return named


def is_prop(b: dict, cast: dict) -> bool:
    return b.get("kind") in KINDS and not hero_named(b, cast)


class OwlDetector:
    """OWLv2 / OWL-ViT through ``transformers`` on the CPU: ``(image, [text]) -> [[{box (shares x0 y0 x1 y1), score}]]``."""

    def __init__(self, name: str = MODEL):
        import torch
        from transformers import AutoProcessor
        try:
            from transformers import Owlv2ForObjectDetection as Model
        except ImportError:  # an old transformers: OWL-ViT only
            from transformers import OwlViTForObjectDetection as Model
        if "owlvit" in name:
            from transformers import OwlViTForObjectDetection as Model
        self.torch = torch
        self.name = name
        self.processor = AutoProcessor.from_pretrained(name)
        self.model = Model.from_pretrained(name).eval()

    def __call__(self, image: Image.Image, texts: list[str]) -> list[list[dict]]:
        torch = self.torch
        im = image.convert("RGB")
        with torch.no_grad():
            inputs = self.processor(text=[texts], images=im, return_tensors="pt")
            outputs = self.model(**inputs)
        # OWLv2 pads the picture to a square at its bottom / right: boxes come back in the square's pixels
        side = max(im.size) if "owlv2" in self.name else None
        size = [[side, side]] if side else [[im.height, im.width]]
        res = self.processor.post_process_grounded_object_detection(
            outputs, threshold=SCORE_FLOOR, target_sizes=torch.tensor(size), text_labels=[texts])[0]
        out: list[list[dict]] = [[] for _ in texts]
        for box, score, label in zip(res["boxes"], res["scores"], res["labels"]):
            x0, y0, x1, y1 = (float(v) for v in box)
            out[int(label)].append({"box": [round(max(0.0, x0 / im.width), 4), round(max(0.0, y0 / im.height), 4),
                                            round(min(1.0, x1 / im.width), 4), round(min(1.0, y1 / im.height), 4)],
                                    "score": round(float(score), 3)})
        return [sorted(r, key=lambda b: -b["score"])[:MAX_BOXES] for r in out]


_DETECTOR: dict = {}


def detector():
    """The OWL detector, loaded once; None (with the reason in ``detector_error``) without torch, transformers or the model."""
    import os
    name = os.environ.get("EXPLAINER_OWL_MODEL") or MODEL
    if name not in _DETECTOR:
        try:
            _DETECTOR[name] = OwlDetector(name)
        except Exception as e:  # noqa: BLE001 - missing package, no network, no cached model: the check says so and skips
            _DETECTOR[name] = None
            _DETECTOR["error"] = f"{type(e).__name__}: {e}"[:300]
    return _DETECTOR[name]


def detector_error() -> str:
    return _DETECTOR.get("error", "")


def inside(pos, box) -> bool:
    return box[0] <= pos[0] <= box[2] and box[1] <= pos[1] <= box[3]


def box_dist(pos, box, aspect: float = 16 / 9) -> float:
    """Distance from a point to a box, in shares of the picture's width (0 inside it)."""
    dx = max(box[0] - pos[0], 0.0, pos[0] - box[2])
    dy = max(box[1] - pos[1], 0.0, pos[1] - box[3])
    return math.hypot(dx, dy / aspect)


def area(box) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def centre(box) -> list[float]:
    return [round((box[0] + box[2]) / 2, 3), round((box[1] + box[3]) / 2, 3)]


def script_beats(doc: dict) -> list[dict]:
    """Every ring / label of the script: segment, line (1-based), index in the line's beats, the beat."""
    out = []
    for seg in doc["segments"]:
        for li, line in enumerate(seg["lines"]):
            for bi, b in enumerate(line.get("visual_beats") or []):
                if b.get("kind") in KINDS:
                    out.append({"segment": seg["id"], "line": li + 1, "index": bi, "beat": b})
    return out


def pair_timed(doc: dict, timed_beats: list[dict]) -> dict[tuple, dict]:
    """(segment, line, index) of a script beat -> its timed beat (same line, same kind and phrase, in order)."""
    by_line: dict[tuple, list] = {}
    for t in timed_beats:
        if t.get("kind") in KINDS:
            by_line.setdefault((t["segment"], t["line"]), []).append(t)
    out = {}
    for row in script_beats(doc):
        q = by_line.get((row["segment"], row["line"]), [])
        for k, t in enumerate(q):
            if t["kind"] == row["beat"]["kind"] and t.get("at") == row["beat"].get("at"):
                out[(row["segment"], row["line"], row["index"])] = t
                del q[k]
                break
    return out


def time_doc(doc: dict, words: Path | None) -> dict:
    from explainer_engine.production import timing as T
    from explainer_engine.production import validate as V
    words_doc = json.loads(Path(words).read_text(encoding="utf-8")) if words else V.estimated_words(doc)
    return T.time_script(doc, words_doc)


def measure(doc: dict, timed: dict, dirs: list[Path], detect=None, only_pictures: set | None = None) -> dict:
    """prop_points.json: per prop beat its shot, picture, old pos, the boxes found for its phrase and the decision."""
    cast = doc.get("cast", {})
    out: dict = {"model": None, "score_min": SCORE_MIN, "off_max": OFF_MAX, "beats": [], "missing": [], "hero_beats": 0,
                 "not_timed": []}
    if detect is None:
        detect = detector()
        if detect is None:
            out["skipped"] = f"no detector (torch / transformers / {MODEL}): no prop points measured. {detector_error()}"
            return out
    out["model"] = getattr(detect, "name", type(detect).__name__)
    pics, _ = S.pictures(doc)
    paired = pair_timed(doc, timed.get("visual_beats", []))
    rows = []
    for r in script_beats(doc):
        b = r["beat"]
        if not is_prop(b, cast):
            out["hero_beats"] += 1
            continue
        t = paired.get((r["segment"], r["line"], r["index"]))
        if t is None:
            out["not_timed"].append({k: r[k] for k in ("segment", "line", "index")} | {"at": b.get("at")})
            continue
        if only_pictures is not None and t["picture"] not in only_pictures:
            continue
        rows.append(dict(segment=r["segment"], line=r["line"], index=r["index"], kind=b["kind"], at=b.get("at"),
                         text=b.get("text"), shot=t["shot"], picture=t["picture"], start=t.get("start"),
                         pos=list(b.get("pos") or BEATS.DEFAULT_POS.get(b["kind"], (0.5, 0.5))), query=query(b.get("at"))))
    by_pic: dict[str, list] = {}
    for row in rows:
        by_pic.setdefault(row["picture"], []).append(row)
    for pid, group in sorted(by_pic.items()):
        path = A.find_picture(pid, pics, dirs)
        if path is None:
            out["missing"].append(pid)
            for row in group:
                row.update(decision="missing", file=None)
            continue
        with Image.open(path) as im:
            image = im.convert("RGB")
        aspect = image.width / image.height
        texts = sorted({q for row in group for q in queries(row["at"])})
        found = dict(zip(texts, detect(image, texts)))
        for row in group:
            boxes = sorted((dict(b, query=q) for q in queries(row["at"]) for b in found.get(q, [])), key=lambda b: -b["score"])
            good = next(([dict(b, query=q) for b in found.get(q, []) if b["score"] >= SCORE_MIN] for q in queries(row["at"])
                         if any(b["score"] >= SCORE_MIN for b in found.get(q, []))), [])  # the preferred text with a find
            row.update(file=str(path), boxes=boxes[:3], best=boxes[0] if boxes else None)
            scene = [b for b in good if area(b["box"]) >= SCENE_AREA]
            things = [b for b in good if area(b["box"]) < SCENE_AREA]
            holding = [b for b in things if inside(row["pos"], b["box"])]
            if holding:
                row.update(decision="keep", found=holding[0], distance=0.0, new_pos=row["pos"])
            elif scene and (row["kind"] == "label" or good[0] is scene[0]):  # the best find is the whole picture
                if row["kind"] == "label":  # the place itself: any spot of the picture names it
                    row.update(decision="keep", found=scene[0], distance=0.0, new_pos=row["pos"], scene=True)
                else:
                    row.update(decision="drop", found=None, distance=None, new_pos=None, scene=True)
            elif things:
                row.update(decision="move", found=things[0], distance=round(box_dist(row["pos"], things[0]["box"], aspect), 4),
                           new_pos=centre(things[0]["box"]))
            else:
                row.update(decision="drop", found=None, distance=None, new_pos=None)
    out["beats"] = sorted(rows, key=lambda r: (r.get("start") or 0.0, r["segment"], r["line"], r["index"]))
    out["counts"] = {d: sum(1 for r in rows if r.get("decision") == d) for d in ("keep", "move", "drop", "missing")}
    out["counts"]["prop_beats"] = len(rows)
    out["counts"]["off"] = sum(1 for r in rows if r.get("decision") == "move" and r["distance"] > OFF_MAX)
    return out


def check(measured: dict) -> list[dict]:
    """PB-OFF / PB-NONE (REVIEW): a prop beat's pos away from its found box, or its phrase found nowhere in its picture."""
    out = []
    for r in measured.get("beats", []):
        where = f"{r['segment']} line {r['line']} {r['shot']} {r['kind']} {r['at']!r}"
        base = {"severity": "REVIEW", "where": where, "shot": r["shot"], "source": "prop_points"}
        if r.get("decision") == "move" and r["distance"] > OFF_MAX:
            out.append(dict(base, rule="PB-OFF", detail=f"pos {r['pos']} is {r['distance']:.2f} of the width from "
                            f"{r['query']!r} found at {r['found']['box']} (score {r['found']['score']}) in {r['picture']}: "
                            f"move it to {r['new_pos']}"))
        elif r.get("decision") == "drop":
            best = r.get("best")
            what = (f"{r['query']!r} is the whole picture, a ring cannot circle it" if r.get("scene") else
                    f"{r['query']!r} is not found in {r['picture']} (best score {best['score'] if best else 0} < {SCORE_MIN})")
            out.append(dict(base, rule="PB-NONE", detail=f"{what}: a ring on nothing is worse than no ring (CC-03, BP-93): "
                            "drop the beat or name what the picture shows"))
    return out


def apply(doc: dict, measured: dict) -> dict:
    """Moves rewrite ``pos``; drops remove the beat from its line. Returns {moved: [...], dropped: [...]}."""
    segs = {s["id"]: s for s in doc["segments"]}
    moved, dropped, gone = [], [], {}
    for r in measured.get("beats", []):
        line = segs[r["segment"]]["lines"][r["line"] - 1]
        b = line["visual_beats"][r["index"]]
        if b.get("at") != r["at"] or b.get("kind") != r["kind"]:
            continue  # the script changed since it was measured
        if r["decision"] == "move":
            b["pos"] = list(r["new_pos"])
            moved.append({"segment": r["segment"], "line": r["line"], "at": r["at"], "old": r["pos"], "new": b["pos"]})
        elif r["decision"] == "drop":
            gone.setdefault((r["segment"], r["line"] - 1), set()).add(r["index"])
            dropped.append({"segment": r["segment"], "line": r["line"], "at": r["at"], "pos": r["pos"]})
    for (sid, li), idx in gone.items():
        line = segs[sid]["lines"][li]
        line["visual_beats"] = [b for k, b in enumerate(line["visual_beats"]) if k not in idx]
    return {"moved": moved, "dropped": dropped}


def save(doc: dict, path: Path) -> None:
    write_text_atomic(Path(path), json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def sheets(measured: dict, out: Path, cols: int = 3, width: int = 560) -> list[str]:
    """Contact sheets: each prop beat on its picture, old pos (red dot) -> found box (green; grey = best box below
    SCORE_MIN), with the decision."""
    from PIL import ImageDraw
    tiles = []
    cache: dict = {}
    for r in measured.get("beats", []):
        if not r.get("file"):
            continue
        if r["file"] not in cache:
            with Image.open(r["file"]) as im:
                cache[r["file"]] = im.convert("RGB").resize((width, round(width * im.height / im.width)))
        t = cache[r["file"]].copy()
        d = ImageDraw.Draw(t)
        W, H = t.size
        best = r.get("found") or r.get("best")
        if best:
            x0, y0, x1, y1 = best["box"]
            col = (60, 220, 60) if r.get("found") else (150, 150, 150)
            d.rectangle([x0 * W, y0 * H, x1 * W, y1 * H], outline=col, width=3)
            d.text((x0 * W + 3, y1 * H - 13), f"{best['score']:.2f}", fill=col)
        x, y = r["pos"][0] * W, r["pos"][1] * H
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(230, 40, 40))
        if r.get("decision") == "move":
            nx, ny = r["new_pos"][0] * W, r["new_pos"][1] * H
            d.line([x, y, nx, ny], fill=(240, 200, 40), width=2)
            d.ellipse([nx - 5, ny - 5, nx + 5, ny + 5], outline=(240, 200, 40), width=2)
        colour = {"keep": (60, 200, 60), "move": (240, 200, 40), "drop": (230, 60, 60)}.get(r.get("decision"), (200, 200, 200))
        d.rectangle([0, 0, W, 30], fill=(20, 20, 20))
        d.text((4, 2), f"{r['shot']} {r['picture']}  {r['kind']} {r['at']!r}", fill="white")
        d.text((4, 16), f"{r.get('decision', '?').upper()}  q={r['query']!r}", fill=colour)
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
        name = out / f"prop_points_{n // per + 1:02d}.jpg"
        sheet.save(name, quality=85)
        names.append(str(name))
    return names


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m explainer_engine.qa.prop_points", description=__doc__.split("\n")[0])
    p.add_argument("script")
    p.add_argument("--words", type=Path, help="the read's words.json (default: the estimated read)")
    p.add_argument("--timed", type=Path, help="reuse a timed.json instead of timing the script")
    p.add_argument("--pics", action="append")
    p.add_argument("--out", type=Path)
    p.add_argument("--sheets", type=Path, help="write contact sheets (old pos -> found box) to this folder")
    p.add_argument("--apply", action="store_true", help="move the found ones, remove the ones found nowhere")
    a = p.parse_args(argv)
    path = Path(a.script)
    doc = S.load(path)
    dirs = [Path(x) for x in a.pics or []] + [path.parent / x for x in doc.get("picture_dirs", [])]
    timed = json.loads(a.timed.read_text(encoding="utf-8")) if a.timed else time_doc(doc, a.words)
    m = measure(doc, timed, dirs)
    out = a.out or path.with_name("prop_points.json")
    if m.get("skipped"):
        write_json_atomic(out, m)
        print(m["skipped"])
        return 0
    if a.sheets and m["beats"]:
        m["sheets"] = sheets(m, a.sheets)
    if a.apply:
        m["applied"] = apply(doc, m)
        save(doc, path)
    write_json_atomic(out, m)
    c = m["counts"]
    print(f"prop points ({m['model']}): {c['prop_beats']} prop rings / labels ({m['hero_beats']} hero ones not measured, "
          f"{len(m['not_timed'])} not drawn by the timing): keep {c['keep']}, move {c['move']} ({c['off']} off by more than "
          f"{OFF_MAX}), drop {c['drop']}, missing picture {c['missing']}")
    for f in check(m):
        print(f"  REVIEW {f['rule']} {f['where']}: {f['detail'][:140]}")
    if a.apply:
        print(f"  applied: {len(m['applied']['moved'])} moved, {len(m['applied']['dropped'])} dropped in {path}")
    print(f"  {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
