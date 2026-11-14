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
BASE_RATE = 0.015                     # a base push or pull, scale per second (the middle of BP-21's range; house default)
SNAP_S = float(SR.T("BP-197", "snap_s_max"))
ACCENT_S = 1.25                       # an accent's ease-out: its 10-90 % rise is about half of this, inside SNAP_S
ACCENT_LEAD_S = 1.0                   # an accent needs this much calm before it: a word earlier than this is carried by the
                                      # base move instead (eye review of C4A 2026-11-14: S05_SH016 jumped 8.7 % in 1.2 s, then froze)
TRUCK_STRENGTH = 2.0                  # a truck on a word: the people at mid depth travel ~5-8 % of the width (eye review: S05_SH020's
                                      # truck at strength 1 read as no lateral move)
KEEP_LIGHTS = ("fire", "candle", "glow", "sun_glint", "sun_shaft")   # their lights stay in frame when the people allow (soft)
PUSH_SCALE = 0.06                     # directed25d's zoom of a push at strength 1 (layers25d.PUSH_SCALE)
FACE_SCORE = 0.8                      # YuNet faces below this are false hits on drawn pictures (the six P1 photos: 0.5-0.75)
FACE_CLOSE = 0.02                     # a face box over this share of the frame is near the lens: only the far flakes fall
FLAKE_DARK_LUMA = 0.7                 # flakes read where the picture is darker than this (0..1)
FLAKE_DARK_MIN = 0.3                  # ... and at least this share of the frame is that dark
TARGET_PART = 0.2                     # an element within this distance of the shot's focus is in focus (2), twice it 1

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
    """Faces of living people: YuNet rows (``[x, y, w, h, ..., score]`` in pixels; landmarks 10..13 the mouth corners when
    present) above ``FACE_SCORE``, outside every ``depicted`` box (a photo or poster in the picture)."""
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


def candidates(d: dict, spine, faces: list[dict], duration_s: float) -> list[dict]:
    """Every effect the seen elements allow, scored (LP-04) with the reason of each score part."""
    seen = d.get("seen") or {}
    words = _words(spine)
    scene = d.get("scene") or {}
    scene_words = re.findall(r"[a-zA-Z']+", str(scene.get("surroundings", "")))
    focus, focus_why = _focus_point(d, words, faces)
    cold, sky = is_cold(d, words), open_sky(d)
    lights = seen.get("lights", [])
    living = seen.get("living", [])
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
    if cold and faces and not any(e.get("kind") == "breath" for e in seen.get("living", [])):
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
    if kind == "sun" and not near:
        near = [li for li in lights if li.get("kind") == "sun"]
    return [li["id"] for li in near]


def decide_weather(d: dict, spine, picture=None, faces: list[dict] | None = None, prev: dict | None = None) -> list[dict]:
    """Each weather word of the scene let in or left out by the five criteria in order; ``prev`` is the previous shot's
    direction of the same scene (its ``weather`` records)."""
    words = _words(spine)
    out = []
    prev_in = {r.get("weather"): r.get("in") for r in (prev or {}).get("weather") or []}
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
    """CT-08 over a sequence: the same weather word in and then out (or back) between neighbouring shots of one scene,
    where the later shot's decision is not a reason of the place itself (open sky, light, picture), FAILs."""
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


