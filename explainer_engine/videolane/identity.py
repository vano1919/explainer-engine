"""The hero identity rows of the video lane (Fable audit 2026-11-13, FA-14): checked on the storyboard's pictures BEFORE a
paid LTX scene (VL-10) and again on the clips at G10 (``videolane/master_qa``), with tools the repo already has, all free:

* costume and colours: each hero's box (from the shot's ``edit_plan.screen_positions``: left, centre or right third of the
  frame) is compared between two consecutive shots of one scene with ``training/video_qa.shot_identity``'s hero palette
  distance against BP-166's ``hero_palette_max`` (a changed helmet colour moves it);
* the face: OpenCV SFace (``qa/face_points``) names the faces of a shot's picture against the heroes' reference pictures;
  a hero listed on the shot whose face is not found is listed. Without the YuNet/SFace models or the references the row
  is REVIEW and says NOT MEASURED (never a pass; a person looks at the sheet);
* the continuity-card questions (``scripting/continuity.vision_questions``) go with the contact sheet for the look by
  Claude (``qa/sheet_review``) and the creator.

How strict (switch Q3 of config/creator_open_questions.json): REVIEW (default until the creator answers), FAIL, or
FAIL_FACE_REVIEW_COSTUME (Fable's recommendation). The boxes are an engineering default (thirds of the frame), not a
detector: a REVIEW asks a person to look."""
from __future__ import annotations

from pathlib import Path

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

BOX = {"left": (0.0, 0.1, 0.5, 1.0), "centre": (0.25, 0.1, 0.75, 1.0), "center": (0.25, 0.1, 0.75, 1.0),
       "right": (0.5, 0.1, 1.0, 1.0)}


def levels() -> dict:
    from explainer_engine.core import open_questions as OQ
    v = OQ.value("Q3")
    return {"face": G.FAIL if v in ("FAIL", "FAIL_FACE_REVIEW_COSTUME") else G.REVIEW,
            "costume": G.FAIL if v == "FAIL" else G.REVIEW}


def _head(box: tuple) -> tuple:
    x0, y0, x1, y1 = box
    return (x0, y0, x1, y0 + HEAD_SHARE * (y1 - y0))


HEAD_SHARE = 0.35   # engineering default: the top of a standing hero's box holds the head and headgear


def _positions(script: dict, shot: dict) -> dict:
    from explainer_engine.videolane import plan as P
    ep = shot.get("edit_plan") or {}
    notes = str((shot.get("screen_composition") or {}).get("screen_direction_notes") or "")
    return dict(ep.get("screen_positions") or P._positions(script, shot, notes))


def costume_findings(script: dict, shot_ids: list[str], frames: dict) -> list[str]:
    """``frames``: ``{shot_id: (first RGB array, last RGB array)}`` (a picture gives the same array twice). Every hero seen
    in two consecutive shots is compared, the earlier shot's last frame against the later one's first."""
    from explainer_engine.training import video_qa as VQ
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    lim = float(SR.T("BP-166", "hero_palette_max"))
    out = []
    ids = [s for s in shot_ids if s in frames]
    for a, b in zip(ids, ids[1:]):
        pa, pb = _positions(script, by[a]), _positions(script, by[b])
        both = [h for h in sorted(set(pa) & set(pb)) if pa[h] in BOX and pb[h] in BOX]
        heroes = [{"label": h, "a": BOX[pa[h]], "b": BOX[pb[h]]} for h in both]
        # the head third of the box on its own: a helmet, hat or hair change is a small share of the whole body box
        # (the video-lane report's missed helmet; measured in the test: 0.08 on the body box, over 0.15 on the head)
        heroes += [{"label": f"{h} (head)", "a": _head(BOX[pa[h]]), "b": _head(BOX[pb[h]])} for h in both]
        if not heroes:
            continue
        m = VQ.shot_identity(frames[a][1], frames[b][0], heroes)
        out += [f"{h} {a} -> {b}: colours move {d} (> {lim}): clothes, skin or hair changed" for h, d in m["heroes"].items()
                if d > lim]
    return out


