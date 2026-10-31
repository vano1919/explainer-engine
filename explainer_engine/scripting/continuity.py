"""Scene continuity cards (CT-01..CT-16, docs/SHOT_CONTINUITY.md): one card per shot describes the shot's whole state (place,
camera and axis, every person with position, facing, eyeline, costume and props, landmarks, light), the references in
order and what changed since the previous shot. Code checks the cards and assembles the keyframe prompt; nobody writes a
continuity prompt by hand. Research: docs/research/SHOT_CONTINUITY_2026-10-25.md. stdlib + jsonschema.

ვანო (2026-10-25 20:11 / 20:17 Tbilisi): the base models already know how shots join; we train only the style and test
which prompts and references work best, with an agent whose output format is standardised on the research.

    python -m explainer_engine.scripting.continuity check <cards.json>
    python -m explainer_engine.scripting.continuity prompts <cards.json> [--out prompts.json]
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

from explainer_engine.core.errors import ContractError

SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "continuity_card.schema.json"

# CT-05: references per call. "refs" = all pictures, "people" = character references with high fidelity.
MODEL_REFS = {
    "qwen_edit_2511": {"refs": 3, "people": 3, "source": "Qwen-Image-Edit-2509/2511 cards: 1-3 inputs optimal"},
    "qwen_image_21": {"refs": 3, "people": 3, "source": "house: 3 until our test (secondary sources say up to 10, unverified)"},
    "gemini_3_1_flash_image": {"refs": 14, "people": 4, "source": "Gemini API image docs 2026-10-25: 4 characters, 10 objects"},
    "gemini_3_pro_image": {"refs": 14, "people": 5, "source": "Gemini API image docs 2026-10-25: 5 characters, 14 total"},
    "flux2": {"refs": 10, "people": 10, "source": "BFL docs: up to 10 reference images"},
}
SIZES = ["EWS", "WS", "MWS", "MS", "MCU", "CU"]   # one step = a clear size change (CT-07); "insert" is its own kind
MAX_CHAIN = 0          # CT-09: every shot from the references, never on a generated shot (D-78/D-80; Banana100, FreqEdit)
MIN_ANGLE = 30         # CT-07: the 30-degree rule
TRACKED = ("screen_pos", "depth", "facing", "costume", "flags", "props")   # CT-08: a person's state that must hook up


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def schema_findings(doc: dict) -> list[dict]:
    """CT-01: the cards follow continuity_card/1."""
    try:
        import jsonschema
    except ImportError:   # pragma: no cover - the venv has it
        return [{"rule": "CT-01", "level": "FAIL", "shot": "-", "detail": "jsonschema is not installed"}]
    validator = jsonschema.Draft202012Validator(_load_schema())
    return [{"rule": "CT-01", "level": "FAIL", "shot": "/".join(str(p) for p in e.path) or "-", "detail": e.message}
            for e in sorted(validator.iter_errors(doc), key=lambda e: list(map(str, e.path)))]


def scene_state(doc: dict, shot: dict) -> dict:
    """The place, time and light a shot inherits from the scene unless it sets its own."""
    loc, light = doc["location"], doc["light"]
    return {"time_of_day": shot.get("time_of_day", loc["time_of_day"]), "weather": shot.get("weather", loc["weather"]),
            "key_light_dir": shot.get("key_light_dir", light["key_light_dir"])}


def _person_state(person: dict) -> dict:
    return {"screen_pos": person["screen_pos"], "depth": person["depth"], "facing": person["facing"],
            "costume": person.get("costume", ""), "flags": sorted(person.get("flags", [])),
            "props": sorted((p["id"], p["hand"], p.get("state", "")) for p in person.get("props", []))}


def differences(prev: dict, shot: dict, doc: dict) -> set[tuple[str, str]]:
    """(entity, field) pairs whose state differs between two consecutive shots (CT-08)."""
    diff: set[tuple[str, str]] = set()
    a, b = scene_state(doc, prev), scene_state(doc, shot)
    for field in a:
        if a[field] != b[field]:
            diff.add(("scene", field))
    for key in set(prev.get("set_state", {})) | set(shot.get("set_state", {})):
        if key in prev.get("set_state", {}) and key in shot.get("set_state", {}) \
                and prev["set_state"][key] != shot["set_state"][key]:
            diff.add((key, "state"))
    before = {p["id"]: _person_state(p) for p in prev["characters"]}
    same_side = prev["camera_side"] == shot["camera_side"]
    for person in shot["characters"]:
        old = before.get(person["id"])
        if old is None:
            continue
        new = _person_state(person)
        for field in TRACKED:
            # positions and facing are compared only on the same side of the axis and size class: a new camera changes them
            if field in ("screen_pos", "depth", "facing") and (not same_side or prev["shot_size"] != shot["shot_size"]):
                continue
            if old[field] != new[field]:
                diff.add((person["id"], field))
    return diff


def _size_step(a: str, b: str) -> int:
    if "insert" in (a, b):
        return 99
    return abs(SIZES.index(a) - SIZES.index(b))


def check(doc: dict) -> list[dict]:
    """All CC findings for one scene: FAIL blocks generation, REVIEW goes to the agent's second look."""
    found = schema_findings(doc)
    if found:
        return found

    def add(rule: str, level: str, shot: str, detail: str) -> None:
        found.append({"rule": rule, "level": level, "shot": shot, "detail": detail})

    cast, loc = doc["cast"], doc["location"]
    limits = MODEL_REFS.get(doc["model"])
    if limits is None:
        add("CT-05", "FAIL", "-", f"unknown model {doc['model']!r}; known: {', '.join(MODEL_REFS)}")
        limits = {"refs": 3, "people": 3}
    landmark_ids = {l["id"] for l in loc.get("landmarks", [])}
    shots = doc["shots"]
    ids = [s["shot_id"] for s in shots]
    if len(set(ids)) != len(ids):
        add("CT-01", "FAIL", "-", "shot_id repeats")
    masters = [s for s in shots if s.get("is_master")]
    if len(masters) > 1:
        add("CT-03", "FAIL", "-", "more than one master shot")
    prev = None
    for shot in shots:
        sid = shot["shot_id"]
        people = shot["characters"]
        on_screen = [p["id"] for p in people]
        # CT-02 identity: every person is in the cast; the costume is one of the cast's variants
        for p in people:
            if p["id"] not in cast:
                add("CT-02", "FAIL", sid, f"{p['id']} is not in the cast registry")
            elif p.get("costume") and p["costume"] not in cast[p["id"]].get("costumes", {}):
                add("CT-02", "FAIL", sid, f"{p['id']}: costume {p['costume']!r} is not a registered variant")
        if len(set(on_screen)) != len(on_screen):
            add("CT-02", "FAIL", sid, "a person is listed twice")
        # CT-03 the place: refs[0] is the master frame unless this shot is the master itself
        refs = shot["refs"]
        if not shot.get("is_master"):
            if not refs or refs[0]["role"] != "place" or refs[0]["path"] != loc["master_frame"]:
                add("CT-03", "FAIL", sid, "image 1 must be the scene's master frame (role 'place')")
        # CT-04 head count
        expected = len(people) + shot.get("extras", 0)
        if shot["head_count"] != expected:
            add("CT-04", "FAIL", sid, f"head_count {shot['head_count']} != {len(people)} named + {shot.get('extras', 0)} extras")
        # CT-05 references: cap, roles, every person's sheet
        if len(refs) > limits["refs"]:
            add("CT-05", "FAIL", sid, f"{len(refs)} references > {limits['refs']} for {doc['model']}")
        char_refs = [r for r in refs if r["role"] == "character"]
        if len(char_refs) > limits["people"]:
            add("CT-05", "FAIL", sid, f"{len(char_refs)} character references > {limits['people']}")
        for r in char_refs:
            if r.get("of") not in cast:
                add("CT-05", "FAIL", sid, f"character reference {r['path']} names no cast id")
            elif r["path"] != cast[r["of"]]["sheet"]:
                add("CT-05", "FAIL", sid, f"{r['of']}: reference is not the registered model sheet")
        missing = [pid for pid in on_screen if pid not in {r.get("of") for r in char_refs}]
        if missing:
            level = "REVIEW" if len(refs) >= limits["refs"] else "FAIL"
            add("CT-05", level, sid, f"no model sheet among the references for: {', '.join(missing)}")
        # CT-06 the axis
        if len(people) >= 2:
            axis = shot.get("axis")
            if not axis:
                add("CT-06", "FAIL", sid, "two or more people on screen and no axis")
            elif any(a not in cast for a in axis):
                add("CT-06", "FAIL", sid, f"axis {axis} names someone outside the cast")
        for p in people:
            eye = p.get("eyeline")
            if eye and eye not in cast and eye not in ("off_left", "off_right", "down", "up"):
                add("CT-11", "FAIL", sid, f"{p['id']} looks at unknown {eye!r}")
            if eye and eye in cast and eye in on_screen:
                target = next(t for t in people if t["id"] == eye)
                order = ["left", "centre", "right"]
                towards = "right" if order.index(target["screen_pos"]) > order.index(p["screen_pos"]) else "left"
                if target["screen_pos"] != p["screen_pos"] and p["facing"] not in (towards, "camera"):
                    add("CT-11", "REVIEW", sid, f"{p['id']} looks at {eye} but faces {p['facing']}, away from them")
        # CT-10 landmarks belong to the location
        for lm in shot.get("landmarks", []):
            if lm["id"] not in landmark_ids:
                add("CT-10", "FAIL", sid, f"landmark {lm['id']!r} is not in the location's list")
        # CT-09 drift: fresh from the originals, at most MAX_CHAIN edits deep
        depth = shot.get("chain_depth", 0)
        if depth > MAX_CHAIN:
            add("CT-09", "FAIL", sid, f"chain depth {depth} > {MAX_CHAIN}: draw it again from the original references")
        src = shot.get("derive_from", "original")
        if src != "original" and src not in ids[:ids.index(sid)]:
            add("CT-09", "FAIL", sid, f"derive_from {src!r} is not an earlier shot")
        elif src != "original" and MAX_CHAIN == 0:
            add("CT-09", "FAIL", sid, f"derive_from {src!r}: no edit pass on an earlier shot (D-78/D-80); draw it from the references")
        if any(r["role"] == "previous_shot" for r in refs) and refs[-1]["role"] != "previous_shot":
            add("CT-05", "FAIL", sid, "the previous shot, when used, is the last reference")
        if prev is None:
            if shot.get("hook_up") not in (None, "first"):
                add("CT-07", "REVIEW", sid, "the first shot of a scene has hook_up 'first'")
        else:
            psid = prev["shot_id"]
            same_people = set(on_screen) == {p["id"] for p in prev["characters"]} and on_screen
            # CT-06 camera side carries over unless a reason crosses it
            if shot["camera_side"] != prev["camera_side"] and not shot.get("axis_cross_reason"):
                add("CT-06", "REVIEW", sid, f"camera crosses the axis after {psid} with no reason "
                                            "(neutral shot, cutaway, insert or an on-screen move)")
            # CT-07 the 30-degree rule
            if same_people and _size_step(prev["shot_size"], shot["shot_size"]) < 1 \
                    and shot.get("angle_change_deg", 0) < MIN_ANGLE and shot.get("hook_up") != "time_cut":
                add("CT-07", "FAIL", sid, f"same people as {psid}, same size {shot['shot_size']} and under "
                                          f"{MIN_ANGLE} degrees: a jump cut")
            # CT-12 screen direction on a match on action
            if shot.get("hook_up") == "match_on_action":
                before = {p["id"]: p for p in prev["characters"]}
                for p in people:
                    if p["id"] in before and p["facing"] in ("left", "right") \
                            and before[p["id"]]["facing"] in ("left", "right") and p["facing"] != before[p["id"]]["facing"] \
                            and shot["camera_side"] == prev["camera_side"]:
                        add("CT-12", "FAIL", sid, f"{p['id']} moves {before[p['id']]['facing']} in {psid}, "
                                                  f"{p['facing']} here: the screen direction flips")
            # CT-08 every difference is a listed change with a cause
            diff = differences(prev, shot, doc)
            listed = {(c["entity"], c["field"]) for c in shot.get("changes", [])}
            for entity, field in sorted(diff - listed):
                add("CT-08", "FAIL", sid, f"{entity}.{field} changed since {psid} and is not in 'changes'")
            for entity, field in sorted(listed - diff):
                add("CT-08", "REVIEW", sid, f"'changes' lists {entity}.{field} but the state did not change")
        prev = shot
    return found


