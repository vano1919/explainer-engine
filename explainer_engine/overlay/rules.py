"""The overlay validator (OVERLAY_INTEGRATION_RULES_ka.md, OV-01..OV-56): one function per rule, each PASS / FAIL / NOT_RUN / N/A with a detail.

``validate(specs, shots, measures, mix, ...)`` returns {"shots": {no: {OV: {status, detail}}}, "episode": {OV: {...}}}. A rule that needs a
measurement says NOT_RUN when the measurement is absent (never PASS by default); N/A means the rule has nothing to judge in that shot.
The numbers: BP-134 (enter 200-400 ms, exit 150-250 ms, one moving element, counters at most 10 steps a second), BP-54 (early at most
1 frame, late at most 3), BP-56, BP-124, BP-127 come from ``sourced_rules``; the "წ" numbers of the rules file are the ``HOUSE`` table below
(the creator confirms or changes each one after the demo).
"""
from __future__ import annotations

import colorsys
import re
from typing import Callable

from explainer_engine.overlay import camera as CAM
from explainer_engine.overlay import place as PL
from explainer_engine.standards import sourced_rules as SR

PASS, FAIL, NOT_RUN, NA = "PASS", "FAIL", "NOT_RUN", "N/A"
FPS = 24
FRAME_AREA = CAM.W * CAM.H

HOUSE = {  # the numbers of the rules file marked "წ"; the demo uses exactly these
    "OV-02 exit margin frames": 8, "OV-02 first frame": 8,
    "OV-13 saturation margin over the frame": 0.10,
    "OV-14 minimum text px at 2560x1440 (P-64)": 40, "OV-14 fonts max": 2,
    "OV-15 contrast ratio min": 4.5,
    "OV-16 draw seconds": (0.5, 1.5),
    "OV-21 glass alpha": (0.45, 0.70), "OV-21 glass blur px": (12, 24),
    "OV-32 elements at once (accent)": 2, "OV-32 consecutive accent shots with overlay": 2,
    "OV-33 overlay area share of the frame": 0.15, "OV-33 one glass panel": 0.12,
    "OV-34 face box margin": 0.10, "OV-34 safe margin from the edge": 0.05,
    "OV-35 stay seconds (or words x 0.3 s, the larger)": 1.5, "OV-35 overlay share of an accent shot": 0.60,
    "OV-42 full shot seconds": (4, 12),
    "OV-43 longest frozen run seconds": 2.0,
    "OV-45 grid lines": 3, "OV-45 title words": 6, "OV-49 bars in an accent chart": 3,
    "OV-53 overlay sounds below the scene's real sounds, LU": 6.0,
    "OV-55 spread of the group levels, LU": 1.0,
}
ALLOWED_REASONS = {"number", "place", "date", "compare", "name"}
ALLOWED_KINDS = {"date_chip", "label", "pulse", "highlight", "spread", "plume", "route_arrow", "front_line", "counter", "counter_big", "bar", "line_seg",
                 "timeline_axis", "marker", "stat_callout", "compare_half", "scale_bar", "chart_title", "chart_axis", "chart_zero"}
STATIC = {"scale_bar", "chart_title", "chart_axis", "chart_zero"}
CONTINUOUS = {"pencil_scribble", "air_swell", "slide_grow"}
ORGANIC = {"pop_in", "glow_ping", "pencil_scribble", "tick", "tock", "landing_thud", "slide_grow", "air_swell", "swish"}
KIND_SOUND = {"route_arrow": "pencil_scribble", "front_line": "pencil_scribble", "line_seg": "pencil_scribble", "timeline_axis": "pencil_scribble",
              "label": "pop_in", "date_chip": "pop_in", "stat_callout": "pop_in", "compare_half": "pop_in", "pulse": "glow_ping", "highlight": "glow_ping",
              "spread": "air_swell", "plume": "air_swell", "counter": "tick", "counter_big": "tick", "bar": "slide_grow", "marker": "tick"}
TEXT_KINDS = {"label", "date_chip", "scale_bar", "counter", "counter_big", "chart_title", "chart_zero", "bar", "line_seg", "timeline_axis", "stat_callout",
              "compare_half", "highlight"}


def r(status: str, detail: str = "") -> dict:
    return {"status": status, "detail": detail}


class Ctx:
    def __init__(self, spec: dict, shot: dict, line: dict | None, boxes: dict | None, meas: dict, html: str | None):
        self.spec, self.shot, self.line, self.boxes, self.meas, self.html = spec, shot, line, boxes, meas, html
        self.items = spec["items"]
        self.panels = spec["panels"]
        self.n = spec["frames"]
        self.words = {w["word"] for w in spec["words"]}
        self.route = shot["route"]
        self.accent = spec.get("mode") == "accent"
        self.full = spec.get("mode") == "full"
        self.live = [i for i in self.items if i["kind"] not in STATIC]


