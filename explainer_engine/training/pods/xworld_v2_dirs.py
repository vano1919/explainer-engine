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


def all_labels(s):
    """The labels of every object of the set, once each, in the set's order."""
    return list(dict.fromkeys(o["label"] for o in s["objects"]))


def view_prompt(sc, s, i, trigger):
    """The text of ONE direction view (round 3b, Opus 2026-10-27: one prompt for four panels drew the same place four times): what this yaw shows
    from left to right and what must NOT be seen, both from the ray cast of the set."""
    lm = view_landmarks(s)[i]
    absent = [x for x in all_labels(s) if x not in lm]
    inside = "Always inside the same room." if s["kind"] == "interior" else "Always outdoors in the same place."
    shown = ("In this picture, from left to right: " + ", ".join(lm) + ".") if lm else "None of the landmarks is in view here, only the plain surroundings of the place."
    hidden = (" These are NOT visible in this picture, they are behind the camera or out of view: " + ", ".join(absent) + ".") if absent else ""
    turn = "the same view as Image 1" if i == 0 else f"the camera standing in the same spot, {VIEW_NAMES[i]}"
    return (f"{trigger}, Image 1 is a wide shot of this scene. Draw ONE picture of the same EMPTY place with no people at all: {turn}, "
            f"a 90 degree wide view, in the same drawn style, with the same buildings, objects and light. The place: {sc['place']} {inside} {shown}{hidden}")


def view_checklist(sc, s):
    """For the eye or a local model that checks the four turnaround pictures: per view what must be seen, left to right, and what must not."""
    out = []
    for i, lm in enumerate(view_landmarks(s)):
        out.append({"view": i, "name": VIEW_NAMES[i], "yaw": YAWS[i], "must_show_left_to_right": lm,
                    "must_not_show": [x for x in all_labels(s) if x not in lm]})
    return out


