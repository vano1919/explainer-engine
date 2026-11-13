"""The per-event audiovisual report and the delivered file's timeline (AV-08, docs/EPISODE_FIRST.md; D-135).

``event_report`` follows every visible event from the script to the sound: its id, frames, decision and class (from
``episode/events``), the asset the cue sheet gave it and where (``audio/stems_report.json``'s ``events_placed``), the onset
measured on the SFX stem, and, once the master exists, whether it is heard over its bed (``qa/sound_realism``'s
``action_sounds_heard`` per event). Machine QC is never a person's approval: every event says ``human: not_listened``.

``timeline`` is the adapter from the v4.3 runner to ``qa/sound_realism``'s ``scene_timeline/1`` (the scene join writes its
own for a scene): the cuts from the shot records, the dialogue from the line windows, the events from the placed effect rows
(with their ids), the places from the sound plan's beds.
"""
from __future__ import annotations

FPS_DEFAULT = 24


def timeline(plan: dict, records: list[dict], stems_report: dict | None, line_windows: dict | None = None) -> dict:
    cuts, t = [], 0.0
    for i, r in enumerate(records):
        if i:
            cuts.append(round(t, 3))
        t += float(r["duration_sec"])
    lines = [{"id": lid, "start_s": round(a, 3), "end_s": round(b, 3)} for lid, (a, b) in sorted((line_windows or {}).items(),
                                                                                              key=lambda kv: kv[1][0])]
    dialogue = [[lines[0]["start_s"], lines[-1]["end_s"]]] if lines else []
    events = [{"at_s": round(p["at_s"], 3), "dur_s": round(min(1.0, max(0.1, float(p.get("end_s", p["at_s"] + 0.6)) - p["at_s"])), 3),
               "class": p["class"], "event_id": p.get("event_id")}
              for p in (stems_report or {}).get("events_placed", []) if p.get("layer") in ("foley", "spot", "transition")]
    places = [{"start_s": b["start_s"], "end_s": b["end_s"], "place": b["place"]} for b in plan.get("beds", [])]
    return {"schema": "scene_timeline/1", "file": f"{plan.get('episode_id')} (episode runner)", "cuts": cuts,
            "dialogue": dialogue, "lines": lines, "intended_pauses": [], "events": events, "places": places}


