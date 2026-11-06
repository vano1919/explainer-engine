"""J5 dialogue collage, step 1 (creator 2026-11-06 16:44 UTC; brief ``ltx_gap_review_2026-11-06/J5_DIALOGUE_TEST_BRIEF.md``): two heroes
cut out of their flat-lit sheets, stood in ONE backdrop as Blender 2.5D cards, four frames cut as J5 would cut a dialogue. Free:
the BiRefNet cut-outs run on the CPU, Blender is the pinned bpy wheel, nothing is painted or paid.

    python -m explainer_engine.blender.j5_collage render --inputs D --out O [--size 2560x1440] [--shots S1,S2] [--bpy-python P]

How a frame is made (the creator's "maximum realism" list, 16:55 UTC):

1. **One light.** The only key is the camp fire, a point at ``FIRE`` behind the pair. Per card its screen side (``lateral``) says
   which edge it lights; ``grade_card`` puts a warm wrap on that side, a warm rim on the contour that faces the fire, a cool sky
   rim on top, and shades the other side.
2. **Colour match.** Every card is multiplied by the dusk ambient of the backdrop, its black is lifted to the backdrop's black and
   its warm part comes from the fire's colour, so the sheet's neutral-paper lighting does not ride along.
3. **Depth.** Each card is rendered alone on alpha (``transparent`` job of ``bpy/assemble_25d.py``); ``compose`` blurs the backdrop
   and a foreground shoulder by their own sigma (the backdrop more the longer the lens), darkens the shoulder, adds the fire's
   bloom, and
4. **one grain/paper layer over everything**, so card and backdrop share a texture.
5. Scale and eye-line from the camera: eye height 1.55-1.7 m, level camera, heroes' eyes on the horizon row of the backdrop crop.

The backdrop is a CROP of the painted A1 (2048x1024) as a flat plate 40 m away, one crop per shot (a 360 equirect of 2048 px gives
about 250 px across a 44 degree frame: 10x soft). The sheets' own cut is hidden by the framing: H1's sheets end at the belt, so
nothing below his belt is ever in frame (no legs, no ground contact in these four frames).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_engine.blender import assemble_25d as A
from explainer_engine.core.store import write_json_atomic

FPS = 24
PLATE_DISTANCE_M = 40.0
FIRE = (0.0, 9.0, 0.6)          # the camp fire in the world (the plate's fire is behind and between the pair in S1)
EYE_H1, EYE_H2 = 1.71, 1.44      # measured on the sheets (head/belt proportions, see HERO)
AMBIENT = np.array([0.50, 0.45, 0.64])      # dusk sky-and-ground fill (A1's mean tone, purple-blue)
WARM = np.array([1.0, 0.58, 0.22])          # the fire's colour as it sits in A1's flame
HAZE_BLACK = np.array([0.09, 0.065, 0.14])  # A1's darkest tone: the cards' blacks are lifted to it

# hero sheets: file stem, card height in metres (the alpha box of the figure), z of the card's bottom
# H2 is a whole figure (1.65 m). H1's sheets end at the belt (head 41 % of the bust, a four-head figure = 1.9 m), so the bust card is
# 0.85 m tall (its head then measures 0.27 m against the scout's 0.23 m, as rendered) and its bottom stands 0.91 m above the ground,
# so his eyes (z about 1.62) and the scout's (about 1.56) both sit on the camera's eye-line.
HERO = {"H2": {"height": 1.65, "z0": 0.0}, "H1": {"height": 0.85, "z0": 0.91}}

SHOTS = {
    "S1_two_shot": {
        "label": "medium two-shot", "lens": 60, "cam": (0.0, 0.0, 1.6), "aim": (0.0, 10.0, 1.6), "plate": (220, 11, 1780, 889),
        "sigma_plate": 3.0,
        "cards": [{"id": "H2", "img": "B_H2_right34", "pos": (-0.7, 3.8), "sigma": 0.0, "dark": 1.0},
                  {"id": "H1", "img": "B_H1_left34", "pos": (0.55, 3.8), "sigma": 0.0, "dark": 1.0}]},
    "S2_ots_h2_to_h1": {
        "label": "over H2's shoulder, H1 speaks", "lens": 60, "cam": (-2.8, 2.4, 1.6), "aim": (0.55, 3.8, 1.6),
        "plate": (1100, 183, 2048, 717), "sigma_plate": 9.0,
        "cards": [{"id": "H2", "img": "B_H2_back", "pos": (-0.7, 3.8), "sigma": 5.0, "dark": 0.68},
                  {"id": "H1", "img": "B_H1_left34", "pos": (0.55, 3.8), "sigma": 0.0, "dark": 1.0}]},
    "S3_ots_h1_to_h2": {
        "label": "over H1's shoulder (reverse), H2 listens", "lens": 60, "cam": (2.7, 2.4, 1.6), "aim": (-0.7, 3.8, 1.55),
        "plate": (0, 183, 950, 717), "sigma_plate": 9.0,
        "cards": [{"id": "H1", "img": "B_H1_back", "mirror": True, "pos": (0.55, 3.8), "sigma": 5.0, "dark": 0.68},
                  {"id": "H2", "img": "B_H2_right34", "pos": (-0.7, 3.8), "sigma": 0.0, "dark": 1.0}]},
    "S4_close_up_h1": {
        "label": "close-up H1, eye-line left to H2", "lens": 70, "cam": (-0.2, 0.6, 1.62), "aim": (0.55, 3.8, 1.62),
        "plate": (1150, 253, 1850, 647), "sigma_plate": 14.0,
        "cards": [{"id": "H1", "img": "B_H1_left34", "pos": (0.55, 3.8), "sigma": 0.0, "dark": 1.0}]},
}


# --- geometry -------------------------------------------------------------------------------------------------------------------

def basis(cam, aim):
    f = np.array(aim, float) - np.array(cam, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    return f, r, np.cross(r, f)


def project(cam, aim, lens, pt, sensor=36.0, aspect=16 / 9):
    """NDC (x right, y up, both -1..1 at the frame edge) and the distance along the optical axis of a world point."""
    f, r, u = basis(cam, aim)
    d = np.array(pt, float) - np.array(cam, float)
    z = float(d @ f)
    sx = sensor / 2 / lens
    return float(d @ r) / (z * sx), float(d @ u) / (z * sx / aspect), z


# --- the plate and the cards -------------------------------------------------------------------------------------------------------

def _cv2():
    import cv2
    return cv2


def plate_image(a1: Image.Image, crop, size) -> Image.Image:
    cv2 = _cv2()
    c = np.asarray(a1.convert("RGB").crop(crop))
    out = cv2.resize(c, size, interpolation=cv2.INTER_LANCZOS4)
    soft = cv2.GaussianBlur(out, (0, 0), 1.6)
    out = cv2.addWeighted(out, 1.35, soft, -0.35, 0)   # the 1.6-3.7x enlargement gets a light unsharp mask
    return Image.fromarray(out)


def clean_cut(path: Path, *, mirror: bool = False) -> np.ndarray:
    """RGBA float 0..1 of a BiRefNet cut-out (edit/cutout.py finish): alpha eroded by 1 px, then feathered by sigma 0.7."""
    cv2 = _cv2()
    im = np.asarray(Image.open(path).convert("RGBA"), np.float32) / 255.0
    if mirror:
        im = im[:, ::-1]
    a = cv2.erode(im[..., 3], np.ones((3, 3), np.uint8))
    a = np.clip(cv2.GaussianBlur(a, (0, 0), 0.7), 0, 1)
    out = im.copy()
    out[..., 3] = a
    return out


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def grade_card(rgba: np.ndarray, lateral: float, *, dark: float = 1.0) -> np.ndarray:
    """The card as the fire at ``lateral`` (-1 camera-left .. +1 camera-right) and the dusk would light it (items 1 and 2 above).
    Returns RGBA float with the same alpha."""
    cv2 = _cv2()
    rgb, a = rgba[..., :3], rgba[..., 3]
    h, w = a.shape
    ys, xs = np.nonzero(a > 0.5)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    u = np.clip((np.arange(w)[None, :] - x0) / max(1, x1 - x0), 0, 1) * np.ones((h, 1))
    v = np.clip((np.arange(h)[:, None] - y0) / max(1, y1 - y0), 0, 1) * np.ones((1, w))
    side = 0.5 + 0.5 * lateral * (2 * u - 1)                 # 1 on the side that faces the fire
    lit = smoothstep(side * 1.15 - 0.10)[..., None]
    mult = AMBIENT * 0.86 * (1 - lit) + (AMBIENT * 0.95 + WARM * 0.50) * lit
    out = rgb * mult
    # ground bounce: the firelit ground warms the lower quarter
    out += WARM * 0.10 * smoothstep((v - 0.72) / 0.28)[..., None] * (0.4 + 0.6 * lit)
    # rims: the inner band of the figure, by the direction its edge faces
    k = max(3, int(round(0.012 * max(h, w))))
    soft = cv2.GaussianBlur(a, (0, 0), k)
    gx = cv2.Sobel(soft, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(soft, cv2.CV_32F, 0, 1, ksize=3)
    n = np.sqrt(gx * gx + gy * gy) + 1e-6
    nx, ny = -gx / n, -gy / n                                 # the outward normal (image y down)
    band = np.clip(a - cv2.GaussianBlur(a, (0, 0), k * 1.8), 0, 1) * 2.2
    band = np.clip(band, 0, 1)
    ld = np.array([lateral * 0.9, 0.35]); ld /= np.linalg.norm(ld) + 1e-6
    fire_rim = np.clip(nx * ld[0] + ny * ld[1], 0, 1) ** 1.6 * band
    sky_rim = np.clip(-ny, 0, 1) ** 2.0 * band
    out += fire_rim[..., None] * WARM * 0.85 * (0.6 + 0.4 * abs(lateral))
    out += sky_rim[..., None] * np.array([0.30, 0.26, 0.52]) * 0.35
    # the blacks of the ink and the tunic rise to the backdrop's black (they were pure sheet-black)
    out = out + HAZE_BLACK * (1 - np.clip(out, 0, 1)) * 0.55
    out = np.clip(out * dark, 0, 1)
    return np.dstack([out, a])


def save_rgba(arr: np.ndarray, path: Path) -> Path:
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(path)
    return path


# --- Blender passes ---------------------------------------------------------------------------------------------------------------

def _job(shot: dict, cards: list[dict], *, size, transparent: bool, a1: str, seconds: float, name: str) -> dict:
    cam, aim = shot["cam"], shot["aim"]
    frames = max(1, round(seconds * FPS))
    return {"job": A.JOB, "shot_id": name, "fps": FPS, "frames": frames, "width": size[0], "height": size[1], "engine": "eevee",
            "samples": 8, "world": {"image": a1, "yaw_deg": 0.0},
            "camera": {"keys": [{"frame": 0, "location": list(cam), "look_at": list(aim)},
                                {"frame": frames - 1, "location": list(cam), "look_at": list(aim)}],
                       "lens_mm": shot["lens"], "sensor_mm": 36.0, "setup": shot["label"]},
            "cards": cards, "probe": [], "transparent": transparent}


def card_dict(name: str, image: Path, pos, height: float, *, cam) -> dict:
    geo = A.card_geometry(image, height)
    return {"name": name, "kind": "hero", "image": str(image), "pos": list(pos), "yaw_deg": A._facing(pos, cam), **geo}


def plate_card(image: Path, shot: dict, *, size) -> dict:
    d = PLATE_DISTANCE_M
    f, _, _ = basis(shot["cam"], shot["aim"])
    centre = np.array(shot["cam"], float) + f * d
    w = d * 36.0 / shot["lens"]
    h = w * size[1] / size[0]
    return {"name": "plate", "kind": "prop", "image": str(image), "pos": list(map(float, centre)),
            "yaw_deg": A._facing(centre, shot["cam"]), "width_m": w, "height_m": h, "left_m": -w / 2, "bottom_m": -h / 2,
            "figure_width_m": w, "px": list(size)}


def blender_layers(shot: dict, work: Path, *, inputs: Path, size, launcher, pin: str) -> dict:
    """Render the plate and every card alone; returns {"plate": path, "<id>": path, "seconds": {...}} (frame 0 of each pass)."""
    a1 = Image.open(inputs / "A1_tent.png")
    work.mkdir(parents=True, exist_ok=True)
    plate_png = work / "plate.png"
    plate_image(a1, shot["plate"], size).save(plate_png)
    cam = shot["cam"]
    fx, _, fz = project(cam, shot["aim"], shot["lens"], FIRE)
    out, secs = {}, {}
    passes = [("plate", [plate_card(plate_png, shot, size=size)], False)]
    for c in shot["cards"]:
        hero = HERO[c["id"]]
        cut = clean_cut(inputs / f"{c['img']}.cut.png", mirror=c.get("mirror", False))
        px, _, _ = project(cam, shot["aim"], shot["lens"], (c["pos"][0], c["pos"][1], hero["z0"] + hero["height"] / 2))
        lateral = float(np.clip((fx - px) / 0.5, -1, 1))
        c["lateral"] = round(lateral, 3)
        graded = save_rgba(grade_card(cut, lateral, dark=c["dark"]), work / f"card_{c['id']}_{c['img']}.png")
        cd = card_dict(f"card_{c['id']}", graded, (c["pos"][0], c["pos"][1], hero["z0"]), hero["height"], cam=cam)
        passes.append((c["id"], [cd], True))
    for name, cards, transparent in passes:
        d = work / f"pass_{name}"
        body = _job(shot, cards, size=size, transparent=transparent, a1=str(inputs / "A1_tent.png"), seconds=1 / FPS, name=name)
        t = time.perf_counter()
        rep = A.run(body, d, launcher, pin)
        secs[name] = round(time.perf_counter() - t, 1)
        out[name] = rep["frame_files"][0]
    out["seconds"] = secs
    return out


# --- compose -------------------------------------------------------------------------------------------------------------------------

def _blur(img: np.ndarray, sigma: float) -> np.ndarray:
    return img if sigma <= 0 else _cv2().GaussianBlur(img, (0, 0), sigma)


def grain_layer(shape, seed: int, *, scale: float) -> np.ndarray:
    """One luminance grain + paper layer for the whole frame (item 7): fine grain, a mid mottling, a long soft unevenness."""
    cv2 = _cv2()
    rng = np.random.default_rng(seed)
    h, w = shape
    fine = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.8 * scale) * 0.017 * (scale ** 0.5)
    mid = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 5.0 * scale) * 0.045 * scale
    long = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 40.0 * scale) * 0.26 * scale
    return (fine * 2.2 + mid + long).astype(np.float32)


def compose(layers: dict, shot: dict, size, *, seed: int = 7) -> tuple[Image.Image, Image.Image]:
    """The finished frame and the backdrop alone (graded and blurred the same way, for the 'does it read pasted' comparison)."""
    cv2 = _cv2()
    s = size[0] / 2560.0
    plate = np.asarray(Image.open(layers["plate"]).convert("RGB"), np.float32) / 255.0
    base = _blur(plate, shot["sigma_plate"] * s)
    # distance order: the nearest card on top
    order = sorted(shot["cards"], key=lambda c: -math.hypot(c["pos"][0] - shot["cam"][0], c["pos"][1] - shot["cam"][1]))
    img = base.copy()
    for c in order:
        la = np.asarray(Image.open(layers[c["id"]]).convert("RGBA"), np.float32) / 255.0
        a = la[..., 3:4]
        pm = np.dstack([la[..., :3] * a, a])           # premultiplied
        pm = _blur(pm, c["sigma"] * s)
        a2 = pm[..., 3:4]
        img = img * (1 - a2) + pm[..., :3]
    # the fire's bloom and the finishing: vignette, one shared grain/paper layer
    def finish(x):
        hi = np.clip(x - np.array([0.62, 0.40, 0.18]), 0, 1) * np.array([1.0, 0.75, 0.4])
        x = 1 - (1 - x) * (1 - _blur(hi, 30 * s) * 0.55)
        yy, xx = np.mgrid[0:x.shape[0], 0:x.shape[1]].astype(np.float32)
        r = np.hypot((xx / x.shape[1] - 0.5) * 1.1, (yy / x.shape[0] - 0.5) * 1.25)
        x = x * (1 - 0.32 * smoothstep((r - 0.35) / 0.65))[..., None]
        g = grain_layer(x.shape[:2], seed, scale=s)
        lum = x.mean(-1, keepdims=True)
        x = x + g[..., None] * (0.55 + 0.9 * (1 - np.abs(2 * lum - 1)))
        return np.clip(x, 0, 1)
    full, only = finish(img), finish(base)
    to8 = lambda a: Image.fromarray((a * 255 + 0.5).astype(np.uint8))   # noqa: E731
    return to8(full), to8(only)


def contact_sheet(frames: dict[str, Image.Image], out: Path, *, labels: dict[str, str]) -> Path:
    from PIL import ImageDraw
    names = list(frames)
    w, h = 1280, 720
    sheet = Image.new("RGB", (w * 2, h * ((len(names) + 1) // 2)), (12, 10, 16))
    for i, n in enumerate(names):
        t = frames[n].resize((w, h), Image.LANCZOS)
        d = ImageDraw.Draw(t)
        d.rectangle((0, 0, w, 30), fill=(0, 0, 0))
        d.text((10, 8), f"{n}: {labels[n]}", fill=(235, 225, 205))
        sheet.paste(t, ((i % 2) * w, (i // 2) * h))
    sheet.save(out)
    return out


def render(inputs: Path, out: Path, *, size=(2560, 1440), shots=None, launcher, pin) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    frames, rows = {}, {}
    for name, shot in SHOTS.items():
        if shots and name not in shots:
            continue
        shot = json.loads(json.dumps(shot))   # per-run copy (lateral is written into it)
        shot["cam"], shot["aim"] = tuple(shot["cam"]), tuple(shot["aim"])
        for c in shot["cards"]:
            c["pos"] = tuple(c["pos"])
        lay = blender_layers(shot, out / "work" / name, inputs=inputs, size=size, launcher=launcher, pin=pin)
        full, only = compose(lay, shot, size)
        full.save(out / f"{name}.png")
        only.save(out / "work" / name / "backdrop_only.png")
        frames[name] = full
        rows[name] = {"label": shot["label"], "lens_mm": shot["lens"], "camera": shot["cam"], "aim": shot["aim"],
                      "plate_crop_a1": shot["plate"], "cards": [{k: c[k] for k in ("id", "img", "pos", "lateral", "sigma")}
                                                                for c in shot["cards"]],
                      "blender_seconds": lay["seconds"]}
    labels = {n: SHOTS[n]["label"] for n in frames}
    sheet = contact_sheet(frames, out / "contact_sheet.png", labels=labels)
    report = {"schema": "j5_collage/1", "size": list(size), "shots": rows, "contact_sheet": sheet.name,
              "tools": {"blender": pin, "cutout": "BiRefNet (CPU, edit/cutout.py)", "paid": False}}
    write_json_atomic(out / "report.json", report)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--inputs", required=True, help="a folder with A1_tent.png and the <sheet>.cut.png cut-outs")
    r.add_argument("--out", required=True)
    r.add_argument("--size", default="2560x1440")
    r.add_argument("--shots", default=None)
    r.add_argument("--bpy-python", required=True)
    a = ap.parse_args(argv)
    from explainer_engine.blender import project as P
    w, h = (int(x) for x in a.size.split("x"))
    rep = render(Path(a.inputs), Path(a.out), size=(w, h), shots=a.shots.split(",") if a.shots else None,
                 launcher=[a.bpy_python], pin=P.BlenderProject().version)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
