"""The episode's sound plan (v4.3 plan P7, G4; SP-01 in docs/EPISODE_FIRST.md): one ``sound_plan.json`` per episode that the one
renderer (``audio/stems.py``) plays, whatever the picture route of a shot (R-D: sound does not know the route).

Per shot: its events with their time (an authored ``sound_events`` item, a spoken word, or a visible action in the shot's text),
era-checked (``audio/sfx_planner.filter_sound_events_for_era``); per place (``location_id``): one ambience bed over the run of
shots in that place, with a J/L bridge at every place change (the next place's bed starts ``BRIDGE_S`` before the cut, the old
one tails ``BRIDGE_S`` after it); per segment: one music cue. Every event names a class of ``EVENT_CLASSES``: the one list of
the sounds an episode asks for, so the library is filled once and reused (``needs``).

Sources (``resolve``): library first (``audio/sfx_library``); a procedural numpy sound is a PLACEHOLDER (its manifest source is
``procedural``) and a mix holding one is never shippable; a class with no library sound is MISSING and goes on the needs list
(new takes by the creator's Q5 route: ElevenLabs sound effects, asked and priced first). A Wan clip's own audio
(``source: clip_audio``) is an extra layer only: every shot sits in its place's bed.

Events (AV contract, 2026-11-13, D-135; AV-01..AV-08 in docs/EPISODE_FIRST.md): a shot's placed events are its authored
``sound_events`` and the audio decisions of its visible events (``episode/events.visual_events``: map actions and 2.5D motion,
the one resolver), each carrying its ``event_id``, decision, sync and span. A spoken word or a word of the shot's action text is
only a CANDIDATE (``candidates``: listed for a person, never placed, never a picture event): the narrator saying "falls" does
not shake the picture or play an impact. A 2.5D shot's motion items name what the picture shows (rain, fire, water, leaves):
their ambience joins the place's bed for that shot (``AMBIENCE_OF_EFFECT``), so the bed comes from the place and the picture,
not from the narration.

Scene-aware design (2026-11-13, SP-03..SP-05 in docs/EPISODE_FIRST.md): every shot carries a ``design`` block that answers the ten
questions of the creator's brief from the shot's own data (what is visible, which sounds the place makes, which actions are
heard, near or far, the bed, music or not, the mood, the sync points, what is lowered for the voice, intentional silence),
names one coverage state (``COVERAGE_STATES``) and the layers it uses. A word of the read places an event only when the
picture shows it too (``_visible``: the class's own words or its ``seen`` words in the shot's action, composition or
prompts); a sound only mentioned is listed under ``heard_not_seen`` and never placed. A map shot takes no word events, only
its action layer and its authored (overlay) events: no battle sound because the narrator names a war. Each event gets a distance from the shot's size and the
composition plane its words sit in. Music follows each segment's mood (``segment_mood``): a calm, peaceful segment carries its
ambience without music unless the script asks for it.
"""
from __future__ import annotations

import re
from pathlib import Path

from explainer_engine.audio import duck, sfx_library
from explainer_engine.audio.sfx_planner import (ERA_COMPATIBILITY_TABLE, build_shot_sound_design_metadata,
                                                infer_historical_period)
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.episode import events as E
from explainer_engine.maps import actions as MA

SCHEMA = "sound_plan/1"
BRIDGE_S = 0.5          # engineering default: a J/L bridge of half a second each side of a place change (ED J/L cuts)
BED_FADE_S = 0.65       # the beds' crossfade (kept from the zip's renderer)

