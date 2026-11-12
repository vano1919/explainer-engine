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

KINDS = ("route_arrow", "front_line", "spread", "plume", "pulse", "highlight", "label", "counter", "zoom", "split_compare")
PLACE_KINDS = {"route_arrow": ("from", "to"), "front_line": ("from", "to"), "plume": ("from", "to"), "spread": ("from",),
               "pulse": ("from",), "highlight": ("from",), "label": ("from",)}
ANIM_FRAMES = 18          # an action takes this long to arrive (0.75 s at 24 fps); a house default, not a sourced rule
LEAD_IN = 0.06            # estimated word times: the line starts this share into the shot ...
LEAD_OUT = 0.12           # ... and ends this share before its end
MIN_SPAN_KM = 300.0
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


def plan(shot: dict, script: dict, places: dict, fps: int, spine: list[dict] | None = None) -> dict:
    """Resolve a shot's actions to frames and lon/lat. Every ``at_word`` must be a word of the shot's line, in order."""
    sid = shot.get("shot_id", "?")
    frames = max(fps, int(round(float(shot.get("target_duration_seconds") or 0) * fps)))
    acts = shot.get("actions") or []
    if not acts:
        raise ContractError(f"{sid}: a map_action shot needs actions (RT-03)")
    words = shot_words(shot, script)
    starts, basis = word_frames(words, frames, spine)
    cursor, out = 0, []
    for a in acts:
        kind = a.get("kind")
        if kind not in KINDS:
            raise ContractError(f"{sid}: unknown action kind {kind!r}")
        want = _words(a.get("at_word", ""))
        if not want:
            raise ContractError(f"{sid}: {kind} has no at_word")
        hit = next((i for i in range(cursor, len(words)) if words[i:i + len(want)] == want), None)
        if hit is None:
            raise ContractError(f"{sid}: {kind} lands on {a.get('at_word')!r}, which is not in the shot's line after word "
                                f"{cursor} (the action must be tied to a spoken word, Q6)")
        cursor = hit
        need = PLACE_KINDS.get(kind, ())
        for k in need:
            if not a.get(k):
                raise ContractError(f"{sid}: {kind} needs {k!r}")
        f0 = starts[hit]
        out.append({"kind": kind, "start": f0, "end": min(frames - 1, f0 + ANIM_FRAMES), "word": a.get("at_word"),
                    "from": _place(places, a.get("from"), sid, kind), "to": _place(places, a.get("to"), sid, kind),
                    "from_id": a.get("from"), "to_id": a.get("to"),
                    "name": (places.get(a.get("from")) or {}).get("name") if a.get("from") else None,
                    "value": a.get("value"), "unit": a.get("unit", ""), "label": a.get("label")})
    card = not any(a["from"] or a["to"] for a in out)
    return {"shot_id": sid, "frames": frames, "fps": fps, "basis": basis, "card": card, "actions": out,
            "view0": None if card else _first_view(shot, out)}


def _first_view(shot: dict, acts: list[dict]) -> dict:
    mv = shot.get("map_view")
    if mv:
        return {"lon": float(mv["lon"]), "lat": float(mv["lat"]), "span_km": float(mv["span_km"])}
    pts = [p for a in acts if a["kind"] != "zoom" for p in (a["from"], a["to"]) if p]
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
    if f < a["start"]:
        return 0.0
    return D.ease_in_out(min(1.0, (f - a["start"]) / max(1, a["end"] - a["start"])))


def camera(p: dict, f: int) -> dict:
    """The view at frame ``f``: the first view, eased by every zoom that has started (log-eased width)."""
    cur = dict(p["view0"])
    for a in p["actions"]:
        if a["kind"] != "zoom" or f < a["start"]:
            continue
        tgt = a["to"] or a["from"] or (cur["lon"], cur["lat"])
        span = float(a["value"]) if a.get("value") else cur["span_km"] / 3.0
        u = _u(a, f)
        cur = {"lon": cur["lon"] + (tgt[0] - cur["lon"]) * u, "lat": cur["lat"] + (tgt[1] - cur["lat"]) * u,
               "span_km": math.exp(math.log(cur["span_km"]) + (math.log(span) - math.log(cur["span_km"])) * u)}
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


def _fmt(v: float) -> str:
    return f"{int(round(v)):,}" if abs(v) >= 1 else f"{v:.2f}"


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


def _draw_one(c, a, p, f, view, col, ink, accent, px, unit) -> None:
    if True:
        u = _u(a, f)
        k = a["kind"]
        if k in ("route_arrow", "front_line"):
            pts = [px(a["from"]), px(a["to"])]
            path = _arc(*pts, bend=0.12 if k == "route_arrow" else 0.0)
            part = D.polyline_prefix(path, u)
            w = max(3.0, unit * (0.011 if k == "route_arrow" else 0.016))
            if len(part) >= 2:
                c.line(part, ink, w * 1.7)
                c.line(part, accent, w, dash=(w * 2.2, w * 1.2) if k == "front_line" else None)
                if k == "route_arrow" and u > 0.02:
                    D.arrow_head(c, part[-1], part[-2] if part[-2] != part[-1] else part[0], w * 2.6, accent, ink)
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
                c.circle(cx, cy, unit * (0.01 + 0.08 * t), outline=(*col["accent"], int(255 * (1 - t))), width=max(2.0, unit * 0.004))
            c.circle(cx, cy, unit * 0.008, fill=accent)
        elif k == "highlight":
            cx, cy = px(a["from"])
            r = float(a.get("value") or 120.0) / view.km_per_px
            c.circle(cx, cy, max(4.0, r), fill=(*col["glow"], int(90 * u)), outline=(*col["glow"], int(220 * u)),
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
            text = f"{_fmt(v)} {a.get('unit') or ''}".strip()
            size = unit * 0.07
            x0, y0 = c.w * 0.05, c.h * 0.78
            w = c.text_width(text, size) + size
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
