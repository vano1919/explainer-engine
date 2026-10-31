"""The sound director (Blueprint P4, docs/AUDIO_SYSTEM.md "Sound director", SD-01..SD-15): from the audio spine, the timed script and
(when the job has one) ``film_shots/2`` it DERIVES ``sound_mix_manifest/2`` (CN-02: never edited by hand) and checks it.

    python -m explainer_engine.audio.sound_director plan  <job> [--library DIR]    # writes audio/sound_mix_manifest.json + sound_director_report.json
    python -m explainer_engine.audio.sound_director check <job> [--stems DIR] [--strict] [--library DIR]
    python -m explainer_engine.audio.sound_director matrix [write]                  # the lane matrix table (docs/AUDIO_SYSTEM.md)

What it decides (spec P4_DESIGN section 2, every number read from the rule named in the table, BP ids only, none copied):
a room-tone bed under every scene (BP-116), J and L leads at scene changes (BP-117), a presence-band dip (BP-118) and perspective
(BP-122) that the renderer applies, three-layer hits on reveals and HARD accents (BP-119), at most ``vacuums_max`` vacuums before the
biggest reveals (BP-120), pan inside ``sfx_pan_max`` (BP-121), one motif per owner and a beat grid (BP-123), the lane matrix (BP-160).
``check`` has two halves: the plan-time one reads the manifest (structure, ranges, layering, freshness) and the render-time one
(``stems=``) measures what ``assemble.build_audio_v2`` rendered (digital silence, the band gap, the vacuum level, the BP-52 gap).

Room tones the library lacks are generated procedurally (free, deterministic) and registered as ``procedural`` in the library root
the caller passes; nothing is ever written to a library the caller did not name. numpy + stdlib only.
"""

from __future__ import annotations

import bisect
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

from explainer_engine import assets_reuse
from explainer_engine.audio import acoustics, duck, foley, sfx_library
from explainer_engine.audio import layers as L
from explainer_engine.core import contracts, delivery
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import targets
from explainer_engine.standards import sourced_rules as SR

RATE = acoustics.SR
NEUTRAL_LANES = ("MAP", "COMPENSATOR")
DRAMA_LANES = ("KEYFRAME_LTX", "DIALOGUE_CU", "DRAMA_BLOCKED_3D")
SIZE_PERSPECTIVE = {"EWS": "far", "WS": "far", "MWS": "mid", "MS": "mid", "OTS": "mid",
                    "MCU": "near", "CU": "near", "ECU": "near", "INSERT": "near"}  # BP-122
OFFSCREEN = ("off-screen", "offscreen", "distant")  # a foley text that says the source is not in the frame
ROOM_TONE_SECONDS = 30.0  # a circular tone: a loop of it has no seam
XFADE_S = 0.5  # the overlap of two scenes' room tones at a butt cut (a render detail, not a rule): never a gap between them
SPOT_S = 1.0  # how long a spot is counted as sounding in the layer count (timing.SFX_MAX)
SPOT_DB = min(-18.0, L.MAX_SFX_DB)  # pre-mix peak gain of a foley spot (the timing default for an effect, under BP-65's cap)
LOUDEST_DB = -14.0
HIT_DB = {"sub": -16.0, "body": -16.0, "air": -22.0}  # the three layers of a hit (peak gains, all under BP-65's cap)
OFFSCREEN_DB = -6.0
RAMPS_S = (0.5, 1.5)  # the opening ramp and the final fade of the mix (assemble.FADE_OUT, ED-04); SD-02 looks between them
VACUUM_RAMP_MS = max(duck.ATTACK_MS, 40.0 / duck.MAX_STEP_DB_PER_MS)  # a 40 dB fall is never steeper than the level JND per ms
FRAME_TOL = 1  # frames of slack when two frame numbers are "the same" instant
ACOUSTIC_WORDS = (("cave", "cave"), ("hall", "hall"), ("church", "hall"), ("palace", "hall"),
                  ("room", "room"), ("tent", "room"), ("house", "room"), ("office", "room"))  # spec 2.3, the fixed keyword table

# SD id -> the rule whose severity it carries (None: not a BP rule, CN-02 / invariant 7 makes it a FAIL)
RULE_OF = {"SD-01": "BP-116", "SD-02": "BP-161", "SD-03": "BP-117", "SD-04": "BP-118", "SD-05": "BP-119", "SD-06": "BP-120",
           "SD-07": "BP-121", "SD-08": "BP-121", "SD-09": "BP-122", "SD-10": "BP-123", "SD-11": "BP-123", "SD-12": "BP-160",
           "SD-13": "BP-162", "SD-14": "BP-50", "SD-15": None}

# What a shot's audio is made of, by lane (BP-160, spec 2.2). The table lives only here; AUDIO_SYSTEM.md carries a copy rendered
# from it (``render_matrix``) and a test keeps them equal. Columns: native clip audio | scene bed | spots | perspective.
MATRIX: dict = {
    "KEYFRAME_LTX": {"native": "bed", "bed": "scene", "spots": "foley+loudest", "perspective": "yes"},
    "DIALOGUE_CU": {"native": "dialogue", "bed": "scene, ducked", "spots": "none", "perspective": "near, dry"},
    "DRAMA_BLOCKED_3D": {"native": "none", "bed": "scene", "spots": "foley", "perspective": "yes"},
    "ATMOS_BROLL": {"native": "bed if present", "bed": "scene", "spots": "loudest", "perspective": "yes"},
    "MAP": {"native": "none", "bed": "neutral room tone", "spots": "cues only", "perspective": "no"},
    "COMPENSATOR": {"native": "none", "bed": "neutral room tone", "spots": "cues only", "perspective": "no"},
    "STILL_HOLD": {"native": "none", "bed": "scene", "spots": "foley, one", "perspective": "yes"},
    None: {"native": "none", "bed": "timed beds", "spots": "timed sfx", "perspective": "mid"},
}
MATRIX_MARKERS = ("<!-- sd-matrix:begin -->", "<!-- sd-matrix:end -->")
DOC = Path(__file__).resolve().parents[2] / "docs" / "AUDIO_SYSTEM.md"
ARCHETYPES = Path(__file__).resolve().parents[1] / "edit" / "archetypes.json"


def render_matrix() -> str:
    rows = ["| lane | native clip audio | scene bed | spots | perspective |", "|---|---|---|---|---|"]
    for lane, m in MATRIX.items():
        rows.append(f"| {lane if lane else 'none (D-43)'} | {m['native']} | {m['bed']} | {m['spots']} | {m['perspective']} |")
    return "\n".join(rows)


def _spots_allowed(lane) -> str:
    return MATRIX[lane]["spots"]


def _no_hits(lane) -> bool:
    return _spots_allowed(lane) in ("none", "cues only")


# --- small helpers --------------------------------------------------------------------------------------------------------

def _mid(pair) -> float:
    return (float(pair[0]) + float(pair[1])) / 2.0


def _level(rule: str | None) -> str:
    """The severity a check of this rule may emit (D-59): a hypothesis is REVIEW, a binding or house FAIL rule is FAIL."""
    return "FAIL" if rule is None else SR.level(rule, SR.severity(rule))


def _f(sd: str, where: str, detail: str, rule: str | None = "") -> dict:
    basis = RULE_OF[sd] if rule == "" else rule
    return {"rule": sd, "severity": _level(basis), "where": where, "detail": detail, "basis": basis or "CN-02"}


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ref(job: Path, path: Path) -> dict:
    return {"path": os.path.relpath(path, job).replace(os.sep, "/"), "sha256": contracts.sha256_file(path)}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def infer_acoustic(text: str) -> str:
    """The fixed keyword table of spec 2.3: cave; hall, church, palace -> hall; room, tent, house, office -> room; else outdoor."""
    t = text.lower()
    return next((kind for word, kind in ACOUSTIC_WORDS if word in t), "outdoor")


def acoustic_of(place_value) -> tuple[str, str]:
    """``(acoustic, source)``: ``declared`` when the place itself says it (a dict with ``acoustic``), else inferred from its text."""
    if isinstance(place_value, dict) and place_value.get("acoustic") in acoustics.KINDS:
        return place_value["acoustic"], "declared"
    text = place_value.get("text", "") if isinstance(place_value, dict) else str(place_value or "")
    return infer_acoustic(text), "inferred"


