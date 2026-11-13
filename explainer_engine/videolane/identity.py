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


def face_findings(script: dict, shot_ids: list[str], pictures: dict, references: dict) -> list[str] | None:
    """None when the face tools or the references are missing (NOT_RUN); else the heroes whose face SFace does not name."""
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
        heroes = [h for h in by[sid].get("character_ids") or [] if h in feats]
        if not heroes:
            continue
        named = FP.identify(FP.detect(Path(pictures[sid]), model, rec), feats, rec, heroes)
        out += [f"{sid}: {h}'s face is not found" for h in heroes if h not in named]
    return out


def rows(script: dict, shot_ids: list[str], frames: dict, pictures: dict, references: dict, where: str) -> list[dict]:
    lv = levels()
    cost = costume_findings(script, shot_ids, frames)
    face = face_findings(script, shot_ids, pictures, references)
    return [G.row(f"{where}_hero_costume_holds", not cost, f"{len(cost)} hero box(es) whose colours move across a cut "
                  f"(BP-166 hero_palette_max; switch Q3 -> {lv['costume']})", cost[:20], level=lv["costume"]),
            G.row(f"{where}_hero_face_holds", False, "NOT MEASURED: the face tools (tools/yunet YuNet + SFace) or the hero "
                  "references are missing; a person looks at the sheet", None, level=G.REVIEW) if face is None else
            G.row(f"{where}_hero_face_holds", not face, f"{len(face)} hero face(s) SFace does not name (switch Q3 -> "
                  f"{lv['face']})", face[:20], level=lv["face"])]


def references_of(root: Path, script: dict) -> dict:
    """The heroes' reference pictures: ``assets/reference/characters/<id>.jpg`` (the episode's asset registry layout)."""
    return {c["character_id"]: Path(root) / "assets" / "reference" / "characters" / f"{c['character_id']}.jpg"
            for c in (script.get("world_bible") or {}).get("characters", [])}
