"""The eight map laws (docs/COMPENSATOR.md, CMP-01..08) as validators over a map item and its timeline.

Each validator returns findings ``{rule, severity, where, detail}`` and never raises: the numbers come from the registry (BP-124,
BP-125, BP-140, BP-141, BP-145, BP-146), and every one is a hypothesis, so a finding is REVIEW (D-59, CN-11). The structural
checks (the shape the renderer needs, a word that is not in the spine) are in ``render.validate_payload`` and ``timeline``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from explainer_engine.design import palette as PAL
from explainer_engine.maps import camera as CAM
from explainer_engine.maps import plate, render
from explainer_engine.maps.timeline import Timeline
from explainer_engine.standards import sourced_rules as SR

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
COLOUR_KEYS = {"color", "colour", "hex", "fill", "stroke"}


def _f(rule: str, bp: str, where: str, detail: str) -> dict:
    return {"rule": rule, "severity": SR.level(bp), "where": where, "detail": detail}


def _concurrency(tl: Timeline, ops) -> int:
    marks = []
    for e in tl.events:
        if e.op in ops:
            marks += [(e.start, 1), (e.start + e.frames, -1)]
    cur = best = 0
    for _, d in sorted(marks, key=lambda m: (m[0], m[1])):  # an event that ends where another starts does not overlap it
        cur += d
        best = max(best, cur)
    return best


def terrain_paths(spec: dict) -> list[dict]:
    """Law 2 (CMP-02): routes follow the land, stay out of the no-go areas and are eased, never a constant-speed arrow."""
    return render.route_findings(spec)


def signalling(spec: dict, tl: Timeline) -> list[dict]:
    """Law 3 (CMP-03, BP-124): at most labels_max labels and units_max unit groups at any frame, one change at a time, the inactive
    terrain dimmed round an active area."""
    out, where = [], spec["item_id"]
    labels_max, units_max = SR.T("BP-124", "labels_max"), SR.T("BP-124", "units_max")
    samples = sorted({0, tl.duration - 1} | {min(tl.duration - 1, e.start + e.frames) for e in tl.events})
    worst_l = worst_u = 0
    for f in samples:
        s = render.state(spec, tl, f)
        worst_l, worst_u = max(worst_l, len(s["labels"])), max(worst_u, len(s["unit_groups"]))
    if worst_l > labels_max:
        out.append(_f("CMP-03", "BP-124", where, f"{worst_l} labels on screen at once (at most {labels_max})"))
    if worst_u > units_max:
        out.append(_f("CMP-03", "BP-124", where, f"{worst_u} unit groups on screen at once (at most {units_max})"))
    at_once = _concurrency(tl, render.CHANGE_OPS)
    if at_once > SR.T("BP-124", "changes_at_once_max"):
        out.append(_f("CMP-03", "BP-124", where, f"{at_once} changes run at the same time (one at a time, the changed thing flagged first)"))
    p = spec["payload"]
    if (p.get("routes") or p.get("units")) and not p.get("focus"):
        out.append(_f("CMP-03", "BP-124", where, "no active area (payload.focus): the inactive terrain is not dimmed"))
    return out


def word_lock(spec: dict, tl: Timeline, duration_frames: int) -> list[dict]:
    """Law 4 (CMP-04): every element of the map appears on a spoken word; nothing sits frozen from frame 1; no event after the item."""
    out, where, p = [], spec["item_id"], spec["payload"]
    reveal = {"routes": "show_route", "labels": "show_label", "rings": "show_ring"}
    for key, op in reveal.items():
        for x in p.get(key, []):
            if not tl.by_target(x["id"], op):
                out.append(_f("CMP-04", "BP-140", where, f"{key[:-1]} {x['id']!r} has no {op} event: it would sit on frame 1, frozen"))
    for u in p.get("units", []):
        if not (tl.by_target(u["id"], "show_unit") or tl.by_target(u["id"], "march")):
            out.append(_f("CMP-04", "BP-140", where, f"unit {u['id']!r} has no show_unit or march event"))
    if not tl.events:
        out.append(_f("CMP-04", "BP-140", where, "a map item without a timed visual event"))
    for e in tl.events:
        if e.start >= duration_frames:
            out.append(_f("CMP-04", "BP-140", f"{where}.{e.id}", f"starts at frame {e.start}, after the item's {duration_frames} frames"))
    return out


def scale_progression(spec: dict, tl: Timeline, clock) -> list[dict]:
    """Law 5 (CMP-05, BP-125, BP-141): macro, then meso, then micro; an altitude change takes altitude_change_s; the camera moves
    again within camera_change_every_max_s."""
    out, where, fps = [], spec["item_id"], tl.fps
    start, moves = CAM.from_spec(spec["payload"]["camera"], clock.frame_of)
    lo, hi = SR.T("BP-125", "altitude_change_s")
    every = SR.T("BP-141", "camera_change_every_max_s")
    order = {t: i for i, t in enumerate(CAM.TIERS)}
    tiers = [CAM.tier_of(start.span_km)] + [CAM.tier_of(m.to.span_km) for m in moves]
    for prev, cur in zip(tiers, tiers[1:]):
        if order[cur] < order[prev]:
            out.append(_f("CMP-05", "BP-141", where, f"the camera climbs from {prev} back to {cur}: an explanation goes macro, meso, micro"))
    last_tier = tiers[0]
    for m in moves:
        tier = CAM.tier_of(m.to.span_km)
        secs = (m.end - m.start) / fps
        if tier != last_tier and not lo <= secs <= hi:
            out.append(_f("CMP-05", "BP-125", where, f"the change {last_tier} to {tier} takes {secs:.1f} s (it takes {lo:g}-{hi:g} s)"))
        last_tier = tier
    edges = [0] + [x for m in moves for x in (m.start, m.end)] + [tl.duration]
    for a, b in zip(edges[0::2], edges[1::2]):   # the holds: from the end of one move to the start of the next
        if (b - a) / fps > every:
            out.append(_f("CMP-05", "BP-141", where, f"the camera holds one view for {(b - a) / fps:.1f} s (it changes within {every:g} s)"))
    return out


def faction_colours(spec: dict) -> list[dict]:
    """Law 6 (CMP-06, BP-144): colours are the two faction tokens by side, never a literal colour; the pair is colour-blind safe."""
    out, where = [], spec["item_id"]

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k.lower() in COLOUR_KEYS:
                    out.append(_f("CMP-06", "BP-144", f"{where}.{path}{k}", "a colour is named by a side (a, b) or a palette token, never given"))
                walk(v, f"{path}{k}.")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}{i}.")
        elif isinstance(node, str) and HEX.match(node):
            out.append(_f("CMP-06", "BP-144", f"{where}.{path}", f"{node} is a literal colour: hex values live only in design/palette.json"))

    walk(spec["payload"], "")
    out += [_f("CMP-06", "BP-144", where, p["detail"]) for p in PAL.faction_findings()]
    return out


def map_to_scene(spec: dict, fps: int, scene_set: dict | None = None, base_dir: Path | None = None) -> list[dict]:
    """Law 7 (CMP-07, BP-145): a map that hands over to a scene ends at pitch_deg, exports its depth map and the next shot's camera
    has the same pitch; the scene's sound starts prelap_s before the cut."""
    t = spec["payload"].get("transition")
    if not t:
        return []
    out, where = [], spec["item_id"]
    want, tol, prelap = SR.T("BP-145", "pitch_deg"), SR.T("BP-145", "tolerance_deg"), SR.T("BP-145", "prelap_s")
    cam = spec["payload"]["camera"]
    moves = cam.get("moves") or []
    end_pitch = (moves[-1] if moves else cam["start"]).get("pitch_deg", 0.0)
    if abs(end_pitch - want) > tol:
        out.append(_f("CMP-07", "BP-145", where, f"the map ends at pitch {end_pitch:g}, not {want:g} +- {tol:g}"))
    if not t.get("zdepth_ref"):
        out.append(_f("CMP-07", "BP-145", where, "the map does not export its depth map (transition.zdepth_ref)"))
    elif base_dir is not None and not (Path(base_dir) / t["zdepth_ref"]).exists():
        out.append(_f("CMP-07", "BP-145", where, f"{t['zdepth_ref']} does not exist"))
    if t.get("prelap_frames", 0) < round(prelap * fps) - 1:
        out.append(_f("CMP-07", "BP-145", where, f"the scene's sound starts {t.get('prelap_frames', 0)} frames early (at least {round(prelap * fps)})"))
    if scene_set is not None:
        cams = {c["shot_id"]: c for c in scene_set.get("cameras", [])}
        c = cams.get(t["to_shot"])
        if c is None:
            out.append(_f("CMP-07", "BP-145", where, f"the scene set has no camera for shot {t['to_shot']!r}"))
        elif abs(c["pitch_deg"] - end_pitch) > tol:
            out.append(_f("CMP-07", "BP-145", where, f"shot {t['to_shot']} looks down at {c['pitch_deg']:g}, the map ended at {end_pitch:g}"))
    return out