# class -> kind, library tags (ALL must match), words that ask for it, the picture event it drives (plan P5.6), era key
EVENT_CLASSES: dict[str, dict] = {
    "footsteps_dirt": {"kind": "foley", "tags": ["footstep", "dirt"], "words": r"walk|walks|walking|trek|trekking|step|steps"},
    "footsteps_stone": {"kind": "foley", "tags": ["footstep", "stone"], "words": r"basalt|ledge|rock shelter|cave floor"},
    "footsteps_grass": {"kind": "foley", "tags": ["footstep", "grass"], "words": r"grass|savanna|meadow"},
    "footsteps_ash": {"kind": "foley", "tags": ["footstep", "ash"], "words": r"ash-covered|through the ash|ashfall"},
    "running": {"kind": "foley", "tags": ["footstep", "run"], "words": r"run|runs|running|sprint|sprints|sprinting|flee|flees|fleeing"},
    "eruption_boom": {"kind": "spot", "tags": ["eruption", "boom"], "words": r"erupt|erupts|eruption|explodes|explosion|blast",
                      "picture_event": "eruption"},
    "eruption_rumble": {"kind": "ambience", "tags": ["eruption", "rumble"], "words": r"caldera|supervolcano|volcano|rumble"},
    "ash_fall": {"kind": "ambience", "tags": ["ash", "fall"], "words": r"ash|pumice|cinder"},
    "thunder": {"kind": "spot", "tags": ["thunder"], "words": r"thunder|lightning", "picture_event": "thunder"},
    "fire": {"kind": "ambience", "tags": ["fire"], "words": r"fire|hearth|embers|ember|torch|flames"},
    "water_waves": {"kind": "ambience", "tags": ["water", "waves"], "words": r"sea|ocean|waves|shore|coast"},
    "river": {"kind": "ambience", "tags": ["water", "river"], "words": r"river|riverbed|stream|wadi"},
    "rain": {"kind": "ambience", "tags": ["rain"], "words": r"rain|monsoon|downpour|storm"},
    "wind": {"kind": "ambience", "tags": ["wind"], "words": r"wind|gust"},
    "crowd": {"kind": "foley", "tags": ["crowd"], "words": r"band|crowd|families|group|people"},
    "stone_tools": {"kind": "foley", "tags": ["stone", "tool"], "words": r"flint|knapping|flaker|microlith|stone tool|stone tools"},
    "bow": {"kind": "foley", "tags": ["bow"], "words": r"bow|arrow|arrows"},
    "impact": {"kind": "spot", "tags": ["impact"], "words": r"crash|slams|falls|collapse|collapses", "picture_event": "impact"},
    # classes some eras forbid (ERA_COMPATIBILITY_TABLE): named so a script that asks for them is refused, not silently kept
    "horse_hooves": {"kind": "foley", "tags": ["horse", "hooves"], "words": r"horse|horses|cavalry|gallop|galloping|hooves"},
    "metal_clash": {"kind": "spot", "tags": ["sword", "metal"], "words": r"sword|swords|sabre|saber|bayonet"},
    # W1 (2026-11-12): the battle and the love scene's sources, real CC0 takes (assets/audio/free_picks_2026-11-12.json)
    "army_march": {"kind": "ambience", "tags": ["army", "march"], "words": r"march|marches|marching"},
    "armour_clink": {"kind": "foley", "tags": ["armour", "clink"], "words": r"armour|armor|armoured|armored|shield|shields"},
    "crowd_shout": {"kind": "ambience", "tags": ["crowd", "shout"], "words": r"charge|charges|attack|attacks"},
    "war_horn": {"kind": "spot", "tags": ["horn", "war"], "words": r"horn|horns|trumpet"},
    "crickets": {"kind": "ambience", "tags": ["crickets"], "words": r"crickets|cicadas"},
    "birds": {"kind": "ambience", "tags": ["birds"], "words": r"birds|birdsong"},
    # overlay motions (BP-192: every motion its own sound); authored by the overlay specs, never read from words
    "ov_pop": {"kind": "foley", "tags": ["pop", "appear"], "words": None},
    "ov_glow": {"kind": "foley", "tags": ["bell", "soft"], "words": None},
    "ov_draw": {"kind": "foley", "tags": ["write", "line"], "words": None},
    "ov_tick": {"kind": "foley", "tags": ["tick", "counter"], "words": None},
    "ov_thud": {"kind": "foley", "tags": ["thud", "soft"], "words": None},
    "ov_slide": {"kind": "foley", "tags": ["paper", "slide"], "words": None},
    "ov_air": {"kind": "foley", "tags": ["air", "swell"], "words": None},
    "ov_swish": {"kind": "foley", "tags": ["swish", "transition"], "words": None},
    "ov_map_open": {"kind": "foley", "tags": ["map", "unfold"], "words": None},
    "music_bed": {"kind": "music", "tags": ["music", "bed"], "words": None},   # the segment cues; never read from words
    # 2026-11-13: the professional library (assets/audio/free_picks_2026-11-13.json)
    "war_drums": {"kind": "spot", "tags": ["drum", "war"], "words": r"drum|drums|drumbeat|wardrums"},
    "battle_cry": {"kind": "spot", "tags": ["scream", "battle"], "words": r"scream|screams|screaming|war cry|battle cry"},
    "horse_neigh": {"kind": "foley", "tags": ["horse", "neigh"], "words": r"neigh|neighs|whinny|rears"},
    "horse_walk": {"kind": "foley", "tags": ["horse", "walk", "hooves"], "words": r"horseback|mounted"},
    "arrow_flight": {"kind": "spot", "tags": ["arrow", "flyby"], "words": r"volley|volleys|arrows fly|arrow flies"},
    "crowd_murmur": {"kind": "ambience", "tags": ["crowd", "murmur"], "words": r"market|marketplace|bazaar|agora|forum|square"},
    "church_bell": {"kind": "spot", "tags": ["bell", "church"], "words": r"bell|bells|church|cathedral|abbey"},
    "harbor": {"kind": "ambience", "tags": ["harbor"], "words": r"harbor|harbour|port|dock|docks|quay"},
    "ship": {"kind": "ambience", "tags": ["ship", "wooden"], "words": r"ship|ships|galley|trireme|fleet|boat|boats"},
    "seabirds": {"kind": "ambience", "tags": ["seabirds"], "words": r"gull|gulls|seabird|seabirds"},
    "storm": {"kind": "ambience", "tags": ["storm"], "words": r"storm|tempest|gale"},
    "forest": {"kind": "ambience", "tags": ["forest"], "words": r"forest|forests|woods|woodland|jungle"},
    "desert": {"kind": "ambience", "tags": ["desert"], "words": r"desert|dune|dunes"},
    "night_insects": {"kind": "ambience", "tags": ["insects", "night"], "words": r"night|nightfall|midnight"},
    "farm": {"kind": "ambience", "tags": ["farm", "village"], "words": r"village|villagers|farm|farmers|herd|livestock"},
    "door_wood": {"kind": "foley", "tags": ["door", "wood"], "words": r"door|doors|gate|gates"},
    "paper_map": {"kind": "foley", "tags": ["paper", "map"], "words": None},       # a map handled on screen; authored
    "riser": {"kind": "transition", "tags": ["riser"], "words": None},           # a designed transition; authored
    "chariot": {"kind": "foley", "tags": ["chariot"], "words": r"chariot|chariots|cart|carts|wagon|wagons"},
    "battle_din": {"kind": "ambience", "tags": ["battle", "crowd"], "words": r"melee|fighting|skirmish"},
    "arrow_volley": {"kind": "spot", "tags": ["arrow", "bow"], "words": r"archers|archer|bowmen"},
    # AV contract (2026-11-13, D-135): the map, data and 2.5D motion classes, authored by the visible events only. Where an
    # overlay class already plays the same takes, ``same_as`` names it (one set of takes, a name that says what moves);
    # ``match`` are the catalog facets tried first, ``tags`` the reported legacy fallback (W1 handoff section 6).
    "map_route_draw": {"kind": "foley", "tags": ["line", "write"], "words": None, "same_as": "ov_draw",
                       "match": {"sound_category": ["foley"], "action_tags": ["draw", "write", "scratch"],
                                 "materials": ["paper"]}},
    "map_pin_set": {"kind": "foley", "tags": ["soft", "thud"], "words": None, "same_as": "ov_thud",
                    "match": {"action_tags": ["pin", "tap", "set_down"], "materials": ["paper", "wood"]}},
    "map_arrive_click": {"kind": "foley", "tags": ["click", "tick"], "words": None,
                         "match": {"sound_category": ["interface"], "action_tags": ["click"]}},
    "map_tokens_shift": {"kind": "foley", "tags": ["paper", "slide"], "words": None, "same_as": "ov_slide",
                         "match": {"action_tags": ["slide", "shift"], "materials": ["paper", "wood"]}},
    "map_line_strain": {"kind": "foley", "tags": ["rope", "strain"], "words": None,
                        "match": {"action_tags": ["strain", "stretch", "creak"], "materials": ["cloth", "plant"]}},
    "map_line_snap": {"kind": "spot", "tags": ["rope", "snap"], "words": None,
                      "match": {"action_tags": ["snap", "break"], "materials": ["cloth", "plant", "wood"]}},
    "data_rise_texture": {"kind": "transition", "tags": ["riser"], "words": None, "same_as": "riser",
                          "match": {"sound_category": ["transitions", "cinematic_textures"], "action_tags": ["rise", "reveal"]}},
    "data_tick": {"kind": "foley", "tags": ["click", "counter", "tick"], "words": None,
                  "match": {"sound_category": ["interface"], "action_tags": ["tick", "count"]}},
    "data_confirm": {"kind": "foley", "tags": ["bell", "soft"], "words": None, "same_as": "ov_glow",
                     "match": {"sound_category": ["interface"], "action_tags": ["confirm", "chime"]}},
    "cloth_flap": {"kind": "foley", "tags": ["cloth", "flap"], "words": None,
                   "match": {"action_tags": ["flap", "flag"], "materials": ["cloth"]}},
}
AV_CLASSES = ("map_route_draw", "map_pin_set", "map_arrive_click", "map_tokens_shift", "map_line_strain", "map_line_snap",
              "data_rise_texture", "data_tick", "data_confirm", "cloth_flap")
