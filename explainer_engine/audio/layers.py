"""Sound-layer rules on a timed production script: AL-01..AL-04 (docs/STORY_ENGINE.md, D-48) with their numbers read from the
sourced-rules registry, and the BP audio rules that have no older id (BP-54 sync window, BP-55 beat share, BP-57 repeats,
BP-62 music spotting). Enough sound that the picture's motion is heard, never so much that the layers turn into noise under
the voice.

Episode 1 had 22 effects in 18 minutes (1.2 a minute) under one bed and up to two music tracks; the creator heard the
music and the tick fighting the voice (ED-03). The rules count what plays at once and what is missing:

* AL-01 (BP-56) at most ``MAX_SFX_AT_ONCE`` effects overlap, and voice + music + bed + effects stay at most ``MAX_LAYERS``;
* AL-02 sound events a minute, effects and beat cues together, inside ``SFX_PER_MIN`` (a hypothesis: no source
  gives a rate; REVIEW only, BP-55; the cues count because the ear hears them, D-58);
* AL-03 (BP-54) a drawn accent that moves the picture hard (whip, flash, slam, shake, punch) has an effect that lands with it:
  within ``SYNC_EARLY`` before or ``SYNC_LATE`` after (early is worse than late); no effect near it is REVIEW, an effect
  outside the window is FAIL;
* AL-04 (BP-52) effects and beds stay under the voice before the mix's ducking (``MAX_SFX_DB`` / ``MAX_BED_DB``; the bed cap
  is the sourced "ambience at least 15 LU under the voice");
* BP-55 at most one visual beat in two carries an audible non-cue effect (mickey-mousing is redundancy);
* BP-57 the same sound never plays twice in a row within its type;
* BP-62 music starts and stops on a shot or segment boundary, a long video keeps a no-music stretch, a sting stays short.

Severities come from the registry (D-59): a REVIEW rule never FAILs here.
"""

from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

MAX_SFX_AT_ONCE = int(SR.T("BP-56", "same_class_max"))
MAX_LAYERS = int(SR.T("BP-56", "layers_max"))  # voice + music + bed + effects, all counted
SFX_PER_MIN = (4.0, 20.0)  # AL-02: a hypothesis band (BP-55 keeps it REVIEW; no source names a rate)
HARD = {"whip_in", "flash_in", "slam_text", "shake", "punch"}
SYNC_EARLY = SR.T("BP-54", "early_max_ms") / 1000  # seconds a sound may lead its picture event
SYNC_LATE = SR.T("BP-54", "late_max_ms") / 1000  # seconds it may trail it
NEAR = 0.5  # seconds: beyond this there is simply no effect for the accent (AL-03), not a mistimed one (BP-54)
MAX_SFX_DB = -8.0  # house pre-mix cap for an effect
MAX_BED_DB = -float(SR.T("BP-52", "bed_under_lu"))  # BP-52: the ambience bed at least 15 LU under the voice
BOUNDARY_TOL = 0.05  # seconds: a music edge within this of a cut counts as on it (one frame and a half at 30 fps)
LONG_FORM_S = 120.0  # below this a video is a Short for BP-62's no-music stretch (EBU's short-form line, BP-61)


def _sev(rule: str) -> str:
    return SR.rule(rule).get("severity", "REVIEW") if rule.startswith("BP-") else "REVIEW"


def _active(items: list[dict], t: float) -> int:
    return sum(1 for x in items if x["start"] <= t < x["end"])


def sync_offset(event_t: float, starts: list[float]) -> float | None:
    """The nearest sound start relative to a picture event (negative = early), or None when nothing is within NEAR."""
    near = [x - event_t for x in starts if abs(x - event_t) <= NEAR]
    return min(near, key=abs) if near else None


def in_sync(offset: float) -> bool:
    return -SYNC_EARLY <= offset <= SYNC_LATE


