"""The shot designer of the Ink Chronicle path (roadmap 7.3, 7.4 and 11, ICW-03; D-97): reads one ``film_shots/3`` card and
says which of the 20 archetypes it is, how intense its beat is, whether a Python helper visual could carry it, whether a
spoken line is seen (``dialogue_cover``), and writes the lane fields once the lane planner (``visual/lanes.py``) has chosen
the lane: ``archetype``, ``still_mode``, ``render_profile``, ``lipsync``, ``helper_archetype``, ``tier``, and the D-116 ``route`` with its
``sub_category``. It never touches
the words (narration, dialogue, claims): the speech mix is the script's (BP-105, D-99), not the picture's.

The archetypes and the lane sub-categories live in ``visual/archetypes_ic.json`` (``archetypes_ic/2``, validated against
``schemas/archetypes_ic.schema.json`` and by ``registry_errors``). Shot caps and shares are never copied here: they are read
through ``scripting/film_shots`` (BP-108, BP-109), the module the registry lists as their reader.

Classification is a deterministic rule list (no model): the cold open (a scene holding a KP-41 teaser) is 18, a seen spoken
line is 3 (4 with three or more people in frame), a loud peak of the climax scene is 19, the last scene is 20; every other
shot takes the archetype whose trigger words its beat, narration and action name most often, among those whose frame fits
(shot size, people), with a structural default when no word fits. Helper candidates (12 map, 13 explanation, 17 evidence)
are shots with narration, claims, a number or a helper word and no named character in frame; the planner decides which
candidates really become HELPER.
"""

from __future__ import annotations

import copy
import json
import re
from functools import lru_cache
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.scripting import film_shots as F

REGISTRY = Path(__file__).with_name("archetypes_ic.json")
LANES = ("VIDEO_3D", "STILL_3D", "HELPER")
# the twelve attributes of brief section 5 each sub-category carries (roadmap 7.4); the schema makes every one required
ATTRIBUTES = ("purpose_and_trigger", "when_not", "required_metadata", "shot_design", "motion", "look", "duration",
              "blender_strategy", "render_profile_and_cost_class", "audio_and_continuity", "qa", "archetype_examples")
SUB_COUNTS = {"HELPER": 6, "STILL_3D": 7, "VIDEO_3D": 10}  # roadmap 7.4's lists
HELPER_IDS = (12, 13, 17)  # the archetypes a HELPER shot takes (roadmap 7.3); the others are drawn by Blender
WIDE = {"EWS", "WS"}
CLOSE = {"MCU", "CU", "ECU"}
# frame.camera (the card's words) -> the shot_spec/2 camera rig (roadmap 10.1); a pan or tilt turns a static rig between its
# start and end pose
RIG = {"static": "static", "push_in": "push", "pull_out": "push", "truck_left": "rail", "truck_right": "rail", "follow": "rail",
       "pan_left": "static", "pan_right": "static", "tilt_up": "static", "tilt_down": "static"}
# which catalogue visual (edit/archetypes.json) a helper archetype draws, by the words of the shot (first hit wins; heuristic)
HELPER_PICK = {
    12: [("LOGISTICS_TETHER_AND_ATTRITION", ("wagon", "bread", "food", "supply", "stomach", "ate ", "farms", "dinner")),
         ("FORMATION_MICRO_MECHANICS", ("square", "formation", "rank", "row after row")),
         ("TACTICAL_UNIT_MANEUVER", ("range", "metres", "meters", "charge", "ridge", "bait", "crest", "guns", "gap", "division"))],
    13: [("MULTI_SCENARIO_VERDICT_MATRIX", ("yes", "no,", "campaign", "battlefield", "question", "two kinds", "philosoph")),
         ("BALLISTIC_RANGE_AND_ENERGY_HUD", ("metres", "meters", "range", "reach", "hit a target", "arrow", "musket", "gun")),
         ("SPLIT_SCREEN_SPEED_RACE", ("horses", "fresh", "speed", "move", "faster")),
         ("ORDER_OF_BATTLE_TELEMETRY_HUD", ("men", "losses", "hundreds", "riders", "count", "army")),
         ("TECH_TREE_DEPENDENCY_GRAPH", ("method", "promoted", "trained", "system"))],
    17: [("WEAPON_AND_MATERIAL_CUTAWAY", ("weapon", "gun", "bow", "musket", "cannon", "artillery"))],
}
HELPER_DEFAULT = {12: "MAP_3D_TERRAIN_FLYOVER", 13: "ORDER_OF_BATTLE_TELEMETRY_HUD", 17: "PRIMARY_SOURCE_DOSSIER_CARD"}
# the order a tie between trigger counts is broken in (the more specific archetype first)
PRIORITY = (10, 1, 2, 16, 9, 14, 6, 7, 8, 15, 5, 11, 4, 3)


