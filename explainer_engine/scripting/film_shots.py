"""Film shot cards (``film_shots/1``): the animated shots of an approved script, and the prompts composed from them.

A shot card says what the shot is for (``beat``), the frame (size, angle, camera, place, light), who stands where and
looks where (``blocking``), the one action with its start, peak and settle, the others' reactions, the line spoken (or
the narrator's line over it) and the sound. ``compose`` writes every prompt from those fields, so the keyframe, the next
pose, the cut and the video always say the same thing in each model's own grammar; ``check`` runs the card rules
(KP-15..KP-34, docs/SHOT_PROMPTS.md) and then the prompt lint (KP-01..KP-14) on what it composed. Cards marked
``"engine": "script_engine/1"`` (docs/SCRIPT_ENGINE.md) also get the episode rules KP-35..KP-43 and ZI-02/ZI-03:
rhythm, clip length, animation tiers, camera moves, narration blocks, the outro, the cold open's teasers, cutaways out of
one place, runs of spoken lines, and a claim behind every number.

    python -m explainer_engine.scripting.film_shots check <film_shots.json>
    python -m explainer_engine.scripting.film_shots compose <film_shots.json> [--out prompts.json]
    python -m explainer_engine.scripting.film_shots script <film_shots.json> [--out script.md]
    python -m explainer_engine.scripting.film_shots shotlist <film_shots.json> [--out shotlist.md]   # script + prompts
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.compose import episode_look
from explainer_engine.qa import style_prompt
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
# the episode rules of the script engine v1 (KP-35..KP-40, docs/research/SCRIPT_ENGINE_V1_2026-10-24.md)
SHOTS_PER_MIN = tuple(sourced_rules.T("BP-107", "shots_per_min"))  # KP-35
MEDIAN_SHOT_S = tuple(sourced_rules.T("BP-107", "median_shot_s"))
CLIP_MAX_S = sourced_rules.T("BP-108", "clip_max_s")  # KP-36
KEYPOSE_AFTER_S = sourced_rules.T("BP-108", "keypose_after_s")
HOLD_SHARE_MAX = sourced_rules.T("BP-109", "hold_share_max")  # KP-37
CAMERA_MOVE_SHARE_MAX = sourced_rules.T("BP-110", "camera_move_share_max")  # KP-38
NARRATION_BLOCK_MAX_S = sourced_rules.T("BP-104", "narration_block_max_s")  # KP-39
NARRATOR_SHARE = tuple(sourced_rules.T("BP-105", "narrator_share"))
NARRATION_WPM_MAX = sourced_rules.T("BP-01", "wpm_max")
OUTRO_WORLDS_MIN = sourced_rules.T("BP-106", "worlds_on_min"), sourced_rules.T("BP-106", "worlds_coming_min")  # KP-40
SIGN_OFF = [x.lower() for x in sourced_rules.T("BP-43", "lexicon")]
TEASER_WINDOW_S = sourced_rules.T("BP-111", "teaser_window_s")  # KP-41
TEASERS_MIN = sourced_rules.T("BP-111", "teasers_min")
SAME_PLACE_MAX_S = sourced_rules.T("BP-112", "same_place_max_s")  # KP-42
TALK_RUN_MAX = sourced_rules.T("BP-113", "talk_run_max")  # KP-43
ENGINE = "script_engine/1"
FPS = 24
# the model each tier runs on (SCRIPT_ENGINE.md, "Variants in use"): hold = our camera code on the keyframe, no video model
MODEL = {"hold": "camera", "light": "ltx-2.5-distilled", "full": "ltx-2.5-dev"}
NUMBER = re.compile(r"\d|\b(?:hundred|thousand|million|dozen|half|twice|three|four|five|six|seven|eight|nine|ten|"
                    r"eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b", re.I)

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
# LT-65 (docs/LORA_TRAINING.md, qa/style_prompt.py; revised 2026-10-25): a style-LoRA prompt has the shape of the prompts
# that drew the approved look: the trigger, then a short story of the moment (a place, an action at its peak, someone's
# reaction, the bodies' caricature words, a light source), at most MOMENT_WORDS_MAX words, no camera, size or position
# words (those are the layout's: boxes, the composition of assets, ASSET_COMPOSE.md). The caption tail is retired.
MOMENT_WORDS_MAX = style_prompt.MAX_WORDS
BODY_WORDS = "thin-limbed and bulging-eyed"  # the caricature words a moment gives its lead (a card may set style.body)
NEXTPOSE = "nextpose, a later frame of the same continuous animated shot, same camera: "
NEG_KEYFRAME = style_prompt.NEGATIVE  # LT-66 A3: a style-LoRA picture's negative is exactly this, never per episode
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
    """The cards; a ``style.look`` that names a look file (``episode_look/1``, AC-16) is read relative to them."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    look = doc.get("style", {}).get("look")
    if isinstance(look, str):
        doc["style"]["look"] = json.loads((Path(path).parent / look).read_text(encoding="utf-8"))
    return doc


