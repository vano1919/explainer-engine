"""The living-photo balance of a photo shot (Fable's LIVING_PHOTO_RULES of 2026-11-14, LP-01..LP-12, BP-200).

The director's inventory (``seen.living``, BP-196) says WHAT in the picture can move; this module says HOW MANY of them
move and which first, so a shot is neither frozen nor a busy screensaver:

- LP-01 an effect that contradicts the words is forbidden; LP-02 a body that must move (lips, hands, a turned head) is not
  2.5D work: the element is routed to LTX; LP-03 an element under ``dot_pct`` of the frame is a dot and gets no effect of
  its own unless it is groupable (distant fires, stars, glints: one group effect); LP-05 an element that cannot be cut out
  cleanly (quality 0) is skipped;
- LP-04 the score: ``w_text x text + scale + focus + quality + cost`` (each 0..2, scale 0..3 by the share of the frame);
  LP-04/05 tiers P1 (the words name it and it is not a dot, or the score reaches ``p1``), P2, P3, else skipped;
- LP-06 a visible flame is always alive and outside the cap; LP-07 the cap of effects by duration (4, 5, 6);
- LP-08 the floor: at least ``effects_min`` effects beyond the flames, ``non_light_min`` of them outside the light family,
  and one full-frame layer of moving air;
- LP-09 as amended by the owner (2026-11-14 12:38 UTC): the scene's weather is a ceiling, not a fill. A shot carries the
  scene's precipitation only where the director let it in (``weather`` records, ``production/living_director``: open sky,
  light, picture, words, neighbours); no snow where the scene has none;
- LP-10 people in a medium or close view longer than ``long_people_s`` go to LTX or are split; LP-11 at most
  ``rounds_max`` rounds; LP-12 the reviewer sees the skipped list.

An inventory row (``seen.living[]``) gives the extra fields ``area_pct`` (share of the frame, %), ``text``, ``focus``,
``quality``, ``cost`` (0..2) and optionally ``body_motion`` / ``contradicts_text``; its ``effects`` name the tracks that
move it (ids, ``direction.py``), and the first track's op is the row's effect. The numbers are Fable's proposals (REVIEW,
D-59) until the owner confirms them on a free rebuilt round.
"""
from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

DOT_PCT = float(SR.T("BP-200", "dot_pct"))
SCALE_STEPS = tuple(float(v) for v in SR.T("BP-200", "scale_steps_pct"))
W_TEXT = int(SR.T("BP-200", "w_text"))
P1_SCORE, P2_SCORE, P3_SCORE = (int(SR.T("BP-200", k)) for k in ("p1_score", "p2_score", "p3_score"))
EFFECTS_MIN = int(SR.T("BP-200", "effects_min"))
NON_LIGHT_MIN = int(SR.T("BP-200", "non_light_min"))
ROUNDS_MAX = int(SR.T("BP-200", "rounds_max"))
LONG_PEOPLE_S = float(SR.T("BP-200", "long_people_s"))
CAP_STEPS_S = tuple(float(v) for v in SR.T("BP-200", "cap_steps_s"))
CAPS = tuple(int(v) for v in SR.T("BP-200", "caps"))

# the renderer's effect ops (direction.EFFECT_OPS) and LP-08's families
FAMILY = {**{e: "light" for e in ("fire", "candle", "glow", "sun_shaft", "fire_box", "sun_glint", "stars", "light_fade")},
          **{e: "air" for e in ("smoke", "mist", "cloud_drift", "steam", "breath", "heat_haze")},
          **{e: "particles" for e in ("snow", "rain", "embers", "dust", "spindrift")},
          **{e: "surface" for e in ("foliage_sway", "cloth_flap", "wire_sway", "water_shimmer", "glint")},
          "subject_sway": "subject"}
