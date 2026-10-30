"""The four map archetypes (1 flyover, 2 unit manoeuvre, 3 formation, 4 logistics) drawn as a pure function of (spec, frame).

The base is the vector plate (or a certified painted plate), the overlays are drawn over it at the frame the viewer sees: routes that
draw themselves on their spoken word, unit counters that march a terrain-following curve, labels, range rings, a date chip, a
scale bar on meso and micro views. Inactive terrain is dimmed (law 3). Archetype 1 is the 2D-vector camera over the plate: the
Blueprint's 3D relief fly-over needs a height model we do not have, so it is the documented ceiling (D-86) and the parallax
tableau (archetype 8) is its fallback.
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image

from explainer_engine.maps import camera as CAM
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo, paths, plate
from explainer_engine.maps.timeline import Event, Timeline, progress

ARCHETYPES = ("MAP_3D_TERRAIN_FLYOVER", "TACTICAL_UNIT_MANEUVER", "FORMATION_MICRO_MECHANICS", "LOGISTICS_TETHER_AND_ATTRITION")
CHANGE_OPS = ("show_route", "march", "show_unit", "show_label", "show_ring", "set_focus", "form", "supply_state", "snap", "strength")
OPS = CHANGE_OPS + ("date", "hide")
LABEL_PX_1080 = 40            # P-64: a label is at least 40 px at 1080p; scaled with the frame
HIGHLIGHT_FRAMES = 8          # the changed thing pulses this long before it moves (CRAFT-CART-02)
FADE_FRAMES = 6
FORMATIONS = ("scatter", "line", "column", "square", "wedge")
PROXY_MAX = 500               # render cost bound of one formation, not a craft rule
SUPPLY_STATES = ("blue", "amber", "red")
SUPPLY_TOKEN = {"blue": "support_blue", "amber": "uncertain_amber", "red": "false_red"}


def _ids(payload: dict, key: str) -> set[str]:
    return {x["id"] for x in payload.get(key, [])}


def validate_payload(spec: dict) -> list[dict]:
    """The structural findings of a map item: the shape the renderer needs (FAIL: it could not draw) and the route checks."""
    out: list[dict] = []
    p, iid = spec["payload"], spec["item_id"]

    def bad(where: str, detail: str) -> None:
        out.append({"rule": "CN-01", "severity": "FAIL", "where": f"{iid}.{where}", "detail": detail})

    cam = p.get("camera")
    if not cam or "start" not in cam:
        bad("camera", "a map item needs camera.start (lon, lat, span_km)")
    else:
        for k in ("lon", "lat", "span_km"):
            if k not in cam["start"]:
                bad("camera.start", f"missing {k}")
        for i, m in enumerate(cam.get("moves", [])):
            for k in ("from_word", "to_word", "lon", "lat", "span_km"):
                if k not in m:
                    bad(f"camera.moves[{i}]", f"missing {k}")
            if "from_word" in m and "to_word" in m and m["to_word"] <= m["from_word"]:
                bad(f"camera.moves[{i}]", "a move ends on a later word than it starts")
    if p.get("base", {"kind": "vector"}).get("kind") not in ("vector", "plate"):
        bad("base.kind", "vector or plate")
    routes, units, labels, rings = _ids(p, "routes"), _ids(p, "units"), _ids(p, "labels"), _ids(p, "rings")
    for r in p.get("routes", []):
        if len(r.get("waypoints", [])) < 2:
            bad(f"routes.{r.get('id')}", "a route has at least two waypoints")
    for u in p.get("units", []):
        if u.get("side") not in ("a", "b"):
            bad(f"units.{u.get('id')}", "side is a or b (the two faction tokens)")
        if u.get("route") is not None and u["route"] not in routes:
            bad(f"units.{u.get('id')}", f"route {u['route']!r} is not in routes")
    known = {"show_route": routes, "march": units, "show_unit": units, "show_label": labels, "show_ring": rings, "set_focus": rings,
             "hide": routes | units | labels | rings | {"formation", "supply"}, "form": {"formation"},
             "supply_state": {"supply"}, "snap": {"supply"}, "strength": {"supply"}, "date": {None}}
    for e in spec["events"]:
        if e["op"] not in OPS:
            bad(f"events.{e['id']}", f"op {e['op']!r} is not one of {sorted(OPS)}")
        elif e.get("target") not in known[e["op"]]:
            bad(f"events.{e['id']}", f"{e['op']} has no target {e.get('target')!r}")
        elif e["op"] == "form" and e.get("args", {}).get("kind") not in FORMATIONS:
            bad(f"events.{e['id']}", f"form kind is one of {FORMATIONS}")
        elif e["op"] == "supply_state" and e.get("args", {}).get("state") not in SUPPLY_STATES:
            bad(f"events.{e['id']}", f"supply state is one of {SUPPLY_STATES}")
        elif e["op"] == "date" and not e.get("args", {}).get("text"):
            bad(f"events.{e['id']}", "a date event carries args.text")
    if spec["archetype_id"] == "FORMATION_MICRO_MECHANICS":
        f = p.get("formation")
        if not f or not 1 <= f.get("count", 0) <= PROXY_MAX or f.get("side") not in ("a", "b"):
            bad("formation", f"formation needs side a or b and a count of 1..{PROXY_MAX}")
    if spec["archetype_id"] == "LOGISTICS_TETHER_AND_ATTRITION":
        s = p.get("supply")
        if not s or s.get("route") not in routes or not s.get("strength_max"):
            bad("supply", "supply needs a route of the routes and strength_max")
    return out


def route_findings(spec: dict) -> list[dict]:
    out = []
    for r in spec["payload"].get("routes", []):
        out += paths.validate(r, f"{spec['item_id']}.routes.{r['id']}")
    return out


def _view(spec: dict, tl: Timeline, clock, f: float) -> tuple[geo.View, CAM.State]:
    start, moves = CAM.from_spec(spec["payload"]["camera"], clock.frame_of)
    st = CAM.state_at(start, moves, f)
    return geo.View(st.lon, st.lat, st.span_km, spec["width"], spec["height"]), st


def _plate_base(spec: dict, view: geo.View, ss: int, base_dir) -> D.Canvas:
    """A painted plate as the base: the part of the plate the camera sees, resampled to the frame."""
    b = spec["payload"]["base"]
    src = Image.open(base_dir / b["ref"]).convert("RGB")
    pv = geo.View(b["view"]["lon"], b["view"]["lat"], b["view"]["span_km"], src.width, src.height)
    x0, y0 = pv.to_px(*view.to_lonlat(0, 0))
    x1, y1 = pv.to_px(*view.to_lonlat(view.width, view.height))
    c = D.Canvas(view.width, view.height, None, ss)
    c.replace(src.transform((view.width * ss, view.height * ss), Image.EXTENT, (float(x0), float(y0), float(x1), float(y1)),
                            Image.BICUBIC))
    return c


def _dim(c: D.Canvas, view: geo.View, focus: tuple[float, float, float] | None, amount: float) -> None:
    """Law 3: the terrain outside the active area is dimmed by ``amount`` towards the night colour, with a soft edge."""
    if focus is None or amount <= 0:
        return
    lon, lat, radius_km = focus
    w, h = c.im.size
    cx, cy = view.to_px(lon, lat)
    r_px = radius_km / view.km_per_px * c.ss
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.hypot(xx - float(cx) * c.ss, yy - float(cy) * c.ss)
    outside = D.smoothstep(r_px, r_px * 1.35 + 1.0, dist).astype(np.float32) * amount
    arr = np.asarray(c.im, dtype=np.float32)
    night = np.array([*D.rgb("night"), 255], dtype=np.float32)
    arr = arr * (1 - outside[..., None]) + night * outside[..., None]
    c.replace(Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), "RGBA"))


def _nice_km(target: float) -> float:
    base = 10 ** math.floor(math.log10(target))
    for m in (1, 2, 5, 10):
        if m * base >= target:
            return m * base
    return 10 * base


def _scale_bar(c: D.Canvas, view: geo.View, tier: str) -> None:
    if tier == "macro":
        return
    km = _nice_km(view.span_km * 0.18)
    length = km / view.km_per_px
    x0, y = c.w * 0.04, c.h * 0.94
    ink = (*D.rgb("ink"), 255)
    c.rect(x0 - c.h * 0.012, y - c.h * 0.05, x0 + length + c.h * 0.012, y + c.h * 0.02, fill=(*D.rgb("paper"), 230), radius=c.h * 0.01)
    c.line([(x0, y), (x0 + length, y)], ink, c.h * 0.004)
    for x in (x0, x0 + length):
        c.line([(x, y - c.h * 0.012), (x, y + c.h * 0.012)], ink, c.h * 0.004)
    c.text((x0 + length / 2, y - c.h * 0.016), f"{km:g} km", c.h * 0.03, ink, anchor="mb")


def _label(c: D.Canvas, x: float, y: float, text: str, alpha: float) -> None:
    size = max(LABEL_PX_1080 / 1080 * c.h, 6.0)
    a = int(255 * alpha)
    c.text((x + size * 0.35, y - size * 0.35), text, size, (*D.rgb("ink"), a), anchor="lb", stroke=max(1.0, size * 0.12),
           stroke_fill=(*D.rgb("paper"), a))


def _active_events(tl: Timeline, op: str, target: str, f: float) -> list[Event]:
    return sorted((e for e in tl.events if e.op == op and e.target == target and e.start <= f), key=lambda e: e.start)


def _pulse(c: D.Canvas, x: float, y: float, f: float, start: int) -> None:
    """The changed thing is highlighted before it moves: a ring that closes in on it in the last frames before the event."""
    lead = start - f
    if 0 < lead <= HIGHLIGHT_FRAMES:
        r = c.h * (0.015 + 0.03 * lead / HIGHLIGHT_FRAMES)
        c.circle(x, y, r, outline=(*D.rgb("answer_coral"), 255), width=max(2.0, c.h * 0.004))


def state(spec: dict, tl: Timeline, f: float) -> dict:
    """What is on screen at frame ``f`` as numbers (for the laws and the tests): visible labels, unit groups, route shares."""
    p = spec["payload"]
    vis_labels = [x["id"] for x in p.get("labels", []) if _active_events(tl, "show_label", x["id"], f)
                  and not _active_events(tl, "hide", x["id"], f)]
    groups = set()
    for u in p.get("units", []):
        if (_active_events(tl, "show_unit", u["id"], f) or _active_events(tl, "march", u["id"], f)) and not _active_events(tl, "hide", u["id"], f):
            groups.add(u.get("group", u["id"]))
    if spec["archetype_id"] == "FORMATION_MICRO_MECHANICS" and p.get("formation") and tl.of("form") and tl.of("form")[0].start <= f:
        groups.add("formation")
    routes = {r["id"]: (D.ease_in_out(progress(_active_events(tl, "show_route", r["id"], f)[-1], f)) if _active_events(tl, "show_route", r["id"], f) else 0.0)
              for r in p.get("routes", [])}
    return {"labels": vis_labels, "unit_groups": sorted(groups), "route_share": routes}


def _unit_position(spec: dict, u: dict, tl: Timeline, f: float, curves: dict) -> tuple[float, float] | None:
    marches = _active_events(tl, "march", u["id"], f)
    if marches:
        e = marches[-1]
        rid = e.args.get("route", u.get("route"))
        if rid in curves:
            r = next(x for x in spec["payload"]["routes"] if x["id"] == rid)
            curve = curves[rid]
            share = paths.march_progress(r, progress(e, f))
            return _along(curve, share)
    if u.get("at"):
        return tuple(u["at"])
    if u.get("route") in curves:
        return curves[u["route"]][0]
    return None


def _along(curve: list[tuple[float, float]], share: float) -> tuple[float, float]:
    lens = [geo.distance_km(a[0], a[1], b[0], b[1]) for a, b in zip(curve, curve[1:])]
    goal, run = sum(lens) * min(max(share, 0.0), 1.0), 0.0
    for (a, b), n in zip(zip(curve, curve[1:]), lens):
        if run + n >= goal and n > 0:
            t = (goal - run) / n
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        run += n
    return curve[-1]


def _layout(kind: str, n: int, spread_km: float, seed_key: str) -> np.ndarray:
    """``n`` proxy slots (east, north km) of a formation of about ``spread_km`` across; the same call gives the same slots."""
    rng = D.seeded("formation", seed_key, kind, n)
    if kind == "scatter":
        ang, rad = rng.uniform(0, 2 * math.pi, n), np.sqrt(rng.uniform(0, 1, n)) * spread_km * 0.9
        pts = np.stack([np.cos(ang) * rad, np.sin(ang) * rad], axis=1)
    elif kind == "line":
        pts = np.stack([np.linspace(-spread_km, spread_km, n), np.zeros(n)], axis=1)
    elif kind == "column":
        cols = max(1, int(round(math.sqrt(n / 6))))
        rows = math.ceil(n / cols)
        i = np.arange(n)
        pts = np.stack([(i % cols - (cols - 1) / 2) * spread_km * 0.12, -(i // cols - (rows - 1) / 2) * spread_km * 2 / max(rows, 1)], axis=1)
    elif kind == "square":
        side = max(1, math.ceil(math.sqrt(n)))
        i = np.arange(n)
        pts = np.stack([(i % side - (side - 1) / 2) * spread_km * 1.6 / side, (i // side - (side - 1) / 2) * spread_km * 1.6 / side], axis=1)
    else:  # wedge
        rows = max(1, math.ceil((-1 + math.sqrt(1 + 8 * n)) / 2))
        pts, k = [], 0
        for r in range(rows):
            for j in range(r + 1):
                if k < n:
                    pts.append(((j - r / 2) * spread_km * 1.4 / rows, -r * spread_km * 1.4 / rows + spread_km * 0.7))
                    k += 1
        pts = np.array(pts)
    order = np.lexsort((pts[:, 0], pts[:, 1]))   # a stable order, so slot i of one layout is near slot i of the next
    return pts[order]


def _formation_points(spec: dict, tl: Timeline, f: float) -> np.ndarray | None:
    """Proxy positions in km from the formation's centre: each proxy leaves its slot a little late and takes a slightly bowed way
    to the next one (a flocking look that is still a pure function of the frame)."""
    form = spec["payload"]["formation"]
    n, spread = form["count"], form.get("spread_km", 1.0)
    forms = tl.of("form")
    kinds = [(form.get("start", "scatter"), -10 ** 9, 1)] + [(e.args["kind"], e.start, e.frames) for e in forms]
    cur = _layout(kinds[0][0], n, spread, spec["item_id"])
    rng = D.seeded("delay", spec["item_id"], n)
    delay = rng.uniform(0.0, 0.35, n)
    bow = rng.uniform(-0.25, 0.25, n)
    for kind, start, frames in kinds[1:]:
        if f <= start:
            break
        nxt = _layout(kind, n, spread, spec["item_id"])
        u = np.clip(((f - start) / frames - delay) / (1 - delay), 0.0, 1.0)
        u = np.where(u < 0.5, 4 * u ** 3, 1 - (-2 * u + 2) ** 3 / 2)[:, None]
        mid = (nxt - cur)
        perp = np.stack([-mid[:, 1], mid[:, 0]], axis=1) * bow[:, None] * (u * (1 - u) * 4)
        cur = cur + mid * u + perp
    return cur


def _draw_supply(c: D.Canvas, spec: dict, tl: Timeline, f: float, view: geo.View, curves: dict) -> None:
    s = spec["payload"]["supply"]
    curve = curves[s["route"]]
    pts = [(float(x), float(y)) for x, y in zip(*view.to_px([p[0] for p in curve], [p[1] for p in curve]))]
    state_ev = sorted(tl.of("supply_state"), key=lambda e: e.start)
    colour = D.rgb(SUPPLY_TOKEN["blue"])
    prev = SUPPLY_TOKEN["blue"]
    for e in state_ev:
        if e.start > f:
            break
        tok = SUPPLY_TOKEN[e.args["state"]]
        colour = D.blend(D.rgb(prev), D.rgb(tok), D.ease_in_out(progress(e, f)))
        prev = tok if progress(e, f) >= 1 else prev
    snaps = [e for e in tl.of("snap") if e.start <= f]
    ink, w = (*D.rgb("ink"), 255), max(3.0, c.h * 0.012)
    if snaps:
        e = snaps[-1]
        at = e.args.get("at", 0.5)
        gap = D.ease_in_out(progress(e, f)) * c.h * 0.03
        left, right = D.polyline_prefix(pts, at), list(reversed(D.polyline_prefix(list(reversed(pts)), 1 - at)))
        for seg, sign in ((left, -1), (right, 1)):
            if len(seg) >= 2:
                seg = list(seg)
                if sign < 0:
                    seg[-1] = (seg[-1][0] - gap, seg[-1][1])
                else:
                    seg[0] = (seg[0][0] + gap, seg[0][1])
                c.line(seg, ink, w * 1.7)
                c.line(seg, (*colour, 255), w, dash=(c.h * 0.02, c.h * 0.012))
    else:
        c.line(pts, ink, w * 1.7)
        c.line(pts, (*colour, 255), w, dash=(c.h * 0.02, c.h * 0.012))
    # the troop-strength bar, driven by the numbers of the strength events
    value = float(s.get("strength_start", s["strength_max"]))
    for e in sorted(tl.of("strength"), key=lambda e: e.start):
        if e.start <= f:
            value += (float(e.args["value"]) - value) * D.ease_in_out(progress(e, f))
    x0, y0, x1, y1 = c.w * 0.62, c.h * 0.9, c.w * 0.96, c.h * 0.96
    c.rect(x0, y0, x1, y1, fill=(*D.rgb("paper"), 235), outline=ink, width=max(2.0, c.h * 0.004), radius=c.h * 0.01)
    share = min(max(value / s["strength_max"], 0.0), 1.0)
    side = s.get("side", "a")
    c.rect(x0 + c.h * 0.006, y0 + c.h * 0.006, x0 + c.h * 0.006 + (x1 - x0 - c.h * 0.012) * share, y1 - c.h * 0.006, fill=(*D.faction(side), 255))
    c.text(((x0 + x1) / 2, (y0 + y1) / 2), f"{int(round(value)):,}", c.h * 0.04, ink, anchor="mm", stroke=max(1.0, c.h * 0.004), stroke_fill=(*D.rgb("paper"), 255))


def render_frame(spec: dict, tl: Timeline, clock, f: int, ss: int = D.SS, base_dir=None) -> Image.Image:
    p = spec["payload"]
    view, cam = _view(spec, tl, clock, f)
    base = p.get("base", {"kind": "vector"})
    c = _plate_base(spec, view, ss, base_dir) if base["kind"] == "plate" else plate.draw_base(view, ss=ss)
    # the active area (law 3): a focus ring or the payload's fixed focus
    focus = None
    if p.get("focus"):
        fo = p["focus"]
        focus = (fo["lon"], fo["lat"], fo["radius_km"])
        for e in sorted(tl.of("set_focus"), key=lambda e: e.start):
            ring = next(r for r in p["rings"] if r["id"] == e.target)
            u = D.ease_in_out(progress(e, f))
            if e.start <= f:
                focus = (focus[0] + (ring["lon"] - focus[0]) * u, focus[1] + (ring["lat"] - focus[1]) * u,
                         focus[2] + (ring["radius_km"] - focus[2]) * u)
    from explainer_engine.standards import sourced_rules as SR
    _dim(c, view, focus, SR.T("BP-124", "inactive_dim"))
    curves = {r["id"]: paths.spline(r["waypoints"]) for r in p.get("routes", [])}
    px = lambda lon, lat: tuple(float(v) for v in view.to_px(lon, lat))  # noqa: E731
    ink = (*D.rgb("ink"), 255)
    for r in p.get("routes", []):
        evs = _active_events(tl, "show_route", r["id"], f)
        if not evs or _active_events(tl, "hide", r["id"], f):
            for e in tl.by_target(r["id"], "show_route"):
                x, y = px(*r["waypoints"][0])
                _pulse(c, x, y, f, e.start)
            continue
        share = D.ease_in_out(progress(evs[-1], f))
        pts = [px(lon, lat) for lon, lat in curves[r["id"]]]
        part = D.polyline_prefix(pts, share)
        colour = (*(D.faction(r["side"]) if r.get("side") else D.rgb("mechanism_teal")), 255)
        w = max(3.0, c.h * 0.011)
        c.line(part, ink, w * 1.7)
        c.line(part, colour, w)
        if len(part) >= 2 and share > 0.02:
            D.arrow_head(c, part[-1], part[-2] if part[-2] != part[-1] else part[0], w * 2.6, colour, ink)
    for ring in p.get("rings", []):
        evs = _active_events(tl, "show_ring", ring["id"], f)
        if not evs:
            continue
        u = D.ease_in_out(progress(evs[-1], f))
        x, y = px(ring["lon"], ring["lat"])
        r_px = ring["radius_km"] / view.km_per_px * u
        c.circle(x, y, r_px, outline=(*D.rgb("mechanism_teal"), 255), width=max(3.0, c.h * 0.006))
    for u in p.get("units", []):
        if _active_events(tl, "hide", u["id"], f):
            continue
        shown = _active_events(tl, "show_unit", u["id"], f) or _active_events(tl, "march", u["id"], f)
        pos = _unit_position(spec, u, tl, f, curves)
        if pos is None:
            continue
        x, y = px(*pos)
        if not shown:
            for e in tl.by_target(u["id"], "show_unit") + tl.by_target(u["id"], "march"):
                _pulse(c, x, y, f, e.start)
            continue
        D.marker(c, u["side"], x, y, max(4.0, c.h * 0.022))
    if spec["archetype_id"] == "FORMATION_MICRO_MECHANICS":
        form = p["formation"]
        pts = _formation_points(spec, tl, f)
        if pts is not None and tl.of("form") and tl.of("form")[0].start - HIGHLIGHT_FRAMES <= f:
            cx, cy = px(form["center"][0], form["center"][1])
            r = max(2.0, c.h * form.get("proxy", 0.006))
            for ex, nk in pts:
                D.marker(c, form["side"], cx + float(ex) / view.km_per_px, cy - float(nk) / view.km_per_px, r)
    if spec["archetype_id"] == "LOGISTICS_TETHER_AND_ATTRITION":
        _draw_supply(c, spec, tl, f, view, curves)
    for lab in p.get("labels", []):
        evs = _active_events(tl, "show_label", lab["id"], f)
        if evs and not _active_events(tl, "hide", lab["id"], f):
            x, y = px(lab["lon"], lab["lat"])
            _label(c, x, y, lab["text"], min(1.0, (f - evs[-1].start + 1) / FADE_FRAMES))
        else:
            for e in tl.by_target(lab["id"], "show_label"):
                _pulse(c, *px(lab["lon"], lab["lat"]), f, e.start)
    dates = [e for e in tl.of("date") if e.start <= f]
    chip = dates[-1].args["text"] if dates else (p.get("date_chip", {}) or {}).get("text")
    if chip:
        size = c.h * 0.05
        w = c.text_width(chip, size)
        c.rect(c.w * 0.04, c.h * 0.04, c.w * 0.04 + w + size, c.h * 0.04 + size * 1.5, fill=(*D.rgb("paper"), 240), outline=ink,
               width=max(2.0, c.h * 0.004), radius=size * 0.3)
        c.text((c.w * 0.04 + size / 2, c.h * 0.04 + size * 0.75), chip, size, ink, anchor="lm")
    _scale_bar(c, view, CAM.tier_of(cam.span_km))
    img = c.image()
    if cam.pitch_deg > 0:
        bg = Image.new("RGBA", img.size, (*plate.colours()["sea"], 255))
        img = Image.alpha_composite(bg, CAM.tilt(img, cam.pitch_deg))
    return img.convert("RGB")