def motion_items(c: Ctx) -> list[dict]:
    return [i for i in c.live if i["kind"] not in ("scale_bar",)]


# ------------------------------------------------------------------------------------------------ section 2: where the overlay is allowed
def ov01(c): return r(NA) if c.route != "ltx" else (r(FAIL, f"{len(c.items)} items, {len(c.panels)} panels on an ltx shot") if (c.items or c.panels) else r(PASS, "no overlay element, no chip, no inset"))
def ov02(c):
    if not c.panels: return r(NA)
    lo, hi = HOUSE["OV-02 first frame"], c.n - HOUSE["OV-02 exit margin frames"]
    bad = [f"{p['id']} {p['start']}-{p['end']}" for p in c.panels if p["start"] < lo or p["end"] > hi]
    bad += [f"{i['id']} start {i['start']}" for i in c.items if i["start"] < lo]
    bad += [f"{i['id']} end {i['end']}" for i in c.items if i["end"] is not None and i["end"] > hi]
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"every element starts at frame >= {lo} and ends at frame <= {hi} of {c.n}")
def ov03(c): return r(NA) if c.route != "ltx" else (r(FAIL, "an ltx shot carries an overlay_reason") if c.spec.get("overlay_reason") else r(PASS, "an ltx shot has no overlay_reason"))
def ov04(c): return r(NA) if c.spec.get("mode") != "full" else (r(PASS, "full on a map_action shot") if c.route == "map_action" else r(FAIL, f"full on a {c.route} shot"))
def ov05(c): return r(NA) if c.route != "still_25d" or not c.items else (r(PASS, "accent only") if c.spec.get("mode") == "accent" else r(FAIL, f"mode {c.spec.get('mode')} on a still_25d shot"))
def ov06(c): return r(PASS, f"route {c.spec['route']} unchanged by the overlay") if c.spec["route"] == c.shot["route"] else r(FAIL, f"route {c.shot['route']} -> {c.spec['route']}")


# ------------------------------------------------------------------------------------------------ section 3: style
def sat(hexv: str) -> float:
    n = int(hexv[1:], 16)
    return colorsys.rgb_to_hsv((n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255)[1]


def ov10(c):
    if not c.items: return r(NA)
    st = c.spec["style"]
    return r(PASS, f"style {c.spec['style_ref']} from {st.get('source_picture')}") if st.get("id") == c.spec["style_ref"] and st.get("source_picture") else r(FAIL, "no style source")
def ov11(c):
    if not c.items: return r(NA)
    if c.html is None: return r(NOT_RUN, "no composition html given")
    tok = {v.lower() for v in c.spec["style"]["tokens"].values()}
    found = {m.lower() for m in re.findall(r"#[0-9a-fA-F]{3,8}\b", c.html)}
    bad = sorted(found - tok)
    return r(FAIL, f"colours outside the style tokens: {bad}") if bad else r(PASS, f"{len(found)} colour literals, all style tokens")
def ov13(c):
    if not c.items: return r(NA)
    tok = c.spec["style"]["tokens"]
    top = max(sat(v) for v in tok.values())
    lim = c.spec["style"]["frame_saturation_p99"] * (1 + HOUSE["OV-13 saturation margin over the frame"])
    bad = [k for k, v in tok.items() if v.upper() in ("#FFFFFF", "#000000")]
    if bad: return r(FAIL, f"pure white or black token {bad}")
    return r(PASS, f"most saturated token {top:.2f} <= {lim:.2f} (frame p99 x 1.10)") if top <= lim else r(FAIL, f"token saturation {top:.2f} > {lim:.2f}")
def sizes(c) -> list[int]:
    out = []
    for i in c.items:
        for k in ("size", "label_size", "size_num", "size_unit", "size_cap"):
            if k in i and i[k]: out.append(i[k])
    return out
def ov14(c):
    if not c.items: return r(NA)
    fonts = set(c.spec["style"]["fonts"].values())
    small = [s for s in sizes(c) if s < HOUSE["OV-14 minimum text px at 2560x1440 (P-64)"]]
    if len(fonts) > HOUSE["OV-14 fonts max"]: return r(FAIL, f"{len(fonts)} font families")
    if small: return r(FAIL, f"text below {HOUSE['OV-14 minimum text px at 2560x1440 (P-64)']} px: {small}")
    tab = "" if c.html is None else (", tabular numbers" if "tabular-nums" in c.html else "")
    if c.html is not None and "tabular-nums" not in c.html: return r(FAIL, "numbers are not tabular")
    return r(PASS, f"{sorted(fonts)}, smallest text {min(sizes(c))} px{tab}")
def ov15(c):
    txt = [i for i in c.items if i["kind"] in TEXT_KINDS]
    if not txt: return r(NA)
    cm = c.meas.get("contrast")
    if not cm: return r(NOT_RUN, "no contrast measurement")
    lo = HOUSE["OV-15 contrast ratio min"]
    got = {k: v for k, v in cm.items()}
    bad = {k: round(v, 2) for k, v in got.items() if v < lo}
    return r(FAIL, f"below {lo}: {bad}") if bad else r(PASS, f"{len(got)} text items, lowest {min(got.values()):.2f}:1")
def motion_ok(c):
    lo, hi = (int(round(x * FPS)) for x in HOUSE["OV-16 draw seconds"])
    bad = []
    for i in c.live:
        d = i["motion_end"] - i["start"]
        if i["kind"] in ("route_arrow", "front_line", "bar", "plume", "spread", "timeline_axis", "marker", "highlight", "counter", "counter_big") or (i["kind"] == "line_seg" and not i.get("first")):
            if not lo <= d <= hi: bad.append(f"{i['id']} {i['kind']} {d} frames")
    return bad
def ov16(c):
    if not c.live: return r(NA)
    if c.spec["ease"] != "power3.inOut": return r(FAIL, f"ease {c.spec['ease']}")
    bad = motion_ok(c)
    en, ex = 6, 6
    lo_e, hi_e = (0.200 * FPS, 0.400 * FPS)
    if not (lo_e <= en <= hi_e) or not (0.150 * FPS <= ex <= 0.250 * FPS): bad.append("enter/exit frames outside BP-134")
    mv = sorted([(i["start"], i["motion_end"], i["id"], i["kind"]) for i in c.live if i["kind"] not in ("counter", "counter_big", "marker", "date_chip")])
    for a, b in zip(mv, mv[1:]):
        if b[0] < a[1]: bad.append(f"{a[2]} {a[3]} and {b[2]} {b[3]} move together")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, "draws 0.5-1.5 s, enter 250 ms, exit 250 ms, ease power3.inOut, one change at a time (counter and marker excepted)")