GROUPABLE = ("glow", "stars", "candle", "glint")                     # LP-03: many dots, one effect
GLOBAL_AIR = ("mist", "snow", "dust", "cloud_drift", "spindrift")     # LP-08: one full-frame layer of moving air
ALWAYS_ON = ("fire", "fire_box", "candle", "glow")                    # LP-06: a visible flame is never frozen
# LP-09: the scene block's weather words -> the element every shot of the scene gets (effect, share of the frame, text)
WEATHER = {"snow": ("snow", 100.0, 2), "snow_light": ("snow", 100.0, 2), "snow_steady": ("snow", 100.0, 2),
           "mist": ("mist", 100.0, 1), "fog": ("mist", 100.0, 1), "rain": ("rain", 100.0, 2), "dust": ("dust", 100.0, 1)}
TIERS = ("P1", "P2", "P3")


def cap(duration_s: float) -> int:
    """LP-07: the most effects a shot carries besides the camera and the always-on flames."""
    for step, n in zip(CAP_STEPS_S, CAPS):
        if duration_s <= step:
            return n
    return CAPS[-1]


def scale_points(area_pct: float) -> int:
    return sum(area_pct >= s for s in SCALE_STEPS)


def score(e: dict) -> int:
    """LP-04."""
    return (W_TEXT * int(e.get("text", 0)) + scale_points(float(e.get("area_pct", 0))) + int(e.get("focus", 0))
            + int(e.get("quality", 0)) + int(e.get("cost", 0)))


def tier(e: dict) -> str:
    """LP-01..LP-05."""
    if e.get("contradicts_text"):
        return "FORBIDDEN"
    if e.get("body_motion"):
        return "LTX"
    if float(e.get("area_pct", 0)) < DOT_PCT and e.get("effect") not in GROUPABLE:
        return "SKIP_DOT"
    if int(e.get("quality", 0)) == 0:
        return "SKIP_QUALITY"
    s = score(e)
    if (int(e.get("text", 0)) == 2 and scale_points(float(e.get("area_pct", 0))) >= 1) or s >= P1_SCORE:
        return "P1"
    return "P2" if s >= P2_SCORE else "P3" if s >= P3_SCORE else "SKIP_LOW"


def rows_of(d: dict) -> list[dict]:
    """The inventory rows of a director's file with their effect (the op of the first track they name) and the scene's
    weather elements (LP-09) that the inventory does not already carry."""
    ops = {t.get("id"): t.get("op") for t in d.get("tracks", []) if t.get("id")}
    rows = []
    for e in (d.get("seen") or {}).get("living") or []:
        if e.get("decision") == "skip":
            continue
        eff = e.get("effect") or next((ops[i] for i in e.get("effects") or [] if i in ops), None)
        rows.append({**e, "effect": eff})
    have = {r["effect"] for r in rows}
    ceiling = set((d.get("scene") or {}).get("weather") or [])
    for rec in d.get("weather") or []:             # LP-09 as amended (12:38 UTC): only weather the director let in
        w = rec.get("weather")
        if rec.get("in") and w in ceiling and w in WEATHER and WEATHER[w][0] not in have:
            eff, area, text = WEATHER[w]
            rows.append({"id": f"weather_{w}", "kind": w, "effect": eff, "area_pct": area, "text": text, "focus": 1,
                         "quality": 2, "cost": 2, "decision": "add", "from_weather": True})
    return rows


