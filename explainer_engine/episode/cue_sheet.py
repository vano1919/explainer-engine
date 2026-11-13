"""The cue sheet (SP-06, docs/EPISODE_FIRST.md): the sound plan (``episode/sound_plan``) turned into concrete cues, one row per
sound that plays, so the renderer (``audio/stems``) plays rows and never decides anything itself.

``build(plan, sources, library_root)`` gives every row its asset (a library take, a placeholder in a preview, the episode's read
or the place's room tone), its time (start, end, the sync point it lands on), its layer (one of ``LAYERS``), its gain (the kind's
level ``LEVELS`` plus the distance offset ``DISTANCE_DB``), pan, fades, pitch, a low-pass for distance, a reverb, its ducking group,
its priority, why it was chosen, how sure the choice is, and the asset's licence.

* Ambience: one row per bed class (the place's bed with its J/L lead and tail) plus the room tone; a place sound named in one shot
  is a shot-long row over the bed. Loops are preferred for ambience, one-shots for foley and spots.
* Events: each sound_plan event, with variation (BP-57: the same class rotates through its takes, with a small pitch and gain
  jitter that depends only on the cue id, so a rerender is identical).
* Music: one row per run of segments with the same mood (a cue carries on across segments of one mood instead of restarting),
  a crossfade at each change of mood; the track is chosen by mood, era and intensity from the library's catalog.
* Transition: an authored transition event, or a designed one at a segment boundary where the story turns tense, or rises by
  two steps of intensity into a violent mood (tense -> aggressive): a riser that ends on the cut; never a diegetic sound the
  picture does not show.

``validate(sheet, plan, library_root)`` returns gate rows (``qa/gates``): coverage states, undeclared silence, the required
ambience, assets that exist, the licence of the music (and its credit line), value ranges, events inside their shot and on their
sync point (BP-54), overlaps (BP-56) and repeats (BP-57). ``coverage_report`` writes what each shot carries, per layer.

AV contract (2026-11-13, D-135): every event row carries its ``event_id``, the decision and sync of the visible event it plays,
and a one-shot starts its take at the take's own onset (``asset_offset_s`` skips the take's lead-in, so the sound lands on the
frame, BP-54). An event whose class has no real take is ``review_required`` in ``missing`` (never an unrelated sound). The
AV rows of ``validate``: ``events_on_sync`` in BP-54's three bands (within one frame PASS; inside -45/+125 ms REVIEW; outside
FAIL), ``purpose_and_share`` (BP-55: a purpose on every effect, at most half of the visual beats with an audible non-cue
effect; a silent_by_design beat is a beat, never a missing sound), ``overlap`` from the rows' intervals (BP-56: at most 2 of
one class and 5 layers in all, the voice, the music and the bed counted once each), ``cue_density`` (BP-81) and
``review_required_events``. The measured onsets on the rendered SFX stem come from ``audio/stems.onsets``.
"""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path

from explainer_engine.audio import sfx_library
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic
from explainer_engine.episode import sound_plan as SP
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR_RULES

SCHEMA = "cue_sheet/1"
LAYERS = ("narration", "ambience", "foley", "spot", "music", "transition")
# RMS of one cue in dBFS before ducking (engineering defaults kept under BP-65's caps: effect -8 dB, bed -15 dB peaks)
LEVELS = {"spot": -26.0, "foley": -30.0, "ambience": -36.0, "music": -32.0, "clip_audio": -36.0, "transition": -30.0}
ROOM_TONE_DB = -54.0                 # the place's floor (BP-60/BP-161: never digital silence)
BED_STEP_DB = 3.0                    # each further class of a bed sits this much under the one before
# distance -> gain offset, low-pass and reverb (engineering defaults: a far source is quieter, duller and wetter)
DISTANCE_DB = {"close": 0.0, "medium": -4.0, "distant": -9.0}
DISTANCE_LOWPASS_HZ = {"close": None, "medium": 9000.0, "distant": 4500.0}
DISTANCE_REVERB = {"close": "dry", "medium": "air", "distant": "air_far"}
PRIORITY = {"narration": 1, "spot": 2, "foley": 3, "transition": 3, "music": 4, "ambience": 5}
DUCK_GROUP = {"narration": "voice", "music": "music", "ambience": "bed", "spot": "fx", "foley": "fx", "transition": "fx"}
CONFIDENCE = {"authored": 0.95, "measured": 0.85, "action": 0.75, "estimated": 0.6, "bed": 0.8, "music": 0.7,
              "designed": 0.7, "line": 1.0}
MUSIC_XFADE_S = 2.0                  # crossfade between two music cues (equal power)
MUSIC_FADE_S = 2.0                   # fade in at the first cue, out at the last
EVENT_FADE_S = 0.01                  # click guard on a one-shot
LOOP_FADE_S = 0.2                    # a looped event's fades
SPOT_TAIL_S = 2.0                    # a one-shot may ring this far past its shot's cut (it starts inside the shot)
RISER_S = 2.5                        # a designed riser's length, ending on the cut
TENSE_MOODS = {"aggressive", "tense"}
PITCH_JITTER = float(SR_RULES.T("BP-57", "pitch_jitter"))        # +-5 % speed for a repeated class (BP-57, binding)
GAIN_JITTER_DB = float(SR_RULES.T("BP-57", "gain_jitter_db"))    # +-1.5 dB
VARIANTS_MIN = int(SR_RULES.T("BP-57", "variants_min"))
SAME_CLASS_MAX = int(SR_RULES.T("BP-56", "same_class_max"))      # BP-56 (binding): at most 2 of one class at once
LAYERS_MAX = int(SR_RULES.T("BP-56", "layers_max"))              # ... and at most 5 effect layers at once
SYNC_EARLY_MS = float(SR_RULES.T("BP-54", "early_max_ms"))
SYNC_LATE_MS = float(SR_RULES.T("BP-54", "late_max_ms"))
SILENCE_HOLE_S = 0.25                # an uncovered stretch longer than this is undeclared silence
MOOD_INTENSITY = {"aggressive": 5, "epic": 4, "heroic": 4, "tense": 3, "dark": 3, "tragic": 2, "mysterious": 2,
                  "reflective": 1, "neutral": 2, "peaceful": 1, "joyful": 2}