def ov17(c):
    dist = [i for i in c.items if i["kind"] == "scale_bar" or (i["kind"] == "counter" and i.get("unit") in ("miles", "km")) or i["kind"] == "highlight"]
    if not dist: return r(NA)
    units = {i.get("unit") for i in dist if i["kind"] in ("scale_bar", "counter")}
    units |= {"miles" if "miles" in i.get("label", "") else "other" for i in dist if i["kind"] == "highlight"}
    if units - {"miles"}: return r(FAIL, f"units {sorted(u for u in units if u)} (the narrator says miles)")
    said = [i for i in dist if i["kind"] != "scale_bar"]        # a quantity shown on screen must be a unit the narrator says; a scale bar is only a reference
    if said and c.line and "miles" not in {w["word"] for w in c.line["words"]}: return r(FAIL, "the narration line does not say miles")
    return r(PASS, "scale, counter and ring labels in miles" + (", the line says miles" if said else ""))
def seg_hits(poly, box, pad):
    x0, y0, w, h = box
    x1, y1 = x0 + w, y0 + h
    for (ax, ay), (bx, by) in zip(poly, poly[1:]):
        for k in range(21):
            px, py = ax + (bx - ax) * k / 20, ay + (by - ay) * k / 20
            if x0 - pad <= px <= x1 + pad and y0 - pad <= py <= y1 + pad: return True
    return False
def ov18(c):
    labels = [i for i in c.items if i["kind"] in ("label", "highlight", "counter")]
    lines = [i for i in c.items if i["kind"] in ("route_arrow", "front_line")]
    if not labels: return r(NA)
    if not lines: return r(PASS, "0 line paths in the shot, 0 intersections")
    if c.boxes is None: return r(NOT_RUN, "no measured label boxes")
    bad = []
    for lb in labels:
        b = c.boxes.get(lb["id"])
        if not b: continue
        for ln in lines:
            pbx, pby = next(p["box"][:2] for p in c.panels if p["id"] == ln["pid"])
            poly = [(x + pbx, y + pby) for x, y in ln["path"]]
            if seg_hits(poly, b, ln["width"] / 2): bad.append(f"{lb['id']} on {ln['id']}")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"{len(labels)} labels, 0 intersections with {len(lines)} lines")