@lru_cache(maxsize=None)
def registry() -> dict:
    """The validated registry (schema + ``registry_errors``); raises ``ContractError`` on a broken file."""
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    contracts.validate(doc)
    bad = registry_errors(doc)
    if bad:
        raise contracts.ContractError("archetypes_ic.json: " + "; ".join(bad))
    return doc


def registry_errors(doc: dict) -> list[str]:
    """What the schema cannot say: ids 1-20 once each, the lane counts of roadmap 7.4, the default and fallback lanes inside
    ``lanes``, archetype <-> sub-category links both ways and on a lane the archetype may take, helper ids in the catalogue."""
    from explainer_engine.edit import visual_compensator as VC

    out: list[str] = []
    ids = [a["id"] for a in doc["archetypes"]]
    if sorted(ids) != list(range(1, 21)):
        out.append(f"archetype ids are {sorted(ids)}, not 1..20 once each")
    subs = {s["id"]: s for s in doc["sub_categories"]}
    if len(subs) != len(doc["sub_categories"]):
        out.append("a sub-category id repeats")
    for lane, n in SUB_COUNTS.items():
        got = sum(1 for s in doc["sub_categories"] if s["lane"] == lane)
        if got != n:
            out.append(f"{lane} has {got} sub-categories, roadmap 7.4 lists {n}")
    catalogue = set(VC.ids())
    for a in doc["archetypes"]:
        aid = a["id"]
        if a["default_lane"] not in a["lanes"]:
            out.append(f"archetype {aid}: default lane {a['default_lane']} is not in its lanes")
        if a["fallback"] is not None and a["fallback"]["lane"] not in a["lanes"]:
            out.append(f"archetype {aid}: fallback lane {a['fallback']['lane']} is not in its lanes")
        if ("HELPER" in a["lanes"]) != bool(a["helper_archetypes"]):
            out.append(f"archetype {aid}: a HELPER archetype names catalogue visuals, and only a HELPER archetype does")
        if ("HELPER" in a["lanes"]) != (aid in HELPER_IDS):
            out.append(f"archetype {aid}: HELPER is the lane of archetypes {HELPER_IDS} only (roadmap 7.3)")
        for h in a["helper_archetypes"]:
            if h not in catalogue:
                out.append(f"archetype {aid}: {h} is not in edit/archetypes.json")
            elif h == "PARALLAX_25D_TABLEAU":
                out.append(f"archetype {aid}: the parallax tableau is a STILL_3D plate on /3, never a HELPER visual")
        for sid in a["sub_categories"]:
            sub = subs.get(sid)
            if sub is None:
                out.append(f"archetype {aid}: sub-category {sid} does not exist")
                continue
            if aid not in sub["archetype_examples"]:
                out.append(f"archetype {aid} names {sid}, but {sid} does not list it in archetype_examples")
            if sub["lane"] not in a["lanes"]:
                out.append(f"archetype {aid}: sub-category {sid} is on {sub['lane']}, a lane it never takes")
    by_id = {a["id"]: a for a in doc["archetypes"]}
    for s in doc["sub_categories"]:
        for aid in s["archetype_examples"]:
            if s["id"] not in by_id.get(aid, {}).get("sub_categories", []):
                out.append(f"sub-category {s['id']} lists archetype {aid}, which does not name it")
        if s["lane"] != {"H": "HELPER", "S": "STILL_3D", "V": "VIDEO_3D"}[s["id"][0]]:
            out.append(f"sub-category {s['id']}: its letter does not match lane {s['lane']}")
        if (s["lane"] == "HELPER") != (s["route"] == "H"):
            out.append(f"sub-category {s['id']}: route H is the HELPER lane's and only its (D-116)")
        if s["lane"] == "STILL_3D" and s["route"] != "J5":
            out.append(f"sub-category {s['id']}: a STILL_3D plate is route J5 (D-116), not {s['route']}")
        if s["route_alt"] is not None and s["route_alt"] == s["route"]:
            out.append(f"sub-category {s['id']}: route_alt repeats its route")
    return out


def archetype(aid: int) -> dict:
    return next(a for a in registry()["archetypes"] if a["id"] == aid)


def sub_category(sid: str) -> dict:
    return next(s for s in registry()["sub_categories"] if s["id"] == sid)


