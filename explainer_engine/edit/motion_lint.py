"""Motion and visual-change rules MO-01..MO-06 (docs/STORY_ENGINE.md, D-48) on a timed production script.

Episode 1 (measured 2026-10-19 on its production script): 217 shots, a picture change every 5.0 s on average, but every
change the same kind (161 pushes, 54 pans, zoom at most 1.08), 89 of the changes a reframe of the same picture, no
transition but the cut, 8 bubbles and 11 data visuals in 18 minutes. The rate was fine; the sameness read as a
slideshow. These rules measure *events* (anything new the eye gets: a new picture, a reframe, an accent, a bubble, a
data visual, a card) and their *variety*, not only the cut rate. All findings are REVIEW: the creator judges the cut.

    findings = check(timed)      # list of {rule, severity, where, detail}
    report = measure(timed)      # numbers for the review bundle
"""

from __future__ import annotations

from collections import Counter

MAX_GAP = 5.0            # MO-01: seconds without any new visual event
WINDOW, MIN_KINDS = 60.0, 3   # MO-02: kinds of event inside every minute
MAX_PLAIN_RUN = 4        # MO-03: consecutive shots that are only a camera move
ENTRY_MIN_GAP = 45.0     # MO-04: seconds between two whips or flashes
TEXT_MIN_GAP = 12.0      # MO-05: seconds between two pop/slam words
MIN_ALIVE = 0.5          # MO-06: share of shots with something moving besides the camera
ENTRY = {"whip_in", "flash_in"}
TEXT = {"pop_text", "slam_text"}


def events(timed: dict) -> list[tuple[float, str]]:
    """(time, kind) of every visual event, sorted."""
    ev: list[tuple[float, str]] = []
    prev = None
    for s in timed["shots"]:
        ev.append((s["start"], "reframe" if s["picture"] == prev else "picture"))
        prev = s["picture"]
        for a in s.get("accents", []):
            if a["kind"] != "wobble":
                ev.append((a["start"], a["kind"]))
        for b in s.get("bubbles", []):
            ev.append((b["start"], "bubble"))
    for g in timed.get("visuals", []):
        ev.append((g["start"], "visual"))
    for c in timed.get("cards", []):
        ev.append((c["start"], "card"))
    return sorted(ev)


def _alive(s: dict) -> bool:
    return bool(s.get("accents") or s.get("bubbles") or s.get("speaker"))


def measure(timed: dict) -> dict:
    ev = events(timed)
    times = [t for t, _ in ev] + [timed["duration"]]
    gaps = [b - a for a, b in zip(times, times[1:])]
    shots = timed["shots"]
    return {"events": len(ev), "per_minute": round(len(ev) / max(timed["duration"], 1e-6) * 60, 1),
            "mean_gap": round(sum(gaps) / max(1, len(gaps)), 2), "max_gap": round(max(gaps, default=0.0), 2),
            "kinds": dict(Counter(k for _, k in ev)),
            "alive_share": round(sum(_alive(s) for s in shots) / max(1, len(shots)), 2),
            "transitions": dict(Counter(s.get("transition", "cut") for s in shots))}


def check(timed: dict) -> list[dict]:
    out: list[dict] = []

    def add(rule, where, detail):
        out.append({"rule": rule, "severity": "REVIEW", "where": where, "detail": detail})

    ev = events(timed)
    dur = timed["duration"]
    times = [0.0] + [t for t, _ in ev] + [dur]
    for a, b in zip(times, times[1:]):
        if b - a > MAX_GAP:
            add("MO-01", f"{a:.1f}s", f"{b - a:.1f} s with nothing new on screen: add an accent, a bubble, a reframe or a visual "
                f"(at most {MAX_GAP:.0f} s)")
    t = 0.0
    while t + WINDOW <= dur + 1e-6:
        kinds = {k for x, k in ev if t <= x < t + WINDOW}
        if len(kinds) < MIN_KINDS:
            add("MO-02", f"{t:.0f}-{t + WINDOW:.0f}s", f"only {len(kinds)} kind(s) of visual event ({', '.join(sorted(kinds)) or 'none'}); "
                f"a minute needs at least {MIN_KINDS} (pictures, reframes, accents, bubbles, visuals)")
        t += WINDOW
    run: list[str] = []
    for s in timed["shots"] + [{"id": "<end>", "accents": [{"kind": "end"}]}]:
        plain = not _alive(s) and not any(g["start_frame"] < s.get("end_frame", 0) and g["end_frame"] > s.get("start_frame", 0)
                                          for g in timed.get("visuals", []))
        if plain:
            run.append(s["id"])
            continue
        if len(run) > MAX_PLAIN_RUN:
            add("MO-03", run[0], f"{len(run)} shots in a row are only a camera move ({run[0]}..{run[-1]}): a slideshow run, "
                f"at most {MAX_PLAIN_RUN}")
        run = []
    last_entry = last_text = None
    seg_first = {}
    for s in timed["shots"]:
        seg_first.setdefault(s["segment"], s["id"])
    for s in timed["shots"]:
        for a in s.get("accents", []):
            if a["kind"] in ENTRY:
                if seg_first[s["segment"]] != s["id"]:
                    add("MO-04", s["id"], f"{a['kind']} inside a segment: a whip or flash marks a story turn, so it opens a segment")
                if last_entry is not None and a["start"] - last_entry < ENTRY_MIN_GAP:
                    add("MO-04", s["id"], f"{a['kind']} {a['start'] - last_entry:.0f} s after the last one (at least {ENTRY_MIN_GAP:.0f} s)")
                last_entry = a["start"]
            if a["kind"] in TEXT:
                if last_text is not None and a["start"] - last_text < TEXT_MIN_GAP:
                    add("MO-05", s["id"], f"words pop {a['start'] - last_text:.0f} s after the last ones (at least {TEXT_MIN_GAP:.0f} s): "
                        "on-screen words are for the one word that matters")
                if len(a.get("text", "").split()) > 4:
                    add("MO-05", s["id"], "more than four words on screen")
                last_text = a["start"]
    m = measure(timed)
    if timed["shots"] and m["alive_share"] < MIN_ALIVE:
        add("MO-06", "video", f"only {m['alive_share']:.0%} of shots have motion besides the camera (accent or bubble); "
            f"at least {MIN_ALIVE:.0%}")
    return out
