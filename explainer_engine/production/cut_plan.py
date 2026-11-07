"""The cut plan of a short test or episode part: the shots, the read's lines, the places and their ambience, checked against every
free rule of docs/SCENE_REUSE_RULES.md (LV-, DL-, AS-) and docs/EDITING.md (ED-04, ED-14) BEFORE anything is drawn, rendered or
joined, then joined by FFmpeg with the clips' own sound and one ambience bed per place.

The creator, 2026-11-07 22:23 UTC (Gemini review of the stone-age minute-1 test, his answers 1a-8a): the point of the test video and
of the review is to make the code better; every rule must be checked by a test; no talking still without a mouth; actions and
conversation openings are LTX; collage only for narration; ambience per place; hard cuts. Before this the minute-1 cut was a one-off
script (``minute1_plan.py`` / ``minute1_assemble.py`` on the PC) that stripped the LTX sound (``-an``), squeezed 1920x1088 clips to
1280x704 and checked no rule; the review found a line about spears with no spears on screen, Ura's line over Marcus's face, full-body
cut-outs too small to read a mouth, and no ambience.

Plan (``plan.json``)::

    {"fps": 24, "size": [1280, 704], "total": 77.0,
     "lines": [{"who": "N"|"M"|..., "text", "file", "at", "seconds", "scene": "cave", "must_show": ["spears"], "action": false}],
     "ambience": {"<place>": "<loop.wav>"},
     "cast": {"M": "marcus", "U": "ura"},                    # speaker letter -> the entity a shot's ``shows`` names
     "shots": [{"id", "type": "C"|"V"|"D"|"H", "start", "dur", "lines": [i, ...], "place", "drawing", "kind"?,
                "shows": ["marcus", "spears", ...],
                # V: "clip", "trim_head", "two_shot", "keep_audio" (default true), "clip_gain_db"
                # D: "who", "cut", "bg", "framing": "MCU", "h", "drop", "facing": "left"|"right", "flip_x",
                #    "mouth": {"rest", "half", "wide", "round"}, "mouth_cues", "breathing", "edge_trim_px"
                # H: "card": {...} (drawn by production/cards.py)
                "transition": "cut"|"dissolve", "state": {"fire": "embers"}, "event": ["fire"]}]}

    python -m explainer_engine.production.cut_plan check <dir>      # the gate: exit 1 on any FAIL
    python -m explainer_engine.production.cut_plan assemble <dir>   # gate, then FFmpeg (refuses on a FAIL)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from explainer_engine.production import scene_reuse
from explainer_engine.qa import targets

NARRATOR = "N"
MOUTH_STATES = ("rest", "half", "wide", "round")      # DL-04: lips closed (also M/B/P), half-open, wide, round (O/U)
# words_to_mouth_cues / Rhubarb shapes -> the four drawn states (A = closed lips, X = rest)
CUE_TO_STATE = {"A": "rest", "X": "rest", "B": "half", "C": "half", "G": "half", "H": "half", "D": "wide", "E": "round",
                "F": "round"}
MCU_MIN_H = 1.35            # DL-01: chest-up close-up; Gemini review: a full figure at h 0.95 is too small to read a mouth
MCU_MIN_DROP = 0.30
HEAD_TOLERANCE = 0.02       # DL-03: the same size in every shot of the same size in a scene
TWO_SHOT_S = (4.0, 8.0)     # AS-03: a conversation opens on an LTX two-shot of 4-8 s (the creator 21:01-21:03)
REACTION_EVERY = 4          # DL-07 / ED-14: a listener's reaction at least every 4th line
CUT_SNAP_S = 0.10           # AS-07: a cut sits in a pause, or within 100 ms of a line's start
AMBIENCE_GAIN = 0.12        # AS-05: the bed sits about 18 dB under the voice
CLIP_GAIN = 0.5             # AS-10: the clip's own sound (LTX native audio) under the voice
NAME_PREFIX = re.compile(r"^\s*[A-Z][A-Z .'-]{1,20}:\s")   # AS-09: "MARCUS: " in a subtitle

# every rule of SCENE_REUSE_RULES.md and the edit rules this gate owns -> where it is checked; rules no code can check say why
CHECKS = {
    "LV-01": "cut_plan.check_places (scene_reuse.check_place_register)",
    "LV-02": "cut_plan.check_places (consecutive sharp shots of a place share one drawing)",
    "LV-04": "cut_plan.check_inserts",
    "LV-06": "cut_plan.check_places (V shots are in the place register)",
    "LV-07": "cut_plan.check_places (every C/V shot names place and drawing)",
    "LV-08": "cut_plan.check_places (REVIEW: one shot between two drawings of a place)",
    "RF-01": "scene_reuse.check_refs",
    "RF-04": "scene_reuse.check_refs",
    "RF-05": "scene_reuse.check_refs (an out: reference only for a variant of itself)",
    "HI-01": "scene_reuse.check_prompts (in_shot registry blocks verbatim)",
    "HI-02": "scene_reuse.check_registry",
    "HI-04": "scene_reuse.check_prompts",
    "HI-05": "scene_reuse.check_registry",
    "HI-07": "scene_reuse.check_lora_weight",
    "HI-08": "scene_reuse.check_prompts (FAIL above the ceiling)",
    "DL-01": "cut_plan.check_dialogue",
    "DL-02": "cut_plan.check_dialogue",
    "DL-03": "cut_plan.check_dialogue",
    "DL-04": "cut_plan.check_dialogue (+ mouth_track at render)",
    "DL-05": "cut_plan.check_dialogue",
    "DL-06": "cut_plan.check_dialogue",
    "DL-07": "cut_plan.check_conversations",
    "DL-08": "cut_plan.check_conversations",
    "DL-09": "cut_plan.check_conversations",
    "ED-04": "cut_plan.check_transitions",
    "ED-14": "cut_plan.check_conversations (opening two-shot, AS-03)",
    "AS-01": "cut_plan.check_coverage",
    "AS-02": "cut_plan.check_coverage",
    "AS-03": "cut_plan.check_conversations",
    "AS-04": "cut_plan.check_coverage",
    "AS-05": "cut_plan.check_ambience",
    "AS-06": "cut_plan.check_coverage",
    "AS-07": "cut_plan.check_cut_timing",
    "AS-08": "cut_plan.check_coverage",
    "AS-09": "cut_plan.check_subtitles",
    "AS-10": "cut_plan.check_clips",
    "AS-11": "cut_plan.check_clips (+ fit_filter crops, never squeezes)",
    "AS-12": "cut_plan.check_cards",
    "AS-13": "cut_plan.check_states",
    "AS-14": "shot_prompt_lint KP-59..KP-62 via ltx_preflight (no paid LTX run on a FAIL)",
}
MANUAL = {
    "LV-03": "which landmarks make a part of a location its own place is a script decision; REVIEW by eye",
    "LV-05": "light/weather change inside a picture is a creative choice; REVIEW by eye",
    "RF-02": "the approval of a reference is the creator's recorded yes (AC-02), not something code can see in a picture",
    "RF-03": "the reference map rows are measured by tests of pictures, REVIEW until measured",
    "HI-03": "distinct silhouettes are judged on the contact sheet",
    "HI-06": "the identity contact sheet is seen by the creator before use",
    "DL-10": "a process gate: one free exchange assembled before any other dialogue picture is paid",
}


def _f(rule, sev, where, text):
    return {"rule": rule, "severity": sev, "where": where, "detail": text}


def _kind(s: dict) -> str:
    if s.get("kind"):
        return s["kind"]
    return {"D": "blurred", "H": "insert"}.get(s["type"], "sharp")


def _speaker_entity(plan: dict, who: str) -> str:
    return plan.get("cast", {}).get(who, who).lower()


def _shot_lines(plan: dict, s: dict) -> list[dict]:
    return [plan["lines"][i] for i in s.get("lines", [])]


def check_places(plan: dict) -> list[dict]:
    """LV-01/02/06 by the place register, LV-07 (every C/V shot names its place and drawing), LV-08 (REVIEW)."""
    out, reg = [], []
    for s in plan["shots"]:
        if s["type"] in ("C", "V") and _kind(s) == "sharp":
            if not s.get("place") or not s.get("drawing"):
                out.append(_f("LV-07", "FAIL", s["id"], "a sharp C/V shot must name its place and drawing (place register)"))
                continue
        if s.get("place") and s.get("drawing"):
            reg.append({"id": s["id"], "place": s["place"], "drawing": s["drawing"], "kind": _kind(s)})
    types = {str(s["id"]): s["type"] for s in plan["shots"]}
    for rule, sev, text in scene_reuse.check_place_register(reg):
        sid = text.split(":")[0]
        out.append(_f(rule, sev, sid, text))
        out.append(_f("LV-02", sev, sid, "consecutive sharp shots of one place must be one picture"))
        if types.get(sid) == "V":
            out.append(_f("LV-06", sev, sid, "an LTX clip starts from a second drawing of the place it cut from"))
    last = {}
    for i, r in enumerate(reg):
        if r["kind"] != "sharp":
            continue
        prev = last.get(r["place"])
        if prev and prev[0] != r["drawing"] and i - prev[1] == 2:
            out.append(_f("LV-08", "REVIEW", r["id"], f"only one shot between two drawings of {r['place']}"))
        last[r["place"]] = (r["drawing"], i)
    return out


def check_inserts(plan: dict) -> list[dict]:
    """LV-04: an insert (H) shows a thing, not a place: it may not be registered as a sharp view of a place."""
    return [_f("LV-04", "REVIEW", s["id"], "an insert is registered as a sharp view of a place")
            for s in plan["shots"] if s["type"] == "H" and s.get("kind") == "sharp" and s.get("place")]


def check_dialogue(plan: dict) -> list[dict]:
    """DL-01..06 on every cut-out (D) shot."""
    out, heads = [], {}
    shots = plan["shots"]
    for s in shots:
        if s["type"] != "D":
            continue
        sid, who = s["id"], s.get("who")
        if not who:
            out.append(_f("DL-01", "FAIL", sid, "a cut-out shot must name its hero (who)"))
            continue
        if s.get("framing") != "MCU" or float(s.get("h", 0)) < MCU_MIN_H or float(s.get("drop", 0)) < MCU_MIN_DROP:
            out.append(_f("DL-01", "FAIL", sid, f"a dialogue cut-out is a chest-up close-up: framing MCU, h >= {MCU_MIN_H}, "
                                                f"drop >= {MCU_MIN_DROP} (got {s.get('framing')}, h {s.get('h')}, drop {s.get('drop')})"))
        bg = str(s.get("bg", ""))
        if not (s.get("bg_blur_sigma", 0) or "blur" in Path(bg).name.lower()):
            out.append(_f("DL-02", "FAIL", sid, "the background of a cut-out is the place's picture blurred (bg_blur_sigma or a blur_ file)"))
        if int(s.get("edge_trim_px", 0)) < 1:
            out.append(_f("DL-03", "FAIL", sid, "the cut-out's matte edge is not trimmed (edge_trim_px >= 1): the white line of v1"))
        key = (s.get("scene") or s.get("place"), who, s.get("framing"))
        if key in heads and abs(float(s.get("h", 0)) - heads[key][1]) > HEAD_TOLERANCE * heads[key][1]:
            out.append(_f("DL-03", "FAIL", sid, f"{who} at h {s.get('h')} but {heads[key][0]} at h {heads[key][1]}: one size per "
                                                "shot size in a scene"))
        heads.setdefault(key, (sid, float(s.get("h", 0))))
        speaks = any(l["who"] != NARRATOR and _speaker_entity(plan, l["who"]) == who.lower() for l in _shot_lines(plan, s))
        if speaks:
            m = s.get("mouth") or {}
            missing = [k for k in MOUTH_STATES if not m.get(k)]
            if missing:
                out.append(_f("DL-04", "FAIL", sid, f"{who} speaks but the cut-out lacks mouth states {missing}: a talking figure "
                                                    "without a moving mouth is never rendered"))
            if not s.get("mouth_cues"):
                out.append(_f("DL-04", "FAIL", sid, f"{who} speaks but no mouth_cues file (audio/words_to_mouth_cues.py)"))
        if s.get("breathing") is False:
            out.append(_f("DL-05", "REVIEW", sid, "breathing is off: the body never freezes"))
    # DL-06: consecutive cut-outs of two different heroes face opposite sides
    for a, b in zip(shots, shots[1:]):
        if a["type"] == b["type"] == "D" and a.get("who") and b.get("who") and a["who"] != b["who"]:
            if not a.get("facing") or not b.get("facing"):
                out.append(_f("DL-06", "FAIL", b["id"], "a cut-out in an exchange must say which side it faces (facing)"))
            elif a["facing"] == b["facing"]:
                out.append(_f("DL-06", "FAIL", b["id"], f"{a['who']} and {b['who']} both face {a['facing']}: speakers of one "
                                                        "exchange face opposite sides (flip_x a three-quarter view)"))
    return out


def _conversations(plan: dict) -> dict[str, list[int]]:
    """scene -> indexes of the shots that carry its lines, for scenes with two or more distinct speakers."""
    speakers, shots = {}, {}
    for i, s in enumerate(plan["shots"]):
        for l in _shot_lines(plan, s):
            sc = l.get("scene")
            if sc and l["who"] != NARRATOR:
                speakers.setdefault(sc, set()).add(l["who"])
                shots.setdefault(sc, [])
                if i not in shots[sc]:
                    shots[sc].append(i)
    return {sc: sorted(ix) for sc, ix in shots.items() if len(speakers[sc]) >= 2}


def check_conversations(plan: dict) -> list[dict]:
    """AS-03 / ED-14 (a conversation opens on an LTX two-shot of 4-8 s), DL-07 (listener reaction at least every 4th line),
    DL-08 (a two-shot is a place picture or an LTX clip from it, never a cut-out), DL-09 (an overlap cuts on its first frame)."""
    out, shots = [], plan["shots"]
    for sc, ix in _conversations(plan).items():
        first = ix[0]
        opener = shots[first - 1] if first and shots[first - 1].get("two_shot") else shots[first]
        lo, hi = TWO_SHOT_S
        if not (opener["type"] == "V" and opener.get("two_shot") and lo <= float(opener["dur"]) <= hi):
            out.append(_f("AS-03", "FAIL", opener["id"], f"conversation '{sc}' must open on an LTX two-shot of {lo:g}-{hi:g} s "
                                                         "(type V, two_shot), then the close-ups"))
            out.append(_f("ED-14", "FAIL", opener["id"], f"conversation '{sc}' has no establishing two-shot"))
        run = 0
        for i in range(first, ix[-1] + 1):
            s = shots[i]
            reaction = not s.get("lines") or s.get("reaction")
            run = 0 if reaction else run + len(s.get("lines", []))
            if run > REACTION_EVERY:
                out.append(_f("DL-07", "REVIEW", s["id"], f"{run} lines in '{sc}' without a listener's reaction"))
                run = 0
    for s in shots:
        if s.get("two_shot") and s["type"] not in ("V", "C"):
            out.append(_f("DL-08", "FAIL", s["id"], "a two-shot is a place picture or an LTX clip from it, never a cut-out"))
        if s.get("overlap_at") is not None and abs(float(s["overlap_at"]) - float(s["start"])) > 1 / plan.get("fps", 24):
            out.append(_f("DL-09", "REVIEW", s["id"], "an overlap cuts to the new speaker on the overlap's first frame"))
    return out


def check_coverage(plan: dict) -> list[dict]:
    """AS-01 (an action line is an LTX clip), AS-02 (no talking still without a mouth), AS-04 (collage C only for narration),
    AS-06 (whoever speaks is the one shown), AS-08 (what the narration names is on screen)."""
    out = []
    for s in plan["shots"]:
        sid, shows = s["id"], {x.lower() for x in s.get("shows", [])}
        if s["type"] == "D" and s.get("who"):
            shows.add(s["who"].lower())
        for l in _shot_lines(plan, s):
            if l.get("action") and s["type"] != "V":
                out.append(_f("AS-01", "FAIL", sid, f"'{l['text'][:40]}' is an action: an LTX clip, never a still"))
            if l["who"] == NARRATOR:
                for thing in l.get("must_show", []):
                    if thing.lower() not in shows:
                        out.append(_f("AS-08", "FAIL", sid, f"the line names '{thing}' but the shot does not show it"))
                continue
            ent = _speaker_entity(plan, l["who"])
            if s["type"] == "H":
                out.append(_f("AS-02", "FAIL", sid, f"{ent} speaks over a graphic: a talking hero is an LTX clip or a cut-out with a mouth"))
            if s["type"] == "C":
                out.append(_f("AS-04", "FAIL", sid, f"{ent} speaks over a collage still: collage is only for narration"))
            if ent not in shows:
                out.append(_f("AS-06", "FAIL", sid, f"{ent} speaks but the shot shows {sorted(shows) or 'nobody'}"))
            for thing in l.get("must_show", []):
                if thing.lower() not in shows:
                    out.append(_f("AS-08", "FAIL", sid, f"the line names '{thing}' but the shot does not show it"))
    return out


def check_ambience(plan: dict) -> list[dict]:
    """AS-05: every place on screen has its ambience bed."""
    amb = plan.get("ambience", {})
    places = []
    for s in plan["shots"]:
        if s.get("place") and s["place"] not in places:
            places.append(s["place"])
    return [_f("AS-05", "FAIL", p, f"place {p} has no ambience bed") for p in places if not amb.get(p)]


def check_cut_timing(plan: dict) -> list[dict]:
    """AS-07: a cut sits in a pause between lines, or within 100 ms of a line's start (REVIEW: L-cuts are allowed on purpose)."""
    out, spans = [], [(l["at"], l["at"] + l["seconds"]) for l in plan["lines"]]
    for s in plan["shots"][1:]:
        t = float(s["start"])
        if s.get("l_cut"):
            continue
        for a, b in spans:
            if a + CUT_SNAP_S < t < b - CUT_SNAP_S:
                out.append(_f("AS-07", "REVIEW", s["id"], f"cut at {t:.2f} s inside a line ({a:.2f}-{b:.2f}); mark l_cut if meant"))
                break
    return out