def compose_turn(views, panel=PANEL):
    """The four separately drawn views as the 2x2 turnaround picture (the order of YAWS)."""
    from PIL import Image
    out = Image.new("RGB", (2 * panel[0], 2 * panel[1]), (255, 255, 255))
    for i, v in enumerate(views):
        out.paste(v.convert("RGB").resize(panel), ((i % 2) * panel[0], (i // 2) * panel[1]))
    return out


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


# --- backdrop per panel (round 3a finding, 2026-10-27): the grid COPIES the turnaround panel by panel, so the panels of the turnaround are arranged
# --- in the order of the grid, each cut to its shot's direction and field of view, and the model only adds the people -----------------------

def _crop_box(s, sid, panel=PANEL):
    """(view index, left, top, right, bottom) in the 1280x704 view picture of the crop that a shot sees: the direction offset and the narrower field of view."""
    cam = S3.camera(s, s["shots"][sid])
    i = view_index(s, sid)
    d = (yaw_of(s, sid) - YAWS[i] + 180) % 360 - 180  # degrees right of the view's centre
    vf = math.radians(cam["vfov"])
    half_s = math.tan(vf / 2) * panel[0] / panel[1]  # tan of half the shot's horizontal field of view
    fw = min(1.0, half_s / math.tan(math.radians(45)))  # share of the 90 degree view that the shot sees
    cx = 0.5 + math.tan(math.radians(max(-45, min(45, d)))) / 2
    pos, look = np.asarray(cam["pos"], float), np.asarray(cam["look_at"], float)
    hd = float(np.linalg.norm((look - pos)[:2])) or 1.0
    pitch = math.atan2(look[2] - pos[2], hd)
    vview = math.radians(math.degrees(2 * math.atan(math.tan(math.radians(45)) * panel[1] / panel[0])))
    cy = 0.5 - math.tan(pitch) / (2 * math.tan(vview / 2))
    cx, cy = min(max(cx, fw / 2), 1 - fw / 2), min(max(cy, fw / 2), 1 - fw / 2)
    return i, (cx - fw / 2) * panel[0], (cy - fw / 2) * panel[1], (cx + fw / 2) * panel[0], (cy + fw / 2) * panel[1]


BLEND_DEG = 8.0  # a ray within this many degrees of the line between two views takes both (a smooth seam instead of a hard cut)


def _view_weights(psi):
    """{view index: weight} of the views a ray of global yaw ``psi`` (degrees) is read from: the nearest view, and its neighbour near the seam."""
    d = [((psi - y + 180) % 360) - 180 for y in YAWS]  # signed offset of the ray from each view's centre
    i = min(range(4), key=lambda k: abs(d[k]))
    w = {i: 1.0}
    edge = 45.0 - abs(d[i])  # degrees to the seam
    if edge < BLEND_DEG:
        j = (i + (1 if d[i] > 0 else -1)) % 4
        a = 0.5 * (1 - edge / BLEND_DEG)  # 0.5 on the seam, 0 at BLEND_DEG from it
        w = {i: 1 - a, j: a}
    return w


BLEND_DEG = 8.0  # a ray within this many degrees of the line between two views reads both (a soft seam instead of a hard cut)


def view_weight(d):
    """Weight (0..1) of a direction view for a ray ``d`` degrees (array) from its centre: 1 inside, 0.5 on the seam at 45, 0 beyond 45 + BLEND_DEG."""
    return np.clip((45.0 + BLEND_DEG - np.abs(d)) / (2 * BLEND_DEG), 0.0, 1.0)


def reproject(turn, yaw_deg, pitch, hfov, size, view=PANEL):
    """The picture a camera looking ``yaw_deg`` degrees to the right of the master (pitch in radians, horizontal field of view ``hfov`` in radians)
    would see, read out of the turnaround picture ``turn`` (2x2 of the four 90 degree views): every output ray reads the view it points into, rays near the
    line between two views read both, so a shot that looks between two views gets a soft seam. The camera position is taken as the master's."""
    from PIL import Image
    w, h = size
    tan_h = math.tan(hfov / 2)
    tan_v = tan_h * h / w
    right = ((np.arange(w) + 0.5) / w - 0.5)[None, :] * 2 * tan_h * np.ones((h, 1))
    up = (0.5 - (np.arange(h) + 0.5) / h)[:, None] * 2 * tan_v * np.ones((1, w))
    y0, cp, sp = math.radians(yaw_deg), math.cos(pitch), math.sin(pitch)
    fwd = np.array([math.sin(y0) * cp, math.cos(y0) * cp, sp])
    rgt = np.array([math.cos(y0), -math.sin(y0), 0.0])
    upv = np.array([-math.sin(y0) * sp, -math.cos(y0) * sp, cp])
    ray = fwd + right[..., None] * rgt + up[..., None] * upv  # (h, w, 3): east, north, up
    horiz = np.hypot(ray[..., 0], ray[..., 1])
    psi = np.degrees(np.arctan2(ray[..., 0], ray[..., 1]))
    src = np.asarray(turn.convert("RGB"), float)
    vw, vh = view
    tan_vv = math.tan(math.radians(45)) * vh / vw
    out, wsum = np.zeros((h, w, 3)), np.zeros((h, w, 1))
    for i in range(4):
        d = ((psi - YAWS[i] + 180) % 360) - 180
        wt = view_weight(d)[..., None]
        if not wt.any():
            continue
        dr = np.radians(np.clip(d, -80, 80))
        x = np.tan(dr)
        y = ray[..., 2] / np.maximum(horiz * np.cos(dr), 1e-6)
        u = np.clip((0.5 + x / 2) * vw, 0, vw - 1.001)
        v = np.clip((0.5 - y / (2 * tan_vv)) * vh, 0, vh - 1.001)
        u0, v0 = np.floor(u).astype(int), np.floor(v).astype(int)
        fu, fv = (u - u0)[..., None], (v - v0)[..., None]
        ox, oy = (i % 2) * vw, (i // 2) * vh
        px = (src[oy + v0, ox + u0] * (1 - fu) * (1 - fv) + src[oy + v0, ox + u0 + 1] * fu * (1 - fv)
              + src[oy + v0 + 1, ox + u0] * (1 - fu) * fv + src[oy + v0 + 1, ox + u0 + 1] * fu * fv)
        out += px * wt
        wsum += wt
    return Image.fromarray(np.clip(out / np.maximum(wsum, 1e-6), 0, 255).astype(np.uint8))


def plate_view(turn, s, sid, panel=PANEL):
    """The empty backdrop of one shot: the turnaround read along the shot camera's own yaw, pitch and field of view."""
    cam = S3.camera(s, s["shots"][sid])
    pos, look = np.asarray(cam["pos"], float), np.asarray(cam["look_at"], float)
    d = look - pos
    pitch = math.atan2(d[2], float(np.hypot(d[0], d[1])) or 1.0)
    hfov = 2 * math.atan(math.tan(math.radians(cam["vfov"]) / 2) * panel[0] / panel[1])
    return reproject(turn, yaw_of(s, sid), pitch, hfov, panel)


def plate_grid(turn, s, shot_ids, panel=PANEL):
    """The 2x2 picture of one EMPTY backdrop per panel, each read out of the turnaround picture ``turn`` along its own shot camera."""
    from PIL import Image
    out = Image.new("RGB", (2 * panel[0], 2 * panel[1]), (255, 255, 255))
    for k, sid in enumerate(shot_ids):
        out.paste(plate_view(turn, s, sid, panel), ((k % 2) * panel[0], (k // 2) * panel[1]))
    return out


def people_rule(s, sid):
    """Who is in this panel, as a hard rule in words: the number of people and, for an over-the-shoulder shot, who is seen from behind (once only)."""
    ids = [i for i in people_words(s, sid)]
    back = s["shots"][sid].get("ots")
    if back and back not in ids:
        ids.append(back)
    if not ids:
        return ""
    txt = f"Exactly {len(ids)} {'person' if len(ids) == 1 else 'people'} in this panel: {', '.join(ids)}; nobody else, nobody twice."
    if back:
        txt += f" The person seen from behind, back to the camera, is {back}; {back} appears only that once."
    return txt


def plate_words(s, shot_ids, number):
    """The paragraph for a +dpl cell: Image ``number`` holds the empty backdrop of every panel; the people are added where the ray cast puts them."""
    out = [f"Image {number} is a 2x2 picture of the EMPTY backdrop of each of the four panels, in the same order, with no people. Draw the storyboard on it: keep every panel's "
           "place, objects, horizon, camera and light exactly as in Image " + str(number) + ", and ADD the people of that panel into it, every person named for that panel, "
           "the full number of them, in the same style."]
    for i, sid in enumerate(shot_ids):
        w = people_words(s, sid)
        if w:
            out.append(f"{ORDER[i].capitalize()} panel: " + "; ".join(f"the {n} {t}" for n, t in w.items()) + ". " + people_rule(s, sid))
    return " ".join(out)
