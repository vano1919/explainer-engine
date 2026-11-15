"""The action layer of a map shot (v4.3 plan P4.3-4, the creator's Q6): something happens on the map, on its spoken word.

A ``map_action`` shot carries ``actions`` (schema ``ShotSpec.actions``): each one a ``kind`` from the vocabulary below, the word
of the shot's line it lands on (``at_word``), and the places it uses (``from``, ``to``: ids of ``episode.json`` ``places``,
lon/lat). Everything is anchored in lon/lat and drawn in Python over the letter-free plate, so it stays right under any camera
move, and each frame is a pure function of (plan, frame number) (CMP-09): chunked renders match.

Vocabulary: ``route_arrow`` (a curved arrow draws itself from -> to), ``front_line`` (a heavy line grows from -> to),
``spread`` (an area grows round ``from`` to ``value`` km: ash fall, drought), ``plume`` (the area drifts from -> to while it
grows), ``pulse`` (rings beat at ``from``), ``highlight`` (a glow of ``value`` km round ``from``), ``label`` (the place's name
or ``label``), ``counter`` (a number counts up to ``value`` with its ``unit``), ``zoom`` (the camera eases to ``to`` or
``from`` at ``value`` km wide), ``split_compare`` (the frame splits into two cards, ``label`` "left | right").

W3 (2026-11-13, D-135; MA-01..MA-08 in docs/EPISODE_FIRST.md): ``marker_travel`` (a token rides a path from -> to, or the
route ``route`` names, sharing its progress), ``supply_line`` (a supply line draws itself; ``supply_state`` sets it ``active``,
``strained`` or ``cut``; ``snap`` breaks it), ``bar_grow`` (bars grow to ``values``), ``progress_bar`` (a bar fills to
``value`` of ``max``), ``milestone`` (a tick on the progress bar at ``value``). A route with ``via`` waypoints follows a
Catmull-Rom spline through them (``maps/paths.spline``, validated by ``maps/paths.validate``: the frame's projection is a local
equirectangular one, linear in lon/lat, so a spline in lon/lat is the same curve on screen). Every number shown carries the claim
that backs it (``claim``; the G1 row ``map_numbers_have_claims``). Frames and decisions come from ``episode/events.visual_events``
(the one resolver): half-open spans ``[start, end)``; ``until_word`` ends an action on a later word; a continuous action lasts until
the next one starts. Each action may ask the camera for ``hold`` (default), ``push``, ``pull``, ``route_pan``, ``fly_to`` or
``scale``; a dense map (``DENSE_ACTIONS`` place actions or more) holds unless it zooms. Restrained persistent life: the view drifts
``DRIFT`` over the shot, a drawn route keeps a slow flow of dashes, a pulse keeps beating; everything is a function of the frame.

A shot whose actions name no place is a card (the "other 10 %" moments: counters, comparisons on a plain styled card).
Word times: measured from the read's word spine when it exists, else spread over the line (``basis: estimated``).
"""
from __future__ import annotations

import math
import re

import numpy as np
from PIL import Image, ImageFilter

from explainer_engine.core.errors import ContractError
from explainer_engine.maps import data as MD
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, plate

KINDS = ("route_arrow", "front_line", "spread", "plume", "pulse", "highlight", "label", "counter", "zoom", "split_compare",
         "marker_travel", "supply_line", "supply_state", "snap", "bar_grow", "progress_bar", "milestone")
PLACE_KINDS = {"route_arrow": ("from", "to"), "front_line": ("from", "to"), "plume": ("from", "to"), "spread": ("from",),
               "pulse": ("from",), "highlight": ("from",), "label": ("from",), "supply_line": ("from", "to")}
PATH_KINDS = ("route_arrow", "front_line", "supply_line", "marker_travel")
NUMBER_KINDS = ("counter", "bar_grow", "progress_bar", "milestone")
CAMERAS = ("hold", "push", "pull", "route_pan", "fly_to", "scale")
DENSE_ACTIONS = 4         # a map with this many place actions holds its camera unless it zooms (house default)
DRIFT = 0.04              # the view narrows this share over a shot (restrained life; house default)
CAM_PUSH = 0.7            # a push narrows the view to this share over the event's span (pull: the inverse)
FLOW_PERIOD_F = 48        # a drawn line's dashes travel one period in this many frames
ANIM_FRAMES = 18          # an action takes this long to arrive (0.75 s at 24 fps); a house default, not a sourced rule
LEAD_IN = 0.06            # estimated word times: the line starts this share into the shot ...
LEAD_OUT = 0.12           # ... and ends this share before its end
MIN_SPAN_KM = 300.0
RENDERER_VERSION = "map_action/2.3"       # M1-M9 (2026-11-15): camera inheritance, log-zoom pan coupling, 8-pos labels, 1914 borders
WORD = re.compile(r"[A-Za-z0-9']+")


def _words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def _shot_text(shot: dict, script: dict) -> str:
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    return " ".join(str(lines.get(lid, {}).get("text") or "") for lid in shot.get("audio_line_ids", [])).strip()


def shot_words(shot: dict, script: dict) -> list[str]:
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    out: list[str] = []
    for lid in shot.get("audio_line_ids", []):
        out += _words(lines.get(lid, {}).get("text", ""))
    return out


def word_frames(words: list[str], frames: int, spine: list[dict] | dict | None = None) -> tuple[list[int], str]:
    """The frame each word starts on: from the measured spine (``[{word, start_frame}]`` relative to the shot) or estimated (M4)."""
    if isinstance(spine, dict):
        spine = spine.get("words") or spine.get("spine") or None
    if spine:
        if len(spine) != len(words):
            raise ContractError(f"the word spine has {len(spine)} words, the shot's line {len(words)}")
        starts = [int(w["start_frame"] if "start_frame" in w else w["start"]) for w in spine]
        basis = "estimated" if all(w.get("basis") == "estimated" for w in spine if isinstance(w, dict)) and any(
            isinstance(w, dict) and "basis" in w for w in spine
        ) else "measured"
        return starts, basis
    if not words:
        return [], "estimated"
    a, b = LEAD_IN * frames, (1.0 - LEAD_OUT) * frames
    return [int(round(a + (b - a) * i / len(words))) for i in range(len(words))], "estimated"


def _is_chip(pid: str | None) -> bool:
    return bool(pid and str(pid).startswith("chip_"))


def _place(places: dict, pid: str | None, sid: str, kind: str) -> tuple[float, float] | None:
    if pid is None:
        return None
    if pid not in places:
        if kind == "label" and _is_chip(pid):
            return 0.0, 0.0
        raise ContractError(f"{sid}: {kind} names the place {pid!r}, which episode.json places does not list")
    p = places[pid]
    return float(p["lon"]), float(p["lat"])


def _path_ll(a: dict, places: dict, sid: str) -> tuple[list[tuple[float, float]] | None, list[dict]]:
    """The lon/lat path of a route-like action: a spline through ``from``, ``via``..., ``to`` (validated), or the old gentle arc."""
    from explainer_engine.maps import paths as PATHS
    p0, p1 = _place(places, a.get("from"), sid, a.get("kind")), _place(places, a.get("to"), sid, a.get("kind"))
    if p0 is None or p1 is None:
        return None, []
    via = [_place(places, v, sid, a.get("kind")) for v in a.get("via") or []]
    if via:
        wp = [list(p0)] + [list(v) for v in via] + [list(p1)]
        route = {"waypoints": wp, "ease": "march", "domain": a.get("domain"), "allow_water": a.get("allow_water", False)}
        return [tuple(q) for q in PATHS.spline(wp, 24)], PATHS.validate(route, f"{sid}:{a.get('event_id') or a.get('kind')}")
    kx = math.cos(math.radians((p0[1] + p1[1]) / 2))     # bend in a locally metric space, so the arc is round on screen
    arc = _arc((p0[0] * kx, p0[1]), (p1[0] * kx, p1[1]), bend=0.12 if a.get("kind") != "front_line" else 0.0)
    return [(x / kx, y) for x, y in arc], []


def _stands(a: dict) -> bool:
    """True when an action is a standing pre-existing element (``cues: "none"`` or ``stands: true``, M2)."""
    return bool(a.get("stands") or a.get("cues") == "none")


def _is_map_shot_dict(s: dict) -> bool:
    return bool(
        s.get("route") == "map_action"
        or s.get("visual_type") == "map_visualization"
        or s.get("generation_mode") in ("TACTILE_MAP", "MAP_25D")
    )


def _same_theater(shot_a: dict, shot_b: dict, places: dict) -> bool:
    loc_a = shot_a.get("location_id") or shot_a.get("place")
    loc_b = shot_b.get("location_id") or shot_b.get("place")
    if loc_a is not None or loc_b is not None:
        return loc_a == loc_b
    mv_a, mv_b = shot_a.get("map_view"), shot_b.get("map_view")
    if isinstance(mv_a, dict) and isinstance(mv_b, dict) and "lon" in mv_a and "lon" in mv_b:
        return geo.distance_km(float(mv_a["lon"]), float(mv_a["lat"]), float(mv_b["lon"]), float(mv_b["lat"])) < 1500.0
    return True


