"""overlay_spec/2 (OVERLAY_INTEGRATION_RULES section 9): one shot's overlay as the JSON a HyperFrames composition animates.

Geometry, time and sound are decided here in Python; the composition only draws them. New against spec/1: modes (full / accent),
surfaces (solid / glass / bare), panels with a place chosen by ``place.choose``, the chart kinds, a sound event for every motion, the
style tokens, the protected boxes and the screen anchor. Every number that is not geometry is named below.
"""
from __future__ import annotations

from explainer_engine.core.errors import ContractError
from explainer_engine.maps import actions as MA
from explainer_engine.maps import geo
from explainer_engine.overlay import narration as NAR
from explainer_engine.overlay import place as PL

SCHEMA = "overlay_spec/2"
W, H, FPS = 2560, 1440, 24
LEAD_S = 0.6
KM_PER_MILE = 1.609344
EASE = "power3.inOut"
ENTER, EXIT = 6, 6          # frames: 250 ms in and out (BP-134: enter 200-400 ms, exit 150-250 ms)
EXIT_MARGIN = 8             # OV-02: every element is gone 8 frames before the cut
FIRST = 8                   # OV-02: nothing starts before frame 8
HOLD_S = 1.6                # an accent group stays this long after its last motion (OV-35: at least 1.5 s)
ANIM = 18                   # a drawing takes 0.75 s (OV-16: 0.5-1.5 s)
LONG = 36                   # plume, spread, counter, marker: 1.5 s
PULSE = 24
STEP = 3                    # a counter steps every 3 frames = 8 per second (BP-134: at most 10)
CHART = [340, 250, 1880, 940]   # the solid chart card of a full shot (frame pixels)
NICE_MILES = [10, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000]
PLACES = None


def places() -> dict:
    global PLACES
    if PLACES is None:
        from explainer_engine.overlay.demo_script import PLACES as P
        PLACES = P
    return PLACES


def ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_inv(y: float) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ease(mid) < y else (lo, mid)
    return (lo + hi) / 2


def fmt(v: float) -> str:
    return f"{int(round(v)):,}"


def snd(cls: str, t: int, dur: int, gain: float = 1.0) -> dict:
    return {"cls": cls, "t": int(t), "dur": int(dur), "gain": gain}


def nice_miles(target: float) -> int:
    return max([m for m in NICE_MILES if m <= target] or [NICE_MILES[0]])


def words_frames(line_words: list[dict]) -> list[dict]:
    return [{"word": w["word"], "start_frame": int(round((LEAD_S + w["start_s"]) * FPS)), "end_frame": int(round((LEAD_S + w["end_s"]) * FPS))}
            for w in line_words]


