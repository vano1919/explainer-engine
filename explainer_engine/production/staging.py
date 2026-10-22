"""Scene continuity (D-69, CS-01..CS-12, docs/PRODUCTION_SCRIPT.md): consecutive pictures of one staged scene are painted
as shots of ONE room, not as independent illustrations. The titans episode (2026-10-21) painted every Gemini picture from
its prompt and the style references alone, so a bench of ten became five in one shot and two different men in another
room in the next while the narration still told the same conversation.

A segment's optional ``staging`` block is the scene state that persists across its shots (and across segments that
continue the same scene): ``location``, ``time``, ``layout``, ``fixed`` details, the ``roster`` of who is in the room,
``positions`` (the spatial map, written left to right as the master frame sees it), the ``master`` picture. A picture adds
the shot-specific state: ``framing``, ``visible`` (faces that must be seen), ``partial`` (a shoulder or a back),
``change`` (what this shot changes), ``cut_away`` (a picture outside the staged room). Everything left out is derived: the
roster from ``scene.present``, the framing from the subject's words, the master from the first wide picture that shows
the whole roster. ``look.continuity: "auto"`` stages every segment that has a ``scene.place`` without a ``staging`` block.

    plan(doc)                  scenes and one spec per painted picture: scene_id, kind, framing, visible, master, refs
    prompt_block(doc, pid)     the continuity part of a picture's prompt (compile appends it): what stays, what changes
    refs_for(doc, pid, base)   the picture's references in priority order: master, previous shot, faces, style
    fit_refs(items, model)     trims each item to the model's reference slots (CS-08: what was dropped is named)
    lint(doc)                  CS-01..CS-07 on the script (free, part of ``validate``)
    blockers(...)              CS-09: why a picture must wait (its master is not painted or not reviewed yet)
    questions / verdict        CS-10, CS-11: the continuity review of one painted picture against its shot spec
    apply(...)                 records verdicts in the run ledger and the targeted correction of a rejected picture;
                               CS-12 stops a picture after MAX_REPAINTS corrections (the creator decides)

Shot kinds (the planner's answer to "does this picture continue the scene?"): ``master`` (the scene's canonical frame),
``continue`` (same framing as the shot before: painted as an edit of it), ``action`` (same framing, a stated change of
action: an edit of the shot before), ``reframe`` (another camera angle or size in the same room: painted against the
master), ``insert`` (a detail in the room: the master carries the light), ``cut_away`` and ``montage`` (outside a staged
scene: painted alone, as before). Only a new place or time starts a new scene; a new sentence or a new camera never does.

    python -m explainer_engine.production.staging plan    <script.json>                       # the scene table, free
    python -m explainer_engine.production.staging request <script.json> --pictures DIR [--out FILE]
    python -m explainer_engine.production.staging judge   <script.json> --pictures DIR --run run.json --yes <ref>
                                                          --max-usd X [--out FILE]            # paid vision answers
    python -m explainer_engine.production.staging apply   <script.json> <continuity_review.json> --run run.json
                                                          --pictures DIR [--max-repaints N]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

from explainer_engine.production import script as S

SCHEMA = "continuity_review/1"
FRAMINGS = ("wide", "full", "medium", "two_shot", "over_shoulder", "close", "reaction", "insert")
GROUP = {"wide", "full"}  # framings that show the room: the roster is expected in them (CS-04)
EDIT_KINDS = {"continue", "action"}  # painted as an edit of the previous shot
# CS-12: corrections of one picture before the creator decides (keep, edit by hand, or rewrite the shot). Spend control
# like paint.MAX_FAILURES, not a quality threshold; ``apply --max-repaints`` lowers it, never raises it past this.
MAX_REPAINTS = 2
NUMBER = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12}
COUNTED = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d{1,2})\s+(?:[a-z-]+\s+){0,3}?"
                     r"(men|women|people|heroes|figures|bosses|founders|billionaires|friends|strangers)\b", re.I)
SPLIT = re.compile(r"\b(split[- ](frame|screen)|diptych|side[- ]by[- ]side panels)\b", re.I)
SINGLE = "One single full-frame picture: never a collage, split screen, panel grid or storyboard."


def _norm(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _name(doc: dict, who: str) -> str:
    return ((doc.get("cast") or {}).get(who) or {}).get("names", [who])[0]


def _engine(doc: dict, pic: dict) -> str:
    from explainer_engine.production import compile as C
    return C.engine_of(doc, pic)


# --- scene state ------------------------------------------------------------------------------------------------------

def staging_of(doc: dict, seg: dict) -> dict | None:
    """The segment's scene state, or None for an unstaged segment (each of its pictures stands alone, as before D-69)."""
    st = seg.get("staging")
    sc = seg.get("scene") or {}
    if st is None:
        if (doc.get("look") or {}).get("continuity") != "auto" or not sc.get("place"):
            return None
        st = {}
    return {"scene_id": st.get("scene_id"), "continues": bool(st.get("continues")),
            "location": st.get("location") or sc.get("place") or "", "time": st.get("time") or sc.get("time") or "",
            "layout": st.get("layout", ""), "fixed": list(st.get("fixed", [])),
            "roster": list(st.get("roster") or sc.get("present") or []), "positions": dict(st.get("positions") or {}),
            "master": st.get("master")}


