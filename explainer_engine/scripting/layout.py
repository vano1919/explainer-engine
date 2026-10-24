"""Shot layout from real sizes and a camera (LY-01..LY-08, docs/KEYFRAME_GATE.md "Layout"): code computes where every figure
of a keyframe stands and how big it is, checks the numbers, and writes them as a technical prompt, a relative prompt, EliGen
boxes and a grey blockout / depth picture for a ControlNet. Claude never invents a size. stdlib + Pillow.

ვანო (2026-10-24 19:34 Tbilisi): give exact sizes with ± in one variant and relative proportions in the other; make sure the
system writing the numbers does not make mistakes; look at drawing simple figures first and the style after.

A spec is ``{"id", "size": EWS|WS|MWS|MS|MCU|CU, "angle"?: eye|low|high, "items": [{"tag", "kind", "where",
"depth"?: front|mid|back or metres behind the lead, "elev"?: metres above the lead's ground, "lead"?: bool}]}``; ``kind`` is a row of SIZES.

    python -m explainer_engine.scripting.layout <spec.json> [--png out.png]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# LY-01: real heights in metres (standing, as seen in a picture) with the reference they come from; widths for boxes.
# Cartoon figures keep real HEIGHTS (big heads change the inside of the figure, not its height in the frame).
SIZES = {
    "adult": {"h": 1.72, "w": 0.55, "ref": "average adult height ~1.7 m (Wikipedia: Human height)"},
    "old_adult": {"h": 1.65, "w": 0.55, "ref": "adult height, a little stooped"},
    "child": {"h": 1.20, "w": 0.40, "ref": "child of ~7 years ~1.2 m (WHO growth reference)"},
    "city_bus": {"h": 3.05, "w": 12.0, "ref": "12 m single-deck city bus, ~3.0-3.2 m tall (Wikipedia: Bus)"},
    "woolly_mammoth": {"h": 3.3, "w": 4.5, "ref": "woolly mammoth shoulder height 2.7-3.4 m (Wikipedia: Woolly mammoth)"},
    "brown_bear": {"h": 1.1, "w": 2.0, "ref": "brown bear on four legs ~1 m at the shoulder (Wikipedia: Brown bear)"},
    "brown_bear_standing": {"h": 2.3, "w": 0.9, "ref": "brown bear standing upright 2-2.5 m (Wikipedia: Brown bear)"},
    "lynx": {"h": 0.65, "w": 1.0, "ref": "Eurasian lynx ~0.6-0.7 m at the shoulder (Wikipedia: Eurasian lynx)"},
    "car": {"h": 1.5, "w": 4.5, "ref": "family car ~1.5 m tall, ~4.5 m long"},
    "tent": {"h": 2.0, "w": 2.5, "ref": "hide tent / hut ~2 m"},
    "phone": {"h": 0.15, "w": 0.075, "ref": "smartphone ~15 cm"},
}
# LY-02: how big the LEAD figure is in each shot size, as a share of the frame height (its full height; >1 = cut by the frame)
LEAD_SHARE = {"EWS": 0.12, "WS": 0.35, "MWS": 0.82, "MS": 1.9, "MCU": 2.8, "CU": 5.5}
X = {"left": .22, "center": .5, "right": .78, "left_back": .3, "center_back": .5, "right_back": .7, "left_front": .18,
     "right_front": .82}
DEPTH = {"front": 0.8, "mid": 1.0, "back": 1.7}
FOV_V = math.radians(32)       # vertical field of view of a ~40 mm lens on 16:9
EYE = {"eye": 1.6, "low": 0.6, "high": 4.0}  # camera height in metres
TOL = 0.05                     # LY-05: the ± of the technical prompt, share of the frame height


def _depth(item: dict, z0: float) -> float:
    d = item.get("depth", "back" if str(item.get("where", "")).endswith("_back") else
                 "front" if str(item.get("where", "")).endswith("_front") else "mid")
    return z0 + float(d) if isinstance(d, (int, float)) else z0 * DEPTH[d]


def solve(spec: dict) -> dict:
    """Every item's box in the frame (0..1, y down) from its real height, its distance and the camera."""
    items = spec["items"]
    lead = next((i for i in items if i.get("lead")), items[0])
    f = 0.5 / math.tan(FOV_V / 2)                     # focal length in frame heights
    z0 = SIZES[lead["kind"]]["h"] * f / LEAD_SHARE[spec["size"]]
    cam_h = EYE.get(spec.get("angle", "eye"), 1.6)
    # a low camera tilts up (the horizon sinks in the frame), a high one tilts down (the horizon rises)
    horizon = {"eye": 0.5, "low": 0.68, "high": 0.3}[spec.get("angle", "eye")]
    out = []
    for it in items:
        size = SIZES[it["kind"]]
        z = max(0.5, _depth(it, z0))
        h = size["h"] * f / z
        w = min(size["w"], size["h"] * 1.6) * f / z * 9 / 16    # frame-width units on a 16:9 frame
        bottom = horizon + (cam_h - float(it.get("elev", 0))) * f / z     # elev: standing on a hill or a step
        cx = X.get(it.get("where", "center"), .5)
        out.append({"tag": it["tag"], "kind": it["kind"], "z": round(z, 2), "height": round(h, 3),
                    "box": [round(cx - w / 2, 3), round(bottom - h, 3), round(cx + w / 2, 3), round(bottom, 3)],
                    "cx": cx, "lead": it is lead, "elev": it.get("elev", 0)})
    return {"id": spec.get("id"), "size": spec["size"], "items": out}