class Shot:
    def __init__(self, shot: dict, narr: dict | None, style: dict):
        self.shot, self.style = shot, style
        self.n = int(shot["dur"] * FPS)
        self.sp = words_frames(narr["words"]) if narr else []
        self.cur = 0
        self.panels: list[dict] = []
        self.items: list[dict] = []
        self.sounds: list[dict] = []

    # -- time
    def word(self, token: str) -> tuple[int, int]:
        toks = NAR.words_of(token)
        for i in range(self.cur, len(self.sp) - len(toks) + 1):
            if [w["word"] for w in self.sp[i:i + len(toks)]] == toks:
                self.cur = i
                return max(FIRST, self.sp[i]["start_frame"]), i
        raise ContractError(f"'{token}' is not a word of the line after word {self.cur}")

    def add(self, pid: str, kind: str, start: int, motion_end: int, sounds: list[dict], word: str | None, layer: str = "screen", **kw) -> dict:
        it = {"id": f"i{len(self.items)}", "pid": pid, "kind": kind, "start": int(start), "motion_end": int(motion_end), "end": None, "word": word,
              "layer": layer, "sound": sounds, **kw}
        self.items.append(it)
        self.sounds += [{**s, "item": it["id"]} for s in sounds]
        return it

    def panel(self, pid: str, box, surface: str, deco: str, view: dict | None = None, anchor: str = "screen", plate: bool = False) -> dict:
        st = self.style
        p = {"id": pid, "box": [int(v) for v in box], "surface": surface, "deco": deco, "radius": st["radius_px_2k"], "view": view, "anchor": anchor,
             "plate": plate, "alpha": 0.58 if surface == "glass" else (0.96 if deco == "card" else 0.0), "blur_px": 18 if surface == "glass" else 0,
             "colour": "paper", "start": None, "end": None}
        self.panels.append(p)
        return p

    def view(self, p: dict) -> geo.View:
        v = p["view"]
        return geo.View(v["lon"], v["lat"], v["span_km"], p["box"][2], p["box"][3])

    def px(self, p: dict, pid: str) -> list[float]:
        lon, lat, _n = places()[pid]
        x, y = self.view(p).to_px(lon, lat)
        return [round(float(x), 1), round(float(y), 1)]

    # -- map items
    def map_item(self, p: dict, it: dict) -> None:
        kind, view, unit = it["kind"], (self.view(p) if p["view"] else None), float(H)
        layer = "world" if p["anchor"] == "world" else "screen"
        if kind == "date_chip":
            s, _ = self.word(it["at"])
            self.add(p["id"], "date_chip", s, s + ENTER, [snd("pop_in", s, 8)], it["at"], layer="screen", text=it["text"], size=52, at=[70, 70])
        elif kind == "scale_bar":
            miles = nice_miles(view.span_km * 0.2 / KM_PER_MILE)
            self.add(p["id"], "scale_bar", FIRST, FIRST, [], None, layer=layer, px=round(miles * KM_PER_MILE / view.km_per_px, 1), label=f"{miles:,} miles",
                     unit="miles", size=42, at=[p["box"][2] - 120, p["box"][3] - 150])
        elif kind == "label":
            s, _ = self.word(it["at"])
            if "place" in it:
                at, text = self.px(p, it["place"]), places()[it["place"]][2]
            else:
                at, text = it["at_px"], it["text"]
            self.add(p["id"], "label", s, s + ENTER, [snd("pop_in", s, 8)], it["at"], layer=layer, text=text, at=at, size=it.get("size", 60))
        elif kind == "pulse":
            s, _ = self.word(it["at"])
            self.add(p["id"], "pulse", s, s + it.get("frames", PULSE), [snd("glow_ping", s, 14)], it["at"], layer=layer, at=self.px(p, it["place"]), r0=round(unit * 0.012, 1),
                     r1=round(unit * 0.09, 1), width=round(unit * 0.005, 1), frames=it.get("frames", PULSE))
        elif kind == "highlight":
            s, _ = self.word(it["at"])
            r = it["miles"] * KM_PER_MILE / view.km_per_px
            self.add(p["id"], "highlight", s, s + ANIM, [snd("glow_ping", s, 14)], it["at"], layer=layer, at=self.px(p, it["place"]), radius=round(r, 1),
                     width=round(unit * 0.005, 1), label=f"{it['miles']} miles", size=52)
        elif kind == "spread":
            s, _ = self.word(it["at"])
            r = it["miles"] * KM_PER_MILE / view.km_per_px
            self.add(p["id"], "spread", s, s + LONG, [snd("air_swell", s, LONG)], it["at"], layer=layer, origin=self.px(p, it["place"]), radius=round(r, 1),
                     shape=[[round(a, 4), round(b, 4)] for a, b in MA._blob(0.0, 0.0, 1.0, f"{self.shot['no']}spread")], blur=round(max(1.0, r * 0.10), 1))
        elif kind == "plume":
            s, _ = self.word(it["at"])
            r = it["miles"] * KM_PER_MILE / view.km_per_px
            src, dst = self.px(p, it["a"]), self.px(p, it["b"])
            blobs = [{"t": k / 8, "scale": round(0.6 * (0.35 + 0.65 * k / 8), 4),
                      "shape": [[round(x, 4), round(y, 4)] for x, y in MA._blob(0.0, 0.0, 1.0, f"{self.shot['no']}plume{k}")]} for k in range(9)]
            self.add(p["id"], "plume", s, s + LONG, [snd("air_swell", s, LONG)], it["at"], layer=layer, origin=src, target=dst, radius=round(r, 1),
                     blur=round(max(1.0, r * 0.10), 1), blobs=blobs)
        elif kind in ("route_arrow", "front_line"):
            s, _ = self.word(it["at"])
            a, b = self.px(p, it["a"]), self.px(p, it["b"])
            pts = MA._arc(tuple(a), tuple(b), bend=0.12 if kind == "route_arrow" else 0.0)
            w = round(max(4.0, unit * (0.010 if kind == "route_arrow" else 0.014)), 1)
            self.add(p["id"], kind, s, s + ANIM, [snd("pencil_scribble", s, ANIM), snd("tick", s + ANIM, 4)], it["at"], layer=layer,
                     path=[[round(x, 1), round(y, 1)] for x, y in pts], width=w)
        elif kind in ("counter", "counter_big"):
            s, _ = self.word(it["at"])
            big = kind == "counter_big"
            n = LONG // STEP
            steps = [[s + k * STEP, fmt(it["value"] * ease(k / n)) if k < n else fmt(it["value"])] for k in range(1, n + 1)]
            snds = [snd("tick" if k % 2 == 0 else "tock", f, 4, 0.7) for k, (f, _t) in enumerate(steps[:-1])] + [snd("landing_thud", steps[-1][0], 10, 0.8)]
            w, h = p["box"][2], p["box"][3]
            at = [round(w / 2, 1), round(h * 0.80, 1)] if big else [round(w * 0.045, 1), round(h * it.get("at_y", 0.90), 1)]
            self.add(p["id"], kind, s, s + LONG, snds, it["at"], layer="screen", steps=steps, unit=it["unit"], size=140 if big else 58, at=at, big=big)
        elif kind == "bar_chart":
            self.bar_chart(p, it)
        elif kind == "line_chart":
            self.line_chart(p, it)
        elif kind == "timeline":
            self.timeline(p, it)
        else:
            raise ContractError(f"unknown overlay kind {kind}")

    def bar_chart(self, p: dict, it: dict) -> None:
        w = p["box"][2]
        x0, x1, ybase, ytop = 240, w - 240, 700, 250
        slot = (x1 - x0) / len(it["series"])
        bw = slot * 0.46
        vmax = max(s["value"] for s in it["series"])
        self.add(p["id"], "chart_title", FIRST, FIRST, [], None, text=it["title"], at=[w / 2, 110], size=54, static=True)
        self.add(p["id"], "chart_axis", FIRST, FIRST, [], None, x0=x0 - 30, x1=x1 + 30, y=ybase, static=True)
        for k, s in enumerate(it["series"]):
            start, _ = self.word(s["at"])
            h = max(3.0, (ybase - ytop) * s["value"] / vmax)
            cx = x0 + slot * (k + 0.5)
            self.add(p["id"], "bar", start, start + ANIM, [snd("slide_grow", start, ANIM), snd("tick", start + ANIM, 4)], s["at"], x=round(cx - bw / 2, 1),
                     w=round(bw, 1), y=round(ybase - h, 1), h=round(h, 1), ybase=ybase, text=s["text"] + " " + it["unit"], label=s["label"], cx=round(cx, 1),
                     highlight=bool(s.get("highlight")), size=58, label_size=42, value=s["value"])

    def line_chart(self, p: dict, it: dict) -> None:
        w = p["box"][2]
        x0, x1, ytop, ybot = 300, w - 300, 270, 690
        vals = [q["value"] for q in it["series"]]
        lo, hi = min(vals), max(vals)
        n = len(it["series"])
        xs = [x0 + (x1 - x0) * k / (n - 1) for k in range(n)]
        ys = [ytop + (hi - v) / (hi - lo) * (ybot - ytop) for v in vals]
        self.add(p["id"], "chart_title", FIRST, FIRST, [], None, text=it["title"], at=[w / 2, 110], size=54, static=True)
        self.add(p["id"], "chart_zero", FIRST, FIRST, [], None, x0=x0 - 40, x1=x1 + 40, y=round(ytop + hi / (hi - lo) * (ybot - ytop), 1), label="0 °C", size=40,
                 static=True)
        prev = None
        for k, q in enumerate(it["series"]):
            start, _ = self.word(q["at"])
            last = k == n - 1
            sd = [snd("pencil_scribble", start, ANIM)] if k else [snd("pencil_scribble", start, ENTER)]
            if last:
                sd.append(snd("tick", start + ANIM, 4))
            p1 = [round(xs[k], 1), round(ys[k], 1)]
            self.add(p["id"], "line_seg", start, start + (ANIM if k else ENTER), sd, q["at"], p0=prev, p1=p1, first=(k == 0), last=last,
                     text=("%+.1f °C" % q["value"]).replace("-", "−") if last else None, size=58, width=14)
            prev = p1

    def timeline(self, p: dict, it: dict) -> None:
        w = p["box"][2]
        x0, x1, y = 200, w - 200, 230
        s0, _ = self.word(it["at"])
        top = it["marks"][0][0]
        marks = [(x0 + (top - yrs) / top * (x1 - x0), label) for yrs, label in it["marks"]]
        self.add(p["id"], "chart_title", FIRST, FIRST, [], None, text="Years ago", at=[w / 2, 110], size=54, static=True)
        self.add(p["id"], "timeline_axis", s0, s0 + ANIM, [snd("pencil_scribble", s0, ANIM)], it["at"], x0=x0, x1=x1, y=y, width=12,
                 ticks=[{"x": round(x, 1), "label": lab} for x, lab in marks], size=44)
        ms, _ = self.word(it["move_at"])
        ms = max(ms, s0 + ANIM + 2)
        sd = [snd("tick", ms + round(ease_inv((x - x0) / (x1 - x0)) * LONG), 4) for x, _l in marks]
        self.add(p["id"], "marker", ms, ms + LONG, sd, it["move_at"], x0=x0, x1=x1, y=y, r=26)

    # -- accent items
    def stat(self, p: dict, it: dict) -> None:
        s, _ = self.word(it["at"])
        w, h = p["box"][2], p["box"][3]
        self.add(p["id"], "stat_callout", s, s + ENTER, [snd("pop_in", s, 8)], it["at"], number=it["number"], unit=it["unit"], caption=it["caption"],
                 at=[w / 2, h * 0.52], size_num=230, size_unit=84, size_cap=52)

    def compare(self, p: dict, it: dict) -> None:
        w, h = p["box"][2], p["box"][3]
        for side, cx in (("left", w * 0.27), ("right", w * 0.73)):
            d = it[side]
            s, _ = self.word(d["at"])
            self.add(p["id"], "compare_half", s, s + ENTER, [snd("pop_in", s, 8)], d["at"], side=side, label=d["label"], direction=d["direction"],
                     at=[round(cx, 1), round(h * 0.5, 1)], size=84)

    def finish(self, protected: list, push, photo_id: str | None, world_k: float | None, anchor: str) -> dict:
        full = self.shot.get("mode") == "full"
        for p in self.panels:
            its = [i for i in self.items if i["pid"] == p["id"]]
            if not its:
                continue
            if full:
                p["start"], p["end"] = FIRST, self.n - EXIT_MARGIN
            else:
                p["start"] = max(FIRST, min(i["start"] for i in its))
                p["end"] = min(self.n - EXIT_MARGIN, max(i["motion_end"] for i in its) + int(HOLD_S * FPS))
            for i in its:
                i["end"] = p["end"]
        for p in self.panels:
            if p["surface"] == "glass" and p["start"] is not None:
                self.sounds.append({"cls": "swish", "t": p["start"], "dur": 8, "gain": 0.8, "item": p["id"]})
        return {"schema": SCHEMA, "shot_no": self.shot["no"], "shot_id": f"D{self.shot['no']:02d}", "fps": FPS, "frames": self.n, "frame": {"w": W, "h": H},
                "route": self.shot["route"], "mode": self.shot.get("mode"), "surface": self.shot.get("surface"), "overlay_reason": self.shot.get("reason"),
                "style_ref": self.style["id"], "style": self.style, "anchor": anchor, "ease": EASE, "panels": self.panels, "items": self.items,
                "sound": self.sounds, "words": self.sp, "photo": photo_id, "push": push, "world_k": world_k, "protected": protected,
                "demo_data": True, "claim_ids": [], "camera_events": [], "plate_alpha": 0.5}