def stimulus_window(spec: dict, tl: Timeline, clock) -> list[dict]:
    """Law 8 (CMP-08, BP-140): something visibly changes (an event or a camera move) so that no stretch longer than static_flag_s is
    still; the starts follow each other within the upper end of event_every_s."""
    out, where, fps = [], spec["item_id"], tl.fps
    static, (_lo, hi) = SR.T("BP-140", "static_flag_s"), SR.T("BP-140", "event_every_s")
    spans = [(e.start, e.start + e.frames) for e in tl.events]
    starts = [e.start for e in tl.events]
    if "camera" in spec["payload"]:
        for m in CAM.from_spec(spec["payload"]["camera"], clock.frame_of)[1]:
            spans.append((m.start, m.end))
            starts.append(m.start)
    spans.sort()
    reach, worst = 0, 0
    for a, b in spans:
        worst = max(worst, a - reach)
        reach = max(reach, b)
    worst = max(worst, tl.duration - reach)
    if worst / fps > static:
        out.append(_f("CMP-08", "BP-140", where, f"nothing changes for {worst / fps:.1f} s (a shot still for over {static:g} s is flagged)"))
    starts = sorted(set([0] + starts))
    gaps = [b - a for a, b in zip(starts, starts[1:] + [tl.duration])]
    if gaps and max(gaps) / fps > hi:
        out.append({"rule": "CMP-08", "severity": "INFO", "where": where,
                    "detail": f"the longest wait for the next change is {max(gaps) / fps:.1f} s (the window is up to {hi:g} s)"})
    return out