def check(layout: dict) -> list[dict]:
    """LY-03/LY-04: numbers that cannot be drawn or contradict each other FAIL before anything is paid for."""
    found = []
    close = layout["size"] in ("MS", "MCU", "CU")
    for it in layout["items"]:
        x0, y0, x1, y1 = it["box"]
        if y1 < 0.05 or y0 > 0.98 or x1 < 0 or x0 > 1:
            found.append({"rule": "LY-03", "severity": "FAIL", "where": it["tag"], "detail": "outside the frame"})
        elif not close and (y0 < -0.02 or y1 > 1.02) and not it["lead"]:
            found.append({"rule": "LY-03", "severity": "REVIEW", "where": it["tag"], "detail": "cut by the frame edge"})
        if it["height"] < 0.04:
            found.append({"rule": "LY-04", "severity": "REVIEW", "where": it["tag"],
                          "detail": f"{it['height']:.0%} of the frame height: too small to act (KP-13)"})
    items = layout["items"]
    for a in items:
        for b in items:
            if a is b or a["z"] != b["z"]:
                continue
            ix = min(a["box"][2], b["box"][2]) - max(a["box"][0], b["box"][0])
            if ix > 0.5 * min(a["box"][2] - a["box"][0], b["box"][2] - b["box"][0]) and a["tag"] < b["tag"]:
                found.append({"rule": "LY-04", "severity": "FAIL", "where": f"{a['tag']} / {b['tag']}",
                              "detail": "two figures at the same depth overlap by more than half: move one"})
    # LY-04: a figure hidden behind a nearer one cannot act or be seen (the mammoth behind the bus)
    for b in items:
        bx0, by0, bx1, by1 = b["box"]
        area = max(1e-6, (bx1 - bx0) * (by1 - by0))
        for a in items:
            if a["z"] >= b["z"]:
                continue
            ix = max(0.0, min(a["box"][2], bx1) - max(a["box"][0], bx0))
            iy = max(0.0, min(a["box"][3], by1) - max(a["box"][1], by0))
            if ix * iy / area > 0.6:
                found.append({"rule": "LY-04", "severity": "FAIL", "where": b["tag"],
                              "detail": f"{ix * iy / area:.0%} hidden behind {a['tag']}: move it, raise it (elev) or bring it nearer"})
    return found


def _pct(v: float) -> str:
    return f"{round(v * 100)} %"