def _look(doc: dict, prompt: str, light: str | None = None) -> str:
    """AC-17: the episode's colour-and-light phrase (or the scene's named variant) at the end of a style-LoRA prompt,
    through ``episode_look.apply`` so the words are never written by hand."""
    look = doc["style"].get("look")
    if not look:
        return prompt
    return episode_look.apply(prompt, look, light if light in look.get("lights", {}) else None)[0]  # unknown: AC-17 FAIL


def _look_words(doc: dict, light: str | None = None) -> int:
    look = doc["style"].get("look")
    if not look:
        return 0
    return len((look["lights"][light] if light in look.get("lights", {}) else look["phrase"]).split())


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


# KP-32: the size is said in words; a number in the prompt is drawn as rulers and percentages (test v2 2026-10-24: 6 of
# 10 pictures) and does not size the figure better, so height_pct is turned into the nearest word and kept for the gate
PCT_WORDS = ((30, "quarter"), (42, "third"), (58, "half"), (78, "two_thirds"), (101, "most"))


def _height_word(p: dict) -> str | None:
    if p.get("height"):
        return p["height"]
    if p.get("height_pct"):
        return next(w for limit, w in PCT_WORDS if p["height_pct"] < limit)
    return None


def _height(p: dict) -> str:
    word = _height_word(p)
    if word == "most":
        return "filling most of the frame height"
    return f"filling about {HEIGHTS[word]} of the frame height" if word else ""


def _head_noun(tag: str) -> str:
    """The noun a tag is about: 'the woolly mammoth with a broken left tusk' -> 'mammoth'."""
    core = re.split(r"\s+(?:with|in|on|beside|wearing|holding|from)\s+|,", tag.strip(), maxsplit=1)[0]
    return core.split()[-1].lower()


def _people(doc: dict, shot: dict, *, actor_pose: str | None, layout: bool = False) -> list[str]:
    """Each person by tag, side, gaze and pose; with ``layout`` (a drawn first frame) also what they stand on and how
    much of the frame height they fill (KP-31, KP-32)."""
    action = shot.get("action") or {}
    out = []
    for p in shot.get("blocking", []):
        if p.get("partial"):  # only part of this figure is in the frame (an animal's trunk, a hand)
            out.append(_end(f"Only {p['partial']} of {_tag(doc, p['who'])} reaches into the frame {WHERE[p['where']]}"))
            continue
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


def _plural(name: str) -> str:
    """'yellow city bus' -> 'yellow city buses' (the gate asks 'How many <plural> are in the picture?')."""
    head, _, last = name.rpartition(" ")
    if re.search(r"(s|x|z|ch|sh)$", last):
        last += "es"
    elif re.search(r"[^aeiou]y$", last):
        last = last[:-1] + "ies"
    else:
        last += "s"
    return f"{head} {last}".strip()


def _things(f: dict) -> list[dict]:
    """KG-01 for objects: ``frame.things`` {name: count} (or {name: {count, plural}}) -> the gate's {plural, count}."""
    out = []
    for name, v in (f.get("things") or {}).items():
        v = v if isinstance(v, dict) else {"count": v}
        out.append({"name": name, "plural": v.get("plural") or _plural(name), "count": v["count"]})
    return out


def gate_card(doc: dict, shot: dict, end: bool = False) -> dict:
    """What the keyframe gate (PR #22, qa/keyframe_gate.py) checks a drawn frame against: the people by tag, side,
    height and support (the lead marked ``actor``), the relations, the free space, the exact counts of things (KG-01:
    one bus is one bus) and what must not be there (KG-21: the world's ``absent`` plus the frame's). ``end`` is the
    guided last frame (the settle, a next pose); a lead who exits is not in it."""
    f, lead = shot["frame"], _lead(shot)
    people = [{"tag": _tag(doc, p["who"]), "where": p["where"], "height": _height_word(p), "on": p.get("on"),
               "actor": p["who"] == lead, **({"partial": p["partial"]} if p.get("partial") else {})}
              for p in shot.get("blocking", []) if not (end and shot.get("exit") and p["who"] == lead)]
    absent = list(dict.fromkeys([*doc.get("absent", []), *f.get("absent", [])]))
    src = shot["source"]
    card = {"id": f"{shot['id']}.{'last' if end else 'first'}", "kind": "nextpose" if end else src, "size": f["size"],
            "people": people, "relations": list(f.get("relations", [])), "lead_room": dict(f.get("lead_room") or {}),
            "things": _things(f), "absent": absent}
    if end or src != "keyframe":  # KG-13 compares it with the picture it was edited from (as compose names it)
        card["master"] = shot.get("master") if (src == "nextpose" or not end) else shot["id"]
    return card


