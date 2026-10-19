"""Which pictures are filler (D-53, PV-43). stdlib only.

Importance is computed from what the script already says, never declared by the script: a writer cannot mark a picture
"filler" to get it past a gate. A picture is NOT filler when any of these holds:

* a shot that uses it is type B (named heroes acting) or the picture itself names heroes or shows people;
* it is used more than once (the viewer meets it again, so it carries the story);
* it is a premium picture (reused identity assets or a reveal);
* a segment that uses it has a beat job outside FILLER_JOBS (hook, question, evidence, complication, reveal, payoff) or no job at all.

What stays is the establishing plate (type A) or the insert (type C) with no person in it, used once, inside an explanation,
emotional pause, humour or transition beat. Shot length is not known at script stage; the 4-second limit the creator chose is
checked after timing (docs/PRODUCTION_SCRIPT.md PV-43).
"""

from __future__ import annotations

from explainer_engine.production import script as S

FILLER_JOBS = {"explanation", "emotional_pause", "humor", "transition"}
FILLER_SHARE_MAX = 0.30        # at most this share of an episode's painted pictures may come from Canva (D-53)
CANVA_FREE_AI_USES = 20        # the creator's free plan (V-39); a count above it is reviewed


def classify(doc: dict) -> dict[str, dict]:
    """picture id -> {"filler": bool, "why_not": [reasons]} for every used picture."""
    pics, _ = S.pictures(doc)
    seg_job = {seg["id"]: seg.get("job") for seg in doc["segments"]}
    shots_of: dict[str, list[dict]] = {}
    for sh in S.shots(doc):
        shots_of.setdefault(sh["picture_id"], []).append(sh)
    out = {}
    for pid, pic in pics.items():
        shots = shots_of.get(pid, [])
        if not shots:
            continue
        why = []
        if any(sh["shot"].get("type") == "B" for sh in shots):
            why.append("used in a B shot (named heroes acting)")
        if pic.get("heroes") or pic.get("people"):
            why.append("shows heroes or people")
        if len(shots) > 1:
            why.append("used more than once")
        if pic.get("tier") == "premium":
            why.append("premium picture")
        for sh in shots:
            job = seg_job.get(sh["segment"])
            if job not in FILLER_JOBS:
                why.append(f"beat {sh['segment']} has job {job!r}" if job else f"beat {sh['segment']} has no job")
        out[pid] = {"filler": not why, "why_not": sorted(set(why))}
    return out