def check(timed: dict) -> list[dict]:
    out: list[dict] = []

    def add(rule, where, detail, severity=None):
        out.append({"rule": rule, "severity": severity or _sev(rule), "where": where, "detail": detail})

    au = timed.get("audio", {})
    sfx, beds, music, cues = au.get("sfx", []), au.get("beds", []), au.get("music", []), au.get("cues", [])
    dur = max(timed.get("duration", 0.0), 1e-6)
    flagged = 0.0
    for e in sorted(sfx, key=lambda x: x["start"]):
        t = e["start"] + 1e-3
        n_sfx = _active(sfx, t)
        layers = 1 + min(1, _active(music, t)) + min(1, _active(beds, t)) + n_sfx
        if (n_sfx > MAX_SFX_AT_ONCE or layers > MAX_LAYERS) and t > flagged:
            add("AL-01", f"{e['start']:.1f}s", f"{n_sfx} effects and {layers} layers at once: the voice drowns in noise "
                f"(at most {MAX_SFX_AT_ONCE} effects, {MAX_LAYERS} layers, BP-56)", _sev("BP-56"))
            flagged = e["start"] + 1.0
        if e.get("gain_db", -18) > MAX_SFX_DB:
            add("AL-04", e["sound"], f"effect at {e['gain_db']} dB: above {MAX_SFX_DB} dB it competes with the voice")
    # AL-02 counts everything the ear hears as an event: effects AND beat cues. The old count left the cues out, so
    # the density rule never fired on the layer it existed for (Syndicate Wars: 33 cues/min, AL-02 silent).
    n_events = len(sfx) + len(au.get("cues", []))
    per_min = n_events / dur * 60
    if dur >= 60 and not SFX_PER_MIN[0] <= per_min <= SFX_PER_MIN[1]:
        add("AL-02", "video", f"{per_min:.1f} sound events a minute, effects and cues together "
            f"(keep {SFX_PER_MIN[0]:.0f}-{SFX_PER_MIN[1]:.0f}, a hypothesis): "
            + ("the motion is silent" if per_min < SFX_PER_MIN[0] else "clutter"), "REVIEW")
    starts = [e["start"] for e in sfx] + [c["start"] for c in cues]  # a beat cue (VB-08) is heard too
    for s in timed.get("shots", []):
        for a in s.get("accents", []):
            if a["kind"] not in HARD:
                continue
            off = sync_offset(a["start"], starts)
            if off is None:
                add("AL-03", s["id"], f"{a['kind']} at {a['start']:.1f}s has no effect within {NEAR} s: a move the eye sees, "
                    "the ear misses", "REVIEW")
            elif not in_sync(off):
                add("AL-03", s["id"], f"{a['kind']} at {a['start']:.1f}s: its sound is {abs(off) * 1000:.0f} ms "
                    f"{'early' if off < 0 else 'late'} (BP-54 allows {SYNC_EARLY * 1000:.0f} ms early, {SYNC_LATE * 1000:.0f} ms "
                    "late; a miss goes late, never early)", _sev("BP-54"))
    for b in beds:
        if b.get("gain_db", MAX_BED_DB) > MAX_BED_DB:
            add("AL-04", b["sound"], f"bed at {b['gain_db']} dB: above {MAX_BED_DB:g} dB the ambience masks words (BP-52)")
    out += beat_share_findings(timed)
    out += repeat_findings(timed)
    out += music_findings(timed)
    return out


def beat_share_findings(timed: dict) -> list[dict]:
    """BP-55: the share of visual beats that carry an audible non-cue effect (a sound on every beat is mickey-mousing)."""
    beats = timed.get("visual_beats", [])
    sfx_starts = [e["start"] for e in timed.get("audio", {}).get("sfx", [])]
    if not beats or not sfx_starts:
        return []
    carrying = sum(1 for b in beats if sync_offset(b["start"], sfx_starts) is not None
                   and in_sync(sync_offset(b["start"], sfx_starts)))
    share = carrying / len(beats)
    cap = SR.T("BP-55", "beats_with_sfx_share_max")
    if share <= cap:
        return []
    return [{"rule": "BP-55", "severity": _sev("BP-55"), "where": "visual beats",
             "detail": f"{carrying} of {len(beats)} beats ({share:.0%}) carry a sound effect; at most {cap:.0%} should: a sound "
                       "that only doubles the picture is redundancy"}]