def _build_carry_over(shot: dict, script: dict, places: dict, own_acts: list[dict], frames: int, sid: str) -> list[dict]:
    """Carry over path actions from the previous same-theater map shot as a 22 % ghost from frame 0 (V5)."""
    prev_acts: list[dict] = []
    if isinstance(shot.get("carry_over_actions"), list):
        prev_acts = list(shot["carry_over_actions"])
    elif isinstance(shot.get("prev_shot"), dict) and _same_theater(shot["prev_shot"], shot, places):
        prev_acts = list(shot["prev_shot"].get("actions") or [])
    else:
        shots = script.get("shots") or []
        for idx, s in enumerate(shots):
            if s.get("shot_id") == sid and idx > 0:
                prev_s = shots[idx - 1]
                if _is_map_shot_dict(prev_s) and _same_theater(prev_s, shot, places):
                    prev_acts = list(prev_s.get("actions") or [])
                break
    if not prev_acts:
        return []
    own_keys = {(a.get("kind"), a.get("from_id"), a.get("to_id")) for a in own_acts}
    out: list[dict] = []
    for pa in prev_acts:
        k = pa.get("kind")
        if k not in ("route_arrow", "front_line", "supply_line"):
            continue
        f_id, t_id = pa.get("from"), pa.get("to")
        if not f_id or not t_id or f_id not in places or t_id not in places:
            continue
        if (k, f_id, t_id) in own_keys:
            continue
        path, _ = _path_ll(pa, places, sid)
        if not path:
            continue
        out.append({
            "kind": k,
            "event_id": f"ghost:{pa.get('event_id') or k}",
            "start": 0,
            "end": frames,
            "from": _place(places, f_id, sid, k),
            "to": _place(places, t_id, sid, k),
            "from_id": f_id,
            "to_id": t_id,
            "path": path,
            "route": None,
            "stands": True,
            "cues": "none",
            "ghost": True,
            "alpha": MD.CARRY_OVER_GHOST_ALPHA,
        })
    return out


def _find_word_frame(phrase: str, words: list[str], starts: list[int]) -> int | None:
    tokens = _words(phrase)
    if not tokens or not words or len(starts) != len(words):
        return None
    t0 = tokens[0]
    for i, w in enumerate(words):
        if w == t0:
            if len(tokens) == 1 or words[i:i + len(tokens)] == tokens:
                return int(starts[i])
    return None


def _build_auto_labels(
    shot: dict,
    script: dict,
    places: dict,
    acts: list[dict],
    raw_acts: list[dict],
    words: list[str],
    starts: list[int],
    own_view: dict | None,
) -> list[dict]:
    """Automatic place label pills from narration/action places plus macro theater reference cities (V2)."""
    if not places or own_view is None:
        return []
    explicit_pids = {a.get("from_id") for a in acts if a["kind"] == "label" and not _is_chip(a.get("from_id"))}
    explicit_names = {
        str(a.get("label") or a.get("name") or "").strip().lower()
        for a in acts
        if a["kind"] == "label" and not _is_chip(a.get("from_id"))
    }
    by_pid: dict[str, dict] = {}
    order_counter = 0

    def upsert(
        pid: str,
        lon: float,
        lat: float,
        text: str,
        start: int,
        stands: bool,
        priority: int,
        prefer: str = "NE",
        macro_only: bool = False,
        close_only: bool = False,
    ) -> None:
        nonlocal order_counter
        norm = text.strip().lower()
        if pid in explicit_pids or norm in explicit_names:
            return
        pref_dir = MD.PLACE_LABEL_PREFER.get(pid, prefer)
        if pid in by_pid:
            cur = by_pid[pid]
            if priority < cur["priority"]:
                cur["priority"] = priority
            if stands:
                cur["stands"] = True
                cur["start"] = 0
            else:
                cur["start"] = min(cur["start"], int(start))
            if not macro_only:
                cur["macro_only"] = False
            if not close_only:
                cur["close_only"] = False
            return
        by_pid[pid] = {
            "id": pid,
            "lon": float(lon),
            "lat": float(lat),
            "text": text,
            "start": 0 if stands else int(start),
            "stands": bool(stands),
            "priority": int(priority),
            "prefer": pref_dir,
            "macro_only": bool(macro_only),
            "close_only": bool(close_only),
            "order": order_counter,
        }
        order_counter += 1

    # 1. Narration-named places (including aliases like "North Sea" -> nieuport, "Switzerland" -> swiss_border)
    raw_text_low = _shot_text(shot, script).lower()
    zoom_only_pids = {
        raw_a.get(k)
        for raw_a in raw_acts
        if raw_a.get("kind") == "zoom"
        for k in ("from", "to")
        if raw_a.get(k)
    }
    for alias, target_pid in MD.NARRATION_PLACE_ALIASES.items():
        if alias in raw_text_low and target_pid in places and not _is_chip(target_pid):
            pinfo = places[target_pid]
            wf = _find_word_frame(alias, words, starts)
            upsert(
                target_pid,
                float(pinfo["lon"]),
                float(pinfo["lat"]),
                str(pinfo.get("name") or target_pid),
                wf if wf is not None else 0,
                wf is None,
                priority=1,
                prefer="E",
            )
    for pid, pinfo in places.items():
        if _is_chip(pid) or not isinstance(pinfo, dict) or "lon" not in pinfo or "lat" not in pinfo:
            continue
        pname = str(pinfo.get("name") or pid)
        candidates = {pid.replace("_", " ").lower(), pname.lower(), re.sub(r"^the\s+", "", pname.lower())}
        for cand in candidates:
            if cand and re.search(rf"\b{re.escape(cand)}\b", raw_text_low):
                wf = _find_word_frame(cand, words, starts)
                # A regional zoom target (e.g. "Flanders") yields to specific sector towns when 6 towns are in frame
                is_region_zoom = pid in zoom_only_pids or pid == "flanders"
                upsert(
                    pid,
                    float(pinfo["lon"]),
                    float(pinfo["lat"]),
                    pname,
                    0 if is_region_zoom else (wf if wf is not None else 0),
                    is_region_zoom or (wf is None),
                    priority=5 if is_region_zoom else 1,
                    prefer="NW" if is_region_zoom else "NE",
                )
                break

    # 2. Places named in shot actions (from, to, and via waypoints)
    standing_line_pids: set[str] = set()
    for a, raw_a in zip(acts, raw_acts):
        if a["kind"] in PATH_KINDS and _stands(a):
            for k in ("from", "to"):
                if raw_a.get(k):
                    standing_line_pids.add(raw_a[k])
            for v_pid in raw_a.get("via") or []:
                standing_line_pids.add(v_pid)

    prefer_cycle = ("E", "W", "NE", "NW", "SE", "SW")
    for idx, (a, raw_a) in enumerate(zip(acts, raw_acts)):
        k = a["kind"]
        if k == "label":
            continue
        st = _stands(a)
        for role_idx, role in enumerate(("from", "to")):
            pid = raw_a.get(role)
            if not pid or _is_chip(pid) or pid not in places:
                continue
            pinfo = places[pid]
            is_standing = st or (pid in standing_line_pids) or k == "zoom"
            prio = 5 if k == "zoom" else (1 if k in ("pulse", "highlight", "spread") else 2)
            pref = raw_a.get("prefer") or prefer_cycle[(idx + role_idx) % len(prefer_cycle)]
            upsert(
                pid,
                float(pinfo["lon"]),
                float(pinfo["lat"]),
                str(pinfo.get("name") or pid),
                0 if is_standing else a["start"],
                is_standing,
                priority=prio,
                prefer=pref,
            )
        for v_idx, v_pid in enumerate(raw_a.get("via") or []):
            if not v_pid or _is_chip(v_pid) or v_pid not in places:
                continue
            pinfo = places[v_pid]
            is_standing = st or (v_pid in standing_line_pids)
            prio = 3 if k == "route_arrow" else 4
            pref = prefer_cycle[(idx + v_idx + 2) % len(prefer_cycle)]
            upsert(
                v_pid,
                float(pinfo["lon"]),
                float(pinfo["lat"]),
                str(pinfo.get("name") or v_pid),
                0 if is_standing else a["start"],
                is_standing,
                priority=prio,
                prefer=pref,
            )

    # 3. Theater key reference cities at macro spans (Paris / Brussels / Aachen / Ypres / Liege / Verdun)
    vlon, vlat = float(own_view["lon"]), float(own_view["lat"])
    for _th_name, th_cfg in MD.THEATER_REFERENCE_CITIES.items():
        b0, b1, b2, b3 = th_cfg["bbox"]
        if not (b0 <= vlon <= b2 and b1 <= vlat <= b3):
            continue
        has_theater_place = any(
            isinstance(pv, dict)
            and "lon" in pv
            and "lat" in pv
            and b0 <= float(pv["lon"]) <= b2
            and b1 <= float(pv["lat"]) <= b3
            for pk, pv in places.items()
            if not _is_chip(pk)
        )
        if not has_theater_place:
            continue
        for city in th_cfg["cities"]:
            cid = city["id"]
            if cid in places and isinstance(places[cid], dict):
                clon = float(places[cid]["lon"])
                clat = float(places[cid]["lat"])
                cname = str(places[cid].get("name") or city["name"])
            else:
                clon, clat, cname = float(city["lon"]), float(city["lat"]), str(city["name"])
            upsert(
                cid,
                clon,
                clat,
                cname,
                start=0,
                stands=True,
                priority=3,
                prefer=city.get("prefer", "NE"),
                macro_only=cid not in by_pid,
            )
        # Also make close-sector places from episode.json available when zoomed in (< 180 km, e.g. S02_SH003 end)
        for idx_p, (pid, pinfo) in enumerate(places.items()):
            if _is_chip(pid) or pid == "flanders" or pid in by_pid or not isinstance(pinfo, dict):
                continue
            if "lon" in pinfo and "lat" in pinfo:
                upsert(
                    pid,
                    float(pinfo["lon"]),
                    float(pinfo["lat"]),
                    str(pinfo.get("name") or pid),
                    start=0,
                    stands=True,
                    priority=4,
                    prefer=prefer_cycle[idx_p % len(prefer_cycle)],
                    close_only=True,
                )

    return sorted(by_pid.values(), key=lambda x: (x["priority"], x["order"]))