def motif_of(owner: str, library_items: list[dict]) -> dict | None:
    """The motif item of an owner (BP-123): ``motif_of`` on the item, or the tag ``motif:<owner>``. Two motifs for one owner is
    SD-11; this returns the first by id so a plan can go on and the check reports the duplicate."""
    mine = [i for i in library_items if _owner(i) == owner]
    return min(mine, key=lambda i: i["id"]) if mine else None


def _owner(item: dict) -> str | None:
    if item.get("motif_of"):
        return item["motif_of"]
    return next((t.split(":", 1)[1] for t in item.get("tags", []) if t.startswith("motif:")), None)


# --- the shot timeline (spec 2.1) -----------------------------------------------------------------------------------------

def scene_bounds(spine: dict) -> dict[str, tuple[int, int]]:
    """Scene -> (start, end) frames: they tile the spine; the first starts at 0, each next at its segment's first word."""
    segs = spine["segments"]
    starts = [0] + [s["start_frame"] for s in segs[1:]]
    ends = starts[1:] + [spine["total_frames"]]
    return {s["id"]: (a, b) for s, a, b in zip(segs, starts, ends)}


def _shot_at(timeline: list[dict], frame: int) -> dict | None:
    if not timeline:
        return None
    k = bisect.bisect_right([s["start_frame"] for s in timeline], frame) - 1
    return timeline[max(0, k)]


def shot_timeline(spine: dict, timed: dict, film_shots: dict | None, edit: dict | None = None, *, screenplay: dict | None = None) -> list[dict]:
    """Every shot the sound is placed against: ``id, scene, lane, size, focal_x, start_frame, end_frame, frames, place, acoustic,
    estimated, events`` (events: the reveals, turns, loudest sounds and HARD accents inside it, each ``frame, kind, label``).

    With ``edit`` (P7) the cuts give the starts; else ``film_shots/2`` shots are laid end to end per scene from the scene's first
    frame (a scene whose shots do not add up to its length within a frame is ``estimated``, never stretched); without film_shots the
    D-43 ``timed.shots`` are the timeline (lane ``None``, perspective ``mid``, focal 0.5)."""
    fps = spine["fps"]
    bounds = scene_bounds(spine)
    cuts = {c["to_shot"]: c for sc in (edit or {}).get("scenes", []) for c in sc["cuts"]}
    out: list[dict] = []
    if film_shots is None:
        text_of: dict = {}
        for b in timed.get("audio", {}).get("beds", []):
            text_of.setdefault(b.get("segment"), re.sub(r"__v\d+$", "", b["sound"]).replace("amb_", "").replace("_", " "))
        for s in timed.get("shots", []):
            ac, src = acoustic_of(text_of.get(s["segment"], ""))
            out.append({"id": s["id"], "scene": s["segment"], "lane": None, "size": None, "focal_x": 0.5, "start_frame": s["start_frame"],
                        "end_frame": s["end_frame"], "frames": s["end_frame"] - s["start_frame"], "place": None,
                        "place_text": text_of.get(s["segment"], ""), "acoustic": ac, "acoustic_source": src, "estimated": False,
                        "events": [], "foley": [], "loudest": None, "window": None, "cut": cuts.get(s["id"])})
    else:
        window = {h["shot_id"]: h for h in spine["post_hoc_shots"]}
        places = film_shots.get("places", {})
        cursor: dict = {}
        for sh in film_shots["shots"]:
            if sh["scene"] not in bounds:
                raise ContractError(f"shot {sh['id']} is in scene {sh['scene']}, which the spine does not have")
            a, n = cursor.get(sh["scene"], bounds[sh["scene"]][0]), sh["duration_frames"]
            if sh["id"] in window:
                a, n = window[sh["id"]]["start_frame"], window[sh["id"]]["end_frame"] - window[sh["id"]]["start_frame"]
            elif sh["id"] in cuts:
                a = cuts[sh["id"]]["at_frame"]
            cursor[sh["scene"]] = a + n
            place = sh["frame"]["place"]
            ac, src = acoustic_of(places.get(place, ""))
            snd = sh.get("sound", {})
            out.append({"id": sh["id"], "scene": sh["scene"], "lane": sh["lane"], "size": sh["frame"]["size"],
                        "focal_x": float(sh["focal_xy"][0]), "start_frame": a, "end_frame": a + n, "frames": n, "place": place,
                        "place_text": str(places.get(place, "")), "acoustic": ac, "acoustic_source": src, "estimated": False,
                        "events": [], "foley": list(snd.get("foley", [])), "loudest": snd.get("loudest"), "window": window.get(sh["id"]),
                        "cut": cuts.get(sh["id"])})
        for sid, (a, b) in bounds.items():  # shots laid end to end that do not fill their scene are flagged, not stretched
            mine = [s for s in out if s["scene"] == sid]
            if mine and not any(s["cut"] for s in mine) and abs(cursor.get(sid, a) - b) > FRAME_TOL:
                for s in mine:
                    s["estimated"] = True
    out.sort(key=lambda s: (s["start_frame"], s["id"]))
    if edit is not None:  # an edit cut moved the starts: a shot ends where the next one of its scene starts (or the scene ends)
        for k, s in enumerate(out):
            nxt = next((t for t in out[k + 1:] if t["scene"] == s["scene"]), None)
            end = nxt["start_frame"] if nxt is not None else bounds[s["scene"]][1]
            if s["window"] is None and end >= s["start_frame"]:
                s["end_frame"], s["frames"] = end, end - s["start_frame"]
    fm = max(1, round(delivery.frame_ms(fps) / 1000 * fps))
    for s in out:  # sounds the shot itself names: loudest and the foley land on its first beat
        if s["loudest"]:
            s["events"].append({"frame": s["start_frame"] + fm, "kind": "loudest", "label": s["loudest"]})
    for s in timed.get("shots", []):  # the D-43 reveal and HARD accents sit on the timed clock; attach them to the shot at that frame
        if s.get("reveal"):
            sh = _shot_at(out, s["start_frame"])
            if sh is not None:
                sh["events"].append({"frame": s["start_frame"], "kind": "reveal", "label": s["reveal"]})
        for a in s.get("accents", []):
            if a["kind"] in L.HARD:
                sh = _shot_at(out, a["start_frame"])
                if sh is not None:
                    sh["events"].append({"frame": a["start_frame"], "kind": "hard", "label": a["kind"]})
    seg_start = {sid: a for sid, (a, _b) in bounds.items()}
    for sg in (screenplay or {}).get("segments", []):  # a turn: a segment that opens on BUT (the screenplay spine's causal connector)
        if sg["causal_connector"] == "BUT" and sg["id"] in seg_start:
            sh = _shot_at(out, seg_start[sg["id"]])
            if sh is not None:
                sh["events"].append({"frame": seg_start[sg["id"]], "kind": "turn", "label": sg["id"]})
    for s in out:
        s["events"].sort(key=lambda e: (e["frame"], e["kind"]))
    return out


def _ranked_events(timeline: list[dict]) -> list[dict]:
    """The reveal candidates, strongest first: a turn, then a reveal, then a loudest sound; ties go to the later position (spec 2.6)."""
    rank = {"turn": 0, "reveal": 1, "loudest": 2}
    ev = [dict(e, shot_id=s["id"]) for s in timeline for e in s["events"] if e["kind"] in rank]
    return sorted(ev, key=lambda e: (rank[e["kind"]], -e["frame"]))


# --- the plan (spec 2.3 - 2.8) --------------------------------------------------------------------------------------------

