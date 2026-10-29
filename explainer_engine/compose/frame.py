"""AC-05..AC-09: one shot composed from library assets. The layout (scripting/layout.py, LY-01..LY-08) says where every
figure stands and how tall it is; this module scales each cut-out to its box, stands it on the ground, draws its contact
shadow, hazes it by distance and paints far to near. No model and no money: Pillow + numpy on the CPU. A light repaint with
the style LoRA (img2img, strength 0.30, the 2026-10-25 composition test) evens the light afterwards and is the only paid step.

Shot: ``{"id", "size", "angle"?, "background": <name>, "items": [layout item + "asset": {"name", "angle", "facing",
"expression"}], "crowd"?: [crowd.py band], "light"?: "left"|"right"|"front"}``.

    python -m explainer_engine.compose.frame <library.json> <shot.json> <out.png> [--size 1280x720]
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from explainer_engine.compose.library import Library
from explainer_engine.scripting import layout as LY

HORIZON_TOL = {"EWS": 0.04, "WS": 0.05, "MWS": 0.08, "MS": 0.12, "MCU": 0.2, "CU": 0.3}   # AC-05, share of frame height
SHADOW_ALPHA = 0.38          # AC-07: contact shadow darkness under a figure standing in the frame
HAZE_MAX = 0.28              # AC-08: the farthest figures take at most this much of the horizon's colour


def camera(shot: dict) -> dict:
    """The camera the layout implies: focal length (frame heights), camera height (m) and the horizon (share of height)."""
    lay = LY.solve(shot)
    f = 0.5 / math.tan(LY.FOV_V / 2)
    cam_h = LY.EYE.get(shot.get("angle", "eye"), 1.6)
    lead = next(i for i in lay["items"] if i["lead"])
    horizon = lead["box"][3] - (cam_h - float(lead.get("elev", 0))) * f / lead["z"]
    return {"f": f, "cam_h": cam_h, "horizon": horizon, "layout": lay}


def project(cam: dict, kind: str, z: float, x: float, elev: float = 0.0) -> dict:
    """A figure of ``kind`` at distance z (m) and frame x (0..1): its box, the way layout.solve computes it."""
    size = LY.SIZES[kind]
    h = size["h"] * cam["f"] / z
    bottom = cam["horizon"] + (cam["cam_h"] - elev) * cam["f"] / z
    w = min(size["w"], size["h"] * 1.6) * cam["f"] / z * 9 / 16
    return {"kind": kind, "z": round(z, 2), "height": h, "cx": x, "box": [x - w / 2, bottom - h, x + w / 2, bottom]}


def _cover(img: Image.Image, w: int, h: int, horizon_src: float | None, horizon_dst: float) -> tuple[Image.Image, float]:
    """Scale a background to cover the frame and slide it so its horizon lands on the shot's horizon. Returns the frame and
    the horizon error (share of the frame height) left when the plate is too short to slide that far."""
    s = max(w / img.width, h / img.height)
    big = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x0 = (big.width - w) // 2
    if horizon_src is None:
        y0 = (big.height - h) // 2
        return big.crop((x0, y0, x0 + w, y0 + h)), 0.0
    want = horizon_src * big.height - horizon_dst * h
    y0 = int(round(min(max(want, 0), big.height - h)))
    return big.crop((x0, y0, x0 + w, y0 + h)), abs(want - y0) / h


def _alpha_box(im: Image.Image) -> tuple[int, int, int, int]:
    a = np.asarray(im.getchannel("A"))
    ys, xs = np.nonzero(a > 16)
    if not len(ys):
        raise ValueError("empty cut-out")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _haze(im: Image.Image, colour: tuple[int, int, int], amount: float) -> Image.Image:
    if amount <= 0:
        return im
    rgb = Image.new("RGB", im.size, colour)
    out = Image.blend(im.convert("RGB"), rgb, amount)
    out.putalpha(im.getchannel("A"))
    return out


def place(canvas: Image.Image, cut: Image.Image, box: list[float], *, flip=False, foot=0.0, shadow=True, light="left",
          haze=0.0, haze_colour=(200, 200, 200), tint=None) -> dict:
    """AC-06: scale the cut-out so its drawn height (above the ground contact) fills the box height; centre it on the box
    and stand its contact row on the box bottom. AC-07: a soft contact shadow under feet that are in the frame."""
    W, H = canvas.size
    bx0, by0, bx1, by1 = _alpha_box(cut)
    fig = cut.crop((bx0, by0, bx1, by1))
    if flip:
        fig = fig.transpose(Image.FLIP_LEFT_RIGHT)
    if tint:
        r, g, b, a = fig.split()
        fig = Image.merge("RGBA", [c.point(lambda v, k=k: min(255, int(v * k))) for c, k in zip((r, g, b), tint)] + [a])
    drawn_h = (box[3] - box[1]) * H
    s = drawn_h / (fig.height * (1 - foot))
    fw, fh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    fig = fig.resize((fw, fh), Image.LANCZOS)
    fig = _haze(fig, haze_colour, haze)
    cx = (box[0] + box[2]) / 2 * W
    ground = box[3] * H
    x, y = round(cx - fw / 2), round(ground - fh * (1 - foot))
    if shadow and ground <= H * 1.02:
        sw = fw * 0.85
        sh = max(2.0, sw * 0.12)
        dx = {"left": 0.12, "right": -0.12}.get(light, 0.0) * fw
        layer = Image.new("L", canvas.size, 0)
        ImageDraw.Draw(layer).ellipse([cx - sw / 2 + dx, ground - sh / 2, cx + sw / 2 + dx, ground + sh / 2],
                                      fill=int(255 * SHADOW_ALPHA * (1 - haze)))
        layer = layer.filter(ImageFilter.GaussianBlur(max(1.5, sh / 2.5)))
        canvas.paste(Image.new("RGB", canvas.size, (20, 18, 26)), (0, 0), layer)
    canvas.paste(fig, (x, y), fig)
    return {"px": [x, y, x + fw, y + fh], "scale": round(s, 3), "flip": flip}


def haze_for(z: float, z_lead: float) -> float:
    """AC-08: aerial perspective: nothing within 3x the lead's distance, then up to HAZE_MAX by ~10x."""
    return max(0.0, min(HAZE_MAX, (z / max(z_lead, 1e-6) - 3) / 7 * HAZE_MAX))