FACE_TOO_SMALL = ("extreme_wide", "wide")   # Q3: measured on the 11-12 battle, a hero's face in a wide is ~3 % of the
# frame width; SFace named none of them and once named a soldier at the edge: a wide shot's faces are not judged


def facing_of(root: Path) -> dict:
    """``{shot_id: {hero: facing}}`` from the episode's continuity cards (``planning/continuity/*.json``, continuity_card/1);
    a hero facing ``away`` shows no face to judge."""
    import json
    out: dict = {}
    for f in sorted((Path(root) / "planning" / "continuity").glob("*.json")):
        try:
            card = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for sh in card.get("shots") or []:
            out[sh.get("shot_id")] = {c.get("id"): c.get("facing") for c in sh.get("characters") or []}
    return out


def face_findings(script: dict, shot_ids: list[str], pictures: dict, references: dict,
                  facing: dict | None = None) -> list[str] | None:
    """None when the face tools or the references are missing (NOT_RUN); else the heroes whose face SFace does not name.
    Wide shots (``FACE_TOO_SMALL``) are not judged: their faces are too small to name."""
    from explainer_engine.qa import face_points as FP
    from explainer_engine.qa import pixels as PX
    model = PX.YUNET
    rec = FP.recognizer()
    refs_present = {h: Path(p) for h, p in references.items() if Path(p).is_file()}
    if rec is None or not Path(model).is_file() or not refs_present:
        return None
    feats = {}
    for h, p in refs_present.items():
        faces = FP.detect(p, model, rec)
        if faces:
            feats[h] = [faces[0]["_emb"]]
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    out = []
    for sid in shot_ids:
        if sid not in pictures:
            continue
        heroes = [h for h in by[sid].get("character_ids") or [] if h in feats
                  and ((facing or {}).get(sid) or {}).get(h) != "away"]
        if not heroes or (by[sid].get("camera_spec") or {}).get("shot_size") in FACE_TOO_SMALL:
            continue
        named = FP.identify(FP.detect(Path(pictures[sid]), model, rec), feats, rec, heroes)
        out += [f"{sid}: {h}'s face is not found" for h in heroes if h not in named]
    return out


REVIEW_SCHEMA = "costume_review/1"
EYE_KEYS = ("same_headgear", "same_props", "same_clothes")


def hero_cuts(script: dict, shot_ids: list[str]) -> list[dict]:
    """The cuts between consecutive shots that show a hero on both sides (``character_ids`` or screen positions):
    ``[{"cut": "A->B", "a", "b", "heroes"}]``. These are the cuts a person looks at for helmets, props and clothes."""
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    ids = [s for s in shot_ids if s in by]
    out = []
    for a, b in zip(ids, ids[1:]):
        ha = set(by[a].get("character_ids") or []) | set(_positions(script, by[a]))
        hb = set(by[b].get("character_ids") or []) | set(_positions(script, by[b]))
        both = sorted(ha & hb)
        if both:
            out.append({"cut": f"{a}->{b}", "a": a, "b": b, "heroes": both})
    return out


def eye_findings(review: dict | None, cuts: list[dict]) -> tuple[list[str], list[str]]:
    """Q3 (the creator 2026-11-13, answer c; D-138): the eye check of headgear, props and clothes across each hero cut
    (``costume_review/1``: ``{"by", "cuts": {"A->B": {same_headgear, same_props, same_clothes, note}}}``), because the palette
    alone missed the 11-12 helmet (0.094 on the head box against BP-166's 0.15). Returns (findings, cuts not looked at)."""
    looked = (review or {}).get("cuts") or {}
    if review and review.get("schema") != REVIEW_SCHEMA:
        raise ValueError(f"costume review schema {review.get('schema')!r} is not {REVIEW_SCHEMA}")
    out, unlooked = [], []
    for c in cuts:
        a = looked.get(c["cut"])
        if not a or any(k not in a for k in EYE_KEYS):
            unlooked.append(c["cut"])
            continue
        changed = [k.replace("same_", "") for k in EYE_KEYS if a[k] is False]
        if changed:
            out.append(f"{c['cut']}: {', '.join(changed)} changed by eye ({a.get('note') or 'no note'})")
    return out, unlooked