ROUTE_OF_LANE = {"STILL_3D": "J5", "HELPER": "H"}  # D-116: a lane whose every sub-category has the one route


def route_of(aid: int, lane: str) -> tuple[str | None, str]:
    """``(sub-category id, route)`` of a shot of archetype ``aid`` on ``lane`` (D-116): the archetype's first sub-category on
    that lane and its registry route; an archetype with no sub-category on the lane (a fallback, e.g. a battle held as a
    STILL_3D plate) takes the lane's one route, and a VIDEO_3D shot with none is J5 (no LTX unless the registry says so)."""
    for sid in archetype(aid)["sub_categories"]:
        s = sub_category(sid)
        if s["lane"] == lane:
            return sid, s["route"]
    return None, ROUTE_OF_LANE.get(lane, "J5")


def _text(shot: dict) -> str:
    act = shot.get("action") or {}
    parts = [shot.get("beat", ""), shot.get("narration", ""), act.get("start", ""), act.get("peak", ""), act.get("settle", "")]
    return " " + " ".join(p for p in parts if p).lower() + " "


def _beat_hits(shot: dict, words: list[str]) -> int:
    """Trigger hits with the beat counted twice: the beat says what the shot is for, the rest only what is in it."""
    return _hits(_text(shot), words) + _hits(" " + shot.get("beat", "").lower() + " ", words)


def _hits(text: str, words: list[str] | tuple[str, ...]) -> int:
    return sum(1 for w in words if re.search(r"(?<![a-z])" + re.escape(w.lower()) + r"(?![a-z])", text))


