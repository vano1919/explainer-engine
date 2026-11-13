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
"""
from __future__ import annotations

import re
from pathlib import Path

from explainer_engine.audio import sfx_library
from explainer_engine.audio.sfx_planner import (ERA_COMPATIBILITY_TABLE, build_shot_sound_design_metadata,
                                                infer_historical_period)
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.maps import actions as MA

SCHEMA = "sound_plan/1"
BRIDGE_S = 0.5          # engineering default: a J/L bridge of half a second each side of a place change (ED J/L cuts)
BED_FADE_S = 0.65       # the beds' crossfade (kept from the zip's renderer)
ACTION_AT = 0.2         # an event read from the shot's visible action lands at this share of the shot (no word to hang on)

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
}
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


def _forbidden(era: str) -> set[str]:
    return set(ERA_COMPATIBILITY_TABLE.get(era, {}).get("forbidden_events", ()))


def _event(cls: str, at_s: float, basis: str, fps: int, **extra) -> dict:
    spec = EVENT_CLASSES[cls]
    ev = {"class": cls, "kind": spec["kind"], "at_s": round(at_s, 3), "at_frame": int(round(at_s * fps)), "basis": basis}
    if spec.get("picture_event"):
        ev["picture_event"] = spec["picture_event"]
    ev.update(extra)
    return ev


def shot_events(shot: dict, script: dict, fps: int, era: str, spine: list[dict] | None = None) -> tuple[list[dict], list]:
    """The events of one shot (shot-relative times): authored first, then spoken words, then the visible action."""
    sid = shot.get("shot_id", "?")
    dur = float(shot.get("target_duration_seconds") or 0.0)
    frames = max(1, int(round(dur * fps)))
    events, blocked, seen = [], [], set()
    for item in shot.get("sound_events") or []:
        cls = item.get("class") or _class_of(item.get("what", ""))
        if cls is None:
            raise ContractError(f"{sid}: sound event {item.get('what')!r} names no class of EVENT_CLASSES; add the class "
                                f"once (so the library is filled once) or name it")
        at = float(item.get("at_s", 0.0))
        if at > dur + 1e-6:
            raise ContractError(f"{sid}: sound event {cls} at {at} s is after the shot's end ({dur} s)")
        extra = {k: item[k] for k in ("library_id", "source", "what") if k in item}
        if item.get("picture_event"):
            extra["picture_event"] = item["picture_event"]
        events.append(_event(cls, at, "authored", fps, **extra))
        seen.add(cls)
    words = MA.shot_words(shot, script)
    starts, word_basis = MA.word_frames(words, frames, spine)
    for i, w in enumerate(words):
        for cls, rx in _COMPILED.items():
            if cls in seen or not rx.fullmatch(w):
                continue
            events.append(_event(cls, starts[i] / fps, f"word:{w}:{word_basis}", fps))
            seen.add(cls)
    text = _action_text(shot)
    for cls, rx in _COMPILED.items():
        if cls in seen or not rx.search(text):
            continue
        events.append(_event(cls, ACTION_AT * dur, "action", fps))
        seen.add(cls)
    forbidden = _forbidden(era)
    kept = []
    for ev in events:
        if _ERA_NAMES.get(ev["class"], ev["class"]) in forbidden:
            blocked.append({"shot_id": sid, "class": ev["class"], "era": era})
        else:
            kept.append(ev)
    return sorted(kept, key=lambda e: (e["at_s"], e["class"])), blocked


def _class_of(what: str) -> str | None:
    for cls, rx in _COMPILED.items():
        if rx.search(what or ""):
            return cls
    return None


def build(script: dict, *, fps: int = 24, spines: dict | None = None, routes: dict | None = None) -> dict:
    """The plan: shots with absolute times and events, beds per place with J/L bridges, music per segment, the needs."""
    era = infer_historical_period(script)
    shots, blocked, beds = [], [], []
    t = 0.0
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
                      "audio_line_ids": list(sh.get("audio_line_ids") or []), "events": evs})
        if beds and beds[-1]["place"] == place:
            beds[-1]["end_s"] = round(t + dur, 3)
            beds[-1]["shot_ids"].append(sid)
        else:
            beds.append({"bed_id": f"BED_{len(beds) + 1:02d}_{place}", "place": place, "room": shots[-1]["room"],
                         "classes": BED_OF_WEATHER.get(meta["weather"], ["wind"]), "start_s": round(t, 3),
                         "end_s": round(t + dur, 3), "shot_ids": [sid]})
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
        music.append({"music_id": f"MUS_{seg['segment_id']}", "segment_id": seg["segment_id"], "start_s": a,
                      "end_s": round(b, 3), "mood": seg.get("factual_status") or "actual_history"})
    return {"schema": SCHEMA, "episode_id": script.get("episode_id"), "era": era, "fps": fps, "duration_s": round(t, 3),
            "shots": shots, "beds": beds, "bridges": bridges, "music": music, "blocked_era_events": blocked,
            "classes": sorted({e["class"] for s in shots for e in s["events"]} | {c for b in beds for c in b["classes"]}
                              | ({"music_bed"} if music else set()))}


def _origin(item: dict) -> str:
    src = item.get("source")
    return (src.get("kind") if isinstance(src, dict) else src) or "unknown"


def _words_of(item: dict) -> set[str]:
    """What a take says about its world: its tags, the words of its id and of the prompt it was made from."""
    src = item.get("source") if isinstance(item.get("source"), dict) else {}
    text = " ".join([item.get("id", ""), str(src.get("prompt", ""))]).lower()
    return set(item.get("tags", [])) | set(re.findall(r"[a-z]+", text))


def resolve(plan: dict, library_root: Path) -> dict:
    """Pick a library sound for every class: ``library`` (a real take), ``placeholder`` (procedural only) or ``missing``."""
    out = {}
    foreign = ERA_FOREIGN_TAGS.get(plan.get("era"), set())
    for cls in plan["classes"]:
        tags = EVENT_CLASSES[cls]["tags"]
        found = [i for i in sfx_library.find(Path(library_root), tags=tags) if not foreign & _words_of(i)]
        real = [i for i in found if _origin(i) != "procedural"]
        if real:
            out[cls] = {"status": "library", "ids": [i["id"] for i in real], "origin": _origin(real[0])}
        elif found:
            out[cls] = {"status": "placeholder", "ids": [i["id"] for i in found], "origin": "procedural"}
        else:
            out[cls] = {"status": "missing", "ids": [], "tags": tags}
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