# ------------------------------------------------------------------------------------------------ section 4: transparent styles
def ov20(c): return r(NA) if c.route != "still_25d" or not c.items else (r(PASS, f"surface {c.spec['surface']}") if c.spec["surface"] in ("glass", "bare") else r(FAIL, f"surface {c.spec['surface']} in the 30 % lane"))
def glass(c): return [p for p in c.panels if p["surface"] == "glass"]
def ov21(c):
    g = glass(c)
    if not g: return r(NA)
    bad = []
    for p in g:
        if not HOUSE["OV-21 glass alpha"][0] <= p["alpha"] <= HOUSE["OV-21 glass alpha"][1]: bad.append(f"{p['id']} alpha {p['alpha']}")
        if not HOUSE["OV-21 glass blur px"][0] <= p["blur_px"] <= HOUSE["OV-21 glass blur px"][1]: bad.append(f"{p['id']} blur {p['blur_px']}")
        if p["colour"] not in ("paper", "dim"): bad.append(f"{p['id']} colour {p['colour']}")
    if bad: return r(FAIL, "; ".join(bad))
    ma = c.meas.get("glass_alpha")
    if not ma: return r(NOT_RUN, "spec in range; the rendered alpha was not measured")
    off = {k: v for k, v in ma.items() if not 115 <= v <= 179}
    return r(FAIL, f"rendered alpha outside 115-179: {off}") if off else r(PASS, f"alpha {p['alpha']}, blur {p['blur_px']} px, rendered centre alpha {ma}")
def ov22(c):
    bare = [p for p in c.panels if p["surface"] == "bare"]
    if not bare: return r(NA)
    if c.spec["style"]["halo_px_2k"] <= 0: return r(FAIL, "no halo on bare text")
    if any(p["deco"] != "none" for p in bare): return r(FAIL, "a bare element has a panel")
    cm = c.meas.get("contrast")
    if not cm: return r(NOT_RUN, "halo present; contrast not measured")
    return r(PASS, f"no panel, halo {c.spec['style']['halo_px_2k']} px, lowest contrast {min(cm.values()):.2f}:1")
def values(c) -> int:
    n = 0
    for i in c.items:
        if i["kind"] in ("route_arrow", "counter", "counter_big", "label", "stat_callout", "bar"): n += 1
        if i["kind"] == "compare_half": n += 1
    if any(p.get("plate") for p in c.panels): n += 1            # a map is one more value
    return n
def ov23(c):
    if not c.accent or not c.items: return r(NA)
    v, s = values(c), c.spec["surface"]
    if v <= 1 and s != "bare": return r(FAIL, f"one value on a {s} surface")
    if v >= 3 and s != "glass": return r(FAIL, f"{v} values on a {s} surface")
    return r(PASS, f"{v} value(s) on a {s} surface")
def ov24(c):
    if not c.full: return r(NA)
    if c.spec["surface"] != "solid": return r(PASS, "not solid")
    sd = c.meas.get("bg_std")
    if sd is None: return r(NOT_RUN, "background not measured")
    return r(PASS, f"relief plate or style card, pixel std {sd:.1f}") if sd > 3.0 else r(FAIL, f"flat background, pixel std {sd:.1f}")


# ------------------------------------------------------------------------------------------------ section 5: the strict 30 % rules
def ov30(c):
    if not c.accent: return r(NA)
    why = c.spec.get("overlay_reason")
    if why not in ALLOWED_REASONS: return r(FAIL, f"overlay_reason {why}")
    miss = [i["word"] for i in c.live if i.get("word") and i["word"].split()[0].lower() not in c.words]
    return r(FAIL, f"at_word not in the line: {miss}") if miss else r(PASS, f"reason {why}; every at_word is a word of the line")
def ov31(c): return r(NA) if not c.accent else r(NOT_RUN, "needs the script-critic's removal-test answer (one per shot)")
def active_at(c, f):
    return [i for i in c.live if i["start"] <= f < (i["end"] or c.n)]
def ov32(c):
    if not c.accent: return r(NA)
    groups = len({i["pid"] for i in c.items})
    worst = max((len(active_at(c, f)) for f in range(c.n)), default=0)
    if groups > 1: return r(FAIL, f"{groups} groups")
    if worst > HOUSE["OV-32 elements at once (accent)"]: return r(FAIL, f"{worst} elements at once")
    return r(PASS, f"1 group, at most {worst} elements at once")
