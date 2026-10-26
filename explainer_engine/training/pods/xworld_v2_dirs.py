"""Direction views and line sketches of a place (round 3a, Opus plan sections 11-13, 2026-10-26): two extra pictures that give the grid
what a text line cannot, the whole place around the camera.

* the TURNAROUND: the EMPTY place from four directions (ahead, 90 degrees right, turned around, 90 degrees left) around the master camera,
  at 90 degrees horizontal field of view; its words come from the set's 3D ray cast, so the same code serves any place;
* the SKETCH: for each panel of a grid, a plain line drawing from the same ray cast (outlines of the landmarks with their names, a stick
  figure with the name of each person), put in the 2x2 order of the grid.

Pure numpy and PIL; the drawing models are on the pod side (xworld_v2_loop_run.py). No word of any one place is in this file: every name
comes from the set file.
"""
from __future__ import annotations

import math

import numpy as np

if __package__:
    from . import xworld_v2_s3 as S3
else:
    import xworld_v2_s3 as S3

YAWS = (0, 90, 180, 270)  # degrees to the right of the master camera: ahead, right, behind, left
VIEW_NAMES = ("straight ahead", "turned 90 degrees to the right", "turned around, looking back", "turned 90 degrees to the left")
ORDER = ("top-left", "top-right", "bottom-left", "bottom-right")
PANEL = (1280, 704)


def _turn(v, deg):
    a = math.radians(deg)
    return np.array([v[0] * math.cos(a) + v[1] * math.sin(a), -v[0] * math.sin(a) + v[1] * math.cos(a)])


def master_cam(s):
    return S3.camera(s, s["shots"]["s0"])


def view_cam(s, yaw, panel=PANEL):
    """The camera of one direction view: the master camera's position, its look turned ``yaw`` degrees to the right, a 90 degree horizontal view."""
    c0 = master_cam(s)
    pos = np.asarray(c0["pos"], float)
    d = np.asarray(c0["look_at"], float) - pos
    h = _turn(d[:2], yaw)
    look = np.array([pos[0] + h[0], pos[1] + h[1], pos[2]])  # a level look: the horizon in the middle
    return {"pos": pos, "look_at": look, "vfov": math.degrees(2 * math.atan(math.tan(math.radians(45)) * panel[1] / panel[0]))}


def yaw_of(s, sid):
    """The direction (degrees to the right of the master camera, 0..359) a shot's camera looks in."""
    c0, c = master_cam(s), S3.camera(s, s["shots"][sid])
    a = np.asarray(c0["look_at"], float)[:2] - np.asarray(c0["pos"], float)[:2]
    b = np.asarray(c["look_at"], float)[:2] - np.asarray(c["pos"], float)[:2]
    return math.degrees(math.atan2(b[0], b[1]) - math.atan2(a[0], a[1])) % 360  # clockwise from a to b = to the right


def view_index(s, sid):
    """Which of the four direction views a shot's camera looks at (the nearest yaw)."""
    y = yaw_of(s, sid)
    return min(range(4), key=lambda i: min(abs(y - YAWS[i]), 360 - abs(y - YAWS[i])))


def empty(s):
    return dict(s, people=[])


def view_landmarks(s, w=320, h=180):
    """[[landmark labels left to right] per direction view]: the objects of the set the empty place shows there (no people)."""
    e = empty(s)
    out = []
    for yaw in YAWS:
        ident, _, _ = S3.render(e, view_cam(s, yaw, (w, h)), w, h)
        out.append([it["label"] for it, _ in S3.visible(e, ident, "objects")])
    return out


def turnaround_prompt(sc, s, trigger):
    """The text of the four-view picture of the empty place."""
    inside = "Always inside the same room." if s["kind"] == "interior" else "Always outdoors in the same place."
    parts = []
    for i, lm in enumerate(view_landmarks(s)):
        what = ("from left to right: " + ", ".join(lm) + ".") if lm else "none of the landmarks is in view here, only the plain surroundings of the place."
        parts.append(f"{ORDER[i]} panel, the view {VIEW_NAMES[i]}: {what}")
    return (f"{trigger}, Image 1 is a wide shot of this scene. Draw a 2x2 grid separated by thin white borders: the same EMPTY place with no people at all, "
            f"seen from the same spot in four directions, a 90 degree wide view each, in the same drawn style, with the same buildings, objects and light. "
            f"The place: {sc['place']} {inside} " + " ".join(parts))


def dir_words(s, shot_ids, number):
    """The paragraph that tells the grid prompt how to use the turnaround (Image ``number``): which view lies behind and beside each panel."""
    out = [f"Image {number} is a 2x2 picture of the same empty place from four directions around the first panel's camera "
           f"(top-left: straight ahead, top-right: turned 90 degrees to the right, bottom-left: turned around, bottom-right: turned 90 degrees to the left); "
           "use it for what lies in each direction, to the sides of and behind every panel."]
    for i, sid in enumerate(shot_ids):
        out.append(f"{ORDER[i].capitalize()} panel looks like the {ORDER[view_index(s, sid)]} view of Image {number}.")
    return " ".join(out)


# --- the sketch -------------------------------------------------------------------------------------------------------------------

def _font(px):
    from PIL import ImageFont
    for name in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            pass
    try:
        return ImageFont.load_default(px)
    except TypeError:
        return ImageFont.load_default()