def scene_ids(doc: dict) -> list[str | None]:
    """One scene id per segment (None = unstaged). Consecutive segments share a scene when the second says so
    (``scene_id`` or ``continues``) or names the same place at the same time; a new place or time is a new scene."""
    out, prev_key, prev_id = [], None, None
    for seg in doc["segments"]:
        st = staging_of(doc, seg)
        if st is None:
            out.append(None)
            prev_key = prev_id = None
            continue
        key = (_norm(st["location"]), _norm(st["time"]))
        if st["scene_id"]:
            sid = st["scene_id"]
        elif st["continues"] and prev_id:
            sid = prev_id
        elif prev_id and key == prev_key and key[0]:
            sid = prev_id
        else:
            sid = "SC" + seg["id"][1:]
        out.append(sid)
        prev_key, prev_id = key, sid
    return out


def framing_of(shot: dict, pic: dict) -> str:
    """The shot's framing: the picture's ``framing``, else read from its subject and shot type."""
    if pic.get("framing"):
        return pic["framing"]
    sub = (pic.get("subject") or "").lower()
    if shot.get("type") == "C" or shot.get("insert"):
        return "insert"
    if re.search(r"\bover (the |his |her |their |[a-z]+'s )[^,.]{0,30}\bshoulders?\b", sub):
        return "over_shoulder"
    if re.search(r"\btwo[- ]shot\b", sub):
        return "two_shot"
    if re.search(r"\b(close[- ]up|close on|extreme close)\b", sub):
        return "close"
    if re.search(r"\breaction\b", sub):
        return "reaction"
    if shot.get("type") == "A" or re.search(r"^wide\b|\b(wide|establishing) (cinematic )?(shot|view|angle)\b", sub):
        return "wide"
    return "medium"


def visible_of(pic: dict, framing: str) -> tuple[list[str], list[str]]:
    """(faces that must be seen, figures seen only in part). An over-the-shoulder picture lists the facing hero first;
    the others are a shoulder or a back unless ``visible`` / ``partial`` say otherwise."""
    heroes = list(pic.get("heroes", []))
    partial = list(pic["partial"]) if "partial" in pic else (heroes[1:] if framing == "over_shoulder" else [])
    visible = list(pic["visible"]) if "visible" in pic else [h for h in heroes if h not in partial]
    return visible, partial


def _speaker(seg: dict, shot: dict) -> tuple[str | None, str | None]:
    """(speaker, listener) of a shot: its first bubble, else the voiced line its ``at`` words fall in."""
    for b in shot.get("bubbles", []):
        return b["who"], None
    at = _norm(shot.get("at"))
    for ln in seg["lines"]:
        if ln.get("speaker") and at and at in _norm(ln["text"]):
            return ln["speaker"], ln.get("to") if ln.get("to") not in (None, "self", "room") else None
    return None, None