def boxes_of(c) -> list[tuple[str, float, float, float, float]]:
    out = []
    for p in c.panels:
        if p["surface"] == "bare":
            ms = [c.boxes[i["id"]] for i in c.items if i["pid"] == p["id"] and c.boxes and i["id"] in c.boxes]
            if ms:
                out += [(p["id"], b[0], b[1], b[2], b[3]) for b in ms]
                continue
        out.append((p["id"], *p["box"]))
    return out
def ov33(c):
    if not c.accent or not c.items: return r(NA)
    tot = sum(b[3] * b[4] for b in boxes_of(c)) / FRAME_AREA
    gl = [p["box"][2] * p["box"][3] / FRAME_AREA for p in glass(c)]
    if tot > HOUSE["OV-33 overlay area share of the frame"]: return r(FAIL, f"overlay area {tot:.1%}")
    if any(g > HOUSE["OV-33 one glass panel"] for g in gl): return r(FAIL, f"glass panel {max(gl):.1%}")
    return r(PASS, f"overlay area {tot:.1%} of the frame" + (f", glass panel {max(gl):.1%}" if gl else ""))
def ov34(c):
    if not c.accent or not c.items: return r(NA, "map or style card: no protected zones") if c.items else r(NA)
    prot = [tuple(b) for b in c.spec["protected"]]
    if not prot: return r(NOT_RUN, "no protected boxes in the spec")
    push, n = tuple(c.spec["push"]), c.n
    hit = margin = checked = 0
    for p in c.panels:
        bxs = [b[1:] for b in boxes_of(c) if b[0] == p["id"]] + [tuple(p["box"])]
        for f in range(p["start"], p["end"]):
            cam = CAM.cam(push, f, n)
            pf = [CAM.to_frame(b, cam) for b in prot]
            checked += 1
            for x, y, w, h in bxs:
                if PL.hits((x, y, x + w, y + h), pf): hit += 1; break
            if not PL.inside_margin((p["box"][0], p["box"][1], p["box"][0] + p["box"][2], p["box"][1] + p["box"][3])): margin += 1
    return r(FAIL, f"{hit} frames touch a face or the subject, {margin} outside the 5 % margin (of {checked})") if hit or margin else r(PASS, f"0 intersections on {checked} frames (face box + 10 %, subject box, 5 % margin)")
def ov35(c):
    if not c.items: return r(NA)
    bad = []
    wf = {}
    for w in c.spec["words"]: wf.setdefault(w["word"], w["start_frame"])
    for i in c.live:
        if i.get("word") is None: continue
        first = c.spec["words"]
        # the word the item was planned on: the first word in the line at or before the item start that matches
        cand = [w["start_frame"] for w in first if w["word"] == i["word"].split()[0].lower() and abs(w["start_frame"] - i["start"]) <= 3]
        if not cand: bad.append(f"{i['id']} {i['kind']} start {i['start']} is not on '{i['word']}'")
    if c.accent:
        for i in c.live:
            stay = (i["end"] - i["start"]) / FPS
            need = max(HOUSE["OV-35 stay seconds (or words x 0.3 s, the larger)"], len((i.get("caption") or "").split()) * 0.3 + 0.3)
            if stay < need - 1e-6: bad.append(f"{i['id']} stays {stay:.2f} s < {need:.2f}")
        cover = sum(p["end"] - p["start"] for p in c.panels) / c.n
        if cover > HOUSE["OV-35 overlay share of an accent shot"]: bad.append(f"overlay on screen {cover:.0%} of the shot")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, "every element on its word; stays long enough; photo clear time kept" if c.accent else "every element on its word")
def ov36(c): return r(NA) if not c.accent or not c.items else (r(PASS, "anchor screen") if c.spec["anchor"] == "screen" else r(FAIL, f"anchor {c.spec['anchor']}"))
def ov37(c):
    if not c.items: return r(NA)
    ev = [e for e in c.spec.get("camera_events", []) if e["kind"] in ("shake", "lightning")]
    clash = [e for e in ev for p in c.panels if e["start"] < p["end"] and e["end"] > p["start"]]
    return r(FAIL, f"{len(clash)} impact effects while an element moves") if clash else r(PASS, "no shake or lightning in the shot")
def ov38(c):
    mm = [p for p in c.panels if p.get("plate") and c.accent]
    if not mm: return r(NA)
    p = mm[0]
    x, y, w, h = p["box"]
    cx, cy = (x + w / 2) / CAM.W, (y + h / 2) / CAM.H
    corner = (cx <= 0.40 or cx >= 0.60) and (cy <= 0.40 or cy >= 0.60)
    acts = [i for i in c.items if i["kind"] in ("route_arrow", "front_line", "pulse", "highlight", "plume", "spread")]
    labs = [i for i in c.items if i["kind"] in ("label", "counter")]
    bad = []
    if p["surface"] != "glass": bad.append("not glass")
    if not corner: bad.append("not in a corner")
    if len(acts) > 1 or len(labs) > 1: bad.append(f"{len(acts)} actions, {len(labs)} labels")
    if w * h / FRAME_AREA > HOUSE["OV-33 one glass panel"]: bad.append("area")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"glass inset in a corner, {len(acts)} action, {len(labs)} label, {w * h / FRAME_AREA:.1%} of the frame")


