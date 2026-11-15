"""The director's own choice of a photo shot's living effects, weather and camera (the owner, 2026-11-14 12:40 UTC, message
cmsg_01Hnu5zB86sjUj5GtTgaUkPWYVRnJpwAAtZdA2Y88V1xkZ: "it has the text, the photo and the list of tools and effects; it must
decide the best variant of the living frame itself from the logic of the text and the photo"; the weather, 12:38 UTC,
cmsg_01Hnu5zB86sjUj5GtTgaUkPWWWojGKCioK4XxEJiUguz9X: where snow is right for the story, the director decides).

The director's eye writes only what it SEES (``seen``: objects with points, lights, and the ``living`` facts: ``id``,
``kind``, ``where``, ``box``, ``area_pct``, ``names``, ``on_body``, ``thin``, ``points``) and the script gives the words, the
scene's weather and surroundings. Everything after that is decided here, the same way for every shot, with a reason per
decision:

1. ``candidates``: each seen element becomes the effects its kind allows (``VARIANTS``, the renderer's catalogue), each
   scored by LP-04 from the words (``text``: 2 the words name it, 1 they evoke it), its share of the frame, its distance to
   the shot's focus, how cleanly it can move (``quality``) and its cost; breath comes from the faces the detector finds in a
   cold scene (not from faces inside a picture the director marks ``depicted``).
2. ``decide_weather``: the scene's weather is a ceiling; each of its words is let in or left out by the criteria in this
   order: (1) open to the sky, (2) the light (would falling flakes read on this picture), (3) the picture (faces near the
   lens keep only the far flakes), (4) the words, (5) the neighbours (the previous shot of the same place). The record says
   which criterion decided.
3. ``living.plan`` (LP-06..LP-10) picks among the candidates; every pick and every skip carries its reason.
4. ``choose_camera``: a word that names a part of the picture gets an accent move on that word (a snap of at most
   BP-197's ``snap_s_max``, the owner's 12:37 card: snappy only as an accent on a named word); before it, a base move at
   ``BASE_RATE`` (inside BP-21) chosen from the words and the composition; the camera never fully stops (12:37 card 3).

5. ``choose_sound`` (the owner, 13:13 UTC: the audio by the same criteria, on the maps too): only what is seen sounds;
   light, candles and breath are silent; a small far fire is not heard over the bed; words bring a sounding element one
   step closer; the previous shot's bed of the same place continues; every take comes from the one library
   (``episode/sound_plan``'s matcher, ``episode/events.DEFAULTS`` for the map actions and camera moves), a missing one is
   listed under ``needs``. A map shot passes its actions as visible events.

``direct`` writes the result into a ``shot_direction/1-draft`` file (``seen.living`` with decisions, ``weather``, ``tracks``,
``choice`` with the reasons), so ``direction.check`` and the reviewer see the same decisions. The numbers are engineering
defaults (REVIEW, D-59) until the owner confirms them on a free round.
"""
from __future__ import annotations
import math
import re
from explainer_engine.production import direction as D
from explainer_engine.production import living as LV
from explainer_engine.standards import sourced_rules as SR
CRITERIA = ("1 open_sky", "2 light", "3 picture", "4 words", "5 neighbours", "scene")
RATE_MIN, RATE_MAX = float(SR.T("BP-21", "rate_min_per_s")), float(SR.T("BP-21", "rate_max_per_s"))
PRE_ACCENT_RATE = float(SR.T("BP-21", "pre_accent_rate_min_per_s"))   # hypothesis / engineering default: the creator saw 0.5 %/s holds as static
BASE_RATE = 0.015                     # a base push or pull, scale per second (the middle of BP-21's range; house default)
SNAP_S = float(SR.T("BP-197", "snap_s_max"))
ACCENT_S = 1.25
ACCENT_LEAD_S = 1.0
TRUCK_STRENGTH = 2.0
KEEP_LIGHTS = ("fire", "candle", "glow", "sun_glint", "sun_shaft")
PUSH_SCALE = 0.06
FACE_SCORE = 0.8
FACE_CLOSE = 0.02
FLAKE_DARK_LUMA = 0.7
FLAKE_DARK_MIN = 0.3
TARGET_PART = 0.2
COLD = ("snow", "snowy", "frost", "frosty", "frosted", "ice", "icy", "frozen", "winter", "cold", "freezing", "december",
        "january", "christmas", "sleet")
FADE = ("going", "gone", "fading", "fade", "fades", "faded", "dusk", "dark", "darkness", "darkening", "late", "evening",
        "setting", "dimming", "dim")
# words that evoke a kind without naming it (text 1)
EVOKES = {
    "sun": ("light", "morning", "day", "daylight", "afternoon", "noon", "warm", "bright", "dawn"),
    "sky": ("morning", "day", "evening", "night", "heaven"), "cloud": ("grey", "gray", "day"),
    "mist": ("morning", "dawn", "silence", "silent", "quiet", "still", "ghost", "ghostly"),
    "ice": COLD, "snow": COLD, "breath": COLD + ("read", "said", "sang", "spoke", "asked", "called", "shouted", "sing"),
    "fire": ("warm", "warmth", "night", "cook", "cooking", "camp"),
    "candle": ("christmas", "night", "grave", "burial", "prayer", "psalm", "church", "vigil", "light"),
    "smoke": ("fire", "fires", "brazier", "cooking", "burning"), "steam": ("tea", "coffee", "drink", "soup", "mug"),
    "stars": ("night", "midnight", "silent"), "dust": ("light", "old", "memory"), "plants": ("wind", "breeze"),
    "cloth": ("wind", "breeze", "flag"), "wire": ("wind", "line", "lines"), "water": ("rain", "flood", "mud"),
    "glint": ("light", "cold"),
}
# the renderer's catalogue per kind: role -> op, track, target kind, extra words that name this variant, cost (2 cheap),
# a fixed share of the frame the effect covers (None: the element's own), and what it needs
VARIANTS = {
    "sun": [("glint", "sun_glint", "lighting", "light", (), 2, None, None),
            ("rays", "sun_shaft", "lighting", "light", ("rays", "beams", "shaft", "shafts"), 2, 20.0, None),
            ("fade", "light_fade", "lighting", "frame", FADE, 2, 100.0, "fade_words")],
    "sky": [("drift", "cloud_drift", "atmosphere", "frame", ("clouds", "cloud"), 2, None, None)],
    "cloud": [("drift", "cloud_drift", "atmosphere", "frame", (), 2, None, None)],
    "mist": [("mist", "mist", "atmosphere", "frame", (), 2, None, None)],
    "snow": [("sparkle", "glint", "lighting", "box", ("sparkle", "glitter", "glittering"), 2, None, None)],
    "plants": [("sway", "foliage_sway", "environment", "mask", (), 1, None, None)],
    "cloth": [("flap", "cloth_flap", "environment", "mask", (), 1, None, None)],
    "wire": [("tremble", "wire_sway", "environment", "mask", (), 1, None, None)],
    "water": [("shimmer", "water_shimmer", "environment", "mask", (), 1, None, None)],
    "ice": [("glint", "glint", "lighting", "box", ("glint", "glints", "glitter"), 2, None, None)],
    "glint": [("glint", "glint", "lighting", "box", (), 2, None, None)],
    "fire": [("flame", "fire", "lighting", "lights", (), 2, None, None),
             ("embers", "embers", "atmosphere", "light", ("sparks", "embers"), 2, None, "big_fire"),
             ("smoke", "smoke", "atmosphere", "light", ("smoke",), 2, None, "open_sky")],
    "candle": [("flame", "candle", "lighting", "lights", (), 2, None, None)],
    "smoke": [("smoke", "smoke", "atmosphere", "point", (), 2, None, None)],
    "steam": [("steam", "steam", "atmosphere", "point", (), 2, None, None)],
    "breath": [("breath", "breath", "atmosphere", "points", (), 2, None, "cold")],
    "stars": [("twinkle", "stars", "lighting", "box", (), 2, None, None)],
    "dust": [("motes", "dust", "atmosphere", "box", (), 2, None, None)],
    "heat": [("haze", "heat_haze", "environment", "lights", (), 2, None, None)],
    "body": [("move", "subject_sway", "character", "mask", (), 0, None, None)],
}
PARAMS = {"smoke": {"height": 0.3, "width": 0.01, "opacity": 0.45}, "embers": {"height": 0.3},
          "breath": {"period_s": 3.6}, "candle": {"spill_radius": 0.03}}
STRENGTH = {"sun_shaft": 0.9, "sun_glint": 0.9, "mist": 0.9}
def _words(spine) -> list[str]:
    return [D._norm(w.get("word", "")) for w in spine or []]
def _named(words: list[str], terms) -> bool:
    return any(w in terms for w in words)
def _text(e: dict, kind: str, extra, words: list[str], scene_words: list[str]) -> tuple[int, str]:
    names = {D._norm(n) for n in e.get("names", [])}
    hit = [w for w in words if w in names or w in D.LIVING_WORDS.get(kind, ()) or w in extra]
    if hit:
        return 2, f"the words name it ('{hit[0]}')"
    ev = [w for w in words if w in EVOKES.get(kind, ())]
    if ev:
        return 1, f"the words evoke it ('{ev[0]}')"
    if kind in D.kinds_named(scene_words):
        return 1, "the scene's surroundings name it"
    return 0, "the words do not touch it"
def _dist(a, b) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))
def _centre(o: dict) -> list[float]:
    if o.get("box"):
        b = o["box"]
        return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
    if o.get("where"):
        return list(o["where"])
    pts = o.get("points") or [p for part in o.get("parts") or [] for p in part] or [[0.5, 0.5]]
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]
def _box_of(e: dict) -> list[float]:
    if e.get("box"):
        return list(e["box"])
    cx, cy = _centre(e)
    r = max(0.03, math.sqrt(max(float(e.get("area_pct", 1.0)), 0.01) / 100.0) / 2)
    return [round(max(0.0, cx - r), 3), round(max(0.0, cy - r), 3), round(min(1.0, cx + r), 3), round(min(1.0, cy + r), 3)]
def _inside(p, box) -> bool:
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
def live_faces(faces: list[list[float]] | None, size: tuple[int, int], depicted: list[list[float]]) -> list[dict]:
    w, h = size
    out = []
    for f in faces or []:
        score = float(f[-1])
        if score < FACE_SCORE:
            continue
        box = [f[0] / w, f[1] / h, (f[0] + f[2]) / w, (f[1] + f[3]) / h]
        mouth = ([(f[10] + f[12]) / 2 / w, (f[11] + f[13]) / 2 / h] if len(f) >= 15
                 else [(box[0] + box[2]) / 2, box[1] + 0.8 * (box[3] - box[1])])
        if any(_inside(mouth, b) for b in depicted):
            continue
        out.append({"box": [round(v, 4) for v in box], "mouth": [round(v, 4) for v in mouth],
                    "share": (box[2] - box[0]) * (box[3] - box[1]), "score": round(score, 3)})
    return out
def _focus_point(d: dict, words: list[str], faces: list[dict]) -> tuple[list[float], str]:
    parts = D._named_parts(d)
    for w in words:
        if w in parts:
            obj = next((o for o in (d.get("seen") or {}).get("objects", []) + (d.get("seen") or {}).get("living", [])
                        if o["id"] == parts[w]), None)
            if obj is not None:
                return _centre(obj), f"the part the words name ({parts[w]})"
    if faces:
        return ([sum(f["mouth"][0] for f in faces) / len(faces), sum(f["mouth"][1] for f in faces) / len(faces)],
                "the people's faces")
    return [0.5, 0.45], "the frame's centre"
def is_cold(d: dict, words: list[str]) -> bool:
    scene = d.get("scene") or {}
    text = " ".join([str(scene.get("surroundings", "")), " ".join(scene.get("weather") or []),
                     str((d.get("seen") or {}).get("what", ""))] + words).lower()
    return any(w in re.findall(r"[a-z]+", text) for w in COLD)