# a 2.5D motion item names what the picture shows: its sound joins the shot's bed (the picture, not the narration)
AMBIENCE_OF_EFFECT = {"rain": "rain", "fire_flicker": "fire", "embers": "fire", "water_shimmer": "water_waves",
                      "foliage_sway": "wind", "cloud_drift": "wind", "cloth_flap": "wind", "ash_fall": "ash_fall",
                      "smoke_drift": "wind", "dust": "wind"}
# what the picture must show for a word of the read to place the class (besides the class's own words): a narrator saying
# "erupts" over smoke on the ridge is heard; "erupts" over a face in a cave is not placed (heard_not_seen)
SEEN = {"eruption_boom": r"smoke|plume|lava|ash cloud|crater|volcano|caldera", "thunder": r"storm|lightning|clouds",
        "crowd": r"band|families|group|people|crowd|army|soldiers", "fire": r"hearth|embers|torch|flames|campfire|fire",
        "horse_hooves": r"horse|horses|cavalry|rider|riders|chariot|chariots", "war_horn": r"horn|horns|trumpet|signal",
        "army_march": r"army|column|soldiers|troops|legion|phalanx|march", "metal_clash": r"sword|swords|blade|melee",
        "crowd_shout": r"charge|charges|attack|surge|surges|rush", "battle_din": r"battle|army|armies|soldiers|warriors",
        "chariot": r"chariot|chariots|cart|wagon|wheels", "arrow_volley": r"bow|bows|arrow|arrows|volley"}
_SEEN = {c: re.compile(rf"\b({w})\b", re.I) for c, w in SEEN.items()}
COVERAGE_STATES = ("FULL_LAYERED_DESIGN", "AMBIENCE_ONLY", "FOLEY_AND_AMBIENCE", "ACTION_FOCUSED", "MUSIC_SUPPORTED",
                   "MINIMAL_DESIGN", "INTENTIONAL_SILENCE")