def subtitles(plan: dict) -> list[tuple[float, float, str]]:
    """The subtitle cues: the line's words only, never the speaker's name (AS-09)."""
    return [(l["at"], l["at"] + l["seconds"], l["text"]) for l in plan["lines"]]


def check_subtitles(plan: dict, cues: list | None = None) -> list[dict]:
    return [_f("AS-09", "FAIL", f"sub {i}", f"'{t[:30]}' carries a speaker name: the face says who speaks")
            for i, (_, _, t) in enumerate(cues if cues is not None else subtitles(plan), 1) if NAME_PREFIX.match(t)]


def check_clips(plan: dict) -> list[dict]:
    """AS-10 (an LTX clip keeps its own sound unless a reason is written), AS-11 (never squeezed: fit is cover-and-crop)."""
    out = []
    for s in plan["shots"]:
        if s["type"] != "V":
            continue
        if s.get("keep_audio") is False and not s.get("mute_reason"):
            out.append(_f("AS-10", "FAIL", s["id"], "the clip's own sound is dropped with no mute_reason"))
        if s.get("fit", "cover") != "cover":
            out.append(_f("AS-11", "FAIL", s["id"], f"fit '{s.get('fit')}' squeezes the clip: only cover-and-crop"))
    return out


def check_cards(plan: dict) -> list[dict]:
    """AS-12: a graphic (H) is drawn in the house style by production/cards.py, never a flat UI mock-up."""
    return [_f("AS-12", "FAIL", s["id"], "a graphic without a house-style card spec (production/cards.py)")
            for s in plan["shots"] if s["type"] == "H" and not s.get("card")]