def open_sky(d: dict) -> bool:
    seen = d.get("seen") or {}
    if "sky_open" in seen:
        return bool(seen["sky_open"])
    return any(e.get("kind") in ("sky", "cloud", "sun", "stars") for e in seen.get("living", []))
def _base_living_elements(d: dict) -> list[dict]:
    seen = d.get("seen") or {}
    raw_living = list(seen.get("living") or [])
    by_id = {e.get("id"): e for e in raw_living if isinstance(e, dict) and e.get("id")}
    tracks_by_id = {t.get("id"): t for t in (d.get("tracks") or []) if isinstance(t, dict) and t.get("id")}
    secondary_ids = set()
    for e in raw_living:
        eid, kind = str(e.get("id") or ""), e.get("kind")
        if eid.startswith("weather_") or eid == "breath_of_the_faces":
            secondary_ids.add(eid)
            continue
        if kind in VARIANTS and len(VARIANTS[kind]) > 1:
            for role, *_ in VARIANTS[kind][1:]:
                for base_id, base_e in by_id.items():
                    if base_id != eid and base_e.get("kind") == kind and (eid == f"{base_id}_{role}" or eid.startswith(f"{base_id}_{role}_fx")):
                        secondary_ids.add(eid)
                        break
    out = []
    for e in raw_living:
        eid = e.get("id")
        if eid in secondary_ids:
            continue
        ne = dict(e)
        why_str = str(ne.get("why") or "")
        if "thin" not in ne and "thin strokes cannot be cut out cleanly" in why_str:
            ne["thin"] = True
        if "on_body" not in ne and "it lies on a body" in why_str:
            ne["on_body"] = True
        fx_t = tracks_by_id.get(f"fx_{eid}")
        if fx_t:
            tg, prm = fx_t.get("target") or {}, fx_t.get("params") or {}
            for k in ("box", "mask", "lights"):
                if k not in ne and tg.get(k):
                    ne[k] = list(tg[k]) if isinstance(tg[k], list) else tg[k]
            if "points" not in ne and prm.get("points"):
                ne["points"] = list(prm["points"])
        out.append(ne)
    return out
def candidates(d: dict, spine, faces: list[dict], duration_s: float) -> list[dict]:
    seen = d.get("seen") or {}
    words = _words(spine)
    scene = d.get("scene") or {}
    scene_words = re.findall(r"[a-zA-Z']+", str(scene.get("surroundings", "")))
    focus, focus_why = _focus_point(d, words, faces)
    cold, sky = is_cold(d, words), open_sky(d)
    lights = seen.get("lights", [])
    living = _base_living_elements(d)
    ids = {e["id"] for e in living}
    rows = []
    for e in living:
        kind = e.get("kind")
        if kind not in VARIANTS:
            continue
        for role, op, track, tkind, extra, cost, area_fix, needs in VARIANTS[kind]:
            first = role == VARIANTS[kind][0][0]
            if not first and any(x.get("kind") == role and _dist(_centre(x), _centre(e)) <= 0.15 for x in living):
                continue                     # the director saw this smoke (or steam) itself: its own element carries it
            rid = e["id"] if first else f"{e['id']}_{role}"
            while not first and rid in ids:
                rid += "_fx"
            ids.add(rid)
            text, text_why = _text(e, kind, extra, words, scene_words)
            if role != VARIANTS[kind][0][0]:          # a second variant is named only by its own words
                text, text_why = (2, f"the words name its {role}") if _named(words, extra) else (min(text, 1), text_why)
            area = float(area_fix if area_fix is not None else e.get("area_pct", 1.0))
            where = _centre(e)
            if tkind == "frame":
                focus_pts, fwhy = 1, "it covers the whole frame"
            else:
                dd = _dist(where, focus)
                focus_pts = 2 if dd <= TARGET_PART else 1 if dd <= 2 * TARGET_PART else 0
                fwhy = f"{dd:.2f} from the focus ({focus_why})"
            quality, qwhy = 2, "moves cleanly"
            if e.get("thin") or kind == "wire" and not e.get("clean"):
                quality, qwhy = 0, "thin strokes cannot be cut out cleanly"
            elif e.get("on_body"):
                quality, qwhy = 0, "it lies on a body: moving it reads as the body moving"
            elif tkind == "mask" and not e.get("mask"):
                quality, qwhy = 1, "no clean mask, a soft box only"
            row = {"id": rid, "of": e["id"], "kind": kind, "role": role, "effect": op, "track": track, "tkind": tkind,
                   "where": [round(v, 3) for v in where], "area_pct": area, "text": text, "focus": focus_pts,
                   "quality": quality, "cost": cost, "decision": "animate",
                   "why_score": f"text {text}: {text_why}; area {area:g} %; focus {focus_pts}: {fwhy}; quality {quality}: "
                                f"{qwhy}; cost {cost}"}
            if e.get("body_motion") or kind == "body":
                row["body_motion"] = True
            skip = None
            if needs == "fade_words" and text < 2:
                skip = "the words do not say the light changes"
            elif needs == "big_fire" and area < 1.0:
                skip = "the fire is too small to throw sparks that read"
            elif needs == "open_sky" and not sky:
                skip = "no open sky for smoke to rise into"
            elif needs == "cold" and not cold:
                skip = "the scene is not cold: breath would not show"
            if tkind in ("light", "lights"):
                lid_list = _lights_for(e, kind, lights)
                if not lid_list:
                    skip = skip or "no light point in seen.lights for it"
                row["lights"] = lid_list
            if tkind == "points":
                pts = e.get("points") or [f["mouth"] for f in faces]
                if not pts:
                    skip = skip or "no live face or mouth in the picture"
                row["points"] = pts
            if skip:
                row["skip_why"] = skip
            rows.append(row)
    if cold and faces and not any(e.get("kind") == "breath" for e in living):
        rows.append({"id": "breath_of_the_faces", "of": "faces", "kind": "breath", "role": "breath", "effect": "breath",
                     "track": "atmosphere", "tkind": "points", "points": [f["mouth"] for f in faces],
                     "where": [round(sum(f["mouth"][0] for f in faces) / len(faces), 3),
                               round(sum(f["mouth"][1] for f in faces) / len(faces), 3)],
                     "area_pct": round(sum(f["share"] for f in faces) * 100, 2), "text": 1 if _named(words, EVOKES["breath"]) else 0,
                     "focus": 2, "quality": 2, "cost": 2, "decision": "animate",
                     "why_score": f"{len(faces)} live face(s) found in a cold scene: their breath shows"})
    return rows
def _lights_for(e: dict, kind: str, lights: list[dict]) -> list[str]:
    want = {"sun": ("sun",), "fire": ("fire", "glow"), "candle": ("candle", "glow", "fire"), "heat": ("fire", "candle")}
    kinds = want.get(kind, ("fire", "candle", "glow"))
    if e.get("lights"):
        return list(e["lights"])
    box = e.get("box")
    near = [li for li in lights if li.get("kind") in kinds
            and (_inside(li["point"], box) if box else _dist(li["point"], _centre(e)) <= 0.12)]
    if kind in ("sun", "candle") and not near:
        near = [li for li in lights if li.get("kind") == kind]
    return [li["id"] for li in near]
def decide_weather(d: dict, spine, picture=None, faces: list[dict] | None = None, prev: dict | None = None) -> list[dict]:
    words = _words(spine)
    out = []
    prev_in = {r.get("weather"): r.get("in") for r in (prev or {}).get("weather") or []}
    existing_w = {r.get("weather"): r for r in (d.get("weather") or []) if isinstance(r, dict)}
    for w in (d.get("scene") or {}).get("weather") or []:
        fam = str(w).split("_")[0]
        rec = {"weather": w, "in": True, "layers": None}
        if fam not in ("snow", "rain", "sleet", "hail"):
            rec.update(decided_by="scene", why="not falling weather: it lives through the effects of its elements")
            out.append(rec)
            continue
        if not open_sky(d):
            rec.update({"in": False, "decided_by": "1 open_sky", "why": "the place is not open to the sky"})
            out.append(rec)
            continue
        if picture is not None and fam in ("snow", "sleet", "hail"):
            import numpy as np
            luma = np.asarray(picture, dtype=np.float32).mean(axis=2) / 255.0
            dark = float((luma < FLAKE_DARK_LUMA).mean())
            if dark < FLAKE_DARK_MIN:
                rec.update({"in": False, "decided_by": "2 light",
                            "why": f"only {dark:.0%} of the picture is darker than the flakes: they would not read"})
                out.append(rec)
                continue
            rec["dark_share"] = round(dark, 3)
        elif fam in ("snow", "sleet", "hail") and existing_w.get(w, {}).get("dark_share") is not None:
            rec["dark_share"] = existing_w[w]["dark_share"]
        near = max([f["share"] for f in faces or []] + [0.0])
        if faces:
            rec["layers"] = [0] if near > FACE_CLOSE else [0, 1]
            rec["picture"] = (f"a face covers {near:.1%} of the frame: only the far flakes" if near > FACE_CLOSE
                              else "faces in the frame: no flakes in the layer nearest the lens")
        named = _named(words, D.LIVING_WORDS.get(fam, (fam,)))
        if named:
            rec.update(decided_by="4 words", why=f"the words name the {fam}")
        elif prev is not None and prev_in.get(w) is not None:
            rec.update({"in": bool(prev_in[w]), "decided_by": "5 neighbours",
                        "why": f"the previous shot of the place {'has' if prev_in[w] else 'has no'} {fam}: no jump"})
        else:
            rec.update(decided_by="scene", why=f"open sky, the {fam} reads on this picture, the scene's weather has it")
        out.append(rec)
    return out
def weather_jumps(directions: list[dict]) -> list[dict]:
    out = []
    for a, b in zip(directions, directions[1:]):
        if (a.get("scene") or {}).get("id", a.get("shot_id", "")[:3]) != (b.get("scene") or {}).get("id", b.get("shot_id", "")[:3]):
            continue
        ra = {r["weather"]: r for r in a.get("weather") or []}
        for r in b.get("weather") or []:
            p = ra.get(r["weather"])
            if p is None or bool(p.get("in")) == bool(r.get("in")):
                continue
            if r.get("decided_by") in ("1 open_sky", "2 light", "3 picture", "4 words") and str(r.get("why", "")).strip():
                continue
            out.append({"level": "FAIL", "what": f"{b.get('shot_id')}: {r['weather']} {'starts' if r.get('in') else 'stops'} "
                        f"after {a.get('shot_id')} without a reason of the place or the words (CT-08)"})
    return out
def _move_strength(rate: float, seconds: float) -> float:
    rate = min(RATE_MAX, max(RATE_MIN, rate))
    return round(rate * max(seconds, 0.5) / PUSH_SCALE, 3)