def technical(layout: dict) -> str:
    """LY-05: every figure as numbers with a tolerance."""
    parts = []
    for it in layout["items"]:
        x0, y0, x1, y1 = it["box"]
        parts.append(f"{it['tag'][0].upper() + it['tag'][1:]}: {_pct(min(it['height'], 1.0))} ± {_pct(TOL)} of the frame height"
                     f"{' (cut by the frame)' if it['height'] > 1 else ''}, centred {_pct(it['cx'])} from the left edge, "
                     f"feet {_pct(min(y1, 1.0))} from the top edge")
    return ". ".join(parts) + "."


def _ratio(r: float) -> str:
    for limit, words in ((0.15, "a tiny fraction of the height of"), (0.3, "about a quarter as tall as"),
                         (0.42, "about a third as tall as"), (0.6, "about half as tall as"),
                         (0.85, "a little shorter than"), (1.15, "about as tall as"), (1.45, "about a third taller than"),
                         (1.8, "about one and a half times as tall as"), (2.5, "about twice as tall as")):
        if r < limit:
            return words
    return f"about {round(r)} times as tall as"


def relative(layout: dict) -> str:
    """LY-06: every figure compared with the lead (or the biggest thing near it): proportions and distance in words."""
    items = layout["items"]
    lead = next(i for i in items if i["lead"])
    parts = []
    for it in items:
        if it is lead:
            continue
        real = SIZES[it["kind"]]["h"] / SIZES[lead["kind"]]["h"]
        gap = it["z"] - lead["z"]
        n = abs(round(gap))
        where = ("beside" if abs(gap) < 1 else
                 f"about {n} metre{'s' if n != 1 else ''} {'behind' if gap > 0 else 'in front of'}")
        raised = f", about {round(float(it['elev']))} metres higher up" if it.get("elev") else ""
        parts.append(f"{it['tag']} is {_ratio(real)} {lead['tag']} and stands {where} {lead['tag']}{raised}")
    return "; ".join(parts) + "." if parts else ""


def eligen(layout: dict) -> list[dict]:
    """LY-07: boxes for EliGen (clipped to the frame)."""
    return [{"prompt": it["tag"], "box": [max(0.0, min(1.0, v)) for v in it["box"]]} for it in layout["items"]]


def blockout(layout: dict, path: str | Path, size=(1280, 720)) -> Path:
    """LY-08: grey figures on a ground gradient, nearer = lighter: a depth-like picture for a ControlNet (depth / soft edge)."""
    from PIL import Image, ImageDraw
    w, h = size
    im = Image.new("L", size, 0)
    d = ImageDraw.Draw(im)
    for y in range(h // 2, h):               # the ground comes nearer toward the bottom
        d.line([(0, y), (w, y)], fill=int(20 + 70 * (y - h / 2) / (h / 2)))
    zs = [it["z"] for it in layout["items"]]
    zmin, zmax = min(zs), max(zs)
    for it in sorted(layout["items"], key=lambda i: -i["z"]):
        x0, y0, x1, y1 = it["box"]
        shade = 255 if zmax == zmin else int(130 + 125 * (zmax - it["z"]) / (zmax - zmin))
        box = [x0 * w, y0 * h, x1 * w, y1 * h]
        if it["kind"] in SIZES and SIZES[it["kind"]]["w"] > SIZES[it["kind"]]["h"]:   # animals and vehicles: a body
            d.rounded_rectangle(box, radius=max(2, int((box[3] - box[1]) * 0.15)), fill=shade)
        else:                                                                          # people: head + body
            head = (box[2] - box[0]) * 0.55
            cx = (box[0] + box[2]) / 2
            d.ellipse([cx - head / 2, box[1], cx + head / 2, box[1] + head], fill=shade)
            d.rounded_rectangle([box[0], box[1] + head * 0.9, box[2], box[3]], radius=int(head / 3), fill=shade)
    path = Path(path)
    im.convert("RGB").save(path)
    return path


def main(argv: list[str]) -> int:
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    lay = solve(spec)
    found = check(lay)
    print(json.dumps({"layout": lay, "technical": technical(lay), "relative": relative(lay), "eligen": eligen(lay),
                      "findings": found}, indent=1, ensure_ascii=False))
    if "--png" in argv:
        blockout(lay, argv[argv.index("--png") + 1])
    return 1 if any(f["severity"] == "FAIL" for f in found) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