def check_states(plan: dict) -> list[dict]:
    """AS-13: a place's state (the fire burning / embers / out) changes only on a shot whose ``event`` names it."""
    out, now = [], {}
    for s in plan["shots"]:
        p = s.get("place")
        for k, v in (s.get("state") or {}).items():
            prev = now.get((p, k))
            if prev is not None and prev != v and k not in (s.get("event") or []):
                out.append(_f("AS-13", "REVIEW", s["id"], f"{p} {k}: {prev} -> {v} with no event shot"))
            now[(p, k)] = v
    return out


def check_transitions(plan: dict) -> list[dict]:
    """ED-04: hard cut by default; a dissolve only where the place changes."""
    out, prev = [], None
    for s in plan["shots"]:
        t = s.get("transition", "cut")
        if t not in ("cut", "dissolve"):
            out.append(_f("ED-04", "FAIL", s["id"], f"transition '{t}': hard cut, or a dissolve at a change of place"))
        elif t == "dissolve" and prev is not None and s.get("place") == prev.get("place"):
            out.append(_f("ED-04", "REVIEW", s["id"], "a dissolve inside one place"))
        prev = s
    return out


GATES = (check_places, check_inserts, check_dialogue, check_conversations, check_coverage, check_ambience, check_cut_timing,
         check_subtitles, check_clips, check_cards, check_states, check_transitions)