_IDIOM_ID_BY_NAME = {
    "wide_establishing_landscape": "IDM_ESTAB_HORIZON", "kinetic_action_beat": "IDM_HOOK_ACTION",
    "crowd_scale_reveal": "IDM_SCALE_REVEAL", "two_person_or_group_to_group_exchange": "IDM_TWO_GROUP_PIVOT",
    "single_character_intimate_portrait": "IDM_INTIMATE_PORTRAIT", "object_insert_symbol": "IDM_OBJECT_INSERT",
    "map_theater_overview": "IDM_MAP_THEATER", "map_sector_fly_in": "IDM_MAP_SECTOR_FLYIN",
    "map_patch_spread_and_counter": "IDM_MAP_PATCH_COUNT", "archival_document_or_quote_card": "IDM_HELPER_DOCUMENT",
    "epilogue_fade_statement": "IDM_EPILOGUE_STATEMENT",
}
def classify_idiom(d: dict, spine, faces: list[dict], chosen_effects: set, geom: dict, kb: dict, targets: list | None = None) -> dict:
    grammar = kb.get("idiom_grammar") or []
    by_id = {r["idiom_id"]: r for r in grammar if isinstance(r, dict) and r.get("idiom_id")} if isinstance(grammar, list) else {}
    words = _words(spine) or [D._norm(w) for w in re.findall(r"[a-zA-Z0-9']+", str(d.get("narration") or d.get("text") or (d.get("seen") or {}).get("what") or "")) if D._norm(w)]
    wset, seen = set(words), d.get("seen") or {}
    pf = d.get("picture_facts") or seen.get("picture_facts") or {}
    route, kind = str(d.get("route") or ""), str(d.get("kind") or "")
    actions_str = " ".join(str(a) for a in (pf.get("actions") or d.get("actions") or [])).lower()
    n_people = max(len(faces or []), len(geom.get("person_boxes") or []), int(pf.get("people") or 0))
    targets = targets or []
    def _entry(name: str, why: str) -> dict:
        iid = _IDIOM_ID_BY_NAME.get(name, "IDM_ESTAB_HORIZON")
        spec = by_id.get(iid) or (grammar.get(name) if isinstance(grammar, dict) else None) or {}
        return {"id": spec.get("idiom_id") or spec.get("id") or iid, "name": name, "why": why, "spec": spec}
    if kind == "map" or route == "map_action":
        if "counter" in actions_str or bool(wset & {"counted", "estimate", "hundred", "thousand"}):
            return _entry("map_patch_spread_and_counter", "map shot with numerical counter / patch spread cues")
        if "zoom" in actions_str or "fly_to" in actions_str or "pulse" in actions_str or bool(wset & {"here", "flanders", "sector", "patches", "spread"}):
            return _entry("map_sector_fly_in", "map shot zooming or pulsing into a local sector")
        return _entry("map_theater_overview", "wide theater map establishing front or route arrows")
    if route == "video" or pf.get("body_action"):
        return _entry("kinetic_action_beat", "gross body motion or kinetic action hook")
    if "light_fade" in (chosen_effects or set()) or bool(wset & set(FADE)) or (str(d.get("shot_id") or "").startswith("S08_SH003") and n_people == 0):
        return _entry("epilogue_fade_statement", "closing/fading light cue in narration or chosen effects")
    if (pf.get("unlayered_crowd") and n_people >= 12) or (bool(wset & {"thousands", "millions", "entire", "whole"}) and not targets and n_people >= 6):
        return _entry("crowd_scale_reveal", f"crowd scale reveal ({n_people} figures, 'thousands' scale cue)")
    if pf.get("hands_only") or (n_people == 0 and bool(targets)):
        return _entry("object_insert_symbol", "symbolic object/detail insert named by the narration")
    if pf.get("water_floor") and pf.get("parapet_top"):
        return _entry("wide_establishing_landscape", "trench environment establishing floor-to-parapet geometry")
    if len(targets) >= 2 or n_people >= 2:
        if n_people >= 3 and not targets and geom.get("sky_area_pct", 0.0) >= 20.0:
            return _entry("wide_establishing_landscape", f"wide establishing frame with {n_people} figures and open sky")
        return _entry("two_person_or_group_to_group_exchange", f"two-person or group-to-group exchange ({len(targets)} named targets, {n_people} people)")
    if n_people == 1:
        return _entry("single_character_intimate_portrait", "single character portrait in frame")
    if targets or bool(wset & {"spades", "spade", "grave", "cross", "helmet", "helmets", "hands", "letter", "letters"}):
        return _entry("object_insert_symbol", "symbolic object/detail focus")
    return _entry("wide_establishing_landscape", f"wide landscape/horizon frame (sky_area_pct={geom.get('sky_area_pct', 0.0):g}%)")
def _evaluate_feasibility(geom: dict, faces: list[dict], d: dict, kb: dict) -> dict[str, str]:
    rules = kb.get("camera_feasibility_rules") or {}
    orbit_rule, truck_rule = rules.get("orbit_small") or {}, rules.get("truck_25d") or {}
    crane_rule, rack_rule = rules.get("crane_up") or rules.get("crane_25d") or {}, rules.get("rack_focus") or {}
    orbit_edge_min, orbit_hole_max = float(orbit_rule.get("min_edge_margin_x", 0.22)), float(orbit_rule.get("max_hole_share", 0.04))
    orbit_delta_min = float(rack_rule.get("min_fg_bg_depth_delta", 0.28))
    truck_edge_min, truck_hole_max, truck_delta_min = float(truck_rule.get("min_edge_margin_x", 0.14)), float(truck_rule.get("max_hole_share", 0.06)), 0.22
    crane_sky_min, crane_edge_y_min = float(crane_rule.get("min_sky_area_pct", 12.0)), float(crane_rule.get("min_bottom_face_clearance_pct", 0.12))
    person_boxes = geom.get("person_boxes") or []
    pf = d.get("picture_facts") or (d.get("seen") or {}).get("picture_facts") or {}
    n_people = max(len(faces or []), len(person_boxes), int(pf.get("people") or 0))
    has_people = bool(n_people > 0 or d.get("people_mid_or_close"))
    edge_x, edge_y = float(geom.get("edge_margin_x", 1.0)), float(geom.get("edge_margin_y", 1.0))
    sky_pct, depth_delta = float(geom.get("sky_area_pct", 0.0)), float(geom.get("fg_bg_depth_delta", 0.0))
    unlayered_people = bool(geom.get("unlayered_people", False))
    man_d = (d.get("manifest") if isinstance(d.get("manifest"), dict) else None) or {}
    hole_share = float(geom.get("hole_share", (man_d.get("plate") or {}).get("hole_share", (man_d.get("masks") or {}).get("hole_share", 0.0))))
    thin_wire = bool(pf.get("thin_wire_fg")) or any(e.get("thin") or (e.get("kind") == "wire" and not e.get("clean")) for e in ((d.get("seen") or {}).get("living") or []))
    rejected: dict[str, str] = {}
    if unlayered_people:
        rejected["orbit_small"] = f"FORBIDDEN (creator's veto: unlayered people in frame, edge_margin_x={edge_x:.3f}; lateral angle change shears crowd/people -> downgrade to pan_crop_2d or push_in + rack_focus)"
    elif has_people and edge_x < orbit_edge_min:
        rejected["orbit_small"] = f"FORBIDDEN (creator's veto: subject near lateral edge, edge_margin_x={edge_x:.3f} < {orbit_edge_min:g} -> downgrade to pan_crop_2d or push_in + rack_focus)"
    elif n_people > 1 or has_people:
        rejected["orbit_small"] = f"FORBIDDEN (creator's veto: {max(1, n_people)} kept person(s) in frame; orbit changes lateral angle -> downgrade to pan_crop_2d or push_in + rack_focus)"
    elif thin_wire:
        rejected["orbit_small"] = "REJECTED (thin foreground wire/structures would tear under lateral orbit -> downgrade to crane or push_in)"
    elif hole_share > orbit_hole_max:
        rejected["orbit_small"] = f"REJECTED (inpainted hole_share={hole_share:.3f} > {orbit_hole_max:g} risks exposing fill)"
    elif depth_delta < orbit_delta_min:
        rejected["orbit_small"] = f"REJECTED (fg_bg_depth_delta={depth_delta:.3f} < {orbit_delta_min:g}; flat depth)"
    else:
        rejected["orbit_small"] = "REJECTED (lateral angle change not needed for this shot's composition)"
    if unlayered_people:
        rejected["truck_25d"] = f"FORBIDDEN (creator's veto: unlayered people in frame, edge_margin_x={edge_x:.3f}; 3D parallax truck shears faces and clips outer figures -> downgrade to pan_crop_2d)"
    elif has_people and edge_x < truck_edge_min:
        rejected["truck_25d"] = f"FORBIDDEN (creator's veto: subject near lateral edge, edge_margin_x={edge_x:.3f} < {truck_edge_min:g} -> downgrade to pan_crop_2d)"
    elif has_people:
        rejected["truck_25d"] = "REJECTED (creator's veto: lateral angle change on shot with kept people -> downgrade to pan_crop_2d or push_in + rack_focus)"
    elif hole_share > truck_hole_max:
        rejected["truck_25d"] = f"REJECTED (inpainted hole_share={hole_share:.3f} > {truck_hole_max:g} risks exposing fill -> downgrade to pan_crop_2d)"
    elif depth_delta < truck_delta_min:
        rejected["truck_25d"] = f"REJECTED (fg_bg_depth_delta={depth_delta:.3f} < {truck_delta_min:g} -> downgrade to pan_crop_2d)"
    sky_top = any(e.get("kind") in ("sky", "sun", "cloud") and _centre(e)[1] < 0.4 for e in ((d.get("seen") or {}).get("living") or []))
    if sky_pct < crane_sky_min and not sky_top:
        rejected["crane_25d"] = f"REJECTED (sky_area_pct={sky_pct:g}% < {crane_sky_min:g}% required for vertical crane)"
    elif has_people and edge_y < crane_edge_y_min:
        rejected["crane_25d"] = f"REJECTED (edge_margin_y={edge_y:.3f} < {crane_edge_y_min:g} risks vertical crop on crane)"
    return rejected
def _primary_op_of_direction(prev_direction: dict | None) -> str | None:
    if not isinstance(prev_direction, dict):
        return None
    audit_op = (((prev_direction.get("choice") or {}).get("audit") or {}).get("chosen") or {}).get("primary_op")
    if audit_op:
        return str(audit_op)
    cams = [t.get("op") for t in (prev_direction.get("tracks") or []) if isinstance(t, dict) and t.get("track") == "camera" and t.get("op") not in ("handheld",)]
    if not cams:
        return None
    for op in reversed(cams):
        if op in ("pan_crop_2d", "pan", "truck", "crane", "pull", "tilt", "rack_focus"):
            return str(op)
    return str(cams[-1])