class ShotDesigner:
    """One episode's designer: knows the cast (named heroes vs crowds), the cold-open scene, the climax scene and the last
    scene of ``doc`` (a ``film_shots/3`` document)."""

    def __init__(self, doc: dict, *, climax_scene: str | None = None):
        if doc.get("schema") != F.V3:
            raise ValueError(f"the shot designer reads {F.V3}, not {doc.get('schema')!r}")
        self.doc = doc
        self.reg = registry()
        self.named = {k for k, v in doc.get("cast", {}).items() if v.get("name")}
        scenes = list(dict.fromkeys(s["scene"] for s in doc["shots"]))
        first = scenes[0] if scenes else None
        self.cold_open = first if any(s.get("teaser_of") for s in doc["shots"] if s["scene"] == first) else None
        self.last_scene = scenes[-1] if len(scenes) > 1 else None
        self.climax = climax_scene if climax_scene is not None else self._climax(doc)
        w = self.reg["planner"]
        self.weights, self.helper_weights = w["intensity"], w["helper_score"]

    @staticmethod
    def _climax(doc: dict) -> str | None:
        """The central turn of template D (variant_plan: a turn whose function is climax/crisis, else the fourth turn)."""
        from explainer_engine.scripting import variant_plan as VP

        segs = VP.segments_from_film_shots(doc)
        turns = VP.turn_ids(segs)
        return turns[3] if len(turns) >= 4 else None

    # --- what the card says ----------------------------------------------------------------------------------------------
    def people(self, shot: dict) -> list[str]:
        return [b["who"] for b in shot.get("blocking", [])]

    def named_in_frame(self, shot: dict) -> list[str]:
        return [w for w in self.people(shot) if w in self.named]

    def cover(self, shot: dict) -> str | None:
        """``on_screen`` when the speaker of the shot's line is in frame with a visible mouth (not the over-the-shoulder
        figure, not partial, not an extreme wide or an insert); ``off_screen`` otherwise; None without a line."""
        line = shot.get("dialogue")
        if not line:
            return None
        who, size = line["who"], shot["frame"]["size"]
        seen = [b for b in shot.get("blocking", []) if b["who"] == who and not b.get("partial")]
        if not seen or size in ("EWS", "INSERT") or shot["frame"].get("over") == who:
            return "off_screen"
        return "on_screen"

    def is_peak(self, shot: dict) -> bool:
        return bool((shot.get("sound") or {}).get("loudest")) and bool(shot.get("action"))

    def visual_archetype(self, shot: dict) -> int:
        """The Blender archetype of a shot (never 12, 13 or 17: those are the planner's HELPER choice)."""
        if shot["scene"] == self.cold_open or shot.get("teaser_of"):
            return 18
        if self.cover(shot) == "on_screen":
            return 4 if len(self.people(shot)) >= 3 else 3
        if shot["scene"] == self.climax and self.is_peak(shot):
            return 19
        if shot["scene"] == self.last_scene:
            return 20
        size = shot["frame"]["size"]
        people, named = self.people(shot), self.named_in_frame(shot)
        crowd = [p for p in people if p not in self.named]
        fits = {
            1: size in WIDE | {"MWS", "MS"} and bool(crowd),
            2: bool(named) and len(named) <= 2 and size not in WIDE | {"INSERT"},
            4: len(people) >= 3,
            5: len(named) == 1 and len(people) == 1 and size in CLOSE | {"MS"},
            6: size in ("INSERT", "ECU") or not people,
            7: size in WIDE | {"MWS"},
            8: True, 9: True, 10: bool(people), 14: True,
            11: size in WIDE,
            15: bool(crowd) and size in WIDE | {"MWS"},
            16: True,
            3: len(named) == 2,
        }
        scored = []
        for aid in PRIORITY:
            if not fits[aid]:
                continue
            n = _beat_hits(shot, archetype(aid)["triggers"])
            if n:
                scored.append((n, -PRIORITY.index(aid), aid))
        if scored:
            return max(scored)[2]
        if size == "INSERT" or not people:
            return 6 if size in ("INSERT", "ECU") else 11
        if len(people) >= 3:
            return 4
        if len(named) == 1 and len(people) == 1:
            return 5
        if len(named) == 2:
            return 3
        if crowd and size in WIDE | {"MWS"}:
            return 15
        return 11 if size in WIDE else 8

    def helper_candidate(self, shot: dict) -> tuple[int, str, float] | None:
        """``(archetype 12/13/17, catalogue visual, score)`` when a Python helper visual could carry this shot, else None. Only
        a narrated, unvoiced shot outside the cold open and the climax's peaks qualifies; a named character in frame
        lowers the score (the beat is theirs)."""
        if shot.get("dialogue") or not shot.get("narration") or shot.get("teaser_of") or shot.get("mode") == "scene":
            return None  # a spoken line, a played scene beat and a teaser belong to the characters
        if shot["scene"] in (self.cold_open, self.last_scene):  # the cold open plays the conflict; the ending is a plate
            return None
        if shot["scene"] == self.climax and self.is_peak(shot):
            return None
        text = _text(shot)
        hits = {aid: _hits(text, archetype(aid)["triggers"]) for aid in HELPER_IDS}
        w = self.helper_weights
        number = bool(F.NUMBER.search(shot["narration"]))
        score = (w["claims"] * bool(shot.get("claims")) + w["number"] * number + w["cue_word"] * max(hits.values())
                 + w["named_character"] * bool(self.named_in_frame(shot)))
        if score < 2:
            return None
        best = max(HELPER_IDS, key=lambda a: (hits[a], a == 13 and number, a == 12))
        if not hits[best]:
            best = 13 if number else 17
        return best, self.helper_visual(best, text), float(score)

    @staticmethod
    def helper_visual(aid: int, text: str) -> str:
        """The catalogue visual whose words the shot names most (the list order breaks a tie); the default without a hit."""
        picks = [(_hits(text, words), -k, visual) for k, (visual, words) in enumerate(HELPER_PICK.get(aid, []))]
        best = max(picks, default=(0, 0, None))
        return best[2] if best[0] else HELPER_DEFAULT[aid]

    def intensity(self, shot: dict, aid: int) -> float:
        """Beat intensity (registry weights, a heuristic): the ranking the planner swaps lanes by, highest stays VIDEO."""
        w = self.weights
        x = w["mode"].get(shot.get("mode"), 0) + archetype(aid)["intensity"]
        x += w["dialogue_on_screen"] * (self.cover(shot) == "on_screen")
        x += w["loudest_sound"] * bool((shot.get("sound") or {}).get("loudest"))
        x += w["action"] * bool(shot.get("action")) + w["reactions"] * bool(shot.get("reactions"))
        x += w["teaser"] * bool(shot.get("teaser_of")) + w["climax_peak"] * (shot["scene"] == self.climax and self.is_peak(shot))
        x += w["no_people"] * (not self.people(shot))
        return float(x)

    def lanes(self, shot: dict, aid: int) -> list[str]:
        """The lanes this shot may take: its archetype's, minus what the card forbids (a seen line needs VIDEO_3D lip-sync, a
        spoken line is never a HELPER visual, a plate longer than BP-109's still cap is not a still)."""
        out = [x for x in archetype(aid)["lanes"] if x != "HELPER"]
        if self.cover(shot) == "on_screen":
            out = [x for x in out if x == "VIDEO_3D"]
        if shot["seconds"] > F.STILL_SHOT_MAX_S:
            out = [x for x in out if x != "STILL_3D"] or out
        return out

    # --- what the card becomes -------------------------------------------------------------------------------------------
    def still_mode(self, shot: dict, aid: int) -> str:
        if shot["frame"].get("camera", "static") != "static":
            return "camera_move_3d"
        a = archetype(aid)
        if a["default_lane"] == "STILL_3D" and a.get("still_mode"):
            return a["still_mode"]
        if a["fallback"] and a["fallback"]["lane"] == "STILL_3D" and a["fallback"]["still_mode"]:
            return a["fallback"]["still_mode"]
        return a.get("still_mode", "hold")

    def camera_rig(self, shot: dict, lane: str, still_mode: str | None) -> str | None:
        """The shot_spec/2 camera rig the router (ICW-07) starts from; None for a HELPER visual."""
        if lane == "HELPER":
            return None
        if lane == "STILL_3D" and still_mode == "dramatic_curve":
            return "dramatic_curve"
        if lane == "STILL_3D" and still_mode == "drift":
            return "dolly"
        return RIG.get(shot["frame"].get("camera", "static"), "static")

    def design(self, shot: dict, aid: int, lane: str, helper_visual: str | None = None) -> dict:
        """The card with its lane fields written for ``lane`` (a copy; the words are never touched)."""
        if lane not in LANES:
            raise ValueError(f"lane {lane!r}")
        s = copy.deepcopy(shot)
        for k in ("still_mode", "render_profile", "lipsync", "helper_archetype", "dialogue_cover", "route", "sub_category", "ltx_clips"):
            s.pop(k, None)
        s["lane"], s["archetype"] = lane, aid
        sid, s["route"] = route_of(aid, lane)   # D-116: the registry's route per sub-category
        if sid is not None:
            s["sub_category"] = sid
        cover = self.cover(shot)
        if lane == "HELPER":
            if shot.get("dialogue"):
                raise ValueError(f"{shot['id']}: a spoken line is never a HELPER visual")
            s["helper_archetype"] = helper_visual or HELPER_DEFAULT[aid]
            s["tier"] = "hold"
            return s
        if lane == "VIDEO_3D":
            if shot.get("tier") not in ("light", "full"):
                s["tier"] = "full"
            s["render_profile"] = shot.get("render_profile") or ("eevee_fast" if s["tier"] == "light" else "eevee_full")
            s["lipsync"] = cover == "on_screen"
        else:
            if cover == "on_screen":
                raise ValueError(f"{shot['id']}: a seen spoken line needs VIDEO_3D lip-sync")
            s["tier"] = "hold"
            s["render_profile"] = shot.get("render_profile") or "eevee_full"
            s["still_mode"] = self.still_mode(shot, aid)
        if cover:
            s["dialogue_cover"] = cover
        return s

    def split_voiced(self, shot: dict) -> list[dict]:
        """A seen line longer than BP-108's dialogue cap becomes the lip-sync close-up (the cap's seconds, the first words)
        and an ``off_screen`` cover shot (``<id>b``: the listener, the rest of the words); the words are split, never
        dropped or repeated, so the speech mix is unchanged (roadmap 8.1)."""
        cap = F.DIALOGUE_SHOT_MAX_S
        if self.cover(shot) != "on_screen" or shot["seconds"] <= cap:
            return [shot]
        words = shot["dialogue"]["text"].split()
        k = max(1, min(len(words) - 1, round(len(words) * cap / shot["seconds"])))
        fps = self.doc["fps"]
        a, b = copy.deepcopy(shot), copy.deepcopy(shot)
        a["seconds"], b["seconds"] = cap, round(shot["seconds"] - cap, 3)
        a["dialogue"]["text"], b["dialogue"]["text"] = " ".join(words[:k]), " ".join(words[k:])
        a["duration_frames"], b["duration_frames"] = round(a["seconds"] * fps), round(b["seconds"] * fps)
        b["id"] = shot["id"] + "b"
        listener = shot["dialogue"].get("to")
        b["blocking"] = [p for p in shot.get("blocking", []) if p["who"] != shot["dialogue"]["who"]] or b.get("blocking", [])
        b["beat"] = f"{shot['beat']} (cover: {listener or 'the room'} listens)"
        for k2 in ("narration", "claims", "teaser_of", "last_frame"):
            b.pop(k2, None)
        if not b["blocking"]:
            b.pop("blocking", None)
        b["frame"] = dict(b["frame"], over=None)
        b["frame"].pop("over")
        return [a, b]