def choose_camera(d: dict, spine, frames: int, fps: float, faces: list[dict], chosen_effects: set) -> tuple[list, list]:
    """Camera tracks and their reasons: accents on the words that name parts, a base move before them, a breathing hand."""
    seen = d.get("seen") or {}
    words = spine or []
    parts = D._named_parts(d)
    objs = {o["id"]: o for o in seen.get("objects", [])}
    tracks, why = [], []
    targets, done = [], set()
    livs = {e["id"]: e for e in seen.get("living", [])}
    for w in words:
        pid = parts.get(D._norm(w.get("word", "")))
        if pid and (pid in objs or pid in livs) and pid not in done:
            done.add(pid)
            targets.append((D._norm(w["word"]), int(w.get("frame", w.get("start_frame", 0))), pid,
                            _centre(objs.get(pid) or livs[pid])))
    dur = frames / fps
    early = targets[0] if targets and targets[0][1] < ACCENT_LEAD_S * fps else None
    if early:
        targets = targets[1:]
    first = targets[0][1] if targets else frames
    if d.get("intent") == "still_by_design":
        tracks.append(_cam("handheld", 0.3))
        why.append("still by design: the camera only breathes (the owner's 12:37 card 3)")
        return tracks, why
    if first >= 0.5 * fps:
        base_s = first / fps
        people = bool(faces) and d.get("people_mid_or_close")
        sky_top = any(e.get("kind") in ("sky", "sun", "cloud") and _centre(e)[1] < 0.4 for e in seen.get("living", []))
        if early:
            op, tgt, reason = ("push", _aim(early[2], early[3], objs), f"'{early[0]}' names {early[2]} in the first "
                               f"{ACCENT_LEAD_S:g} s, too early for an accent: the base move leans towards it instead")
        elif "light_fade" in chosen_effects:
            op, tgt, reason = "pull", None, "the words say the light is going: the camera pulls back as it fades"
        elif not people and sky_top and not targets:
            op, tgt, reason = "crane", None, "an open landscape with the sky above and no named part: the camera rises to it"
        elif faces:
            fx_ = [sum(f["mouth"][0] for f in faces) / len(faces), sum(f["mouth"][1] for f in faces) / len(faces)]
            op, tgt, reason = "push", {"point": [round(fx_[0], 3), round(fx_[1], 3)]}, "people in the frame: the camera leans in"
        else:
            op, tgt, reason = "push", {"point": [0.5, 0.45]}, "no named part and no people: a slow push into the picture"
        end = {"word": targets[0][0]} if targets else {"frac": 1.0}
        if op == "crane":
            t = _cam("crane", 1.0, end=end, direction="up", ease="ease_out",
                     validate={"measure": "shift_y_pct", "direction": "up", "perceptible": True})
            reason += f" (crane over {base_s:.1f} s)"
        else:
            rate = RATE_MIN if targets else BASE_RATE           # a slow approach makes the accent that follows read
            s = _move_strength(rate, base_s)
            t = _cam(op, s, end=end, target=tgt, ease="linear", validate={"measure": "scale"})
            reason += (f" ({rate * 100:g} %/s over {base_s:.1f} s, BP-21"
                       + ("; the slowest rate, so the accent on the word stands out)" if targets else ")"))
        tracks.append(t)
        why.append(reason)
    prev = None
    for word, wf, pid, c in targets[:D.SEGMENTS_MAX - len(tracks)]:
        end = {"frame": min(frames - 1, wf + int(round(ACCENT_S * fps)))}
        if prev is not None and abs(c[0] - prev[0]) > 0.2:
            t = _cam("truck", TRUCK_STRENGTH, start={"word": word}, end=end, target=_aim(pid, c, objs), ease="ease_out",
                     direction="right" if c[0] > prev[0] else "left", validate={"measure": "shift_x_pct"})
            why.append(f"'{word}' names {pid}, across the frame from the last target: a truck to it on the word (accent)")
        else:
            t = _cam("push", 1.0, start={"word": word}, end=end, target=_aim(pid, c, objs),
                     ease="ease_out", validate={"measure": "scale"})
            why.append(f"'{word}' names {pid}: a snap push to it on the word (accent, rise inside {SNAP_S:g} s)")
        tracks.append(t)
        prev = c
    if targets or d.get("people_mid_or_close"):
        tracks.append(_cam("handheld", 0.3))
        why.append("a breathing hand so the camera never fully stops after the accent (the owner's 12:37 card 3)")
    return tracks, why


def keep_in_frame(faces: list[dict], tracks: list[dict]) -> list[dict]:
    """The safe zone the renderer holds (the owner, 2026-11-14 13:29 UTC: "people are cut in some frames"): every live
    person, and softly the lights the chosen effects animate (a candle pushed out of frame wastes its effect)."""
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


def _track(r: dict, d: dict, weather_layers=None) -> dict:
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
        e = next((x for x in (d.get("seen") or {}).get("living", []) if x["id"] == r["of"]), {})
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
           library_root=None) -> dict:
    """The whole choice for one shot: a copy of ``d`` with ``seen.living`` decided, ``weather``, the tracks, the sound
    (``sound``: beds and events from the library, the silent ones and the needs; one audio track that names them) and
    ``choice`` (every reason)."""
    import copy
    out = copy.deepcopy(d)
    seen = out.setdefault("seen", {})
    size = (picture.shape[1], picture.shape[0]) if picture is not None else (1, 1)
    faces = live_faces(faces_px, size, seen.get("depicted", [])) if faces_px is not None else []
    dur = frames / fps
    weather = decide_weather(out, spine, picture, faces, prev)
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
        base = {"id": r["id"], "kind": r["kind"], "where": r["where"], **{k: r[k] for k in ("area_pct", "text", "focus",
                                                                                         "quality", "cost")}}
        if r.get("body_motion"):
            base["body_motion"] = True
        if r["id"] in picked:
            t = _track(r, out, layers)
            tracks.append(t)
            tier = picked[r["id"]].get("tier", "always on (LP-06)")
            living.append({**base, "decision": r["decision"], "effects": [t["id"]],
                           "why": f"{tier}: {r['why_score']}"})
        else:
            why = r.get("skip_why")
            if not why:
                s = skipped.get(r["id"], {})
                tier = s.get("tier", "")
                why = {"SKIP_DOT": "LP-03: a dot in the frame", "SKIP_QUALITY": "LP-05: it cannot move cleanly",
                       "SKIP_LOW": "LP-04: score too low", "LTX": "LP-02: body motion, LTX's work",
                       "FORBIDDEN": "LP-01: it contradicts the words"}.get(tier, f"LP-07: the cap of {p['cap']} is taken "
                                                                              f"by higher scores ({tier})")
                why += f" (score {s.get('score', LV.score(r))}; {r['why_score']})"
            living.append({**base, "decision": "skip", "why": why})
    cams, cam_why = choose_camera(out, spine, frames, fps, faces, {t["op"] for t in tracks})
    out["keep_in_frame"] = keep_in_frame(faces, tracks)
    seen["living"] = living
    out["tracks"] = cams + tracks
    snd = sound_of_direction(out, spine, frames, fps, prev, library_root)
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
                     "sound": {"beds": snd["beds"], "coverage": snd["coverage"], "silent": snd["silent"], "needs": snd["needs"]}}
    return out