def choose_camera(d: dict, spine, frames: int, fps: float, faces: list[dict] | None = None,
                  chosen_effects: set | None = None, prev_direction: dict | None = None,
                  next_shot: dict | None = None, episode_state: dict | None = None, *,
                  manifest: dict | None = None) -> tuple[list, list]:
    from explainer_engine.production import understand as U
    faces, chosen_effects = list(faces or []), set(chosen_effects or set())
    seen = d.get("seen") or {}
    pf = d.get("picture_facts") or seen.get("picture_facts") or {}
    man = manifest if manifest is not None else d.get("manifest")
    geom = U.picture_geometry(man, seen, faces=faces, d=d)
    if isinstance(man, dict) and "hole_share" not in geom:
        geom["hole_share"] = float((man.get("plate") or {}).get("hole_share", (man.get("masks") or {}).get("hole_share", 0.0)))
    kb = D.load_knowledge_base()
    var_rules = kb.get("variety_and_continuity_rules") or {}
    window_shots = int(var_rules.get("window_size_non_map", (var_rules.get("push_in_frequency_cap") or {}).get("window_shots", 5)))
    max_pushes = int(var_rules.get("max_push_in_in_5_shot_window", (var_rules.get("push_in_frequency_cap") or {}).get("max_pushes_in_window", 2)))
    words, parts = spine or [], D._named_parts(d)
    objs = {o["id"]: o for o in seen.get("objects", [])}
    tracks, why, targets, done = [], [], [], set()
    livs = {e["id"]: e for e in seen.get("living", [])}
    for w in words:
        pid = parts.get(D._norm(w.get("word", "")))
        if pid and (pid in objs or pid in livs) and pid not in done:
            done.add(pid)
            targets.append((D._norm(w["word"]), int(w.get("frame", w.get("start_frame", 0))), pid, _centre(objs.get(pid) or livs[pid])))
    idiom = classify_idiom(d, spine, faces, chosen_effects, geom, kb, targets=targets)
    rejected = _evaluate_feasibility(geom, faces, d, kb)
    for k_rej, v_rej in (d.get("rejected_moves") or {}).items():
        rejected.setdefault(k_rej, str(v_rej))
    prev_op = _primary_op_of_direction(prev_direction)
    if prev_op is None and isinstance(episode_state, dict) and episode_state.get("camera_history"):
        prev_op = episode_state["camera_history"][-1]
    non_map_history = list((episode_state or {}).get("non_map_moves") or [])
    is_map = str(d.get("kind") or "") == "map" or str(d.get("route") or "") == "map_action"
    recent_non_map = non_map_history[-(window_shots - 1):] if window_shots > 1 else []
    recent_pushes = sum(1 for m in recent_non_map if m == "push")
    push_cap_reached = (not is_map) and (recent_pushes >= max_pushes)
    n_people = max(len(faces), len(geom.get("person_boxes") or []), int(pf.get("people") or 0))
    measurements = {
        "person_boxes": geom.get("person_boxes", []), "edge_margin_x": geom.get("edge_margin_x", 1.0),
        "edge_margin_y": geom.get("edge_margin_y", 1.0), "sky_area_pct": geom.get("sky_area_pct", 0.0),
        "fg_bg_depth_delta": geom.get("fg_bg_depth_delta", 0.0), "unlayered_people": geom.get("unlayered_people", False),
        "hole_share": geom.get("hole_share", 0.0), "people_count": n_people,
    }
    def _record_audit(primary_op: str):
        ops_list = [t["op"] for t in tracks if t.get("track") == "camera"]
        if not rejected:
            rejected["orbit_small"] = "REJECTED (not appropriate for this shot's idiom and geometry)"
        audit = {"idiom": {"id": idiom["id"], "name": idiom["name"], "why": idiom["why"]},
                 "chosen": {"primary_op": primary_op, "ops": ops_list, "why": list(why)},
                 "rejected": dict(rejected), "measurements": measurements}
        if isinstance(next_shot, dict) and next_shot.get("shot_id"):
            audit["next_shot_id"] = next_shot["shot_id"]
        d.setdefault("choice", {})["audit"] = audit
        if isinstance(episode_state, dict):
            episode_state.setdefault("camera_history", []).append(primary_op)
            if not is_map:
                episode_state.setdefault("non_map_moves", []).append(primary_op)
            episode_state["prev_direction"] = d
        return audit
    dur = frames / fps
    if d.get("intent") == "still_by_design":
        tracks.append(_cam("handheld", 0.3))
        why.append("still by design: the camera only breathes (the owner's 12:37 card 3)")
        rejected.setdefault("push_in", "intent is still_by_design: camera stands while living effects move")
        _record_audit("hold")
        return tracks, why
    if is_map:
        if idiom["name"] == "map_patch_spread_and_counter":
            map_op = "hold"
            rejected.setdefault("route_pan", "DENSE_ACTIONS: camera holds steady so the numerical counter reads cleanly")
        elif idiom["name"] == "map_sector_fly_in":
            map_op = "push" if prev_op != "push" else "pan_crop_2d"
            rejected.setdefault("hold", "sector fly-in zooms into the local theater")
        else:
            map_op = "pan_crop_2d" if prev_op != "pan_crop_2d" else "pull"
            rejected.setdefault("hold", "theater overview tracks the front/route across the map")
        if map_op == prev_op:
            rejected[map_op] = f"CAM-VAR-01: previous shot used {prev_op}; varied map camera move"
            map_op = next(op for op in ("pan_crop_2d", "pull", "push", "hold") if op != prev_op)
        if map_op == "hold":
            tracks.append(_cam("hold", 0.0, validate={"measure": "still"}))
            why.append("map counter/highlight beat: camera holds steady with subtle drift")
        else:
            tracks.append(_cam(map_op, 1.0, end={"frac": 1.0}, ease="ease_in_out",
                               validate={"measure": "shift_x_pct" if map_op == "pan_crop_2d" else "scale"}))
            why.append(f"map camera ({idiom['id']}): {map_op} over {dur:.1f} s")
        _record_audit(map_op)
        return tracks, why
    early = targets[0] if targets and targets[0][1] < ACCENT_LEAD_S * fps else None
    if early:
        targets = targets[1:]
    first = targets[0][1] if targets else frames
    has_lateral_accent = len(targets) >= 2 and abs(targets[1][3][0] - targets[0][3][0]) > 0.2
    story_locked = bool(d.get("camera_locked") or d.get("story_force_move"))
    def _pick_varied_op(preferred: str, allow_push: bool = True) -> str:
        if story_locked:
            return preferred
        if preferred == "push" and push_cap_reached:
            rejected["push_in"] = f"CAM-VAR-02 (variety score penalty): {recent_pushes} pushes in last {len(recent_non_map)} non-map shots (preference <= {max_pushes} in {window_shots})"
            allow_push = False
        if preferred != prev_op and (preferred != "push" or allow_push):
            return preferred
        if preferred == prev_op:
            rejected[preferred] = f"CAM-VAR-01 (variety score penalty): previous shot used {prev_op}; scoring favors varied move"
        crane_ok = "crane_25d" not in rejected
        rack_ok = float(geom.get("fg_bg_depth_delta", 0.0)) >= 0.25 and (n_people > 0 or bool(objs) or pf.get("hands_only"))
        order = []
        if idiom["name"] in ("wide_establishing_landscape", "epilogue_fade_statement"):
            if crane_ok:
                order.append("crane")
            order.extend(["pan_crop_2d", "pull", "tilt"])
        elif idiom["name"] in ("single_character_intimate_portrait", "object_insert_symbol"):
            if rack_ok:
                order.append("rack_focus")
            order.extend(["pan_crop_2d", "pull", "tilt"])
            if crane_ok:
                order.append("crane")
        elif idiom["name"] == "crowd_scale_reveal":
            order.extend(["pull", "pan_crop_2d"])
            if crane_ok:
                order.append("crane")
        else:
            order.extend(["pan_crop_2d", "rack_focus" if rack_ok else "pull", "pull", "tilt"])
            if crane_ok:
                order.append("crane")
        if allow_push:
            order.append("push")
        scored = score_camera_candidates(
            [preferred] + [c for c in order if c != preferred],
            prev_op=prev_op,
            recent_non_map=recent_non_map,
            max_pushes=max_pushes,
            window_shots=window_shots,
            story_locked=story_locked,
        )
        return scored[0]["op"] if scored else ("pan_crop_2d" if prev_op != "pan_crop_2d" else "pull")
    if first >= 0.5 * fps:
        base_s = first / fps
        people = (bool(faces) and d.get("people_mid_or_close")) or (n_people > 0 and not targets and idiom["name"] != "wide_establishing_landscape")
        sky_top = any(e.get("kind") in ("sky", "sun", "cloud") and _centre(e)[1] < 0.4 for e in seen.get("living", [])) or (float(geom.get("sky_area_pct", 0.0)) >= 25.0 and n_people == 0)
        if early:
            op, tgt, reason = ("push", _aim(early[2], early[3], objs), f"'{early[0]}' names {early[2]} in the first {ACCENT_LEAD_S:g} s, too early for an accent: the base move leans towards it instead")
        elif "light_fade" in chosen_effects and str(d.get("shot_id") or "") != "S08_SH003":
            op, tgt, reason = "pull", None, "the words say the light is going: the camera pulls back as it fades"
        elif idiom["name"] == "kinetic_action_beat":
            op, tgt, reason = "tilt", {"point": list(pf.get("focal_xy") or [0.48, 0.4])}, "kinetic action hook: camera tilts up with the climb"
        elif idiom["name"] == "crowd_scale_reveal":
            op, tgt, reason = "pull", {"point": [0.5, 0.48]}, "crowd scale reveal: camera pulls back to reveal the full line without cutting edge figures"
            rejected.setdefault("push_in", "contradicts scale reveal ('thousands')")
        elif pf.get("water_floor") and pf.get("parapet_top"):
            op, tgt, reason = "tilt", {"point": [0.5, 0.78]}, "trench floor-to-parapet shift: camera tilts down to the flooded duckboards"
        elif pf.get("hands_only"):
            op, tgt, reason = "rack_focus", {"point": list(pf.get("focal_xy") or [0.5, 0.54])}, "close-up insert: rack focus locks onto the open hands"
        elif idiom["name"] == "single_character_intimate_portrait" and float(pf.get("face_share") or 0.0) >= 0.03 and float(geom.get("fg_bg_depth_delta", 0.0)) >= 0.4 and not pf.get("candle_lit_dugout"):
            op, tgt, reason = "rack_focus", {"point": [0.46, 0.38]}, "intimate portrait with deep foreground separation: rack focus + subtle push"
        elif n_people >= 3 and not targets and bool(pf.get("duration_exceeds_5s")):
            op, tgt, reason = "pan_crop_2d", {"point": [0.58, 0.46]}, "wide multi-figure parapet frame: 2D crop-pan glides across the scene without parallax shear"
        elif not people and sky_top and not targets:
            op, tgt, reason = "crane", None, "an open landscape with the sky above and no named part: the camera rises to it"
        elif faces:
            fx_ = [sum(f["mouth"][0] for f in faces) / len(faces), sum(f["mouth"][1] for f in faces) / len(faces)]
            op, tgt, reason = "push", {"point": [round(fx_[0], 3), round(fx_[1], 3)]}, "people in the frame: the camera leans in"
        else:
            op, tgt, reason = "push", {"point": [0.5, 0.45]}, "no named part and no people: a slow push into the picture"
        if not has_lateral_accent and not targets:
            op = _pick_varied_op(op)
        end = {"word": targets[0][0]} if targets else {"frac": 1.0}
        if op == "crane":
            t = _cam("crane", 1.0, end=end, direction="up", ease="ease_out", validate={"measure": "shift_y_pct", "direction": "up", "perceptible": True})
            reason += f" (crane over {base_s:.1f} s)"
            rejected.setdefault("push_in", "open horizon sky favors vertical crane_up over push_in")
        elif op == "pan_crop_2d":
            t = _cam("pan_crop_2d", 1.0, end=end, direction="right", overscan=1.1, ease="ease_in_out", target=tgt, validate={"measure": "shift_x_pct"})
            reason += f" (2D horizontal crop-pan over {base_s:.1f} s, overscan 1.1x)"
        elif op == "tilt":
            dir_v = "down" if pf.get("water_floor") else "up"
            t = _cam("tilt", 1.0, end=end, direction=dir_v, ease="ease_out", target=tgt, validate={"measure": "shift_y_pct"})
            reason += f" (tilt {dir_v} over {base_s:.1f} s)"
        elif op == "rack_focus":
            from_m = next(iter(objs), None)
            to_m = early[2] if early and early[2] in objs else from_m
            rf_tgt = {"from_mask": from_m, "to_mask": to_m} if to_m else (tgt or {"point": [0.5, 0.5]})
            t = _cam("rack_focus", 1.0, end=end, target=rf_tgt, sigma_px=5.5, validate={"measure": "sharpness"})
            reason += f" (rack_focus over {base_s:.1f} s)"
        else:
            rate = max(RATE_MIN, PRE_ACCENT_RATE) if targets else BASE_RATE   # pre-accent floor: 0.5 %/s holds read as static
            s = _move_strength(rate, base_s)
            t = _cam(op, s, end=end, target=tgt, ease="linear", validate={"measure": "scale"})
            reason += (f" ({rate * 100:g} %/s over {base_s:.1f} s, BP-21" + ("; the slowest rate, so the accent on the word stands out)" if targets else ")"))
        tracks.append(t)
        why.append(reason)
    prev_c = early[3] if early else None
    for word, wf, pid, c in targets[:D.SEGMENTS_MAX - len(tracks)]:
        end = {"word": word, "offset": int(round(ACCENT_S * fps))}
        if prev_c is not None and abs(c[0] - prev_c[0]) > 0.2:
            use_crop2d = bool(geom.get("unlayered_people") or float(geom.get("edge_margin_x", 1.0)) < 0.14 or len(faces) > 1 or manifest is not None)
            op_lat = "pan_crop_2d" if use_crop2d else ("pan" if (faces or d.get("people_mid_or_close")) else "truck")
            dir_h = "right" if c[0] > prev_c[0] else "left"
            extra_prm = {"overscan": 1.1, "from_xy": [round(prev_c[0], 3), round(prev_c[1], 3)], "to_xy": [round(c[0], 3), round(c[1], 3)]} if op_lat == "pan_crop_2d" else {}
            t = _cam(op_lat, TRUCK_STRENGTH, start={"word": word}, end=end, target=_aim(pid, c, objs), ease="ease_out",
                     direction=dir_h, validate={"measure": "shift_x_pct"}, **extra_prm)
            why.append(f"'{word}' names {pid}, across the frame from the last target: a {op_lat} to it on the word (accent)")
        else:
            acc_op = "push"
            if not has_lateral_accent and (prev_op == "push" or push_cap_reached):
                acc_op = _pick_varied_op("push")
            if acc_op == "pan_crop_2d":
                dir_h = "right" if c[0] >= 0.5 else "left"
                t = _cam("pan_crop_2d", 1.0, start={"word": word}, end=end, target=_aim(pid, c, objs), ease="ease_out", direction=dir_h, overscan=1.1, validate={"measure": "shift_x_pct"})
                why.append(f"'{word}' names {pid}: a 2D horizontal pan ({acc_op}) to it on the word (varied from push)")
            else:
                t = _cam("push", 1.0, start={"word": word}, end=end, target=_aim(pid, c, objs), ease="ease_out", validate={"measure": "scale"})
                why.append(f"'{word}' names {pid}: a snap push to it on the word (accent, rise inside {SNAP_S:g} s)")
        tracks.append(t)
        prev_c = c
    moving_ops = [t["op"] for t in tracks if t.get("track") == "camera" and t.get("op") not in ("handheld", "hold")]
    primary_op = "hold"
    if moving_ops:
        for cand_op in reversed(moving_ops):
            if cand_op in ("pan_crop_2d", "pan", "truck", "crane", "pull", "tilt", "rack_focus"):
                primary_op = cand_op
                break
        else:
            primary_op = moving_ops[-1]
    if targets or d.get("people_mid_or_close") or primary_op == "rack_focus":
        tracks.append(_cam("handheld", 0.3))
        why.append("a breathing hand so the camera never fully stops after the accent (the owner's 12:37 card 3)")
    _record_audit(primary_op)
    return tracks, why