def plan(doc: dict) -> dict:
    """{"scenes": {scene_id: state}, "segments": [{segment, scene_id, starts_scene}], "pictures": {pid: spec}}.
    A spec exists for every picture this script paints (Gemini, no file); a reused picture is not painted again."""
    pics, _ = S.pictures(doc)
    sids = scene_ids(doc)
    by_seg = {seg["id"]: (seg, sid) for seg, sid in zip(doc["segments"], sids)}
    shots = [sh for sh in S.shots(doc) if sh["picture_id"] in pics]  # an undefined picture is PV-05's finding
    scenes: dict[str, dict] = {}
    for seg, sid in zip(doc["segments"], sids):
        if sid is None:
            continue
        st = staging_of(doc, seg)
        sc = scenes.setdefault(sid, dict(st, scene_id=sid, segments=[], light_beats=[], pictures=[]))
        sc["segments"].append(seg["id"])
        sc["light_beats"].append(seg["light_beat"])
        for k in ("layout", "fixed", "positions", "master", "time"):  # a later segment may only add what is missing
            if not sc.get(k) and st.get(k):
                sc[k] = st[k]
        sc["roster"] = list(dict.fromkeys(sc["roster"] + st["roster"]))
    painted = {pid for pid, p in pics.items() if p.get("uses") and not p.get("file") and _engine(doc, p) == "gemini"}
    for sh in shots:  # the pictures of each scene, in order; the roster falls back to everyone they draw
        seg, sid = by_seg[sh["segment"]]
        pic = pics[sh["picture_id"]]
        if sid and not pic.get("cut_away") and sh["picture_id"] not in scenes[sid]["pictures"]:
            scenes[sid]["pictures"].append(sh["picture_id"])
    for sc in scenes.values():
        if not sc["roster"]:
            sc["roster"] = list(dict.fromkeys(h for p in sc["pictures"] for h in pics[p].get("heroes", [])))
        if not sc.get("master"):
            first = {p: next(s for s in shots if s["picture_id"] == p) for p in sc["pictures"]}
            wide = [p for p in sc["pictures"] if framing_of(first[p]["shot"], pics[p]) in GROUP]
            whole = [p for p in wide if set(sc["roster"]) <= set(pics[p].get("heroes", []))]
            ranked = sorted(sc["pictures"], key=lambda p: -len(set(pics[p].get("heroes", [])) & set(sc["roster"])))
            sc["master"] = (whole or wide or ranked or [None])[0]
    specs: dict[str, dict] = {}
    last: dict[str, str] = {}  # scene id -> the last picture on screen in it (inserts and cut-aways excluded)
    for sh in shots:
        seg, sid = by_seg[sh["segment"]]
        pid = sh["picture_id"]
        pic = pics[pid]
        framing = framing_of(sh["shot"], pic)
        if pid in painted and pid not in specs:
            visible, partial = visible_of(pic, framing)
            speaker, listener = _speaker(seg, sh["shot"])
            spec = {"id": pid, "shot": sh["id"], "segment": seg["id"], "framing": framing, "visible": visible,
                    "partial": partial, "speaker": speaker, "listener": listener, "change": pic.get("change", ""),
                    "split": bool(SPLIT.search(pic.get("subject") or "")), "master": None, "prev": None}
            if sid is None or pic.get("cut_away"):
                spec.update(scene_id=f"{seg['id']}:{pid}", kind="cut_away" if sid else "montage", offscreen=[])
            else:
                sc = scenes[sid]
                prev = last.get(sid)
                # the same camera = the same framing on the same faces; a reverse angle (the other hero's face over a
                # shoulder) is another camera, painted against the master, never as an edit of the shot before
                same = prev in specs and (specs[prev]["framing"], specs[prev]["visible"]) == (framing, visible)
                if pid == sc["master"]:
                    kind = "master"
                elif framing == "insert":
                    kind = "insert"
                elif same:  # same camera as the shot before: an edit of it
                    kind = "action" if spec["change"] else "continue"
                else:
                    kind = "reframe"
                spec.update(scene_id=sid, kind=kind, master=None if kind == "master" else sc["master"],
                            prev=prev if kind in EDIT_KINDS and prev and prev != sc["master"] else None,
                            offscreen=[h for h in sc["roster"] if h not in visible and h not in partial])
            specs[pid] = spec
        if sid and not pic.get("cut_away") and framing != "insert":
            last[sid] = pid
    segments, prev_sid = [], None
    for seg, sid in zip(doc["segments"], sids):
        segments.append({"segment": seg["id"], "scene_id": sid, "starts_scene": sid is None or sid != prev_sid})
        prev_sid = sid
    return {"scenes": scenes, "segments": segments, "pictures": specs}


# --- references and the prompt ----------------------------------------------------------------------------------------

def face_ref(doc: dict, who: str) -> str | None:
    """The hero's approved reference picture (cast.<id>.reference, OR-16), when it is in the library."""
    ref = ((doc.get("cast", {}).get(who) or {}).get("reference") or {}).get("picture")
    return ref if ref and ref in doc.get("library", {}) else None


def refs_for(doc: dict, pid: str, base: list[str], staged: dict | None = None) -> list[str]:
    """The picture's references in priority order (the most important first; ``fit_refs`` drops from the end): the
    scene's master frame, the previous shot (an edit), the visible heroes' faces, then ``base`` (the style references)."""
    spec = (staged or plan(doc))["pictures"].get(pid)
    out: list[str] = []
    if spec and spec["kind"] not in ("montage", "cut_away"):
        for r in (spec["master"], spec["prev"]):
            if r and r not in out:
                out.append(r)
        for who in ([spec["speaker"]] if spec["speaker"] in spec["visible"] else []) + spec["visible"]:
            r = face_ref(doc, who)
            if r and r not in out:
                out.append(r)
    out += [r for r in base if r not in out]
    return out


def role_of(doc: dict, ref: str) -> str:
    """object (the master, a previous shot, a style frame) or character (a hero's face reference)."""
    return "character" if ref in {face_ref(doc, w) for w in doc.get("cast", {})} else "object"


def fit_refs(doc: dict, items: list[dict], provider: str, model: str | None) -> tuple[list[dict], list[dict]]:
    """Each item's references trimmed to the provider's and the model's slots (characters, total), lowest priority
    first. Returns (items, CS-08 findings naming every dropped reference): a limit is never exceeded, and never silently."""
    from explainer_engine.imagegen import gemini, plan as P
    total = P.PROVIDERS[provider]["max_refs"]
    chars = total
    if provider == "gemini" and model:
        lim = gemini.ref_limits(model)
        total, chars = min(total, lim["total"]), lim["characters"]
    found, out = [], []
    for it in items:
        refs = [r.removesuffix(".png") for r in it.get("refs", [])]
        keep, n_chars, dropped = [], 0, []
        for r in refs:
            is_char = role_of(doc, r) == "character"
            if len(keep) >= total or (is_char and n_chars >= chars):
                dropped.append(r)
                continue
            keep.append(r)
            n_chars += is_char
        if dropped:
            found.append({"rule": "CS-08", "severity": "REVIEW", "where": it["id"],
                          "detail": f"{len(refs)} references, {model or provider} takes {total} ({chars} faces): dropped "
                                    f"{', '.join(dropped)}; those faces come from the master frame and the cards"})
        suffix = ".png" if any(str(r).endswith(".png") for r in it.get("refs", [])) else ""
        out.append(dict(it, refs=[r + suffix for r in keep]))
    return out, found


