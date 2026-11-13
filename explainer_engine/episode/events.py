"""One event contract for picture and sound (AV-01..AV-08, docs/EPISODE_FIRST.md; D-135).

Every visible event of a shot (a map action of ``ShotSpec.actions``, a 2.5D motion of ``ShotSpec.motion_imitation``) is ONE
event with an id, a half-open frame span ``[start_frame, end_frame)`` on the episode's clock (``episode/timing``'s measured word
spine when the read exists, else the estimated word times of ``maps/actions.word_frames``) and exactly one audio decision.
The map renderer, the 2.5D renderer, the sound plan and the QA read the same list from ``visual_events`` (R-AV: one resolver),
so a sound can only land where the picture moves, and a word of the narration can never make a sound by itself.

The audio decision (``audio``): ``decision`` one of ``DECISIONS``; ``class`` (a class of ``episode/sound_plan.EVENT_CLASSES``,
required for ``sfx`` and ``ui_cue``); ``sync`` (``onset``: the sound starts on ``start_frame``; ``span``: it lasts the span, a
continuous action; ``end``: it lands on the arrival, ``end_frame - 1``); ``purpose`` (BP-55: clarify, humour, transition, sync);
``why`` (required for ``silent_by_design`` and ``review_required``). Camera moves are silent by default.

Contract (``script["av_contract"] == CONTRACT``): every action and motion item carries ``event_id`` and ``audio`` and the rows of
``contract_rows`` FAIL without them. An older script (no ``av_contract``) still runs: its events get derived ids
(``<shot>.A1``, ``<shot>.M1``) and the default decision of their kind (``DEFAULTS``), and the report says so (REVIEW).

Timing: an event starts on its ``at_word`` (actions: searched from the previous action's word on, as ``maps/actions.plan``
always did; motion items: from the first word), or on ``at_frame``; ``until_word`` ends it on the start of the word after the
phrase (the last word of the line: its start plus one word's length). Without ``until_word`` a continuous action lasts until the
next action of the shot starts or the line ends (never shorter than ``ANIM_FRAMES``); an instant one lasts ``ANIM_FRAMES``.

Anchors that follow the read (Fable audit 2026-11-13, FA-06 / P1): the read changes every shot's length, so an anchor in
absolute frames or seconds breaks on a retimed shot. A motion item may anchor on a share of the shot (``at_frac``,
``from_frac``, ``to_frac``, 0..1) or on a word; a sound event (``sound_events[]``) on ``at_word`` (a phrase of the shot's
line, or ``{line_id, word, offset_s}``), resolved on the same word spine. An absolute end past a retimed shot is cut and the
event says so (``truncated_frames``), never silently; ``anchor_rows`` lists every broken or cut anchor at G6, right after
the retime, before any clip or stem is made.

A sound event with a ``picture_event`` (an eruption, an impact) is a visible event too (FA-10): it is resolved here with
``source: "sound_events"`` and its authored class, so the 2.5D renderer shakes on the same frame the sound plan places and
the event report lists it.
"""
from __future__ import annotations

import hashlib
import json

from explainer_engine.core.errors import ContractError
from explainer_engine.maps import actions as MA
from explainer_engine.qa import gates as G

SCHEMA = "av_events/1"
CONTRACT = "av_events/1"
RESOLVER_VERSION = "av_events/1.0"
DECISIONS = ("sfx", "ui_cue", "ambience_only", "music_only", "silent_by_design", "review_required")
NEEDS_CLASS = ("sfx", "ui_cue")
NEEDS_WHY = ("silent_by_design", "review_required")
SYNCS = ("onset", "span", "end")
PURPOSES = ("clarify", "humour", "transition", "sync")
ANIM_FRAMES = MA.ANIM_FRAMES
WORD_FRAMES_MIN = 6                     # one word's length when the line's own spacing says nothing (0.25 s at 24 fps)

CONTINUOUS = ("route_arrow", "front_line", "marker_travel", "supply_line", "counter", "bar_grow", "progress_bar", "spread",
              "plume", "zoom")