def date_chip(spec: dict, tl: Timeline) -> list[dict]:
    """CRAFT-CART-03 (CMP-13): whenever map time advances, a date chip shows it."""
    p = spec["payload"]
    if p.get("time_advances") and not (p.get("date_chip") or tl.of("date")):
        return [{"rule": "CMP-13", "severity": "REVIEW", "where": spec["item_id"], "detail": "map time advances without a date chip (ED-15's counter slot)"}]
    return []


def no_diffusion(spec: dict, base_dir: Path | None = None) -> list[dict]:
    """Law 1 (CMP-01, BP-146): the base is the vector plate or a painted plate that carries its certificate; no model call in a map."""
    out, where, base = [], spec["item_id"], spec["payload"].get("base", {"kind": "vector"})
    blob = json.dumps(spec["payload"]).lower()
    for word in ("prompt", "diffusion", "text2video", "model_id"):
        if f'"{word}"' in blob:
            out.append(_f("CMP-01", "BP-146", where, f"payload names {word!r}: a map is drawn from vectors, never generated"))
    if base["kind"] == "plate":
        if base_dir is None or not (Path(base_dir) / base["ref"]).exists():
            return out + [_f("CMP-01", "BP-146", where, f"the painted plate {base['ref']} is missing")]
        cert_path = Path(base_dir) / base.get("certificate", "")
        cert = json.loads(cert_path.read_text(encoding="utf-8")) if base.get("certificate") and cert_path.exists() else None
        out += [{**f, "where": where} for f in plate.certificate_findings(Path(base_dir) / base["ref"], cert)]
    return out


def check_item(spec: dict, spine: dict, trigger_word_index: int, duration_frames: int, base_dir: Path | None = None,
               scene_set: dict | None = None) -> list[dict]:
    """Every law on one map item (what ``visual_compensator.check`` runs for the four map archetypes)."""
    from explainer_engine.maps import timeline
    findings = render.validate_payload(spec)
    if any(f["severity"] == "FAIL" for f in findings):
        return findings
    try:     # a word outside the spine, or before the trigger word, raises from the clock: the item is refused, not drawn from frame 0
        tl, clock = timeline.build(spec, spine, trigger_word_index, duration_frames)
        return findings + no_diffusion(spec, base_dir) + terrain_paths(spec) + signalling(spec, tl) + word_lock(spec, tl, duration_frames) \
            + scale_progression(spec, tl, clock) + faction_colours(spec) + map_to_scene(spec, tl.fps, scene_set, base_dir) \
            + stimulus_window(spec, tl, clock) + date_chip(spec, tl)
    except ValueError as e:
        return findings + [{"rule": "CN-01", "severity": "FAIL", "where": spec["item_id"], "detail": str(e)}]
