"""Film shot cards (``film_shots/1``): the animated shots of an approved script, and the prompts composed from them.

A shot card says what the shot is for (``beat``), the frame (size, angle, camera, place, light), who stands where and
looks where (``blocking``), the one action with its start, peak and settle, the others' reactions, the line spoken (or
the narrator's line over it) and the sound. ``compose`` writes every prompt from those fields, so the keyframe, the next
pose, the cut and the video always say the same thing in each model's own grammar; ``check`` runs the card rules
(KP-15..KP-34, docs/SHOT_PROMPTS.md) and then the prompt lint (KP-01..KP-14) on what it composed.

    python -m explainer_engine.scripting.film_shots check <film_shots.json>
    python -m explainer_engine.scripting.film_shots compose <film_shots.json> [--out prompts.json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.scripting import shot_prompt_lint as lint
from explainer_engine.standards import sourced_rules

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "film_shots.schema.json"

# BP-100: speech a video clip can lip-sync, with a settle before and after the line
SPEECH_WPS = sourced_rules.T("BP-100", "words_per_second")
SPEECH_SETTLE_S = sourced_rules.T("BP-100", "settle_s")
# BP-101: faces the video model keeps apart in a medium or closer shot (the creator's cartoons: 78 % of shots show <= 2)
CLOSE_FACES_MAX = sourced_rules.T("BP-101", "close_faces_max")
# BP-103: shot-size variety inside a scene
SAME_SIZE_RUN_MAX = sourced_rules.T("BP-103", "same_size_run_max")

SIZES = {"EWS": "extreme wide shot", "WS": "wide shot", "MWS": "full-body shot", "MS": "medium shot from the waist up",
         "MCU": "medium close-up from the chest up", "CU": "close-up on the face", "ECU": "extreme close-up",
         "OTS": "over-the-shoulder shot", "INSERT": "close insert shot"}
WIDE = {"EWS", "WS"}
CLOSE = {"MS", "MCU", "CU", "ECU", "OTS"}
ANGLES = {"eye": "at eye level", "low": "from a low angle", "high": "from a high angle",
          "overhead": "from directly overhead", "dutch": "at a tilted dutch angle"}
WHERE = {"left": "on the left", "center": "in the center", "right": "on the right",
         "left_back": "in the background on the left", "center_back": "in the background in the center",
         "right_back": "in the background on the right", "left_front": "in the foreground on the left",
         "right_front": "in the foreground on the right"}
CAMERA = {"static": "Static camera.", "push_in": "The camera pushes in slowly", "pull_out": "The camera pulls out slowly",
          "pan_left": "The camera pans left", "pan_right": "The camera pans right", "tilt_up": "The camera tilts up",
          "tilt_down": "The camera tilts down", "follow": "The camera follows {actor}",
          "truck_left": "The camera trucks left", "truck_right": "The camera trucks right"}
NEXTPOSE = "nextpose, a later frame of the same continuous animated shot, same camera: "
NEG_KEYFRAME = ("text, watermark, logo, signature, extra people, duplicated person, extra fingers, deformed hands, "
                "extra limbs, blurry face, low resolution")
NEG_VIDEO = ("text, watermark, logo, subtitles, extra people, duplicated character, morphing face, melting body, "
             "deformed hands, extra fingers, flicker, still image")
HEIGHTS = {"quarter": "a quarter", "third": "a third", "half": "half", "two_thirds": "two thirds", "most": "most"}
# KP-33: a relation the picture can draw one way only; "by the boulder" can be any side, or the boulder itself
CLEAR = re.compile(r"\b(?:behind|in front of|on top of|on|under|beneath|inside|above|below|against|to the (?:left|right) of|"
                   r"in the (?:fore|back)ground|holds?|holding|rides?|riding)\b", re.I)
VAGUE = re.compile(r"\b(?:by|near|beside|next to|with|around|close to)\b", re.I)
SUPPORT = re.compile(r"\b(?:on|in|against|at|astride|inside|over)\b", re.I)
BARE = re.compile(r"(?:the|a|an|one)?\s*(?:old|young|little|tall|short|big|small)?\s*(?:woman|man|girl|boy|person|guy|lady|"
                  r"kid|child|caveman|cavewoman|stranger|figure)", re.I)
STOP = set("a an the and or but of to in on at by for with from his her their its it he she they them this that is are was "
           "were be been as into onto over under up down out then than so very just only all every each one two".split())


def load(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema_errors(doc: dict) -> list[str]:
    import jsonschema

    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in validator.iter_errors(doc)]


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _end(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?", '"')) else text + "."


def _tag(doc: dict, who: str) -> str:
    return doc["cast"][who]["tag"] if who in doc["cast"] else who


def _facing(doc: dict, facing: str) -> str:
    plain = {"camera": "facing the camera", "left": "facing left", "right": "facing right", "away": "with the back to the camera"}
    return plain.get(facing) or f"looking at {_tag(doc, facing)}"


def _height(p: dict) -> str:
    if p.get("height_pct"):
        return f"filling about {p['height_pct']} % of the frame height"
    if p.get("height") == "most":
        return "filling most of the frame height"
    return f"filling about {HEIGHTS[p['height']]} of the frame height" if p.get("height") else ""


def _people(doc: dict, shot: dict, *, actor_pose: str | None, layout: bool = False) -> list[str]:
    """Each person by tag, side, gaze and pose; with ``layout`` (a drawn first frame) also what they stand on and how
    much of the frame height they fill (KP-31, KP-32)."""
    action = shot.get("action") or {}
    out = []
    for p in shot.get("blocking", []):
        pose = actor_pose if p["who"] == action.get("who") and actor_pose else p.get("pose") or "stands"
        bits = [_cap(_tag(doc, p["who"])), WHERE[p["where"]], _facing(doc, p["facing"])]
        bits += [] if layout and p.get("on") and pose == "stands" else [pose]  # "stands, standing on the snow"
        if layout:
            bits += [x for x in (p.get("on", ""), _height(p)) if x]
        out.append(_end(", ".join(bits)))
    return out


def _layout(shot: dict) -> list[str]:
    """The relations between things and the free space the action moves into (KP-33, KP-34)."""
    f = shot["frame"]
    out = [_end(_cap(r)) for r in f.get("relations", [])]
    room = f.get("lead_room") or {}
    why = f", {room['for']}" if room.get("for") else ""
    if room.get("side") in ("left", "right"):
        out.append(_end(f"Empty space on the {room['side']} side of the frame{why}"))
    elif room.get("side") in ("above", "below"):
        out.append(_end(f"Empty space at the {'top' if room['side'] == 'above' else 'bottom'} of the frame{why}"))
    return out


def _lead(shot: dict) -> str | None:
    """The figure the frame is built around: the actor, else the first person in the blocking."""
    who = (shot.get("action") or {}).get("who")
    people = [p["who"] for p in shot.get("blocking", [])]
    return who if who in people else (people[0] if people else None)


def gate_card(doc: dict, shot: dict) -> dict:
    """What the keyframe gate (PR #22, qa/keyframe_gate.py) checks a drawn first frame against: the people by tag,
    side, height and support (the lead marked ``actor``), the relations and the free space."""
    f, lead = shot["frame"], _lead(shot)
    people = [{"tag": _tag(doc, p["who"]), "where": p["where"], "height": p.get("height"), "on": p.get("on"),
               "actor": p["who"] == lead} for p in shot.get("blocking", [])]
    return {"id": f"{shot['id']}.first", "kind": shot["source"], "size": f["size"], "people": people,
            "relations": list(f.get("relations", [])), "lead_room": dict(f.get("lead_room") or {})}


def gate_cards(doc: dict) -> list[dict]:
    return [gate_card(doc, s) for s in doc["shots"] if s["source"] in ("keyframe", "cut")]


def _where(shot: dict, who: str) -> str:
    for p in shot.get("blocking", []):
        if p["who"] == who:
            return WHERE[p["where"]]
    return ""


def _frame(shot: dict) -> str:
    f = shot["frame"]
    angle = ANGLES.get(f.get("angle", "eye"), "")
    return f"{SIZES[f['size']]} {angle}".strip()


def _a(text: str) -> str:
    return ("an " if text[:1].lower() in "aeiou" else "a ") + text


def keyframe_prompt(doc: dict, shot: dict) -> str:
    """Qwen-Image-2512 + the style LoRA: trigger, shot size and angle, place and light, then every person by tag, screen
    side, gaze and FIRST-frame pose (the start of the action, never its peak: the video needs somewhere to go)."""
    f = shot["frame"]
    place = doc["places"].get(f["place"], f["place"])
    head = f"{doc['style']['trigger']}, {_frame(shot)}, {place}"
    if f.get("light"):
        head += f", {f['light']}"
    if f["size"] == "OTS" and f.get("over"):
        head += f", past the shoulder of {_tag(doc, f['over'])} in the foreground"
    action = shot.get("action") or {}
    parts = [_end(head)] + _people(doc, shot, actor_pose=action.get("start"), layout=True)
    if action and not any(p["who"] == action.get("who") for p in shot.get("blocking", [])):
        parts.append(_end(_cap(action["start"])))
    parts += _layout(shot)
    n = len(shot.get("blocking", []))
    if n and f["size"] not in WIDE:
        parts.append(f"Only these {n} {'person is' if n == 1 else 'people are'} in the picture.")
    return " ".join(parts)


def nextpose_prompt(doc: dict, shot: dict, *, end: bool) -> str:
    """Qwen-Image-Edit-2511 + the scene LoRA, drawn from the master: the training caption's prefix, then only what
    changed (the actor's start or end pose, the others' reaction), never a framing word (KP-07)."""
    action = shot.get("action") or {}
    changes = []
    if action:
        who = action["who"]
        pose = action["settle"] if end else action["start"]
        changes.append(f"{_tag(doc, who)}, {_where(shot, who)}, {pose}".replace(", ,", ","))
        if end and action.get("face"):
            changes.append(action["face"])
    for r in shot.get("reactions", []) if end else []:
        changes.append(f"{_tag(doc, r['who'])} {r['does']}")
    if not changes:
        changes = [_tag(doc, p["who"]) + ", " + (p.get("pose") or "stands") for p in shot.get("blocking", [])]
    return NEXTPOSE + "; ".join(changes) + ". Same characters, same camera; nobody new appears and nobody disappears."


def cut_prompt(doc: dict, shot: dict) -> str:
    """The edit model with the master and the hero sheets: a new size or angle of the same place, light and people."""
    f = shot["frame"]
    over = f", past the shoulder of {_tag(doc, f['over'])}" if f["size"] == "OTS" and f.get("over") else ""
    action = shot.get("action") or {}
    parts = [f"The same place, light and characters as in the first image, now {_a(_frame(shot))}{over}."]
    parts += _people(doc, shot, actor_pose=action.get("start"), layout=True)
    parts += _layout(shot)
    parts.append("Every character looks exactly as on their character sheet.")
    return " ".join(parts)


def video_prompt(doc: dict, shot: dict) -> str:
    """LTX-2.5 from the keyframe: one present-tense paragraph that describes only the change (the picture already
    shows the place): the style sentence, the action start -> peak -> settle, the face, the others, the spoken line in
    quotes with its speaker and voice, who stays in frame, ONE camera sentence, then the sound."""
    s = [_end(doc["style"]["video_sentence"])]
    action = shot.get("action") or {}
    if action:
        where = _where(shot, action["who"])
        if shot["mode"] == "insert" or action["who"] not in {p["who"] for p in shot.get("blocking", [])}:
            lead = ""  # a detail of someone out of frame: the action text names what we see
        else:
            lead = f"{_cap(_tag(doc, action['who']))}, {where}, " if where else _cap(_tag(doc, action["who"])) + " "
        s.append(_end(_cap(f"{lead}{action['start']}, then {action['peak']}, and {action['settle']}")))
        if action.get("face"):
            s.append(_end(_cap(action["face"])))
    reactions = [f"{_tag(doc, r['who'])} {r['does']}" for r in shot.get("reactions", [])]
    if reactions:
        s.append(_end(_cap("; ".join(reactions))))
    d = shot.get("dialogue")
    if d:
        to = {"room": "everyone", "self": "nobody in particular"}.get(d["to"], _tag(doc, d["to"]))
        two = len(shot.get("blocking", [])) == 2 and d["to"] not in ("room", "self")  # the listener is obvious
        voice = doc["cast"].get(d["who"], {}).get("voice")
        how = ", ".join(x for x in (d.get("delivery"), f"in {voice}" if voice else "") if x)
        lang = d.get("language", "English")
        s.append(f'After a short pause, {_tag(doc, d["who"])} says{"" if two else " to " + to} in {lang}{", " + how if how else ""}: '
                 f'"{d["text"].strip()}"')
    else:
        s.append("Nobody speaks.")
    if shot.get("blocking") and not shot.get("exit"):
        s.append("Everyone stays in frame.")
    f = shot["frame"]
    cam = CAMERA[f.get("camera", "static")].format(actor=_tag(doc, action.get("who", "")) if action else "the action")
    if not cam.endswith("."):
        cam = _end(cam + (f", ending on {f['camera_end']}" if f.get("camera_end") else ""))
    s.append(cam)
    snd = shot.get("sound") or {}
    heard = [x for x in [snd.get("ambience"), *snd.get("foley", []), snd.get("loudest"), snd.get("diegetic_music")] if x]
    if heard:
        s.append("We hear " + (", ".join(heard[:-1]) + " and " + heard[-1] if len(heard) > 1 else heard[0]) + ".")
    return " ".join(s)


def compose(doc: dict) -> list[dict]:
    """Every prompt of every shot, in the prompt lint's shape (``shot_prompt_lint``): the first frame (keyframe, next
    pose or cut), the last frame when guided, and the video."""
    style = doc["style"]
    out: list[dict] = []
    for shot in doc["shots"]:
        sid, src = shot["id"], shot["source"]
        if src == "keyframe":
            out.append({"id": f"{sid}.first", "kind": "keyframe", "lora": "style", "prompt": keyframe_prompt(doc, shot),
                        "neg": style.get("neg_keyframe", NEG_KEYFRAME)})
        elif src == "nextpose":
            out.append({"id": f"{sid}.first", "kind": "nextpose", "source": "master", "master": shot.get("master"),
                        "lora": "scene", "prompt": nextpose_prompt(doc, shot, end=False)})
        else:
            out.append({"id": f"{sid}.first", "kind": "cut", "master": shot.get("master"), "lora": "scene",
                        "prompt": cut_prompt(doc, shot)})
        if shot.get("last_frame"):
            out.append({"id": f"{sid}.last", "kind": "nextpose", "source": "master",
                        "master": sid if src == "keyframe" else shot.get("master"), "lora": "scene",
                        "prompt": nextpose_prompt(doc, shot, end=True)})
        out.append({"id": f"{sid}.video", "kind": "video", "seconds": shot["seconds"], "exit": bool(shot.get("exit")),
                    "mode": shot["mode"], "people": len(shot.get("blocking", [])),
                    "diegetic_music": bool((shot.get("sound") or {}).get("diegetic_music")),
                    "prompt": video_prompt(doc, shot), "neg": style.get("neg_video", NEG_VIDEO)})
    return out


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 2}


def check(doc: dict) -> list[dict]:
    """The card rules (KP-15..KP-34) and then the prompt lint on the composed prompts. A schema error stops here."""
    out: list[dict] = []

    def add(rule: str, sev: str, where: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    errors = schema_errors(doc)
    if errors:
        return [{"rule": "KP-00", "severity": "FAIL", "where": "schema", "detail": e} for e in errors]
    cast, shots = doc["cast"], doc["shots"]
    # KP-15: one visible identity tag per hero, the same words everywhere, never a bare role word
    tags: dict[str, str] = {}
    for cid, c in cast.items():
        tag = c["tag"].strip()
        if BARE.fullmatch(tag) or lint.NOBODY.search(tag):
            add("KP-15", "FAIL", cid, f"tag '{tag}' is a bare role word: two visible traits (hair, clothes colour, a prop)")
        elif len(tag.split()) < 5:
            add("KP-15", "REVIEW", cid, f"tag '{tag}' is short: two visible traits tell the model which figure it is")
        low = tag.lower()
        for other, otag in tags.items():
            if low == otag or low in otag or otag in low:
                add("KP-15", "FAIL", cid, f"tag is not distinct from {other}'s: the model cannot tell them apart")
        tags[cid] = low
    names = [c["name"] for c in cast.values() if c.get("name")]
    by_id = {s["id"]: s for s in shots}
    for shot in shots:
        sid, f = shot["id"], shot["frame"]
        present = {p["who"] for p in shot.get("blocking", [])}
        for who in present | {x for x in [(shot.get("action") or {}).get("who"), (shot.get("dialogue") or {}).get("who")] if x}:
            if who not in cast and shot["mode"] != "insert":
                add("KP-15", "FAIL", sid, f"'{who}' is not in the cast: every person needs a tag")
        if f["place"] not in doc["places"]:
            add("KP-00", "FAIL", sid, f"place '{f['place']}' is not in places")
        action = shot.get("action")
        # KP-16: start -> peak -> settle; the first frame shows the start
        if action:
            if action["who"] not in present and shot["mode"] != "insert":
                add("KP-16", "FAIL", sid, "the actor is not in the blocking: the model hands the action to someone else (KP-02)")
            if action["peak"].strip().lower() == action["settle"].strip().lower():
                add("KP-16", "REVIEW", sid, "peak and settle are the same: the shot needs somewhere to land")
            if shot["mode"] == "scene" and not lint.STRONG.search(action["peak"]):
                add("KP-16", "REVIEW", sid, "the peak has no big verb with a body part: a small verb freezes the shot (KP-12)")
        elif shot["mode"] == "scene":
            add("KP-16", "REVIEW", sid, "a scene shot without an action: say what moves (a reaction shot still has one)")
        # KP-17: the emotion as the lens sees it
        for text in [action.get("face", "") if action else "", *(r["does"] for r in shot.get("reactions", []))]:
            if lint.EMOTION.search(text) and not lint.BODY.search(text):
                add("KP-17", "REVIEW", sid, f"'{text}' names a feeling: say what the eyes, brows, mouth or shoulders do")
        # KP-18: the spoken line
        d = shot.get("dialogue")
        if d:
            if shot["mode"] != "scene":
                add("KP-20", "FAIL", sid, f"a line spoken in a {shot['mode']} shot: only scene shots carry sync dialogue")
            if d["who"] not in present:
                add("KP-18", "FAIL", sid, "the speaker is not in the blocking")
            if d["to"] not in present | {"room", "self"}:
                add("KP-18", "FAIL", sid, f"the line is said to '{d['to']}', who is not in the shot (or room / self)")
            n = len(d["text"].split())
            room = SPEECH_WPS * max(0.0, shot["seconds"] - 2 * SPEECH_SETTLE_S)
            if n > room:
                add("KP-18", "REVIEW", sid, f"{n} words in {shot['seconds']:g} s: at most {room:.0f} (BP-100); split the line "
                                            "or lengthen the shot")
            if f["size"] in WIDE | {"MWS"}:
                add("KP-18", "REVIEW", sid, f"the speaker in a {f['size']}: lip-sync needs MS or closer")
        # KP-19: faces the model keeps apart; nobody acts small in a wide
        if f["size"] in CLOSE and len(present) > CLOSE_FACES_MAX:
            add("KP-19", "REVIEW", sid, f"{len(present)} people in a {f['size']}: faces merge past {CLOSE_FACES_MAX} "
                                        "(BP-101); a group is a wide, the acting is a medium")
        if f["size"] in WIDE and action and shot["mode"] == "scene":
            add("KP-19", "REVIEW", sid, "acting in a wide shot: the heroes are small and freeze (KP-13); give the action a medium")
        # KP-20: narrated shots stay silent in frame and never narrate the picture
        if shot.get("narration"):
            if d:
                add("KP-20", "FAIL", sid, "narration and a spoken line on one shot: the narrator never talks over a scene line")
            act = action or {}
            seen = _words(" ".join([act.get("start", ""), act.get("peak", ""), act.get("settle", ""),
                                    *(r["does"] for r in shot.get("reactions", []))]))
            said = _words(shot["narration"])
            if said and seen and len(said & seen) / len(said) >= 0.5:
                add("KP-20", "REVIEW", sid, "the narration says what the picture shows: give the narrator what the heroes "
                                            "cannot know, let the picture show the rest")
        # KP-31..KP-34: a drawn first frame (keyframe or cut) states its composition
        if shot["source"] in ("keyframe", "cut") and shot.get("blocking"):
            for p in shot["blocking"]:
                if not p.get("on"):
                    add("KP-31", "FAIL", sid, f"{p['who']}: what does the figure stand or sit on? ('standing on the packed snow')")
                elif not SUPPORT.search(p["on"]):
                    add("KP-31", "FAIL", sid, f"{p['who']}: '{p['on']}' names no surface ('standing on ...', 'sitting in ...')")
            lead = next(p for p in shot["blocking"] if p["who"] == _lead(shot))
            if not (lead.get("height") or lead.get("height_pct")):
                add("KP-32", "FAIL", sid, f"{lead['who']}: how much of the frame height does the figure fill?")
            if action and not f.get("lead_room"):
                add("KP-34", "FAIL", sid, "where is the free space the action moves into? (lead_room; side none if it stays)")
        for r in f.get("relations", []):
            if not CLEAR.search(r):
                why = "a vague relation" if VAGUE.search(r) else "no relation"
                add("KP-33", "FAIL", sid, f"'{r}': {why}; say behind, in front of, on top of, under, to the left of ...")
        # KP-27: next poses and cuts come from a keyframe master of the same scene
        if shot["source"] in ("nextpose", "cut"):
            m = by_id.get(shot.get("master", ""))
            if not m or m["source"] != "keyframe" or m["scene"] != shot["scene"]:
                add("KP-27", "FAIL", sid, f"master '{shot.get('master')}' must be a keyframe shot of scene {shot['scene']}")
        if f.get("camera", "static") == "follow" and not action:
            add("KP-04", "REVIEW", sid, "a follow move with nothing to follow")
    # KP-26: the scene's shot grammar (establish, size variety, screen sides, a close shot for the exchange)
    scenes: dict[str, list[dict]] = {}
    for shot in shots:
        scenes.setdefault(shot["scene"], []).append(shot)
    for scene, group in scenes.items():
        people = {p["who"] for s in group for p in s.get("blocking", [])}
        first = group[0]
        if len(people) >= 2 and first["frame"]["size"] not in WIDE | {"MWS"} and first["mode"] != "establish":
            add("KP-26", "REVIEW", scene, "the scene opens close: show where everyone is first (a wide or full shot), "
                                          "or say why the opening is a close hook")
        run = 1
        for a, b in zip(group, group[1:]):
            run = run + 1 if a["frame"]["size"] == b["frame"]["size"] else 1
            if run > SAME_SIZE_RUN_MAX:
                add("KP-26", "REVIEW", b["id"], f"{run} {b['frame']['size']} shots in a row (BP-103): change the size")
        side: dict[str, str] = {}
        for s in group:
            if s["frame"]["size"] == "OTS" or s["frame"].get("crosses_line"):
                continue
            for p in s.get("blocking", []):
                lr = p["where"].split("_")[0]
                if lr == "center":
                    continue
                if p["who"] in side and side[p["who"]] != lr:
                    add("KP-26", "REVIEW", s["id"], f"{p['who']} jumps from the {side[p['who']]} to the {lr}: keep screen "
                                                    "sides (the 180-degree line) or mark crosses_line")
                side[p["who"]] = lr
        lines = [s for s in group if s.get("dialogue")]
        if len(lines) >= 2 and not any(s["frame"]["size"] in {"MCU", "CU", "ECU", "OTS"} for s in group):
            add("KP-26", "REVIEW", scene, "an exchange without a close shot: the turn of the scene plays on a face")
    # the composed prompts go through the prompt lint (KP-01..KP-14 and its KP-17..KP-25 checks), names included (KP-22)
    for found in lint.check(compose(doc), names=names):
        out.append(found)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("check", "compose"):
        print(__doc__)
        return 2
    doc = load(argv[1])
    if argv[0] == "compose":
        errors = schema_errors(doc)
        if errors:
            print("\n".join(errors))
            return 1
        prompts = compose(doc)
        text = json.dumps({"shots": prompts, "gate": gate_cards(doc)}, ensure_ascii=False, indent=1)
        if "--out" in argv:
            from explainer_engine.core.store import write_text_atomic

            write_text_atomic(Path(argv[argv.index("--out") + 1]), text + "\n")
        else:
            print(text)
        return 0
    found = check(doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(f"{len(doc.get('shots', []))} shot(s), {fails} FAIL, {len(found) - fails} REVIEW")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