def gate_cards(doc: dict) -> list[dict]:
    """A card for every drawn frame: each first frame (keyframe, next pose, cut) and each guided last frame."""
    out = []
    for s in doc["shots"]:
        if s.get("teaser_of"):
            continue  # a teaser reuses its payoff's frames
        out.append(gate_card(doc, s))
        if s.get("last_frame"):
            out.append(gate_card(doc, s, end=True))
    return out


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


def _short(text: str) -> str:
    """A place's first clause: 'a French army camp on the open steppe, white canvas tents, ...' -> its head."""
    return text.split(",")[0].strip()




def _core(tag: str) -> str:
    """A tag's head phrase: 'the tall khan with a long grey beard ...' -> 'the tall khan' (still not a bare role word)."""
    return re.split(r"\s+(?:with|in|on|beside|wearing|holding|from)\s+|,", tag.strip(), maxsplit=1)[0]


def keyframe_prompt(doc: dict, shot: dict) -> str:
    """The moment for Qwen-Image-2512 + the style LoRA (LT-65): ``<trigger>, <place>, <lead> <body words> <action at its
    peak>, <a reaction>, <light>`` in at most MOMENT_WORDS_MAX words, with no camera, size or position. The peak and a
    reaction carry the mood the approved pictures had; the video's first frame in the START pose (KP-16) and the layout
    (sides, heights, supports, free space: the gate card) come from the composition of assets, not from these words.
    Each figure is named once (LY-09): the lead and the reacting figure by tag (the tag's head phrase when words run
    out), the others by their head phrase while words remain."""
    f = shot["frame"]
    place = _short(doc["places"].get(f["place"], f["place"]))
    action = shot.get("action") or {}
    body = doc["style"].get("body", BODY_WORDS)
    people = shot.get("blocking", [])
    lead = _lead(shot)
    reacts = [r for r in shot.get("reactions", []) if r["who"] in {p["who"] for p in people} and r["who"] != lead]
    # each piece runs from bare to full; pieces are raised in order while the moment fits
    pieces: list[list[str]] = [[place]]
    if lead:
        tag = _tag(doc, lead)
        doing = action.get("peak") if action.get("who") == lead else next(
            (p.get("pose") for p in people if p["who"] == lead and p.get("pose")), None)
        core = f"{_core(tag)}, {body}," if body else _core(tag)
        full = f"{tag}, {body}," if body else tag
        pieces.append([f"{_core(tag)} {doing}" if doing else _core(tag), f"{core} {doing}" if doing else core,
                       f"{full} {doing}" if doing else full])
    elif action.get("peak"):
        pieces.append([action["peak"]])
    for r in reacts[:1]:
        pieces.append(["", f"{_core(_tag(doc, r['who']))} {r['does']}", f"{_tag(doc, r['who'])} {r['does']}"])
    seen = {lead} | {r["who"] for r in reacts[:1]}
    for p in people:
        if p["who"] not in seen:
            core = _core(_tag(doc, p["who"]))
            pieces.append(["", f"only {p['partial']} of {core}" if p.get("partial") else core])
    light = len(pieces)
    pieces.append(["", f["light"]] if f.get("light") else [""])
    level = [0] * len(pieces)
    budget = MOMENT_WORDS_MAX - len(doc["style"]["trigger"].split()) - _look_words(doc, f.get("look"))  # AC-17

    def text() -> str:
        return ", ".join(x for x in (pc[lv] for pc, lv in zip(pieces, level)) if x).replace(",,", ",")

    order = [(1, 1), (light, 1), (2, 1), (1, 2), (2, 2)] + [(k, 1) for k in range(3, light)]
    for k, lv in order:
        if k < len(pieces) and lv < len(pieces[k]) and lv > level[k]:
            old, level[k] = level[k], lv
            if len(text().split()) > budget:
                level[k] = old
    return _look(doc, f"{doc['style']['trigger']}, {text()}", f.get("look"))


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
    by_id = {s["id"]: s for s in doc["shots"]}
    out: list[dict] = []
    for shot in doc["shots"]:
        sid, src = shot["id"], shot["source"]
        if shot.get("teaser_of"):
            # a teaser is a piece of its payoff's clip (KP-41): nothing new is drawn or rendered
            of = by_id[shot["teaser_of"]]
            start = round(max(0.0, (of["seconds"] - shot["seconds"]) / 2), 2)
            out.append({"id": f"{sid}.video", "kind": "reuse", "of": f"{of['id']}.video", "seconds": shot["seconds"],
                        "trim": [start, round(start + shot["seconds"], 2)]})
            continue
        if src == "keyframe":
            out.append({"id": f"{sid}.first", "kind": "keyframe", "lora": "style", "prompt": keyframe_prompt(doc, shot),
                        "neg": style_prompt.NEGATIVE, "inference": style_prompt.INFERENCE})
        elif src == "nextpose":
            out.append({"id": f"{sid}.first", "kind": "nextpose", "source": "master", "master": shot.get("master"),
                        "lora": "scene", "prompt": nextpose_prompt(doc, shot, end=False)})
        else:
            out.append({"id": f"{sid}.first", "kind": "cut", "master": shot.get("master"), "lora": "scene",
                        "prompt": cut_prompt(doc, shot)})
        if shot.get("last_frame"):
            out.append({"id": f"{sid}.last", "kind": "nextpose", "source": "master",
                        # the settle is a next pose of this shot's own first frame when it was drawn (keyframe or cut),
                        # of the scene's master when the first frame is itself a next pose (same camera)
                        "master": shot.get("master") if src == "nextpose" else sid, "lora": "scene",
                        "prompt": nextpose_prompt(doc, shot, end=True)})
        tier = shot.get("tier", "full")
        out.append({"id": f"{sid}.video", "kind": "video", "seconds": shot["seconds"], "exit": bool(shot.get("exit")),
                    "tier": tier, "model": MODEL[tier], "fps": FPS, "frames": frames(shot["seconds"]),
                    "mode": shot["mode"], "people": len(shot.get("blocking", [])),
                    "diegetic_music": bool((shot.get("sound") or {}).get("diegetic_music")),
                    "prompt": video_prompt(doc, shot), "neg": style.get("neg_video", NEG_VIDEO),
                    **_acting(doc, shot)})
    return out


