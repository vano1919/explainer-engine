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
RENDERER_VERSION = "map_action/2.2"       # W3 (D-135): the clip cache keys on it (2.1: numbers laid out per card or map)
WORD = re.compile(r"[A-Za-z0-9']+")


def _words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def shot_words(shot: dict, script: dict) -> list[str]:
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", [])}
    out: list[str] = []
    for lid in shot.get("audio_line_ids", []):
        out += _words(lines.get(lid, {}).get("text", ""))
    return out


def word_frames(words: list[str], frames: int, spine: list[dict] | None = None) -> tuple[list[int], str]:
    """The frame each word starts on: from the spine (``[{word, start_frame}]`` relative to the shot) or estimated."""
    if spine:
        if len(spine) != len(words):
            raise ContractError(f"the word spine has {len(spine)} words, the shot's line {len(words)}")
        return [int(w["start_frame"]) for w in spine], "measured"
    if not words:
        return [], "estimated"
    a, b = LEAD_IN * frames, (1.0 - LEAD_OUT) * frames
    return [int(round(a + (b - a) * i / len(words))) for i in range(len(words))], "estimated"


def _place(places: dict, pid: str | None, sid: str, kind: str) -> tuple[float, float] | None:
    if pid is None:
        return None
    if pid not in places:
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


def plan(shot: dict, script: dict, places: dict, fps: int, spine: list[dict] | None = None) -> dict:
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
    evs = [e for e in E.visual_events(shot, script, spine, fps) if e["source"] == "actions"]
    words = shot_words(shot, script)
    basis = word_frames(words, frames, spine)[1]
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
        out.append({"kind": kind, "event_id": ev["event_id"], "audio": ev["audio"], "start": ev["start_frame"],
                    "end": ev["end_frame"], "timing": ev["timing"], "word": a.get("at_word"), "until_word": a.get("until_word"),
                    "from": _place(places, a.get("from"), sid, kind), "to": _place(places, a.get("to"), sid, kind),
                    "from_id": a.get("from"), "to_id": a.get("to"), "path": path, "route": a.get("route"),
                    "state": a.get("state"), "claim": a.get("claim"), "values": a.get("values"), "labels": a.get("labels"),
                    "max": a.get("max"), "camera": a.get("camera") or ("zoom" if kind == "zoom" else "hold"),
                    "name": (places.get(a.get("from")) or {}).get("name") if a.get("from") else None,
                    "value": a.get("value"), "unit": a.get("unit", ""), "label": a.get("label"),
                    "stands": kind == "front_line" and a.get("cues") == "none"})   # a line the viewer already knows stands at once, nothing is drawn
    ids = {a["event_id"]: a for a in out}
    for a in out:
        if a["route"] is not None:
            r = ids.get(a["route"])
            if r is None or r["path"] is None:
                raise ContractError(f"{sid}: {a['kind']} rides {a['route']!r}, which is no route of this shot")
            if a["kind"] == "marker_travel" and a["path"] is None:
                a["path"] = r["path"]
    card = not any(a["from"] or a["to"] or a["path"] for a in out)
    dense = sum(1 for a in out if a["from"] or a["path"]) >= DENSE_ACTIONS
    return {"shot_id": sid, "frames": frames, "fps": fps, "basis": basis, "card": card, "actions": out, "dense": dense,
            "drift": DRIFT,
            "path_findings": findings, "view0": None if card else _first_view(shot, out)}


def _first_view(shot: dict, acts: list[dict]) -> dict:
    mv = shot.get("map_view")
    if mv:
        return {"lon": float(mv["lon"]), "lat": float(mv["lat"]), "span_km": float(mv["span_km"])}
    pts = [p for a in acts if a["kind"] != "zoom" for p in (a["from"], a["to"]) if p]
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


def _u(a: dict, f: int) -> float:
    """Eased progress of an action on its half-open span ``[start, end)``: 0 before, 1 from its last frame on."""
    if f < a["start"]:
        return 0.0
    return D.ease_in_out(min(1.0, (f - a["start"]) / max(1, a["end"] - 1 - a["start"])))


def _progress(a: dict, f: int) -> float:
    """A path's progress: a march (slow start, cruise, halt; map law 2) for routes and markers, the ease for the rest."""
    if a.get("stands"):
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
    tgt = tgt or (cur["lon"], cur["lat"])
    return {"lon": cur["lon"] + (tgt[0] - cur["lon"]) * u, "lat": cur["lat"] + (tgt[1] - cur["lat"]) * u,
            "span_km": math.exp(math.log(cur["span_km"]) + (math.log(span) - math.log(cur["span_km"])) * u)}