PATH_MOVES = ("push", "pull", "truck", "crane", "orbit_small")
CAMERA_MOVES = ("push", "pull", "truck", "crane", "orbit_small", "handheld", "rack_focus", "zoom")


def _a(decision, cls=None, sync="onset", purpose=None, why=None) -> dict:
    out = {"decision": decision, "sync": sync}
    if cls:
        out["class"] = cls
    if purpose:
        out["purpose"] = purpose
    if why:
        out["why"] = why
    return out


# the default decision of every kind (the map sound taxonomy of the AV brief, 2026-11-13; the 2.5D families)
DEFAULTS = {
    "route_arrow": _a("sfx", "map_route_draw", "span", "clarify"),
    "front_line": _a("sfx", "map_route_draw", "span", "clarify"),
    "supply_line": _a("sfx", "map_route_draw", "span", "clarify"),
    "marker_travel": _a("sfx", "map_tokens_shift", "span", "clarify"),
    "pulse": _a("ui_cue", "map_pin_set", "onset", "clarify"),
    "highlight": _a("ui_cue", "map_arrive_click", "onset", "clarify"),
    "milestone": _a("ui_cue", "data_tick", "onset", "clarify"),
    "snap": _a("sfx", "map_line_snap", "onset", "sync"),
    "counter": _a("sfx", "data_rise_texture", "span", "clarify"),
    "bar_grow": _a("sfx", "data_rise_texture", "span", "clarify"),
    "progress_bar": _a("sfx", "data_rise_texture", "span", "clarify"),
    "split_compare": _a("ui_cue", "map_tokens_shift", "onset", "transition"),
    "label": _a("silent_by_design", why="a name appearing is read, not heard"),
    "zoom": _a("silent_by_design", why="a camera move is silent by default"),
    "spread": _a("ambience_only", sync="span", why="a slow area change: the place's bed carries it"),
    "plume": _a("ambience_only", sync="span", why="a slow drift: the place's bed carries it"),
    "supply_state:active": _a("silent_by_design", why="the line already sounds while it draws"),
    "supply_state:strained": _a("ui_cue", "map_line_strain", "onset", "clarify"),
    "supply_state:cut": _a("sfx", "map_line_snap", "onset", "sync"),
    # 2.5D
    "push": _a("silent_by_design", why="a camera move is silent by default"),
    "pull": _a("silent_by_design", why="a camera move is silent by default"),
    "truck": _a("silent_by_design", why="a camera move is silent by default"),
    "crane": _a("silent_by_design", why="a camera move is silent by default"),
    "orbit_small": _a("silent_by_design", why="a camera move is silent by default"),
    "handheld": _a("silent_by_design", why="a camera move is silent by default"),
    "rack_focus": _a("silent_by_design", why="a focus change is silent by default"),
    "subject_sway": _a("silent_by_design", why="a breath and a sway make no sound of their own"),
    "sun_shaft_drift": _a("silent_by_design", why="light makes no sound"),
    "shake": _a("sfx", "impact", "onset", "sync"),
    "lightning:timed": _a("sfx", "thunder", "onset", "sync"),
    "lightning": _a("ambience_only", why="a storm's light: the storm bed carries it"),
    "fire_flicker": _a("ambience_only", why="the fire's crackle is the bed's"),
    "ash_fall": _a("ambience_only", why="falling ash is heard in the bed"),
    "smoke_drift": _a("ambience_only", why="drifting smoke is heard in the bed"),
    "mist": _a("ambience_only", why="mist is heard in the bed"),
    "rain": _a("ambience_only", why="rain is the bed"),
    "embers": _a("ambience_only", why="embers are the fire's bed"),
    "dust": _a("ambience_only", why="dust is heard in the bed"),
    "water_shimmer": _a("ambience_only", why="the water's sound is the bed"),
    "heat_haze": _a("ambience_only", why="heat makes no sound of its own"),
    "foliage_sway": _a("ambience_only", why="leaves in the wind are the bed"),
    "cloud_drift": _a("ambience_only", why="clouds are heard as the wind bed"),
    "cloth_flap": _a("ambience_only", why="a flag in the wind: the wind bed carries it (cloth_flap takes are missing)"),
}