def axis_cross(axis: dict, pos: list) -> float:
    """Signed distance (m) of a camera at ``pos`` [x, y, z] from the axis line of a ``scene_set/1``: the line runs through
    ``origin`` [x, z] at ``deg`` in the floor plane (x right, z forward, y up). Positive = side A, negative = side B."""
    ox, oz = axis["origin"]
    rad = math.radians(axis["deg"])
    return math.cos(rad) * (pos[2] - oz) - math.sin(rad) * (pos[0] - ox)


def derive_card_v2(card_v1: dict, scene_set: "dict | Path | str", scene_set_ref: dict | None = None) -> dict:
    """``continuity_card/2`` (P6, CN-02): the scene's cards with every ``camera_side`` computed from the ``scene_set/1`` camera of
    the same ``shot_id`` (which side of the axis it stands on), the set's landmark objects added to the location's landmarks, and
    ``derived_from.scene_set`` naming the set. A shot with no camera in the set keeps its side. A camera exactly on the axis has no
    side: refused. Nothing else of the cards changes; ``check`` then reports an unexplained crossing (CT-06) as it does for any card."""
    if card_v1.get("schema") not in ("continuity_card/1", "continuity_card/2"):
        raise ContractError("derive_card_v2 reads a continuity_card/1 (or /2) document")
    set_path = None
    if not isinstance(scene_set, dict):
        set_path = Path(scene_set)
        scene_set = json.loads(set_path.read_text(encoding="utf-8"))
    doc = copy.deepcopy(card_v1)
    doc["schema"] = "continuity_card/2"
    if scene_set_ref is None and set_path is not None:
        from explainer_engine.core import contracts
        scene_set_ref = {"path": f"sets/{set_path.name}", "sha256": contracts.sha256_file(set_path)}
    if scene_set_ref is None:
        raw = json.dumps(scene_set, indent=2, ensure_ascii=False).encode("utf-8")
        scene_set_ref = {"path": f"sets/{scene_set['set_id']}.json", "sha256": hashlib.sha256(raw).hexdigest()}
    doc["derived_from"] = {"scene_set": dict(scene_set_ref)}
    cameras = {c["shot_id"]: c for c in scene_set["cameras"]}
    for shot in doc["shots"]:
        cam = cameras.get(shot["shot_id"])
        if cam is None:
            continue
        cross = round(axis_cross(scene_set["axis"], cam["pos"]), 6)
        if cross == 0:
            raise ContractError(f"{shot['shot_id']}: the camera of {scene_set['set_id']} stands on the axis, so it has no side (CT-06)")
        shot["camera_side"] = "A" if cross > 0 else "B"
        shot["camera"] = {"pos": list(cam["pos"]), "yaw_deg": cam["yaw_deg"], "pitch_deg": cam["pitch_deg"],
                          "fov_deg": cam["fov_deg"], "axis_cross": cross}
    have = {lm["id"] for lm in doc["location"].get("landmarks", [])}
    for obj in scene_set["objects"]:
        if obj["landmark"] and obj["id"] not in have:
            doc["location"].setdefault("landmarks", []).append({"id": obj["id"], "text": obj["kind"]})
    return doc