# a segment's mood from its own words (title, purpose, the delivery of its lines, its light): first match in this order wins
MOODS = [("aggressive", r"battle|attack|charge|assault|slaughter|war\b|fight|clash|siege"),
         ("tragic", r"death|dies|died|famine|starv|grief|loss|collapse|extinct|ruin|tragedy|mourning"),
         ("tense", r"tense|threat|danger|fear|panic|escape|flee|hunt|warning|race against|suspense|ominous"),
         ("dark", r"dark|darkness|ash|volcanic winter|cold|grim|bleak|apocalyp"),
         ("mysterious", r"mystery|mysterious|paradox|secret|hidden|clue|riddle|unknown|awe"),
         ("heroic", r"victory|triumph|survive|survivors|hope|rescue|heroic|endure"),
         ("epic", r"empire|epic|vast|giant|supervolcano|world|eight billion|continent"),
         ("reflective", r"reflect|memory|remember|quiet|today|legacy|lesson|hushed"),
         ("peaceful", r"peaceful|calm|village life|harvest|gentle|morning|idyll|market day")]
_MOODS = [(m, re.compile(w, re.I)) for m, w in MOODS]
MUSIC_MOODS = {"aggressive", "tragic", "tense", "dark", "mysterious", "heroic", "epic", "reflective", "neutral"}
# shot size -> how far the shot's events sound (engineering default: the camera's distance to the action)
SHOT_DISTANCE = {"extreme_wide": "distant", "wide": "distant", "establishing": "distant", "full": "medium", "medium_wide": "medium",
                 "medium": "medium", "medium_close_up": "close", "close_up": "close", "extreme_close_up": "close"}
_COMPILED = {c: re.compile(rf"\b({v['words']})\b", re.I) for c, v in EVENT_CLASSES.items() if v["words"]}
# the era table speaks in the planner's event names; these classes are those events
_ERA_NAMES = {"footsteps_dirt": "footstep_dirt", "footsteps_stone": "footstep_stone", "footsteps_grass": "footstep_grass",
              "horse_hooves": "horse_hooves_gallop", "metal_clash": "sword_metal_clash"}
# library tags that place a sound in a later world: a take carrying one never plays in that era (the burnt garage's fire
# crackle is not a Pleistocene hearth)
_MODERN_TAGS = {"city", "street", "traffic", "garage", "motel", "highway", "warehouse", "factory", "office", "courthouse",
                "parking", "electric", "battery", "industrial", "workshop", "pool"}
ERA_FOREIGN_TAGS = {"prehistoric_pleistocene": _MODERN_TAGS | {"clock", "ui", "notebook", "pencil"},
                    "bronze_age": _MODERN_TAGS}   # W1: the Trojan plain and the cliff-edge scene (the motel pool's crickets stay out)
BED_OF_WEATHER = {"volcanic_ash_storm_and_wind": ["ash_fall", "wind"], "heavy_rain_and_wind": ["rain", "wind"],
                  "enclosed_draft": ["fire"], "freezing_wind_and_snow": ["wind"], "high_altitude_wind": ["wind"]}


def _shot_lines(shot: dict, script: dict) -> str:
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    return " ".join(str(lines.get(lid, {}).get("text", "")) for lid in shot.get("audio_line_ids", []))


def _action_text(shot: dict) -> str:
    return " ".join(str(shot.get(k) or "") for k in ("action_start_state", "action_end_state", "narrative_purpose"))


def _visible(shot: dict) -> str:
    """Everything the picture is said to show: the action, the purpose, the composition planes and the prompts."""
    comp = shot.get("screen_composition") or {}
    img = shot.get("image_prompt") or {}
    vid = shot.get("video_prompt") or {}
    parts = [_action_text(shot)] + [str(comp.get(k) or "") for k in ("foreground", "midground", "background")]
    parts += [str(img.get("start_frame_prompt") or "") if isinstance(img, dict) else str(img),
              str(vid.get("motion_prompt") or "") if isinstance(vid, dict) else str(vid), str(shot.get("visual") or "")]
    return " ".join(parts)


def is_map(shot: dict) -> bool:
    return shot.get("route") == "map_action" or shot.get("visual_type") == "map_visualization"


def seen_in(cls: str, text: str) -> bool:
    rx = _COMPILED.get(cls)
    return bool((rx and rx.search(text)) or (cls in _SEEN and _SEEN[cls].search(text)))


def distance_of(cls: str, shot: dict) -> str:
    """close | medium | distant: the plane of the composition that names the class, else the shot's size."""
    comp = shot.get("screen_composition") or {}
    for plane, d in (("foreground", "close"), ("midground", "medium"), ("background", "distant")):
        if seen_in(cls, str(comp.get(plane) or "")):
            return d
    size = str((shot.get("camera_spec") or {}).get("shot_size") or "medium")
    return SHOT_DISTANCE.get(size, "medium")


def segment_mood(seg: dict, lines: list[dict], shots: list[dict]) -> tuple[str, str]:
    """(mood, basis) of a segment from its own words; ``neutral`` when nothing names one. An authored ``mood`` wins."""
    if seg.get("mood"):
        return str(seg["mood"]), "authored"
    text = " ".join([str(seg.get("title") or ""), str(seg.get("narrative_purpose") or "")]
                    + [str(ln.get("delivery_direction") or "") for ln in lines]
                    + [str(s.get("lighting_and_time") or "") + " " + _action_text(s) for s in shots])
    for mood, rx in _MOODS:
        m = rx.search(text)
        if m:
            return mood, f"word:{m.group(0).lower()}"
    return "neutral", "default"


