"""RETIRED by D-80 (2026-10-26): the night-run route of the wldnk era; kept as history, never run. Checks and plans for an AI-video test (shots.json + timeline.json), shared by the pod scripts and the montage.

shots.json: {"title", "trigger", "style_suffix", "characters": {id: description}, "plates": {id: description},
             "shots": [{"id", "chars": [ids], "plate": id|null, "first", "last", "motion"}]}
timeline.json: {"intro_end", "end", "segments": [{"id", "t0", "t1"}]}  (seconds on the narration's clock)

No permanent heroes (the creator, 2026-10-22): characters belong to one video's shots.json, never to a LoRA."""
import math

MAX_REFS = 3          # reference sheets per keyframe (klein multi-reference; the plate makes the fourth)
TOL = 0.02            # seconds of slack between neighbouring timeline segments


def check_shots(data):
    """Problems in a shots.json (empty list = usable)."""
    bad = []
    trig = (data.get("trigger") or "").strip()
    if not trig:
        bad.append("no trigger word: the style LoRA would not be called")
    chars, plates = data.get("characters") or {}, data.get("plates") or {}
    seen = set()
    for s in data.get("shots") or []:
        sid = s.get("id")
        if not sid or sid in seen:
            bad.append(f"shot id missing or repeated: {sid!r}")
        seen.add(sid)
        for k in ("first", "last", "motion"):
            if not (s.get(k) or "").strip():
                bad.append(f"{sid}: empty {k} prompt")
        for c in s.get("chars") or []:
            if c not in chars:
                bad.append(f"{sid}: unknown character {c!r}")
        if s.get("plate") is not None and s["plate"] not in plates:
            bad.append(f"{sid}: unknown plate {s['plate']!r}")
    if not seen:
        bad.append("no shots")
    return bad


def check_timeline(tl, data):
    """Problems in a timeline against its shots: contiguous segments from the opening to the end, one shot each."""
    bad = []
    segs = tl.get("segments") or []
    if not segs:
        return ["no segments"]
    ids = {s.get("id") for s in data.get("shots") or []}
    t = tl.get("intro_end", 0.0)
    for g in segs:
        if g["id"] not in ids:
            bad.append(f"{g['id']}: no shot for this segment")
        if abs(g["t0"] - t) > TOL:
            bad.append(f"{g['id']}: starts at {g['t0']} but the previous part ends at {t}")
        if g["t1"] <= g["t0"]:
            bad.append(f"{g['id']}: empty or negative length")
        t = g["t1"]
    if abs(t - tl.get("end", t)) > TOL:
        bad.append(f"segments end at {t} but the narration ends at {tl.get('end')}")
    return bad


def keyframe_refs(shot, sheets):
    """Reference images for a shot's first keyframe: up to MAX_REFS character sheets, then the plate's picture."""
    refs = [sheets[c] for c in shot.get("chars") or [] if c in sheets][:MAX_REFS]
    if shot.get("plate") and shot["plate"] in sheets:
        refs.append(sheets[shot["plate"]])
    return refs


def prompt(data, text):
    """A keyframe prompt: trigger first (as the LoRA was captioned), then the shot, then the house style."""
    return ", ".join(p for p in (data.get("trigger"), text, data.get("style_suffix")) if p)


def montage_plan(tl, clip_seconds, have_first):
    """What fills each segment. clip_seconds: {id: length of its clip} (missing = no clip); have_first: ids with a
    first keyframe. A segment longer than its clip holds the first keyframe first (the clip starts on that frame)."""
    plan = []
    for g in tl["segments"]:
        sid, d = g["id"], round(g["t1"] - g["t0"], 3)
        L = clip_seconds.get(sid)
        if L:
            hold = round(d - L, 3) if d > L + 0.05 and sid in have_first else 0.0
            plan.append({"id": sid, "seconds": d, "how": "hold+clip" if hold else "clip", "hold": hold})
        elif sid in have_first:
            plan.append({"id": sid, "seconds": d, "how": "still", "hold": d})
        else:
            plan.append({"id": sid, "seconds": d, "how": "MISSING", "hold": 0.0})
    return plan


def affordable_minutes(max_usd, price_per_hour):
    """Minutes a pod may run before its money ceiling stops it."""
    return math.floor(max_usd / price_per_hour * 60) if price_per_hour > 0 else 0


def schedule_fits(stage_ends_min, max_usd, price_per_hour, upload_margin_min=10):
    """True when every stage deadline (minutes after the pod starts) lands before the money ceiling, with time to upload."""
    limit = affordable_minutes(max_usd, price_per_hour) - upload_margin_min
    return all(m <= limit for m in stage_ends_min)
