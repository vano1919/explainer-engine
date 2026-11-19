"""Continuity cards (continuity_card/1, docs/SHOT_CONTINUITY.md CT-01..CT-14) for ep_truce_1914, stage S3 of the demo run.

Data builder, not repo code (freeze law 1): it lives in the demo folder as evidence, like build_truce.py. It starts from the
repo's own first draft (`scripting/continuity.cards_from_v4`, read, never changed) and lays the S3 thread's layout decisions on
top: the place and light of every scene, each hero's costume variant (the button and cap continuity of the script's
costume_continuity_notes), props in hands, depth, facing, the crowd count, landmarks, and the cause of every change.
Then it runs `continuity.check` on every scene and writes one file per scene plus a report.

Usage: python build_continuity_cards.py <repo root> <out dir>
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(ROOT))

from explainer_engine.scripting import continuity as C   # noqa: E402
from explainer_engine.videolane import plan as VP          # noqa: E402

EP = ROOT / "episodes" / "ep_truce_1914"
SCRIPT = json.loads((EP / "story" / "production_script.json").read_text(encoding="utf-8"))
SHOTS = {s["shot_id"]: s for s in SCRIPT["shots"]}
NAME = {"char_thomas_hale": "Thomas", "char_friedrich_brandt": "Friedrich", "char_sgt_harris": "Harris"}

# ---- the cast: tags (never a story name, KP), verbatim registry text, the R1 portrait as the sheet, costume variants -----
TAG = {"char_thomas_hale": "the young British private", "char_friedrich_brandt": "the Saxon corporal",
       "char_sgt_harris": "the British sergeant"}
COSTUMES = {
    "char_thomas_hale": {
        "service": "khaki soft cap, long khaki greatcoat open over the tunic, every brass tunic button in place",
        "button_cut": "khaki soft cap, long khaki greatcoat open over the tunic, the top right brass tunic button cut off"},
    "char_friedrich_brandt": {
        "field": "field-grey round cap with red band, grey greatcoat buttoned, the portrait card in the left breast pocket",
        "button_given": "field-grey round cap with red band, grey greatcoat buttoned with one button missing, the portrait "
                        "card in the left breast pocket"},
    "char_sgt_harris": {
        "cap_on": "khaki soft cap, goatskin jerkin over the khaki tunic, three chevrons",
        "cap_off": "bareheaded, the khaki soft cap in his hand, goatskin jerkin over the khaki tunic, three chevrons"},
}


def costume(cid: str, sid: str) -> str:
    seg, n = sid.split("_SH")[0], int(sid.split("_SH")[1])
    order = (int(seg[1:]), n)
    if cid == "char_thomas_hale":
        return "button_cut" if order >= (6, 10) else "service"     # S06_SH009 is the cut itself (insert of the button)
    if cid == "char_friedrich_brandt":
        return "button_given" if order >= (6, 12) else "field"   # S06_SH011's start frame shows the button being twisted off
    if cid == "char_sgt_harris":
        return "cap_on"   # S05_SH021's start frame shows the cap coming off (its prompt); he is not seen bareheaded after
    return "default"


# ---- places: where/when, landmarks (from the registry's fixed_environment_prompt) -----------------------------------------
LANDMARKS = {
    "loc_british_trench": [("sandbag_breastwork", "waist-high sandbag breastworks with frost"),
                           ("duckboards", "duckboards over brown floodwater"),
                           ("fire_step", "the fire step"), ("brazier", "a small coke brazier"),
                           ("trench_ladder", "a trench ladder")],
    "loc_german_trench": [("fir_trees", "small fir trees set on the parapet"),
                          ("dugout_entrance", "a dugout entrance with a hanging oil lamp"),
                          ("timber_walls", "timber-revetted earth walls"), ("sandbag_parapet", "a parapet of sandbags")],
    "loc_no_mans_land": [("wire", "rows of barbed wire on wooden stakes"), ("shell_holes", "shell holes skinned with ice"),
                         ("ruined_farm", "a ruined brick farm in the distance"), ("willows", "pollarded willows"),
                         ("ammo_box", "an ammunition box"), ("graves", "fresh graves with small wooden crosses")],
}
KEYWORDS = {"sandbag_breastwork": ["sandbag"], "duckboards": ["duckboard", "floodwater"], "fire_step": ["fire step"],
            "brazier": ["brazier"], "trench_ladder": ["ladder"], "fir_trees": ["fir tree", "candle tree", "fir trees"],
            "dugout_entrance": ["dugout"], "timber_walls": ["timber"], "sandbag_parapet": ["parapet"],
            "wire": ["wire"], "shell_holes": ["shell hole"], "ruined_farm": ["farm"], "willows": ["willow"],
            "ammo_box": ["ammunition box", " box"], "graves": ["grave"]}


def time_of(light: str) -> str:
    t = light.lower()
    if "night" in t or "moon" in t or "candlelight" in t:
        return "night"
    if "sunset" in t or "dusk" in t or "late-afternoon" in t or "last light" in t:
        return "dusk"
    if "sunrise" in t or "dawn" in t or "morning" in t:
        return "dawn"
    return "day"


def weather_of(light: str) -> str:
    t = light.lower()
    return "snow" if "snow" in t else "fog" if "fog" in t else "clear"


def key_dir(light: str, loc: str) -> str:
    """The sun rises behind the German line (screen right on side A) and sets behind the British (screen left)."""
    t = light.lower()
    if "brazier" in t or "oil-lamp" in t or "candlelight" in t or "candle glow" in t:
        return "front"
    if "night" in t or "moon" in t:
        return "right" if loc == "loc_british_trench" else "top"   # the faint candle line across the field
    if time_of(light) == "dusk":
        return "left"
    if time_of(light) == "dawn":
        return "right"
    return "top"


def source_of(light: str) -> str:
    t = light.lower()
    if "brazier" in t:
        return "the coke brazier"
    if "oil-lamp" in t:
        return "an oil lamp"
    if "candle" in t:
        return "the candles on the parapet"
    if "moon" in t:
        return "the moon"
    return "the low winter sun"


# ---- per-shot layout the script states in words (start state, direction notes) ---------------------------------------------
# props: shot -> {cast id: [(prop id, hand, state)]}; a prop that is not in a hand goes into set_state instead.
PROPS = {
    "S01_SH002": {}, "S04_SH005": {"char_thomas_hale": [("prop_smle_rifle", "right", "held upright")]},
    "S02_SH006": {"char_thomas_hale": [("prop_mothers_letter", "both", "open")]},
    "S03_SH001": {"char_friedrich_brandt": [("prop_candle_tree", "both", "candles lit")]},
    "S05_SH009": {"char_friedrich_brandt": [("prop_family_photo", "right", "out of the pocket")]},
    "S05_SH011": {"char_thomas_hale": [("prop_family_photo", "both", "held, looked at")]},
    "S05_SH012": {"char_friedrich_brandt": [("prop_family_photo", "right", "going back into the pocket")]},
    "S05_SH015": {"char_thomas_hale": [("prop_spade", "both", "digging")],
                  "char_friedrich_brandt": [("prop_spade", "both", "digging")]},
    "S06_SH009": {"char_thomas_hale": [("prop_brass_button", "right", "on the tunic, being cut")]},
    "S06_SH010": {"char_thomas_hale": [("prop_brass_button", "right", "cut off, on the open palm")]},
    "S06_SH011": {"char_friedrich_brandt": [("prop_brass_button", "left", "received"),
                                            ("prop_grey_button", "right", "being twisted off his greatcoat")]},
    "S07_SH007": {"char_thomas_hale": [("prop_smle_rifle", "both", "held")]},
}
SET_STATE = {
    "S01_SH002": {"rifle": "leaning against the sandbags"}, "S07_SH008": {"rifle": "leaning on the sandbags"},
    "S03_SH003": {"candle_tree": "on the parapet, candles lit"}, "S03_SH009": {"candle_tree": "on the parapet, candles lit"},
    "S02_SH007": {"rifle": "across Harris's knees, being cleaned"},
    "S05_SH018": {"cap": "Friedrich's cap in his hand"},
    "S05_SH021": {"cap": "coming off Harris's head in his right hand"},
    "S02_SH005": {"hands": "Thomas's cold hands in khaki greatcoat sleeves holding the letter open"},
    "S03_SH002": {"hands": "Friedrich's gloved hand in a field-grey sleeve holding the portrait card"},
    "S04_SH011": {"hands": "two pairs of empty hands: khaki sleeves on the left, field-grey sleeves on the right"},
    "S05_SH010": {"hands": "the portrait card between khaki sleeves on the left and field-grey sleeves on the right"},
    "S05_SH016": {"spades": "a British and a German spade side by side in a heap of frozen earth"},
    "S06_SH012": {"figures": "Thomas (left) and Friedrich (right) as silhouettes on the box against the last light"},
}
# crowd: unnamed people the script shows; a layout count (the script says "soldiers", "groups"), not a story fact
EXTRAS = {"S03_SH003": 5, "S03_SH009": 5, "S01_SH004": 20, "S02_SH004": 6, "S02_SH009": 4, "S04_SH015": 16,
          "S05_SH003": 14, "S05_SH006": 2, "S05_SH014": 4, "S05_SH020": 14, "S07_SH001": 12, "S07_SH005": 1,
          "S06_SH012": 2}
_SIDES = re.compile(r"\b(Thomas|Friedrich|Harris)\b (left|right)\b", re.I)

# facing words of the direction notes: "<Name> faces (screen) left|right", "both/they face screen right", "away from camera"
_FACE = re.compile(r"\b(Thomas|Friedrich|Harris)\b[^.;,]{0,40}?\b(?:faces|looks|climbs|walks|stands)\b[^.;,]{0,25}?"
                   r"\b(left|right|away from camera)\b", re.I)


def facings(sh: dict, people: list[dict]) -> dict:
    notes = str((sh.get("screen_composition") or {}).get("screen_direction_notes") or "")
    start = str(sh.get("action_start_state") or "")
    out = {}
    for name, d in _FACE.findall(notes):
        cid = next(c for c, n in NAME.items() if n.lower() == name.lower())
        out[cid] = "away" if "away" in d.lower() else d.lower()
    m = re.search(r"\b(both|they|the group) faces? screen (left|right)", notes, re.I)
    if m:
        for p in people:
            out.setdefault(p["id"], m.group(2).lower())
    if "away from camera" in notes.lower() and len(people) == 1:
        out.setdefault(people[0]["id"], "away")
    # a two-hander that names only the sides ("Thomas left, Friedrich right"): they face each other
    for p in people:
        if p["id"] not in out and len(people) == 2:
            out[p["id"]] = "right" if p["screen_pos"] == "left" else "left" if p["screen_pos"] == "right" else "camera"
    del start
    return out


def build_scene(scene: list[dict]) -> dict | None:
    doc = C.cards_from_v4(SCRIPT, scene)
    if doc is None:
        return None
    first = SHOTS[doc["shots"][0]["shot_id"]]
    loc = first["location_id"]
    light0 = first.get("lighting_and_time") or ""
    locd = next(l for l in SCRIPT["world_bible"]["locations"] if l["location_id"] == loc)
    when = {"dawn": "Christmas morning", "day": "Christmas Day", "dusk": "Christmas dusk", "night": "Christmas Eve night"}
    seg = first["segment_id"]
    date = {"S01": "Christmas morning 1914", "S02": "Christmas Eve 1914, afternoon to dusk", "S03": "Christmas Eve 1914, night",
            "S04": "Christmas morning 1914, dawn", "S05": "Christmas Day 1914", "S06": "Christmas Day 1914, sunset",
            "S07": "Boxing Day 1914, morning"}.get(seg, when[time_of(light0)])
    doc["style_line"] = SCRIPT["world_bible"]["style_anchor_token"]
    doc["location"].update({"where_when": f"{locd['name'].replace('/', '-')} / {date}", "int_ext": "EXT",
                            "time_of_day": time_of(light0), "weather": weather_of(light0),
                            "landmarks": [{"id": i, "text": t} for i, t in LANDMARKS[loc]]})
    doc["light"] = {"key_light_dir": key_dir(light0, loc), "light_source": source_of(light0),
                    "colour_key": locd.get("lighting_palette", "")}
    for cid, c in doc["cast"].items():
        c["name"] = TAG[cid]
        c["sheet"] = f"planning/gemini_task/refs/ref_{cid}_portrait.jpg"
        c["costumes"] = COSTUMES[cid]
    sheets = {cid: c["sheet"] for cid, c in doc["cast"].items()}
    prev = None
    for card in doc["shots"]:
        sid = card["shot_id"]
        sh = SHOTS[sid]
        light = sh.get("lighting_and_time") or light0
        for k, v in (("time_of_day", time_of(light)), ("weather", weather_of(light)), ("key_light_dir", key_dir(light, loc))):
            scene_v = doc["location"][k] if k != "key_light_dir" else doc["light"]["key_light_dir"]
            if v != scene_v:
                card[k] = v
        role = sh.get("shot_role") or ""
        notes = str((sh.get("screen_composition") or {}).get("screen_direction_notes") or "")
        sides = {next(c for c, n in NAME.items() if n.lower() == nm.lower()): d.lower() for nm, d in _SIDES.findall(notes)}
        if len(card["characters"]) == 2 and all(p["screen_pos"] == "centre" for p in card["characters"]):
            for p in card["characters"]:
                p["screen_pos"] = sides.get(p["id"], p["screen_pos"])
                p.pop("facing", None)
                p["facing"] = "camera"
        face = facings(sh, card["characters"])
        start = str(sh.get("action_start_state") or "")
        for p in card["characters"]:
            p["costume"] = costume(p["id"], sid)
            p["facing"] = face.get(p["id"], p["facing"])
            named = NAME[p["id"]] in start.split(" ")[0] or start.startswith(NAME[p["id"]])
            p["depth"] = "front" if (role.startswith("dialogue") and len(card["characters"]) == 2 and not named
                                     and card["shot_size"] in ("MS", "MCU")) else "mid"
            if named or len(card["characters"]) == 1:
                p["action"] = start[:160]
            ps = PROPS.get(sid, {}).get(p["id"])
            if ps:
                p["props"] = [{"id": i, "hand": h, "state": s} for i, h, s in ps]
            if p["facing"] == "away":
                p.pop("eyeline", None)
            elif "eyeline" in p and p["facing"] in ("left", "right"):
                other = next(o for o in card["characters"] if o["id"] == p["eyeline"])
                toward = "right" if {"left": 0, "centre": 1, "right": 2}[other["screen_pos"]] > \
                                    {"left": 0, "centre": 1, "right": 2}[p["screen_pos"]] else "left"
                if toward != p["facing"]:   # both face the enemy line, not each other
                    p["eyeline"] = f"off_{p['facing']}"
        if len(card["characters"]) == 1 and "eyeline" not in card["characters"][0]:
            f = card["characters"][0]["facing"]
            if f in ("left", "right"):
                card["characters"][0]["eyeline"] = f"off_{f}"
        if sid in SET_STATE:
            card["set_state"] = SET_STATE[sid]
        if sid in EXTRAS:
            card["extras"] = EXTRAS[sid]
        card["head_count"] = len(card["characters"]) + card.get("extras", 0)
        text = " ".join(str(v) for v in (sh.get("screen_composition") or {}).values()) + " " + start
        lms = [i for i, _ in LANDMARKS[loc] if any(k in text.lower() for k in KEYWORDS[i])]
        if lms:
            card["landmarks"] = [{"id": i, "side": "centre"} for i in lms[:3]]
        card["refs"] = ([] if card.get("is_master") else [{"path": doc["location"]["master_frame"], "role": "place"}]) + \
            [{"path": sheets[p["id"]], "role": "character", "of": p["id"]} for p in card["characters"]]
        card["derive_from"] = "original"
        card["chain_depth"] = 0
        if prev is not None:
            ep = sh.get("edit_plan") or {}
            reason = ep.get("cut_in_reason")
            card["hook_up"] = {"insert": "insert", "reaction": "reaction", "time_cut": "time_cut", "action": "match_on_action",
                               "line": "eyeline" if len(card["characters"]) else "cutaway"}.get(reason, "cutaway")
            if card["camera_side"] != prev["camera_side"]:
                card["axis_cross_reason"] = "insert" if card["shot_size"] in ("MCU", "CU") and not card["characters"] \
                    else "cutaway"
            card["changes"] = [change(e, f, prev, card, sh, SHOTS[prev["shot_id"]])
                               for e, f in sorted(C.differences(prev, card, doc))]
            if not card["changes"]:
                card.pop("changes")
        prev = card
    return doc


def _state(card: dict, entity: str, field: str):
    if entity == "scene":
        return card.get(field)
    if field == "state":
        return (card.get("set_state") or {}).get(entity)
    p = next((x for x in card["characters"] if x["id"] == entity), {})
    v = p.get(field)
    return [f"{x['id']} ({x['hand']}, {x.get('state', '')})" for x in v] if field == "props" and v else v


CAUSES = {
    ("char_thomas_hale", "costume", "S06_SH010"): "he cut the top brass button off his tunic in S06_SH009",
    ("char_friedrich_brandt", "costume", "S06_SH011"): "he cuts a button off his greatcoat to give it to Thomas",
}


def change(entity: str, field: str, prev: dict, card: dict, sh: dict, psh: dict) -> dict:
    if entity == "scene":
        why = f"the light of this shot: {sh.get('lighting_and_time')}"
    elif field in ("props", "costume", "state"):
        why = f"end of {psh['shot_id']}: {psh.get('action_end_state')}; this shot starts: {sh.get('action_start_state')}"
    else:
        why = f"a new set-up ({card['shot_size']}, {card.get('hook_up')}): {sh.get('action_start_state')}"
    cause = CAUSES.get((entity, field, card["shot_id"])) or why[:200]
    return {"entity": entity, "field": field, "from": _state(prev, entity, field), "to": _state(card, entity, field),
            "cause": cause}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report, total_f, total_r = [], 0, 0
    for scene in VP.scenes(SCRIPT):
        if not any(VP.is_video(s) for s in scene):
            continue
        doc = build_scene(scene)
        if doc is None:
            continue
        name = doc["shots"][0]["shot_id"]
        (OUT / f"{name}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        found = C.check(doc)
        fails = [f for f in found if f["level"] == "FAIL"]
        total_f += len(fails)
        total_r += len(found) - len(fails)
        report.append({"scene": doc["scene_id"], "file": f"{name}.json", "shots": [s["shot_id"] for s in doc["shots"]],
                       "findings": found})
        if not fails:
            (OUT / f"{name}.prompts.json").write_text(json.dumps(C.prompts(doc), indent=1, ensure_ascii=False) + "\n",
                                                     encoding="utf-8")
    (OUT / "report.json").write_text(json.dumps({"fail": total_f, "review": total_r, "scenes": report}, indent=1) + "\n",
                                     encoding="utf-8")
    print(f"{len(report)} scene(s), {sum(len(r['shots']) for r in report)} card(s): {total_f} FAIL, {total_r} REVIEW")
    for r in report:
        for f in r["findings"]:
            print(f"  {f['level']:6} {f['rule']} {f['shot']}: {f['detail'][:140]}")
    return 1 if total_f else 0


if __name__ == "__main__":
    raise SystemExit(main())