NEUTRAL_MOODS = ("mysterious", "reflective", "dark")      # what a segment without a named mood is scored by


def _jitter(cue_id: str, span: float) -> float:
    """A deterministic value in [-span, span] from the cue id (the same sheet renders the same sound)."""
    h = int(hashlib.sha256(cue_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return round((2 * h - 1) * span, 3)


def _items(library_root: Path) -> dict:
    p = Path(library_root) / "manifest.json"
    return {i["id"]: i for i in sfx_library.load_manifest(Path(library_root))["items"]} if p.is_file() else {}


def _seconds(item: dict, root: Path) -> float:
    if item.get("seconds"):
        return float(item["seconds"])
    path = Path(root) / item["file"]
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return 1.0


def _kind(item: dict) -> str:
    return item.get("kind") or ("loop" if item.get("loop") else "one_shot")


def _licence(item: dict | None) -> dict:
    if not item:
        return {"type": "none", "production": "n/a"}
    lic = item.get("licence") or {}
    return {"type": lic.get("type") or lic.get("status") or "unknown", "production": sfx_library.production_status(item),
            "attribution_required": bool(lic.get("attribution_required")), "attribution_text": lic.get("attribution_text")}


class Picker:
    """Takes per class from the resolved sources: the most specific take first (fewest tags beyond the class's own), loops
    first for ambience, one-shots first for events, rotating so the same class never plays the same take twice in a row
    (BP-57)."""

    def __init__(self, sources: dict, items: dict, allow_placeholder: bool):
        self.sources, self.items, self.allow = sources, items, allow_placeholder
        self.count: dict[str, int] = {}

    def pick(self, cls: str, want: str) -> tuple[str | None, str]:
        src = self.sources.get(cls) or {"status": "missing", "ids": []}
        if src["status"] != "library":
            if self.allow:                 # a preview plays a placeholder for a missing take too, and says so
                return f"placeholder:{cls}", f"placeholder (preview only; {src['status']})"
            return None, src["status"]
        ids = [i for i in src["ids"] if i in self.items] or list(src["ids"])
        want_tags = set(SP.EVENT_CLASSES.get(cls, {}).get("tags", []))
        # the most specific take first: a horse class takes plain hooves before a battle recording that also has horses in it
        bed_use = {"background_layer", "distant_layer", "musical_bed"}

        def fit(i):                      # a bed row prefers takes catalogued for a bed, an event row the others
            use = set(((self.items.get(i) or {}).get("catalog") or {}).get("usage") or [])
            return 0 if not use or bool(use & bed_use) == (want == "loop") else 1

        ids.sort(key=lambda i: (fit(i), len(set(self.items[i].get("tags", [])) - want_tags) if i in self.items else 99, i))
        pref = [i for i in ids if i in self.items and (_kind(self.items[i]) in ("loop", "track")) == (want == "loop")]
        pool = pref or ids
        k = self.count.get(cls, 0)
        self.count[cls] = k + 1
        iid = pool[k % len(pool)]
        why = f"{cls}: take {k % len(pool) + 1} of {len(pool)} ({'preferred ' + want if pref else 'any kind'})"
        return iid, why


ONSET_DB = -20.0                     # a take's onset: its envelope first within this of its peak (BP-54 measures the onset)
ONSET_HOP_S = 0.005
LEAD_MAX_S = 0.5                     # a take never skips more than this of its head


def take_onset_s(path: Path) -> float | None:
    """Where a take's sound starts: the first 5 ms window whose RMS is within ``ONSET_DB`` of the take's loudest window."""
    import numpy as np
    try:
        x, rate = sfx_library.read_wav(Path(path))
    except (OSError, ValueError, EOFError, wave.Error):
        return None
    x = np.asarray(x, np.float64)
    h = max(1, int(ONSET_HOP_S * rate))
    k = len(x) // h
    if k == 0:
        return None
    env = 20 * np.log10(np.sqrt(np.mean(x[: k * h].reshape(k, h) ** 2, axis=1)) + 1e-12)
    hit = np.flatnonzero(env >= env.max() + ONSET_DB)
    return float(hit[0] * h / rate) if hit.size else 0.0


def _row(cue_id, *, scene_id, shot_id, asset_id, start, end, layer, visual_event, sync, gain, pan=0.0, fade_in=0.0,
         fade_out=0.0, pitch=1.0, lowpass=None, reverb="dry", reason="", confidence=0.8, licence=None, offset=0.0,
         loop=False, cls=None, distance=None, event=None):
    ev = event or {}
    return {"cue_id": cue_id, "event_id": ev.get("event_id"), "decision": ev.get("decision"), "event_sync": ev.get("sync"),
            "purpose": ev.get("purpose"), "status": "placed", "scene_id": scene_id, "shot_id": shot_id, "asset_id": asset_id,
            "class": cls,
            "start_s": round(start, 3), "end_s": round(end, 3), "duration_s": round(end - start, 3), "layer": layer,
            "visual_event": visual_event, "sync_point_s": None if sync is None else round(sync, 3), "gain_db": round(gain, 2),
            "pan": round(pan, 3), "fade_in_s": round(fade_in, 3), "fade_out_s": round(fade_out, 3), "pitch": round(pitch, 4),
            "eq": {"lowpass_hz": lowpass}, "reverb": reverb, "ducking_group": DUCK_GROUP[layer], "priority": PRIORITY[layer],
            "selection_reason": reason, "confidence": confidence, "license_status": licence or {"type": "none"},
            "asset_offset_s": round(offset, 3), "loop": loop, "distance": distance}


def _music_score(item: dict, mood: str, era: str) -> float:
    c = item.get("catalog") or {}
    moods = c.get("mood") or []
    score = 0.0
    if mood in moods:
        score += 3.0 - 0.5 * moods.index(mood)
    elif mood == "neutral":
        score += max((2.0 - 0.5 * moods.index(m) for m in NEUTRAL_MOODS if m in moods), default=0.0)
    eras = c.get("historical_era") or []
    if era in eras:
        score += 1.0
    elif "any" in eras:
        score += 0.5
    elif eras:
        score -= 2.0
    if c.get("intensity"):
        score -= 0.3 * abs(int(c["intensity"]) - MOOD_INTENSITY.get(mood, 2))
    return score


def pick_music(mood: str, era: str, sources: dict, items: dict, avoid: set[str]) -> tuple[str | None, str]:
    src = sources.get("music_bed") or {"status": "missing", "ids": []}
    if src["status"] != "library":
        return None, src["status"]
    cands = [i for i in src["ids"] if i in items and sfx_library.production_status(items[i]) == "verified"]
    if not cands:
        return None, "no verified music take"
    ep_era = SP_ERA.get(era, era)
    ranked = sorted(cands, key=lambda i: (-_music_score(items[i], mood, ep_era), i in avoid, i))
    best = ranked[0]
    c = items[best].get("catalog") or {}
    return best, f"{mood} cue: {best} (moods {c.get('mood')}, eras {c.get('historical_era')}, intensity {c.get('intensity')})"


def _load_taxonomy_eras() -> dict:
    p = Path(__file__).resolve().parents[2] / "assets" / "audio" / "taxonomy.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("episode_eras", {})
    except OSError:
        return {}


SP_ERA = _load_taxonomy_eras()       # the episode's era key -> the catalog's era word (assets/audio/taxonomy.json)


def build(plan: dict, sources: dict, library_root: Path, *, allow_placeholder: bool = False) -> dict:
    root = Path(library_root)
    items = _items(root)
    pk = Picker(sources, items, allow_placeholder)
    rows, missing = [], []
    dur_ep = float(plan["duration_s"])
    silent = {s["shot_id"] for s in plan["shots"] if (s.get("design") or {}).get("state") == "INTENTIONAL_SILENCE"}
    # narration: one row per shot that carries lines (the episode's read; its own timing is the spine's)
    for s in plan["shots"]:
        if s.get("audio_line_ids"):
            rows.append(_row(f"NAR_{s['shot_id']}", scene_id=s.get("segment_id"), shot_id=s["shot_id"],
                             asset_id="narration:" + ",".join(s["audio_line_ids"]), start=s["start_s"],
                             end=s["start_s"] + s["dur_s"], layer="narration", visual_event="lines", sync=None, gain=0.0,
                             reason="the episode's read; nothing here makes a voice", confidence=CONFIDENCE["line"],
                             licence={"type": "elevenlabs_output", "production": "verified"}))
    # ambience: the beds (J/L lead and tail), each class a step under the one before, plus the room tone
    nb = len(plan["beds"])
    for bi, bed in enumerate(plan["beds"]):
        a = max(0.0, bed["start_s"] - bed.get("lead_s", 0.0))
        b = min(dur_ep, bed["end_s"] + bed.get("tail_s", 0.0))
        fi = SP.BED_FADE_S if bi > 0 else 0.0
        fo = SP.BED_FADE_S if bi + 1 < nb else 0.0
        quiet = all(sid in silent for sid in bed["shot_ids"])
        for k, cls in enumerate([] if quiet else bed["classes"]):
            iid, why = pk.pick(cls, "loop")
            if iid is None:
                missing.append({"class": cls, "why": why, "bed": bed["bed_id"]})
                continue
            rows.append(_row(f"AMB_{bed['bed_id']}_{cls}", scene_id=None, shot_id=bed["shot_ids"][0], asset_id=iid, start=a,
                             end=b, layer="ambience", visual_event=f"place {bed['place']}", sync=None,
                             gain=LEVELS["ambience"] - BED_STEP_DB * k, fade_in=fi, fade_out=fo,
                             reverb="cave" if bed["room"] == "cave" else "dry", reason=f"bed of {bed['place']}: {why}",
                             confidence=CONFIDENCE["bed"], licence=_licence(items.get(iid)), loop=True, cls=cls))
        rows.append(_row(f"TONE_{bed['bed_id']}", scene_id=None, shot_id=bed["shot_ids"][0],
                         asset_id=f"room_tone:{bed['room']}", start=a, end=b, layer="ambience", visual_event="room tone",
                         sync=None, gain=ROOM_TONE_DB, fade_in=fi, fade_out=fo,
                         reverb="cave" if bed["room"] == "cave" else "dry",
                         reason="the place's floor: never digital silence (BP-60/BP-161)", confidence=1.0,
                         licence={"type": "own_procedural", "production": "verified"}, loop=True, cls="room_tone"))
    # events
    for s in plan["shots"]:
        s0, sd = s["start_s"], s["dur_s"]
        n_ev = 0
        for ev in s["events"]:
            if ev.get("source") == "clip_audio":
                continue
            kind = ev["kind"]
            layer = {"ambience": "ambience", "foley": "foley", "spot": "spot", "transition": "transition",
                     "music": "music"}.get(kind, "spot")
            if s["shot_id"] in silent and ev["basis"] != "authored":
                continue
            want = "loop" if kind == "ambience" else "one_shot"
            iid, why = (ev["library_id"], "authored take") if ev.get("library_id") else pk.pick(ev["class"], want)
            if iid is None:
                missing.append({"class": ev["class"], "why": why, "shot_id": s["shot_id"], "event_id": ev.get("event_id"),
                                "status": "review_required"})
                continue
            at = s0 + ev["at_s"]
            item = items.get(iid)
            is_loop = kind == "ambience" or (item is not None and _kind(item) == "loop")
            lead = 0.0       # an event's take starts at its own onset (one-shots and the takes a span repeats alike)
            if kind != "ambience" and item is not None and (root / item["file"]).is_file():
                lead = min(LEAD_MAX_S, take_onset_s(root / item["file"]) or 0.0)
            length = float(ev.get("dur_s") or 0.0) or (max(1.0, s0 + sd - at) if is_loop else
                                                       (_seconds(item, root) if item else 1.0))
            end = min(dur_ep, at + length, s0 + sd + (0.0 if is_loop else SPOT_TAIL_S))
            if ev.get("sync") == "span" and not is_loop and item is not None and _seconds(item, root) - lead < end - at - 0.05:
                is_loop = True    # a continuous action lasts its span: the take repeats under it (crossfaded seams)
            dist = ev.get("distance") or "medium"
            cue_id = f"EV_{s['shot_id']}_{ev['class']}_{n_ev}"
            base = LEVELS.get(kind, LEVELS["spot"]) + (0.0 if kind == "ambience" else DISTANCE_DB.get(dist, 0.0))
            pitch = 1.0 if kind == "ambience" else round(1.0 + _jitter(cue_id + "p", PITCH_JITTER), 4)
            gain = base + (0.0 if kind == "ambience" else _jitter(cue_id + "g", GAIN_JITTER_DB))
            pan = float(ev.get("pan", 0.0 if kind == "ambience" else max(-0.3, min(0.3, ((n_ev % 5) - 2) * 0.15))))
            basis = ev["basis"].split(":")[-1] if ev["basis"].startswith("word") else ev["basis"]
            rows.append(_row(cue_id, scene_id=s.get("segment_id"), shot_id=s["shot_id"], asset_id=iid, start=at, end=end,
                             layer=layer, visual_event=ev.get("picture_event") or ev.get("what") or ev["class"],
                             sync=at, gain=gain, pan=pan,
                             fade_in=LOOP_FADE_S if kind == "ambience" else EVENT_FADE_S,   # an event starts on its frame
                             fade_out=LOOP_FADE_S if is_loop else min(0.3, max(EVENT_FADE_S, (end - at) * 0.2)),
                             pitch=pitch, lowpass=None if kind == "ambience" else DISTANCE_LOWPASS_HZ.get(dist),
                             reverb="cave" if s.get("room") == "cave" else
                             ("dry" if kind == "ambience" else DISTANCE_REVERB.get(dist, "dry")),
                             reason=f"{ev['class']} on {ev['basis']} ({dist}): {why}",
                             confidence=CONFIDENCE.get(basis, CONFIDENCE.get(ev.get("audio_basis"), 0.7)),
                             licence=_licence(item), loop=is_loop, cls=ev["class"], distance=dist, offset=lead,
                             event=ev))
            n_ev += 1
    # music: one row per run of the same mood, crossfades at each change
    runs = []
    for cue in plan.get("music", []):
        if runs and runs[-1]["mood"] == cue["mood"] and abs(runs[-1]["end_s"] - cue["start_s"]) < 1e-3:
            runs[-1]["end_s"] = cue["end_s"]
            runs[-1]["segments"].append(cue["segment_id"])
        else:
            runs.append({"mood": cue["mood"], "start_s": cue["start_s"], "end_s": cue["end_s"],
                         "segments": [cue["segment_id"]], "reason": cue.get("reason", "")})
    used: set[str] = set()
    for k, run in enumerate(runs):
        iid, why = pick_music(run["mood"], plan.get("era", ""), sources, items, used)
        if iid is None and allow_placeholder:
            iid, why = "placeholder:music_bed", "placeholder (preview only)"
        if iid is None:
            missing.append({"class": "music_bed", "why": why, "segments": run["segments"]})
            continue
        used.add(iid)
        prev_joined = k > 0 and abs(runs[k - 1]["end_s"] - run["start_s"]) < 1e-3
        next_joined = k + 1 < len(runs) and abs(runs[k + 1]["start_s"] - run["end_s"]) < 1e-3
        a = run["start_s"] - (MUSIC_XFADE_S / 2 if prev_joined else 0.0)
        b = run["end_s"] + (MUSIC_XFADE_S / 2 if next_joined else 0.0)
        rows.append(_row(f"MUS_{'_'.join(run['segments'])}", scene_id=run["segments"][0], shot_id=None, asset_id=iid,
                         start=max(0.0, a), end=min(dur_ep, b), layer="music", visual_event=f"segments {run['segments']}",
                         sync=run["start_s"], gain=LEVELS["music"],
                         fade_in=MUSIC_XFADE_S if prev_joined else MUSIC_FADE_S,
                         fade_out=MUSIC_XFADE_S if next_joined else MUSIC_FADE_S,
                         reason=f"{run['reason']}; {why}", confidence=CONFIDENCE["music"],
                         licence=_licence(items.get(iid)), loop=True, cls="music_bed"))
    # designed transitions: a riser into a segment where the story turns tense or violent
    seg_first = {}
    for s in plan["shots"]:
        seg_first.setdefault(s.get("segment_id"), s)
    moods = plan.get("segment_moods") or {}
    segs = list(seg_first)
    for prev, nxt in zip(segs, segs[1:]):
        m0, m1 = (moods.get(prev) or {}).get("mood"), (moods.get(nxt) or {}).get("mood")
        cut = seg_first[nxt]["start_s"]
        rise = MOOD_INTENSITY.get(m1 or "", 2) - MOOD_INTENSITY.get(m0 or "", 2)
        if m1 in TENSE_MOODS and (m0 not in TENSE_MOODS or rise >= 2) and cut >= RISER_S and "riser" in sources:
            iid, why = pk.pick("riser", "one_shot")
            if iid is None:
                missing.append({"class": "riser", "why": why, "at_s": cut})
                continue
            item = items.get(iid)
            length = min(RISER_S, _seconds(item, root) if item else RISER_S)
            off = max(0.0, (_seconds(item, root) if item else length) - length)
            rows.append(_row(f"TR_{prev}_{nxt}", scene_id=nxt, shot_id=seg_first[nxt]["shot_id"], asset_id=iid,
                             start=cut - length, end=cut, layer="transition", visual_event=f"cut into {nxt} ({m1})",
                             sync=cut, gain=LEVELS["transition"], fade_in=0.5, fade_out=0.05,
                             reason=f"designed: {m0} -> {m1} at the cut; {why}", confidence=CONFIDENCE["designed"],
                             licence=_licence(item), offset=off, cls="riser"))
    rows.sort(key=lambda r: (r["start_s"], PRIORITY[r["layer"]], r["cue_id"]))
    credits = sorted({r["license_status"]["attribution_text"] for r in rows
                      if r["license_status"].get("attribution_required") and r["license_status"].get("attribution_text")})
    return {"schema": SCHEMA, "episode_id": plan.get("episode_id"), "era": plan.get("era"), "duration_s": dur_ep,
            "rows": rows, "missing": missing, "credits": credits,
            "takes": {c: len(v.get("ids") or []) for c, v in sorted(sources.items())},
            "shots": [{"shot_id": s["shot_id"], "start_s": s["start_s"], "dur_s": s["dur_s"],
                       "state": (s.get("design") or {}).get("state"),
                       "silence_reason": (s.get("design") or {}).get("silence_reason")} for s in plan["shots"]]}


def _covered(rows: list[dict], a: float, b: float, step: float = 0.05) -> list[tuple[float, float]]:
    """Stretches of [a, b) no narration, ambience or music row covers (undeclared silence candidates)."""
    spans = [(r["start_s"], r["end_s"]) for r in rows if r["layer"] in ("narration", "ambience", "music")]
    holes, t, start = [], a, None
    while t < b - 1e-9:
        on = any(x <= t < y for x, y in spans)
        if not on and start is None:
            start = t
        if on and start is not None:
            holes.append((start, t))
            start = None
        t += step
    if start is not None:
        holes.append((start, b))
    return holes


def validate(sheet: dict, plan: dict, library_root: Path | None = None, onsets: dict | None = None) -> dict:
    """The gate rows of a sheet; ``onsets`` (``{cue_id: measured onset s}``, from the rendered SFX stem) makes BP-54 a measurement
    of the sound, not of the sheet."""
    rows = sheet["rows"]
    items = _items(Path(library_root)) if library_root else {}
    out = []
    bad_state = [s["shot_id"] for s in sheet["shots"] if s["state"] not in SP.COVERAGE_STATES]
    no_reason = [s["shot_id"] for s in sheet["shots"] if s["state"] == "INTENTIONAL_SILENCE" and not s.get("silence_reason")]
    out.append(G.row("coverage_state", not bad_state and not no_reason,
                     f"every shot names one of the seven states; intentional silence has its reason "
                     f"(no state: {bad_state}; silence without reason: {no_reason})", len(bad_state) + len(no_reason)))
    holes = []
    for s in sheet["shots"]:
        if s["state"] == "INTENTIONAL_SILENCE":
            continue
        for a, b in _covered(rows, s["start_s"], s["start_s"] + s["dur_s"]):
            if b - a > SILENCE_HOLE_S:
                holes.append({"shot_id": s["shot_id"], "from_s": round(a, 2), "to_s": round(b, 2)})
    out.append(G.row("no_undeclared_silence", not holes, f"stretches with no narration, ambience or music outside a declared "
                     f"silence: {holes[:5]}", len(holes)))
    amb_missing = []
    for s in sheet["shots"]:
        if s["state"] == "INTENTIONAL_SILENCE":
            continue
        a, b = s["start_s"], s["start_s"] + s["dur_s"]
        cov = sum(max(0.0, min(b, r["end_s"]) - max(a, r["start_s"])) for r in rows
                  if r["layer"] == "ambience" and not str(r["asset_id"]).startswith("room_tone"))
        if cov < 0.9 * (b - a):
            amb_missing.append(s["shot_id"])
    out.append(G.row("ambience_present", not amb_missing, f"every non-silent shot sits in a real ambience (not only room "
                     f"tone): missing in {amb_missing}", len(amb_missing)))
    unknown = [r["cue_id"] for r in rows if items and not str(r["asset_id"]).startswith(("narration:", "room_tone:",
                                                                                          "placeholder:"))
               and r["asset_id"] not in items]
    out.append(G.row("assets_exist", not sheet["missing"] and not unknown,
                     f"every row names a library take: unknown {unknown[:5]}, missing classes "
                     f"{[m['class'] for m in sheet['missing']][:8]}", len(unknown) + len(sheet["missing"])))
    lic_bad = [r["cue_id"] for r in rows if r["layer"] == "music" and not str(r["asset_id"]).startswith("placeholder:")
               and r["license_status"].get("production") != "verified"]
    credit_bad = [r["cue_id"] for r in rows if r["license_status"].get("attribution_required")
                  and not r["license_status"].get("attribution_text")]
    out.append(G.row("music_licence", not lic_bad and not credit_bad,
                     f"music is licence-checked (the creator, 2026-11-13: licence matters for the music only): unverified "
                     f"{lic_bad}, credit line missing {credit_bad}; credits: {len(sheet.get('credits', []))}",
                     len(lic_bad) + len(credit_bad)))
    rng = []
    dur = sheet["duration_s"]
    for r in rows:
        why = []
        if r["start_s"] < 0 or r["end_s"] <= r["start_s"] or r["end_s"] > dur + 1e-3:
            why.append("time")
        if r["layer"] != "narration" and not (-70.0 <= r["gain_db"] <= -6.0):
            why.append("gain")
        if not -1.0 <= r["pan"] <= 1.0:
            why.append("pan")
        if r["fade_in_s"] + r["fade_out_s"] > r["duration_s"] + 1e-3:
            why.append("fades")
        if not 0.85 <= r["pitch"] <= 1.15:
            why.append("pitch")
        if r["layer"] not in LAYERS:
            why.append("layer")
        if why:
            rng.append(f"{r['cue_id']}:{'/'.join(why)}")
    out.append(G.row("values_in_range", not rng, f"time, gain (-70..-6 dB), pan, fades, pitch (0.85..1.15), layer: {rng[:5]}",
                     len(rng)))
    shots = {s["shot_id"]: s for s in plan["shots"]}
    outside = []
    for r in rows:
        if r["layer"] in ("foley", "spot") and r["shot_id"] in shots:
            s = shots[r["shot_id"]]
            if not s["start_s"] - 1e-3 <= r["start_s"] <= s["start_s"] + s["dur_s"] + 1e-3:
                outside.append(r["cue_id"])
    out.append(G.row("events_inside_their_shot", not outside, f"foley and spots start inside their shot: {outside[:5]}",
                     len(outside)))
    out += sync_rows(rows, plan, onsets)
    out += overlap_rows(rows)
    out += av_rows(rows, plan, sheet)
    fx = [r for r in rows if r["layer"] in ("foley", "spot", "transition")]
    rep, thin = [], set()
    takes = sheet.get("takes", {})
    last: dict[str, tuple[str, float]] = {}
    for r in sorted(fx, key=lambda x: x["start_s"]):
        prev = last.get(r["class"])
        if prev and prev[0] == r["asset_id"] and r["start_s"] - prev[1] < 10.0 and not str(r["asset_id"]).startswith("placeholder"):
            (rep.append(r["cue_id"]) if takes.get(r["class"], 1) > 1 else thin.add(r["class"]))
        last[r["class"]] = (r["asset_id"], r["start_s"])
    out.append(G.row("variation", not rep, f"BP-57: a class with several takes never plays the same take twice within 10 s: "
                     f"{rep[:5]}", len(rep), level=SR_RULES.level("BP-57")))
    out.append(G.row("variants_available", not thin, f"BP-57 asks {VARIANTS_MIN} takes per repeated class; repeated with one "
                     f"take (pitch and gain jitter only): {sorted(thin)}", len(thin), level="REVIEW"))
    return {"rows": out, "verdict": G.verdict(out)}

FRAME_MS = 1000.0 / 24.0


def sync_rows(rows: list[dict], plan: dict, onsets: dict | None) -> list[dict]:
    """BP-54 in its three bands (the registry's ``frames``, ``early_max_ms``, ``late_max_ms``): the sound's onset against its
    event's frame. Within ``frames`` frame(s) PASS; earlier than -early or later than +late FAIL; between them REVIEW (the
    registry asks one frame and FAILs only outside the ms window). Measured onsets when given, else the sheet's start plus the
    take's skipped lead (the planned onset, said so)."""
    fps = float(plan.get("fps") or 24)
    one = float(SR_RULES.T("BP-54", "frames")) * 1000.0 / fps
    shots = {s["shot_id"]: s for s in plan["shots"]}
    fail, review, measured = [], [], 0
    for r in rows:
        if r["layer"] not in ("foley", "spot", "transition") or not r.get("event_id") or r["shot_id"] not in shots:
            continue
        s = shots[r["shot_id"]]
        ev = next((e for e in s["events"] if e.get("event_id") == r["event_id"]), None)
        if ev is None:
            continue
        want = s["start_s"] + ev["at_frame"] / fps
        got = (onsets or {}).get(r["cue_id"])
        measured += got is not None
        got = r["start_s"] if got is None else got
        d = (got - want) * 1000.0
        if d < -SYNC_EARLY_MS or d > SYNC_LATE_MS:
            fail.append(f"{r['event_id']}:{d:+.0f}ms")
        elif abs(d) > one + 1e-6:
            review.append(f"{r['event_id']}:{d:+.0f}ms")
    basis = f"measured on the SFX stem ({measured} onsets)" if onsets else "planned (no stem measured)"
    return [G.row("events_on_sync", not fail, f"BP-54 onset against the event frame, {basis}: outside -{SYNC_EARLY_MS:g}/"
                  f"+{SYNC_LATE_MS:g} ms {fail[:6]}", len(fail), level=SR_RULES.level("BP-54")),
            G.row("events_on_the_frame", not review, f"BP-54 one-frame target ({one:.0f} ms): off by more than a frame but "
                  f"inside the window {review[:6]}", len(review), level=G.REVIEW)]


def overlap_rows(rows: list[dict]) -> list[dict]:
    """BP-56 from the rows' intervals (a sweep over every start and end): at most ``SAME_CLASS_MAX`` effects of one class at
    once, at most ``LAYERS_MAX`` layers in all, where the voice, the music and the bed (every ambience row, room tone left out)
    count once each and every effect row counts itself."""
    marks = sorted({r["start_s"] for r in rows} | {r["end_s"] for r in rows})
    crowd, same = [], []
    for a, b in zip(marks, marks[1:]):
        t = (a + b) / 2
        live = [r for r in rows if r["start_s"] <= t < r["end_s"]]
        fx = [r for r in live if r["layer"] in ("foley", "spot", "transition")]
        layers = len(fx) + sum(1 for lay in ("narration", "music") if any(r["layer"] == lay for r in live)) \
            + (1 if any(r["layer"] == "ambience" and not str(r["asset_id"]).startswith("room_tone") for r in live) else 0)
        if layers > LAYERS_MAX:
            crowd.append(f"{t:.2f}s:{layers}")
        by: dict[str, int] = {}
        for r in fx:
            by[r["class"]] = by.get(r["class"], 0) + 1
        over = [c for c, n in by.items() if n > SAME_CLASS_MAX]
        if over:
            same.append(f"{t:.2f}s:{over[0]}")
    return [G.row("overlap", not crowd and not same, f"BP-56 from the intervals: at most {LAYERS_MAX} layers (voice, music and "
                  f"bed once each) and {SAME_CLASS_MAX} of one class at once: crowded {crowd[:5]}, same class {same[:5]}",
                  len(crowd) + len(same), level=SR_RULES.level("BP-56"))]


EMPHASIS_CLASSES = {"map_pin_set": "thud", "ov_thud": "thud", "data_confirm": "chime", "ov_glow": "chime",
                    "data_rise_texture": "rise", "riser": "rise"}


def _sev(rule_id: str) -> str:
    """The severity the registry gives the rule (BP-55 and BP-56 are REVIEW rules), never above what its status allows."""
    return SR_RULES.level(rule_id, SR_RULES.rule(rule_id).get("severity") or G.FAIL)


def av_rows(rows: list[dict], plan: dict, sheet: dict) -> list[dict]:
    """BP-55 (purpose and share), BP-81 (cue density, bursts, one emphasis cue a line) and the events left for a person."""
    out = []
    beats = [d for s in plan["shots"] for d in s.get("visual_events", []) if not str(d.get("op", "")).count(":")]
    effects = [d for d in beats if d["decision"] == "sfx"]
    share = len(effects) / len(beats) if beats else None
    lim = float(SR_RULES.T("BP-55", "beats_with_sfx_share_max"))
    no_purpose = [r["event_id"] for r in rows if r.get("decision") in ("sfx", "ui_cue") and r.get("purpose") not in
                  SR_RULES.T("BP-55", "purposes")]
    silent = sum(1 for d in beats if d["decision"] == "silent_by_design")
    if beats:   # a sheet without visible events has no beats to share out (the row is left out, not faked)
        out.append(G.row("purpose_and_share", share <= lim and not no_purpose,
                         f"BP-55: {len(effects)} of {len(beats)} visual beats carry an audible non-cue effect ({share:.0%}, max "
                         f"{lim:.0%}; {silent} silent by design count as beats, never as missing); without a purpose "
                         f"{no_purpose[:5]}", round(share, 3), level=_sev("BP-55")))
    cues = sorted(r["start_s"] for r in rows if r.get("decision") == "ui_cue")
    dur = float(sheet.get("duration_s") or 0.0)
    per_min = len(cues) / (dur / 60.0) if dur > 0 else 0.0
    burst_n, win = int(SR_RULES.T("BP-81", "burst_max")), float(SR_RULES.T("BP-81", "burst_window_s"))
    burst = max((sum(1 for t in cues if a <= t < a + win) for a in cues), default=0)
    measured = dur >= float(SR_RULES.T("BP-81", "measured_from_s"))
    if measured:   # BP-81 counts a minute's density only on a read of measured_from_s or more
        out.append(G.row("cue_density", per_min <= float(SR_RULES.T("BP-81", "per_min_fail")),
                         f"BP-81: {len(cues)} cue(s), {per_min:.1f} a minute (REVIEW over "
                         f"{SR_RULES.T('BP-81', 'per_min_review')}, FAIL over {SR_RULES.T('BP-81', 'per_min_fail')})",
                         round(per_min, 2), level=SR_RULES.level("BP-81")))
    out.append(G.row("cue_rate_review", per_min <= float(SR_RULES.T("BP-81", "per_min_review")) and burst <= burst_n,
                     f"BP-81: {per_min:.1f} cues a minute, worst {win:g} s holds {burst} (REVIEW over {burst_n})",
                     {"per_min": round(per_min, 2), "burst": burst}, level=G.REVIEW))
    heavy = []
    for s in plan["shots"]:
        a, b = s["start_s"], s["start_s"] + s["dur_s"]
        n = sum(1 for r in rows if a <= r["start_s"] < b and EMPHASIS_CLASSES.get(r.get("class") or "") and r.get("decision"))
        if n > int(SR_RULES.T("BP-81", "emphasis_per_line_max")) * max(1, len(s.get("audio_line_ids") or [])):
            heavy.append(f"{s['shot_id']}:{n}")
    out.append(G.row("one_emphasis_a_line", not heavy, f"BP-81: at most {SR_RULES.T('BP-81', 'emphasis_per_line_max')} "
                     f"emphasis cue (thud, chime, rise) a line: {heavy[:5]}", len(heavy), level=SR_RULES.level("BP-81")))
    review = [d["event_id"] for s in plan["shots"] for d in s.get("visual_events", []) if d["decision"] == "review_required"]
    review += [m["event_id"] for m in sheet.get("missing", []) if m.get("event_id")]
    out.append(G.row("review_required_events", not review, f"{len(review)} event(s) a person decides (review_required or no "
                     f"real take for their class): {review[:8]}", review[:30], level=G.REVIEW))
    return out



def coverage_report(sheet: dict, plan: dict) -> dict:
    per = []
    for s in plan["shots"]:
        a, b = s["start_s"], s["start_s"] + s["dur_s"]
        mine = [r for r in sheet["rows"] if r["end_s"] > a + 0.01 and r["start_s"] < b - 0.01]
        d = s.get("design") or {}
        per.append({"shot_id": s["shot_id"], "segment_id": s.get("segment_id"), "start_s": a, "dur_s": s["dur_s"],
                    "route": s.get("route"), "mood": s.get("mood"), "state": d.get("state"),
                    "layers": {k: v["active"] for k, v in (d.get("layers") or {}).items()},
                    "cues": {lay: sorted({r["asset_id"] for r in mine if r["layer"] == lay}) for lay in LAYERS},
                    "heard_not_seen": d.get("heard_not_seen", []), "silence_reason": d.get("silence_reason")})
    states: dict[str, int] = {}
    for p in per:
        states[p["state"]] = states.get(p["state"], 0) + 1
    seconds = {lay: round(sum(r["duration_s"] for r in sheet["rows"] if r["layer"] == lay), 2) for lay in LAYERS}
    return {"schema": "sound_coverage/1", "episode_id": plan.get("episode_id"), "states": states,
            "layer_seconds": seconds, "missing": sheet["missing"], "credits": sheet.get("credits", []), "shots": per}


def coverage_markdown(cov: dict, gate: dict) -> str:
    lines = [f"# Sound coverage: {cov['episode_id']}", "", f"Verdict: **{gate['verdict']['status']}**", "",
             "| gate | status | detail |", "|---|---|---|"]
    lines += [f"| {r['gate']} | {r['status']} | {r['detail'][:160]} |" for r in gate["rows"]]
    lines += ["", "States: " + ", ".join(f"{k} {v}" for k, v in sorted(cov["states"].items())), "",
              "| shot | mood | state | ambience | foley | spot | music | transition | heard, not seen |",
              "|---|---|---|---|---|---|---|---|---|"]
    for p in cov["shots"]:
        c = p["cues"]
        lines.append(f"| {p['shot_id']} | {p['mood']} | {p['state']} | {', '.join(c['ambience'])} | {', '.join(c['foley'])} | "
                     f"{', '.join(c['spot'])} | {', '.join(c['music'])} | {', '.join(c['transition'])} | "
                     f"{', '.join(p['heard_not_seen'])} |")
    if cov["credits"]:
        lines += ["", "## Credits (description)", ""] + [f"- {c}" for c in cov["credits"]]
    return "\n".join(lines) + "\n"


def write(sheet: dict, plan: dict, out_dir: Path, library_root: Path | None = None, onsets: dict | None = None) -> dict:
    out_dir = Path(out_dir)
    gate = validate(sheet, plan, library_root, onsets)
    cov = coverage_report(sheet, plan)
    write_json_atomic(out_dir / "cue_sheet.json", sheet)
    write_json_atomic(out_dir / "sound_coverage.json", dict(cov, gate=gate))
    write_text_atomic(out_dir / "sound_coverage.md", coverage_markdown(cov, gate))
    return gate


def require(gate: dict) -> None:
    if gate["verdict"]["status"] == G.FAIL:
        raise ContractError("cue sheet FAIL: " + ", ".join(gate["verdict"].get("failed", [])))