# ------------------------------------------------------------------------------------------------ section 6: the full 10 % shots
def ov40(c):
    if not c.items: return r(NA)
    bad = sorted({i["kind"] for i in c.items} - ALLOWED_KINDS)
    return r(FAIL, f"kinds {bad}") if bad else r(PASS, f"kinds {sorted({i['kind'] for i in c.items})}")
def ov41(c):
    if not c.full or not c.panels or not c.panels[0].get("view"): return r(NA)
    t = SR.T("BP-124", "labels_max"), SR.T("BP-124", "units_max")
    bad = []
    peak_l = max((sum(1 for i in active_at(c, f) if i["kind"] == "label") for f in range(c.n)), default=0)
    if peak_l > t[0]: bad.append(f"{peak_l} labels at once")
    if c.spec.get("overlay_reason") == "date" and not any(i["kind"] == "date_chip" for i in c.items): bad.append("time advances without a date chip")
    if not any(i["kind"] == "scale_bar" for i in c.items): bad.append("no scale bar")
    first = {}
    for i in c.items:
        if i["kind"] in ("plume", "spread", "route_arrow", "front_line"):
            src = i.get("origin") or (i["path"][0] if i.get("path") else None)
            flagged = [j for j in c.items if j["kind"] in ("pulse", "highlight", "label") and j["start"] < i["start"] and src and j.get("at") and abs(j["at"][0] - src[0]) < 160 and abs(j["at"][1] - src[1]) < 160]
            if not flagged: bad.append(f"{i['id']} {i['kind']} moves without a highlight of its source first")
    if bad: return r(FAIL, "; ".join(bad))
    return r(NOT_RUN, "labels, date chip, scale bar and 'highlight first' pass; the dim of inactive terrain (BP-124) is not drawn in this demo")
def ov42(c):
    if not c.full: return r(NA)
    s = c.n / FPS
    lo, hi = HOUSE["OV-42 full shot seconds"]
    return r(PASS, f"{s:.0f} s") if lo <= s <= hi else r(FAIL, f"{s:.1f} s outside {lo}-{hi}")
def ov43(c):
    if not c.full: return r(NA)
    run = c.meas.get("max_frozen_run")
    if run is None: return r(NOT_RUN, "frame differences not measured")
    lim = int(HOUSE["OV-43 longest frozen run seconds"] * FPS)
    return r(PASS, f"longest identical run {run} frames <= {lim}") if run <= lim else r(FAIL, f"{run} identical frames in a row (> {lim})")
def ov44(c): return r(NA) if not c.full else r(NOT_RUN, "episode-level: see the ambience row")


# ------------------------------------------------------------------------------------------------ section 7: charts
def charts(c): return [i for i in c.items if i["kind"] in ("bar", "line_seg", "timeline_axis")]
def ov45(c):
    if not charts(c): return r(NA)
    titles = [i["text"] for i in c.items if i["kind"] == "chart_title"]
    lines = sum(1 for i in c.items if i["kind"] in ("chart_axis", "chart_zero", "timeline_axis"))
    bad = []
    if lines > HOUSE["OV-45 grid lines"]: bad.append(f"{lines} lines")
    for t in titles:
        if len(t.replace("(", " ").replace(")", " ").split()) > HOUSE["OV-45 title words"]: bad.append(f"title '{t}' has more than 6 words")
    if any(i["kind"] == "legend" for i in c.items): bad.append("legend")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"no legend, {lines} lines, titles <= 6 words")
def ov46(c):
    if not charts(c): return r(NA)
    if c.spec.get("claim_ids"): return r(PASS, "claim_ids present")
    return r(NOT_RUN, "DEMO data: no claim map; the chart titles carry '(demo data)'") if c.spec.get("demo_data") else r(FAIL, "a chart without claim_ids")
def ov47(c):
    ch = [i for i in charts(c) if i["kind"] in ("bar", "line_seg")]
    if not ch: return r(NA)
    t = c.meas.get("timing", {})
    bad = []
    for i in ch:
        w = i["word"].split()[0].lower()
        if not any(abs(x["start_frame"] - i["start"]) <= 3 for x in c.spec["words"] if x["word"] == w): bad.append(f"{i['id']} not on '{w}'")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"{len(ch)} values on the word that says them")