def _edges(ident):
    e = np.zeros(ident.shape, bool)
    e[:, 1:] |= ident[:, 1:] != ident[:, :-1]
    e[1:, :] |= ident[1:, :] != ident[:-1, :]
    return e


def sketch_panel(s, sid, w=PANEL[0], h=PANEL[1]):
    """A plain line drawing of one panel from the ray cast: black outlines of the landmarks with their names, a stick figure with a name for each person."""
    from PIL import Image, ImageDraw
    ident, _, _ = S3.render(s, S3.camera(s, s["shots"][sid]), w, h)
    img = Image.new("RGB", (w, h), "white")
    px = np.asarray(img).copy()
    edge = _edges(ident) & (ident >= 0)
    for _ in range(2):  # a line three pixels wide
        edge = edge | np.roll(edge, 1, 0) | np.roll(edge, 1, 1)
    px[edge] = 0
    img = Image.fromarray(px)
    dr = ImageDraw.Draw(img)
    f = _font(max(14, h // 22))
    nobj = len(s["objects"])
    for i, ob in enumerate(s["objects"]):
        m = ident == i
        if m.mean() >= S3.MIN_PIXELS:
            ys, xs = np.nonzero(m)
            dr.text((float(xs.mean()), float(ys.mean())), ob["label"], fill=(0, 0, 0), font=f, anchor="mm")
    for j, p in enumerate(s["people"]):
        m = ident == nobj + j
        if m.mean() < S3.MIN_PIXELS / 4:
            continue
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        cx, bh = (x0 + x1) / 2, y1 - y0
        hr = bh * 0.09
        lw = max(4, int(h / 140))
        top, neck, hip = y0, y0 + 2 * hr, y0 + bh * 0.55
        dr.ellipse([cx - hr, top, cx + hr, top + 2 * hr], outline=(0, 0, 0), width=lw)
        dr.line([cx, neck, cx, hip], fill=(0, 0, 0), width=lw)
        dr.line([cx - bh * 0.18, neck + bh * 0.22, cx, neck + bh * 0.05, cx + bh * 0.18, neck + bh * 0.22], fill=(0, 0, 0), width=lw)
        dr.line([cx - bh * 0.14, y1, cx, hip, cx + bh * 0.14, y1], fill=(0, 0, 0), width=lw)
        dr.text((cx, max(0, y0 - h // 30)), p["id"].replace("_", " "), fill=(200, 0, 0), font=_font(max(16, h // 18)), anchor="mm")
    return img


def sketch_canvas(s, shot_ids, panel=PANEL):
    """The four sketches in the grid's 2x2 order, thin grey borders between them."""
    from PIL import Image
    cv = Image.new("RGB", (2 * panel[0], 2 * panel[1]), (160, 160, 160))
    for i, sid in enumerate(shot_ids):
        cv.paste(sketch_panel(s, sid, *panel).resize((panel[0] - 4, panel[1] - 4)), ((i % 2) * panel[0] + 2, (i // 2) * panel[1] + 2))
    return cv


def sketch_words(number):
    return (f"Image {number} is a plain line sketch of the four panels in the same 2x2 order: it only shows who stands where and where each landmark is in each panel, "
            "with their names written on it. Follow it for the positions. Draw the real pictures; draw none of its lines, stick figures or letters.")


# --- the paintover (round 3a, Opus plan 13, 2026-10-26): the ray cast as a shaded colour picture, painted over by the model ---------------

SKY, FLOOR, WALL, NEUTRAL = (205, 215, 228), (150, 136, 112), (190, 176, 152), (170, 150, 120)


def shaded_plate(s, sid, w=PANEL[0], h=PANEL[1]):
    """The EMPTY place from one shot's camera as a soft colour picture: muted object colours, a warm floor, a pale sky, Lambert shading and haze.
    It is the init of an SDEdit paintover (the model repaints every pixel, the geometry stays), never a control image."""
    from PIL import Image
    e = empty(s)
    ident, tmap, shade = S3.render(e, S3.camera(s, s["shots"][sid]), w, h)
    img = np.zeros((h, w, 3), float)
    img[ident == -1] = SKY
    img[ident == -2] = WALL
    img[ident == -3] = FLOOR
    for i, ob in enumerate(s["objects"]):
        img[ident == i] = 0.45 * np.asarray(ob["color"], float) + 0.55 * np.asarray(NEUTRAL, float)
    img *= shade[..., None]
    far = float(s.get("far", 60.0))
    haze = np.clip(np.nan_to_num(tmap, nan=far) / far, 0, 1)[..., None] * (ident >= -3)[..., None] * (s["kind"] != "interior")
    img = img * (1 - 0.6 * haze) + np.asarray(SKY, float) * 0.6 * haze
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def people_words(s, sid, w=320, h=180):
    """{person id: where the ray cast puts them in this shot} in words: the third of the picture and the share of its height."""
    ident, _, _ = S3.render(s, S3.camera(s, s["shots"][sid]), w, h)
    out = {}
    for j, p in enumerate(s["people"]):
        m = ident == len(s["objects"]) + j
        if m.mean() < S3.MIN_PIXELS / 4:
            continue
        ys, xs = np.nonzero(m)
        cx = (xs.min() + xs.max()) / 2 / w
        part = "left third" if cx < 1 / 3 else "right third" if cx > 2 / 3 else "middle third"
        out[p["id"]] = f"stands in the {part} of the picture and is about {int(round(100 * (ys.max() - ys.min() + 1) / h, -1))} percent of its height"
    return out