def default_audio(op: str, item: dict) -> dict:
    if op == "supply_state":
        return dict(DEFAULTS.get(f"supply_state:{item.get('state') or 'active'}", DEFAULTS["supply_state:active"]))
    if op == "lightning" and (item.get("at_word") or item.get("at_frame") is not None):
        return dict(DEFAULTS["lightning:timed"])
    return dict(DEFAULTS.get(op) or _a("review_required", why=f"no default sound decision for {op!r}"))


def _frames(shot: dict, fps: int) -> int:
    """The shot's frames as its renderer counts them: a map at least one second (``maps/actions.plan``), a 2.5D shot its
    own length (``production/layers25d.plan``; a Wan fallback in a rehearsal can be shorter than a second)."""
    n = int(round(float(shot.get("target_duration_seconds") or 0) * fps))
    return max(fps, n) if shot.get("actions") else max(1, n)


def _find(words: list[str], want: list[str], start: int) -> int | None:
    return next((i for i in range(start, len(words) - len(want) + 1) if words[i:i + len(want)] == want), None)


def _word_len(starts: list[int], frames: int) -> int:
    gaps = [b - a for a, b in zip(starts, starts[1:]) if b > a]
    if not gaps:
        return WORD_FRAMES_MIN
    gaps.sort()
    return max(WORD_FRAMES_MIN, gaps[len(gaps) // 2])


def has_events(shot: dict) -> bool:
    """True when the shot has a visible event for the resolver: an action, a motion item or a picture sound event."""
    return bool(shot.get("actions") or shot.get("motion_imitation")
                or any(e.get("picture_event") for e in shot.get("sound_events") or []))


def _frac(v, frames: int, what: str, sid: str) -> int:
    x = float(v)
    if not 0.0 <= x <= 1.0:
        raise ContractError(f"{sid}: {what} {x} is not a share of the shot (0..1)")
    return int(round(x * frames))


def _line_word_index(shot: dict, script: dict, anchor: dict, sid: str) -> int:
    """The index in the shot's words of ``{line_id, word}`` (``word``: its index in that line from 0, or its text, the
    first time it is spoken in that line)."""
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    base = 0
    for lid in shot.get("audio_line_ids") or []:
        ws = MA._words(lines.get(lid, {}).get("text", ""))
        if lid == anchor.get("line_id"):
            w = anchor.get("word")
            if isinstance(w, int) and not isinstance(w, bool):
                if not 0 <= w < len(ws):
                    raise ContractError(f"{sid}: at_word word {w} is outside line {lid}'s {len(ws)} words")
                return base + w
            want = MA._words(str(w or ""))
            hit = _find(ws, want, 0) if want else None
            if hit is None:
                raise ContractError(f"{sid}: at_word {w!r} is not spoken in line {lid}")
            return base + hit
        base += len(ws)
    raise ContractError(f"{sid}: at_word names line {anchor.get('line_id')!r}, which this shot does not carry")


def sound_event_frame(shot: dict, script: dict, item: dict, measured_spine: list[dict] | None = None,
                      fps: int = 24) -> tuple[int, str]:
    """(frame, basis) of one authored sound event on the shot's clock: ``at_word`` on the word spine (the measured one after
    the read; FA-06), else ``at_s``; an anchor outside the shot raises ``ContractError``."""
    sid = str(shot.get("shot_id") or "?")
    frames = _frames(shot, fps)
    if item.get("at_word") is not None and item.get("at_s") is not None:
        raise ContractError(f"{sid}: sound event {item.get('what')!r} has both at_s and at_word (exactly one)")
    if item.get("at_word") is not None:
        words = MA.shot_words(shot, script)
        starts, basis = MA.word_frames(words, frames, measured_spine)
        aw = item["at_word"]
        if isinstance(aw, dict):
            idx = _line_word_index(shot, script, aw, sid)
            off = float(aw.get("offset_s") or 0.0)
        else:
            want = MA._words(str(aw))
            idx = _find(words, want, 0) if want else None
            off = 0.0
            if idx is None:
                raise ContractError(f"{sid}: sound event at_word {aw!r} is not spoken in the shot")
        f = starts[idx] + int(round(off * fps))
        how = f"{basis}:word"
    else:
        f, how = int(round(float(item.get("at_s", 0.0)) * fps)), "seconds"
    if not 0 <= f < frames + 1:
        raise ContractError(f"{sid}: sound event {item.get('class') or item.get('what')} lands at frame {f}, outside the "
                            f"shot's {frames} frames")
    return min(f, frames - 1) if frames else f, how


def visual_events(shot: dict, script: dict, measured_spine: list[dict] | None = None, fps: int = 24) -> list[dict]:
    """The shot's events on its own clock (frames from the shot's first frame), in order: actions, motion items, then the
    sound events that move the picture (``picture_event``, FA-10).

    Raises ``ContractError`` where a word is not spoken in the shot, a frame lies outside it, or an audio block is malformed
    (the contract rows report the softer misses)."""
    sid = str(shot.get("shot_id") or "?")
    frames = _frames(shot, fps)
    words = MA.shot_words(shot, script)
    starts, basis = MA.word_frames(words, frames, measured_spine)
    wlen = _word_len(starts, frames)
    line_end = min(frames, (starts[-1] + wlen) if starts else frames)

    def end_of_phrase(phrase: str, after: int, what: str) -> int:
        want = MA._words(phrase)
        hit = _find(words, want, after)
        if hit is None:
            raise ContractError(f"{sid}: {what} until_word {phrase!r} is not spoken in the shot after its start word")
        last = hit + len(want) - 1
        return starts[last + 1] if last + 1 < len(starts) else min(frames, starts[last] + wlen)

    out: list[dict] = []
    cursor = 0
    acts = list(shot.get("actions") or [])
    act_starts: list[int] = []
    for i, a in enumerate(acts):
        op = a.get("kind")
        want = MA._words(a.get("at_word", ""))
        if a.get("at_frame") is not None:
            f0, hit, t0 = int(a["at_frame"]), None, "frame"
        else:
            if not want:
                raise ContractError(f"{sid}: {op} has no at_word")
            hit = _find(words, want, cursor)
            if hit is None:
                raise ContractError(f"{sid}: {op} lands on {a.get('at_word')!r}, which is not in the shot's line after word "
                                    f"{cursor} (the action must be tied to a spoken word, Q6)")
            cursor = hit
            f0, t0 = starts[hit], f"{basis}:word"
        if not 0 <= f0 < frames:
            raise ContractError(f"{sid}: {op} starts at frame {f0}, outside the shot's {frames} frames")
        act_starts.append(f0)
        out.append({"_item": a, "_hit": hit, "_want": want, "source": "actions", "index": i, "op": op, "start_frame": f0,
                    "timing_start": t0})
    for k, ev in enumerate(out):
        a, op = ev["_item"], ev["op"]
        f0 = ev["start_frame"]
        if a.get("until_word"):
            after = (ev["_hit"] + len(ev["_want"])) if ev["_hit"] is not None else 0
            f1, t1 = end_of_phrase(a["until_word"], after, op), f"{basis}:until_word"
        elif op in CONTINUOUS:
            nxt = next((s for s in act_starts[k + 1:] if s > f0), None)
            f1, t1 = (nxt, "next_action") if nxt is not None else (line_end, "line_end")
            f1 = max(f1, f0 + ANIM_FRAMES)
        else:
            f1, t1 = f0 + ANIM_FRAMES, "anim_frames"
        ev["end_frame"] = int(max(f0 + 1, min(frames, f1)))
        ev["timing_end"] = t1
    motion = list(shot.get("motion_imitation") or [])
    for j, m in enumerate(motion):
        op = m.get("effect")
        hit = None
        if m.get("at_frame") is not None:
            f0, t0 = int(m["at_frame"]), "frame"
        elif m.get("at_frac") is not None:
            f0, t0 = min(frames - 1, _frac(m["at_frac"], frames, f"{op} at_frac", sid)), "frac"
        elif m.get("at_word"):
            want = MA._words(m["at_word"])
            hit = _find(words, want, 0)
            if hit is None:
                raise ContractError(f"{sid}: {op} lands on {m['at_word']!r}, which is not a spoken word of the shot")
            f0, t0 = starts[hit], f"{basis}:word"
        else:
            f0, t0 = 0, "shot"
        if not 0 <= f0 < frames:
            raise ContractError(f"{sid}: {op} at frame {f0} is outside the shot's {frames} frames")
        if m.get("until_word"):
            after = (hit + len(MA._words(m["at_word"]))) if hit is not None else 0
            f1, t1 = end_of_phrase(m["until_word"], after, op), f"{basis}:until_word"
        elif m.get("to_frame") is not None:
            f1, t1 = int(m["to_frame"]), "frame"
        elif m.get("to_frac") is not None:
            f1, t1 = _frac(m["to_frac"], frames, f"{op} to_frac", sid), "frac"
        elif t0 == "shot" or op in PATH_MOVES:
            f1, t1 = frames, "shot"     # a camera path started on a word runs to the shot's end unless told otherwise
        else:
            f1, t1 = f0 + ANIM_FRAMES, "anim_frames"
        if m.get("from_frame") is not None and t0 == "shot":
            f0, t0 = int(m["from_frame"]), "frame"
        elif m.get("from_frac") is not None and t0 == "shot":
            f0, t0 = min(frames - 1, _frac(m["from_frac"], frames, f"{op} from_frac", sid)), "frac"
        if not 0 <= f0 < frames:
            raise ContractError(f"{sid}: {op} starts at frame {f0}, outside the shot's {frames} frames")
        out.append({"_item": m, "source": "motion_imitation", "index": j, "op": op, "start_frame": f0, "timing_start": t0,
                    "end_frame": int(max(f0 + 1, min(frames, f1))), "timing_end": t1,
                    "truncated_frames": max(0, int(f1) - frames)})
    for k, item in enumerate(shot.get("sound_events") or []):
        if not item.get("picture_event"):
            continue
        f0, t0 = sound_event_frame(shot, script, item, measured_spine, fps)
        cls = item.get("class") or item.get("what")
        audio = _a("sfx", cls, "onset", item.get("purpose") or "sync")
        it = dict(item, audio=audio, event_id=item.get("event_id") or f"{sid}.S{k + 1}")
        out.append({"_item": it, "source": "sound_events", "index": k, "op": f"picture:{item['picture_event']}",
                    "start_frame": f0, "timing_start": t0, "end_frame": min(frames, f0 + 1), "timing_end": "one frame",
                    "_authored": True})
    events = []
    for ev in out:
        item = ev.pop("_item")
        ev.pop("_hit", None)
        ev.pop("_want", None)
        letter = "A" if ev["source"] == "actions" else "M"
        authored = item.get("audio") if not ev.pop("_authored", False) else item["audio"]
        audio = dict(authored) if isinstance(authored, dict) else default_audio(ev["op"], item)
        audio.setdefault("sync", "span" if ev["op"] in CONTINUOUS and audio.get("decision") == "sfx" else "onset")
        e = {"event_id": item.get("event_id") or f"{sid}.{letter}{ev['index'] + 1}", "shot_id": sid,
             "source": ev["source"], "index": ev["index"], "op": ev["op"], "start_frame": int(ev["start_frame"]),
             "end_frame": int(ev["end_frame"]), "audio": audio, "audio_basis": "authored" if authored else "default",
             "id_basis": "authored" if item.get("event_id") else "derived",
             "timing": {"start": ev["timing_start"], "end": ev["timing_end"]}, "word": item.get("at_word"),
             "until_word": item.get("until_word")}
        if ev.get("truncated_frames"):
            e["truncated_frames"] = int(ev["truncated_frames"])
        if ev["source"] == "sound_events":
            e["picture_event"] = item["picture_event"]
        if ev["op"] == "supply_state":
            e["state"] = item.get("state") or "active"
        if item.get("route"):
            e["route"] = item["route"]
        e["_cues"] = item.get("cues", "auto")
        events.append(e)
    return _derive(events, frames)


DERIVED_CUES = {   # the map sound taxonomy's arrival and confirmation cues (AV brief, 2026-11-13). No start cue: the line's own
    # draw sound starts on its first frame, and a second sound there broke BP-81 in the pilot (14.1 cues a minute, 4 emphasis
    # cues on one line); a number confirms only when its count was silent (the riser already ends on the value)
    "route_arrow": (("arrive", "map_arrive_click", "end"),),
    "supply_line": (("arrive", "map_arrive_click", "end"),),
    "marker_travel": (("arrive", "map_arrive_click", "end"),),
    "counter": (("done", "data_confirm", "end"),),
    "bar_grow": (("done", "data_confirm", "end"),),
    "progress_bar": (("done", "data_confirm", "end"),),
}


def _derive(events: list[dict], frames: int) -> list[dict]:
    """A marker riding a route shares the route's sound; a route gets its start and arrival cues, a number its one
    confirmation (``cues: none`` on the item turns them off). Derived events are sound only: no renderer draws them."""
    by_id = {e["event_id"]: e for e in events}
    out = []
    for e in events:
        cues = e.pop("_cues", "auto")
        out.append(e)
        if e["op"] == "marker_travel" and e.get("route") in by_id and e["audio_basis"] == "default":
            r = by_id[e["route"]]
            if e["start_frame"] < r["end_frame"] and r["start_frame"] < e["end_frame"]:
                e["audio"] = _a("silent_by_design", why=f"rides {r['event_id']}: shares its route sound")
                continue
        if cues == "none" or e["source"] != "actions" or e["audio"].get("decision") in ("silent_by_design",):
            continue
        if e["op"] in ("counter", "bar_grow", "progress_bar") and e["audio"].get("decision") == "sfx":
            continue
        for tag, cls, sync in DERIVED_CUES.get(e["op"], ()):
            f = e["start_frame"] if sync == "onset" else max(e["start_frame"], e["end_frame"] - 1)
            out.append({"event_id": f"{e['event_id']}.{tag}", "shot_id": e["shot_id"], "source": "derived",
                        "index": e["index"], "op": f"{e['op']}:{tag}", "start_frame": f, "end_frame": min(frames, f + 1),
                        "audio": _a("ui_cue", cls, "onset", "clarify"), "audio_basis": "default",
                        "id_basis": f"derived_from:{e['event_id']}", "timing": {"start": f"{tag} of {e['event_id']}",
                                                                                 "end": "one frame"},
                        "word": e.get("word"), "until_word": None, "parent": e["event_id"]})
    return out


def audio_problems(ev: dict, classes=None) -> list[tuple[str, str]]:
    """``[(level, text)]`` for one event's audio block: FAIL where the contract is broken, REVIEW where a person looks."""
    a = ev.get("audio") or {}
    d = a.get("decision")
    out = []
    if d not in DECISIONS:
        return [(G.FAIL, f"{ev['event_id']}: decision {d!r} is not one of {', '.join(DECISIONS)}")]
    if d in NEEDS_CLASS and not a.get("class"):
        out.append((G.FAIL, f"{ev['event_id']}: {d} needs a class"))
    if d in NEEDS_CLASS and a.get("class") and classes is not None and a["class"] not in classes:
        out.append((G.FAIL, f"{ev['event_id']}: class {a['class']!r} is not a class of the sound plan"))
    if d in NEEDS_WHY and not str(a.get("why") or "").strip():
        out.append((G.FAIL, f"{ev['event_id']}: {d} needs its reason (why)"))
    if a.get("sync") not in SYNCS:
        out.append((G.FAIL, f"{ev['event_id']}: sync {a.get('sync')!r} is not one of {', '.join(SYNCS)}"))
    if d == "sfx" and ev["op"] in CONTINUOUS and a.get("sync") != "span":
        out.append((G.FAIL, f"{ev['event_id']}: {ev['op']} is a continuous action: its sound uses a span"))
    if d in NEEDS_CLASS and a.get("purpose") is not None and a["purpose"] not in PURPOSES:
        out.append((G.REVIEW, f"{ev['event_id']}: purpose {a['purpose']!r} is not one of BP-55's {', '.join(PURPOSES)}"))
    if ev["op"] in CAMERA_MOVES and d in NEEDS_CLASS:
        out.append((G.REVIEW, f"{ev['event_id']}: a camera move is silent by default; this one asks for {d}"))
    if d == "review_required":
        out.append((G.REVIEW, f"{ev['event_id']}: review_required: {a.get('why')}"))
    return out


def episode_events(script: dict, spines: dict | None = None, fps: int = 24) -> dict:
    """``{shot_id: [events]}`` for every shot with actions or motion items."""
    out = {}
    for sh in script.get("shots", []):
        if has_events(sh):
            out[sh["shot_id"]] = visual_events(sh, script, (spines or {}).get(sh["shot_id"]), fps)
    return out


def spine_hash(spine) -> str:
    return hashlib.sha256(json.dumps(spine or [], sort_keys=True).encode()).hexdigest()[:16]


def events_hash(events: list[dict]) -> str:
    return hashlib.sha256(json.dumps(events, sort_keys=True, default=str).encode()).hexdigest()[:16]


def contract_rows(script: dict, classes=None, fps: int = 24) -> list[dict]:
    """G1 rows: the contract on a locked script (``av_contract``), the derived ids and defaults on an older one, the audio
    blocks of every event, unique ids."""
    locked = script.get("av_contract") == CONTRACT
    missing, derived, fails, reviews, ids, dup, broken = [], 0, [], [], set(), [], []
    for sh in script.get("shots", []):
        for src in ("actions", "motion_imitation"):
            for i, item in enumerate(sh.get(src) or []):
                if not item.get("event_id") or not isinstance(item.get("audio"), dict):
                    missing.append(f"{sh.get('shot_id')}.{src}[{i}]")
        try:
            evs = visual_events(sh, script, None, fps) if has_events(sh) else []
        except ContractError as exc:
            broken.append(str(exc)[:160])
            continue
        for ev in evs:
            derived += ev["id_basis"] == "derived" or ev["audio_basis"] == "default"
            if ev["event_id"] in ids:
                dup.append(ev["event_id"])
            ids.add(ev["event_id"])
            if ev["source"] == "sound_events":   # its class is checked by sound_plan.shot_events (what or class, G4)
                continue
            for lvl, text in audio_problems(ev, classes):
                (fails if lvl == G.FAIL else reviews).append(text)
    rows = []
    if locked:
        rows.append(G.row("av_contract_complete", not missing, f"av_contract {CONTRACT}: {len(missing)} action/motion item(s) "
                          "without event_id and audio (AV-02)", missing[:20]))
    else:
        rows.append(G.row("av_contract_complete", derived == 0, f"an older script (no av_contract): {derived} event(s) got a "
                          "derived id or the default decision of their kind (AV-03; a new locked script carries both)",
                          derived, level=G.REVIEW))
    rows.append(G.row("av_events_resolve", not broken, f"{len(broken)} shot(s) whose events do not resolve on the planned clock",
                      broken[:10]))
    rows.append(G.row("av_event_ids_unique", not dup, f"{len(dup)} duplicate event id(s)", dup[:10]))
    rows.append(G.row("av_audio_decisions", not fails, f"{len(fails)} audio decision(s) break the contract (AV-04)", fails[:20]))
    rows.append(G.row("av_audio_review", not reviews, f"{len(reviews)} decision(s) a person looks at (review_required, a "
                      "sounding camera move, a purpose outside BP-55)", reviews[:20], level=G.REVIEW))
    return rows


def events_report(script: dict, spines: dict | None, fps: int) -> dict:
    """The event report of an episode: every event with its frames and decision, per shot the spine hash and the event hash
    (the clip cache keys on both)."""
    per = {}
    for sid, evs in episode_events(script, spines, fps).items():
        sp = (spines or {}).get(sid)
        per[sid] = {"spine_sha": spine_hash(sp), "spine_basis": "measured" if sp else "estimated",
                    "events_sha": events_hash(evs), "events": evs}
    counts: dict[str, int] = {}
    for v in per.values():
        for e in v["events"]:
            counts[e["audio"]["decision"]] = counts.get(e["audio"]["decision"], 0) + 1
    return {"schema": SCHEMA, "resolver": RESOLVER_VERSION, "episode_id": script.get("episode_id"), "fps": fps,
            "contract": script.get("av_contract") or "legacy", "decisions": counts, "shots": per}


def absolute_anchors(shot: dict) -> list[str]:
    """The absolute anchors inside a shot (``at_s`` of a sound event; ``at_frame``, ``from_frame``, ``to_frame`` of an action
    or motion item): they do not follow the read (FA-06)."""
    sid = shot.get("shot_id")
    out = [f"{sid}.sound_events[{k}].at_s" for k, e in enumerate(shot.get("sound_events") or []) if e.get("at_s") is not None]
    for src in ("actions", "motion_imitation"):
        for i, item in enumerate(shot.get(src) or []):
            out += [f"{sid}.{src}[{i}].{f}" for f in ("at_frame", "from_frame", "to_frame") if item.get(f) is not None]
    return out


def absolute_anchor_rows(script: dict) -> list[dict]:
    """G1 (FA-06): in a locked script (``av_contract``) an absolute anchor on a shot that carries a read line is REVIEW with
    the list: the read will change the shot's length (use a word or a share of the shot). An older script: not checked."""
    if script.get("av_contract") != CONTRACT:
        return []
    found = [a for sh in script.get("shots", []) if sh.get("audio_line_ids") for a in absolute_anchors(sh)]
    return [G.row("av_anchors_follow_the_read", not found, f"{len(found)} absolute anchor(s) on shots with a read line: they do "
                  "not move with the read (anchor on a word or a share of the shot, FA-06)", found[:30], level=G.REVIEW)]


def anchor_rows(timed_script: dict, spines: dict | None, fps: int = 24) -> list[dict]:
    """G6, right after the retime (FA-06): every anchor of every shot resolved on the measured clock, so a broken one is
    found at the read stage, before a clip or a stem is made. FAIL lists every anchor outside its retimed shot (and every 2.5D
    camera plan that no longer fits); REVIEW lists the segments the resolver had to cut, with the frames they lost."""
    from explainer_engine.production import layers25d as L25
    broken, cut = [], []
    for sh in timed_script.get("shots", []):
        sid = sh.get("shot_id")
        sp = (spines or {}).get(sid)
        try:
            if has_events(sh):
                for e in visual_events(sh, timed_script, sp, fps):
                    if e.get("truncated_frames"):
                        cut.append(f"{e['event_id']}: {e['op']} loses {e['truncated_frames']} frame(s) at the shot's end")
            for item in sh.get("sound_events") or []:
                sound_event_frame(sh, timed_script, item, sp, fps)
            if sh.get("motion_imitation"):
                L25.plan(sh, fps, events=[], script=timed_script, spine=sp)
        except ContractError as exc:
            broken.append(str(exc)[:200])
    return [G.row("av_anchors_inside_retimed_shots", not broken, f"{len(broken)} shot(s) with an anchor outside the retimed "
                  "shot (FA-06: anchor on a word or a share of the shot, or re-plan it)", broken[:40]),
            G.row("av_anchors_truncated", not cut, f"{len(cut)} event(s) cut short by the retimed shot", cut[:40],
                  level=G.REVIEW)]