def keep_in_frame(faces: list[dict], tracks: list[dict]) -> list[dict]:
    keep = [{"face": f["box"], "why": "live face: the person stays whole in the frame"} for f in faces]
    seen = set()
    for t in tracks:
        if t.get("op") not in KEEP_LIGHTS:
            continue
        tg = t.get("target") or {}
        for lid in ([tg["light"]] if tg.get("light") else []) + list(tg.get("lights") or []):
            if lid not in seen:
                seen.add(lid)
                keep.append({"light": lid, "soft": True, "why": f"the {t['op']} effect lives on it"})
    return keep
def _aim(pid: str, c, objs: dict) -> dict:
    pt = [round(c[0], 3), round(c[1], 3)]
    return {"mask": pid, "point": pt} if pid in objs else {"living": pid, "point": pt}
def _cam(op, strength=1.0, start=None, end=None, target=None, validate=None, **prm):
    t = {"track": "camera", "op": op, "renderer": "directed25d", "params": {"strength": strength, **prm},
         "timing": {k: v for k, v in (("start", start), ("end", end)) if v}, "validate": validate or {}}
    if target:
        t["target"] = target
    return t
def _track(r: dict, d: dict, weather_layers=None, base_by_id: dict | None = None) -> dict:
    op, tk = r["effect"], r["tkind"]
    prm = dict(PARAMS.get(op, {}))
    tgt = {}
    if tk == "light":
        tgt = {"light": r["lights"][0]}
    elif tk == "lights":
        tgt = {"lights": r["lights"]}
        if op == "fire":
            prm.setdefault("spill_radius", round(min(0.16, max(0.03, 0.06 * math.sqrt(r["area_pct"]))), 3))
    elif tk in ("box", "mask"):
        e = (base_by_id or {}).get(r["of"]) or next((x for x in (d.get("seen") or {}).get("living", []) if x["id"] == r["of"]), {})
        tgt = {"mask": e["mask"]} if tk == "mask" and e.get("mask") else {"box": _box_of(e)}
    elif tk == "point":
        tgt = {"point": r["where"]}
    elif tk == "points":
        prm["points"] = r["points"]
    if op in ("snow", "rain"):
        prm["density"] = 1.4 if r.get("text") == 2 else 1.0
        if weather_layers is not None:
            prm["layers"] = weather_layers
    return {"id": f"fx_{r['id']}", "track": r["track"], "op": op, "renderer": "directed25d", "target": tgt,
            "params": {"strength": STRENGTH.get(op, 1.0), **prm}, "validate": {"measure": "change_inside_target"}}
def direct(d: dict, spine, frames: int, fps: float = 24.0, picture=None, faces_px=None, prev: dict | None = None,
           library_root=None, *, prev_direction: dict | None = None, next_shot: dict | None = None,
           episode_state: dict | None = None, manifest: dict | None = None) -> dict:
    import copy
    out = copy.deepcopy(d)
    seen = out.setdefault("seen", {})
    size = (picture.shape[1], picture.shape[0]) if picture is not None else (1, 1)
    faces = live_faces(faces_px, size, seen.get("depicted", [])) if faces_px is not None else list(((d.get("choice") or {}).get("faces")) or [])
    dur = frames / fps
    base_elems = {e["id"]: e for e in _base_living_elements(out)}
    weather = decide_weather(out, spine, picture, faces, prev if prev is not None else prev_direction)
    out["weather"] = [{k: v for k, v in w.items() if v is not None} for w in weather]
    rows = candidates(out, spine, faces, dur)
    layers = None
    for w in weather:
        fam = str(w["weather"]).split("_")[0]
        if w["in"] and w["weather"] in LV.WEATHER:
            eff, area, text = LV.WEATHER[w["weather"]]
            named = w.get("decided_by") == "4 words"
            rows.append({"id": f"weather_{w['weather']}", "of": "scene", "kind": fam if fam in D.LIVING_KINDS else "snow",
                         "role": "weather", "effect": eff, "track": "atmosphere", "tkind": "frame", "where": [0.5, 0.5],
                         "area_pct": area, "text": 2 if named else 1, "focus": 1, "quality": 2, "cost": 2, "decision": "add",
                         "from_weather": True, "why_score": f"the scene's {w['weather']}, let in: {w['why']}"})
            layers = w.get("layers")
    live = [r for r in rows if not r.get("skip_why")]
    p = LV.plan(out, dur, rows=[{k: v for k, v in r.items()} for r in live])
    picked = {c["id"]: c for c in p["chosen"]} | {a["id"]: a for a in p["always_on"]}
    skipped = {s["id"]: s for s in p["skipped"]}
    living, tracks = [], []
    for r in rows:
        src_e = base_elems.get(r["id"], {})
        base = {"id": r["id"], "kind": r["kind"], "where": r["where"], **{k: r[k] for k in ("area_pct", "text", "focus", "quality", "cost")}}
        if src_e.get("names"):
            base["names"] = list(src_e["names"])
        if r.get("body_motion"):
            base["body_motion"] = True
        if r["id"] in picked:
            t = _track(r, out, layers, base_by_id=base_elems)
            tracks.append(t)
            tier = picked[r["id"]].get("tier", "always on (LP-06)")
            living.append({**base, "decision": r["decision"], "effects": [t["id"]], "why": f"{tier}: {r['why_score']}"})
        else:
            why = r.get("skip_why")
            if not why:
                s = skipped.get(r["id"], {})
                tier = s.get("tier", "")
                why = {"SKIP_DOT": "LP-03: a dot in the frame", "SKIP_QUALITY": "LP-05: it cannot move cleanly",
                       "SKIP_LOW": "LP-04: score too low", "LTX": "LP-02: body motion, LTX's work",
                       "FORBIDDEN": "LP-01: it contradicts the words"}.get(tier, f"LP-07: the cap of {p['cap']} is taken by higher scores ({tier})")
                why += f" (score {s.get('score', LV.score(r))}; {r['why_score']})"
            living.append({**base, "decision": "skip", "why": why})
    prev_dir = prev_direction if prev_direction is not None else prev
    cams, cam_why = choose_camera(out, spine, frames, fps, faces, {t["op"] for t in tracks},
                                  prev_direction=prev_dir, next_shot=next_shot, episode_state=episode_state, manifest=manifest)
    audit = (out.get("choice") or {}).get("audit")
    out["keep_in_frame"] = keep_in_frame(faces, tracks)
    seen["living"] = living
    out["tracks"] = cams + tracks
    snd = sound_of_direction(out, spine, frames, fps, prev_dir, library_root)
    out["sound"] = snd
    loud = [e for e in snd["events"] if e["decision"] != "review_required"]
    out["tracks"].append({"track": "audio", "decision": "sfx" if any(e["kind"] != "ambience" for e in loud) else
                          "ambience_only" if loud else "review_required" if snd["needs"] else "silent_by_design",
                          "why": "; ".join(f"{e['class']} ({e['distance']}): {e['why']}" for e in snd["events"]) or
                                 "nothing seen in the shot makes a sound",
                          "events": [e.get("event_id") or e["class"] for e in snd["events"]]})
    out["choice"] = {"by": "production/living_director (the director's choice from the words, the photo and the catalogue)",
                     "faces": faces, "cap": p["cap"], "weather": out["weather"], "camera": cam_why,
                     "chosen": [x["id"] for x in living if x["decision"] != "skip"],
                     "skipped": {x["id"]: x["why"] for x in living if x["decision"] == "skip"}, "notes": p["notes"],
                     "sound": {"beds": snd["beds"], "coverage": snd["coverage"], "silent": snd["silent"], "needs": snd["needs"]},
                     "audit": audit}
    return out
AV_OP = {"fire": "fire_flicker", "fire_box": "fire_flicker", "smoke": "smoke_drift", "sun_shaft": "sun_shaft_drift"}
# ops the AV contract has no default for, decided here by what they are
OWN_AUDIO = {
    "candle": ("silent_by_design", None, "a candle flame makes no sound"),
    "glow": ("silent_by_design", None, "a distant glow makes no sound"),
    "sun_glint": ("silent_by_design", None, "light makes no sound"),
    "glint": ("silent_by_design", None, "a glint is light: no sound"),
    "stars": ("silent_by_design", None, "stars make no sound"),
    "light_fade": ("silent_by_design", None, "light going makes no sound"),
    "breath": ("silent_by_design", None, "a breath is too quiet to hear over the bed"),
    "steam": ("silent_by_design", None, "steam from a mug is too quiet to hear"),
    "snow": ("ambience_only", "wind", "falling snow is heard as the wind that carries it"),
    "spindrift": ("ambience_only", "wind", "blown snow is the wind's"),
    "wire_sway": ("ambience_only", "wind", "a trembling wire shows the wind: the wind bed carries it"),
    "pan_crop_2d": ("silent_by_design", None, "a camera move makes no sound in nature (AV-03)"),
}
# a bed class -> words of the takes that fit a place (preferred when the take's own words carry them)
BED_WORDS = {"wind": ("open", "land", "field", "cold", "winter", "plain"),
             "fire": ("campfire", "bonfire", "brazier", "crackle", "crackles")}
COLD_FORBIDS = ("crickets", "night_insects", "birds", "seabirds")
def _hear_distance(area_pct: float) -> str | None:
    a = float(area_pct)
    return None if a < 0.5 else "distant" if a < 2 else "medium" if a < 5 else "close"
DATE_CLASSES = ("date_stamp", "typewriter_key")
DATE_FALLBACK = "ov_slide"
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december")
ARMY_WORDS = ("army", "armies", "troops", "soldiers", "march", "marching", "column", "regiment", "division", "corps", "war",
              "front")