def _room_tone(root: Path, acoustic: str, place_tag: str | None) -> dict:
    """The library's room tone for an acoustic (and a place), library first (OR-18); else a procedural one, registered."""
    tags = ["room_tone", acoustic] + ([place_tag] if place_tag else [])
    found = assets_reuse.lookup("sfx", tags, sound_root=root)
    if found:
        return min(found, key=lambda i: i["id"])
    name = "roomtone_" + acoustic + (f"_{place_tag}" if place_tag else "")
    seed = acoustics.seed_of(name)
    return sfx_library.add(root, name=name, take=1, category="foley", tags=tags, rate=RATE, loop=True,
                           samples=acoustics.room_tone(acoustic, seed, ROOM_TONE_SECONDS, RATE),
                           source={"kind": "procedural", "seed": seed},
                           licence={"status": "own_procedural", "note": "pink noise shaped in explainer_engine/audio/acoustics.py; no third-party material"},
                           machine_review="procedural room tone: plain, replaceable by a recorded one")


def _hit_items(root: Path) -> dict[str, dict]:
    """The sub, body and air library items of a hit; the procedural ``foley.hit_*`` (take 1) are registered when the library has none."""
    out = {}
    for layer in ("sub", "body", "air"):
        found = assets_reuse.lookup("sfx", [f"hit_{layer}"], sound_root=root)
        if found:
            out[layer] = min(found, key=lambda i: i["id"])
            continue
        tags, fn, seeds = foley.BUILD[f"hit_{layer}"]
        out[layer] = sfx_library.add(root, name=f"hit_{layer}", take=1, category="foley", tags=tags, samples=fn(seeds[0]), rate=RATE,
                                     source={"kind": "procedural", "seed": seeds[0]},
                                     licence={"status": "own_procedural", "note": "built from noise and tones in explainer_engine/audio/foley.py"},
                                     machine_review="procedural placeholder: plain, replaceable by recorded foley", loop=False)
    return out


def _match_sound(root: Path, text: str) -> dict | None:
    """The library sound whose tags share the most words with a foley or loudest text (library first, OR-18); ties by id."""
    score: dict = {}
    byid: dict = {}
    for w in sorted({w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3}):
        for it in assets_reuse.lookup("sfx", [w], sound_root=root):
            if "room_tone" in it["tags"] or it["id"].startswith("hit_"):
                continue
            score[it["id"]] = score.get(it["id"], 0) + 1
            byid[it["id"]] = it
    if not score:
        return None
    return byid[sorted(score, key=lambda i: (-score[i], i))[0]]


def _pan_of(shot: dict | None, text: str = "") -> tuple[float, str, float]:
    """``(pan, perspective, extra gain dB)`` of a spot in a shot: toward the focal side within ``sfx_pan_max`` (BP-121); a source
    that is off-screen goes to the far side, far and 6 dB down (BP-122); lanes without perspective are centred."""
    mx = float(SR.T("BP-121", "sfx_pan_max"))
    if shot is None or shot["lane"] in NEUTRAL_LANES + ("HOST_COMMENTARY",):
        return 0.0, "mid", 0.0
    persp = SIZE_PERSPECTIVE.get(shot["size"], "mid")
    fx = shot["focal_x"]
    if any(w in text.lower() for w in OFFSCREEN):
        return (-mx if fx > 0.5 else mx), "far", OFFSCREEN_DB
    return round(float(np.clip(2 * (fx - 0.5) * mx, -mx, mx)), 4), persp, 0.0


def _story_ops(archetype_id: str) -> set[str]:
    """The ops of an archetype that are story events (CMP-16, ``story_ops`` of edit/archetypes.json). Read from the file, not imported
    from the compensator, so the sound director stays free of the renderers."""
    try:
        doc = json.loads(ARCHETYPES.read_text(encoding="utf-8"))
    except OSError:
        return set()
    return next((set(a.get("story_ops") or []) for a in doc["archetypes"] if a["id"] == archetype_id), set())


def _micro_cue_item(root: Path) -> dict:
    """The library sound of a compensator micro-cue (``pop_in``, a short UI appear); library first (OR-18), else the procedural one, registered."""
    found = assets_reuse.lookup("sfx", list(foley.BUILD["pop_in"][0]), sound_root=root)
    if found:
        return min(found, key=lambda i: i["id"])
    tags, fn, seeds = foley.BUILD["pop_in"]
    return sfx_library.add(root, name="pop_in", take=1, category="foley", tags=tags, samples=fn(seeds[0]), rate=RATE,
                           source={"kind": "procedural", "seed": seeds[0]},
                           licence={"status": "own_procedural", "note": "built from noise and tones in explainer_engine/audio/foley.py"},
                           machine_review="procedural placeholder: plain, replaceable by recorded foley", loop=False)


def _densest(kept: list[int], at: int, span: int) -> int:
    """The most cues, ``at`` included, that fall in any window of ``span`` frames containing ``at``: cues kept on either side of
    ``at`` count (a later existing cue is as much a neighbour as an earlier one)."""
    near = sorted(f for f in kept if abs(f - at) < span) + [at]
    return max(sum(1 for f in near if lo <= f < lo + span) for lo in set(f for f in near if f > at - span and f <= at))


def compensator_cues(job: Path, spine: dict, root: Path, existing: list[dict]) -> tuple[list[dict], list[dict]]:
    """F5 / CMP-16: a micro-cue at BP-120's ``micro_cue_dbfs`` for each story event (``story_ops``) of the job's
    ``visual/visual_comp_manifest.json`` and the ``comp_spec/1`` of its items; camera moves, labels and the rest stay silent (VB-08).
    A cue starts a few frames before its word (within BP-54's early limit, so the sound never leads the picture by more than a viewer
    notices) and inside the gap after the word before: a cue that would start inside a narration word is dropped, and so is one that
    would pass BP-81's cues per minute (counted with the cues already planned) or its burst. Returns (new cues, dropped with the reason)."""
    path = job / "visual" / "visual_comp_manifest.json"
    if not path.exists():
        return [], []
    manifest = _load(path)
    spine_file = job / "audio" / "audio_spine.json"
    if not spine_file.exists() or manifest["audio_spine"]["sha256"] != contracts.sha256_file(spine_file):
        raise ContractError("CN-02: visual/visual_comp_manifest.json was built on another audio spine than audio/audio_spine.json "
                            "(its audio_spine.sha256 differs): its cues would land on the wrong words; rebuild the manifest")
    fps, words = spine["fps"], spine["words"]
    item = _micro_cue_item(root)
    gain = float(SR.T("BP-120", "micro_cue_dbfs"))
    lead = max(1, int(SR.T("BP-54", "early_max_ms") / 1000 * fps))
    per_min = int(SR.T("BP-81", "per_min_review"))
    burst, burst_s = int(SR.T("BP-81", "burst_max")), float(SR.T("BP-81", "burst_window_s"))
    cands: list[tuple[int, str, str]] = []
    for it in manifest["items"]:
        ref = next((ly["ref"] for ly in it["layers"] if ly["kind"] == "spec"), None)
        if ref is None or not (job / ref).exists():
            continue
        spec = _load(job / ref)
        story = _story_ops(spec["archetype_id"])
        for e in spec["events"]:
            if e["op"] in story and 0 <= e["word_index"] < len(words):
                cands.append((words[e["word_index"]]["start_frame"], f"{spec['item_id']}.{e['id']}", e["op"]))
    cands.sort()
    kept = [c["frame"] for c in existing]
    new: list[dict] = []
    dropped: list[dict] = []
    minute, window = int(round(60 * fps)), int(round(burst_s * fps))
    for frame, where, op in cands:
        at = frame - lead
        prev_end = max((w["end_frame"] for w in words if w["end_frame"] <= frame and w["start_frame"] < frame), default=0)
        why = None
        if at < prev_end or at < 0 or any(w["start_frame"] <= at < w["end_frame"] for w in words):
            why = "no gap before the word: the cue would start inside a narration word"
        elif _densest(kept, at, minute) > per_min:
            why = f"more than {per_min} cues a minute (BP-81)"
        elif _densest(kept, at, window) > burst:
            why = f"more than {burst} cues in {burst_s:g} s (BP-81)"
        if why:
            dropped.append({"where": where, "op": op, "frame": frame, "why": why})
            continue
        kept.append(at)
        new.append({"name": item["id"], "frame": at, "gain_db": gain, "max_ms": int(round(item["seconds"] * 1000))})
    return new, dropped


