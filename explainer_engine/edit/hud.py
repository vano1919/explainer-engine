"""The HUD and graph archetypes of the visual compensator: 5 ballistic range HUD, 7 split-screen speed race, 10 tech tree,
11 order-of-battle telemetry (a transparent overlay), 12 verdict matrix. Free, drawn by code, a pure function of (spec, frame).

Every number on screen is a number of the spec (the spec's author traces it to a claim, invariant 5); nothing here invents one.
Each change starts on a spoken word (word lock): the caller resolves the events with ``maps.timeline``.
"""

from __future__ import annotations

import math

from PIL import Image

from explainer_engine.maps import draw as D
from explainer_engine.maps.timeline import Timeline, progress

ARCHETYPES = ("BALLISTIC_RANGE_AND_ENERGY_HUD", "SPLIT_SCREEN_SPEED_RACE", "TECH_TREE_DEPENDENCY_GRAPH",
              "ORDER_OF_BATTLE_TELEMETRY_HUD", "MULTI_SCENARIO_VERDICT_MATRIX")
OPS = {
    "BALLISTIC_RANGE_AND_ENERGY_HUD": {"show_ring": "rings", "draw_arc": "arcs", "stamp": "stamps"},
    "SPLIT_SCREEN_SPEED_RACE": {"start": "race"},
    "TECH_TREE_DEPENDENCY_GRAPH": {"light": "nodes"},
    "ORDER_OF_BATTLE_TELEMETRY_HUD": {"set": "rows"},
    "MULTI_SCENARIO_VERDICT_MATRIX": {"grow": "scenarios"},
}
TONES = {"teal": "mechanism_teal", "blue": "support_blue", "coral": "answer_coral", "amber": "uncertain_amber", "grey": "grey_mid"}
TICK_FRAMES = 18


def _tone(name: str | None) -> tuple[int, int, int]:
    if name in ("a", "b"):
        return D.faction(name)
    return D.rgb(TONES.get(name or "teal", "mechanism_teal"))


def _targets(payload: dict, key: str) -> set[str]:
    if key == "race":
        return {"race"}
    return {x["id"] for x in payload.get(key, [])}


def validate_payload(spec: dict) -> list[dict]:
    out, p, iid, arch = [], spec["payload"], spec["item_id"], spec["archetype_id"]

    def bad(where: str, detail: str) -> None:
        out.append({"rule": "CN-01", "severity": "FAIL", "where": f"{iid}.{where}", "detail": detail})

    ops = OPS[arch]
    for e in spec["events"]:
        if e["op"] not in ops:
            bad(f"events.{e['id']}", f"op {e['op']!r} is not one of {sorted(ops)} for {arch}")
        elif e.get("target") not in _targets(p, ops[e["op"]]) and not (ops[e["op"]] == "race" and e.get("target") in (None, "race")):
            bad(f"events.{e['id']}", f"{e['op']} has no target {e.get('target')!r}")
        elif arch == "ORDER_OF_BATTLE_TELEMETRY_HUD" and "value" not in e.get("args", {}):
            bad(f"events.{e['id']}", "a set event carries args.value")
    if arch == "BALLISTIC_RANGE_AND_ENERGY_HUD":
        if not p.get("scale_m") or "origin" not in p:
            bad("payload", "scale_m (the metres across the frame) and origin are required")
    elif arch == "SPLIT_SCREEN_SPEED_RACE":
        for k in ("left", "right"):
            if not p.get(k, {}).get("seconds", 0) > 0:
                bad(f"payload.{k}", "a racer has a label and seconds > 0")
    elif arch == "TECH_TREE_DEPENDENCY_GRAPH":
        ids = _targets(p, "nodes")
        edges = p.get("edges", [])
        for e in edges:
            if e.get("from") not in ids or e.get("to") not in ids:
                bad("edges", f"edge {e.get('from')}->{e.get('to')} names a node that is not there (an edge has from and to)")
        if _cyclic(ids, edges):
            bad("edges", "a dependency graph has no cycle")
    elif arch == "ORDER_OF_BATTLE_TELEMETRY_HUD":
        if not p.get("rows"):
            bad("rows", "a telemetry overlay has rows")
    elif arch == "MULTI_SCENARIO_VERDICT_MATRIX":
        probs = [s.get("probability") for s in p.get("scenarios", [])]
        if any(not isinstance(x, (int, float)) for x in probs):
            bad("scenarios", "every scenario carries a numeric probability")
            probs = []
        total = sum(probs)
        if not p.get("scenarios") or total > 1.0005 or any(not 0 <= x <= 1 for x in probs):
            bad("scenarios", f"probabilities are 0..1 and add up to at most 1 (got {total:g})")
    return out