def plan(d: dict, duration_s: float, rows: list[dict] | None = None) -> dict:
    """LP-06..LP-10 over the rows (the file's inventory, or the candidate rows the director's choice step passes): what
    moves, what is skipped and why, and the notes (``FAIL ...``, ``REVIEW ...``, ``ROUTE ...``) a check turns into
    problems."""
    rows = [{**r, "score": score(r), "tier": tier(r)} for r in (rows_of(d) if rows is None else rows)]
    n = cap(duration_s)
    live = [r for r in rows if r["tier"] in TIERS]
    always = [r for r in rows if r.get("effect") in ALWAYS_ON and r["tier"] not in ("FORBIDDEN", "LTX", "SKIP_QUALITY")]
    rest = sorted([r for r in live if r.get("effect") not in ALWAYS_ON], key=lambda r: (r["tier"], -r["score"]))
    p1 = [r for r in rest if r["tier"] == "P1"]
    chosen, notes = p1[:n], []
    if len(p1) > n:
        notes.append(f"REVIEW LP-07: {len(p1)} P1 elements over the cap of {n} for {duration_s:g} s")
    if not any(c.get("effect") in GLOBAL_AIR for c in chosen):
        air = [r for r in rest if r.get("effect") in GLOBAL_AIR and r not in chosen]
        if air:
            if len(chosen) >= n:
                chosen = chosen[:n - 1]
            chosen.append(air[0])

    def non_light(cs):
        return sum(FAMILY.get(c.get("effect"), "light") != "light" for c in cs)

    for r in rest:                         # then P1, P2, P3 by score while room remains under the cap ("P3 only if room
        if len(chosen) >= n:               # remains", the rules' section 0)
            break
        if r not in chosen:
            chosen.append(r)
    for r in rest:                         # LP-08's floor outside the light family: the best non-light candidate takes the
        if non_light(chosen) >= NON_LIGHT_MIN:     # slot of the lowest light pick when the cap is full
            break
        if r in chosen or FAMILY.get(r.get("effect"), "light") == "light":
            continue
        lights = [c for c in chosen if FAMILY.get(c.get("effect"), "light") == "light"]
        if len(chosen) >= n:
            if not lights:
                break
            chosen.remove(min(lights, key=lambda c: (c["score"], -TIERS.index(c["tier"]))))
        chosen.append(r)
    if len(chosen) < EFFECTS_MIN:
        notes.append(f"FAIL LP-08: only {len(chosen)} living effects beyond the flames (the floor is {EFFECTS_MIN})")
    if non_light(chosen) < NON_LIGHT_MIN:
        notes.append(f"FAIL LP-08: {non_light(chosen)} effects outside the light family (the floor is {NON_LIGHT_MIN})")
    if not any(c.get("effect") in GLOBAL_AIR for c in chosen):
        notes.append("FAIL LP-08: no full-frame layer of moving air (mist, snow, dust, cloud drift or spindrift)")
    for r in rows:
        if r["tier"] == "FORBIDDEN":
            notes.append(f"FAIL LP-01: {r['id']} contradicts the words")
        if r["tier"] == "LTX" and int(r.get("text", 0)) == 2:
            notes.append(f"ROUTE LP-02: the words need {r['id']} to move a body: LTX")
    if d.get("people_mid_or_close") and duration_s > LONG_PEOPLE_S:
        notes.append(f"ROUTE LP-10: people in a medium or close view for {duration_s:g} s: LTX or split")
    if len(d.get("rounds") or []) > ROUNDS_MAX:
        notes.append(f"REVIEW LP-11: {len(d['rounds'])} rounds (at most {ROUNDS_MAX})")
    picked = [r["id"] for r in chosen + always]
    return {"cap": n, "chosen": [{k: r.get(k) for k in ("id", "effect", "tier", "score")} for r in chosen],
            "always_on": [{"id": r["id"], "effect": r.get("effect")} for r in always],
            "skipped": [{"id": r["id"], "tier": r["tier"], "score": r["score"]} for r in rows if r["id"] not in picked],
            "families": sorted({FAMILY.get(r.get("effect"), "light") for r in chosen + always}),
            "ltx": [r["id"] for r in rows if r["tier"] == "LTX"], "notes": notes}


def check(d: dict, duration_s: float) -> list[dict]:
    """The plan's notes as problems for ``direction.check``; an animated element the plan did not choose is REVIEW
    (over the cap or below its tier), so the director either drops it or says why it earns the slot."""
    p = plan(d, duration_s)
    probs = []
    for note in p["notes"]:
        level, _, what = note.partition(" ")
        probs.append({"level": "FAIL" if level == "FAIL" else "REVIEW", "what": what, "rule": "BP-200"})
    chosen = {c["id"] for c in p["chosen"]} | {a["id"] for a in p["always_on"]}
    for r in rows_of(d):
        if r.get("decision") in ("animate", "add") and r["id"] not in chosen and not r.get("from_weather"):
            t = tier({**r})
            probs.append({"level": "REVIEW", "rule": "BP-200",
                          "what": f"seen.living {r['id']} is animated but LP-04..07 did not choose it ({t}, score {score(r)})"})
    return probs