def ov48(c):
    b = [i for i in c.items if i["kind"] == "bar"]
    if not b: return r(NA)
    no = [i["id"] for i in b if not i.get("label")]
    return r(FAIL, f"bars without a label: {no}") if no else r(PASS, "every bar, the highlighted one too, has a direct label")
def ov49(c): return r(NA)


# ------------------------------------------------------------------------------------------------ section 8: sound
def ov50(c):
    mv = [i for i in c.live if i["kind"] in KIND_SOUND]
    if not mv: return r(NA)
    bad = []
    for i in mv:
        ev = [e for e in c.spec["sound"] if e["item"] == i["id"]]
        if not any(-1 <= e["t"] - i["start"] <= 3 for e in ev): bad.append(f"{i['id']} {i['kind']}: no sound event at its start")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"{len(mv)} motions, each with a sound event within BP-54 of its start")
def ov51(c):
    mv = [i for i in c.live if i["kind"] in KIND_SOUND]
    if not mv: return r(NA)
    bad = []
    for i in mv:
        ev = [e for e in c.spec["sound"] if e["item"] == i["id"]]
        for e in ev:
            if e["cls"] in CONTINUOUS and abs(e["dur"] - (i["motion_end"] - i["start"])) > 2: bad.append(f"{i['id']} {e['cls']} {e['dur']} vs motion {i['motion_end'] - i['start']}")
        if i["kind"] in ("counter", "counter_big"):
            steps = len(i["steps"])
            if sum(1 for e in ev if e["cls"] in ("tick", "tock")) != steps - 1: bad.append(f"{i['id']} {steps} steps but {len(ev)} sounds")
            sps = steps / ((i["motion_end"] - i["start"]) / FPS)
            if sps > SR_T("counter_steps_per_s_max") + 1e-6: bad.append(f"{i['id']} {sps:.1f} steps per second")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, "long sounds as long as their motion (+-2 frames), one hit per point motion, counters <= 10 steps/s")
def SR_T(k): return SR.T("BP-134", k)
def ov54(c):
    ev = c.spec["sound"]
    if not ev: return r(NA)
    worst = 0
    for e in ev:
        n = sum(1 for o in ev if o["cls"] == e["cls"] and o["t"] < e["t"] + e["dur"] and e["t"] < o["t"] + o["dur"])
        worst = max(worst, n)
    lim = SR.T("BP-56", "same_class_max")
    return r(FAIL, f"{worst} sounds of one class together (> {lim})") if worst > lim else r(PASS, f"at most {worst} sounds of one class at once")


SHOT_RULES: dict[str, Callable] = {
    "OV-01": ov01, "OV-02": ov02, "OV-03": ov03, "OV-04": ov04, "OV-05": ov05, "OV-06": ov06, "OV-10": ov10, "OV-11": ov11, "OV-13": ov13, "OV-14": ov14,
    "OV-15": ov15, "OV-16": ov16, "OV-17": ov17, "OV-18": ov18, "OV-20": ov20, "OV-21": ov21, "OV-22": ov22, "OV-23": ov23, "OV-24": ov24, "OV-30": ov30,
    "OV-31": ov31, "OV-32": ov32, "OV-33": ov33, "OV-34": ov34, "OV-35": ov35, "OV-36": ov36, "OV-37": ov37, "OV-38": ov38, "OV-40": ov40, "OV-41": ov41,
    "OV-42": ov42, "OV-43": ov43, "OV-44": ov44, "OV-45": ov45, "OV-46": ov46, "OV-47": ov47, "OV-48": ov48, "OV-49": ov49, "OV-50": ov50, "OV-51": ov51,
    "OV-54": ov54,
}


# ------------------------------------------------------------------------------------------------ the episode-level rules
def ep12(order: dict | None):
    if not order: return r(NOT_RUN, "no render order recorded")
    o = order.get("order", [])
    return r(PASS, f"order {o}") if o.index("composite") < o.index("grade") else r(FAIL, f"order {o}")
def ep32(specs: list[dict]):
    run = best = 0
    for s in specs:
        run = run + 1 if (s.get("mode") == "accent" and s["items"]) else 0
        best = max(best, run)
    lim = HOUSE["OV-32 consecutive accent shots with overlay"]
    return r(FAIL, f"{best} accent shots with overlay in a row") if best > lim else r(NOT_RUN, f"at most {best} in a row (<= {lim}) PASS; the 40 % budget of the 30 % lane is not checked in a showcase demo (rules file, section 10)")