def _acting(doc: dict, shot: dict) -> dict:
    """KP-43: a spoken line on a face is checked for acting (the mouth moves only on the line, the action's peak is
    visible, the face reaches the card's face, the motion does not freeze); a take that fails twice is replaced by the
    fallback, which hides the mouth: over the speaker's shoulder onto the listener, or the speaker's hands."""
    d = shot.get("dialogue")
    if not d or shot.get("tier", "full") != "full" or shot["frame"]["size"] not in CLOSE:
        return {}
    a = shot.get("action") or {}
    checks = {"lips": d["text"], "peak": a.get("peak"), **({"face": a["face"]} if a.get("face") else {})}
    listener = d.get("to") if d.get("to") in doc["cast"] else None
    fallback = ({"kind": "ots_on_listener", "over": d["who"], "on": listener} if listener
                else {"kind": "insert_hands", "who": d["who"], "does": a.get("peak")})
    return {"qa": ["acting"], "acting": checks, "fallback": fallback}


def frames(seconds: float, fps: int = FPS) -> int:
    """LTX's frame count for a clip: 8k + 1 frames covering the seconds (LT-07)."""
    return 8 * -(-round(seconds * fps) // 8) + 1


def _sheet_text(doc: dict, tag: str) -> str:
    """A hero sheet in the moment shape (LT-65): the most of these pieces that fits MOMENT_WORDS_MAX words."""
    head = f"{doc['style']['trigger']}, four variants of {tag}"
    pieces = [doc["style"].get("body", BODY_WORDS), "side by side", "neutral faces", "warm studio light",
              "each a little different in face and build"]
    out = head
    for x in pieces:
        if len(f"{out}, {x}".split()) + _look_words(doc) <= MOMENT_WORDS_MAX:
            out = f"{out}, {x}"
    return _look(doc, out)


def sheet_prompts(doc: dict) -> list[dict]:
    """A new hero's look is chosen by the creator from one collage of variants (invariant 6), drawn by Qwen-Image-2512
    with the style LoRA; the chosen variant becomes the hero sheet every keyframe and next pose is checked against.
    Groups (a cast entry without a story name) need no sheet: they are drawn inside the shots."""
    out = []
    for cid, c in doc["cast"].items():
        if not c.get("name"):
            continue
        tag = c["tag"]
        out.append({"id": f"sheet.{cid}", "kind": "keyframe", "lora": "style",
                    "prompt": _sheet_text(doc, tag),
                    "neg": style_prompt.NEGATIVE, "inference": style_prompt.INFERENCE})
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
                if p.get("partial"):
                    continue  # a figure cut by the frame edge stands on nothing we see
                if not p.get("on"):
                    add("KP-31", "FAIL", sid, f"{p['who']}: what does the figure stand or sit on? ('standing on the packed snow')")
                elif not SUPPORT.search(p["on"]):
                    add("KP-31", "FAIL", sid, f"{p['who']}: '{p['on']}' names no surface ('standing on ...', 'sitting in ...')")
            lead = next(p for p in shot["blocking"] if p["who"] == _lead(shot))
            if not (lead.get("height") or lead.get("height_pct")):
                add("KP-32", "FAIL", sid, f"{lead['who']}: how much of the frame height does the figure fill?")
            if action and not f.get("lead_room"):
                add("KP-34", "FAIL", sid, "where is the free space the action moves into? (lead_room; side none if it stays)")
        heads = {_head_noun(cast[w]["tag"]): w for w in present if w in cast}
        for r in f.get("relations", []):
            for m in re.finditer(r"\b(?:a|an|another|one)\s+((?:[\w-]+\s*){1,4})", r, re.I):
                for word in m.group(1).lower().split():  # the article's noun phrase, up to four words
                    noun = word if word in heads else word[:-1] if word.endswith("s") and word[:-1] in heads else None
                    if noun:
                        add("KP-33", "FAIL", sid, f"'{m.group(0).strip()}' in a relation draws a second {noun}: name the "
                                                  f"one in the picture as '{_tag(doc, heads[noun])}'")
                        break
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
    if doc.get("engine") == ENGINE:
        out += episode_check(doc)
    # the composed prompts go through the prompt lint (KP-01..KP-14 and its KP-17..KP-25 checks), names included (KP-22)
    for found in lint.check([p for p in compose(doc) if p["kind"] != "reuse"], names=names):
        out.append(found)
    out += style_check(doc)
    out += absent_check(doc)
    return out


def _absent_words(item: str) -> list[str]:
    """'a paved road' -> ['paved', 'road']: the words of an absent thing a prompt must not say."""
    return [w for w in re.findall(r"[a-z]+", item.lower()) if w not in STOP and len(w) > 2]


def absent_check(doc: dict) -> list[dict]:
    """KP-44: a picture prompt never says a word of what its frame must not show (the world's ``absent`` and
    ``frame.absent``). Models draw what is named, also inside another name or after "no": the Qwen-Image-2.1 style LoRA
    drew a city behind every "city bus" (base model at step 0 none, LoRA steps 250 and 500 did, 2026-10-25). Spoken
    lines in quotes are left out: they are the line, not the picture."""
    out, by_id = [], {s["id"]: s for s in doc["shots"]}
    for p in compose(doc):
        shot = by_id.get(p["id"].rsplit(".", 1)[0])
        if not shot or p["kind"] == "reuse":
            continue
        seen = re.sub(r'"[^"]*"', "", p["prompt"])  # a spoken line in quotes is sound, not a picture word
        for item in dict.fromkeys([*doc.get("absent", []), *shot["frame"].get("absent", [])]):
            for w in _absent_words(item):
                m = re.search(rf"\b{w}(e?s)?\b", seen, re.I)
                if m:
                    out.append({"rule": "KP-44", "severity": "REVIEW", "where": p["id"],
                                "detail": f"'{m.group(0)}' names '{item}', which must be absent: say it another way"})
    return out


def style_check(doc: dict) -> list[dict]:
    """LT-65/LT-66: every style-LoRA prompt (moment or hero sheet) passes ``qa/style_prompt.check``: the trigger first, at
    most its word limit, no caption tail, no washed-out light, no camera or size words, no other medium or art style; the
    negative is exactly ``style_prompt.NEGATIVE`` (A3); the episode look's phrase and variants pass AC-17."""
    out = []
    if doc["style"].get("neg_keyframe") not in (None, style_prompt.NEGATIVE):
        out.append({"rule": "LT-66", "severity": "FAIL", "where": "style.neg_keyframe",
                    "detail": "A3: the style LoRA's negative is exactly style_prompt.NEGATIVE"})
    look = doc["style"].get("look")
    if look:  # AC-17: the phrase and every light variant the shots name
        names = ({s["frame"].get("look") for s in doc["shots"]} - {None}) & set(look.get("lights", {}))
        out += [{"rule": f["rule"], "severity": f["severity"], "where": f"style.look.{n or 'phrase'}", "detail": f["detail"]}
                for n in [None, *sorted(names)] for f in episode_look.check_phrase(look["lights"][n] if n else look["phrase"])]
        out += [{"rule": "AC-17", "severity": "FAIL", "where": s["id"], "detail": f"no light variant '{s['frame']['look']}'"}
                for s in doc["shots"] if s["frame"].get("look") and s["frame"]["look"] not in look.get("lights", {})]
        if any(f["severity"] == "FAIL" for f in out):
            return out
    for p in [*sheet_prompts(doc), *compose(doc)]:
        if p.get("lora") == "style":
            out += [{"rule": f["rule"], "severity": f["severity"], "where": p["id"], "detail": f["detail"]}
                    for f in style_prompt.check(p["prompt"])]
    return out


def episode_check(doc: dict) -> list[dict]:
    """The episode rules of the script engine v1: rhythm (KP-35), clip length (KP-36), tiers (KP-37), camera moves
    (KP-38), narration blocks and the narrator's share (KP-39), the outro (KP-40), a tier on every shot (ZI-03) and a
    claim behind every number the narrator says (ZI-02)."""
    out: list[dict] = []

    def add(rule: str, sev: str, where: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    shots, claims = doc["shots"], doc.get("claims", {})
    total = sum(s["seconds"] for s in shots)
    for s in shots:
        sid, tier = s["id"], s.get("tier")
        if not tier:
            add("ZI-03", "FAIL", sid, "no tier: say hold, light or full (KP-37)")
        if s["seconds"] > CLIP_MAX_S:
            add("KP-36", "REVIEW", sid, f"{s['seconds']:g} s in one clip: past {CLIP_MAX_S:g} s people duplicate and fade "
                                        "(BP-108); cut it in two")
        if s["seconds"] > KEYPOSE_AFTER_S and s.get("action") and tier != "hold" and not s.get("last_frame"):
            add("KP-36", "REVIEW", sid, f"{s['seconds']:g} s with an action and no drawn last frame: guide the settle "
                                        "(last_frame) so a key pose lands every few seconds (BP-108)")
        if s.get("dialogue") and tier in ("hold", "light"):
            add("KP-37", "FAIL", sid, f"a spoken line on a {tier} shot: lips and acting need the full tier")
        elif s["mode"] == "scene" and s.get("action") and tier == "hold":
            add("KP-37", "REVIEW", sid, "an acted peak on a hold: a still cannot act it; light or full")
        for c in s.get("claims", []):
            if c not in claims:
                add("ZI-02", "FAIL", sid, f"claim '{c}' is not in the claim map")
        if s.get("narration") and NUMBER.search(s["narration"]) and not s.get("claims"):
            add("ZI-02", "FAIL", sid, "the narrator says a number with no claim behind it: add the claim id (and its "
                                      "source to the claim map) or cut the number")
    if total >= 60:
        per_min = len(shots) / (total / 60)
        if not SHOTS_PER_MIN[0] <= per_min <= SHOTS_PER_MIN[1]:
            add("KP-35", "REVIEW", "episode", f"{per_min:.1f} shots a minute (aim {SHOTS_PER_MIN[0]}-{SHOTS_PER_MIN[1]}, BP-107)")
        lengths = sorted(s["seconds"] for s in shots)
        mid = len(lengths) // 2
        median = lengths[mid] if len(lengths) % 2 else (lengths[mid - 1] + lengths[mid]) / 2
        if not MEDIAN_SHOT_S[0] <= median <= MEDIAN_SHOT_S[1]:
            add("KP-35", "REVIEW", "episode", f"median shot {median:g} s (aim {MEDIAN_SHOT_S[0]:g}-{MEDIAN_SHOT_S[1]:g} s, BP-107)")
    holds = sum(1 for s in shots if s.get("tier") == "hold") / len(shots)
    if holds > HOLD_SHARE_MAX:
        add("KP-37", "REVIEW", "episode", f"{holds:.0%} of the shots are held pictures (at most {HOLD_SHARE_MAX:.0%}, "
                                          "BP-109): the cartoons hold a still only on establishing shots")
    moving = sum(1 for s in shots if s["frame"].get("camera", "static") != "static") / len(shots)
    if moving > CAMERA_MOVE_SHARE_MAX:
        add("KP-38", "REVIEW", "episode", f"the camera moves on {moving:.0%} of the shots (at most "
                                          f"{CAMERA_MOVE_SHARE_MAX:.0%}, BP-110)")
    # KP-39: an unbroken narration block (no line spoken between) and whether its words fit its pictures
    block: list[dict] = []
    for s in [*shots, None]:
        if s is not None and not s.get("dialogue"):
            block.append(s)
            continue
        said = [b for b in block if b.get("narration")]
        if said:
            first = block.index(said[0])
            span = block[first:block.index(said[-1]) + 1]
            secs = sum(b["seconds"] for b in span)
            words = sum(len(b["narration"].split()) for b in said)
            where = f"{span[0]['id']}..{span[-1]['id']}"
            if secs > NARRATION_BLOCK_MAX_S:
                add("KP-39", "REVIEW", where, f"{secs:.0f} s of narration with no line spoken: give the scene back "
                                              f"within {NARRATION_BLOCK_MAX_S:g} s (BP-104)")
            room = (secs + sum(b["seconds"] for b in block[block.index(said[-1]) + 1:])) * NARRATION_WPM_MAX / 60
            if words > room:
                add("KP-39", "REVIEW", where, f"{words} narrator words over {room * 60 / NARRATION_WPM_MAX:.0f} s of "
                                              f"pictures: more than {NARRATION_WPM_MAX} wpm (BP-01); add shots or cut words")
        block = []
    n_words = sum(len(s["narration"].split()) for s in shots if s.get("narration"))
    d_words = sum(len(s["dialogue"]["text"].split()) for s in shots if s.get("dialogue"))
    if n_words + d_words and total >= 60:
        share = n_words / (n_words + d_words)
        if not NARRATOR_SHARE[0] <= share <= NARRATOR_SHARE[1]:
            add("KP-39", "REVIEW", "episode", f"the narrator has {share:.0%} of the words (aim {NARRATOR_SHARE[0]:.0%}-"
                                              f"{NARRATOR_SHARE[1]:.0%}, BP-105)")
    # KP-41: the cold open shows pieces of the conflict to come, cut from the later shots themselves
    by_id = {s["id"]: i for i, s in enumerate(shots)}
    t, teasers = 0.0, 0
    for i, s in enumerate(shots):
        of = s.get("teaser_of")
        if of:
            if of not in by_id or by_id[of] <= i:
                add("KP-41", "FAIL", s["id"], f"teaser_of '{of}' is not a later shot: a teaser is a piece of a shot to come")
            elif s["seconds"] > shots[by_id[of]]["seconds"]:
                add("KP-41", "FAIL", s["id"], f"the teaser is longer than its payoff {of}")
            elif t < TEASER_WINDOW_S:
                teasers += 1
        t += s["seconds"]
    if total >= 60 and teasers < TEASERS_MIN:
        add("KP-41", "REVIEW", "opening", f"{teasers} teaser shot(s) in the first {TEASER_WINDOW_S:g} s: show at least "
                                          f"{TEASERS_MIN} pieces of the conflict to come (teaser_of, BP-111)")
    # KP-42: talk in one place is broken by a cutaway that shows what the talk is about
    run: list[dict] = []
    for s in [*shots, None]:
        if s is not None and (not run or s["frame"]["place"] == run[-1]["frame"]["place"]):
            run.append(s)
            continue
        secs = sum(r["seconds"] for r in run)
        if secs > SAME_PLACE_MAX_S:
            add("KP-42", "REVIEW", f"{run[0]['id']}..{run[-1]['id']}", f"{secs:.0f} s in '{run[0]['frame']['place']}' "
                f"with no cutaway: show the plan or its cost while it is told (at most {SAME_PLACE_MAX_S:g} s, BP-112)")
        run = [s] if s is not None else []
    # KP-43: a run of spoken lines rests on the AI's acting; a reaction, an insert or a cutaway breaks it
    talk: list[dict] = []
    for s in [*shots, None]:
        if s is not None and s.get("dialogue"):
            talk.append(s)
            continue
        if len(talk) > TALK_RUN_MAX:
            add("KP-43", "REVIEW", f"{talk[0]['id']}..{talk[-1]['id']}", f"{len(talk)} spoken lines in a row: after "
                f"{TALK_RUN_MAX} put in a silent reaction, an insert or a cutaway (BP-113)")
        talk = []
    # KP-40: the outro points to the channel's worlds; never a dry sign-off
    tail = " ".join(s.get("narration", "") for s in shots[-6:]).lower()
    for phrase in SIGN_OFF:
        if phrase in tail:
            add("KP-40", "FAIL", "outro", f"'{phrase}' is a sign-off (BP-43): point to the channel's worlds instead")
    if "subscribe" in tail:
        ch = doc.get("channel") or {}
        on = [w for w in ch.get("worlds_on", []) if w.lower() in tail]
        coming = [w for w in ch.get("worlds_coming", []) if w.lower() in tail]
        if len(on) < OUTRO_WORLDS_MIN[0] or len(coming) < OUTRO_WORLDS_MIN[1]:
            add("KP-40", "FAIL", "outro", "a subscribe line names the worlds already on the channel and the worlds coming "
                                          "(the channel block's words, BP-106)")
    return out


def script(doc: dict) -> str:
    """The readable script of the cards: scene by scene, the clock, who speaks, the narrator's lines and the claims
    behind them. What the narrator reads (ElevenLabs) and what the clips say (LTX) both come from here."""
    lines = [f"# {doc['episode']}", ""]
    t, scene = 0.0, None
    for s in doc["shots"]:
        if s["scene"] != scene:
            scene = s["scene"]
            lines += ["", f"## {scene}", ""]
        clock = f"{int(t // 60)}:{t % 60:04.1f}"
        if s.get("dialogue"):
            d = s["dialogue"]
            name = doc["cast"].get(d["who"], {}).get("name") or d["who"]
            lines.append(f"- `{clock}` {s['id']} **{name.upper()}**: \"{d['text']}\"")
        elif s.get("narration"):
            ref = f" [{', '.join(s['claims'])}]" if s.get("claims") else ""
            lines.append(f"- `{clock}` {s['id']} NARRATOR: {s['narration']}{ref}")
        else:
            lines.append(f"- `{clock}` {s['id']} ({s['beat']})")
        t += s["seconds"]
    lines += ["", f"Runtime {int(t // 60)}:{t % 60:04.1f}, {len(doc['shots'])} shots."]
    if doc.get("claims"):
        lines += ["", "## Claims", ""]
        lines += [f"- **{cid}** ({c.get('kind', 'fact')}): {c['text']} Source: {c['source']}" for cid, c in doc["claims"].items()]
    return "\n".join(lines) + "\n"


def shotlist(doc: dict) -> str:
    """The script with every prompt under its shot: what the creator reads to judge the pictures before anything is
    drawn. The prompts are the composer's own (ZI-01), never retyped; a teaser names the clip it is cut from."""
    prompts: dict[str, list[dict]] = {}
    for p in compose(doc):
        prompts.setdefault(p["id"].rsplit(".", 1)[0], []).append(p)
    label = {"keyframe": "First frame (new picture, style LoRA)", "nextpose": "First frame (next pose of the master, scene LoRA)",
             "cut": "First frame (cut from the master, scene LoRA)"}
    lines = [f"# {doc['episode']}: shot list with prompts", ""]
    t, scene = 0.0, None
    for s in doc["shots"]:
        if s["scene"] != scene:
            scene = s["scene"]
            lines += ["", f"## {scene}", ""]
        clock = f"{int(t // 60)}:{t % 60:04.1f}"
        f = s["frame"]
        lines.append(f"\n### `{clock}` {s['id']} {f['size']}, {s['seconds']:g} s, {s.get('tier', 'full')}: {s['beat']}")
        if s.get("dialogue"):
            d = s["dialogue"]
            lines.append(f"- **{(doc['cast'].get(d['who'], {}).get('name') or d['who']).upper()}**: \"{d['text']}\"")
        if s.get("narration"):
            lines.append(f"- NARRATOR: {s['narration']}")
        for p in prompts.get(s["id"], []):
            if p["kind"] == "reuse":
                lines.append(f"- Teaser: the clip of {p['of'].split('.')[0]}, seconds {p['trim'][0]:g}-{p['trim'][1]:g} "
                             "(nothing new is drawn)")
            elif p["kind"] == "video":
                extra = " Acting check: lips, peak, face; fallback " + p["fallback"]["kind"] + "." if p.get("qa") else ""
                lines.append(f"- Video ({p['model']}, {p['frames']} frames at {p['fps']} fps):{extra}")
                lines.append(f"  > {p['prompt']}")
            else:
                head = "Last frame (settle, scene LoRA)" if p["id"].endswith(".last") else label[p["kind"]]
                lines.append(f"- {head}:")
                lines.append(f"  > {p['prompt']}")
        t += s["seconds"]
    sheets = sheet_prompts(doc)
    if sheets:
        lines += ["", "## Hero sheets (the creator picks one variant each)", ""]
        lines += [f"- {p['id']}:\n  > {p['prompt']}" for p in sheets]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("check", "compose", "script", "shotlist"):
        print(__doc__)
        return 2
    doc = load(argv[1])
    if argv[0] in ("script", "shotlist"):
        text = script(doc) if argv[0] == "script" else shotlist(doc)
        if "--out" in argv:
            from explainer_engine.core.store import write_text_atomic

            write_text_atomic(Path(argv[argv.index("--out") + 1]), text)
        else:
            print(text)
        return 0
    if argv[0] == "compose":
        errors = schema_errors(doc)
        if errors:
            print("\n".join(errors))
            return 1
        prompts = compose(doc)
        text = json.dumps({"sheets": sheet_prompts(doc), "shots": prompts, "gate": gate_cards(doc)}, ensure_ascii=False,
                          indent=1)
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