def compose(shot: dict, lib: Library, root: str | Path = ".", size=(1280, 720)) -> tuple[Image.Image, dict]:
    """The composed frame and its record (every placement, the horizon error, findings)."""
    from explainer_engine.compose import crowd as CR
    root = Path(root)
    W, H = size
    cam = camera(shot)
    findings = []
    bg = lib.find("background", shot["background"])
    if not bg:
        raise KeyError(f"no background {shot['background']!r} in the library")
    bgr = lib.get(bg["id"])
    frame, err = _cover(Image.open(root / bgr["path"]).convert("RGB"), W, H, bgr.get("horizon"), cam["horizon"])
    tol = HORIZON_TOL[shot["size"]]
    if err > tol:
        findings.append({"rule": "AC-05", "severity": "FAIL", "detail": f"background horizon off by {err:.0%} of the frame "
                         f"(plate {bgr.get('horizon')}, shot {cam['horizon']:.2f}): draw a taller plate or change the angle"})
    band = np.asarray(frame)[max(0, int(cam["horizon"] * H) - 6):max(1, int(cam["horizon"] * H) + 6)]
    hz = tuple(int(v) for v in (band.reshape(-1, 3).mean(0) if band.size else (200, 200, 200)))
    lead_z = next(i for i in cam["layout"]["items"] if i["lead"])["z"]
    jobs = []
    for spec, it in zip(shot["items"], cam["layout"]["items"]):
        a = spec.get("asset")
        if not a:
            continue
        hit = lib.find(a.get("kind", "hero"), a["name"], a.get("angle"), a.get("facing"), a.get("expression"))
        if not hit:
            findings.append({"rule": "AC-04", "severity": "FAIL", "detail": f"no asset for {a}"})
            continue
        jobs.append((it["z"], it["box"][3], {"tag": it["tag"], "asset": hit["id"], "flip": hit["flip"], "box": it["box"],
                                             "z": it["z"]}))
    for band_spec in shot.get("crowd", []):
        for p in CR.scatter(band_spec, cam, lib):
            jobs.append((p["z"], p["box"][3], p))
    findings += CR.check(shot.get("crowd", []), [j[2] for j in jobs if j[2].get("crowd")])
    placed = []
    for z, _, job in sorted(jobs, key=lambda j: (-j[0], j[1])):
        rec = lib.get(job["asset"])
        cut = Image.open(root / rec["path"]).convert("RGBA")
        px = place(frame, cut, job["box"], flip=job["flip"], foot=float(rec.get("foot", 0)), light=shot.get("light", "left"),
                   haze=haze_for(z, lead_z), haze_colour=hz, tint=job.get("tint"), shadow=not job.get("crowd") or z < lead_z * 4)
        placed.append({**job, **px})
    return frame, {"id": shot.get("id"), "horizon": round(cam["horizon"], 3), "horizon_error": round(err, 3),
                   "placed": placed, "findings": findings}


def main(argv: list[str]) -> int:
    lib = Library(argv[0])
    shot = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    size = (1280, 720)
    if "--size" in argv:
        size = tuple(int(v) for v in argv[argv.index("--size") + 1].split("x"))
    img, rec = compose(shot, lib, Path(argv[0]).parent, size)
    img.save(argv[2])
    print(json.dumps(rec["findings"], ensure_ascii=False))
    return 1 if any(f["severity"] == "FAIL" for f in rec["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