def _forbidden(era: str) -> set[str]:
    return set(ERA_COMPATIBILITY_TABLE.get(era, {}).get("forbidden_events", ()))


def _event(cls: str, at_s: float, basis: str, fps: int, **extra) -> dict:
    spec = EVENT_CLASSES[cls]
    ev = {"class": cls, "kind": spec["kind"], "at_s": round(at_s, 3), "at_frame": int(round(at_s * fps)), "basis": basis}
    if spec.get("picture_event"):
        ev["picture_event"] = spec["picture_event"]
    ev.update(extra)
    return ev


def _visual(ev: dict, fps: int) -> dict | None:
    """The sound plan's event for one visible event, or None when it places nothing (ambience_only, music_only, silence and
    review are recorded on the shot, not placed)."""
    a = ev["audio"]
    if a["decision"] not in E.NEEDS_CLASS:
        return None
    cls = a["class"]
    if cls not in EVENT_CLASSES:
        raise ContractError(f"{ev['shot_id']}: event {ev['event_id']} names the class {cls!r}, which EVENT_CLASSES does not list")
    f0 = ev["end_frame"] - 1 if a.get("sync") == "end" else ev["start_frame"]
    extra = {"event_id": ev["event_id"], "decision": a["decision"], "sync": a.get("sync", "onset"),
             "purpose": a.get("purpose"), "op": ev["op"], "audio_basis": ev["audio_basis"],
             "span_frames": [ev["start_frame"], ev["end_frame"]]}
    if a.get("sync") == "span":
        extra["dur_s"] = round((ev["end_frame"] - ev["start_frame"]) / fps, 3)
    out = _event(cls, f0 / fps, f"visual:{ev['op']}:{ev['timing']['start']}", fps, **extra)
    out["at_frame"] = int(f0)
    return out


def shot_events(shot: dict, script: dict, fps: int, era: str, spine: list[dict] | None = None) -> tuple[list[dict], list]:
    """The placed events of one shot (shot-relative times): its authored ``sound_events`` and the audio decisions of its
    visible events. Words of the read and of the action text are candidates only (``_CANDIDATES``)."""
    sid = shot.get("shot_id", "?")
    dur = float(shot.get("target_duration_seconds") or 0.0)
    frames = max(1, int(round(dur * fps)))
    events, blocked, seen = [], [], set()
    for k, item in enumerate(shot.get("sound_events") or []):
        cls = item.get("class") or _class_of(item.get("what", ""))
        if cls is None:
            raise ContractError(f"{sid}: sound event {item.get('what')!r} names no class of EVENT_CLASSES; add the class "
                                f"once (so the library is filled once) or name it")
        if cls not in EVENT_CLASSES:
            raise ContractError(f"{sid}: sound event class {cls!r} is not in EVENT_CLASSES")
        at = float(item.get("at_s", 0.0))
        if at > dur + 1e-6:
            raise ContractError(f"{sid}: sound event {cls} at {at} s is after the shot's end ({dur} s)")
        extra = {k_: item[k_] for k_ in ("library_id", "source", "what", "distance", "dur_s", "purpose") if k_ in item}
        if item.get("picture_event"):     # the picture shakes or flashes on it: its purpose is sync (BP-55)
            extra["picture_event"] = item["picture_event"]
            extra.setdefault("purpose", "sync")
        extra.update(event_id=item.get("event_id") or f"{sid}.S{k + 1}", decision="sfx" if EVENT_CLASSES[cls]["kind"] !=
                     "ambience" else "ambience_only", sync="span" if item.get("dur_s") else "onset", audio_basis="authored")
        events.append(_event(cls, at, "authored", fps, **extra))
        seen.add(cls)
    vis = E.visual_events(shot, script, spine, fps) if (shot.get("actions") or shot.get("motion_imitation")) else []
    decisions = []
    for ev in vis:
        placed = _visual(ev, fps)
        decisions.append({"event_id": ev["event_id"], "op": ev["op"], "decision": ev["audio"]["decision"],
                          "class": ev["audio"].get("class"), "why": ev["audio"].get("why"), "audio_basis": ev["audio_basis"],
                          "frames": [ev["start_frame"], ev["end_frame"]], "placed": placed is not None})
        if placed is not None:
            events.append(placed)
        elif ev["audio"]["decision"] == "ambience_only" and ev["source"] == "motion_imitation" \
                and AMBIENCE_OF_EFFECT.get(ev["op"]) and AMBIENCE_OF_EFFECT[ev["op"]] not in seen:
            cls = AMBIENCE_OF_EFFECT[ev["op"]]
            events.append(_event(cls, 0.0, f"picture:{ev['op']}", fps, event_id=ev["event_id"], decision="ambience_only",
                                 sync="span", audio_basis=ev["audio_basis"], dur_s=round(dur, 3)))
            seen.add(cls)
    _DECISIONS[sid] = decisions
    # candidates: what the words name (the read, then the action text); listed for a person, never placed
    words = MA.shot_words(shot, script)
    starts, word_basis = MA.word_frames(words, frames, spine)
    visible = _visible(shot)
    heard_only, cands = [], []
    for i, w in enumerate(words if not is_map(shot) else []):
        for cls, rx in _COMPILED.items():
            if not rx.fullmatch(w) or any(c["class"] == cls for c in cands):
                continue
            if not seen_in(cls, visible):
                if cls not in heard_only:
                    heard_only.append(cls)
                continue
            cands.append({"class": cls, "source": "word", "word": w, "at_s": round(starts[i] / fps, 3),
                          "basis": word_basis, "why": "a word of the read names it and the picture shows it: a person "
                          "authors the event (AV-07); words never place a sound"})
    text = _action_text(shot)
    for cls, rx in _COMPILED.items():
        if any(c["class"] == cls for c in cands) or not rx.search(text):
            continue
        cands.append({"class": cls, "source": "action_text", "at_s": None, "basis": "text",
                      "why": "the shot's action text names it: a person authors the event with its frame (AV-07)"})
    _CANDIDATES[sid] = [c for c in cands if c["class"] not in seen]
    for ev in events:
        ev["distance"] = ev.get("distance") or distance_of(ev["class"], shot)
    _HEARD[sid] = heard_only
    forbidden = _forbidden(era)
    kept = []
    for ev in events:
        if _ERA_NAMES.get(ev["class"], ev["class"]) in forbidden:
            blocked.append({"shot_id": sid, "class": ev["class"], "era": era, "event_id": ev.get("event_id")})
        else:
            kept.append(ev)
    return sorted(kept, key=lambda e: (e["at_s"], e["class"])), blocked