def _who(doc: dict, ids: list[str], scene: dict | None = None) -> str:
    pos = (scene or {}).get("positions", {})
    return ", ".join(_name(doc, w) + (f" ({pos[w]})" if w in pos else "") for w in ids)


def prompt_block(doc: dict, pid: str, staged: dict | None = None) -> str:
    """The continuity part of one picture's prompt: the persistent scene properties (what stays) apart from the
    shot-specific ones (what this shot shows and may change). Empty for an unstaged picture."""
    staged = staged or plan(doc)
    spec = staged["pictures"].get(pid)
    if not spec:
        return ""
    single = "" if spec["split"] else " " + SINGLE
    if spec["kind"] in ("montage", "cut_away"):
        return single.strip()
    sc = staged["scenes"][spec["scene_id"]]
    room = [f"place: {sc['location']}" + (f", {sc['time']}" if sc["time"] else "")]
    if sc["layout"]:
        room.append(f"layout: {sc['layout']}")
    if sc["fixed"]:
        room.append("fixed details: " + "; ".join(sc["fixed"]))
    order = [w for w in sc["positions"]] + [w for w in sc["roster"] if w not in sc["positions"]]
    seats = f"everyone in the room, left to right as the master frame shows them: {_who(doc, order, sc)}" if order else ""
    if spec["kind"] == "master":
        head = (f"SCENE {sc['scene_id']}, MASTER FRAME: this picture fixes the room and the seating for every later shot "
                f"of the scene. " + "; ".join(room) + ".")
        body = (f" {seats}; all {len(order)} of them in frame with readable faces." if order else "")
        return head + body + single
    n = 1
    refs = [f"reference image {n} is the scene's master frame ({spec['master']})"]
    if spec["prev"]:
        n += 1
        refs.append(f"reference image {n} is the previous shot ({spec['prev']})")
    head = (f"SCENE {sc['scene_id']}, continuous with its master frame ({spec['kind']} shot, {spec['framing'].replace('_', ' ')}"
            f"): {'; '.join(refs)}; any further reference images show faces and the drawing style.")
    keep = (" KEEP UNCHANGED from the master frame: " + "; ".join(room) + "; the light and the palette; every "
            "character's face, hair and clothes" + (f"; the seating, {seats}" if seats else "") + ".")
    if spec["kind"] == "insert":
        shot = " THIS SHOT: a close detail inside that same room, nobody new enters it."
    else:
        must = _who(doc, spec["visible"]) or "nobody's face"
        shot = f" THIS SHOT: {spec['framing'].replace('_', ' ')}; must show with readable faces: {must}"
        if spec["partial"]:
            shot += f"; seen only in part (shoulder or back): {_who(doc, spec['partial'])}"
        if spec["speaker"]:
            shot += f"; speaking: {_name(doc, spec['speaker'])}"
            if spec["listener"]:
                shot += f", listening: {_name(doc, spec['listener'])}"
        if spec["offscreen"]:
            shot += f"; still in the room but outside this frame: {_who(doc, spec['offscreen'])}"
        shot += "."
    if spec["prev"]:
        change = spec["change"] or "the expressions and gestures of this moment"
        allowed = f" Edit reference image 2: keep its camera, room and people, change only {change}."
    else:
        allowed = (" MAY CHANGE: the camera angle and framing, expressions and gestures"
                   + (f", and {spec['change']}" if spec["change"] else "") + "; never the room or the seats.")
    return head + keep + shot + allowed + single


# --- the script-level lint (free) -------------------------------------------------------------------------------------