def event_report(events_doc: dict, plan: dict, sheet: dict | None, stems_report: dict | None,
                 realism: dict | None = None) -> dict:
    """One row per event of ``events_doc`` (``episode/events.events_report``)."""
    starts = {s["shot_id"]: s["start_s"] for s in plan.get("shots", [])}
    fps = int(events_doc.get("fps") or FPS_DEFAULT)
    rows_by_event: dict[str, list[dict]] = {}
    for r in (sheet or {}).get("rows", []):
        if r.get("event_id"):
            rows_by_event.setdefault(r["event_id"], []).append(r)
    placed = {p["cue_id"]: p for p in (stems_report or {}).get("events_placed", [])}
    missing = {m.get("event_id"): m for m in (sheet or {}).get("missing", []) if m.get("event_id")}
    heard = {}   # sound_realism measures the timeline's events in order; match them back by (class, start)
    by_key = {(p["class"], round(p["at_s"], 2)): p.get("event_id") for p in (stems_report or {}).get("events_placed", [])}
    lo = None
    try:
        from explainer_engine.standards import sourced_rules as SR
        lo = float(SR.T("BP-192", "heard_min_db"))
    except Exception:   # noqa: BLE001 - the report still lists the numbers without a verdict
        lo = None
    for m in ((realism or {}).get("measured") or {}).get("events", []):
        eid = by_key.get((m.get("class"), round(float(m.get("at_s", -1)), 2)))
        if eid:
            heard[eid] = {"over_db": m.get("above_bed_db"),
                          "status": None if lo is None else ("heard" if m.get("above_bed_db", -99) >= lo else "not_heard")}
    out, warn_n = [], 0
    for sid, shot in events_doc.get("shots", {}).items():
        s0 = starts.get(sid, 0.0)
        for ev in shot["events"]:
            a = ev["audio"]
            rows = rows_by_event.get(ev["event_id"], [])
            warnings = []
            if a["decision"] in ("sfx", "ui_cue") and not rows:
                warnings.append("no cue row: " + (missing[ev["event_id"]]["why"] if ev["event_id"] in missing
                                                  else "not placed"))
            if a["decision"] == "review_required":
                warnings.append(f"review_required: {a.get('why')}")
            onset = None
            for r in rows:
                p = placed.get(r["cue_id"])
                if p and p.get("onset_s") is not None:
                    onset = p["onset_s"]
            want = s0 + (ev["end_frame"] - 1 if a.get("sync") == "end" else ev["start_frame"]) / fps
            off_ms = None if onset is None else round((onset - want) * 1000.0, 1)
            h = heard.get(ev["event_id"])
            warn_n += bool(warnings)
            out.append({"event_id": ev["event_id"], "shot_id": sid, "op": ev["op"], "source": ev["source"],
                        "frames": [ev["start_frame"], ev["end_frame"]], "start_s": round(s0 + ev["start_frame"] / fps, 3),
                        "decision": a["decision"], "class": a.get("class"), "sync": a.get("sync"), "why": a.get("why"),
                        "audio_basis": ev["audio_basis"], "timing": ev["timing"],
                        "assets": [r["asset_id"] for r in rows], "placement": [[r["start_s"], r["end_s"]] for r in rows],
                        "onset_s": onset, "onset_off_ms": off_ms,
                        "audible": None if h is None else h.get("status"), "audible_db": None if h is None else h.get("over_db"),
                        "human": "not_listened", "warnings": warnings})
    # FA-09: a sound no script event asked for (the designed riser from two segment moods) is listed as a DERIVED event with
    # the reason the cue sheet wrote, so nobody hears a sound the report does not name
    for r in (sheet or {}).get("rows", []):
        if r.get("layer") == "transition" and not r.get("event_id"):
            p = placed.get(r["cue_id"])
            out.append({"event_id": r["cue_id"], "shot_id": r.get("shot_id"), "op": f"derived:{r.get('class', 'riser')}",
                        "source": "derived", "frames": None, "start_s": r["start_s"], "decision": "sfx",
                        "class": r.get("class"), "sync": "end", "why": r.get("selection_reason"), "audio_basis": "derived",
                        "timing": "cut", "assets": [r["asset_id"]], "placement": [[r["start_s"], r["end_s"]]],
                        "onset_s": p.get("onset_s") if p else None, "onset_off_ms": None, "audible": None,
                        "audible_db": None, "human": "not_listened", "warnings": []})
    return {"schema": "av_event_report/1", "episode_id": events_doc.get("episode_id"), "resolver": events_doc.get("resolver"),
            "contract": events_doc.get("contract"), "events": out, "with_warnings": warn_n,
            "note": "machine QC only; a person's listening is recorded separately (review.human)"}


def markdown(rep: dict) -> str:
    lines = [f"# AV events: {rep['episode_id']}", "", f"Resolver {rep['resolver']}, contract {rep['contract']}; "
             f"{len(rep['events'])} event(s), {rep['with_warnings']} with warnings. {rep['note']}.", "",
             "| event | shot | op | frames | decision | class | asset | onset off (ms) | audible | warnings |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for e in rep["events"]:
        lines.append(f"| {e['event_id']} | {e['shot_id']} | {e['op']} | {e['frames'][0]}-{e['frames'][1]} | {e['decision']} | "
                     f"{e['class'] or ''} | {', '.join(e['assets'])} | {'' if e['onset_off_ms'] is None else e['onset_off_ms']} | "
                     f"{e['audible'] or ''} | {'; '.join(e['warnings'])[:120]} |")
    return "\n".join(lines) + "\n"