_DECISIONS: dict[str, list[dict]] = {}   # shot id -> every visible event's decision (last build only)
_CANDIDATES: dict[str, list[dict]] = {}  # shot id -> classes a word names (last build only): never placed


_HEARD: dict[str, list[str]] = {}     # shot id -> classes the read names that the picture does not show (last build only)


def heard_not_seen(shot_id: str) -> list[str]:
    return list(_HEARD.get(shot_id, []))


def coverage_state(events: list[dict], music_on: bool, is_map_shot: bool, silence: str | None) -> str:
    """One of ``COVERAGE_STATES`` from what the shot really carries (SP-04)."""
    if silence:
        return "INTENTIONAL_SILENCE"
    kinds = {e["kind"] for e in events if e.get("source") != "clip_audio"}
    if {"spot", "foley"} & kinds and music_on:
        return "FULL_LAYERED_DESIGN"
    if "spot" in kinds or "transition" in kinds:
        return "ACTION_FOCUSED"
    if "foley" in kinds:
        return "FOLEY_AND_AMBIENCE"
    if music_on:
        return "MUSIC_SUPPORTED"
    if is_map_shot:
        return "MINIMAL_DESIGN"
    return "AMBIENCE_ONLY"


def design_of(sh: dict, out: dict, bed: dict, mood: str, music_on: bool, music_reason: str) -> dict:
    """The shot's sound design: the ten answers of the creator's brief, the coverage state and the layers with reasons."""
    sd = sh.get("sound_design") or {}
    silence = sd.get("silence") or sh.get("intentional_silence")
    if silence is True:
        raise ContractError(f"{out['shot_id']}: intentional silence needs its reason (a sentence), not just true")
    evs = out["events"]
    spots = [e for e in evs if e["kind"] == "spot"]
    foley_ = [e for e in evs if e["kind"] == "foley"]
    amb = [e["class"] for e in evs if e["kind"] == "ambience"]
    trans = [e for e in evs if e["kind"] == "transition"]
    voiced = bool(out["audio_line_ids"])
    near = sorted({e["distance"] for e in evs if e.get("distance")})
    state = coverage_state(evs, music_on, is_map(sh), silence)

    def layer(active, reason):
        return {"active": bool(active), "reason": reason}

    layers = {
        "narration": layer(voiced, f"lines {', '.join(out['audio_line_ids'])}" if voiced else "no line in this shot"),
        "ambience": layer(not silence, (f"bed {bed['bed_id']} ({', '.join(bed['classes'])})" + (f" + {', '.join(amb)}" if amb
                          else "")) if not silence else "room tone only: " + str(silence)),
        "foley": layer(foley_ and not silence, ", ".join(f"{e['class']}@{e['at_s']}s ({e['basis']})" for e in foley_)
                       or "no visible body or object movement named"),
        "spot": layer(spots and not silence, ", ".join(f"{e['class']}@{e['at_s']}s ({e['basis']})" for e in spots)
                      or "no visible story event named"),
        "music": layer(music_on and not silence, music_reason),
        "transition": layer(trans, ", ".join(e["class"] for e in trans) or "a plain cut (no designed transition authored)"),
    }
    answers = {
        "visible": _visible(sh).strip()[:300] or "(the shot names no action)",
        "environment_sounds": bed["classes"] + amb,
        "audible_actions": [e["class"] for e in foley_ + spots],
        "perspective": near or ["(no event)"],
        "ambience_layer": layers["ambience"]["reason"],
        "music_supports": layers["music"]["reason"],
        "emotion": mood,
        "sync_points": [{"class": e["class"], "at_s": e["at_s"], "basis": e["basis"]} for e in evs if e["kind"] != "ambience"],
        "protect_voice": (f"music ducks by {duck.DEPTH_DB:.0f} dB and the bed by its BP-53 depth under the lines") if voiced
                         else "no line: nothing to lower",
        "silence": str(silence) if silence else "none (the bed and room tone carry the shot)",
    }
    answers["visual_events"] = [f"{d['event_id']} {d['op']}: {d['decision']}" + (f" {d['class']}" if d.get('class') else "")
                                for d in out.get("visual_events", [])]
    answers["candidates"] = [f"{c['class']} ({c['source']})" for c in out.get("candidates", [])]
    return {"state": state, "layers": layers, "answers": answers, "heard_not_seen": heard_not_seen(out["shot_id"]),
            **({"silence_reason": str(silence)} if silence else {})}


