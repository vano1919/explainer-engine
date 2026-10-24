"""AC-12..AC-13: a shot that returns to a setup already composed reuses that frame through a crop instead of composing (and
repainting) a new one. ვანო 2026-10-25 02:13 Tbilisi: "if the script cuts back to a view, do not generate it again; use the
old frame, even with a zoom or a slightly different crop, and animate it". The cartoons measured on 2026-10-25 return to an
earlier setup in about 20 % of shots (3312 shots, HF footage_2026-10-23).

A setup is the background, the camera angle and the cast in the frame. A shot of the same setup at the same or a tighter
size is a crop of the earlier frame when the crop enlarges it by at most ``ZOOM_MAX`` (relative to the render scale).
"""

from __future__ import annotations

from explainer_engine.scripting import layout as LY

ZOOM_MAX = 1.6          # AC-13: a crop never enlarges the composed frame more than this (the picture goes soft)


def setup_key(shot: dict) -> tuple:
    cast = tuple(sorted(it["asset"]["name"] for it in shot.get("items", []) if it.get("asset")))
    return (shot["background"], shot.get("angle", "eye"), cast)


def _crop(src: dict, dst: dict) -> tuple[list[float], float]:
    """The crop of the earlier frame that gives the tighter size, centred on the lead; and its zoom."""
    zoom = LY.LEAD_SHARE[dst["size"]] / LY.LEAD_SHARE[src["size"]] * float(dst.get("push", 1.0))   # push: a slight push-in
    lay = LY.solve(src)
    lead = next(i for i in lay["items"] if i["lead"])
    w = h = 1 / zoom
    cx = min(max(lead["cx"], w / 2), 1 - w / 2)
    top = LY.TOP.get(dst["size"], 0.1)
    y0 = min(max(lead["box"][1] - top * h, 0), 1 - h)
    return [round(cx - w / 2, 4), round(y0, 4), round(cx + w / 2, 4), round(y0 + h, 4)], zoom


def plan(shots: list[dict], render_scale: float = 1.0) -> list[dict]:
    """Per shot: ``{"id", "action": "compose"|"reuse", "from"?, "crop"?, "zoom"?}``. Teasers may point forward (a cold open
    shows a later moment): a shot with ``"teaser_of": <id>`` reuses that shot whatever its place."""
    by_id = {s["id"]: s for s in shots}
    seen: dict[tuple, list[dict]] = {}
    out = []
    for s in shots:
        if s.get("teaser_of"):
            src = by_id[s["teaser_of"]]
            crop, zoom = _crop(src, s) if LY.LEAD_SHARE[s["size"]] >= LY.LEAD_SHARE[src["size"]] else ([0, 0, 1, 1], 1.0)
            out.append({"id": s["id"], "action": "reuse", "from": src["id"], "crop": crop, "zoom": round(zoom, 2),
                        "ok": zoom / render_scale <= ZOOM_MAX})
            continue
        best = None
        for prev in seen.get(setup_key(s), []):
            if LY.LEAD_SHARE[s["size"]] < LY.LEAD_SHARE[prev["size"]]:
                continue                      # a wider view than the earlier frame holds nothing to crop from
            crop, zoom = _crop(prev, s)
            if zoom / render_scale <= ZOOM_MAX and (best is None or zoom < best["zoom"]):
                best = {"id": s["id"], "action": "reuse", "from": prev["id"], "crop": crop, "zoom": round(zoom, 2), "ok": True}
        out.append(best or {"id": s["id"], "action": "compose"})
        if not best:
            seen.setdefault(setup_key(s), []).append(s)
    return out


def check(planned: list[dict]) -> list[dict]:
    return [{"rule": "AC-13", "severity": "FAIL", "where": p["id"],
             "detail": f"crop of {p['from']} enlarges {p['zoom']}x: compose this shot, or render {p['from']} larger"}
            for p in planned if p["action"] == "reuse" and not p["ok"]]