def camera(p: dict, f: int) -> dict:
    """The view at frame ``f``: the first view, a restrained drift, and every camera move whose event has started (a zoom
    eases to its place and width; push, pull, route_pan, fly_to and scale answer their action; a dense map only zooms)."""
    cur = dict(p["view0"])
    n = max(1, p["frames"] - 1)
    cur["span_km"] *= 1.0 - p.get("drift", DRIFT) * D.ease_in_out(f / n)
    for a in p["actions"]:
        cam = a.get("camera", "zoom" if a["kind"] == "zoom" else "hold")
        if cam == "hold" or f < a["start"] or (p.get("dense") and cam != "zoom"):
            continue
        u = _u(a, f)
        if cam == "zoom":
            span = float(a["value"]) if a.get("value") else cur["span_km"] / 3.0
            cur = _lerp_view(cur, a["to"] or a["from"], span, u)
        elif cam in ("push", "pull"):
            k = CAM_PUSH if cam == "push" else 1.0 / CAM_PUSH
            cur = _lerp_view(cur, a["to"] or a["from"], cur["span_km"] * k, u)
        elif cam == "route_pan" and a.get("path"):
            cur = _lerp_view(cur, D.polyline_point(a["path"], _head(p, a, f)), cur["span_km"], min(1.0, 4 * u))
        elif cam == "fly_to":
            cur = _lerp_view(cur, a["to"] or a["from"], cur["span_km"], u)
        elif cam == "scale" and (a.get("path") or a["from"]):
            pts = a["path"] or [a["from"]] + ([a["to"]] if a["to"] else [])
            lons, lats = [q[0] for q in pts], [q[1] for q in pts]
            kx = geo.KM_PER_DEG * math.cos(math.radians(cur["lat"]))
            want = max(MIN_SPAN_KM, (max(lons) - min(lons)) * kx * 1.4, (max(lats) - min(lats)) * geo.KM_PER_DEG * 1.4 * 16 / 9)
            cur = _lerp_view(cur, ((min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2), want, u)
    return cur


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
            "paper": D.rgb("paper"), "card": pick("card", "kit_card"), "glow": pick("accent", "uncertain_amber")}


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


def draw(base: D.Canvas, p: dict, f: int, view: geo.View | None, look: dict | None = None) -> None:
    """Draw every started action of plan ``p`` at frame ``f`` on canvas ``base`` (output pixels). Each action is drawn on its
    own transparent layer and composited, so its alpha blends (PIL writes RGBA pixels as they are on an RGBA image)."""
    col = colours(look)
    ink, accent = (*col["ink"], 255), (*col["accent"], 255)
    px = (lambda ll: tuple(float(v) for v in view.to_px(*ll))) if view else None
    unit = base.h
    for a in p["actions"]:
        if f < a["start"]:
            continue
        c = D.Canvas(base.w, base.h, None, base.ss)
        c.face = base.face
        _draw_one(c, a, p, f, view, col, ink, accent, px, unit)
        base.im.alpha_composite(c.im)


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
        D.marker(c, "a", x, y, unit * 0.030)
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
    for part in pieces:
        if len(part) >= 2:
            c.line(part, ink, w * 1.7)
            c.line(part, colour, w, dash=(w * 2.2, w * 1.2) if k in ("front_line", "supply_line") else None)
    if k == "route_arrow" and u > 0.02 and len(pieces[0]) >= 2:
        part = pieces[0]
        D.arrow_head(c, part[-1], part[-2] if part[-2] != part[-1] else part[0], w * 2.6, accent, ink)
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


def _draw_one(c, a, p, f, view, col, ink, accent, px, unit) -> None:
    if True:
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
            for n in range(3):
                t = ((f - a["start"]) / 24.0 + n / 3.0) % 1.0
                c.circle(cx, cy, unit * (0.014 + 0.12 * t), outline=(*col["accent"], int(255 * (1 - t))), width=max(3.0, unit * 0.006))
            c.circle(cx, cy, unit * 0.013, fill=accent, outline=ink, width=max(2.0, unit * 0.003))
        elif k == "highlight":
            cx, cy = px(a["from"])
            r = float(a.get("value") or 120.0) / view.km_per_px
            c.circle(cx, cy, max(unit * 0.03, r), fill=(*col["glow"], int(90 * u)), outline=(*col["glow"], int(220 * u)),
                     width=max(2.0, unit * 0.004))
        elif k == "label":
            cx, cy = px(a["from"])
            text = a.get("label") or a.get("name") or a["from_id"]
            size = max(unit * 40 / 1080, 6.0)
            alpha = int(255 * min(1.0, (f - a["start"] + 1) / 6))
            c.text((cx + size * 0.35, cy - size * 0.35), text, size, (*col["ink"], alpha), anchor="lb",
                   stroke=max(1.0, size * 0.12), stroke_fill=(*col["paper"], alpha))
        elif k == "counter":
            v = float(a.get("value") or 0) * u
            text = f"{_fmt(v, a.get('value') or 0)} {a.get('unit') or ''}".strip()
            size = unit * (0.12 if p.get("card") else 0.07)
            x0, y0, _, _ = _box(p, c, "counter")
            w = c.text_width(text, size) + size
            if p.get("card"):     # centred on its point, its width taken from the final value so it does not jitter
                final = f"{_fmt(float(a.get('value') or 0), a.get('value') or 0)} {a.get('unit') or ''}".strip()
                w = c.text_width(final, size) + size
                x0, y0 = x0 - w / 2, y0 - size * 0.75
            c.rect(x0, y0, x0 + w, y0 + size * 1.5, fill=(*col["card"], 235), outline=ink, width=max(2.0, unit * 0.004), radius=size * 0.25)
            c.text((x0 + size / 2, y0 + size * 0.75), text, size, ink, anchor="lm")
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
        fine = min(v["span_km"] / width for v in views)
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
        self.image = plate.render_plate(self.view, ss=1, shaded_relief=shaded_relief, look=look)
        self.width, self.height = width, height

    def frame(self, v: dict, ss: int = 1) -> Image.Image:
        """The plate crop of view ``v`` at ``ss`` times the frame size (a supersampled canvas takes it as it is)."""
        fv = geo.View(v["lon"], v["lat"], v["span_km"], self.width, self.height)
        x0, y0 = self.view.to_px(*fv.to_lonlat(0, 0))
        x1, y1 = self.view.to_px(*fv.to_lonlat(fv.width, fv.height))
        return self.image.transform((self.width * ss, self.height * ss), Image.EXTENT,
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