def music_decision(seg: dict, mood: str) -> tuple[bool, str]:
    """Music only where it supports the scene (SP-05): an authored ``music`` (true/false) wins; a peaceful or joyful segment
    lets its ambience carry it; every other mood, and a segment whose mood nothing names, keeps its cue."""
    if isinstance(seg.get("music"), bool):
        return seg["music"], f"authored music={seg['music']}"
    if mood in ("peaceful", "joyful"):
        return False, f"{mood} segment: the place's ambience carries it, no score"
    return True, f"{mood} segment: a {mood} cue supports it" if mood != "neutral" else "no mood named: the segment's cue"


def _class_of(what: str) -> str | None:
    if (what or "").strip() in EVENT_CLASSES:     # the class's own id names it (an authored event of the AV contract)
        return what.strip()
    for cls, rx in _COMPILED.items():
        if rx.search(what or ""):
            return cls
    return None


def build(script: dict, *, fps: int = 24, spines: dict | None = None, routes: dict | None = None) -> dict:
    """The plan: shots with absolute times and events, beds per place with J/L bridges, music per segment, the needs."""
    era = infer_historical_period(script)
    _HEARD.clear()
    _DECISIONS.clear()
    _CANDIDATES.clear()
    shots, blocked, beds = [], [], []
    t = 0.0
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    seg_shots: dict = {}
    for sh in script.get("shots", []):
        seg_shots.setdefault(sh.get("segment_id"), []).append(sh)
    moods, musics = {}, {}
    for seg in script.get("segments", []):
        ss = seg_shots.get(seg.get("segment_id"), [])
        seg_lines = [lines[i] for s_ in ss for i in s_.get("audio_line_ids") or [] if i in lines]
        moods[seg.get("segment_id")] = segment_mood(seg, seg_lines, ss)
        musics[seg.get("segment_id")] = music_decision(seg, moods[seg.get("segment_id")][0])
    for sh in script.get("shots", []):
        sid = sh.get("shot_id", "?")
        dur = float(sh.get("target_duration_seconds") or 0.0)
        if dur <= 0:
            raise ContractError(f"{sid}: a shot without a duration has no place on the sound clock")
        evs, bl = shot_events(sh, script, fps, era, (spines or {}).get(sid))
        blocked += bl
        meta = build_shot_sound_design_metadata(sh, shot_start_sec=t, historical_period=era)
        place = sh.get("location_id") or "loc_unknown"
        route = (routes or {}).get(sid) or sh.get("route")
        shots.append({"shot_id": sid, "segment_id": sh.get("segment_id"), "start_s": round(t, 3), "dur_s": round(dur, 3),
                      "route": route, "place": place, "room": "cave" if meta["spatial_context"].startswith("indoor")
                      else "outdoor", "weather": meta["weather"], "surface": meta["surface"],
                      "audio_line_ids": list(sh.get("audio_line_ids") or []), "events": evs,
                      "visual_events": list(_DECISIONS.get(sid, [])), "candidates": list(_CANDIDATES.get(sid, []))})
        if beds and beds[-1]["place"] == place:
            beds[-1]["end_s"] = round(t + dur, 3)
            beds[-1]["shot_ids"].append(sid)
        else:
            beds.append({"bed_id": f"BED_{len(beds) + 1:02d}_{place}", "place": place, "room": shots[-1]["room"],
                         "classes": BED_OF_WEATHER.get(meta["weather"], ["wind"]), "start_s": round(t, 3),
                         "end_s": round(t + dur, 3), "shot_ids": [sid]})
        mood = moods.get(sh.get("segment_id"), ("neutral", "default"))[0]
        on, why = musics.get(sh.get("segment_id"), (True, "no segment: the cue"))
        shots[-1]["mood"] = mood
        shots[-1]["design"] = design_of(sh, shots[-1], beds[-1], mood, on, why)
        shots[-1]["transition_out"] = sh.get("transition_out")
        t += dur
    bridges = []
    for a, b in zip(beds, beds[1:]):
        cut = b["start_s"]
        bridges.append({"at_s": cut, "from": a["bed_id"], "to": b["bed_id"], "j_start_s": round(max(0.0, cut - BRIDGE_S), 3),
                        "l_end_s": round(min(t, cut + BRIDGE_S), 3)})
        a["tail_s"], b["lead_s"] = BRIDGE_S, BRIDGE_S
    music = []
    by_seg: dict[str, list] = {}
    for s in shots:
        by_seg.setdefault(s["segment_id"], []).append(s)
    for seg in script.get("segments", []):
        ss = by_seg.get(seg.get("segment_id"), [])
        if not ss:
            continue
        a, b = ss[0]["start_s"], ss[-1]["start_s"] + ss[-1]["dur_s"]
        on, why = musics[seg["segment_id"]]
        if not on:
            continue
        mood, basis = moods[seg["segment_id"]]
        music.append({"music_id": f"MUS_{seg['segment_id']}", "segment_id": seg["segment_id"], "start_s": a,
                      "end_s": round(b, 3), "mood": mood, "mood_basis": basis, "reason": why,
                      "factual_status": seg.get("factual_status") or "actual_history"})
    coverage: dict[str, int] = {}
    for s_ in shots:
        coverage[s_["design"]["state"]] = coverage.get(s_["design"]["state"], 0) + 1
    return {"schema": SCHEMA, "episode_id": script.get("episode_id"), "era": era, "fps": fps, "duration_s": round(t, 3),
            "shots": shots, "beds": beds, "bridges": bridges, "music": music, "blocked_era_events": blocked,
            "segment_moods": {k: {"mood": v[0], "basis": v[1], "music": musics[k][0], "music_reason": musics[k][1]}
                              for k, v in moods.items()}, "coverage": coverage,
            "classes": sorted({e["class"] for s in shots for e in s["events"]} | {c for b in beds for c in b["classes"]}
                              | ({"music_bed"} if music else set())),
            "av": {"resolver": E.RESOLVER_VERSION, "contract": script.get("av_contract") or "legacy",
                   "decisions": _count([d["decision"] for s in shots for d in s["visual_events"]]),
                   "review_required": [d["event_id"] for s in shots for d in s["visual_events"]
                                       if d["decision"] == "review_required"],
                   "candidates": sum(len(s["candidates"]) for s in shots)}}