def _refs_text(doc: dict, shot: dict) -> list[str]:
    lines = []
    for k, ref in enumerate(shot["refs"], 1):
        if ref["role"] == "place":
            lines.append(f"Image {k} is the place, {doc['location']['where_when']}: keep its landmarks, light and colours, "
                         f"but show it from a new camera position.")
        elif ref["role"] == "character":
            lines.append(f"Image {k} is {doc['cast'][ref['of']]['name']}: copy the face, body and costume only, not the pose.")
        elif ref["role"] == "previous_shot":
            lines.append(f"Image {k} is the previous shot: keep everything the same except the changes below.")
        else:
            lines.append(f"Image {k} shows the art style only.")
    return lines


def compose_prompt(doc: dict, shot: dict) -> str:
    """CT-13: the keyframe prompt, assembled from the card in a fixed order (research section 4 H)."""
    cast, state = doc["cast"], scene_state(doc, shot)
    size = {"EWS": "extreme wide shot", "WS": "wide shot", "MWS": "medium wide shot", "MS": "medium shot",
            "MCU": "medium close-up", "CU": "close-up", "insert": "insert close-up"}[shot["shot_size"]]
    parts = [doc["style_line"].strip()]
    parts += _refs_text(doc, shot)
    parts.append(f"{size.capitalize()}, {shot['angle']}-level camera." if shot["angle"] == "eye"
                 else f"{size.capitalize()}, {shot['angle']} angle.")
    n = shot["head_count"]
    parts.append("No people." if n == 0 else f"Exactly {n} {'person' if n == 1 else 'people'}.")
    for p in shot["characters"]:
        who = cast[p["id"]]
        text = f"{who['name'][0].upper()}{who['name'][1:]}, {who['description'].rstrip('.')}"
        if p.get("costume"):
            text += f", wearing {who['costumes'][p['costume']]}"
        if p.get("flags"):
            text += ", " + " and ".join(p["flags"])
        place = "in the centre" if p["screen_pos"] == "centre" else f"on the {p['screen_pos']}"
        text += f", {place}, " + {"front": "in the foreground", "mid": "in the middle distance", "back": "in the background"}[p["depth"]]
        text += {"left": ", facing left", "right": ", facing right", "camera": ", facing the viewer",
                 "away": ", seen from behind"}[p["facing"]]
        eye = p.get("eyeline")
        if eye in cast:
            text += f", looking at {cast[eye]['name']}"
        elif eye:
            text += {"off_left": ", looking off to the left", "off_right": ", looking off to the right",
                     "down": ", looking down", "up": ", looking up"}[eye]
        for prop in p.get("props", []):
            hand = "both hands" if prop["hand"] == "both" else f"the {prop['hand']} hand"
            text += f", holding {prop['id'].replace('_', ' ')}" + (f" ({prop['state']})" if prop.get("state") else "") \
                + f" in {hand}"
        if p.get("expression"):
            text += f", {p['expression']}"
        if p.get("action"):
            text += f", {p['action']}"
        parts.append(text + ".")
    if shot.get("extras"):
        parts.append(f"{shot['extras']} unnamed background figure{'s' if shot['extras'] > 1 else ''}.")
    marks = {l["id"]: l["text"] for l in doc["location"].get("landmarks", [])}
    if shot.get("landmarks"):
        parts.append("Visible: " + "; ".join(f"{marks[l['id']]} " + ("in the centre" if l["side"] == "centre" else f"on the {l['side']}")
                                       for l in shot["landmarks"]) + ".")
    for key, value in shot.get("set_state", {}).items():
        parts.append(f"The {key.replace('_', ' ')} is {value}.")
    weather = "" if state["weather"] in ("clear", "indoor") else f", {state['weather']}"
    parts.append(f"{state['time_of_day'].capitalize()}{weather}; key light from the {state['key_light_dir']} "
                 f"({doc['light']['light_source']}).")
    if shot.get("changes"):
        parts.append("Change from the previous shot: " + "; ".join(
            f"{c['entity']} {c['field']} now {c['to']} ({c['cause']})" for c in shot["changes"]) + ".")
        parts.append("Keep everything else the same.")
    return " ".join(parts)