def plan(job: Path, *, library: Path | None = None, write: bool = True) -> dict:
    """Derive ``sound_mix_manifest/2`` for a job (deterministic: the same inputs give the same bytes) and write it with its report.
    ``library`` is the sound library root (default: the repository's); procedural room tones and hits the library lacks are
    registered there."""
    return plan_with_report(job, library=library, write=write)[0]


def plan_with_report(job: Path, *, library: Path | None = None, write: bool = True) -> tuple[dict, dict]:
    """``plan`` and its ``sound_director_report.json`` (findings, the choices that were inferred, dropped vacuums, counts)."""
    job = Path(job)
    root = Path(library) if library is not None else assets_reuse.SOUND_LIB
    spine_path, timed_path = job / "audio" / "audio_spine.json", job / "timed.json"
    if not spine_path.exists():
        raise ContractError("no audio/audio_spine.json: run python -m explainer_engine.audio.spine <job> first")
    spine, timed = _load(spine_path), _load(timed_path)
    contracts.validate(spine, job)
    shots_path, edit_path = job / "film_shots.json", job / "audio" / "edit_and_grade_manifest.json"
    play_path = job / "story" / "screenplay_spine.json"
    film = _load(shots_path) if shots_path.exists() else None
    edit = _load(edit_path) if edit_path.exists() else None
    screenplay = _load(play_path) if play_path.exists() else None
    fps, total = spine["fps"], spine["total_frames"]
    fr = lambda s: min(total, max(0, int(round(float(s) * fps))))  # noqa: E731
    timeline = shot_timeline(spine, timed, film, edit, screenplay=screenplay)
    bounds = scene_bounds(spine)
    words = spine["words"]
    inferred: list[dict] = []
    findings: list[dict] = []
    notes: dict = {"dropped_vacuums": [], "unmatched_sounds": [], "dropped_cues": []}

    # scenes: acoustic, place, IR seed
    ctx: dict = {}
    for sid, (a, b) in bounds.items():
        mine = [s for s in timeline if s["scene"] == sid]
        dramatic = [s for s in mine if s["lane"] not in NEUTRAL_LANES]
        if mine and not dramatic:
            ac, src, place, text = "neutral", "inferred", None, ""
        elif dramatic:
            ac, src, place, text = dramatic[0]["acoustic"], dramatic[0]["acoustic_source"], dramatic[0]["place"], dramatic[0]["place_text"]
        else:
            ac, src, place, text = "outdoor", "inferred", None, ""
        ctx[sid] = {"start": a, "end": b, "acoustic": ac, "source": src, "place": place, "key": place or text, "shots": mine}
        if src == "inferred":
            inferred.append({"scene": sid, "what": "acoustic", "value": ac, "from": text or "(no place text)"})

    # vacuums (BP-120): the top vacuums_max reveals, each ending on its reveal frame, shrunk to the pause or dropped
    vs_lo, vs_hi = SR.T("BP-120", "vacuum_s")
    vlen, vmin = fr(_mid((vs_lo, vs_hi))), fr(vs_lo)
    vacuums: list[dict] = []
    for ev in _ranked_events(timeline)[:int(SR.T("BP-120", "vacuums_max"))]:
        end = ev["frame"]
        start = max(0, end - vlen)
        if any(w["start_frame"] < end and w["end_frame"] > end for w in words):  # a word runs through the reveal frame
            start = end
        else:
            before = [w["end_frame"] for w in words if w["end_frame"] <= end]
            start = max(start, max(before)) if before and max(before) > start else start
        if end - start < vmin:
            notes["dropped_vacuums"].append({"frame": end, "shot": ev["shot_id"], "kind": ev["kind"], "pause_frames": end - start})
            continue
        vacuums.append({"start_frame": start, "end_frame": end, "reason": f"{ev['kind']} {ev['shot_id']}: {ev['label']}"[:120], "reveal_frame": end})
    vacuums.sort(key=lambda v: v["start_frame"])

    # scene entries: J, L or butt, and the lead (BP-117); an edit cut's audio_lead_frames overrides both
    scenes = []
    j_lead, l_lead = fr(abs(_mid(SR.T("BP-117", "j_cut_s")))), fr(_mid(SR.T("BP-117", "l_cut_s")))
    ids = list(bounds)
    for k, sid in enumerate(ids):
        c = ctx[sid]
        entry, lead = "butt", 0
        if k > 0:
            prev = ctx[ids[k - 1]]
            first = c["shots"][0] if c["shots"] else None
            cut = first["cut"] if first else None
            if cut is not None:
                lead = int(cut["audio_lead_frames"])
                entry = "L" if cut["cut_type"] == "KULESHOV_L_CUT" else ("J" if lead > 0 else "butt")
                if entry == "L" and lead == 0:
                    lead = l_lead
            elif c["acoustic"] != prev["acoustic"] or c["key"] != prev["key"]:
                entry, lead = "J", j_lead
            lead = min(lead, prev["end"] - prev["start"] if entry == "J" else c["end"] - c["start"])
            for v in vacuums:  # the lead never crosses a vacuum
                if entry == "J" and v["end_frame"] > c["start"] - lead and v["start_frame"] < c["start"]:
                    lead = max(0, c["start"] - v["end_frame"]) if v["end_frame"] <= c["start"] else 0
                if entry == "L" and v["start_frame"] < c["start"] + lead and v["end_frame"] > c["start"]:
                    lead = max(0, v["start_frame"] - c["start"]) if v["start_frame"] >= c["start"] else 0
            if lead == 0 and entry != "butt":
                entry = "butt"
        c["entry"], c["lead"] = entry, lead
        scenes.append({"scene": sid, "start_frame": c["start"], "end_frame": c["end"], "acoustic": c["acoustic"],
                       "acoustic_source": c["source"], "ir_seed": acoustics.seed_of(sid), "entry": entry, "lead_frames": lead})

    # beds: a room tone under every scene, the editor's timed beds on top, native clip audio by the matrix
    mid_rms = _mid(SR.T("BP-116", "room_tone_dbfs"))
    half, beds = fr(XFADE_S) // 2, []
    scene_gain, amb_gain = {}, {}
    for k, sid in enumerate(ids):
        c = ctx[sid]
        item = _room_tone(root, c["acoustic"], _slug(c["place"]) if c["place"] else None)
        gain = round(mid_rms + (item["peak_dbfs"] - item["rms_dbfs"]), 2)  # peak-normalised bed: RMS = gain - crest
        scene_gain[sid] = gain
        nxt = ctx[ids[k + 1]] if k + 1 < len(ids) else None
        a, b, fin, fout = c["start"], c["end"], 0, 0
        if k > 0:  # the bed meets the previous scene's in an overlap: J before the cut, L after it, a short one centred on a butt
            if c["entry"] == "J":
                a, fin = c["start"] - c["lead"], c["lead"]
            elif c["entry"] == "L":
                fin = c["lead"]
            else:
                a, fin = c["start"] - half, 2 * half
        if nxt is not None:
            if nxt["entry"] == "J":
                fout = nxt["lead"]
            elif nxt["entry"] == "L":
                b, fout = c["end"] + nxt["lead"], nxt["lead"]
            else:
                b, fout = c["end"] + half, 2 * half
        beds.append({"id": f"rt{k + 1:02d}", "scene": sid, "kind": "room_tone", "ref": item["id"], "gain_db": gain,
                     "start_frame": max(0, a), "end_frame": min(total, b), "fade_in_frames": fin, "fade_out_frames": fout})
    for n, b in enumerate(timed.get("audio", {}).get("beds", []), start=1):
        a, z = fr(b["start"]), fr(b["end"])
        sid = b.get("segment") if b.get("segment") in bounds else next((s for s, (x, y) in bounds.items() if x <= a < y), ids[-1])
        fd = fr(b.get("fade_s", 0))
        beds.append({"id": f"amb{n:02d}", "scene": sid, "kind": "ambience", "ref": b["sound"], "gain_db": float(b["gain_db"]),
                     "start_frame": a, "end_frame": z, "fade_in_frames": fd, "fade_out_frames": fd})
        amb_gain.setdefault(sid, float(b["gain_db"]))
    under = float(SR.T("BP-160", "native_under_bed_db"))
    for s in timeline:
        if MATRIX[s["lane"]]["native"] in ("bed", "bed if present") and (job / "audio" / "native" / f"{s['id']}.wav").exists():
            fd = fr(XFADE_S) // 2
            beds.append({"id": f"nat_{s['id']}", "scene": s["scene"], "kind": "native", "ref": f"native/{s['id']}",
                         "gain_db": round(amb_gain.get(s["scene"], scene_gain[s["scene"]]) - under, 2), "start_frame": s["start_frame"],
                         "end_frame": min(total, s["end_frame"]), "fade_in_frames": fd, "fade_out_frames": fd})

    # spots: the timed sfx (word-anchored), foley and loudest by the matrix, three-layer hits on reveals and HARD accents
    spots: list[dict] = []
    wstarts = [w["start_frame"] for w in words]

    def add_spot(**kw):
        spots.append({"id": f"sp{len(spots) + 1:03d}", **kw})

    for e in timed.get("audio", {}).get("sfx", []):
        f = fr(e["start"])
        k = min(range(len(words)), key=lambda i: abs(wstarts[i] - f)) if words else None
        near = k is not None and abs(wstarts[k] - f) <= FRAME_TOL
        sh = _shot_at(timeline, f)
        pan, persp, extra = _pan_of(sh)
        add_spot(shot_id=sh["id"] if sh else "none", ref=e["sound"], word_index=k if near else None, frame=None if near else f,
                 stem="sfx", pan=pan, perspective=persp, gain_db=float(e.get("gain_db", SPOT_DB)) + extra, group=None, layer="single",
                 origin="timed_sfx")
    fm = max(1, round(delivery.frame_ms(fps) / 1000 * fps))
    for s in timeline:
        mode = _spots_allowed(s["lane"])
        if s["lane"] is None or mode in ("none", "cues only"):
            continue
        foley_texts = s["foley"][:1] if mode == "foley, one" else (s["foley"] if mode in ("foley", "foley+loudest") else [])
        texts = [(t, "foley") for t in foley_texts] + ([(s["loudest"], "loudest")] if s["loudest"] and mode in ("loudest", "foley+loudest") else [])
        for text, origin in texts:
            item = _match_sound(root, text)
            if item is None:
                notes["unmatched_sounds"].append({"shot": s["id"], "text": text})
                findings.append(_f("SD-12", s["id"], f"{origin} {text!r} has no library sound: register one (OR-18) or the shot plays without it"))
                continue
            pan, persp, extra = _pan_of(s, text)
            add_spot(shot_id=s["id"], ref=item["id"], word_index=None, frame=min(total, s["start_frame"] + fm), stem="sfx", pan=pan,
                     perspective=persp, gain_db=(SPOT_DB if origin == "foley" else LOUDEST_DB) + extra, group=None, layer="single", origin=origin)
    hit_frames: list[int] = []
    hits = None
    sync = fr(SR.T("BP-54", "late_max_ms") / 1000)
    for s in timeline:
        for e in s["events"]:
            if e["kind"] == "loudest" and not any(v["reveal_frame"] == e["frame"] for v in vacuums):
                continue
            if _no_hits(s["lane"]) or any(abs(e["frame"] - h) <= sync for h in hit_frames):
                continue
            hits = hits or _hit_items(root)
            hit_frames.append(e["frame"])
            pan, persp, _x = _pan_of(s)
            for layer in ("sub", "body", "air"):
                add_spot(shot_id=s["id"], ref=hits[layer]["id"], word_index=None, frame=e["frame"], stem="sfx", pan=pan, perspective=persp,
                         gain_db=HIT_DB[layer], group=f"hit@{e['frame']}", layer=layer, origin="hit")

    # music, cues, dialogue, narration
    lib = {i["id"]: i for i in sfx_library.load_manifest(root)["items"]}
    music = []
    for n, m in enumerate(timed.get("audio", {}).get("music", []), start=1):
        item = lib.get(m["track"])
        one = m.get("fade_s")
        fi = float(m.get("fade_in_s", one if one is not None else SR.T("BP-62", "fade_in_s")))
        fo = float(m.get("fade_out_s", one if one is not None else SR.T("BP-62", "fade_out_s")))
        grid = None
        if item is not None:
            grid = item.get("beat_grid")
            path = root / item["file"]
            if grid is None and path.exists():
                samples, rate = sfx_library.read_wav(path.read_bytes())
                got = acoustics.beat_grid(samples, rate)
                if got is not None:
                    grid = {"bpm": got["bpm"], "offset_s": got["offset_s"], "source": "measured"}
                    _store_item_field(root, item["id"], "beat_grid", grid)
        music.append({"id": f"mu{n:02d}", "ref": m["track"], "motif_of": _owner(item) if item else None, "start_frame": fr(m["start"]),
                      "end_frame": fr(m["end"]), "gain_db": float(m.get("gain_db", -18)), "fade_in_frames": fr(fi), "fade_out_frames": fr(fo),
                      "beat_grid": grid})
    cues = [{"name": c["sound"], "frame": fr(c["start"]), "gain_db": float(c.get("gain_db", -26)), "max_ms": c.get("max_ms")}
            for c in timed.get("audio", {}).get("cues", [])]
    more, notes["dropped_cues"] = compensator_cues(job, spine, root, cues)  # F5, CMP-16: story events of maps and HUD get a quiet micro-cue
    if more:
        cues = sorted(cues + more, key=lambda c: (c["frame"], c["name"]))
    dialogue = []
    for h in spine["post_hoc_shots"]:
        has = (job / "audio" / "dialogue" / f"{h['shot_id']}.wav").exists()
        dialogue.append({"shot_id": h["shot_id"], "ref": f"dialogue/{h['shot_id']}" if has else None,
                         "start_frame": h["start_frame"], "end_frame": h["end_frame"]})
    nar = next((p for p in (job / "audio" / "narration.wav", job / "narration.wav") if p.exists()), None)
    if nar is not None:
        narration = {"ref": os.path.relpath(nar, job).replace(os.sep, "/"), "sha256": contracts.sha256_file(nar)}
    else:
        narration = {"ref": "audio/narration.wav", "sha256": spine["derived_from"]["words"]["sha256"]}
        inferred.append({"what": "narration", "value": "pinned to words.json", "from": "no narration WAV in the job at plan time"})

    lib_manifest = root / "manifest.json"
    if not lib_manifest.exists():
        write_json_atomic(lib_manifest, {"version": 1, "items": []})
    derived = {"audio_spine": _ref(job, spine_path), "timed": _ref(job, timed_path), "library": _ref(job, lib_manifest)}
    if film is not None:
        derived["film_shots"] = _ref(job, shots_path)
    manifest = {"schema": "sound_mix_manifest/2", "derived_from": derived, "fps": fps, "total_frames": total,
                "stems": ["narration", "music", "sfx", "ambience"] + (["dialogue"] if dialogue else []), "narration": narration,
                "dialogue": dialogue, "scenes": scenes, "beds": beds, "music": music, "vacuums": vacuums, "cues": cues, "spots": spots,
                "presence_dip": {"rule": "BP-118"}, "perspective": {"rule": "BP-122"}, "master": {"rule": "BP-50"}}
    contracts.validate(manifest, job)
    lib_items = sfx_library.load_manifest(root)["items"]
    findings += check(manifest, spine=spine, timeline=timeline, library=lib_items, job=job)
    report = {"findings": findings, "inferred": inferred, **notes,
              "counts": {"scenes": len(scenes), "beds": len(beds), "spots": len(spots), "hits": len(hit_frames), "vacuums": len(vacuums),
                         "music": len(music), "cues": len(cues), "dialogue": len(dialogue)}}
    if write:
        write_json_atomic(job / "audio" / "sound_mix_manifest.json", manifest)
        write_json_atomic(job / "audio" / "sound_director_report.json", report)
    return manifest, report