# --- the sound: the same director, the same criteria (the owner, 2026-11-14 13:13 UTC, message
# cmsg_01Hnu5zB86sjUj5GtTgaUkPWX1nj38fCbSqH5mWzZKXzHj: "after seeing the photo the director decides not only the motion but
# the audio too, by the same criteria, on the maps too") ------------------------------------------------------------------
# the renderer's ops -> the AV contract's op names (episode/events.DEFAULTS), where they differ
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
}
# a bed class -> words of the takes that fit a place (preferred when the take's own words carry them)
BED_WORDS = {"wind": ("open", "land", "field", "cold", "winter", "plain"),
             "fire": ("campfire", "bonfire", "brazier", "crackle", "crackles")}
COLD_FORBIDS = ("crickets", "night_insects", "birds", "seabirds")     # no insects or birdsong in a frozen winter


def _hear_distance(area_pct: float) -> str | None:
    """How a sounding element of this share of the frame is heard: None (too small and far to hear over the bed)."""
    a = float(area_pct)
    return None if a < 0.5 else "distant" if a < 2 else "medium" if a < 5 else "close"


# Maps (the owner, 2026-11-14 13:13 UTC: the director decides the sound on maps too; criteria from the clips lane's map test,
# map_sound_criteria/README.md). Engineering defaults; BP-192 owns "a counter = ticks and a final knock".
DATE_CLASSES = ("date_stamp", "typewriter_key")    # a date chip is stamped or typed; the library has neither yet -> needs
DATE_FALLBACK = "ov_slide"                          # ... until then the period paper foley of a tag laid on the map
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december")
ARMY_WORDS = ("army", "armies", "troops", "soldiers", "march", "marching", "column", "regiment", "division", "corps", "war",
              "front")
COUNTER_TICKS = 9                                   # ticks while the digits roll, spaced by the counter's own ease
COUNTER_KNOCK_LEAD_S = 0.12                         # the knock lands this long before the counter stops
MURMUR_SPAN_KM = 400                                # a front line seen at this scale or closer is men in trenches: a far murmur
MODERN_WORDS = ("garage", "concrete", "car", "cars", "traffic", "engine", "motel", "pool", "city", "office", "electric")


def _pick_take(cls: str, root, words: set) -> tuple[list[str], str, str]:
    """(ids best first, status library|placeholder|missing, why) from the one library (sound_plan's matcher). A take is
    ranked by the words of what the class must sound like (``BED_WORDS``, twice), then the place's words; a take whose
    words belong to a later world (a garage, a motel pool) drops to the end."""
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
    """The map criteria beyond the AV contract's defaults: ``None`` when they do not apply, else (spots, silent, needs)."""
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
    """The sound of one shot from its VISIBLE events (a 2.5D effect or camera move, or a map action: ``op``, ``id``,
    ``area_pct``, ``start_frame``/``end_frame``, ``text``), by the visual criteria in the same order: (1) only what is seen
    or authored sounds (words never add a sound, BP-192 / AV-07); (2) does it make a sound in nature (light, a candle, a
    breath: no); (3) is it heard at its size and distance; (4) the words name it: it comes one step closer; (5) the
    neighbours: the previous shot's bed of the same place continues. Every visible action that sounds gets its own event
    (BP-192); a bed the place carries plays under the whole shot. Returns events in the production script's
    ``sound_events`` form, the silent ones with their reason and the library ``needs``."""
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
    """The 2.5D shot's visible events (its chosen effect tracks with their elements' share and words, and its camera moves)
    handed to ``choose_sound``."""
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
    """A map shot's sound by the same chooser: its actions as visible events (``episode.events.visual_events``) with the
    fields the map criteria read (``cues``, ``from``, ``label``, ``token``), the view's scale from ``map_view``."""
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
