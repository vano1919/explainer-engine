"""The multi-zone rhythm lint of a shot list (BP-169, BP-170): per zone of the episode, are the cuts as fast as the profile asks
and does every held still carry a dramatic change? A script of the calm era (``production_script/3`` and older, or
``rhythm_profile: calm_docudrama``) is not judged here; its checks stay in ``film_shots`` / ``board`` / ``motion_lint``.

    python -m explainer_engine.scripting.rhythm_lint <shots.json>      # {"shots": [...]} or a list; exit 1 on a FAIL

A shot is ``{"id", "seconds", "start_s"?, "lane"?, "tier"?, "dramatic_change"?}``; its start is ``start_s`` or the running sum.
Rules: RL-01 shots per minute of a zone outside its band; RL-02 a shot longer than the zone's longest; RL-03 a shot shorter than
the zone's shortest (REVIEW; a cut under 1 s is an insert); RL-04 a held still without its dramatic change (BP-170, FAIL).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from explainer_engine.edit import dramatic_still, rhythm_profile
from explainer_engine.standards import sourced_rules as SR


def zone_stats(shots: list[dict], *, total_s: float, profile_name: str) -> dict[str, dict]:
    """Per zone id: shots starting in it, their seconds, the minutes the zone covers (scaled to ``total_s``)."""
    prof = rhythm_profile.get_profile(profile_name)
    base = float(SR.T("BP-169", "episode_s"))
    stats = {z["id"]: {"shots": 0, "lengths": [], "minutes": (z["window_s"][1] - z["window_s"][0]) * total_s / base / 60.0}
             for z in prof["zones"]}
    t = 0.0
    for s in shots:
        start = float(s.get("start_s", t))
        t = start + float(s["seconds"])
        z = rhythm_profile.zone_at_time(start, total_s=total_s, profile_name=profile_name)
        stats[z["id"]]["shots"] += 1
        stats[z["id"]]["lengths"].append(float(s["seconds"]))
    return stats


def check(doc: dict, *, profile_name: str | None = None) -> list[dict]:
    shots = doc["shots"] if isinstance(doc, dict) and "shots" in doc else doc
    name = profile_name or (rhythm_profile.resolve_profile_name(doc) if isinstance(doc, dict) else "mrbeast_animated")
    if name == rhythm_profile.LEGACY or not shots:
        return []
    total = sum(float(s["seconds"]) for s in shots)
    review = SR.level("BP-169", "REVIEW")
    out: list[dict] = []

    def add(rule, sev, where, detail):
        out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})

    prof = rhythm_profile.get_profile(name)
    stats = zone_stats(shots, total_s=total, profile_name=name)
    for z in prof["zones"]:
        st = stats[z["id"]]
        if not st["lengths"] or st["minutes"] <= 0:
            continue
        per_min = st["shots"] / st["minutes"]
        lo, hi = z["shots_per_min_band"]
        if st["minutes"] >= 0.5 and not lo <= per_min <= hi:
            add("RL-01", review, z["id"], f"{per_min:.1f} shots a minute (band {lo}-{hi}): "
                                          f"{'too slow' if per_min < lo else 'too fast'} for this zone")
        slo, shi = z["shot_len_s_band"]
        long_ = [x for x in st["lengths"] if x > shi]
        short = [x for x in st["lengths"] if x < slo]
        if long_ and len(long_) / len(st["lengths"]) > 0.15:
            add("RL-02", review, z["id"], f"{len(long_)} of {len(st['lengths'])} shots are longer than {shi:g} s "
                                          f"(longest {max(long_):.1f} s)")
        if short and len(short) / len(st["lengths"]) > 0.30:
            add("RL-03", review, z["id"], f"{len(short)} of {len(st['lengths'])} shots are shorter than {slo:g} s")
    still_shots = []
    t = 0.0
    for s in shots:                                        # start_s once, so check_script_stills sees the same times
        still_shots.append(dict(s, start_s=float(s.get("start_s", t))))
        t = still_shots[-1]["start_s"] + float(s["seconds"])
    for f in dramatic_still.check_script_stills(still_shots, profile_name=name):
        add("RL-04", f["severity"], f["where"], f["detail"])
    return out


def summary(doc: dict) -> dict:
    shots = doc["shots"] if isinstance(doc, dict) and "shots" in doc else doc
    total = sum(float(s["seconds"]) for s in shots)
    name = rhythm_profile.resolve_profile_name(doc if isinstance(doc, dict) else None)
    if name == rhythm_profile.LEGACY:
        return {"profile": name}
    stats = zone_stats(shots, total_s=total, profile_name=name)
    return {"profile": name, "seconds": round(total, 1), "shots": len(shots),
            "zones": {k: {"shots": v["shots"], "per_min": round(v["shots"] / v["minutes"], 1) if v["minutes"] else None,
                          "median_s": round(statistics.median(v["lengths"]), 2) if v["lengths"] else None}
                      for k, v in stats.items()}}


def main(argv: list[str]) -> int:
    doc = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    found = check(doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(json.dumps(summary(doc)))
    print(f"{len(found)} finding(s), {fails} FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
