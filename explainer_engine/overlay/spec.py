"""The overlay layer's contract (v4.3 plan section 9.2, stage B5): a map shot's action plan, resolved to pixels, as the one JSON
a HyperFrames composition animates.

Python decides everything that is geometry or time (``maps/actions.py`` resolves the actions to frames and lon/lat; here the view
turns lon/lat into pixels and the spoken words into frames); the composition only animates what this file says. So the overlay is
a pure function of (shot, script, places, word spine, card) and the renderer (HyperFrames or the Python drawer) is replaceable.
"""
from __future__ import annotations

import math
import re

from explainer_engine.core.errors import ContractError
from explainer_engine.maps import actions as MA
from explainer_engine.maps import draw as D
from explainer_engine.maps import geo
from explainer_engine.maps.render import _nice_km

SCHEMA = "overlay_spec/1"
EASE = "power3.inOut"          # = draw.ease_in_out (cubic in-out), the easing of every map move (BP-23)
SUPPORTED = ("route_arrow", "front_line", "spread", "plume", "pulse", "highlight", "label", "counter")  # not zoom / split_compare
WORD = re.compile(r"[A-Za-z0-9']+")


def spine_from_scribe(scribe_words: list[dict], fps: int, offset_s: float = 0.0) -> list[dict]:
    """ElevenLabs Scribe word list (``{text, start, end, type}``, seconds in the line's own audio) -> the shot-relative spine
    ``[{word, start_frame}]`` that ``maps/actions.plan`` takes. A token that holds several words ("ocean-but") is shared out."""
    out: list[dict] = []
    for t in scribe_words:
        if t.get("type", "word") != "word":
            continue
        ws = WORD.findall(t.get("text", ""))
        a, b = float(t["start"]), float(t.get("end", t["start"]))
        for i, w in enumerate(ws):
            out.append({"word": w.lower(), "start_frame": int(round((a + (b - a) * i / len(ws) - offset_s) * fps))})
    return out


def _px(view: geo.View, ll: tuple[float, float]) -> list[float]:
    x, y = view.to_px(*ll)
    return [round(float(x), 2), round(float(y), 2)]


def _palette(look: dict | None) -> dict:
    col = MA.colours(look)
    return {k: "#%02X%02X%02X" % tuple(v) for k, v in col.items()}