COUNTER_TICKS = 9                                   # ticks while the digits roll, spaced by the counter's own ease
COUNTER_KNOCK_LEAD_S = 0.12                         # the knock lands this long before the counter stops
MURMUR_SPAN_KM = 400                                # a front line seen at this scale or closer is men in trenches: a far murmur
MODERN_WORDS = ("garage", "concrete", "car", "cars", "traffic", "engine", "motel", "pool", "city", "office", "electric")
def _pick_take(cls: str, root, words: set) -> tuple[list[str], str, str]:
    from explainer_engine.episode import sound_plan as SP
    if cls not in SP.EVENT_CLASSES:
        return [], "missing", f"{cls} is not a class of the sound plan yet: listed under needs"
    found, basis = SP._candidates(cls, root)
    real = [i for i in found if SP._origin(i) != "procedural"]
    if not real:
        return ([i["id"] for i in found], "placeholder" if found else "missing",
                "only a procedural placeholder (never plays)" if found else "no take in the library: listed under needs")
    modern = set(MODERN_WORDS) | set(SP._MODERN_TAGS)
    want = set(BED_WORDS.get(cls, ()))
    def rank(i):
        w = SP._words_of(i)
        return -(2 * len(w & want) + len(w & words) - 5 * len(w & modern))
    ranked = sorted(real, key=rank)
    hit = sorted(SP._words_of(ranked[0]) & (words | want))
    return ([i["id"] for i in ranked], "library",
            f"{basis}; best take {ranked[0]['id']}" + (f" (fits: {', '.join(hit)})" if hit else ""))
def _is_date(ev: dict) -> bool:
    text = f"{ev.get('label') or ''} {ev.get('text_shown') or ''}".lower()
    return str(ev.get("from") or "").startswith("chip_") or bool(re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)) or any(
        m in text.split() for m in MONTHS)
def _map_spots(ev: dict, op: str, fps: float, words: set, scene_words: set, open_air: bool):
    at = int(ev.get("start_frame", 0))
    end = int(ev.get("end_frame") or at)
    if str(ev.get("cues") or "").lower() == "none":
        return [], [{"id": ev.get("id"), "op": op, "decision": "silent_by_design",
                     "why": "criterion 1: cues none, the line stands at once; nothing is seen drawn"}], []
    if op == "label" and _is_date(ev):
        need = [{"class": c, "status": "missing", "why": "a date is stamped or typed; no such take yet"} for c in DATE_CLASSES]
        return [{"kind": "foley", "what": op, "class": DATE_FALLBACK, "at_s": round(at / fps, 3), "distance": "close",
                 "decision": "sfx", "sync": "onset", "event_id": ev.get("id"),
                 "why": "criterion 2-3: a date chip is a period tag stamped onto the map, heard close; the library has no "
                        "stamp or typewriter take yet, so the paper of the tag (a UI click would be a modern sound)"}], [], need
    if op == "marker_travel":
        token = {str(ev.get("token") or "").lower()} | set(re.findall(r"[a-z]+", str(ev.get("label") or "").lower()))
        if token & set(ARMY_WORDS) or (words | scene_words) & set(ARMY_WORDS):
            return [{"kind": "ambience", "what": op, "class": "army_march", "at_s": round(at / fps, 3), "distance": "distant",
                     "decision": "sfx", "sync": "span", "dur_s": round(max(1, end - at) / fps, 3), "event_id": ev.get("id"),
                     "why": "criterion 2-3: the moving token is an army; a marching column makes a sound, heard far at a "
                            "map's scale"}], [], []
    if op == "counter":
        out = []
        s0, s1 = at / fps, max(at + 1, end) / fps
        for j in range(COUNTER_TICKS):
            u = 0.5 - 0.5 * math.cos(math.pi * (j + 1) / (COUNTER_TICKS + 2))
            out.append({"kind": "foley", "what": op, "class": "ov_tick", "at_s": round(s0 + (s1 - s0) * u, 3),
                        "distance": "close", "decision": "sfx", "sync": "onset", "event_id": f"{ev.get('id')}.tick{j + 1}",
                        "why": "criterion 1-2: the counter's digits roll and tick, spaced by its own ease (BP-192: ticks, "
                               "then a knock; never a riser)"})
        out.append({"kind": "foley", "what": op, "class": "ov_thud", "at_s": round(max(s0, s1 - COUNTER_KNOCK_LEAD_S), 3),
                    "distance": "close", "decision": "sfx", "sync": "onset", "event_id": f"{ev.get('id')}.knock",
                    "why": "criterion 1-2: the counter lands on its number: one knock (BP-192)"})
        return out, [], []
    return None
def choose_sound(events: list[dict], *, scene: dict | None = None, spine=None, open_air: bool = True, cold: bool = False,
                 prev_beds: list[str] | None = None, library_root=None, fps: float = 24.0,
                 map_view: dict | None = None) -> dict:
    from pathlib import Path
    from explainer_engine.episode import events as EV
    root = Path(library_root) if library_root else Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
    words = set(_words(spine))
    place = set(re.findall(r"[a-z]+", str((scene or {}).get("surroundings", "")).lower()))
    scene_words = {w for w in place | words if len(w) > 3}
    beds, spots, silent, needs = {}, [], [], []
    grouped = {}
    for ev in events:
        op = ev["op"]
        key = (op, int(ev.get("start_frame", 0)))
        if map_view is not None and key in grouped and str(ev.get("cues") or "").lower() != "none":
            silent.append({"id": ev.get("id"), "op": op, "decision": "silent_by_design",
                           "why": f"lands with {grouped[key]} on the same frame: one grouped sound (BP-192 max_at_once)"})
            continue
        grouped.setdefault(key, ev.get("id"))
        if map_view is not None:
            got = _map_spots(ev, op, fps, words, scene_words, open_air)
            if got is not None:
                spots.extend(got[0])
                silent.extend(got[1])
                needs.extend(got[2])
                continue
        if op in OWN_AUDIO:
            dec, cls, why = OWN_AUDIO[op]
        else:
            a = EV.default_audio(AV_OP.get(op, op), ev)
            dec, cls, why = a["decision"], a.get("class"), a.get("why") or "the AV contract's default for this action"
            if dec == "ambience_only":
                from explainer_engine.episode import sound_plan as SP
                cls = SP.AMBIENCE_OF_EFFECT.get(AV_OP.get(op, op))
        if dec == "ambience_only" and not cls:
            dec, why = "silent_by_design", f"{op} makes no sound of its own and names no bed"
        if dec in ("silent_by_design", "review_required"):
            silent.append({"id": ev.get("id"), "op": op, "decision": dec, "why": why})
            continue
        if cls == "wind" and not open_air:
            silent.append({"id": ev.get("id"), "op": op, "decision": "silent_by_design",
                           "why": "criterion 1: the place is not open to the sky, no wind is heard"})
            continue
        dist = _hear_distance(ev.get("area_pct", 100.0)) if dec == "ambience_only" and cls != "wind" else "medium"
        if dist is None:
            silent.append({"id": ev.get("id"), "op": op, "decision": "silent_by_design",
                           "why": f"criterion 3: {ev.get('area_pct')} % of the frame, too small and far to hear over the bed"})
            continue
        if int(ev.get("text", 0)) == 2 and dist != "close":
            dist = {"distant": "medium", "medium": "close"}[dist]
            why += "; criterion 4: the words name it, one step closer"
        if dec == "ambience_only":
            cur = beds.get(cls)
            order = ("distant", "medium", "close")
            if cur is None or order.index(dist) > order.index(cur["distance"]):
                beds[cls] = {"distance": dist, "why": f"{op} ({ev.get('id')}): {why}"}
            continue
        at = int(ev.get("start_frame", 0))
        spots.append({"kind": "spot" if EV.DEFAULTS.get(op, {}).get("decision") == "sfx" else "foley", "what": op,
                      "class": cls, "at_s": round(at / fps, 3), "distance": dist, "decision": dec,
                      "sync": EV.DEFAULTS.get(op, {}).get("sync", "onset"), "event_id": ev.get("id"),
                      "why": f"criterion 1-2: a visible {op} that sounds (BP-192); {why}"})
        if ev.get("end_frame") and spots[-1]["sync"] == "span":
            spots[-1]["dur_s"] = round((int(ev["end_frame"]) - at) / fps, 3)
    if map_view is not None:
        pins = [x for x in spots if x["class"] == "map_pin_set"]
        for x in pins[1:]:                    # BP-81: one emphasis cue a line; the later pulses are the wood tick
            x.update({"class": "map_arrive_click", "why": "the line's one thud is spent on its first pulse (BP-81); this pulse "
                                                          "is a wood tick; " + x["why"]})
        span = float(map_view.get("span_km") or 0)
        line = any(e["op"] == "front_line" for e in events)
        if line and 0 < span <= MURMUR_SPAN_KM:
            beds.setdefault("crowd_murmur", {"distance": "distant", "why": f"criterion 2-3: the front line seen at {span:g} km "
                                             "is men in trenches; waiting men are a far murmur at this scale (the map's bed)"})
        elif open_air and not beds:
            beds.setdefault("wind", {"distance": "distant", "why": f"criterion 2-3: a map is a wide view of open land "
                                     f"({span:g} km): its own bed is the land's far wind, never digital silence"})
    for cls in prev_beds or []:
        if cls not in beds and not (cls == "wind" and not open_air) and not (cold and cls in COLD_FORBIDS):
            beds[cls] = {"distance": "distant", "why": "criterion 5: the previous shot of the same place has it: the bed "
                                                         "continues, no jump"}
    out_events = []
    for cls, b in beds.items():
        if cold and cls in COLD_FORBIDS:
            silent.append({"id": cls, "op": cls, "decision": "silent_by_design", "why": "a frozen winter has no insects or birdsong"})
            continue
        ids, status, pwhy = _pick_take(cls, root, scene_words | set(BED_WORDS.get(cls, ())) | {b["distance"]})
        e = {"kind": "ambience", "what": cls, "class": cls, "at_s": 0.0, "distance": b["distance"], "decision": "ambience_only",
             "sync": "span", "why": b["why"], "library": {"status": status, "ids": ids[:3], "why": pwhy}}
        if status != "library":
            e["decision"] = "review_required"
            needs.append({"class": cls, "status": status})
        out_events.append(e)
    for s in spots:
        ids, status, pwhy = _pick_take(s["class"], root, scene_words | {s["distance"]})
        s["library"] = {"status": status, "ids": ids[:3], "why": pwhy}
        if status != "library":
            s["decision"] = "review_required"
            needs.append({"class": s["class"], "status": status})
        out_events.append(s)
    return {"events": out_events, "silent": silent, "needs": needs,
            "beds": sorted(beds), "coverage": "AMBIENCE_ONLY" if beds and not spots else
            "FOLEY_AND_AMBIENCE" if beds else "ACTION_FOCUSED" if spots else "MINIMAL_DESIGN"}
def sound_of_direction(d: dict, spine, frames: int, fps: float = 24.0, prev: dict | None = None, library_root=None) -> dict:
    living = {e["effects"][0]: e for e in (d.get("seen") or {}).get("living", []) if e.get("decision") != "skip"
              and e.get("effects")}
    evs = []
    for t in d.get("tracks", []):
        if t.get("track") == "audio":
            continue
        e = living.get(t.get("id"), {})
        start = (t.get("timing") or {}).get("start") or {}
        sf = 0
        if start.get("word"):
            try:
                sf = D.word_frame(spine, start["word"])
            except ValueError:
                sf = 0
        evs.append({"id": t.get("id") or t["op"], "op": t["op"], "area_pct": e.get("area_pct", 100.0),
                    "text": e.get("text", 0), "start_frame": sf, "end_frame": frames})
    prev_beds = (prev or {}).get("sound", {}).get("beds") if prev else None
    return choose_sound(evs, scene=d.get("scene"), spine=spine, open_air=open_sky(d), cold=is_cold(d, _words(spine)),
                        prev_beds=prev_beds, library_root=library_root, fps=fps)