def _count(xs: list) -> dict:
    out: dict = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return out


def _origin(item: dict) -> str:
    src = item.get("source")
    return (src.get("kind") if isinstance(src, dict) else src) or "unknown"


def _words_of(item: dict) -> set[str]:
    """What a take says about its world: its tags, the words of its id and of the prompt it was made from."""
    src = item.get("source") if isinstance(item.get("source"), dict) else {}
    text = " ".join([item.get("id", ""), str(src.get("prompt", ""))]).lower()
    return set(item.get("tags", [])) | set(re.findall(r"[a-z]+", text))


def _facet_hit(item: dict, match: dict) -> bool:
    """A take whose own (not inferred) catalog carries every facet the class names (any value of each)."""
    cat = item.get("catalog") or {}
    if not cat or cat.get("inferred"):
        return False
    for key, want in match.items():
        have = cat.get(key)
        have = set(have) if isinstance(have, list) else ({have} if have else set())
        if not have & set(want):
            return False
    return True


def _candidates(cls: str, root: Path) -> tuple[list[dict], str]:
    """(takes, basis): catalog facets first (``facets``), else the class's legacy tags (``legacy_tags``, reported)."""
    spec = EVENT_CLASSES[cls]
    usable = sfx_library.find(Path(root))
    if spec.get("match"):
        hit = [i for i in usable if _facet_hit(i, spec["match"])]
        if hit:
            return hit, "facets"
    return sfx_library.find(Path(root), tags=spec["tags"]), "legacy_tags"


def resolve(plan: dict, library_root: Path) -> dict:
    """Pick a library sound for every class: ``library`` (a real take), ``placeholder`` (procedural only) or ``missing``.
    Each source says how it was matched (catalog ``facets`` or the reported ``legacy_tags`` fallback), how many of its takes
    carry an inferred catalog, their technical QC and whether a person has listened (three statuses, never merged)."""
    out = {}
    foreign = ERA_FOREIGN_TAGS.get(plan.get("era"), set())
    for cls in plan["classes"]:
        tags = EVENT_CLASSES[cls]["tags"]
        found, basis = _candidates(cls, library_root)
        found = [i for i in found if not foreign & _words_of(i)]
        real = [i for i in found if _origin(i) != "procedural"]
        info = {"match": basis, "same_as": EVENT_CLASSES[cls].get("same_as")}
        if real:
            out[cls] = {"status": "library", "ids": [i["id"] for i in real], "origin": _origin(real[0]), **info,
                        "inferred_catalog": sum(1 for i in real if (i.get("catalog") or {}).get("inferred")),
                        "qc": _count([(i.get("qc") or {}).get("status") or "NOT_RUN" for i in real]),
                        "human": _count([(i.get("review") or {}).get("human") or "not_listened" for i in real])}
        elif found:
            out[cls] = {"status": "placeholder", "ids": [i["id"] for i in found], "origin": "procedural", **info}
        else:
            out[cls] = {"status": "missing", "ids": [], "tags": tags, **info}
    return out


def needs(sources: dict) -> list[dict]:
    """Every class without a real library take, listed once: the shopping list for new takes (asked and priced first)."""
    return [{"class": c, "status": s["status"], "tags": EVENT_CLASSES[c]["tags"], "kind": EVENT_CLASSES[c]["kind"]}
            for c, s in sorted(sources.items()) if s["status"] != "library"]


def shippable(sources: dict, plan: dict) -> tuple[bool, list[str]]:
    """A mix ships only from real sounds: no placeholder and nothing missing. (Every shot sits in a place's bed, so a clip's
    own audio is never a shot's only sound.)"""
    why = [f"{c}: {s['status']}" for c, s in sorted(sources.items()) if s["status"] != "library"]
    return not why, why


def write(plan: dict, sources: dict, episode_dir: Path) -> Path:
    path = Path(episode_dir) / "audio" / "sound_plan.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, why = shippable(sources, plan)
    write_json_atomic(path, dict(plan, sources=sources, needs=needs(sources), shippable=ok, not_shippable_because=why))
    return path
