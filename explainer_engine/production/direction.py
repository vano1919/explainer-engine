"""The Scene Director's file for one shot (roadmap 2026-11-14 B.1 ``shot_direction/1``; phase P1 draft, human-in-the-loop).

The director (in P1 the thread's Claude, looking at the real picture and the rendered frames; L-11 a) writes one JSON per
shot. The script stays Stage A's approved intent; this file is Stage B's decision as a difference with a reason. P1 only
loads, checks and resolves it into a ``production/directed25d`` plan; P2 turns the draft into a versioned schema and a runner
stage (``direction``, after ``pictures``, before ``clips``).

The draft's fields: ``schema``, ``shot_id``, ``kind`` (photo|map), ``picture_sha256``, ``seen`` (what is REALLY in the frame:
``what`` in words, ``objects`` with points, ``lights``, ``depth_checks``), ``purpose``, ``emotion``, ``focus``, ``composition``,
``intent`` (intended|minimal|still_by_design), ``tracks`` (camera, character, object, environment, lighting, atmosphere,
audio; each with ``op``, ``target``, ``timing``, ``renderer``, ``validate``), ``sound``, ``transition_out``, ``route``,
``overrides`` (field, from, to, why: a change without a reason FAILs), ``rounds`` and ``expect`` (what QA measures).

The owner's rules of 2026-11-14 (after P1 round 2 stood still for 27 of 38 seconds; Fable's 2.5D audit of the same day):

- ``seen.living`` (BP-196): every element of the picture that moves in nature, from the fixed checklist ``LIVING_KINDS``,
  with ``where`` and a ``decision``: ``animate`` (``effects`` = the ids of the tracks that move it), ``add`` (not in the
  picture, but the scene's weather or the words call for it: snow that falls) or ``skip`` (``why``; a REVIEW row, so the
  reviewer sees every element left frozen). A living kind named in ``seen.what``, in ``scene.weather`` / ``scene.surroundings``
  or in the shot's spoken words but missing from the inventory FAILs: that is how the sun of a sunrise gets its rays.
- BP-185 for every photo shot, ``still_by_design`` included (it means the camera stands, never that nature freezes): at least
  ``ALIVE_MIN`` families move beyond the camera; when all of them are light (a flame and nothing else) it is REVIEW.
- The camera follows the words (BP-196, timing BP-195): every object or living element with ``names`` that the shot's words
  name gets a camera track aimed at it (``target.mask`` / ``target.living``) starting on that word, or a ``text_targets_skip``
  entry with ``word`` and ``why``.
- A hold before the first move lasts at most ``HOLD_MAX_S`` unless a handheld or drift moves the camera meanwhile (BP-197).
- Every effect op the file asks of ``directed25d`` must exist in the renderer (``directed25d.FX_OPS``): an op not built yet
  FAILs, so a missing tool shows up as a gap instead of a silently frozen element.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from explainer_engine.standards import sourced_rules as SR
SCHEMA = "shot_direction/1-draft"
INTENTS = ("intended", "minimal", "still_by_design")
TRACKS = ("camera", "character", "object", "environment", "lighting", "atmosphere", "audio")
CAMERA_OPS = ("hold", "push", "pull", "truck", "crane", "pan", "pan_crop_2d", "tilt", "orbit", "handheld", "rack_focus")
EFFECT_OPS = ("fire", "candle", "glow", "smoke", "mist", "sun_shaft", "cloud_drift", "heat_haze", "fire_box", "dust",
              "snow", "rain", "embers", "steam", "stars", "sun_glint", "glint", "foliage_sway", "cloth_flap", "wire_sway",
              "water_shimmer", "subject_sway", "breath", "spindrift", "light_fade")
# BP-185's families of the effects (a camera move is none of them)
FAMILY_OF = {**{e: "light" for e in ("fire", "candle", "glow", "sun_shaft", "fire_box", "sun_glint", "glint", "stars",
                                     "light_fade")},
             **{e: "atmosphere" for e in ("smoke", "mist", "cloud_drift", "dust", "snow", "rain", "embers", "steam", "breath",
                                          "spindrift")},
             **{e: "surface" for e in ("heat_haze", "foliage_sway", "cloth_flap", "wire_sway", "water_shimmer")},
             "subject_sway": "subject"}
ALIVE_MIN = int(SR.T("BP-185", "families_min"))
# BP-196's fixed checklist: the kinds of living element and the effects that may move each one
LIVING_KINDS = {
    "sun": ("sun_shaft", "sun_glint", "glow", "light_fade"), "sky": ("cloud_drift", "stars", "glow"), "cloud": ("cloud_drift",),
    "mist": ("mist",), "snow": ("snow", "spindrift", "glint"), "rain": ("rain",),
    "wind": ("foliage_sway", "cloth_flap", "wire_sway", "snow", "spindrift", "smoke", "mist", "steam"),
    "plants": ("foliage_sway",), "cloth": ("cloth_flap",), "wire": ("wire_sway",), "water": ("water_shimmer", "glint"),
    "ice": ("glint", "sun_glint"), "fire": ("fire", "fire_box", "embers", "smoke", "glow"), "candle": ("candle", "glow"),
    "smoke": ("smoke",), "steam": ("steam", "smoke"), "breath": ("breath", "steam"), "stars": ("stars",), "glint": ("glint", "sun_glint"),
    "dust": ("dust",), "heat": ("heat_haze",), "body": ("subject_sway",),
}
# words that name a living kind (in seen.what, the scene's weather and surroundings, and the shot's spoken words)
LIVING_WORDS = {
    "sun": ("sun", "sunrise", "sunset", "dawn", "daybreak", "sunlight", "sunlit", "sunbeam", "sunbeams", "rays", "sunrays"),
    "sky": ("sky", "skies"), "cloud": ("cloud", "clouds", "cloudy", "overcast"),
    "mist": ("mist", "misty", "fog", "foggy", "haze", "hazy"),
    "snow": ("snow", "snowy", "snowing", "snowfall", "snowflakes", "flakes", "blizzard"),
    "rain": ("rain", "raining", "rainy", "drizzle", "downpour"), "wind": ("wind", "windy", "breeze", "gust", "gusts", "gale"),
    "plants": ("tree", "trees", "forest", "grass", "branch", "branches", "leaves", "willow", "willows", "pine", "pines",
               "fir", "firs", "bush", "bushes", "reeds", "foliage"),
    "cloth": ("flag", "flags", "banner", "banners", "tarp", "tarpaulin", "canvas", "sail", "sails", "cloak", "cloaks",
              "kilt", "kilts"),
    "wire": ("wire", "wires", "barbed"), "water": ("water", "river", "sea", "lake", "puddle", "puddles", "stream", "waves"),
    "ice": ("ice", "icy", "icicles", "frost", "frosty", "frosted", "frozen", "hoarfrost"),
    "fire": ("fire", "fires", "flame", "flames", "brazier", "braziers", "campfire", "bonfire", "torch", "torches", "burning",
             "embers"),
    "candle": ("candle", "candles", "lantern", "lanterns", "lamp", "lamps"), "smoke": ("smoke", "smoking", "ash", "ashes"),
    "steam": ("steam", "steaming"), "breath": ("breath", "breathing", "exhale", "exhales"),
    "stars": ("star", "stars", "starry", "starlight"), "dust": ("dust", "dusty"),
}
_WORD_KIND = {w: k for k, ws in LIVING_WORDS.items() for w in ws}
LIVING_DECISIONS = ("animate", "add", "skip")
LEAD_S, LAG_S = float(SR.T("BP-195", "lead_s")), float(SR.T("BP-195", "lag_s"))
HOLD_MAX_S = float(SR.T("BP-197", "hold_before_word_s_max"))
MOVING_CAMERA = ("push", "pull", "truck", "crane", "pan", "pan_crop_2d", "tilt", "orbit", "rack_focus")
AUDIO_DECISIONS = ("sfx", "ui_cue", "ambience_only", "music_only", "silent_by_design", "review_required")
RENDERERS = ("directed25d", "layers25d", "map_action", "ltx", "blender", "none")
MINIMAL_MAX = 0.5          # a "minimal" shot moves its camera at no more than this strength (engineering default, REVIEW)
SEGMENTS_MAX = 3
KB_PATH = Path(__file__).resolve().parents[1] / "standards" / "director_knowledge_base.json"
_KB_CACHE: dict | None = None
def load_knowledge_base(path: Path | None = None) -> dict:
    global _KB_CACHE
    if path is not None:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if _KB_CACHE is None:
        _KB_CACHE = json.loads(KB_PATH.read_text(encoding="utf-8"))
    return _KB_CACHE
def _feasibility(d: dict, manifest: dict | None = None) -> list[dict]:
    from explainer_engine.production import understand as U
    kb = load_knowledge_base()
    rules = kb.get("camera_feasibility_rules") or {}
    orbit_rule = rules.get("orbit_small") or {}
    truck_rule = rules.get("truck_25d") or {}
    crane_rule = rules.get("crane_up") or rules.get("crane_25d") or {}
    rack_rule = rules.get("rack_focus") or {}
    orbit_edge_min = float(orbit_rule.get("min_edge_margin_x", 0.22))
    orbit_hole_max = float(orbit_rule.get("max_hole_share", 0.04))
    orbit_delta_min = float(rack_rule.get("min_fg_bg_depth_delta", 0.28))
    truck_edge_min = float(truck_rule.get("min_edge_margin_x", 0.14))
    truck_hole_max = float(truck_rule.get("max_hole_share", 0.06))
    truck_delta_min = 0.22
    crane_sky_min = float(crane_rule.get("min_sky_area_pct", 12.0))
    crane_edge_y_min = float(crane_rule.get("min_bottom_face_clearance_pct", 0.12))
    man = manifest if manifest is not None else d.get("manifest")
    geom = U.picture_geometry(man, d.get("seen"), d=d)
    audit_meas = (((d.get("choice") or {}).get("audit") or {}).get("measurements") or {})
    for k in ("person_boxes", "edge_margin_x", "edge_margin_y", "sky_area_pct", "fg_bg_depth_delta", "unlayered_people", "hole_share"):
        if man is None and k in audit_meas:
            geom[k] = audit_meas[k]
    person_boxes = geom.get("person_boxes") or []
    kept_faces = [k["face"] for k in (d.get("keep_in_frame") or []) if isinstance(k.get("face"), (list, tuple)) and len(k["face"]) == 4]
    choice_faces = [f["box"] for f in ((d.get("choice") or {}).get("faces") or []) if isinstance(f.get("box"), (list, tuple)) and len(f["box"]) == 4]
    all_people = list(person_boxes) + kept_faces + choice_faces
    has_people = bool(all_people or d.get("people_mid_or_close") or audit_meas.get("people_count", 0) > 0)
    edge_x = float(geom.get("edge_margin_x", 1.0))
    edge_y = float(geom.get("edge_margin_y", 1.0))
    if all_people and edge_x >= 1.0:
        edge_x = round(min(min(float(b[0]), 1.0 - float(b[2])) for b in all_people), 4)
    if all_people and edge_y >= 1.0:
        edge_y = round(min(min(float(b[1]), 1.0 - float(b[3])) for b in all_people), 4)
    sky_pct = float(geom.get("sky_area_pct", 0.0))
    depth_delta = float(geom.get("fg_bg_depth_delta", 0.0))
    unlayered_people = bool(geom.get("unlayered_people", False))
    man_d = man if isinstance(man, dict) else {}
    hole_share = float(geom.get("hole_share", (man_d.get("plate") or {}).get("hole_share", (man_d.get("masks") or {}).get("hole_share", 0.0))))
    out = []
    cams = [t for t in d.get("tracks", []) if t.get("track") == "camera" and t.get("op") not in ("hold", "handheld", "rack_focus")]
    for t in cams:
        op = str(t.get("op", ""))
        if op in ("orbit", "orbit_small", "truck", "truck_25d"):
            is_orbit = op.startswith("orbit")
            min_edge = orbit_edge_min if is_orbit else truck_edge_min
            max_hole = orbit_hole_max if is_orbit else truck_hole_max
            min_delta = orbit_delta_min if is_orbit else truck_delta_min
            if has_people and (edge_x < min_edge or unlayered_people):
                out.append({"level": "FAIL", "rule": "_feasibility",
                            "what": f"_feasibility: creator's veto: {op} changes lateral angle on a shot with people near the edge (edge_margin_x={edge_x:.3f} < {min_edge:g}, unlayered_people={unlayered_people}): use push or horizontal pan without angle change (pan_crop_2d)"})
            elif is_orbit and has_people:
                out.append({"level": "REVIEW", "rule": "_feasibility",
                            "what": "orbit changes lateral angle on one photo with kept people: use push or horizontal pan without angle change"})
            if hole_share > max_hole:
                out.append({"level": "REVIEW", "rule": "_feasibility",
                            "what": f"_feasibility: {op} with inpainted hole_share {hole_share:.3f} > {max_hole:g} risks exposing fill (D-59)"})
            if 0.0 < depth_delta < min_delta:
                out.append({"level": "REVIEW", "rule": "_feasibility",
                            "what": f"_feasibility: {op} with fg_bg_depth_delta {depth_delta:.3f} < {min_delta:g} has insufficient depth separation (D-59)"})
        elif op in ("crane", "crane_up", "crane_25d"):
            if sky_pct < crane_sky_min:
                out.append({"level": "REVIEW", "rule": "_feasibility",
                            "what": f"_feasibility: {op} with sky_area_pct {sky_pct:g}% < {crane_sky_min:g}% lacks vertical headroom (D-59)"})
            if has_people and edge_y < crane_edge_y_min:
                out.append({"level": "REVIEW", "rule": "_feasibility",
                            "what": f"_feasibility: {op} with edge_margin_y {edge_y:.3f} < {crane_edge_y_min:g} risks vertical crop (D-59)"})
    return out
def _audit_present(d: dict) -> list[dict]:
    choice = d.get("choice")
    if not isinstance(choice, dict) or not isinstance(choice.get("audit"), dict):
        return [{"level": "REVIEW", "rule": "_audit_present",
                 "what": "_audit_present: choice.audit is missing (director must record idiom, chosen, rejected, measurements)"}]
    audit = choice["audit"]
    missing = [k for k in ("idiom", "chosen", "rejected", "measurements") if not audit.get(k)]
    if missing:
        return [{"level": "REVIEW", "rule": "_audit_present",
                 "what": f"_audit_present: choice.audit is missing {' , '.join(missing)}"}]
    return []
def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())
def _ids(d: dict) -> tuple[set, set]:
    seen = d.get("seen") or {}
    return {o["id"] for o in seen.get("objects", [])}, {li["id"] for li in seen.get("lights", [])}
def _norm(w: str) -> str:
    return str(w).lower().strip(".,!?;:'\"()-")
def kinds_named(text: str | list) -> set:
    words = text if isinstance(text, list) else re.findall(r"[a-zA-Z']+", str(text or ""))
    return {_WORD_KIND[_norm(w)] for w in words if _norm(w) in _WORD_KIND}
def check(d: dict, picture_sha256: str | None = None, spine: list[dict] | None = None, fps: float = 24.0,
          frames: int | None = None, manifest: dict | None = None) -> list[dict]:
    out = []
    def bad(what, level="FAIL"):
        out.append({"level": level, "what": what})
    if d.get("schema") != SCHEMA:
        bad(f"schema is {d.get('schema')!r}, not {SCHEMA}")
    if d.get("intent") not in INTENTS:
        bad(f"intent {d.get('intent')!r} is not one of {', '.join(INTENTS)}")
    if picture_sha256 and d.get("picture_sha256") != picture_sha256:
        bad("picture_sha256 does not match the picture: the direction was written for another picture")
    if not (d.get("seen") or {}).get("what"):
        bad("seen.what is empty: the director must say in words what is really in the frame")
    for o in d.get("overrides", []):
        for k in ("field", "from", "to", "why"):
            if not str(o.get(k, "")).strip():
                bad(f"override {o.get('field', '?')}: no {k} (a change without a reason FAILs)")
    objs, lights = _ids(d)
    cams = []
    for i, t in enumerate(d.get("tracks", [])):
        name = f"track {i} ({t.get('track')}/{t.get('op')})"
        if t.get("track") not in TRACKS:
            bad(f"{name}: unknown track")
            continue
        if t["track"] == "audio":
            if t.get("decision") not in AUDIO_DECISIONS:
                bad(f"{name}: audio decision {t.get('decision')!r}")
            continue
        if t.get("renderer") not in RENDERERS:
            bad(f"{name}: renderer {t.get('renderer')!r}")
        if t["track"] == "camera":
            if t.get("op") not in CAMERA_OPS:
                bad(f"{name}: camera op unknown")
            if "validate" not in t:
                bad(f"{name}: no validate block (every camera track says what QA measures)")
            if t.get("op") not in ("hold", "handheld", "rack_focus"):
                cams.append(t)
        elif t.get("op") not in EFFECT_OPS:
            bad(f"{name}: effect op unknown")
        tg = t.get("target") or {}
        for key in ("mask", "from_mask", "to_mask"):
            if tg.get(key) and tg[key] not in objs:
                bad(f"{name}: target {key} {tg[key]!r} is not an object of seen.objects")
        for lid in tg.get("lights", []) + ([tg["light"]] if tg.get("light") else []):
            if lid not in lights:
                bad(f"{name}: light {lid!r} is not in seen.lights")
    out += _living(d, spine)
    out += _weather(d)
    out += _families(d)
    out += _renderable(d)
    if spine is not None:
        out += _words_to_camera(d, spine, fps, frames)
    out += _hold(d, spine, fps, frames)
    if frames:
        out += _balance(d, frames / fps)
    out += _feasibility(d, manifest=manifest)
    if "choice" in d:
        out += _audit_present(d)
    if any(t.get("op") == "orbit" for t in cams) and any(k.get("face") for k in (d.get("keep_in_frame") or [])) and not any("orbit changes lateral angle" in r["what"] for r in out):
        bad("orbit changes lateral angle on one photo with kept people: use push or horizontal pan without angle change", "REVIEW")
    if len(cams) > SEGMENTS_MAX:
        bad(f"{len(cams)} camera segments; at most {SEGMENTS_MAX}")
    if d.get("intent") == "still_by_design" and cams:
        bad(f"still_by_design but the camera moves ({', '.join(t['op'] for t in cams)})")
    if d.get("intent") == "minimal":
        for t in cams:
            if float(t.get("params", {}).get("strength", 1.0)) > MINIMAL_MAX:
                bad(f"minimal but {t['op']} strength {t['params']['strength']} > {MINIMAL_MAX}", "REVIEW")
    return out
def _living(d: dict, spine) -> list[dict]:
    out = []
    seen = d.get("seen") or {}
    living = seen.get("living")
    if living is None:
        return [{"level": "FAIL", "what": "seen.living is missing: the director lists every element of the picture that moves "
                 "in nature (BP-196)"}]
    tracks = {t.get("id"): t for t in d.get("tracks", []) if t.get("id")}
    have = set()
    for e in living:
        k, name = e.get("kind"), f"living {e.get('id', '?')}"
        if k not in LIVING_KINDS:
            out.append({"level": "FAIL", "what": f"{name}: kind {k!r} is not on the checklist ({', '.join(LIVING_KINDS)})"})
            continue
        have.add(k)
        dec = e.get("decision")
        if dec not in LIVING_DECISIONS:
            out.append({"level": "FAIL", "what": f"{name}: decision {dec!r} is not one of {', '.join(LIVING_DECISIONS)}"})
        elif dec == "skip":
            why = str(e.get("why", "")).strip()
            out.append({"level": "FAIL" if not why else "REVIEW",
                        "what": f"{name} ({k}) is left frozen" + (f": {why}" if why else " without a reason (BP-196)")})
        else:
            ids = e.get("effects") or []
            if not ids:
                out.append({"level": "FAIL", "what": f"{name} ({k}): {dec} but no effect track named"})
            for tid in ids:
                t = tracks.get(tid)
                if t is None:
                    out.append({"level": "FAIL", "what": f"{name}: effect track {tid!r} does not exist"})
                elif t.get("op") not in LIVING_KINDS[k]:
                    out.append({"level": "FAIL", "what": f"{name} ({k}): track {tid} op {t.get('op')!r} does not move a {k} "
                                f"({', '.join(LIVING_KINDS[k])})"})
            if dec == "animate" and not (e.get("where") or e.get("mask") or e.get("box")):
                out.append({"level": "FAIL", "what": f"{name}: no where/mask/box (the effect needs the element's place)"})
    scene = d.get("scene") or {}
    sources = [("seen.what", seen.get("what", "")),
               ("scene.weather", " ".join(scene.get("weather", []) if isinstance(scene.get("weather"), list)
                                          else [str(scene.get("weather", ""))])),
               ("scene.surroundings", scene.get("surroundings", ""))]
    if spine is not None:
        sources.append(("the shot's words", [w.get("word", "") for w in spine]))
    decided = kinds_named(" ".join(str(r.get("weather", "")).replace("_", " ") for r in d.get("weather") or []))
    for where, text in sources:
        cover = have | decided if where == "scene.weather" else have   # the scene's weather is a ceiling (12:38 UTC)
        for k in sorted(kinds_named(text) - cover):
            verb = "name" if where.endswith("words") else "names"
            out.append({"level": "FAIL", "what": f"{where} {verb} {k} but seen.living has no {k} (BP-196: every living "
                        "element gets an effect or a reason)"})
    return out
PRECIPITATION = {"snow": "snow", "rain": "rain"}
def _weather(d: dict) -> list[dict]:
    from explainer_engine.production import living_director as LD
    out = []
    ceiling = [str(w) for w in ((d.get("scene") or {}).get("weather") or [])]
    for t in d.get("tracks", []):
        need = PRECIPITATION.get(t.get("op")) if t.get("track") not in ("camera", "audio") else None
        if need and not any(w.startswith(need) for w in ceiling):
            out.append({"level": "FAIL", "what": f"track {t.get('id', '?')}: {t['op']} falls but the scene's weather "
                        f"({', '.join(ceiling) or 'none'}) has no {need} (the scene's weather is the ceiling)"})
    recs = {r.get("weather"): r for r in d.get("weather") or []}
    for w in ceiling:
        r = recs.get(w)
        if r is None:
            continue                       # _living reports the scene's weather left without an element or a decision
        if r.get("decided_by") not in LD.CRITERIA:
            out.append({"level": "FAIL", "what": f"weather {w}: decided_by {r.get('decided_by')!r} is not one of "
                        f"{', '.join(LD.CRITERIA)}"})
        if not str(r.get("why", "")).strip():
            out.append({"level": "FAIL", "what": f"weather {w}: {'in' if r.get('in') else 'left out'} without a reason"})
    for w in recs:
        if w not in ceiling and recs[w].get("in"):
            out.append({"level": "FAIL", "what": f"weather {w} is let in but the scene's weather has no {w}"})
    return out
def _balance(d: dict, duration_s: float) -> list[dict]:
    from explainer_engine.production import living
    rows = [e for e in (d.get("seen") or {}).get("living") or [] if e.get("decision") != "skip"]
    if rows and not any("area_pct" in e for e in rows):
        return [{"level": "REVIEW", "rule": "BP-200",
                 "what": "seen.living has no LP scores (area_pct, text, focus, quality, cost): the balance was not checked"}]
    return [{k: v for k, v in p.items()} for p in living.check(d, duration_s)]
def _families(d: dict) -> list[dict]:
    fams = {FAMILY_OF[t["op"]] for t in d.get("tracks", []) if t.get("track") not in ("camera", "audio")
            and t.get("op") in FAMILY_OF}
    out = []
    if len(fams) < ALIVE_MIN:
        out.append({"level": "FAIL", "what": f"alive beyond the camera: {sorted(fams) or 'nothing'}; BP-185 needs {ALIVE_MIN} "
                    "families (atmosphere, light, surface, subject), whatever the intent"})
    elif fams == {"light"}:
        out.append({"level": "REVIEW", "what": "every moving family is light: the flames flicker and nothing else lives"})
    return out
def _renderable(d: dict) -> list[dict]:
    from explainer_engine.production import directed25d
    return [{"level": "FAIL", "what": f"track {t.get('id', '?')}: directed25d cannot draw {t['op']!r} yet (not built)"}
            for t in d.get("tracks", []) if t.get("renderer") == "directed25d" and t.get("track") not in ("camera", "audio")
            and t.get("op") in EFFECT_OPS and t["op"] not in directed25d.FX_OPS]
def _named_parts(d: dict) -> dict:
    seen = d.get("seen") or {}
    out = {}
    for e in list(seen.get("objects", [])) + list(seen.get("living", [])):
        for n in e.get("names", []):
            out[_norm(n)] = e["id"]
    return out
def _words_to_camera(d: dict, spine: list[dict], fps: float, frames: int | None) -> list[dict]:
    parts = _named_parts(d)
    if not parts:
        return []
    skip = {_norm(s.get("word", "")): str(s.get("why", "")).strip() for s in d.get("text_targets_skip", [])}
    cams = [t for t in d.get("tracks", []) if t.get("track") == "camera" and t.get("op") in MOVING_CAMERA]
    n = int(frames or max([int(w.get("frame", 0)) for w in spine] + [0]) + 1)
    out, done = [], set()
    for w in spine:
        word = _norm(w.get("word", ""))
        pid = parts.get(word)
        if pid is None or pid in done:
            continue
        done.add(pid)
        wf = int(w.get("frame", w.get("start_frame", 0)))
        if word in skip:
            if not skip[word]:
                out.append({"level": "FAIL", "what": f"text_targets_skip '{word}' without a reason"})
            continue
        aimed = [t for t in cams if pid in ((t.get("target") or {}).get("mask"), (t.get("target") or {}).get("living"),
                                            (t.get("target") or {}).get("to_mask"))]
        if not aimed:
            out.append({"level": "FAIL", "what": f"the words name '{word}' ({pid}) at frame {wf} but no camera track aims at it "
                        "(BP-196: the camera follows the words)"})
            continue
        starts = []
        for t in aimed:
            try:
                starts.append(_frame((t.get("timing") or {}).get("start"), n, spine, 0))
            except ValueError:
                pass
        if not any(wf - LEAD_S * fps <= a <= wf + LAG_S * fps for a in starts):
            out.append({"level": "REVIEW", "what": f"the camera on '{word}' ({pid}) starts at frame(s) {starts}, the word is at "
                        f"{wf} (BP-195: from {LEAD_S} s before to {LAG_S} s after)"})
    return out
def _hold(d: dict, spine, fps: float, frames: int | None) -> list[dict]:
    tracks = d.get("tracks", [])
    if any(t.get("track") == "camera" and t.get("op") == "handheld" for t in tracks):
        return []
    moving = [t for t in tracks if t.get("track") == "camera" and t.get("op") in MOVING_CAMERA]
    if not moving:
        return []
    n = int(frames or 10 ** 6)
    starts = []
    for t in moving:
        try:
            starts.append(_frame((t.get("timing") or {}).get("start"), n, spine, 0))
        except ValueError:
            return []                  # a word not in this clock: the words rule reports it
    first = min(starts)
    if first > HOLD_MAX_S * fps:
        return [{"level": "REVIEW", "what": f"the camera stands for {first / fps:.1f} s before its first move with no drift or "
                 f"handheld meanwhile (BP-197: at most {HOLD_MAX_S} s)"}]
    return []
def word_frame(spine: list[dict], word: str, nth: int = 1) -> int:
    k = 0
    for w in spine or []:
        if str(w.get("word", "")).lower().strip(".,!?;:'\"") == word.lower():
            k += 1
            if k == nth:
                return int(w.get("frame", w.get("start_frame", 0)))
    raise ValueError(f"the word {word!r} (#{nth}) is not spoken in this shot")
def _frame(spec: dict | None, frames: int, spine, default: int) -> int:
    if not spec:
        return default
    if "frame" in spec:
        return max(0, min(int(frames), int(spec["frame"])))
    if "frac" in spec:
        return max(0, min(int(frames), int(round(float(spec["frac"]) * frames))))
    if "word" in spec:
        off = int(spec.get("offset", spec.get("offset_frames", 0)))
        return max(0, min(int(frames), word_frame(spine, spec["word"], int(spec.get("nth", int(spec.get("occurrence", 1))))) + off))
    raise ValueError(f"timing {spec!r}: give frame, frac or word")
def _target(tg: dict | None) -> dict | None:
    if not tg:
        return None
    out = {}
    if tg.get("mask"):
        out["mask"] = tg["mask"]
    if tg.get("point"):
        out["point"] = tg["point"]
    if tg.get("light"):
        out["light"] = tg["light"]
    return out or None
def resolve(d: dict, frames: int, spine: list[dict] | None = None, variant: str | None = None) -> dict:
    if spine and isinstance(spine[0], dict) and "_parent_spine" in spine[0]:
        f_lo = int(spine[0].get("_part_start_frame", 0))
        f_hi = int(spine[0].get("_part_end_frame", f_lo + int(frames)))
        p_frames = int(spine[0].get("_parent_frames", max(f_hi, int(frames))))
        full = resolve(d, p_frames, spine=spine[0]["_parent_spine"], variant=variant)
        full["shot_id"] = d["shot_id"]
        full["frames"] = int(frames)
        part_cams = []
        for c in full["cameras"]:
            c0, c1 = int(c["from"]), int(c["to"])
            if c1 <= f_lo or c0 >= f_hi:
                continue
            ov0, ov1 = max(c0, f_lo), min(c1, f_hi)
            frac = (ov1 - ov0) / max(1, c1 - c0)
            nc = dict(c, **{"from": ov0 - f_lo, "to": max(ov0 - f_lo + 1, ov1 - f_lo),
                            "strength": round(float(c.get("strength", 1.0)) * frac, 4)})
            part_cams.append(nc)
        full["cameras"] = part_cams
        if full.get("rack"):
            r0 = int(full["rack"]["at"])
            r1 = r0 + int(full["rack"]["frames"])
            if r1 <= f_lo or r0 >= f_hi:
                full["rack"] = None
            else:
                full["rack"] = dict(full["rack"], at=max(0, r0 - f_lo), frames=max(1, min(r1, f_hi) - max(r0, f_lo)))
        return full
    tracks = d.get("tracks", [])
    if variant:
        tracks = d["variants"][variant]["tracks"]
    plan = {"shot_id": d["shot_id"], "frames": int(frames), "cameras": [], "handheld": None, "rack": None, "effects": [],
            "far_share": float(d.get("far_share", 0.2)), "intent": d.get("intent")}
    if d.get("layers") is not None:
        plan["layers"] = list(d["layers"])
    if d.get("keep_in_frame"):
        plan["keep_in_frame"] = [dict(k) for k in d["keep_in_frame"]]   # the safe zone: the people the camera never cuts
    for t in tracks:
        if t.get("track") == "audio" or t.get("renderer") not in (None, "directed25d"):
            continue
        prm = dict(t.get("params", {}))
        tm = t.get("timing", {})
        a = _frame(tm.get("start"), frames, spine, 0)
        b = _frame(tm.get("end"), frames, spine, frames)
        if isinstance(tm.get("start"), dict) and "word" in tm["start"] and isinstance(tm.get("end"), dict) and "frame" in tm["end"]:
            if b - a < 12:
                b = min(int(frames), a + 30)
        op = t["op"]
        if t["track"] == "camera":
            if op == "hold":
                continue
            if op == "handheld":
                plan["handheld"] = float(prm.get("strength", 0.3))
                continue
            if op == "rack_focus":
                tg = t.get("target", {})
                plan["rack"] = {"from": {"mask": tg["from_mask"]} if tg.get("from_mask") else {"light": tg.get("from_light")},
                                "to": {"mask": tg["to_mask"]} if tg.get("to_mask") else {"light": tg.get("to_light")},
                                "at": a, "frames": max(1, b - a), "strength": float(prm.get("strength", 1.0)),
                                **{k: prm[k] for k in ("sigma_px", "span") if k in prm}}
                continue
            cam_row = {"op": op, "strength": float(prm.get("strength", 1.0)), "direction": prm.get("direction"),
                       "from": a, "to": max(a + 1, b), "easing": prm.get("ease", "ease_in_out"),
                       "target": _target(t.get("target"))}
            for k in ("overscan", "from_xy", "to_xy"):
                if k in prm:
                    cam_row[k] = prm[k]
            plan["cameras"].append(cam_row)
        else:
            tg = t.get("target") or {}
            e = {"op": op, "strength": float(prm.pop("strength", 1.0)), "params": prm}
            if tg.get("lights"):
                e["lights"] = list(tg["lights"])
            if tg.get("light"):
                e["light"] = tg["light"]
                e.setdefault("lights", [tg["light"]])
            if tg.get("box"):
                e["box"] = tg["box"]
            if tg.get("mask"):
                e["mask"] = tg["mask"]
            if tg.get("point"):
                e["point"] = tg["point"]
            if tg.get("origin"):
                e["origin"] = tg["origin"]
            plan["effects"].append(e)
    plan["cameras"].sort(key=lambda c: c["from"])
    for c_prev, c_next in zip(plan["cameras"], plan["cameras"][1:]):
        if c_prev["to"] == c_next["from"] and c_prev["to"] < int(frames):
            c_prev["to"] = c_next["from"] + 1
    if (d.get("scene") or {}).get("wind"):
        plan["wind"] = list(d["scene"]["wind"])        # one wind per shot: smoke, snow, grass and cloth lean together
    return plan