def lint(doc: dict) -> list[dict]:
    """CS-01..CS-07 on the script: [{rule, severity, where, detail}]."""
    out = []

    def f(rule, where, detail, sev="FAIL"):
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    pics, _ = S.pictures(doc)
    staged = plan(doc)
    cast = set(doc.get("cast", {}))
    for sid, sc in staged["scenes"].items():
        for who in [w for w in sc["roster"] + list(sc["positions"]) if w not in cast]:
            f("CS-01", sid, f"{who!r} is not a cast id")
        for who in [w for w in sc["positions"] if w not in sc["roster"]]:
            f("CS-01", sid, f"{who!r} has a position but is not in the scene's roster")
        if sc["master"] is None:
            if any(p in staged["pictures"] for p in sc["pictures"]):
                f("CS-01", sid, "no master frame: name `staging.master`, or add a wide picture that shows the whole roster")
            continue
        if sc["master"] not in pics:
            f("CS-01", sid, f"master {sc['master']!r} is not a picture of this script")
            continue
        if sc["master"] not in sc["pictures"]:
            f("CS-01", sid, f"master {sc['master']!r} is not shown in this scene")
        missing = [w for w in sc["roster"] if w not in pics[sc["master"]].get("heroes", [])]
        if missing:
            f("CS-02", sc["master"], f"the master frame of {sid} must show everyone in the room; it leaves out "
                                     f"{', '.join(missing)} (add them to its heroes, or take them out of the roster)")
        if len(sc["roster"]) >= 3:
            unplaced = [w for w in sc["roster"] if w not in sc["positions"]]
            if unplaced:
                f("CS-04", sid, f"{len(sc['roster'])} people in the room and no position for {', '.join(unplaced)}: "
                                "write `staging.positions` (left to right in the master) so every shot keeps the seats",
                  "REVIEW")
        if len(set(sc["light_beats"])) > 1:
            f("CS-06", sid, f"one continuous scene over segments {', '.join(sc['segments'])} with light beats "
                            f"{sorted(set(sc['light_beats']))}: the light changes between shots of one room; give them one "
                            "light beat, or start a new scene", "REVIEW")
        for pid in sc["pictures"]:
            stray = [h for h in pics[pid].get("heroes", []) if h not in sc["roster"]]
            if stray:
                f("CS-03", pid, f"draws {', '.join(stray)}, who {'is' if len(stray) == 1 else 'are'} not in the room of "
                                f"{sid} (roster {', '.join(sc['roster'])}): add to the roster, or mark the picture cut_away")
    for pid, spec in staged["pictures"].items():
        pic = pics[pid]
        if spec["kind"] not in ("montage", "cut_away") and spec["framing"] in GROUP and spec["kind"] != "master":
            gone = [w for w in staged["scenes"][spec["scene_id"]]["roster"] if w not in pic.get("heroes", [])]
            if gone:
                f("CS-04", pid, f"a {spec['framing']} shot of the room without {', '.join(gone)}: list them in heroes, "
                                "or frame it tighter (medium, two_shot)", "REVIEW")
        m = COUNTED.search(pic.get("subject") or "")
        if m:
            g = m.group(1).lower()
            n = int(g) if g.isdigit() else NUMBER[g]
            named = len(pic.get("heroes", []))
            if n > named and named:
                f("CS-05", pid, f"the subject counts {n} {m.group(2)} but names {named} hero{'es' if named > 1 else ''}: "
                                f"the painter invents the other {n - named} anew in every picture; name every hero who must "
                                "be recognised, or say they are anonymous extras", "REVIEW")
    if doc.get("schema") == "production_script/3":
        for seg, sid in zip(doc["segments"], scene_ids(doc)):
            new = [p for p in staged["pictures"] if staged["pictures"][p]["segment"] == seg["id"]]
            if sid is None and seg.get("scene") and len(new) >= 2:
                f("CS-07", seg["id"], f"a staged dialogue scene with {len(new)} new pictures and no `staging`: each is "
                                      "painted alone, without a master frame (add `staging`, or look.continuity auto)",
                  "REVIEW")
    return out


# --- paint order (CS-09) ----------------------------------------------------------------------------------------------

def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def review_state(run, pid: str, painted_hash: str | None) -> str | None:
    """The continuity verdict of the picture as painted now (PASS / FAIL / REVIEW), None when not reviewed since."""
    rec = ((run.data.get("continuity") if run else None) or {}).get(pid)
    if not rec or not rec.get("history"):
        return None
    last = rec["history"][-1]
    return last["status"] if painted_hash is None or last.get("painted") == painted_hash else None


def blockers(doc: dict, item: dict, out: Path, run, todo: set[str], staged: dict | None = None) -> list[str]:
    """Why ``item`` cannot be painted yet: a reference picture of this script not painted, being repainted, or (the
    master) not passed by the continuity review. References painted in this same run (``todo``) are ordered, not blocked."""
    staged = staged or plan(doc)
    pics, _ = S.pictures(doc)
    spec = staged["pictures"].get(item["id"])
    why = []
    for r in (r.removesuffix(".png") for r in item.get("refs", [])):
        p = pics.get(r)
        if p is None or p.get("file") or r in todo:
            continue
        if not (Path(out) / f"{r}.png").exists():
            why.append(f"waits for {r}: not painted yet (paint it first, e.g. `paint plan --masters`)")
            continue
        rec = ((run.data["items"].get("pictures", {}) if run else {}).get(r)) or {}
        state = review_state(run, r, rec.get("hash"))
        if state == "FAIL":
            why.append(f"waits for {r}: it failed its continuity review (CS-10/CS-11) and is being repainted")
        elif spec and r == spec["master"] and state != "PASS":
            why.append(f"waits for {r}: the master frame needs a PASS continuity review first "
                       "(`staging request` / `staging apply`)")
    return why


def waves(items: list[dict]) -> list[list[dict]]:
    """The items in painting order: a picture after every reference it takes from the same batch."""
    ids = {it["id"] for it in items}
    deps = {it["id"]: {r.removesuffix(".png") for r in it.get("refs", [])} & ids for it in items}
    done, left, out = set(), list(items), []
    while left:
        wave = [it for it in left if deps[it["id"]] <= done]
        if not wave:  # a cycle cannot come from plan(), but never loop forever on a hand-made one
            wave = left
        out.append(wave)
        done |= {it["id"] for it in wave}
        left = [it for it in left if it["id"] not in done]
    return out


# --- the continuity review (CS-10, CS-11, CS-12) ----------------------------------------------------------------------