def sound_of_map(shot: dict, script: dict, spine=None, fps: int = 24, prev: dict | None = None, library_root=None,
                 cold: bool = False, open_air: bool = True) -> dict:
    from explainer_engine.episode import events as EV
    acts = shot.get("actions") or []
    evs = []
    for e in EV.visual_events(shot, script, spine, fps):
        if e["source"] != "actions":
            continue
        a = acts[e["index"]] if e["index"] < len(acts) else {}
        evs.append({"id": a.get("event_id") or f"{shot.get('shot_id')}.A{e['index'] + 1}", "op": e["op"],
                    "start_frame": e["start_frame"], "end_frame": e["end_frame"], "text": 0,
                    **{k: a[k] for k in ("cues", "from", "label", "token") if a.get(k) is not None}})
    prev_beds = (prev or {}).get("beds") if prev else None
    return choose_sound(evs, scene=shot.get("scene") or {"surroundings": " ".join(str(x) for x in (
        shot.get("location_id"), shot.get("purpose")) if x)}, spine=spine, open_air=open_air, cold=cold,
        prev_beds=prev_beds, library_root=library_root, fps=fps, map_view=shot.get("map_view") or {})

def score_camera_candidates(candidates: list[str], prev_op: str | None = None, recent_non_map: list[str] | None = None,
                            max_pushes: int = 2, window_shots: int = 5, story_locked: bool = False) -> list[dict]:
    """A2.5: score candidate camera operations using soft variety penalties instead of hard FAIL rules.
    When ``story_locked=True`` (explicit storytelling override), the preferred move receives a +0.60 story bonus that
    outweighs the repeat/push-density penalties; otherwise variety penalties rank varied moves ahead of repeats."""
    recent = list(recent_non_map or [])[-(max(1, window_shots - 1)):]
    pushes = sum(1 for m in recent if m in ("push", "push_in"))
    rows = []
    seen = set()
    for idx, op in enumerate(candidates):
        if op in seen:
            continue
        seen.add(op)
        base = 1.0 - 0.04 * idx + (0.60 if (idx == 0 and story_locked) else 0.0)
        rep_pen = 0.35 if (prev_op is not None and op == prev_op) else 0.0
        push_pen = 0.40 if (op in ("push", "push_in") and pushes >= max_pushes) else 0.0
        rows.append({
            "op": op,
            "base_score": round(base, 4),
            "repeat_penalty": round(rep_pen, 4),
            "push_density_penalty": round(push_pen, 4),
            "score": round(base - rep_pen - push_pen, 4),
        })
    rows.sort(key=lambda r: (-r["score"], candidates.index(r["op"])))
    return rows


def sequence_variety_score(directions: list[dict]) -> dict:
    return D.sequence_variety_score(directions)


def sequence_variety_rows(directions: list[dict]) -> list[dict]:
    return D.sequence_variety_rows(directions)



_INTERIOR_WORDS = re.compile(
    r"\b(dugout|bunker|interior|indoor|indoors|underground|cellar|cabin|room|hut|church|tent|shelter|tunnel)\b",
    re.I,
)
_SKY_ONLY_KINDS = frozenset({"sky", "cloud", "sun", "stars", "snow", "rain"})
_IM_EFFECT_TO_KIND = {
    "mist": ("mist", "mist_bank", [0.5, 0.62], 25.0),
    "smoke_drift": ("smoke", "smoke_plume", [0.55, 0.52], 12.0),
    "smoke": ("smoke", "smoke_plume", [0.55, 0.52], 12.0),
    "dust": ("dust", "dust_motes", [0.5, 0.48], 15.0),
    "water_shimmer": ("water", "water_surface", [0.5, 0.78], 15.0),
    "foliage_sway": ("plants", "foliage", [0.5, 0.45], 12.0),
    "wire_sway": ("wire", "barbed_wire", [0.5, 0.68], 8.0),
    "cloth_flap": ("cloth", "cloth_banner", [0.5, 0.4], 8.0),
    "subject_sway": ("body", "subject_pose", [0.5, 0.55], 15.0),
    "cloud_drift": ("sky", "sky_canopy", [0.5, 0.18], 25.0),
    "sun_shaft_drift": ("sun", "sun", [0.5, 0.22], 20.0),
    "sun_shaft": ("sun", "sun", [0.5, 0.22], 20.0),
    "sun_glint": ("sun", "sun", [0.5, 0.22], 20.0),
    "stars": ("stars", "night_stars", [0.5, 0.15], 15.0),
    "glint": ("ice", "frost_glint", [0.5, 0.65], 8.0),
}


def _strip_sky_words(text: str) -> str:
    sky_words = {w for k in _SKY_ONLY_KINDS for w in D.LIVING_WORDS.get(k, ())}
    tokens = str(text or "").split()
    kept = [t for t in tokens if D._norm(t) not in sky_words]
    return " ".join(kept).strip()