def gate(plan: dict) -> list[dict]:
    return [f for g in GATES for f in g(plan)]


def mouth_track(cues: list[dict], line_at: float, start: float, n: int, fps: int) -> list[str]:
    """DL-04: the drawn mouth state of each of a shot's ``n`` frames. ``cues`` are the line's mouth cues ({start, end, value},
    seconds from the line's start); the shot begins at ``start`` on the plan's clock and the line at ``line_at``. Outside the
    line the lips rest (the mouth never moves on silence or on another speaker's line)."""
    out = []
    for f in range(n):
        t = start + f / fps - line_at
        st = "rest"
        for c in cues:
            if c["start"] <= t < c["end"]:
                st = CUE_TO_STATE.get(c["value"], "half")
                break
        out.append(st)
    return out


def fit_filter(w: int, h: int, fps: int) -> str:
    """AS-11: cover the frame and crop the overflow centred; never scale to a different aspect."""
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps={fps}"


def assemble_commands(plan: dict, root: Path) -> list[list[str]]:
    """The FFmpeg commands of the cut, in order (pure, tested): one segment per shot, the concat, the sound mix (voice lines,
    each V clip's own sound at its shot, one looping ambience bed per place over that place's shots), the subtitles."""
    fps, (w, h) = plan["fps"], plan["size"]
    seg = root / "seg"
    cmds, parts = [], []
    for s in plan["shots"]:
        n = round(s["dur"] * fps)
        out = seg / f"s{s['id']}.mp4"
        if s["type"] == "V":
            cmds.append(["ffmpeg", "-y", "-v", "error", "-ss", str(s.get("trim_head", 0.5)), "-i", s["clip"], "-frames:v", str(n),
                         "-vf", fit_filter(w, h, fps) + ",tpad=stop_mode=clone:stop_duration=2", "-an", "-c:v", "libx264",
                         "-crf", "17", "-pix_fmt", "yuv420p", str(out)])
        else:
            cmds.append(["ffmpeg", "-y", "-v", "error", "-framerate", str(fps), "-i", str(root / "frames" / f"s{s['id']}" / "f_%04d.png"),
                         "-frames:v", str(n), "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(out)])
        parts.append(out)
    cmds.append(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(seg / "list.txt"), "-c", "copy",
                 str(seg / "video.mp4")])
    ins, flt, labels = [], [], []
    idx = 0
    for l in plan["lines"]:                                   # the read
        ms = int(l["at"] * 1000)
        ins += ["-i", l["file"]]
        flt.append(f"[{idx}:a]aresample=48000,adelay={ms}|{ms},apad[a{idx}]")
        labels.append(f"[a{idx}]"); idx += 1
    for s in plan["shots"]:                                   # AS-10: each LTX clip's own sound, at its shot, under the voice
        if s["type"] == "V" and s.get("keep_audio", True):
            ms = int(float(s["start"]) * 1000)
            ins += ["-ss", str(s.get("trim_head", 0.5)), "-i", s["clip"]]
            g = 10 ** (float(s.get("clip_gain_db", -6.0)) / 20)
            flt.append(f"[{idx}:a]aresample=48000,atrim=0:{s['dur']},afade=t=out:st={max(0, s['dur'] - 0.2)}:d=0.2,"
                       f"volume={g:.3f},adelay={ms}|{ms},apad[a{idx}]")
            labels.append(f"[a{idx}]"); idx += 1
    for place, bed in sorted(plan.get("ambience", {}).items()):   # AS-05: one looping bed per place, over that place's shots
        for s in plan["shots"]:
            if s.get("place") != place:
                continue
            ms, d = int(float(s["start"]) * 1000), float(s["dur"])
            ins += ["-stream_loop", "-1", "-i", bed]
            flt.append(f"[{idx}:a]aresample=48000,atrim=0:{d},afade=t=in:d=0.15,afade=t=out:st={max(0, d - 0.15)}:d=0.15,"
                       f"volume={AMBIENCE_GAIN},adelay={ms}|{ms},apad[a{idx}]")
            labels.append(f"[a{idx}]"); idx += 1
    flt.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,atrim=0:{plan['total']},"
               f"{targets.loudnorm(plan.get('loudness_profile', 'long'))}[aout]")
    cmds.append(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[aout]", "-ac", "2",
                 "-c:a", "aac", "-b:a", "192k", str(seg / "sound.m4a")])
    srt = (root / "subs.srt").as_posix().replace(":", "\\:")
    style = "FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,MarginV=28"
    cmds.append(["ffmpeg", "-y", "-v", "error", "-i", str(seg / "video.mp4"), "-i", str(seg / "sound.m4a"),
                 "-vf", f"subtitles='{srt}':force_style='{style}'", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                 "-c:a", "copy", "-shortest", str(root / plan.get("output", "cut.mp4"))])
    return cmds


def _ts(x: float) -> str:
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def srt_text(plan: dict) -> str:
    return "".join(f"{n}\n{_ts(a)} --> {_ts(b)}\n{t}\n\n" for n, (a, b, t) in enumerate(subtitles(plan), 1))


def report(found: list[dict]) -> int:
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(f"{fails} FAIL, {len(found) - fails} REVIEW")
    return fails


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("check", "assemble"):
        print(__doc__)
        return 2
    root = Path(argv[1])
    plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
    if report(gate(plan)):
        print("stopped: the plan breaks a FAIL rule; nothing was rendered")
        return 1
    if argv[0] == "check":
        return 0
    from explainer_engine.core.store import write_text_atomic
    (root / "seg").mkdir(exist_ok=True)
    write_text_atomic(root / "subs.srt", srt_text(plan))
    write_text_atomic(root / "seg" / "list.txt",
                      "".join(f"file '{(root / 'seg' / ('s' + str(s['id']) + '.mp4')).as_posix()}'\n" for s in plan["shots"]))
    for cmd in assemble_commands(plan, root):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(" ".join(cmd[:6]) + "\n" + r.stderr[-1500:])
    print("wrote", root / plan.get("output", "cut.mp4"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