def questions(doc: dict, pid: str, staged: dict | None = None) -> dict[str, str]:
    """The questions one painted picture is checked with, built from its shot spec: only the faces THIS framing must
    show are asked for, so a close-up is never failed for the people outside it."""
    staged = staged or plan(doc)
    spec = staged["pictures"][pid]
    cards = {w: c.get("card", "") for w, c in doc.get("cast", {}).items()}
    q = {} if spec["split"] else {"single_frame": "Is this ONE single full-frame picture (no collage, no split screen, "
                                                    "no panel grid, no storyboard, no inset frames)?"}
    for w in spec["visible"]:
        q[f"visible_{w}"] = f"Is {_name(doc, w)} clearly in the picture with a readable face ({cards.get(w, '')})?"
    for w in spec["partial"]:
        q[f"partial_{w}"] = f"Is {_name(doc, w)} at least partly in the picture (a shoulder, a back or an edge)?"
    if spec["kind"] in ("montage", "cut_away"):
        return q
    sc = staged["scenes"][spec["scene_id"]]
    place = sc["location"] + (f"; with {'; '.join(sc['fixed'])}" if sc["fixed"] else "")
    if spec["kind"] == "master":
        q["place"] = f"Is the place: {place}?"
        placed = [w for w in sc["positions"] if w in spec["visible"]]
        if len(placed) >= 2:
            q["order"] = "From left to right, are they placed as: " + _who(doc, placed, sc) + "?"
    else:
        q["place"] = (f"Compared with the master frame (second image), is it the SAME place, with the same furniture, "
                      f"walls, light and palette ({place})? A different camera angle is fine; a different room is not.")
        if len(spec["visible"]) >= 2:
            q["seats"] = ("Do the people keep their places relative to each other as in the master frame (a reverse "
                          "angle may mirror left and right)?")
    q["action"] = f"Does it show this moment: {(S.pictures(doc)[0][pid].get('subject') or '')[:300]}?"
    return q


def verdict(doc: dict, pid: str, answers: dict, staged: dict | None = None) -> dict:
    """{status, fails, review, correction}: FAIL when a face this framing must show is missing (CS-10), when a
    continuation left the master's room or the picture is a collage (CS-11); REVIEW for seats, action and gaps."""
    staged = staged or plan(doc)
    spec = staged["pictures"][pid]
    fails, review, fix = [], [], []
    for key in questions(doc, pid, staged):
        if key not in answers:
            review.append(f"{key}: no answer")
            continue
        ok = bool(answers[key])
        if ok:
            continue
        why = answers.get(f"why_{key}") or answers.get("note") or ""
        if key.startswith("visible_"):
            who = key[len("visible_"):]
            fails.append(f"CS-10 {_name(doc, who)} must be visible in this {spec['framing'].replace('_', ' ')} and is not")
            fix.append(f"{_name(doc, who)} must be clearly in frame with a readable face"
                       + (f" ({staged['scenes'][spec['scene_id']]['positions'][who]})"
                          if spec["scene_id"] in staged["scenes"] and who in staged["scenes"][spec["scene_id"]]["positions"]
                          else ""))
        elif key == "single_frame":
            fails.append("CS-11 not one single frame (collage, split screen or panels)")
            fix.append("paint ONE continuous full-frame picture, no panels, no split, no inset frames")
        elif key == "place" and spec["kind"] not in ("master", "montage", "cut_away"):
            fails.append(f"CS-11 the room changed from the master frame {spec['master']} without a scene change")
            fix.append(f"the room must be exactly the room of the master frame ({spec['master']}): same walls, furniture, "
                       "light and palette; only the camera moves")
        elif key == "place":
            fails.append("CS-11 the master frame does not show the scene's place")
            fix.append(f"the place must be: {staged['scenes'][spec['scene_id']]['location']}")
        elif key == "order" and spec["kind"] == "master":
            fails.append("CS-10 the master frame does not place the roster as staged")
            fix.append("place them left to right exactly as listed")
        else:
            review.append(f"{key}: no" + (f" ({why})" if why else ""))
    correction = ""
    if fix:
        correction = "CORRECTION of the previous attempt: " + "; ".join(fix) + "."
    return {"status": "FAIL" if fails else "REVIEW" if review else "PASS", "fails": fails, "review": review,
            "correction": correction}


def correction_of(run, pid: str) -> str:
    """The targeted correction the next paint of ``pid`` carries (empty when it is not rejected)."""
    rec = ((run.data.get("continuity") if run else None) or {}).get(pid) or {}
    return rec.get("correction", "") if rec.get("open") else ""


def attempts(run, pid: str) -> int:
    return len((((run.data.get("continuity") if run else None) or {}).get(pid) or {}).get("corrections", []))


def exhausted(run, pid: str) -> bool:
    """CS-12: the picture failed again after its last allowed correction: no more paid repaints without the creator."""
    rec = (((run.data.get("continuity") if run else None) or {}).get(pid)) or {}
    return bool(rec.get("open") and rec.get("stopped"))