def cut_sheet(frames: dict, cuts: list[dict], out: Path, width: int = 640) -> Path:
    """The sheet the eye check reads: per hero cut, A's last frame beside B's first, labelled."""
    from PIL import Image, ImageDraw
    import numpy as np
    pairs = [(c, frames[c["a"]][1], frames[c["b"]][0]) for c in cuts if c["a"] in frames and c["b"] in frames]
    if not pairs:
        raise ValueError("no hero cut with frames on both sides")
    h = int(width * pairs[0][1].shape[0] / pairs[0][1].shape[1])
    sheet = Image.new("RGB", (2 * width, (h + 24) * len(pairs)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    for k, (c, fa, fb) in enumerate(pairs):
        y = k * (h + 24)
        d.text((6, y + 4), f"{c['cut']}  heroes: {', '.join(c['heroes'])}  (left: last frame of {c['a']}, right: first of "
                           f"{c['b']})", fill=(240, 240, 240))
        for j, f in enumerate((fa, fb)):
            sheet.paste(Image.fromarray(np.asarray(f, np.uint8)).resize((width, h)), (j * width, y + 24))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=90)
    return out


def rows(script: dict, shot_ids: list[str], frames: dict, pictures: dict, references: dict, where: str,
         review: dict | None = None, facing: dict | None = None) -> list[dict]:
    lv = levels()
    cost = costume_findings(script, shot_ids, frames)
    eye, unlooked = eye_findings(review, hero_cuts(script, shot_ids))
    face = face_findings(script, shot_ids, pictures, references, facing)
    cost_all = cost + eye
    cost_row = G.row(f"{where}_hero_costume_holds", not cost_all, f"{len(cost)} hero box(es) whose colours move across a "
                     f"cut (BP-166 hero_palette_max), {len(eye)} change(s) seen by eye (switch Q3 -> {lv['costume']})",
                     cost_all[:20], level=lv["costume"])
    if not cost_all and unlooked:   # Q3: a palette PASS alone never clears a helmet; the eye check is a warning, never a stop
        cost_row = G.row(f"{where}_hero_costume_holds", False, f"the palette sees no change, {len(unlooked)} hero cut(s) "
                         "wait for the eye check of headgear, props and clothes (costume_review/1; the palette missed the "
                         "11-12 helmet)", unlooked[:20], level=G.REVIEW)
    face_row = (G.row(f"{where}_hero_face_holds", False, "NOT MEASURED: the face tools (tools/yunet YuNet + SFace) or the "
                      "hero references are missing; a person looks at the sheet" + (
                          "; switch Q3 makes the face binding: a paid scene is refused until it is measured"
                          if lv["face"] == G.FAIL else ""), None, level=G.REVIEW) if face is None else
                G.row(f"{where}_hero_face_holds", not face, f"{len(face)} hero face(s) SFace does not name (switch Q3 -> "
                      f"{lv['face']})", face[:20], level=lv["face"]))
    return [cost_row, face_row]


def face_not_measured(record: dict) -> bool:
    """A storyboard record whose face row could not measure (Q3: binding face -> no paid scene)."""
    return any(r.get("gate") == "storyboard_hero_face_holds" and str(r.get("detail", "")).startswith("NOT MEASURED")
               for r in record.get("rows") or [])


def references_of(root: Path, script: dict) -> dict:
    """The heroes' reference pictures: ``assets/reference/characters/<id>.jpg`` (the episode's asset registry layout)."""
    return {c["character_id"]: Path(root) / "assets" / "reference" / "characters" / f"{c['character_id']}.jpg"
            for c in (script.get("world_bible") or {}).get("characters", [])}


def check_joined(clip: Path, cut_frames: list[int], script: dict, out_dir: Path, review: dict | None = None,
                 references: dict | None = None) -> dict:
    """Q3 on a joined clip that is already made (a master or a test scene, e.g. the 11-12 battle): the shots of ``script`` in
    order, separated at ``cut_frames``; writes ``<out_dir>/cuts.jpg`` (the eye check's sheet) and ``identity.json`` with the
    rows. Free: frames only, no generation."""
    from explainer_engine.training import video_qa as VQ
    frames_all = VQ.read_video(clip, width=640)[0]
    ids = [s["shot_id"] for s in script.get("shots", [])]
    if len(ids) != len(cut_frames) + 1:
        raise ValueError(f"{len(ids)} shots need {len(ids) - 1} cut frames, got {len(cut_frames)}")
    bounds = [0] + list(cut_frames) + [len(frames_all)]
    frames = {sid: (frames_all[bounds[k]], frames_all[bounds[k + 1] - 1]) for k, sid in enumerate(ids)}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pictures = {}
    if references:
        from PIL import Image
        for k, sid in enumerate(ids):   # the face check reads a picture per shot: the middle frame of the shot at full size
            mid = (bounds[k] + bounds[k + 1]) // 2
            p = out_dir / f"{sid}_mid.png"
            Image.fromarray(_frame_at(clip, mid)).save(p)
            pictures[sid] = p
    cuts = hero_cuts(script, ids)
    sheet = cut_sheet(frames, cuts, out_dir / "cuts.jpg") if cuts else None
    facing = {s["shot_id"]: s["facing"] for s in script.get("shots", []) if s.get("facing")}
    rows_ = rows(script, ids, frames, pictures, references or {}, "clip", review=review, facing=facing)
    rec = {"clip": str(clip), "cut_frames": list(cut_frames), "cuts": cuts, "sheet": str(sheet) if sheet else None,
           "rows": rows_, "verdict": G.verdict(rows_), "switch_q3": levels()}
    from explainer_engine.core.store import write_json_atomic
    write_json_atomic(out_dir / "identity.json", rec)
    return rec


def _frame_at(clip: Path, n: int):
    import subprocess
    import numpy as np
    j = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of",
                        "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h = int(j[0]), int(j[1])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"select=eq(n\\,{n})", "-vframes", "1", "-f",
                          "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def main(argv=None) -> int:
    """python -m explainer_engine.videolane.identity <clip.mp4> <scene.json> <out_dir> --cuts 160,250,442 [--review r.json]
    [--refs hero=path,...]; ``scene.json`` is a script-shaped ``{"shots": [...], "world_bible": ...}``; exit 1 on a FAIL."""
    import argparse
    import json
    ap = argparse.ArgumentParser(prog="videolane.identity")
    ap.add_argument("clip")
    ap.add_argument("scene")
    ap.add_argument("out_dir")
    ap.add_argument("--cuts", required=True)
    ap.add_argument("--review")
    ap.add_argument("--refs", default="")
    a = ap.parse_args(argv)
    script = json.loads(Path(a.scene).read_text(encoding="utf-8"))
    review = json.loads(Path(a.review).read_text(encoding="utf-8")) if a.review else None
    refs = dict(kv.split("=", 1) for kv in a.refs.split(",") if kv)
    rec = check_joined(Path(a.clip), [int(x) for x in a.cuts.split(",")], script, Path(a.out_dir), review, refs or None)
    for r in rec["rows"]:
        print(f"{r['status']:7} {r['gate']}: {r['detail']}")
    return 1 if rec["verdict"]["status"] == G.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