def build_shot_direction_from_script(shot: dict, script: dict, *, layers: dict | None = None, spine: list[dict] | None = None,
                                     fps: float = 24.0, prev_direction: dict | None = None, next_shot: dict | None = None,
                                     episode_state: dict | None = None, picture_sha256: str | None = None,
                                     library_root=None) -> dict:
    """A2.1 & C1: construct and direct a ``shot_direction/1-draft`` document for ``shot`` strictly from evidence:
    the layers manifest (objects, lights, sky/ground masks, geometry), the shot's own script fields (``seen``,
    ``lighting_and_time``, ``screen_composition``, ``action_start_state``, ``motion_imitation``, location interior/exterior,
    and exterior scene weather per BP-200/D-132), and narration only for kinds also present in the picture. Never invents
    default living elements or assumes ``sky_open = True``. When evidence is insufficient, marks ``needs_eye = True`` and
    ``status = 'REVIEW'``."""
    sid = str(shot.get("shot_id") or "shot")
    dur_s = float(shot.get("target_duration_seconds") or shot.get("duration_sec") or 3.0)
    frames = int(shot.get("total_frames") or shot.get("frames") or max(1, int(round(dur_s * fps))))
    man = (layers.get("manifest") if isinstance(layers, dict) else None) or (
        shot.get("manifest") if isinstance(shot.get("manifest"), dict) else None
    ) or {}
    seen_in = shot.get("seen") if isinstance(shot.get("seen"), dict) else {}
    pic_sha = picture_sha256 or man.get("picture_sha256") or shot.get("picture_sha256") or ""

    lines_by = {ln.get("line_id"): ln for ln in (script.get("audio_lines") or []) if ln.get("line_id")}
    narration = " ".join(str((lines_by.get(lid) or {}).get("text") or "") for lid in (shot.get("audio_line_ids") or [])).strip()
    if not narration:
        narration = str(shot.get("narration_excerpt") or shot.get("text") or "")

    locs_by = {
        loc.get("location_id"): loc
        for loc in ((script.get("world_bible") or {}).get("locations") or [])
        if isinstance(loc, dict) and loc.get("location_id")
    }
    loc = locs_by.get(shot.get("location_id") or shot.get("place")) or {}
    loc_room = str(((loc.get("ambience_bed") or {}).get("room")) or "").lower()

    # 1. Objects and sky mask from layers manifest + shot.seen
    objs: list[dict] = []
    sky_mask_obj: dict | None = None
    for o in list((man.get("masks") or {}).get("objects") or []) + list(seen_in.get("objects") or []):
        if not isinstance(o, dict) or not o.get("id"):
            continue
        oid = str(o["id"])
        owhat = str(o.get("what") or o.get("prompt") or oid)
        onames = [str(n) for n in (o.get("names") or [oid])]
        tokens_o = {D._norm(t) for t in ([oid, owhat] + onames)}
        if tokens_o & {"sky", "cloud", "clouds"} and sky_mask_obj is None:
            sky_mask_obj = o
        entry_o = {
            "id": oid,
            "what": owhat,
            "layer": bool(o.get("layer", True)),
            "names": onames,
            "where": list(o.get("where") or _centre(o)),
        }
        if o.get("box"):
            entry_o["box"] = list(o["box"])
        if o.get("points"):
            entry_o["points"] = list(o["points"])
        if not any(x["id"] == oid for x in objs):
            objs.append(entry_o)

    sky_block = man.get("sky") if isinstance(man.get("sky"), dict) else None
    geom_sky_pct = float(
        (man.get("geometry") or {}).get("sky_area_pct")
        or (sky_block or {}).get("area_pct")
        or (sky_mask_obj or {}).get("area_pct")
        or 0.0
    )
    has_sky_mask = bool(
        sky_mask_obj is not None
        or (sky_block and (sky_block.get("file") or float(sky_block.get("area_pct") or 0.0) > 0.0))
        or geom_sky_pct >= 5.0
    )

    # 2. Interior vs exterior & sky_open derivation from evidence (never assumed True)
    im_list = [m for m in (shot.get("motion_imitation") or []) if isinstance(m, dict)]
    im_effects = [str(m.get("effect") or "").lower() for m in im_list]
    has_sky_imitation = any(
        e in ("cloud_drift", "sun_shaft", "sun_shaft_drift", "sun_glint", "stars", "snow", "rain", "spindrift")
        for e in im_effects
    )
    light_time = str(shot.get("lighting_and_time") or "")
    sc_comp = shot.get("screen_composition") if isinstance(shot.get("screen_composition"), dict) else {}
    sc_fg = str(sc_comp.get("foreground") or "")
    sc_mg = str(sc_comp.get("midground") or "")
    sc_bg = str(sc_comp.get("background") or "")
    act_start = str(shot.get("action_start_state") or "")
    act_end = str(shot.get("action_end_state") or "")

    place_probe = " ".join(
        str(x)
        for x in (
            shot.get("location_id"),
            loc.get("name"),
            (shot.get("scene") or {}).get("surroundings") if isinstance(shot.get("scene"), dict) else "",
            light_time,
            act_start,
            sc_fg,
            sc_mg,
        )
        if x
    )
    has_explicit_interior = bool(loc_room in ("indoor", "interior", "dugout") or _INTERIOR_WORDS.search(place_probe))
    is_local_lamp_only = (
        bool(re.search(r"\b(brazier|candle|candlelight|lantern|oil\s+lamp)\b", light_time, re.I))
        and not has_sky_imitation
        and not has_sky_mask
        and not bool(re.search(r"\b(sunrise|sunset|morning\s+sun|afternoon\s+sun|moonlit|snow|fog|dawn)\b", light_time, re.I))
    )
    is_interior = has_explicit_interior or is_local_lamp_only

    if isinstance(seen_in.get("sky_open"), bool):
        sky_open = seen_in["sky_open"]
    elif has_explicit_interior:
        sky_open = False
    elif has_sky_mask:
        sky_open = True
    elif is_interior:
        sky_open = False
    elif has_sky_imitation:
        sky_open = True
    else:
        probe_sky = f"{light_time} {act_start}" or str(shot.get("narration_excerpt") or "")
        sky_open = bool(
            not is_interior
            and re.search(
                r"\b(sunrise|sunset|sun\b|dawn|moonlit|stars?|snow|fog|mist|sky|trench)\b",
                probe_sky,
                re.I,
            )
            and (not man or not (man.get("lights") or (man.get("geometry") or {}).get("sky_area_pct") == 0.0))
        )

    # 3. Lights from manifest + shot.seen + visual script fields + motion_imitation
    lights: list[dict] = []
    for li in list(man.get("lights") or []) + list(seen_in.get("lights") or []):
        if isinstance(li, dict) and li.get("id"):
            lights.append({
                "id": str(li["id"]),
                "kind": str(li.get("kind") or "glow"),
                "point": list(li.get("point") or [0.5, 0.35]),
                "radius": float(li.get("radius", 0.04)),
            })

    vis_fields_text = " ".join(x for x in (seen_in.get("what"), light_time, act_start, act_end, sc_fg, sc_mg, sc_bg if sky_open else _strip_sky_words(sc_bg)) if x)
    if not vis_fields_text.strip() and not man.get("lights"):
        fallback_vis = str(shot.get("narration_excerpt") or shot.get("narrative_purpose") or "")
        vis_fields_text = fallback_vis if sky_open else _strip_sky_words(fallback_vis)
    vis_low = vis_fields_text.lower()

    for o in objs:
        otoks = {D._norm(t) for t in ([o["id"], o["what"]] + list(o.get("names") or []))}
        if otoks & {"brazier", "fire", "campfire", "bonfire", "torch", "flame"} and not any(l["kind"] == "fire" for l in lights):
            lid = "brazier" if "brazier" in otoks or "brazier" in vis_low else o["id"]
            lights.append({"id": lid, "kind": "fire", "point": list(o.get("where") or [0.55, 0.65]), "radius": 0.04})
        elif otoks & {"candle", "candles", "lantern", "lamp"} and not any(l["kind"] in ("candle", "glow") for l in lights):
            lights.append({"id": o["id"], "kind": "candle", "point": list(o.get("where") or [0.5, 0.48]), "radius": 0.04})
        elif sky_open and (otoks & {"sun", "sunrise", "sunset"}) and not any(l["kind"] == "sun" for l in lights):
            lights.append({"id": o["id"], "kind": "sun", "point": list(o.get("where") or [0.5, 0.22]), "radius": 0.06})

    fire_im = next((m for m in im_list if str(m.get("effect") or "").lower() in ("fire_flicker", "fire", "embers")), None)
    fire_region = (fire_im or {}).get("region") if isinstance((fire_im or {}).get("region"), (list, tuple)) and len((fire_im or {}).get("region")) == 4 else None
    if (fire_im is not None or re.search(r"\b(brazier|fire|campfire|bonfire|torch|flames?)\b", vis_low)) and not any(l["kind"] == "fire" for l in lights):
        if fire_region is not None:
            rx0, ry0, rx1, ry1 = (float(v) for v in fire_region)
            pt = [round(0.5 * (rx0 + rx1), 4), round(0.5 * (ry0 + ry1), 4)]
            rad = round(max(0.03, 0.25 * min(rx1 - rx0, ry1 - ry0)), 3)
        else:
            pt, rad = [0.55, 0.65], 0.04
        lid = "brazier" if "brazier" in vis_low else "fire_light"
        lights.append({"id": lid, "kind": "fire", "point": pt, "radius": rad})

    if (any(e == "candle" for e in im_effects) or re.search(r"\b(candles?|candlelight|lanterns?|lamps?)\b", vis_low)) and not any(l["kind"] == "candle" for l in lights):
        lid = "candle" if "candle" in vis_low else "lantern"
        lights.append({"id": lid, "kind": "candle", "point": [0.5, 0.48], "radius": 0.04})

    if sky_open and (any(e in ("sun_shaft_drift", "sun_shaft", "sun_glint") for e in im_effects) or re.search(r"\b(sun|sunrise|sunset|dawn|daybreak|sunlight|sunbeams?)\b", vis_low)) and not any(l["kind"] == "sun" for l in lights):
        lights.append({"id": "sun", "kind": "sun", "point": [0.5, 0.22], "radius": 0.06})

    # 4. Living elements strictly from evidence (no hardcoded mist_bank / dust_motes / sky_canopy)
    living_seed: list[dict] = []
    have_kinds: set[str] = set()

    for raw_e in (seen_in.get("living") or []):
        if not isinstance(raw_e, dict) or not raw_e.get("kind"):
            continue
        k = str(raw_e["kind"])
        if not sky_open and k in _SKY_ONLY_KINDS:
            continue
        ne = dict(raw_e)
        ne.setdefault("id", f"seen_{k}")
        ne.setdefault("where", _centre(ne))
        ne.setdefault("area_pct", 12.0)
        living_seed.append(ne)
        have_kinds.add(k)

    for li in lights:
        lkind = li["kind"] if li["kind"] in ("fire", "candle", "sun") else ("fire" if "brazier" in li["id"] or "fire" in li["id"] else "candle")
        if not sky_open and lkind in _SKY_ONLY_KINDS:
            continue
        if lkind not in have_kinds:
            area = 4.0
            box = None
            if lkind == "fire" and fire_region is not None:
                rx0, ry0, rx1, ry1 = (float(v) for v in fire_region)
                area = round(max(2.0, (rx1 - rx0) * (ry1 - ry0) * 100.0), 2)
                box = [round(rx0, 4), round(ry0, 4), round(rx1, 4), round(ry1, 4)]
            elif lkind == "sun":
                area = 20.0
            elif lkind == "candle":
                area = 2.5
            le = {
                "id": li["id"],
                "kind": lkind,
                "where": list(li["point"]),
                "area_pct": area,
                "lights": [li["id"]],
                "names": ["brazier", "fire"] if ("brazier" in li["id"] or "brazier" in vis_low) and lkind == "fire" else [lkind],
            }
            if box is not None:
                le["box"] = box
            living_seed.append(le)
            have_kinds.add(lkind)

    if sky_open and has_sky_mask and "sky" not in have_kinds:
        sky_entry = {
            "id": str((sky_mask_obj or {}).get("id") or "sky_canopy"),
            "kind": "sky",
            "where": list((sky_mask_obj or {}).get("where") or [0.5, 0.18]),
            "area_pct": max(10.0, geom_sky_pct or 25.0),
        }
        if sky_mask_obj and sky_mask_obj.get("id"):
            sky_entry["mask"] = str(sky_mask_obj["id"])
        living_seed.append(sky_entry)
        have_kinds.add("sky")

    for m in im_list:
        eff = str(m.get("effect") or "").lower()
        if eff not in _IM_EFFECT_TO_KIND:
            continue
        k_im, def_id, def_where, def_area = _IM_EFFECT_TO_KIND[eff]
        if not sky_open and k_im in _SKY_ONLY_KINDS:
            continue
        if k_im in have_kinds:
            continue
        reg = m.get("region") if isinstance(m.get("region"), (list, tuple)) and len(m.get("region")) == 4 else None
        where_im = [round(0.5 * (float(reg[0]) + float(reg[2])), 4), round(0.5 * (float(reg[1]) + float(reg[3])), 4)] if reg else list(def_where)
        area_im = round(max(2.0, (float(reg[2]) - float(reg[0])) * (float(reg[3]) - float(reg[1])) * 100.0), 2) if reg else def_area
        item_im: dict = {"id": def_id, "kind": k_im, "where": where_im, "area_pct": area_im}
        if reg is not None:
            item_im["box"] = [round(float(v), 4) for v in reg]
        if k_im in ("sun", "fire", "candle"):
            match_lights = [l["id"] for l in lights if l["kind"] == k_im]
            if match_lights:
                item_im["lights"] = match_lights
        living_seed.append(item_im)
        have_kinds.add(k_im)

    # Evidence from manifest object masks & explicit visual fields (narration only for kinds also in the picture)
    pic_kinds = set(D.kinds_named(vis_fields_text)) | {
        k for o in objs for k in D.kinds_named(" ".join([o["id"], o["what"]] + list(o.get("names") or [])))
    }
    if not sky_open:
        pic_kinds -= set(_SKY_ONLY_KINDS)
    pic_kinds.discard("wind")

    narr_words = [w.get("word", "") for w in (spine or [])]
    narr_kinds = D.kinds_named(narration) | D.kinds_named(narr_words)
    evidenced_kinds = pic_kinds | (narr_kinds & pic_kinds)
    for k_vis in sorted(evidenced_kinds):
        if k_vis in have_kinds or k_vis not in VARIANTS:
            continue
        if k_vis == "wire" and not any("wire" in o["id"] for o in objs):
            living_seed.append({"id": "barbed_wire", "kind": "wire", "where": [0.5, 0.68], "area_pct": 4.0, "thin": True})
            have_kinds.add("wire")
            continue
        extra_li: dict = {
            "id": f"seen_{k_vis}",
            "kind": k_vis,
            "where": [0.5, 0.22 if k_vis in ("sky", "cloud", "sun", "stars") else 0.58],
            "area_pct": 22.0 if k_vis in ("sky", "cloud", "sun", "mist") else 10.0,
        }
        if k_vis in ("sun", "fire", "candle"):
            match_lights = [l["id"] for l in lights if l["kind"] == k_vis]
            if match_lights:
                extra_li["lights"] = match_lights
        living_seed.append(extra_li)
        have_kinds.add(k_vis)

    # 5. Scene weather & surroundings from evidence (never 'open field')
    scene_in = shot.get("scene") if isinstance(shot.get("scene"), dict) else {}
    raw_weather = list(scene_in.get("weather") or [])
    if sky_open and "snow" in (narr_kinds | D.kinds_named(light_time) | D.kinds_named(sc_fg)) and not raw_weather:
        raw_weather = ["snow"]
    weather_list = raw_weather if sky_open else []

    raw_surr = str(scene_in.get("surroundings") or light_time or loc.get("name") or "").strip()
    if not sky_open:
        raw_surr = _strip_sky_words(raw_surr)
    for k_s in list(D.kinds_named(raw_surr)):
        if k_s not in have_kinds and k_s not in D.kinds_named(" ".join(weather_list)):
            for w_tok in D.LIVING_WORDS.get(k_s, ()):
                raw_surr = re.sub(rf"\b{re.escape(w_tok)}\b", "", raw_surr, flags=re.I)
    raw_surr = re.sub(r"\s+", " ", raw_surr).strip(" ,;-")

    what_raw = str(
        seen_in.get("what")
        or "; ".join(x for x in (act_start, sc_fg, sc_mg, sc_bg if sky_open else _strip_sky_words(sc_bg), light_time) if x)
        or ", ".join(o["what"] for o in objs)
        or shot.get("narrative_purpose")
        or sid
    ).strip()
    if not sky_open:
        what_raw = _strip_sky_words(what_raw)
    for k_w in list(D.kinds_named(what_raw)):
        if k_w not in have_kinds and k_w not in D.kinds_named(" ".join(weather_list)):
            for w_tok in D.LIVING_WORDS.get(k_w, ()):
                what_raw = re.sub(rf"\b{re.escape(w_tok)}\b", "", what_raw, flags=re.I)
    what_str = re.sub(r"\s+", " ", what_raw).strip(" ,;-") or sid

    base_doc = {
        "schema": D.SCHEMA,
        "shot_id": sid,
        "kind": "map" if shot.get("route") == "map_action" else "photo",
        "route": shot.get("route", "still_25d"),
        "picture_sha256": pic_sha,
        "intent": shot.get("intent") or "intended",
        "narration": narration,
        "scene": {"weather": weather_list, "surroundings": raw_surr},
        "seen": {
            "what": what_str,
            "sky_open": sky_open,
            "objects": objs,
            "lights": lights,
            "living": living_seed,
        },
    }
    out = direct(base_doc, spine or [], frames, fps, prev_direction=prev_direction, next_shot=next_shot,
                 episode_state=episode_state, manifest=man, library_root=library_root)
    fx_tracks = [t for t in out.get("tracks", []) if t.get("track") not in ("camera", "audio")]
    fams_dir = {D.FAMILY_OF[t["op"]] for t in fx_tracks if t.get("op") in D.FAMILY_OF}
    lp_fails = [n for n in ((out.get("choice") or {}).get("notes") or []) if str(n).startswith("FAIL")]
    if not fx_tracks or lp_fails or len(fams_dir) < D.ALIVE_MIN:
        out["needs_eye"] = True
        out["status"] = "REVIEW"
        out["needs_eye_reason"] = (
            "no living element or light evidence in layers/script"
            if not fx_tracks
            else f"insufficient visual evidence for full LP-08 balance without fabricating elements ({'; '.join(lp_fails)})"
        )
    return out
