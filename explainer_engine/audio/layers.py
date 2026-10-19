"""Sound-layer rules AL-01..AL-04 (docs/STORY_ENGINE.md, D-48) on a timed production script: enough sound that the
picture's motion is heard, never so much that the layers turn into noise under the voice.

Episode 1 had 22 effects in 18 minutes (1.2 a minute) under one bed and up to two music tracks; the creator heard the
music and the tick fighting the voice (ED-03). The rules count what plays at once and what is missing:

* AL-01 at most ``MAX_SFX_AT_ONCE`` effects overlap, and voice + music + bed + effects stay at most ``MAX_LAYERS`` layers;
* AL-02 sound events a minute — effects and beat cues together — inside ``SFX_PER_MIN`` (too few: the motion is
  silent; too many: clutter);
* AL-03 a drawn accent that moves the picture hard (whip, flash, slam, shake, punch) has an effect within 0.25 s;
* AL-04 effects and beds stay under the voice (gain at most ``MAX_SFX_DB`` / ``MAX_BED_DB`` before the mix's ducking;
  the bed cap follows the measured preference for ambience 15 LU under commentary, docs/research/PARAMETER_AUDIT_2026-10-19.md).

All REVIEW: the ear decides; the numbers say where to listen.
"""

from __future__ import annotations

MAX_SFX_AT_ONCE = 2
MAX_LAYERS = 4  # voice + music + bed + one effect (a second effect may overlap briefly, AL-01 counts it)
SFX_PER_MIN = (4.0, 20.0)
HARD = {"whip_in", "flash_in", "slam_text", "shake", "punch"}
SYNC = 0.25
MAX_SFX_DB, MAX_BED_DB = -8.0, -15.0  # D-49: listeners want ambience >= 15 LU under commentary (Torcoli 2019)


def _active(items: list[dict], t: float) -> int:
    return sum(1 for x in items if x["start"] <= t < x["end"])


def check(timed: dict) -> list[dict]:
    out: list[dict] = []

    def add(rule, where, detail):
        out.append({"rule": rule, "severity": "REVIEW", "where": where, "detail": detail})

    au = timed.get("audio", {})
    sfx, beds, music = au.get("sfx", []), au.get("beds", []), au.get("music", [])
    dur = max(timed.get("duration", 0.0), 1e-6)
    flagged = 0.0
    for e in sorted(sfx, key=lambda x: x["start"]):
        t = e["start"] + 1e-3
        n_sfx = _active(sfx, t)
        layers = 1 + min(1, _active(music, t)) + min(1, _active(beds, t)) + n_sfx
        if (n_sfx > MAX_SFX_AT_ONCE or layers > MAX_LAYERS + 1) and t > flagged:
            add("AL-01", f"{e['start']:.1f}s", f"{n_sfx} effects and {layers} layers at once: the voice drowns in noise "
                f"(at most {MAX_SFX_AT_ONCE} effects, {MAX_LAYERS} layers)")
            flagged = e["start"] + 1.0
        if e.get("gain_db", -18) > MAX_SFX_DB:
            add("AL-04", e["sound"], f"effect at {e['gain_db']} dB: above {MAX_SFX_DB} dB it competes with the voice")
    # AL-02 counts everything the ear hears as an event: effects AND beat cues. The old count left the cues out, so
    # the density rule never fired on the layer it existed for (Syndicate Wars: 33 cues/min, AL-02 silent).
    n_events = len(sfx) + len(au.get("cues", []))
    per_min = n_events / dur * 60
    if dur >= 60 and not SFX_PER_MIN[0] <= per_min <= SFX_PER_MIN[1]:
        add("AL-02", "video", f"{per_min:.1f} sound events a minute, effects and cues together "
            f"(keep {SFX_PER_MIN[0]:.0f}-{SFX_PER_MIN[1]:.0f}): "
            + ("the motion is silent" if per_min < SFX_PER_MIN[0] else "clutter"))
    starts = [e["start"] for e in sfx] + [c["start"] for c in au.get("cues", [])]  # a beat cue (VB-08) is heard too
    for s in timed.get("shots", []):
        for a in s.get("accents", []):
            if a["kind"] in HARD and not any(abs(x - a["start"]) <= SYNC for x in starts):
                add("AL-03", s["id"], f"{a['kind']} at {a['start']:.1f}s has no effect within {SYNC} s: a move the eye sees, the ear misses")
    for b in beds:
        if b.get("gain_db", MAX_BED_DB) > MAX_BED_DB:
            add("AL-04", b["sound"], f"bed at {b['gain_db']} dB: above {MAX_BED_DB} dB the ambience masks words")
    return out