def _runs(names: list[str]) -> list[tuple[str, int]]:
    """(name, run length) for every run of 2+ identical consecutive names."""
    runs, k = [], 0
    while k < len(names):
        j = k
        while j + 1 < len(names) and names[j + 1] == names[k]:
            j += 1
        if j > k:
            runs.append((names[k], j - k + 1))
        k = j + 1
    return runs


def repeat_findings(timed: dict) -> list[dict]:
    """BP-57: the same sample never twice in a row within its type (effects by sound id; beat cues by cue id)."""
    au = timed.get("audio", {})
    out = []
    sfx = sorted(au.get("sfx", []), key=lambda x: x["start"])
    for name, n in _runs([e["sound"] for e in sfx]):
        out.append({"rule": "BP-57", "severity": _sev("BP-57"), "where": name,
                    "detail": f"effect {name!r} plays {n} times in a row: use another variant (at least "
                              f"{SR.T('BP-57', 'variants_min')}) or a deterministic pitch and gain jitter"})
    cues = sorted(au.get("cues", []), key=lambda x: x["start"])
    runs = _runs([c["sound"] for c in cues])
    if runs:
        worst = max(runs, key=lambda r: r[1])
        out.append({"rule": "BP-57", "severity": _sev("BP-57"), "where": "cues",
                    "detail": f"{len(runs)} runs of the same cue in a row (longest {worst[0]!r} x {worst[1]}); a cue counts as "
                              "an asset: vary the cue or jitter its pitch and gain"})
    return out


def boundaries(timed: dict) -> list[float]:
    """Where a music start or stop may sit (BP-62): the video's ends, every shot edge and every segment edge."""
    pts = {0.0, float(timed.get("duration", 0.0))}
    for s in timed.get("shots", []):
        pts.update((float(s["start"]), float(s["end"])))
    for g in timed.get("segments", []):
        pts.update((float(g["start"]), float(g["end"])))
    return sorted(pts)


def music_findings(timed: dict) -> list[dict]:
    """BP-62: music is spotted, not wallpaper."""
    music = sorted(timed.get("audio", {}).get("music", []), key=lambda m: m["start"])
    if not music:
        return []
    out = []
    sev = _sev("BP-62")
    pts = boundaries(timed)
    dur = float(timed.get("duration", 0.0))
    for m in music:
        for edge in ("start", "end"):
            t = float(m[edge])
            if not any(abs(t - p) <= BOUNDARY_TOL for p in pts):
                out.append({"rule": "BP-62", "severity": sev, "where": m.get("track", "music"),
                            "detail": f"music {edge} at {t:.2f}s is on no shot or segment boundary: spot it to a cut"})
        length = float(m["end"]) - float(m["start"])
        if (m.get("kind") == "sting" or "sting" in str(m.get("track", ""))) and length > SR.T("BP-62", "sting_max_s"):
            out.append({"rule": "BP-62", "severity": sev, "where": m.get("track", "music"),
                        "detail": f"sting of {length:.1f} s: a sting is a one-shot of at most {SR.T('BP-62', 'sting_max_s'):g} s"})
    if dur >= LONG_FORM_S:
        need = SR.T("BP-62", "no_music_stretch_min_s")
        t, longest = 0.0, 0.0
        for m in music:
            longest = max(longest, float(m["start"]) - t)
            t = max(t, float(m["end"]))
        longest = max(longest, dur - t)
        if longest < need:
            out.append({"rule": "BP-62", "severity": sev, "where": "music",
                        "detail": f"the longest stretch without music is {longest:.1f} s; a long video plans at least "
                                  f"{need:g} s of no music"})
    return out