def build(shot: dict, script: dict, places: dict, fps: int, *, card: tuple[int, int, int, int], frame: tuple[int, int] = (2560, 1440),
          spine: list[dict] | None = None, date_text: str | None = None, look: dict | None = None,
          hold_frames: int | None = None) -> dict:
    """The overlay spec of one map_action shot. ``card`` = (x, y, w, h) of the inset in the frame; every coordinate in the spec is
    relative to the card's top-left. Zoom and split_compare shots are refused: they move the camera or the plate, which Python
    owns (a moving camera would need one spec per frame)."""
    p = MA.plan(shot, script, places, fps, spine)
    bad = [a["kind"] for a in p["actions"] if a["kind"] not in SUPPORTED]
    if bad:
        raise ContractError(f"{p['shot_id']}: the overlay layer does not draw {sorted(set(bad))} (the camera and plate are Python's)")
    if p["card"]:
        raise ContractError(f"{p['shot_id']}: a card shot (no place) has no map to overlay")
    x, y, w, h = card
    v0 = p["view0"]
    view = geo.View(v0["lon"], v0["lat"], v0["span_km"], w, h)
    unit = float(frame[1])      # line widths and type are shares of the delivered frame, not of the small card (readable at 2K)
    items: list[dict] = []
    for i, a in enumerate(p["actions"]):
        k = a["kind"]
        it: dict = {"id": f"a{i}", "kind": k, "start": a["start"], "end": a["end"], "word": a["word"]}
        if k in ("route_arrow", "front_line"):
            pts = MA._arc(tuple(_px(view, a["from"])), tuple(_px(view, a["to"])), bend=0.12 if k == "route_arrow" else 0.0)
            it.update(path=[[round(px, 2), round(py, 2)] for px, py in pts], width=round(max(3.0, unit * (0.011 if k == "route_arrow" else 0.016)), 2))
        elif k in ("spread", "plume"):
            r_px = float(a.get("value") or 400.0) / view.km_per_px
            it.update(origin=_px(view, a["from"]), radius=round(r_px, 2),
                      shape=[[round(px, 4), round(py, 4)] for px, py in MA._blob(0.0, 0.0, 1.0, p["shot_id"] + k)],
                      blur=round(max(1.0, r_px * 0.10), 2))
            if k == "plume":
                it["target"] = _px(view, a["to"])
                it["blobs"] = [{"t": n / 8, "scale": round(0.6 * (0.35 + 0.65 * n / 8), 4),
                                "shape": [[round(px, 4), round(py, 4)] for px, py in MA._blob(0.0, 0.0, 1.0, f"{p['shot_id']}{k}{n}")]}
                               for n in range(9)]
        elif k == "pulse":
            it.update(at=_px(view, a["from"]), r0=round(unit * 0.01, 2), r1=round(unit * 0.09, 2), width=round(max(2.0, unit * 0.004), 2))
        elif k == "highlight":
            it.update(at=_px(view, a["from"]), radius=round(max(4.0, float(a.get("value") or 120.0) / view.km_per_px), 2),
                      width=round(max(2.0, unit * 0.004), 2))
        elif k == "label":
            size = max(unit * 40 / 1080, 6.0)
            it.update(at=_px(view, a["from"]), text=str(a.get("label") or a.get("name") or a["from_id"]), size=round(size, 2))
        elif k == "counter":
            it.update(value=float(a.get("value") or 0), unit=a.get("unit") or "", size=round(unit * 0.045, 2))
        items.append(it)
    km = _nice_km(view.span_km * 0.2)
    spec = {"schema": SCHEMA, "shot_id": p["shot_id"], "fps": fps, "frames": max(p["frames"], hold_frames or 0), "shot_frames": p["frames"], "word_basis": p["basis"],
            "frame": {"w": frame[0], "h": frame[1]}, "card": {"x": x, "y": y, "w": w, "h": h, "radius": round(unit * 0.03, 1)},
            "palette": _palette(look), "ease": EASE, "anim_frames": MA.ANIM_FRAMES,
            "date_chip": {"text": date_text, "start": 0} if date_text else None,
            "scale_bar": {"km": km, "px": round(km / view.km_per_px, 2), "label": f"{int(km):,} km"},
            "view": {"lon": v0["lon"], "lat": v0["lat"], "span_km": v0["span_km"]}, "items": items}
    return spec


def active_regions(spec: dict) -> list[dict]:
    """The pixel box (frame coordinates) each item can touch, for the timing check that looks at the rendered alpha."""
    cx, cy = spec["card"]["x"], spec["card"]["y"]
    out = []
    for it in spec["items"]:
        k = it["kind"]
        if k in ("route_arrow", "front_line"):
            xs, ys = [q[0] for q in it["path"]], [q[1] for q in it["path"]]
            pad = it["width"] * 4
            box = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
        elif k in ("spread", "plume"):
            pts = [it["origin"]] + ([it["target"]] if k == "plume" else [])
            r = it["radius"] * 1.4
            box = (min(q[0] for q in pts) - r, min(q[1] for q in pts) - r, max(q[0] for q in pts) + r, max(q[1] for q in pts) + r)
        elif k in ("highlight", "pulse"):
            r = it.get("radius") or it.get("r1")
            box = (it["at"][0] - r, it["at"][1] - r, it["at"][0] + r, it["at"][1] + r)
        elif k == "label":
            box = (it["at"][0], it["at"][1] - it["size"] * 1.6, it["at"][0] + it["size"] * len(it["text"]) * 0.75, it["at"][1] + it["size"] * 0.3)
        else:  # counter
            box = (spec["card"]["w"] * 0.05, spec["card"]["h"] * 0.78, spec["card"]["w"] * 0.05 + it["size"] * 10, spec["card"]["h"] * 0.78 + it["size"] * 1.5)
        out.append({"id": it["id"], "kind": k, "start": it["start"],
                    "box": [int(round(box[0] + cx)), int(round(box[1] + cy)), int(round(box[2] + cx)), int(round(box[3] + cy))]})
    return out