def build(shot: dict, narr: dict | None, style: dict, assets: dict | None = None) -> dict:
    """The spec of one shot. ``assets`` = {photo id: demo_assets.info} for the calm-zone choice of the accent shots."""
    sh = Shot(shot, narr, style)
    items = shot.get("items", [])
    if shot["route"] == "ltx" or not items:
        return sh.finish([], shot.get("push"), shot.get("photo"), None, "none")
    mode = shot["mode"]
    if mode == "full" and shot.get("bg") == "map":
        p = sh.panel("p0", [0, 0, W, H], "solid", "none", view=shot["view"], anchor="world", plate=True)
        for it in items:
            sh.map_item(p, it)
        return sh.finish([], None, shot.get("photo"), 0.04, "map")
    if mode == "full":
        p = sh.panel("p0", shot.get("panel", CHART), "solid", "card")
        for it in items:
            sh.map_item(p, it)
        return sh.finish([], shot.get("push"), shot.get("photo"), None, "screen")
    # accent: a calm zone for the panel (glass) or for the bare element
    info = assets[shot["photo"]]
    push, n = shot["push"], sh.n
    it0 = items[0]
    size = it0["size"] if isinstance(it0.get("size"), (tuple, list)) else (round(len(it0.get("text", "")) * it0.get("size", 64) * 0.62) + 40, round(it0.get("size", 64) * 1.7))
    # the window the overlay is on screen: from its first word to the last motion + the hold
    kinds = it0["kind"]
    if kinds == "mini_map":
        s0, _ = sh.word(items[1]["at"]) if len(items) > 1 else (FIRST, 0)
        sh.cur = 0
        last = max(sh.word(i["at"])[0] for i in items if "at" in i) + LONG
        sh.cur = 0
    else:
        s0 = sh.word(it0["at"] if "at" in it0 else it0["left"]["at"])[0] if kinds != "compare_pair" else sh.word(it0["left"]["at"])[0]
        sh.cur = 0
        last = (sh.word(it0["right"]["at"])[0] + ENTER) if kinds == "compare_pair" else s0 + ENTER
        sh.cur = 0
    end = min(n - EXIT_MARGIN, last + int(HOLD_S * FPS))
    box = PL.choose(info, tuple(size), push, n, it0.get("pref", "top_right"), start=max(FIRST, s0), end=end)
    surface = shot["surface"]
    prot = [list(b) for b in PL.protected(info)]
    if kinds == "mini_map" and shot.get("variant") == "bare":
        # the A/B variant of the same shot: the same arrow and counter on the photo itself, no panel, no map (halo on the text)
        p = sh.panel("p0", box, "bare", "none")
        w, h = box[2], box[3]
        s, _ = sh.word(items[1]["at"])
        pts = MA._arc((40.0, 70.0), (w - 40.0, 70.0), bend=0.12)
        sh.add("p0", "route_arrow", s, s + ANIM, [snd("pencil_scribble", s, ANIM), snd("tick", s + ANIM, 4)], items[1]["at"], layer="screen",
               path=[[round(x, 1), round(y, 1)] for x, y in pts], width=round(float(H) * 0.010, 1))
        sh.map_item(p, {**items[2], "at_y": 0.34})
    elif kinds == "mini_map":
        p = sh.panel("p0", box, "glass", "glass", view=it0["view"], plate=True)
        p["plate_file"] = "plates/p0.png"
        for it in items[1:]:
            sh.map_item(p, it)
    elif kinds == "stat_callout":
        p = sh.panel("p0", box, surface, "none" if surface == "bare" else "glass")
        sh.stat(p, it0)
    elif kinds == "compare_pair":
        p = sh.panel("p0", box, surface, "none" if surface == "bare" else "glass")
        sh.compare(p, it0)
    elif kinds == "label":
        p = sh.panel("p0", box, "bare", "none")
        h = box[3]
        s, _ = sh.word(it0["at"])
        sh.add("p0", "label", s, s + ENTER, [snd("pop_in", s, 8)], it0["at"], layer="screen", text=it0["text"], at=[0, round(h * 0.80, 1)], size=it0.get("size", 64),
               plain=True)
    else:
        raise ContractError(f"accent kind {kinds}")
    spec = sh.finish(prot, push, shot["photo"], None, "screen")
    if shot.get("variant") == "bare":
        spec["surface"] = "bare"
    return spec