def vision_questions(doc: dict, shot: dict) -> list[str]:
    """CT-14: the yes/no and count questions asked about the finished keyframe (the blind check's second look)."""
    cast, state = doc["cast"], scene_state(doc, shot)
    qs = [f"How many people are in the picture? (expected {shot['head_count']})"]
    for p in shot["characters"]:
        name = cast[p["id"]]["name"]
        qs.append(f"Is {name} " + ("in the centre" if p["screen_pos"] == "centre" else f"on the {p['screen_pos']}")
                  + " of the frame?")
        if p["facing"] in ("left", "right"):
            qs.append(f"Does {name} face {p['facing']}?")
        for prop in p.get("props", []):
            qs.append(f"Does {name} hold {prop['id'].replace('_', ' ')} in the {prop['hand']} hand?")
        qs.append(f"Does {name} match the model sheet (face, colours, costume)?")
    marks = {l["id"]: l["text"] for l in doc["location"].get("landmarks", [])}
    for lm in shot.get("landmarks", []):
        qs.append(f"Is {marks[lm['id']]} visible " + ("in the centre" if lm["side"] == "centre" else f"on the {lm['side']}") + "?")
    qs.append(f"Does the main light come from the {state['key_light_dir']}?")
    if not shot.get("is_master"):
        qs.append("Is the framing clearly different from the previous shot (new size or angle)?")
    return qs


def prompts(doc: dict) -> list[dict]:
    """One generation job per shot: prompt, references in order, the questions for the check."""
    return [{"shot_id": s["shot_id"], "prompt": compose_prompt(doc, s), "refs": [r["path"] for r in s["refs"]],
             "questions": vision_questions(doc, s)} for s in doc["shots"]]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ("check", "prompts"):
        print(__doc__)
        return 2
    doc = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    found = check(doc)
    for f in found:
        print(f"{f['level']:6} {f['rule']} {f['shot']}: {f['detail']}")
    fails = [f for f in found if f["level"] == "FAIL"]
    print(f"{len(fails)} FAIL, {len(found) - len(fails)} REVIEW")
    if argv[0] == "prompts":
        if fails:
            print("no prompts: fix the FAILs first")
            return 1
        out = json.dumps(prompts(doc), indent=2, ensure_ascii=False)
        if "--out" in argv:
            from explainer_engine.core.store import write_text_atomic
            write_text_atomic(Path(argv[argv.index("--out") + 1]), out + "\n")
        else:
            print(out)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
