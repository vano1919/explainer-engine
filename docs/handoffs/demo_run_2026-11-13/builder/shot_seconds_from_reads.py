"""S3b (voice first, RN-03): each shot's measured seconds from S4's per-line reads (durations.json), without Scribe.

A line's measured length is shared over the shots that carry it in proportion to their planned lengths; a shot with no
spoken line keeps its planned length. Every shot is judged against the +-10 % frame (`gemini_task.timing.in_band`) and every
video shot against the LTX clip limit (`gemini_task.timing.video_clip`, the same check G1 runs). Free, no code changed.
Usage: python shot_seconds_from_reads.py <repo root> <durations.json> <out.json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

repo, dur_path, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(repo))
from explainer_engine.gemini_task import timing as TM  # noqa: E402

script = json.loads((repo / "episodes/ep_truce_1914/story/production_script.json").read_text(encoding="utf-8"))
dur = {d["line_id"]: float(d.get("measured_s") or d["duration_s"]) for d in json.loads(dur_path.read_text(encoding="utf-8"))}
holders = defaultdict(list)
for s in script["shots"]:
    for lid in s.get("audio_line_ids") or []:
        holders[lid].append(s)
share = defaultdict(float)
for lid, shots in holders.items():
    if lid not in dur:
        continue
    tot = sum(float(s.get("target_duration_seconds") or 0) for s in shots) or len(shots)
    for s in shots:
        share[s["shot_id"]] += dur[lid] * (float(s.get("target_duration_seconds") or 0) or 1) / tot
rows, review, over = {}, [], []
for s in script["shots"]:
    planned = float(s.get("target_duration_seconds") or 0)
    spoken = [l for l in (s.get("audio_line_ids") or []) if l in dur]
    secs = round(share[s["shot_id"]], 3) if spoken else planned
    r = {"seconds": secs, "planned_seconds": planned, "source": "reads" if spoken else "planned (no spoken line)",
         "lines": spoken, "in_frame": TM.in_band(secs, planned), "mode": s.get("generation_mode")}
    if str(s.get("generation_mode", "")).upper() in ("VIDEO", "WAN", "LTX", "WAN_I2V") or s.get("route") == "video":
        r["clip"] = TM.video_clip(script, s, secs, measured=bool(spoken))
        if r["clip"].get("status") == "REVIEW":
            over.append(s["shot_id"])
    if not r["in_frame"]:
        review.append(s["shot_id"])
    rows[s["shot_id"]] = r
missing = sorted(set(holders) - set(dur))
doc = {"source": str(dur_path), "lines_read": len(dur), "lines_in_script_not_read": missing,
       "total_measured_s": round(sum(r["seconds"] for r in rows.values()), 2),
       "total_planned_s": round(sum(r["planned_seconds"] for r in rows.values()), 2),
       "outside_10pct": review, "clip_over_ltx_limit": over, "shots": rows}
out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in doc.items() if k != "shots"}, indent=1))