def plan(
    shot: dict,
    script: dict,
    places: dict,
    fps: int,
    spine: list[dict] | None = None,
    prev_end_view: dict | None = None,
) -> dict:
    """Resolve a shot's actions to frames (``episode/events.visual_events``, the one resolver) and lon/lat. Every ``at_word``
    must be a word of the shot's line, in order."""
    from explainer_engine.episode import events as E
    sid = shot.get("shot_id", "?")
    frames = max(fps, int(round(float(shot.get("target_duration_seconds") or 0) * fps)))
    acts = shot.get("actions") or []
    if not acts:
        raise ContractError(f"{sid}: a map_action shot needs actions (RT-03)")
    for a in acts:
        if a.get("kind") not in KINDS:
            raise ContractError(f"{sid}: unknown action kind {a.get('kind')!r}")
    if spine is None:
        spine = shot.get("spine") or shot.get("word_spine")
    if prev_end_view is None and isinstance(shot.get("prev_end_view"), dict):
        prev_end_view = shot["prev_end_view"]
    evs = [e for e in E.visual_events(shot, script, spine, fps) if e["source"] == "actions"]
    words = shot_words(shot, script)
    starts, basis = word_frames(words, frames, spine)
    out, findings = [], []
    for a, ev in zip(acts, evs):
        kind = a["kind"]
        for k in PLACE_KINDS.get(kind, ()):
            if not a.get(k):
                raise ContractError(f"{sid}: {kind} needs {k!r}")
        if kind in NUMBER_KINDS:
            vals = a.get("values") if kind == "bar_grow" else [a.get("value")]
            if not vals or any(v is None or isinstance(v, str) for v in vals):
                raise ContractError(f"{sid}: {kind} shows a number: give its value(s) from the claim map (never invented)")
            if kind == "progress_bar" and not a.get("max"):
                raise ContractError(f"{sid}: progress_bar needs max (the full value)")
        if kind == "marker_travel" and not a.get("route") and not (a.get("from") and a.get("to")):
            raise ContractError(f"{sid}: marker_travel needs from and to, or the route it rides on")
        if kind in ("supply_state", "snap") and not a.get("route"):
            raise ContractError(f"{sid}: {kind} needs the event_id of its supply line (route)")
        if a.get("camera") is not None and a["camera"] not in CAMERAS:
            raise ContractError(f"{sid}: camera {a['camera']!r} is not one of {', '.join(CAMERAS)}")
        path, found = _path_ll(a, places, sid) if kind in PATH_KINDS else (None, [])
        findings += found
        stands = _stands(a)
        out.append({"kind": kind, "event_id": ev["event_id"], "audio": ev["audio"],
                    "start": 0 if stands else ev["start_frame"], "word_start": ev["start_frame"],
                    "end": ev["end_frame"], "timing": ev["timing"], "word": a.get("at_word"), "until_word": a.get("until_word"),
                    "from": _place(places, a.get("from"), sid, kind), "to": _place(places, a.get("to"), sid, kind),
                    "from_id": a.get("from"), "to_id": a.get("to"), "path": path, "route": a.get("route"),
                    "state": a.get("state"), "claim": a.get("claim"), "values": a.get("values"), "labels": a.get("labels"),
                    "max": a.get("max"), "camera": a.get("camera") or ("zoom" if kind == "zoom" else "hold"),
                    "name": (places.get(a.get("from")) or {}).get("name") if a.get("from") else None,
                    "value": a.get("value"), "unit": a.get("unit", ""), "label": a.get("label"),
                    "cues": a.get("cues"), "stands": stands, "prefer": a.get("prefer", "NE")})
    ids = {a["event_id"]: a for a in out}
    for a in out:
        if a["route"] is not None:
            r = ids.get(a["route"])
            if r is None or r["path"] is None:
                raise ContractError(f"{sid}: {a['kind']} rides {a['route']!r}, which is no route of this shot")
            if a["kind"] == "marker_travel" and a["path"] is None:
                a["path"] = r["path"]
    card = not any(a["from"] or a["to"] or a["path"] for a in out)
    dense = sum(1 for a in out if (a["from"] and not _is_chip(a.get("from_id"))) or a["path"]) >= DENSE_ACTIONS
    own_view = None if card else _own_view(shot, out)
    view0 = None if card else _first_view(shot, out, prev_end_view=prev_end_view)
    carry_over = [] if card else _build_carry_over(shot, script, places, out, frames, sid)
    auto_labels = [] if card else _build_auto_labels(shot, script, places, out, acts, words, starts, own_view)
    period = (
        shot.get("period")
        or shot.get("historical_period")
        or script.get("historical_period")
        or (1914 if "1914" in str(script.get("episode_id") or shot.get("episode_id") or "") else None)
    )
    return {"shot_id": sid, "frames": frames, "fps": fps, "basis": basis, "spine_basis": basis, "card": card,
            "actions": out, "carry_over": carry_over, "auto_labels": auto_labels,
            "dense": dense, "drift": DRIFT, "path_findings": findings,
            "view0": view0, "own_view": own_view,
            "prev_end_view": dict(view0) if (prev_end_view is not None and not card) else None,
            "period": period}