def record(run, pid: str, result: dict, painted: str | None, limit: int = MAX_REPAINTS) -> str:
    """Store one verdict in the run ledger; a FAIL opens a correction unless the picture used up its repaints.
    Returns what happens next: "accepted", "review", "repaint" or "creator"."""
    with run.lock:
        rec = run.data.setdefault("continuity", {}).setdefault(pid, {"history": [], "corrections": []})
        rec["history"].append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": result["status"],
                               "fails": result["fails"], "review": result["review"], "painted": painted})
        if result["status"] != "FAIL":
            rec["open"] = rec["stopped"] = False
            nxt = "accepted" if result["status"] == "PASS" else "review"
        elif len(rec["corrections"]) >= min(limit, MAX_REPAINTS):
            rec["open"] = rec["stopped"] = True
            nxt = "creator"
        else:
            rec["open"] = True
            rec["corrections"].append(f"{result['correction']} (repaint {len(rec['corrections']) + 1} of {limit})")
            rec["correction"] = rec["corrections"][-1]
            nxt = "repaint"
        run.save()
    return nxt


def apply(doc: dict, review: dict, run, pictures: Path, limit: int = MAX_REPAINTS) -> list[dict]:
    """Verdicts for every reviewed picture, recorded in the ledger. A rejected picture is copied to
    ``<pictures>/rejected/`` (its file stays as the stand-in until the repaint) and carries a correction into the next
    paint plan; CS-12 FAILs a picture that has no repaint left."""
    if review.get("schema") != SCHEMA:
        return [{"rule": "CS-10", "severity": "FAIL", "where": "schema", "detail": f"expected {SCHEMA}"}]
    staged = plan(doc)
    out = []
    painted_items = run.data["items"].get("pictures", {})
    for pid in staged["pictures"]:
        ans = review.get("pictures", {}).get(pid)
        if ans is None:
            if (Path(pictures) / f"{pid}.png").exists():
                out.append({"rule": "CS-10", "severity": "REVIEW", "where": pid, "detail": "painted, not reviewed"})
            continue
        res = verdict(doc, pid, ans, staged)
        nxt = record(run, pid, res, (painted_items.get(pid) or {}).get("hash"), limit)
        for x in res["fails"]:
            out.append({"rule": x.split()[0], "severity": "FAIL", "where": pid, "detail": x.split(" ", 1)[1]})
        for x in res["review"]:
            out.append({"rule": "CS-11", "severity": "REVIEW", "where": pid, "detail": x})
        if nxt in ("repaint", "creator"):
            src = Path(pictures) / f"{pid}.png"
            if src.exists():
                dst = Path(pictures) / "rejected" / f"{pid}.v{len(run.data['continuity'][pid]['history'])}.png"
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        if nxt == "creator":
            out.append({"rule": "CS-12", "severity": "FAIL", "where": pid,
                        "detail": f"failed again after {attempts(run, pid)} corrections: no more paid repaints; the "
                                  "creator decides (keep it, edit it by hand, or rewrite the shot)"})
    return out


def seam_findings(path: Path) -> list[dict]:
    """A free pixel hint for CS-11 (REVIEW only, house heuristic): a straight full-height or full-width edge, the mark of a
    split screen or a panel grid. Door frames and pillars can trigger it; the review question decides."""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(path).convert("L").resize((320, 180)), dtype=np.float32)
    out = []
    for axis, name in ((1, "vertical"), (0, "horizontal")):
        d = np.abs(np.diff(im, axis=axis))  # step between neighbouring columns (axis 1) or rows (axis 0)
        strong = (d > 40).mean(axis=1 - axis)  # share of the line's length with a hard step
        lo, hi = int(len(strong) * 0.15), int(len(strong) * 0.85)
        k = lo + int(np.argmax(strong[lo:hi])) if hi > lo else 0
        if hi > lo and strong[k] > 0.85:
            out.append({"rule": "CS-11", "severity": "REVIEW", "where": Path(path).stem,
                        "detail": f"a hard {name} edge across {strong[k]:.0%} of the picture at {k / len(strong):.0%}: "
                                  "a split screen or panel border? answer single_frame"})
    return out