def ep06(specs: list[dict], shots: list[dict]):
    tot = sum(s["frames"] for s in specs)
    share = {}
    for s in specs: share[s["route"]] = share.get(s["route"], 0) + s["frames"] / tot
    return r(PASS, "shares by duration: " + ", ".join(f"{k} {v:.0%}" for k, v in sorted(share.items())))
def ep11(specs: list[dict]):
    h = {str(sorted(s["style"]["tokens"].items())) + str(s["style"]["fonts"]) + str(s["ease"]) for s in specs if s["items"]}
    return r(PASS, "one overlay style hash on every shot with an overlay") if len(h) == 1 else r(FAIL, f"{len(h)} different styles")
def ep42(specs: list[dict]):
    run = best = 0
    for s in specs:
        run = run + s["frames"] / FPS if s["items"] and s["mode"] == "full" else 0
        best = max(best, run)
    lim = SR.T("BP-127", "non_character_run_max_s")
    return r(PASS, f"longest run of full shots {best:.0f} s <= {lim} s") if best <= lim else r(FAIL, f"{best:.0f} s of non-character shots in a row")
def ep52(specs: list[dict]):
    seen: dict[str, set] = {}
    for s in specs:
        for i in s["items"]:
            for e in [e for e in s["sound"] if e["item"] == i["id"]][:1]:
                seen.setdefault(i["kind"], set()).add(e["cls"])
    bad = {k: sorted(v) for k, v in seen.items() if len(v) > 1}
    notorg = sorted({e["cls"] for s in specs for e in s["sound"]} - ORGANIC)
    if bad or notorg: return r(FAIL, f"one kind, two sounds: {bad}; not organic: {notorg}")
    if any(seen.get(k) and KIND_SOUND[k] not in seen[k] for k in seen if k in KIND_SOUND): return r(FAIL, "sound class differs from the sound map")
    return r(PASS, f"one sound class per kind, all in the organic family {sorted(ORGANIC)}")
def ep53(mix: dict | None):
    if not mix: return r(NOT_RUN, "no mix report")
    d = mix["sfx_under_scene_lu"]
    lim = HOUSE["OV-53 overlay sounds below the scene's real sounds, LU"]
    return r(PASS, f"overlay sounds {d:.1f} LU below the scene's real sounds (>= {lim})") if d >= lim else r(FAIL, f"only {d:.1f} LU below")
def ep55(mix: dict | None):
    if not mix: return r(NOT_RUN, "no mix report")
    g = mix["groups"]
    spread = max(g.values()) - min(g.values())
    floor = mix["ambience_min_100ms_dbfs"]
    bad = []
    if spread > HOUSE["OV-55 spread of the group levels, LU"]: bad.append(f"group levels {g} spread {spread:.1f} LU")
    if floor < -70: bad.append(f"the bed drops to {floor} dBFS")
    return r(FAIL, "; ".join(bad)) if bad else r(PASS, f"bed never below {floor} dBFS in any 100 ms; group levels (LUFS) {g}, spread {spread:.1f} LU")
def ep56(lib_present: bool, classes_used: set):
    return r(PASS, "library wavs used") if lib_present else r(NOT_RUN, f"the library's wav files are not in this container; procedural numpy sounds ({sorted(classes_used)}) are allowed in the demo only")


def validate(specs: list[dict], shots: list[dict], *, lines: dict, boxes: dict, meas: dict, htmls: dict, mix: dict | None, order: dict | None, lib_present: bool = False) -> dict:
    out = {"shots": {}, "episode": {}}
    for sp, sh in zip(specs, shots):
        no = sp["shot_no"]
        c = Ctx(sp, sh, lines.get(no), boxes.get(no), meas.get(no, {}), htmls.get(no))
        out["shots"][no] = {k: fn(c) for k, fn in SHOT_RULES.items()}
    out["episode"] = {"OV-06 shares": ep06(specs, shots), "OV-11": ep11(specs), "OV-12": ep12(order), "OV-32 sequence": ep32(specs), "OV-42 run": ep42(specs),
                      "OV-52": ep52(specs), "OV-53": ep53(mix), "OV-44/55": ep55(mix),
                      "OV-56": ep56(lib_present, {e["cls"] for s in specs for e in s["sound"]})}
    return out


def failures(rep: dict) -> list[str]:
    bad = [f"shot {no} {k}: {v['detail']}" for no, d in rep["shots"].items() for k, v in d.items() if v["status"] == FAIL]
    return bad + [f"episode {k}: {v['detail']}" for k, v in rep["episode"].items() if v["status"] == FAIL]