def _own_view(shot: dict, acts: list[dict]) -> dict:
    mv = shot.get("map_view")
    if mv:
        return {"lon": float(mv["lon"]), "lat": float(mv["lat"]), "span_km": float(mv["span_km"])}
    pts = [p for a in acts if a["kind"] != "zoom" and not _is_chip(a.get("from_id")) for p in (a["from"], a["to"]) if p]
    pts += [q for a in acts if a.get("path") for q in a["path"][:: max(1, len(a["path"]) // 8)]]
    if not pts:
        pts = [p for a in acts for p in (a["from"], a["to"]) if p]
    lons, lats = [p[0] for p in pts], [p[1] for p in pts]
    lon, lat = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
    kx = geo.KM_PER_DEG * math.cos(math.radians(lat))
    span = max(MIN_SPAN_KM, (max(lons) - min(lons)) * kx * 1.5, (max(lats) - min(lats)) * geo.KM_PER_DEG * 1.5 * 16 / 9)
    for a in acts:
        if a["kind"] in ("spread", "plume", "highlight") and a.get("value"):
            span = max(span, float(a["value"]) * 3.0)
    return {"lon": lon, "lat": lat, "span_km": span}


def _first_view(shot: dict, acts: list[dict], prev_end_view: dict | None = None) -> dict:
    """The initial camera view of a map shot: starts at ``prev_end_view`` when chained from a same-location map shot, and
    records the shot's own view so ``camera()`` moves smoothly to it (M3)."""
    own = _own_view(shot, acts)
    if prev_end_view is None and isinstance(shot.get("prev_end_view"), dict):
        prev_end_view = shot["prev_end_view"]
    if prev_end_view is not None:
        v0 = {"lon": float(prev_end_view["lon"]), "lat": float(prev_end_view["lat"]), "span_km": float(prev_end_view["span_km"])}
        if acts:
            acts[0]["_own_view"] = own
            acts[0]["_from_prev_view"] = True
        return v0
    return own


def _u(a: dict, f: int) -> float:
    """Eased progress of an action on its half-open span ``[start, end)``: 0 before, 1 from its last frame on (1.0 when standing)."""
    if _stands(a):
        return 1.0
    if f < a["start"]:
        return 0.0
    return D.ease_in_out(min(1.0, (f - a["start"]) / max(1, a["end"] - 1 - a["start"])))


def _u_counter(a: dict, f: int) -> float:
    """Eased progress of a counter from its first visible frame (never 0 at ``f == a['start']``, M6)."""
    if f < a["start"]:
        return 0.0
    span = max(1, a["end"] - a["start"])
    return D.ease_in_out(min(1.0, (f - a["start"] + 1) / span))


def _progress(a: dict, f: int) -> float:
    """A path's progress: 1.0 from frame 0 if standing (M2), else a march for routes and markers and ease_in_out for the rest."""
    if _stands(a):
        return 1.0
    if f < a["start"]:
        return 0.0
    u = min(1.0, (f - a["start"]) / max(1, a["end"] - 1 - a["start"]))
    return D.march(u) if a["kind"] in PATH_KINDS else D.ease_in_out(u)


def _head(p: dict, a: dict, f: int) -> float:
    """How far a path is drawn at ``f``: its own progress, never behind a marker that rides it (one progress)."""
    u = _progress(a, f)
    for m in p["actions"]:
        if m["kind"] == "marker_travel" and m.get("route") == a["event_id"]:
            u = max(u, _progress(m, f))
    return u


def _lerp_view(cur: dict, tgt: tuple | None, span: float, u: float) -> dict:
    """Interpolate camera in log-scale ``span_km`` with pan progress coupled to scale change (M1)."""
    tgt = tgt or (cur["lon"], cur["lat"])
    s0, s1 = max(1e-3, float(cur["span_km"])), max(1e-3, float(span))
    s = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * u)
    if abs(s1 - s0) > 25.0:
        pan_u = 0.65 * ((s - s0) / (s1 - s0)) + 0.35 * u
    else:
        pan_u = u
    return {"lon": cur["lon"] + (tgt[0] - cur["lon"]) * pan_u,
            "lat": cur["lat"] + (tgt[1] - cur["lat"]) * pan_u,
            "span_km": s}


def lerp_view(v0, v1, u: float, span: float | None = None):
    """Public camera interpolator with cubic ease-in-out, log-scale zoom, and scale-coupled pan (M1).

    Supports both ``lerp_view(v0, v1, u)`` (where ``v0`` and ``v1`` are ``dict`` or ``geo.View``) and
    ``lerp_view(cur_dict, tgt_lonlat, span_km, u_eased)``."""
    if span is not None:
        return _lerp_view(v0, v1, float(u), float(span))
    e = D.ease_in_out(float(u))
    if isinstance(v0, geo.View) and isinstance(v1, geo.View):
        d = _lerp_view({"lon": v0.lon, "lat": v0.lat, "span_km": v0.span_km}, (v1.lon, v1.lat), v1.span_km, e)
        return geo.View(d["lon"], d["lat"], d["span_km"], v0.width, v0.height)
    lon1 = v1["lon"] if isinstance(v1, dict) else v1[0]
    lat1 = v1["lat"] if isinstance(v1, dict) else v1[1]
    s1 = float(v1["span_km"]) if isinstance(v1, dict) else float(v0["span_km"])
    return _lerp_view(v0, (lon1, lat1), s1, e)


def camera(p: dict, f: int) -> dict:
    """The view at frame ``f``: starts at ``view0`` (inherited from ``prev_end_view`` when present, easing to the shot's own
    view), applies restrained drift, and executes every camera move whose event has started (``zoom`` and ``fly_to`` both
    honour ``a['value']`` with log-scale zoom and scale-coupled pan, M1 & M3)."""
    cur = dict(p["view0"])
    n = max(1, p["frames"] - 1)
    acts = p.get("actions") or []
    own = p.get("own_view") or next((a.get("_own_view") for a in acts if a.get("_own_view")), None)
    inherited = p.get("prev_end_view") is not None or any(a.get("_from_prev_view") for a in acts)
    if inherited and own is not None and f > 0:
        same_center = abs(own["lon"] - cur["lon"]) < 1e-3 and abs(own["lat"] - cur["lat"]) < 1e-3
        drift_share = p.get("drift", DRIFT)
        drift_only = same_center and abs(own["span_km"] * (1.0 - drift_share) - cur["span_km"]) / max(1.0, own["span_km"]) < 0.015
        cam_starts = [a["start"] for a in acts if a.get("camera") in ("zoom", "fly_to", "scale") or a.get("kind") == "zoom"]
        if not drift_only and not (same_center and cam_starts):
            path_starts = [a["start"] for a in acts if a.get("kind") in PATH_KINDS and not _stands(a) and a["start"] >= ANIM_FRAMES]
            h_end = max(1, min(cam_starts) if cam_starts else (min(path_starts) if path_starts else n))
            u_h = D.ease_in_out(min(1.0, f / h_end))
            cur = _lerp_view(cur, (own["lon"], own["lat"]), own["span_km"], u_h)
    cur["span_km"] *= 1.0 - p.get("drift", DRIFT) * D.ease_in_out(f / n)
    for a in acts:
        cam = a.get("camera", "zoom" if a["kind"] == "zoom" else "hold")
        if cam == "hold" or f < a["start"] or (p.get("dense") and cam not in ("zoom", "fly_to")):
            continue
        u = _u(a, f)
        if cam in ("zoom", "fly_to"):
            default_span = cur["span_km"] / 3.0 if (cam == "zoom" or a["kind"] == "zoom") else cur["span_km"]
            span = float(a["value"]) if a.get("value") else default_span
            cur = _lerp_view(cur, a["to"] or a["from"], span, u)
        elif cam in ("push", "pull"):
            k = CAM_PUSH if cam == "push" else 1.0 / CAM_PUSH
            cur = _lerp_view(cur, a["to"] or a["from"], cur["span_km"] * k, u)
        elif cam == "route_pan" and a.get("path"):
            cur = _lerp_view(cur, D.polyline_point(a["path"], _head(p, a, f)), cur["span_km"], min(1.0, 4 * u))
        elif cam == "scale" and (a.get("path") or a["from"]):
            pts = a["path"] or [a["from"]] + ([a["to"]] if a["to"] else [])
            lons, lats = [q[0] for q in pts], [q[1] for q in pts]
            kx = geo.KM_PER_DEG * math.cos(math.radians(cur["lat"]))
            want = max(MIN_SPAN_KM, (max(lons) - min(lons)) * kx * 1.4, (max(lats) - min(lats)) * geo.KM_PER_DEG * 1.4 * 16 / 9)
            cur = _lerp_view(cur, ((min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2), want, u)
    return cur


def safe_frame_bounds(width: int = 1920, height: int = 1080) -> tuple[float, float, float, float]:
    """Safe-frame bounding box ``(xmin, ymin, xmax, ymax)`` in output pixels (M5)."""
    mx = max(4.0, width * max(MD.SAFE_MARGIN_MIN_FRAC, MD.SAFE_MARGIN_X_FRAC))
    mt = max(4.0, height * max(MD.SAFE_MARGIN_MIN_FRAC, MD.SAFE_MARGIN_TOP_FRAC))
    mb = max(4.0, height * max(MD.SAFE_MARGIN_MIN_FRAC, MD.SAFE_MARGIN_BOTTOM_FRAC))
    return mx, mt, width - mx, height - mb


def place_label_8pos(
    cx: float,
    cy: float,
    tw: float,
    th: float,
    occupied: list[tuple[float, float, float, float]],
    prefer: str = "NE",
    width: int = 1920,
    height: int = 1080,
) -> tuple[float, float, tuple[float, float, float, float], bool]:
    """8-position greedy label/chip solver with safe-frame clamping and obstacle avoidance (M5)."""
    pad = max(2.0, th * 0.35)
    pad_x = max(2.0, tw * 0.04)
    pad_y = max(2.0, th * 0.10)
    # Second-tier leader offsets clear the first-tier boxes (-pad - th and +pad) plus 2 * pad_y so colocated labels never overlap (V7)
    dy_up2 = -pad - 2.0 * th - 2.5 * pad_y
    dy_dn2 = +pad + th + 2.5 * pad_y
    order_map = {
        "NE": [
            (+pad, -pad - th, False),
            (-pad - tw, -pad - th, False),
            (+pad, +pad, False),
            (-pad - tw, +pad, False),
            (+pad * 1.4, -th * 0.5, False),
            (-pad * 1.4 - tw, -th * 0.5, False),
            (+pad * 1.8, dy_up2, True),
            (-pad * 1.8 - tw, dy_up2, True),
        ],
        "NW": [
            (-pad - tw, -pad - th, False),
            (+pad, -pad - th, False),
            (-pad - tw, +pad, False),
            (+pad, +pad, False),
            (-pad * 1.4 - tw, -th * 0.5, False),
            (+pad * 1.4, -th * 0.5, False),
            (-pad * 1.8 - tw, dy_up2, True),
            (+pad * 1.8, dy_up2, True),
        ],
        "E": [
            (+pad * 1.35, -th * 0.5, False),
            (+pad, -pad - th, False),
            (+pad, +pad, False),
            (-pad * 1.35 - tw, -th * 0.5, False),
            (-pad - tw, -pad - th, False),
            (-pad - tw, +pad, False),
            (+pad * 1.8, dy_up2, True),
            (-pad * 1.8 - tw, dy_up2, True),
        ],
        "W": [
            (-pad * 1.35 - tw, -th * 0.5, False),
            (-pad - tw, -pad - th, False),
            (-pad - tw, +pad, False),
            (+pad * 1.35, -th * 0.5, False),
            (+pad, -pad - th, False),
            (+pad, +pad, False),
            (-pad * 1.8 - tw, dy_up2, True),
            (+pad * 1.8, dy_up2, True),
        ],
        "SE": [
            (+pad, +pad, False),
            (+pad, -pad - th, False),
            (-pad - tw, +pad, False),
            (-pad - tw, -pad - th, False),
            (+pad * 1.35, -th * 0.5, False),
            (-pad * 1.35 - tw, -th * 0.5, False),
            (+pad * 1.8, dy_dn2, True),
            (-pad * 1.8 - tw, dy_dn2, True),
        ],
        "SW": [
            (-pad - tw, +pad, False),
            (+pad, +pad, False),
            (-pad - tw, -pad - th, False),
            (+pad, -pad - th, False),
            (-pad * 1.35 - tw, -th * 0.5, False),
            (+pad * 1.35, -th * 0.5, False),
            (-pad * 1.8 - tw, dy_dn2, True),
            (+pad * 1.8, dy_dn2, True),
        ],
    }
    extra_ring = [
        (+pad * 1.8, dy_dn2, True),
        (-pad * 1.8 - tw, dy_dn2, True),
        (+pad * 2.4, dy_up2 - th - 2.5 * pad_y, True),
        (-pad * 2.4 - tw, dy_up2 - th - 2.5 * pad_y, True),
        (+pad * 2.4, dy_dn2 + th + 2.5 * pad_y, True),
        (-pad * 2.4 - tw, dy_dn2 + th + 2.5 * pad_y, True),
    ]
    candidates = list(order_map.get(prefer, order_map["NE"])) + extra_ring
    xmin, ymin, xmax, ymax = safe_frame_bounds(width, height)
    max_x0 = max(xmin, xmax - tw)
    max_y0 = max(ymin, ymax - th)

    best = None
    best_cost = float("inf")
    for idx, (dx, dy, leader) in enumerate(candidates):
        x0 = float(np.clip(cx + dx, xmin, max_x0))
        y0 = float(np.clip(cy + dy, ymin, max_y0))
        x1, y1 = x0 + tw, y0 + th

        hard_overlap = 0.0
        soft_overlap = 0.0
        px0, py0, px1, py1 = x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y   # the stored box is padded: test the padded box
        for obs in occupied:
            ox0, oy0, ox1, oy1 = obs[0], obs[1], obs[2], obs[3]
            w_obs = float(obs[4]) if len(obs) > 4 else 1.0
            iw = max(0.0, min(px1, ox1) - max(px0, ox0))
            ih = max(0.0, min(py1, oy1) - max(py0, oy0))
            if w_obs >= 0.5:
                hard_overlap += iw * ih * w_obs
            else:
                soft_overlap += iw * ih * w_obs

        overlap = hard_overlap + soft_overlap
        cost = hard_overlap * 1000000.0 + soft_overlap * 200.0 + idx * 14.0 + (30.0 if leader else 0.0)
        if cost < best_cost:
            best_cost = cost
            best = (x0, y0, (x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y), leader)
            if overlap == 0.0 and not leader:
                break

    assert best is not None
    occupied.append(best[2])
    return best


def _arc(a: tuple, b: tuple, n: int = 64, bend: float = 0.12) -> list[tuple[float, float]]:
    (x0, y0), (x1, y1) = a, b
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    t = np.linspace(0, 1, n)
    xs = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1
    ys = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1
    return list(zip(xs.tolist(), ys.tolist()))


def _blob(cx: float, cy: float, r: float, key: str, stretch: tuple[float, float] = (0.0, 0.0), n: int = 72):
    rng = D.seeded("blob", key)
    ph = rng.uniform(0, 2 * math.pi, 3)
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        wob = 1.0 + 0.10 * math.sin(3 * t + ph[0]) + 0.06 * math.sin(5 * t + ph[1]) + 0.04 * math.sin(9 * t + ph[2])
        dx, dy = math.cos(t), math.sin(t)
        along = dx * stretch[0] + dy * stretch[1]
        out.append((cx + r * wob * dx + max(0.0, along) * stretch[0] * r, cy + r * wob * dy + max(0.0, along) * stretch[1] * r))
    return out


def colours(look: dict | None = None) -> dict:
    look = look or {}
    pick = lambda k, d: D.rgb(look.get(k) or d)   # noqa: E731
    return {"ink": pick("ink", "ink"), "accent": pick("accent", "answer_coral"), "ash": pick("ash", "grey_mid"),
            "paper": D.rgb("paper"), "card": pick("card", "kit_card"), "glow": pick("accent", "uncertain_amber"),
            "allied": D.rgb(look.get("allied") or "faction_a"), "german": D.rgb(look.get("german") or "faction_b")}


def _fmt(v: float, like: float | None = None) -> str:
    """A shown number; a count towards a whole target shows whole numbers all the way (no "0.00" on its first frame)."""
    if like is not None and float(like).is_integer():
        return f"{int(round(v)):,}"
    return f"{int(round(v)):,}" if abs(v) >= 1 else f"{v:.2f}"


def _box(p: dict, c, kind: str) -> tuple[float, float, float, float]:
    """Where a number sits: on a card (no map under it) the numbers are the picture, large and centred, the counter above the
    bars; on a map they keep to the corners the land leaves free (the counter bottom left, a progress bar top left, bars on the
    right), so two numbers never sit on each other (the pilot's card, 2026-11-13, had the counter under the progress bar)."""
    if p.get("card"):
        has_bar = any(a["kind"] in ("bar_grow", "progress_bar") for a in p["actions"])
        return {"counter": (c.w * 0.5, c.h * (0.30 if has_bar else 0.50), 0, 0),
                "progress_bar": (c.w * 0.16, c.h * 0.60, c.w * 0.84, c.h * 0.66),
                "bar_grow": (c.w * 0.25, c.h * 0.42, c.w * 0.75, c.h * 0.90)}[kind]
    return {"counter": (c.w * 0.05, c.h * 0.78, 0, 0),
            "progress_bar": (c.w * 0.06, c.h * 0.10, c.w * 0.50, c.h * 0.145),
            "bar_grow": (c.w * 0.60, c.h * 0.50, c.w * 0.95, c.h * 0.90)}[kind]


def counter_layout(p: dict, c: D.Canvas, a: dict, unit: float) -> tuple[float, float, float, float, str, str, float]:
    """Compute ``(x0, y0, x1, y1, text, final_text, size)`` for a ``counter`` action at frame ``f`` (locked width, M6)."""
    target_val = float(a.get("value") or 0)
    final_text = f"{_fmt(target_val, a.get('value') or 0)} {a.get('unit') or ''}".strip()
    size = unit * (0.12 if p.get("card") else 0.07)
    x0, y0, _, _ = _box(p, c, "counter")
    w = c.text_width(final_text, size) + size
    th = size * 1.5
    if p.get("card"):
        x0, y0 = x0 - w / 2, y0 - size * 0.75
    xmin, ymin, xmax, ymax = safe_frame_bounds(c.w, c.h)
    stroke = max(2.0, unit * 0.004)
    x0 = float(np.clip(x0, xmin + stroke, max(xmin + stroke, xmax - stroke - w)))
    y0 = float(np.clip(y0, ymin + stroke, max(ymin + stroke, ymax - stroke - th)))
    return x0, y0, x0 + w, y0 + th, final_text, final_text, size


def _hud_chip_box(c: D.Canvas, text: str, unit: float) -> tuple[float, float, float, float, float, float]:
    """Safe-frame clamped HUD date card layout ``(x0, y0, x1, y1, size, stroke)`` at least 4% inside every edge (V1)."""
    xmin, ymin, xmax, ymax = safe_frame_bounds(c.w, c.h)
    size = max(unit * 0.042, 6.0)
    stroke = max(2.0, unit * 0.004)
    tw = c.text_width(text, size) + size * 1.25
    th = size * 1.5
    x0 = max(xmin + stroke, c.w * MD.HUD_CARD_X_FRAC)
    y0 = max(ymin + stroke, c.h * MD.HUD_CARD_Y_FRAC)
    x0 = min(x0, max(xmin + stroke, xmax - stroke - tw))
    y0 = min(y0, max(ymin + stroke, ymax - stroke - th))
    return x0, y0, x0 + tw, y0 + th, size, stroke


def _precollect_obstacles(base: D.Canvas, p: dict, f: int, px, unit: float) -> list[tuple]:
    """Collect bounding boxes of drawn lines and HUD cards at frame ``f`` so labels avoid them (M5)."""
    occupied: list[tuple] = []
    for a in p["actions"]:
        k = a["kind"]
        if k == "label" and _is_chip(a.get("from_id")):
            text = a.get("label") or a.get("name") or a["from_id"]
            x0, y0, x1, y1, _sz, stroke = _hud_chip_box(base, text, unit)
            occupied.append((x0 - stroke, y0 - stroke, x1 + stroke, y1 + stroke))
        elif k == "counter":
            x0, y0, x1, y1, _, _, _ = counter_layout(p, base, a, unit)
            occupied.append((x0, y0, x1, y1))
        elif k in ("progress_bar", "bar_grow"):
            x0, y0, x1, y1 = _box(p, base, k)
            occupied.append((x0, y0, x1, y1))
        elif k in PATH_KINDS and a.get("path") and px is not None:
            # Reserve the full path corridor across the shot so standing city labels never jump when a line draws through them
            part = [px(q) for q in a["path"]]
            r = max(2.5, unit * 0.0055)
            step = max(6.0, r * 1.8)
            acc = step
            for p0, p1 in zip(part, part[1:]):
                seg_len = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
                if seg_len <= 1e-6:
                    continue
                pos = 0.0
                while pos <= seg_len:
                    if acc >= step:
                        t = pos / seg_len
                        qx = p0[0] + (p1[0] - p0[0]) * t
                        qy = p0[1] + (p1[1] - p0[1]) * t
                        occupied.append((qx - r, qy - r, qx + r, qy + r, 0.05))
                        acc = 0.0
                    rem = step - acc
                    if pos + rem <= seg_len:
                        pos += rem
                        acc = step
                    else:
                        acc += seg_len - pos
                        break
    return occupied


def _draw_geo_label_pill(
    c: D.Canvas,
    cx: float,
    cy: float,
    text: str,
    alpha: int,
    prefer: str,
    col: dict,
    unit: float,
    occupied: list,
    label_boxes: list[dict] | None,
) -> None:
    """Draw a collision-free place label pill with pin dot and optional leader line (V2, V7)."""
    size = max(unit * 0.022, 6.5)
    pad_in_x = max(3.0, size * 0.45)
    tw = max(8.0, c.text_width(text, size) + 2.0 * pad_in_x)
    th = max(8.0, size * 1.48)
    lx, ly, _, leader = place_label_8pos(cx, cy, tw, th, occupied, prefer=prefer, width=c.w, height=c.h)
    pin_r = max(2.0, unit * 0.0042)
    dist_to_pill = math.hypot(
        cx - float(np.clip(cx, lx, lx + tw)),
        cy - float(np.clip(cy, ly, ly + th)),
    )
    if leader or dist_to_pill > th * 0.95:
        c.line([(cx, cy), (lx + tw * 0.5, ly + th * 0.5)], (*col["ink"], int(alpha * 0.78)), max(1.0, unit * 0.002))
    if 0.0 <= cx <= c.w and 0.0 <= cy <= c.h:
        c.circle(cx, cy, pin_r, fill=(*col["paper"], alpha), outline=(*col["ink"], alpha), width=max(1.0, unit * 0.002))
    pill_fill = (*D.blend(col["paper"], col["card"], 0.12), int(alpha * 0.94))
    pill_out = (*col["ink"], int(alpha * 0.90))
    c.rect(lx, ly, lx + tw, ly + th, fill=pill_fill, outline=pill_out, width=max(1.2, unit * 0.0022), radius=th * 0.24)
    c.text((lx + pad_in_x, ly + th * 0.5), text, size, (*col["ink"], alpha), anchor="lm")
    if label_boxes is not None:
        label_boxes.append({"text": text, "kind": "geo_label", "box": (lx, ly, lx + tw, ly + th), "leader": leader})


def draw(base: D.Canvas, p: dict, f: int, view: geo.View | None, look: dict | None = None) -> None:
    """Draw every started action of plan ``p`` at frame ``f`` on canvas ``base`` (output pixels). Each action is drawn on its
    own transparent layer and composited, so its alpha blends (PIL writes RGBA pixels as they are on an RGBA image)."""
    col = colours(look)
    ink, accent = (*col["ink"], 255), (*col["accent"], 255)
    px = (lambda ll: tuple(float(v) for v in view.to_px(*ll))) if view else None
    unit = base.h
    occupied = _precollect_obstacles(base, p, f, px, unit)
    label_boxes: list[dict] = []
    # 1. Render carried-over ghost lines from the previous same-theater map shot at 22% opacity (V5)
    for g in p.get("carry_over") or []:
        cg = D.Canvas(base.w, base.h, None, base.ss)
        cg.face = base.face
        _draw_one(cg, g, p, f, view, col, ink, accent, px, unit, occupied=occupied, label_boxes=None)
        arr = np.asarray(cg.im, dtype=np.uint8).copy()
        ghost_alpha = float(g.get("alpha", MD.CARRY_OVER_GHOST_ALPHA))
        arr[:, :, 3] = np.clip(arr[:, :, 3].astype(np.float32) * ghost_alpha + 0.5, 0, 255).astype(np.uint8)
        base.im.alpha_composite(Image.fromarray(arr, mode="RGBA"))
    # 2. Render active actions of this shot
    geo_label_count = 0
    for a in p["actions"]:
        if f < a["start"] and not _stands(a):
            continue
        c = D.Canvas(base.w, base.h, None, base.ss)
        c.face = base.face
        _draw_one(c, a, p, f, view, col, ink, accent, px, unit, occupied=occupied, label_boxes=label_boxes)
        base.im.alpha_composite(c.im)
        if a["kind"] == "label" and not _is_chip(a.get("from_id")):
            geo_label_count += 1
    # 3. Render automatic place label pills and macro reference cities up to MAX_LABELS_PER_FRAME (V2)
    if view is not None and px is not None and p.get("auto_labels"):
        xmin, ymin, xmax, ymax = safe_frame_bounds(base.w, base.h)
        visible_auto: list[dict] = []
        for lb in p["auto_labels"]:
            if not lb.get("stands") and f < lb["start"]:
                continue
            if lb.get("macro_only") and view.span_km < MD.MACRO_LABEL_MIN_SPAN_KM:
                continue
            if lb.get("close_only") and view.span_km >= MD.MACRO_LABEL_MIN_SPAN_KM:
                continue
            cx, cy = px((lb["lon"], lb["lat"]))
            if not (xmin <= cx <= xmax and ymin <= cy <= ymax):
                continue
            visible_auto.append({**lb, "cx": cx, "cy": cy})
        slots_left = max(0, MD.MAX_LABELS_PER_FRAME - geo_label_count)
        selected_auto = visible_auto[:slots_left]
        # Place standing labels before newly appearing labels so standing labels never jump slots across frames
        selected_auto.sort(key=lambda x: (0 if x.get("stands") else 1, x["start"], x["priority"], x["order"]))
        if selected_auto:
            ca = D.Canvas(base.w, base.h, None, base.ss)
            ca.face = base.face
            for lb in selected_auto:
                alpha = 255 if lb.get("stands") else int(255 * min(1.0, (f - lb["start"] + 1) / 6.0))
                _draw_geo_label_pill(
                    ca, lb["cx"], lb["cy"], lb["text"], alpha, lb.get("prefer", "NE"), col, unit, occupied, label_boxes
                )
            base.im.alpha_composite(ca.im)
    p.setdefault("_label_boxes", {})[f] = label_boxes


def _subpath(pts: list[tuple[float, float]], a: float, b: float) -> list[tuple[float, float]]:
    """The part of a polyline between shares ``a`` and ``b`` of its length."""
    if b <= a:
        return []
    head = D.polyline_prefix(pts, b)
    if a <= 0:
        return head
    cut = D.polyline_prefix(pts, a)
    return [cut[-1]] + head[len(cut):] if len(head) > len(cut) - 1 else [cut[-1], head[-1]]


def supply_state(p: dict, line: dict, f: int) -> tuple[str, float, float]:
    """(state, eased progress of the change, where the line breaks) of a supply line at ``f``: the last ``supply_state`` or
    ``snap`` that rides it and has started; a snap is a cut."""
    state, u, at = "active", 1.0, 0.5
    for a in p["actions"]:
        if a.get("route") != line["event_id"] or a["kind"] not in ("supply_state", "snap") or f < a["start"]:
            continue
        state = "cut" if a["kind"] == "snap" else (a.get("state") or "active")
        u = _u(a, f)
        if a.get("value") not in (None, "") and not isinstance(a.get("value"), str):
            at = min(0.95, max(0.05, float(a["value"])))
    return state, u, at


def _flow(c, path_px, f, colour, r) -> None:
    """Restrained life on a finished line: a few small dots travel slowly along it (pure in the frame number)."""
    n = 5
    for k in range(n):
        t = ((k + f / FLOW_PERIOD_F) / n) % 1.0
        x, y = D.polyline_point(path_px, t)
        c.circle(x, y, r, fill=colour)


def _draw_dual_front_line(c: D.Canvas, part: list[tuple[float, float]], col: dict, ink: tuple, w: float, unit: float) -> None:
    """Draw the Western Front dual Entente (blue west) / German (red east) line around a dark core with traverse ticks (V4)."""
    if len(part) < 2:
        return
    # Soft warm/dark shadow under the front line
    c.line(part, (*col["ink"], 55), w * 2.3)
    offset_px = max(1.8, w * 0.42)
    west_line: list[tuple[float, float]] = []
    east_line: list[tuple[float, float]] = []
    # Determine overall north->south vs south->north orientation so west (smaller x) is always Entente blue and east (larger x) is German red
    overall_dy = part[-1][1] - part[0][1]
    overall_dx = part[-1][0] - part[0][0]
    sign = 1.0 if (overall_dy > 0 or (abs(overall_dy) < 1e-3 and overall_dx >= 0)) else -1.0
    for i, (tx, ty) in enumerate(part):
        p_prev = part[max(0, i - 1)]
        p_next = part[min(len(part) - 1, i + 1)]
        dx, dy = (p_next[0] - p_prev[0]) * sign, (p_next[1] - p_prev[1]) * sign
        ln = math.hypot(dx, dy) or 1.0
        # For north->south (dy > 0), east (+x) unit normal is (+dy/ln, -dx/ln); if east_nx < 0 on a sharp bend, keep east on +x
        east_nx, east_ny = dy / ln, -dx / ln
        if east_nx < 0:
            east_nx, east_ny = -east_nx, -east_ny
        west_line.append((tx - east_nx * offset_px, ty - east_ny * offset_px))
        east_line.append((tx + east_nx * offset_px, ty + east_ny * offset_px))

    flank_w = max(1.5, w * 0.46)
    casing_w = max(2.2, flank_w * 1.55)
    core_w = max(1.2, w * 0.28)
    c.line(west_line, (*col["ink"], 235), casing_w)
    c.line(east_line, (*col["ink"], 235), casing_w)
    c.line(west_line, (*col["allied"], 248), flank_w)
    c.line(east_line, (*col["german"], 248), flank_w)
    c.line(part, ink, core_w)

    # Perpendicular traverse ticks along the trench core
    tick_spacing = max(8.0, unit * 0.024)
    tick_half = max(2.5, offset_px * 1.35)
    tick_w = max(1.0, unit * 0.0018)
    acc_d = tick_spacing * 0.5
    for a_pt, b_pt in zip(part, part[1:]):
        seg_d = math.hypot(b_pt[0] - a_pt[0], b_pt[1] - a_pt[1])
        if seg_d <= 1e-4:
            continue
        ux, uy = (b_pt[0] - a_pt[0]) / seg_d, (b_pt[1] - a_pt[1]) / seg_d
        nx, ny = -uy, ux
        pos = 0.0
        while pos + (tick_spacing - acc_d) <= seg_d:
            pos += tick_spacing - acc_d
            mx = a_pt[0] + ux * pos
            my = a_pt[1] + uy * pos
            c.line([(mx - nx * tick_half, my - ny * tick_half), (mx + nx * tick_half, my + ny * tick_half)],
                   (*col["ink"], 220), tick_w)
            acc_d = 0.0
        acc_d += seg_d - pos


def _arrow_lookback(part: list[tuple[float, float]], min_dist: float) -> tuple[float, float]:
    """Find a point along ``part`` at least ``min_dist`` behind ``part[-1]`` so the arrowhead direction never wobbles (V4)."""
    tip = part[-1]
    for pt in reversed(part[:-1]):
        if math.hypot(tip[0] - pt[0], tip[1] - pt[1]) >= min_dist:
            return pt
    return part[0]


def _draw_path(c, a, p, f, col, ink, accent, px, unit) -> None:
    k = a["kind"]
    path = [px(q) for q in a["path"]]
    w = max(3.0, unit * {"route_arrow": 0.011, "front_line": 0.016, "supply_line": 0.008, "marker_travel": 0.006}[k])
    u = _head(p, a, f)
    if k == "marker_travel":
        if a.get("route") is None:   # its own faint trail; a marker on a route leaves the route to draw itself
            trail = D.polyline_prefix(path, u)
            if len(trail) >= 2:
                c.line(trail, (*col["ink"], 110), w, dash=(w * 2.0, w * 1.6))
        x, y = D.polyline_point(path, u)
        D.marker(c, "a", x, y, unit * 0.016)
        return
    colour = accent
    pieces = [D.polyline_prefix(path, u)]
    if k == "supply_line":
        state, su, at = supply_state(p, a, f)
        if state == "strained":   # the line thins, turns amber and breathes
            colour = (*D.blend(col["accent"], col["glow"], su), 255)
            w *= 1.0 - 0.35 * su * (0.75 + 0.25 * math.sin(2 * math.pi * f / 20.0))
        elif state == "cut":
            gap = 0.07 * su
            pieces = [_subpath(path, 0.0, min(u, at - gap)), _subpath(path, at + gap, u)]
            bx, by = D.polyline_point(path, at)
            r = unit * 0.018 * su
            if r > 1:
                c.line([(bx - r, by - r), (bx + r, by + r)], ink, max(2.0, w * 0.9))
                c.line([(bx - r, by + r), (bx + r, by - r)], ink, max(2.0, w * 0.9))
    if k == "front_line":
        for part in pieces:
            if len(part) >= 2:
                _draw_dual_front_line(c, part, col, ink, w, unit)
        return
    if k == "route_arrow":
        part = pieces[0]
        if len(part) >= 2:
            s_dx, s_dy = max(1.5, unit * 0.003), max(2.0, unit * 0.004)
            shadow_pts = [(x + s_dx, y + s_dy) for x, y in part]
            c.line(shadow_pts, (*col["ink"], 50), w * 2.2)
            c.line(shadow_pts, (*col["ink"], 85), w * 1.65)
            c.line(part, ink, w * 1.7)
            c.line(part, colour, w)
            if u > 0.02:
                tip = part[-1]
                back = _arrow_lookback(part, max(4.0, w * 1.6))
                D.arrow_head(c, (tip[0] + s_dx, tip[1] + s_dy), (back[0] + s_dx, back[1] + s_dy), w * 2.6, (*col["ink"], 75), None)
                D.arrow_head(c, tip, back, w * 2.6, accent, ink)
        if u >= 1.0:
            _flow(c, path, f - a["end"], (*col["paper"], 170), max(1.5, w * 0.35))
        return
    for part in pieces:
        if len(part) >= 2:
            c.line(part, ink, w * 1.7)
            c.line(part, colour, w, dash=(w * 2.2, w * 1.2) if k in ("front_line", "supply_line") else None)
    if u >= 1.0 and k in ("route_arrow", "supply_line") and not (k == "supply_line" and supply_state(p, a, f)[0] == "cut"):
        _flow(c, path, f - a["end"], (*col["paper"], 170), max(1.5, w * 0.35))


def _panel(c, x0, y0, x1, y1, col, ink, unit):
    c.rect(x0, y0, x1, y1, fill=(*col["card"], 225), outline=ink, width=max(2.0, unit * 0.003), radius=unit * 0.012)


def _draw_numbers(c, a, p, f, col, ink, accent, unit) -> None:
    k = a["kind"]
    u = _u(a, f)
    size = unit * (0.05 if p.get("card") else 0.034)
    if k == "bar_grow":
        vals = [float(v) for v in a["values"]]
        labels = list(a.get("labels") or [])
        top = max(vals) or 1.0
        x0, y0, x1, y1 = _box(p, c, "bar_grow")
        _panel(c, x0, y0, x1, y1, col, ink, unit)
        n = len(vals)
        slot = (x1 - x0) / n
        base = y1 - size * 1.6
        hmax = (base - y0) - size * 2.2
        for i, v in enumerate(vals):
            ui = D.ease_in_out(min(1.0, max(0.0, u * 1.25 - 0.25 * i / max(1, n - 1))))   # bars grow in a short stagger
            bx = x0 + slot * (i + 0.2)
            h = hmax * v / top * ui
            c.rect(bx, base - h, bx + slot * 0.6, base, fill=accent, outline=ink, width=max(1.5, unit * 0.002))
            if ui > 0.05:
                c.text((bx + slot * 0.3, base - h - size * 0.3), f"{_fmt(v * ui, v)}", size, ink, anchor="mb")
            if i < len(labels):
                c.text((bx + slot * 0.3, base + size * 0.25), labels[i], size * 0.8, ink, anchor="mt")
    elif k in ("progress_bar", "milestone"):
        bar = a if k == "progress_bar" else next((b for b in p["actions"] if b["kind"] == "progress_bar"), None)
        full = float((bar or a).get("max") or a.get("value") or 1.0)
        x0, y0, x1, y1 = _box(p, c, "progress_bar")
        if k == "progress_bar":
            _panel(c, x0 - unit * 0.01, y0 - size * 1.5, x1 + unit * 0.01, y1 + unit * 0.012, col, ink, unit)
            share = min(1.0, float(a["value"]) / full) * u
            c.rect(x0, y0, x1, y1, fill=(*col["paper"], 235), outline=ink, width=max(1.5, unit * 0.002), radius=unit * 0.006)
            if share > 0:
                c.rect(x0, y0, x0 + (x1 - x0) * share, y1, fill=accent, radius=unit * 0.006)
            c.text((x1, y0 - size * 0.35), f"{_fmt(float(a['value']) * u, a['value'])} / {_fmt(full)} {a.get('unit') or ''}"
                   .strip(), size, ink, anchor="rb")      # right-aligned: a milestone's label keeps the left side
        else:
            x = x0 + (x1 - x0) * min(1.0, float(a["value"]) / full)
            alpha = int(255 * min(1.0, (f - a["start"] + 1) / 6))
            pop = 1.0 + 0.4 * max(0.0, 1.0 - (f - a["start"]) / 8.0)
            c.polygon([(x, y0 - size * 0.2), (x - size * 0.35 * pop, y0 - size * 0.9 * pop),
                       (x + size * 0.35 * pop, y0 - size * 0.9 * pop)], fill=(*col["glow"], alpha), outline=(*col["ink"], alpha),
                      width=max(1.0, unit * 0.002))
            if a.get("label"):     # under the bar, clear of the bar's own value above it
                c.text((x - size * 0.35, y1 + size * 0.35), a["label"], size * 0.9, (*col["ink"], alpha), anchor="lt",
                       stroke=max(1.0, size * 0.08), stroke_fill=(*col["paper"], alpha))


def _sector_diameter_px(km: float, view: geo.View, unit: float) -> float:
    """Sector diameter in pixels clamped to 6-14 % of the frame height (V6)."""
    raw_d = float(km) / max(1e-6, view.km_per_px)
    return float(np.clip(raw_d, unit * MD.SECTOR_WIDTH_MIN_FRAC, unit * MD.SECTOR_WIDTH_MAX_FRAC))


def _draw_one(c, a, p, f, view, col, ink, accent, px, unit, occupied=None, label_boxes=None) -> None:
    u = _u(a, f)
    k = a["kind"]
    if k in PATH_KINDS:
        if a.get("path") and px is not None:
            _draw_path(c, a, p, f, col, ink, accent, px, unit)
    elif k in ("bar_grow", "progress_bar", "milestone"):
        _draw_numbers(c, a, p, f, col, ink, accent, unit)
    elif k in ("supply_state", "snap"):
        pass    # drawn by the supply line they ride on
    elif k in ("spread", "plume"):
        r = float(a.get("value") or 400.0) * u / view.km_per_px
        sx, sy = px(a["from"])
        if r > 1:   # a soft-edged cloud: drawn on its own layer and blurred, then laid over the map
            layer = D.Canvas(c.w, c.h, None, 1)
            fill = (*col["ash"], int(140 * min(1.0, 0.4 + u)))
            if k == "plume" and a["to"]:   # a trail from the source to the moving head, widening as it goes
                tx, ty = px(a["to"])
                for n in range(9):
                    t = u * n / 8
                    layer.polygon(_blob(sx + (tx - sx) * t, sy + (ty - sy) * t, r * (0.35 + 0.65 * t / max(u, 1e-6)) * 0.6,
                                        f"{p['shot_id']}{k}{n}"), fill=fill)
            else:
                layer.polygon(_blob(sx, sy, r, p["shot_id"] + k), fill=fill)
            c.paste(layer.image().filter(ImageFilter.GaussianBlur(max(1.0, r * 0.10))))
    elif k == "pulse":
        cx, cy = px(a["from"])
        km = float(a.get("value") or MD.DEFAULT_PULSE_KM)
        diam = _sector_diameter_px(km, view, unit)
        max_r = diam * 0.5
        for n in range(3):
            t = ((f - a["start"]) / 24.0 + n / 3.0) % 1.0
            r_ring = max_r * (0.20 + 0.80 * t)
            c.circle(cx, cy, r_ring, outline=(*col["accent"], int(235 * (1 - t))), width=max(1.5, unit * 0.003))
        c.circle(cx, cy, max(2.0, unit * 0.006), fill=accent)
        p.setdefault("_pulse_radii", {}).setdefault(f, []).append(max_r)
    elif k == "highlight":
        cx, cy = px(a["from"])
        km = float(a.get("value") or MD.DEFAULT_HIGHLIGHT_KM)
        diam = _sector_diameter_px(km, view, unit)
        active_hl = max(1, sum(1 for x in p["actions"] if x["kind"] == "highlight" and (f >= x["start"] or _stands(x))))
        max_area_r = math.sqrt((MD.HIGHLIGHT_AREA_MAX_FRAC * 0.85 * c.w * c.h) / (math.pi * active_hl))
        r = min(diam * 0.5, max_area_r)
        c.circle(cx, cy, max(3.0, r), fill=(*col["glow"], int(85 * u)), outline=(*col["glow"], int(215 * u)),
                 width=max(1.5, unit * 0.003))
        p.setdefault("_highlight_radii", {}).setdefault(f, []).append(r)
    elif k == "label":
        text = a.get("label") or a.get("name") or a["from_id"]
        alpha = int(255 * min(1.0, (f - a["start"] + 1) / 6))
        if _is_chip(a.get("from_id")):   # M5: date actions at chip_* render as a top-left screen-space HUD card
            x0, y0, x1, y1, size, stroke = _hud_chip_box(c, text, unit)
            th = y1 - y0
            card_fill = (*D.blend(col["paper"], col["card"], 0.25), int(242 * alpha / 255))
            c.rect(x0, y0, x1, y1, fill=card_fill, outline=(*col["ink"], alpha),
                   width=stroke, radius=size * 0.25)
            bar_w = max(3.0, size * 0.22)
            bar_col = col["allied"] if "dec" in str(a.get("from_id")).lower() else col["accent"]
            c.rect(x0, y0, x0 + bar_w, y1, fill=(*bar_col, alpha), radius=size * 0.12)
            c.text((x0 + size * 0.65, y0 + th * 0.5), text, size, (*col["ink"], alpha), anchor="lm")
            if label_boxes is not None:
                label_boxes.append({"text": text, "kind": "hud_chip", "box": (x0, y0, x1, y1)})
        else:
            cx, cy = px(a["from"])
            occ = occupied if occupied is not None else []
            _draw_geo_label_pill(c, cx, cy, text, alpha, a.get("prefer", "NE"), col, unit, occ, label_boxes)
    elif k == "counter":
        target_val = float(a.get("value") or 0)
        u_cnt = _u_counter(a, f)
        v = target_val * u_cnt
        if target_val > 0:
            floor_v = 1.0 if float(target_val).is_integer() or target_val >= 1.0 else 0.01
            v = max(floor_v, v)
        elif target_val < 0:
            floor_v = -1.0 if float(target_val).is_integer() or target_val <= -1.0 else -0.01
            v = min(floor_v, v)
        text = f"{_fmt(v, a.get('value') or 0)} {a.get('unit') or ''}".strip()
        x0, y0, x1, y1, _final, _, size = counter_layout(p, c, a, unit)
        c.rect(x0, y0, x1, y1, fill=(*col["card"], 235), outline=ink, width=max(2.0, unit * 0.004), radius=size * 0.25)
        c.text((x0 + size / 2, y0 + size * 0.75), text, size, ink, anchor="lm")
        p.setdefault("_counter_boxes", {})[f] = (x0, y0, x1, y1)
    elif k == "split_compare":
        left, _, right = str(a.get("label") or "|").partition("|")
        top = c.h * (1.0 - u)
        c.rect(c.w / 2 - unit * 0.004, top, c.w / 2 + unit * 0.004, c.h, fill=ink)
        size = unit * 0.06
        alpha = int(255 * u)
        for x, t in ((c.w * 0.25, left.strip()), (c.w * 0.75, right.strip())):
            if t:
                c.text((x, c.h * 0.5), t, size, (*col["ink"], alpha), anchor="mm", stroke=max(1.0, size * 0.1),
                       stroke_fill=(*col["paper"], alpha))


class Plate:
    """One letter-free plate for the whole shot, drawn once at the resolution its finest frame needs, cropped per frame
    (bicubic, never nearest: no moire)."""

    MAX_W = 8192

    def __init__(self, p: dict, width: int, height: int, look: dict | None = None, shaded_relief: bool = True):
        views = [camera(p, f) for f in range(p["frames"])]
        spans = [v["span_km"] for v in views]
        min_span, max_span = min(spans), max(spans)
        # When a shot zooms more than 2.2x (e.g. S02_SH003 1000 -> 60 km), build a wide plate and a native close-range plate
        # so the close view is never clamped by MAX_W or blurred/magnified from the wide plate (V3, V6).
        has_zoom_split = (max_span / max(1e-3, min_span)) > 2.2
        wide_views = [v for v in views if v["span_km"] >= min_span * 2.0] if has_zoom_split else views
        if not wide_views:
            wide_views = views
        fine = min(v["span_km"] / width for v in wide_views)
        boxes = [geo.View(v["lon"], v["lat"], v["span_km"], width, height).bbox(0.02) for v in views]
        lon0, lat0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        lon1, lat1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        lat = (lat0 + lat1) / 2
        kx = geo.KM_PER_DEG * math.cos(math.radians(lat))
        span = (lon1 - lon0) * kx
        h_km = (lat1 - lat0) * geo.KM_PER_DEG
        pw = int(min(self.MAX_W, max(width, math.ceil(span / fine))))
        ph = int(max(height, math.ceil(pw * h_km / span)))
        self.view = geo.View((lon0 + lon1) / 2, lat, span, pw, ph)
        self.image = plate.render_plate(self.view, ss=1, shaded_relief=shaded_relief, look=look, period=p.get("period"))
        self.fine_view: geo.View | None = None
        self.fine_image: Image.Image | None = None
        self.fine_threshold_km: float = 0.0
        if has_zoom_split:
            close_cut = min_span * 2.2
            close_views = [v for v in views if v["span_km"] <= close_cut]
            if close_views:
                c_fine = min(v["span_km"] / width for v in close_views)
                c_boxes = [geo.View(v["lon"], v["lat"], v["span_km"], width, height).bbox(0.04) for v in close_views]
                clon0, clat0 = min(b[0] for b in c_boxes), min(b[1] for b in c_boxes)
                clon1, clat1 = max(b[2] for b in c_boxes), max(b[3] for b in c_boxes)
                clat = (clat0 + clat1) / 2
                ckx = geo.KM_PER_DEG * math.cos(math.radians(clat))
                cspan = (clon1 - clon0) * ckx
                ch_km = (clat1 - clat0) * geo.KM_PER_DEG
                cpw = int(min(self.MAX_W, max(width, math.ceil(cspan / c_fine))))
                cph = int(max(height, math.ceil(cpw * ch_km / cspan)))
                self.fine_view = geo.View((clon0 + clon1) / 2, clat, cspan, cpw, cph)
                self.fine_image = plate.render_plate(
                    self.fine_view, ss=1, shaded_relief=shaded_relief, look=look, period=p.get("period")
                )
                self.fine_threshold_km = close_cut
        self.width, self.height = width, height

    def frame(self, v: dict, ss: int = 1) -> Image.Image:
        """The plate crop of view ``v`` at ``ss`` times the frame size (a supersampled canvas takes it as it is)."""
        fv = geo.View(v["lon"], v["lat"], v["span_km"], self.width, self.height)
        src_view, src_im = self.view, self.image
        if self.fine_view is not None and self.fine_image is not None and v["span_km"] <= self.fine_threshold_km:
            fx0, fy0 = self.fine_view.to_px(*fv.to_lonlat(0, 0))
            fx1, fy1 = self.fine_view.to_px(*fv.to_lonlat(fv.width, fv.height))
            if fx0 >= 0 and fy0 >= 0 and fx1 <= self.fine_view.width and fy1 <= self.fine_view.height:
                src_view, src_im = self.fine_view, self.fine_image
        x0, y0 = src_view.to_px(*fv.to_lonlat(0, 0))
        x1, y1 = src_view.to_px(*fv.to_lonlat(fv.width, fv.height))
        return src_im.transform((self.width * ss, self.height * ss), Image.EXTENT,
                                (float(x0), float(y0), float(x1), float(y1)), Image.BICUBIC)

    def upsample(self, v: dict, raster_km_per_px: float) -> float:
        """How much the relief raster is enlarged in view ``v`` (above about 3 the relief looks soft: a finer DEM is needed)."""
        return raster_km_per_px / (v["span_km"] / self.width)


def card_base(width: int, height: int, look: dict | None = None) -> Image.Image:
    """The plain styled card of the "other 10 %" moments: a soft vertical gradient of the look's card colour."""
    col = colours(look)
    top, bottom = np.asarray(col["card"], np.float32), np.asarray(D.blend(col["card"], col["ink"], 0.18), np.float32)
    t = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    arr = np.broadcast_to(top + (bottom - top) * t, (height, width, 3))
    return Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), "RGB")


def render_frame(p: dict, f: int, base, width: int, height: int, look: dict | None = None, ss: int = D.SS) -> Image.Image:
    """One frame: the plate crop (or the card) and the actions at frame ``f``."""
    if p["card"]:
        bg, view = base.resize((width * ss, height * ss), Image.BICUBIC) if ss > 1 else base, None
    else:
        v = camera(p, f)
        bg, view = base.frame(v, ss), geo.View(v["lon"], v["lat"], v["span_km"], width, height)
    c = D.Canvas(width, height, None, ss)
    c.replace(bg.convert("RGBA"))   # Canvas.replace takes the supersampled size
    c.face = "map"
    draw(c, p, f, view, look)
    return c.image().convert("RGB")