def request(doc: dict, dirs: list[Path]) -> str:
    """The free review sheet: every painted picture of a staged scene with its master frame and its questions; Claude opens
    both files, answers into ``continuity_review.json`` (``continuity_review/1``) and runs ``apply``."""
    staged = plan(doc)
    find = lambda p: next((str(d / f"{p}.png") for d in dirs if (d / f"{p}.png").exists()), None)  # noqa: E731
    lines = [f"# Continuity review: {doc['episode']['id']}", "",
             "Open each picture AND its master frame, answer every question true/false with a why_<key> for every false "
             f"answer, and write `continuity_review.json` ({SCHEMA}): "
             '{"schema": "continuity_review/1", "by": "claude", "pictures": {"<id>": {"<key>": true, ...}}}. Free.', ""]
    for pid, spec in staged["pictures"].items():
        f = find(pid)
        if not f:
            continue
        hints = seam_findings(Path(f))
        lines += [f"## {pid} ({spec['kind']}, {spec['framing']}, scene {spec['scene_id']})", f"picture: {f}"]
        if spec["master"]:
            lines.append(f"master frame: {find(spec['master']) or spec['master'] + ' (not painted)'}")
        lines += [f"pixel hint: {h['detail']}" for h in hints]
        lines += ["", "```json", json.dumps(questions(doc, pid, staged), indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


def judge(doc: dict, dirs: list[Path], client, max_usd: float) -> dict:
    """The same questions answered by the existing Gemini vision call (``GeminiClient.judge``, reserved in the ledger),
    with the master frame as the second image. Paid: refuses past ``max_usd``. Returns a continuity_review/1 dict."""
    from explainer_engine.imagegen.gemini import JUDGE_USD
    staged = plan(doc)
    find = lambda p: next((d / f"{p}.png" for d in dirs if (d / f"{p}.png").exists()), None)  # noqa: E731
    todo = [(pid, find(pid), find(spec["master"]) if spec["master"] else None)
            for pid, spec in staged["pictures"].items() if find(pid)]
    cost = sum(JUDGE_USD * (2 if m else 1) for _, _, m in todo)
    if cost > max_usd + 1e-9:
        raise ValueError(f"the judge would cost ${cost:.4f} for {len(todo)} pictures, over --max-usd {max_usd}")
    out = {"schema": SCHEMA, "by": "gemini-judge", "pictures": {}}
    for pid, pic, master in todo:
        q = questions(doc, pid, staged)
        ask = ("You check one painted picture (first image)" + (" against its scene's master frame (second image)"
                                                                 if master else "") +
               ". Answer ONLY a JSON object with a boolean for every key and a 'why_<key>' string for every false one:\n"
               + json.dumps(q, ensure_ascii=False))
        images = [pic.read_bytes()] + ([master.read_bytes()] if master else [])
        from explainer_engine.qa import visual_judge as J
        out["pictures"][pid] = J.parse(client.judge(images[0], ask, images=images[1:]))
    return out


# --- CLI ---------------------------------------------------------------------------------------------------------------

def table(doc: dict, staged: dict | None = None) -> str:
    staged = staged or plan(doc)
    lines = ["segment  scene   starts"]
    lines += [f"{s['segment']:8} {str(s['scene_id'] or '-'):7} {'new scene' if s['starts_scene'] else 'continues'}"
              for s in staged["segments"]]
    lines.append("")
    lines.append("picture                    scene   kind       framing        refs")
    for pid, spec in staged["pictures"].items():
        lines.append(f"{pid:26} {spec['scene_id'][:7]:7} {spec['kind']:10} {spec['framing']:14} "
                     f"{', '.join(refs_for(doc, pid, [], staged))}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.staging", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("plan")
    q.add_argument("script")
    for name in ("request", "judge"):
        q = sub.add_parser(name)
        q.add_argument("script")
        q.add_argument("--pictures", action="append", required=True)
        q.add_argument("--out")
        if name == "judge":
            q.add_argument("--run", required=True)
            q.add_argument("--yes", required=True, help="the creator's message that approves this paid check")
            q.add_argument("--max-usd", type=float, required=True)
    q = sub.add_parser("apply")
    q.add_argument("script")
    q.add_argument("review")
    q.add_argument("--run", required=True)
    q.add_argument("--pictures", required=True)
    q.add_argument("--max-repaints", type=int, default=MAX_REPAINTS)
    a = ap.parse_args(argv)
    doc = S.load(a.script)
    from explainer_engine.core.store import write_json_atomic, write_text_atomic
    if a.cmd == "plan":
        print(table(doc))
        for f in lint(doc):
            print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
        return 1 if any(f["severity"] == "FAIL" for f in lint(doc)) else 0
    if a.cmd == "request":
        target = Path(a.out) if a.out else Path(a.script).parent / "continuity_review_request.md"
        write_text_atomic(target, request(doc, [Path(p) for p in a.pictures]))
        print(target)
        return 0
    from explainer_engine.core.ledger import Run
    run = Run.open(a.run)
    if a.cmd == "judge":
        from explainer_engine.imagegen.gemini import GeminiClient
        client = GeminiClient(Path(a.pictures[0]) / "_gemini", cap_usd=1e9, run=run)
        res = judge(doc, [Path(p) for p in a.pictures], client, a.max_usd)
        res["approved"] = a.yes
        target = Path(a.out) if a.out else Path(a.script).parent / "continuity_review.json"
        write_json_atomic(target, res)
        print(target)
        return 0
    if a.max_repaints > MAX_REPAINTS:
        ap.error(f"--max-repaints is at most {MAX_REPAINTS} (CS-12); more needs the creator's word in the code")
    found = apply(doc, json.loads(Path(a.review).read_text(encoding="utf-8")), run, Path(a.pictures), a.max_repaints)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    reps = [p for p, r in run.data.get("continuity", {}).items() if r.get("open") and not exhausted(run, p)]
    if reps:
        print(f"{len(reps)} pictures carry a correction into the next `paint plan --run {a.run}`: {', '.join(reps)}")
    print(f"{sum(f['severity'] == 'FAIL' for f in found)} FAIL, {sum(f['severity'] == 'REVIEW' for f in found)} REVIEW")
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    sys.exit(main())