def _cyclic(ids: set[str], edges: list[dict]) -> bool:
    nxt: dict[str, list[str]] = {i: [] for i in ids}
    for e in edges:
        if e["from"] in nxt:
            nxt[e["from"]].append(e["to"])
    state: dict[str, int] = {}

    def visit(n: str) -> bool:
        if state.get(n) == 1:
            return True
        if state.get(n) == 2:
            return False
        state[n] = 1
        if any(m in nxt and visit(m) for m in nxt[n]):
            return True
        state[n] = 2
        return False

    return any(visit(n) for n in ids)


def _bg(c: D.Canvas) -> None:
    c.rect(0, 0, c.w, c.h, fill=(*D.rgb("night"), 255))


def _first(tl: Timeline, op: str, target: str, f: float):
    ev = [e for e in tl.events if e.op == op and e.target == target and e.start <= f]
    return ev[-1] if ev else None


def _ballistic(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink, paper, grey = spec["payload"], (*D.rgb("ink"), 255), (*D.rgb("paper"), 255), D.rgb("grey_mid")
    _bg(c)
    ox, oy = p["origin"][0] * c.w, p["origin"][1] * c.h
    per_m = c.w * (1 - p["origin"][0] - 0.04) / p["scale_m"]      # pixels per metre along the ground
    for k in range(1, 6):                                         # a quiet grid
        c.line([(0, c.h * k / 6), (c.w, c.h * k / 6)], (*grey, 40), max(1.0, c.h * 0.002))
    c.line([(c.w * 0.04, oy), (c.w * 0.97, oy)], paper, c.h * 0.006)
    D.marker(c, "a", ox, oy - c.h * 0.025, c.h * 0.02)
    for ring in p.get("rings", []):
        ev = _first(tl, "show_ring", ring["id"], f)
        if not ev:
            continue
        u = D.ease_in_out(progress(ev, f))
        r = ring["range_m"] * per_m * u
        box = [(ox + r * math.cos(a), oy - r * math.sin(a)) for a in [math.pi * k / 40 for k in range(0, 41)]]
        c.line(box, (*D.rgb("mechanism_teal"), 255), max(2.0, c.h * 0.005), dash=(c.h * 0.02, c.h * 0.012))
        c.line([(ox + r, oy - c.h * 0.015), (ox + r, oy + c.h * 0.015)], paper, c.h * 0.004)
    for arc in p.get("arcs", []):
        ev = _first(tl, "draw_arc", arc["id"], f)
        if not ev:
            continue
        u = D.ease_in_out(progress(ev, f))
        n = 60
        pts = [(ox + arc["range_m"] * per_m * t / n, oy - 4 * arc["peak_m"] * per_m * (t / n) * (1 - t / n)) for t in range(n + 1)]
        part = D.polyline_prefix(pts, u)
        col = (*_tone(arc.get("tone", "coral")), 255)
        c.line(part, ink, c.h * 0.012)
        c.line(part, col, c.h * 0.007)
        if u > 0.02 and len(part) >= 2:
            D.arrow_head(c, part[-1], part[-2], c.h * 0.03, col, ink)
    for st in p.get("stamps", []):
        ev = _first(tl, "stamp", st["id"], f)
        if not ev:
            continue
        u = D.ease_in_out(progress(ev, f))
        x = ox + st["range_m"] * per_m
        size = c.h * 0.06 * (1 + 0.35 * (1 - u))                  # it lands: a little large, then locks to size
        w = c.text_width(st["text"], size) + size
        y = oy - c.h * 0.18
        c.line([(x, y + size * 0.8), (x, oy)], paper, c.h * 0.004)
        c.rect(x - w / 2, y - size * 0.75, x + w / 2, y + size * 0.75, fill=paper, outline=ink, width=c.h * 0.005, radius=size * 0.2)
        c.text((x, y), st["text"], size, ink, anchor="mm")
        if u >= 1.0:   # the caliper click: two ticks close on the number
            c.line([(x - w / 2 - size * 0.3, y - size * 0.9), (x - w / 2 - size * 0.3, y + size * 0.9)], paper, c.h * 0.005)
            c.line([(x + w / 2 + size * 0.3, y - size * 0.9), (x + w / 2 + size * 0.3, y + size * 0.9)], paper, c.h * 0.005)


def _race(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink = spec["payload"], (*D.rgb("ink"), 255)
    _bg(c)
    ev = tl.of("start")
    u = progress(ev[0], f) if ev else 0.0
    longest = max(p["left"]["seconds"], p["right"]["seconds"])
    shown = u * longest * p.get("scale", 1.0)
    for i, (key, side) in enumerate((("left", p.get("side_left", "a")), ("right", p.get("side_right", "b")))):
        r = p[key]
        x0, x1 = i * c.w / 2 + c.w * 0.04, (i + 1) * c.w / 2 - c.w * 0.04
        t = min(shown, r["seconds"])
        done = shown >= r["seconds"] and u > 0
        c.text(((x0 + x1) / 2, c.h * 0.16), r["label"], c.h * 0.07, (*D.rgb("paper"), 255), anchor="mm")
        c.text(((x0 + x1) / 2, c.h * 0.42), f"{t:0.3f} s", c.h * 0.14, (*D.rgb("paper"), 255), anchor="mm")
        y = c.h * 0.7
        c.rect(x0, y - c.h * 0.03, x1, y + c.h * 0.03, fill=(*D.rgb("ink"), 255), outline=(*D.rgb("paper"), 255), width=c.h * 0.004, radius=c.h * 0.02)
        c.rect(x0 + c.h * 0.006, y - c.h * 0.024, x0 + c.h * 0.006 + (x1 - x0 - c.h * 0.012) * (t / r["seconds"]), y + c.h * 0.024,
               fill=(*D.faction(side), 255), radius=c.h * 0.015)
        D.marker(c, side, x0 + (x1 - x0) * (t / r["seconds"]), y - c.h * 0.075, c.h * 0.03)
        if done:
            c.text(((x0 + x1) / 2, c.h * 0.86), "DONE", c.h * 0.06, (*D.rgb("true_green"), 255), anchor="mm", stroke=c.h * 0.004, stroke_fill=ink)
    c.line([(c.w / 2, c.h * 0.05), (c.w / 2, c.h * 0.95)], (*D.rgb("grey_mid"), 255), c.h * 0.006)


def _tree(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink, paper = spec["payload"], (*D.rgb("ink"), 255), (*D.rgb("paper"), 255)
    _bg(c)
    nodes = {n["id"]: n for n in p["nodes"]}
    lit = {}
    for n in p["nodes"]:
        ev = _first(tl, "light", n["id"], f)
        lit[n["id"]] = D.ease_in_out(progress(ev, f)) if ev and n.get("state", "open") != "blocked" else 0.0
    grey = D.rgb("grey_mid")
    for e in p.get("edges", []):
        a, b = nodes[e["from"]], nodes[e["to"]]
        pa, pb = (a["x"] * c.w, a["y"] * c.h), (b["x"] * c.w, b["y"] * c.h)
        u = lit[e["to"]] * lit[e["from"]] if lit[e["from"]] > 0 else 0.0
        blocked = b.get("state") == "blocked"
        c.line([pa, pb], (*grey, 255), c.h * 0.006, dash=(c.h * 0.02, c.h * 0.015) if blocked else None)
        if u > 0:
            c.line(D.polyline_prefix([pa, pb], u), (*D.rgb("mechanism_teal"), 255), c.h * 0.011)
    r = c.h * 0.075
    for n in p["nodes"]:
        x, y = n["x"] * c.w, n["y"] * c.h
        u = lit[n["id"]]
        fill = D.blend(grey, D.rgb("mechanism_teal"), u)
        c.circle(x, y, r * (1 + 0.12 * math.sin(math.pi * u)), fill=(*fill, 255), outline=paper if u > 0 else (*grey, 255), width=c.h * 0.006)
        if n.get("state") == "blocked":
            d = r * 0.5
            c.line([(x - d, y - d), (x + d, y + d)], ink, c.h * 0.012)
            c.line([(x - d, y + d), (x + d, y - d)], ink, c.h * 0.012)
        c.text((x, y + r * 1.5), n["label"], c.h * 0.045, paper, anchor="mm")


def _telemetry(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink = spec["payload"], (*D.rgb("ink"), 255)
    rows = p["rows"]
    pw, ph = c.w * 0.3, c.h * (0.07 + 0.085 * len(rows))
    x0 = c.w * 0.03 if p.get("corner", "tl")[1] == "l" else c.w * 0.97 - pw
    y0 = c.h * 0.04 if p.get("corner", "tl")[0] == "t" else c.h * 0.96 - ph
    c.rect(x0, y0, x0 + pw, y0 + ph, fill=(*D.rgb("paper"), 225), outline=ink, width=c.h * 0.005, radius=c.h * 0.015)
    for i, row in enumerate(rows):
        value = float(row["value"])
        for e in sorted((e for e in tl.events if e.target == row["id"] and e.op == "set"), key=lambda e: e.start):
            if e.start <= f:
                u = D.ease_in_out(min(1.0, (f - e.start) / TICK_FRAMES))
                value += (float(e.args["value"]) - value) * u
        y = y0 + c.h * (0.07 + 0.085 * i)
        D.marker(c, row["side"], x0 + c.h * 0.05, y, c.h * 0.022)
        c.text((x0 + c.h * 0.1, y), row["label"], c.h * 0.04, ink, anchor="lm")
        c.text((x0 + pw - c.h * 0.03, y), f"{int(round(value)):,}{row.get('unit', '')}", c.h * 0.05, ink, anchor="rm")


def _verdict(c: D.Canvas, spec: dict, tl: Timeline, f: float) -> None:
    p, ink, paper = spec["payload"], (*D.rgb("ink"), 255), (*D.rgb("paper"), 255)
    _bg(c)
    n = len(p["scenarios"])
    top, row_h = c.h * 0.12, c.h * 0.76 / max(n, 1)
    x0, x1 = c.w * 0.3, c.w * 0.94
    for i, s in enumerate(p["scenarios"]):
        y = top + row_h * i + row_h / 2
        ev = _first(tl, "grow", s["id"], f)
        u = D.ease_in_out(progress(ev, f)) if ev else 0.0
        c.text((c.w * 0.04, y), s["label"], min(c.h * 0.055, row_h * 0.5), paper, anchor="lm")
        c.rect(x0, y - row_h * 0.3, x1, y + row_h * 0.3, fill=ink, outline=(*D.rgb("grey_mid"), 255), width=c.h * 0.003, radius=row_h * 0.12)
        if u > 0:
            c.rect(x0 + 2, y - row_h * 0.3 + 2, x0 + 2 + (x1 - x0 - 4) * s["probability"] * u, y + row_h * 0.3 - 2,
                   fill=(*_tone(s.get("tone")), 255), radius=row_h * 0.1)
            c.text((x0 + c.w * 0.02 + (x1 - x0) * s["probability"] * u, y), f"{round(100 * s['probability'] * u)} %",
                   min(c.h * 0.055, row_h * 0.45), paper, anchor="lm")


RENDERERS = {"BALLISTIC_RANGE_AND_ENERGY_HUD": _ballistic, "SPLIT_SCREEN_SPEED_RACE": _race, "TECH_TREE_DEPENDENCY_GRAPH": _tree,
             "ORDER_OF_BATTLE_TELEMETRY_HUD": _telemetry, "MULTI_SCENARIO_VERDICT_MATRIX": _verdict}


def render_frame(spec: dict, tl: Timeline, f: int, ss: int = D.SS) -> Image.Image:
    """RGB for every archetype but 11, whose frame is RGBA with a transparent background (the overlay of a shot)."""
    c = D.Canvas(spec["width"], spec["height"], None, ss)
    RENDERERS[spec["archetype_id"]](c, spec, tl, f)
    im = c.image()
    return im if spec["archetype_id"] == "ORDER_OF_BATTLE_TELEMETRY_HUD" else im.convert("RGB")