def _store_item_field(root: Path, item_id: str, key: str, value) -> None:
    """Write a measured field back onto a library item (the beat grid is measured once and kept, spec 2.7)."""
    man = sfx_library.load_manifest(root)
    for it in man["items"]:
        if it["id"] == item_id:
            it[key] = value
    write_json_atomic(Path(root) / "manifest.json", man)


# --- the checks (spec 4.4) ------------------------------------------------------------------------------------------------

def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a, b in sorted(spans):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def speech_masks(spine: dict, n: int, sr: int = RATE) -> tuple[np.ndarray, np.ndarray]:
    """``(speech, pause)`` boolean masks over ``n`` samples. Speech: the words with 0.15 s of margin, a gap under 0.3 s closed;
    pause: at least 0.4 s from any such stretch (the duck has released by then, BP-53)."""
    fps = spine["fps"]
    ms = [(int(w["start_frame"] / fps * 1000) - 150, int(w["end_frame"] / fps * 1000) + 150) for w in spine["words"]]
    runs = _merge(ms)
    speech, near = np.zeros(n, bool), np.zeros(n, bool)
    for a, b in runs:
        speech[max(0, a * sr // 1000):max(0, b * sr // 1000)] = True
        near[max(0, (a - 400) * sr // 1000):max(0, (b + 400) * sr // 1000)] = True
    return speech, ~near


def _spot_frame(spot: dict, spine: dict) -> int:
    return spot["frame"] if spot["frame"] is not None else spine["words"][spot["word_index"]]["start_frame"]


def _crest(item: dict | None) -> float | None:
    return None if item is None else item["peak_dbfs"] - item["rms_dbfs"]


def check(manifest: dict, *, spine: dict, timeline: list[dict], stems: dict | None = None, measures: dict | None = None,
          library: list[dict] | None = None, job: Path | None = None, ramps: tuple[float, float] = RAMPS_S) -> list[dict]:
    """SD findings ``{rule, severity, where, detail, basis}``. Plan-time (always): SD-01 coverage and level, SD-03, SD-05 hits and
    onsets, SD-06 counts and speech, SD-07, SD-08, SD-09, SD-10, SD-11, SD-12, SD-13 and, with ``job``, SD-15 freshness. Render-time
    (``stems``, arrays of the rendered stems and optionally ``mix``): SD-02, SD-04, SD-06 level, SD-05 band shares from ``measures``
    (``hit_band_share``), and BP-52 from ``measures`` (``voice_lu``, ``music_lu``, ``bed_lu``) through ``qa/targets.gap_verdict``."""
    out: list[dict] = []
    fps, total = manifest["fps"], manifest["total_frames"]
    lib = {i["id"]: i for i in library or []}
    by_shot = {s["id"]: s for s in timeline}
    ms = lambda frames: frames / fps * 1000.0  # noqa: E731

    if job is not None:  # SD-15: CN-02
        for f in contracts.derived_findings(manifest, job):
            out.append(_f("SD-15", f["where"], f["detail"], None))

    # SD-01: a room-tone bed over the whole span of every scene, at the middle of BP-116's band
    lo, hi = SR.T("BP-116", "room_tone_dbfs")
    for sc in manifest["scenes"]:
        spans = _merge([(b["start_frame"], b["end_frame"]) for b in manifest["beds"] if b["scene"] == sc["scene"] and b["kind"] == "room_tone"])
        if not any(a <= sc["start_frame"] and z >= sc["end_frame"] for a, z in spans):
            out.append(_f("SD-01", sc["scene"], f"no room-tone bed over the whole span {sc['start_frame']}..{sc['end_frame']} (BP-116: "
                                                 f"no cut falls to digital silence); the bed covers {spans or 'nothing'}"))
        for b in (x for x in manifest["beds"] if x["scene"] == sc["scene"] and x["kind"] == "room_tone"):
            crest = _crest(lib.get(b["ref"]))
            if crest is not None and not lo - 0.25 <= b["gain_db"] - crest <= hi + 0.25:
                out.append(_f("SD-01", b["id"], f"room tone placed at {b['gain_db'] - crest:.1f} dBFS RMS, outside BP-116's {lo:g}..{hi:g}"))

    # SD-03: J or L at a place or acoustic change; no butt cut between a map and a drama shot
    ids = [s["scene"] for s in manifest["scenes"]]
    for k in range(1, len(ids)):
        cur, prev = manifest["scenes"][k], manifest["scenes"][k - 1]
        a = [s for s in timeline if s["scene"] == prev["scene"]]
        b = [s for s in timeline if s["scene"] == cur["scene"]]
        if cur["entry"] != "butt":
            continue
        if prev["acoustic"] != cur["acoustic"]:
            out.append(_f("SD-03", cur["scene"], f"acoustic changes {prev['acoustic']} -> {cur['acoustic']} on a butt cut: the next scene's sound "
                                                 "should lead (J) or the last one trail (L), BP-117"))
        if a and b and ((a[-1]["lane"] in NEUTRAL_LANES and b[0]["lane"] in DRAMA_LANES) or (a[-1]["lane"] in DRAMA_LANES and b[0]["lane"] in NEUTRAL_LANES)):
            out.append(_f("SD-03", cur["scene"], f"a butt cut between a {a[-1]['lane']} and a {b[0]['lane']} shot (BP-117)"))

    # SD-05: every reveal, turn and HARD accent has a three-layer hit, its layers together, its onset inside BP-54's window
    groups: dict = {}
    for s in manifest["spots"]:
        if s["group"]:
            groups.setdefault(s["group"], []).append(_spot_frame(s, spine))
    near = int(L.NEAR * fps)
    early, late, sync = SR.T("BP-54", "early_max_ms"), SR.T("BP-54", "late_max_ms"), SR.T("BP-119", "sync_ms")
    for s in timeline:
        for e in s["events"]:
            if e["kind"] == "loudest" or _no_hits(s["lane"]):
                continue
            cand = [(min(fs), max(fs)) for fs in groups.values() if abs(min(fs) - e["frame"]) <= near]
            where = f"{s['id']} {e['kind']} at frame {e['frame']}"
            if not cand:
                out.append(_f("SD-05", where, "no three-layer hit (sub, body, air) lands on this event (BP-119)"))
                continue
            onset, last = min(cand, key=lambda c: abs(c[0] - e["frame"]))
            dt = ms(onset - e["frame"])
            if dt < -early or dt > late:
                out.append(_f("SD-05", where, f"the hit's onset is {abs(dt):.0f} ms {'early' if dt < 0 else 'late'}; BP-54 allows {early:g} ms early and "
                                              f"{late:g} ms late, and a miss goes late, never early", "BP-54"))
            if ms(last - onset) > sync:
                out.append(_f("SD-05", where, f"the hit's layers start {ms(last - onset):.0f} ms apart (BP-119: within {sync:g} ms)"))

    # SD-06: at most vacuums_max, each inside vacuum_s, none over speech, one before each of the top reveals
    vs_lo, vs_hi = SR.T("BP-120", "vacuum_s")
    vmax = int(SR.T("BP-120", "vacuums_max"))
    vacs = manifest["vacuums"]
    if len(vacs) > vmax:
        out.append(_f("SD-06", "vacuums", f"{len(vacs)} vacuums; BP-120 allows {vmax}"))
    for v in vacs:
        sec = (v["end_frame"] - v["start_frame"]) / fps
        if not vs_lo - 1.5 / fps <= sec <= vs_hi + 1.5 / fps:
            out.append(_f("SD-06", f"vacuum {v['start_frame']}", f"{sec:.2f} s long; BP-120 wants {vs_lo:g}..{vs_hi:g} s"))
        if any(w["start_frame"] < v["end_frame"] and w["end_frame"] > v["start_frame"] for w in spine["words"]):
            out.append(_f("SD-06", f"vacuum {v['start_frame']}", "narration runs inside the vacuum: it is never laid over speech"))
        if v["reveal_frame"] != v["end_frame"]:
            out.append(_f("SD-06", f"vacuum {v['start_frame']}", "the vacuum does not end on its reveal"))
    for e in _ranked_events(timeline)[:vmax]:
        if not any(v["reveal_frame"] == e["frame"] for v in vacs):
            out.append(_f("SD-06", f"{e['shot_id']} {e['kind']}", f"no vacuum before this reveal at frame {e['frame']}: narration runs to it or the "
                                                                     f"pause is under {vs_lo:g} s (BP-120)"))

    # SD-07: pans inside sfx_pan_max and on the focal side; encoded stems centred
    mx = float(SR.T("BP-121", "sfx_pan_max"))
    for s in manifest["spots"]:
        sh = by_shot.get(s["shot_id"])
        if abs(s["pan"]) > mx + 1e-9:
            out.append(_f("SD-07", s["id"], f"pan {s['pan']:+.2f} is outside +-{mx:g} (BP-121)"))
        elif s["stem"] in ("narration", "dialogue") and s["pan"] != 0:
            out.append(_f("SD-07", s["id"], f"a {s['stem']} spot pans {s['pan']:+.2f}: narration and dialogue stay centred"))
        elif sh is not None and sh["lane"] not in NEUTRAL_LANES and abs(sh["focal_x"] - 0.5) > 0.05 and s["pan"] != 0:
            offscreen = s["perspective"] == "far" and abs(abs(s["pan"]) - mx) < 1e-9
            if (s["pan"] > 0) != (sh["focal_x"] > 0.5) and not offscreen:
                out.append(_f("SD-07", s["id"], f"pan {s['pan']:+.2f} is on the wrong side of the focal point ({sh['focal_x']:.2f})"))
        if sh is not None and sh["lane"] in NEUTRAL_LANES + ("HOST_COMMENTARY",) and s["pan"] != 0:
            out.append(_f("SD-07", s["id"], f"{sh['lane']} spots are centred, this one pans {s['pan']:+.2f}"))

    # SD-08: one encoded layer at a time; same-colour layers; total layers
    for d in manifest["dialogue"]:
        if any(w["start_frame"] < d["end_frame"] and w["end_frame"] > d["start_frame"] for w in spine["words"]):
            out.append(_f("SD-08", d["shot_id"], "narration plays inside a dialogue window: two encoded layers at once (CRAFT-SND-09)"))
    cap = int(SR.T("BP-121", "same_colour_layers"))  # floor(2.5)

    def over(rows: list[dict], gain_key: str, label: str):
        edges = sorted({r["start_frame"] + r.get("fade_in_frames", 0) for r in rows} | {r["end_frame"] - r.get("fade_out_frames", 0) for r in rows})
        for t in edges:
            live = [r for r in rows if r["start_frame"] + r.get("fade_in_frames", 0) <= t < r["end_frame"] - r.get("fade_out_frames", 0)]
            if len(live) > cap:
                g = sorted(r[gain_key] for r in live)
                if not (len(live) == cap + 1 and g[0] <= g[1] - 6.0):  # one more only when it sits 6 dB under the others
                    out.append(_f("SD-08", f"{label} at frame {t}", f"{len(live)} {label} layers at once; at most {cap}, a third only 6 dB under the others (BP-121)"))
                    return
    over(manifest["beds"], "gain_db", "bed")
    over(manifest["music"], "gain_db", "music")
    span = int(SPOT_S * fps)
    pos = sorted((_spot_frame(s, spine), s["group"] or s["id"]) for s in manifest["spots"])
    for k, (f0, _g) in enumerate(pos):
        live = {g for f1, g in pos[k:] if f1 < f0 + span}
        music_on = any(m["start_frame"] <= f0 < m["end_frame"] for m in manifest["music"])
        if len(live) > L.MAX_SFX_AT_ONCE or 1 + music_on + 1 + len(live) > L.MAX_LAYERS:
            out.append(_f("SD-08", f"frame {f0}", f"{len(live)} effects with the voice, music and bed: at most {L.MAX_SFX_AT_ONCE} effects and "
                                                 f"{L.MAX_LAYERS} layers (BP-56)"))
            break

    # SD-09: perspective follows the size; one IR per scene
    seeds: dict = {}
    for sc in manifest["scenes"]:
        seeds.setdefault(sc["scene"], set()).add(sc["ir_seed"])
        if sc["ir_seed"] != acoustics.seed_of(sc["scene"]):
            out.append(_f("SD-09", sc["scene"], "the scene's impulse response seed is not derived from its id"))
    for sid, sd in seeds.items():
        if len(sd) > 1:
            out.append(_f("SD-09", sid, f"{len(sd)} impulse responses in one scene: BP-122 gives all its shots one"))
    for sid in ids:
        kinds = {s["acoustic"] for s in timeline if s["scene"] == sid and s["lane"] not in NEUTRAL_LANES}
        if len(kinds) > 1:
            out.append(_f("SD-09", sid, f"its shots disagree on the acoustic ({sorted(kinds)}): one impulse response per scene"))
    for s in manifest["spots"]:
        sh = by_shot.get(s["shot_id"])
        if sh is None or sh["size"] is None or sh["lane"] in NEUTRAL_LANES + ("HOST_COMMENTARY",):
            continue
        want = SIZE_PERSPECTIVE[sh["size"]]
        offscreen = s["perspective"] == "far" and abs(abs(s["pan"]) - mx) < 1e-9
        if s["perspective"] != want and not offscreen:
            out.append(_f("SD-09", s["id"], f"perspective {s['perspective']} in a {sh['size']} shot (it follows the size: {want}, BP-122)"))

    # SD-10: an action cut falls on the beat grid while music is up
    tol_note = SR.T("BP-123", "beat_tolerance_note")
    cuts = [(s["start_frame"], s["id"]) for s in timeline if s["cut"] and s["cut"]["cut_type"] == "ACTION_PEAK_CUT"]
    cuts += [(e["frame"], s["id"]) for s in timeline for e in s["events"] if e["kind"] == "hard" and abs(e["frame"] - s["start_frame"]) <= FRAME_TOL]
    for f0, sid in sorted(set(cuts)):
        for m in manifest["music"]:
            g = m["beat_grid"]
            if g is None or not m["start_frame"] <= f0 < m["end_frame"]:
                continue
            period = 60.0 / g["bpm"]
            t = (f0 - m["start_frame"]) / fps - g["offset_s"]
            off = min(t % period, period - t % period)
            tol = tol_note * period / 2.0  # beat_tolerance_note of an eighth note (spec section 7: 250 ms at 120 BPM -> 31 ms)
            if off > tol:
                out.append(_f("SD-10", f"{sid} at frame {f0}", f"the cut is {off * 1000:.0f} ms off music {m['id']}'s beat grid "
                                                               f"({g['bpm']:g} BPM); BP-123 allows {tol * 1000:.0f} ms"))

    # SD-11: one motif per owner (the library); SD-13: a free-generator take needs its admission
    owners: dict = {}
    for it in library or []:
        if _owner(it):
            owners.setdefault(_owner(it), []).append(it["id"])
    for owner, found in sorted(owners.items()):
        if len(found) > 1:
            out.append(_f("SD-11", owner, f"{len(found)} motifs for one owner: {sorted(found)} (BP-123: one motif each)"))
    used = {b["ref"] for b in manifest["beds"]} | {m["ref"] for m in manifest["music"]} | {s["ref"] for s in manifest["spots"]}
    for ref in sorted(used):
        it = lib.get(ref)
        if it is not None and it["source"]["kind"] == "open_model" and not it["source"].get("admission"):
            out.append(_f("SD-13", ref, "a free-generator take without an admission for its kind (BP-162): library first, then the connector"))
        elif it is not None and it["source"]["kind"] == "open_model":   # the admission must exist, fit the kind and the model
            from explainer_engine.audio import generator_gate
            out += [_f("SD-13", ref, problem) for problem in generator_gate.item_problems(it)]

    # SD-12: the lane matrix and the timeline hold
    done: set = set()
    for s in timeline:
        if s["estimated"] and s["scene"] not in done:
            done.add(s["scene"])
            out.append(_f("SD-12", s["scene"], "the shot timeline is estimated: the shots do not add up to the scene's length within a frame "
                                               "(laid as written, never stretched)"))
    for d in manifest["dialogue"]:
        if d["ref"] is None:
            out.append(_f("SD-12", d["shot_id"], "a dialogue window without its clip: room tone plays, never silence"))
    for s in manifest["spots"]:
        sh = by_shot.get(s["shot_id"])
        if sh is not None and sh["lane"] is not None and _spots_allowed(sh["lane"]) in ("none", "cues only"):
            out.append(_f("SD-12", s["id"], f"a spot in a {sh['lane']} shot, whose matrix row allows {_spots_allowed(sh['lane'])}"))

    if stems:
        out += _check_stems(manifest, spine, stems, measures or {}, ramps)
    elif measures:
        out += _check_measures(manifest, measures)
    return out


def _check_measures(manifest: dict, measures: dict) -> list[dict]:
    out = []
    floor = SR.T("BP-161", "hit_band_share_min")
    for sid, share in sorted((measures.get("hit_band_share") or {}).items()):
        if share < floor:
            out.append(_f("SD-05", sid, f"a hit layer keeps {share:.0%} of its energy in its own band; at least {floor:.0%} (BP-161)"))
    if "voice_lu" in measures and ("music_lu" in measures or "bed_lu" in measures):
        verdict = targets.gap_verdict(measures["voice_lu"], measures.get("music_lu"), measures.get("bed_lu"))
        if verdict != "PASS":
            g = targets.gaps(measures["voice_lu"], measures.get("music_lu"), measures.get("bed_lu"))
            out.append({"rule": "BP-52", "severity": verdict, "where": "stems", "basis": "BP-52",
                        "detail": "background under the voice while speaking: " + ", ".join(f"{k} {v:.1f} LU" for k, v in g.items())})
    return out


def _mid_channel(a: np.ndarray) -> np.ndarray:
    return a.mean(axis=1) if a.ndim == 2 else a


def _check_stems(manifest: dict, spine: dict, stems: dict, measures: dict, ramps: tuple[float, float]) -> list[dict]:
    out = _check_measures(manifest, measures)
    fps = manifest["fps"]
    mix = stems.get("mix")
    if mix is None:
        parts = [_mid_channel(v) for k, v in stems.items() if k != "room_tone"]
        mix = np.sum(parts, axis=0) if parts else np.zeros(0, np.float32)
    mix = _mid_channel(mix)
    # SD-02: no 10 ms window of the mix under the digital-silence floor between the opening ramp and the final fade
    h = max(1, int(SR.T("BP-161", "window_ms") / 1000 * RATE))
    a, z = int(ramps[0] * RATE), len(mix) - int(ramps[1] * RATE)
    if z - a >= h:
        w = mix[a:a + (z - a) // h * h].astype(np.float64).reshape(-1, h)
        floor = float(SR.T("BP-161", "digital_silence_dbfs"))
        db = 10 * np.log10(np.mean(w ** 2, axis=1) + 1e-20)
        bad = np.flatnonzero(db < floor)
        if len(bad):
            out.append(_f("SD-02", "mix", f"{len(bad)} window(s) of {h * 1000 // RATE} ms under {floor:g} dBFS, the first at {(a + bad[0] * h) / RATE:.2f} s "
                                          "(BP-161: no digital silence between the opening ramp and the final fade)"))
    # SD-04: the background's share of the presence band under speech against the pauses
    lo, hi = SR.T("BP-118", "measure_band_hz")
    need = float(SR.T("BP-118", "notch_depth_db")[0])
    speech, pause = speech_masks(spine, len(mix))
    for name in ("music", "ambience"):
        if name not in stems:
            continue
        x = _mid_channel(stems[name])
        s_in, s_out = acoustics.band_share(x, RATE, lo, hi, speech[:len(x)]), acoustics.band_share(x, RATE, lo, hi, pause[:len(x)])
        if s_in is None or s_out is None:
            continue
        gap = 10 * np.log10(s_in / s_out)
        if gap > -need:
            out.append(_f("SD-04", name, f"the {lo:g}-{hi:g} Hz share of the {name} stem is {gap:+.2f} dB under speech against the pauses; "
                                         f"BP-118 wants at least {need:g} dB less"))
    # SD-06: the level of the dipped stems inside each vacuum
    target = float(SR.T("BP-120", "vacuum_dbfs"))
    ramp = int(VACUUM_RAMP_MS / 1000 * RATE)
    for v in manifest["vacuums"]:
        a, z = int(v["start_frame"] / fps * RATE) + ramp, int(v["end_frame"] / fps * RATE)
        for name in ("music", "sfx", "ambience"):
            if name not in stems or z - a < RATE // 20:
                continue
            x = _mid_channel(stems[name]).astype(np.float64)
            seg = x[a:z] - (_mid_channel(stems["room_tone"]).astype(np.float64)[a:z] if name == "ambience" and "room_tone" in stems else 0.0)
            level = acoustics.rms_db(seg)
            if level > target + 1.0:
                out.append(_f("SD-06", f"vacuum {v['start_frame']} {name}", f"{level:.1f} dBFS inside the vacuum; BP-120 wants {target:g} dBFS"))
    return out


# --- command line ---------------------------------------------------------------------------------------------------------

def _load_stems(directory: Path) -> dict:
    import wave
    out = {}
    for p in sorted(Path(directory).glob("*.wav")):
        with wave.open(str(p)) as w:
            raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            out[p.stem] = raw.reshape(-1, w.getnchannels())
    return out


def check_job(job: Path, *, stems: dict | None = None, measures: dict | None = None, library: Path | None = None) -> list[dict]:
    """``check`` on a job folder: the manifest, spine and shot timeline are read from the job, the library is the root the manifest was
    planned against (its ``derived_from.library`` folder) unless ``library`` names one. ``stems`` and ``measures`` add the render half."""
    job = Path(job)
    manifest, spine = _load(job / "audio" / "sound_mix_manifest.json"), _load(job / "audio" / "audio_spine.json")
    timed = _load(job / "timed.json")
    film = _load(job / "film_shots.json") if (job / "film_shots.json").exists() else None
    edit_p, play_p = job / "audio" / "edit_and_grade_manifest.json", job / "story" / "screenplay_spine.json"
    timeline = shot_timeline(spine, timed, film, _load(edit_p) if edit_p.exists() else None,
                             screenplay=_load(play_p) if play_p.exists() else None)
    if library is not None:
        root = Path(library)
    else:
        root = (job / manifest["derived_from"]["library"]["path"]).parent
        root = root if (root / "manifest.json").exists() else assets_reuse.SOUND_LIB
    return check(manifest, spine=spine, timeline=timeline, stems=stems, measures=measures,
                 library=sfx_library.load_manifest(root)["items"], job=job)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    opts: dict = {}
    for flag in ("--library", "--stems"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = args[i + 1] if i + 1 < len(args) else ""
            del args[i:i + 2]
    strict = "--strict" in args
    args = [a for a in args if a != "--strict"]
    if args and args[0] == "matrix":
        if args[1:] == ["write"]:
            text = DOC.read_text(encoding="utf-8")
            head, rest = text.split(MATRIX_MARKERS[0], 1)
            DOC.write_text(head + MATRIX_MARKERS[0] + "\n" + render_matrix() + "\n" + MATRIX_MARKERS[1] + rest.split(MATRIX_MARKERS[1], 1)[1], encoding="utf-8")
            print(f"wrote the matrix table into {DOC}")
        else:
            print(render_matrix())
        return 0
    if len(args) != 2 or args[0] not in ("plan", "check"):
        print(__doc__)
        return 2
    job = Path(args[1])
    root = Path(opts["--library"]) if "--library" in opts else assets_reuse.SOUND_LIB
    try:
        if args[0] == "plan":
            _manifest, report = plan_with_report(job, library=root)
            findings = report["findings"]
            print(f"{job / 'audio' / 'sound_mix_manifest.json'}: {report['counts']}")
        else:
            stems = _load_stems(Path(opts["--stems"])) if "--stems" in opts else None
            findings = check_job(job, stems=stems, library=Path(opts["--library"]) if "--library" in opts else None)
    except (ContractError, FileNotFoundError, KeyError) as exc:
        print(f"sound director: {exc}")
        return 1
    for f in findings:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    print(f"{len(findings)} finding(s)")
    return 1 if any(f["severity"] == "FAIL" or strict for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
